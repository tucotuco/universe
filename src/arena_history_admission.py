"""Host-authorized, detached inspection of one validated Arena history prefix.

This module does not restore a native Encounter. Calling the private approval
factory is an application-host policy decision; validation and a digest alone
never establish trust or original publisher authenticity.
"""
from dataclasses import dataclass
import base64
import re
from threading import Lock
from weakref import WeakKeyDictionary

from arena_history_prefix import (
    ArenaHistoryRejected,
    ArenaSpotHistoryPrefix,
    decode_arena_history_prefix,
)


VIEW_SCHEMA = "universe.arena.host-accepted-spot-history-view/1"
VIEW_TRUST = (
    "host-accepted local historical claim; original native publisher receipts "
    "are not established"
)
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class ArenaAdmissionRejected(ValueError):
    """Input, host admission or prepared-view access is not supported."""


@dataclass(frozen=True)
class ExpectedArenaBinding:
    """Host-authored expectation for one source-record-to-Being binding."""

    binding_key: str
    source_sha256: str
    display_name: str
    native_being_id: str
    native_definition_name: str
    position_hex: tuple


@dataclass(frozen=True)
class ExpectedArenaScenario:
    """Host-authored identity and interval expectations for the fixed Arena."""

    universe_id: str
    encounter_id: str
    action_id: str
    actor_id: str
    target_id: str
    start_time: str
    through_boundary: int


@dataclass(frozen=True)
class ArenaHistoricalSpot:
    action_id: str
    actor_id: str
    target_id: str
    start_time: str
    nominal_end: str
    resolved_boundary: int
    outcome: str
    metadata: tuple


@dataclass(frozen=True)
class ArenaHistoricalEffect:
    identity: tuple
    kind: str
    data: tuple


@dataclass(frozen=True)
class ArenaHistoricalTarget:
    being_id: str
    position_hex: tuple
    aware_of: tuple


@dataclass(frozen=True)
class ArenaHistoricalBinding:
    binding_key: str
    source_sha256: str
    source_bytes: bytes
    display_name: str
    native_being_id: str
    native_definition_name: str
    position_hex: tuple


@dataclass(frozen=True)
class ArenaObserverHistoryView:
    """Only the selected participant's own Awareness from the historical view."""

    trust: str
    through_boundary: int
    observer_id: str
    aware_of: tuple


@dataclass(frozen=True)
class HostAcceptedArenaHistoryView:
    """Detached immutable host inspection; contains no native simulation objects."""

    schema: str
    trust: str
    source_trust: str
    universe_id: str
    encounter_id: str
    through_boundary: int
    boundaries: tuple
    spot: ArenaHistoricalSpot
    effects: tuple
    targets: tuple
    npc_bindings: tuple

    def observer_view(self, observer_id):
        """Return only that participant's Awareness, without Reality coordinates."""
        if type(observer_id) is not str or not observer_id:
            raise ArenaAdmissionRejected("observer identity must be a nonempty string")
        target = next((row for row in self.targets if row.being_id == observer_id), None)
        if target is None:
            raise ArenaAdmissionRejected("observer is not a participant in this Arena prefix")
        return ArenaObserverHistoryView(
            self.trust, self.through_boundary, observer_id, target.aware_of)

    def host_summary(self):
        """Build a fresh JSON-compatible copy for explicitly omniscient host display."""
        return {
            "schema": self.schema,
            "trust": self.trust,
            "source_trust": self.source_trust,
            "universe_id": self.universe_id,
            "encounter_id": self.encounter_id,
            "through_boundary": self.through_boundary,
            "boundaries": list(self.boundaries),
            "spot": {
                "action_id": self.spot.action_id,
                "actor_id": self.spot.actor_id,
                "target_id": self.spot.target_id,
                "start_time": self.spot.start_time,
                "nominal_end": self.spot.nominal_end,
                "resolved_boundary": self.spot.resolved_boundary,
                "outcome": self.spot.outcome,
                "metadata": dict(self.spot.metadata),
            },
            "effects": [{
                "identity": list(row.identity),
                "kind": row.kind,
                "data": _thaw_record(row.data),
            } for row in self.effects],
            "targets": [{
                "being_id": row.being_id,
                "position_hex": list(row.position_hex),
                "aware_of": list(row.aware_of),
            } for row in self.targets],
            "npc_bindings": [{
                "binding_key": row.binding_key,
                "source_sha256": row.source_sha256,
                "display_name": row.display_name,
                "native_being_id": row.native_being_id,
                "native_definition_name": row.native_definition_name,
                "position_hex": list(row.position_hex),
            } for row in self.npc_bindings],
            "continuation": "not a live restored Encounter; no authoritative continuation",
        }


class _ArenaAdmissionCapability:
    __slots__ = ("__weakref__",)

    def __reduce__(self):
        raise TypeError("Arena admission capability is process-local and cannot be serialized")

    def __reduce_ex__(self, protocol):
        raise TypeError("Arena admission capability is process-local and cannot be serialized")

    def __repr__(self):
        return "<opaque Arena history admission capability>"


@dataclass(frozen=True)
class _AdmissionRecord:
    prefix: object
    canonical_bytes: bytes
    digest: str
    expected_scenario: object
    expected_bindings: tuple
    policy_context: str


_CAPABILITIES = WeakKeyDictionary()
_CAPABILITY_LOCK = Lock()


def _validate_expected_bindings(rows):
    if type(rows) is not tuple or len(rows) != 2 or any(type(row) is not ExpectedArenaBinding for row in rows):
        raise ArenaAdmissionRejected("host must explicitly provide exactly two expected Arena bindings")
    keys = tuple(row.binding_key for row in rows)
    ids = tuple(row.native_being_id for row in rows)
    digests = tuple(row.source_sha256 for row in rows)
    if (len(set(keys)) != 2 or len(set(ids)) != 2 or len(set(digests)) != 2
            or set(keys) != {"arena-ari", "arena-bex"}
            or set(ids) != {"arena/being/ari", "arena/being/bex"}):
        raise ArenaAdmissionRejected("expected bindings do not describe the fixed two-person Arena")
    for row in rows:
        if (any(type(value) is not str or not value for value in (
                row.binding_key, row.display_name, row.native_being_id,
                row.native_definition_name))
                or type(row.source_sha256) is not str
                or _DIGEST.fullmatch(row.source_sha256) is None
                or type(row.position_hex) is not tuple or len(row.position_hex) != 3
                or any(type(value) is not str for value in row.position_hex)):
            raise ArenaAdmissionRejected("an expected Arena binding is malformed")
    return tuple(sorted(rows, key=lambda row: row.binding_key))


def _validate_expected_scenario(value):
    if type(value) is not ExpectedArenaScenario:
        raise ArenaAdmissionRejected("host must explicitly provide expected Arena scenario identities")
    if (type(value.universe_id) is not str or not value.universe_id
            or value.universe_id != "0"
            or value.encounter_id != "npc-arena/encounter/1"
            or value.action_id != "npc-arena/action/spot-ari-bex"
            or value.actor_id != "arena/being/ari"
            or value.target_id != "arena/being/bex"
            or value.start_time != "0x0.0p+0"
            or type(value.through_boundary) is not int or value.through_boundary != 6):
        raise ArenaAdmissionRejected("expected scenario is outside the fixed six-boundary Ari/Bex Arena")
    return value


def _revalidate_prefix(prefix):
    if type(prefix) is not ArenaSpotHistoryPrefix:
        raise ArenaAdmissionRejected("validated ArenaSpotHistoryPrefix/1 object required")
    try:
        raw = prefix.to_bytes()
        checked = decode_arena_history_prefix(raw)
    except (ArenaHistoryRejected, TypeError, ValueError) as exc:
        raise ArenaAdmissionRejected(f"Arena historical claim failed revalidation: {exc}") from exc
    if (checked.payload() != prefix.payload()
            or checked.content_sha256 != prefix.content_sha256):
        raise ArenaAdmissionRejected("Arena prefix object differs from its canonical decoded content")
    return raw, checked


def _prefix_binding_expectations(prefix):
    rows = []
    for row in prefix.payload()["npc_bindings"]:
        rows.append(ExpectedArenaBinding(
            row["binding_key"], row["source_sha256"], row["display_name"],
            row["native_being_id"], row["native_definition_name"],
            tuple(row["position"])))
    return tuple(sorted(rows, key=lambda row: row.binding_key))


def _verify_host_selection(prefix, digest, expected_scenario, expected_rows):
    if type(digest) is not str or _DIGEST.fullmatch(digest) is None:
        raise ArenaAdmissionRejected("host must select an exact canonical SHA-256 digest")
    if prefix.content_sha256 != digest:
        raise ArenaAdmissionRejected("host-selected digest does not identify this exact Arena prefix")
    spot = prefix.payload()["spot"]
    if (prefix.universe_id != expected_scenario.universe_id
            or prefix.encounter_id != expected_scenario.encounter_id
            or prefix.start_time != expected_scenario.start_time
            or prefix.through_boundary != expected_scenario.through_boundary
            or spot["action_id"] != expected_scenario.action_id
            or spot["actor_id"] != expected_scenario.actor_id
            or spot["target_id"] != expected_scenario.target_id):
        raise ArenaAdmissionRejected("Arena prefix does not match the host-selected scenario")
    if _prefix_binding_expectations(prefix) != expected_rows:
        raise ArenaAdmissionRejected("Arena source-to-native bindings differ from host expectations")


def _host_authorize_arena_history(prefix, *, expected_content_sha256,
                                  expected_scenario, expected_bindings):
    """Explicit host decision for this exact claim; not publisher authentication.

    The caller is the trusted local application host. This private function
    cannot inspect or enforce why the host trusts its local input.
    """
    raw, checked = _revalidate_prefix(prefix)
    scenario = _validate_expected_scenario(expected_scenario)
    expected_rows = _validate_expected_bindings(expected_bindings)
    _verify_host_selection(checked, expected_content_sha256, scenario, expected_rows)
    if raw != checked.to_bytes():
        raise ArenaAdmissionRejected("Arena prefix did not retain canonical bytes")
    capability = _ArenaAdmissionCapability()
    record = _AdmissionRecord(
        prefix, raw, checked.content_sha256, scenario, expected_rows,
        "host deliberately selected exact prefix digest and source/native bindings")
    with _CAPABILITY_LOCK:
        _CAPABILITIES[capability] = record
    return capability


def _freeze_record(value):
    if type(value) is dict:
        return tuple((key, _freeze_record(value[key])) for key in sorted(value))
    if type(value) is list:
        return tuple(_freeze_record(item) for item in value)
    if type(value) in (str, int, float, bool) or value is None:
        return value
    raise ArenaAdmissionRejected("validated Arena data contains a non-JSON value")


def _thaw_record(value):
    if type(value) is tuple:
        if all(type(row) is tuple and len(row) == 2 and type(row[0]) is str for row in value):
            return {key: _thaw_record(item) for key, item in value}
        return [_thaw_record(item) for item in value]
    return value


def _build_view(prefix):
    data = prefix.payload()
    spot = data["spot"]
    result = ArenaHistoricalSpot(
        spot["action_id"], spot["actor_id"], spot["target_id"], spot["start_time"],
        spot["nominal_end"], spot["resolved_boundary"], spot["outcome"],
        tuple((key, spot["metadata"][key]) for key in sorted(spot["metadata"])))
    effects = tuple(ArenaHistoricalEffect(
        tuple(row["identity"]), row["kind"], _freeze_record(row["data"]))
        for row in data["effects"])
    targets = tuple(ArenaHistoricalTarget(
        row["being_id"], tuple(row["position"]), tuple(row["aware_of"]))
        for row in data["targets"])
    bindings = tuple(ArenaHistoricalBinding(
        row["binding_key"], row["source_sha256"],
        base64.b64decode(row["source_bytes_base64"], validate=True),
        row["display_name"], row["native_being_id"],
        row["native_definition_name"], tuple(row["position"]))
        for row in data["npc_bindings"])
    return HostAcceptedArenaHistoryView(
        VIEW_SCHEMA, VIEW_TRUST, data["trust"], data["universe_id"], data["encounter_id"],
        data["through_boundary"], tuple(row["boundary"] for row in data["boundaries"]),
        result, effects, targets, bindings)


def _prepare_arena_history_view(prefix, capability):
    """Consume one host approval and return an immutable, non-live history view.

    The capability is consumed before validating the supplied object, so any
    attempted use of an issued capability is single-shot, including refusal.
    """
    if type(capability) is not _ArenaAdmissionCapability:
        raise ArenaAdmissionRejected("exact process-local host admission capability required")
    with _CAPABILITY_LOCK:
        record = _CAPABILITIES.pop(capability, None)
    if record is None:
        raise ArenaAdmissionRejected("host admission is foreign, stale, or already consumed")
    if prefix is not record.prefix:
        raise ArenaAdmissionRejected("host capability is bound to a different validated prefix object")
    raw, checked = _revalidate_prefix(prefix)
    _verify_host_selection(checked, record.digest, record.expected_scenario,
                           record.expected_bindings)
    if raw != record.canonical_bytes:
        raise ArenaAdmissionRejected("host-approved Arena prefix bytes changed")
    if record.policy_context != "host deliberately selected exact prefix digest and source/native bindings":
        raise ArenaAdmissionRejected("host admission policy context is unsupported")
    return _build_view(checked)
