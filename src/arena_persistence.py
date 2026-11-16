"""Portable, strict local file wrapper for generated Arena checkpoints."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import stat
import zipfile

from arena_native_snapshot import encode as encode_native, decode as decode_native


SCHEMA = 'universe.generated-arena-save/10'
_PREVIOUS_SCHEMAS = frozenset(('universe.generated-arena-save/9', 'universe.generated-arena-save/8', 'universe.generated-arena-save/7', 'universe.generated-arena-save/6', 'universe.generated-arena-save/5', 'universe.generated-arena-save/4'))
MAX_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 4098
MAX_ARCHIVE_CONTENT_BYTES = 64 * 1024 * 1024
_FIELDS = frozenset(('schema','native_state_base64','session','sha256'))
_ARCHIVE_SCHEMA = 'universe.generated-arena-portable-archive/1'


class ArenaSaveRejected(ValueError):
    """Arena save data is malformed or outside the reviewed file contract."""


def _pairs(rows):
    result={}
    for key,value in rows:
        if key in result:raise ArenaSaveRejected('duplicate Arena save field')
        result[key]=value
    return result


def _canonical(value):
    try:
        return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),
                          allow_nan=False).encode('utf-8')
    except (TypeError,ValueError,UnicodeError,RecursionError) as exc:
        raise ArenaSaveRejected(f'Arena save contains unsupported data: {exc}') from exc


def _tree(value,depth=0,count=None):
    if count is None:count=[0]
    count[0]+=1
    if count[0]>1_000_000 or depth>96:raise ArenaSaveRejected('Arena save exceeds structural limits')
    if value is None or type(value) in (bool,int,str):return
    if type(value) is float:
        if not math.isfinite(value):raise ArenaSaveRejected('Arena save contains a non-finite number')
        return
    if type(value) is list:
        for row in value:_tree(row,depth+1,count)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for row in value.values():_tree(row,depth+1,count)
        return
    raise ArenaSaveRejected('Arena save contains an unsupported value')


def _session_record(session, native_wire):
    from arena_browser_session import GeneratedArenaSession
    from arena_initialization import ArenaInitializationCandidate
    from arena_movement_plan_checkpoint import capture_accepted_plan
    if type(session) is not GeneratedArenaSession:
        raise ArenaSaveRejected('GeneratedArenaSession is required')
    candidate=session._active
    if type(candidate) is not ArenaInitializationCandidate:
        raise ArenaSaveRejected('Generate an Arena before saving')
    if session._opponent_strategy not in ('none', 'attack_only', 'defense_only'):
        raise ArenaSaveRejected('Arena opponent strategy is unsupported')
    if (session._encounter_mode not in ('player_vs_arena', 'arena_vs_arena')
            or type(session._arena_strategies) is not list or len(session._arena_strategies) != 2
            or any(value not in ('none', 'attack_only', 'defense_only')
                   for value in session._arena_strategies)):
        raise ArenaSaveRejected('Arena mode or controller strategies are unsupported')
    players=candidate.participants
    sources=[]
    for participant in players:
        native=participant.native
        sources.append([participant.role,participant.native.being.id,
            base64.b64encode(native.source_record_bytes).decode('ascii'),
            native.source_sha256,native.engine_identity,native.skills_status])
    grounds=[]
    for row in candidate.ground_objects:
        grounds.append([row.source_item_id,row.native_object_id,row.category,
            row.native_type_key,row.origin,row.column,row.row,
            [float(v).hex() for v in row.position.as_tuple()]])
    plan=None
    if session._movement_plan is not None:
        try:plan=base64.b64encode(capture_accepted_plan(session)).decode('ascii')
        except (TypeError,ValueError) as exc:
            raise ArenaSaveRejected(f'accepted movement plan is not portable: {exc}') from exc
    premise=candidate.world_premise
    return {
        'encounter_name':session._encounter_name,
        'player_name':session._player_name,
        'player_id':players[0].native.being.id,
        'opponent_id':players[1].native.being.id,
        'starting_experience':candidate.starting_experience,
        'root_seed':candidate.root_seed,
        'placement_seed':candidate.placement_seed,
        'map':[candidate.arena_map.width_cells,candidate.arena_map.height_cells],
        'world_premise':[premise.terrain,premise.route,float(premise.terrain_multiplier).hex(),
            float(premise.hampered_multiplier).hex(),premise.unobstructed,premise.collision_adjudicated],
        'display_names':[[key,value] for key,value in sorted(session._display_names.items())],
        'movement_plan_base64':plan,
        'movement_sequence':session._movement_sequence,
        'selected_entity_id':next((key for key,value in session._view_handles.items()
            if value==session._selected_entity_handle),None),
        'source_beings':sources,
        'ground_objects':grounds,
        'ground_loadout_provenance':list(candidate.ground_loadout_provenance),
        'initial_equipment_provenance':list(candidate.initial_equipment_provenance),
        'equipment_mode':candidate.equipment_mode,
        'opponent_strategy':session._opponent_strategy,
        'encounter_mode':session._encounter_mode,
        'arena_strategies':list(session._arena_strategies),
        'authored_scenario_id':session._authored_scenario_id,
    }


def encode(session, native_inventory):
    from arena_history_segments import split
    try:
        snapshot, segments, metrics = split(native_inventory)
    except (TypeError, ValueError) as exc:
        raise ArenaSaveRejected(f'native Arena state cannot be segmented: {exc}') from exc
    with session._lock:
        record=_session_record(session,b'')
        _tree(record)
        entries={'session.json':_canonical(record), 'snapshot.json':snapshot}
        for index, segment in enumerate(segments):
            entries[f'history/segment-{index:06d}.json']=segment
        _need_archive(len(entries) <= MAX_ARCHIVE_ENTRIES,
                      'Arena archive has too many independent entries')
        total_content=sum(map(len,entries.values()))
        _need_archive(total_content <= MAX_ARCHIVE_CONTENT_BYTES,
                      'Arena archive exceeds aggregate decoded content limit')
        listing=[{'name':name,'size':len(data),
                  'sha256':hashlib.sha256(data).hexdigest()}
                 for name,data in sorted(entries.items())]
        manifest_payload={'schema':_ARCHIVE_SCHEMA,'save_schema':SCHEMA,
            'entry_count':len(entries),'history_segment_count':len(segments),
            'snapshot_cursor':metrics['history_cursor'],
            'snapshot_sha256':hashlib.sha256(snapshot).hexdigest(),
            'entries':listing,
            'metrics':{'snapshot_bytes':metrics['snapshot_bytes'],
                'history_bytes':metrics['history_bytes'],
                'snapshot_nodes':metrics['snapshot_nodes'],
                'snapshot_depth':metrics['snapshot_depth'],
                'history_wire_nodes':metrics['history_wire_nodes'],
                'history_max_depth':metrics['history_max_depth'],
                'history_segments':metrics['history_segment_count'],
                'history_owned_nodes':metrics['history_owned_nodes'],
                'total_inventory_nodes':metrics['total_inventory_nodes'],
                'history_field_entries':metrics['history_field_entries']}}
        manifest=_canonical(dict(manifest_payload,
            sha256=hashlib.sha256(_canonical(manifest_payload)).hexdigest()))
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6,strict_timestamps=True) as archive:
            _write_archive_entry(archive,'manifest.json',manifest)
            for name,data in sorted(entries.items()):
                _write_archive_entry(archive,name,data)
        wire=output.getvalue()
    if len(wire)>MAX_BYTES:raise ArenaSaveRejected('Arena archive exceeds the file size limit')
    return wire


def _need_archive(ok, message):
    if not ok:raise ArenaSaveRejected(message)


def _write_archive_entry(archive,name,data):
    info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
    info.compress_type=zipfile.ZIP_DEFLATED
    info.external_attr=0o600 << 16
    info.create_system=3
    archive.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)


def _decode_archive(wire):
    from arena_history_segments import reassemble
    _need_archive(type(wire) is bytes and len(wire)<=MAX_BYTES,
                  'Arena archive is empty or exceeds the file limit')
    try:
        archive=zipfile.ZipFile(io.BytesIO(wire),'r')
    except (zipfile.BadZipFile, OSError) as exc:
        raise ArenaSaveRejected('Arena portable archive is invalid') from exc
    with archive:
        infos=archive.infolist()
        _need_archive(0<len(infos)<=MAX_ARCHIVE_ENTRIES,
                      'Arena archive entry count is outside limits')
        names=[item.filename for item in infos]
        _need_archive(len(names)==len(set(names)) and 'manifest.json' in names,
                      'Arena archive has duplicate entries or no manifest')
        _need_archive(all(not item.is_dir() and not item.flag_bits & 1
                          and item.compress_type in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED)
                          and stat.S_IFMT(item.external_attr >> 16) != stat.S_IFLNK
                          and item.file_size<=MAX_ARCHIVE_CONTENT_BYTES
                          and item.filename and not item.filename.startswith('/')
                          and '\\' not in item.filename
                          and all(part not in ('','.','..') for part in item.filename.split('/'))
                          for item in infos),
                      'Arena archive entry path or metadata is unsafe')
        decoded_total=sum(item.file_size for item in infos)
        _need_archive(decoded_total<=MAX_ARCHIVE_CONTENT_BYTES,
                      'Arena archive exceeds aggregate decoded content limit')
        _need_archive(all(item.file_size <= max(1,item.compress_size)*200
                          for item in infos),
                      'Arena archive compression ratio exceeds safety limit')
        try:
            raw={item.filename:archive.read(item) for item in infos}
        except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
            raise ArenaSaveRejected('Arena archive CRC or decompression validation failed') from exc
    def parse(name):
        try:
            value=json.loads(raw[name].decode('utf-8'),object_pairs_hook=_pairs,
                parse_constant=lambda _x:(_ for _ in ()).throw(ValueError('nonfinite number')))
        except (KeyError,UnicodeError,ValueError,RecursionError) as exc:
            raise ArenaSaveRejected(f'Arena archive {name} is invalid JSON') from exc
        canonical=(_canonical(value) if name=='session.json'
                   else __import__('arena_history_segments')._canonical(value))
        if canonical!=raw[name]:
            raise ArenaSaveRejected(f'Arena archive {name} is not canonical')
        return value
    manifest=parse('manifest.json')
    fields={'schema','save_schema','entry_count','history_segment_count',
            'snapshot_cursor','snapshot_sha256','entries','metrics','sha256'}
    _need_archive(type(manifest) is dict and set(manifest)==fields
        and manifest['schema']==_ARCHIVE_SCHEMA and manifest['save_schema']==SCHEMA,
        'Arena archive manifest schema is unknown or malformed')
    payload={key:value for key,value in manifest.items() if key!='sha256'}
    _need_archive(type(manifest['sha256']) is str and hashlib.sha256(_canonical(payload)).hexdigest()==manifest['sha256'],
                  'Arena archive manifest digest does not match')
    metric_fields={'snapshot_bytes','history_bytes','snapshot_nodes',
                   'snapshot_depth','history_wire_nodes','history_max_depth',
                   'history_segments','history_owned_nodes',
                   'total_inventory_nodes','history_field_entries'}
    metrics=manifest['metrics']
    history_field_entries=metrics.get('history_field_entries') if type(metrics) is dict else None
    _need_archive(type(metrics) is dict and set(metrics)==metric_fields
        and all(type(value) is int and value>=0 for key,value in metrics.items()
                if key!='history_field_entries')
        and type(history_field_entries) is dict
        and all(type(key) is str and type(value) is int and value>=0
                for key,value in history_field_entries.items())
        and type(manifest['snapshot_cursor']) is int and manifest['snapshot_cursor']>=0,
        'Arena archive metrics or history cursor are malformed')
    listing=manifest['entries']
    _need_archive(type(listing) is list and manifest['entry_count']==len(raw)-1
                  and len(listing)==len(raw)-1,
                  'Arena archive manifest entry set is incomplete')
    declared={}
    for row in listing:
        _need_archive(type(row) is dict and set(row)=={'name','size','sha256'}
            and type(row['name']) is str and row['name'] not in declared
            and type(row['size']) is int and type(row['sha256']) is str,
            'Arena archive manifest entry is malformed')
        declared[row['name']]=row
    _need_archive(set(raw)-{'manifest.json'}==set(declared),
                  'Arena archive contains undeclared or missing entries')
    for name,row in declared.items():
        _need_archive(len(raw[name])==row['size']
            and hashlib.sha256(raw[name]).hexdigest()==row['sha256'],
            'Arena archive entry digest or size does not match')
    segment_names=sorted(name for name in raw if name.startswith('history/'))
    expected_names=[f'history/segment-{index:06d}.json'
                    for index in range(len(segment_names))]
    _need_archive(segment_names==expected_names
        and manifest['history_segment_count']==len(segment_names)
        and set(raw)-{'manifest.json'}=={'snapshot.json','session.json',*segment_names},
        'Arena archive history segments are missing, duplicated or unordered')
    snapshot_wire=raw['snapshot.json']
    snapshot_value=parse('snapshot.json')
    expected_field_entries={}
    for descriptor in snapshot_value['history_fields']:
        _need_archive(type(descriptor) is list and len(descriptor)==5
            and type(descriptor[2]) is str and type(descriptor[3]) is str
            and type(descriptor[4]) is int and descriptor[4]>=0,
            'Arena snapshot history field catalog is malformed')
        key=f'{descriptor[2]}.{descriptor[3]}'
        expected_field_entries[key]=expected_field_entries.get(key,0)+descriptor[4]
    _need_archive(history_field_entries==expected_field_entries,
                  'Arena archive history field counts disagree with its snapshot')
    _need_archive(hashlib.sha256(snapshot_wire).hexdigest()==manifest['snapshot_sha256'],
                  'Arena resumable snapshot digest does not match')
    inventory,archive_metrics=reassemble(snapshot_wire,
        tuple(raw[name] for name in segment_names),snapshot_value=snapshot_value,
        include_metrics=True)
    sections={row[0]:row[1:] for row in inventory[1][1:]}
    nodes=sections['nodes'][0]
    encounter_rows=[row for row in nodes if row[1]=='encounter.Encounter']
    _need_archive(len(encounter_rows)==1,'Arena archive must contain one Encounter')
    cursor=dict(encounter_rows[0][2]).get('last_processed_boundary')
    _need_archive(type(cursor) is tuple and len(cursor)==2 and cursor[0]=='integer'
        and cursor[1].isdigit() and int(cursor[1])==manifest['snapshot_cursor'],
        'Arena history cursor disagrees with native Encounter state')
    _need_archive(metrics['snapshot_bytes']==len(snapshot_wire)
        and metrics['history_bytes']==sum(len(raw[name]) for name in segment_names)
        and metrics['snapshot_nodes']==archive_metrics['snapshot_nodes']
        and metrics['history_wire_nodes']==archive_metrics['history_wire_nodes']
        and metrics['snapshot_depth']==archive_metrics['snapshot_depth']
        and metrics['history_max_depth']==archive_metrics['history_max_depth']
        and metrics['history_owned_nodes']==archive_metrics['history_owned_nodes']
        and metrics['total_inventory_nodes']==len(nodes)
        and metrics['history_segments']==len(segment_names),
        'Arena archive measured content does not match its manifest')
    session=parse('session.json')
    return {'schema':SCHEMA,'session':session,'decoded_native':inventory,
            'native_wire':None,'manifest':manifest}


def decode(wire):
    if type(wire) is not bytes or not wire or len(wire)>MAX_BYTES:
        raise ArenaSaveRejected('Arena save is empty or exceeds the file size limit')
    segmented=wire.startswith(b'PK\x03\x04')
    if segmented:
        data=_decode_archive(wire)
    else:
        try:data=json.loads(wire.decode('utf-8'),object_pairs_hook=_pairs,
            parse_constant=lambda _x:(_ for _ in ()).throw(ArenaSaveRejected('non-finite JSON number')))
        except ArenaSaveRejected:raise
        except (UnicodeDecodeError,json.JSONDecodeError,RecursionError) as exc:
            raise ArenaSaveRejected(f'Arena save is not valid UTF-8 JSON: {exc}') from exc
        if (type(data) is not dict or set(data)!=_FIELDS
                or data['schema'] not in _PREVIOUS_SCHEMAS):
            raise ArenaSaveRejected('unknown Arena save schema or field set')
        payload={key:data[key] for key in data if key!='sha256'}
        if type(data['sha256']) is not str or hashlib.sha256(_canonical(payload)).hexdigest()!=data['sha256']:
            raise ArenaSaveRejected('Arena save digest does not match its contents')
        if _canonical(data)!=wire:raise ArenaSaveRejected('Arena save is not canonical')
    _tree(data['session'])
    if segmented:
        native_wire=None
        decoded=data['decoded_native']
    else:
        try:native_wire=base64.b64decode(data['native_state_base64'],validate=True)
        except (TypeError,ValueError) as exc:raise ArenaSaveRejected('embedded native state encoding is invalid') from exc
        try:decoded=decode_native(native_wire)
        except (TypeError,ValueError) as exc:raise ArenaSaveRejected(f'embedded native Arena state refused: {exc}') from exc
    s=data['session']
    required={'encounter_name','player_name','player_id','opponent_id','starting_experience',
        'root_seed','placement_seed',
        'map','world_premise','display_names','movement_plan_base64','movement_sequence',
        'selected_entity_id','source_beings','ground_objects','ground_loadout_provenance',
        'initial_equipment_provenance','equipment_mode'}
    if data['schema'] in (SCHEMA, 'universe.generated-arena-save/8',
                           'universe.generated-arena-save/7'):
        required.update(('opponent_strategy', 'authored_scenario_id', 'encounter_mode', 'arena_strategies'))
    elif data['schema'] == 'universe.generated-arena-save/6':
        required.update(('opponent_strategy', 'authored_scenario_id'))
    elif data['schema'] == 'universe.generated-arena-save/5':
        required.add('opponent_strategy')
    if type(s) is not dict or set(s)!=required:
        raise ArenaSaveRejected('Arena session metadata has unknown or missing fields')
    for key in ('encounter_name','player_name','player_id','opponent_id'):
        if type(s[key]) is not str or not s[key].strip() or len(s[key])>80:
            raise ArenaSaveRejected(f'Arena {key} is malformed')
    if (type(s['starting_experience']) is not int or s['starting_experience']<0
            or type(s['root_seed']) is not int or s['root_seed']<0
            or type(s['placement_seed']) is not int or s['placement_seed']<0
            or type(s['movement_sequence']) is not int or s['movement_sequence']<0):
        raise ArenaSaveRejected('Arena numeric session metadata is malformed')
    if (type(s['map']) is not list or len(s['map'])!=2
            or any(type(v) is not int or v<5 for v in s['map'])):
        raise ArenaSaveRejected('Arena map dimensions are malformed')
    if type(s['display_names']) is not list or any(type(row) is not list or len(row)!=2
            or any(type(v) is not str or not v for v in row) for row in s['display_names']):
        raise ArenaSaveRejected('Arena display-name records are malformed')
    if type(s['source_beings']) is not list or len(s['source_beings'])!=2:
        raise ArenaSaveRejected('Arena source Being records are malformed')
    if type(s['ground_objects']) is not list:
        raise ArenaSaveRejected('Arena ground Object records are malformed')
    if (type(s['ground_loadout_provenance']) is not list
            or type(s['initial_equipment_provenance']) is not list
            or s['equipment_mode'] not in ('equipped','unequipped')):
        raise ArenaSaveRejected('Arena starting equipment provenance is malformed')
    if data['schema'] in _PREVIOUS_SCHEMAS:
        s.setdefault('authored_scenario_id', None)
        s.setdefault('encounter_mode', 'player_vs_arena')
        s.setdefault('arena_strategies', ['none', s.get('opponent_strategy', 'none')])
    if data['schema'] == 'universe.generated-arena-save/4':
        s['opponent_strategy'] = 'none'
    if s['opponent_strategy'] not in ('none', 'attack_only', 'defense_only'):
        raise ArenaSaveRejected('Arena opponent strategy is unsupported')
    if (s['encounter_mode'] not in ('player_vs_arena', 'arena_vs_arena')
            or type(s['arena_strategies']) is not list or len(s['arena_strategies']) != 2
            or any(value not in ('none', 'attack_only', 'defense_only')
                   for value in s['arena_strategies'])):
        raise ArenaSaveRejected('Arena mode or controller strategies are unsupported')
    if s['encounter_mode'] == 'player_vs_arena' and s['arena_strategies'][0] != 'none':
        raise ArenaSaveRejected('Player vs Arena save assigns an Arena controller to the player Being')
    if s['authored_scenario_id'] not in (None, 'ordinary-dagger-draw', 'arena-spot-demo'):
        raise ArenaSaveRejected('Arena authored scenario provenance is unsupported')
    if s['movement_plan_base64'] is not None:
        try:base64.b64decode(s['movement_plan_base64'],validate=True)
        except (TypeError,ValueError) as exc:raise ArenaSaveRejected('movement plan encoding is invalid') from exc
    result={'native_wire':native_wire,'decoded_native':decoded,'session':s}
    if segmented:result['manifest']=data['manifest']
    return result
