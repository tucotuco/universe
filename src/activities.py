"""Small noncombat Actions for the first live Encounter progression loop.

This module deliberately contains only a testable running activity. It does not
claim to model gait, exertion, fatigue, terrain, or whether a speed is realistic.
"""

import math
import json

from action import Action
from experience import ActionResolution, SkillExercise
from spatial.state import CartesianPosition


class RunAction(Action):
    """Attempt to cover a configured straight-line distance while running.

    The Encounter moves the Being using its ordinary step() velocities. This
    Action *observes* the resulting displacement; it never moves the Being.

    The initial position is captured at scheduling, not construction, so an
    Action cannot credit movement that happened before it was scheduled.
    Successful or partial movement exercises 'run'; no motion earns no XP.
    ``experience`` is an explicit scenario award, not a progression policy.

    Straight-line displacement is a deliberately provisional measure: a route
    that returns to its origin will count as no movement until we introduce
    path-aware movement histories.
    """

    def __init__(self, universe, actor_id, start_time, duration,
                 minimum_distance, experience=0):
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
                         target_id=None, instrument_id=None)
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

    def on_schedule(self, encounter):
        """Begin observing physical movement at the encounter's current time."""
        if self.start_position is not None:
            raise ValueError("running activity has already been started")
        if self.start_time != encounter.time:
            raise ValueError("running activity must begin at scheduling time")
        actor = encounter.get_being(self.actor_id)
        if actor is None or actor.get_position() is None:
            raise ValueError("running activity requires a positioned participating Being")
        self.start_position = actor.get_position()

    def resolve(self, difficulty_class):
        """Report practice from measured displacement, not declared intention."""
        if self.start_position is None:
            raise RuntimeError("running activity has not been scheduled")
        actor = self.get_actor()
        position = actor.get_position() if actor is not None else None
        if not isinstance(position, CartesianPosition):
            raise ValueError("running activity requires the Being's current position")
        displacement = math.dist(self.start_position.as_tuple(), position.as_tuple())
        if displacement == 0:
            result = ActionResolution('no_movement')
        else:
            outcome = 'success' if displacement >= self.minimum_distance else 'partial'
            result = ActionResolution(outcome, (SkillExercise('run', self.practice_experience),))
        self.displacement = displacement
        return result
