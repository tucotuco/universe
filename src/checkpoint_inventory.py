"""Inactive D7 checkpoint closure inventory, NOT a save or resumable checkpoint.

Current completeness is deliberately refused: this field inventory is not a
reviewed semantic/rehydration adapter for every native field. It preserves data
and reports gaps rather than advertising a partial graph as a complete save.
No file output, Action evaluation, publication, restoration or replay occurs.
"""
from dataclasses import dataclass, fields
import hashlib
import importlib
import json
import math
import sys
from pathlib import Path
from types import MappingProxyType
import weakref

SCHEMA = 'universe.checkpoint-inventory-draft/1'
_AUTHORITATIVE_DECISIONS_PATH = (
    Path(__file__).resolve().parent.parent
    / 'docs/history/universe4-authoritative-decisions-2026-10-27.md'
)


class CheckpointRejected(ValueError):
    pass


def owned_node_ref(path):
    """Compact stable checkpoint-local ID for a synthetic graph node."""
    encoded=json.dumps(path,ensure_ascii=True,separators=(',',':'))
    return ('owned-node',hashlib.sha256(encoded.encode('ascii')).hexdigest())


@dataclass(frozen=True)
class CheckpointDiagnostic:
    code: str
    owner: tuple
    field: str
    reason: str


@dataclass(frozen=True)
class CheckpointCandidate:
    schema: str
    envelope: tuple
    diagnostics: tuple
    content_digest: str
    closure_validated: bool = False
    portable_schema_defined: bool = False
    restore_verified: bool = False


@dataclass(frozen=True)
class CheckpointValidation:
    inventory_validated: bool
    diagnostics: tuple
    closure_validated: bool = False
    portable_schema_defined: bool = False
    restore_verified: bool = False

    def require_complete(self):
        raise CheckpointRejected('checkpoint closure is incomplete; inspect diagnostic codes; no restore support')


_ISSUED = {}  # Same-process validation only; excluded from the candidate.
_CATALOG = {
    'universe':'Universe', 'encounter':'Encounter EncounterInitiation ArenaActionActivation ArenaMovementActivation', 'event':'Event',
    'action':'Action', 'activities':'RunAction SpotAction ThrowAction PickUpAction ReadyWeaponAction ShieldEquipmentAction ReadyPreparationAction DelayAction', 'melee_combat':'MeleeStrike MeleeResult',
    'melee_defense':'MeleeDefense', 'group_observation':'ObserveGroupAction SampledGroupObservation',
    'history_conversation':'AskAboutPastAction HeardAccount',
    'being':'BeingInstance BeingDefinition BeingDictionary',
    'object':'ObjectInstance ObjectDefinition ObjectRegistry ObjectDictionary',
    'weapon':'WeaponInstance WeaponDefinition WeaponDictionary',
    'armor':'ArmorInstance ArmorDefinition ArmorDictionary', 'statistical_group':'GroupMember MembershipChange StatisticalGroup',
    'conditional_attributes':'ConditionalAttributes',
    'library':'Library', 'actiondictionary':'ActionDictionary ActionDefinition',
    'skill':'SkillDictionary SkillDefinition Skills', 'abilities':'Abilities', 'states':'States',
    'speeds':'Speed', 'strategy':'Strategy', 'exertion':'Exertion',
    'spatial.state':'SpatialState CartesianPosition', 'spatial.frame':'LocalFrame',
    'location_observation':'LocationEvidenceLedger BeingLocationObservation LastSeenLocation',
    'object_observation':'ObjectObservation ObjectObservationLedger',
    'spatial.geometry':'Sphere AxisAlignedBox', 'spatial.occlusion':'VisualOcclusion',
    'physical_fatigue':'PhysicalFatigueState',
    'arena_perception':'ArenaPerceptionLedger ArenaPerceptionEvidence',
    'physiology_registry':'PhysiologyRegistry PhysiologyDefinition ResolvedPhysiology',
    'universe_physical_fatigue_r4':'Profile',
    'encounter_fatigue_bridge':'FrozenFatigueFrame FrozenFatigueView',
    'throwing':'ProjectileFlight ProjectileBoundaryState',
    'personal_history':'PersonalHistory', 'realization':'RealityLedger FactKey CommittedFact Fact',
    'field_observation':'BeliefLedger FieldObservation CountReport BeliefRevision EvidenceReassessment InquiryProposal InquiryRecord',
    'field_interpretation':'FieldInterpreter FieldInterpretation',
    'experience':'SkillUse BatchSkillUse ActionResolution SkillExercise', 'frozen_practice':'CandidatePracticeUse CandidateSkillTransition PracticeProjection',
    'objective_reality':'EpisodeFacts DeclaredObjectiveFact ObjectiveFact SubjectRealityCandidate',
    'action_choice':'ChoiceBook ChoiceView ChoiceMember ChoiceDraft _Accepted Reservation',
    'scheduling':'PreparedSchedule', 'action_settlement':'TargetCandidate',
    'atomic_publication':'PublishedInterval TargetIntervalRecord ObjectiveCommitProvenance',
    'encounter_inspection':'CommittedBoundaryRecord EntityInspection DisarmLandingReceipt',
    'action_evaluation':'ActionView ActionProposal DamageEffect ProtectionEffect FatalEffect PracticeEffect AwarenessEffect DefenseEffect DelayDefenseEffect ProjectileReleaseEffect EffectIdentity IdentifiedEffect PickupEffect ReadyWeaponEffect ShieldEquipmentEffect ReadyPreparationEffect ReadyConsumptionEffect DropObjectEffect DisarmTakeEffect DisarmLandingPendingEffect GrappleStateEffect PositionEffect ObjectGripEffect StunEffect SubdualEffect',
    'observer_proposals':'RecipientIdentity ObservationEffect InterpretationEffect BeliefAcquisitionEffect LocationObservationEffect ObjectObservationEffect TestimonyEffect AccountDeliveryEffect ActionOutcomeEffect LifecycleEffect ReservationReleaseEffect PostCommitNotificationIntent ObserverProjection BeliefProjection AccountsProjection LocationEvidenceProjection ObjectEvidenceProjection FrozenLocationEvidence ObjectiveUse',
    'interval_staging':'AuthorityReference StartFence RegistrationIntent QueueProjection',
}
_TYPES = frozenset(vars(importlib.import_module(module))[name]
    for module,names in _CATALOG.items() for name in names.split())


def _require(test, message):
    if not test:
        raise CheckpointRejected(message)


def _closed(value):
    if value is None or type(value) in (str,bool,int):return value
    if type(value) is tuple:return tuple(_closed(v) for v in value)
    raise CheckpointRejected('non-data or modified inventory envelope')


def _digest(value):
    return hashlib.sha256(json.dumps(_closed(value),ensure_ascii=True,separators=(',',':')).encode('ascii')).hexdigest()


def _compatibility():
    root=Path(__file__).resolve().parent
    implementation=tuple((p.relative_to(root).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest())
        for p in sorted(root.rglob('*.py')) if '__pycache__' not in p.parts)
    kernels=('action_calculations.py','action_evaluation.py','action_settlement.py','frozen_practice.py',
        'checkpoint_choices.py',
        'objective_reality.py','observer_proposals.py','scheduling.py','interval_staging.py','atomic_publication.py','transactional_progression.py',
        'conditional_attributes.py','statistical_group.py','personal_history.py','experience.py',
        'arena_perception.py','checkpoint_arena_perception.py',
        'field_interpretation.py','field_observation.py','location_observation.py',
        'group_observation.py','history_conversation.py')
    return ('compatibility-draft',SCHEMA,('implementation-source',_digest(implementation)),
        ('rule-kernel-source',_digest(tuple(row for row in implementation if row[0] in kernels))),
        ('authoritative-decisions',hashlib.sha256(_AUTHORITATIVE_DECISIONS_PATH.read_bytes()).hexdigest()),
        ('python-runtime',sys.implementation.name,tuple(sys.version_info)),('numeric','IEEE754-binary64-hex'),
        ('python-native-rng','MT19937-state-v3'),('restore-adapters','not-implemented'))


class _Inventory:
    types = _TYPES
    def __init__(self):
        self.known={};self.nodes=[];self.dependencies=[];self.diagnostics=[];self.count=0
        self._owned_path_digests={}

    def _owned_ref(self, path):
        """Return a compact, deterministic identity for a non-domain graph node.

        Domain identities (Universe, Encounter, Event, Object and Choice IDs)
        remain explicit. A traversal path is only a checkpoint-local node
        identity; serializing the whole path into every edge made historical
        snapshots grow with the product of history length and path length.
        """
        ref=owned_node_ref(path)
        digest=ref[1]
        previous=self._owned_path_digests.setdefault(digest,path)
        _require(previous==path,'checkpoint graph node identity digest collision')
        return ref

    def issue(self,code,owner,field,reason):
        self.diagnostics.append(CheckpointDiagnostic(code,owner,field,reason))

    def anchor(self,value,ref):
        old=self.known.get(id(value))
        _require(old is None or old==ref,'aliased or duplicate native logical identity')
        self.known[id(value)]=ref

    def value(self,value,path,depth=0):
        _require(depth<=100,'inventory graph depth limit exceeded')
        kind=type(value)
        if value is None:return ('null',)
        if kind is bool:return ('boolean',value)
        if kind is str:return ('string',value)
        if kind is int:return ('integer',str(value))
        if kind is float:
            _require(math.isfinite(value),'non-finite native inventory data')
            return ('binary64',value.hex())
        existing=self.known.get(id(value))
        if existing is not None and id(value) in self.emitted:return ('reference',existing)
        # Bound allocated graph nodes, not the number of scalar field visits.
        # Repeated historical string values are losslessly interned by the
        # strict wire encoder; counting their pre-encoding appearances here
        # rejected checkpoints that fit both persisted admission limits.
        self.count+=1
        _require(self.count<=250000,'inventory graph node limit exceeded')
        ref=existing if existing is not None else self._owned_ref(path)
        self.known[id(value)]=ref;self.emitted.add(id(value));self.dependencies.append((id(value),id(kind)))
        if kind in (dict,MappingProxyType):
            _require(all(type(k) in (str,int,float,bool,tuple) or type(k) in _TYPES for k in value),'opaque mapping key')
            items=tuple((self.value(k,path+('key',str(i)),depth+1),self.value(v,path+('entry',str(i)),depth+1)) for i,(k,v) in enumerate(value.items()))
            node=(ref,'ordered-map',items)
        elif kind in (list,tuple,set,frozenset):
            if kind in (set,frozenset):
                _require(all(type(v) in (str,int,bool) for v in value),'unsupported unordered native record')
                values=sorted(value,key=lambda v:(type(v).__name__,str(v)))
            else:values=value
            node=(ref,kind.__name__,tuple(self.value(v,path+('item',str(i)),depth+1) for i,v in enumerate(values)))
        elif kind in self.types:
            data=object.__getattribute__(value,'__dict__')
            _require(type(data) is dict and all(type(k)is str for k in data),'opaque native field storage')
            tag=kind.__module__+'.'+kind.__name__;parts=[]
            for field,item in sorted(data.items()):
                projected=self.field(tag,field,item,ref,path,depth)
                parts.append((field,projected))
            # Restore initializes this append-only receipt list for pristine
            # Encounters even before the first transactional boundary. Make
            # its empty value explicit in the canonical inventory from the
            # initial save so immediate fresh-process Save remains stable.
            if tag == 'encounter.Encounter' and '_atomic_interval_history' not in data:
                self.count += 1
                _require(self.count <= 250000,'inventory graph node limit exceeded')
                history_ref = self._owned_ref(path+('_atomic_interval_history',))
                self.nodes.append((history_ref,'list',()))
                parts.append(('_atomic_interval_history',('reference',history_ref)))
                parts.sort(key=lambda row: row[0])
            if tag == 'encounter.Encounter':
                for transient_field in ('_transactional_mode', '_active_fatigue_frame',
                                        '_boundary_context', '_advancing', '_running',
                                        '_dispatching'):
                    if transient_field not in data:
                        parts.append((transient_field,
                            ('excluded-transient', transient_field)))
                parts.sort(key=lambda row: row[0])
            node=(ref,tag,tuple(parts))
        else:
            # No property, serializer, repr or callback from an extension runs.
            self.issue('unsupported_native_value',ref,'value','No reviewed data adapter for this field value; closure refused.')
            node=(ref,'unsupported',())
        self.nodes.append(node)
        return ('reference',ref)

    def field(self,tag,field,item,ref,path,depth):
        if tag=='universe.Universe' and field=='_reproduction_group_registry':
            from reproduction_group import ReproductionGroupRegistry
            _require(type(item) is ReproductionGroupRegistry
                     and item._world is self._capture_world,
                     'ReproductionGroup registry is not bound to the captured Universe')
            _require(item._revision==0 and not item._groups_by_id
                     and not item._group_id_by_parent_set and not item._group_id_by_offspring
                     and not item._parent_set_by_offspring and not item._person_id_reservations
                     and not item._group_id_reservations and not item._requests,
                     'published ReproductionGroup state is outside the native Run/Spot checkpoint subset')
            return ('excluded-out-of-scope-empty-registry',0)
        transient={
            'universe.Universe':{'_schedule_lock'},
            'action_choice.ChoiceBook':{'lock','_drafts','_closed_drafts','_tokens'},
            'encounter.Encounter':{'_transactional_mode','_active_fatigue_frame','_boundary_context','_advancing','_running','_dispatching'},
        }
        if field in transient.get(tag,set()):return ('excluded-transient',field)
        if tag=='action_choice._Accepted' and field=='signatures':
            self.issue('native_signature_rebuild_required',ref,field,'declaration() contains class/Object addresses; semantic adapter and signature revalidation required.')
            return ('derived-rebuild-required','declaration-signatures')
        if tag=='action_choice.ChoiceBook' and field=='_registered':
            _require(type(item)is dict,'unsupported registration mapping')
            return ('registration-index',tuple((aid,self.value(row[0],path+(field,aid,'choice'),depth+1),
                self.value(row[1],path+(field,aid,'packet'),depth+1),('derived-rebuild-required','declaration-signature'))
                for aid,row in item.items()))
        if tag=='encounter_inspection.CommittedBoundaryRecord' and field in ('target_anchors','action_anchors'):
            self.issue('receipt_rebinding_required',ref,field,'Native identity/digest anchors require new authenticated identity-preserving issuance on restore.')
            return ('derived-rebuild-required',field)
        if tag=='objective_reality.SubjectRealityCandidate' and field=='ledger_identity':
            return ('derived-rebuild-required','subject-owned-ledger')
        if tag=='interval_staging.AuthorityReference' and field=='identity':return ('derived-rebuild-required','native-reference-identity')
        if tag=='observer_proposals.RecipientIdentity' and field=='object_identity':
            self.issue('unbound_recipient_identity',ref,field,'Recipient identity is id(handle), not a durable owned binding.')
            return ('unsupported-reference','external-recipient')
        if tag=='statistical_group.StatisticalGroup' and field=='_conditional_attributes':
            self.issue('conditional_attribute_adapter_missing',ref,field,'ConditionalAttributes owns committed formation-attribute data and a lambda-backed keyed RNG provider; no reviewed detached/rehydration adapter exists in this inventory.')
        if field == 'location_ledger' and item is not None and tag == 'activities.SpotAction':
            self.issue('unbound_location_evidence_recipient',ref,field,
                       'Observer-owned location evidence recipient has no portable binding contract; fail closed.')
            return ('unsupported-reference','observer-location-evidence')
        if field in ('ledger','received_accounts') and item is not None and tag in ('group_observation.ObserveGroupAction','history_conversation.AskAboutPastAction','activities.SpotAction'):
            self.issue('unbound_external_recipient',ref,field,'Caller-owned recipient is not registered with a durable Universe ownership/binding contract.')
        if tag=='realization.RealityLedger' and field=='_validators':
            self.issue('validator_rehydration_required',ref,field,'Executable constraint callbacks cannot be captured; a reviewed owner/type adapter must reconstruct and validate constraints.')
            # Include dependencies privately for stale detection, never callbacks in data.
            self.dependencies.append(('validators',id(item),tuple(id(v) for v in item)))
            return ('unsupported-reference','constraint-rebinding')
        return self.value(item,path+(field,),depth+1)

    def build(self,world,encounter,rng_role,rng_state,rng_scope):
        self._capture_world=world
        self.emitted=set()
        self.anchor(world,('universe',world.id));self.anchor(encounter,('encounter',encounter.id))
        for key,obj in world.object_registry.object_instances.items():self.anchor(obj,('object',key))
        for key,event in world.event_history.items():
            if event is not encounter:self.anchor(event,('event',key))
        for cid,record in encounter._choice_book._choices.items():
            self.anchor(record,('choice',encounter.id,cid))
            for member in record.members:
                # Published and unpublished Actions share the same Event role.
                self.anchor(member.action,('event',member.action.id))
        root=self.value(world,('universe',world.id))
        self.issue('semantic_closure_adapter_incomplete',('universe',world.id),'*',
            'Structural native field inventory is not complete semantic closure certification: unknown added fields, global aliases, all dictionary definitions and rehydration dependencies need reviewed field adapters. No candidate is resumable in 5D1.')
        if rng_scope is None or rng_role=='module':
            self.issue('rng_authority_scope_unbound',('encounter',encounter.id),'rng',
                'Module/shared or undeclared RNG authority has no durable ownership closure; one Encounter RNG state alone cannot resume unrelated users.')
        return ('checkpoint-inventory',('root',root),('nodes',tuple(self.nodes)),
            ('rng',rng_role,rng_scope,_rng_data(rng_state)),('readiness',False,False,False))


def _rng_data(value):
    if type(value)is tuple:return ('tuple',tuple(_rng_data(v) for v in value))
    if value is None:return ('null',)
    if type(value)is int:return ('integer',str(value))
    if type(value)is float and math.isfinite(value):return ('binary64',value.hex())
    raise CheckpointRejected('unsupported native RNG state')


def _validate_native_companion_encounters(world, selected, selected_rng_owner):
    """Validate every registered Encounter as independently resumable state."""
    from encounter import Encounter
    from encounter_inspection import _idle
    from interval_staging import _preflight, _rng_input
    from transactional_progression import (_BINDINGS, _all_declarations,
                                           mode_of)
    events = world.event_history
    encounters = [event for event in events.values() if type(event) is Encounter]
    books = world.__dict__.get('_choice_books')
    _require(type(books) is list
             and len(books) == len(encounters)
             and len({id(book) for book in books}) == len(books)
             and {id(book) for book in books}
                 == {id(event._choice_book) for event in encounters},
             'Universe Encounter/ChoiceBook ownership registry differs')
    _require(selected in encounters and events.get(selected.id) is selected,
             'selected native Encounter is missing from the Universe registry')
    owners = set()
    for saved in encounters:
        book = saved._choice_book
        _require(type(book.encounter) is Encounter and book.encounter is saved,
                 'Encounter ChoiceBook owner differs')
        binding = _BINDINGS.get(id(saved))
        bound_owner = (binding.rng_owner if binding is not None
                       and binding.encounter() is saved else None)
        owner = ((selected_rng_owner or bound_owner) if saved is selected
                 else bound_owner)
        mode = mode_of(saved)
        _require(owner is not None and mode == 'transactional',
                 'every registered Encounter requires an independently bound native RNG: '
                 + saved.id + ' (' + mode + ')')
        role, identity, _state = _rng_input(saved, None, owner)
        _require(role in ('caller_cursor', 'native_random')
                 and identity not in owners,
                 'each registered Encounter requires a distinct private RNG owner')
        owners.add(identity)
        _idle(saved)
        if saved is not selected:
            _preflight(saved, saved.last_processed_boundary + 1)
            book.assert_accepted()
            _all_declarations(saved, saved.last_processed_boundary + 1, owner)


def _candidate_seal(candidate):
    _require(type(candidate) is CheckpointCandidate,'native inventory candidate required')
    _require(candidate.closure_validated is False and candidate.portable_schema_defined is False
        and candidate.restore_verified is False,'unsupported checkpoint readiness claim')
    _require(type(candidate.schema) is str and candidate.schema==SCHEMA and type(candidate.content_digest)is str,'unsupported inventory schema')
    _require(type(candidate.diagnostics) is tuple and all(type(d)is CheckpointDiagnostic for d in candidate.diagnostics),'unsupported diagnostics')
    diagnostics=tuple(tuple(object.__getattribute__(d,'__dict__')[f.name] for f in fields(CheckpointDiagnostic)) for d in candidate.diagnostics)
    return _digest((candidate.schema,candidate.envelope,diagnostics,candidate.content_digest,False,False,False))


def _capture(world,encounter,*,quiescent,rng_scope,native_adapters=False,
             bindings=(),rng_owner=None,full_native=False,
             compact_native_target_history=False):
    from universe import Universe
    from encounter import Encounter
    from transactional_progression import _BINDINGS,_all_declarations
    from encounter_inspection import _idle
    from atomic_publication import coordinated_access
    from interval_staging import _preflight,_rng_input,_read_set
    from transactional_progression import is_quarantined
    if is_quarantined(encounter):
        from checkpoint_restore_preparation import _movement_checkpoint_capture_is_authorized
        _require(_movement_checkpoint_capture_is_authorized(world, encounter),
                 'quarantined movement checkpoint capture is restoration-owner controlled')
    _require(type(native_adapters) is bool, 'native_adapters must be a bool')
    _require(type(full_native) is bool and (not full_native or native_adapters),
             'full_native requires the reviewed native adapter mode')
    _require(type(compact_native_target_history) is bool
             and (not compact_native_target_history
                  or native_adapters and full_native),
             'compact native Target history requires the full native adapter mode')
    _require(type(bindings) is tuple, 'bindings must be an explicit tuple')
    _require(native_adapters or bindings == (), 'bindings require explicit native adapter mode')
    _require(quiescent is True,'explicit quiescent/coordinated read ownership is required')
    _require(rng_scope is None or type(rng_scope)is str and rng_scope=='exclusive_encounter', 'unsupported RNG scope assertion')
    _require(type(world) is Universe and type(encounter) is Encounter,'native Universe/Encounter roots required')
    _require(object.__getattribute__(encounter,'__dict__')['universe'] is world,'foreign Encounter root')
    with coordinated_access(world):
        pristine_arena=(encounter.arena_activation_enabled is True
            and encounter.initiated is False and encounter.time==encounter.start_time
            and not encounter.__dict__.get('_atomic_interval_history')
            and not encounter.pending_action_list
            and not encounter.finished_action_list and not encounter.cancelled_action_list
            and not encounter._choice_book._choices and not encounter._choice_book._drafts
            and not encounter._choice_book._registered)
        if pristine_arena:
            import atomic_publication as publication
            _require(not publication._ACTIVE and not publication._PUBLISHING
                     and not any(encounter.__dict__.get(key) for key in
                         ('_advancing','_dispatching','_running'))
                     and encounter.__dict__.get('boundary_fault') is None,
                     'pristine Arena capture requires idle native scheduling/publication')
        else:
            _idle(encounter)
        _require(world.event_history.get(encounter.id)is encounter,'Encounter registry identity changed')
        if full_native and native_adapters:
            _validate_native_companion_encounters(world, encounter, rng_owner)
        else:
            _require(len(world._choice_books)==1,
                     'multi-Encounter closure has no reviewed ownership adapter')
        _require(encounter.end_time is None or encounter.time<encounter.end_time,
                 'terminal Encounter checkpoint predicate is not adapted; no next-boundary preflight is possible')
        before_source=_compatibility();before=_read_set(encounter)
        binding=_BINDINGS.get(id(encounter))
        owner=(binding.rng_owner if binding is not None and binding.encounter() is encounter
               else rng_owner)
        _require(owner is not None,
                 'unbound Encounter checkpoint requires an explicitly supplied private RNG cursor')
        if binding is None or binding.encounter() is not encounter:
            _require(pristine_arena,
                     'only a pristine unactivated Arena may supply its session-owned RNG cursor')
        unactivated_arena=pristine_arena
        if not unactivated_arena:
            _preflight(encounter,encounter.last_processed_boundary+1)
        encounter._choice_book.assert_accepted()
        if not unactivated_arena:
            _all_declarations(encounter,encounter.last_processed_boundary+1,owner)
        if encounter.time!=encounter.start_time or encounter.__dict__.get('_atomic_interval_history'):
            encounter.inspect_committed()
        for aid,event in world.event_history.items():
            _require(type(aid)is str and type(event) in _TYPES and object.__getattribute__(event,'__dict__').get('id')==aid,'unsupported or inconsistent Event registry')
        for key,obj in world.object_registry.object_instances.items():
            _require(type(key)is str and type(obj) in _TYPES and object.__getattribute__(obj,'__dict__').get('id')==key,'unsupported or inconsistent Object registry')
        role,identity,rng=_rng_input(encounter,None,owner)
        if rng_scope=='exclusive_encounter':
            _require(role in ('caller_cursor','native_random'),'module/shared RNG cannot be asserted Encounter-private')
            _require(not any(b.encounter() is not encounter and b.encounter() is not None and b.rng_owner is owner for b in _BINDINGS.values()),'RNG is shared with another Encounter')
        if native_adapters:
            from checkpoint_adapters import NativeInventory
            inventory=NativeInventory(world,encounter,bindings,rng_owner=owner,
                                      full_native=full_native,
                                      compact_native_target_history=compact_native_target_history)
        else:
            inventory=_Inventory()
        body=inventory.build(world,encounter,role,rng,rng_scope)
        # Include RNG nodes appended after world traversal.
        body=tuple(('nodes',tuple(inventory.nodes)) if type(row)is tuple and row and row[0]=='nodes' else row for row in body)
        envelope=(before_source,body)
        _require(before==_read_set(encounter) and before_source==_compatibility()
            and (role,identity,rng)==_rng_input(encounter,None,owner),'state or compatibility inputs changed during read')
        stamp=(before,tuple(inventory.dependencies),identity)
        return envelope,tuple(inventory.diagnostics),stamp


def capture_checkpoint_candidate(world,encounter,*,quiescent=False,rng_scope=None,
        native_adapters=False,bindings=(),rng_owner=None,full_native=False,
        compact_native_target_history=False):
    """Return an inactive partial inventory; all readiness flags remain false.

    rng_scope is an explicit caller assertion, not evidence of global privacy.
    No binding IDs are invented for externally owned recipients.
    """
    envelope,diagnostics,stamp=_capture(world,encounter,quiescent=quiescent,
        rng_scope=rng_scope,native_adapters=native_adapters,bindings=bindings,
        rng_owner=rng_owner,full_native=full_native,
        compact_native_target_history=compact_native_target_history)
    candidate=CheckpointCandidate(SCHEMA,envelope,diagnostics,_digest(envelope))
    key=id(candidate)
    _ISSUED[key]=(weakref.ref(candidate,lambda ref,key=key:_ISSUED.pop(key,None)),
        weakref.ref(world),weakref.ref(encounter),stamp,_candidate_seal(candidate),
        rng_scope,native_adapters,bindings,full_native,
        compact_native_target_history)
    return candidate


def validate_checkpoint_candidate(world,encounter,candidate,*,quiescent=False):
    """Validate in-process inventory provenance/freshness, never restore readiness."""
    issued=_ISSUED.get(id(candidate))
    _require(issued is not None and issued[0]()is candidate and issued[1]()is world and issued[2]()is encounter,'foreign, copied or non-issued inventory candidate')
    _require(_candidate_seal(candidate)==issued[4] and candidate.content_digest==_digest(candidate.envelope),'modified inventory candidate')
    envelope,diagnostics,stamp=_capture(world,encounter,quiescent=quiescent,
        rng_scope=issued[5],native_adapters=issued[6],bindings=issued[7],
        full_native=issued[8],compact_native_target_history=issued[9])
    _require(stamp==issued[3] and envelope==candidate.envelope and diagnostics==candidate.diagnostics,'stale checkpoint inventory; recapture after correction')
    return CheckpointValidation(not any(d.code=='unsupported_native_value' for d in diagnostics),diagnostics)
