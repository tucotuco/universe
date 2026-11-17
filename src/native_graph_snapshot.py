"""Versioned, address-free object-graph snapshots for native persistence.

The Arena schema remains deliberately scoped to generated Arena. Its separate
native schema carries the closed native inventory and rebinds process-local
locks, Choice signatures, Target/action anchors, observer recipients, reality
validators, RNG providers, receipt issuance, and progression ownership. No
Action or committed boundary is evaluated during restore.
"""
from __future__ import annotations

import hashlib
import json
import math
import threading
from types import MappingProxyType

SCHEMA = 'universe.generated-arena-native-state/5'
NATIVE_SCHEMA = 'universe.native-encounter-graph/2'
_LEGACY_NATIVE_SCHEMA_V1 = 'universe.native-encounter-graph/1'
_LEGACY_SCHEMAS = ('universe.generated-arena-native-state/4',
                   'universe.generated-arena-native-state/3')
_COMPACT_INVENTORY = 'universe.generated-arena-compact-inventory/1'
_FIELDS = frozenset(('schema', 'compatibility', 'inventory', 'sha256'))
MAX_BYTES = 64 * 1024 * 1024

# Exact implementation/rule/runtime fingerprint from the last path-identity
# native snapshot format. Only this one legacy producer is migrated; future
# unknown fingerprints remain fail-closed.
_LEGACY_COMPATIBILITY = (
    'compatibility-draft', 'universe.checkpoint-inventory-draft/1',
    ('implementation-source', '7f0fc28b8e1d1599c5340a81208f06d70c2ac883f3d3cc1071ea03c4ce0b194f'),
    ('rule-kernel-source', 'bb6cfd2f532748094488f220397f9ad4f7f277af787dcf551ec5de83443ec8c1'),
    ('authoritative-decisions', '65539e8eef0e4a56601f0811ca2c1d262c696fbc7372d17335510f73e749ee44'),
    ('python-runtime', 'cpython', (3, 14, 3, 'final', 0)),
    ('numeric', 'IEEE754-binary64-hex'),
    ('python-native-rng', 'MT19937-state-v3'),
    ('restore-adapters', 'not-implemented'),
)
_LEGACY_V4_COMPATIBILITY = (
    'compatibility-draft', 'universe.checkpoint-inventory-draft/1',
    ('implementation-source', '0703a58dfb83b19878fd9eeac219458071e854a5bfb1a94b1d40d7e899fc06cd'),
    ('rule-kernel-source', 'f2a68e71424fb3642bdd609701718082f34959e795b104bec817a1099ecc6685'),
    ('authoritative-decisions', '65539e8eef0e4a56601f0811ca2c1d262c696fbc7372d17335510f73e749ee44'),
    ('python-runtime', 'cpython', (3, 14, 3, 'final', 0)),
    ('numeric', 'IEEE754-binary64-hex'),
    ('python-native-rng', 'MT19937-state-v3'),
    ('restore-adapters', 'not-implemented'),
)
_LEGACY_V5_COMPATIBILITY = (
    'compatibility-draft', 'universe.checkpoint-inventory-draft/1',
    ('implementation-source', '4fa06efaeaa44fff5a929d5220c24a517603adc0df578ea260de09df0a3a0982'),
    ('rule-kernel-source', '6133094b36bdb6e5fdd6e9d3890046b93fe6519ac7abbc931d26918c7b5fdb91'),
    ('authoritative-decisions', '65539e8eef0e4a56601f0811ca2c1d262c696fbc7372d17335510f73e749ee44'),
    ('python-runtime', 'cpython', (3, 14, 3, 'final', 0)),
    ('numeric', 'IEEE754-binary64-hex'),
    ('python-native-rng', 'MT19937-state-v3'),
    ('restore-adapters', 'not-implemented'),
)
# Exact source fingerprint of portable Save /11 emitted by commit 1deb61d.
# The next archive schema may migrate this one validated graph while all new
# Saves bind to the current implementation and rule source.
_LEGACY_V6_COMPATIBILITY = (
    'compatibility-draft', 'universe.checkpoint-inventory-draft/1',
    ('implementation-source', '4519f498014ce1191665af22d5b9d8f4f9e5e0114d34165506b95ac4cde0401a'),
    ('rule-kernel-source', '6133094b36bdb6e5fdd6e9d3890046b93fe6519ac7abbc931d26918c7b5fdb91'),
    ('authoritative-decisions', '65539e8eef0e4a56601f0811ca2c1d262c696fbc7372d17335510f73e749ee44'),
    ('python-runtime', 'cpython', (3, 14, 3, 'final', 0)),
    ('numeric', 'IEEE754-binary64-hex'),
    ('python-native-rng', 'MT19937-state-v3'),
    ('restore-adapters', 'not-implemented'),
)
# Exact source fingerprint immediately before the native full-closure adapter
# was introduced. The Arena /12 reader migrates this precise graph in place;
# later unknown fingerprints remain rejected.
_LEGACY_NATIVE_BRIDGE_COMPATIBILITY = (
    'compatibility-draft', 'universe.checkpoint-inventory-draft/1',
    ('implementation-source', '68afd969c1dec66b06bcc1dad4fbd8dc0249a24249c35bfbf4a46f6125ab81f6'),
    ('rule-kernel-source', '2c478db52ab6343596983869ace4ead0d6ccfb636bed0eddda253937e934574f'),
    ('authoritative-decisions', '65539e8eef0e4a56601f0811ca2c1d262c696fbc7372d17335510f73e749ee44'),
    ('python-runtime', 'cpython', (3, 14, 3, 'final', 0)),
    ('numeric', 'IEEE754-binary64-hex'),
    ('python-native-rng', 'MT19937-state-v3'),
    ('restore-adapters', 'not-implemented'),
)
# Exact inventory fingerprint emitted by the last un-compacted native graph
# writer. Schema /1 remains a strict read path and migrates only this reviewed
# source version (plus the older explicitly enumerated compatibility tuples).
_LEGACY_NATIVE_GRAPH_V1_COMPATIBILITY = (
    'compatibility-draft', 'universe.checkpoint-inventory-draft/1',
    ('implementation-source', '69edc9bbca2b98a5e5a0ee0b95a9e3a495efade103c6843765f9ac8a519fa4ae'),
    ('rule-kernel-source', '661905a7826fc109055595c63778cec56d4502efc942116e3b23fb71ea025f1c'),
    ('authoritative-decisions', '65539e8eef0e4a56601f0811ca2c1d262c696fbc7372d17335510f73e749ee44'),
    ('python-runtime', 'cpython', (3, 14, 3, 'final', 0)),
    ('numeric', 'IEEE754-binary64-hex'),
    ('python-native-rng', 'MT19937-state-v3'),
    ('restore-adapters', 'not-implemented'),
)
# Exact fingerprint of native graph /1 as written by repository HEAD
# immediately before graph /2 compaction began. `native_history.py` had
# changed since the earlier /1 writer above, so both emitted contracts need
# explicit strict migration entries.
_LEGACY_NATIVE_GRAPH_V1_BFC_COMPATIBILITY = (
    'compatibility-draft', 'universe.checkpoint-inventory-draft/1',
    ('implementation-source', 'f9c7b2771e9a5b31be89170755f2adca077ca2fd4d8c04fd5081e0b50c813ceb'),
    ('rule-kernel-source', '661905a7826fc109055595c63778cec56d4502efc942116e3b23fb71ea025f1c'),
    ('authoritative-decisions', '65539e8eef0e4a56601f0811ca2c1d262c696fbc7372d17335510f73e749ee44'),
    ('python-runtime', 'cpython', (3, 14, 3, 'final', 0)),
    ('numeric', 'IEEE754-binary64-hex'),
    ('python-native-rng', 'MT19937-state-v3'),
    ('restore-adapters', 'not-implemented'),
)
_LEGACY_NATIVE_GRAPH_V2_TARGET_COMPATIBILITY = (
    'compatibility-draft', 'universe.checkpoint-inventory-draft/1',
    ('implementation-source', 'af95b65227b2fb59a24f157d6f5ae8882e4f6d4586bec58470b5e3f5e3651468'),
    ('rule-kernel-source', '661905a7826fc109055595c63778cec56d4502efc942116e3b23fb71ea025f1c'),
    ('authoritative-decisions', '65539e8eef0e4a56601f0811ca2c1d262c696fbc7372d17335510f73e749ee44'),
    ('python-runtime', 'cpython', (3, 14, 3, 'final', 0)),
    ('numeric', 'IEEE754-binary64-hex'),
    ('python-native-rng', 'MT19937-state-v3'),
    ('restore-adapters', 'not-implemented'),
)
_LEGACY_NATIVE_GRAPH_V2_ENTITY_COMPATIBILITY = (
    'compatibility-draft', 'universe.checkpoint-inventory-draft/1',
    ('implementation-source', '2b3896b5c66983e09bff03696ce7c82e4d93786128a1056ae610d08e7220e071'),
    ('rule-kernel-source', '661905a7826fc109055595c63778cec56d4502efc942116e3b23fb71ea025f1c'),
    ('authoritative-decisions', '65539e8eef0e4a56601f0811ca2c1d262c696fbc7372d17335510f73e749ee44'),
    ('python-runtime', 'cpython', (3, 14, 3, 'final', 0)),
    ('numeric', 'IEEE754-binary64-hex'),
    ('python-native-rng', 'MT19937-state-v3'),
    ('restore-adapters', 'not-implemented'),
)
_LEGACY_NATIVE_GRAPH_V2_RECEIPT_FACTS_COMPATIBILITY = (
    'compatibility-draft', 'universe.checkpoint-inventory-draft/1',
    ('implementation-source', '93ced5a707ba326e7aa56b3e07221bf03102a3ac66ea447dfaf690fb4cef642b'),
    ('rule-kernel-source', '661905a7826fc109055595c63778cec56d4502efc942116e3b23fb71ea025f1c'),
    ('authoritative-decisions', '65539e8eef0e4a56601f0811ca2c1d262c696fbc7372d17335510f73e749ee44'),
    ('python-runtime', 'cpython', (3, 14, 3, 'final', 0)),
    ('numeric', 'IEEE754-binary64-hex'),
    ('python-native-rng', 'MT19937-state-v3'),
    ('restore-adapters', 'not-implemented'),
)
_LEGACY_NATIVE_GRAPH_V2_COMPATIBILITIES = (
    _LEGACY_NATIVE_GRAPH_V2_TARGET_COMPATIBILITY,
    _LEGACY_NATIVE_GRAPH_V2_ENTITY_COMPATIBILITY,
    _LEGACY_NATIVE_GRAPH_V2_RECEIPT_FACTS_COMPATIBILITY,
)
_LEGACY_NATIVE_GRAPH_V1_COMPATIBILITIES = (
    _LEGACY_NATIVE_GRAPH_V1_COMPATIBILITY,
    _LEGACY_NATIVE_GRAPH_V1_BFC_COMPATIBILITY,
)

# Exact native type closure exercised by the current Arena UI: generated
# Beings, typed ground/carry Objects, Run, Pick up, Draw, Dagger strikes, their Choice and
# committed inspection records, and observer-owned Arena evidence.
_ARENA_TAGS = frozenset({
    'universe.Universe','library.Library','event.Event','action.Action','encounter.Encounter',
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
    'spatial.state.SpatialState','spatial.geometry.Sphere','spatial.geometry.AxisAlignedBox',
    'spatial.occlusion.VisualOcclusion',
    'arena_perception.ArenaPerceptionEvidence',
    'arena_perception.ArenaPerceptionLedger','activities.RunAction','activities.SpotAction',
    'activities.ThrowAction','throwing.ProjectileFlight','throwing.ProjectileBoundaryState',
    'activities.PickUpAction','activities.ReadyWeaponAction','activities.ShieldEquipmentAction','activities.ReadyPreparationAction','activities.DelayAction','melee_combat.MeleeStrike',
    'melee_combat.MeleeResult','melee_defense.MeleeDefense',
    'atomic_publication.PublishedInterval','atomic_publication.TargetIntervalRecord',
    'encounter_inspection.CommittedBoundaryRecord','encounter_inspection.EntityInspection',
    'encounter_inspection.DisarmLandingReceipt',
    'action_settlement.TargetCandidate','action_evaluation.ActionProposal',
    'action_evaluation.ActionView','action_evaluation.EffectIdentity',
    'action_evaluation.AwarenessEffect',
    'action_evaluation.IdentifiedEffect','action_evaluation.DamageEffect',
    'action_evaluation.ProtectionEffect','action_evaluation.PickupEffect',
    'action_evaluation.DisarmLandingPendingEffect',
    'action_evaluation.StunEffect','action_evaluation.SubdualEffect',
    'action_evaluation.ReadyWeaponEffect','action_evaluation.ShieldEquipmentEffect','action_evaluation.ReadyPreparationEffect','action_evaluation.ReadyConsumptionEffect','action_evaluation.DelayDefenseEffect','action_evaluation.DropObjectEffect','action_evaluation.DisarmTakeEffect','action_evaluation.GrappleStateEffect','action_evaluation.PositionEffect','action_evaluation.ObjectGripEffect','action_evaluation.PracticeEffect',
    'observer_proposals.ActionOutcomeEffect','observer_proposals.LifecycleEffect',
    'observer_proposals.ReservationReleaseEffect',
    'observer_proposals.ObserverProjection','frozen_practice.PracticeProjection',
    'action_evaluation.DefenseEffect','action_evaluation.ProjectileReleaseEffect',
    'frozen_practice.CandidatePracticeUse','frozen_practice.CandidateSkillTransition',
    'experience.SkillUse','experience.BatchSkillUse','experience.SkillExercise',
    'experience.ActionResolution','interval_staging.AuthorityReference',
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


def _validate_arena_field_schema(inventory, *, require_required=True,
                                allow_rebuilt_fields=False, native=False):
    """Admit only fields in the reviewed native type vocabulary."""
    from checkpoint_fields import FIELD_ADAPTERS
    _need(type(inventory) is tuple and len(inventory) == 2,
          'native Arena field-schema inventory is malformed')
    body = inventory[1]
    _need(type(body) is tuple and body and body[0] == 'checkpoint-inventory',
          'native Arena field-schema body is malformed')
    node_sections = [row for row in body[1:] if type(row) is tuple
                     and row and row[0] == 'nodes']
    _need(len(node_sections) == 1 and type(node_sections[0][1]) is tuple,
          'native Arena field-schema node table is malformed')
    containers = {'ordered-map', 'list', 'tuple', 'set', 'frozenset'}
    for row in node_sections[0][1]:
        _need(type(row) is tuple and len(row) == 3,
              'native Arena field-schema node is malformed')
        _ref, tag, content = row
        _need(type(tag) is str and type(content) is tuple,
              'native Arena field-schema node contents are malformed')
        if tag in containers:
            continue
        adapter = FIELD_ADAPTERS.get(tag)
        _need(type(adapter) is dict and 'allowed' in adapter and 'required' in adapter,
              f'native Arena type has no reviewed field adapter: {tag}')
        _need(all(type(pair) is tuple and len(pair) == 2
                  and type(pair[0]) is str for pair in content),
              f'native Arena field table is malformed: {tag}')
        names = tuple(pair[0] for pair in content)
        _need(len(names) == len(set(names)),
              f'native Arena field table has duplicate names: {tag}')
        fields = set(names)
        allowed = set(adapter['allowed'])
        required = set(adapter['required'])
        if allow_rebuilt_fields and not native:
            from checkpoint_fields import ARENA_REBUILT_FIELDS
            required -= {name for owner, name in ARENA_REBUILT_FIELDS if owner == tag}
        _need(fields <= allowed,
              f'native Arena node has unreviewed fields: {tag}: '
              + ', '.join(sorted(fields - allowed)))
        if require_required:
            _need(required <= fields,
                  f'native Arena node is missing required fields: {tag}: '
                  + ', '.join(sorted(required - fields)))


def _migrate_legacy_v5_inventory(inventory):
    """Migrate the last accepted /10 graph fingerprint without re-simulation."""
    from checkpoint_inventory import _compatibility
    _need(type(inventory) is tuple and len(inventory) == 2
          and inventory[0] == _LEGACY_V5_COMPATIBILITY,
          'legacy v5 native inventory compatibility mismatch')
    _validate_inventory(inventory, expected_compatibility=_LEGACY_V5_COMPATIBILITY)
    _validate_arena_field_schema(inventory, require_required=False)
    migrated = (_compatibility(), inventory[1])
    _validate_arena_field_schema(migrated)
    _validate_inventory(migrated)
    return migrated


def _migrate_legacy_v6_inventory(inventory):
    """Migrate the exact pre-Action-root /11 inventory without re-simulation."""
    from checkpoint_inventory import _compatibility
    _need(type(inventory) is tuple and len(inventory) == 2
          and inventory[0] == _LEGACY_V6_COMPATIBILITY,
          'legacy /11 native inventory compatibility mismatch')
    _validate_inventory(inventory, expected_compatibility=_LEGACY_V6_COMPATIBILITY)
    _validate_arena_field_schema(inventory, require_required=False)
    migrated = (_compatibility(), inventory[1])
    # The /11 segmented adapter had already proved and omitted its exact
    # rebuilt runtime markers, so current-schema migration validates field
    # vocabulary while allowing those reviewed omissions for restore.
    _validate_arena_field_schema(migrated, require_required=False)
    _validate_inventory(migrated)
    return migrated


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
    _validate_arena_field_schema(candidate.envelope)
    return candidate.envelope


def encode(inventory, *, native=False):
    from checkpoint_inventory import _compatibility
    _validate_arena_field_schema(inventory, native=native)
    payload = {'schema': NATIVE_SCHEMA if native else SCHEMA,
               'compatibility': _compatibility(),
               'inventory': _compact_inventory(inventory, native=native)}
    body = _canonical(payload)
    wire = _canonical(dict(payload, sha256=hashlib.sha256(body).hexdigest()))
    # Refuse to write a checkpoint that the unchanged production admission
    # limit would reject. The count is over the lossless compact wire form.
    _tree(json.loads(wire))
    _need(len(wire) <= MAX_BYTES, 'native Arena state exceeds the file limit')
    return wire


def decode(wire, *, native=False):
    from checkpoint_inventory import _compatibility
    _need(type(wire) is bytes and 0 < len(wire) <= MAX_BYTES,
          'native Arena state is empty or exceeds the file limit')
    try:
        data = json.loads(wire.decode('ascii'), object_pairs_hook=_unique,
            parse_constant=lambda _x: (_ for _ in ()).throw(ValueError('nonfinite number')))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ArenaNativeSnapshotRejected(f'native Arena state JSON is invalid: {exc}') from exc
    _tree(data)
    schemas = ((NATIVE_SCHEMA, _LEGACY_NATIVE_SCHEMA_V1) if native
               else (SCHEMA, *_LEGACY_SCHEMAS))
    _need(type(data) is dict and set(data) == _FIELDS
          and data['schema'] in schemas,
          'native Arena state has an unknown schema or field set')
    payload = {key: data[key] for key in data if key != 'sha256'}
    _need(type(data['sha256']) is str and hashlib.sha256(_canonical(payload)).hexdigest() == data['sha256'],
          'native Arena state digest does not match')
    _need(_canonical(data) == wire, 'native Arena state is not canonical')
    saved_compatibility = _tuples(data['compatibility'])
    legacy_schema = data['schema'] if data['schema'] in _LEGACY_SCHEMAS else None
    expected_compatibility = (_LEGACY_COMPATIBILITY
        if legacy_schema == 'universe.generated-arena-native-state/3' else
        _LEGACY_V4_COMPATIBILITY if legacy_schema else
        saved_compatibility
        if native and data['schema'] == _LEGACY_NATIVE_SCHEMA_V1
            and saved_compatibility in _LEGACY_NATIVE_GRAPH_V1_COMPATIBILITIES else
        saved_compatibility
        if native and data['schema'] == NATIVE_SCHEMA
            and saved_compatibility in _LEGACY_NATIVE_GRAPH_V2_COMPATIBILITIES else
        _LEGACY_V5_COMPATIBILITY if saved_compatibility == _LEGACY_V5_COMPATIBILITY
        else _LEGACY_NATIVE_BRIDGE_COMPATIBILITY
        if saved_compatibility == _LEGACY_NATIVE_BRIDGE_COMPATIBILITY
        else _compatibility())
    _need(saved_compatibility == expected_compatibility,
          'saved native Arena implementation/rules differ from this runtime')
    try:
        inventory = _tuples(data['inventory'])
    except RecursionError as exc:
        raise ArenaNativeSnapshotRejected('native Arena state nesting exceeds limits') from exc
    if native:
        inventory = _expand_compact_inventory(inventory, native=True)
        _validate_inventory(inventory,
                            expected_compatibility=saved_compatibility,
                            native=True)
        _validate_arena_field_schema(inventory, native=True)
        if saved_compatibility != _compatibility():
            inventory = (_compatibility(), inventory[1])
    elif legacy_schema == 'universe.generated-arena-native-state/3':
        _need(type(inventory) is tuple and len(inventory) == 2
              and inventory[0] == _LEGACY_COMPATIBILITY,
              'legacy native Arena inventory compatibility mismatch')
        _validate_inventory(inventory, allow_legacy_paths=True,
                            expected_compatibility=_LEGACY_COMPATIBILITY)
        _validate_arena_field_schema(inventory, require_required=False)
        inventory = _migrate_path_identities(inventory)
        inventory = (_compatibility(), inventory[1])
    elif legacy_schema == 'universe.generated-arena-native-state/4':
        _need(type(inventory) is tuple and len(inventory) == 2
              and inventory[0] == _LEGACY_V4_COMPATIBILITY,
              'legacy v4 native Arena inventory compatibility mismatch')
        _validate_inventory(inventory,
                            expected_compatibility=_LEGACY_V4_COMPATIBILITY)
        _validate_arena_field_schema(inventory, require_required=False)
        inventory = (_compatibility(), inventory[1])
    elif saved_compatibility == _LEGACY_V5_COMPATIBILITY:
        inventory = _expand_compact_inventory(inventory)
        inventory = _migrate_legacy_v5_inventory(inventory)
    elif saved_compatibility in (_LEGACY_V5_COMPATIBILITY,
                                 _LEGACY_NATIVE_BRIDGE_COMPATIBILITY):
        inventory = _expand_compact_inventory(inventory)
        if saved_compatibility == _LEGACY_V5_COMPATIBILITY:
            _migrate_legacy_v5_inventory(inventory)
        else:
            from checkpoint_inventory import _compatibility
            _validate_inventory(inventory,
                expected_compatibility=_LEGACY_NATIVE_BRIDGE_COMPATIBILITY)
            _validate_arena_field_schema(inventory)
            inventory = (_compatibility(), inventory[1])
    else:
        inventory = _expand_compact_inventory(inventory)
        _validate_arena_field_schema(inventory)
    _validate_inventory(inventory, native=native)
    return inventory


def _compact_inventory(inventory, *, native=False):
    """Encode repeated scalar strings and pair tables losslessly.

    Inspection history repeats a small vocabulary as typed strings in many
    map entries. A negative integer indexes the sorted per-checkpoint string
    table and replaces the three-node ('string', value) tuple. Native integer
    values already have an explicit ('integer', decimal) tag. Field and map
    pairs are stored flat and reconstructed only after strict tree admission.
    """
    _need(type(inventory) is tuple and len(inventory) == 2,
          'native inventory envelope is malformed')
    compatibility, body = inventory
    allowed_sections = ({'root', 'nodes', 'rng', 'readiness',
                         'native-adapters', 'host-bindings'} if native else
                        {'root', 'nodes', 'rng', 'readiness'})
    _need(type(body) is tuple and body[0] == 'checkpoint-inventory'
          and {row[0] for row in body[1:] if type(row) is tuple and row}
              == allowed_sections,
          'native inventory body is outside Arena schema')
    sections = []
    symbols = set()
    containers = {'ordered-map', 'list', 'tuple', 'set', 'frozenset'}
    for section in body[1:]:
        _need(type(section) is tuple and section,
              'native inventory section is malformed')
        if section[0] != 'nodes':
            sections.append(section)
            continue
        _need(len(section) == 2 and type(section[1]) is tuple,
              'native inventory node table is malformed')
        rows = []
        for row in section[1]:
            _need(type(row) is tuple and len(row) == 3
                  and type(row[2]) is tuple,
                  'native graph node is malformed')
            ref, tag, content = row
            if tag == 'ordered-map' or tag not in containers:
                flat = []
                for pair in content:
                    _need(type(pair) is tuple and len(pair) == 2,
                          'native ordered field/key pair is malformed')
                    flat.extend(pair)
                content = tuple(flat)
            rows.append((ref, tag, content))
        sections.append(('nodes', tuple(rows)))

    def collect(value):
        if type(value) is tuple:
            if (len(value) == 2 and value[0] == 'string'
                    and type(value[1]) is str):
                symbols.add(value[1])
                return
            for item in value:
                collect(item)

    compact_body = (body[0], *sections)
    collect(compact_body)
    symbol_table = tuple(sorted(symbols))
    symbol_ids = {value: index for index, value in enumerate(symbol_table)}

    def compact(value):
        if type(value) is tuple:
            if (len(value) == 2 and value[0] == 'string'
                    and type(value[1]) is str):
                return -symbol_ids[value[1]] - 1
            return tuple(compact(item) for item in value)
        return value

    return (compatibility,
            (_COMPACT_INVENTORY, symbol_table, compact(compact_body)))


def _expand_compact_inventory(inventory, *, native=False):
    _need(type(inventory) is tuple and len(inventory) == 2,
          'compact native inventory envelope is malformed')
    compatibility, compact = inventory
    _need(type(compact) is tuple and len(compact) == 3
          and compact[0] == _COMPACT_INVENTORY
          and type(compact[1]) is tuple and type(compact[2]) is tuple,
          'compact native inventory marker/table is malformed')
    symbols, body = compact[1], compact[2]
    _need(len(symbols) <= 250000 and all(type(value) is str for value in symbols)
          and symbols == tuple(sorted(set(symbols))),
          'compact native inventory symbol table is invalid')

    def expand(value):
        if type(value) is int and value < 0:
            index = -value - 1
            _need(index < len(symbols),
                  'compact native inventory has a dangling symbol')
            return ('string', symbols[index])
        if type(value) is tuple:
            return tuple(expand(item) for item in value)
        return value

    body = expand(body)
    allowed_sections = ({'root', 'nodes', 'rng', 'readiness',
                         'native-adapters', 'host-bindings'} if native else
                        {'root', 'nodes', 'rng', 'readiness'})
    _need(type(body) is tuple and body[0] == 'checkpoint-inventory'
          and {row[0] for row in body[1:] if type(row) is tuple and row}
              == allowed_sections,
          'compact native inventory body is malformed')
    containers = {'ordered-map', 'list', 'tuple', 'set', 'frozenset'}
    sections = []
    for section in body[1:]:
        _need(type(section) is tuple and section,
              'compact native inventory section is malformed')
        if section[0] != 'nodes':
            sections.append(section)
            continue
        _need(len(section) == 2 and type(section[1]) is tuple,
              'compact native inventory node table is malformed')
        rows = []
        for row in section[1]:
            _need(type(row) is tuple and len(row) == 3
                  and type(row[2]) is tuple,
                  'compact native graph node is malformed')
            ref, tag, content = row
            if tag == 'ordered-map' or tag not in containers:
                _need(len(content) % 2 == 0,
                      'compact native field/key sequence has an odd length')
                content = tuple((content[index], content[index + 1])
                                for index in range(0, len(content), 2))
            rows.append((ref, tag, content))
        sections.append(('nodes', tuple(rows)))
    return compatibility, (body[0], *sections)


def _unique(rows):
    result = {}
    for key, value in rows:
        if key in result:
            raise ValueError('duplicate JSON field')
        result[key] = value
    return result


def _validate_inventory(envelope, *, allow_legacy_paths=False,
                        expected_compatibility=None, native=False):
    from checkpoint_inventory import _TYPES
    _need(type(envelope) is tuple and len(envelope) == 2,
          'native inventory envelope is malformed')
    compatibility, body = envelope
    from checkpoint_inventory import _compatibility
    expected_compatibility = _compatibility() if expected_compatibility is None else expected_compatibility
    _need(compatibility == expected_compatibility, 'native inventory compatibility mismatch')
    expected_sections = ({'root', 'nodes', 'rng', 'readiness',
                          'native-adapters', 'host-bindings'} if native else
                         {'root', 'nodes', 'rng', 'readiness'})
    _need(type(body) is tuple and body[0] == 'checkpoint-inventory',
          'native inventory body is outside Arena schema')
    sections = {row[0]: row[1:] for row in body[1:] if type(row) is tuple and row}
    _need(set(sections) == expected_sections,
          'native inventory sections are incomplete or unknown')
    if native:
        _need(sections['native-adapters'] in (
                  ('native-closure-recipes/1',),
                  ('native-closure-recipes/1', 'target-candidate-history/1'),
                  ('native-closure-recipes/1', 'entity-context-history/1'),
                  ('native-closure-recipes/1', 'target-candidate-history/1',
                   'entity-context-history/1'),
                  ('native-closure-recipes/1', 'entity-context-history/1',
                   'committed-receipt-facts/1'),
                  ('native-closure-recipes/1', 'target-candidate-history/1',
                   'entity-context-history/1', 'committed-receipt-facts/1'),
                  ('native-closure-recipes/1', 'entity-context-history/1',
                   'committed-receipt-facts/1', 'published-interval-facts/1'),
                  ('native-closure-recipes/1', 'target-candidate-history/1',
                   'entity-context-history/1', 'committed-receipt-facts/1',
                   'published-interval-facts/1'),
                  ('native-closure-recipes/1', 'entity-context-history/1',
                   'committed-receipt-facts/1', 'disarm-landing-facts/1'),
                  ('native-closure-recipes/1', 'target-candidate-history/1',
                   'entity-context-history/1', 'committed-receipt-facts/1',
                   'disarm-landing-facts/1'),
                  ('native-closure-recipes/1', 'entity-context-history/1',
                   'committed-receipt-facts/1', 'published-interval-facts/1',
                   'disarm-landing-facts/1'),
                  ('native-closure-recipes/1', 'target-candidate-history/1',
                   'entity-context-history/1', 'committed-receipt-facts/1',
                   'published-interval-facts/1', 'disarm-landing-facts/1')),
              'native adapter recipe version differs')
        _validate_host_binding_descriptors(sections['host-bindings'])
    _need(sections['readiness'] == (False, False, False), 'unsupported inventory readiness claim')
    _need(sections['rng'][:2] == ('caller_cursor', 'exclusive_encounter'),
          'native save requires its exclusive caller-owned RNG cursor')
    nodes_row = sections['nodes']
    _need(len(nodes_row) == 1 and type(nodes_row[0]) is tuple,
          'native inventory node table is malformed')
    nodes = nodes_row[0]
    _need(0 < len(nodes) <= 250000, 'native inventory node count is out of bounds')
    refs = set()
    exact_types = {f'{cls.__module__}.{cls.__name__}' for cls in _TYPES}
    if native:
        from checkpoint_fields import FIELD_ADAPTERS
        allowed_tags = exact_types & set(FIELD_ADAPTERS)
        allowed_tags.add('conditional_attributes.ConditionalAttributes')
    else:
        allowed_tags = exact_types & _ARENA_TAGS
    allowed_tags |= {'ordered-map', 'list', 'tuple', 'set', 'frozenset'}
    for row in nodes:
        _need(type(row) is tuple and len(row) == 3 and type(row[0]) is tuple
              and row[1] in allowed_tags and row[0] not in refs,
              'native graph contains a duplicate identity or unsupported type')
        _need(_valid_reference_identity(row[0], allow_legacy_paths=allow_legacy_paths),
              'native graph contains a malformed identity')
        refs.add(row[0])
    _need(sections['root'] == (('reference', ('universe', _root_id(nodes, 'universe.Universe'))),),
          'native inventory root is not its unique Universe')
    _need(any(row[1] == 'encounter.Encounter' for row in nodes)
          and any(row[1] == 'being.BeingInstance' for row in nodes),
          'native Arena Encounter/Being nodes are missing')
    # Resolve every logical reference and exact native class before allocating.
    _walk_refs(envelope, refs)


def _validate_host_binding_descriptors(section):
    _need(type(section) is tuple and len(section) == 1
          and type(section[0]) is tuple,
          'native host bindings are malformed')
    seen = set()
    roles = {'in_world_belief_ledger', 'in_world_received_accounts',
             'observer_location_evidence', 'observer_object_evidence'}
    for row in section[0]:
        _need(type(row) is tuple and len(row) == 5,
              'native host binding row is malformed')
        namespace, name, role, observers, reference = row
        _need(type(namespace) is str and namespace.strip()
              and type(name) is str and name.strip()
              and (namespace, name) not in seen,
              'native host binding identity is empty or duplicated')
        _need(role in roles and type(observers) is tuple and observers
              and all(type(owner) is str and owner for owner in observers)
              and len(observers) == len(set(observers)),
              'native host binding role/observers are malformed')
        _need(type(reference) is tuple and len(reference) == 2
              and reference[0] == 'reference'
              and type(reference[1]) is tuple
              and reference[1][0] == 'host-recipient',
              'native host binding has no stable graph reference')
        seen.add((namespace, name))


def _valid_reference_identity(ref, *, allow_legacy_paths=False):
    if not ref or type(ref[0]) is not str:
        return False
    kind = ref[0]
    if kind == 'owned-node':
        return (len(ref) == 2 and type(ref[1]) is str and len(ref[1]) == 64
                and all(char in '0123456789abcdef' for char in ref[1]))
    if kind == 'owned-path':
        return (allow_legacy_paths and len(ref) >= 2
                and all(type(part) is str for part in ref[1:]))
    if kind in ('universe', 'encounter', 'object', 'event'):
        return len(ref) == 2 and type(ref[1]) is str and bool(ref[1])
    if kind == 'choice':
        return (len(ref) == 3 and all(type(part) is str and part for part in ref[1:]))
    if kind == 'host-recipient':
        return (len(ref) == 4 and all(type(part) is str and part
                                      for part in ref[1:]))
    return False


def _migrate_path_identities(envelope):
    """Translate exact v3 traversal-path identities to compact v4 references."""
    from checkpoint_inventory import owned_node_ref

    body=envelope[1]
    sections={row[0]:row[1:] for row in body[1:]}
    nodes=sections['nodes'][0]
    remap={row[0]:owned_node_ref(tuple(row[0][1:]))
           for row in nodes if row[0][0]=='owned-path'}

    def rewrite(value):
        if type(value) is tuple:
            try:
                replacement=remap.get(value)
            except TypeError:
                replacement=None
            if replacement is not None:
                return replacement
            if value and value[0]=='reference' and len(value)==2:
                return ('reference',remap.get(value[1],value[1]))
            return tuple(rewrite(item) for item in value)
        return value

    migrated=rewrite(envelope)
    _need(type(migrated) is tuple and len(migrated)==2,
          'legacy identity migration produced malformed inventory')
    return migrated


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


def restore(envelope, *, native=False, companion_rng_owners=None,
            native_histories=None):
    """Materialize an exact private graph and bind ordinary native progression."""
    from checkpoint_inventory import _TYPES
    from atomic_publication import RNGCursor
    from universe import Universe
    from encounter import Encounter
    from encounter_inspection import CommittedBoundaryRecord, fingerprint, inspect_encounter
    from action_choice import ChoiceBook, _Accepted, declaration
    from transactional_progression import (_bind_restored_arena_progression,
        _unbind_restored_arena_progression)

    if companion_rng_owners is None:
        companion_rng_owners = {}
    _need(type(companion_rng_owners) is dict
          and all(type(key) is str and key for key in companion_rng_owners),
          'native companion RNG owner map is malformed')

    _validate_inventory(envelope, native=native)
    _validate_arena_field_schema(envelope, require_required=True,
                                 allow_rebuilt_fields=True, native=native)
    body = envelope[1]
    sections = {row[0]: row[1:] for row in body[1:]}
    native_adapter_markers = sections.get('native-adapters', ())
    compact_target_history = (native and
        'target-candidate-history/1' in native_adapter_markers)
    compact_entity_context = (native and
        'entity-context-history/1' in native_adapter_markers)
    compact_receipt_facts = (native and
        'committed-receipt-facts/1' in native_adapter_markers)
    compact_publication_facts = (native and
        'published-interval-facts/1' in native_adapter_markers)
    compact_disarm_landings = (native and
        'disarm-landing-facts/1' in native_adapter_markers)
    _need(not compact_receipt_facts or compact_entity_context,
          'compacted native receipt facts require EntityInspection history')
    _need(not compact_publication_facts or compact_receipt_facts,
          'compacted publication facts require committed receipt history')
    _need(not compact_disarm_landings or compact_receipt_facts,
          'compacted Disarm landing facts require committed receipt history')
    history_map_supplied = native_histories is not None
    if native_histories is None:
        native_histories = {}
    _need(type(native_histories) is dict,
          'native history restoration map is malformed')
    nodes = sections['nodes'][0]
    by_ref = {row[0]: row for row in nodes}
    classes = {f'{cls.__module__}.{cls.__name__}': cls for cls in _TYPES}
    cache = {}
    native_recipes = []
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
        if tag == 'native-recipe':
            _need(native and len(value) >= 3
                  and value[1] == 'native-closure-recipes/1',
                  'unrecognized native restoration recipe')
            native_recipes.append(value)
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
    from object import ObjectInstance
    from weapon import WeaponInstance
    from spatial.state import SpatialState
    from spatial.geometry import AxisAlignedBox, Sphere
    from throwing import ProjectileFlight
    from measured_values import is_truncated_measurement
    exact_projectile_spatial_ids = {
        id(obj.spatial_state) for obj in cache.values()
        if type(obj) in (ObjectInstance, WeaponInstance)
        and type(obj.spatial_state) is SpatialState
        and type(obj.__dict__.get('_projectile_flight')) is ProjectileFlight
    }
    for obj in cache.values():
        if isinstance(obj, ObjectDefinition):
            for name in ObjectDefinition._MEASURED_ATTRIBUTES:
                if not is_truncated_measurement(getattr(obj, name, None)):
                    raise ArenaNativeSnapshotRejected(
                        f'native {name} measurement is not canonically truncated')
        if type(obj) is SpatialState and id(obj) not in exact_projectile_spatial_ids:
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
    selected_encounters = [cache[ref] for ref, tag, _ in nodes
                           if tag == 'encounter.Encounter'
                           and type(ref) is tuple and ref
                           and ref[0] == 'encounter']
    _need(len(selected_encounters) == 1,
          'native graph must contain exactly one selected Encounter root')
    encounter = selected_encounters[0]
    _need(type(world) is Universe and type(encounter) is Encounter
          and encounter.universe is world, 'native Arena roots disagree')
    # Recreate process-local synchronization/runtime state omitted by inventory.
    world._schedule_lock = threading.RLock()
    from reproduction_group import ReproductionGroupRegistry
    world._reproduction_group_registry = ReproductionGroupRegistry(world)
    encounters = [value for value in cache.values()
                  if type(value) is Encounter]
    encounter_ids = {saved.id for saved in encounters}
    _need(set(companion_rng_owners) <= encounter_ids,
          'native companion RNG map names an unknown Encounter')
    for saved_encounter in encounters:
        saved_encounter._transactional_mode = None
        saved_encounter._active_fatigue_frame = None
        saved_encounter._boundary_context = None
        saved_encounter._advancing = saved_encounter._running = False
        saved_encounter._dispatching = False
        if '_coordinator_time' not in saved_encounter.__dict__:
            saved_encounter._coordinator_time = saved_encounter.time
        if '_interval_start' not in saved_encounter.__dict__:
            saved_encounter._interval_start = saved_encounter.time
        if '_physiology_registry' not in saved_encounter.__dict__:
            saved_encounter._physiology_registry = None
        if '_atomic_interval_history' not in saved_encounter.__dict__:
            saved_encounter._atomic_interval_history = []
    if native:
        _rehydrate_native_services(cache, nodes, native_recipes,
                                   sections['host-bindings'][0])
    books = world.__dict__.get('_choice_books')
    _need(type(books) is list
          and len(books) == len(encounters)
          and len({id(book) for book in books}) == len(books)
          and {id(book) for book in books}
              == {id(saved._choice_book) for saved in encounters},
          'native Encounter/ChoiceBook registry ownership is inconsistent')
    by_encounter_id = {saved.id: saved for saved in encounters}
    book_by_action = {}
    for saved in encounters:
        book = saved._choice_book
        _need(type(book) is ChoiceBook and book.encounter is saved,
              'native ChoiceBook owner is inconsistent')
        book.lock = world._schedule_lock
        book._drafts = {}; book._closed_drafts = set(); book._tokens = {}
        # Accepted declarations contain process-local class/object identity data.
        for accepted in book._choices.values():
            _need(type(accepted) is _Accepted, 'unknown accepted Choice record')
            signatures = tuple(
                (member.key, member.priority_penalty, declaration(member.action))
                if member.priority_penalty is not None else
                (member.key, declaration(member.action))
                for member in accepted.members)
            object.__setattr__(accepted, 'signatures', signatures)
        for action_id, row in tuple(book._registered.items()):
            _need(action_id not in book_by_action,
                  'native Action is registered to multiple Encounter ChoiceBooks')
            choice_id, packet, _signature = row
            action = world.get_event_by_id(action_id)
            _need(action is not None,
                  'native registered Action is absent from the Universe')
            book._registered[action_id] = (choice_id, packet, declaration(action))
            book_by_action[action_id] = (book, packet)

    from interval_staging import AuthorityReference
    for ref, tag, _content in nodes:
        if tag == 'interval_staging.AuthorityReference':
            reference = cache[ref]
            if reference.role == 'event':
                target = world.get_event_by_id(reference.key)
            elif reference.role == 'accepted_packet':
                registered = book_by_action.get(reference.key)
                target = None if registered is None else registered[1]
            elif reference.role == 'encounter':
                target = by_encounter_id.get(reference.key)
            elif reference.role == 'universe':
                target = world if reference.key == world.id else None
            else:
                target = None
            _need(target is not None, 'native committed fence reference cannot be rebound')
            object.__setattr__(reference, 'identity', id(target))

    if compact_target_history or compact_entity_context:
        if not history_map_supplied:
            _need(all(not saved.__dict__.get('_atomic_interval_history')
                      and saved.time == saved.start_time
                      for saved in encounters),
                  'committed compact native graph requires its fact histories')
            native_histories = {saved.id: None for saved in encounters}
        _need(set(native_histories) == set(by_encounter_id),
              'compacted native graph requires histories for every Encounter')
        import native_history as history_codec
        try:
            if compact_entity_context:
                history_codec.restore_compacted_entity_context(world,
                                                               native_histories)
            if compact_publication_facts:
                history_codec.restore_compacted_publication_facts(world,
                                                                  native_histories)
            if compact_disarm_landings:
                history_codec.restore_compacted_disarm_landings(world,
                                                                native_histories)
            if compact_receipt_facts:
                history_codec.restore_compacted_receipt_facts(world,
                                                               native_histories)
            if compact_target_history:
                history_codec.restore_compacted_target_history(world,
                                                                native_histories)
        except history_codec.NativeHistoryRejected as exc:
            raise ArenaNativeSnapshotRejected(
                f'compacted native history cannot be restored: {exc}') from exc

    # Native inventory intentionally excludes pointer anchors. Recreate them
    # from the restored objects, then verify the whole history with native inspection.
    entities = world.object_registry.object_instances
    for saved_encounter in encounters:
        for receipt in saved_encounter.__dict__.get('_atomic_interval_history', ()):
            meta = receipt.inspection
            _need(type(meta) is CommittedBoundaryRecord,
                  'unsupported Arena committed inspection record')
            targets = {}
            for entity_id in meta.entities:
                entity = entities.get(entity_id)
                _need(entity is not None, 'committed Target owner is not registered')
                storage = entity.__dict__.get('_atomic_target_history')
                record = next((row for row in storage if row.encounter_id == saved_encounter.id
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
    book = encounter._choice_book
    history = encounter.__dict__.get('_atomic_interval_history', [])
    # Re-issue exact receipts only under this restoration owner, and require
    # the complete native inspection gate before exposing the graph.
    from atomic_publication import (_register_arena_restored_receipts,
                                    _register_arena_restored_disarm_landings)
    for saved_encounter in encounters:
        _register_arena_restored_receipts(saved_encounter, _ARENA_RESTORE_AUTHORITY)
        _register_arena_restored_disarm_landings(saved_encounter, _ARENA_RESTORE_AUTHORITY)
    pristine = (not encounter.initiated and encounter.time == encounter.start_time
        and not history and not encounter.pending_action_list
        and not encounter.finished_action_list and not encounter.cancelled_action_list
        and not book._choices and encounter.arena_activation is None
        and encounter.arena_movement_activation is None)
    bound_encounters = []
    try:
        # Native Saves are resumable simulation state, including a pristine
        # pre-Choice Encounter. Bind that exact initial state to its restored
        # private RNG owner so its deferred history recorder can begin at the
        # first real native commit. The legacy Arena reader keeps its existing
        # pristine, nontransactional coexistence behavior.
        if native or not pristine:
            _bind_restored_arena_progression(encounter, rng_owner, _ARENA_RESTORE_AUTHORITY)
            bound_encounters.append(encounter)
        for saved_encounter in encounters:
            if saved_encounter is encounter:
                continue
            owner = companion_rng_owners.get(saved_encounter.id)
            if owner is not None:
                _bind_restored_arena_progression(
                    saved_encounter, owner, _ARENA_RESTORE_AUTHORITY)
                bound_encounters.append(saved_encounter)
        for saved_encounter in encounters:
            if saved_encounter.__dict__.get('_atomic_interval_history'):
                inspect_encounter(saved_encounter)
    except Exception:
        for bound in reversed(bound_encounters):
            _unbind_restored_arena_progression(bound, _ARENA_RESTORE_AUTHORITY)
        from atomic_publication import (_unregister_arena_restored_receipts,
                                        _unregister_arena_restored_disarm_landings)
        for saved_encounter in encounters:
            _unregister_arena_restored_receipts(saved_encounter, _ARENA_RESTORE_AUTHORITY)
            _unregister_arena_restored_disarm_landings(saved_encounter, _ARENA_RESTORE_AUTHORITY)
        raise
    return world, encounter, rng_owner


def _rehydrate_native_services(cache, nodes, recipes, bindings):
    """Rebind the closed callback recipes admitted by NativeInventory."""
    from realization import RealityLedger
    from statistical_group import (StatisticalGroup,
                                   _formation_attribute_rng_provider)
    from personal_history import PersonalHistory
    from observer_proposals import RecipientIdentity
    from objective_reality import SubjectRealityCandidate
    from field_observation import BeliefLedger
    from history_conversation import HeardAccount
    from history_conversation import AskAboutPastAction
    from location_observation import (LocationEvidenceLedger,
                                      BeingLocationObservation)
    from object_observation import ObjectObservationLedger, ObjectObservation
    from checkpoint_adapters import NativeInventory
    from statistical_group import (validate_composition_records,
                                   validate_membership_history)

    groups = [value for value in cache.values()
              if type(value) is StatisticalGroup]
    histories = [value for value in cache.values()
                 if type(value) is PersonalHistory]
    from universe import Universe
    worlds = [value for value in cache.values() if type(value) is Universe]
    _need(len(worlds) == 1, 'native Save has no unique Universe root')
    world = worlds[0]
    reproduction_recipes = [recipe for recipe in recipes
                            if len(recipe) >= 3 and recipe[2] ==
                            'reproduction_group.logical_registry']
    ledgers = [value for value in cache.values()
               if type(value) is RealityLedger]
    inquiries = [value for value in cache.values()
                 if type(value) is AskAboutPastAction]
    expected_recipes = [
        ('native-recipe', 'native-closure-recipes/1',
         'reproduction_group.logical_registry', ('object', world.id),
         reproduction_recipes[0][4])
    ] if len(reproduction_recipes) == 1 else []
    _need(len(reproduction_recipes) == 1
          and len(reproduction_recipes[0]) == 5
          and reproduction_recipes[0][1] == 'native-closure-recipes/1'
          and reproduction_recipes[0][3] == ('object', world.id)
          and type(reproduction_recipes[0][4]) is str,
          'native reproduction registry recipe is missing or malformed')
    expected_recipes = [reproduction_recipes[0]]
    for group in groups:
        expected_recipes.extend((
            ('native-recipe', 'native-closure-recipes/1',
             'statistical_group.formation_attribute_rng',
             ('object', group.id),
             'composition_rng(seed,id,formation_attribute,member_id,attribute)'),
            ('native-recipe', 'native-closure-recipes/1',
             'statistical_group.validate_composition_records',
             ('object', group.id), 'formation_time,reality'),
        ))
    for history in histories:
        expected_recipes.append((
            'native-recipe', 'native-closure-recipes/1',
            'personal_history.validate_history_constraints',
            ('object', history.being.id),
            'earliest,known_through,nondeclining_skills,reality,skill_use_history'))
    account_recipes = [recipe for recipe in recipes
                       if len(recipe) >= 3 and recipe[2] ==
                       'history_conversation.received_accounts_binding']
    _need(all(len(recipe) == 6 and recipe[1] == 'native-closure-recipes/1'
              and recipe[3][0] == 'object'
              and type(recipe[3][1]) is str
              and type(recipe[4]) is str and type(recipe[5]) is str
              for recipe in account_recipes)
          and len({recipe[3][1] for recipe in account_recipes}) == len(account_recipes),
          'native received-account bindings are malformed or duplicated')
    expected_recipes.extend(account_recipes)
    from encounter import Encounter
    selected = [cache[ref] for ref, tag, _ in nodes
                if tag == 'encounter.Encounter'
                and type(ref) is tuple and ref and ref[0] == 'encounter']
    _need(len(selected) == 1,
          'native Save has no unique selected Encounter for observer-ledger restoration')
    encounter = selected[0]
    arena_recipes = [recipe for recipe in recipes
                     if len(recipe) >= 3 and recipe[2] == 'arena.perception_ledger']
    expected_observers = (tuple(encounter.being_list)
                          if encounter.arena_activation_enabled else ())
    _need(len(arena_recipes) == len(expected_observers)
          and len({recipe[3][1] for recipe in arena_recipes
                   if len(recipe) == 5 and type(recipe[3]) is tuple
                   and len(recipe[3]) == 2 and recipe[3][0] == 'object'
                   and type(recipe[3][1]) is str}) == len(arena_recipes),
          'native Arena perception recipes do not match the participant set')
    from checkpoint_arena_perception import (
        decode_arena_perception_ledger, encode_arena_perception_ledger,
    )
    entities = tuple(sorted(encounter.entity_ids()))
    for recipe in arena_recipes:
        _need(len(recipe) == 5 and recipe[1] == 'native-closure-recipes/1'
              and type(recipe[3]) is tuple and len(recipe[3]) == 2
              and recipe[3][0] == 'object' and type(recipe[3][1]) is str
              and type(recipe[4]) is tuple,
              'native Arena perception recipe is malformed')
        observer_id = recipe[3][1]
        _need(observer_id in expected_observers
              and observer_id in encounter.awareness,
              'native Arena perception recipe has no participant/awareness owner')
        observer = world.object_registry.object_instances.get(observer_id)
        _need(observer is not None,
              'native Arena perception observer is absent from the Entity registry')
        ledger = decode_arena_perception_ledger(
            recipe[4], observer_id=observer_id, entity_ids=entities,
            visible_entity_ids=tuple(sorted(encounter.awareness[observer_id])),
            boundary=encounter.last_processed_boundary, time=encounter.time)
        try:
            verified = encode_arena_perception_ledger(
                ledger, observer=observer, encounter=encounter,
                registry=world.object_registry.object_instances)
        except Exception as exc:
            raise ArenaNativeSnapshotRejected(
                f'native Arena perception recipe failed semantic validation: {exc}') from exc
        _need(verified == recipe[4],
              'native Arena perception recipe differs from restored observer state')
        object.__setattr__(observer, '_arena_perception_ledger', ledger)
        expected_recipes.append(recipe)
    owned_ledgers = {id(group._composition_reality) for group in groups}
    owned_ledgers.update(id(history.reality) for history in histories)
    expected_recipes.extend(
        ('native-recipe', 'native-closure-recipes/1',
         'unconstrained-RealityLedger')
        for ledger in ledgers if id(ledger) not in owned_ledgers)
    _need(sorted(recipes, key=repr) == sorted(expected_recipes, key=repr),
          'native Save callback recipes do not match restored owners')
    recipient_by_name = {}
    for namespace, name, role, observer_ids, reference in bindings:
        if role != 'in_world_received_accounts':
            continue
        recipient = cache.get(reference[1])
        _need(type(recipient) is list and (namespace, name) not in recipient_by_name,
              'native received-account recipient binding is missing or duplicated')
        recipient_by_name[(namespace, name)] = (recipient, observer_ids)
    for recipe in account_recipes:
        inquiry = next((value for value in inquiries if value.id == recipe[3][1]), None)
        bound = recipient_by_name.get((recipe[4], recipe[5]))
        _need(inquiry is not None and bound is not None
              and bound[1] and inquiry.actor_id in bound[1],
              'AskAboutPast recipient binding has no matching listener owner')
        account_list = bound[0]
        # One explicitly bound native list may serve several Actions and
        # listeners. The durable binding has already proved its complete
        # observer set, and native Action bindings above require this inquiry's
        # actor to be one of those owners. Validate each account against that
        # set instead of incorrectly treating a shared list as single-owner.
        _need(all(type(row) is HeardAccount and row.listener_id in bound[1]
                  for row in account_list),
              'AskAboutPast recipient contains an account for an unbound listener')
        inquiry.received_accounts = account_list
    from reproduction_checkpoint import (
        restore_portable_native_reproduction_registry,
        ReproductionCheckpointError,
    )
    try:
        restore_portable_native_reproduction_registry(world,
                                                      reproduction_recipes[0][4])
    except ReproductionCheckpointError as exc:
        raise ArenaNativeSnapshotRejected(
            f'native reproduction registry restore refused: {exc}') from exc
    for group in groups:
        try:
            validate_membership_history(group, world.object_registry.object_instances)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ArenaNativeSnapshotRejected(
                f'native Group membership restore refused: {exc}') from exc
        store = group._conditional_attributes
        group._composition_reality._validators = (
            group._validate_composition_facts,)
        store._rng_for = _formation_attribute_rng_provider(group)
        records = tuple(group._composition_reality._records.values())
        validate_composition_records(group.id, group.formation_time, records)
        class _RejectPendingRecipe:
            @staticmethod
            def issue(code, _owner, _field, reason):
                raise ArenaNativeSnapshotRejected(
                    f'native Group callback recipe is incomplete: {code}: {reason}')
        NativeInventory._conditional(_RejectPendingRecipe(), store, group)
    for history in histories:
        history.reality._validators = (history._validate,)
        history._validate(history.reality.view())
    for ledger in ledgers:
        if not any(group._composition_reality is ledger for group in groups) \
                and not any(history.reality is ledger for history in histories):
            ledger._validators = ()
    recipients = {}
    names = set()
    recipient_tokens = {}
    for namespace, name, role, observer_ids, reference in bindings:
        key = reference[1]
        recipient = cache.get(key)
        _need(recipient is not None and (namespace, name) not in names,
              'native host recipient reference is missing or duplicated')
        names.add((namespace, name))
        if role == 'in_world_belief_ledger':
            _need(type(recipient) is BeliefLedger
                  and observer_ids == (recipient.observer_id,),
                  'native Belief recipient identity/owner differs')
        elif role == 'in_world_received_accounts':
            _need(type(recipient) is list
                  and all(type(account) is HeardAccount
                          and account.listener_id in observer_ids
                          for account in recipient),
                  'native received-accounts binding is invalid')
        elif role == 'observer_location_evidence':
            _need(type(recipient) is LocationEvidenceLedger
                  and observer_ids == (recipient.observer_id,),
                  'native LocationEvidence binding owner differs')
            observations=recipient._observations
            _need(type(observations) is dict,
                  'native LocationEvidence observations are not a mapping')
            for observation_id, row in observations.items():
                _need(type(row) is BeingLocationObservation
                      and observation_id == row.id
                      and row.observer_id == recipient.observer_id,
                      'native location observation identity/owner differs')
                source=world.event_history.get(row.source_action_id)
                _need(type(source).__name__ == 'SpotAction'
                      and source.actor_id == row.observer_id
                      and source.target_id == row.being_id
                      and source._encounter is not None
                      and source._encounter.id == row.encounter_id
                      and type(source.resolution).__name__ == 'ActionProposal'
                      and source.resolution.outcome == 'success'
                      and row.boundary <= source._encounter.last_processed_boundary,
                      'native location observation has no successful Spot provenance')
        elif role == 'observer_object_evidence':
            _need(type(recipient) is ObjectObservationLedger
                  and observer_ids == (recipient.observer_id,),
                  'native ObjectEvidence binding owner differs')
            for observation_id, row in recipient._observations.items():
                _need(type(row) is ObjectObservation and observation_id == row.id
                      and row.observer_id == recipient.observer_id,
                      'native Object observation identity/owner differs')
                source=world.event_history.get(row.source_action_id)
                _need(type(source).__name__ == 'SpotAction'
                      and source.actor_id == row.observer_id
                      and source.target_id == row.object_id
                      and source._encounter is not None
                      and source._encounter.id == row.encounter_id
                      and type(source.resolution).__name__ == 'ActionProposal'
                      and source.resolution.outcome == 'success'
                      and row.boundary <= source._encounter.last_processed_boundary,
                      'native Object observation has no successful Spot provenance')
        else:
            _need(False, 'native host recipient role is unsupported')
        recipients[id(recipient)] = role
        from checkpoint_adapters import RecipientBinding, _portable_recipient_token
        token = _portable_recipient_token(RecipientBinding(
            world, namespace, name, role, observer_ids, recipient))
        _need(token not in recipient_tokens,
              'native recipient identity token collision')
        recipient_tokens[token] = (role, recipient)
    hash_containers = []
    for value in cache.values():
        if type(value) is dict:
            hash_containers.append((value, list(value.items())))
        elif type(value) is set:
            hash_containers.append((value, list(value)))
    for identity in (value for value in cache.values()
                     if type(value) is RecipientIdentity):
        token = identity.__dict__.get('object_identity')
        bound = recipient_tokens.get(token)
        _need(type(identity.role) is str and bound is not None
              and bound[0] == identity.role,
              'native observer identity has no restored recipient')
        recipient = bound[1]
        object.__setattr__(identity, 'object_identity', id(recipient))
    # RecipientIdentity participates in immutable-map keys. Rebuild every
    # restored hash container after replacing its portable integer token with
    # the current-process recipient address.
    for container, contents in hash_containers:
        container.clear()
        if type(container) is dict:
            container.update(contents)
        else:
            container.update(contents)
    reality_by_subject = {group.id: group._composition_reality for group in groups}
    reality_by_subject.update({history.being.id: history.reality for history in histories})
    for candidate in (value for value in cache.values()
                      if type(value) is SubjectRealityCandidate):
        reality = reality_by_subject.get(candidate.subject_id)
        _need(reality is not None,
              'native objective candidate has no restored Reality owner')
        object.__setattr__(candidate, 'ledger_identity',
                           id(reality))
    _need(all(type(ledger._validators) is tuple for ledger in ledgers),
          'native Reality validator rehydration failed')


def _decode_rng(value):
    if type(value) is tuple and value and value[0] == 'tuple':
        return tuple(_decode_rng(row) for row in value[1])
    if type(value) is tuple and value[0] == 'integer': return int(value[1])
    if type(value) is tuple and value[0] == 'binary64': return float.fromhex(value[1])
    if type(value) is tuple and value[0] == 'null': return None
    raise ArenaNativeSnapshotRejected('unsupported private RNG state')


from atomic_publication import _ARENA_RESTORED_RECEIPT_AUTHORITY as _ARENA_RESTORE_AUTHORITY
_OMIT = object()
