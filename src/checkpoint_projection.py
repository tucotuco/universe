"""Detached value projections of narrowly supported committed checkpoint data.

These records are quarantined descriptions only. They are never inserted into
an Encounter, Action, Target, receipt registry, or checkpoint authority store.
"""
from dataclasses import dataclass

from checkpoint_wire import (DecodedRunSpotWire, WIRE_SCHEMA, WireRejected,
    encode_detached_run_spot_data)


PROJECTION_SCHEMA = 'universe.quarantined-run-boundary-projection/1'
MOVEMENT_PROJECTION_SCHEMA = 'universe.quarantined-movement-boundary-projection/1'


class ProjectionRejected(ValueError):
    """Decoded checkpoint data is outside the closed Spot projection subset."""


def _need(test, message):
    if not test:
        raise ProjectionRejected(message)


def _record(value, tag, fields):
    _need(type(value) is tuple and len(value) == 2 and value[0] == tag
          and type(value[1]) is tuple, f'unknown or malformed {tag} record')
    rows = value[1]
    _need(all(type(row) is tuple and len(row) == 2 and type(row[0]) is str for row in rows)
          and tuple(row[0] for row in rows) == fields,
          f'unknown, missing, or reordered {tag} fields')
    return dict(rows)


def _tag(value, name, tag, *, length=2):
    _need(type(value) is tuple and len(value) == length and value[0] == tag,
          f'{name} has an invalid {tag} value')
    return value


def _string(value, name):
    _tag(value, name, 'string')
    _need(type(value[1]) is str and value[1], f'{name} is not a logical identifier')
    return value[1]


def _number(value, name):
    _need(type(value) is tuple and len(value) == 2 and value[0] in ('integer', 'binary64'),
          f'{name} is not an exact encoded number')
    if value[0] == 'integer':
        _need(type(value[1]) is str and str(int(value[1])) == value[1],
              f'{name} integer is not canonical')
    else:
        import math
        _need(type(value[1]) is str and float.fromhex(value[1]).hex() == value[1]
              and math.isfinite(float.fromhex(value[1])),
              f'{name} binary64 is not canonical')
    return value


@dataclass(frozen=True)
class RunActionProjection:
    action_id: str
    actor_id: str
    start: tuple
    end: tuple
    outcome: str
    declaration: tuple
    metadata: tuple
    effect_ids: tuple

    def to_data(self):
        return (self.action_id, self.actor_id, self.start,
                self.end, self.outcome, self.declaration, self.metadata, self.effect_ids)


# Kept as a source-level name for older adapter imports. The projection now
# accepts RunAction only; it does not preserve the obsolete Spot-XP contract.
SpotActionProjection = RunActionProjection


@dataclass(frozen=True)
class PracticeExerciseProjection:
    effect_id: tuple
    action_id: str
    skill: str
    experience: tuple
    nominal_end: tuple
    resolved_at: tuple
    outcome: str

    def to_data(self):
        return (self.effect_id, self.action_id, self.skill, self.experience,
                self.nominal_end, self.resolved_at, self.outcome)


@dataclass(frozen=True)
class PracticeTransitionProjection:
    target_id: str
    skill: str
    time: tuple
    level_before: tuple
    level_after: tuple
    baseline: tuple
    experience_before: tuple
    experience_after: tuple
    effect_ids: tuple

    def to_data(self):
        return (self.target_id, self.skill, self.time, self.level_before,
                self.level_after, self.baseline, self.experience_before,
                self.experience_after, self.effect_ids)


@dataclass(frozen=True)
class BatchPracticeProjection:
    """Target-owned simultaneous history row corresponding to BatchSkillUse."""
    target_id: str
    skill: str
    experience: tuple
    level_before: tuple
    level_after: tuple
    time: tuple
    exercises: tuple
    outcome: str = 'simultaneous'

    def to_data(self):
        return (self.target_id, self.skill, self.experience, self.level_before,
                self.level_after, self.time,
                tuple(row.to_data() for row in self.exercises), self.outcome)


@dataclass(frozen=True)
class TargetProjection:
    target_id: str
    position: tuple
    starting_hp: tuple
    resulting_hp: tuple
    actual_damage: tuple
    incoming_effect_ids: tuple
    outgoing_effect_ids: tuple
    aware_of: tuple
    practice_exercises: tuple
    practice_transitions: tuple
    batch_practice: tuple
    state_data: tuple

    def to_data(self):
        return (self.target_id, self.position, self.starting_hp, self.resulting_hp,
                self.actual_damage, self.incoming_effect_ids, self.outgoing_effect_ids,
                self.aware_of, tuple(row.to_data() for row in self.practice_exercises),
                tuple(row.to_data() for row in self.practice_transitions),
                tuple(row.to_data() for row in self.batch_practice), self.state_data)


@dataclass(frozen=True)
class EffectProjection:
    identity: tuple
    kind: str
    payload: tuple

    def to_data(self):
        return (self.identity, self.kind, self.payload)


@dataclass(frozen=True)
class QuarantinedRunBoundaryProjection:
    schema: str
    universe_id: str
    encounter_id: str
    boundary: int
    start: tuple
    actions: tuple
    effects: tuple
    targets: tuple
    committed_choices: tuple
    rng_after: tuple
    quarantined: bool = True

    def to_data(self):
        return (self.schema, self.universe_id, self.encounter_id, self.boundary,
                self.start, tuple(row.to_data() for row in self.actions),
                tuple(row.to_data() for row in self.effects),
                tuple(row.to_data() for row in self.targets), self.committed_choices,
                self.rng_after, self.quarantined)


@dataclass(frozen=True)
class QuarantinedMovementBoundaryProjection:
    """Detached identity projection for the authentic initial movement receipt."""
    schema: str
    universe_id: str
    encounter_id: str
    boundary: int
    start: tuple
    participant_ids: tuple
    movement_activation: tuple
    target_records: tuple
    start_fences: tuple
    rng_after: tuple
    committed_choices: tuple
    observer_evidence: tuple
    quarantined: bool = True
    receipt_rows: tuple = ()

    def to_data(self):
        return (self.schema, self.universe_id, self.encounter_id, self.boundary,
                self.start, self.participant_ids, self.movement_activation,
                self.target_records, self.start_fences, self.rng_after, self.committed_choices,
                self.observer_evidence, self.quarantined, self.receipt_rows)


def project_quarantined_movement_boundary(decoded):
    """Validate and project the initial movement record and optional boundary 2.

    This projection carries existing Target-owned records and observer evidence
    by their native logical identities; it does not issue or install history.
    """
    _need(type(decoded) is DecodedRunSpotWire and decoded.schema == WIRE_SCHEMA,
          'strict DecodedRunSpotWire/1 input is required')
    data = decoded.envelope_data
    try:
        encode_detached_run_spot_data(data)
    except (WireRejected, TypeError, ValueError) as exc:
        raise ProjectionRejected(f'invalid detached checkpoint data: {exc}') from exc
    _need(type(data) is tuple and len(data) == 17
          and data[0] == 'universe.native-run-spot-checkpoint-envelope/1',
          'unsupported checkpoint envelope version')
    _need(data[12:16] == (True, False, False, False),
          'movement projection cannot promote checkpoint readiness flags')
    _need(type(data[4]) is tuple and 1 <= len(data[4]) <= 4096
          and data[4] == tuple(range(1, len(data[4]) + 1)) and data[7] == (),
          'movement projection requires a consecutive boundary prefix and no Choices')
    chain = data[8]
    _need(type(chain) is tuple and len(chain) == 8
          and chain[:3] == ('universe.committed-native-receipt-chain/1', data[1], data[2])
          and chain[4] and len(chain[4]) == len(data[4]) and not chain[5],
          'movement projection requires the bounded native movement receipt prefix')
    rows = chain[4]
    row = rows[0]
    _need(type(row) is tuple and len(row) == 7
          and row[0] == 'universe.committed-movement-only-boundary/1'
          and row[1] == 1,
          'receipt is not the authentic initial movement-only boundary')
    _need(row[2] == ('integer', '0') and all(
          type(continuing) is tuple and len(continuing) == 7
          and continuing[0] == 'universe.committed-movement-only-boundary/2'
          and continuing[1] == index + 1
          and continuing[2] == ('integer', str(index))
          and continuing[3] == row[3] and continuing[6] == row[6]
          for index, continuing in enumerate(rows[1:], 1)),
          'continuing movement receipts are not consecutive or participant/RNG-bound')
    _need(row[2] == ('integer', '0') and type(row[3]) is tuple
          and len(row[3]) == 2 and len(set(row[3])) == len(row[3])
          and all(type(value) is str and value for value in row[3]),
          'movement receipt has invalid start or participant identities')
    _need(type(row[4]) is tuple and len(row[4]) == 2
          and tuple(target[0] for target in row[4]) == tuple(sorted(row[3]))
          and all(type(target) is tuple and len(target) == 4
                  and target[1] == 'being' for target in row[4]),
          'movement receipt does not contain one Being Target per participant')
    from checkpoint_reconstruction import _rng_data
    def receipt_rng(value):
        _need(type(value) is tuple and len(value) == 2
              and value[0] == 'sequence' and type(value[1]) is tuple,
              'movement receipt RNG state is not a closed sequence')
        def convert(item):
            if type(item) is tuple and len(item) == 2 and item[0] == 'sequence':
                return ('tuple', tuple(convert(child) for child in item[1]))
            return item
        return ('tuple', tuple(convert(item) for item in value[1]))
    _need(all(item[5] == () for item in rows)
          and chain[7] == ('caller-cursor', 'exclusive_encounter-asserted')
          and data[9][:2] == ('caller_cursor', 'exclusive_encounter')
          and _rng_data(data[9][2]) == _rng_data(receipt_rng(rows[-1][6])),
          'movement receipt fences or committed RNG ownership are inconsistent')
    from checkpoint_reconstruction import _sections
    sections = _sections(data[5])
    nodes = sections.get('nodes')
    _need(type(nodes) is tuple and len(nodes) == 1,
          'native graph nodes are missing')
    from checkpoint_reconstruction import _Graph
    graph = _Graph(nodes[0])
    encounter_ref = ('encounter', data[2])
    _need(encounter_ref in graph.nodes
          and graph.nodes[encounter_ref][0] == 'encounter.Encounter',
          'receipt Encounter identity is absent from native graph')
    encounter_fields = graph.fields(encounter_ref)[1]
    latest_boundary = rows[-1][1]
    _need(graph.data(encounter_fields['time']) == latest_boundary
          and graph.data(encounter_fields['last_processed_boundary']) == latest_boundary
          and graph.data(encounter_fields['start_time']) == 0,
          'native Encounter chronology differs from movement receipt')
    _need(graph.data(encounter_fields['arena_activation_enabled']) is True
          and encounter_fields['arena_activation'] == ('null',)
          and graph.data(encounter_fields['initiated']) is True
          and encounter_fields['initiation'] == ('null',),
          'movement receipt has an unsupported activation phase')
    activation_ref = graph.raw_ref(encounter_fields['arena_movement_activation'])
    activation_fields = graph.fields(activation_ref,
        'encounter.ArenaMovementActivation')[1]
    activation = (graph.data(activation_fields['actor_id']),
        graph.data(activation_fields['movement_decision_id']),
        graph.data(activation_fields['time']),
        graph.data(activation_fields['activation_kind']))
    _need(graph.data(activation_fields['encounter_id']) == data[2]
          and graph.data(activation_fields['time']) == 0
          and graph.data(activation_fields['activation_kind']) == 'first_player_movement'
          and graph.data(activation_fields['actor_id']) in row[3],
          'native movement activation does not match the receipt')
    _need(set(graph.data(encounter_fields['being_list'])) == set(row[3])
          and len(graph.data(encounter_fields['being_list'])) == 2,
          'movement participants differ from native Encounter membership')
    awareness = graph.data(encounter_fields['awareness'])
    _need(type(awareness) is dict and set(awareness) == set(row[3]),
          'native observer awareness does not cover both participants')
    observer_evidence = []
    universe_fields = graph.fields(('universe', data[1]))[1]
    registry_ref = graph.raw_ref(universe_fields['object_registry'])
    registry_fields = graph.fields(registry_ref, 'object.ObjectRegistry')[1]
    registry = graph.raw_mapping(registry_fields['object_instances'])
    _need(set(registry) == set(row[3]),
          'native ObjectRegistry differs from movement participants')
    for observer_id in row[3]:
        being_ref = graph.raw_ref(registry[observer_id])
        being_fields = graph.fields(being_ref, 'being.BeingInstance')[1]
        encoded = being_fields.get('_arena_perception_ledger')
        _need(type(encoded) is tuple and len(encoded) == 2
              and encoded[0] == 'arena-perception-ledger',
              'observer-owned Arena evidence is missing or unsupported')
        observer_evidence.append((observer_id, encoded[1]))
    target_awareness = {}
    for target in rows[-1][4]:
        state = _record(target[3], 'target.candidate/1',
            ('target_id', 'category', 'starting_hp', 'projected_hp', 'actual_damage',
             'fatal_effect_ids', 'incoming', 'outgoing_effect_ids', 'aware_of',
             'practice_state', 'observer_state'))
        _need(_string(state['target_id'], 'Target ID') == target[0]
              and _string(state['category'], 'Target category') == 'being',
              'Target state identity/category differs from portable Target')
        known = _tag(state['aware_of'], 'Target awareness', 'set')
        _need(type(known[1]) is tuple, 'Target awareness set is malformed')
        target_awareness[target[0]] = set(_string(value, 'aware Entity ID')
                                          for value in known[1])
    _need(target_awareness == awareness,
          'observer-owned Target awareness differs from native Encounter state')
    return QuarantinedMovementBoundaryProjection(
        MOVEMENT_PROJECTION_SCHEMA, data[1], data[2], latest_boundary, row[2], row[3],
        activation, rows[-1][4], rows[-1][5], rows[-1][6], chain[5],
        tuple(observer_evidence), True, rows)


def project_quarantined_run_boundary(decoded):
    """Project one validated native Run boundary into detached immutable data.

    This adapter performs no native allocation, callback, Action resolution,
    RNG access, receipt authentication, or authoritative history write.
    """
    _need(type(decoded) is DecodedRunSpotWire and decoded.schema == WIRE_SCHEMA,
          'strict DecodedRunSpotWire/1 input is required')
    data = decoded.envelope_data
    try:
        encode_detached_run_spot_data(data)  # Reapply closed wire/reference validation.
    except (WireRejected, TypeError, ValueError) as exc:
        raise ProjectionRejected(f'invalid detached checkpoint data: {exc}') from exc
    _need(type(data) is tuple and len(data) == 17
          and data[0] == 'universe.native-run-spot-checkpoint-envelope/1',
          'unsupported checkpoint envelope version')
    _need(data[12:16] == (True, False, False, False),
          'checkpoint readiness flags are outside the inactive projection contract')
    _need(type(data[4]) is tuple and len(data[4]) == 1 and type(data[4][0]) is int,
          'projection requires exactly one committed integer boundary')
    _need(type(data[7]) is tuple and not data[7],
          'accepted future choices are outside this historical projection')
    chain = data[8]
    _need(type(chain) is tuple and len(chain) == 8
          and chain[0] == 'universe.committed-native-receipt-chain/1'
          and chain[1:3] == data[1:3], 'unsupported receipt descriptor or logical roots')
    _need(type(chain[4]) is tuple and len(chain[4]) == 1,
          'projection requires exactly one receipt row')
    row = chain[4][0]
    _need(type(row) is tuple and len(row) == 9 and row[0] == data[4][0],
          'receipt row disagrees with committed boundary cursor')
    boundary, start, action_ids, effect_ids, action_rows, effect_rows, target_rows, _fences, rng_after = row
    _number(start, 'boundary start')
    _need(type(action_rows) is tuple and action_rows and len(action_rows) == len(action_ids),
          'Run Action coverage is incomplete')
    _need(type(effect_rows) is tuple and len(effect_rows) == len(effect_ids),
          'causal effect coverage is incomplete')
    _need(type(target_rows) is tuple and target_rows,
          'Target-owned result records are missing')

    actions = []
    action_by_id = {}
    actor_ids = set()
    for item in action_rows:
        _need(type(item) is tuple and len(item) == 10
              and item[1] == 'native.run-action/1',
              'only exact native RunActions are supported')
        aid, _adapter, actor, observed, begin, end, declaration, outcome, metadata, refs = item
        _need(type(aid) is str and aid and aid not in action_by_id,
              'missing or duplicate logical Spot Action ID')
        _need(type(actor) is str and actor and observed is None,
              'Run actor/Target references are invalid')
        _number(begin, 'Spot Action start'); _number(end, 'Spot Action end')
        _need(type(outcome) is str and outcome in ('success', 'partial'),
              'Run projection requires a movement-producing outcome')
        _need(type(declaration) is tuple and type(metadata) is tuple and type(refs) is tuple,
              'Spot declaration, metadata, or effect references are malformed')
        actor_ids.add(actor)
        metadata_value = _tag(metadata, 'Run metadata', 'sequence')[1]
        metadata_rows = tuple(_tag(row, 'Run metadata row', 'sequence')[1]
                              for row in metadata_value)
        displacement = next((row[1] for row in metadata_rows
                             if len(row) == 2 and row[0] == ('string', 'displacement')), None)
        measured = None if displacement is None else _number(displacement, 'Run displacement')
        measured_value = (None if measured is None else int(measured[1]) if measured[0] == 'integer'
                          else float.fromhex(measured[1]))
        _need(measured_value is not None and measured_value > 0,
              'Run Action lacks actual nonzero measured displacement')
        actions.append(RunActionProjection(aid, actor, begin, end,
            outcome, declaration, metadata, refs))
        action_by_id[aid] = item
    _need(len(actor_ids) == 1,
          'projection supports one Run actor')
    actor_id = next(iter(actor_ids))

    effects = []
    effect_by_id = {}
    practices_by_action = {}
    practice_by_effect = {}
    outcome_ids = set(); lifecycle_ids = set()
    for identity, payload in effect_rows:
        _need(type(identity) is tuple and len(identity) == 6 and identity[0] == 'effect-id'
              and identity[1] == data[2] and identity[2] == boundary
              and identity[3] in action_by_id,
              'effect has a broken boundary or Action reference')
        _need(identity not in effect_by_id, 'duplicate causal effect identity')
        _need(type(payload) is tuple and len(payload) == 2 and type(payload[0]) is str,
              'effect payload is malformed')
        expected_fields = {
            'effect.awareness/1': ('source_action_id', 'target_id', 'observed_id',
                                   'distance', 'max_distance', 'basis'),
            'effect.practice/1': ('source_action_id', 'target_id', 'skill', 'experience'),
            'effect.action-outcome/1': ('source_action_id', 'action_id', 'outcome'),
            'effect.lifecycle/1': ('source_action_id', 'action_id', 'status', 'from_queue',
                                   'to_queue', 'choice_id', 'previous_choice_action_state',
                                   'nominal_end', 'boundary', 'canceled_at', 'cancellation_reason'),
        }.get(payload[0])
        _need(expected_fields is not None, 'unsupported Spot effect version')
        fields = _record(payload, payload[0], expected_fields)
        source = _string(fields.get('source_action_id'), 'effect source Action')
        _need(source == identity[3], 'effect source does not match its identity')
        if payload[0] == 'effect.practice/1':
            _need(identity[4] == 'effect', 'practice effect has an invalid channel')
            target_id = _string(fields.get('target_id'), 'practice Target')
            skill = _string(fields.get('skill'), 'practice skill')
            exp = _number(fields.get('experience'), 'practice experience')
            _need(target_id == actor_id and action_by_id[source][1] == 'native.run-action/1'
                  and skill == 'run',
                  'Run practice Target/source/skill reference is inconsistent')
            practices_by_action.setdefault(source, []).append((identity, skill, exp))
            practice_by_effect[identity] = (skill, exp)
        elif payload[0] == 'effect.awareness/1':
            raise ProjectionRejected('Run projection does not support awareness effects')
        elif payload[0] == 'effect.action-outcome/1':
            _need(identity[4] == 'lifecycle'
                  and _string(fields.get('action_id'), 'outcome Action') == source
                  and _string(fields.get('outcome'), 'Action outcome') == action_by_id[source][7],
                  'Run outcome causal record is inconsistent')
            outcome_ids.add(source)
        elif payload[0] == 'effect.lifecycle/1':
            _need(identity[4] == 'lifecycle'
                  and _string(fields.get('action_id'), 'lifecycle Action') == source
                  and _string(fields.get('status'), 'lifecycle status') == 'finished'
                  and _number(fields.get('boundary'), 'lifecycle boundary') == ('integer', str(boundary))
                  and _number(fields.get('nominal_end'), 'lifecycle nominal end') == action_by_id[source][5]
                  and _string(fields.get('to_queue'), 'lifecycle destination queue') == 'finished',
                  'Run lifecycle record is inconsistent')
            lifecycle_ids.add(source)
        else:
            raise ProjectionRejected('unsupported Spot effect family')
        effect = EffectProjection(identity, payload[0], payload)
        effects.append(effect); effect_by_id[identity] = effect
    _need(tuple(effect_by_id) == tuple(effect_ids), 'effect identity ordering is inconsistent')
    _need(outcome_ids == set(action_by_id) and lifecycle_ids == set(action_by_id),
          'each Run Action needs one outcome and finished lifecycle record')
    for action in actions:
        expected = tuple(identity for identity in effect_ids if identity[3] == action.action_id)
        _need(action.effect_ids == expected, 'Run Action causal effect links are incomplete')
        practices = practices_by_action.get(action.action_id, ())
        _need(len(practices) == 1, 'each projected Run Action requires one Target-owned practice effect')

    targets = []
    target_by_id = {}
    for target in target_rows:
        _need(type(target) is tuple and len(target) == 4
              and target[1] == 'being' and target[0] not in target_by_id,
              'Target identity/type is missing, duplicated, or unsupported')
        tid, _category, position, state_data = target
        state = _record(state_data, 'target.candidate/1',
            ('target_id', 'category', 'starting_hp', 'projected_hp', 'actual_damage',
             'fatal_effect_ids', 'incoming', 'outgoing_effect_ids', 'aware_of',
             'practice_state', 'observer_state'))
        _need(_string(state['target_id'], 'Target state ID') == tid,
              'Target state identity disagrees with its record')
        _need(position[0] in ('cartesian', 'null'), 'unsupported Target position')
        incoming = _record_sequence(state['incoming'], 'effect.identified/1', ('identity', 'effect'))
        incoming_ids = tuple(_effect_id(fields, 'identity') for fields in incoming)
        outgoing = _sequence_effect_ids(state['outgoing_effect_ids'])
        aware = _sequence_strings(state['aware_of'])
        practice_state = _record(state['practice_state'], 'practice.projection/1',
            ('being_id', 'ordinary_levels', 'weapon_levels', 'baselines', 'skill_experience',
             'prior_uses', 'exercises', 'transitions', 'history_revision'))
        _need(_string(practice_state['being_id'], 'practice owner') == tid,
              'practice state belongs to another Target')
        _need(practice_state['history_revision'] == ('null',),
              'personal-history-bound practice is outside this projection')
        _need(position == ('null',) or (type(position) is tuple and len(position) == 2
              and position[0] == 'cartesian' and type(position[1]) is tuple
              and len(position[1]) == 3), 'Target position is malformed')
        if position != ('null',):
            for coordinate in position[1]: _number(coordinate, 'Target position coordinate')
        _need(state['starting_hp'] == state['projected_hp'] and state['actual_damage'] == ('integer', '0')
              and _tag(state['fatal_effect_ids'], 'fatal effects', 'sequence')[1] == (),
              'Spot boundary contains unsupported damage or fatal state')
        observer = _record(state['observer_state'], 'observer.projection/1',
            ('observer_id', 'observations', 'interpretations', 'heard_accounts', 'belief_recipient_ids'))
        for key in ('observations', 'interpretations', 'heard_accounts'):
            _tag(observer[key], key, 'mapping')
        _tag(observer['belief_recipient_ids'], 'belief recipients', 'sequence')
        _need(_string(observer['observer_id'], 'observer state owner') == tid
              and observer['observations'][1] == () and observer['interpretations'][1] == ()
              and observer['heard_accounts'][1] == () and observer['belief_recipient_ids'][1] == (),
              'observer evidence or recipients are outside this projection')
        exercises = []
        exercise_rows = _record_sequence(practice_state['exercises'], 'practice.exercise/1',
            ('effect_identity', 'skill_name', 'experience', 'action_id', 'nominal_end', 'resolved_at', 'outcome'))
        for fields in exercise_rows:
            effect_id = _effect_id(fields, 'effect_identity')
            _need(effect_id in effect_by_id and effect_by_id[effect_id].kind == 'effect.practice/1',
                  'practice exercise references an absent causal practice effect')
            aid = _string(fields['action_id'], 'practice Action')
            skill_name = _string(fields['skill_name'], 'practice skill')
            _need(fields['outcome'] == ('string', action_by_id[aid][7])
                  and fields['nominal_end'] == action_by_id[aid][5]
                  and fields['resolved_at'] == ('integer', str(boundary)),
                  'practice exercise timing/outcome disagrees with its Action')
            _need(effect_id[3] == aid and effect_id in practice_by_effect
                  and (skill_name, fields['experience']) == practice_by_effect[effect_id],
                  'exercise attribution differs from its causal practice effect')
            _need(type(fields['experience']) == tuple and type(fields['outcome']) == tuple,
                  'practice exercise values are malformed')
            _number(fields['experience'], 'exercise experience')
            _number(fields['nominal_end'], 'exercise nominal end')
            _number(fields['resolved_at'], 'exercise boundary')
            exercises.append(PracticeExerciseProjection(effect_id, aid,
                skill_name, fields['experience'],
                fields['nominal_end'], fields['resolved_at'],
                _string(fields['outcome'], 'practice outcome')))
        transitions = []
        transition_rows = _record_sequence(practice_state['transitions'], 'practice.transition/1',
            ('being_id', 'skill_name', 'time', 'level_before', 'level_after', 'baseline',
             'experience_before', 'experience_after', 'effect_ids'))
        for fields in transition_rows:
            transition_id = _string(fields['being_id'], 'transition Target')
            skill = _string(fields['skill_name'], 'transition skill')
            refs = _sequence_effect_ids(fields['effect_ids'])
            _need(transition_id == tid and all(ref in effect_by_id for ref in refs),
                  'practice transition Target/effect reference is broken')
            for key in ('time', 'level_before', 'level_after', 'baseline', 'experience_before', 'experience_after'):
                _number(fields[key], 'transition ' + key)
            transitions.append(PracticeTransitionProjection(tid, skill, fields['time'],
                fields['level_before'], fields['level_after'], fields['baseline'],
                fields['experience_before'], fields['experience_after'], refs))
        _need(incoming_ids == tuple(identity for identity in effect_ids
                                   if _effect_targets(effect_by_id[identity], tid)),
              'Target incoming effects disagree with causal effect records')
        _need(all(effect_id in effect_by_id for effect_id in outgoing),
              'Target outgoing effect reference is unresolved')
        batch_practice = []
        if transitions:
            _need(all(ex.experience[0] == 'integer' for ex in exercises),
                  'native BatchSkillUse requires integer practice awards')
            for transition in transitions:
                uses = tuple(ex for ex in exercises if ex.skill == transition.skill)
                _need(uses and tuple(ex.effect_id for ex in uses) == transition.effect_ids,
                      'Target practice transition does not match its simultaneous exercises')
                # atomic_publication._make_plan records BatchSkillUse with this
                # native aggregation over the candidate exercises.
                total = sum(int(ex.experience[1]) for ex in uses)
                batch_practice.append(BatchPracticeProjection(tid, transition.skill,
                    ('integer', str(total)), transition.level_before, transition.level_after,
                    transition.time, uses))
        target_projection = TargetProjection(tid, position, state['starting_hp'],
            state['projected_hp'], state['actual_damage'], incoming_ids, outgoing,
            aware, tuple(exercises), tuple(transitions), tuple(batch_practice), state_data)
        targets.append(target_projection); target_by_id[tid] = target_projection
    _need(len(target_by_id) == 2 and actor_id in target_by_id,
          'projection requires the two participant Target records including the Run actor')

    actor_target = target_by_id[actor_id]
    expected_practice_ids = tuple(identity for identity in effect_ids
                                  if effect_by_id[identity].kind == 'effect.practice/1')
    _need(tuple(ex.effect_id for ex in actor_target.practice_exercises) == expected_practice_ids,
          'Target-owned practice exercises do not cover Spot practice effects')
    _need(len(actor_target.practice_transitions) == 1
          and actor_target.practice_transitions[0].effect_ids == expected_practice_ids
          and actor_target.practice_transitions[0].skill == actor_target.practice_exercises[0].skill
          and actor_target.practice_transitions[0].time == ('integer', str(boundary)),
          'simultaneous practice transition does not cover the batch effect set')
    expected_awareness = ()
    _need(actor_target.aware_of == expected_awareness,
          'Run boundary contains unsupported awareness state')
    _need(actor_target.outgoing_effect_ids == tuple(identity for identity in effect_ids
          if identity[3] in action_by_id and action_by_id[identity[3]][2] == actor_id),
          'Target outgoing causal effects disagree with Run actor ownership')
    choice_rows = chain[5]
    _need(type(choice_rows) is tuple and len(choice_rows) == 1
          and type(choice_rows[0]) is tuple and len(choice_rows[0]) == 4
          and choice_rows[0][3] == action_ids,
          'committed Choice membership does not cover the Run Actions exactly')
    _need(type(rng_after) is tuple and type(data[9]) is tuple and len(data[9]) == 3
          and _rng_projection(data[9][2]) == rng_after,
          'receipt and checkpoint private RNG states disagree')
    projection = QuarantinedRunBoundaryProjection(PROJECTION_SCHEMA, data[1], data[2],
        boundary, start, tuple(actions), tuple(effects), tuple(targets), tuple(choice_rows), rng_after)
    _need(_is_data(projection.to_data()), 'projection contains a non-data value')
    return projection


# Historical call sites use the old Spot-named entry point. Its accepted data
# contract is now Run-only, so obsolete Spot checkpoint payloads fail closed.
project_quarantined_spot_boundary = project_quarantined_run_boundary
QuarantinedSpotBoundaryProjection = QuarantinedRunBoundaryProjection


def _record_sequence(value, tag, fields):
    _tag(value, 'record sequence', 'sequence')
    return tuple(_record(row, tag, fields) for row in value[1])


def _effect_id(fields, key):
    value = fields[key]
    _need(type(value) is tuple and len(value) == 6 and value[0] == 'effect-id',
          f'{key} is not a logical effect reference')
    return value


def _sequence_effect_ids(value):
    _tag(value, 'effect references', 'sequence')
    return tuple(_effect_id({'id': row}, 'id') for row in value[1])


def _sequence_strings(value):
    _tag(value, 'logical references', 'set')
    return tuple(_string(row, 'logical reference') for row in value[1])


def _effect_targets(effect, target_id):
    fields = dict(effect.payload[1])
    value = fields.get('target_id')
    return value == ('string', target_id)


def _is_data(value):
    if value is None or type(value) in (str, int, bool):
        return True
    if type(value) is tuple:
        return all(_is_data(item) for item in value)
    return False


def _rng_projection(value):
    if type(value) is tuple and len(value) == 2 and value[0] == 'tuple':
        return ('sequence', tuple(_rng_projection(row) for row in value[1]))
    return value
