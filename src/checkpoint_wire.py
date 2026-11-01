"""Strict deterministic byte codec for detached 5D2C4 Run/Spot envelopes.

The decoder is deliberately independent of Universe/Encounter objects and of
the process-local candidate/receipt registries. A decoded value is a data DTO,
never an authenticated checkpoint or authorization to restore.
"""
from dataclasses import dataclass
import hashlib
import json
import math


WIRE_SCHEMA = 'universe.native-run-spot-checkpoint-wire/1'
_MAX_BYTES = 32 * 1024 * 1024
_MAX_DEPTH = 128
_MAX_NODES = 1_000_000
_MAX_STRING = 1_000_000
_MAX_INTEGER_DIGITS = 4096


class WireRejected(ValueError):
    """Wire data is invalid, incompatible, or outside the resource limits."""


@dataclass(frozen=True)
class DecodedRunSpotWire:
    """Unissued data-only DTO returned by the strict wire decoder."""
    schema: str
    envelope_data: tuple
    wire_digest: str

    def to_data(self):
        return self.envelope_data


def _need(condition, message):
    if not condition:
        raise WireRejected(message)


def _convert(value, *, depth=0, count=None):
    if count is None:
        count = [0]
    count[0] += 1
    _need(count[0] <= _MAX_NODES and depth <= _MAX_DEPTH,
          'wire nesting or node-count limit exceeded')
    kind = type(value)
    if value is None or kind in (bool, int):
        if kind is int:
            _need(value.bit_length() <= _MAX_INTEGER_DIGITS * 4,
                  'wire integer exceeds configured digit limit')
        return value
    if kind is str:
        _need(len(value) <= _MAX_STRING, 'wire string exceeds configured length limit')
        return value
    if kind in (list, tuple):
        return tuple(_convert(item, depth=depth+1, count=count) for item in value)
    raise WireRejected('wire contains an unsupported JSON/native value')


def _wire_value(value):
    """Convert canonical detached tuples to JSON arrays without coercion."""
    kind = type(value)
    if value is None or kind in (str, int, bool):
        return value
    if kind is tuple:
        return [_wire_value(item) for item in value]
    raise WireRejected('detached envelope contains a non-data value')


def _canonical_json(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('ascii')


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _parse_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise WireRejected('duplicate JSON object key')
        result[key] = value
    return result


def _parse_int(text):
    if len(text.lstrip('-')) > _MAX_INTEGER_DIGITS:
        raise WireRejected('wire integer exceeds configured digit limit')
    return int(text)


def _reject_number(_):
    raise WireRejected('untagged JSON floating-point values are forbidden')


def _tree(value, *, depth=0, count=None):
    if count is None:
        count = [0]
    count[0] += 1
    _need(count[0] <= _MAX_NODES and depth <= _MAX_DEPTH,
          'envelope nesting or node-count limit exceeded')
    kind = type(value)
    if value is None or kind in (str, bool, int):
        if kind is str:
            _need(len(value) <= _MAX_STRING, 'envelope string exceeds configured length limit')
        return
    _need(kind is tuple, 'envelope contains a non-data type')
    for item in value:
        _tree(item, depth=depth+1, count=count)


def _canonical_number(value):
    if type(value) is not tuple or not value:
        return
    if value[0] == 'integer':
        _need(len(value) == 2 and type(value[1]) is str,
              'malformed tagged integer')
        try:
            parsed = int(value[1])
        except ValueError as exc:
            raise WireRejected('malformed tagged integer') from exc
        _need(str(parsed) == value[1], 'noncanonical tagged integer')
    elif value[0] == 'binary64':
        _need(len(value) == 2 and type(value[1]) is str,
              'malformed tagged binary64 value')
        try:
            parsed = float.fromhex(value[1])
        except ValueError as exc:
            raise WireRejected('malformed tagged binary64 value') from exc
        _need(math.isfinite(parsed) and parsed.hex() == value[1],
              'noncanonical or nonfinite tagged binary64 value')


def _walk_tags(value):
    if type(value) is tuple:
        _canonical_number(value)
        if value and value[0] == 'mapping':
            _need(len(value) == 2 and type(value[1]) is tuple,
                  'malformed tagged mapping')
            keys = tuple(row[0] for row in value[1]
                         if type(row) is tuple and len(row) == 2)
            _need(len(keys) == len(value[1]) and keys == tuple(sorted(set(keys))),
                  'duplicate or noncanonical tagged mapping keys')
        if value and value[0] == 'set':
            _need(len(value) == 2 and type(value[1]) is tuple
                  and value[1] == tuple(sorted(set(value[1]), key=_canonical_json)),
                  'duplicate or noncanonical tagged set values')
        yield value
        for item in value:
            yield from _walk_tags(item)


def _validate_inventory(state):
    from checkpoint_fields import FIELD_ADAPTERS

    _need(type(state) is tuple and len(state) >= 2
          and state[0] == 'checkpoint-inventory', 'unknown authoritative inventory schema')
    rows = state[1:]
    _need(all(type(row) is tuple and len(row) >= 2 and type(row[0]) is str for row in rows),
          'malformed authoritative inventory section')
    tags = tuple(row[0] for row in rows)
    _need(len(tags) == len(set(tags)), 'duplicate inventory section')
    sections = {row[0]: row[1:] for row in rows}
    _need(sections.get('readiness') == (False, False, False),
          'wire envelope cannot assert global checkpoint readiness')
    _need(sections.get('host-bindings') == ((),),
          'external recipient bindings are outside the Run/Spot wire schema')
    _need(sections.get('native-adapters') == ('native-closure-recipes/1',),
          'unknown native adapter version')
    _need(sections.get('rng') and len(sections['rng']) == 3
          and sections['rng'][0] == 'caller_cursor'
          and sections['rng'][1] == 'exclusive_encounter',
          'private RNG ownership is absent or incompatible')
    nodes_section = sections.get('nodes')
    _need(type(nodes_section) is tuple and len(nodes_section) == 1
          and type(nodes_section[0]) is tuple, 'authoritative node table is missing')
    nodes = nodes_section[0]
    references = set()
    node_by_ref = {}
    collection_tags = {'ordered-map', 'list', 'tuple', 'set', 'frozenset'}
    for node in nodes:
        _need(type(node) is tuple and len(node) == 3
              and type(node[0]) is tuple and type(node[1]) is str
              and type(node[2]) is tuple, 'malformed inventory node')
        ref, tag, content = node
        _need(ref not in references, 'duplicate inventory alias/reference identity')
        references.add(ref)
        node_by_ref[ref] = node
        if tag in collection_tags:
            if tag == 'ordered-map':
                _need(all(type(row) is tuple and len(row) == 2 for row in content),
                      'malformed ordered-map entries')
                keys = tuple(row[0] for row in content)
                _need(len(keys) == len(set(keys)), 'duplicate logical key in ordered map')
        else:
            adapter = FIELD_ADAPTERS.get(tag)
            _need(adapter is not None, 'unknown native inventory type tag: ' + tag)
            _need(all(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                      for row in content), 'malformed native field record')
            names = tuple(row[0] for row in content)
            _need(len(names) == len(set(names)), 'duplicate native field name')
            _need(set(names) <= set(adapter['allowed']),
                  'unknown native field in wire inventory: ' + tag)
            _need(set(adapter['required']) <= set(names),
                  'required native field is missing: ' + tag)
            _need(not any(row[1] == ('unsupported', ()) for row in content),
                  'unsupported native value in inventory')
    refs_in_data = []
    for tag in _walk_tags(nodes):
        if len(tag) == 2 and tag[0] == 'reference':
            refs_in_data.append(tag[1])
    _need(all(ref in node_by_ref for ref in refs_in_data),
          'dangling logical/alias reference in inventory')
    root = sections.get('root')
    _need(type(root) is tuple and len(root) == 1 and type(root[0]) is tuple
          and len(root[0]) == 2 and root[0][0] == 'reference'
          and root[0][1] in node_by_ref,
          'Universe root reference is absent from the node table')
    return sections, node_by_ref


_CHOICE_FIELDS = (
    'id', 'universe', 'event_type', 'start_time', 'end_time', 'actor_id',
    'target_id', 'instrument_id', 'parent_event_id', 'encounter', 'reach',
    'kind', 'target_action_id', 'minimum_distance', 'practice_experience',
    'max_distance', 'spotting_conditions', 'declared_roll', 'episode_time', 'topic', 'generate',
    'substituted_claim', 'received_accounts', 'seed', 'random_key', 'observer',
    'interpreter', 'ledger', 'experience_policy', 'focus_category',
    'get_instrument', 'damage_potential', '_status', 'on_schedule',
    'prepare_schedule', 'strategy_effort', 'display_name',
)


def _decoded_numeric(value, label):
    _need(type(value) is tuple and len(value) == 2, label + ' is not numerically tagged')
    if value[0] == 'integer':
        _canonical_number(value)
        return int(value[1])
    _need(value[0] == 'binary64', label + ' has an unsupported numeric tag')
    _canonical_number(value)
    return float.fromhex(value[1])


def _logical_ref(value, role, participants):
    _need(type(value) is tuple and len(value) == 2 and value[0] == role
          and type(value[1]) is str and value[1] in participants,
          'dangling or malformed logical ' + role + ' reference')
    return value[1]


def _validate_choice(choice, universe_id, participants, all_action_ids):
    _need(type(choice) is tuple and len(choice) == 9
          and choice[0] == 'universe.accepted-action-choice/1',
          'unknown accepted-choice schema or field layout')
    choice_id, version, state, origin, action_ids, first_start, members, reservations = choice[1:]
    _need(type(choice_id) is str and choice_id and type(version) is int and version > 0
          and state == 'accepted' and type(origin) is str,
          'invalid accepted-choice identity, version, state, or origin')
    _need(type(action_ids) is tuple and action_ids
          and len(action_ids) == len(set(action_ids))
          and not set(action_ids).intersection(all_action_ids),
          'duplicate or committed Action ID in accepted future choice')
    _decoded_numeric(first_start, 'accepted choice start')
    _need(type(members) is tuple and members, 'accepted choice has no members')
    _need(reservations == (), 'Run/Spot choice has unsupported active Object reservations')
    member_ids = []
    starts = []
    for member in members:
        _need(type(member) is tuple and len(member) == 6,
              'malformed accepted-choice member')
        _key, adapter, action_id, fields, target_key, prepared = member
        _need(type(adapter) is str and adapter in
              ('native.run-action/1', 'native.spot-action/1')
              and type(action_id) is str and action_id
              and target_key is None,
              'unsupported Action family or dependency in accepted choice')
        _need(action_id not in all_action_ids, 'Action occurs in multiple choice/receipt records')
        _need(type(fields) is tuple and tuple(row[0] for row in fields) == _CHOICE_FIELDS
              and all(type(row) is tuple and len(row) == 2 for row in fields),
              'native declaration fields are missing, reordered, or unknown')
        f = dict(fields)
        _need(f['id'] == ('action-id', action_id), 'Action logical ID disagrees with declaration')
        _need(f['universe'] == ('universe', universe_id),
              'Action declaration has an inconsistent Universe reference')
        expected_event = 'run' if adapter == 'native.run-action/1' else 'spot'
        _need(f['event_type'] == ('string', expected_event),
              'Action family and event type disagree')
        actor = _logical_ref(f['actor_id'], 'entity', participants)
        target_data = f['target_id']
        if adapter == 'native.spot-action/1':
            _logical_ref(target_data, 'entity', participants)
        else:
            _need(target_data == ('null',), 'Run Action has unsupported Target reference')
        start = _decoded_numeric(f['start_time'], 'Action start')
        end = _decoded_numeric(f['end_time'], 'Action end')
        _need(start <= end, 'Action interval is reversed')
        _need(type(prepared) is tuple and len(prepared) == 9
              and prepared[0] == action_id,
              'prepared schedule does not identify its Action')
        _need(_decoded_numeric(prepared[1], 'prepared start') == start
              and _decoded_numeric(prepared[2], 'prepared end') == end
              and prepared[3] == ('entity', actor)
              and prepared[4] == target_data
              and prepared[5] == ('null',) and prepared[6] == ('null',)
              and prepared[7] == (),
              'prepared schedule references disagree with Action declaration')
        init = prepared[8]
        _need(type(init) is tuple, 'prepared initialization is malformed')
        _need(all(type(row) is tuple and len(row) == 2 for row in init),
              'prepared initialization entry is malformed')
        for key, value in init:
            _need(type(value) is tuple and value and
                  ((adapter == 'native.spot-action/1' and key == '_encounter'
                    and value[0] == 'encounter') or
                   (adapter == 'native.run-action/1' and key == 'start_position'
                    and value[0] == 'cartesian-position')),
                  'prepared initialization contains an unsupported field')
        member_ids.append(action_id)
        starts.append(start)
    _need(tuple(member_ids) == action_ids, 'accepted Action ID order disagrees with members')
    _need(_decoded_numeric(first_start, 'choice first start') == min(starts),
          'accepted choice first-start fence disagrees with member timing')
    return set(member_ids)


def _validate_receipt_chain(chain, universe_id, encounter_id, participants,
                            expected_choices, boundaries):
    _need(type(chain) is tuple and len(chain) == 8
          and chain[0] == 'universe.committed-native-receipt-chain/1'
          and chain[1:3] == (universe_id, encounter_id),
          'receipt chain schema or roots are incompatible')
    _need(chain[7] == ('caller-cursor', 'exclusive_encounter-asserted'),
          'receipt RNG ownership is incompatible')
    rows = chain[4]
    _need(type(rows) is tuple and len(rows) == len(boundaries)
          and len(rows) in (1, 2), 'receipt boundary rows are incomplete')
    actions_by_id = {}
    all_effects = set()
    lifecycle_choices = {}
    for index, row in enumerate(rows):
        _need(type(row) is tuple and len(row) == 9 and row[0] == boundaries[index],
              'malformed or unordered receipt boundary')
        action_ids, effect_ids = row[2], row[3]
        actions, effects, targets = row[4], row[5], row[6]
        _need(type(action_ids) is tuple and type(actions) is tuple
              and tuple(action[0] for action in actions) == action_ids
              and len(set(action_ids)) == len(action_ids),
              'receipt Action identity/order coverage is inconsistent')
        for action in actions:
            _need(type(action) is tuple and len(action) == 10
                  and action[1] in ('native.run-action/1', 'native.spot-action/1'),
                  'unsupported or malformed committed Action record')
            aid, _adapter, actor, target = action[:4]
            _need(type(aid) is str and aid and aid not in actions_by_id,
                  'duplicate committed Action ID')
            _logical_ref(('entity', actor), 'entity', participants)
            if target is not None:
                _logical_ref(('entity', target), 'entity', participants)
            declaration = action[6]
            _need(type(declaration) is tuple and tuple(row[0] for row in declaration) ==
                  ('event_type', 'strategy', 'parameters', 'display_name', 'parent_encounter_id'),
                  'committed Action declaration fields are unknown or incomplete')
            declaration_map = dict(declaration)
            event_type = 'run' if action[1] == 'native.run-action/1' else 'spot'
            _need(declaration_map['event_type'] == event_type
                  and declaration_map['parent_encounter_id'] == encounter_id,
                  'committed Action declaration has inconsistent roots or family')
            metadata = action[8]
            _need(type(metadata) is tuple and len(metadata) == 2
                  and metadata[0] == 'sequence', 'committed Action metadata is malformed')
            metadata_keys = tuple(row[1][0][1] for row in metadata[1]
                                  if type(row) is tuple and len(row) == 2
                                  and type(row[1]) is tuple and len(row[1]) == 2
                                  and type(row[1][0]) is tuple and len(row[1][0]) == 2
                                  and row[1][0][0] == 'string')
            _need(not set(metadata_keys).intersection(
                      ('hp_before', 'hp_after', 'resulting_hp')),
                  'Action contains Target-owned resulting HP')
            _decoded_numeric(action[4], 'committed Action start')
            _decoded_numeric(action[5], 'committed Action end')
            actions_by_id[aid] = action
        _need(type(effect_ids) is tuple and type(effects) is tuple
              and tuple(item[0] for item in effects) == effect_ids
              and len(set(effect_ids)) == len(effect_ids),
              'receipt effect identity/order coverage is inconsistent')
        for effect_id, payload in effects:
            _need(type(effect_id) is tuple and len(effect_id) == 6
                  and effect_id[0] == 'effect-id'
                  and effect_id[1] == encounter_id and effect_id[2] == row[0]
                  and effect_id[3] in actions_by_id,
                  'effect has a dangling Encounter, boundary, or Action reference')
            _need(effect_id not in all_effects, 'duplicate logical effect identity')
            all_effects.add(effect_id)
            _need(type(payload) is tuple and len(payload) == 2
                  and payload[0] in ('effect.awareness/1', 'effect.practice/1',
                                     'effect.action-outcome/1', 'effect.lifecycle/1')
                  and type(payload[1]) is tuple,
                  'effect payload is malformed')
            payload_fields = payload[1]
            _need(all(type(pair) is tuple and len(pair) == 2 and type(pair[0]) is str
                      for pair in payload_fields), 'effect payload fields are malformed')
            names = tuple(pair[0] for pair in payload_fields)
            _need(len(names) == len(set(names)), 'duplicate effect payload field')
            values = dict(payload_fields)
            if payload[0] in ('effect.awareness/1', 'effect.practice/1'):
                source = values.get('source_action_id')
                _need(source == ('string', effect_id[3]) and effect_id[4] == 'effect',
                      'causal effect source/identity link is inconsistent')
                expected_fields = (('source_action_id', 'target_id', 'observed_id',
                                    'distance', 'max_distance', 'basis')
                                   if payload[0] == 'effect.awareness/1' else
                                   ('source_action_id', 'target_id', 'skill', 'experience'))
                _need(names == expected_fields, 'effect payload fields are unknown or incomplete')
                for ref_field in ('target_id', 'observed_id'):
                    if ref_field in values:
                        _logical_ref(values[ref_field], 'string', participants)
                if payload[0] == 'effect.awareness/1':
                    _logical_ref(values['observed_id'], 'string', participants)
                else:
                    _decoded_numeric(values['experience'], 'practice experience')
            else:
                _need(values.get('action_id') == ('string', effect_id[3])
                      and effect_id[4] == 'lifecycle',
                      'Action lifecycle effect source/identity link is inconsistent')
                expected_fields = (('source_action_id', 'action_id', 'outcome')
                                   if payload[0] == 'effect.action-outcome/1' else
                                   ('source_action_id', 'action_id', 'status', 'from_queue',
                                    'to_queue', 'choice_id', 'previous_choice_action_state',
                                    'nominal_end', 'boundary', 'canceled_at',
                                    'cancellation_reason'))
                _need(names == expected_fields, 'lifecycle payload fields are unknown or incomplete')
                action = actions_by_id[effect_id[3]]
                if payload[0] == 'effect.action-outcome/1':
                    _need(values['outcome'] == ('string', action[7]),
                          'Action outcome effect disagrees with its Action record')
                else:
                    _need(values['status'] == ('string', 'finished')
                          and _decoded_numeric(values['boundary'], 'lifecycle boundary') == row[0]
                          and values['nominal_end'] == action[5],
                          'Action lifecycle timing/status disagrees with its receipt')
                    lifecycle_choices[effect_id[3]] = values['choice_id']
        targets_seen = set()
        for target in targets:
            _need(type(target) is tuple and len(target) == 4
                  and type(target[0]) is str and target[1] == 'being'
                  and target[0] in participants and target[0] not in targets_seen,
                  'Target-owned receipt record has a dangling or duplicate Target ID')
            target_state = target[3]
            target_tag = 'target.candidate/1'
            _need(type(target_state) is tuple and len(target_state) == 2
                  and target_state[0] == target_tag and type(target_state[1]) is tuple,
                  'Target-owned state has an unknown schema')
            target_fields = target_state[1]
            target_names = tuple(pair[0] for pair in target_fields
                                 if type(pair) is tuple and len(pair) == 2)
            expected_target_fields = ('target_id', 'category', 'starting_hp',
                'projected_hp', 'actual_damage', 'fatal_effect_ids', 'incoming',
                'outgoing_effect_ids', 'aware_of', 'practice_state', 'observer_state')
            _need(target_names == expected_target_fields
                  and ('target_id', ('string', target[0])) in target_fields
                  and ('category', ('string', 'being')) in target_fields,
                  'Target state fields, identity, or category are inconsistent')
            targets_seen.add(target[0])
        expected_action_effects = {
            aid: tuple(effect_id for effect_id in effect_ids if effect_id[3] == aid)
            for aid in action_ids
        }
        for action in actions:
            _need(action[9] == expected_action_effects[action[0]],
                  'Action causal effect references are incomplete or mislinked')
    committed_choices = chain[5]
    _need(type(committed_choices) is tuple, 'committed Choice membership is malformed')
    covered = []
    choice_ids = set()
    action_choice = {}
    for choice in committed_choices:
        _need(type(choice) is tuple and len(choice) == 4
              and type(choice[0]) is str and choice[0] not in choice_ids
              and type(choice[1]) is int and choice[1] > 0
              and type(choice[3]) is tuple,
              'committed Choice identity or membership is invalid')
        choice_ids.add(choice[0])
        covered.extend(choice[3])
        for action_id in choice[3]:
            _need(action_id not in action_choice, 'Action belongs to multiple committed choices')
            action_choice[action_id] = choice[0]
    _need(set(covered) == set(actions_by_id) and len(covered) == len(actions_by_id),
          'committed Choice membership does not cover receipt Actions exactly')
    _need(lifecycle_choices == {aid: ('string', cid) for aid, cid in action_choice.items()},
          'Action lifecycle Choice references disagree with committed Choice membership')
    _need(chain[6] == expected_choices, 'receipt accepted-choice set disagrees with envelope')
    return set(actions_by_id)


def _validate_descriptor_components(data):
    _need(type(data) is tuple and len(data) == 17,
          'unknown or incomplete native envelope fields')
    (schema, universe_id, encounter_id, compatibility, boundaries, state,
     certificate, choices, receipts, rng, diagnostics, obligations,
     bounded, closure, portable, restored, digest) = data
    _need(schema == 'universe.native-run-spot-checkpoint-envelope/1',
          'unknown native envelope schema version')
    _need(type(universe_id) is str and universe_id and type(encounter_id) is str and encounter_id,
          'logical root IDs are invalid')
    _need(type(compatibility) is tuple and type(boundaries) is tuple
          and type(choices) is tuple and type(receipts) is tuple
          and type(diagnostics) is tuple and type(obligations) is tuple,
          'envelope section has an invalid container type')
    _validate_compatibility(compatibility)
    _need(bounded is True and closure is False and portable is False and restored is False,
          'envelope status conflicts with inactive readiness policy')
    _need(type(digest) is str and len(digest) == 64
          and all(c in '0123456789abcdef' for c in digest),
          'malformed envelope content digest')
    _need(digest == _sha(_canonical_json(list(data[:-1]))),
          'envelope content digest mismatch')
    sections, node_by_ref = _validate_inventory(state)
    _need(type(certificate) is tuple and certificate
          and certificate[0] == 'native.run-spot-field-closure/1',
          'unknown Run/Spot field-closure schema')
    cert_rows = certificate[1:]
    _need(all(type(row) is tuple and len(row) == 2 and type(row[0]) is str for row in cert_rows),
          'malformed field-closure certificate')
    cert = dict(cert_rows)
    _need(len(cert) == len(cert_rows)
          and tuple(sorted(cert)) == tuple(sorted(('participants', 'being-definitions',
              'required-practice-skills', 'participant-state', 'receipt-descriptors',
              'accepted-choice-descriptors', 'field-policy', 'ownership-policy'))),
          'field-closure certificate fields are incomplete or unknown')
    state_certificate = sections.get('bounded-run-spot-closure')
    _need(state_certificate == (certificate,),
          'envelope field closure does not match authoritative state')
    _need(choices == cert['accepted-choice-descriptors'],
          'accepted choices are missing or inconsistent')
    participant_ids = cert['participants']
    _need(type(participant_ids) is tuple,
          'participant logical IDs are malformed')
    _need(participant_ids == tuple(sorted(set(participant_ids)))
          and all(type(item) is str and item for item in participant_ids),
          'duplicate or noncanonical participant logical IDs')
    receipt_rows = cert['receipt-descriptors']
    _need(type(receipt_rows) is tuple and len(receipt_rows) <= 1,
          'receipt descriptor multiplicity is invalid')
    expected_receipts = receipt_rows[0] if receipt_rows else ()
    _need(receipts == expected_receipts,
          'committed receipts are missing or inconsistent')
    _need(sections.get('rng') == rng,
          'private RNG state is missing or inconsistent')
    _need(sections.get('host-bindings') == ((),),
          'wire schema does not support external recipient bindings')
    _need(type(rng) is tuple and len(rng) == 3
          and rng[:2] == ('caller_cursor', 'exclusive_encounter'),
          'wire private RNG state has an unsupported owner')
    _need(type(boundaries) is tuple and len(boundaries) <= 2
          and all(type(x) is int and x > 0 for x in boundaries),
          'committed boundary sequence is outside the bounded subset')
    if receipts:
        rows = receipts[4] if type(receipts) is tuple and len(receipts) == 8 else ()
        _need(type(rows) is tuple and len(rows) == len(boundaries)
              and tuple(row[0] for row in rows) == boundaries,
              'receipt rows do not match committed boundary sequence')
        committed_action_ids = _validate_receipt_chain(
            receipts, universe_id, encounter_id, set(participant_ids), choices, boundaries)
    else:
        _need(boundaries == (), 'boundary sequence has no committed receipts')
        committed_action_ids = set()
    future_action_ids = set()
    for choice in choices:
        future_action_ids.update(_validate_choice(
            choice, universe_id, set(participant_ids), committed_action_ids | future_action_ids))
    # Ensure the roots named at the envelope top are the unique inventory roots.
    universe_nodes = tuple(node for node in node_by_ref.values()
                           if node[1] == 'universe.Universe')
    encounter_nodes = tuple(node for node in node_by_ref.values()
                            if node[1] == 'encounter.Encounter')
    _need(len(universe_nodes) == 1 and universe_nodes[0][0] == ('universe', universe_id),
          'Universe logical ID does not match its authoritative node')
    _need(len(encounter_nodes) == 1 and encounter_nodes[0][0] == ('encounter', encounter_id),
          'Encounter logical ID does not match its authoritative node')
    # Verify exact tagged number syntax throughout all component and inventory data.
    for value in _walk_tags((compatibility, boundaries, state, certificate,
                             choices, receipts, rng, diagnostics, obligations)):
        _canonical_number(value)
    return True


def _validate_compatibility(value):
    _need(type(value) is tuple and len(value) == 9
          and value[0:2] == ('compatibility-draft', 'universe.checkpoint-inventory-draft/1'),
          'compatibility fingerprint schema is unknown')
    for row, tag in ((value[2], 'implementation-source'),
                     (value[3], 'rule-kernel-source'),
                     (value[4], 'authoritative-decisions')):
        _need(type(row) is tuple and len(row) == 2 and row[0] == tag
              and type(row[1]) is str and len(row[1]) == 64
              and all(char in '0123456789abcdef' for char in row[1]),
              'compatibility fingerprint component is malformed: ' + tag)
    runtime = value[5]
    _need(type(runtime) is tuple and len(runtime) == 3
          and runtime[0] == 'python-runtime' and type(runtime[1]) is str
          and type(runtime[2]) is tuple and len(runtime[2]) == 5
          and all(type(part) in (str, int) for part in runtime[2]),
          'Python runtime compatibility component is malformed')
    _need(value[6] == ('numeric', 'IEEE754-binary64-hex')
          and value[7] == ('python-native-rng', 'MT19937-state-v3')
          and value[8] == ('restore-adapters', 'not-implemented'),
          'numeric, RNG, or restore compatibility rule is unknown')


def _wire_bytes(envelope_data):
    _validate_descriptor_components(envelope_data)
    payload = _wire_value(envelope_data)
    body = {'schema': WIRE_SCHEMA, 'envelope': payload,
            'sha256': _sha(_canonical_json(payload))}
    raw = _canonical_json(body)
    _need(len(raw) <= _MAX_BYTES, 'encoded checkpoint exceeds size limit')
    return raw


def encode_detached_run_spot_data(envelope_data):
    """Encode a detached, already assembled envelope data tuple canonically."""
    _tree(envelope_data)
    return _wire_bytes(envelope_data)


def encode_run_spot_envelope(envelope):
    """Encode an exact 5D2C4 envelope; never reads its source Universe."""
    from checkpoint_envelope import NativeRunSpotCheckpointEnvelope, _validate_shape
    _need(type(envelope) is NativeRunSpotCheckpointEnvelope,
          'exact native Run/Spot envelope required')
    _validate_shape(envelope)
    return encode_detached_run_spot_data(envelope.to_data())


def decode_run_spot_wire(raw):
    """Strictly decode canonical bytes into an unissued, detached data DTO."""
    _need(type(raw) is bytes, 'wire input must be exact bytes')
    _need(0 < len(raw) <= _MAX_BYTES, 'wire byte length is empty or exceeds limit')
    try:
        parsed = json.loads(raw.decode('utf-8'), object_pairs_hook=_parse_pairs,
                            parse_int=_parse_int, parse_float=_reject_number,
                            parse_constant=_reject_number)
    except WireRejected:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise WireRejected('invalid UTF-8 JSON wire data') from exc
    _need(type(parsed) is dict and set(parsed) == {'schema', 'envelope', 'sha256'},
          'unknown or missing wire envelope fields')
    _need(parsed['schema'] == WIRE_SCHEMA, 'unknown wire schema version')
    _need(type(parsed['sha256']) is str and len(parsed['sha256']) == 64
          and all(c in '0123456789abcdef' for c in parsed['sha256']),
          'malformed wire digest')
    payload_value = parsed['envelope']
    _need(type(payload_value) is list, 'wire envelope payload must be an ordered array')
    payload = _convert(payload_value)
    _tree(payload)
    _need(parsed['sha256'] == _sha(_canonical_json(payload_value)),
          'wire payload digest mismatch')
    _validate_descriptor_components(payload)
    canonical = _wire_bytes(payload)
    _need(raw == canonical, 'wire bytes are valid but not in canonical encoding')
    return DecodedRunSpotWire(WIRE_SCHEMA, payload, parsed['sha256'])


def reencode_decoded_run_spot_wire(decoded):
    """Re-encode a decoded DTO; this does not create an issued candidate."""
    _need(type(decoded) is DecodedRunSpotWire and decoded.schema == WIRE_SCHEMA,
          'decoded Run/Spot wire DTO required')
    return encode_detached_run_spot_data(decoded.envelope_data)
