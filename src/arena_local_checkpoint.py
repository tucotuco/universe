"""Strict local bundle and explicit-host activation for the fixed Arena case.

This adapter joins the existing B1 history and B2 state formats without
changing either schema. It is intentionally limited to the authored Ari/Bex
fixture and never accepts a path or approval decision from an HTTP request.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile

from arena_history_admission import (
    ExpectedArenaBinding,
    ExpectedArenaScenario,
    _host_authorize_arena_history,
    _prepare_arena_history_view,
)
from arena_history_prefix import decode_arena_history_prefix
from arena_state_admission import (
    ExpectedArenaSource,
    _host_authorize_arena_state,
    _prepare_arena_state,
)
from arena_state_candidate import decode_arena_post_spot_state
from arena_state_activation import (
    _host_authorize_local_activation,
)


SCHEMA = "universe.arena.operator-bundle/1"
MAX_BUNDLE_BYTES = 16 * 1024 * 1024
_FIELDS = frozenset((
    "schema", "history_prefix_base64", "history_prefix_sha256",
    "state_candidate_base64", "state_candidate_sha256", "bundle_sha256",
))
_SCENARIO = ExpectedArenaScenario(
    "0", "npc-arena/encounter/1", "npc-arena/action/spot-ari-bex",
    "arena/being/ari", "arena/being/bex", "0x0.0p+0", 6,
)


class ArenaLocalCheckpointRejected(ValueError):
    """The local bundle, path, or host-authorized fixed-case admission failed."""


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ArenaLocalCheckpointRejected(f"bundle contains unsupported data: {exc}") from exc


def _no_duplicate_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ArenaLocalCheckpointRejected(f"duplicate bundle field {key!r}")
        value[key] = item
    return value


def encode_local_bundle(prefix, candidate):
    """Encode exactly the existing validated B1/B2 inputs in one bounded file."""
    try:
        prefix_bytes = prefix.to_bytes()
        candidate_bytes = candidate.to_bytes()
        # Re-decode to enforce the underlying closed schemas at this boundary.
        prefix = decode_arena_history_prefix(prefix_bytes)
        candidate = decode_arena_post_spot_state(candidate_bytes)
        if candidate.view().history_prefix_sha256 != prefix.content_sha256:
            raise ArenaLocalCheckpointRejected("B2 candidate is not bound to this B1 prefix")
        payload = {
            "schema": SCHEMA,
            "history_prefix_base64": base64.b64encode(prefix_bytes).decode("ascii"),
            "history_prefix_sha256": prefix.content_sha256,
            "state_candidate_base64": base64.b64encode(candidate_bytes).decode("ascii"),
            "state_candidate_sha256": candidate.content_sha256,
        }
        wire = _canonical(dict(payload, bundle_sha256=hashlib.sha256(_canonical(payload)).hexdigest()))
        if len(wire) > MAX_BUNDLE_BYTES:
            raise ArenaLocalCheckpointRejected("local Arena bundle exceeds its size limit")
        return wire
    except ArenaLocalCheckpointRejected:
        raise
    except (AttributeError, TypeError, ValueError) as exc:
        raise ArenaLocalCheckpointRejected(f"B1/B2 bundle construction refused: {exc}") from exc


def decode_local_bundle(wire):
    """Validate a canonical bundle and return its exact decoded B1/B2 objects."""
    if type(wire) is not bytes or not wire or len(wire) > MAX_BUNDLE_BYTES:
        raise ArenaLocalCheckpointRejected("local Arena bundle is empty or exceeds its size limit")
    try:
        data = json.loads(wire.decode("utf-8"), object_pairs_hook=_no_duplicate_keys)
    except ArenaLocalCheckpointRejected:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ArenaLocalCheckpointRejected(f"local Arena bundle is not valid UTF-8 JSON: {exc}") from exc
    if type(data) is not dict or set(data) != _FIELDS or data["schema"] != SCHEMA:
        raise ArenaLocalCheckpointRejected("local Arena bundle has an unsupported schema or field set")
    payload = {key: data[key] for key in data if key != "bundle_sha256"}
    if (type(data["bundle_sha256"]) is not str
            or hashlib.sha256(_canonical(payload)).hexdigest() != data["bundle_sha256"]):
        raise ArenaLocalCheckpointRejected("local Arena bundle digest does not match its fields")
    if _canonical(data) != wire:
        raise ArenaLocalCheckpointRejected("local Arena bundle is not in canonical encoding")
    try:
        prefix_bytes = base64.b64decode(data["history_prefix_base64"], validate=True)
        candidate_bytes = base64.b64decode(data["state_candidate_base64"], validate=True)
        prefix = decode_arena_history_prefix(prefix_bytes)
        candidate = decode_arena_post_spot_state(candidate_bytes)
    except (TypeError, ValueError) as exc:
        raise ArenaLocalCheckpointRejected(f"embedded B1/B2 data is invalid: {exc}") from exc
    if (prefix.content_sha256 != data["history_prefix_sha256"]
            or candidate.content_sha256 != data["state_candidate_sha256"]
            or candidate.view().history_prefix_sha256 != prefix.content_sha256):
        raise ArenaLocalCheckpointRejected("bundle B1/B2 digests or association disagree")
    return prefix, candidate


def _outside_repository(path, repository_root):
    raw = Path(path)
    if not raw.is_absolute():
        raise ArenaLocalCheckpointRejected("local bundle path must be an absolute host-configured path")
    if raw.is_symlink():
        raise ArenaLocalCheckpointRejected("local bundle path may not be a symbolic link")
    resolved = raw.resolve(strict=False)
    root = Path(repository_root).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return resolved
    raise ArenaLocalCheckpointRejected("local Arena bundles must be stored outside the repository")


def validate_local_path(path, *, repository_root, must_exist=False):
    """Validate a host-configured destination/source before starting HTTP."""
    target = _outside_repository(path, repository_root)
    if must_exist:
        if not target.is_file() or target.stat().st_size > MAX_BUNDLE_BYTES:
            raise ArenaLocalCheckpointRejected("saved Arena bundle is not a bounded regular file")
    elif not target.parent.is_dir():
        raise ArenaLocalCheckpointRejected("configured bundle destination directory must already exist")
    elif target.exists():
        raise ArenaLocalCheckpointRejected("configured bundle destination already exists; overwrite is not supported")
    return target


def write_local_bundle(path, wire, *, repository_root):
    """Atomically create a private local file; never replace an existing file."""
    target = _outside_repository(path, repository_root)
    if type(wire) is not bytes or not wire or len(wire) > MAX_BUNDLE_BYTES:
        raise ArenaLocalCheckpointRejected("bundle bytes are empty or exceed their size limit")
    decode_local_bundle(wire)
    if not target.parent.is_dir():
        raise ArenaLocalCheckpointRejected("configured bundle destination directory must already exist")
    temp_name = None
    try:
        fd, temp_name = tempfile.mkstemp(prefix=".universe-arena-", suffix=".tmp", dir=target.parent)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(wire)
            stream.flush()
            os.fsync(stream.fileno())
        # Hard-link creation is atomic and fails if the destination exists.
        os.link(temp_name, target)
        os.unlink(temp_name)
        temp_name = None
        directory_fd = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except FileExistsError as exc:
        raise ArenaLocalCheckpointRejected("refusing to overwrite an existing local Arena bundle") from exc
    except OSError as exc:
        raise ArenaLocalCheckpointRejected(f"atomic local bundle write failed: {exc}") from exc
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
    return target


def read_local_bundle(path, *, repository_root):
    """Read a bounded regular local file, rejecting repository/protected paths."""
    target = _outside_repository(path, repository_root)
    try:
        if not target.is_file() or target.stat().st_size > MAX_BUNDLE_BYTES:
            raise ArenaLocalCheckpointRejected("saved Arena bundle is not a bounded regular file")
        wire = target.read_bytes()
    except OSError as exc:
        raise ArenaLocalCheckpointRejected(f"cannot read configured local Arena bundle: {exc}") from exc
    decode_local_bundle(wire)
    return wire


def activate_approved_local_bundle(path, *, repository_root, fixture_root,
                                  host_approved, rng_seed):
    """Revalidate the fixed bundle against known NPC fixtures and C1 host gates."""
    if host_approved is not True:
        raise ArenaLocalCheckpointRejected("explicit local-host approval is required")
    if isinstance(rng_seed, bool) or type(rng_seed) is not int:
        raise ArenaLocalCheckpointRejected("a separately host-selected integer RNG seed is required")
    try:
        from examples.npc_encounter_arena import ROOT as example_root

        wire = read_local_bundle(path, repository_root=repository_root)
        prefix, candidate = decode_local_bundle(wire)
        expected_fixture_root = (Path(example_root) / "examples" / "npc_candidates").resolve()
        if Path(fixture_root).resolve() != expected_fixture_root:
            raise ArenaLocalCheckpointRejected("host fixture root is outside the fixed NPC candidate directory")
        source_bytes = {
            "arena-ari": (Path(fixture_root) / "ari.npcgen.json").read_bytes(),
            "arena-bex": (Path(fixture_root) / "bex.npcgen.json").read_bytes(),
        }
        bindings = (
            ExpectedArenaBinding("arena-ari", hashlib.sha256(source_bytes["arena-ari"]).hexdigest(),
                                 "Ari", "arena/being/ari", "Human",
                                 ("0x0.0p+0", "0x0.0p+0", "0x0.0p+0")),
            ExpectedArenaBinding("arena-bex", hashlib.sha256(source_bytes["arena-bex"]).hexdigest(),
                                 "Bex", "arena/being/bex", "Human",
                                 ("0x1.8000000000000p+1", "0x0.0p+0", "0x0.0p+0")),
        )
        # Keep the fixture root supplied by the application host, not from the bundle.
        history_capability = _host_authorize_arena_history(
            prefix, expected_content_sha256=prefix.content_sha256,
            expected_scenario=_SCENARIO, expected_bindings=bindings)
        history = _prepare_arena_history_view(prefix, history_capability)
        expected_sources = tuple(ExpectedArenaSource(key, source_bytes[key])
                                 for key in ("arena-ari", "arena-bex"))
        state_capability = _host_authorize_arena_state(
            candidate, prefix, history, expected_content_sha256=candidate.content_sha256,
            expected_scenario=_SCENARIO, expected_bindings=bindings,
            expected_sources=expected_sources)
        admitted = _prepare_arena_state(
            candidate, prefix, history, state_capability,
            expected_content_sha256=candidate.content_sha256,
            expected_scenario=_SCENARIO, expected_bindings=bindings,
            expected_sources=expected_sources)
        activation_capability = _host_authorize_local_activation(admitted, rng_seed=rng_seed)
        from arena_state_activation import _activate_local_arena
        return _activate_local_arena(admitted, activation_capability)
    except ArenaLocalCheckpointRejected:
        raise
    except Exception as exc:
        # Rejection never returns the private graph/Universe and never loosens
        # the native C1 receipt or constructor safeguards.
        raise ArenaLocalCheckpointRejected(f"trusted-local fixed Arena admission refused: {exc}") from exc
