"""Host-approved, quarantined native Being construction for the fixed Arena.

This module admits one exact 003B2 detached state candidate after a distinct
003B1 history admission. It builds only private native Being/Object instances
for immutable inspection. It does not construct a Universe or Encounter,
install native Action history, import RNG authority, issue receipts, or enable
simulation continuation.
"""
from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import json
from threading import Lock
from weakref import WeakKeyDictionary

from arena_history_admission import (
    ArenaAdmissionRejected,
    ExpectedArenaBinding,
    ExpectedArenaScenario,
    HostAcceptedArenaHistoryView,
    _require_prepared_history_view,
)
from arena_history_prefix import ArenaSpotHistoryPrefix
from arena_state_candidate import (
    ArenaPostSpotStateCandidate,
    ArenaPostSpotStateView,
    ArenaStateRejected,
    validate_arena_post_spot_state,
)


SCHEMA = "universe.arena.host-accepted-quarantined-being-state/1"
TRUST = "host-accepted post-Spot state claim; native historical receipt authenticity is not established"
_EXPECTED_BEING_FIELDS = frozenset((
    "_atomic_target_history", "_posture", "_skill_practice_baselines", "current",
    "effective_fitness", "exertion", "fatigue_level", "front_facing",
    "geometry", "hex_facing", "id", "name", "original", "parent_container_id",
    "personal_history", "physical_fatigue", "physiology_id", "possessions",
    "skill_experience", "skill_use_history", "spatial_state", "strategy",
    "top_facing", "type", "visual_occlusion", "weapons",
))


class ArenaStateAdmissionRejected(ValueError):
    """The host admission or native graph is not the reviewed Arena subset."""


def _require(ok, message):
    if not ok:
        raise ArenaStateAdmissionRejected(message)


@dataclass(frozen=True)
class ExpectedArenaSource:
    """Independently host-supplied exact bytes for one fixed Arena source."""
    binding_key: str
    source_bytes: bytes


@dataclass(frozen=True)
class ArenaNativeBeingInspection:
    being_id: str
    name: str
    definition_name: str
    hit_points: int | float
    position_hex: tuple
    geometry_kind: str
    geometry_radius_hex: str
    top_facing: int
    front_facing: int
    quarantined: bool


@dataclass(frozen=True)
class ArenaStateAdmissionView:
    schema: str
    trust: str
    candidate_sha256: str
    history_prefix_sha256: str
    universe_id: str
    encounter_id: str
    time: float
    committed_boundary: int
    source_provenance: tuple
    beings: tuple
    candidate_state_view: ArenaPostSpotStateView
    history_view: HostAcceptedArenaHistoryView
    rng_role: str
    rng_scope: str
    continuation: str

    def inspect_being(self, being_id):
        if type(being_id) is not str or being_id not in {row.being_id for row in self.beings}:
            raise ArenaStateAdmissionRejected("Being is not in this admitted Arena view")
        return next(row for row in self.beings if row.being_id == being_id)


@dataclass(frozen=True, eq=False)
class QuarantinedArenaState:
    """Public detached inspection result; native objects are held privately."""
    view: ArenaStateAdmissionView
    quarantined: bool = True

    @property
    def logical_ids(self):
        return tuple(row.being_id for row in self.view.beings)


class _ArenaStateCapability:
    __slots__ = ("__weakref__",)

    def __reduce__(self):
        raise TypeError("Arena state-admission capability is process-local and cannot be serialized")

    def __reduce_ex__(self, protocol):
        raise TypeError("Arena state-admission capability is process-local and cannot be serialized")

    def __repr__(self):
        return "<opaque Arena state admission capability>"


@dataclass(frozen=True)
class _CapabilityRecord:
    candidate: object
    candidate_bytes: bytes
    candidate_digest: str
    prefix: object
    prefix_bytes: bytes
    history_view: object
    scenario: object
    expected_bindings: tuple
    expected_sources: tuple
    policy_context: str


_CAPABILITIES = WeakKeyDictionary()
_PRIVATE_NATIVE = WeakKeyDictionary()
_LOCK = Lock()


def _expected_bindings(rows):
    if type(rows) is not tuple or len(rows) != 2 or any(type(row) is not ExpectedArenaBinding for row in rows):
        raise ArenaStateAdmissionRejected("host must bind both fixed native Arena participants")
    rows = tuple(sorted(rows, key=lambda row: row.binding_key))
    if tuple(row.binding_key for row in rows) != ("arena-ari", "arena-bex"):
        raise ArenaStateAdmissionRejected("host bindings do not identify Ari and Bex in the fixed Arena")
    return rows


def _expected_sources(rows):
    if type(rows) is not tuple or len(rows) != 2 or any(type(row) is not ExpectedArenaSource for row in rows):
        raise ArenaStateAdmissionRejected("host must provide exact source bytes for both Arena records")
    rows = tuple(sorted(rows, key=lambda row: row.binding_key))
    if tuple(row.binding_key for row in rows) != ("arena-ari", "arena-bex"):
        raise ArenaStateAdmissionRejected("source-byte bindings do not identify both Arena records")
    for row in rows:
        if type(row.source_bytes) is not bytes or not row.source_bytes:
            raise ArenaStateAdmissionRejected("host Arena source bytes must be nonempty immutable bytes")
    return rows


def _candidate_source_rows(candidate):
    data = json.loads(candidate.to_bytes().decode("utf-8"))
    rows = data.get("source_bindings")
    if type(rows) is not list or len(rows) != 2:
        raise ArenaStateAdmissionRejected("candidate does not contain the exact two source bindings")
    result = []
    for row in rows:
        if type(row) is not dict:
            raise ArenaStateAdmissionRejected("candidate source binding is malformed")
        try:
            raw = base64.b64decode(row["source_bytes_base64"], validate=True)
        except (KeyError, ValueError) as exc:
            raise ArenaStateAdmissionRejected("candidate source bytes are malformed") from exc
        if hashlib.sha256(raw).hexdigest() != row.get("source_sha256"):
            raise ArenaStateAdmissionRejected("candidate source bytes and digest disagree")
        result.append((row.get("binding_key"), raw, row.get("source_sha256")))
    if len({row[0] for row in result}) != 2 or {row[0] for row in result} != {"arena-ari", "arena-bex"}:
        raise ArenaStateAdmissionRejected("candidate source binding identities are duplicate or unexpected")
    return tuple(sorted(result))


def _check_source_bindings(candidate, history_view, expected_bindings, expected_sources):
    prefix_rows = _prefix_view_rows(history_view)
    candidate_rows = {key: (raw, digest) for key, raw, digest in _candidate_source_rows(candidate)}
    source_rows = {row.binding_key: row.source_bytes for row in expected_sources}
    if set(prefix_rows) != {"arena-ari", "arena-bex"} or set(candidate_rows) != set(prefix_rows):
        raise ArenaStateAdmissionRejected("history and state candidate do not share the fixed source set")
    for binding in expected_bindings:
        source = source_rows[binding.binding_key]
        digest = hashlib.sha256(source).hexdigest()
        history = prefix_rows[binding.binding_key]
        candidate_bytes, candidate_digest = candidate_rows[binding.binding_key]
        _require(history["source_bytes"] == source and history["source_sha256"] == digest == binding.source_sha256,
                 "host-selected source bytes differ from B1 history/source digest")
        _require(candidate_bytes == source and candidate_digest == digest,
                 "B2 candidate source bytes differ from host-selected source bytes")
        _require((history["display_name"], history["native_being_id"],
                  history["native_definition_name"], tuple(history["position_hex"])) ==
                 (binding.display_name, binding.native_being_id,
                  binding.native_definition_name, binding.position_hex),
                 "historical source binding differs from host selection")


def _prefix_view_rows(prefix):
    return {row.binding_key: {
        "source_bytes": row.source_bytes,
        "source_sha256": row.source_sha256,
        "display_name": row.display_name,
        "native_being_id": row.native_being_id,
        "native_definition_name": row.native_definition_name,
        "position_hex": tuple(row.position_hex),
    } for row in prefix.npc_bindings}


def _validate_context(candidate, prefix, history_view, *, expected_content_sha256,
                      expected_scenario, expected_bindings, expected_sources):
    if type(candidate) is not ArenaPostSpotStateCandidate:
        raise ArenaStateAdmissionRejected("exact B2 Arena state candidate required")
    if type(prefix) is not ArenaSpotHistoryPrefix:
        raise ArenaStateAdmissionRejected("exact B1 Arena history prefix required")
    if type(expected_scenario) is not ExpectedArenaScenario:
        raise ArenaStateAdmissionRejected("explicit fixed Arena scenario expectation required")
    if (expected_scenario.universe_id, expected_scenario.encounter_id,
        expected_scenario.action_id, expected_scenario.actor_id,
        expected_scenario.target_id, expected_scenario.start_time,
        expected_scenario.through_boundary) != (
        "0", "npc-arena/encounter/1", "npc-arena/action/spot-ari-bex",
        "arena/being/ari", "arena/being/bex", "0x0.0p+0", 6):
        raise ArenaStateAdmissionRejected("host scenario is outside the fixed six-boundary Arena")
    bindings = _expected_bindings(expected_bindings)
    sources = _expected_sources(expected_sources)
    try:
        candidate_bytes = candidate.to_bytes()
        candidate_digest = candidate.content_sha256
    except (ArenaStateRejected, TypeError, ValueError) as exc:
        raise ArenaStateAdmissionRejected(f"B2 candidate failed canonical revalidation: {exc}") from exc
    if type(expected_content_sha256) is not str or candidate_digest != expected_content_sha256:
        raise ArenaStateAdmissionRejected("host-selected candidate digest does not identify exact B2 bytes")
    try:
        _require_prepared_history_view(prefix, history_view)
        prefix_bytes = prefix.to_bytes()
        candidate_view = validate_arena_post_spot_state(candidate, prefix, history_view)
    except (ArenaAdmissionRejected, ArenaStateRejected, TypeError, ValueError) as exc:
        raise ArenaStateAdmissionRejected(f"B1/B2 host admission validation failed: {exc}") from exc
    if (candidate_view.universe_id, candidate_view.encounter_id,
        candidate_view.start_time, candidate_view.time, candidate_view.committed_boundary) != (
        expected_scenario.universe_id, expected_scenario.encounter_id, 0.0, 6.0, 6):
        raise ArenaStateAdmissionRejected("candidate timeline differs from the selected Arena context")
    prefix_rows = _prefix_view_rows(history_view)
    if tuple((key, row["source_sha256"], row["display_name"],
              row["native_being_id"], row["native_definition_name"], row["position_hex"])
             for key, row in sorted(prefix_rows.items())) != tuple(
             (row.binding_key, row.source_sha256, row.display_name,
              row.native_being_id, row.native_definition_name, row.position_hex)
             for row in bindings):
        raise ArenaStateAdmissionRejected("B1 history does not match all host-selected participant bindings")
    _check_source_bindings(candidate, history_view, bindings, sources)
    expected_ids = ("arena/being/ari", "arena/being/bex")
    if tuple(row.being_id for row in candidate_view.participants) != expected_ids:
        raise ArenaStateAdmissionRejected("candidate participant set/order differs from the fixed Arena")
    for participant, binding in zip(candidate_view.participants, bindings):
        if (participant.name != binding.display_name or participant.native_type != "BeingInstance"
                or participant.definition_name != "Human"
                or participant.position_hex != binding.position_hex
                or participant.geometry != ("Sphere", "0x1.0000000000000p-1")):
            raise ArenaStateAdmissionRejected("candidate Being definition, position or geometry differs from host intent")
    return candidate_view, prefix_bytes, bindings, sources


def _host_authorize_arena_state(candidate, prefix, history_view, *,
                                expected_content_sha256, expected_scenario,
                                expected_bindings, expected_sources):
    """Make an explicit trusted-local decision for this exact B2 state claim."""
    candidate_view, prefix_bytes, bindings, sources = _validate_context(
        candidate, prefix, history_view,
        expected_content_sha256=expected_content_sha256,
        expected_scenario=expected_scenario,
        expected_bindings=expected_bindings,
        expected_sources=expected_sources)
    capability = _ArenaStateCapability()
    record = _CapabilityRecord(
        candidate, candidate.to_bytes(), candidate.content_sha256,
        prefix, prefix_bytes, history_view, expected_scenario, bindings, sources,
        "host deliberately selected exact B2 bytes plus the separately B1-prepared history and bindings")
    with _LOCK:
        _CAPABILITIES[capability] = record
    return capability


def _tuple_graph(data):
    """Convert only the already validated B2 JSON graph to _Graph tuples."""
    def atom(value):
        if value is None or type(value) in (str, int, bool):
            return value
        if type(value) is list:
            if value and value[0] in ("reference", "binary64", "null", "boolean", "string", "integer"):
                return tuple([atom(part) for part in value])
            return tuple(atom(part) for part in value)
        raise ArenaStateAdmissionRejected("B2 native graph contains an unsupported JSON value")

    nodes = []
    for row in data["native_data_graph"]["nodes"]:
        ref, tag, content = row
        ref = tuple(ref)
        if tag == "ordered-map":
            content = tuple((atom(pair[0]), atom(pair[1])) for pair in content)
        else:
            content = tuple(atom(value) for value in content)
        nodes.append((ref, tag, content))
    return tuple(nodes)


def _construct_private_beings(candidate_view, candidate):
    """Rebuild the two native BeingInstances from their reviewed constructor graph."""
    try:
        from checkpoint_reconstruction import _Graph
        from being import BeingInstance
        from spatial.state import SpatialState
        from spatial.geometry import Sphere
        from transactional_progression import quarantine_reconstructed_graph
        data = json.loads(candidate.to_bytes().decode("utf-8"))
        graph = _Graph(_tuple_graph(data))
        native = []
        for participant in candidate_view.participants:
            root_ref = ("owned-path", "arena-state", participant.being_id)
            if graph.nodes.get(root_ref, (None,))[0] != "tuple":
                raise ArenaStateAdmissionRejected("candidate native Being root is missing")
            root_content = graph.nodes[root_ref][1]
            if len(root_content) != 3 or graph.data(root_content[0]) != "arena-being" \
                    or graph.data(root_content[1]) != participant.being_id:
                raise ArenaStateAdmissionRejected("candidate native Being root identity is malformed")
            fields_ref = graph.raw_ref(root_content[2])
            if graph.nodes[fields_ref][0] != "tuple":
                raise ArenaStateAdmissionRejected("candidate Being field map has unsupported shape")
            fields = {}
            for pair_ref_value in graph.nodes[fields_ref][1]:
                pair_ref = graph.raw_ref(pair_ref_value)
                if graph.nodes[pair_ref][0] != "tuple" or len(graph.nodes[pair_ref][1]) != 2:
                    raise ArenaStateAdmissionRejected("candidate Being field pair is malformed")
                name = graph.data(graph.nodes[pair_ref][1][0])
                value = graph.value(graph.nodes[pair_ref][1][1])
                if type(name) is not str or name in fields:
                    raise ArenaStateAdmissionRejected("candidate Being has duplicate or non-text field")
                fields[name] = value
            if set(fields) != _EXPECTED_BEING_FIELDS:
                raise ArenaStateAdmissionRejected("candidate Being fields differ from the reviewed closed native set")
            if (fields["id"] != participant.being_id or fields["name"] != participant.name
                    or type(fields["original"]).__name__ != "BeingDefinition"
                    or fields["original"].obj_type != "Human"
                    or type(fields["current"]).__name__ != "BeingDefinition"):
                raise ArenaStateAdmissionRejected("candidate native definitions/identity differ from host-approved state")
            from being import BeingInstance
            if fields["_posture"] not in (None, "standing", "crouching", "lying") \
                    or (fields["hex_facing"] is not None
                        and (type(fields["hex_facing"]) is not int
                             or not 0 <= fields["hex_facing"] < 12)):
                raise ArenaStateAdmissionRejected("candidate native posture/facing is unsupported")
            being = BeingInstance(fields["original"], name=fields["name"], id=fields["id"])
            # Native history and receipt identity remain a detached B1/B2
            # sidecar. Never install candidate inspection rows as authority.
            for name, value in fields.items():
                if name in ("id", "name", "original", "_atomic_target_history"):
                    continue
                if name == "spatial_state":
                    if not isinstance(value, SpatialState):
                        raise ArenaStateAdmissionRejected("native spatial state did not reconstruct as SpatialState")
                    being.set_spatial_state(value)
                elif name == "geometry":
                    if not isinstance(value, Sphere) or value.radius != 0.5:
                        raise ArenaStateAdmissionRejected("native geometry is not the authored Sphere(0.5)")
                    being.set_geometry(value)
                elif name == "visual_occlusion":
                    being.set_visual_occlusion(value)
                else:
                    setattr(being, name, value)
            if (being.id != participant.being_id or being.name != participant.name
                    or being.current.obj_type != participant.definition_name
                    or being.get_hit_points() != participant.hit_points
                    or tuple(float(value).hex() for value in being.get_position().as_tuple()) != participant.position_hex
                    or type(being.geometry).__name__ != participant.geometry[0]
                    or float(being.geometry.radius).hex() != participant.geometry[1]):
                raise ArenaStateAdmissionRejected("reconstructed native Being projection differs from B2 candidate")
            from checkpoint_reconstruction import _projection
            actual_fields = object.__getattribute__(being, "__dict__")
            expected_native_fields = set(fields) - {"_atomic_target_history"}
            if set(actual_fields) != expected_native_fields:
                raise ArenaStateAdmissionRejected("native Being constructor produced an unrepresented field set")
            if any(_projection(actual_fields[key]) != _projection(fields[key])
                   for key in expected_native_fields):
                raise ArenaStateAdmissionRejected("native Being field projection differs from the closed B2 graph")
            native.append(being)
        class _QuarantineAnchor:
            pass
        anchor = _QuarantineAnchor()
        quarantine_reconstructed_graph(anchor, native)
        from transactional_progression import is_quarantined
        if any(not is_quarantined(being) for being in native):
            raise ArenaStateAdmissionRejected("native Being did not retain its process-local quarantine marker")
        return anchor, tuple(native)
    except ArenaStateAdmissionRejected:
        raise
    except (ImportError, KeyError, TypeError, ValueError, AttributeError, IndexError) as exc:
        raise ArenaStateAdmissionRejected(f"closed native Arena Being construction refused: {exc}") from exc


def _native_inspection(beings):
    rows = []
    for being in beings:
        rows.append(ArenaNativeBeingInspection(
            being.id, being.name, being.current.obj_type, being.get_hit_points(),
            tuple(float(value).hex() for value in being.get_position().as_tuple()),
            type(being.geometry).__name__, float(being.geometry.radius).hex(),
            being.top_facing, being.front_facing, True))
    return tuple(rows)


def _prepare_arena_state(candidate, prefix, history_view, capability, *,
                         expected_content_sha256, expected_scenario,
                         expected_bindings, expected_sources):
    """Consume one state approval, then construct an inert private native graph."""
    if type(capability) is not _ArenaStateCapability:
        raise ArenaStateAdmissionRejected("exact process-local Arena state capability required")
    with _LOCK:
        record = _CAPABILITIES.pop(capability, None)
    if record is None:
        raise ArenaStateAdmissionRejected("Arena state capability is foreign, stale, or already consumed")
    # Consumption precedes every input check: even an invalid attempt burns it.
    if candidate is not record.candidate or prefix is not record.prefix or history_view is not record.history_view:
        raise ArenaStateAdmissionRejected("state capability is bound to different candidate/history objects")
    context = _validate_context(candidate, prefix, history_view,
        expected_content_sha256=expected_content_sha256,
        expected_scenario=expected_scenario,
        expected_bindings=expected_bindings,
        expected_sources=expected_sources)
    candidate_view, prefix_bytes, bindings, sources = context
    prefix_rows = _prefix_view_rows(history_view)
    if (candidate.to_bytes() != record.candidate_bytes
            or candidate.content_sha256 != record.candidate_digest
            or prefix_bytes != record.prefix_bytes
            or expected_scenario != record.scenario
            or bindings != record.expected_bindings
            or sources != record.expected_sources
            or record.policy_context != "host deliberately selected exact B2 bytes plus the separately B1-prepared history and bindings"):
        raise ArenaStateAdmissionRejected("host-approved B2 state/context changed before admission")
    anchor, beings = _construct_private_beings(candidate_view, candidate)
    actual = _native_inspection(beings)
    expected = tuple(ArenaNativeBeingInspection(
        row.being_id, row.name, row.definition_name, row.hit_points,
        row.position_hex, row.geometry[0], row.geometry[1],
        row.top_facing, row.front_facing, True)
        for row in candidate_view.participants)
    if actual != expected:
        raise ArenaStateAdmissionRejected("native read-only Being projection differs from admitted B2 candidate")
    view = ArenaStateAdmissionView(
        SCHEMA, TRUST, candidate.content_sha256,
        prefix.content_sha256, candidate_view.universe_id, candidate_view.encounter_id,
        candidate_view.time, candidate_view.committed_boundary,
        tuple((key, row["source_sha256"], row["display_name"],
               row["native_being_id"], row["native_definition_name"], row["position_hex"])
              for key, row in sorted(prefix_rows.items())),
        actual, candidate_view, history_view, candidate_view.rng_role, candidate_view.rng_scope,
        "NO LIVE ENCOUNTER OR CONTINUATION; no Action scheduling, receipt issuance, or RNG authority")
    result = QuarantinedArenaState(view)
    with _LOCK:
        # Retain the exact inputs which produced this quarantined graph. Later
        # bounded Arena policies may consume the graph only after revalidating
        # this same B1/B2 pair and host selection.
        _PRIVATE_NATIVE[result] = (
            anchor, beings, candidate, prefix, history_view,
            record.scenario, record.expected_bindings, record.expected_sources,
        )
    return result


def _private_native_beings(result):
    """Internal test/host hook; never include in the public result API."""
    if type(result) is not QuarantinedArenaState:
        raise ArenaStateAdmissionRejected("quarantined Arena result required")
    with _LOCK:
        graph = _PRIVATE_NATIVE.get(result)
    if graph is None:
        raise ArenaStateAdmissionRejected("quarantined native graph is no longer available")
    return graph[1]


def _private_admitted_inputs(result):
    """Return the exact B1/B2 objects and host expectations for private adapters."""
    if type(result) is not QuarantinedArenaState:
        raise ArenaStateAdmissionRejected("quarantined Arena result required")
    with _LOCK:
        graph = _PRIVATE_NATIVE.get(result)
    if graph is None or len(graph) != 8:
        raise ArenaStateAdmissionRejected("quarantined Arena graph is absent or already consumed")
    return graph[2:]


def _consume_private_native_graph(result, expected_beings):
    """Transfer the exact private graph once to an approved Arena activation."""
    if type(result) is not QuarantinedArenaState:
        raise ArenaStateAdmissionRejected("quarantined Arena result required")
    with _LOCK:
        graph = _PRIVATE_NATIVE.get(result)
        if graph is None or len(graph) != 8 or graph[1] is not expected_beings:
            raise ArenaStateAdmissionRejected("quarantined Arena graph changed or was already consumed")
        del _PRIVATE_NATIVE[result]
    return graph[:2]
