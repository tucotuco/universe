"""Observer-owned passive evidence for the initial unobstructed Arena.

This evidence is a scoped native observation record. It is not an omniscient
player registry, a general line-of-sight model, or a source of hidden Being
attributes. Native interval publication refreshes it from the shared
post-movement snapshot and commits the refresh with the rest of the boundary.
"""
from dataclasses import dataclass
import math

from spatial.state import CartesianPosition


BASIS = "arena.r65.initial_unobstructed_perception"
ENVIRONMENT = "arena.initial.unobstructed.v1"


@dataclass(frozen=True)
class ArenaPerceptionEvidence:
    observer_id: str
    entity_id: str
    category: str
    name: str
    type_key: str
    position: CartesianPosition | None
    present_state: str
    boundary: int
    time: float
    basis: str = BASIS
    owner_id: str | None = None
    equipment_status: str | None = None

    def __post_init__(self):
        if any(type(value) is not str or not value for value in
               (self.observer_id, self.entity_id, self.category, self.name,
                self.type_key, self.present_state, self.basis)):
            raise ValueError("Arena perception identities and labels must be nonempty text")
        if self.category not in ("being", "object"):
            raise ValueError("Arena passive perception supports Beings and physical Objects")
        if self.present_state not in ("present", "ground", "carried", "unplaced"):
            raise ValueError("unsupported Arena present-state evidence")
        if self.present_state == "ground" and self.position is None:
            raise ValueError("ground Object evidence requires a current position")
        if self.owner_id is not None and (type(self.owner_id) is not str or not self.owner_id):
            raise ValueError("Arena Object owner evidence must be a native Being identity or None")
        if self.category == "being" and (self.owner_id is not None or self.equipment_status is not None):
            raise ValueError("Being evidence cannot contain Object equipment state")
        if self.equipment_status is not None and self.equipment_status not in (
                "carried", "worn", "held in left hand", "held in right hand"):
            raise ValueError("unsupported visible Arena equipment status")
        if (self.equipment_status is not None) != (self.owner_id is not None):
            raise ValueError("visible equipment status requires its owner identity")
        if self.position is not None and type(self.position) is not CartesianPosition:
            raise TypeError("Arena position evidence requires native CartesianPosition")
        if type(self.boundary) is not int or self.boundary < 0:
            raise ValueError("Arena evidence boundary must be a nonnegative integer")
        if type(self.time) not in (int, float) or not math.isfinite(self.time) or self.time < 0:
            raise ValueError("Arena evidence time must be finite and nonnegative")
        if self.basis != BASIS:
            raise ValueError("unsupported Arena passive-perception basis")


class ArenaPerceptionLedger:
    """A native observer-owned current view plus immutable observation history."""

    def __init__(self, observer_id):
        if type(observer_id) is not str or not observer_id:
            raise ValueError("Arena perception ledger requires its observer identity")
        self.observer_id = observer_id
        self.environment = ENVIRONMENT
        self._current = {}
        self._history = []

    @property
    def current(self):
        return tuple(self._current[key] for key in sorted(self._current))

    @property
    def history(self):
        return tuple(self._history)


def _category(obj):
    from being import BeingInstance
    from object import ObjectInstance
    if type(obj) is BeingInstance:
        return "being"
    if type(obj) in (ObjectInstance,):
        return "object"
    from weapon import WeaponInstance
    from armor import ArmorInstance
    if type(obj) in (WeaponInstance, ArmorInstance):
        return "object"
    raise ValueError("unsupported entity in the initial Arena perception set")


def _initial_evidence(encounter, observer_id, entity_id, *, boundary=0):
    obj = encounter.universe.get_object_by_id(entity_id)
    category = _category(obj)
    if obj.geometry is not None or obj.visual_occlusion is not None:
        raise ValueError("initial passive perception requires the authored unobstructed Arena premise")
    position = obj.get_position()
    parent = obj.parent_container_id
    state = ("present" if category == "being" else
             "ground" if parent is None and position is not None else
             "carried" if parent is not None else "unplaced")
    type_key = "Being" if category == "being" else obj.current.obj_type
    owner_id = None
    equipment_status = None
    if category == "object" and parent is not None:
        from being import BeingInstance
        owner = encounter.universe.get_object_by_id(parent)
        if type(owner) is not BeingInstance or owner.id not in encounter.being_list:
            raise ValueError("visible carried Object must belong to a participating native Being")
        owner_id = owner.id
        if owner.current.armor_id == entity_id:
            equipment_status = "worn"
        else:
            slots = [slot for slot, held in owner.current.body_parts.items() if held == entity_id]
            equipment_status = f"held in {slots[0]}" if slots else "carried"
    return ArenaPerceptionEvidence(observer_id, entity_id, category,
        obj.name or type_key, type_key, position, state,
        boundary, float(encounter.time), owner_id=owner_id,
        equipment_status=equipment_status)


def initialize_arena_perception(encounter):
    """Seed independent t=0 evidence and native Awareness inside the candidate."""
    from being import BeingInstance

    if type(encounter.time) not in (int, float) or encounter.time != 0:
        raise ValueError("initial Arena perception is authorized only at native time zero")
    observers = tuple(encounter.being_list)
    entities = tuple(encounter.entity_ids())
    if len(observers) != 2 or any(type(encounter.get_being(key)) is not BeingInstance
                                  for key in observers):
        raise ValueError("revision-65 passive perception requires the native two-Being Arena")
    for observer_id in observers:
        observer = encounter.get_being(observer_id)
        ledger = ArenaPerceptionLedger(observer_id)
        for entity_id in entities:
            if entity_id == observer_id:
                continue
            evidence = _initial_evidence(encounter, observer_id, entity_id)
            ledger._current[entity_id] = evidence
            ledger._history.append(evidence)
        observer._arena_perception_ledger = ledger
        encounter.awareness[observer_id] = set(ledger._current)
    return tuple(encounter.get_being(key)._arena_perception_ledger for key in observers)


def refresh_candidate_names(encounter):
    """Replace only t=0 display-name facts after the private host naming step."""
    from being import BeingInstance

    if encounter.time != 0:
        raise ValueError("initial display-name refresh is closed after Encounter start")
    for observer_id in encounter.being_list:
        observer = encounter.get_being(observer_id)
        if type(observer) is not BeingInstance:
            raise ValueError("unknown native Arena observer")
        ledger = object.__getattribute__(observer, "__dict__").get("_arena_perception_ledger")
        if type(ledger) is not ArenaPerceptionLedger:
            raise ValueError("native Arena observer has no passive-perception ledger")
        for entity_id, previous in tuple(ledger._current.items()):
            obj = encounter.universe.get_object_by_id(entity_id)
            updated = ArenaPerceptionEvidence(previous.observer_id, previous.entity_id,
                previous.category, obj.name or obj.current.obj_type, previous.type_key,
                previous.position, previous.present_state, 0, 0.0,
                owner_id=previous.owner_id, equipment_status=previous.equipment_status)
            ledger._current[entity_id] = updated
            for index, row in enumerate(ledger._history):
                if row.entity_id == entity_id:
                    ledger._history[index] = updated
                    break
