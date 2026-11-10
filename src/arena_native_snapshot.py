"""Versioned native object-graph snapshots for the implemented Arena subset.

This module is deliberately scoped to generated Arena. It carries the native
inventory graph verbatim and rebinds only process-local locks, Choice
signatures, Target/action anchors, receipt issuance, and progression ownership.
No Action or committed boundary is evaluated during restore.
"""
from __future__ import annotations

import hashlib
import json
import math
import threading
from types import MappingProxyType

SCHEMA = 'universe.generated-arena-native-state/2'
_FIELDS = frozenset(('schema', 'compatibility', 'inventory', 'sha256'))
MAX_BYTES = 64 * 1024 * 1024

# Exact native type closure exercised by the current Arena UI: generated
# Beings, typed ground/carry Objects, Run, Pick up, Draw, Dagger strikes, their Choice and
# committed inspection records, and observer-owned Arena evidence.
_ARENA_TAGS = frozenset({
    'universe.Universe','library.Library','event.Event','encounter.Encounter',
    'encounter.ArenaActionActivation','encounter.ArenaMovementActivation',
    'encounter.EncounterInitiation','action_choice.ChoiceBook','action_choice.ChoiceMember',
    'action_choice.ChoiceView','action_choice._Accepted','action_choice.Reservation',
    'scheduling.PreparedSchedule','actiondictionary.ActionDictionary',
    'being.BeingDictionary','being.BeingDefinition','being.BeingInstance',
    'object.ObjectRegistry','object.ObjectDictionary','object.ObjectDefinition','object.ObjectInstance',
    'weapon.WeaponDictionary','weapon.WeaponDefinition','weapon.WeaponInstance',
    'armor.ArmorDictionary','armor.ArmorDefinition','armor.ArmorInstance',
    'skill.SkillDictionary','skill.SkillDefinition','skill.Skills','abilities.Abilities',
    'states.States','speeds.Speed','strategy.Strategy','exertion.Exertion',
    'physical_fatigue.PhysicalFatigueState','spatial.state.CartesianPosition',
    'spatial.state.SpatialState','arena_perception.ArenaPerceptionEvidence',
    'arena_perception.ArenaPerceptionLedger','activities.RunAction',
    'activities.PickUpAction','activities.ReadyWeaponAction','melee_combat.MeleeStrike',
    'melee_combat.MeleeResult',
    'atomic_publication.PublishedInterval','atomic_publication.TargetIntervalRecord',
    'encounter_inspection.CommittedBoundaryRecord','encounter_inspection.EntityInspection',
    'action_settlement.TargetCandidate','action_evaluation.ActionProposal',
    'action_evaluation.ActionView','action_evaluation.EffectIdentity',
    'action_evaluation.IdentifiedEffect','action_evaluation.DamageEffect',
    'action_evaluation.ProtectionEffect','action_evaluation.PickupEffect',
    'action_evaluation.ReadyWeaponEffect','action_evaluation.PracticeEffect',
    'observer_proposals.ActionOutcomeEffect','observer_proposals.LifecycleEffect',
    'observer_proposals.ReservationReleaseEffect',
    'observer_proposals.ObserverProjection','frozen_practice.PracticeProjection',
    'frozen_practice.CandidatePracticeUse','frozen_practice.CandidateSkillTransition',
    'experience.SkillUse','experience.BatchSkillUse','interval_staging.AuthorityReference',
    'interval_staging.StartFence','interval_staging.RegistrationIntent',
    'interval_staging.QueueProjection',
    'encounter_fatigue_bridge.FrozenFatigueFrame','encounter_fatigue_bridge.FrozenFatigueView',
    'ordered-map','list','tuple','set','frozenset',
})


class ArenaNativeSnapshotRejected(ValueError):
    pass


def _need(value, message):
    if not value:
        raise ArenaNativeSnapshotRejected(message)


def _tuples(value):
    if type(value) is list:
        return tuple(_tuples(row) for row in value)
    if type(value) is dict:
        return {key: _tuples(row) for key, row in value.items()}
    return value


def _json(value):
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is tuple:
        return [_json(row) for row in value]
    raise ArenaNativeSnapshotRejected('native snapshot contains a non-data value')


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=True,
            separators=(',', ':'), allow_nan=False).encode('ascii')
    except (TypeError, ValueError, RecursionError) as exc:
        raise ArenaNativeSnapshotRejected(f'native snapshot is not canonical data: {exc}') from exc


def _tree(value, depth=0, count=None):
    if count is None:
        count = [0]
    count[0] += 1
    _need(count[0] <= 1_000_000 and depth <= 128,
          'native Arena state exceeds structural limits')
    if value is None or type(value) in (bool, int):
        return
    if type(value) is str:
        _need(len(value) <= 1_000_000, 'native Arena string exceeds the field limit')
        return
    if type(value) is list:
        for row in value:
            _tree(row, depth + 1, count)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for row in value.values():
            _tree(row, depth + 1, count)
        return
    raise ArenaNativeSnapshotRejected('native Arena state has unsupported JSON data')


def capture(world, encounter, rng_owner):
    from checkpoint_inventory import capture_checkpoint_candidate, _compatibility
    from transactional_progression import is_quarantined
    _need(not is_quarantined(encounter), 'quarantined Arena cannot be saved')
    candidate = capture_checkpoint_candidate(world, encounter, quiescent=True,
        rng_scope='exclusive_encounter', rng_owner=rng_owner)
    # These three markers are process-local identities/derived values. The
    # restore owner rebuilds and checks them from the exact captured graph.
    allowed = {'semantic_closure_adapter_incomplete',
               'native_signature_rebuild_required', 'receipt_rebinding_required'}
    _need(all(row.code in allowed for row in candidate.diagnostics),
          'native Arena state contains a value outside the supported save contract: '
          + ', '.join(sorted({row.code for row in candidate.diagnostics if row.code not in allowed})))
    _need(candidate.envelope[0] == _compatibility(), 'native compatibility changed during capture')
    return candidate.envelope


def encode(inventory):
    from checkpoint_inventory import _compatibility
    payload = {'schema': SCHEMA, 'compatibility': _compatibility(),
               'inventory': inventory}
    body = _canonical(payload)
    wire = _canonical(dict(payload, sha256=hashlib.sha256(body).hexdigest()))
    _need(len(wire) <= MAX_BYTES, 'native Arena state exceeds the file limit')
    return wire


def decode(wire):
    from checkpoint_inventory import _compatibility
    _need(type(wire) is bytes and 0 < len(wire) <= MAX_BYTES,
          'native Arena state is empty or exceeds the file limit')
    try:
        data = json.loads(wire.decode('ascii'), object_pairs_hook=_unique,
            parse_constant=lambda _x: (_ for _ in ()).throw(ValueError('nonfinite number')))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ArenaNativeSnapshotRejected(f'native Arena state JSON is invalid: {exc}') from exc
    _tree(data)
    _need(type(data) is dict and set(data) == _FIELDS and data['schema'] == SCHEMA,
          'native Arena state has an unknown schema or field set')
    payload = {key: data[key] for key in data if key != 'sha256'}
    _need(type(data['sha256']) is str and hashlib.sha256(_canonical(payload)).hexdigest() == data['sha256'],
          'native Arena state digest does not match')
    _need(_canonical(data) == wire, 'native Arena state is not canonical')
    _need(_tuples(data['compatibility']) == _compatibility(),
          'saved native Arena implementation/rules differ from this runtime')
    try:
        inventory = _tuples(data['inventory'])
    except RecursionError as exc:
        raise ArenaNativeSnapshotRejected('native Arena state nesting exceeds limits') from exc
    _validate_inventory(inventory)
    return inventory


def _unique(rows):
    result = {}
    for key, value in rows:
        if key in result:
            raise ValueError('duplicate JSON field')
        result[key] = value
    return result


def _validate_inventory(envelope):
    from checkpoint_inventory import _TYPES
    _need(type(envelope) is tuple and len(envelope) == 2,
          'native inventory envelope is malformed')
    compatibility, body = envelope
    from checkpoint_inventory import _compatibility
    _need(compatibility == _compatibility(), 'native inventory compatibility mismatch')
    _need(type(body) is tuple and len(body) == 5 and body[0] == 'checkpoint-inventory',
          'native inventory body is outside Arena schema')
    sections = {row[0]: row[1:] for row in body[1:] if type(row) is tuple and row}
    _need(set(sections) == {'root', 'nodes', 'rng', 'readiness'},
          'native inventory sections are incomplete or unknown')
    _need(sections['readiness'] == (False, False, False), 'unsupported inventory readiness claim')
    _need(sections['rng'][:2] == ('caller_cursor', 'exclusive_encounter'),
          'Arena save requires its exclusive caller-owned RNG cursor')
    nodes_row = sections['nodes']
    _need(len(nodes_row) == 1 and type(nodes_row[0]) is tuple,
          'native inventory node table is malformed')
    nodes = nodes_row[0]
    _need(0 < len(nodes) <= 250000, 'native inventory node count is out of bounds')
    refs = set()
    exact_types = {f'{cls.__module__}.{cls.__name__}' for cls in _TYPES}
    allowed_tags = exact_types & _ARENA_TAGS
    allowed_tags |= {'ordered-map', 'list', 'tuple', 'set', 'frozenset'}
    for row in nodes:
        _need(type(row) is tuple and len(row) == 3 and type(row[0]) is tuple
              and row[1] in allowed_tags and row[0] not in refs,
              'native graph contains a duplicate identity or unsupported type')
        refs.add(row[0])
    _need(sections['root'] == (('reference', ('universe', _root_id(nodes, 'universe.Universe'))),),
          'native inventory root is not its unique Universe')
    _need(any(row[1] == 'encounter.Encounter' for row in nodes)
          and any(row[1] == 'being.BeingInstance' for row in nodes),
          'native Arena Encounter/Being nodes are missing')
    # Resolve every logical reference and exact native class before allocating.
    _walk_refs(envelope, refs)


def _root_id(nodes, tag):
    rows = [row[0][1] for row in nodes if row[1] == tag and row[0][0] == 'universe']
    _need(len(rows) == 1, f'expected one native {tag}')
    return rows[0]


def _walk_refs(value, refs):
    if type(value) is tuple:
        if value and value[0] == 'reference':
            _need(len(value) == 2 and value[1] in refs, 'native graph has a dangling reference')
        for row in value:
            _walk_refs(row, refs)


def restore(envelope):
    """Materialize an exact private graph and bind ordinary native progression."""
    from checkpoint_inventory import _TYPES
    from atomic_publication import RNGCursor
    from universe import Universe
    from encounter import Encounter
    from encounter_inspection import CommittedBoundaryRecord, fingerprint, inspect_encounter
    from action_choice import ChoiceBook, _Accepted, declaration
    from transactional_progression import (_bind_restored_arena_progression,
        _unbind_restored_arena_progression)

    _validate_inventory(envelope)
    body = envelope[1]
    sections = {row[0]: row[1:] for row in body[1:]}
    nodes = sections['nodes'][0]
    by_ref = {row[0]: row for row in nodes}
    classes = {f'{cls.__module__}.{cls.__name__}': cls for cls in _TYPES}
    cache = {}
    for ref, tag, content in nodes:
        if tag in classes:
            cache[ref] = object.__new__(classes[tag])
        elif tag == 'ordered-map': cache[ref] = {}
        elif tag == 'list': cache[ref] = []
        elif tag == 'set': cache[ref] = set()
        elif tag == 'frozenset': pass
        elif tag == 'tuple': pass

    def scalar(value):
        _need(type(value) is tuple and value, 'malformed native value')
        tag = value[0]
        if tag == 'null': _need(len(value) == 1, 'bad null'); return None
        if tag == 'boolean': _need(len(value) == 2 and type(value[1]) is bool, 'bad bool'); return value[1]
        if tag == 'string': _need(len(value) == 2 and type(value[1]) is str, 'bad string'); return value[1]
        if tag == 'integer':
            result = int(value[1]); _need(str(result) == value[1], 'bad integer'); return result
        if tag == 'binary64':
            result = float.fromhex(value[1]); _need(math.isfinite(result) and result.hex() == value[1], 'bad float'); return result
        if tag == 'reference': return container(value[1])
        if tag in ('excluded-transient', 'excluded-out-of-scope-empty-registry',
                   'derived-rebuild-required'):
            return _OMIT
        if tag == 'registration-index':
            _need(len(value) == 2 and type(value[1]) is tuple,
                  'malformed native Choice registration index')
            result = {}
            for aid, choice_ref, packet_ref, marker in value[1]:
                _need(marker == ('derived-rebuild-required', 'declaration-signature'),
                      'native Choice registration signature is malformed')
                choice_id = scalar(choice_ref)
                _need(type(choice_id) is str, 'native Choice registration identity is malformed')
                result[aid] = (choice_id, scalar(packet_ref), None)
            return result
        raise ArenaNativeSnapshotRejected('unknown native value tag')

    building = set()
    def container(ref):
        row = by_ref[ref]; tag, content = row[1], row[2]
        if ref in cache and tag not in ('tuple', 'frozenset'):
            return cache[ref]
        if tag == 'tuple':
            if ref not in cache:
                building.add(ref); value = tuple(scalar(v) for v in content); building.remove(ref); cache[ref] = value
            return cache[ref]
        if tag == 'frozenset':
            if ref not in cache: cache[ref] = frozenset(scalar(v) for v in content)
            return cache[ref]
        if tag in ('ordered-map', 'list', 'set'):
            return container(ref)
        _need(ref in cache, 'native logical reference is missing')
        return cache[ref]

    # Materialize tuple shells first, then fill native fields, then hash-based
    # containers. EffectIdentity-like frozen records can be map keys and must
    # have their fields before their hashes are requested.
    for ref, tag, content in nodes:
        if tag == 'tuple': cache[ref] = tuple(scalar(v) for v in content)
    for ref, tag, content in nodes:
        if tag in classes:
            obj = cache[ref]
            data = {}
            for name, value in content:
                decoded = scalar(value)
                if decoded is not _OMIT:
                    data[name] = decoded
            for name, value in data.items(): object.__setattr__(obj, name, value)
    for ref, tag, content in nodes:
        if tag == 'ordered-map':
            obj = cache[ref]
            for key, value in content: obj[scalar(key)] = scalar(value)
        elif tag == 'list': cache[ref].extend(scalar(v) for v in content)
        elif tag == 'set': cache[ref].update(scalar(v) for v in content)
        elif tag == 'frozenset': cache[ref] = frozenset(scalar(v) for v in content)

    # Restore is an authoritative admission boundary: never normalize a file
    # whose saved measured state was written with a different precision rule.
    from object import ObjectDefinition
    from spatial.state import SpatialState
    from spatial.geometry import AxisAlignedBox, Sphere
    from measured_values import is_truncated_measurement
    for obj in cache.values():
        if isinstance(obj, ObjectDefinition):
            for name in ObjectDefinition._MEASURED_ATTRIBUTES:
                if not is_truncated_measurement(getattr(obj, name, None)):
                    raise ArenaNativeSnapshotRejected(
                        f'native {name} measurement is not canonically truncated')
        if type(obj) is SpatialState:
            if any(not is_truncated_measurement(value)
                   for value in obj.position.as_tuple()):
                raise ArenaNativeSnapshotRejected(
                    'native Cartesian position is not canonically truncated')
        if type(obj) in (Sphere, AxisAlignedBox):
            if any(not is_truncated_measurement(getattr(obj, name))
                   for name in obj._MEASURED_ATTRIBUTES):
                raise ArenaNativeSnapshotRejected(
                    'native geometry measurement is not canonically truncated')

    world = next(cache[ref] for ref, tag, _ in nodes if tag == 'universe.Universe')
    encounter = next(cache[ref] for ref, tag, _ in nodes if tag == 'encounter.Encounter')
    _need(type(world) is Universe and type(encounter) is Encounter
          and encounter.universe is world, 'native Arena roots disagree')
    # Recreate process-local synchronization/runtime state omitted by inventory.
    world._schedule_lock = threading.RLock()
    from reproduction_group import ReproductionGroupRegistry
    world._reproduction_group_registry = ReproductionGroupRegistry(world)
    encounter._transactional_mode = None
    encounter._active_fatigue_frame = None
    encounter._boundary_context = None
    encounter._advancing = encounter._running = encounter._dispatching = False
    if '_atomic_interval_history' not in encounter.__dict__:
        encounter._atomic_interval_history = []
    book = encounter._choice_book
    _need(type(book) is ChoiceBook and book.encounter is encounter,
          'native ChoiceBook owner is inconsistent')
    book.lock = world._schedule_lock
    book._drafts = {}; book._closed_drafts = set(); book._tokens = {}
    # Accepted declarations contain process-local class/object identity data.
    for accepted in book._choices.values():
        _need(type(accepted) is _Accepted, 'unknown accepted Choice record')
        signatures = tuple((member.key, declaration(member.action)) for member in accepted.members)
        object.__setattr__(accepted, 'signatures', signatures)
    for action_id, row in tuple(book._registered.items()):
        choice_id, packet, _signature = row
        action = world.get_event_by_id(action_id)
        book._registered[action_id] = (choice_id, packet, declaration(action))

    from interval_staging import AuthorityReference
    for ref, tag, _content in nodes:
        if tag == 'interval_staging.AuthorityReference':
            reference = cache[ref]
            if reference.role == 'event':
                target = world.get_event_by_id(reference.key)
            elif reference.role == 'accepted_packet':
                registered = book._registered.get(reference.key)
                target = None if registered is None else registered[1]
            else:
                target = None
            _need(target is not None, 'native committed fence reference cannot be rebound')
            object.__setattr__(reference, 'identity', id(target))

    # Native inventory intentionally excludes pointer anchors. Recreate them
    # from the restored objects, then verify the whole history with native inspection.
    entities = world.object_registry.object_instances
    history = encounter.__dict__.get('_atomic_interval_history', [])
    for receipt in history:
        meta = receipt.inspection
        _need(type(meta) is CommittedBoundaryRecord,
              'unsupported Arena committed inspection record')
        targets = {}
        for entity_id in meta.entities:
            entity = entities.get(entity_id)
            _need(entity is not None, 'committed Target owner is not registered')
            storage = entity.__dict__.get('_atomic_target_history')
            record = next((row for row in storage if row.encounter_id == encounter.id
                           and row.boundary == receipt.boundary), None)
            _need(record is not None, 'committed Target history is missing')
            targets[entity_id] = (id(entity), id(entity.current), id(entity.spatial_state),
                                  id(storage), id(record), fingerprint(record))
        actions = {action_id: id(world.get_event_by_id(action_id))
                   for action_id in meta.actions}
        object.__setattr__(meta, 'target_anchors', MappingProxyType(targets))
        object.__setattr__(meta, 'action_anchors', MappingProxyType(actions))

    rng_data = sections['rng']
    rng_owner = RNGCursor(_decode_rng(rng_data[2]))
    # Re-issue exact receipts only under this restoration owner, and require
    # the complete native inspection gate before exposing the graph.
    from atomic_publication import _register_arena_restored_receipts
    _register_arena_restored_receipts(encounter, _ARENA_RESTORE_AUTHORITY)
    pristine = (not encounter.initiated and encounter.time == encounter.start_time
        and not history and not encounter.pending_action_list
        and not encounter.finished_action_list and not encounter.cancelled_action_list
        and not book._choices and encounter.arena_activation is None
        and encounter.arena_movement_activation is None)
    try:
        if not pristine:
            _bind_restored_arena_progression(encounter, rng_owner, _ARENA_RESTORE_AUTHORITY)
        if history:
            inspect_encounter(encounter)
    except Exception:
        _unbind_restored_arena_progression(encounter, _ARENA_RESTORE_AUTHORITY)
        from atomic_publication import _unregister_arena_restored_receipts
        _unregister_arena_restored_receipts(encounter, _ARENA_RESTORE_AUTHORITY)
        raise
    return world, encounter, rng_owner


def _decode_rng(value):
    if type(value) is tuple and value and value[0] == 'tuple':
        return tuple(_decode_rng(row) for row in value[1])
    if type(value) is tuple and value[0] == 'integer': return int(value[1])
    if type(value) is tuple and value[0] == 'binary64': return float.fromhex(value[1])
    if type(value) is tuple and value[0] == 'null': return None
    raise ArenaNativeSnapshotRejected('unsupported private RNG state')


from atomic_publication import _ARENA_RESTORED_RECEIPT_AUTHORITY as _ARENA_RESTORE_AUTHORITY
_OMIT = object()
