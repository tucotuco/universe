"""Inactive 5D2A native data recipes and explicit host recipient bindings.

No serializer, restoration, callback invocation, RNG draw or world publication.
Recipes describe native reconstruction obligations; they do not execute them.
Complete checkpoint readiness remains refused by checkpoint_inventory.
"""
from dataclasses import dataclass
from types import FunctionType, MethodType, CodeType, MappingProxyType
import hashlib
import math

from checkpoint_inventory import _Inventory, _TYPES, _require, CheckpointRejected
from checkpoint_fields import FIELD_ADAPTERS, RUN_SPOT_FIELD_CLOSURE
from conditional_attributes import ConditionalAttributes
import statistical_group
from statistical_group import (StatisticalGroup, validate_composition_records,
                               validate_membership_history)
from personal_history import PersonalHistory
from realization import RealityLedger, CommittedFact, FactKey
from field_observation import BeliefLedger
from being import BeingDefinition, BeingInstance
from frozen_practice import _copy_use, _capture_history

ADAPTER_VERSION = 'native-closure-recipes/1'
_ABSENT = object()
_NATIVE_GROUP_RNG = StatisticalGroup._rng
_NATIVE_ADULT_FORMATION_ASSIGNMENTS = StatisticalGroup._adult_formation_assignments
_NATIVE_GROUP_HOUSEHOLD_COUNT = StatisticalGroup.household_count
_NATIVE_GROUP_HOUSEHOLD = StatisticalGroup.household
_NATIVE_FORMATION_TRAIT_ASSIGNMENTS = statistical_group._formation_trait_assignments
_NATIVE_COMPOSITION_RNG = statistical_group.composition_rng
_NATIVE_GROUP_CONSTRAINT = StatisticalGroup._validate_composition_facts
_NATIVE_HISTORY_CONSTRAINT = PersonalHistory._validate
_NATIVE_ATTRIBUTE_LAMBDA = statistical_group._formation_attribute_rng_provider.__code__.co_consts[
    next(i for i, value in enumerate(
        statistical_group._formation_attribute_rng_provider.__code__.co_consts)
         if type(value) is CodeType and value.co_name == '<lambda>')]


def _portable_recipient_token(binding):
    """Stable, hashable temporary key for a bound recipient during restore."""
    identity = f'{binding.role}\0{binding.namespace}\0{binding.name}'
    return -1 - int.from_bytes(hashlib.sha256(identity.encode('utf-8')).digest()[:16],
                               'big')


@dataclass(frozen=True)
class RecipientBinding:
    """Host declaration, never embedded as a live handle in candidate data.

    namespace/name are supplied by the host, scoped to this exact world.
    One physical recipient has exactly one binding; shared consumers refer to
    that binding. observer_ids declares all permitted native recipient users.
    """
    world: object
    namespace: str
    name: str
    role: str
    observer_ids: tuple
    recipient: object


def _data_tree(value, active=None):
    """Check exact finite native data before any native deepcopy/pure validator."""
    if value is None or type(value) in (str, bool, int): return
    if type(value) is float:
        _require(math.isfinite(value), 'nonfinite adapter data'); return
    _require(type(value) in (dict,list,tuple,set,frozenset), 'opaque adapter data')
    active=set() if active is None else active
    _require(id(value) not in active, 'cyclic adapter data')
    active.add(id(value))
    if type(value) is dict:
        for key,item in value.items():
            _require(type(key) in (str,int,float,bool,tuple), 'opaque adapter key')
            _data_tree(key,active); _data_tree(item,active)
    else:
        for item in value: _data_tree(item,active)
    active.remove(id(value))


def _fields(value):
    tag=type(value).__module__+'.'+type(value).__name__
    _require(tag in FIELD_ADAPTERS, 'missing closed-field adapter: '+tag)
    data=object.__getattribute__(value,'__dict__')
    _require(type(data) is dict and all(type(k) is str for k in data), 'opaque field storage: '+tag)
    row=FIELD_ADAPTERS[tag]
    _require(not set(data)-set(row['allowed']), 'unknown native fields: '+tag+': '+','.join(sorted(set(data)-set(row['allowed']))))
    _require(not set(row['required'])-set(data), 'missing native fields: '+tag)
    return data


def _definition_values_equal(first, second, active=None):
    """Compare copied native definition values without relying on object identity."""
    if type(first) is not type(second):
        return False
    if first is None or type(first) in (str, bool, int):
        return first == second
    if type(first) is float:
        return math.isfinite(first) and math.isfinite(second) and first.hex() == second.hex()
    active = set() if active is None else active
    pair = (id(first), id(second))
    _require(pair not in active, 'cycle in native definition comparison')
    active.add(pair)
    try:
        if type(first) is dict:
            return (first.keys() == second.keys()
                    and all(_definition_values_equal(first[key], second[key], active)
                            for key in first))
        if type(first) in (list, tuple):
            return (len(first) == len(second)
                    and all(_definition_values_equal(a, b, active)
                            for a, b in zip(first, second)))
        if type(first) in (set, frozenset):
            return first == second
        first_data, second_data = _fields(first), _fields(second)
        return (first_data.keys() == second_data.keys()
                and all(_definition_values_equal(first_data[name], second_data[name], active)
                        for name in first_data))
    finally:
        active.remove(pair)


def _movement_activation_state(encounter, *, allow_first_choice=False):
    """Validate the existing movement-start record without adding authority."""
    from encounter import ArenaMovementActivation

    enabled = encounter.arena_activation_enabled
    _require(type(enabled) is bool,
             'Arena activation-enabled flag must be an explicit native Boolean')
    record = encounter.arena_movement_activation
    if record is None:
        if enabled:
            if encounter.arena_activation is not None:
                _require(allow_first_choice,
                         'activated Arena Encounter cannot be resumed by the bounded Run/Spot checkpoint')
                _action_activation_state(encounter, encounter.arena_activation)
                return None
            _require(encounter.initiated is False and encounter.arena_activation is None
                     and encounter.initiation is None and encounter.time==encounter.start_time
                     and encounter.last_processed_boundary==math.floor(encounter.start_time)
                     and not encounter.pending_action_list and not encounter.finished_action_list
                     and not encounter.cancelled_action_list
                     and not encounter.__dict__.get('_atomic_interval_history')
                     and not encounter._choice_book._choices,
                     'unactivated Arena state contains incompatible activation or progression data')
        return None
    _require(enabled and encounter.initiated is True
             and encounter.arena_activation is None and encounter.initiation is None,
             'Arena movement activation phase conflicts with Encounter activation state')
    _require(type(record) is ArenaMovementActivation,
             'unsupported Arena movement activation record type')
    data = _fields(record)
    _require(type(data['encounter_id']) is str and data['encounter_id'] == encounter.id
             and type(data['actor_id']) is str and data['actor_id'] in encounter.being_list
             and type(data['movement_decision_id']) is str
             and data['movement_decision_id'].strip()
             and len(data['movement_decision_id']) <= 512
             and type(data['time']) in (int, float) and math.isfinite(data['time'])
             and data['time'] == encounter.start_time
             and type(data['activation_kind']) is str
             and data['activation_kind'] == 'first_player_movement',
             'Arena movement activation record is inconsistent with its Encounter phase')
    return record


def _action_activation_state(encounter, record):
    """Validate the exact first-Arena-Choice binding for full native Saves."""
    from encounter import ArenaActionActivation
    from activities import (DelayAction, ReadyPreparationAction,
                            ReadyWeaponAction, RunAction)

    _require(type(encounter.arena_activation_enabled) is bool
             and encounter.arena_activation_enabled
             and encounter.initiated is True
             and encounter.arena_movement_activation is None
             and encounter.initiation is None,
             'Arena first-Choice activation conflicts with Encounter phase')
    _require(type(record) is ArenaActionActivation,
             'unsupported Arena first-Choice activation record')
    data = _fields(record)
    _require(data['encounter_id'] == encounter.id
             and type(data['actor_id']) is str
             and data['actor_id'] in encounter.being_list
             and type(data['choice_id']) is str and data['choice_id']
             and type(data['time']) in (int, float) and math.isfinite(data['time'])
             and data['time'] == encounter.start_time
             and data['activation_kind'] == 'first_player_choice',
             'Arena first-Choice activation identity or start cursor is invalid')
    record_choice = encounter._choice_book._choices.get(data['choice_id'])
    _require(record_choice is not None
             and record_choice.view.id == data['choice_id']
             and record_choice.origin == 'arena-first-player-choice'
             and record_choice.view.first_start == encounter.start_time
             and len(record_choice.members) == 1
             and record_choice.view.action_ids == (record_choice.members[0].action.id,)
             and record_choice.members[0].action.actor_id == data['actor_id']
             and type(record_choice.members[0].action) in
                 (RunAction, ReadyWeaponAction, ReadyPreparationAction, DelayAction)
             and encounter.universe.event_history.get(
                 record_choice.members[0].action.id) is record_choice.members[0].action,
             'Arena activation does not name its exact first native Choice')
    return record


def _ledger_records(ledger):
    _require(type(ledger) is RealityLedger, 'unreviewed Reality ledger type')
    d=_fields(ledger); rev=d['_revision']; records=d['_records']
    _require(type(rev) is int and rev>=0 and type(records) is dict, 'invalid Reality metadata')
    revisions=[]
    for key,record in records.items():
        _require(type(key) is FactKey and type(record) is CommittedFact, 'opaque Reality fact')
        kd=_fields(key);rd=_fields(record); _require(type(rd['key']) is FactKey,'opaque record key');_fields(rd['key'])
        _require(type(kd['entity_id']) is str and kd['entity_id'] and type(kd['attribute']) is str and kd['attribute'] and type(kd['detail']) is str, 'invalid fact identity')
        _require(kd['time'] is None or type(kd['time']) in (int,float) and math.isfinite(kd['time']), 'invalid fact time')
        _require(key==rd['key'] and type(rd['revision']) is int and 1<=rd['revision']<=rev and type(rd['origin']) is str and rd['origin'].strip(), 'invalid fact key/revision/origin')
        _data_tree(rd['value']);revisions.append(rd['revision'])
    _require(revisions==sorted(revisions) and set(revisions)==set(range(1,rev+1)), 'invalid Reality revision chronology')
    return tuple(records.values())


class NativeInventory(_Inventory):
    types = _TYPES | {ConditionalAttributes}

    def __init__(self, world, encounter, bindings, *, rng_owner=None,
                 full_native=False, compact_native_target_history=False,
                 compact_native_entity_context=False,
                 compact_native_receipt_facts=False,
                 compact_native_recipient_facts=False,
                 compact_native_publication_facts=False,
                 compact_native_disarm_landings=False,
                 compact_native_boundary_history=False):
        super().__init__()
        _require(type(bindings) is tuple, 'bindings must be an explicit tuple')
        self.world=world; self.encounter=encounter;self.bindings=bindings
        self.rng_owner=rng_owner
        self.full_native=full_native
        self.compact_native_target_history=compact_native_target_history
        self.compact_native_entity_context=compact_native_entity_context
        self.compact_native_receipt_facts=compact_native_receipt_facts
        self.compact_native_recipient_facts=compact_native_recipient_facts
        self.compact_native_publication_facts=compact_native_publication_facts
        self.compact_native_disarm_landings=compact_native_disarm_landings
        self.compact_native_boundary_history=compact_native_boundary_history
        self.recipient_by_id={}; self.names=set();self.conditional_owners={};self.ledger_owners={}
        self.stack=set();self.checked=set();self.mutable_recipients={}
        objects=world.object_registry.object_instances
        for b in bindings:
            _require(type(b) is RecipientBinding and b.world is world, 'foreign or opaque recipient binding root')
            _require(all(type(s) is str and s.strip() for s in (b.namespace,b.name)), 'empty binding namespace/name')
            _require(type(b.observer_ids) is tuple and b.observer_ids and all(type(i) is str and type(objects.get(i)) is BeingInstance for i in b.observer_ids), 'binding observer must be a registered native Being')
            _require(len(set(b.observer_ids))==len(b.observer_ids), 'duplicate binding observer')
            key=(b.namespace,b.name)
            _require(key not in self.names, 'duplicate durable recipient name')
            _require(id(b.recipient) not in self.recipient_by_id, 'one physical recipient cannot have distinct bindings')
            if b.role=='in_world_belief_ledger':
                _require(type(b.recipient) is BeliefLedger and b.observer_ids==(b.recipient.observer_id,), 'mismatched Belief role/observer')
                self._recipient_aliases(b.recipient)
            elif b.role=='in_world_received_accounts':
                from history_conversation import HeardAccount
                _require(type(b.recipient) is list, 'mismatched accounts role')
                for account in b.recipient:
                    _require(type(account) is HeardAccount,'opaque heard account');ad=_fields(account)
                    _require(ad['listener_id'] in b.observer_ids and ad['speaker_id'] in objects,'account binding owner/reference mismatch')
            elif b.role=='observer_location_evidence':
                from activities import SpotAction
                from location_observation import (LocationEvidenceLedger,
                                                  BeingLocationObservation)
                _require(type(b.recipient) is LocationEvidenceLedger
                         and b.observer_ids==(b.recipient.observer_id,),
                         'mismatched location-evidence role/observer')
                ledger_data=_fields(b.recipient)
                observations=ledger_data['_observations']
                _require(type(observations) is dict,
                         'location observations must be a native mapping')
                _require(id(observations) not in self.mutable_recipients,
                         'shared mutable location recipient container')
                self.mutable_recipients[id(observations)]=(id(b.recipient),'_observations')
                for observation_id, row in observations.items():
                    _require(type(row) is BeingLocationObservation
                             and observation_id==row.id
                             and row.observer_id==b.recipient.observer_id
                             and type(objects.get(row.being_id)) is BeingInstance,
                             'location observation owner/Being identity is inconsistent')
                    source=world.event_history.get(row.source_action_id)
                    _require(type(source) is SpotAction
                             and source.actor_id==row.observer_id
                             and source.target_id==row.being_id,
                             'location observation has no matching native Spot Action')
            elif b.role=='observer_object_evidence':
                from activities import SpotAction
                from object import ObjectInstance
                from object_observation import (ObjectObservationLedger,
                                                ObjectObservation)
                _require(type(b.recipient) is ObjectObservationLedger
                         and b.observer_ids==(b.recipient.observer_id,),
                         'mismatched ObjectEvidence role/observer')
                observations=_fields(b.recipient)['_observations']
                _require(type(observations) is dict
                         and id(observations) not in self.mutable_recipients,
                         'Object observations must be a unique native mapping')
                self.mutable_recipients[id(observations)]=(id(b.recipient),'_observations')
                for observation_id, row in observations.items():
                    _require(type(row) is ObjectObservation
                             and observation_id==row.id
                             and row.observer_id==b.recipient.observer_id
                             and type(objects.get(row.object_id)) is ObjectInstance,
                             'Object observation owner/Object identity is inconsistent')
                    source=world.event_history.get(row.source_action_id)
                    _require(type(source) is SpotAction
                             and source.actor_id==row.observer_id
                             and source.target_id==row.object_id,
                             'Object observation has no matching native Spot Action')
            else: raise CheckpointRejected('unsupported recipient role')
            self.names.add(key);self.recipient_by_id[id(b.recipient)]=b
            self.anchor(b.recipient,('host-recipient',world.id,b.namespace,b.name))
        _require(not set(self.recipient_by_id).intersection(self.mutable_recipients),
                 'recipient binding aliases another recipient internal container')
        for obj in objects.values():
            if type(obj) is StatisticalGroup:
                validate_membership_history(obj, objects)
                data=_fields(obj)
                for lookup,child in ((self.conditional_owners,data['_conditional_attributes']), (self.ledger_owners,data['_composition_reality'])):
                    _require(id(child) not in lookup,'shared native owner store');lookup[id(child)]=obj
            elif type(obj) is BeingInstance:
                data=_fields(obj); history=data.get('personal_history')
                if history is not None:
                    _require(type(history) is PersonalHistory,'unsupported historical owner')
                    hd=_fields(history);_require(hd['being'] is obj,'foreign personal history owner')
                    _require(id(hd['reality']) not in self.ledger_owners,'shared native Reality ledger')
                    self.ledger_owners[id(hd['reality'])]=history
        self._references(objects)

    def _recipient_aliases(self,ledger):
        d=_fields(ledger)
        for name in ('_evidence','_interpretations','_current_reassessments','_belief_history','_reassessments','communication_log','_inquiry_history'):
            value=d[name]
            _require(type(value) is (dict if name in ('_evidence','_interpretations','_current_reassessments') else list),'opaque recipient container')
            _require(id(value) not in self.mutable_recipients,'unsupported shared recipient internal container')
            self.mutable_recipients[id(value)]=(id(ledger),name)

    def _references(self,objects):
        exclusive={}
        for key,obj in objects.items():
            if type(obj) not in self.types:continue
            d=_fields(obj)
            for field in ('current','spatial_state','physical_fatigue'):
                v=d.get(field)
                if v is not None:
                    _require(id(v) not in exclusive,'unsupported shared live entity state: '+field)
                    exclusive[id(v)]=(key,field)
            parent=d.get('parent_container_id')
            _require(parent is None or type(parent) is str and parent in objects,'dangling parent container')
            seen={key};current=parent
            while current is not None:
                _require(current not in seen,'cyclic containment');seen.add(current)
                od=object.__getattribute__(objects[current],'__dict__');current=od.get('parent_container_id')
                _require(current is None or type(current) is str and current in objects,'dangling ancestor container')
            if type(obj) is BeingInstance:
                c=_fields(d['current']);parts=c['body_parts']
                _require(type(parts)is dict,'opaque equipment slots')
                refs=(*parts.values(),c['armor_id'],*d['possessions'])
                _require(all(r is None or type(r)is str and r in objects for r in refs),'dangling equipment/possession')

    def value(self,value,path,depth=0):
        kind=type(value)
        self._objects_by_identity[id(value)]=value
        if kind in self.types:
            _fields(value)
        if kind is BeliefLedger:
            _require(id(value) in self.recipient_by_id,'missing durable Belief binding')
        if kind.__module__+'.'+kind.__name__ == 'location_observation.LocationEvidenceLedger':
            _require(id(value) in self.recipient_by_id,
                     'missing durable LocationEvidence binding')
        if kind.__module__+'.'+kind.__name__ == 'object_observation.ObjectObservationLedger':
            _require(id(value) in self.recipient_by_id,
                     'missing durable ObjectEvidence binding')
        if kind in (dict,list,set):
            _require(id(value) not in self.stack, 'unsupported mutable container cycle at '+ '/'.join(path))
        self.stack.add(id(value))
        try:return super().value(value,path,depth)
        finally:self.stack.discard(id(value))

    def field(self,tag,field,item,ref,path,depth):
        if (self.compact_native_boundary_history
                and tag == 'encounter.Encounter'
                and field == '_atomic_interval_history'):
            from atomic_publication import PublishedInterval
            from encounter_inspection import CommittedBoundaryRecord
            from native_history import _canonical, _plain
            _require(type(item) is list and all(
                type(row) is PublishedInterval and row.committed is True
                and type(row.inspection) is CommittedBoundaryRecord
                for row in item),
                'native committed boundary history cannot be compacted from unreviewed receipts')
            source_digest = hashlib.sha256(_canonical(_plain(item))).hexdigest()
            self.dependencies.append((id(item), id(type(item)), source_digest))
            replacement = []
            encoded = super().field(tag, field, replacement, ref, path, depth)
            token_id = id(replacement)
            self.dependencies = [row for row in self.dependencies
                                 if row[0] != token_id]
            self._objects_by_identity.pop(token_id, None)
            self.known.pop(token_id, None)
            self.emitted.discard(token_id)
            return encoded
        if (self.compact_native_entity_context and
                tag == 'encounter_inspection.CommittedBoundaryRecord'
                and field == 'entities'):
            from encounter_inspection import EntityInspection
            from native_history import _canonical, _plain
            _require(type(item) in (dict, MappingProxyType)
                     and all(type(identity) is str and identity
                         and type(row) is EntityInspection
                         for identity, row in item.items()),
                     'native EntityInspection context cannot be compacted from unreviewed records')
            # The history stream already stores these exact typed projections.
            # Bind capture freshness to the omitted source value, not merely
            # its immutable map handle, because the receipt itself is frozen
            # while its mapping must remain independently integrity checked.
            source_digest = hashlib.sha256(_canonical(_plain(item))).hexdigest()
            self.dependencies.append((id(item), id(type(item)), source_digest))
            empty_context = {}
            encoded = super().field(tag, field, empty_context, ref, path, depth)
            token_id = id(empty_context)
            self.dependencies = [row for row in self.dependencies
                                 if row[0] != token_id]
            self._objects_by_identity.pop(token_id, None)
            self.known.pop(token_id, None)
            self.emitted.discard(token_id)
            return encoded
        if (self.compact_native_receipt_facts
                and tag == 'encounter_inspection.CommittedBoundaryRecord'
                and field in ('actions', 'effects', 'objective', 'objective_use',
                              'starts', 'participants', 'schedule',
                              'projectile_states')):
            from native_history import _canonical, _plain
            if field in ('actions', 'effects', 'objective', 'projectile_states'):
                valid_shape = type(item) in (dict, MappingProxyType)
            elif field == 'schedule':
                from interval_staging import QueueProjection
                valid_shape = type(item) is QueueProjection
            else:
                valid_shape = type(item) is tuple
            _require(valid_shape,
                     'committed receipt fact cannot be compacted from unreviewed field')
            source_digest = hashlib.sha256(_canonical(_plain(item))).hexdigest()
            self.dependencies.append((id(item), id(type(item)), source_digest))
            if field in ('actions', 'effects', 'objective', 'projectile_states'):
                replacement = {}
            elif field == 'schedule':
                replacement = None
            else:
                replacement = ()
            encoded = super().field(tag, field, replacement, ref, path, depth)
            token_id = id(replacement)
            self.dependencies = [row for row in self.dependencies
                                 if row[0] != token_id]
            self._objects_by_identity.pop(token_id, None)
            self.known.pop(token_id, None)
            self.emitted.discard(token_id)
            return encoded
        if (self.compact_native_recipient_facts
                and tag == 'encounter_inspection.CommittedBoundaryRecord'
                and field == 'recipients'):
            from native_history import _canonical, _plain
            from observer_proposals import (RecipientIdentity, BeliefProjection,
                AccountsProjection, LocationEvidenceProjection,
                ObjectEvidenceProjection)
            _require(type(item) in (dict, MappingProxyType)
                     and all(type(identity) is RecipientIdentity
                         and type(projection) in (BeliefProjection,
                             AccountsProjection, LocationEvidenceProjection,
                             ObjectEvidenceProjection)
                         for identity, projection in item.items()),
                     'committed recipient projections cannot be compacted from unreviewed fields')
            source_digest = hashlib.sha256(_canonical(_plain(item))).hexdigest()
            self.dependencies.append((id(item), id(type(item)), source_digest))
            replacement = MappingProxyType({})
            encoded = super().field(tag, field, replacement, ref, path, depth)
            token_id = id(replacement)
            self.dependencies = [row for row in self.dependencies
                                 if row[0] != token_id]
            self._objects_by_identity.pop(token_id, None)
            self.known.pop(token_id, None)
            self.emitted.discard(token_id)
            return encoded
        if (self.compact_native_publication_facts
                and tag == 'atomic_publication.PublishedInterval'
                and field in ('action_ids', 'effect_ids', 'rng_state',
                              'notification_intents')):
            from native_history import _canonical, _plain
            _require(type(item) is tuple,
                     'committed publication fact cannot be compacted from unreviewed tuple')
            source_digest = hashlib.sha256(_canonical(_plain(item))).hexdigest()
            self.dependencies.append((id(item), id(type(item)), source_digest))
            empty_facts = ()
            encoded = super().field(tag, field, empty_facts, ref, path, depth)
            token_id = id(empty_facts)
            self.dependencies = [row for row in self.dependencies
                                 if row[0] != token_id]
            self._objects_by_identity.pop(token_id, None)
            self.known.pop(token_id, None)
            self.emitted.discard(token_id)
            return encoded
        if (self.compact_native_disarm_landings
                and tag == 'encounter.Encounter'
                and field == '_disarm_landing_receipts'):
            from encounter_inspection import DisarmLandingReceipt
            from native_history import _canonical, _plain
            _require(type(item) is list and all(
                type(row) is DisarmLandingReceipt for row in item),
                'Disarm landing history cannot be compacted from unreviewed records')
            source_digest = hashlib.sha256(_canonical(_plain(item))).hexdigest()
            self.dependencies.append((id(item), id(type(item)), source_digest))
            empty_facts = []
            encoded = super().field(tag, field, empty_facts, ref, path, depth)
            token_id = id(empty_facts)
            self.dependencies = [row for row in self.dependencies
                                 if row[0] != token_id]
            self._objects_by_identity.pop(token_id, None)
            self.known.pop(token_id, None)
            self.emitted.discard(token_id)
            return encoded
        if (self.compact_native_target_history and field == '_atomic_target_history'
                and tag in ('being.BeingInstance', 'object.ObjectInstance',
                            'weapon.WeaponInstance', 'armor.ArmorInstance',
                            'statistical_group.StatisticalGroup')):
            from action_settlement import TargetCandidate
            from atomic_publication import TargetIntervalRecord
            owner = self._objects_by_identity.get(self._owner_identity(ref))
            _require(type(item) is list and owner is not None
                     and all(type(row) is TargetIntervalRecord
                         and row.encounter_id in self.world.event_history
                         and type(row.boundary) is int and row.boundary > 0
                         and type(row.state) is TargetCandidate
                         and row.state.target_id == owner.id
                         for row in item),
                     'native Target history cannot be compacted from unreviewed records')
            # The replacement token below is synthetic. Keep the actual
            # source list in the candidate seal so any Target append between
            # capture and publication makes this exact cut stale.
            from native_history import _canonical, _plain
            source_digest = hashlib.sha256(_canonical(_plain(item))).hexdigest()
            self.dependencies.append((id(item), id(type(item)), source_digest))
            # TargetCandidate receipts have an exact, independently validated
            # representation in NativeHistory. The graph keeps the field in
            # its closed schema but stores an empty list; restore repopulates
            # this exact target-owned history before issuing receipt anchors.
            empty_history = []
            encoded = super().field(tag, field, empty_history, ref, path, depth)
            # The replacement is a serialization token, not part of the live
            # source read set. The source's actual list remains covered by the
            # candidate freshness snapshot and by the validated history log.
            token_id = id(empty_history)
            self.dependencies = [row for row in self.dependencies
                                 if row[0] != token_id]
            self._objects_by_identity.pop(token_id, None)
            self.known.pop(token_id, None)
            self.emitted.discard(token_id)
            return encoded
        if self.full_native and tag=='history_conversation.AskAboutPastAction' and field in (
                'generate','received_accounts'):
            _require(self.full_native,
                     'AskAboutPast callback/recipient requires the native adapter')
            owner=self._objects_by_identity.get(self._owner_identity(ref))
            from history_conversation import AskAboutPastAction
            _require(type(owner) is AskAboutPastAction,
                     'AskAboutPast field has no exact native Action owner')
            if field=='generate':
                from objective_reality import EpisodeFacts
                _require(type(item) is EpisodeFacts,
                         'AskAboutPast requires its adopted literal EpisodeFacts recipe')
                return super().field(tag,field,item,ref,path,depth)
            if item is None:
                return super().field(tag,field,item,ref,path,depth)
            binding=self.recipient_by_id.get(id(item))
            _require(binding is not None
                     and binding.role=='in_world_received_accounts'
                     and type(item) is list,
                     'AskAboutPast account list requires its explicit durable binding')
            return ('native-recipe', ADAPTER_VERSION,
                    'history_conversation.received_accounts_binding',
                    ('object',owner.id), binding.namespace, binding.name)
        if tag=='universe.Universe' and field=='_reproduction_group_registry':
            from reproduction_group import ReproductionGroupRegistry
            _require(type(item) is ReproductionGroupRegistry and item._world is self.world,
                     'ReproductionGroup registry is not bound to the captured Universe')
            if not self.full_native:
                return super().field(tag,field,item,ref,path,depth)
            from reproduction_checkpoint import (
                encode_portable_native_reproduction_registry,
                ReproductionCheckpointError,
            )
            try:
                portable=encode_portable_native_reproduction_registry(self.world)
            except ReproductionCheckpointError as exc:
                raise CheckpointRejected(str(exc)) from exc
            return ('native-recipe', ADAPTER_VERSION,
                    'reproduction_group.logical_registry', ('object',self.world.id),
                    portable)
        if tag=='being.BeingInstance' and field=='_arena_perception_ledger':
            if item is None:
                if self.full_native:
                    _require(not self.encounter.arena_activation_enabled,
                             'Arena-enabled Being has no observer-owned perception ledger')
                    return super().field(tag,field,item,ref,path,depth)
                _require(not self.encounter.arena_activation_enabled,
                         'Arena-enabled Being has no observer-owned perception ledger')
                return ('null-arena-perception-ledger',1)
            _require(self.encounter.arena_activation_enabled,
                     'Arena perception ledger is attached outside an enabled Arena Encounter')
            from checkpoint_arena_perception import (
                ArenaPerceptionCheckpointRejected, encode_arena_perception_ledger,
            )
            from being import BeingInstance
            owner=self._objects_by_identity[self._owner_identity(ref)]
            _require(type(owner) is BeingInstance,
                     'Arena perception ledger field is not owned by a native Being')
            try:
                encoded=encode_arena_perception_ledger(item,observer=owner,
                    encounter=self.encounter,registry=self.world.object_registry.object_instances)
            except ArenaPerceptionCheckpointRejected as exc:
                raise CheckpointRejected(str(exc)) from exc
            self.dependencies.append(('arena-perception-ledger',id(item),owner.id,encoded[0]))
            if self.full_native:
                return ('native-recipe', ADAPTER_VERSION,
                        'arena.perception_ledger', ('object', owner.id), encoded)
            return ('arena-perception-ledger',encoded)
        if tag=='encounter.Encounter' and field=='arena_activation_enabled':
            _require(type(item) is bool,'Arena activation-enabled flag must be an explicit native Boolean')
        if tag=='encounter.Encounter' and field=='arena_activation' and item is not None:
            if not self.full_native:
                raise CheckpointRejected(
                    'activated Arena Encounter cannot be resumed by the bounded Run/Spot checkpoint')
            _require(_action_activation_state(self.encounter, item) is item,
                     'Arena first-Choice activation failed native validation')
        if tag=='encounter.Encounter' and field=='arena_movement_activation':
            _require(_movement_activation_state(self.encounter, allow_first_choice=self.full_native) is item,
                     'Arena movement activation field differs from its owning Encounter state')
        if tag=='being.BeingInstance' and field=='_posture':
            _require(item is None or type(item) is str and item in ('standing', 'crouching', 'lying'),
                     'native Being posture must be unknown or a supported posture string')
        if tag=='being.BeingInstance' and field=='_arena_initial_profile' and item is not None:
            from npcgen_arena_adapter import validate_arena_initial_profile_record
            try:
                validate_arena_initial_profile_record(item)
            except (TypeError, ValueError) as exc:
                raise CheckpointRejected(str(exc)) from exc
            owner=self._objects_by_identity[self._owner_identity(ref)]
            _require(item['initial_total_experience'] == owner.original.experience,
                     'Arena initial profile XP differs from the registered Being original')
        if tag=='activities.SpotAction' and field=='location_ledger' and item is not None:
            if not self.full_native:
                self.issue('unbound_location_evidence_recipient',ref,field,
                    'Observer-owned location evidence recipient requires the full native Save binding.')
                return ('unsupported-reference','observer-location-evidence')
            binding=self.recipient_by_id.get(id(item))
            owner=self._objects_by_identity.get(self._owner_identity(ref))
            _require(binding is not None and binding.role=='observer_location_evidence'
                     and type(owner).__name__=='SpotAction'
                     and owner.actor_id in binding.observer_ids,
                     'Spot location evidence requires its explicit observer-owned binding')
            return self.value(item,path+(field,),depth+1)
        if tag=='activities.SpotAction' and field=='object_ledger' and item is not None:
            if not self.full_native:
                self.issue('unbound_object_evidence_recipient',ref,field,
                    'Observer-owned Object evidence recipient requires the full native Save binding.')
                return ('unsupported-reference','observer-object-evidence')
            binding=self.recipient_by_id.get(id(item))
            owner=self._objects_by_identity.get(self._owner_identity(ref))
            _require(binding is not None and binding.role=='observer_object_evidence'
                     and type(owner).__name__=='SpotAction'
                     and owner.actor_id in binding.observer_ids,
                     'Spot Object evidence requires its explicit observer-owned binding')
            return self.value(item,path+(field,),depth+1)
        if tag=='action_choice._Accepted' and field=='signatures':
            if self.full_native:
                # Every accepted declaration is revalidated at capture and
                # reconstructed from the exact restored Action fields under
                # the source fingerprint. The address-bearing signature itself
                # is a derived process-local cache.
                return ('derived-rebuild-required','declaration-signatures')
            from checkpoint_choices import describe_accepted_choice, ChoiceDescriptorRejected
            record=self._objects_by_identity.get(self._owner_identity(ref))
            try:
                _require(self.encounter._choice_book._choices.get(record.view.id) is record,
                         'choice owner identity changed')
                if record.view.state=='accepted':
                    descriptor=describe_accepted_choice(self.world,self.encounter,record.view.id)
                    return ('portable-choice-descriptor',descriptor.to_data())
                if record.view.state=='finished':
                    from checkpoint_receipts import describe_committed_receipt_chain
                    chain=describe_committed_receipt_chain(self.world,self.encounter,
                        quiescent=True,rng_scope='exclusive_encounter')
                    matches=tuple(row for row in chain.committed_choices if row.choice_id==record.view.id)
                    _require(len(matches)==1 and matches[0].action_ids==tuple(record.view.action_ids),
                             'finished ChoiceBook membership is not represented by committed receipts')
                    choice=matches[0]
                    return ('receipt-choice-membership',choice.choice_id,choice.version,
                            choice.origin,choice.action_ids)
                raise CheckpointRejected('executing/cancelled ChoiceBook signatures are not portable')
            except (ChoiceDescriptorRejected, AttributeError, TypeError, ValueError) as exc:
                self.issue('portable_choice_descriptor_unsupported',ref,field,str(exc))
                return ('unsupported-portable-choice',)
        if tag=='conditional_attributes.ConditionalAttributes' and field=='_rng_for':
            store=self.conditional_owners.get(self._owner_identity(ref))
            _require(store is not None, 'conditional store has no native group owner')
            self.dependencies.append(('conditional-provider',id(item),id(store)))
            _require(type(item) is FunctionType and item.__code__ is _NATIVE_ATTRIBUTE_LAMBDA
                and item.__defaults__ is None and not item.__kwdefaults__ and not item.__dict__
                and item.__code__.co_freevars==('self',) and item.__closure__ is not None
                and len(item.__closure__)==1 and item.__closure__[0].cell_contents is store
                and StatisticalGroup._rng is _NATIVE_GROUP_RNG
                and item.__globals__ is statistical_group.__dict__
                and statistical_group.composition_rng is _NATIVE_COMPOSITION_RNG,
                'conditional_attribute_adapter_missing: unreviewed provider or owner')
            return ('native-recipe',ADAPTER_VERSION,'statistical_group.formation_attribute_rng',('object',store.id),
                    'composition_rng(seed,id,formation_attribute,member_id,attribute)')
        if tag=='statistical_group.StatisticalGroup' and field=='_conditional_attributes':
            self._conditional(item,self.world.object_registry.object_instances[ref[-1]])
            return self.value(item,path+(field,),depth+1)
        if tag=='realization.RealityLedger' and field=='_validators':
            identity=self._owner_identity(ref);owner=self.ledger_owners.get(identity)
            self.dependencies.append(('native-validators',id(item),tuple(id(v) for v in item) if type(item)is tuple else ()))
            _require(type(item) is tuple,'opaque native validators')
            ledger=self._objects_by_identity[identity]
            records=_ledger_records(ledger)
            if not item:
                _require(owner is None,'missing required native constraint')
                return ('native-recipe',ADAPTER_VERSION,'unconstrained-RealityLedger')
            _require(len(item)==1 and type(item[0]) is MethodType,'unreviewed constraint callback')
            cb=item[0]
            if type(owner) is PersonalHistory:
                _require(cb.__self__ is owner and cb.__func__ is _NATIVE_HISTORY_CONSTRAINT
                    and PersonalHistory._validate is _NATIVE_HISTORY_CONSTRAINT,'unreviewed history validator')
                prior=tuple(_copy_use(v) for v in owner.being.skill_use_history)
                _capture_history(owner.being,owner,prior)
                return ('native-recipe',ADAPTER_VERSION,'personal_history.validate_history_constraints',('object',owner.being.id),
                        'earliest,known_through,nondeclining_skills,reality,skill_use_history')
            _require(type(owner) is StatisticalGroup and cb.__self__ is owner and cb.__func__ is _NATIVE_GROUP_CONSTRAINT
                and StatisticalGroup._validate_composition_facts is _NATIVE_GROUP_CONSTRAINT,'unreviewed Reality validator')
            validate_composition_records(owner.id,owner.formation_time,records)
            if owner._counts is not None:
                from objective_reality import _frozen_group, _counts
                expected=_counts(_frozen_group(owner),{r.key:r for r in records})
                _require(type(owner._counts) is dict and owner._counts==expected, 'group count cache contradicts established facts')
            return ('native-recipe',ADAPTER_VERSION,'statistical_group.validate_composition_records',('object',owner.id),'formation_time,reality')
        if tag=='observer_proposals.RecipientIdentity' and field=='object_identity':
            b=self.recipient_by_id.get(item)
            _require(b is not None,'missing durable committed recipient binding')
            owner=self._objects_by_identity[self._owner_identity(ref)]
            _require(owner.role==b.role,'committed recipient role mismatch')
            if self.full_native:
                return ('integer',str(_portable_recipient_token(b)))
            return ('reference',('host-recipient',self.world.id,b.namespace,b.name))
        if field in ('ledger','received_accounts') and tag in ('group_observation.ObserveGroupAction','history_conversation.AskAboutPastAction','activities.SpotAction') and item is not None:
            b=self.recipient_by_id.get(id(item));action=self._objects_by_identity[self._owner_identity(ref)]
            role='in_world_belief_ledger' if field=='ledger' else 'in_world_received_accounts'
            _require(b is not None and b.role==role and action.actor_id in b.observer_ids,'missing durable committed recipient binding: external Action owner/role does not match')
            return self.value(item,path+(field,),depth+1)
        return super().field(tag,field,item,ref,path,depth)

    def issue(self,code,owner,field,reason):
        if self.full_native and code=='semantic_closure_adapter_incomplete':
            return
        if self.full_native and code=='receipt_rebinding_required':
            return
        if code=='semantic_closure_adapter_incomplete':
            reason=('A bounded native Run/Spot field certificate may be present, but it does not close unrelated '
                'Library dictionaries/entities, all Universe alias roles, fresh declaration signatures, '
                'receipt reissuance/anchors, or restoration. Whole-checkpoint readiness remains refused.')
        super().issue(code,owner,field,reason)

    def _owner_identity(self,ref):
        return next(k for k,v in self.known.items() if v==ref)

    def _conditional(self,store,group):
        _require(type(store) is ConditionalAttributes,'conditional_attribute_adapter_missing: native store required')
        d=_fields(store)
        _data_tree(d['specifications']);_data_tree(d['_external']);_data_tree(d['_committed'])
        traits=group._formation_traits
        _data_tree(traits)
        _require(type(traits)is dict and not (set(traits)-{'adults'}),
            'only native adult formation traits are supported')
        adult_traits=traits.get('adults',{})
        _require(type(adult_traits)is dict,'adult formation traits must be a mapping')
        for trait_name,spec in adult_traits.items():
            _require(type(trait_name)is str and trait_name and type(spec)is dict,
                'formation trait names and specifications must be valid')
            quota=spec.get('count')
            initial=spec.get('initial_skills',{})
            _require(type(quota)is int and quota>=0,
                'formation trait count must be a nonnegative integer')
            _require(type(initial)is dict and all(type(name)is str and name
                and type(level)is int and level>=0 for name,level in initial.items()),
                'formation initial skills must be nonnegative integer levels')
        _require(type(d['_external']) is set and all(type(s)is str for s in d['_external'])
            and d['_external']==set(adult_traits), 'conditional external dependencies mismatch')
        # Native construction validates detached specifications only; it does not call rng_for.
        ConditionalAttributes(d['specifications'],None,d['_external'])
        _require(type(d['_committed']) is dict,'opaque conditional commitments')
        records=_ledger_records(group._composition_reality);facts={r.key:r.value for r in records}
        validate_composition_records(group.id,group.formation_time,records)
        exact_adult_assignments={}
        root_key=FactKey(group.id,'household_count',group.formation_time)
        root=facts.get(root_key)
        composition_complete=(type(root)is int and not isinstance(root,bool) and root>=0
            and all(type(facts.get(FactKey(group.id,'household',group.formation_time,str(household))))is dict
                    for household in range(root)))
        if adult_traits:
            _require(type(group)is StatisticalGroup
                and StatisticalGroup._adult_formation_assignments is _NATIVE_ADULT_FORMATION_ASSIGNMENTS
                and StatisticalGroup.household_count is _NATIVE_GROUP_HOUSEHOLD_COUNT
                and StatisticalGroup.household is _NATIVE_GROUP_HOUSEHOLD
                and StatisticalGroup._rng is _NATIVE_GROUP_RNG
                and statistical_group._formation_trait_assignments is _NATIVE_FORMATION_TRAIT_ASSIGNMENTS
                and statistical_group.composition_rng is _NATIVE_COMPOSITION_RNG
                and type(group._composition_reality)is RealityLedger
                and not any(name in object.__getattribute__(group,'__dict__')
                    for name in ('household','household_count','_adult_formation_assignments','_rng')),
                'unreviewed native formation-assignment provider')
        if composition_complete and adult_traits:
            candidates=[f'{group.id}/{household}/adults/{index}'
                for household in range(root)
                for index in range(facts[FactKey(group.id,'household',group.formation_time,str(household))]['adults'])]
            for trait_name in sorted(adult_traits):
                quota=adult_traits[trait_name]['count']
                _require(quota<=len(candidates),'formation trait quota exceeds committed adult cohort')
                exact_adult_assignments[trait_name]=_NATIVE_FORMATION_TRAIT_ASSIGNMENTS(
                    group.seed,group.id,trait_name,candidates,quota)
        for identity,values in d['_committed'].items():
            _require(type(identity)is str and identity.startswith(group.id+'/'),'foreign conditional identity')
            parts=identity[len(group.id)+1:].split('/')
            _require(len(parts)==3 and parts[1]=='adults' and parts[0].isdecimal() and parts[2].isdecimal(),'invalid conditional member identity')
            household,index=int(parts[0]),int(parts[2])
            _require(str(household)==parts[0] and str(index)==parts[2],'noncanonical conditional identity')
            h=facts.get(FactKey(group.id,'household',group.formation_time,str(household)))
            _require(type(h)is dict and index<h['adults'],'conditional member lacks established household')
            _require(type(values)is dict and set(values)<=set(d['specifications']),'unknown committed conditional attribute')
            for name,value in values.items():
                spec=d['specifications'][name];parent=spec.get('given')
                if parent is None: cdfs=[spec['cdf']]
                elif parent in d['_external']:
                    if parent not in exact_adult_assignments:
                        _require(composition_complete,
                            'conditional external assignment requires committed complete household composition')
                        _require(parent in exact_adult_assignments,
                            'formation assignment provider was not validated')
                    branch='true' if identity in exact_adult_assignments[parent] else 'false'
                    _require(branch in spec['conditional_cdfs'],'missing conditional external assignment branch')
                    cdfs=[spec['conditional_cdfs'][branch]]
                else:
                    _require(parent in values,'missing committed conditional parent')
                    p=values[parent]; branch=('true' if p else 'false') if type(p)is bool else str(p)
                    _require(branch in spec['conditional_cdfs'],'missing conditional parent branch');cdfs=[spec['conditional_cdfs'][branch]]
                _require(any(type(v)is type(value) and v==value for cdf in cdfs for v,_ in cdf),'impossible committed conditional value')

    def _bounded_run_spot_closure(self,world,encounter,rng_role,rng_owner=None):
        """Prove the native Arena Being and ground/carried Object subset."""
        from library import Library
        from being import BeingDictionary
        from object import ObjectDefinition, ObjectInstance
        from weapon import WeaponInstance, WeaponDefinition
        from armor import ArmorInstance, ArmorDefinition
        from skill import SkillDictionary
        from activities import RunAction,SpotAction
        from atomic_publication import RNGCursor
        from checkpoint_choices import describe_accepted_choice,ChoiceDescriptorRejected
        from checkpoint_receipts import (describe_committed_receipt_chain,
            ReceiptDescriptorRejected,PortableBoundaryReceipt,
            PortableMovementOnlyBoundaryReceipt,
            PortableContinuingMovementBoundaryReceipt)
        from physiology_registry import PhysiologyRegistry,PhysiologyDefinition
        from physical_fatigue import PhysicalFatigueState
        from action_choice import ChoiceBook
        from spatial.state import SpatialState
        from spatial.geometry import Sphere,AxisAlignedBox
        from spatial.occlusion import VisualOcclusion
        from abilities import Abilities
        from skill import Skills
        from speeds import Speed
        from states import States
        from transactional_progression import _BINDINGS
        binding=_BINDINGS.get(id(encounter))

        _require(type(encounter.arena_activation_enabled) is bool,
                 'Arena activation-enabled flag is malformed')
        _require(encounter.arena_activation is None,
                 'activated Arena Encounter cannot be resumed by the bounded Run/Spot checkpoint')
        movement_activation = _movement_activation_state(encounter)
        _require(encounter.initiation is None,
                 'target-directed Encounter initiation is outside the bounded checkpoint subset')

        _require(type(world.library) is Library,'Run/Spot closure requires one exact native Library')
        _require(type(world.id) is str and world.id and type(encounter.id) is str and encounter.id
                 and type(world.library.id) is str and world.library.id,
                 'Universe, Encounter and Library logical IDs must be nonempty strings')
        _require(type(world.library.being_dictionary) is BeingDictionary
                 and type(world.library.skill_dictionary) is SkillDictionary,
                 'Run/Spot closure requires native Being and Skill dictionaries')
        for tag,policy in RUN_SPOT_FIELD_CLOSURE.items():
            _require(tag in FIELD_ADAPTERS,'missing Run/Spot field vocabulary for '+tag)
            adapter=FIELD_ADAPTERS[tag]
            classified=(set(policy['authoritative'])|set(policy.get('derived',()))
                        |set(policy.get('transient',()))|set(policy.get('out_of_scope',()))
                        |set(policy.get('unsupported_optional',())))
            _require(classified==set(adapter['allowed'])
                     and not set(policy.get('transient',()))-set(adapter['allowed'])
                     and not (set(adapter['required'])-set(adapter['allowed'])),
                     'Run/Spot A/D/T/U field policy does not exactly cover the native closed-field adapter: '+tag)
        pristine=(encounter.arena_activation_enabled is True and not encounter.initiated
            and encounter.time==encounter.start_time and not encounter._choice_book._choices
            and not encounter.pending_action_list and not encounter.finished_action_list
            and not encounter.cancelled_action_list
            and not encounter.__dict__.get('_atomic_interval_history'))
        selected_owner=(binding.rng_owner if binding is not None
            and binding.encounter() is encounter else rng_owner)
        _require(type(rng_role) is str and rng_role=='caller_cursor'
                 and type(selected_owner) is RNGCursor
                 and ((binding is not None and binding.encounter() is encounter
                       and binding.rng_owner is selected_owner)
                      or (binding is None and pristine)),
                 'Run/Spot closure requires the private bound cursor or a pristine Arena session cursor')
        _require(not self.bindings,'external recipient bindings are outside the Run/Spot subset')
        _require(type(encounter.being_list) is list and encounter.being_list
                 and len(encounter.being_list)==len(set(encounter.being_list))
                 and type(encounter.non_being_object_list) is list
                 and len(encounter.non_being_object_list)==len(set(encounter.non_being_object_list)),
                 'bounded Encounter entity lists must contain unique native IDs')

        being_dictionary=world.library.being_dictionary
        bd=_fields(being_dictionary);definitions=bd['objects']
        _require(type(definitions) is dict and definitions,'Being definition dictionary is missing or malformed')
        definition_ids={};definition_mutables={}
        for key,definition in definitions.items():
            _require(type(key) is str and key.strip() and type(definition) is BeingDefinition,
                     'unsupported Being definition dictionary entry')
            data=_fields(definition)
            _require(data['obj_type']==key,'Being definition key and obj_type disagree')
            self._validate_being_definition(definition)
            _require(id(definition) not in definition_ids,'one Being definition is ambiguously indexed by multiple keys')
            definition_ids[id(definition)]=key
            self._closed_definition_value(definition,owner=('definition',key),mutable_owners=definition_mutables)

        skill_dictionary=world.library.skill_dictionary
        sd=_fields(skill_dictionary);skill_rows=sd['skills']
        _require(type(skill_rows) is dict and {'run','spot'}<=set(skill_rows),
                 'Run/Spot practice definitions are missing')
        for name,row in skill_rows.items():
            _require(type(name) is str and name.strip() and type(row) is dict
                     and tuple(row)==('is_ordinary','is_progressive')
                     and type(row['is_ordinary']) is bool and type(row['is_progressive']) is bool,
                     'unsupported or corrupt native SkillDictionary definition')
        _require(len({id(row) for row in skill_rows.values()})==len(skill_rows),
                 'SkillDictionary definition rows have ambiguous shared mutable aliases')

        physiology=encounter.__dict__.get('_physiology_registry')
        if physiology is not None:
            _require(type(physiology) is PhysiologyRegistry,'unsupported physiology registry type')
            pd=_fields(physiology);rows=pd['_definitions']
            _require(type(rows) is dict,'malformed physiology definition dictionary')
            from dataclasses import fields as dataclass_fields
            from universe_physical_fatigue_r4 import Profile
            profile_fields={field.name for field in dataclass_fields(Profile)}
            for key,definition in rows.items():
                _require(type(key) is str and type(definition) is PhysiologyDefinition
                         and definition.identifier==key,'physiology definition ID mismatch')
                _fields(definition)
                _require('@' in key and key.strip()==key
                         and (definition.parent_id is None)==(definition.model is not None)
                         and definition.model in (None,'human-r4','parameterized-r4'),
                         'physiology definition root/model contract is invalid')
                params=definition.parameters
                _require(type(params) is tuple and tuple(name for name,_ in params)==tuple(sorted({name for name,_ in params}))
                         and all(type(name) is str and name in profile_fields
                                 and type(value) is float and math.isfinite(value) for name,value in params),
                         'physiology parameter data is not canonical')
                if definition.model=='parameterized-r4':
                    _require({name for name,_ in params}==profile_fields,
                             'parameterized physiology root is missing profile fields')
                cursor=definition;seen=set()
                while cursor.parent_id is not None:
                    _require(cursor.identifier not in seen,'cyclic physiology reference')
                    seen.add(cursor.identifier)
                    cursor=rows.get(cursor.parent_id)
                    _require(type(cursor) is PhysiologyDefinition,'missing physiology parent definition')

        being_ids=set(encounter.being_list)
        object_ids=set(encounter.non_being_object_list)
        receipts=();receipt_descriptor_data=()
        history=encounter.__dict__.get('_atomic_interval_history',())
        if movement_activation is not None:
            _require((history is None or history == () or type(history) is list) and
                     (history or (encounter.time==encounter.start_time
                                  and encounter.last_processed_boundary==math.floor(encounter.start_time))),
                     'movement activation without receipts must remain at its exact pre-boundary cursor')
        if history:
            try:
                receipt_descriptor=describe_committed_receipt_chain(world,encounter,
                    quiescent=True,rng_scope='exclusive_encounter')
            except ReceiptDescriptorRejected as exc:
                raise CheckpointRejected('Run/Spot receipt closure refused: '+str(exc)) from exc
            receipts=receipt_descriptor.receipts
            receipt_descriptor_data=(receipt_descriptor.to_data(),)
            for receipt in receipts:
                if type(receipt) is PortableBoundaryReceipt:
                    for action in receipt.actions:
                        _require(action.adapter in ('native.run-action/1','native.spot-action/1'),
                                 'committed receipt contains an unsupported Action family')
                        being_ids.add(action.actor_id)
                        if action.target_id is not None:being_ids.add(action.target_id)
                elif type(receipt) in (PortableMovementOnlyBoundaryReceipt,
                                       PortableContinuingMovementBoundaryReceipt):
                    _require(set(receipt.participant_ids)==being_ids|object_ids,
                             'movement receipt Entity set disagrees with native Encounter registry')
                else:
                    raise CheckpointRejected('receipt chain contains an unsupported boundary type')

        accepted=[];committed_ids={aid for receipt in receipts for aid in receipt.action_ids}
        book=encounter._choice_book
        _require(type(book) is ChoiceBook and book.encounter is encounter,
                 'ChoiceBook is outside the bounded Run/Spot owner graph')
        from action_choice import _Accepted
        with book.lock:
            for choice_id,record in book._choices.items():
                _require(type(record) is _Accepted and record.view.id==choice_id,
                         'unsupported ChoiceBook record or identity')
                if record.view.state=='accepted':
                    try:descriptor=describe_accepted_choice(world,encounter,choice_id)
                    except ChoiceDescriptorRejected as exc:
                        raise CheckpointRejected('accepted Run/Spot choice closure refused: '+str(exc)) from exc
                    accepted.append(descriptor)
                    for member in record.members:
                        action=member.action
                        _require(type(action) in (RunAction,SpotAction),
                                 'accepted choice contains an unsupported Action')
                        being_ids.add(action.actor_id)
                        if action.target_id is not None:being_ids.add(action.target_id)
                elif record.view.state=='finished':
                    _require(set(record.view.action_ids)<=committed_ids,
                             'finished ChoiceBook record lacks matching committed receipt')
                else:
                    raise CheckpointRejected('executing or cancelled choices are outside the bounded subset')
        _require(not encounter.pending_action_list and not encounter.cancelled_action_list,
                 'active pending or cancelled Actions are outside the bounded subset')
        if not receipts:
            _require(not encounter.finished_action_list and not committed_ids,
                     'finished Actions require a committed receipt descriptor')
        allowed_events={'0',encounter.id}|committed_ids
        _require(set(world.event_history)==allowed_events,
                 'Event registry contains data outside the bounded origin/Encounter/Run/Spot graph')

        registry=world.object_registry.object_instances
        expected_ids=being_ids|object_ids
        _require(set(registry)==expected_ids,
                 'bounded Universe registry contains unrelated entities outside the selected Encounter')
        _require(all(type(registry.get(entity_id)) is BeingInstance
                     and encounter.get_being(entity_id) is registry[entity_id]
                     for entity_id in being_ids),
                 'Encounter Being participant is missing or has an unsupported native type')
        _require(all(type(registry.get(entity_id)) in (ObjectInstance,WeaponInstance,ArmorInstance)
                     and encounter.get_entity(entity_id) is registry[entity_id]
                     for entity_id in object_ids),
                 'Encounter Object registry contains an unsupported or unresolved native entity')
        object_rows=[]
        possession_owners={}
        for being_id in sorted(being_ids):
            possessions=_fields(registry[being_id]).get('possessions')
            _require(type(possessions) is list and all(type(item) is str for item in possessions)
                     and len(possessions)==len(set(possessions)),
                     'Being possession references are malformed')
            for object_id in possessions:
                _require(object_id in object_ids and object_id not in possession_owners,
                         'Object possession is missing, duplicated, or owned outside this Encounter')
                possession_owners[object_id]=being_id
        for object_id in sorted(object_ids):
            obj=registry[object_id];data=_fields(obj)
            original=data['original'];current=data['current']
            _require(data['id']==object_id and data['type']==type(obj).__name__
                     and type(original) in (ObjectDefinition,WeaponDefinition,ArmorDefinition)
                     and type(current) is type(original) and current is not original
                     and original.obj_type==current.obj_type,
                     'Object identity or original/current definition state is unsupported')
            definition_dictionary=(world.library.weapon_dictionary if type(original) is WeaponDefinition
                else world.library.armor_dictionary if type(original) is ArmorDefinition
                else world.library.object_dictionary)
            _require(definition_dictionary.objects.get(original.obj_type) is original,
                     'Object original definition is not the exact registered native Library definition')
            self._closed_definition_value(original,
                owner=('object-definition',type(original).__name__,original.obj_type),
                mutable_owners=definition_mutables)
            self._closed_definition_value(current,
                owner=('object-current',object_id),mutable_owners=definition_mutables)
            parent=data['parent_container_id'];position=obj.get_position()
            _require(parent is None or type(parent) is str and parent in being_ids,
                     'Object custody parent is outside the Encounter Being set')
            if parent is None:
                _require(object_id not in possession_owners and position is not None,
                         'free Object must have a native position and no Being possession reference')
            else:
                _require(possession_owners.get(object_id)==parent and position is None,
                         'carried Object custody disagrees with native Being possession state')
            history=data.get('_atomic_target_history')
            _require(history is None or type(history) is list,
                     'Object Target history has an unsupported representation')
            object_rows.append((object_id,original.obj_type,type(obj).__name__,parent,
                None if position is None else tuple(float(value).hex() for value in position.as_tuple())))
        current_owned=dict(definition_mutables);covered=[];individualized_original_ids=set()
        for entity_id in sorted(being_ids):
            being=registry.get(entity_id)
            _require(type(entity_id) is str and type(being) is BeingInstance
                     and being.id==entity_id and encounter.get_being(entity_id) is being,
                     'Run/Spot logical Being reference is missing, ambiguous, or not a participant')
            data=_fields(being)
            _require(data['id']==entity_id and data['type']=='BeingInstance',
                     'Being identity fields disagree with the registry')
            facing=data['hex_facing']
            _require(facing is None or type(facing) is int and 0 <= facing < 12,
                     'invalid native hex facing in Being checkpoint state')
            posture=data['_posture']
            _require(posture is None or type(posture) is str
                     and posture in ('standing', 'crouching', 'lying'),
                     'invalid native Being posture in checkpoint state')
            try:
                effective_posture=being.get_posture()
            except ValueError as exc:
                raise CheckpointRejected('contradictory native Being posture state') from exc
            original=data['original'];current=data['current']
            original_kind=self._validate_being_original_definition(
                original, entity_id=entity_id, definitions=definitions,
                definition_ids=definition_ids,
                individualized_original_ids=individualized_original_ids,
                mutable_owners=current_owned)
            _require(type(current) is BeingDefinition and current.obj_type==original.obj_type
                     and current is not original,'Being current definition has unsupported type or aliases its Library original')
            owner=('being-current',entity_id)
            previous=current_owned.get(id(current))
            _require(previous is None,'mutable current definition aliases a Library definition or another Being')
            current_owned[id(current)]=owner
            _require(data.get('personal_history') is None,
                     'personal-history binding is outside this exact Run/Spot subset')
            physiology_id=data.get('physiology_id')
            _require(physiology_id is None or (type(physiology_id) is str
                     and physiology is not None and physiology_id in physiology._definitions),
                     'Being physiology reference is missing or outside its native registry')
            _require('alignment' not in data and 'current_armor_class' not in data,
                     'unsupported instance-level optional Being override')
            if data.get('spatial_state') is not None:
                _require(type(data['spatial_state']) is SpatialState,
                         'unsupported Being spatial state type')
                _fields(data['spatial_state'])
            fatigue=data.get('physical_fatigue')
            _require(type(fatigue) is PhysicalFatigueState
                     and type(fatigue.q) is float and type(fatigue.b) is float
                     and math.isfinite(fatigue.q) and math.isfinite(fatigue.b)
                     and 0<=fatigue.q<=1 and 0<=fatigue.b<=1,
                     'unsupported or malformed persistent Q/B state')
            history_rows=data.get('_atomic_target_history',[])
            _require(type(history_rows) is list,
                     'Target history storage has an unsupported optional representation')
            _require(type(data.get('skill_experience')) is dict
                     and type(data.get('skill_use_history')) is list
                     and type(data.get('_skill_practice_baselines')) is dict,
                     'Being practice fields have an unsupported optional representation')
            current_data=_fields(current)
            from skill import Skills
            _require(type(current_data['skills']) is Skills,'Being current Skills owner has unsupported type')
            skill_state=_fields(current_data['skills'])
            for skill_name,level in skill_state['skills'].items():
                _require(skill_name in skill_rows and type(level) in (int,float)
                         and math.isfinite(level),'Being skill rank has a missing definition or invalid value')
            for skill_name,level in skill_state['weapon_skills'].items():
                _require(skill_name in skill_rows and type(level) in (int,float)
                         and math.isfinite(level),'Being weapon-skill rank has a missing definition or invalid value')
            self._closed_definition_value(current,owner=owner,mutable_owners=current_owned)
            geometry=data.get('geometry')
            _require(geometry is None or type(geometry) in (Sphere,AxisAlignedBox),
                     'unsupported optional Being geometry')
            if geometry is not None:
                from measured_values import is_truncated_measurement
                _require(all(is_truncated_measurement(getattr(geometry, name))
                             for name in geometry._MEASURED_ATTRIBUTES),
                         'Being geometry measurements must be canonically truncated')
            occlusion=data.get('visual_occlusion')
            _require(occlusion is None or type(occlusion) is VisualOcclusion,
                     'unsupported optional Being visual-occlusion value')
            covered.append((entity_id,original.obj_type,original_kind,
                            tuple(sorted(skill_state['skills'])),
                            tuple(sorted(skill_state['weapon_skills'])),
                            ('binary64',fatigue.q.hex()),('binary64',fatigue.b.hex()),
                            physiology_id,geometry is not None,occlusion is not None,facing,effective_posture))
        return ('native.run-spot-field-closure/5',
            ('participants',tuple(sorted(being_ids))),
            ('objects',tuple(object_rows)),
            ('being-definitions',tuple(sorted({row[1] for row in covered}))),
            ('required-practice-skills',('run','spot')),
            ('participant-state',tuple(covered)),
            ('receipt-descriptors',receipt_descriptor_data),
            ('accepted-choice-descriptors',tuple(choice.to_data() for choice in sorted(accepted,key=lambda row:row.choice_id))),
            ('field-policy',tuple((tag,tuple(sorted(row['authoritative'])),
                                   tuple(sorted(row.get('derived',()))),
                                   tuple(sorted(row.get('transient',()))),
                                   tuple(sorted(row.get('out_of_scope',()))),
                                   tuple(sorted(row.get('unsupported_optional',()))),
                                   tuple(sorted(row.get('optional_values',{}))))
                                  for tag,row in sorted(RUN_SPOT_FIELD_CLOSURE.items()))),
            ('ownership-policy',('original-definition-canonical-or-template-derived',
                                 'individualized-original-exclusive-per-Being',
                                 'current-definition-exclusive-per-Being',
                                 'mutable-definition-subgraphs-cross-Being-exclusive',
                                 'logical-IDs-resolve-through-native-registry')))

    def _closed_definition_value(self,value,*,owner,active=None,mutable_owners=None):
        """Check all data below a selected definition without calling hooks."""
        if value is None or type(value) in (str,bool,int):return
        if type(value) is float:
            _require(math.isfinite(value),'nonfinite value in selected Being definition')
            return
        active=set() if active is None else active
        if type(value) in (dict,list,tuple,set,frozenset):
            identity=id(value)
            _require(identity not in active,'cycle in selected Being definition data')
            if mutable_owners is not None and type(value) in (dict,list,set):
                previous=mutable_owners.get(identity)
                _require(previous is None or previous==owner,
                         'mutable current-definition alias crosses Being ownership')
                mutable_owners[identity]=owner
            active.add(identity)
            if type(value) is dict:
                _require(all(type(key) in (str,bool,int,float,tuple) for key in value),
                         'unsupported selected definition dictionary key')
                for key,item in value.items():
                    self._closed_definition_value(key,owner=owner,active=active,mutable_owners=mutable_owners)
                    self._closed_definition_value(item,owner=owner,active=active,mutable_owners=mutable_owners)
            else:
                for item in value:
                    self._closed_definition_value(item,owner=owner,active=active,mutable_owners=mutable_owners)
            active.remove(identity);return
        tag=type(value).__module__+'.'+type(value).__name__
        _require(type(value) in self.types and tag in FIELD_ADAPTERS,
                 'unsupported executable or nonnative selected-definition value: '+tag)
        identity=id(value)
        _require(identity not in active,'cycle in selected native definition objects')
        if mutable_owners is not None:
            previous=mutable_owners.get(identity)
            _require(previous is None or previous==owner,
                     'mutable current-definition object alias crosses Being ownership')
            mutable_owners[identity]=owner
        data=_fields(value);active.add(identity)
        for item in data.values():
            self._closed_definition_value(item,owner=owner,active=active,mutable_owners=mutable_owners)
        active.remove(identity)

    def _validate_being_original_definition(self, original, *, entity_id,
                                           definitions, definition_ids,
                                           individualized_original_ids,
                                           mutable_owners):
        _require(type(original) is BeingDefinition,
                 'Being original definition has an unsupported native type')
        data=_fields(original)
        registered=tuple(key for key,value in definitions.items() if value is original)
        if registered:
            _require(len(registered)==1 and registered[0]==data['obj_type']
                     and definition_ids.get(id(original))==data['obj_type'],
                     'Being original definition has a foreign or ambiguous Library registration')
            return 'library-template'

        template=definitions.get(data['obj_type'])
        _require(type(template) is BeingDefinition and template.obj_type==data['obj_type'],
                 'individualized Being original has no matching registered native type template')
        _require(id(original) not in individualized_original_ids,
                 'individualized Being original definition is aliased by multiple Beings')
        template_data=_fields(template)
        self._validate_being_definition(original, individualized=True)
        mapped_fields={'length','weight','hit_points','experience','race','abilities','skills'}
        for field in set(template_data)-mapped_fields:
            _require(_definition_values_equal(data[field], template_data[field]),
                     'individualized Being original differs from its native type template outside mapped fields')

        expected_race=template_data['race']
        if expected_race is None:
            from npcgen_arena_adapter import _MOVEMENT_RACE_CATEGORIES
            obj_type=template_data['obj_type']
            if (type(obj_type) is str and obj_type.strip()
                    and obj_type.casefold() in _MOVEMENT_RACE_CATEGORIES):
                expected_race=obj_type
        _require(data['race']==expected_race,
                 'individualized Being original has a race value inconsistent with its native template')
        owner=('being-original',entity_id)
        self._closed_definition_value(original,owner=owner,mutable_owners=mutable_owners)
        individualized_original_ids.add(id(original))
        return 'individualized-native-template'

    def _validate_being_definition(self,definition,*,individualized=False):
        from abilities import Abilities
        from skill import Skills
        from speeds import Speed
        from states import States
        d=_fields(definition)
        numeric=('length','width','height','weight','cost','hardness','hit_points',
                 'experience','armor_class','challenge_rating')
        _require(all(type(d[name]) in (int,float) and math.isfinite(d[name]) for name in numeric),
                 'Being definition has an invalid numeric field')
        _require(all(type(d[name]) is str for name in ('obj_type','hit_dice','alignment'))
                 and type(d['is_magical']) is bool,
                 'Being definition has invalid scalar fields')
        _require(type(d['max_speed']) is Speed and type(d['abilities']) is Abilities
                 and type(d['skills']) is Skills and type(d['states']) is States,
                 'Being definition has unsupported native value object')
        for name in ('tags','senses','vulnerabilities','resistances','immunities',
                     'languages','psionics','spells','traits','actions','reactions','body_parts'):
            _require(type(d[name]) is dict,'Being definition map field is malformed: '+name)
        _require(type(d['weapon_categories']) is list,
                 'Being definition weapon categories are not an ordered list')
        _require(d['armor_id'] is None or type(d['armor_id']) is str,
                 'Being definition armor reference is not a logical ID')
        _require(d['physiology_id'] is None or type(d['physiology_id']) is str,
                 'Being definition physiology reference is not a logical ID')
        race_supported=(d['race'] is None or d['race'] in ('Elf', 'Half-elf'))
        if individualized and type(d['race']) is str:
            from npcgen_arena_adapter import _MOVEMENT_RACE_CATEGORIES
            race_supported=race_supported or d['race'].casefold() in _MOVEMENT_RACE_CATEGORIES
        _require(race_supported,
                 'Being definition has unsupported Spot action aptitude race')
        _require(d['discovery_dc'] is None or type(d['discovery_dc']) is int
                 and d['discovery_dc'] >= 0,
                 'Being definition has invalid discovery DC')

    def build(self,world,encounter,rng_role,rng_state,rng_scope):
        _require(rng_scope=='exclusive_encounter' and rng_role in ('caller_cursor','native_random'), 'native adapters require explicit private RNG authority')
        self._objects_by_identity={}
        if encounter.arena_activation_enabled:
            from being import BeingInstance
            from checkpoint_arena_perception import (
                ArenaPerceptionCheckpointRejected, encode_arena_perception_ledger,
            )
            observers=tuple(world.get_object_by_id(key) for key in encounter.being_list)
            _require(all(type(observer) is BeingInstance for observer in observers),
                     'Arena-enabled Encounter has a non-Being observer')
            ledger_fields=tuple(_fields(observer).get('_arena_perception_ledger',_ABSENT)
                                for observer in observers)
            # Legacy activation tests and out-of-scope hand-authored Encounters
            # have no revision-65 ledger at all. Preserve their existing
            # activation refusal; once any native ledger is present, require and
            # validate the complete observer-owned set before proceeding.
            if any(value is not _ABSENT for value in ledger_fields):
                for observer,ledger in zip(observers,ledger_fields):
                    try:
                        data=encode_arena_perception_ledger(ledger,observer=observer,
                            encounter=encounter,registry=world.object_registry.object_instances)
                    except ArenaPerceptionCheckpointRejected as exc:
                        raise CheckpointRejected(str(exc)) from exc
                    self.dependencies.append(('arena-perception-ledger',id(ledger),
                                              observer.id,data[0]))
        body=super().build(world,encounter,rng_role,rng_state,rng_scope)
        if not self.full_native:
            try:
                bounded=self._bounded_run_spot_closure(world,encounter,rng_role,self.rng_owner)
            except CheckpointRejected as exc:
                self.issue('bounded_run_spot_closure_refused',('encounter',encounter.id),'*',str(exc))
                bounded=None
            if bounded is not None:
                self.issue('bounded_run_spot_closure_verified',('encounter',encounter.id),'*',
                           'The exact native Run/Spot field, definition and alias subset passed; this is not checkpoint readiness.')
                body=body+(('bounded-run-spot-closure',bounded),)
        descriptions=[]
        for b in sorted(self.bindings,key=lambda b:(b.namespace,b.name)):
            ref=self.value(b.recipient,('host-recipient',world.id,b.namespace,b.name))
            if b.role=='in_world_belief_ledger':
                from observer_proposals import _capture_belief
                _capture_belief(b.recipient,b.observer_ids[0])
            descriptor=(b.namespace,b.name,b.role,b.observer_ids,ref)
            if self.full_native and self.compact_native_recipient_facts:
                from native_history import _recipient_binding_id
                descriptor += (_recipient_binding_id(
                    world,b.role,id(b.recipient)),)
            descriptions.append(descriptor)
        native_adapters = (ADAPTER_VERSION,
            *(('target-candidate-history/1',)
              if self.compact_native_target_history else ()),
            *(('entity-context-history/1',)
              if self.compact_native_entity_context else ()),
            *(('committed-receipt-facts/1',)
              if self.compact_native_receipt_facts else ()),
            *(('observer-recipient-facts/1',)
              if self.compact_native_recipient_facts else ()),
            *(('published-interval-facts/1',)
              if self.compact_native_publication_facts else ()),
            *(('disarm-landing-facts/1',)
              if self.compact_native_disarm_landings else ()),
            *(('committed-boundary-history/1',)
              if self.compact_native_boundary_history else ()))
        return body+(('native-adapters',*native_adapters),('host-bindings',tuple(descriptions)))
