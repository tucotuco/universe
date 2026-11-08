"""Inactive, in-memory composition of the bounded native Run/Spot subset.

This module assembles already-reviewed inventory, choice and receipt data from
one coordinated capture. It does not save, restore, issue receipts, or resume a
Universe. A successful bounded envelope is not a checkpoint-readiness claim.
"""
from dataclasses import dataclass
import hashlib
import json
import weakref

from checkpoint_inventory import (
    CheckpointRejected,
    validate_checkpoint_candidate,
    capture_checkpoint_candidate,
)


ENVELOPE_SCHEMA = 'universe.native-run-spot-checkpoint-envelope/1'
_ALLOWED_DIAGNOSTICS = frozenset((
    'semantic_closure_adapter_incomplete',
    'bounded_run_spot_closure_verified',
    'receipt_rebinding_required',
))
_RECONSTRUCTION_OBLIGATIONS = (
    'reconstruct-native-Universe-Library-Beings-Encounter-and-ChoiceBook',
    'recompute-accepted-choice-declaration-signatures-from-fresh-native-objects',
    'rebind-and-authenticate-committed-receipts-and-Action-Target-storage-anchors',
    'validate-compatible-rules-adapters-and-source-before-any-restoration',
    'restore-private-RNGCursor-under-exclusive-owner-protocol',
)
_ISSUED = {}


class EnvelopeRejected(CheckpointRejected):
    """The state or detached envelope is outside this bounded contract."""


@dataclass(frozen=True)
class NativeRunSpotCheckpointEnvelope:
    schema: str
    universe_id: str
    encounter_id: str
    compatibility: tuple
    boundary_sequence: tuple
    authoritative_state: tuple
    field_closure: tuple
    accepted_choice_descriptors: tuple
    committed_receipt_chain: tuple
    private_rng: tuple
    diagnostics: tuple
    reconstruction_obligations: tuple
    bounded_envelope_validated: bool
    closure_validated: bool
    portable_schema_defined: bool
    restore_verified: bool
    content_digest: str

    def payload(self):
        return (
            self.schema, self.universe_id, self.encounter_id,
            self.compatibility, self.boundary_sequence,
            self.authoritative_state, self.field_closure,
            self.accepted_choice_descriptors, self.committed_receipt_chain,
            self.private_rng, self.diagnostics, self.reconstruction_obligations,
            self.bounded_envelope_validated, self.closure_validated,
            self.portable_schema_defined, self.restore_verified,
        )

    def to_data(self):
        """Return detached primitive/tuple data, never native handles."""
        return self.payload() + (self.content_digest,)


@dataclass(frozen=True)
class EnvelopeValidation:
    bounded_envelope_validated: bool
    diagnostics: tuple
    closure_validated: bool = False
    portable_schema_defined: bool = False
    restore_verified: bool = False


def _require(test, message):
    if not test:
        raise EnvelopeRejected(message)


def _tree(value, path='envelope'):
    """Require canonical detached primitive tuples; floats are tagged upstream."""
    kind = type(value)
    if value is None or kind in (str, int, bool):
        return
    if kind is tuple:
        for index, item in enumerate(value):
            _tree(item, f'{path}[{index}]')
        return
    raise EnvelopeRejected(f'{path} contains nonportable value type {kind.__name__}')


def _digest(payload):
    raw = json.dumps(payload, ensure_ascii=True, separators=(',', ':')).encode('ascii')
    return hashlib.sha256(raw).hexdigest()


def _rows_by_tag(body):
    _require(type(body) is tuple and body and body[0] == 'checkpoint-inventory',
             'unsupported native inventory body')
    rows = body[1:]
    _require(all(type(row) is tuple and len(row) >= 2 and type(row[0]) is str for row in rows),
             'malformed inventory section')
    tags = tuple(row[0] for row in rows)
    _require(len(tags) == len(set(tags)), 'duplicate inventory section')
    return {row[0]: row[1:] for row in rows}


def _logical_roots(sections):
    root = sections.get('root')
    _require(type(root) is tuple and len(root) == 1 and type(root[0]) is tuple
             and len(root[0]) == 2 and root[0][0] == 'reference'
             and type(root[0][1]) is tuple and len(root[0][1]) == 2
             and root[0][1][0] == 'universe', 'Universe root reference is missing')
    universe_id = root[0][1][1]
    nodes = sections.get('nodes')
    _require(type(nodes) is tuple and len(nodes) == 1 and type(nodes[0]) is tuple,
             'authoritative native node set is missing')
    encounters = tuple(node for node in nodes[0]
                       if type(node) is tuple and len(node) == 3
                       and type(node[0]) is tuple and len(node[0]) == 2
                       and node[0][0] == 'encounter'
                       and node[1] == 'encounter.Encounter')
    _require(len(encounters) == 1, 'selected Encounter root is missing or ambiguous')
    encounter_id = encounters[0][0][1]
    _require(type(universe_id) is str and universe_id and type(encounter_id) is str and encounter_id,
             'root logical IDs must be nonempty strings')
    return universe_id, encounter_id


def _parts(certificate):
    _require(type(certificate) is tuple and len(certificate) >= 1
             and certificate[0] == 'native.run-spot-field-closure/2',
             'missing or incompatible Run/Spot field-closure certificate')
    rows = certificate[1:]
    _require(all(type(row) is tuple and len(row) == 2 and type(row[0]) is str for row in rows),
             'malformed Run/Spot field-closure certificate')
    keys = tuple(row[0] for row in rows)
    _require(len(keys) == len(set(keys)), 'duplicate Run/Spot certificate section')
    return dict(rows)


def _components(candidate_envelope, diagnostics):
    _require(type(candidate_envelope) is tuple and len(candidate_envelope) == 2,
             'unsupported captured inventory envelope')
    compatibility, body = candidate_envelope
    _tree(compatibility, 'compatibility')
    _tree(body, 'authoritative_state')
    sections = _rows_by_tag(body)
    _require(sections.get('readiness') == (False, False, False),
             'captured inventory readiness flags are not false')
    _require(sections.get('host-bindings') == ((),),
             'external recipient bindings are outside this envelope')
    rng = sections.get('rng')
    _require(type(rng) is tuple and len(rng) == 3
             and rng[0] == 'caller_cursor' and rng[1] == 'exclusive_encounter',
             'private caller-owned RNG state is not represented')
    local = sections.get('bounded-run-spot-closure')
    _require(type(local) is tuple and len(local) == 1,
             'bounded semantic-closure certificate is missing')
    certificate = local[0]
    policy = _parts(certificate)
    _require(set(policy) == {'participants', 'being-definitions', 'required-practice-skills',
                             'participant-state', 'receipt-descriptors',
                             'accepted-choice-descriptors', 'field-policy',
                             'ownership-policy'},
             'Run/Spot certificate fields are incomplete or unknown')
    receipts = policy['receipt-descriptors']
    _require(type(receipts) is tuple and len(receipts) <= 1,
             'receipt descriptor set is missing or ambiguous')
    receipt_chain = receipts[0] if receipts else ()
    choices = policy['accepted-choice-descriptors']
    _require(type(choices) is tuple, 'accepted future choices are not a closed tuple')
    boundaries = ()
    if receipt_chain:
        _require(type(receipt_chain) is tuple and len(receipt_chain) == 8
                 and receipt_chain[0] == 'universe.committed-native-receipt-chain/1',
                 'unsupported committed receipt-chain schema')
        _require(receipt_chain[1:3] == _logical_roots(sections),
                 'receipt chain refers to different Universe/Encounter roots')
        receipt_rows = receipt_chain[4]
        _require(type(receipt_rows) is tuple and 1 <= len(receipt_rows) <= 2,
                 'committed receipt chain must contain one or two boundaries')
        boundaries = tuple(row[0] for row in receipt_rows
                           if type(row) is tuple and len(row) == 9 and type(row[0]) is int)
        _require(len(boundaries) == len(receipt_rows)
                 and boundaries == tuple(range(boundaries[0], boundaries[0] + len(boundaries))),
                 'committed boundaries are missing, duplicate, or unordered')
        _require(receipt_chain[6] == choices,
                 'accepted future choices disagree between certificate and receipt chain')
    _require(type(diagnostics) is tuple, 'diagnostics are not a closed tuple')
    encoded_diagnostics = tuple((d.code, d.owner, d.field, d.reason) for d in diagnostics)
    _tree(encoded_diagnostics, 'diagnostics')
    codes = {row[0] for row in encoded_diagnostics}
    _require('bounded_run_spot_closure_verified' in codes
             and not codes.intersection({'bounded_run_spot_closure_refused',
                                         'unsupported_native_value',
                                         'portable_choice_descriptor_unsupported',
                                         'unbound_external_recipient',
                                         'rng_authority_scope_unbound'}),
             'native Run/Spot field closure was refused or contains unsupported data')
    _require(codes <= _ALLOWED_DIAGNOSTICS,
             'captured native state has diagnostics outside the bounded envelope contract')
    universe_id, encounter_id = _logical_roots(sections)
    return (
        compatibility, universe_id, encounter_id, boundaries, body, certificate,
        choices, receipt_chain, rng, encoded_diagnostics,
    )


def _payload(candidate_envelope, diagnostics):
    (compatibility, universe_id, encounter_id, boundaries, body, certificate,
     choices, receipts, rng, encoded_diagnostics) = _components(candidate_envelope, diagnostics)
    return (
        ENVELOPE_SCHEMA, universe_id, encounter_id, compatibility, boundaries,
        body, certificate, choices, receipts, rng, encoded_diagnostics,
        _RECONSTRUCTION_OBLIGATIONS, True, False, False, False,
    )


def _make(candidate):
    payload = _payload(candidate.envelope, candidate.diagnostics)
    _tree(payload)
    digest = _digest(payload)
    return NativeRunSpotCheckpointEnvelope(*payload, digest)


def _seal(envelope):
    return _digest(envelope.payload())


def _validate_shape(envelope):
    _require(type(envelope) is NativeRunSpotCheckpointEnvelope,
             'native Run/Spot envelope required')
    names = tuple(NativeRunSpotCheckpointEnvelope.__dataclass_fields__)
    data = object.__getattribute__(envelope, '__dict__')
    _require(type(data) is dict and set(data) == set(names), 'unknown envelope fields')
    _require(envelope.schema == ENVELOPE_SCHEMA, 'unknown envelope schema version')
    _tree(envelope.payload())
    _require(envelope.closure_validated is False
             and envelope.portable_schema_defined is False
             and envelope.restore_verified is False,
             'bounded envelope cannot assert global checkpoint readiness')
    _require(envelope.bounded_envelope_validated is True,
             'bounded envelope assembly status is not validated')
    _require(type(envelope.content_digest) is str
             and envelope.content_digest == _seal(envelope),
             'envelope content digest mismatch')
    # Reuse the closed source sections to reject internally inconsistent copies.
    expected = _payload((envelope.compatibility, envelope.authoritative_state),
                        tuple(_DiagnosticView(*row) for row in envelope.diagnostics))
    _require(expected == envelope.payload(), 'envelope components do not close over one captured state')


@dataclass(frozen=True)
class _DiagnosticView:
    code: str
    owner: tuple
    field: str
    reason: str


def assemble_native_run_spot_envelope(world, encounter, *, quiescent=False,
                                      rng_scope=None):
    """Capture and assemble one inactive, detached Run/Spot envelope.

    The existing inventory capture owns the coordinated read, RNG ownership
    check, descriptor generation, field-closure proof, and read-set comparison.
    This function only composes its immutable result; it never rereads or
    mutates the native graph after that capture.
    """
    _require(quiescent is True and rng_scope == 'exclusive_encounter',
             'explicit quiescent ownership and exclusive Encounter RNG scope are required')
    source = capture_checkpoint_candidate(
        world, encounter, quiescent=True, rng_scope=rng_scope,
        native_adapters=True, bindings=(),
    )
    envelope = _make(source)
    _validate_shape(envelope)
    key = id(envelope)
    _ISSUED[key] = (
        weakref.ref(envelope, lambda ref, key=key: _ISSUED.pop(key, None)),
        weakref.ref(world), weakref.ref(encounter), source, _seal(envelope),
    )
    return envelope


def validate_native_run_spot_envelope(world, encounter, envelope, *, quiescent=False):
    """Validate same-process provenance, integrity, and current source freshness."""
    _validate_shape(envelope)
    issued = _ISSUED.get(id(envelope))
    _require(issued is not None and issued[0]() is envelope
             and issued[1]() is world and issued[2]() is encounter,
             'foreign, copied, or non-issued envelope')
    source = issued[3]
    _require(source is not None and _seal(envelope) == issued[4],
             'modified or expired native Run/Spot envelope')
    try:
        inventory_validation = validate_checkpoint_candidate(
            world, encounter, source, quiescent=quiescent)
    except CheckpointRejected as exc:
        raise EnvelopeRejected('stale or invalid source capture: ' + str(exc)) from exc
    _require(inventory_validation.inventory_validated,
             'source inventory contains unsupported native values')
    expected = _make(source)
    _require(expected == envelope,
             'envelope components no longer match the coherent source capture')
    return EnvelopeValidation(True, envelope.diagnostics)
