"""Experimental, provisional statistical-group observation through Encounter Actions.

Objective composition is read only by the evidence generator.  The interpreter
receives *only* the imperfect evidence.  No tactical line-of-sight or terrain
visibility is asserted: range merely gates the currently modeled sensor.
Its Spot-skill-based sampling and practice are a separate unresolved Group
sensor model; they are not adopted deliberate Spot rules.
"""
from __future__ import annotations

from transactional_progression import guard_legacy_action, guard_legacy_encounter

from dataclasses import asdict
import hashlib
import json
import math
import random

from action import Action
from scheduling import PreparedSchedule
from experience import ActionResolution, SkillExercise
from field_observation import BeliefLedger, CountReport, FieldObservation
from field_interpretation import FieldInterpreter
from perception import Perception
from spatial.state import CartesianPosition
from statistical_group import StatisticalGroup


def observation_rng(seed, random_key, target_id, start_time, stage):
    token = f'{seed}|{random_key}|{target_id}|{start_time}|{stage}'
    number = int.from_bytes(hashlib.sha256(token.encode()).digest()[:16], 'big')
    return random.Random(number)


def group_check(roll, level, distance, detailed_range, difficulty):
    return roll == 20 or (roll != 1 and roll + level >= difficulty + (2 if distance > detailed_range else 0))


class SampledGroupObservation:
    """Sample fallible evidence; neither observation nor interpretation sets truth.

    The noise scale decreases with rank, but positive probability of error
    remains at every level. False-positive classifications may be marked as
    dubious cues, which the independent interpretation model can discount.
    This is a sensor *proxy*, not a physical optics/individual-detection model.
    """

    def __init__(self, coarse_range_m, detailed_range_m, *,
                 coarse_count_sigma=None, detailed_count_sigma=None,
                 coarse_position_sigma_m=40.0, detailed_position_sigma_m=12.0,
                 skill_precision_gain=0.25, max_ambiguous_dogs=2,
                 focus_precision_factor=0.5):
        if not 0 < detailed_range_m <= coarse_range_m:
            raise ValueError('observation ranges must be ordered positive distances')
        self.coarse_range_m = float(coarse_range_m)
        self.detailed_range_m = float(detailed_range_m)
        self.count_sigmas = {
            'coarse': dict(coarse_count_sigma or {'humans': 3., 'livestock': 5., 'dogs': 2.5}),
            'detailed': dict(detailed_count_sigma or {'humans': 1.5, 'livestock': 2.5, 'dogs': 1.2}),
        }
        self.position_sigmas = {'coarse': float(coarse_position_sigma_m),
                                'detailed': float(detailed_position_sigma_m)}
        self.skill_precision_gain = float(skill_precision_gain)
        if type(max_ambiguous_dogs) is not int or max_ambiguous_dogs < 0:
            raise ValueError('max_ambiguous_dogs must be a nonnegative integer')
        self.max_ambiguous_dogs = max_ambiguous_dogs
        if (isinstance(focus_precision_factor, bool) or
                not isinstance(focus_precision_factor, (int, float)) or
                not math.isfinite(focus_precision_factor) or
                not 0 < focus_precision_factor <= 1):
            raise ValueError('focus precision factor must lie in (0, 1]')
        self.focus_precision_factor = float(focus_precision_factor)
        if not math.isfinite(self.skill_precision_gain) or self.skill_precision_gain < 0:
            raise ValueError('skill_precision_gain must be finite and nonnegative')
        for value in list(self.position_sigmas.values()) + [x for d in self.count_sigmas.values() for x in d.values()]:
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError('noise scales must be finite nonnegative numbers')
        for sigmas in self.count_sigmas.values():
            if set(sigmas) != {'humans', 'livestock', 'dogs'}:
                raise ValueError('count noise requires humans, livestock, dogs')

    def sample(self, group, observer_id, time, distance, level, observation_id, rng,
               focus_category=None):
        if not isinstance(group, StatisticalGroup):
            raise TypeError('requires a StatisticalGroup')
        if distance is None or distance > self.coarse_range_m:
            raise ValueError('observation outside modeled range')
        if type(level) is not int or level < 0:
            raise ValueError('spot level must be a nonnegative integer')
        if focus_category not in (None, 'humans', 'livestock', 'dogs'):
            raise ValueError('unknown observation focus category')
        return sample_group_evidence(self.__dict__, group.counts(), group.get_position(),
            group.id, observer_id, time, distance, level, observation_id, rng, focus_category)



def sample_group_evidence(config, truths, center, group_id, observer_id, time, distance,
                          level, observation_id, rng, focus_category=None):
    """Native sampling math against explicit truth; no world reads or writes."""
    if distance is None or distance > config['coarse_range_m']:
        raise ValueError('observation outside modeled range')
    if type(level) is not int or level < 0:
        raise ValueError('spot level must be a nonnegative integer')
    if focus_category not in (None, 'humans', 'livestock', 'dogs'):
        raise ValueError('unknown observation focus category')
    detail = 'detailed' if distance <= config['detailed_range_m'] else 'coarse'
    factor = 1 / math.sqrt(1 + level * config['skill_precision_gain'])
    reports = {}
    false_positives = rng.randint(0, config['max_ambiguous_dogs'] if detail == 'coarse' else min(1, config['max_ambiguous_dogs']))
    for category in ('humans', 'livestock', 'dogs'):
        sigma = config['count_sigmas'][detail][category] * factor
        if category == focus_category:
            sigma *= config['focus_precision_factor']
        noise = round(rng.gauss(0, sigma))
        estimate = max(0, truths[category] + noise + (false_positives if category == 'dogs' else 0))
        uncertainty = max(1, math.ceil(2 * sigma))
        reports[category] = CountReport(estimate, uncertainty)
    # A few genuine dogs may also look dubious. Expertise isn't an oracle.
    ambiguous_true = int(truths['dogs'] > 0 and rng.random() < .15)
    dubious = min(reports['dogs'].estimate, false_positives + ambiguous_true)
    position_sigma = config['position_sigmas'][detail] * factor
    reported_position = CartesianPosition(*(v + rng.gauss(0, position_sigma)
                                            for v in center.as_tuple()))
    return FieldObservation(
        observation_id, observer_id, group_id, time, reported_position,
        max(1., 2 * position_sigma), reports,
        f'sampled_{detail}_range_proxy', {'dogs': dubious}, focus_category)


class ObserveGroupAction(Action):
    """Exercise Spotting through the Encounter timeline and create imperfect evidence.

    A seeded d20 determines success after the range feasibility gate. An
    unsuccessful *feasible* attempt still exercises Spotting. Successful
    attempts sample observational evidence and interpret it without passing
    group truth to the interpreter. The Encounter owns Action completion and
    skill experience; the optional BeliefLedger accepts committed observations.
    """

    def __init__(self, universe, actor_id, target_id, start_time, *, duration=1,
                 seed=0, observation=None, interpretation=None, experience=None,
                 ledger=None, random_key=None, focus_category=None):
        if type(seed) is not int:
            raise TypeError('seed must be an integer')
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
            raise ValueError('duration must be a finite positive number')
        if isinstance(start_time, bool) or not isinstance(start_time, (int, float)) or not math.isfinite(start_time):
            raise ValueError('start_time must be finite')
        super().__init__(universe, start_time, None, 'observe_group', actor_id, target_id, None)
        self.end_time = start_time + duration
        if not math.isfinite(self.end_time):
            raise ValueError('end_time overflow')
        self.seed = seed
        self.random_key = actor_id if random_key is None else str(random_key)
        if not self.random_key:
            raise ValueError('random_key must not be empty')
        self.observer = observation if isinstance(observation, SampledGroupObservation) else SampledGroupObservation(**(observation or {}))
        self.interpreter = interpretation if isinstance(interpretation, FieldInterpreter) else FieldInterpreter(**(interpretation or {}))
        self.experience_policy = dict(experience or {'success': 12, 'failure': 18})
        if any(k not in ('success', 'failure') or type(v) is not int or v < 0
               for k, v in self.experience_policy.items()):
            raise ValueError('experience policy must define nonnegative integer awards')
        for key in ('success', 'failure'):
            if key not in self.experience_policy:
                raise ValueError('experience policy requires success and failure')
        if ledger is not None and (not isinstance(ledger, BeliefLedger) or ledger.observer_id != actor_id):
            raise ValueError('ledger must belong to the observing Being')
        if focus_category not in (None, 'humans', 'livestock', 'dogs'):
            raise ValueError('focus must be a supported observed count category')
        self.focus_category = focus_category
        self.ledger = ledger
        self._encounter = None
        self.roll = None
        self.skill_level_used = None
        self.field_observation = None
        self.field_interpretation = None

    def _rng(self, stage):
        # No mutable shared random stream and no Action UUID in the seed.
        return observation_rng(self.seed, self.random_key, self.target_id, self.start_time, stage)

    def prepare_schedule(self, encounter):
        if self._encounter is not None or self.start_time < encounter.time:
            raise ValueError('group observation must be scheduled once at current time')
        if not isinstance(encounter.get_entity(self.target_id), StatisticalGroup):
            raise ValueError('target must be a participating StatisticalGroup')
        if encounter.universe.get_skill_dictionary().get_skill_definition('spot') is None:
            raise ValueError('spot skill is not defined')
        return PreparedSchedule.from_action(self, initialization=(('_encounter', encounter),))

    def resolve(self, difficulty_class):
        guard_legacy_action(self, effect=True)
        if self._encounter is None:
            raise RuntimeError('group observation was not scheduled')
        if not isinstance(difficulty_class, (int, float)) or isinstance(difficulty_class, bool) or not math.isfinite(difficulty_class):
            raise ValueError('difficulty_class must be finite')
        actor = self._encounter.get_being(self.actor_id)
        group = self._encounter.get_entity(self.target_id)
        if actor is None or not isinstance(group, StatisticalGroup):
            raise ValueError('missing observer or group')
        self.skill_level_used = actor.get_skill_level('spot') or 0
        distance = self._encounter.distance_between_entities(self.actor_id, self.target_id)
        if distance is None:
            return ActionResolution('unplaced')
        if distance > self.observer.coarse_range_m:
            return ActionResolution('out_of_range')
        # The simple range instrument is the only feasibility gate. Group
        # geometry/terrain/lighting are not yet modeled; no visibility claim.
        self.roll = self._rng('d20').randint(1, 20)
        passed = group_check(self.roll, self.skill_level_used, distance, self.observer.detailed_range_m, difficulty_class)
        if not passed:
            return ActionResolution('failure', (SkillExercise('spot', self.experience_policy['failure']),))
        self.field_observation = self.observer.sample(
            group, self.actor_id, self.end_time, distance, self.skill_level_used,
            self.id, self._rng('evidence'), focus_category=self.focus_category)
        self.field_interpretation = self.interpreter.interpret(self.field_observation, actor)
        signal = Perception(self.actor_id, self.target_id, 'sampled_group_observation',
                            distance, self.observer.coarse_range_m)
        return ActionResolution('success',
                                (SkillExercise('spot', self.experience_policy['success']),),
                                (signal,))

    def on_completed(self, encounter):
        """Record evidence only after Encounter accepts the completed Action."""
        guard_legacy_action(self, effect=True)
        guard_legacy_encounter(encounter, "legacy completion hook")
        if self.ledger is not None and self.field_observation is not None:
            self.ledger.learn(self.field_observation, interpretation=self.field_interpretation)

    def to_json(self):
        record = json.loads(super().to_json())
        record.update({'seed': self.seed, 'random_key': self.random_key,
                       'focus_category': self.focus_category, 'roll': self.roll,
                       'skill_level_used': self.skill_level_used,
                       'field_observation': None if self.field_observation is None else asdict(self.field_observation),
                       'field_interpretation': None if self.field_interpretation is None else asdict(self.field_interpretation)})
        return json.dumps(record, indent=2)
