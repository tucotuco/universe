"""Small noncombat Actions for the first live Encounter progression loop.

This module deliberately contains only a testable running activity. It does not
claim to model gait, exertion, fatigue, terrain, or whether a speed is realistic.
"""

from transactional_progression import guard_legacy_action

import math
import json
import random

from action import Action
from scheduling import PreparedSchedule
from experience import ActionResolution, SkillExercise
from perception import Perception
from spatial.state import CartesianPosition


class RunAction(Action):
    """Attempt to cover a configured straight-line distance while running.

    The Encounter moves the Being using its ordinary step() velocities. This
    Action *observes* the resulting displacement; it never moves the Being.

    The initial position is captured when activity starts, not construction, so an
    Action cannot credit movement that happened before it was scheduled.
    Successful or partial movement exercises 'run'; no motion earns no XP.
    ``experience`` is an explicit scenario award, not a progression policy.

    Straight-line displacement is a deliberately provisional measure: a route
    that returns to its origin will count as no movement until we introduce
    path-aware movement histories.
    """

    def __init__(self, universe, actor_id, start_time, duration,
                 minimum_distance, experience=0, id=None):
        for name, value in (("start_time", start_time),
                            ("duration", duration),
                            ("minimum_distance", minimum_distance)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number")
        if duration <= 0 or minimum_distance <= 0:
            raise ValueError("duration and minimum_distance must be positive")
        if isinstance(experience, bool) or not isinstance(experience, int) or experience < 0:
            raise ValueError("experience must be a nonnegative integer")
        super().__init__(universe, start_time, None, 'run', actor_id,
                         target_id=None, instrument_id=None, id=id)
        self.end_time = start_time + duration
        if not math.isfinite(self.end_time):
            raise ValueError("end_time must be finite")
        self.minimum_distance = float(minimum_distance)
        self.practice_experience = experience
        self.start_position = None
        self.displacement = None


    def to_json(self):
        """Preserve the declared task and measured evidence with the Action."""
        data = json.loads(super().to_json())
        data.update({
            'minimum_distance': self.minimum_distance,
            'practice_experience': self.practice_experience,
            'start_position': (None if self.start_position is None
                               else dict(zip(('x', 'y', 'z'), self.start_position.as_tuple()))),
            'displacement': self.displacement,
        })
        return json.dumps(data, indent=2)

    def prepare_schedule(self, encounter):
        """Stage a sample; the choice coordinator captures the actual start."""
        if self.start_position is not None:
            raise ValueError("running activity has already been started")
        if self.start_time < encounter.time:
            raise ValueError("running activity cannot begin before scheduling time")
        actor = encounter.get_being(self.actor_id)
        if actor is None or actor.get_position() is None:
            raise ValueError("running activity requires a positioned participating Being")
        return PreparedSchedule.from_action(self, initialization=(
            ('start_position', actor.get_position()),))

    def resolve(self, difficulty_class):
        """Report practice from measured displacement, not declared intention."""
        guard_legacy_action(self, effect=True)
        if self.start_position is None:
            if getattr(self, '_activity_started', False):
                return ActionResolution('unplaced')
            raise RuntimeError("running activity has not been scheduled")
        actor = self.get_actor()
        position = actor.get_position() if actor is not None else None
        if position is None:
            return ActionResolution('unplaced')
        if not isinstance(position, CartesianPosition):
            raise ValueError("running activity requires the Being's current position")
        displacement = math.dist(self.start_position.as_tuple(), position.as_tuple())
        if displacement == 0:
            result = ActionResolution('no_movement')
        else:
            from action_calculations import run_outcome
            outcome = run_outcome(displacement, self.minimum_distance)
            result = ActionResolution(outcome, (SkillExercise('run', self.practice_experience),))
        self.displacement = displacement
        return result


class SpotAction(Action):
    """Six-second deliberate Spot discovery Action (revision-60 rules).

    The geometry gate remains a limited scaffold and does not model complete
    visibility, lighting, acuity, or terrain.
    """

    def __init__(self, universe, actor_id, target_id, start_time,
                 duration=6, die_roll=None, id=None, spotting_conditions=(), *,
                 ledger=None, group_fully_visible=False,
                 location_ledger=None):
        for name, value in (("start_time", start_time), ("duration", duration)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number")
        if duration != 6:
            raise ValueError("deliberate Spot takes exactly six seconds")
        if die_roll is not None and (type(die_roll) is not int or not 1 <= die_roll <= 20):
            raise ValueError("die_roll must be an integer between 1 and 20")
        if actor_id == target_id:
            raise ValueError("a Being cannot spot itself")
        if type(group_fully_visible) is not bool:
            raise TypeError("group_fully_visible must be a Boolean scenario premise")
        if ledger is not None:
            from field_observation import BeliefLedger
            if type(ledger) is not BeliefLedger or ledger.observer_id != actor_id:
                raise ValueError("Spot evidence ledger must belong to the observing Being")
        if group_fully_visible and ledger is None:
            raise ValueError("fully visible Group observation requires the observer's BeliefLedger")
        if ledger is not None and not group_fully_visible:
            raise ValueError("Spot ledger is supported only with an explicit fully visible Group premise")
        if location_ledger is not None:
            from location_observation import LocationEvidenceLedger
            if (type(location_ledger) is not LocationEvidenceLedger
                    or location_ledger.observer_id != actor_id):
                raise ValueError("location evidence ledger must belong to the Spotter")
        from discovery import SpottingConditions
        conditions = SpottingConditions(tuple(spotting_conditions))
        super().__init__(universe, start_time, None, 'spot', actor_id,
                         target_id, instrument_id=None, id=id)
        self.end_time = start_time + 6
        if not math.isfinite(self.end_time):
            raise ValueError("end_time must be finite")
        self.spotting_conditions = conditions.values
        self.declared_roll = die_roll
        self.roll = None
        self.path_status = None
        self._encounter = None
        self.ledger = ledger
        self.group_fully_visible = group_fully_visible
        if location_ledger is not None:
            self.location_ledger = location_ledger

    def prepare_schedule(self, encounter):
        """Bind to a validated Encounter but do not manufacture awareness."""
        if self._encounter is not None:
            raise ValueError("spotting activity has already been scheduled")
        if self.start_time < encounter.time:
            raise ValueError("spotting activity cannot begin before scheduling time")
        if self.group_fully_visible:
            from statistical_group import StatisticalGroup
            if type(encounter.get_entity(self.target_id)) is not StatisticalGroup:
                raise ValueError("fully visible Group premise requires a StatisticalGroup target")
        location_ledger = self.__dict__.get('location_ledger')
        if location_ledger is not None:
            target = encounter.get_being(self.target_id)
            if target is None:
                raise ValueError("location evidence requires a participating Being target")
            if location_ledger.observer_id != self.actor_id:
                raise ValueError("location evidence ledger owner changed")
        return PreparedSchedule.from_action(self, initialization=(('_encounter', encounter),))

    def resolve(self, difficulty_class):
        """Report the check and any awareness; Encounter applies consequences."""
        guard_legacy_action(self, effect=True)
        if self.group_fully_visible:
            raise RuntimeError("exact Group evidence requires native transactional Spot publication")
        if self._encounter is None:
            raise RuntimeError("spotting activity has not been scheduled")
        actor = self._encounter.get_being(self.actor_id)
        target = self._encounter.get_entity(self.target_id)
        if actor is None or target is None:
            raise ValueError("spotting requires participating actor and target")
        distance = self._encounter.distance_between_entities(self.actor_id, self.target_id)
        self.path_status = None
        self.roll = None
        observation = ()
        if distance is None:
            outcome = 'unplaced'
        elif target.geometry is None:
            outcome = 'unmodeled_target'
        else:
            path = self._encounter.line_of_sight(self.actor_id, self.target_id)
            self.path_status = None if path is None else path.status
            if path is None or not path.clear:
                outcome = 'no_clear_path'
            else:
                self.roll = self.declared_roll if self.declared_roll is not None else random.randint(1, 20)
                from discovery import SpottingConditions, discovery_dc, racial_discovery_bonus
                target_dc = discovery_dc(target.current.discovery_dc)
                target_dc += SpottingConditions(self.spotting_conditions).dc_adjustment
                race = getattr(actor.current, 'race', None)
                passed = self.roll + racial_discovery_bonus(race, 'spot') >= target_dc
                outcome = 'success' if passed else 'failure'
                if passed:
                    observation = (Perception(self.actor_id, self.target_id,
                                              'spot_check_geometric_path',
                                              distance, None),)
        return ActionResolution(outcome, (), observation)

    def to_json(self):
        data = json.loads(super().to_json())
        data.update({
            'spotting_conditions': self.spotting_conditions,
            'declared_roll': self.declared_roll,
            'roll': self.roll,
            'path_status': self.path_status,
        })
        return json.dumps(data, indent=2)
