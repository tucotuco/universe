"""Quarantined reconstruction of the zero-boundary native Run/Spot subset.

This is a developer/test adapter for already decoded wire data. It is not a
load/restore API and never authenticates bytes or issues committed receipts.
"""
from dataclasses import dataclass
from copy import deepcopy
import json
import math
import random
from weakref import WeakKeyDictionary

from checkpoint_wire import DecodedRunSpotWire, WireRejected, encode_detached_run_spot_data
from checkpoint_views import (NativeActionInspection, NativeBeingInspection,
    QuarantinedReconstructionView, freeze_inspection_value)


RECONSTRUCTION_SCHEMA = 'universe.quarantined-run-spot-reconstruction/1'


class ReconstructionRejected(ValueError):
    """Untrusted wire data is outside the closed reconstruction subset."""


@dataclass(frozen=True, eq=False)
class QuarantinedReconstruction:
    """Public result: detached inspection only, with native graph held privately."""
    schema: str
    view: QuarantinedReconstructionView
    quarantined: bool = True

    @property
    def logical_ids(self):
        """All reconstructed Object logical IDs, detached as a tuple."""
        return self.view.logical_ids


# The weak-key store owns native reconstructed objects only while the public
# result is alive. Raw graph references are deliberately absent from the result
# object and all documented inspection values.
_NATIVE_GRAPHS = WeakKeyDictionary()


_SUPPORTED_TAGS = frozenset({
    'universe.Universe', 'library.Library', 'being.BeingDictionary',
    'skill.SkillDictionary', 'being.BeingDefinition', 'being.BeingInstance',
    'encounter.Encounter', 'encounter.EncounterInitiation',
    'encounter.ArenaActionActivation', 'encounter.ArenaMovementActivation',
    'event.Event', 'action_choice.ChoiceBook',
    'object.ObjectRegistry', 'actiondictionary.ActionDictionary',
    'armor.ArmorDictionary', 'object.ObjectDictionary', 'weapon.WeaponDictionary',
    'object.ObjectDefinition', 'object.ObjectInstance',
    'weapon.WeaponDefinition', 'weapon.WeaponInstance',
    'armor.ArmorDefinition', 'armor.ArmorInstance',
    'abilities.Abilities', 'speeds.Speed',
    'skill.Skills', 'states.States', 'strategy.Strategy', 'exertion.Exertion',
    'physical_fatigue.PhysicalFatigueState', 'spatial.state.CartesianPosition',
    'spatial.state.SpatialState', 'spatial.geometry.Sphere',
    'spatial.occlusion.VisualOcclusion', 'activities.RunAction',
    'activities.SpotAction', 'action_choice.ChoiceMember',
    'action_choice.ChoiceView', 'action_choice._Accepted',
    'scheduling.PreparedSchedule', 'observer_proposals.ObserverProjection',
    'frozen_practice.PracticeProjection', 'frozen_practice.CandidatePracticeUse',
    'frozen_practice.CandidateSkillTransition', 'experience.SkillUse',
    'experience.BatchSkillUse', 'action_evaluation.IdentifiedEffect',
    'action_evaluation.EffectIdentity', 'action_evaluation.AwarenessEffect',
    'action_evaluation.PracticeEffect', 'observer_proposals.LifecycleEffect',
    'observer_proposals.ActionOutcomeEffect',
    'action_settlement.TargetCandidate',
    'encounter_inspection.CommittedBoundaryRecord',
    'encounter_inspection.EntityInspection',
    'interval_staging.QueueProjection',
    'arena_perception.ArenaPerceptionEvidence',
    'arena_perception.ArenaPerceptionLedger',
})


def _need(test, message):
    if not test:
        raise ReconstructionRejected(message)


def _unoccupied_template_hands(body_parts):
    """Allow only explicit empty native hand slots in the closed initial subset."""
    return (type(body_parts) is dict
            and set(body_parts) <= {'left hand', 'right hand'}
            and all(value is None for value in body_parts.values()))


def _sections(state):
    _need(type(state) is tuple and state and state[0] == 'checkpoint-inventory',
          'unsupported inventory body')
    rows = state[1:]
    _need(all(type(row) is tuple and len(row) >= 2 for row in rows),
          'malformed inventory section')
    result = {row[0]: row[1:] for row in rows}
    _need(len(result) == len(rows), 'duplicate inventory sections')
    return result


def _tagged(value):
    _need(type(value) is tuple and value, 'malformed tagged native value')
    tag = value[0]
    if tag == 'null':
        _need(len(value) == 1, 'malformed null'); return None
    if tag == 'boolean':
        _need(len(value) == 2 and type(value[1]) is bool, 'malformed boolean'); return value[1]
    if tag == 'string':
        _need(len(value) == 2 and type(value[1]) is str, 'malformed string'); return value[1]
    if tag == 'integer':
        _need(len(value) == 2 and type(value[1]) is str, 'malformed integer')
        number = int(value[1]); _need(str(number) == value[1], 'noncanonical integer'); return number
    if tag == 'binary64':
        _need(len(value) == 2 and type(value[1]) is str, 'malformed float')
        number = float.fromhex(value[1]); _need(math.isfinite(number) and number.hex() == value[1], 'noncanonical float'); return number
    raise ReconstructionRejected('expected a scalar tagged value')


def _rng_data(value):
    if type(value) is tuple and value and value[0] == 'tuple':
        return tuple(_rng_data(item) for item in value[1])
    return _tagged(value)


class _Graph:
    def __init__(self, nodes):
        self.nodes = {row[0]: (row[1], row[2]) for row in nodes}
        _need(len(self.nodes) == len(nodes), 'duplicate native logical node IDs')
        self.cache = {}

    def raw_ref(self, value):
        _need(type(value) is tuple and len(value) == 2 and value[0] == 'reference',
              'expected native logical reference')
        ref = value[1]
        _need(ref in self.nodes, 'dangling native logical reference')
        return ref

    def fields(self, ref, expected=None):
        tag, content = self.nodes[ref]
        if expected is not None:
            _need(tag == expected, 'logical reference has an incompatible native type')
        _need(type(content) is tuple and all(type(row) is tuple and len(row) == 2 for row in content),
              'malformed native field record')
        fields = dict(content)
        _need(len(fields) == len(content), 'duplicate native field')
        return tag, fields

    def data(self, value):
        if type(value) is not tuple or not value:
            raise ReconstructionRejected('malformed inventory value')
        tag = value[0]
        if tag in ('null', 'boolean', 'string', 'integer', 'binary64'):
            return _tagged(value)
        if tag == 'reference':
            ref = self.raw_ref(value)
            node_tag, content = self.nodes[ref]
            _need(node_tag in ('ordered-map', 'list', 'tuple', 'set', 'frozenset'),
                  'unexpected native object in data-only mapping')
            if ref in self.cache:
                return self.cache[ref]
            if node_tag == 'ordered-map':
                result = {}; self.cache[ref] = result
                for key, item in content:
                    result[self.data(key)] = self.data(item)
                return result
            if node_tag == 'list':
                result = []; self.cache[ref] = result
                result.extend(self.data(item) for item in content); return result
            if node_tag in ('set', 'frozenset'):
                values = (self.data(item) for item in content)
                result = set(values) if node_tag == 'set' else frozenset(values)
                self.cache[ref] = result
                return result
            result = tuple(self.data(item) for item in content)
            self.cache[ref] = result; return result
        raise ReconstructionRejected('unsupported encoded native data value')

    def mapping(self, value, *, native_values=False):
        ref = self.raw_ref(value)
        _need(self.nodes[ref][0] == 'ordered-map', 'expected native ordered-map reference')
        result = {}
        for key, item in self.nodes[ref][1]:
            decoded_key = self.data(key)
            result[decoded_key] = self.value(item) if native_values else self.data(item)
        return result

    def raw_mapping(self, value):
        ref = self.raw_ref(value)
        _need(self.nodes[ref][0] == 'ordered-map', 'expected native ordered-map reference')
        result = {}
        for key, item in self.nodes[ref][1]:
            decoded_key = self.data(key)
            result[decoded_key] = item
        return result

    def native(self, ref):
        if ref in self.cache:
            return self.cache[ref]
        tag, raw = self.fields(ref)
        _need(tag in _SUPPORTED_TAGS, f'unsupported native reconstruction type: {tag}')
        values = {key: self.value(value) for key, value in raw.items()}
        from abilities import Abilities
        from being import BeingDefinition
        from object import ObjectDefinition, ObjectInstance
        from weapon import WeaponDefinition, WeaponInstance
        from armor import ArmorDefinition, ArmorInstance
        from exertion import Exertion
        from physical_fatigue import PhysicalFatigueState
        from spatial.geometry import Sphere
        from spatial.occlusion import VisualOcclusion
        from spatial.state import CartesianPosition, SpatialState
        from speeds import Speed
        from states import States
        from strategy import Strategy
        from skill import Skills
        from observer_proposals import ObserverProjection
        from frozen_practice import (PracticeProjection, CandidatePracticeUse,
                                     CandidateSkillTransition)
        from experience import SkillUse, BatchSkillUse
        from action_evaluation import (IdentifiedEffect, EffectIdentity,
                                       AwarenessEffect, PracticeEffect)
        from observer_proposals import LifecycleEffect, ActionOutcomeEffect
        from arena_perception import ArenaPerceptionEvidence, ArenaPerceptionLedger
        if tag == 'abilities.Abilities':
            table = values['abilities']
            names = {'STR': 'strength', 'DEX': 'dexterity', 'CON': 'constitution',
                     'INT': 'intelligence', 'WIS': 'wisdom', 'CHA': 'charisma'}
            _need(set(table) == set(names) | {'FIT'}, 'Ability dictionary has unsupported keys')
            obj = Abilities(**{names[key]: table[key] for key in names})
            if 'FIT' in table: obj.set_ability('FIT', table['FIT'])
        elif tag == 'speeds.Speed': obj = Speed(**values['speeds'])
        elif tag == 'skill.Skills':
            obj = Skills(); obj.skills = values['skills']; obj.weapon_skills = values['weapon_skills']
        elif tag == 'states.States': obj = States(); obj.states = values['states']
        elif tag == 'strategy.Strategy': obj = Strategy(**values)
        elif tag == 'physical_fatigue.PhysicalFatigueState': obj = PhysicalFatigueState(**values)
        elif tag == 'spatial.state.CartesianPosition': obj = CartesianPosition(**values)
        elif tag == 'spatial.state.SpatialState': obj = SpatialState(**values)
        elif tag == 'spatial.geometry.Sphere': obj = Sphere(**values)
        elif tag == 'spatial.occlusion.VisualOcclusion': obj = VisualOcclusion(**values)
        elif tag == 'arena_perception.ArenaPerceptionEvidence':
            obj = ArenaPerceptionEvidence(**values)
        elif tag == 'arena_perception.ArenaPerceptionLedger':
            obj = ArenaPerceptionLedger(values['observer_id'])
            obj.environment = values['environment']
            obj._current = values['_current']
            obj._history = values['_history']
        elif tag == 'exertion.Exertion':
            obj = Exertion(start_time=values['start_time'], end_time=values['end_time'],
                activity_level=values['activity_level'], fatigue_level=values['fatigue_level'],
                load_level=values['load_level'], accumulated_exertion=values['accumulated_exertion'])
            _need(obj.check_periods == values['check_periods'] and obj.fatigue_levels == values['fatigue_levels'],
                  'Exertion definition differs from the native reconstruction contract')
        elif tag == 'being.BeingDefinition':
            obj = BeingDefinition(**values)
        elif tag == 'object.ObjectDefinition':
            obj = ObjectDefinition(**values)
        elif tag == 'weapon.WeaponDefinition':
            attacks=values['attacks']
            obj=WeaponDefinition(values['obj_type'],values['length'],values['weight'],
                values['cost'],values['hardness'],values['hit_points'],
                attacks['R']['t'],attacks['R']['d'],attacks['R']['p'],
                attacks['S']['t'],attacks['S']['d'],attacks['S']['p'],
                attacks['T']['t'],attacks['T']['d'],attacks['T']['p'],
                values['weapon_size'],width=values['width'],height=values['height'],
                is_magical=values['is_magical'],tags=values['tags'],
                weapon_categories=values['weapon_categories'])
            obj.discovery_dc=values['discovery_dc']
        elif tag == 'armor.ArmorDefinition':
            defenses=values['defenses']
            obj=ArmorDefinition(values['obj_type'],values['cost'],values['weight'],
                defenses['B']['h'],defenses['P']['h'],defenses['S']['h'],
                defenses['B']['d'],defenses['P']['d'],defenses['S']['d'],
                values['armor_check_penalty'],values['dexterity_check_penalty'],
                values['hit_points'],length=values['length'],width=values['width'],
                height=values['height'],hardness=values['hardness'],
                is_magical=values['is_magical'],tags=values['tags'],
                weapon_categories=values['weapon_categories'])
            obj.discovery_dc=values['discovery_dc']
        elif tag in ('object.ObjectInstance','weapon.WeaponInstance','armor.ArmorInstance'):
            constructors={'object.ObjectInstance':ObjectInstance,
                'weapon.WeaponInstance':WeaponInstance,'armor.ArmorInstance':ArmorInstance}
            obj=constructors[tag](values['original'],name=values['name'])
            from identifiable import Identifiable
            Identifiable.__init__(obj,values['name'],id=values['id'])
            obj.original=values['original']
            obj.current=values['current']
            for name in ('top_facing','front_facing','parent_container_id'):
                if name in values:setattr(obj,name,values[name])
            for name,setter in (('spatial_state','set_spatial_state'),
                                ('geometry','set_geometry'),
                                ('visual_occlusion','set_visual_occlusion')):
                if name in values:getattr(obj,setter)(values[name])
            if '_atomic_target_history' in values:
                obj._atomic_target_history=values['_atomic_target_history']
        elif tag == 'observer_proposals.ObserverProjection':
            obj = ObserverProjection(**values)
        elif tag == 'frozen_practice.PracticeProjection': obj = PracticeProjection(**values)
        elif tag == 'frozen_practice.CandidatePracticeUse': obj = CandidatePracticeUse(**values)
        elif tag == 'frozen_practice.CandidateSkillTransition': obj = CandidateSkillTransition(**values)
        elif tag == 'experience.SkillUse': obj = SkillUse(**values)
        elif tag == 'experience.BatchSkillUse': obj = BatchSkillUse(**values)
        elif tag == 'action_evaluation.IdentifiedEffect': obj = IdentifiedEffect(**values)
        elif tag == 'action_evaluation.EffectIdentity': obj = EffectIdentity(**values)
        elif tag == 'action_evaluation.AwarenessEffect': obj = AwarenessEffect(**values)
        elif tag == 'action_evaluation.PracticeEffect': obj = PracticeEffect(**values)
        elif tag == 'observer_proposals.LifecycleEffect': obj = LifecycleEffect(**values)
        elif tag == 'observer_proposals.ActionOutcomeEffect': obj = ActionOutcomeEffect(**values)
        elif tag == 'action_settlement.TargetCandidate':
            from action_settlement import TargetCandidate
            obj = TargetCandidate(**values)
        elif tag == 'encounter_inspection.CommittedBoundaryRecord':
            from encounter_inspection import CommittedBoundaryRecord
            obj = CommittedBoundaryRecord(**values)
        elif tag == 'encounter_inspection.EntityInspection':
            from encounter_inspection import EntityInspection
            obj = EntityInspection(**values)
        elif tag == 'interval_staging.QueueProjection':
            from interval_staging import QueueProjection
            obj = QueueProjection(**values)
        elif tag.startswith('encounter.'):
            from encounter import (EncounterInitiation, ArenaActionActivation,
                                   ArenaMovementActivation)
            constructors = {'encounter.EncounterInitiation': EncounterInitiation,
                'encounter.ArenaActionActivation': ArenaActionActivation,
                'encounter.ArenaMovementActivation': ArenaMovementActivation}
            obj = constructors[tag](**values)
        else:
            raise ReconstructionRejected(f'native object requires a root adapter: {tag}')
        actual_fields = object.__getattribute__(obj, '__dict__')
        different = tuple(key for key in set(actual_fields) | set(values)
                          if key not in actual_fields or key not in values or
                          _projection(actual_fields[key]) != _projection(values[key]))
        if different:
            raise ReconstructionRejected(f'native constructor changed captured fields for {tag}: {different}')
        self.cache[ref] = obj
        return obj

    def value(self, value):
        if type(value) is tuple and value and value[0] == 'reference':
            ref = self.raw_ref(value)
            if self.nodes[ref][0] in ('ordered-map', 'list', 'tuple', 'set', 'frozenset'):
                return self.data(value)
            return self.native(ref)
        return self.data(value)


def reconstruct_initial_run_spot(decoded):
    """Build a fresh, quarantined initial graph from strict decoded wire data."""
    _need(type(decoded) is DecodedRunSpotWire, 'strict DecodedRunSpotWire required')
    try:
        # Re-run the strict data encoder's validation. The digest is integrity
        # checking only; compatibility below is an exact local contract check.
        encode_detached_run_spot_data(decoded.envelope_data)
    except (WireRejected, TypeError, ValueError) as exc:
        raise ReconstructionRejected(f'invalid decoded envelope: {exc}') from exc
    data = decoded.envelope_data
    _need(type(data) is tuple and len(data) == 17 and data[0] == 'universe.native-run-spot-checkpoint-envelope/1',
          'unknown envelope schema')
    _need(data[4] == (),
          'committed boundaries are refused: no reviewed quarantine-only native Action/Target '
          'projection exists; native receipt authenticity depends on process-local issuance, '
          'which checkpoint reconstruction must not recreate')
    _need(data[8] == (),
          'committed receipts cannot be reconstructed as native history: authenticity depends on '
          'process-local issuance, which checkpoint reconstruction must not recreate')
    _need(data[12:16] == (True, False, False, False),
          'bounded envelope flags are inconsistent or claim checkpoint readiness')
    from checkpoint_envelope import _RECONSTRUCTION_OBLIGATIONS
    _need(data[11] == _RECONSTRUCTION_OBLIGATIONS,
          'reconstruction obligation contract is unknown')
    _need(type(data[10]) is tuple and
          {row[0] for row in data[10] if type(row) is tuple and row and type(row[0]) is str} ==
          {'semantic_closure_adapter_incomplete', 'bounded_run_spot_closure_verified'},
          'unsupported candidate diagnostics')
    from checkpoint_inventory import _compatibility
    _need(data[3] == _compatibility(), 'runtime/rules compatibility does not match this native adapter')
    sections = _sections(data[5])
    _need(sections.get('readiness') == (False, False, False), 'wire readiness flags must remain false')
    _need(sections.get('host-bindings') == ((),), 'external recipient binding is unsupported')
    _need(sections.get('rng') is not None, 'private RNG state is missing')
    _need(sections.get('rng')[:2] == ('caller_cursor', 'exclusive_encounter'),
          'shared or nonexclusive RNG is unsupported')
    nodes_row = sections.get('nodes')
    _need(type(nodes_row) is tuple and len(nodes_row) == 1 and type(nodes_row[0]) is tuple,
          'native graph nodes are missing')
    nodes = nodes_row[0]
    graph = _Graph(nodes)
    tags = {row[1] for row in nodes}
    _need(tags <= _SUPPORTED_TAGS | {'ordered-map', 'list', 'tuple', 'set'},
          'initial graph includes unsupported native types or definitions')
    _need('encounter.Encounter' in tags and 'being.BeingInstance' in tags,
          'initial native Encounter and participants are required')
    _need(not any(row[1] in ('realization.RealityLedger', 'personal_history.PersonalHistory') for row in nodes),
          'Reality and personal-history reconstruction is unsupported')

    by_tag = {}
    for row in nodes:
        by_tag.setdefault(row[1], []).append(row[0])
    _need(len(by_tag.get('universe.Universe', ())) == 1
          and len(by_tag.get('encounter.Encounter', ())) == 1,
          'Universe or Encounter identity is missing or ambiguous')
    universe_ref = by_tag['universe.Universe'][0]
    encounter_ref = by_tag['encounter.Encounter'][0]
    _need(universe_ref == ('universe', data[1]) and encounter_ref == ('encounter', data[2]),
          'envelope roots disagree with native logical identities')
    _need(len(by_tag.get('action_choice.ChoiceBook', ())) == 1,
          'ChoiceBook identity is missing or ambiguous')
    _need(len(by_tag.get('event.Event', ())) == 1,
          'initial graph must contain only the native origin Event')
    _preflight_initial_graph(graph, by_tag, data[1], data[2], data[7])

    from library import Library
    from universe import Universe
    from encounter import Encounter
    from being import BeingDefinition, BeingDictionary, BeingInstance
    from skill import SkillDictionary
    from identifiable import Identifiable
    from activities import RunAction, SpotAction
    from strategy import Strategy
    from transactional_progression import enable_transactional_progression

    def one(tag):
        refs = by_tag.get(tag, ())
        _need(len(refs) == 1, f'required native node is missing or ambiguous: {tag}')
        return refs[0]

    def ref_field(ref, field, expected=None):
        fields = graph.fields(ref)[1]
        value = fields.get(field)
        if value is None or value == ('null',):
            return None
        logical = graph.raw_ref(value)
        if expected is not None:
            _need(graph.nodes[logical][0] == expected, f'{field} has an incompatible native reference')
        return logical

    def scalar_field(ref, fields, key):
        _need(key in fields, f'missing required field {key}')
        return graph.data(fields[key])

    # Definitions are rebuilt only from the reviewed Being/Skill dictionaries.
    being_dictionary_ref = one('being.BeingDictionary')
    skill_dictionary_ref = one('skill.SkillDictionary')
    bd_fields = graph.fields(being_dictionary_ref)[1]
    sd_fields = graph.fields(skill_dictionary_ref)[1]
    being_objects = graph.mapping(bd_fields['objects'], native_values=True)
    being_categories = graph.data(bd_fields['object_categories'])
    _need(type(being_objects) is dict and type(being_categories) is dict,
          'Being definition dictionary must use native ordered maps')
    definition_ids = {graph.raw_ref(value) for value in graph.raw_mapping(bd_fields['objects']).values()}
    instance_definition_ids = set()
    for instance_ref in by_tag.get('being.BeingInstance', ()):
        instance_fields = graph.fields(instance_ref, 'being.BeingInstance')[1]
        instance_definition_ids.update(graph.raw_ref(instance_fields[field])
                                       for field in ('original', 'current'))
    _need({ref for ref in graph.nodes if graph.nodes[ref][0] == 'being.BeingDefinition'} ==
          definition_ids | instance_definition_ids,
          'unreferenced or missing Being definition node is outside the closed graph')
    skill_values = graph.data(sd_fields['skills'])
    _need(type(skill_values) is dict and all(type(k) is str and type(v) is dict for k, v in skill_values.items()),
          'Skill definitions are outside the reviewed native dictionary contract')
    rebuilt_beings = {}
    for name, definition in being_objects.items():
        _need(type(name) is str and type(definition) is BeingDefinition,
              'Being dictionary contains a nonnative definition')
        _need(definition.obj_type == name, 'Being definition key and type disagree')
        rebuilt_beings[name] = definition
    native_being_dict = BeingDictionary()
    native_being_dict.objects = rebuilt_beings
    native_being_dict.object_categories = being_categories
    native_skill_dict = SkillDictionary()
    native_skill_dict.skills = skill_values

    # Library construction explicitly skips host configuration loading.
    lib_fields = graph.fields(one('library.Library'))[1]
    library_id = scalar_field(one('library.Library'), lib_fields, 'id')
    library_name = scalar_field(one('library.Library'), lib_fields, 'name')
    _need(type(library_id) is str and library_id, 'invalid Library logical ID')
    native_library = Library(load_definitions=False, name=library_name, id=library_id)
    native_library.being_dictionary = native_being_dict
    native_library.skill_dictionary = native_skill_dict
    from actiondictionary import ActionDictionary
    from armor import ArmorDictionary
    from object import ObjectDictionary
    from weapon import WeaponDictionary
    dictionary_classes = {
        'action_dictionary': ('actiondictionary.ActionDictionary', ActionDictionary),
        'armor_dictionary': ('armor.ArmorDictionary', ArmorDictionary),
        'object_dictionary': ('object.ObjectDictionary', ObjectDictionary),
        'weapon_dictionary': ('weapon.WeaponDictionary', WeaponDictionary),
    }
    for field, (tag, constructor) in dictionary_classes.items():
        dictionary_ref = graph.raw_ref(lib_fields[field])
        _need(graph.nodes[dictionary_ref][0] == tag, f'unsupported Library dependency: {field}')
        native_dictionary = constructor()
        dictionary_fields = graph.fields(dictionary_ref)[1]
        for attr, encoded in dictionary_fields.items():
            value=(graph.mapping(encoded,native_values=True) if attr=='objects'
                   and tag!='actiondictionary.ActionDictionary' else graph.data(encoded))
            setattr(native_dictionary, attr, value)
        if tag=='actiondictionary.ActionDictionary':
            _need(type(native_dictionary.actions) is dict,
                  'native Action catalog did not reconstruct as a data mapping')
        setattr(native_library, field, native_dictionary)

    universe_fields = graph.fields(universe_ref)[1]
    universe_name = scalar_field(universe_ref, universe_fields, 'name')
    _need(scalar_field(universe_ref, universe_fields, 'id') == '0',
          'native Universe constructor contract requires logical ID 0')
    native_world = Universe(name=universe_name, library=native_library)
    _need(native_world.id == data[1], 'Universe constructor produced an incompatible logical identity')

    # Restore fresh Being instances through their native constructors. Their
    # original definitions bind to the Library; current state remains detached.
    registry_ref = ref_field(universe_ref, 'object_registry', 'object.ObjectRegistry')
    registry_fields = graph.fields(registry_ref)[1]
    registry_data = graph.raw_mapping(registry_fields['object_instances'])
    _need(type(registry_data) is dict, 'ObjectRegistry must be a native ordered map')
    start_time = graph.data(graph.fields(encounter_ref)[1]['start_time'])
    being_registry={key:value for key,value in registry_data.items()
        if graph.nodes[graph.raw_ref(value)][0]=='being.BeingInstance'}
    referenced_types=set()
    for raw in being_registry.values():
        instance_fields=graph.fields(graph.raw_ref(raw),'being.BeingInstance')[1]
        original_fields=graph.fields(graph.raw_ref(instance_fields['original']),
                                     'being.BeingDefinition')[1]
        referenced_types.add(graph.data(original_fields['obj_type']))
    _templates, template_refs, definition_kinds = _validate_being_definition_bindings(
        graph, being_registry, {name:graph.raw_mapping(bd_fields['objects'])[name]
                                for name in referenced_types})
    _need(set(registry_data) == {row[0][1] for row in nodes
          if type(row[0]) is tuple and len(row[0]) == 2 and row[0][0] == 'object'},
          'ObjectRegistry keys and logical Object IDs disagree')
    native_objects = {}
    object_to_ref = {row[0][1]: row[0] for row in nodes
                     if type(row[0]) is tuple and len(row[0]) == 2 and row[0][0] == 'object'}
    for object_id, raw_instance in registry_data.items():
        _need(type(object_id) is str and graph.raw_ref(raw_instance) == object_to_ref[object_id],
              'ObjectRegistry entry does not use the reviewed Being reference form')
        instance_ref = object_to_ref[object_id]
        instance_tag, fields = graph.fields(instance_ref)
        if instance_tag in ('object.ObjectInstance','weapon.WeaponInstance','armor.ArmorInstance'):
            instance=graph.native(instance_ref)
            _need(type(instance.id) is str and instance.id==object_id,
                  'native Object logical identity was not preserved')
            native_world.add_object(instance)
            native_objects[object_id]=instance
            continue
        _need(instance_tag == 'being.BeingInstance', 'ObjectRegistry contains an unsupported native Entity')
        _need(graph.data(fields['personal_history']) is None,
              'personal-history reconstruction is unsupported')
        _need(graph.data(fields['skill_use_history']) == [],
              'historical practice and skill-use records are unsupported')
        original_ref = ref_field(instance_ref, 'original', 'being.BeingDefinition')
        current_ref = ref_field(instance_ref, 'current', 'being.BeingDefinition')
        original = _materialize_being_original(
            graph, object_id, fields, rebuilt_beings, template_refs, definition_kinds)
        current = graph.native(current_ref)
        instance = BeingInstance(original, name=scalar_field(instance_ref, fields, 'name'))
        Identifiable.__init__(instance, scalar_field(instance_ref, fields, 'name'), id=object_id)
        instance.current = current
        _need(instance.current is not instance.original, 'current Being state must be detached from definition')
        for field in ('top_facing', 'front_facing', 'parent_container_id', 'physiology_id',
                      'fatigue_level', 'effective_fitness', 'skill_experience',
                      '_skill_practice_baselines', 'possessions', 'weapons'):
            if field in fields:
                setattr(instance, field, graph.value(fields[field]))
        if '_arena_initial_profile' in fields and fields['_arena_initial_profile'] != ('null',):
            profile = graph.value(fields['_arena_initial_profile'])
            from npcgen_arena_adapter import validate_arena_initial_profile_record
            try:
                validate_arena_initial_profile_record(profile)
            except (TypeError, ValueError) as exc:
                raise ReconstructionRejected(f'Arena initial profile refused: {exc}') from exc
            _need(profile['initial_total_experience'] == instance.original.experience,
                  'Arena initial profile XP differs from the reconstructed Being original')
            instance._arena_initial_profile = profile
        if fields.get('_arena_perception_ledger') != ('absent-for-non-Arena',):
            ledger_value=fields.get('_arena_perception_ledger')
            _need(type(ledger_value) is tuple and len(ledger_value)==2
                  and ledger_value[0]=='arena-perception-ledger',
                  'Arena observer evidence has an unsupported checkpoint adapter')
            from checkpoint_arena_perception import decode_arena_perception_ledger
            encoded_ledger=ledger_value[1]
            current_rows=encoded_ledger[3]
            try:
                instance._arena_perception_ledger=decode_arena_perception_ledger(
                    encoded_ledger,observer_id=object_id,
                    entity_ids=tuple(sorted(registry_data)),
                    visible_entity_ids=tuple(row[0] for row in current_rows),
                    boundary=0,time=start_time)
            except (TypeError,ValueError) as exc:
                raise ReconstructionRejected(f'Arena observer evidence refused: {exc}') from exc
        instance.set_hex_facing(graph.data(fields['hex_facing']))
        instance.set_posture(graph.data(fields['_posture']))
        for field, setter in (('spatial_state', 'set_spatial_state'),
                               ('geometry', 'set_geometry'),
                               ('visual_occlusion', 'set_visual_occlusion')):
            value = graph.value(fields[field])
            getattr(instance, setter)(value)
        instance.physical_fatigue = graph.value(fields['physical_fatigue'])
        instance.strategy = graph.value(fields['strategy'])
        instance.exertion = graph.value(fields['exertion'])
        _need(instance.id == object_id, 'Being logical identity was not preserved')
        native_world.add_object(instance)
        native_objects[object_id] = instance

    # Existing source graphs in this subset contain only the origin and target
    # Encounter. Encounter construction creates a fresh ChoiceBook/lock.
    event_history = graph.raw_mapping(graph.fields(universe_ref)[1]['event_history'])
    _need(type(event_history) is dict and set(event_history) == {'0', data[2]},
          'initial event history must contain only origin and selected Encounter')
    origin_ref = graph.raw_ref(event_history['0'])
    _need(graph.nodes[origin_ref][0] == 'event.Event', 'origin Event has an unsupported native type')
    origin_fields = graph.fields(origin_ref)[1]
    _need(scalar_field(origin_ref, origin_fields, 'id') == '0', 'origin Event logical identity mismatch')
    source_origin = native_world.event_history['0']
    _need(source_origin.name == scalar_field(origin_ref, origin_fields, 'name'),
          'origin Event constructor semantics differ from captured state')

    enc_tag, enc_fields = graph.fields(encounter_ref)
    _need(enc_tag == 'encounter.Encounter', 'selected root is not native Encounter')
    start_time = scalar_field(encounter_ref, enc_fields, 'start_time')
    _need(scalar_field(encounter_ref, enc_fields, 'time') == start_time
          and scalar_field(encounter_ref, enc_fields, 'last_processed_boundary') == math.floor(start_time),
          'Encounter is not at its initial uncommitted cursor')
    for field in ('pending_action_list', 'finished_action_list', 'cancelled_action_list',
                  'fatigue_frame_history'):
        _need(graph.data(enc_fields[field]) == [], f'initial Encounter contains historical state: {field}')
    encounter = Encounter(native_world, scalar_field(encounter_ref, enc_fields, 'difficulty_class'),
        start_time, end_time=graph.data(enc_fields['end_time']),
        event_type=graph.data(enc_fields['event_type']), location=graph.data(enc_fields['location']),
        name=scalar_field(encounter_ref, enc_fields, 'name'),
        parent_event_id=graph.data(enc_fields['parent_event_id']), id=data[2],
        initiated=scalar_field(encounter_ref, enc_fields, 'initiated'))
    source_choice_book = graph.raw_ref(enc_fields['_choice_book'])
    _need(graph.nodes[source_choice_book][0] == 'action_choice.ChoiceBook' and
          graph.raw_ref(graph.fields(source_choice_book)[1]['encounter']) == encounter_ref,
          'ChoiceBook/Encounter ownership references are inconsistent')
    for field in ('being_list', 'non_being_object_list', 'awareness',
                  'arena_activation_enabled'):
        setattr(encounter, field, graph.data(enc_fields[field]))
    for field in ('arena_activation','arena_movement_activation','initiation'):
        setattr(encounter, field, graph.value(enc_fields[field]))
    for being_id in encounter.being_list:
        _need(being_id in native_objects, 'Encounter references an unowned Being')
    for field in ('_coordinator_time', '_interval_start'):
        setattr(encounter, field, graph.data(enc_fields[field]))
    native_world.add_event(encounter)
    _need(encounter.id == data[2] and encounter.time == start_time,
          'Encounter native identity/cursor validation failed')

    # Choice support is accepted only after all entities and definitions are
    # ready. The normal ChoiceBook path creates fresh declarations/signatures.
    choices = data[7]
    _need(type(choices) is tuple, 'accepted choices must be a tuple')
    if choices:
        _rebuild_future_choices(graph, choices, native_world, encounter, native_objects)
    source_book_fields = graph.fields(source_choice_book)[1]
    source_counter = graph.data(source_book_fields['_counter'])
    _need(type(source_counter) is int and source_counter >= encounter._choice_book._counter,
          'source scheduling counter cannot be represented after choice reconstruction')
    encounter._choice_book._counter = source_counter

    rng_record = sections['rng']
    rng_state = _rng_data(rng_record[2])
    probe = random.Random()
    try:
        probe.setstate(rng_state)
    except (TypeError, ValueError) as exc:
        raise ReconstructionRejected('private RNG state is not valid native MT19937 state') from exc
    from atomic_publication import RNGCursor
    rng_owner = RNGCursor(rng_state)
    module_rng_before = random.getstate()
    enable_transactional_progression(encounter, quiescent=True, rng_owner=rng_owner)
    _need(rng_owner.state == rng_state and random.getstate() == module_rng_before,
          'RNG ownership changed during isolated graph construction')

    # Quarantine is installed last, after normal constructor validation and safe
    # native choice registration. Entry-point guards reject all gameplay use.
    from transactional_progression import quarantine_reconstruction
    quarantine_reconstruction(encounter)
    for action_id in encounter.pending_action_list:
        action = native_world.get_event_by_id(action_id)
        if action is not None:
            action._checkpoint_quarantined = True

    # Capture public inspection only after construction and quarantine have
    # completed. JSON/native values are copied into a closed recursively
    # immutable tree; no live reference escapes this function.
    being_views = []
    for being_id in encounter.being_list:
        being = native_world.get_object_by_id(being_id)
        _need(being is not None, 'reconstructed Being disappeared before view capture')
        try:
            state = freeze_inspection_value(json.loads(being.to_json()))
        except (TypeError, ValueError) as exc:
            raise ReconstructionRejected(f'Being inspection view is not closed: {exc}') from exc
        position = being.get_position()
        position_value = None if position is None else tuple(position.as_tuple())
        skill_levels = tuple(sorted(being.current.skills.skills.items()))
        skill_experience = tuple(sorted(being.skill_experience.items()))
        being_views.append(NativeBeingInspection(
            being_id, being.name, position_value, being.get_hit_points(),
            (being.physical_fatigue.q, being.physical_fatigue.b),
            being.physiology_id, freeze_inspection_value(skill_levels),
            freeze_inspection_value(skill_experience), state))

    action_views = []
    choice_descriptors = data[7]
    reservations = []
    for descriptor in choice_descriptors:
        choice_id = descriptor[1]
        reservations.extend(descriptor[8])
        for member in descriptor[7]:
            _key, family, action_id, declaration_fields, _target_key, _prepared = member
            fields = dict(declaration_fields)
            def ref_value(name):
                value = fields[name]
                return value[1] if type(value) is tuple and value and value[0] == 'entity' else None
            action_views.append(NativeActionInspection(
                action_id, choice_id, family, ref_value('actor_id'),
                ref_value('target_id'), fields['start_time'], fields['end_time'],
                freeze_inspection_value(declaration_fields)))

    rng_record = sections['rng']
    try:
        rng_view = freeze_inspection_value(rng_owner.state)
    except Exception as exc:
        raise ReconstructionRejected(f'RNG inspection view is not closed: {exc}') from exc
    view = QuarantinedReconstructionView(
        RECONSTRUCTION_SCHEMA, native_world.id, native_world.name, encounter.id,
        encounter.start_time, encounter.end_time, encounter.time,
        encounter.difficulty_class, tuple(sorted(native_objects)),
        tuple(encounter.being_list), tuple(being_views),
        tuple(action_views), freeze_inspection_value(choice_descriptors),
        freeze_inspection_value(tuple(reservations)), rng_record[0], rng_record[1],
        rng_view, True)
    result = QuarantinedReconstruction(RECONSTRUCTION_SCHEMA, view, True)
    _NATIVE_GRAPHS[result] = (native_world, encounter, rng_owner)
    return result


def _admit_pristine_arena_reconstruction(result):
    """Release only a fully checked time-zero Arena into ordinary browser play."""
    if type(result) is not QuarantinedReconstruction or result.quarantined is not True:
        raise ReconstructionRejected('exact quarantined native reconstruction is required')
    native=_NATIVE_GRAPHS.get(result)
    if type(native) is not tuple or len(native)!=3:
        raise ReconstructionRejected('reconstructed native Arena graph is unavailable')
    world,encounter,rng_owner=native
    from transactional_progression import (_BINDINGS,_QUARANTINED,mode_of)
    binding=_BINDINGS.get(id(encounter))
    movement_started=(encounter.initiated is True
        and encounter.arena_movement_activation is not None
        and encounter.arena_activation is None and encounter.initiation is None)
    pristine=(encounter.initiated is False
        and encounter.arena_movement_activation is None
        and encounter.arena_activation is None and encounter.initiation is None)
    if (binding is None or binding.encounter() is not encounter
            or binding.rng_owner is not rng_owner or mode_of(encounter)!='transactional'
            or not encounter.arena_activation_enabled or encounter.time!=encounter.start_time
            or not (pristine or movement_started)
            or encounter.pending_action_list or encounter.finished_action_list
            or encounter.cancelled_action_list or encounter._choice_book._choices
            or encounter.__dict__.get('_atomic_interval_history')):
        raise ReconstructionRejected('only a pristine or time-zero movement-activated native Arena can enter ordinary play')
    # A pristine Encounter still selects transactional mode at real activation.
    # A movement-activated one retains its native cursor binding and accepted
    # plan so its first interval can proceed through Encounter.step normally.
    if pristine:
        _BINDINGS.pop(id(encounter),None)
        object.__getattribute__(encounter,'__dict__').pop('_transactional_mode',None)
    _QUARANTINED.discard(encounter);_QUARANTINED.discard(world)
    object.__getattribute__(encounter,'__dict__').pop('_checkpoint_quarantined',None)
    object.__getattribute__(world,'__dict__').pop('_checkpoint_quarantined',None)
    for value in world.object_registry.object_instances.values():
        _QUARANTINED.discard(value)
        object.__getattribute__(value,'__dict__').pop('_checkpoint_quarantined',None)
    return world,encounter,rng_owner


def _rebuild_future_choices(graph, choices, world, encounter, native_objects):
    """Rebuild only exact accepted Run/Spot descriptors via native ChoiceBook."""
    from activities import RunAction, SpotAction
    from action_choice import ChoiceMember
    from identifiable import Identifiable
    from strategy import Strategy
    expected_ids = []
    for descriptor in choices:
        _need(type(descriptor) is tuple and len(descriptor) == 9,
              'accepted choice descriptor has an unsupported shape')
        _need(descriptor[0] == 'universe.accepted-action-choice/1'
              and descriptor[3] == 'accepted', 'only accepted native choice descriptors are supported')
        choice_id, members = descriptor[1], descriptor[7]
        _need(type(choice_id) is str and type(members) is tuple and members,
              'accepted choice identity or members are invalid')
        actions = []
        for member in members:
            _need(type(member) is tuple and len(member) == 6, 'malformed accepted choice member')
            key, adapter, action_id, fields, target_key, prepared = member
            _need(adapter in ('native.run-action/1', 'native.spot-action/1'),
                  'unsupported accepted Action family')
            values = dict(fields)
            def field(name):
                _need(name in values, f'choice declaration is missing {name}')
                return _descriptor_scalar(values[name])
            actor_id = field('actor_id'); start = field('start_time'); end = field('end_time')
            duration = end - start
            actor = world.get_object_by_id(actor_id)
            _need(actor is not None and encounter.get_being(actor_id) is actor,
                  'accepted Action actor reference is not an Encounter Being')
            if adapter == 'native.run-action/1':
                action = RunAction(world, actor_id, start, duration,
                    field('minimum_distance'), field('practice_experience'))
            else:
                target_id = field('target_id')
                _need(target_id in native_objects and target_id in encounter.being_list,
                      'accepted Spot target reference is not an Encounter Being')
                action = SpotAction(world, actor_id, target_id, start, duration,
                    field('declared_roll'), spotting_conditions=field('spotting_conditions'))
            Identifiable.__init__(action, field('display_name'), id=action_id)
            effort_data = values.get('strategy_effort')
            _need(type(effort_data) is tuple and len(effort_data) == 4,
                  'invalid native Action strategy')
            effort = tuple(_descriptor_scalar(pair[1]) for pair in effort_data)
            _need(tuple(pair[0] for pair in effort_data) ==
                  ('attack', 'defense', 'timing', 'extra_damage'), 'unknown Action strategy fields')
            action.strategy = Strategy(*effort)
            actions.append(ChoiceMember(key, action, target_action_key=target_key))
            expected_ids.append(action_id)
        book = encounter._choice_book
        # The native API generates the draft id from its monotonic counter. Set
        # that counter to the immediately preceding captured ordinal, then let
        # normal proposal, validation and acceptance regenerate fresh signatures.
        prefix = encounter.id + '/draft/'
        _need(choice_id.startswith(prefix) and choice_id[len(prefix):].isdigit(),
              'choice ID is outside the native draft identity contract')
        ordinal = int(choice_id[len(prefix):])
        _need(ordinal > book._counter, 'accepted choice IDs are duplicate or out of order')
        book._counter = ordinal - 1
        view = encounter.schedule_choice(tuple(actions))
        _need(view.id == choice_id and view.action_ids == tuple(a.action.id for a in actions),
              'native choice acceptance did not preserve logical choice references')
        from checkpoint_choices import describe_accepted_choice
        rebuilt = describe_accepted_choice(world, encounter, choice_id).to_data()
        _need(rebuilt == descriptor, 'rebuilt native scheduling descriptor differs from captured declaration')
    _need(tuple(expected_ids) == tuple(aid for choice in choices for aid in choice[5]),
          'accepted Action member ordering differs from its logical declarations')


def _descriptor_scalar(value):
    _need(type(value) is tuple and value, 'malformed choice scalar')
    tag = value[0]
    if tag == 'null': _need(len(value) == 1, 'malformed choice null'); return None
    _need(len(value) == 2, 'malformed choice scalar')
    content = value[1]
    if tag == 'string': _need(type(content) is str, 'malformed choice string'); return content
    if tag in ('entity', 'universe', 'action-id'):
        _need(type(content) is str and content, 'malformed logical choice reference'); return content
    if tag == 'boolean': _need(type(content) is bool, 'malformed choice boolean'); return content
    if tag == 'integer':
        number = int(content); _need(str(number) == content, 'noncanonical choice integer'); return number
    if tag == 'binary64':
        number = float.fromhex(content); _need(math.isfinite(number) and number.hex() == content,
            'noncanonical choice float'); return number
    if tag == 'strings':
        _need(type(content) is tuple and all(type(item) is str for item in content),
              'malformed Spotting condition tuple')
        return content
    raise ReconstructionRejected('unsupported choice declaration scalar')


def _projection(value):
    """Detached exact comparison of reviewed constructor data, without reprs."""
    if value is None or type(value) in (str, bool, int, float):
        return (type(value).__name__, value.hex() if type(value) is float else value)
    if type(value) is dict:
        return ('dict', tuple((_projection(k), _projection(v)) for k, v in value.items()))
    if type(value) in (list, tuple):
        return (type(value).__name__, tuple(_projection(v) for v in value))
    if type(value) in (set, frozenset):
        return (type(value).__name__, tuple(sorted((_projection(v) for v in value), key=str)))
    data = object.__getattribute__(value, '__dict__')
    _need(type(data) is dict, 'native adapter projection found opaque storage')
    return (type(value).__module__ + '.' + type(value).__name__,
            tuple((key, _projection(item)) for key, item in sorted(data.items())))


_INDIVIDUAL_BEING_FIELDS = (
    'race', 'length', 'weight', 'hit_points', 'experience', 'abilities', 'skills')


def _validate_being_definition_bindings(graph, registry, definition_rows):
    """Validate canonical or exclusive template-derived originals in a closed graph."""
    from being import BeingDefinition
    from checkpoint_adapters import NativeInventory

    templates = {}
    template_refs = {}
    for name, raw_ref in definition_rows.items():
        _need(type(name) is str and name.strip(), 'Being definition key is invalid')
        ref = graph.raw_ref(raw_ref)
        definition = graph.native(ref)
        _need(type(definition) is BeingDefinition and definition.obj_type == name,
              'Being template key/type relationship is invalid')
        templates[name] = definition
        template_refs[name] = ref

    inventory = object.__new__(NativeInventory)
    mutable_owners = {}
    for name, template in templates.items():
        try:
            inventory._validate_being_definition(template)
            inventory._closed_definition_value(template, owner=('definition', name),
                                               mutable_owners=mutable_owners)
        except ValueError as exc:
            raise ReconstructionRejected(f'Being type template is not closed native data: {exc}') from exc
    definition_ids = {id(value): key for key, value in templates.items()}
    individualized_ids = set()
    kinds = {}
    referenced_types = set()
    for logical_id, raw_instance in registry.items():
        _need(type(logical_id) is str and logical_id,
              'Being definition owner identity is invalid')
        instance_ref = graph.raw_ref(raw_instance)
        fields = graph.fields(instance_ref, 'being.BeingInstance')[1]
        _need(graph.data(fields['id']) == logical_id,
              'Being definition owner differs from its ObjectRegistry identity')
        original_ref = graph.raw_ref(fields['original'])
        original_fields = graph.fields(original_ref, 'being.BeingDefinition')[1]
        type_name = graph.data(original_fields['obj_type'])
        _need(type(type_name) is str and type_name in templates,
              'Being original has no matching registered type template')
        referenced_types.add(type_name)
        original = graph.native(original_ref)
        try:
            kinds[logical_id] = inventory._validate_being_original_definition(
                original, entity_id=logical_id, definitions=templates,
                definition_ids=definition_ids,
                individualized_original_ids=individualized_ids,
                mutable_owners=mutable_owners)
        except ValueError as exc:
            raise ReconstructionRejected(f'Being original/template binding refused: {exc}') from exc

        current_ref = graph.raw_ref(fields['current'])
        _need(current_ref != original_ref,
              'Being current definition aliases its original definition')
        current = graph.native(current_ref)
        _need(type(current) is BeingDefinition and current.obj_type == type_name,
              'Being current definition type differs from its original')
        try:
            inventory._closed_definition_value(
                current, owner=('being-current', logical_id),
                mutable_owners=mutable_owners)
        except ValueError as exc:
            raise ReconstructionRejected(f'Being current definition ownership refused: {exc}') from exc

    _need(referenced_types == set(templates),
          'BeingDictionary contains definitions outside the selected Being types')
    return templates, template_refs, kinds


def _materialize_being_original(graph, logical_id, instance_fields,
                                templates, template_refs, definition_kinds):
    """Rebuild one individualized original from its registered template and closed values."""
    from being import BeingDefinition

    original_ref = graph.raw_ref(instance_fields['original'])
    original_fields = graph.fields(original_ref, 'being.BeingDefinition')[1]
    type_name = graph.data(original_fields['obj_type'])
    template = templates[type_name]
    if definition_kinds[logical_id] == 'library-template':
        _need(original_ref == template_refs[type_name],
              'canonical Being original does not use its registered template identity')
        return template

    _need(definition_kinds[logical_id] == 'individualized-native-template',
          'Being original has an unsupported materialization kind')
    source = graph.native(original_ref)
    _need(type(source) is BeingDefinition and source.obj_type == type_name,
          'individualized Being original has an invalid native type')
    result = template.copy()
    for name in _INDIVIDUAL_BEING_FIELDS:
        value = getattr(source, name)
        setattr(result, name, deepcopy(value))
    _need(_projection(result) == _projection(source),
          'materialized Being original differs from its closed individualized definition')
    _need(result is not template and result.abilities is not template.abilities
          and result.skills is not template.skills,
          'individualized Being original aliases mutable template values')
    return result


def _preflight_initial_graph(graph, by_tag, universe_id, encounter_id, choices):
    """Reject unsupported state before any native destination is allocated."""
    def fields(tag):
        refs = by_tag.get(tag, ())
        _need(len(refs) == 1, f'required native node is missing or ambiguous: {tag}')
        return graph.fields(refs[0])[1]

    universe_fields = fields('universe.Universe')
    _need(graph.data(universe_fields['id']) == universe_id == '0',
          'Universe logical identity is unsupported by its native constructor')
    library_ref = graph.raw_ref(universe_fields['library'])
    library_fields = graph.fields(library_ref, 'library.Library')[1]
    for name in ('action_dictionary', 'armor_dictionary', 'object_dictionary', 'weapon_dictionary'):
        ref = graph.raw_ref(library_fields[name])
        tag, values = graph.fields(ref)
        _need(tag in _SUPPORTED_TAGS, f'unsupported Library definition adapter: {tag}')
        if tag == 'actiondictionary.ActionDictionary':
            actions=graph.data(values['actions'])
            _need(type(actions) is dict and all(type(key) is str and key
                and type(row) is dict and tuple(row)==('target_type','required_skill','is_melee')
                and type(row['target_type']) is str and type(row['required_skill']) is str
                and row['is_melee'] in ('True','False') for key,row in actions.items()),
                'native Action catalog is not in the closed Library data contract')
        else:
            rows=graph.raw_mapping(values['objects'])
            categories=graph.data(values['object_categories'])
            expected={'armor_dictionary':('armor.ArmorDefinition','armor.ArmorInstance'),
                      'weapon_dictionary':('weapon.WeaponDefinition','weapon.WeaponInstance'),
                      'object_dictionary':('object.ObjectDefinition','object.ObjectInstance')}[name]
            _need(type(categories) is dict and all(type(key) is str for key in categories),
                  f'{name} categories are not closed native data')
            for key, raw in rows.items():
                definition_ref=graph.raw_ref(raw)
                definition_tag,definition_fields=graph.fields(definition_ref)
                _need(type(key) is str and key and definition_tag==expected[0]
                      and graph.data(definition_fields['obj_type'])==key,
                      f'{name} has a mismatched native definition identity')
                graph.native(definition_ref)

    event_history = graph.raw_mapping(universe_fields['event_history'])
    _need(set(event_history) == {'0', encounter_id},
          'initial Universe event history must contain only origin and selected Encounter')
    origin_ref = graph.raw_ref(event_history['0'])
    encounter_ref = graph.raw_ref(event_history[encounter_id])
    _need(graph.nodes[origin_ref][0] == 'event.Event' and
          graph.nodes[encounter_ref][0] == 'encounter.Encounter',
          'Universe event history has unsupported or mismatched event references')
    _need(graph.data(graph.fields(origin_ref)[1]['id']) == '0' and
          graph.raw_ref(graph.fields(origin_ref)[1]['universe']) == ('universe', universe_id),
          'origin Event identity or Universe ownership is inconsistent')
    _need(graph.raw_ref(graph.fields(encounter_ref)[1]['universe']) == ('universe', universe_id),
          'Encounter belongs to a different Universe')
    choice_books_value = universe_fields['_choice_books']
    choice_books_ref = graph.raw_ref(choice_books_value)
    _need(graph.nodes[choice_books_ref][0] == 'list' and
          len(graph.nodes[choice_books_ref][1]) == 1,
          'exactly one native ChoiceBook must own the Encounter')
    choice_book_ref = graph.raw_ref(graph.nodes[choice_books_ref][1][0])
    _need(graph.nodes[choice_book_ref][0] == 'action_choice.ChoiceBook' and
          graph.raw_ref(graph.fields(choice_book_ref)[1]['encounter']) == encounter_ref and
          graph.raw_ref(graph.fields(encounter_ref)[1]['_choice_book']) == choice_book_ref,
          'ChoiceBook ownership aliases are inconsistent')

    registry_ref = graph.raw_ref(universe_fields['object_registry'])
    registry_fields = graph.fields(registry_ref, 'object.ObjectRegistry')[1]
    registry = graph.raw_mapping(registry_fields['object_instances'])
    native_entity_tags=('being.BeingInstance','object.ObjectInstance',
                        'weapon.WeaponInstance','armor.ArmorInstance')
    object_refs = {ref[1]: ref for tag in native_entity_tags
                   for ref in by_tag.get(tag, ())
                   if type(ref) is tuple and len(ref) == 2 and ref[0] == 'object'}
    _need(set(registry) == set(object_refs), 'ObjectRegistry contains unsupported entity families')
    being_dictionary_ref = graph.raw_ref(library_fields['being_dictionary'])
    being_dictionary_fields = graph.fields(being_dictionary_ref, 'being.BeingDictionary')[1]
    definitions_encoded = graph.raw_mapping(being_dictionary_fields['objects'])
    being_registry={logical_id:encoded for logical_id,encoded in registry.items()
        if graph.nodes[graph.raw_ref(encoded)][0]=='being.BeingInstance'}
    used_definition_names=set()
    for encoded in being_registry.values():
        instance_fields=graph.fields(graph.raw_ref(encoded),'being.BeingInstance')[1]
        original_fields=graph.fields(graph.raw_ref(instance_fields['original']),
                                     'being.BeingDefinition')[1]
        used_definition_names.add(graph.data(original_fields['obj_type']))
    _templates, _template_refs, _definition_kinds = _validate_being_definition_bindings(
        graph, being_registry, {name:definitions_encoded[name] for name in used_definition_names})
    for logical_id, encoded_ref in registry.items():
        ref = graph.raw_ref(encoded_ref)
        _need(ref == object_refs[logical_id], 'ObjectRegistry logical identity mismatch')
        entity_tag,values = graph.fields(ref)
        if entity_tag in ('object.ObjectInstance','weapon.WeaponInstance','armor.ArmorInstance'):
            _need(graph.data(values['id'])==logical_id
                  and graph.data(values['type'])==entity_tag.rsplit('.',1)[1],
                  'Object logical identity or native type field is inconsistent')
            continue
        _need(entity_tag=='being.BeingInstance','unsupported registered native Entity family')
        values = graph.fields(ref, 'being.BeingInstance')[1]
        _need(graph.data(values['id']) == logical_id and
              graph.data(values['type']) == 'BeingInstance',
              'Being logical identity or native type field is inconsistent')
        facing = graph.data(values['hex_facing'])
        _need(facing is None or type(facing) is int and 0 <= facing < 12,
              'Being hex facing must be null or an integer from 0 through 11')
        posture = graph.data(values['_posture'])
        _need(posture is None or type(posture) is str
              and posture in ('standing', 'crouching', 'lying'),
              'Being posture must be unknown or a supported posture string')
        current_fields = graph.fields(graph.raw_ref(values['current']), 'being.BeingDefinition')[1]
        states_fields = graph.fields(graph.raw_ref(current_fields['states']), 'states.States')[1]
        legacy_states = graph.data(states_fields['states'])
        _need(type(legacy_states) is dict, 'Being legacy state dictionary is malformed')
        legacy_prone = legacy_states.get('prone')
        _need(legacy_prone is None or type(legacy_prone) is bool,
              'legacy prone state must be an explicit Boolean or unknown')
        _need(legacy_prone is not True or posture in (None, 'lying'),
              'legacy prone state conflicts with standing/crouching posture')
        _need(graph.data(values['personal_history']) is None,
              'personal-history reconstruction is unsupported')
        for name in ('skill_use_history', 'weapons'):
            _need(graph.data(values[name]) == [],
                  f'unsupported initial ownership/history state: {name}')
        possessions=graph.data(values['possessions'])
        _need(type(possessions) is list and all(item in object_refs for item in possessions)
              and len(possessions)==len(set(possessions)),
              'initial Being possession references are malformed')
        _need(graph.data(values['parent_container_id']) is None,
              'contained Being references are outside the initial subset')
        _need(graph.data(values['physiology_id']) is None,
              'external physiology/profile bindings are unsupported')
        for def_field in ('original', 'current'):
            definition_ref = graph.raw_ref(values[def_field])
            definition_fields = graph.fields(definition_ref, 'being.BeingDefinition')[1]
            _need(graph.data(definition_fields['physiology_id']) is None,
                  'Being definition has an unsupported physiology/profile binding')
            _need(_unoccupied_template_hands(graph.data(definition_fields['body_parts'])) and
                  graph.data(definition_fields['armor_id']) is None,
                  'equipment ownership is outside the initial subset; only empty native hand slots are supported')
        _need(graph.raw_ref(values['current']) != graph.raw_ref(values['original']),
              'Being current state aliases its original definition')

    encounter_fields = fields('encounter.Encounter')
    arena_enabled = graph.data(encounter_fields['arena_activation_enabled'])
    _need(type(arena_enabled) is bool,
          'Arena activation-enabled state is not a native Boolean')
    _need(encounter_fields['arena_activation'] == ('null',),
          'Action-activated Arena Encounter is outside the initial reconstruction path')
    _need(encounter_fields['initiation'] == ('null',),
          'target-directed Encounter initiation is outside the bounded checkpoint subset')
    movement_activation_value=encounter_fields['arena_movement_activation']
    movement_activation=(None if movement_activation_value == ('null',)
                         else graph.value(movement_activation_value))
    if movement_activation is not None:
        from encounter import ArenaMovementActivation
        _need(type(movement_activation) is ArenaMovementActivation
              and movement_activation.encounter_id == encounter_id
              and movement_activation.actor_id in graph.data(encounter_fields['being_list'])
              and movement_activation.time == graph.data(encounter_fields['start_time'])
              and movement_activation.activation_kind == 'first_player_movement'
              and type(movement_activation.movement_decision_id) is str
              and movement_activation.movement_decision_id,
              'movement activation record differs from its native Arena identity')
    if arena_enabled:
        _need(graph.data(encounter_fields['initiated']) is (movement_activation is not None)
              and encounter_fields['arena_activation'] == ('null',)
              and encounter_fields['initiation'] == ('null',),
              'initial Arena activation fields are inconsistent')
    _need(graph.data(encounter_fields['id']) == encounter_id,
          'Encounter logical identity mismatch')
    start = graph.data(encounter_fields['start_time'])
    _need(graph.data(encounter_fields['time']) == start and
          graph.data(encounter_fields['last_processed_boundary']) == math.floor(start),
          'Encounter is not at its initial cursor')
    for name in ('pending_action_list', 'finished_action_list', 'cancelled_action_list',
                 'fatigue_frame_history'):
        _need(graph.data(encounter_fields[name]) == [],
              f'historical Encounter field is unsupported: {name}')
    entity_ids = set(registry)
    being_ids=graph.data(encounter_fields['being_list'])
    object_ids=graph.data(encounter_fields['non_being_object_list'])
    _need(type(being_ids) is list and len(being_ids)==len(set(being_ids))
          and set(being_ids)<=entity_ids
          and all(graph.nodes[graph.raw_ref(registry[being_id])][0]=='being.BeingInstance'
                  for being_id in being_ids),
          'Encounter contains a dangling or non-Being participant reference')
    _need(type(object_ids) is list and len(object_ids)==len(set(object_ids))
          and set(object_ids)<=entity_ids-set(being_ids)
          and all(graph.nodes[graph.raw_ref(registry[object_id])][0] in
                  ('object.ObjectInstance','weapon.WeaponInstance','armor.ArmorInstance')
                  for object_id in object_ids),
          'Encounter contains a dangling or unsupported Object reference')
    awareness = graph.data(encounter_fields['awareness'])
    _need(type(awareness) is dict and set(awareness) <= entity_ids and
          all(type(targets) is set and targets <= entity_ids for targets in awareness.values()),
          'Encounter awareness has dangling or unsupported logical references')
    choice_map = graph.raw_mapping(graph.fields(choice_book_ref)[1]['_choices'])
    _need(set(choice_map) == {choice[1] for choice in choices},
          'accepted ChoiceBook records and portable descriptors disagree')
    for choice_id, encoded_record in choice_map.items():
        record_ref = graph.raw_ref(encoded_record)
        _need(graph.nodes[record_ref][0] == 'action_choice._Accepted',
              'ChoiceBook contains an unsupported record')
        view_ref = graph.raw_ref(graph.fields(record_ref)[1]['view'])
        _need(graph.nodes[view_ref][0] == 'action_choice.ChoiceView' and
              graph.data(graph.fields(view_ref)[1]['id']) == choice_id,
              'accepted ChoiceBook view identity mismatch')
    described_actions = {member[2]: member[1] for choice in choices for member in choice[7]}
    native_actions = {ref[1]: graph.nodes[ref][0] for ref in graph.nodes
                      if type(ref) is tuple and len(ref) == 2 and ref[0] == 'event' and
                      graph.nodes[ref][0] in ('activities.RunAction', 'activities.SpotAction')}
    _need(set(native_actions) == set(described_actions),
          'native future Action nodes and portable choice descriptors disagree')
    for action_id, adapter in described_actions.items():
        expected = {'native.run-action/1': 'activities.RunAction',
                    'native.spot-action/1': 'activities.SpotAction'}[adapter]
        _need(native_actions[action_id] == expected, 'future Action native type and adapter disagree')
    _preflight_choices(choices, encounter_id, entity_ids, start)


def _preflight_choices(choices, encounter_id, entity_ids, encounter_time):
    _need(type(choices) is tuple, 'accepted choices must be a tuple')
    previous_ordinal = 0
    action_ids = set()
    for choice in choices:
        _need(type(choice) is tuple and len(choice) == 9 and
              choice[0] == 'universe.accepted-action-choice/1' and choice[3] == 'accepted',
              'only versioned accepted future choices are supported')
        choice_id = choice[1]
        prefix = encounter_id + '/draft/'
        _need(type(choice_id) is str and choice_id.startswith(prefix) and
              choice_id[len(prefix):].isdigit(), 'accepted choice ID has no native logical form')
        ordinal = int(choice_id[len(prefix):])
        _need(ordinal > previous_ordinal, 'accepted choice IDs are duplicate or unordered')
        previous_ordinal = ordinal
        members = choice[7]
        _need(type(members) is tuple and members, 'accepted choice has no complete member set')
        for member in members:
            _need(type(member) is tuple and len(member) == 6, 'malformed accepted choice member')
            key, adapter, action_id, fields, target_key, prepared = member
            _need(adapter in ('native.run-action/1', 'native.spot-action/1'),
                  'unsupported accepted Action family')
            _need(type(key) is str and key and type(action_id) is str and action_id not in action_ids,
                  'duplicate or invalid accepted Action identity')
            action_ids.add(action_id)
            field_map = dict(fields)
            _need(len(field_map) == len(fields), 'duplicate accepted Action declaration field')
            actor = _descriptor_scalar(field_map.get('actor_id'))
            start = _descriptor_scalar(field_map.get('start_time'))
            end = _descriptor_scalar(field_map.get('end_time'))
            _need(actor in entity_ids and type(start) in (int, float) and
                  type(end) in (int, float) and start >= encounter_time and end > start,
                  'accepted Action has invalid actor or future interval')
            _need(_descriptor_scalar(field_map.get('universe')) == '0',
                  'accepted Action references a different Universe')
            if adapter == 'native.spot-action/1':
                target = _descriptor_scalar(field_map.get('target_id'))
                _need(target in entity_ids and target != actor, 'accepted Spot has invalid target')
            _need(type(prepared) is tuple, 'accepted Action preparation is malformed')
