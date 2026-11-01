"""Detached immutable inspection values for quarantined reconstruction.

These records intentionally contain no native Universe, Encounter, Being,
Action, RNG cursor, mutable mapping, or callable reference.
"""
from dataclasses import dataclass
import math


class InspectionViewRejected(ValueError):
    """A native inspection value is outside the closed detached view format."""


def freeze_inspection_value(value):
    """Copy a supported native value to recursively immutable primitive data."""
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise InspectionViewRejected('inspection values must contain finite numbers')
        return value
    if type(value) in (tuple, list):
        return tuple(freeze_inspection_value(item) for item in value)
    if type(value) is dict:
        if not all(type(key) is str for key in value):
            raise InspectionViewRejected('inspection mappings require string keys')
        return tuple((key, freeze_inspection_value(value[key]))
                     for key in sorted(value))
    raise InspectionViewRejected(
        f'unsupported mutable/native inspection value: {type(value).__module__}.{type(value).__qualname__}')


@dataclass(frozen=True)
class NativeBeingInspection:
    logical_id: str
    name: str
    position: tuple | None
    hit_points: int | float
    physical_fatigue: tuple
    physiology_id: str | None
    skill_levels: tuple
    skill_experience: tuple
    state: tuple


@dataclass(frozen=True)
class NativeActionInspection:
    logical_id: str
    choice_id: str
    family: str
    actor_id: str | None
    target_id: str | None
    start_time: tuple
    end_time: tuple
    declaration: tuple


@dataclass(frozen=True)
class QuarantinedReconstructionView:
    schema: str
    universe_id: str
    universe_name: str
    encounter_id: str
    encounter_start: float
    encounter_end: float | None
    encounter_time: float
    difficulty_class: float
    logical_ids: tuple
    being_ids: tuple
    beings: tuple
    actions: tuple
    accepted_choices: tuple
    reservations: tuple
    rng_role: str
    rng_scope: str
    rng_state: tuple
    quarantined: bool = True


@dataclass(frozen=True)
class NativeIdentityView:
    kind: str
    logical_id: str
    display_name: str
    state_role: str
    # Recursively frozen data-only current state. Historical Action/Target
    # records remain in their separately identified sidecar.
    state: tuple = ()


@dataclass(frozen=True)
class NativeRunActionIdentityView:
    logical_id: str
    choice_id: str
    actor_id: str
    start: tuple
    end: tuple
    family: str = 'native.run-action/1'


# The old symbol remains importable for downstream code, but the bound value
# contract is Run-only and has no observed-Target field.
NativeSpotActionIdentityView = NativeRunActionIdentityView


@dataclass(frozen=True)
class QuarantinedNativeEncounterView:
    logical_id: str
    universe_id: str
    start_time: float
    time: float
    last_processed_boundary: int
    next_boundary: int
    being_ids: tuple
    awareness: tuple
    pending_action_ids: tuple
    finished_action_ids: tuple
    cancelled_action_ids: tuple
    choice_count: int
    reservation_count: int
    rng_role: str
    rng_scope: str
    rng_state: tuple
    quarantined: bool = True


@dataclass(frozen=True)
class QuarantinedRunBindingView:
    schema: str
    universe_id: str
    encounter_id: str
    boundary: int
    start: tuple
    beings: tuple
    actions: tuple
    choice_id: str
    effect_ids: tuple
    rng_state: tuple
    quarantined: bool = True
    native_encounter: QuarantinedNativeEncounterView | None = None


QuarantinedSpotBindingView = QuarantinedRunBindingView
