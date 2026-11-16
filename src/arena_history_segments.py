"""Generated-Arena snapshot/history split for the native checkpoint contract.

This adapter is intentionally Arena-specific. It moves reviewed append-only
list fields out of the resumable node table, retaining stable list/node IDs so
the ordinary native validator and restore path still see the exact inventory
after the portable archive has verified and reassembled its segments.
"""
from __future__ import annotations

import hashlib
import json


SCHEMA = 'universe.generated-arena-history-segment/1'
SNAPSHOT_SCHEMA = 'universe.generated-arena-resumable-snapshot/1'
MAX_SNAPSHOT_NODES = 1_000_000
MAX_SEGMENT_NODES = 1_000_000
MAX_TOTAL_NODES = 10_000_000
MAX_TOTAL_BYTES = 64 * 1024 * 1024

# Each field is classified by its owner and read contract in
# docs/design/persistence-sufficiency-inventory.md. This is a closed adapter,
# not a naming convention applied to arbitrary future Python fields.
_HISTORY_FIELDS = frozenset({
    ('encounter.Encounter', '_atomic_interval_history'),
    ('encounter.Encounter', 'fatigue_frame_history'),
    ('being.BeingInstance', '_atomic_target_history'),
    ('being.BeingInstance', 'skill_use_history'),
    ('object.ObjectInstance', '_atomic_target_history'),
    ('object.ObjectInstance', '_atomic_projectile_history'),
    ('weapon.WeaponInstance', '_atomic_target_history'),
    ('weapon.WeaponInstance', '_atomic_projectile_history'),
    ('armor.ArmorInstance', '_atomic_target_history'),
    ('arena_perception.ArenaPerceptionLedger', '_history'),
})


class ArenaHistorySegmentsRejected(ValueError):
    pass


def _need(ok, why):
    if not ok:
        raise ArenaHistorySegmentsRejected(why)


def _json(value):
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is tuple:
        return [_json(row) for row in value]
    if type(value) is dict:
        _need(all(type(key) is str for key in value),
              'history segment object key is not text')
        return {key: _json(row) for key, row in value.items()}
    raise ArenaHistorySegmentsRejected('history segment contains unsupported data')


def _tuples(value):
    if type(value) is list:
        return tuple(_tuples(row) for row in value)
    if type(value) is dict:
        return {key: _tuples(row) for key, row in value.items()}
    return value


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=True,
            separators=(',', ':'), allow_nan=False).encode('ascii')
    except (TypeError, ValueError, RecursionError) as exc:
        raise ArenaHistorySegmentsRejected('history archive JSON is not canonical data') from exc


def _count(value, *, max_nodes=MAX_SEGMENT_NODES, max_depth=128):
    count = 0
    stack = [(value, 0)]
    while stack:
        row, depth = stack.pop()
        count += 1
        _need(count <= max_nodes and depth <= max_depth,
              'history archive document exceeds structural limits')
        if type(row) is list:
            stack.extend((item, depth + 1) for item in row)
        elif type(row) is dict:
            _need(all(type(key) is str for key in row),
                  'history archive object key is not text')
            stack.extend((item, depth + 1) for item in row.values())
        else:
            _need(row is None or type(row) in (str, int, bool),
                  'history archive has unsupported JSON data')
    return count


def _max_depth(value):
    maximum = 0
    stack = [(value, 0)]
    while stack:
        row, depth = stack.pop()
        maximum = max(maximum, depth)
        if type(row) is list:
            stack.extend((item, depth + 1) for item in row)
        elif type(row) is dict:
            stack.extend((item, depth + 1) for item in row.values())
    return maximum


def _read_rows(inventory):
    _need(type(inventory) is tuple and len(inventory) == 2,
          'native inventory envelope is malformed')
    compatibility, body = inventory
    _need(type(body) is tuple and len(body) == 5
          and body[0] == 'checkpoint-inventory',
          'native inventory body is malformed')
    sections = {row[0]: row[1:] for row in body[1:]}
    _need(set(sections) == {'root', 'nodes', 'rng', 'readiness'}
          and len(sections['nodes']) == 1, 'native inventory sections are malformed')
    rows = sections['nodes'][0]
    by_ref = {}
    for row in rows:
        _need(type(row) is tuple and len(row) == 3 and row[0] not in by_ref,
              'native graph has a malformed or duplicate node')
        by_ref[row[0]] = row
    return compatibility, body, rows, by_ref


def _references(value):
    if type(value) is tuple:
        if len(value) == 2 and value[0] == 'reference':
            yield value[1]
        else:
            for item in value:
                yield from _references(item)
    elif type(value) is dict:
        for item in value.values():
            yield from _references(item)


def split(inventory, *, include_diagnostics=False):
    """Return compact snapshot bytes, ordered segment bytes and metrics."""
    from arena_native_snapshot import _compact_inventory

    compatibility, body, rows, by_ref = _read_rows(inventory)
    history_lists = {}
    for ref, tag, content in rows:
        if tag in ('ordered-map', 'list', 'tuple', 'set', 'frozenset'):
            continue
        for field, value in content:
            if (tag, field) not in _HISTORY_FIELDS:
                continue
            _need(type(value) is tuple and len(value) == 2 and value[0] == 'reference',
                  f'{tag}.{field} must be a native list')
            list_ref = value[1]
            node = by_ref.get(list_ref)
            _need(node is not None and node[1] == 'list',
                  f'{tag}.{field} has no list node')
            owner = history_lists.get(list_ref)
            _need(owner is None, 'history list is aliased by multiple owners')
            history_lists[list_ref] = {'owner': ref, 'tag': tag, 'field': field,
                                       'items': node[2]}

    history_refs = set(history_lists)
    snapshot_refs = set()

    def snapshot_value(value):
        for ref in _references(value):
            snapshot_node(ref)

    def snapshot_node(ref):
        if ref in snapshot_refs:
            return
        row = by_ref.get(ref)
        _need(row is not None, 'snapshot graph contains a dangling reference')
        snapshot_refs.add(ref)
        if ref in history_refs:
            return
        _ref, tag, content = row
        if tag not in ('ordered-map', 'list', 'tuple', 'set', 'frozenset'):
            for field, value in content:
                if (tag, field) in _HISTORY_FIELDS:
                    refs = tuple(_references(value))
                    _need(len(refs) == 1, 'history field does not reference one list node')
                    snapshot_node(refs[0])
                    continue
                snapshot_value(value)
        else:
            snapshot_value(content)

    for section in body[1:]:
        if section[0] == 'nodes':
            continue
        snapshot_value(section[1:])
    root_section = next(row for row in body[1:] if row[0] == 'root')
    snapshot_value(root_section[1:])
    _need(snapshot_refs, 'resumable snapshot has no root graph')

    count = max((len(value['items']) for value in history_lists.values()), default=0)
    segment_roots = []
    for ordinal in range(count):
        roots = []
        for list_ref in sorted(history_lists, key=repr):
            items = history_lists[list_ref]['items']
            if ordinal < len(items):
                roots.append((list_ref, ordinal, items[ordinal]))
        segment_roots.append(tuple(roots))

    segment_reach = []
    first_owner = {}
    first_owner_field = {}
    list_categories = {list_ref: (value['tag'], value['field'])
                       for list_ref, value in history_lists.items()}
    for ordinal, roots in enumerate(segment_roots):
        reached = set()
        for list_ref, _index, item in roots:
            category = list_categories[list_ref]
            stack = list(_references(item))
            while stack:
                ref = stack.pop()
                if ref in snapshot_refs or ref in reached:
                    continue
                row = by_ref.get(ref)
                _need(row is not None, 'history graph contains a dangling reference')
                reached.add(ref)
                first_owner_field.setdefault(ref, category)
                _ref, tag, content = row
                if tag not in ('ordered-map', 'list', 'tuple', 'set', 'frozenset'):
                    for field, value in content:
                        if (tag, field) in _HISTORY_FIELDS:
                            continue
                        stack.extend(_references(value))
                else:
                    stack.extend(_references(content))
        for ref in reached:
            first_owner.setdefault(ref, ordinal)
        segment_reach.append(reached)

    snapshot_nodes = []
    for row in rows:
        if row[0] not in snapshot_refs:
            continue
        if row[0] in history_refs:
            row = (row[0], row[1], ())
        snapshot_nodes.append(row)
    snapshot_nodes.sort(key=lambda row: _canonical(_json(row[0])))
    snapshot_body = tuple(
        ('nodes', tuple(snapshot_nodes)) if section[0] == 'nodes' else section
        for section in body[1:])
    snapshot_inventory = (compatibility, (body[0], *snapshot_body))
    snapshot_compact = _compact_inventory(snapshot_inventory)
    descriptors = tuple((list_ref, value['owner'], value['tag'], value['field'],
                         len(value['items']))
                        for list_ref, value in sorted(history_lists.items(), key=lambda x: repr(x[0])))
    snapshot = {'schema': SNAPSHOT_SCHEMA, 'compatibility': compatibility,
                'inventory': snapshot_compact,
                'history_fields': descriptors}
    encounter_rows = [row for row in rows if row[1] == 'encounter.Encounter']
    _need(len(encounter_rows) == 1, 'native checkpoint must have one Encounter')
    encounter_fields = dict(encounter_rows[0][2])
    cursor_value = encounter_fields.get('last_processed_boundary')
    history_cursor = (int(cursor_value[1]) if type(cursor_value) is tuple
                      and len(cursor_value) == 2 and cursor_value[0] == 'integer'
                      else 0 if cursor_value == ('null',) else None)
    snapshot_wire = _canonical(_json(snapshot))
    _count(json.loads(snapshot_wire), max_nodes=MAX_SNAPSHOT_NODES)
    segments = []
    all_segment_nodes = 0
    for ordinal, roots in enumerate(segment_roots):
        node_rows = tuple(sorted((row for row in rows
                          if first_owner.get(row[0]) == ordinal),
                          key=lambda row: _canonical(_json(row[0]))))
        all_segment_nodes += len(node_rows)
        segment = {'schema': SCHEMA, 'ordinal': ordinal,
                   'attachments': roots, 'nodes': node_rows}
        wire = _canonical(_json(segment))
        _count(json.loads(wire), max_nodes=MAX_SEGMENT_NODES)
        segments.append(wire)
    aggregate = len(snapshot_wire) + sum(map(len, segments))
    _need(aggregate <= MAX_TOTAL_BYTES,
          'segmented native state exceeds aggregate uncompressed byte limit')
    _need(len(snapshot_nodes) + all_segment_nodes == len(rows),
          'segmented graph accounting is inconsistent')
    metrics = {'snapshot_bytes': len(snapshot_wire),
        'snapshot_nodes': _count(json.loads(snapshot_wire), max_nodes=MAX_SNAPSHOT_NODES),
        'snapshot_depth': _max_depth(json.loads(snapshot_wire)),
        'history_segment_count': len(segments),
        'history_bytes': sum(map(len, segments)),
        'history_owned_nodes': all_segment_nodes,
        'history_wire_nodes': sum(_count(json.loads(row), max_nodes=MAX_SEGMENT_NODES)
                                  for row in segments),
        'history_max_depth': max((_max_depth(json.loads(row)) for row in segments),
                                 default=0),
        'aggregate_bytes': aggregate, 'total_inventory_nodes': len(rows),
        'history_field_entries': {f'{tag}.{field}': sum(len(value['items'])
            for value in history_lists.values()
            if (value['tag'], value['field']) == (tag, field))
            for tag, field in sorted(set(list_categories.values()))},
        'history_category_owned_nodes': {f'{tag}.{field}': sum(owner == (tag,field)
            for owner in first_owner_field.values())
            for tag, field in sorted(set(list_categories.values()))},
        'history_cursor': history_cursor}
    if include_diagnostics:
        # Diagnostic-only attribution of native graph rows to the first
        # history field that owns them. This is intentionally excluded from
        # production Save so normal exports do not pay for report metrics.
        category_rows = {}
        category_bytes = {}
        for row in rows:
            category = first_owner_field.get(row[0])
            if category is None:
                continue
            name = f'{category[0]}.{category[1]}'
            category_rows[name] = category_rows.get(name, 0) + 1
            category_bytes[name] = category_bytes.get(name, 0) + len(_canonical(_json(row)))
        metrics['history_category_owned_rows'] = category_rows
        metrics['history_category_owned_row_bytes'] = category_bytes
    return snapshot_wire, tuple(segments), metrics


def reassemble(snapshot_wire, segment_wires):
    """Validate independently bounded documents, then restore exact inventory."""
    try:
        snapshot_data = json.loads(snapshot_wire.decode('ascii'))
    except (AttributeError, UnicodeError, ValueError, RecursionError) as exc:
        raise ArenaHistorySegmentsRejected('resumable snapshot is invalid JSON') from exc
    _need(_canonical(snapshot_data) == snapshot_wire,
          'resumable snapshot is not canonical')
    _count(snapshot_data, max_nodes=MAX_SNAPSHOT_NODES)
    _need(type(snapshot_data) is dict and set(snapshot_data) ==
          {'schema', 'compatibility', 'inventory', 'history_fields'}
          and snapshot_data['schema'] == SNAPSHOT_SCHEMA,
          'resumable snapshot schema or fields are invalid')
    compact = _tuples(snapshot_data['inventory'])
    expected_compatibility = _tuples(snapshot_data['compatibility'])
    history_fields = _tuples(snapshot_data['history_fields'])
    _need(type(history_fields) is tuple and len(set(row[0] for row in history_fields)) == len(history_fields),
          'snapshot history field catalog is malformed')
    from arena_native_snapshot import _expand_compact_inventory
    compact = _expand_compact_inventory(compact)
    compatibility, body = compact
    _need(compatibility == expected_compatibility,
          'snapshot compatibility disagrees with its inventory')
    sections = {row[0]: row[1:] for row in body[1:]}
    _need(set(sections) == {'root', 'nodes', 'rng', 'readiness'}
          and len(sections['nodes']) == 1, 'snapshot inventory sections are malformed')
    snapshot_rows = sections['nodes'][0]
    by_ref = {}
    for row in snapshot_rows:
        _need(type(row) is tuple and len(row) == 3 and row[0] not in by_ref,
              'snapshot graph has duplicate or malformed nodes')
        by_ref[row[0]] = row
    expected_attachments = {}
    for row in history_fields:
        _need(type(row) is tuple and len(row) == 5
              and row[2:4] in _HISTORY_FIELDS and type(row[4]) is int and row[4] >= 0,
              'snapshot history field descriptor is invalid')
        list_ref, owner_ref, tag, field, length = row
        node = by_ref.get(list_ref)
        owner = by_ref.get(owner_ref)
        _need(node is not None and node[1] == 'list' and node[2] == ()
              and owner is not None and owner[1] == tag,
              'snapshot history field is not an empty list on its declared owner')
        expected_attachments[list_ref] = {'owner': owner_ref, 'tag': tag,
            'field': field, 'length': length, 'items': {}}
        owner_fields = owner[2]
        pairs = dict(owner_fields)
        _need(pairs.get(field) == ('reference', list_ref),
              'snapshot history field does not reference its declared list')

    node_owners = {}
    aggregate_bytes = len(snapshot_wire)
    total_nodes = _count(json.loads(snapshot_wire), max_nodes=MAX_SNAPSHOT_NODES)
    for expected_ordinal, wire in enumerate(segment_wires):
        aggregate_bytes += len(wire)
        _need(aggregate_bytes <= MAX_TOTAL_BYTES,
              'segmented native state exceeds aggregate uncompressed byte limit')
        try:
            data = json.loads(wire.decode('ascii'))
        except (UnicodeError, ValueError, RecursionError) as exc:
            raise ArenaHistorySegmentsRejected('history segment is invalid JSON') from exc
        _need(_canonical(data) == wire, 'history segment is not canonical')
        total_nodes += _count(data, max_nodes=MAX_SEGMENT_NODES)
        _need(total_nodes <= MAX_TOTAL_NODES,
              'segmented native state exceeds aggregate structural limit')
        _need(type(data) is dict and set(data) ==
              {'schema', 'ordinal', 'attachments', 'nodes'}
              and data['schema'] == SCHEMA and data['ordinal'] == expected_ordinal,
              'history segment schema/order is invalid')
        _need(type(data['attachments']) is list and type(data['nodes']) is list,
              'history segment content is malformed')
        for attachment in data['attachments']:
            _need(type(attachment) is list and len(attachment) == 3,
                  'history attachment is malformed')
            list_ref, index, item = _tuples(attachment)
            state = expected_attachments.get(list_ref)
            _need(state is not None and type(index) is int and index >= 0
                  and index < state['length'] and index not in state['items'],
                  'history attachment is unknown, duplicate or out of range')
            state['items'][index] = item
        for row in data['nodes']:
            row = _tuples(row)
            _need(type(row) is tuple and len(row) == 3
                  and row[0] not in by_ref and row[0] not in node_owners,
                  'history graph contains duplicate node identity')
            node_owners[row[0]] = expected_ordinal
            by_ref[row[0]] = row

    for list_ref, state in expected_attachments.items():
        _need(set(state['items']) == set(range(state['length'])),
              'history segment sequence has a missing attachment')
        row = by_ref[list_ref]
        by_ref[list_ref] = (row[0], row[1], tuple(state['items'][i]
                                                  for i in range(state['length'])))
    rows = tuple(by_ref[row[0]] for row in snapshot_rows) + tuple(
        by_ref[ref] for ref in node_owners)
    rebuilt_body = tuple(('nodes', rows) if section[0] == 'nodes' else section
                         for section in body[1:])
    result = (compatibility, (body[0], *rebuilt_body))
    from arena_native_snapshot import _validate_inventory
    _validate_inventory(result)
    return result
