"""Inactive 5D2A native data recipes and explicit host recipient bindings.

No serializer, restoration, callback invocation, RNG draw or world publication.
Recipes describe native reconstruction obligations; they do not execute them.
Complete checkpoint readiness remains refused by checkpoint_inventory.
"""
from dataclasses import dataclass
from types import FunctionType, MethodType, CodeType
import math

from checkpoint_inventory import _Inventory, _TYPES, _require, CheckpointRejected
from checkpoint_fields import FIELD_ADAPTERS
from conditional_attributes import ConditionalAttributes
import statistical_group
from statistical_group import StatisticalGroup, validate_composition_records
from personal_history import PersonalHistory
from realization import RealityLedger, CommittedFact, FactKey
from field_observation import BeliefLedger
from being import BeingInstance
from frozen_practice import _copy_use, _capture_history

ADAPTER_VERSION = 'native-closure-recipes/1'
_NATIVE_GROUP_RNG = StatisticalGroup._rng
_NATIVE_COMPOSITION_RNG = statistical_group.composition_rng
_NATIVE_GROUP_CONSTRAINT = StatisticalGroup._validate_composition_facts
_NATIVE_HISTORY_CONSTRAINT = PersonalHistory._validate
_NATIVE_ATTRIBUTE_LAMBDA = next(c for c in StatisticalGroup.__init__.__code__.co_consts
    if type(c) is CodeType and c.co_name == '<lambda>')


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

    def __init__(self, world, encounter, bindings):
        super().__init__()
        _require(type(bindings) is tuple, 'bindings must be an explicit tuple')
        self.world=world; self.encounter=encounter;self.bindings=bindings
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
            else: raise CheckpointRejected('unsupported recipient role')
            self.names.add(key);self.recipient_by_id[id(b.recipient)]=b
            self.anchor(b.recipient,('host-recipient',world.id,b.namespace,b.name))
        _require(not set(self.recipient_by_id).intersection(self.mutable_recipients),
                 'recipient binding aliases another recipient internal container')
        for obj in objects.values():
            if type(obj) is StatisticalGroup:
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
        if kind in (dict,list,set):
            _require(id(value) not in self.stack, 'unsupported mutable container cycle at '+ '/'.join(path))
        self.stack.add(id(value))
        try:return super().value(value,path,depth)
        finally:self.stack.discard(id(value))

    def field(self,tag,field,item,ref,path,depth):
        if tag=='action_choice._Accepted' and field=='signatures':
            from checkpoint_choices import describe_accepted_choice, ChoiceDescriptorRejected
            record=self._objects_by_identity.get(self._owner_identity(ref))
            try:
                descriptor=describe_accepted_choice(self.world,self.encounter,record.view.id)
                _require(self.encounter._choice_book._choices.get(record.view.id) is record,
                         'accepted-choice owner identity changed')
                return ('portable-choice-descriptor',descriptor.to_data())
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
            return ('reference',('host-recipient',self.world.id,b.namespace,b.name))
        if field in ('ledger','received_accounts') and tag in ('group_observation.ObserveGroupAction','history_conversation.AskAboutPastAction') and item is not None:
            b=self.recipient_by_id.get(id(item));action=self._objects_by_identity[self._owner_identity(ref)]
            role='in_world_belief_ledger' if field=='ledger' else 'in_world_received_accounts'
            _require(b is not None and b.role==role and action.actor_id in b.observer_ids,'missing or mismatched external recipient binding')
            return self.value(item,path+(field,),depth+1)
        return super().field(tag,field,item,ref,path,depth)

    def issue(self,code,owner,field,reason):
        if code=='semantic_closure_adapter_incomplete':
            reason=('Native recipes/closed field vocabulary do not yet prove complete definition semantics, '
                'all alias/reference roles, receipt reissuance or restoration. Complete and portable readiness remain refused in 5D2A.')
        super().issue(code,owner,field,reason)

    def _owner_identity(self,ref):
        return next(k for k,v in self.known.items() if v==ref)

    def _conditional(self,store,group):
        _require(type(store) is ConditionalAttributes,'conditional_attribute_adapter_missing: native store required')
        d=_fields(store)
        _data_tree(d['specifications']);_data_tree(d['_external']);_data_tree(d['_committed'])
        _data_tree(group._formation_traits)
        if group._formation_traits:
            self.issue('formation_trait_semantics_adapter_pending',('object',group.id),'_formation_traits',
                'Frozen quota/initial-skill data are preserved, but whole-cohort assignment and realization semantics have no complete checkpoint validation adapter; closure refused.')
        _require(type(d['_external']) is set and all(type(s)is str for s in d['_external'])
            and d['_external']==set(group._formation_traits.get('adults',{})), 'conditional external dependencies mismatch')
        # Native construction validates detached specifications only; it does not call rng_for.
        ConditionalAttributes(d['specifications'],None,d['_external'])
        _require(type(d['_committed']) is dict,'opaque conditional commitments')
        records=_ledger_records(group._composition_reality);facts={r.key:r.value for r in records}
        validate_composition_records(group.id,group.formation_time,records)
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
                    cdfs=list(spec['conditional_cdfs'].values())
                    self.issue('conditional_external_assignment_validation_pending',('object',group.id),name,
                        'Committed external quota assignment is keyed/derived, not stored; no draws permitted during capture. Recipe preserves dependencies but full branch-membership proof remains refused.')
                else:
                    _require(parent in values,'missing committed conditional parent')
                    p=values[parent]; branch=('true' if p else 'false') if type(p)is bool else str(p)
                    _require(branch in spec['conditional_cdfs'],'missing conditional parent branch');cdfs=[spec['conditional_cdfs'][branch]]
                _require(any(type(v)is type(value) and v==value for cdf in cdfs for v,_ in cdf),'impossible committed conditional value')

    def build(self,world,encounter,rng_role,rng_state,rng_scope):
        _require(rng_scope=='exclusive_encounter' and rng_role in ('caller_cursor','native_random'), 'native adapters require explicit private RNG authority')
        self._objects_by_identity={}
        body=super().build(world,encounter,rng_role,rng_state,rng_scope)
        descriptions=[]
        for b in sorted(self.bindings,key=lambda b:(b.namespace,b.name)):
            ref=self.value(b.recipient,('host-recipient',world.id,b.namespace,b.name))
            if b.role=='in_world_belief_ledger':
                from observer_proposals import _capture_belief
                _capture_belief(b.recipient,b.observer_ids[0])
            descriptions.append((b.namespace,b.name,b.role,b.observer_ids,ref))
        return body+(('native-adapters',ADAPTER_VERSION),('host-bindings',tuple(descriptions)))
