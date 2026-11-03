"""Explicit world-level binding of an existing offspring ID to a native Being.

This narrow bridge creates one Being from caller-authored native properties.
It does not infer physical or reproductive traits from genealogy and does not
add population, Encounter, Observation, Awareness, or Belief state.
"""
from __future__ import annotations

from dataclasses import dataclass
import json

from being import BeingDefinition, BeingInstance
from reproduction_group import ReproductionGroupRegistry
from universe import Universe


class ReproductionBeingBridgeError(ValueError):
    """The requested native identity binding is unsupported or inconsistent."""


class InjectedReproductionBeingBridgeFailure(RuntimeError):
    """Deterministic fault injection used to verify atomic registration."""


_PUBLICATION_PHASES = ("object_registry", "binding_index", "request_index", "consistency")
_NATIVE_DATA_MODULES = {"abilities", "skill", "speeds", "states"}


@dataclass(frozen=True)
class _NativeBeingBindingRecord:
    request_key: str
    person_id: str
    normalized_request: tuple[str, str, str]
    being: BeingInstance


def _validate_fail_after(phase):
    if phase is not None and phase not in _PUBLICATION_PHASES:
        raise ReproductionBeingBridgeError("unknown native Being bridge fault phase")


def _definition_signature(definition):
    try:
        # BeingDefinition.to_json() currently omits the JSON default handler
        # for its native Speed/Abilities/Skills/States members. Serialize the
        # closed native object data directly; unsupported callbacks/types and
        # cycles still fail rather than being invoked.
        def native_data(value):
            if callable(value) or type(value).__module__ not in _NATIVE_DATA_MODULES:
                raise TypeError(f"unsupported BeingDefinition value: {type(value).__name__}")
            return value.__dict__

        encoded = json.dumps(
            definition.__dict__, sort_keys=True, ensure_ascii=True, separators=(",", ":"),
            allow_nan=False, default=native_data,
        )
        value = json.loads(encoded)
        return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ReproductionBeingBridgeError("BeingDefinition must be closed JSON-compatible authored data") from exc


def _maybe_fail(phase, fail_after):
    if phase == fail_after:
        raise InjectedReproductionBeingBridgeFailure(f"injected native Being bridge failure after {phase}")


def materialize_reproductive_offspring(
    world: Universe,
    person_id: str,
    *,
    being_definition: BeingDefinition,
    name: str,
    request_key: str,
    expected_revision: int,
    _fail_after: str | None = None,
) -> BeingInstance:
    """Construct/register exactly one Being for an existing logical offspring.

    ``being_definition`` and ``name`` are explicit author inputs. The definition
    is copied before constructing the native Being. A repeated request with
    identical input returns the same mutable Being instance and does not write
    or revise reproductive facts.
    """
    if not isinstance(world, Universe):
        raise TypeError("world must be a native Universe")
    if type(person_id) is not str or not person_id.strip():
        raise ReproductionBeingBridgeError("person_id must be a nonempty logical identity")
    if type(name) is not str or not name.strip():
        raise ReproductionBeingBridgeError("an explicit nonempty Being name is required")
    if type(request_key) is not str or not request_key.strip():
        raise ReproductionBeingBridgeError("request_key must be nonempty text")
    if not isinstance(being_definition, BeingDefinition):
        raise TypeError("being_definition must be a BeingDefinition")
    if type(expected_revision) is not int or expected_revision < 0:
        raise ReproductionBeingBridgeError("expected_revision must be a nonnegative integer")
    _validate_fail_after(_fail_after)
    definition_signature = _definition_signature(being_definition)
    normalized = (person_id, name, definition_signature)

    with world._schedule_lock:
        registry: ReproductionGroupRegistry = world._reproduction_group_registry
        if registry._world is not world:
            raise ReproductionBeingBridgeError("reproduction registry is not owned by this Universe")
        if _definition_signature(being_definition) != definition_signature:
            raise ReproductionBeingBridgeError("BeingDefinition changed while materialization was being prepared")
        if registry._revision:
            try:
                registry._assert_consistent()
            except (RuntimeError, ValueError, TypeError) as exc:
                raise ReproductionBeingBridgeError(f"reproduction/native identity state is inconsistent: {exc}") from exc

        # Exact retries are read-only. Permit them after an explicit native
        # Encounter publication has established the binding; every new or
        # conflicting materialization still requires the legacy no-Encounter
        # world-level context below.
        prior = registry._native_being_requests.get(request_key)
        if prior is not None:
            if prior.normalized_request != normalized:
                raise ReproductionBeingBridgeError("request key was already used for different Being properties")
            if (registry._native_beings_by_person_id.get(person_id) is not prior.being
                    or world.get_object_by_id(person_id) is not prior.being):
                raise ReproductionBeingBridgeError("stored native Being binding is stale or replaced")
            return prior.being
        try:
            registry._validate_no_encounter_context()
        except (TypeError, ValueError) as exc:
            raise ReproductionBeingBridgeError(f"native Being bridge requires a no-Encounter world: {exc}") from exc
        if request_key in (set(registry._requests) | set(registry._generation_requests)
                           | set(registry._progressive_requests)):
            raise ReproductionBeingBridgeError("request key is already used by a reproduction publication")
        if expected_revision != registry._revision:
            raise ReproductionBeingBridgeError("reproduction revision changed before Being materialization")
        if person_id not in registry._group_id_by_offspring:
            raise ReproductionBeingBridgeError("only an already-published logical offspring can be materialized")
        if person_id in registry._native_beings_by_person_id:
            raise ReproductionBeingBridgeError("logical offspring is already bound by a different request")
        if world.get_object_by_id(person_id) is not None:
            raise ReproductionBeingBridgeError("native ObjectRegistry already contains this logical identity")

        try:
            definition_copy = being_definition.copy()
            if type(definition_copy) is not BeingDefinition:
                raise ReproductionBeingBridgeError("BeingDefinition.copy() did not return a native definition")
            if _definition_signature(definition_copy) != definition_signature:
                raise ReproductionBeingBridgeError("BeingDefinition.copy() changed the authored properties")
            being = BeingInstance(definition_copy, name=name, id=person_id)
        except ReproductionBeingBridgeError:
            raise
        except Exception as exc:
            raise ReproductionBeingBridgeError(f"native Being construction failed before publication: {exc}") from exc
        if being.id != person_id:
            raise ReproductionBeingBridgeError("native Being constructor did not preserve the logical identity")

        undo = registry._capture_undo()
        try:
            world.add_object(being)
            if world.get_object_by_id(person_id) is not being:
                raise ReproductionBeingBridgeError("Universe did not register the constructed Being")
            _maybe_fail("object_registry", _fail_after)

            registry._native_beings_by_person_id[person_id] = being
            _maybe_fail("binding_index", _fail_after)

            registry._native_being_requests[request_key] = _NativeBeingBindingRecord(
                request_key, person_id, normalized, being,
            )
            _maybe_fail("request_index", _fail_after)

            registry._assert_consistent()
            _maybe_fail("consistency", _fail_after)
            return being
        except BaseException:
            if world.object_registry.get_object_by_id(person_id) is being:
                world.object_registry.object_instances.pop(person_id, None)
            registry._restore_undo(undo)
            raise


__all__ = [
    "InjectedReproductionBeingBridgeFailure",
    "ReproductionBeingBridgeError",
    "materialize_reproductive_offspring",
]
