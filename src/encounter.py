#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2024 Rauthiflor LLC"
__version__ = "encounter.py 2024-03-09T22:00-03:00"

# TODO: Make ''' comments on classes and methods

from transactional_progression import guard_legacy_encounter, planning_entry, validate_action_contract, validate_choice_actions
import json
import math
import random
from dataclasses import dataclass

from spatial.state import CartesianPosition, integrate_position
from spatial.frame import LocalFrame, LocalPosition
from spatial.visibility import trace_sightline

from utils import convert_to_dc
from action import Action
from action_choice import ChoiceBook, ChoiceView, ChoiceRejected
from scheduling import PreparedSchedule, native_preparer
from event import Event
from experience import ActionResolution
from library import Library
from being import BeingInstance
from encounter_fatigue_bridge import FrozenFatigueFrame
from object import ObjectInstance
from perception import RangePerception, GeometricPathPerception
from strategy import Strategy
from weapon import WeaponInstance


class BoundaryInvariantError(ValueError):
    """Invalid timeline/dispatch state; never a request to execute late."""


@dataclass(frozen=True)
class BoundaryContext:
    boundary: int
    interval_start: float


@dataclass(frozen=True)
class EncounterInitiation:
    """The minimal decision that turns an encounter context into an active encounter.

    Awareness is a prerequisite but is not itself sufficient: a participating Being
    must decide to act toward an Entity it is aware of.  ``intent`` is deliberately
    lightweight scaffolding (for example ``approach``, ``flee``, ``communicate``, or
    ``attack``); later Agent decision systems can replace how that intent is chosen.
    """

    actor_id: str
    target_id: str
    intent: str
    time: float

    def to_dict(self):
        return {
            "actor_id": self.actor_id,
            "target_id": self.target_id,
            "intent": self.intent,
            "time": self.time,
        }

@dataclass(frozen=True)
class EncounterStep:
    """Outcome of one bounded Encounter simulation step.

    Movement is applied from a simultaneous position snapshot.  Actions are
    resolved at each crossed integer boundary using the native timeline.
    """

    start_time: float
    end_time: float
    moved_entity_ids: tuple
    completed_action_ids: tuple


# An Encounter is a container for the activity that occurs in a location over a period
# of time. Each Encounter has a start time in seconds from a base epoch that anchors it 
# in a broader historical context. 
class Encounter(Event):
    '''
    A subtype of Event that captures interactions among Encounter entities.
    '''
    def __init__(self, universe, difficulty_class, start_time, end_time=None, 
                 event_type=None, location=None, name="", parent_event_id=None, id=None, 
                 time=None, being_list=None, non_being_object_list=None, 
                 pending_action_list=None, finished_action_list=None,
                 cancelled_action_list=None, initiated=False,
                 map=None, awareness=None, initiation=None, local_frame=None,
                 fatigue_frame_history=None):
        Event.__init__(self, universe, start_time, end_time, 
                 event_type, location, name, parent_event_id, id)
        self.difficulty_class = convert_to_dc(difficulty_class)
        self.initiated = initiated
        self.map = map
        self.set_local_frame(local_frame)
        if time is None:
            self.time = start_time
        else:
            self.time = time
        if (isinstance(self.time, bool) or not isinstance(self.time, (int, float))
                or not math.isfinite(self.time) or self.time < 0):
            raise BoundaryInvariantError('Encounter start time must be finite and nonnegative')
        if self.time != start_time:
            raise BoundaryInvariantError('Restoring an advanced Encounter requires an unsupported checkpoint migration')
        self.last_processed_boundary = math.floor(self.time)
        self.active_boundary = None
        self.boundary_fault = None
        self._coordinator_time = self.time
        self._interval_start = self.time
        self._advancing = False
        self._running = False
        self._dispatching = False
        self._boundary_context = None
        self._choice_book = ChoiceBook(self)
        if being_list is None:
            self.being_list = [] # A list of ids of Beings involved in the Encounter
        else:
            self.being_list = being_list
        if non_being_object_list is None:
            self.non_being_object_list = [] # A list of ids of Objects involved in the Encounter
        else:
            self.non_being_object_list = non_being_object_list
        if pending_action_list is None:
            self.pending_action_list = []
        else:
            self.pending_action_list = pending_action_list
        if finished_action_list is None:
            self.finished_action_list = []
        else:
            self.finished_action_list = finished_action_list
        self.cancelled_action_list = list(cancelled_action_list or [])  # recorded aborted Actions
        # Patch 1: observational Q/B snapshots, not independent combat state.
        self._active_fatigue_frame = None
        # Registry is a transient explicit dependency, not a new save-game meter.
        self._physiology_registry = None
        self.last_fatigue_frame = None
        self.fatigue_frame_history = list(fatigue_frame_history or [])
        # Awareness is directed encounter state: observer Being id -> Entity ids
        # currently known to that observer.  It is deliberately distinct from physical proximity;
        # later sight, hearing, memory, concealment, and other perception systems can
        # decide when awareness should be added or removed.
        self.awareness = {}
        if awareness is not None:
            for observer_id, target_ids in awareness.items():
                self.awareness[observer_id] = set(target_ids)
        if isinstance(initiation, EncounterInitiation):
            self.initiation = initiation
        elif isinstance(initiation, dict):
            self.initiation = EncounterInitiation(**initiation)
        else:
            self.initiation = None

    def to_json(self):
        if self.progression_mode == 'transactional' or self.__dict__.get('_atomic_interval_history') or (self.boundary_fault or {}).get('kind') == 'atomic_publication':
            raise BoundaryInvariantError('Transactional Encounter serialization requires Increment 5C3 compatibility')
        def handle_circular_refs(obj):
            if isinstance(obj, (Universe)):
                return obj.id  # Return only the ID for Universe and Event instances
            return obj.__dict__

        data = {
            "type": self.type,
            "event_type": self.event_type,
            "name": self.name,
            "universe_id": self.universe.get_id(),
            "start_time": self.start_time,
            "end_time": self.end_time,
            "parent_event_id": self.parent_event_id,
            "location": self.location,
            "difficulty_class": self.difficulty_class,
            "initiated": self.initiated,
            "time": self.time,
            "boundary_state": self.boundary_state,
            "choice_state": self.choice_state,
            "initiation": None if self.initiation is None else self.initiation.to_dict(),
            "map": self.map,
            "local_frame": None if self.local_frame is None else self.local_frame.to_dict(),
            "being_list": self.being_list,
            "object_list": self.non_being_object_list,
            "awareness": {
                observer_id: sorted(target_ids)
                for observer_id, target_ids in self.awareness.items()
            },
            "pending_action_list": self.pending_action_list,
            "finished_action_list": self.finished_action_list,
            "cancelled_action_list": self.cancelled_action_list,
            "fatigue_frame_history": list(self.fatigue_frame_history),
        }
        return json.dumps(data, default=handle_circular_refs, sort_keys=False, indent=2)

    # Generate an Encounter.
    def generate(self):
        guard_legacy_encounter(self, "generate")
        if self.map is None:
#            self.map = EncounterMap(location)
            pass
	
    def make_being(self, being_type, name):
        new_being_id = self.universe.make_being(being_type, name)
        self.add_being(new_being_id)
        return new_being_id
    
    def make_object(self, object_type, name):
        new_object_id = self.universe.make_object(object_type, name)
        self.add_object(new_object_id)
        return new_object_id

    def make_weapon(self, weapon_type, name):
        new_weapon_id = self.universe.make_weapon(weapon_type, name)
        self.add_object(new_weapon_id)
        return new_weapon_id

    def make_weapon_for_being(self, being_id, weapon_type, name):
        return self.universe.make_weapon_for_being(being_id, weapon_type, name)
    
    def make_object_for_being(self, being_id, object_type, name):
        new_object_id = self.universe.make_object_for_being(being_id, object_type, name)
        if new_object_id is None:
            return None
        self.non_being_object_list.append(new_object_id)
        return new_object_id

    def make_weapon_for_being(self, being_id, weapon_type, name):
        new_weapon_id = self.universe.make_weapon_for_being(being_id, weapon_type, name)
        if new_weapon_id is None:
            return None
        self.non_being_object_list.append(new_weapon_id)
        return new_weapon_id

    def arm_being(self, being_id, weapon_id, body_location):
        return self.universe.arm_being(being_id, weapon_id, body_location)

    def make_armor_for_being(self, being_id, armor_type, name):
        new_armor_id = self.universe.make_armor_for_being(being_id, armor_type, name)
        if new_armor_id is None:
            return None
        self.non_being_object_list.append(new_armor_id)
        return new_armor_id

    def armor_being(self, being_id, armor_id):
        return self.universe.armor_being(being_id, armor_id)

    def add_object(self, object_id):
        if object_id not in self.non_being_object_list:
            self.non_being_object_list.append(object_id)

    def add_being(self, being_id):
        if being_id not in self.being_list:
            self.being_list.append(being_id)

    def entity_ids(self):
        """Return ids of all participating Encounter entities in stable order.

        At present, spatially participating entities are ``ObjectInstance`` objects:
        Beings first, followed by non-Being Objects.  The method deliberately exposes
        an entity-level view so later Entity subclasses need not change spatial APIs.
        """
        result = []
        for entity_id in self.being_list + self.non_being_object_list:
            if entity_id not in result:
                result.append(entity_id)
        return result

    def get_entity(self, entity_id):
        """Return a participating spatial Entity, or ``None`` if unavailable."""
        if entity_id not in self.entity_ids():
            return None
        entity = self.universe.get_object_by_id(entity_id)
        if not isinstance(entity, ObjectInstance):
            return None
        return entity

    def get_being(self, being_id):
        """Return a participating Being, or ``None`` if it is unavailable."""
        if being_id not in self.being_list:
            return None
        being = self.get_entity(being_id)
        if not isinstance(being, BeingInstance):
            return None
        return being

    def set_local_frame(self, frame):
        """Set or clear the Encounter's optional local *view* of physical space.

        Setting a frame does not transform or change any Entity's persistent
        global position. A local frame is required only by local-coordinate
        accessors and locally expressed movement commands.
        """
        if frame is not None and not isinstance(frame, LocalFrame):
            raise TypeError("local_frame must be a LocalFrame or None")
        self.local_frame = frame

    def entity_local_position(self, entity_id):
        """Return local coordinates for a placed Encounter Entity.

        Unplaced or nonparticipating entities yield ``None``. LocalPosition is
        deliberately distinct from the global CartesianPosition type.
        """
        if self.local_frame is None:
            raise RuntimeError("Encounter has no local frame")
        entity = self.get_entity(entity_id)
        if entity is None or entity.get_position() is None:
            return None
        return self.local_frame.to_local(entity.get_position())

    def global_position(self, local_position):
        """Convert an Encounter-local position to global 3D coordinates."""
        if self.local_frame is None:
            raise RuntimeError("Encounter has no local frame")
        return self.local_frame.to_global(local_position)

    def line_of_sight(self, source_entity_id, target_entity_id, *,
                      source_point=None, target_point=None):
        """Evaluate a single global 3D segment against Encounter Entity geometry.

        Default endpoints are the Entities' reference positions, NOT eye/target
        surface points. Callers may provide explicit CartesianPosition endpoints
        (for example an eye or an exposed point). Source and target volumes are
        excluded. A "clear" result describes only the modeled geometry; this
        does not model terrain, lighting, or other sensory constraints.
        Returns None if an Entity or required position is unavailable.
        """
        source = self.get_entity(source_entity_id)
        target = self.get_entity(target_entity_id)
        if source is None or target is None or source_entity_id == target_entity_id:
            return None
        if source_point is not None and not isinstance(source_point, CartesianPosition):
            raise TypeError("source_point must be a CartesianPosition")
        if target_point is not None and not isinstance(target_point, CartesianPosition):
            raise TypeError("target_point must be a CartesianPosition")
        start = source.get_position() if source_point is None else source_point
        end = target.get_position() if target_point is None else target_point
        if start is None or end is None or start == end:
            return None
        candidates = ((entity_id, self.get_entity(entity_id))
                      for entity_id in self.entity_ids())
        return trace_sightline(start, end, candidates,
                               exclude_ids=(source_entity_id, target_entity_id))

    def perceive_geometric_paths(self, observer_being_id, max_distance):
        """Opt-in path-only perception; not a physical vision model."""
        return self.perceive(observer_being_id, GeometricPathPerception(max_distance))

    def distance_between_entities(self, first_entity_id, second_entity_id):
        """Return continuous 3D distance between two participating entities.

        ``None`` is returned if either entity is not part of this Encounter or has
        not yet been placed in continuous space.
        """
        first = self.get_entity(first_entity_id)
        second = self.get_entity(second_entity_id)
        if first is None or second is None:
            return None
        relation = first.spatial_relation_to(second)
        if relation is None:
            return None
        return relation.distance

    def distance_between_beings(self, first_being_id, second_being_id):
        """Return continuous 3D distance between two participating Beings."""
        if self.get_being(first_being_id) is None or self.get_being(second_being_id) is None:
            return None
        return self.distance_between_entities(first_being_id, second_being_id)

    @staticmethod
    def _validate_max_distance(max_distance):
        try:
            max_distance = float(max_distance)
        except (TypeError, ValueError) as exc:
            raise TypeError("max_distance must be numeric") from exc
        if not math.isfinite(max_distance) or max_distance < 0.0:
            raise ValueError("max_distance must be a finite non-negative number")
        return max_distance

    def entity_within(self, first_entity_id, second_entity_id, max_distance):
        """Return whether two participating, placed entities are within a distance.

        Distance is measured in the units of their shared continuous Cartesian
        reference frame; no grid or cell relation is used.
        """
        max_distance = self._validate_max_distance(max_distance)
        distance = self.distance_between_entities(first_entity_id, second_entity_id)
        return distance is not None and distance <= max_distance

    def within_distance(self, first_entity_id, second_entity_id, max_distance):
        """Compatibility alias for :meth:`entity_within`."""
        return self.entity_within(first_entity_id, second_entity_id, max_distance)

    def entities_within(self, subject_entity_id, max_distance):
        """Return participating entity ids within ``max_distance`` of a subject.

        The subject itself is excluded. Unplaced entities are ignored. Encounter
        order is preserved for deterministic downstream perception or interaction
        processing.
        """
        if self.get_entity(subject_entity_id) is None:
            return []
        result = []
        for entity_id in self.entity_ids():
            if entity_id == subject_entity_id:
                continue
            if self.entity_within(subject_entity_id, entity_id, max_distance):
                result.append(entity_id)
        return result

    def beings_within(self, subject_entity_id, max_distance):
        """Return nearby participating Being ids."""
        return [
            entity_id for entity_id in self.entities_within(subject_entity_id, max_distance)
            if isinstance(self.get_entity(entity_id), BeingInstance)
        ]

    def objects_within(self, subject_entity_id, max_distance):
        """Return nearby participating non-Being Object ids."""
        return [
            entity_id for entity_id in self.entities_within(subject_entity_id, max_distance)
            if not isinstance(self.get_entity(entity_id), BeingInstance)
        ]

    def mark_aware(self, observer_being_id, target_entity_id):
        """Record directed awareness of an Encounter entity by a Being."""
        if observer_being_id == target_entity_id:
            return False
        if self.get_being(observer_being_id) is None or self.get_entity(target_entity_id) is None:
            return False
        targets = self.awareness.setdefault(observer_being_id, set())
        before = len(targets)
        targets.add(target_entity_id)
        return len(targets) != before

    def clear_awareness(self, observer_being_id, target_entity_id):
        """Remove directed awareness, returning whether stored state changed."""
        targets = self.awareness.get(observer_being_id)
        if targets is None or target_entity_id not in targets:
            return False
        targets.remove(target_entity_id)
        if not targets:
            del self.awareness[observer_being_id]
        return True

    def is_aware(self, observer_being_id, target_entity_id):
        """Return whether directed awareness of an entity is recorded."""
        return target_entity_id in self.awareness.get(observer_being_id, set())

    def aware_entities(self, observer_being_id):
        """Return participating entity ids currently known to the observer."""
        if self.get_being(observer_being_id) is None:
            return []
        targets = self.awareness.get(observer_being_id, set())
        return [entity_id for entity_id in self.entity_ids() if entity_id in targets]

    def aware_beings(self, observer_being_id):
        """Return participating Being ids currently known to the observer."""
        return [
            entity_id for entity_id in self.aware_entities(observer_being_id)
            if isinstance(self.get_entity(entity_id), BeingInstance)
        ]

    def aware_objects(self, observer_being_id):
        """Return participating non-Being Object ids currently known to the observer."""
        return [
            entity_id for entity_id in self.aware_entities(observer_being_id)
            if not isinstance(self.get_entity(entity_id), BeingInstance)
        ]

    def perceive(self, observer_being_id, perception_model):
        """Apply a perception model and convert successful observations to awareness.

        The model determines what is perceptible; Encounter owns the directed
        awareness state.  Returned observations retain the explicit basis used by
        the model so callers can inspect why awareness was acquired.
        """
        if not hasattr(perception_model, "detect"):
            raise TypeError("perception_model must provide a detect() method")
        observations = perception_model.detect(self, observer_being_id)
        for observation in observations:
            self.mark_aware(observation.observer_id, observation.target_id)
        return observations

    def perceive_within(self, observer_being_id, max_distance):
        """Use the temporary range-only perception model for an observer.

        This convenience method is scaffolding for the first perception bridge;
        it should not be interpreted as a claim that proximity alone implies
        real-world perception.
        """
        return self.perceive(observer_being_id, RangePerception(max_distance))

    def decide_to_act(self, actor_being_id, target_entity_id, intent="act"):
        """Initiate this Encounter when an aware Being decides to act.

        Awareness is required but does not itself initiate the Encounter.  The
        target may be any participating Entity, allowing a Being to react to an
        object as well as another Being.  The first successful decision is retained
        as the initiation record; later decisions belong to the Encounter cycle.

        Returns the :class:`EncounterInitiation` record on success, otherwise
        ``None``.
        """
        if self.initiated:
            return None
        if self.get_being(actor_being_id) is None:
            return None
        if self.get_entity(target_entity_id) is None:
            return None
        if not self.is_aware(actor_being_id, target_entity_id):
            return None
        if not isinstance(intent, str):
            raise TypeError("intent must be a string")
        intent = intent.strip()
        if not intent:
            raise ValueError("intent must not be empty")

        self.initiation = EncounterInitiation(
            actor_id=actor_being_id,
            target_id=target_entity_id,
            intent=intent,
            time=self.time,
        )
        self.initiated = True
        return self.initiation

    def prepare_action(self, action, *, _proposed_actions=None, _target_action_id=None):
        """Prepare and validate one native schedule without publishing effects.

        No opaque extension callback is invoked. Native preparers treat this
        Encounter and their Action as read-only; initialization is returned as
        data and applied only by schedule_action after final validation.
        """
        self._assert_timeline()
        from transactional_progression import validate_action_contract
        validate_action_contract(self, action)
        preparer = native_preparer(action)
        if not self.initiated:
            raise RuntimeError("Encounter must be initiated before scheduling actions")
        if action.universe is not self.universe:
            raise ValueError("action must belong to this Universe")
        from melee_defense import MeleeDefense
        if type(action) is MeleeDefense:
            prepared = preparer(action, self, proposed_actions=_proposed_actions,
                                target_action_id=_target_action_id)
        else:
            prepared = preparer(action, self)
        self._validate_prepared_schedule(action, prepared)
        return prepared

    def _validate_prepared_schedule(self, action, prepared):
        if not isinstance(prepared, PreparedSchedule) or prepared.action_id != action.id:
            raise ValueError("preparation must describe this Action")
        for name in ('actor_id', 'target_id', 'instrument_id', 'parent_event_id', 'start_time'):
            if getattr(prepared, name) != getattr(action, name):
                raise ValueError(f"prepared {name} does not match the Action declaration")
        if self.get_being(prepared.actor_id) is None:
            raise ValueError("action actor must be a participating Being")
        if prepared.target_id is not None and self.get_entity(prepared.target_id) is None:
            raise ValueError("action target must be a participating Entity")
        if prepared.parent_event_id not in (None, self.id):
            raise ValueError("action belongs to a different parent Event")
        times = (prepared.start_time, prepared.end_time, self.time)
        if any(isinstance(t, bool) or not isinstance(t, (int, float))
               or not math.isfinite(t) for t in times):
            raise ValueError("finalized action times and Encounter time must be finite numbers")
        if prepared.end_time - prepared.start_time < 1:
            raise ValueError('finalized Action duration must be at least one second')
        boundary = math.ceil(prepared.end_time)
        if boundary <= self.last_processed_boundary or (
                self.active_boundary is not None and boundary <= self.active_boundary):
            raise BoundaryInvariantError('Cannot schedule into an active or already processed boundary')
        if (self.time < 0 or prepared.start_time < 0 or prepared.start_time < self.time
                or prepared.end_time - prepared.start_time < 1):
            raise ValueError("finalized Action must start at or after time zero and now, "
                             "with duration at least one second")
        if self.end_time is not None and prepared.end_time > self.end_time:
            raise ValueError("action would finish after the Encounter end time")
        if self.end_time is not None and boundary > self.end_time:
            raise ValueError("Action resolution boundary would exceed the Encounter end time")
        if (prepared.instrument_id is not None and
                self.universe.get_object_by_id(prepared.instrument_id) is None):
            raise ValueError("action instrument must be an existing Object")
        if (len(prepared.active_object_ids) != len(set(prepared.active_object_ids))
                or any(self.universe.get_object_by_id(resource) is None
                       for resource in prepared.active_object_ids)):
            raise ValueError("prepared active Objects must be distinct existing Objects")
        if action.id in self.pending_action_list or action.id in self.finished_action_list:
            raise ValueError("action is already scheduled or completed")
        registered = self.universe.get_event_by_id(action.id)
        if registered is not None and registered is not action:
            raise ValueError("an Event with this id already exists")
        allowed = {'start_position', '_encounter', 'ready_at', 'threat_at_schedule', 'target_action_id'}
        names = [name for name, _ in prepared.initialization]
        if len(names) != len(set(names)) or any(name not in allowed for name in names):
            raise ValueError("unsupported prepared initialization fields")
        for name, value in prepared.initialization:
            if name == '_encounter' and value is not self:
                raise ValueError("prepared binding must refer to this Encounter")
            if name == 'ready_at' and (isinstance(value, bool)
                    or not isinstance(value, (int, float)) or not math.isfinite(value)
                    or not prepared.start_time <= value <= prepared.end_time):
                raise ValueError("prepared readiness must lie within the finalized Action")

    def propose_choice(self, actions):
        planning_entry(self)
        return self._choice_book.propose(actions)

    def edit_choice(self, draft, actions):
        planning_entry(self)
        return self._choice_book.edit(draft, actions)

    def validate_choice(self, draft, *, replacing=None):
        planning_entry(self)
        with self._choice_book.lock:
            return self._choice_book.validate(draft, replacing=self._choice_id(replacing))

    def accept_valid_choice(self, validation):
        planning_entry(self)
        return self._choice_book.accept(validation)

    def _choice_id(self, choice):
        if isinstance(choice, ChoiceView):
            if self._choice_book.view(choice.id) != choice:
                from action_choice import ChoiceRejected, ChoiceDiagnostic
                raise ChoiceRejected((ChoiceDiagnostic('stale_choice', 'choice',
                    'The choice changed; inspect the current version before editing'),))
            return choice.id
        return choice

    def undo_choice(self, choice):
        planning_entry(self)
        with self._choice_book.lock:
            return self._choice_book.undo(self._choice_id(choice))

    def replace_choice(self, choice, validation):
        planning_entry(self)
        with self._choice_book.lock:
            return self._choice_book.replace(self._choice_id(choice), validation)

    def publish_choice(self, choice):
        guard_legacy_encounter(self, "direct choice publication; transactional start fences publish the whole choice")
        with self._choice_book.lock:
            return self._choice_book.publish(self._choice_id(choice))

    def get_choice(self, choice_id):
        return self._choice_book.view(choice_id)

    def choice_for_action(self, action_id):
        return self._choice_book.for_action(action_id)

    @property
    def active_reservations(self):
        return self._choice_book.reservations

    @property
    def choice_state(self):
        return self._choice_book.summary()

    def schedule_action(self, action, *, interrupt_action_id=None):
        """Single-item adapter to the same whole-choice/resource validator.

        Current starts publish and begin before returning (after settlement if
        called during a boundary). Future starts reserve now and publish later.
        """
        planning_entry(self)
        validate_action_contract(self, action)
        return self._choice_book.schedule_single(action, interrupt_action_id)

    def schedule_choice(self, actions):
        """Immediate/future complete-set convenience adapter to the same book."""
        planning_entry(self)
        validate_choice_actions(self, actions)
        return self._choice_book.schedule_complete(actions)

    def cancel_action(self, action_id, *, reason='interrupted'):
        planning_entry(self)
        with self._choice_book.lock:
            return self._cancel_action(action_id, reason=reason)

    def _cancel_action(self, action_id, *, reason='interrupted'):
        """Withdraw a pending Action, retaining the Event as evidence of intent.

        It has no resolution, completion, damage, or practice award.  Repeated
        cancellation or attempts to cancel a finished action are rejected.
        """
        self._assert_timeline()
        if action_id not in self.pending_action_list:
            raise ValueError('action is not pending')
        action = self.universe.get_event_by_id(action_id)
        if not isinstance(action, Action):
            raise ValueError('only pending Actions may be canceled')
        self._choice_book.assert_registered(action)
        self.pending_action_list.remove(action_id)
        action.canceled_at = self.time
        action.cancellation_reason = reason
        self.cancelled_action_list.append(action_id)
        self._choice_book.cancelled(action_id)
        return action

    def record_skill_use(self, action_id, skill_name, experience=0, outcome=None):
        """Attribute documented practice to a Being after a completed Action.

        Action prerequisites are not evidence that a skill was exercised. The
        caller supplies the skill and experience awarded by the actual resolver.
        Duplicate awards for the same action/skill are rejected by the Being.
        """
        if action_id not in self.finished_action_list:
            raise ValueError('skill use requires a completed Encounter action')
        action = self.universe.get_event_by_id(action_id)
        if not isinstance(action, Action):
            raise ValueError('action_id must refer to an Action')
        if action.actor_id not in self.being_list:
            raise ValueError('the acting Being must participate in the Encounter')
        actor = self.universe.get_object_by_id(action.actor_id)
        if not isinstance(actor, BeingInstance):
            raise ValueError('only Beings can exercise skills at this stage')
        return actor.record_skill_use(
            self.universe.get_skill_dictionary(), skill_name, experience,
            action_id=action_id, time=action.end_time, outcome=outcome)

    def set_physiology_registry(self, registry):
        """Opt in to resolving versioned physiology at the snapshot boundary."""
        from physiology_registry import PhysiologyRegistry
        if not isinstance(registry, PhysiologyRegistry):
            raise TypeError('registry must be a PhysiologyRegistry')
        self._physiology_registry = registry

    def capture_evaluation_snapshot(self, boundary, *, rng_state=None):
        """Inactive Increment 4 read boundary; never progresses or resolves.

        A caller must supply post-movement, pre-action state at this exact
        integer fence. The live dispatcher remains sequential and unchanged.
        """
        from action_evaluation import capture_snapshot
        return capture_snapshot(self, boundary, rng_state=rng_state)

    @property
    def progression_mode(self):
        from transactional_progression import mode_of
        return mode_of(self)

    def enable_transactional_progression(self, *, quiescent=False, rng_owner=None):
        from transactional_progression import enable_transactional_progression
        return enable_transactional_progression(self, quiescent=quiescent, rng_owner=rng_owner)

    def recover_transactional_progression(self, token):
        from transactional_progression import recover_transactional_progression
        return recover_transactional_progression(self, token)

    def inspect_committed(self, boundary=None, *, receipt=None):
        """Detached omniscient committed results; never a command or save API."""
        from encounter_inspection import inspect_encounter
        return inspect_encounter(self, boundary, receipt=receipt)

    def assert_legacy_consumer(self):
        from transactional_progression import guard_legacy_encounter
        guard_legacy_encounter(self, 'legacy facade/UI/replay consumer')

    def prepare_interval_candidate(self, next_boundary, *, velocities=None,
                                   velocity_frame="global", rng_state=None, rng_owner=None):
        """Inactive one-interval staging; never advances or publishes live state."""
        from interval_staging import prepare_interval_candidate
        return prepare_interval_candidate(self, next_boundary, velocities=velocities,
            velocity_frame=velocity_frame, rng_state=rng_state, rng_owner=rng_owner)

    def _capture_fatigue_frame(self):
        return FrozenFatigueFrame((self.get_being(being_id)
                                   for being_id in self.being_list),
                                  registry=self._physiology_registry)

    def propose_physical_fatigue(self, timeline, *, max_step=0.25):
        """Pure proposed Q/B from the last native post-movement frame.

        Deliberately does not commit; action/damage effects are still sequential
        in the legacy resolver. Only Patch 3 may integrate atomic settlement.
        """
        if self.last_fatigue_frame is None:
            raise RuntimeError('no Encounter fatigue snapshot is available')
        if not self.fatigue_frame_history or abs(
                timeline.end - self.fatigue_frame_history[-1]['time']) > 1e-9:
            raise ValueError('work must end at the last completed step')
        if not self.fatigue_frame_history or abs(
                timeline.start - self.fatigue_frame_history[-1]['start']) > 1e-9:
            raise ValueError('work interval must match the latest Encounter step')
        return self.last_fatigue_frame.propose_work(timeline, max_step=max_step)

    def fatigue_view(self, being_id):
        """Read the common post-movement Q/B view *during* action resolution."""
        if self._active_fatigue_frame is None:
            raise RuntimeError('no active frozen Encounter fatigue frame')
        return self._active_fatigue_frame.view(being_id)

    @property
    def boundary_state(self):
        """Diagnostic cursor surface, not an authoritative restore format."""
        return {'version': 1, 'time': self.time,
                'last_processed': self.last_processed_boundary,
                'active': self.active_boundary,
                'fault': None if self.boundary_fault is None else dict(self.boundary_fault)}

    def _assert_timeline(self):
        if self.boundary_fault is not None:
            if self.boundary_fault.get('kind') == 'atomic_publication':
                raise BoundaryInvariantError('Atomic publication stopped: ' + self.boundary_fault['rollback']
                    + '; explicit controlled recovery is required')
            raise BoundaryInvariantError(
                'Encounter progression is faulted; legacy movement/effects/RNG may remain. '
                'Checkpoint recovery is not implemented; do not retry this state')
        if (isinstance(self.time, bool) or not isinstance(self.time, (int, float))
                or not math.isfinite(self.time) or self.time != self._coordinator_time):
            raise BoundaryInvariantError('Encounter clock changed outside the boundary coordinator')
        if type(self.last_processed_boundary) is not int:
            raise BoundaryInvariantError('Invalid boundary cursor')
        expected = math.floor(self.time)
        if self.active_boundary is None:
            if self.last_processed_boundary != expected:
                raise BoundaryInvariantError('Skipped, duplicate, or inconsistent boundary cursor')
        elif (self.active_boundary != self.last_processed_boundary + 1
              or self.time != self.active_boundary):
            raise BoundaryInvariantError('Out-of-order active boundary')

    def _pending_schedule(self):
        """Preflight all references/deadlines, including future pending Actions.

        Missing instruments remain ordinary weapon-unavailable outcomes. Missing
        actor/target registry entries are corrupt references, not new targets.
        """
        self._assert_timeline()
        seen = set()
        pending = []
        for index, action_id in enumerate(self.pending_action_list):
            if action_id in seen or action_id in self.finished_action_list or action_id in self.cancelled_action_list:
                raise BoundaryInvariantError('Duplicate or conflicting pending Action lifecycle')
            seen.add(action_id)
            action = self.universe.get_event_by_id(action_id)
            if not isinstance(action, Action) or action.id != action_id or action.parent_event_id != self.id:
                raise BoundaryInvariantError(f'Missing/invalid pending Action reference: {action_id}')
            times = (action.start_time, action.end_time)
            if (any(isinstance(t, bool) or not isinstance(t, (int, float))
                    or not math.isfinite(t) for t in times)
                    or action.start_time < 0 or action.end_time - action.start_time < 1):
                raise BoundaryInvariantError(f'Invalid pending Action deadline/duration: {action_id}')
            boundary = math.ceil(action.end_time)
            if boundary <= self.last_processed_boundary:
                raise BoundaryInvariantError(f'Overdue Action for boundary {boundary}: {action_id}')
            if self.get_being(action.actor_id) is None or (action.target_id is not None
                    and self.get_entity(action.target_id) is None):
                raise BoundaryInvariantError(f'Missing pending Action actor/target: {action_id}')
            if self.end_time is not None and boundary > self.end_time:
                raise BoundaryInvariantError('Pending Action resolves beyond Encounter end')
            self._choice_book.assert_registered(action)
            pending.append((index, action, boundary))
        self._choice_book.assert_accepted()
        return pending

    def assert_checkpoint_exportable(self, *, replay=False):
        self._assert_timeline()
        if self.progression_mode == 'transactional' or self.__dict__.get('_atomic_interval_history'):
            raise BoundaryInvariantError('Transactional checkpoint/replay compatibility requires Increment 5C3')
        if (self._advancing or self._running or self.active_boundary is not None
                or (self.time != self.start_time and self.time != self.last_processed_boundary)):
            raise BoundaryInvariantError('Only a completed boundary checkpoint can be saved')
        self._pending_schedule()
        self._choice_book.assert_exportable(replay=replay)

    def validate_progression_entry(self):
        """Facade preflight before choices, strategy changes, or policy/RNG use."""
        guard_legacy_encounter(self, "validate_progression_entry")
        if self._advancing or self._dispatching or self._running:
            raise BoundaryInvariantError('Reentrant progression/choice entry')
        self._pending_schedule()

    def step(self, duration=1.0, velocities=None, velocity_frame="global"):
        """Advance fractional kinematics; dispatch only crossed integer boundaries."""
        if self._running:
            raise BoundaryInvariantError('Reentrant progression during run()')
        return self._advance(duration, velocities, velocity_frame)

    def _advance(self, duration, velocities=None, velocity_frame="global"):
        from transactional_progression import mode_of, step_transactionally
        if mode_of(self) == 'transactional':
            return step_transactionally(self, duration, velocities, velocity_frame)
        if self._advancing or self._dispatching:
            raise BoundaryInvariantError('Reentrant Encounter advancement')
        if not self.initiated:
            raise RuntimeError("Encounter must be initiated before stepping")
        self._pending_schedule()
        try:
            duration = float(duration)
        except (TypeError, ValueError) as exc:
            raise TypeError("duration must be numeric") from exc
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("duration must be finite and positive")
        start = self.time
        end = start + duration
        if not math.isfinite(end) or end <= start:
            raise ValueError("Encounter time overflow or unrepresentable advance")
        if self.end_time is not None and end > self.end_time:
            raise ValueError("step would exceed the Encounter end time")
        if velocity_frame not in ("global", "local"):
            raise ValueError("velocity_frame must be 'global' or 'local'")
        if velocity_frame == "local" and self.local_frame is None:
            raise RuntimeError("Encounter has no local frame")
        velocities = {} if velocities is None else velocities
        if not hasattr(velocities, "items"):
            raise TypeError("velocities must be a mapping of Entity ids to 3D vectors")
        motion = []
        for entity_id, vector in velocities.items():
            entity = self.get_entity(entity_id)
            if entity is None or entity.get_position() is None:
                raise ValueError("moving Entity must participate and have a continuous position")
            try:
                vx, vy, vz = vector
                vx, vy, vz = float(vx), float(vy), float(vz)
            except (TypeError, ValueError) as exc:
                raise TypeError("velocity must have three numeric components") from exc
            if not all(math.isfinite(v) for v in (vx, vy, vz)):
                raise ValueError("velocity components must be finite")
            if velocity_frame == "local":
                vx, vy, vz = self.local_frame.vector_to_global((vx, vy, vz))
            previous = entity.get_position()
            # Validate the complete requested displacement before any movement.
            integrate_position(previous, (vx, vy, vz), duration)
            motion.append((entity_id, entity, (vx, vy, vz)))
        if self._physiology_registry is not None:
            for being_id in self.being_list:
                for mode in ('ordinary', 'running'):
                    self._physiology_registry.resolve(self.get_being(being_id), mode=mode)

        self._choice_book.publish_due(self.time)
        completed = []
        self._advancing = True
        try:
            while self.time < end:
                self._pending_schedule()
                boundary = self.last_processed_boundary + 1
                destination_time = min(end, boundary, self._choice_book.next_start(self.time))
                dt = destination_time - self.time
                destinations = []
                for entity_id, entity, (vx, vy, vz) in motion:
                    if self.get_entity(entity_id) is not entity:
                        raise BoundaryInvariantError('Moving Entity reference changed during progression')
                    previous = entity.get_position()
                    destinations.append((entity, integrate_position(previous, (vx, vy, vz), dt)))
                for entity, position in destinations:
                    entity.set_position(position)
                self.time = float(destination_time)
                self._coordinator_time = self.time
                if destination_time == boundary:
                    self.active_boundary = boundary
                    context = BoundaryContext(boundary, self._interval_start)
                    self._boundary_context = context
                    self._active_fatigue_frame = self._capture_fatigue_frame()
                    self.last_fatigue_frame = self._active_fatigue_frame
                    completed.extend(self.resolve_actions(as_of=boundary, _context=context))
                    self.update_environment()
                    self._assert_timeline()
                    self.fatigue_frame_history.append({
                        'start': self._interval_start, 'time': self.time,
                        'views': self.last_fatigue_frame.to_dict()})
                    self.last_processed_boundary = boundary
                    self._interval_start = self.time
                    self.active_boundary = None
                    self._boundary_context = None
                    self._active_fatigue_frame = None
                    self._choice_book.settled(boundary)
                self._choice_book.publish_due(self.time)
            return EncounterStep(start, end, tuple(item[0] for item in motion), tuple(completed))
        except Exception as exc:
            if isinstance(exc, ChoiceRejected) and self.active_boundary is None and not self._dispatching:
                exc.add_note('Progression paused at a planning/start fence; earlier physical progression '
                             'remains. Correct the selection or settle its prior commitment before continuing.')
                raise
            self.boundary_fault = {
                'time': self.time, 'boundary': self.active_boundary,
                'last_processed': self.last_processed_boundary,
                'error': type(exc).__name__, 'message': str(exc)}
            exc.add_note('Increment 2 stops here: sequential legacy movement/effects/RNG may remain; '
                         'this Encounter cannot be retried or saved without future checkpoint recovery.')
            raise
        finally:
            self._advancing = False
            self._dispatching = False
            self.active_boundary = None
            self._boundary_context = None
            self._active_fatigue_frame = None

    def run(self, run_children=True):
        """Choose at the current instant, then use the same boundary walker as step."""
        guard_legacy_encounter(self, "run")
        if self._running or self._advancing or self._dispatching:
            raise BoundaryInvariantError('Reentrant Encounter run')
        self._pending_schedule()
        if not self.initiated:
            self.generate()
        if not self.initiated:
            raise RuntimeError('Encounter must be initiated before running')
        self._running = True
        try:
            continue_turns = True
            while continue_turns and (self.end_time is None or self.time < self.end_time):
                self._pending_schedule()
                # The native movement hook has no model; optional velocity
                # output uses the existing constant-velocity step interface.
                velocities = self.choose_movement()
                self.choose_fight_actions()
                target = self.last_processed_boundary + 1
                if self.end_time is not None:
                    target = min(target, self.end_time)
                self._advance(target - self.time, velocities)
                continue_turns = self.keep_going()
        except ChoiceRejected:
            # Invalid planning is editable input, not a simulation fault. If
            # an exception escaped an executing legacy callback, _advance has
            # already latched its separate partial-effect safety stop.
            raise
        except Exception as exc:
            if self.boundary_fault is None:
                self.boundary_fault = {
                    'time': self.time, 'boundary': None, 'phase': 'run-choice',
                    'last_processed': self.last_processed_boundary,
                    'error': type(exc).__name__, 'message': str(exc)}
                exc.add_note('run() stopped: legacy choices/RNG may remain; checkpoint recovery is not implemented.')
            raise
        finally:
            self._running = False

    def keep_going(self):
        # Do one round
#       return self.do_one_round()

        # Go until one or no one left standing
#        return self.last_one_standing()

        # Go until one or no one left running
        guard_legacy_encounter(self, "keep_going")
        return self.last_one_running()

    def do_one_round(self):
        # Do just one round
        if self.time == 1:
            return False
        return True

    def last_one_standing(self):
        # Go until one or no one has positive hit points
        being_count = len(self.being_list)
        beings_alive = 0
        for being_id in self.being_list:
            being = self.universe.get_object_by_id(being_id)
#            print(f"Current hit points for {being.name}: {being.current.hit_points}")
            if being.current.hit_points > 0:
                beings_alive += 1
                if beings_alive > 1:
                    return True
        return False

    def last_one_running(self):
        # Go until one or no one is not exhausted
        being_count = len(self.being_list)
        beings_exhausted = 0
        for being_id in self.being_list:
            being = self.universe.get_object_by_id(being_id)
            fatigue = being.get_fatigue_level()
            print(f"Current fatigue for {being.name}: {fatigue}")
            if fatigue > 4: # Preserve the legacy continuation predicate.
                beings_exhausted += 1
                if beings_exhausted > 1:
                    return True
        return False

    def choose_movement(self):
        guard_legacy_encounter(self, "choose_movement")
        pass

    def move(self):
        # If not immobile
        guard_legacy_encounter(self, "move")
        pass

    def resolve_actions(self, as_of=None, *, _context=None):
        """Dispatch one coordinator-owned boundary; direct calls are unsupported.

        Eligibility and Q/B are frozen for the batch, but legacy action effects
        still execute sequentially. This is not a world-state transaction.
        """
        guard_legacy_encounter(self, "resolve_actions")
        if (isinstance(as_of, bool) or not isinstance(as_of, (int, float))
                or not math.isfinite(as_of) or as_of < 1 or as_of != math.floor(as_of)):
            raise BoundaryInvariantError('Action dispatch requires a positive integer boundary')
        if (self._dispatching or not self._advancing or _context is None
                or _context is not self._boundary_context
                or _context.boundary != as_of or self.active_boundary != as_of
                or self.time != as_of or self.last_processed_boundary + 1 != as_of):
            raise BoundaryInvariantError('Direct, duplicate, or reentrant dispatch lacks a boundary context')
        pending = self._pending_schedule()
        ordered = [(index, action, action.end_time) for index, action, boundary in pending
                   if boundary == as_of]
        ordered.sort(key=lambda item: (getattr(item[1], 'resolution_priority', 0), item[0]))
        completed = []
        self._dispatching = True
        try:
            # One eligibility group even when nominal ends differ fractionally.
            for _, candidate, _ in ordered:
                freeze = getattr(candidate, 'capture_simultaneous_eligibility', None)
                if freeze is not None:
                    candidate._simultaneous_eligibility = freeze()
            for _, action, nominal_end in ordered:
                if action.id not in self.pending_action_list:
                    if action.id in self.cancelled_action_list:
                        continue  # A legitimate interruption, not late execution.
                    raise BoundaryInvariantError('Due Action disappeared from the pending schedule')
                self._pending_schedule()
                if action.end_time != nominal_end:
                    raise BoundaryInvariantError('Due Action deadline changed during dispatch')
                resolution = action.resolve(self.difficulty_class)
                if isinstance(resolution, ActionResolution):
                    # Preflight the entire award set before updating any skill.
                    # A resolver returning None retains legacy, no-award behavior.
                    if not isinstance(action, Action):
                        if resolution.skill_exercises or resolution.observations:
                            raise ValueError("Only Actions can report exercised skills or observations")
                    else:
                        actor = self.get_being(action.actor_id)
                        if actor is None:
                            raise ValueError("Resolving Action has no participating Being")
                        # Observations are declarative consequences. Validate them
                        # before applying experience, so invalid observations cannot
                        # cause partial practice awards or spurious awareness.
                        for observation in resolution.observations:
                            if observation.observer_id != action.actor_id:
                                raise ValueError("Action observation must belong to its actor")
                            if (observation.target_id == action.actor_id or
                                    self.get_entity(observation.target_id) is None):
                                raise ValueError("Action observation target must be another Encounter Entity")
                        skills = self.universe.get_skill_dictionary()
                        for exercise in resolution.skill_exercises:
                            actor.validate_skill_use(
                                skills, exercise.skill_name, exercise.experience,
                                action_id=action.id, time=action.end_time,
                                outcome=resolution.outcome)
                        for exercise in resolution.skill_exercises:
                            actor.record_skill_use(
                                skills, exercise.skill_name, exercise.experience,
                                action_id=action.id, time=action.end_time,
                                outcome=resolution.outcome)
                        for observation in resolution.observations:
                            self.mark_aware(observation.observer_id, observation.target_id)
                        action.resolution = resolution
                self.pending_action_list.remove(action.id)
                self.finished_action_list.append(action.id)
                self._choice_book.completed(action.id)
                on_completed = getattr(action, 'on_completed', None)
                if on_completed is not None:
                    on_completed(self)
                completed.append(action.id)
            return completed
    
        finally:
            for _, candidate, _ in ordered:
                if hasattr(candidate, '_simultaneous_eligibility'):
                    candidate._simultaneous_eligibility = None
            self._dispatching = False

    def update_environment(self):
        pass

    def is_being_occupied(self, being_id):
        if self._choice_book.actor_planned_now(being_id):
            return True
        for action_id in self.pending_action_list:
            action = self.universe.get_event_by_id(action_id)
            if action.actor_id == being_id and action.start_time <= self.time:
                if action.event_type == "delay":
                    return False
                if math.ceil(action.end_time) > self.time:
                    return True
        return False

    def choose_target_being(self, subject_being_id):
        if len(self.being_list) == 0:
            return None
        if len(self.being_list) == 1:
            return subject_being_id
        while True:
            choice = random.choice(self.being_list)
            if choice != subject_being_id:
                return choice

    def choose_target_object(self, subject_being_id):
#        print(f"Encounter Objects: {self.non_being_object_list}")
        # TODO: Could implement logic about whose Object
        if len(self.non_being_object_list) == 0:
            return None
        choice = random.choice(self.non_being_object_list)
        return choice

    def choose_target_attack(self, subject_being_id):
        # Make a list of attacks that aren't mine to try to target
        attack_list = None
        return random.choice(self.attack_list)

    def choose_target_weapon(self, subject_being_id):
        # Make a list of possible target weapons
        weapon_list = None
        return random.choice(self.weapon_list)

    def choose_fight_actions(self):
        # Decide the complete native AI set before registering any member.
        # Rejected planning consumes no authoritative selection RNG.
        guard_legacy_encounter(self, "choose_fight_actions")
        before_rng = random.getstate()
        try:
            proposed = self._propose_fight_actions()
            if len(proposed) == 1:
                self.schedule_action(proposed[0])
            elif proposed:
                self.schedule_choice(proposed)
        except ChoiceRejected:
            random.setstate(before_rng)
            raise

    def _propose_fight_actions(self):
        proposed = []
        action_dict = self.universe.get_action_dictionary()
        object_registry = self.universe.object_registry

        for subject_being_id in self.being_list:
            subject_being = self.universe.get_object_by_id(subject_being_id)
#            print(f"Choosing fight action for {subject_being.name}")

            if subject_being.is_dead():
#                print(f"{subject_being.name} is dead")
                continue

            if subject_being.is_helpless():
#                print(f"{subject_being.name} is helpless")
                continue

            if self.is_being_occupied(subject_being_id):
#                print(f"{subject_being.name} is occupied")
                continue

            target = None
            new_action = None
            if isinstance(subject_being, (BeingInstance)):
                # Randomly decide an melee action among those available
                chosen_action = subject_being.choose_melee_action(self.universe)
                # At this point the chosen action should already be one the Being has
                # the required skills to do.
#                print(f"chosen action: {chosen_action}")
                action_definition = action_dict.get_action_definition(chosen_action)
                target_id = None
                target = None
                # If the Action requires a target Being, choose the target
                if action_definition["target_type"] == 'being':
                    target_id = self.choose_target_being(subject_being_id)
                    target = self.universe.get_object_by_id(target_id)
                # Otherwise if the Action requires a target Object, choose the target
                elif action_definition["target_type"] == 'object':
                    target_id = self.choose_target_object(subject_being_id)
                    target = self.universe.get_object_by_id(target_id)
                # Otherwise if the Action requires a target Attack, choose the target
#                 elif action_definition["target_type"] == 'attack':
#                     target_id = self.choose_target_attack(subject_being_id)
#                     #target = self.universe.get_object_by_id(target_id)
                # Otherwise if the Action requires a target Attack, choose the target
                elif action_definition["target_type"] == 'weapon':
                    target_id = self.choose_target_weapon(subject_being_id)
                    target = self.universe.get_object_by_id(target_id)
                # Otherwise no target is necessary

                # Create an Action Event with the Encounter as its parent
                armed = subject_being.armed_with(self.universe)
#                print(f"armed: {armed}")
                weapon_id = subject_being.choose_weapon(armed)
                weapon = self.universe.get_object_by_id(weapon_id)
#                print(f"weapon_id: {weapon_id} weapon_type: {weapon.obj_type}, weapon_name: {weapon.name}")
                if "swing" in chosen_action:
                    name = f"{subject_being.name} swing t={self.time}"
                    new_action = Action(self.universe, start_time=self.time, 
                        end_time=None, event_type="swing", actor_id=subject_being_id, 
                        target_id=target_id, instrument_id=weapon_id, strategy=None, 
                        location=None, name=name, parent_event_id=self.id)
                elif "thrust" in chosen_action:
                    name = f"{subject_being.name} thrust at t={self.time}"
                    new_action = Action(self.universe, start_time=self.time, 
                        end_time=None, event_type="thrust", actor_id=subject_being_id, 
                        target_id=target_id, instrument_id=weapon_id, strategy=None, 
                        location=None, name=name, parent_event_id=self.id)
                else:
                    pass

#                print(f"{subject_being.name} targets {target.name} with {chosen_action} using {weapon.name}")
#                print(f"{subject_being.name} targets {target.name} with {chosen_action} using {weapon.name} ending at t={new_action.end_time}")
                # Add Action to the Event History
                if new_action is not None:
                    proposed.append(new_action)
        return proposed

    def choose_actions(self):
        guard_legacy_encounter(self, "choose_actions")
        for subject_being_id in self.being_list:
            subject_being = self.universe.get_object_by_id(subject_being_id)
            if isinstance(subject_being, (BeingInstance)):
                # Randomly decide an action among those available
                chosen_action = subject_being.choose_action(self.universe.get_action_dictionary(), self.universe.get_weapon_dictionary())
#                print(f"{subject_being.name} chose the Action {chosen_action}")
                # At this point the chosen action should already be one the Being has
                # the required skills to do.
                action_definition = self.universe.get_action_definition(chosen_action)
                target_id = None
                # If the Action requires a target Being, choose the target
                if action_definition["target_type"] == 'being':
                    target_id = self.choose_target_being(subject_being_id)
                    target = self.universe.get_object_by_id(target_id)
#                    print(f"Target being for {subject_being.name} is {target.name}")
                # Otherwise if the Action requires a target Object, choose the target
                elif action_definition["target_type"] == 'object':
                    target_id = self.choose_target_object(subject_being_id)
                    target = self.universe.get_object_by_id(target_id)
#                    print(f"Target object for {subject_being.name} is {target.name}")
                # Otherwise if the Action requires a target Attack, choose the target
                elif action_definition["target_type"] == 'attack':
                    target_id = self.choose_target_attack(subject_being_id)
                    #target = self.universe.get_object_by_id(target_id)
#                    print(f"Target attack for {subject_being.name} is {target.name}")
                # Otherwise if the Action requires a target Attack, choose the target
                elif action_definition["target_type"] == 'weapon':
                    target_id = self.choose_target_weapon(subject_being_id)
                    #target = self.universe.get_object_by_id(target_id)
#                    print(f"Target weapon for {subject_being.name} is {target.name}")
                # Otherwise no target is necessary

    def choose_action(self, being):
        # randomly decide an action among those available
        chosen_action = being.choose_action(self.universe)
        return chosen_action
            
    def get_object_registry(self):
        return self.universe.get_object_registry()
