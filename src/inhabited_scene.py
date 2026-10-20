"""Bounded inhabited-world integration: world facts -> sensing -> belief -> history.

The actual geographic relief, aggregate composition, Being positions, and
established environmental facts retain their *existing* authoritative owners.
This is a scenario coordinator, NOT a second reality ledger or vision engine.
Coordinates for the encounter are local, planar metres; the geographic map is
registered by an explicit x/y offset (4 km, -0.5 km), with NO terrain occlusion.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import json
import math

from encounter import Encounter
from field_observation import BeliefLedger
from geographical_requirements import GeographicalDesign
from group_observation import ObserveGroupAction
from library import Library
from lantern_inquiry import LanternInquiry, Lantern
from perception import RangePerception
from realization import Fact, FactKey, RealityLedger
from spatial.state import CartesianPosition
from statistical_group import StatisticalGroup
from universe import Universe

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GROUP = ROOT / 'examples' / 'nomadic_group.json'


class InhabitedScene:
    """One tiny test world. Commands replay deterministically from an event journal.

    'Reality' is split across existing domain objects; the coordinator reports
    provenance rather than copying their facts into a second authority.
    """
    VERSION = 2
    VIEW_ORIGIN = (4., -.5)  # regional km corresponding to local encounter (0,0) m
    SENSOR = {'coarse_range_m': 600., 'detailed_range_m': 260.}
    COMMANDS = frozenset({'scan', 'survey', 'approach', 'observe', 'talk', 'sky', 'look_lantern'})

    def __init__(self, terrain_candidate_index=2, lantern_lit=True):
        if isinstance(terrain_candidate_index, bool) or not isinstance(terrain_candidate_index, int) or not 0 <= terrain_candidate_index <= 100000:
            raise ValueError('terrain_candidate_index must be an integer from 0 to 100000')
        if not isinstance(lantern_lit, bool):
            raise ValueError('lantern_lit must be a Boolean')
        self.terrain_candidate_index = terrain_candidate_index
        self.lantern_lit = lantern_lit
        configuration = json.loads(DEFAULT_GROUP.read_text(encoding='utf-8'))
        configuration['motion'] = dict(configuration['motion'])
        configuration['motion'].update({'position': [450., 0., 0.],
                                        'velocity': [0., 0., 0.],
                                        'acceleration': [0., 0., 0.]})
        self.world = Universe('A village at dusk', library=Library(
            config_dir=str(ROOT / 'src' / 'config')))
        self.group = StatisticalGroup(configuration['group_name'],
                                      configuration['group_id'], configuration,
                                      configuration['seed'])
        self.world.add_object(self.group)
        self.actors = {}
        self.ledgers = {}
        for role, name, position, skill in (
            ('traveler', 'Traveler', (0, 0, 0), 2),
            ('companion', 'Companion', (80, 50, 0), 4),
        ):
            identifier = self.world.make_being('Human', name)
            actor = self.world.get_object_by_id(identifier)
            actor.set_position(CartesianPosition(*position))
            actor.set_skill_level(self.world.get_skill_dictionary(), 'spot', skill)
            self.actors[role] = actor
            self.ledgers[role] = BeliefLedger(identifier)
        self.encounter = Encounter(self.world, difficulty_class=6, start_time=0)
        for actor in self.actors.values():
            self.encounter.add_being(actor.id)
        self.encounter.add_object(self.group.id)
        self.encounter.mark_aware(self.actors['traveler'].id, self.actors['companion'].id)
        self.encounter.decide_to_act(self.actors['traveler'].id,
                                     self.actors['companion'].id,
                                     'explore the valley at dusk')
        self.terrain = GeographicalDesign(seed=712)
        self.lantern = Lantern(lit=lantern_lit)
        self.lantern_inquiry = LanternInquiry(self.terrain, self.lantern)
        self.environment = RealityLedger()
        self.environment.commit([
            Fact(FactKey('scene', 'daypart'), 'dusk', 'scenario_condition'),
            Fact(FactKey('scene', 'settlement'), 'Valley village', 'scenario_condition'),
            Fact(FactKey('scene', 'lantern'),
                 {'location_km': list(self.lantern.location_km),
                  'mast_height_m': self.lantern.mast_height_m,
                  'intensity_cd': self.lantern.intensity_cd, 'lit': self.lantern.lit},
                 'scenario_condition'),
        ])
        self._events = []
        self._sensory = []  # first-person statements, never authoritative world facts

    def _map_xy(self, actor):
        p = actor.get_position()
        return (round(self.VIEW_ORIGIN[0] + p.x / 1000, 6),
                round(self.VIEW_ORIGIN[1] + p.y / 1000, 6))

    def inspect(self):
        """Pure projection; never triggers Group.counts() or terrain previews."""
        return self.state()

    def _observe(self, role):
        actor = self.actors[role]
        distance = self.encounter.distance_between_entities(actor.id, self.group.id)
        action = ObserveGroupAction(
            self.world, actor.id, self.group.id, self.encounter.time,
            seed=62, random_key=role,
            observation=self.SENSOR,
            interpretation={'skill_name': 'spot', 'expert_level': 5},
            experience={'success': 12, 'failure': 18},
            ledger=self.ledgers[role])
        self.encounter.schedule_action(action)
        self.encounter.step(duration=1)
        return {'outcome': action.resolution.outcome,
                'distance_m': round(distance, 2),
                'evidence_created': action.field_observation is not None,
                'spot_roll': action.roll}

    def _execute(self, operation, args):
        person = self.actors['traveler']
        if operation == 'scan':
            perceived = self.encounter.perceive(person.id, RangePerception(600))
            targets = sorted(('caravan' if item.target_id == self.group.id else 'companion')
                             for item in perceived)
            self._sensory.append({'source': 'range_proxy',
                                  'time': self.encounter.time,
                                  'statement': 'Detected nearby: ' + ', '.join(targets),
                                  'limitations': 'range only; no optical visibility'})
            return {'perceived': targets, 'mode': 'range_proxy',
                    'objective_realized': []}
        if operation == 'survey':
            # Candidate is grounded in the character's current neighborhood,
            # not an arbitrary unseen point anywhere in the region.
            x, y = args['x_km'], args['y_km']
            current_x, current_y = self._map_xy(person)
            if math.hypot(x-current_x, y-current_y) > .3 + 1e-9:
                raise ValueError('Survey site must lie within 300 m of the traveler')
            before = self.terrain.inspect(x, y)
            added = []
            if not before['resolved']:
                proposal = self.terrain.preview(before['tile'], self.terrain_candidate_index)
                self.terrain.commit(proposal)
                added = [f'terrain_tile:{before["tile"][0]},{before["tile"][1]}']
            result = self.terrain.inspect(x, y)
            self._sensory.append({'source': 'terrain_proxy',
                                  'time': self.encounter.time,
                                  'statement': 'Local surface sampled; no visual/terrain-occlusion model',
                                  'limitations': 'numerical height is objective model output, not traveler knowledge'})
            return {'x_km': x, 'y_km': y, 'tile': result['tile'],
                    'elevation_m': round(result['elevation_m'], 2),
                    'objective_realized': added, 'source': 'GeographicalDesign'}
        if operation == 'approach':
            # 240 m at 2 m/s toward the stationary caravan, without
            # inventing terrain-following motion or a walking locomotion solver.
            if person.get_position().x >= 240:
                raise ValueError('Already near the caravan')
            self.encounter.step(duration=120, velocities={person.id: (2.0, 0, 0)})
            return {'position_m': list(person.get_position().as_tuple()),
                    'elapsed_s': 120, 'movement': 'kinematic_placeholder',
                    'objective_realized': []}
        if operation == 'observe':
            if not self.encounter.is_aware(person.id, self.group.id):
                raise ValueError('Locate the caravan with Scan surroundings first')
            prior = self.group._counts is not None
            result = self._observe('traveler')
            result['objective_realized'] = [] if prior or self.group._counts is None else [
                'caravan:aggregate_composition']
            return result
        if operation == 'talk':
            friend = self.actors['companion']
            distance = self.encounter.distance_between_entities(person.id, friend.id)
            if distance > 150:
                raise ValueError('Companion is too far away to converse (150 m proxy)')
            # An independent witness must first obtain evidence; no invented
            # dialogue or direct transfer of objective group composition.
            witness = None
            if not self.ledgers['companion'].evidence:
                prior = self.group._counts is not None
                witness = self._observe('companion')
                witness['objective_realized'] = [] if prior or self.group._counts is None else [
                    'caravan:aggregate_composition']
            transmitted = self.ledgers['traveler'].share_from(
                self.ledgers['companion'], at_time=self.encounter.time)
            return {'witness_observation': witness, 'reports_shared': transmitted,
                    'mode': 'communicated_evidence',
                    'objective_realized': [] if witness is None else witness['objective_realized']}
        if operation == 'look_lantern':
            # The *world-builder's* candidate policy supplies unresolved
            # relief, not the traveler's visual observation. Resolve only
            # dependencies the bounded interval test cannot settle.
            target = self._map_xy(person)
            assessment = self.lantern_inquiry.assess(target)
            realized = []
            for _ in range(8):
                if assessment['physical_visibility'] != 'unresolved_geometry':
                    break
                missing = assessment['missing_terrain_tiles']
                if not missing:
                    break  # numerical tangency / unsupported indeterminacy
                tile = missing[0]
                if tile in self.terrain.state()['committed_tiles']:
                    raise ValueError('Visibility dependency did not advance')
                self.terrain.commit(self.terrain.preview(tile, self.terrain_candidate_index))
                realized.append(f'terrain_tile:{tile[0]},{tile[1]}')
                assessment = self.lantern_inquiry.assess(target)
            physical = assessment['physical_visibility']
            if physical == 'unresolved_geometry':
                # No claim about vision when geometric certainty is absent.
                return {'physical_visibility': physical, 'perceived': None,
                        'reason': 'Unresolved sampled geometry',
                        'objective_realized': realized, 'assessment': assessment}
            # Bounded observational noise, intentionally NOT a perfect copy of
            # world truth. A false alarm is an apparent light, not proof that
            # a ray travelled through terrain or that the lamp was seen.
            spot = person.get_skill_level('spot') or 0
            p_detection = min(0.92, 0.72 + .04*spot) if physical == 'detectable_candidate' else .04
            key = f'lantern-look:{self.terrain_candidate_index}:{self.lantern_lit}:{len(self._events)}'.encode()
            u = int.from_bytes(hashlib.sha256(key).digest()[:8], 'big') / 2**64
            perceived = u < p_detection
            evidence_id = f'lantern-observation-{sum(x["source"] == "lantern_proxy" for x in self._sensory)+1}'
            self._sensory.append({'id': evidence_id, 'source': 'lantern_proxy',
                                  'time': self.encounter.time,
                                  'reported_glow': perceived,
                                  'statement': 'Possible lantern glow reported' if perceived else 'No lantern glow reported',
                                  'limitations': 'sampled terrain + dusk photometry; heuristic detection and false alarm rates',
                                  'observer': 'traveler', 'mode': 'direct_visual_proxy'})
            return {'physical_visibility': physical, 'perceived': perceived,
                    'evidence_id': evidence_id, 'detection_probability': round(p_detection, 2),
                    'objective_realized': realized, 'assessment': assessment}
        if operation == 'sky':
            established = self.environment.inspect(FactKey('scene', 'daypart'))
            self._sensory.append({'source': 'environmental_condition',
                                  'time': self.encounter.time,
                                  'statement': 'The scene is established as dusk.',
                                  'limitations': 'not an astronomical observation or sunset calculation'})
            return {'known_daypart': established.value,
                    'sunset_prediction': None,
                    'missing': ['local solar phase', 'axial tilt',
                                'astronomical time and latitude'],
                    'objective_realized': []}
        raise ValueError('Unsupported operation')

    def act(self, operation, **args):
        if operation not in self.COMMANDS:
            raise ValueError('Unsupported operation')
        if operation == 'survey':
            if set(args) != {'x_km', 'y_km'}:
                raise ValueError('Survey requires x_km and y_km')
            for name in ('x_km', 'y_km'):
                value = args[name]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError(f'{name} must be finite numeric value')
            args = {'x_km': float(args['x_km']), 'y_km': float(args['y_km'])}
            # Preflight regional validity before any mutation.
            self.terrain.inspect(args['x_km'], args['y_km'])
        elif args:
            raise ValueError('Unexpected parameters')
        result = self._execute(operation, args)
        record = {'index': len(self._events) + 1, 'time_s': self.encounter.time,
                  'operation': operation, 'args': deepcopy(args),
                  'result': deepcopy(result)}
        self._events.append(record)
        return deepcopy(record)

    def state(self):
        traveler, companion = self.actors['traveler'], self.actors['companion']
        led = self.ledgers['traveler']
        observations = []
        for n, report in enumerate(led.evidence, 1):
            labels = {actor.id: role for role, actor in self.actors.items()}
            observations.append({
                'id': f'observation-{n}',
                'source': labels.get(report.observer_id, 'unknown'),
                'mode': report.mode, 'time_s': report.time,
                'counts': {k: {'estimate': v.estimate, 'uncertainty': v.uncertainty}
                           for k, v in led.reports_for_observation(report.id).items()},
                'acquired_as': 'direct' if report.observer_id == traveler.id else 'communicated',
            })
        lantern_evidence = [e for e in self._sensory if e['source'] == 'lantern_proxy']
        estimates = {category: led.count_estimate(self.group.id, category)
                     for category in ('humans', 'livestock', 'dogs')}
        estimates = {category: None if estimate is None else round(estimate, 3)
                     for category, estimate in estimates.items()}
        return {
            'version': self.VERSION, 'time_s': self.encounter.time,
            'scene': {'daypart': self.environment.inspect(FactKey('scene', 'daypart')).value,
                      'village': self.environment.inspect(FactKey('scene', 'settlement')).value},
            'traveler': {'map_km': list(self._map_xy(traveler)),
                         'position_m': list(traveler.get_position().as_tuple()),
                         'spot_level': traveler.get_skill_level('spot') or 0},
            'companion': {'map_km': list(self._map_xy(companion)),
                          'nearby': self.encounter.distance_between_entities(
                              traveler.id, companion.id) <= 150},
            'caravan': {'map_km': list(self._map_xy(self.group)),
                        'aggregate_composition_realized': self.group._counts is not None,
                        'individuals_realized': self.group.materialized_count,
                        # Do not reveal true counts through the character panel;
                        # the separate audit panel may show them once committed.
                        'objective_counts': None if self.group._counts is None else self.group._counts.copy(),
                        'noticed': self.encounter.is_aware(traveler.id, self.group.id)},
            'terrain': {'revision': self.terrain.revision,
                        'committed_tiles': self.terrain.state()['committed_tiles'],
                        'unresolved_tiles': 8-len(self.terrain.state()['committed_tiles'])},
            'lantern': {'location_km': list(self.lantern.location_km),
                        'lit': self.lantern.lit,
                        'assessment': self.lantern_inquiry.assess(self._map_xy(traveler))},
            'perceptions': deepcopy(self._sensory),
            'evidence': observations,
            'beliefs': {'lantern': {'belief': 'unexamined' if not lantern_evidence else
                                             ('possible_glow' if lantern_evidence[-1]['reported_glow'] else 'not_detected'),
                                    'evidence_ids': [e['id'] for e in lantern_evidence]},
                        'estimates': estimates,
                        'disputes': sorted({c for c, _, _ in led.discrepancies(self.group.id)}),
                        'revisions': len(led.belief_history)},
            'history': deepcopy(self._events),
            'authorities': {'terrain': 'GeographicalDesign',
                            'population': 'StatisticalGroup',
                            'position_and_awareness': 'Universe / Encounter',
                            'belief': 'BeliefLedger',
                            'established_environment': 'RealityLedger',
                            'lamp_and_visibility': 'RealityLedger / LanternInquiry / GeographicalDesign'},
        }

    def map_data(self):
        """Baseline-only in unresolved tiles; client must label that explicitly."""
        return self.terrain.map_data(nx=65, ny=33)

    def export(self):
        return {'format': 'universe-inhabited-scene', 'version': self.VERSION,
                'configuration': {'terrain_candidate_index': self.terrain_candidate_index,
                                  'lantern_lit': self.lantern_lit},
                'events': [{'operation': e['operation'], 'args': deepcopy(e['args'])}
                           for e in self._events],
                'expected_state': self.state()}

    @classmethod
    def restore(cls, payload):
        if not isinstance(payload, dict) or payload.get('format') != 'universe-inhabited-scene' or payload.get('version') not in (1, 2):
            raise ValueError('Unsupported inhabited scene save')
        version = payload['version']
        keys = {'format', 'version', 'events', 'expected_state'}
        if version == 2:
            keys.add('configuration')
        if set(payload) != keys:
            raise ValueError('Malformed inhabited scene save')
        events = payload['events']
        if not isinstance(events, list) or len(events) > 300:
            raise ValueError('Invalid scene history')
        config = payload.get('configuration', {})
        if not isinstance(config, dict) or (version == 2 and
                set(config) != {'terrain_candidate_index', 'lantern_lit'}):
            raise ValueError('Invalid scene configuration')
        scene = cls(**config)
        for item in events:
            if not isinstance(item, dict) or set(item) != {'operation', 'args'} or not isinstance(item['args'], dict):
                raise ValueError('Malformed scene event')
            scene.act(item['operation'], **item['args'])
        now = scene.state()
        if version == 1:
            # Compare exactly the fields saved by the preceding prototype.
            now['version'] = 1
            now.pop('lantern')
            now['beliefs'].pop('lantern')
            now['authorities'].pop('lamp_and_visibility')
        if now != payload['expected_state']:
            raise ValueError('Saved state contradicts replayed event history')
        return scene
