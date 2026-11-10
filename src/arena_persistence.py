"""Portable, strict local file wrapper for generated Arena checkpoints."""
from __future__ import annotations

import base64
import hashlib
import json
import math

from arena_native_snapshot import encode as encode_native, decode as decode_native


SCHEMA = 'universe.generated-arena-save/4'
MAX_BYTES = 64 * 1024 * 1024
_FIELDS = frozenset(('schema','native_state_base64','session','sha256'))


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
    }


def encode(session, native_inventory):
    try:native_wire=encode_native(native_inventory)
    except (TypeError,ValueError) as exc:raise ArenaSaveRejected(f'native Arena state is invalid: {exc}') from exc
    with session._lock:
        record=_session_record(session,native_wire)
        _tree(record)
        payload={'schema':SCHEMA,
            'native_state_base64':base64.b64encode(native_wire).decode('ascii'),
            'session':record}
        wire=_canonical(dict(payload,sha256=hashlib.sha256(_canonical(payload)).hexdigest()))
    if len(wire)>MAX_BYTES:raise ArenaSaveRejected('Arena save exceeds the file size limit')
    return wire


def decode(wire):
    if type(wire) is not bytes or not wire or len(wire)>MAX_BYTES:
        raise ArenaSaveRejected('Arena save is empty or exceeds the file size limit')
    try:data=json.loads(wire.decode('utf-8'),object_pairs_hook=_pairs,
        parse_constant=lambda _x:(_ for _ in ()).throw(ArenaSaveRejected('non-finite JSON number')))
    except ArenaSaveRejected:raise
    except (UnicodeDecodeError,json.JSONDecodeError,RecursionError) as exc:
        raise ArenaSaveRejected(f'Arena save is not valid UTF-8 JSON: {exc}') from exc
    if type(data) is not dict or set(data)!=_FIELDS or data['schema']!=SCHEMA:
        raise ArenaSaveRejected('unknown Arena save schema or field set')
    payload={key:data[key] for key in data if key!='sha256'}
    if type(data['sha256']) is not str or hashlib.sha256(_canonical(payload)).hexdigest()!=data['sha256']:
        raise ArenaSaveRejected('Arena save digest does not match its contents')
    if _canonical(data)!=wire:raise ArenaSaveRejected('Arena save is not canonical')
    _tree(data['session'])
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
    if s['movement_plan_base64'] is not None:
        try:base64.b64decode(s['movement_plan_base64'],validate=True)
        except (TypeError,ValueError) as exc:raise ArenaSaveRejected('movement plan encoding is invalid') from exc
    return {'native_wire':native_wire,'decoded_native':decoded,'session':s}
