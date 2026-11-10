"""Quarantine-only native identity binding for one committed Run projection."""
from dataclasses import dataclass
import math
import random
from weakref import WeakKeyDictionary

from checkpoint_projection import (PROJECTION_SCHEMA,
    MOVEMENT_PROJECTION_SCHEMA, QuarantinedMovementBoundaryProjection,
    QuarantinedRunBoundaryProjection, project_quarantined_movement_boundary,
    project_quarantined_run_boundary)
from checkpoint_views import (NativeIdentityView, NativeRunActionIdentityView,
    QuarantinedNativeEncounterView, QuarantinedRunBindingView,
    freeze_inspection_value)
from checkpoint_wire import (DecodedRunSpotWire, WIRE_SCHEMA,
    decode_run_spot_wire, encode_detached_run_spot_data)


BINDING_SCHEMA = 'universe.quarantined-run-native-identity-binding/1'
MOVEMENT_BINDING_SCHEMA = 'universe.quarantined-movement-native-identity-binding/1'


class IdentityBindingRejected(ValueError):
    """Input is outside the single-boundary native Run identity subset."""


def _need(test, message):
    if not test:
        raise IdentityBindingRejected(message)


def _data_number(value, label):
    from checkpoint_reconstruction import _tagged
    try:
        result = _tagged(value)
    except (TypeError, ValueError) as exc:
        raise IdentityBindingRejected(f'{label} is not an exact tagged number') from exc
    _need(type(result) in (int, float) and not isinstance(result, bool)
          and math.isfinite(result), f'{label} must be finite')
    return result


def _data_text(value, label):
    _need(type(value) is tuple and len(value) == 2 and value[0] == 'string'
          and type(value[1]) is str, f'{label} is not a tagged string')
    return value[1]


def _native_state_value(value, active=None):
    """Copy the reviewed native Being value graph to inert primitive data."""
    if value is None or type(value) in (str, bool, int, float):
        if type(value) is float:
            _need(math.isfinite(value), 'native state contains a non-finite number')
        return value
    if type(value) in (tuple, list):
        return tuple(_native_state_value(item, active) for item in value)
    if type(value) is dict:
        _need(all(type(key) in (str, int, float, bool) for key in value),
              'native state dictionary has an unsupported key type')
        return tuple((key, _native_state_value(value[key], active))
                     for key in sorted(value, key=lambda item: (type(item).__name__, repr(item))))
    active = set() if active is None else active
    identity = id(value)
    _need(identity not in active, 'native state contains an unsupported cycle')
    fields = object.__getattribute__(value, '__dict__') if hasattr(value, '__dict__') else None
    _need(type(fields) is dict and all(type(key) is str for key in fields),
          'native state contains an unsupported value')
    active.add(identity)
    try:
        return {key: _native_state_value(item, active) for key, item in fields.items()}
    finally:
        active.remove(identity)


def _being_state_snapshot(being, target):
    """Detached current-state view; deliberately excludes native histories."""
    position = being.get_position()
    state = {
        'id': being.id,
        'name': being.name,
        'type': being.type,
        'original_definition': _native_state_value(being.original.__dict__),
        'current_definition': _native_state_value(being.current.__dict__),
        'top_facing': being.top_facing,
        'front_facing': being.front_facing,
        'hex_facing': being.hex_facing,
        '_posture': being._posture,
        'parent_container_id': being.parent_container_id,
        'position': None if position is None else tuple(position.as_tuple()),
        'spatial_state': _native_state_value(being.spatial_state),
        'geometry': _native_state_value(being.geometry),
        'visual_occlusion': _native_state_value(being.visual_occlusion),
        'possessions': _native_state_value(being.possessions),
        'weapons': _native_state_value(being.weapons),
        'physiology_id': being.physiology_id,
        'physical_fatigue': _native_state_value(being.physical_fatigue.__dict__),
        'fatigue_level': being.fatigue_level,
        'effective_fitness': being.effective_fitness,
        'strategy': _native_state_value(being.strategy.__dict__),
        'exertion': _native_state_value(being.exertion.__dict__),
        'skill_experience': _native_state_value(being.skill_experience),
        'skill_practice_baselines': _native_state_value(being._skill_practice_baselines),
        'awareness': tuple(target.aware_of),
        'history_role': 'detached-target-sidecar-only',
    }
    return freeze_inspection_value(state)


def _encoded_mapping(value, label):
    _need(type(value) is tuple and len(value) == 2 and value[0] == 'mapping'
          and type(value[1]) is tuple, f'{label} is not a closed mapping')
    result = {}
    for row in value[1]:
        _need(type(row) is tuple and len(row) == 2 and type(row[0]) is str
              and row[0] not in result, f'{label} has an invalid key')
        result[row[0]] = _data_number(row[1], label)
    return result


def _record_fields(value, tag, expected, label):
    _need(type(value) is tuple and len(value) == 2 and value[0] == tag
          and type(value[1]) is tuple, f'{label} has an unsupported record')
    rows = value[1]
    _need(all(type(row) is tuple and len(row) == 2 for row in rows)
          and tuple(row[0] for row in rows) == expected,
          f'{label} has missing, reordered, or unsupported fields')
    return dict(rows)


def _validate_target_state(graph, fields, being, target, actor_target):
    """Cross-check hydrated current state against Target-owned projection."""
    state = _record_fields(target.state_data, 'target.candidate/1',
        ('target_id', 'category', 'starting_hp', 'projected_hp', 'actual_damage',
         'fatal_effect_ids', 'incoming', 'outgoing_effect_ids', 'aware_of',
         'practice_state', 'observer_state'), 'Target candidate')
    _need(_data_text(state['target_id'], 'Target ID') == being.id
          and _data_text(state['category'], 'Target category') == 'being',
          'Target candidate identity/category differs from native Being')
    expected_hp = _data_number(state['projected_hp'], 'Target projected HP')
    _need(expected_hp == _data_number(state['starting_hp'], 'Target starting HP')
          and _data_number(state['actual_damage'], 'Target damage') == 0
          and state['fatal_effect_ids'] == ('sequence', ()),
          'supported Run Target state must have no damage or fatal effect')
    _need(being.get_hit_points() == expected_hp,
          'materialized current HP differs from the Target candidate')

    if target.position == ('null',):
        _need(being.get_position() is None,
              'materialized position differs from Target position')
    else:
        _need(type(target.position) is tuple and len(target.position) == 2
              and target.position[0] == 'cartesian' and len(target.position[1]) == 3,
              'Target position is outside the Cartesian contract')
        expected_position = tuple(_data_number(value, 'Target position')
                                  for value in target.position[1])
        position = being.get_position()
        _need(position is not None and tuple(position.as_tuple()) == expected_position,
              'materialized position differs from Target candidate')

    practice = _record_fields(state['practice_state'], 'practice.projection/1',
        ('being_id', 'ordinary_levels', 'weapon_levels', 'baselines',
         'skill_experience', 'prior_uses', 'exercises', 'transitions',
         'history_revision'), 'Target practice state')
    _need(_data_text(practice['being_id'], 'practice owner') == being.id
          and practice['history_revision'] == ('null',)
          and practice['prior_uses'] == ('sequence', ()),
          'unsupported Target practice history or ownership')
    _need(being.current.skills.skills == _encoded_mapping(
              practice['ordinary_levels'], 'Target ordinary levels')
          and being.current.skills.weapon_skills == _encoded_mapping(
              practice['weapon_levels'], 'Target weapon levels')
          and being._skill_practice_baselines == _encoded_mapping(
              practice['baselines'], 'Target practice baselines')
          and being.skill_experience == _encoded_mapping(
              practice['skill_experience'], 'Target practice experience'),
          'materialized skills/practice differ from Target-owned candidate state')
    _need(all(type(observer) is str and observer for observer in target.aware_of),
          'Target awareness contains an unsupported identity')

    # Source history is checked as evidence for the sidecar, never instantiated
    # or attached to the fresh Being. This prevents double practice settlement.
    history_ref = graph.raw_ref(fields['skill_use_history'])
    history_tag, history_values = graph.nodes[history_ref]
    _need(history_tag == 'list', 'native skill-use history is not a closed list')
    expected_batches = target.batch_practice
    _need(len(history_values) == len(expected_batches),
          'native Target-owned batch history differs from projected transitions')
    for history_ref_value, batch in zip(history_values, expected_batches):
        batch_ref = graph.raw_ref(history_ref_value)
        batch_tag, batch_content = graph.nodes[batch_ref]
        _need(batch_tag == 'experience.BatchSkillUse',
              'native practice history contains a non-batch or unsupported record')
        batch_fields = graph.fields(batch_ref)[1]
        _need(set(batch_fields) == {'action_id', 'being_id', 'exercises', 'experience',
              'level_after', 'level_before', 'outcome', 'skill_name', 'time'},
              'native batch practice record has unsupported fields')
        _need(graph.data(batch_fields['action_id']) is None
              and graph.data(batch_fields['being_id']) == batch.target_id
              and graph.data(batch_fields['experience']) == _data_number(batch.experience, 'Batch XP')
              and graph.data(batch_fields['level_before']) == _data_number(batch.level_before, 'Batch level')
              and graph.data(batch_fields['level_after']) == _data_number(batch.level_after, 'Batch level')
              and graph.data(batch_fields['time']) == _data_number(batch.time, 'Batch time')
              and graph.data(batch_fields['skill_name']) == batch.skill
              and graph.data(batch_fields['outcome']) == batch.outcome,
              'native batch practice values differ from the Target sidecar')
        exercises_ref = graph.raw_ref(batch_fields['exercises'])
        exercises_tag, exercise_values = graph.nodes[exercises_ref]
        _need(exercises_tag == 'tuple' and len(exercise_values) == len(batch.exercises),
              'native batch causes differ from projected practice exercises')
        for exercise_ref_value, exercise in zip(exercise_values, batch.exercises):
            exercise_ref = graph.raw_ref(exercise_ref_value)
            exercise_tag, _ = graph.nodes[exercise_ref]
            _need(exercise_tag == 'frozen_practice.CandidatePracticeUse',
                  'native batch cause has an unsupported representation')
            exercise_fields = graph.fields(exercise_ref)[1]
            _need(set(exercise_fields) == {'action_id', 'effect_identity', 'experience',
                  'nominal_end', 'outcome', 'resolved_at', 'skill_name'},
                  'native batch cause has unsupported fields')
            _need(graph.data(exercise_fields['action_id']) == exercise.action_id
                  and graph.data(exercise_fields['skill_name']) == exercise.skill
                  and graph.data(exercise_fields['experience']) == _data_number(
                      exercise.experience, 'Exercise XP')
                  and graph.data(exercise_fields['nominal_end']) == _data_number(
                      exercise.nominal_end, 'Exercise nominal end')
                  and graph.data(exercise_fields['resolved_at']) == _data_number(
                      exercise.resolved_at, 'Exercise boundary')
                  and graph.data(exercise_fields['outcome']) == exercise.outcome,
                  'native batch cause differs from its projected Action contribution')
            graph.raw_ref(exercise_fields['effect_identity'])


@dataclass(frozen=True)
class QuarantinedRunHistoricalSidecar:
    schema: str
    projection: QuarantinedRunBoundaryProjection
    choice_id: str
    being_identity_ids: tuple
    action_identity_ids: tuple
    action_effect_links: tuple
    target_identity_ids: tuple
    batch_practice: tuple


@dataclass(frozen=True, eq=False)
class QuarantinedRunIdentityBinding:
    schema: str
    view: QuarantinedRunBindingView
    historical: QuarantinedRunHistoricalSidecar
    quarantined: bool = True


@dataclass(frozen=True)
class QuarantinedMovementHistoricalSidecar:
    schema: str
    projection: QuarantinedMovementBoundaryProjection
    participant_identity_ids: tuple
    participant_definition_values: tuple
    movement_activation: tuple
    target_record_identity_ids: tuple
    observer_evidence: tuple
    rng_state: tuple
    choice_ids: tuple = ()
    action_ids: tuple = ()
    effect_ids: tuple = ()


@dataclass(frozen=True)
class QuarantinedMovementIdentityBinding:
    schema: str
    universe_id: str
    encounter_id: str
    boundary: int
    sidecar: QuarantinedMovementHistoricalSidecar
    quarantined: bool = True


# Preserve imports for downstream restoration modules while routing the value
# contract to the Run-only classes above.
QuarantinedSpotHistoricalSidecar = QuarantinedRunHistoricalSidecar
QuarantinedSpotIdentityBinding = QuarantinedRunIdentityBinding


@dataclass(frozen=True)
class _PrivateNativeBinding:
    universe: object
    encounter: object
    beings: tuple
    actions: tuple
    rng_owner: object


_NATIVE_BINDINGS = WeakKeyDictionary()


def bind_quarantined_run_boundary(decoded, projection=None):
    """Bind fresh native identity shells to the exact supported Run projection.

    No Encounter choice is registered, no Action is resolved, no committed
    receipt is issued, and no historical Target/Action state is installed.
    """
    _need(type(decoded) is DecodedRunSpotWire and decoded.schema == WIRE_SCHEMA,
          'strict DecodedRunSpotWire/1 is required')
    try:
        canonical = encode_detached_run_spot_data(decoded.envelope_data)
        canonical_decoded = decode_run_spot_wire(canonical)
    except (TypeError, ValueError) as exc:
        raise IdentityBindingRejected(f'wire data failed strict validation: {exc}') from exc
    _need(canonical_decoded.wire_digest == decoded.wire_digest,
          'decoded wire data changed after digest validation')
    try:
        validated_projection = project_quarantined_run_boundary(canonical_decoded)
    except (TypeError, ValueError) as exc:
        raise IdentityBindingRejected(f'Run projection refused: {exc}') from exc
    if projection is not None:
        _need(type(projection) is QuarantinedRunBoundaryProjection
              and projection.schema == PROJECTION_SCHEMA
              and projection.to_data() == validated_projection.to_data(),
              'supplied projection does not exactly match the revalidated wire')
    projection = validated_projection
    data = canonical_decoded.envelope_data
    from checkpoint_inventory import _compatibility
    _need(data[3] == _compatibility(),
          'runtime/rules compatibility does not match this identity adapter')
    _need(data[4] == (projection.boundary,) and data[7] == (),
          'binding requires exactly one committed boundary and no future choices')
    _need(data[12:16] == (True, False, False, False),
          'envelope readiness flags are incompatible')

    from checkpoint_reconstruction import (_Graph, _sections, _rng_data,
        _materialize_being_original, _validate_being_definition_bindings)
    sections = _sections(data[5])
    _need(sections.get('readiness') == (False, False, False),
          'global checkpoint readiness flags must remain false')
    _need(sections.get('host-bindings') == ((),),
          'external recipient bindings are unsupported')
    rng_record = sections.get('rng')
    _need(type(rng_record) is tuple and len(rng_record) == 3
          and rng_record[:2] == ('caller_cursor', 'exclusive_encounter'),
          'private exclusive Encounter RNG ownership is required')
    rng_state = _rng_data(rng_record[2])
    _need(type(projection.rng_after) is tuple
          and type(data[9]) is tuple and len(data[9]) == 3
          and data[9][:2] == rng_record[:2]
          and _rng_data(data[9][2]) == rng_state,
          'checkpoint private RNG records are inconsistent')

    nodes_row = sections.get('nodes')
    _need(type(nodes_row) is tuple and len(nodes_row) == 1
          and type(nodes_row[0]) is tuple, 'closed native graph nodes are missing')
    graph = _Graph(nodes_row[0])
    universe_ref = ('universe', data[1])
    encounter_ref = ('encounter', data[2])
    _need(universe_ref in graph.nodes and encounter_ref in graph.nodes
          and graph.nodes[universe_ref][0] == 'universe.Universe'
          and graph.nodes[encounter_ref][0] == 'encounter.Encounter',
          'wire roots do not identify the native Universe and Encounter')
    universe_fields = graph.fields(universe_ref)[1]
    encounter_fields = graph.fields(encounter_ref)[1]
    arena_enabled = graph.data(encounter_fields['arena_activation_enabled'])
    _need(type(arena_enabled) is bool,
          'Arena activation-enabled state is not a native Boolean')
    _need(encounter_fields['arena_activation'] == ('null',),
          'activated Arena Encounter cannot be resumed by the bounded Run/Spot checkpoint')
    _need(encounter_fields['arena_movement_activation'] == ('null',),
          'movement-activated Arena Encounter cannot be resumed by the bounded Run/Spot checkpoint')
    _need(encounter_fields['initiation'] == ('null',),
          'target-directed Encounter initiation is outside the bounded checkpoint subset')
    _need(not arena_enabled,
          'Arena activation-enabled Encounter is outside the initiated Run/Spot checkpoint subset')
    _need(graph.data(encounter_fields['time']) == projection.boundary
          and graph.data(encounter_fields['last_processed_boundary']) == projection.boundary
          and graph.data(encounter_fields['start_time']) == _data_number(projection.start, 'boundary start'),
          'native Encounter cursor is inconsistent with the projected boundary')
    _need(type(projection.actions) is tuple and len(projection.actions) == 1,
          'exactly one historical Run Action is supported')
    actor_id = projection.actions[0].actor_id
    participants = tuple(target.target_id for target in projection.targets)
    _need(len(participants) == 2 and len(set(participants)) == 2
          and actor_id in participants,
          'the two participant Being identities must include the Run actor')
    participants = set(participants)
    action_ids = tuple(row.action_id for row in projection.actions)
    encounter_beings = graph.data(encounter_fields['being_list'])
    _need(type(encounter_beings) is list and set(encounter_beings) == participants
          and len(encounter_beings) == 2
          and graph.data(encounter_fields['non_being_object_list']) == [],
          'Encounter membership must contain exactly the projected two Beings')
    _need(graph.data(encounter_fields['pending_action_list']) == []
          and graph.data(encounter_fields['cancelled_action_list']) == []
          and tuple(graph.data(encounter_fields['finished_action_list'])) == action_ids,
          'native Action lifecycle queues disagree with the detached boundary')
    event_history = graph.raw_mapping(universe_fields['event_history'])
    _need(set(event_history) == {'0', data[2], *action_ids}
          and graph.raw_ref(event_history['0']) == ('event', '0')
          and graph.raw_ref(event_history[data[2]]) == encounter_ref
          and all(graph.raw_ref(event_history[action_id]) == ('event', action_id)
                  and graph.nodes[('event', action_id)][0] == 'activities.RunAction'
                  for action_id in action_ids),
          'native event history does not exactly cover origin, Encounter, and projected Run Action')
    _need(len(projection.actions) == 1
          and all(row.actor_id == actor_id
                  and _data_number(row.start, 'Action start') ==
                      _data_number(projection.start, 'boundary start')
                  and _data_number(row.end, 'Action end') == projection.boundary
                  for row in projection.actions),
          'only one Run Action ending at the committed boundary is supported')
    _need(projection.boundary == 1
          and _data_number(projection.start, 'Encounter start') == 0,
          'only the supported 0-to-1 Encounter interval is accepted')
    _need(len(projection.targets) == 2
          and {row.target_id for row in projection.targets} == participants,
          'Run Target coverage must be exactly the two participant Beings')
    source_awareness = graph.data(encounter_fields['awareness'])
    expected_awareness = {row.target_id: set(row.aware_of) for row in projection.targets}
    _need(source_awareness == expected_awareness,
          'Encounter awareness differs from the projected Target state')
    actor_target = next(row for row in projection.targets if row.target_id == actor_id)
    _need(len(actor_target.practice_transitions) == 1
          and len(actor_target.batch_practice) == 1,
          'the Run actor must have one Target-owned batch transition')
    run_batch = actor_target.batch_practice[0]
    _need(len(actor_target.practice_transitions) == 1
          and run_batch.skill == 'run' and len(run_batch.exercises) == 1
          and run_batch.exercises[0].action_id == projection.actions[0].action_id
          and run_batch.experience == run_batch.exercises[0].experience
          and run_batch.experience[0] == 'integer' and int(run_batch.experience[1]) > 0,
          'the supported batch must contain the single Run cause and its Target practice')

    receipt_chain = data[8]
    _need(type(receipt_chain) is tuple and len(receipt_chain) == 8
          and receipt_chain[1:3] == (data[1], data[2])
          and type(receipt_chain[5]) is tuple and len(receipt_chain[5]) == 1,
          'committed Choice identity coverage is incomplete')
    choice_row = receipt_chain[5][0]
    _need(type(choice_row) is tuple and len(choice_row) == 4
          and choice_row[3] == tuple(row.action_id for row in projection.actions),
          'one committed Choice must contain both projected Actions in order')
    choice_id = choice_row[0]
    choice_book_ref = graph.raw_ref(encounter_fields['_choice_book'])
    choice_book_fields = graph.fields(choice_book_ref, 'action_choice.ChoiceBook')[1]
    source_choices = graph.raw_mapping(choice_book_fields['_choices'])
    _need(set(source_choices) == {choice_id},
          'native ChoiceBook does not contain exactly the projected committed choice')
    accepted_ref = graph.raw_ref(source_choices[choice_id])
    accepted_fields = graph.fields(accepted_ref, 'action_choice._Accepted')[1]
    choice_view_ref = graph.raw_ref(accepted_fields['view'])
    choice_view_fields = graph.fields(choice_view_ref, 'action_choice.ChoiceView')[1]
    native_choice_actions = graph.data(choice_view_fields['action_ids'])
    _need(graph.data(choice_view_fields['id']) == choice_id
          and graph.data(choice_view_fields['state']) == 'finished'
          and tuple(native_choice_actions) == tuple(row.action_id for row in projection.actions),
          'native ChoiceView membership/status disagrees with the detached choice receipt')
    native_action_states = graph.data(choice_book_fields['_states'])
    _need(native_action_states == {action_id: 'finished' for action_id in action_ids},
          'native Action lifecycle states disagree with the projected boundary')

    from being import BeingDefinition, BeingDictionary, BeingInstance
    from skill import SkillDictionary
    from library import Library
    from actiondictionary import ActionDictionary
    from armor import ArmorDictionary
    from object import ObjectDictionary
    from weapon import WeaponDictionary
    from universe import Universe
    from activities import RunAction
    from strategy import Strategy
    from identifiable import Identifiable
    from atomic_publication import RNGCursor

    library_ref = graph.raw_ref(universe_fields['library'])
    library_fields = graph.fields(library_ref, 'library.Library')[1]
    being_dictionary_ref = graph.raw_ref(library_fields['being_dictionary'])
    being_dictionary_fields = graph.fields(being_dictionary_ref, 'being.BeingDictionary')[1]
    definitions_data = graph.raw_mapping(being_dictionary_fields['objects'])
    definitions = {}
    original_refs = {}
    object_registry_ref = graph.raw_ref(universe_fields['object_registry'])
    registry_fields = graph.fields(object_registry_ref, 'object.ObjectRegistry')[1]
    registry_data = graph.raw_mapping(registry_fields['object_instances'])
    _need(set(registry_data) == participants and len(registry_data) == 2,
          'native identity subset must contain exactly the two projected Being Objects')
    instance_refs = {}
    for logical_id, raw_ref in registry_data.items():
        instance_ref = graph.raw_ref(raw_ref)
        tag, fields = graph.fields(instance_ref, 'being.BeingInstance')
        _need(tag == 'being.BeingInstance', 'only native Being identities are supported')
        _need(graph.data(fields['id']) == logical_id,
              'ObjectRegistry logical key and Being identity disagree')
        original_ref = graph.raw_ref(fields['original'])
        original_refs[logical_id] = original_ref
        instance_refs[logical_id] = (instance_ref, fields)
        _need(graph.data(fields['personal_history']) is None,
              'personal-history-bearing Beings are outside the identity subset')
    referenced_definition_names = set()
    for logical_id, original_ref in original_refs.items():
        original_fields = graph.fields(original_ref, 'being.BeingDefinition')[1]
        name = graph.data(original_fields['obj_type'])
        _need(type(name) is str and name,
              'Being original has an invalid native type-template key')
        referenced_definition_names.add(name)
    _need(set(definitions_data) == referenced_definition_names,
          'BeingDictionary contains definitions outside the two-Being identity subset')
    for name, raw_ref in definitions_data.items():
        definition = graph.native(graph.raw_ref(raw_ref))
        _need(type(definition) is BeingDefinition and definition.obj_type == name,
              'Being definition key/type or native constructor is incompatible')
        definitions[name] = definition
    try:
        definition_kinds_data = _validate_being_definition_bindings(
            graph, registry_data, definitions_data)
    except (TypeError, ValueError) as exc:
        raise IdentityBindingRejected(f'Being definition binding refused: {exc}') from exc
    validated_templates, template_refs, definition_kinds = definition_kinds_data
    _need(all(validated_templates[name] is definitions[name] for name in definitions),
          'Being template reconstruction changed Library object identity')

    native_being_dictionary = BeingDictionary()
    native_being_dictionary.objects = definitions
    native_being_dictionary.object_categories = graph.data(being_dictionary_fields['object_categories'])
    skill_dictionary_ref = graph.raw_ref(library_fields['skill_dictionary'])
    skill_fields = graph.fields(skill_dictionary_ref, 'skill.SkillDictionary')[1]
    native_skill_dictionary = SkillDictionary()
    native_skill_dictionary.skills = graph.data(skill_fields['skills'])
    _need(type(native_skill_dictionary.skills) is dict
          and 'run' in native_skill_dictionary.skills,
          'native Run skill definition is missing')
    library_id = graph.data(library_fields['id'])
    library_name = graph.data(library_fields['name'])
    native_library = Library(load_definitions=False, name=library_name, id=library_id)
    native_library.being_dictionary = native_being_dictionary
    native_library.skill_dictionary = native_skill_dictionary
    for field, constructor in (
            ('action_dictionary', ActionDictionary), ('armor_dictionary', ArmorDictionary),
            ('object_dictionary', ObjectDictionary), ('weapon_dictionary', WeaponDictionary)):
        dictionary_ref = graph.raw_ref(library_fields[field])
        dictionary_tag, dictionary_fields = graph.fields(dictionary_ref)
        native_dictionary = constructor()
        expected_tag = {
            'action_dictionary': 'actiondictionary.ActionDictionary',
            'armor_dictionary': 'armor.ArmorDictionary',
            'object_dictionary': 'object.ObjectDictionary',
            'weapon_dictionary': 'weapon.WeaponDictionary',
        }[field]
        _need(dictionary_tag == expected_tag,
              f'unsupported native Library dependency: {field}')
        for attr, value in dictionary_fields.items():
            setattr(native_dictionary, attr, graph.data(value))
        _need(all(value == {} or value == [] for value in native_dictionary.__dict__.values()),
              f'nonempty unsupported native catalog: {field}')
        setattr(native_library, field, native_dictionary)

    universe_name = graph.data(universe_fields['name'])
    native_universe = Universe(name=universe_name, library=native_library)
    _need(native_universe.id == data[1], 'native Universe logical identity differs')
    native_beings = {}
    being_views = []
    for logical_id in sorted(participants):
        instance_ref, fields = instance_refs[logical_id]
        expected_instance_fields = {
            '_atomic_target_history', '_skill_practice_baselines', 'current',
            'effective_fitness', 'exertion', 'fatigue_level', 'front_facing', 'hex_facing',
            'geometry', 'id', 'name', 'original', 'parent_container_id',
            'personal_history', 'physical_fatigue', 'physiology_id', 'possessions',
            'skill_experience', 'skill_use_history', 'spatial_state', 'strategy',
            'top_facing', 'type', 'visual_occlusion', 'weapons', '_posture'}
        _need(set(fields) == expected_instance_fields,
              'Being has missing or unsupported current-state fields')
        facing = graph.data(fields['hex_facing'])
        _need(facing is None or type(facing) is int and 0 <= facing < 12,
              'Being hex facing must be null or an integer from 0 through 11')
        posture = graph.data(fields['_posture'])
        _need(posture is None or type(posture) is str
              and posture in ('standing', 'crouching', 'lying'),
              'Being posture must be unknown or a supported posture string')
        current_fields = graph.fields(graph.raw_ref(fields['current']),
                                      'being.BeingDefinition')[1]
        states_fields = graph.fields(graph.raw_ref(current_fields['states']),
                                     'states.States')[1]
        legacy_states = graph.data(states_fields['states'])
        _need(type(legacy_states) is dict,
              'Being legacy state dictionary is malformed')
        legacy_prone = legacy_states.get('prone')
        _need(legacy_prone is None or type(legacy_prone) is bool,
              'legacy prone state must be an explicit Boolean or unknown')
        _need(legacy_prone is not True or posture in (None, 'lying'),
              'legacy prone state conflicts with standing/crouching posture')
        name = graph.data(fields['name'])
        _need(type(name) is str and name,
              'Being identity has no supported display name')
        original_ref = original_refs[logical_id]
        definition = _materialize_being_original(
            graph, logical_id, fields, definitions, template_refs, definition_kinds)
        native = BeingInstance(definition, name=name)
        Identifiable.__init__(native, name, id=logical_id)
        current_ref = graph.raw_ref(fields['current'])
        current = graph.native(current_ref)
        _need(native.id == logical_id and current is not definition,
              'Being native identity/state constructor contract failed')
        # This is the same reviewed native initialization path used for the
        # initial quarantined native graph: definitions and nested physical
        # state are rebuilt by _Graph.native, while instance fields are copied
        # from the closed inventory. No Action or practice is replayed.
        native.current = current
        for field in ('top_facing', 'front_facing', 'parent_container_id',
                      'physiology_id', 'fatigue_level', 'effective_fitness',
                      'skill_experience', '_skill_practice_baselines',
                      'possessions', 'weapons'):
            setattr(native, field, graph.value(fields[field]))
        native.set_hex_facing(facing)
        native.set_posture(posture)
        for field, setter in (('spatial_state', 'set_spatial_state'),
                              ('geometry', 'set_geometry'),
                              ('visual_occlusion', 'set_visual_occlusion')):
            getattr(native, setter)(graph.value(fields[field]))
        native.physical_fatigue = graph.value(fields['physical_fatigue'])
        native.strategy = graph.value(fields['strategy'])
        native.exertion = graph.value(fields['exertion'])
        _need(native.id == logical_id and native.original is definition
              and native.current is current,
              'Being logical identity or definition references changed during materialization')

        target = next(row for row in projection.targets if row.target_id == logical_id)
        _validate_target_state(graph, fields, native, target, actor_target)
        native_universe.add_object(native)
        native_beings[logical_id] = native
        being_views.append(NativeIdentityView('being', logical_id, name,
            'verified_quarantined_post_boundary_current_state',
            _being_state_snapshot(native, target)))

    native_actions = {}
    action_views = []
    for projected in projection.actions:
        declaration = dict(projected.declaration)
        _need(declaration.get('event_type') == 'run'
              and declaration.get('parent_encounter_id') == projection.encounter_id,
              'Run declaration family or Encounter identity is inconsistent')
        parameters_row = declaration.get('parameters')
        _need(type(parameters_row) is tuple
              and all(type(row) is tuple and len(row) == 2 for row in parameters_row),
              'Run declaration parameters are unsupported')
        params = dict(parameters_row)
        _need(set(params) == {'minimum_distance', 'practice_experience', 'start_position'},
              'Run declaration contains unsupported or missing parameters')
        strategy_row = declaration.get('strategy')
        _need(type(strategy_row) is tuple
              and all(type(row) is tuple and len(row) == 2 for row in strategy_row),
              'Run strategy declaration is unsupported')
        strategy_values = {key: _data_number(value, 'Strategy effort')
                           for key, value in strategy_row}
        _need(set(strategy_values) == {'attack', 'defense', 'timing', 'extra_damage'},
              'Run strategy fields are incomplete')
        start_time = _data_number(projected.start, 'Run start')
        end_time = _data_number(projected.end, 'Run end')
        minimum_distance = _data_number(params['minimum_distance'], 'Run minimum distance')
        practice_experience = _data_number(params['practice_experience'], 'Run practice')
        start_position_data = params['start_position']
        _need(type(practice_experience) is int and type(minimum_distance) is float
              and type(start_position_data) is tuple and len(start_position_data) == 2
              and start_position_data[0] == 'cartesian'
              and type(start_position_data[1]) is tuple and len(start_position_data[1]) == 3,
              'Run declaration uses unsupported native parameter types')
        display_name = (None if declaration['display_name'] == ('null',)
                        else _data_text(declaration['display_name'], 'Run display name'))
        action = RunAction(native_universe, projected.actor_id,
            start_time, end_time-start_time, minimum_distance,
            experience=practice_experience)
        from spatial.state import CartesianPosition
        action.start_position = CartesianPosition(*(
            _data_number(value, 'Run starting coordinate')
            for value in start_position_data[1]))
        Identifiable.__init__(action, display_name, id=projected.action_id)
        action.start_time = start_time
        action.end_time = end_time
        action.parent_event_id = projection.encounter_id
        action.strategy = Strategy(**strategy_values)
        action._checkpoint_quarantined = True
        _need(type(action) is RunAction and action.id == projected.action_id
              and action.start_time == start_time and action.end_time == end_time
              and action.actor_id == projected.actor_id and action.target_id is None
              and action.resolution is None and action.start_position is not None
              and action.displacement is None,
              'inert native Run Action identity constructor contract failed')
        native_actions[action.id] = action
        action_views.append(NativeRunActionIdentityView(action.id, choice_id,
            action.actor_id, projected.start, projected.end))

    module_rng_before = random.getstate()
    rng_owner = RNGCursor(rng_state)
    _need(rng_owner.state == rng_state and random.getstate() == module_rng_before,
          'private RNG state changed during native identity allocation')
    from encounter import Encounter, _QuarantinedPostBoundaryPlan
    awareness_rows = tuple((observer_id, tuple(sorted(target_ids)))
                           for observer_id, target_ids in sorted(source_awareness.items()))
    plan = _QuarantinedPostBoundaryPlan(
        native_universe, projection.encounter_id, 0, 1,
        graph.data(encounter_fields['difficulty_class']),
        graph.data(encounter_fields['name']),
        graph.data(encounter_fields['event_type']),
        graph.data(encounter_fields['location']),
        graph.data(encounter_fields['parent_event_id']),
        graph.data(encounter_fields['end_time']),
        graph.data(encounter_fields['initiated']),
        tuple(encounter_beings), awareness_rows, rng_owner)
    try:
        native_encounter = Encounter._construct_quarantined_post_boundary(plan)
    except (TypeError, ValueError) as exc:
        raise IdentityBindingRejected(f'quarantined Encounter construction refused: {exc}') from exc
    from transactional_progression import (is_quarantined,
        quarantine_reconstructed_graph)
    quarantine_reconstructed_graph(native_universe,
        tuple(native_beings.values()) + tuple(native_actions.values()) + (native_encounter,))
    _need(is_quarantined(native_encounter)
          and native_encounter.time == projection.boundary
          and native_encounter.last_processed_boundary == projection.boundary
          and native_encounter._coordinator_time == projection.boundary
          and native_encounter._interval_start == projection.boundary
          and native_encounter.being_list == list(encounter_beings)
          and native_encounter.awareness == source_awareness,
          'quarantined Encounter context disagrees with source boundary')

    effect_ids = tuple(effect.identity for effect in projection.effects)
    action_effect_links = tuple((action.action_id, action.effect_ids)
                                for action in projection.actions)
    target_ids = tuple(target.target_id for target in projection.targets)
    batch = actor_target.batch_practice
    participant_ids = tuple(sorted(participants))
    sidecar = QuarantinedRunHistoricalSidecar(
        'universe.quarantined-run-history-sidecar/1', projection, choice_id,
        participant_ids, tuple(row.action_id for row in projection.actions),
        action_effect_links, target_ids, batch)
    native_encounter_view = QuarantinedNativeEncounterView(
        native_encounter.id, native_universe.id,
        native_encounter.start_time, native_encounter.time,
        native_encounter.last_processed_boundary,
        native_encounter.last_processed_boundary + 1,
        tuple(native_encounter.being_list),
        freeze_inspection_value(tuple((observer_id, tuple(sorted(target_ids)))
            for observer_id, target_ids in sorted(native_encounter.awareness.items()))),
        tuple(native_encounter.pending_action_list),
        tuple(native_encounter.finished_action_list),
        tuple(native_encounter.cancelled_action_list),
        len(native_encounter._choice_book._choices),
        len(native_encounter._choice_book._reservations),
        'caller_cursor', 'exclusive_encounter',
        freeze_inspection_value(rng_owner.state), True)
    view = QuarantinedRunBindingView(BINDING_SCHEMA, projection.universe_id,
        projection.encounter_id, projection.boundary, projection.start,
        tuple(being_views), tuple(action_views), choice_id,
        freeze_inspection_value(effect_ids), freeze_inspection_value(rng_state), True,
        native_encounter_view)
    result = QuarantinedRunIdentityBinding(BINDING_SCHEMA, view, sidecar, True)
    _NATIVE_BINDINGS[result] = _PrivateNativeBinding(native_universe, native_encounter,
        tuple(native_beings.items()), tuple(native_actions.items()), rng_owner)
    return result


def bind_quarantined_movement_boundary(decoded, projection=None):
    """Bind the existing movement-only Target identities without installing history.

    The result is a detached sidecar over validated native graph identities.
    It deliberately does not create an Action/Choice, issue a receipt, or make
    the reconstructed Encounter executable.
    """
    _need(type(decoded) is DecodedRunSpotWire and decoded.schema == WIRE_SCHEMA,
          'strict DecodedRunSpotWire/1 is required')
    try:
        wire = encode_detached_run_spot_data(decoded.envelope_data)
        canonical = decode_run_spot_wire(wire)
        current = project_quarantined_movement_boundary(canonical)
    except (TypeError, ValueError) as exc:
        raise IdentityBindingRejected(f'movement projection refused: {exc}') from exc
    _need(canonical.wire_digest == decoded.wire_digest,
          'decoded movement checkpoint changed after digest validation')
    if projection is not None:
        _need(type(projection) is QuarantinedMovementBoundaryProjection
              and projection.schema == MOVEMENT_PROJECTION_SCHEMA
              and projection.to_data() == current.to_data(),
              'supplied movement projection differs from revalidated wire data')
    projection = current
    data = canonical.envelope_data
    from checkpoint_inventory import _compatibility
    _need(data[3] == _compatibility(),
          'runtime/rules compatibility does not match movement identity adapter')
    from checkpoint_reconstruction import (_Graph, _sections, _rng_data,
        _projection, _validate_being_definition_bindings)
    sections = _sections(data[5])
    _need(sections.get('readiness') == (False, False, False)
          and sections.get('host-bindings') == ((),),
          'movement binding requires false readiness and no external recipients')
    rng_record = sections.get('rng')
    _need(type(rng_record) is tuple and len(rng_record) == 3
          and rng_record[:2] == ('caller_cursor', 'exclusive_encounter'),
          'exclusive private Encounter RNG ownership is required')
    rng_state = _rng_data(rng_record[2])
    def receipt_rng(value):
        _need(type(value) is tuple and len(value) == 2
              and value[0] == 'sequence' and type(value[1]) is tuple,
              'movement receipt RNG state is malformed')
        def convert(item):
            if type(item) is tuple and len(item) == 2 and item[0] == 'sequence':
                return ('tuple', tuple(convert(child) for child in item[1]))
            return item
        return ('tuple', tuple(convert(item) for item in value[1]))
    _need(data[9][:2] == rng_record[:2]
          and _rng_data(data[9][2]) == rng_state
          and _rng_data(receipt_rng(projection.rng_after)) == rng_state,
          'committed RNG cursor differs from native movement receipt')
    nodes_row = sections.get('nodes')
    _need(type(nodes_row) is tuple and len(nodes_row) == 1,
          'native graph nodes are missing')
    graph = _Graph(nodes_row[0])
    universe_ref = ('universe', data[1])
    encounter_ref = ('encounter', data[2])
    _need(universe_ref in graph.nodes and encounter_ref in graph.nodes,
          'movement checkpoint roots are missing')
    universe_fields = graph.fields(universe_ref, 'universe.Universe')[1]
    encounter_fields = graph.fields(encounter_ref, 'encounter.Encounter')[1]
    _need(graph.data(encounter_fields['time']) == 1
          and graph.data(encounter_fields['last_processed_boundary']) == 1
          and graph.data(encounter_fields['_coordinator_time']) == 1
          and graph.data(encounter_fields['_interval_start']) == 1,
          'committed native chronology differs from movement Target boundary')
    _need(graph.data(encounter_fields['pending_action_list']) == []
          and graph.data(encounter_fields['finished_action_list']) == []
          and graph.data(encounter_fields['cancelled_action_list']) == [],
          'movement-only boundary contains native Action lifecycle state')
    choice_ref = graph.raw_ref(encounter_fields['_choice_book'])
    choice_fields = graph.fields(choice_ref, 'action_choice.ChoiceBook')[1]
    _need(graph.raw_mapping(choice_fields['_choices']) == {}
          and graph.data(choice_fields['_counter']) == 0
          and graph.data(choice_fields['_states']) == {},
          'movement-only boundary contains native Choice state')
    registry_ref = graph.raw_ref(universe_fields['object_registry'])
    registry_fields = graph.fields(registry_ref, 'object.ObjectRegistry')[1]
    registry = graph.raw_mapping(registry_fields['object_instances'])
    participants = projection.participant_ids
    _need(set(registry) == set(participants) and len(registry) == 2,
          'native registry identity set differs from movement participants')
    library_ref = graph.raw_ref(universe_fields['library'])
    library_fields = graph.fields(library_ref, 'library.Library')[1]
    dictionary_ref = graph.raw_ref(library_fields['being_dictionary'])
    dictionary_fields = graph.fields(dictionary_ref, 'being.BeingDictionary')[1]
    all_definitions = graph.raw_mapping(dictionary_fields['objects'])
    referenced_names = set()
    for target_id in participants:
        instance_ref = graph.raw_ref(registry[target_id])
        original_ref = graph.raw_ref(graph.fields(instance_ref)[1]['original'])
        original_fields = graph.fields(original_ref, 'being.BeingDefinition')[1]
        referenced_names.add(graph.data(original_fields['obj_type']))
    _need(referenced_names and referenced_names <= set(all_definitions),
          'Being originals have no matching registered Library templates')
    definitions = {name: all_definitions[name] for name in referenced_names}
    try:
        _validate_being_definition_bindings(graph, registry, definitions)
    except (TypeError, ValueError) as exc:
        raise IdentityBindingRejected(f'Being original identity binding refused: {exc}') from exc

    from atomic_publication import TargetIntervalRecord
    from action_settlement import TargetCandidate
    from checkpoint_receipts import _value
    record_identity_ids = []
    definition_values = []
    targets_by_id = {row[0]: row for row in projection.target_records}
    _need(set(targets_by_id) == set(participants),
          'portable Target identities do not cover the participant set')
    for target_id in participants:
        instance_ref = graph.raw_ref(registry[target_id])
        instance_tag, instance_fields = graph.fields(instance_ref, 'being.BeingInstance')
        _need(graph.data(instance_fields['id']) == target_id,
              'Target owner and ObjectRegistry logical identity differ')
        original_ref = graph.raw_ref(instance_fields['original'])
        current_ref = graph.raw_ref(instance_fields['current'])
        definition_values.append((target_id, _projection(graph.native(original_ref)),
                                  _projection(graph.native(current_ref))))
        history_ref = graph.raw_ref(instance_fields['_atomic_target_history'])
        history_tag, history_values = graph.nodes[history_ref]
        _need(history_tag == 'list' and len(history_values) == 1,
              'each movement participant must own exactly one Target interval record')
        target_ref = graph.raw_ref(history_values[0])
        record_fields = graph.fields(target_ref, 'atomic_publication.TargetIntervalRecord')[1]
        _need(set(record_fields) == {'boundary', 'encounter_id', 'state'}
              and graph.data(record_fields['encounter_id']) == projection.encounter_id
              and graph.data(record_fields['boundary']) == projection.boundary,
              'Target interval record has a wrong or duplicate committed identity')
        state_ref = graph.raw_ref(record_fields['state'])
        state_fields = graph.fields(state_ref, 'action_settlement.TargetCandidate')[1]
        candidate = TargetCandidate(**{key: graph.value(value)
                                       for key, value in state_fields.items()})
        _need(_value(candidate) == targets_by_id[target_id][3],
              'Target-owned native state differs from its committed portable receipt')
        record_identity_ids.append((target_id, target_ref))

    entity_ids = tuple(sorted(registry))
    observer_rows = []
    from checkpoint_arena_perception import decode_arena_perception_ledger
    for observer_id, encoded in projection.observer_evidence:
        current_rows = encoded[3]
        visible_ids = tuple(row[0] for row in current_rows)
        try:
            ledger = decode_arena_perception_ledger(encoded,
                observer_id=observer_id, entity_ids=entity_ids,
                visible_entity_ids=visible_ids, boundary=1, time=1)
        except (TypeError, ValueError) as exc:
            raise IdentityBindingRejected(f'observer-owned evidence refused: {exc}') from exc
        observer_rows.append((observer_id, ledger.observer_id,
                              tuple(sorted(ledger._current)), tuple(ledger._history), encoded))
    participant_identity_ids = tuple((target_id, graph.raw_ref(registry[target_id]))
                                     for target_id in participants)
    sidecar = QuarantinedMovementHistoricalSidecar(
        'universe.quarantined-movement-history-sidecar/1', projection,
        participant_identity_ids, tuple(definition_values),
        projection.movement_activation, tuple(record_identity_ids), tuple(observer_rows),
        rng_state)
    return QuarantinedMovementIdentityBinding(MOVEMENT_BINDING_SCHEMA,
        data[1], data[2], projection.boundary, sidecar, True)


@dataclass(frozen=True)
class _QuarantinedMovementNativeGraph:
    universe: object
    encounter: object
    beings: tuple
    targets: tuple
    source_receipt_fields: tuple
    source_inspection: object
    rng_owner: object
    projection: QuarantinedMovementBoundaryProjection


def _materialize_quarantined_movement_native(decoded, projection=None):
    """Build a private boundary-1 Arena graph; receipt import is owned elsewhere."""
    binding = bind_quarantined_movement_boundary(decoded, projection)
    data = decoded.envelope_data
    from checkpoint_reconstruction import (_Graph, _sections, _rng_data,
        _materialize_being_original, _validate_being_definition_bindings)
    sections = _sections(data[5])
    rng_state = _rng_data(sections['rng'][2])
    graph = _Graph(sections['nodes'][0])
    universe_ref = ('universe', data[1])
    encounter_ref = ('encounter', data[2])
    universe_fields = graph.fields(universe_ref, 'universe.Universe')[1]
    encounter_fields = graph.fields(encounter_ref, 'encounter.Encounter')[1]
    registry_ref = graph.raw_ref(universe_fields['object_registry'])
    registry_fields = graph.fields(registry_ref, 'object.ObjectRegistry')[1]
    registry = graph.raw_mapping(registry_fields['object_instances'])
    participants = binding.sidecar.projection.participant_ids
    _need(set(registry) == set(participants) and len(registry) == 2,
          'movement native construction requires exactly the recorded two Being identities')

    library_ref = graph.raw_ref(universe_fields['library'])
    library_fields = graph.fields(library_ref, 'library.Library')[1]
    being_dictionary_ref = graph.raw_ref(library_fields['being_dictionary'])
    being_dictionary_fields = graph.fields(being_dictionary_ref, 'being.BeingDictionary')[1]
    all_definitions = graph.raw_mapping(being_dictionary_fields['objects'])
    referenced_types = set()
    instance_fields_by_id = {}
    for being_id in participants:
        instance_ref = graph.raw_ref(registry[being_id])
        fields = graph.fields(instance_ref, 'being.BeingInstance')[1]
        _need(graph.data(fields['id']) == being_id,
              'native participant reference differs from its registry identity')
        instance_fields_by_id[being_id] = fields
        original_ref = graph.raw_ref(fields['original'])
        original_fields = graph.fields(original_ref, 'being.BeingDefinition')[1]
        referenced_types.add(graph.data(original_fields['obj_type']))
    _need(referenced_types and referenced_types <= set(all_definitions),
          'native Being originals have no matching registered templates')
    definitions = {name: graph.native(graph.raw_ref(all_definitions[name]))
                   for name in referenced_types}
    try:
        validated, template_refs, kinds = _validate_being_definition_bindings(
            graph, registry, {name: all_definitions[name] for name in referenced_types})
    except (TypeError, ValueError) as exc:
        raise IdentityBindingRejected(f'Being template/original reconstruction refused: {exc}') from exc
    _need(all(validated[name] is definitions[name] for name in definitions),
          'native shared Being template identity changed during reconstruction')

    from being import BeingDictionary, BeingInstance
    from skill import SkillDictionary
    from library import Library
    from actiondictionary import ActionDictionary
    from armor import ArmorDictionary
    from object import ObjectDictionary
    from weapon import WeaponDictionary
    from universe import Universe
    from identifiable import Identifiable
    native_being_dictionary = BeingDictionary()
    native_being_dictionary.objects = definitions
    native_being_dictionary.object_categories = graph.data(
        being_dictionary_fields['object_categories'])
    skill_ref = graph.raw_ref(library_fields['skill_dictionary'])
    skill_fields = graph.fields(skill_ref, 'skill.SkillDictionary')[1]
    native_skill_dictionary = SkillDictionary()
    native_skill_dictionary.skills = graph.data(skill_fields['skills'])
    _need(type(native_skill_dictionary.skills) is dict,
          'native skill dictionary is outside the bounded movement import')
    native_library = Library(load_definitions=False,
        name=graph.data(library_fields['name']), id=graph.data(library_fields['id']))
    native_library.being_dictionary = native_being_dictionary
    native_library.skill_dictionary = native_skill_dictionary
    # The result is inspection-only and remains quarantined. The full catalog is
    # retained in the portable source graph but is outside this native import.
    for field, constructor in (
            ('action_dictionary', ActionDictionary), ('armor_dictionary', ArmorDictionary),
            ('object_dictionary', ObjectDictionary), ('weapon_dictionary', WeaponDictionary)):
        setattr(native_library, field, constructor())
    native_universe = Universe(name=graph.data(universe_fields['name']),
                               library=native_library)
    _need(native_universe.id == data[1],
          'native Universe constructor changed the logical identity')

    from checkpoint_arena_perception import decode_arena_perception_ledger
    evidence_by_observer = dict(binding.sidecar.projection.observer_evidence)
    entity_ids = tuple(sorted(registry))
    native_beings = {}
    for being_id in participants:
        fields = instance_fields_by_id[being_id]
        expected_fields = {
            '_arena_perception_ledger', '_atomic_target_history',
            '_skill_practice_baselines', 'current', 'effective_fitness', 'exertion',
            'fatigue_level', 'front_facing', 'hex_facing', 'geometry', 'id', 'name',
            'original', 'parent_container_id', 'personal_history', 'physical_fatigue',
            'physiology_id', 'possessions', 'skill_experience', 'skill_use_history',
            'spatial_state', 'strategy', 'top_facing', 'type', 'visual_occlusion',
            'weapons', '_posture'}
        _need(set(fields) == expected_fields,
              'Being checkpoint has missing or unsupported movement state fields')
        _need(graph.data(fields['personal_history']) is None,
              'personal-history-bearing Beings are outside movement restoration')
        name = graph.data(fields['name'])
        original = _materialize_being_original(graph, being_id, fields,
            definitions, template_refs, kinds)
        being = BeingInstance(original, name=name)
        Identifiable.__init__(being, name, id=being_id)
        current = graph.native(graph.raw_ref(fields['current']))
        _need(current is not original and current.obj_type == original.obj_type,
              'Being original/current separation is invalid')
        being.current = current
        for field in ('top_facing', 'front_facing', 'parent_container_id',
                      'physiology_id', 'fatigue_level', 'effective_fitness',
                      'skill_experience', '_skill_practice_baselines',
                      'possessions', 'weapons'):
            setattr(being, field, graph.value(fields[field]))
        facing = graph.data(fields['hex_facing'])
        posture = graph.data(fields['_posture'])
        being.set_hex_facing(facing)
        being.set_posture(posture)
        for field, setter in (('spatial_state', 'set_spatial_state'),
                              ('geometry', 'set_geometry'),
                              ('visual_occlusion', 'set_visual_occlusion')):
            getattr(being, setter)(graph.value(fields[field]))
        being.physical_fatigue = graph.value(fields['physical_fatigue'])
        being.strategy = graph.value(fields['strategy'])
        being.exertion = graph.value(fields['exertion'])
        encoded = evidence_by_observer[being_id]
        visible_ids = tuple(row[0] for row in encoded[3])
        being._arena_perception_ledger = decode_arena_perception_ledger(
            encoded, observer_id=being_id, entity_ids=entity_ids,
            visible_entity_ids=visible_ids, boundary=1, time=1)
        being._atomic_target_history = []
        native_universe.add_object(being)
        native_beings[being_id] = being

    from action_settlement import TargetCandidate
    from atomic_publication import RNGCursor, TargetIntervalRecord
    from checkpoint_receipts import _value
    target_data = {row[0]: row for row in binding.sidecar.projection.target_records}
    native_targets = {}
    for target_id in participants:
        fields = instance_fields_by_id[target_id]
        source_history_ref = graph.raw_ref(fields['_atomic_target_history'])
        source_history = graph.nodes[source_history_ref][1]
        _need(len(source_history) == 1,
              'source Being does not have exactly one committed Target record')
        source_target_ref = graph.raw_ref(source_history[0])
        source_record = graph.fields(source_target_ref,
            'atomic_publication.TargetIntervalRecord')[1]
        _need(graph.data(source_record['encounter_id']) == data[2]
              and graph.data(source_record['boundary']) == 1,
              'source Target record identity differs from imported boundary')
        target_ref = graph.raw_ref(source_record['state'])
        target_fields = graph.fields(target_ref, 'action_settlement.TargetCandidate')[1]
        target = TargetCandidate(**{key: graph.value(value)
                                    for key, value in target_fields.items()})
        _need(_value(target) == target_data[target_id][3]
              and target.target_id == target_id and target.category == 'being',
              'materialized native Target differs from its exact committed record')
        record = TargetIntervalRecord(data[2], 1, target)
        native_beings[target_id]._atomic_target_history = [record]
        native_targets[target_id] = record

    module_rng_before = random.getstate()
    rng_owner = RNGCursor(rng_state)
    _need(rng_owner.state == rng_state and random.getstate() == module_rng_before,
          'native movement reconstruction changed process RNG')
    from encounter import Encounter, _QuarantinedPostBoundaryPlan
    awareness = graph.data(encounter_fields['awareness'])
    awareness_rows = tuple((key, tuple(sorted(value)))
                           for key, value in sorted(awareness.items()))
    plan = _QuarantinedPostBoundaryPlan(native_universe, data[2], 0, 1,
        graph.data(encounter_fields['difficulty_class']),
        graph.data(encounter_fields['name']), graph.data(encounter_fields['event_type']),
        graph.data(encounter_fields['location']),
        graph.data(encounter_fields['parent_event_id']),
        graph.data(encounter_fields['end_time']),
        graph.data(encounter_fields['initiated']), tuple(participants),
        awareness_rows, rng_owner)
    try:
        native_encounter = Encounter._construct_quarantined_post_boundary(plan)
    except (TypeError, ValueError) as exc:
        raise IdentityBindingRejected(f'native Encounter shell construction refused: {exc}') from exc
    activation_ref = graph.raw_ref(encounter_fields['arena_movement_activation'])
    activation = graph.native(activation_ref)
    native_encounter.arena_activation_enabled = True
    native_encounter.arena_movement_activation = activation
    _need(native_encounter.initiated is True and native_encounter.arena_activation is None
          and native_encounter.initiation is None,
          'native movement activation phase is inconsistent')

    source_history_ref = graph.raw_ref(encounter_fields['_atomic_interval_history'])
    source_history = graph.nodes[source_history_ref][1]
    _need(len(source_history) == 1,
          'native movement import requires one recorded PublishedInterval')
    source_receipt_ref = graph.raw_ref(source_history[0])
    source_receipt_fields = graph.fields(source_receipt_ref,
        'atomic_publication.PublishedInterval')[1]
    _need(graph.data(source_receipt_fields['encounter_id']) == data[2]
          and graph.data(source_receipt_fields['boundary']) == 1
          and not graph.data(source_receipt_fields['action_ids'])
          and not graph.data(source_receipt_fields['effect_ids'])
          and graph.data(source_receipt_fields['committed']) is True
          and not graph.data(source_receipt_fields['notification_intents']),
          'source receipt is outside the exact Action-free movement contract')
    source_inspection_ref = graph.raw_ref(source_receipt_fields['inspection'])
    meta_fields = graph.fields(source_inspection_ref,
        'encounter_inspection.CommittedBoundaryRecord')[1]
    _need(set(meta_fields) == {'start', 'end', 'entities', 'target_anchors', 'actions',
          'action_anchors', 'effects', 'objective', 'objective_use', 'recipients',
          'starts', 'participants', 'schedule', 'projectile_states'}
          and meta_fields['target_anchors'] == ('derived-rebuild-required', 'target_anchors')
          and meta_fields['action_anchors'] == ('derived-rebuild-required', 'action_anchors'),
          'source receipt does not use the strict native anchor-rebuild markers')
    from encounter_inspection import CommittedBoundaryRecord
    source_inspection = CommittedBoundaryRecord(
        graph.data(meta_fields['start']), graph.data(meta_fields['end']),
        graph.mapping(meta_fields['entities'], native_values=True), {},
        graph.mapping(meta_fields['actions']), {}, graph.mapping(meta_fields['effects']),
        graph.mapping(meta_fields['objective']), graph.data(meta_fields['objective_use']),
        graph.mapping(meta_fields['recipients']), graph.data(meta_fields['starts']),
        graph.data(meta_fields['participants']), graph.value(meta_fields['schedule']),
        graph.mapping(meta_fields['projectile_states']))
    _need(set(source_inspection.participants) == set(participants)
          and set(source_inspection.entities) == set(participants)
          and not source_inspection.actions and not source_inspection.effects
          and not source_inspection.objective and not source_inspection.recipients
          and not source_inspection.target_anchors
          and not source_inspection.action_anchors,
          'stored committed inspection data has unsupported Action/Target coverage')
    return _QuarantinedMovementNativeGraph(
        native_universe, native_encounter, tuple(sorted(native_beings.items())),
        tuple(sorted(native_targets.items())),
        tuple(sorted((key, graph.data(value)) for key, value in source_receipt_fields.items()
                     if key != 'inspection')), source_inspection,
        rng_owner, binding.sidecar.projection)


# The legacy symbol now calls the Run-only binder; Spot projection data is
# rejected by the same strict Run projection validator.
bind_quarantined_spot_boundary = bind_quarantined_run_boundary
