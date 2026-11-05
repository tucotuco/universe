"""One-shot trusted-local activation of the fixed six-boundary Arena state.

This is deliberately not a checkpoint loader. It consumes the exact quarantined
B3 graph in this process, keeps B1 history as a provenance-labeled sidecar, and
creates a fresh native Encounter whose committed cursor begins at time 6.
Only future boundaries use this process's native receipt issuer.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import random
from threading import Lock
from weakref import WeakKeyDictionary, WeakSet

from arena_history_admission import (
    ArenaAdmissionRejected,
    ExpectedArenaScenario,
    _require_prepared_history_view,
)
from arena_state_admission import (
    ArenaStateAdmissionRejected,
    QuarantinedArenaState,
    _consume_private_native_graph,
    _native_inspection,
    _private_admitted_inputs,
    _private_native_beings,
    _validate_context,
)


SCHEMA = "universe.arena.trusted-local-continuation/1"
IMPORTED_TRUST = "imported/host-accepted claim; original receipt authenticity not established"
NATIVE_TRUST = "native/publisher-issued in this process"
_SCENARIO = ExpectedArenaScenario(
    "0", "npc-arena/encounter/1", "npc-arena/action/spot-ari-bex",
    "arena/being/ari", "arena/being/bex", "0x0.0p+0", 6,
)
_LOCK = Lock()
_CAPABILITIES = WeakKeyDictionary()
_ACTIVATED = WeakSet()


class ArenaActivationRejected(ValueError):
    """The host activation is unsupported, stale, mismatched, or already used."""


def _require(ok, message):
    if not ok:
        raise ArenaActivationRejected(message)


class _ArenaActivationCapability:
    __slots__ = ("__weakref__",)

    def __reduce__(self):
        raise TypeError("Arena activation capability is process-local and cannot be serialized")

    def __reduce_ex__(self, protocol):
        raise TypeError("Arena activation capability is process-local and cannot be serialized")

    def __repr__(self):
        return "<opaque single-use trusted-local Arena activation capability>"


@dataclass(frozen=True)
class _ActivationRecord:
    state: object
    native_beings: tuple
    candidate: object
    prefix: object
    history_view: object
    scenario: object
    bindings: tuple
    sources: tuple
    candidate_bytes: bytes
    prefix_bytes: bytes
    rng_seed: int


@dataclass(frozen=True)
class _ActiveArenaContinuation:
    """Trusted host-owned live context returned only by the private adapter."""
    world: object
    encounter: object
    rng: object
    imported_history: object
    imported_prefix: object
    source_provenance: tuple


@dataclass(frozen=True)
class ComposedArenaBoundary:
    encounter_id: str
    boundary: int
    start: float
    action_ids: tuple
    effect_ids: tuple
    provenance: str


@dataclass(frozen=True)
class ComposedArenaAction:
    action_id: str
    provenance: str
    actor_id: str
    target_id: str | None
    effect_ids: tuple


@dataclass(frozen=True)
class ComposedArenaInspection:
    schema: str
    trust: str
    encounter_id: str
    timeline: tuple
    actions: tuple
    imported_history: object
    native_inspection: object
    source_provenance: tuple


def _reviewed_inputs(state):
    if type(state) is not QuarantinedArenaState:
        raise ArenaActivationRejected("exact B3 quarantined Arena state required")
    view = state.view
    _require(state.quarantined is True
             and view.schema == "universe.arena.host-accepted-quarantined-being-state/1",
             "B3 state schema is unsupported")
    _require(view.time == 6.0 and view.committed_boundary == 6
             and view.universe_id == "0" and view.encounter_id == _SCENARIO.encounter_id,
             "only the exact quiescent boundary-6 Arena state is supported")
    _require(view.candidate_state_view.time == 6.0
             and view.candidate_state_view.committed_boundary == 6
             and view.candidate_state_view.start_time == 0.0,
             "B3 state projection is not the supported six-boundary candidate")
    _require(view.history_prefix_sha256 == view.candidate_state_view.history_prefix_sha256,
             "B1/B2 digest binding differs")
    _require(view.trust == "host-accepted post-Spot state claim; native historical receipt authenticity is not established",
             "B3 host trust label differs")
    expected_being_ids = ("arena/being/ari", "arena/being/bex")
    _require(tuple(row.being_id for row in view.beings) == expected_being_ids
             and tuple(row.being_id for row in view.candidate_state_view.participants) == expected_being_ids,
             "B3 participant identities differ from the fixed Arena")
    history_view = view.history_view
    _require(history_view.through_boundary == 6
             and history_view.encounter_id == _SCENARIO.encounter_id
             and history_view.universe_id == "0"
             and tuple(history_view.boundaries) == tuple(range(1, 7)),
             "B1 historical prefix is incomplete or mismatched")
    _require(history_view.spot.action_id == _SCENARIO.action_id
             and history_view.spot.actor_id == _SCENARIO.actor_id
             and history_view.spot.target_id == _SCENARIO.target_id
             and history_view.spot.resolved_boundary == 6
             and history_view.spot.outcome == "success",
             "B1 history is not the exact supported successful Spot")
    _require(history_view.observer_view(_SCENARIO.actor_id).aware_of == (_SCENARIO.target_id,)
             and history_view.observer_view(_SCENARIO.target_id).aware_of == (),
             "B1 observer-specific Awareness differs from the selected Arena state")

    try:
        candidate, prefix, registered_view, scenario, bindings, sources = _private_admitted_inputs(state)
        beings = _private_native_beings(state)
        _require(registered_view is history_view and scenario == _SCENARIO,
                 "B3 private admission inputs differ from the fixed host scenario")
        _require(prefix.content_sha256 == view.history_prefix_sha256,
                 "B1 history digest differs from B3")
        _require(candidate.content_sha256 == view.candidate_sha256,
                 "B2 candidate digest differs from B3")
        _require(candidate.to_bytes() and prefix.to_bytes(), "B1/B2 data did not revalidate")
        _require_prepared_history_view(prefix, history_view)
        candidate_view, prefix_bytes, checked_bindings, checked_sources = _validate_context(
            candidate, prefix, history_view,
            expected_content_sha256=view.candidate_sha256,
            expected_scenario=scenario,
            expected_bindings=bindings,
            expected_sources=sources,
        )
    except (ArenaStateAdmissionRejected, ArenaAdmissionRejected, TypeError, ValueError) as exc:
        if isinstance(exc, ArenaActivationRejected):
            raise
        raise ArenaActivationRejected(f"B1/B2/B3 validation failed: {exc}") from exc
    _require(candidate_view == view.candidate_state_view,
             "B3 state view differs from the exact revalidated B2 candidate")
    _require(prefix_bytes == prefix.to_bytes()
             and checked_bindings == bindings and checked_sources == sources,
             "B1/B2 source bindings changed after B3 admission")
    from being import BeingInstance
    _require(type(beings) is tuple and len(beings) == 2
             and all(type(being) is BeingInstance for being in beings),
             "B3 private native Being graph is incomplete")
    _require(tuple(being.id for being in beings) == expected_being_ids,
             "B3 native logical identities changed")
    _require(_native_inspection(beings) == view.beings,
             "B3 private Being state differs from the immutable admitted view")
    data = json.loads(candidate.to_bytes().decode("utf-8"))
    enc_data = data["encounter"]
    _require(enc_data["choice_counter"] == 1
             and enc_data["choice_ids"] == ["npc-arena/encounter/1/draft/1"]
             and enc_data["registered_action_ids"] == [_SCENARIO.action_id]
             and enc_data["reservations_empty"] is True,
             "B2 historical Choice/Action identity reservations differ")
    return candidate, prefix, history_view, beings, scenario, bindings, sources, data


def _host_authorize_local_activation(state, *, rng_seed):
    """Host deliberately accepts the exact B1/B2 pair as local initial state."""
    if isinstance(rng_seed, bool) or type(rng_seed) is not int:
        raise ArenaActivationRejected("new process-local RNG seed must be an integer chosen by the host")
    context = _reviewed_inputs(state)
    candidate, prefix, history_view, beings, scenario, bindings, sources, _ = context
    with _LOCK:
        if (state in _ACTIVATED
                or any(record.state is state for record in _CAPABILITIES.values())):
            raise ArenaActivationRejected("this B3 state already has an activation decision")
        capability = _ArenaActivationCapability()
        _CAPABILITIES[capability] = _ActivationRecord(
            state, beings, candidate, prefix, history_view, scenario, bindings, sources,
            candidate.to_bytes(), prefix.to_bytes(), rng_seed,
        )
    return capability


def _activate_local_arena(state, capability):
    """Consume one host capability and construct the fixed native time-6 Arena."""
    if type(capability) is not _ArenaActivationCapability:
        raise ArenaActivationRejected("exact process-local host activation capability required")
    with _LOCK:
        record = _CAPABILITIES.pop(capability, None)
    if record is None:
        raise ArenaActivationRejected("activation capability is foreign, stale, or already consumed")
    if state is not record.state:
        raise ArenaActivationRejected("activation capability is bound to a different B3 state result")
    context = _reviewed_inputs(state)
    candidate, prefix, history_view, beings, scenario, bindings, sources, _ = context
    _require(beings is record.native_beings and candidate is record.candidate
             and prefix is record.prefix and history_view is record.history_view
             and scenario == record.scenario and bindings == record.bindings
             and sources == record.sources,
             "B3 private graph or activation dependencies changed")
    _require(candidate.to_bytes() == record.candidate_bytes
             and prefix.to_bytes() == record.prefix_bytes,
             "B1/B2 bytes changed after host authorization")

    # The fixed historical Choice draft occupies counter 1. Seed the empty
    # fresh ChoiceBook at that verified high-water mark so the native Run gets
    # draft/2 without registering historical Actions or Choices.
    from pathlib import Path
    from library import Library
    from universe import Universe
    from encounter import Encounter
    from atomic_publication import RNGCursor
    import transactional_progression as progression

    config = Path(__file__).resolve().parent / "config"
    world = Universe("NPC candidate Arena (trusted-local continuation)",
                     library=Library(config_dir=str(config)))
    expected_ids = {"arena/being/ari", "arena/being/bex"}
    _require(set(world.object_registry.object_instances) == set()
             and set(world.event_history) == {"0"}
             and world.event_history["0"].id not in expected_ids,
             "new Universe has unexpected or colliding registry state")
    for being in beings:
        _require(world.get_object_by_id(being.id) is None,
                 "native Being identity collides with the new Universe registry")
        world.add_object(being)
        _require(world.get_object_by_id(being.id) is being,
                 "Universe registry did not retain the exact admitted Being")
    _require(set(world.object_registry.object_instances) == expected_ids,
             "Universe ObjectRegistry contains missing or extra Objects")

    awareness = {
        row.being_id: tuple(row.aware_of)
        for row in history_view.targets
    }
    encounter = Encounter(
        world, difficulty_class=15, start_time=6, initiated=True,
        id=_SCENARIO.encounter_id,
        awareness=awareness,
    )
    _require(encounter.time == 6 and encounter.last_processed_boundary == 6
             and encounter.start_time == 6,
             "ordinary Encounter constructor did not create the quiescent time-6 context")
    world.add_event(encounter)
    for identity in ("arena/being/ari", "arena/being/bex"):
        encounter.add_being(identity)
    _require(set(world.event_history) == {"0", _SCENARIO.encounter_id}
             and world.event_history[_SCENARIO.encounter_id] is encounter
             and tuple(encounter.being_list) == ("arena/being/ari", "arena/being/bex")
             and encounter.non_being_object_list == [],
             "fresh Encounter registries differ from the exact Arena subset")
    _require(encounter.awareness == {
        "arena/being/ari": {"arena/being/bex"},
        "arena/being/bex": set(),
    }, "new Encounter Awareness differs from imported Target-owned state")
    encounter._choice_book._counter = 1
    rng = RNGCursor(random.Random(record.rng_seed).getstate())
    rng_before = rng.state
    # The exact B3 objects stay quarantined until every native constructor and
    # transactional-mode preflight succeeds. Marker transfer is reversible.
    for being in beings:
        data = object.__getattribute__(being, "__dict__")
        _require(data.get("_checkpoint_quarantined") is True and progression.is_quarantined(being),
                 "native Being is no longer held by the B3 quarantine")
    try:
        for being in beings:
            data = object.__getattribute__(being, "__dict__")
            progression._QUARANTINED.discard(being)
            data.pop("_checkpoint_quarantined", None)
        encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
        _require(encounter.progression_mode == "transactional"
                 and encounter.time == 6 and encounter.last_processed_boundary == 6
                 and not encounter.__dict__.get("_atomic_interval_history"),
                 "fresh transactional Encounter did not start at the imported checkpoint fence")
        _require(rng.state == rng_before,
                 "new host-owned RNG was changed while constructing the Encounter")
        _consume_private_native_graph(state, beings)
    except BaseException:
        for being in beings:
            data = object.__getattribute__(being, "__dict__")
            data["_checkpoint_quarantined"] = True
            progression._QUARANTINED.add(being)
        raise
    with _LOCK:
        _ACTIVATED.add(state)
    provenance = tuple((row.binding_key, row.source_sha256, row.native_being_id,
                        row.native_definition_name, row.position_hex)
                       for row in history_view.npc_bindings)
    return _ActiveArenaContinuation(world, encounter, rng, history_view, prefix, provenance)


def _compose_committed_inspection(active):
    """Join imported claims and native inspection without authenticating/importing claims."""
    if type(active) is not _ActiveArenaContinuation:
        raise ArenaActivationRejected("trusted-local Arena continuation context required")
    native = active.encounter.inspect_committed(7)
    imported = active.imported_history
    _require(native.encounter_id == _SCENARIO.encounter_id
             and native.boundary == native.latest_boundary == 7
             and tuple(row.boundary for row in native.timeline) == (7,),
             "native issuer did not provide exactly the fresh boundary-7 receipt")
    _require(tuple(imported.boundaries) == tuple(range(1, 7)),
             "imported history is not the exact six-boundary prefix")
    def identity_row(value):
        return (value.encounter_id, value.boundary, value.source_action_id,
                value.channel, value.slot)
    boundary_data = active.imported_prefix.payload()["boundaries"]
    imported_rows = tuple(ComposedArenaBoundary(
        imported.encounter_id, row["boundary"], float.fromhex(row["start_time"]),
        tuple(row["action_ids"]), tuple(tuple(value) for value in row["effect_ids"]), IMPORTED_TRUST,
    ) for row in boundary_data)
    native_rows = tuple(ComposedArenaBoundary(
        row.encounter_id, row.boundary, row.start, tuple(row.action_ids),
        tuple(identity_row(value) for value in row.effect_ids), NATIVE_TRUST,
    ) for row in native.timeline)
    _require(tuple(row.boundary for row in imported_rows + native_rows) == tuple(range(1, 8)),
             "composed chronology contains a gap or overlap")
    _require(tuple(row.provenance for row in imported_rows) == (IMPORTED_TRUST,) * 6
             and tuple(row.provenance for row in native_rows) == (NATIVE_TRUST,),
             "composed provenance labels were lost")
    _require(tuple(imported.spot.action_id for _ in (0,)) == (_SCENARIO.action_id,)
             and set(native.actions) == {"npc-arena/action/run-ari-boundary-7"},
             "composed Action identities are outside the fixed Spot/Run case")
    imported_effect_ids = {tuple(row.identity) for row in imported.effects}
    native_effect_ids = {tuple(value) for value in native_rows[0].effect_ids}
    _require(not imported_effect_ids.intersection(native_effect_ids),
             "native boundary effects collide with imported historical effect identities")
    spot = imported.spot
    imported_action = ComposedArenaAction(
        spot.action_id, IMPORTED_TRUST, spot.actor_id, spot.target_id,
        tuple(tuple(row.identity) for row in imported.effects),
    )
    action = native.action("npc-arena/action/run-ari-boundary-7")
    native_action = ComposedArenaAction(
        action.declaration.id, NATIVE_TRUST, action.declaration.actor_id,
        action.declaration.target_id, tuple(identity_row(row.identity) for row in action.effects),
    )
    return ComposedArenaInspection(
        SCHEMA, "omniscient developer inspection; imported history is not receipt-authenticated",
        _SCENARIO.encounter_id, imported_rows + native_rows,
        (imported_action, native_action), imported, native, active.source_provenance,
    )
