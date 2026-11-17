"""Reusable Arena-independent authoring harness for native Encounter scenarios.

This module creates legal native setup state and routes declarations through
the existing Encounter scheduler/transaction publisher. It contains no Action
evaluation or resolution code; callers instantiate the same native Actions
used by the application.
"""
from __future__ import annotations

import random

from atomic_publication import RNGCursor
from encounter import Encounter
from spatial.geometry import Sphere
from spatial.state import CartesianPosition
from universe import Universe


class NativeScenarioBuilder:
    """Author a deterministic headless Encounter and submit real native work."""

    def __init__(self, name, library, *, start_time=0, end_time=10,
                 seed=0, initiated=True, encounter_id=None):
        if type(name) is not str or not name.strip():
            raise ValueError("scenario name must be nonempty")
        if type(seed) is not int or seed < 0:
            raise ValueError("scenario seed must be a nonnegative integer")
        self.world = Universe(name, library=library)
        self.encounter = Encounter(self.world, end_time, start_time,
                                   initiated=initiated, id=encounter_id)
        self.world.add_event(self.encounter)
        self.rng = RNGCursor(random.Random(seed).getstate())
        self._enabled = False

    def add_being(self, being_type, name, *, position=None, radius=None,
                  hit_points=None, participant=True, aware_of=()):
        """Create a native Being with only the explicitly supplied facts."""
        identity = self.world.make_being(being_type, name)
        being = self.world.get_object_by_id(identity)
        if position is not None:
            if type(position) not in (tuple, list) or len(position) != 3:
                raise ValueError("position must be a represented three-coordinate tuple")
            being.set_position(CartesianPosition(*position))
        if radius is not None:
            being.set_geometry(Sphere(radius))
        if hit_points is not None:
            being.set_hit_points(hit_points)
        if participant:
            self.encounter.add_being(identity)
        for observer_id in aware_of:
            self.encounter.mark_aware(observer_id, identity)
        return being

    def add_object(self, object_id, *, participant=True):
        """Include an existing native Object by its unchanged logical identity."""
        obj = self.world.get_object_by_id(object_id)
        if obj is None:
            raise ValueError("Object identity is not registered in this Universe")
        if participant:
            self.encounter.add_object(object_id)
        return obj

    def make_object(self, object_type, name, *, position=None, geometry=None,
                    participant=True):
        """Create a represented Object without inferring placement or geometry.

        Definitions and identity come from the native Universe Library. A
        position or geometry is added only when the scenario author supplies
        it; definition dimensions are never converted to world geometry.
        """
        object_id = self.world.make_object(object_type, name)
        if object_id is None:
            raise ValueError(f"native Object definition is unavailable: {object_type}")
        obj = self.world.get_object_by_id(object_id)
        self.set_placement(obj.id, position=position, geometry=geometry)
        if participant:
            self.encounter.add_object(object_id)
        return obj

    def make_possession_object(self, being_id, object_type, name, *,
                               participant=True):
        """Create an Object using Universe's possession-list operation.

        This preserves ``make_object_for_being`` semantics; it does not infer
        a spatial or physical-carried relation from inventory membership.
        """
        object_id = self.world.make_object_for_being(being_id, object_type, name)
        if object_id is None:
            raise ValueError(f"native Object could not be carried: {object_type}")
        obj = self.world.get_object_by_id(object_id)
        if participant:
            self.encounter.add_object(object_id)
        return obj

    def make_armor(self, armor_type, name, *, wearer_id=None, participant=True):
        """Create native Armor, optionally wearing it on an identified Being."""
        armor_id = self.world.make_armor(armor_type, name)
        if armor_id is None:
            raise ValueError(f"native Armor definition is unavailable: {armor_type}")
        if wearer_id is not None and not self.world.armor_being(wearer_id, armor_id):
            raise ValueError(f"native Armor could not be worn by {wearer_id}")
        armor = self.world.get_object_by_id(armor_id)
        if participant:
            self.encounter.add_object(armor_id)
        return armor

    def set_placement(self, entity_id, *, position=None, geometry=None):
        """Set only explicitly authored native location/geometry facts."""
        entity = self.world.get_object_by_id(entity_id)
        if entity is None:
            raise ValueError("native placement Entity is not registered")
        if position is not None:
            if type(position) not in (tuple, list) or len(position) != 3:
                raise ValueError("position must be a represented three-coordinate tuple")
            entity.set_position(CartesianPosition(*position))
        if geometry is not None:
            entity.set_geometry(geometry)
        return entity

    def arm(self, being_id, weapon_id, hand):
        """Use the native Universe equipment transition and retain Object identity."""
        if not self.world.arm_being(being_id, weapon_id, hand):
            raise ValueError("native weapon could not be equipped in the selected hand")
        return self.world.get_object_by_id(weapon_id)

    def make_weapon(self, being_id, weapon_type, name, *, hand=None,
                    participant=False):
        weapon_id = self.world.make_weapon_for_being(being_id, weapon_type, name)
        weapon = self.world.get_object_by_id(weapon_id)
        if participant:
            self.encounter.add_object(weapon_id)
        if hand is not None:
            self.arm(being_id, weapon_id, hand)
        return weapon

    def mark_aware(self, observer_id, target_id):
        self.encounter.mark_aware(observer_id, target_id)

    def enable(self):
        """Bind deterministic native transactional progression after setup."""
        if self._enabled:
            raise ValueError("native transactional progression is already enabled")
        self.encounter.enable_transactional_progression(
            quiescent=True, rng_owner=self.rng)
        self._enabled = True
        return self

    def schedule(self, action):
        if not self._enabled:
            raise ValueError("enable native progression before scheduling Actions")
        self.encounter.schedule_action(action)
        return action

    def schedule_choice(self, actions):
        if not self._enabled:
            raise ValueError("enable native progression before scheduling Choices")
        self.encounter.schedule_choice(tuple(actions))
        return tuple(actions)

    def step(self, seconds, **progression):
        if not self._enabled:
            raise ValueError("enable native progression before advancing the Encounter")
        return self.encounter.step(seconds, **progression)
