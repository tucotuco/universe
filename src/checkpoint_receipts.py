"""Inactive portable descriptors for a small native committed-receipt chain.

This module describes authenticated in-memory receipts. It never issues,
registers, restores, publishes, or replays receipts.
"""
from dataclasses import dataclass, fields, is_dataclass, replace
import hashlib
import json
import math
from types import MappingProxyType

from action_evaluation import (ActionProposal, AwarenessEffect, EffectIdentity,
    IdentifiedEffect, PracticeEffect, native_data)
from checkpoint_choices import (ChoiceDescriptorRejected, describe_accepted_choice,
    _number)


DESCRIPTOR_SCHEMA = 'universe.committed-native-receipt-chain/1'
REBINDING_SCHEMA = 'universe.committed-native-rebinding-plan/1'
MOVEMENT_ONLY_BOUNDARY_SCHEMA = 'universe.committed-movement-only-boundary/1'
CONTINUING_MOVEMENT_BOUNDARY_SCHEMA = 'universe.committed-movement-only-boundary/2'


class ReceiptDescriptorRejected(ValueError):
    """The committed history is outside the exact portable subset."""


@dataclass(frozen=True)
class PortableCommittedAction:
    action_id: str
    adapter: str
    actor_id: str
    target_id: str | None
    start: tuple
    end: tuple
    declaration: tuple
    outcome: str
    metadata: tuple
    effect_ids: tuple

    def to_data(self):
        return (self.action_id, self.adapter, self.actor_id, self.target_id,
            self.start, self.end, self.declaration, self.outcome,
            self.metadata, self.effect_ids)


@dataclass(frozen=True)
class PortableTargetRecord:
    target_id: str
    category: str
    position: object
    state: tuple

    def to_data(self):
        return (self.target_id, self.category, self.position, self.state)


@dataclass(frozen=True)
class PortableBoundaryReceipt:
    boundary: int
    start: tuple
    action_ids: tuple
    effect_ids: tuple
    actions: tuple
    effects: tuple
    targets: tuple
    start_fences: tuple
    rng_after: tuple

    def to_data(self):
        return (self.boundary, self.start, self.action_ids, self.effect_ids,
            tuple(row.to_data() for row in self.actions),
            self.effects,
            tuple(row.to_data() for row in self.targets), self.start_fences,
            self.rng_after)


@dataclass(frozen=True)
class PortableMovementOnlyBoundaryReceipt:
    """Closed Target/RNG receipt for the initial target-free Arena movement."""

    schema: str
    boundary: int
    start: tuple
    participant_ids: tuple
    targets: tuple
    start_fences: tuple
    rng_after: tuple

    @property
    def action_ids(self):
        return ()

    def to_data(self):
        return (self.schema, self.boundary, self.start, self.participant_ids,
            tuple(row.to_data() for row in self.targets), self.start_fences,
            self.rng_after)


@dataclass(frozen=True)
class PortableContinuingMovementBoundaryReceipt:
    """A later Action-free movement boundary following the initial activation."""

    schema: str
    boundary: int
    start: tuple
    participant_ids: tuple
    targets: tuple
    start_fences: tuple
    rng_after: tuple

    @property
    def action_ids(self):
        return ()

    def to_data(self):
        return (self.schema, self.boundary, self.start, self.participant_ids,
            tuple(row.to_data() for row in self.targets), self.start_fences,
            self.rng_after)


@dataclass(frozen=True)
class PortableCommittedChoice:
    choice_id: str
    version: int
    origin: str
    action_ids: tuple

    def to_data(self):
        return (self.choice_id, self.version, self.origin, self.action_ids)


@dataclass(frozen=True)
class PortableReceiptChain:
    schema: str
    universe_id: str
    encounter_id: str
    start_time: tuple
    receipts: tuple
    committed_choices: tuple
    accepted_future_choices: tuple
    rng_ownership: tuple

    def to_data(self):
        validate_receipt_descriptor(self)
        return _receipt_data(self)

    @property
    def content_digest(self):
        raw=json.dumps(self.to_data(),ensure_ascii=False,separators=(',',':'))
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class ReceiptRebindingPlan:
    schema: str
    descriptor_digest: str
    universe_id: str
    encounter_id: str
    entity_ids: tuple
    action_ids: tuple
    choice_ids: tuple
    boundaries: tuple
    steps: tuple

    def to_data(self):
        _closed(self, ReceiptRebindingPlan)
        if self.schema != REBINDING_SCHEMA:
            raise ReceiptDescriptorRejected('unknown rebinding-plan version')
        return (self.schema,self.descriptor_digest,self.universe_id,self.encounter_id,
            self.entity_ids,self.action_ids,self.choice_ids,self.boundaries,self.steps)


_STEPS = (
    'select-compatible-rules-and-adapter-versions',
    'allocate-native-universe-encounter-and-entities',
    'bind-each-logical-entity-action-and-choice-id-uniquely',
    'reconstruct-only-whitelisted-run-spot-declarations',
    'validate-target-owned-practice-and-chronological-receipt-chain',
    'rebuild-choice-book-and-private-rng-cursor-under-exclusive-ownership',
    'regenerate-target-action-and-storage-anchors-from-rebound-objects',
    'authenticate-and-register-fresh-receipts-only-after-complete-validation',
)


def _closed(value, cls):
    if type(value) is not cls or not is_dataclass(value):
        raise ReceiptDescriptorRejected(f'unknown {cls.__name__} type')
    names={f.name for f in fields(cls)}
    if set(object.__getattribute__(value,'__dict__')) != names:
        raise ReceiptDescriptorRejected(f'unknown {cls.__name__} fields')
    return object.__getattribute__(value,'__dict__')


def _finite(value, label):
    if type(value) not in (int,float) or (type(value) is float and not math.isfinite(value)):
        raise ReceiptDescriptorRejected(f'{label} must be an exact finite number')
    return _number(value,label)


def _decoded_number(value,label):
    if type(value) is not tuple or len(value)!=2:
        raise ReceiptDescriptorRejected(f'{label} has no exact numeric encoding')
    if value[0]=='integer' and type(value[1]) is str:
        try:result=int(value[1])
        except ValueError as exc:raise ReceiptDescriptorRejected(f'{label} integer encoding is invalid') from exc
        if str(result)!=value[1]:raise ReceiptDescriptorRejected(f'{label} integer encoding is not canonical')
        return result
    if value[0]=='binary64' and type(value[1]) is str:
        try:result=float.fromhex(value[1])
        except ValueError as exc:raise ReceiptDescriptorRejected(f'{label} float encoding is invalid') from exc
        if not math.isfinite(result) or result.hex()!=value[1]:raise ReceiptDescriptorRejected(f'{label} float encoding is noncanonical or nonfinite')
        return result
    raise ReceiptDescriptorRejected(f'{label} has an unknown numeric tag')


def _validate_encoded(value):
    """Validate the recursively tagged subset emitted by _value()."""
    if type(value) is not tuple or not value or type(value[0]) is not str:
        raise ReceiptDescriptorRejected('untagged receipt data value')
    tag=value[0]
    if tag=='null':
        if len(value)!=1:raise ReceiptDescriptorRejected('invalid null data tag')
    elif tag=='boolean':
        if len(value)!=2 or type(value[1]) is not bool:raise ReceiptDescriptorRejected('invalid boolean data tag')
    elif tag=='string':
        if len(value)!=2 or type(value[1]) is not str:raise ReceiptDescriptorRejected('invalid string data tag')
    elif tag in ('integer','binary64'):_decoded_number(value,'receipt number')
    elif tag=='effect-id':
        if (len(value)!=6 or type(value[1]) is not str or type(value[2]) is not int
                or type(value[3]) is not str or value[4] not in ('effect','defense','lifecycle')
                or type(value[5]) is not int or value[5]<0):raise ReceiptDescriptorRejected('invalid portable effect identity')
    elif tag in ('sequence','set'):
        if len(value)!=2 or type(value[1]) is not tuple:raise ReceiptDescriptorRejected('invalid sequence data tag')
        for row in value[1]:_validate_encoded(row)
    elif tag=='mapping':
        if len(value)!=2 or type(value[1]) is not tuple:raise ReceiptDescriptorRejected('invalid mapping data tag')
        keys=[]
        for row in value[1]:
            if type(row) is not tuple or len(row)!=2 or type(row[0]) is not str:raise ReceiptDescriptorRejected('invalid mapping entry')
            keys.append(row[0]);_validate_encoded(row[1])
        if keys!=sorted(set(keys)):raise ReceiptDescriptorRejected('mapping keys are duplicate or unordered')
    else:
        known={tag:cls for cls,tag in _records().items()}
        cls=known.get(tag)
        if cls is None:raise ReceiptDescriptorRejected('unknown data-record version '+tag)
        if len(value)!=2 or type(value[1]) is not tuple:raise ReceiptDescriptorRejected('invalid data-record payload')
        pairs=value[1]
        names=tuple(name for name,_ in pairs if type(name) is str)
        expected=tuple(f.name for f in fields(cls))
        if names!=expected or any(type(row) is not tuple or len(row)!=2 for row in pairs):
            raise ReceiptDescriptorRejected('unknown or incomplete data-record fields')
        for _,item in pairs:_validate_encoded(item)


def _validate_future_choice(choice):
    from checkpoint_choices import PortableAcceptedChoice,PortableChoiceMember,PortableActionDeclaration
    _closed(choice,PortableAcceptedChoice)
    data=choice.to_data()
    if type(data) is not tuple or len(data)!=9 or data[0]!='universe.accepted-action-choice/1' or data[3]!='accepted':
        raise ReceiptDescriptorRejected('unknown or nonaccepted future choice version/state')
    if type(choice.members) is not tuple or not choice.members:
        raise ReceiptDescriptorRejected('future choice has no portable members')
    for member in choice.members:
        _closed(member,PortableChoiceMember);_closed(member.action,PortableActionDeclaration)
        if member.action.adapter not in ('native.run-action/1','native.spot-action/1'):
            raise ReceiptDescriptorRejected('unknown future Action adapter')
    return data


def _tagged_fields(value,tag):
    if type(value) is not tuple or len(value)!=2 or value[0]!=tag or type(value[1]) is not tuple:
        raise ReceiptDescriptorRejected(f'malformed {tag} record')
    return dict(value[1])


def _tagged_string(value,label):
    if type(value) is not tuple or len(value)!=2 or value[0]!='string' or type(value[1]) is not str:
        raise ReceiptDescriptorRejected(f'{label} is not a logical string reference')
    return value[1]


def _effect_key(value):
    _validate_encoded(value)
    if type(value) is not tuple or value[0]!='effect-id':raise ReceiptDescriptorRejected('expected portable effect reference')
    return value


def _sequence(value, label):
    if type(value) is not tuple or len(value)!=2 or value[0]!='sequence' or type(value[1]) is not tuple:
        raise ReceiptDescriptorRejected(f'{label} is not a closed sequence')
    return value[1]


def _reference_set(value, label):
    if type(value) is not tuple or len(value)!=2 or value[0]!='set' or type(value[1]) is not tuple:
        raise ReceiptDescriptorRejected(f'{label} is not a closed logical-reference set')
    result=tuple(_tagged_string(row,label) for row in value[1])
    if result!=tuple(sorted(set(result))):raise ReceiptDescriptorRejected(f'{label} contains duplicate or unordered references')
    return result


def _check_target_effect_links(target, effects, action_by_id):
    state=_tagged_fields(target.state,'target.candidate/1');tid=target.target_id
    _reference_set(state.get('aware_of'),'Target awareness')
    expected=set()
    effect_payloads=dict(effects)
    for identity,payload in effects:
        if payload[0] in ('effect.awareness/1','effect.practice/1'):
            fields=_tagged_fields(payload,payload[0])
            if _tagged_string(fields.get('target_id'),'effect Target')==tid:expected.add(identity)
    incoming=_sequence(state.get('incoming'),'Target incoming effects')
    actual=set()
    for row in incoming:
        values=_tagged_fields(row,'effect.identified/1');identity=_effect_key(values.get('identity'))
        if identity not in effect_payloads or values.get('effect')!=effect_payloads[identity]:
            raise ReceiptDescriptorRejected('Target incoming effect has no matching causal receipt effect')
        actual.add(identity)
    if actual!=expected:raise ReceiptDescriptorRejected('Target incoming causal effect coverage is inconsistent')
    outgoing=tuple(_effect_key(row) for row in _sequence(state.get('outgoing_effect_ids'),'Target outgoing effects'))
    if len(set(outgoing))!=len(outgoing):raise ReceiptDescriptorRejected('duplicate Target outgoing effect reference')
    for identity in outgoing:
        action=action_by_id.get(identity[3])
        if identity not in effect_payloads or action is None or action.actor_id!=tid:
            raise ReceiptDescriptorRejected('Target outgoing effect source Action is unresolved')
    category=_tagged_string(state.get('category'),'Target category')
    if category=='being':
        practice=_tagged_fields(state.get('practice_state'),'practice.projection/1')
        if practice.get('being_id')!=('string',tid):raise ReceiptDescriptorRejected('Target practice projection belongs to another Being')
        for exercise in _sequence(practice.get('exercises'),'Target practice exercises'):
            fields=_tagged_fields(exercise,'practice.exercise/1')
            if _effect_key(fields.get('effect_identity')) not in expected:
                raise ReceiptDescriptorRejected('Target practice exercise has a broken causal reference')
    elif state.get('practice_state')!=('null',):
        raise ReceiptDescriptorRejected('Object Target has an unsupported practice projection')


def _id(value, label):
    if type(value) is not str or not value:
        raise ReceiptDescriptorRejected(f'{label} requires a stable logical ID')
    return value


def _record(value, cls, tag):
    data=native_data(value,(cls,))
    if set(data) != {f.name for f in fields(cls)}:
        raise ReceiptDescriptorRejected(f'unknown fields in {tag}')
    return (tag,tuple((f.name,_value(data[f.name])) for f in fields(cls)))


_DATA_RECORDS = None


def _records():
    global _DATA_RECORDS
    if _DATA_RECORDS is None:
        from action_evaluation import IdentifiedEffect
        from observer_proposals import ActionOutcomeEffect, LifecycleEffect
        from frozen_practice import (PracticeProjection,CandidatePracticeUse,
                                     CandidateSkillTransition)
        from experience import SkillUse,BatchSkillUse
        from observer_proposals import ObserverProjection
        from spatial.state import CartesianPosition
        from action_settlement import TargetCandidate
        _DATA_RECORDS={
            AwarenessEffect:'effect.awareness/1', PracticeEffect:'effect.practice/1',
            ActionOutcomeEffect:'effect.action-outcome/1', LifecycleEffect:'effect.lifecycle/1',
            PracticeProjection:'practice.projection/1', CandidatePracticeUse:'practice.exercise/1',
            CandidateSkillTransition:'practice.transition/1', SkillUse:'practice.skill-use/1',
            BatchSkillUse:'practice.batch-use/1', ObserverProjection:'observer.projection/1',
            CartesianPosition:'spatial.cartesian-position/1',TargetCandidate:'target.candidate/1',
            IdentifiedEffect:'effect.identified/1',
        }
    return _DATA_RECORDS


def _value(value):
    if value is None:return ('null',)
    if type(value) is bool:return ('boolean',value)
    if type(value) is str:return ('string',value)
    if type(value) in (int,float):return _finite(value,'data value')
    if type(value) is EffectIdentity:
        d=native_data(value,(EffectIdentity,))
        if type(d['encounter_id']) is not str or type(d['source_action_id']) is not str:
            raise ReceiptDescriptorRejected('invalid effect identity')
        if type(d['boundary']) is not int or type(d['slot']) is not int or d['slot']<0:
            raise ReceiptDescriptorRejected('invalid effect identity boundary/slot')
        if d['channel'] not in ('effect','defense','lifecycle'):
            raise ReceiptDescriptorRejected('unknown effect identity channel')
        return ('effect-id',d['encounter_id'],d['boundary'],d['source_action_id'],d['channel'],d['slot'])
    if type(value) in (tuple,list):return ('sequence',tuple(_value(x) for x in value))
    if type(value) in (set,frozenset):
        rows=tuple(sorted((_value(x) for x in value),key=lambda x:json.dumps(x,separators=(',',':'))))
        return ('set',rows)
    if type(value) in (dict,MappingProxyType):
        if any(type(k) is not str for k in value):
            raise ReceiptDescriptorRejected('data mappings require string keys')
        return ('mapping',tuple((k,_value(value[k])) for k in sorted(value)))
    cls=type(value);tag=_records().get(cls)
    if tag is None:raise ReceiptDescriptorRejected(f'unknown receipt/practice value type {cls.__name__}')
    return _record(value,cls,tag)


def _position(value):
    if value is None:return ('null',)
    from spatial.state import CartesianPosition
    if type(value) is not CartesianPosition:raise ReceiptDescriptorRejected('unknown Target position type')
    d=native_data(value,(CartesianPosition,))
    if set(d)!={'x','y','z'}:raise ReceiptDescriptorRejected('unknown position fields')
    return ('cartesian',tuple(_finite(d[k],'position') for k in ('x','y','z')))


def _portable_effect(row, encounter_id, boundary, action_ids):
    from observer_proposals import ActionOutcomeEffect,LifecycleEffect
    if type(row) is not IdentifiedEffect:raise ReceiptDescriptorRejected('unknown identified effect type')
    d=native_data(row,(IdentifiedEffect,));identity=d['identity'];effect=d['effect']
    if type(identity) is not EffectIdentity:raise ReceiptDescriptorRejected('unknown effect identity')
    identity_data=native_data(identity,(EffectIdentity,))
    aid=identity_data['source_action_id']
    if (identity_data['encounter_id']!=encounter_id or identity_data['boundary']!=boundary
            or aid not in action_ids):raise ReceiptDescriptorRejected('effect has a broken receipt/action link')
    allowed=(AwarenessEffect,PracticeEffect,ActionOutcomeEffect,LifecycleEffect)
    if type(effect) not in allowed:raise ReceiptDescriptorRejected('unknown or unsupported effect type')
    payload=_value(effect)
    return (('effect-id',encounter_id,boundary,aid,identity_data['channel'],identity_data['slot']),payload)


def _portable_action(inspection, live, world, encounter, boundary, effect_ids):
    from activities import RunAction,SpotAction
    from strategy import Strategy
    from observer_proposals import ActionOutcomeEffect,LifecycleEffect
    from action_evaluation import ActionView
    declaration=inspection.declaration;proposal=inspection.facts
    if type(declaration) is not ActionView or type(proposal) is not ActionProposal:
        raise ReceiptDescriptorRejected('unknown committed Action declaration/proposal type')
    if type(live) not in (RunAction,SpotAction):
        raise ReceiptDescriptorRejected('only exact native RunAction/SpotAction receipts are supported')
    d=object.__getattribute__(live,'__dict__')
    required_common={'id','type','universe','event_type','start_time','end_time','location','name',
        'parent_event_id','actor_id','target_id','instrument_id','strategy','resolution',
        '_activity_started','_atomic_effect_ids','_atomic_lifecycle'}
    specific=({'minimum_distance','practice_experience','start_position','displacement'} if type(live) is RunAction
              else {'spotting_conditions','declared_roll','roll','path_status','_encounter',
                    'ledger','group_fully_visible'})
    if set(d)!=required_common|specific:raise ReceiptDescriptorRejected('unknown committed Action fields')
    aid=_id(d['id'],'Action');adapter=('native.run-action/1' if type(live) is RunAction else 'native.spot-action/1')
    if (aid!=declaration.id or d['universe'] is not world or d['event_type']!=declaration.data['event_type']
            or d['type']!=type(live).__name__ or d['parent_event_id']!=encounter.id
            or d['location'] is not None or d['instrument_id'] is not None
            or d['actor_id']!=declaration.actor_id or d['target_id']!=declaration.target_id
            or d['start_time']!=declaration.start or d['end_time']!=declaration.nominal_end):
        raise ReceiptDescriptorRejected('committed Action declaration or owner link is inconsistent')
    if d['_activity_started'] is not True or type(d['strategy']) is not Strategy:
        raise ReceiptDescriptorRejected('Action start or Strategy state is unsupported')
    sd=native_data(d['strategy'],(Strategy,))
    if set(sd)!={'attack','defense','timing','extra_damage'}:
        raise ReceiptDescriptorRejected('unknown native Strategy fields')
    strategy=tuple((k,_finite(sd[k],'strategy.'+k)) for k in ('attack','defense','timing','extra_damage'))
    snapshot_data=declaration.data
    if type(snapshot_data) not in (dict,MappingProxyType):raise ReceiptDescriptorRejected('Action snapshot declaration is opaque')
    snapshot_strategy=snapshot_data.get('strategy')
    if type(snapshot_strategy) not in (dict,MappingProxyType) or tuple((k,_finite(snapshot_strategy.get(k),'snapshot strategy')) for k in ('attack','defense','timing','extra_damage'))!=strategy:
        raise ReceiptDescriptorRejected('Action Strategy differs from committed pre-action snapshot')
    if d['name'] is not None and type(d['name']) is not str:raise ReceiptDescriptorRejected('Action name is not data')
    if type(live) is RunAction:
        if d['target_id'] is not None or d['displacement'] is not None:
            raise ReceiptDescriptorRejected('RunAction contains unsupported target/result state')
        params=(('minimum_distance',_finite(d['minimum_distance'],'minimum_distance')),
                ('practice_experience',_finite(d['practice_experience'],'practice_experience')),
                ('start_position',_position(d['start_position'])))
        if (snapshot_data.get('minimum_distance')!=d['minimum_distance']
                or snapshot_data.get('practice_experience')!=d['practice_experience']
                or snapshot_data.get('started') is not True
                or _position(snapshot_data.get('start_position'))!=_position(d['start_position'])):
            raise ReceiptDescriptorRejected('RunAction differs from its pre-action declaration')
    else:
        if (d['_encounter'] is not encounter or d['roll'] is not None
                or d['path_status'] is not None
                or d['ledger'] is not None or d['group_fully_visible'] is not False):
            raise ReceiptDescriptorRejected('SpotAction has an unsupported process binding or live sampled result')
        if d['target_id'] is None or d['target_id']==d['actor_id']:
            raise ReceiptDescriptorRejected('SpotAction target reference is invalid')
        params=(('spotting_conditions',_value(d['spotting_conditions'])),
                ('declared_roll',_value(d['declared_roll'])))
        if (snapshot_data.get('spotting_conditions')!=d['spotting_conditions']
                or snapshot_data.get('declared_roll')!=d['declared_roll']
                or snapshot_data.get('group_fully_visible') is not False
                or any(snapshot_data.get(key) is not None for key in ('roll','path_status'))):
            raise ReceiptDescriptorRejected('SpotAction differs from its pre-action declaration')
    if proposal.action_id!=aid or proposal.actor_id!=d['actor_id'] or proposal.defenses:
        raise ReceiptDescriptorRejected('unsupported proposal identity or defense family')
    if proposal.outcome not in (('unplaced','no_movement','success','partial') if type(live) is RunAction else
                                ('unplaced','out_of_range','unmodeled_target','no_clear_path','success','failure')):
        raise ReceiptDescriptorRejected('unknown native Run/Spot outcome')
    if tuple(row.identity for row in inspection.effects)!=tuple(effect_ids):
        raise ReceiptDescriptorRejected('Action/effect identity list disagrees with receipt')
    if tuple(row.effect for row in inspection.effects if row.identity.channel=='effect')!=tuple(proposal.effects):
        raise ReceiptDescriptorRejected('Action proposal effects differ from identified receipt effects')
    lifecycle=[row.effect for row in inspection.effects if type(row.effect) is LifecycleEffect]
    outcomes=[row.effect for row in inspection.effects if type(row.effect) is ActionOutcomeEffect]
    if (len(lifecycle)!=1 or len(outcomes)!=1 or lifecycle[0].status!='finished'
            or lifecycle[0].action_id!=aid or lifecycle[0].boundary!=boundary
            or outcomes[0].action_id!=aid or outcomes[0].outcome!=proposal.outcome):
        raise ReceiptDescriptorRejected('missing or inconsistent committed Action lifecycle')
    if any(type(row.effect) not in (AwarenessEffect,PracticeEffect,ActionOutcomeEffect,LifecycleEffect)
           for row in inspection.effects):
        raise ReceiptDescriptorRejected('unsupported Action effect family')
    declaration_data=(('event_type',d['event_type']),('strategy',strategy),('parameters',params),
        ('display_name',_value(d['name'])),('parent_encounter_id',encounter.id))
    return PortableCommittedAction(aid,adapter,d['actor_id'],d['target_id'],
        _finite(d['start_time'],'action.start'),_finite(d['end_time'],'action.end'),
        declaration_data,proposal.outcome,_value(proposal.metadata),tuple(effect_ids))


def _portable_target(view, target_id, boundary, effect_lookup, action_actors):
    from action_settlement import TargetCandidate
    from observer_proposals import ObserverProjection
    state=view.state
    if (type(state) is not TargetCandidate or state.target_id!=target_id
            or state.category not in ('being','weapon','armor')):
        raise ReceiptDescriptorRejected('Target record is not owned by a supported native Being or Object')
    if state.category=='being':
        if type(state.observer_state) is not ObserverProjection:
            raise ReceiptDescriptorRejected('unknown Being Target observer state')
        od=native_data(state.observer_state,(ObserverProjection,))
        if (od['observations'] or od['interpretations'] or od['heard_accounts'] or od['belief_recipient_ids']):
            raise ReceiptDescriptorRejected('observer evidence/Belief records are outside this receipt subset')
    elif state.observer_state is not None:
        raise ReceiptDescriptorRejected('Object Target contains an unsupported observer projection')
    incoming=[]
    for row in state.incoming:
        if type(row) is not IdentifiedEffect or row.identity not in effect_lookup or effect_lookup[row.identity]!=row:
            raise ReceiptDescriptorRejected('Target incoming effect has no matching causal receipt effect')
        incoming.append(_value(row.identity))
    outgoing=tuple(_value(x) for x in state.outgoing_effect_ids)
    for identity in state.outgoing_effect_ids:
        if identity not in effect_lookup or action_actors.get(identity.source_action_id)!=target_id:
            raise ReceiptDescriptorRejected('Target outgoing effect has an unresolved source')
    for row in state.incoming:
        if row.identity.source_action_id not in action_actors:
            raise ReceiptDescriptorRejected('Target effect source Action is absent')
    practice=state.practice_state
    if practice is not None:
        if type(practice).__name__!='PracticeProjection':raise ReceiptDescriptorRejected('unknown practice projection')
        if practice.history_revision is not None:
            raise ReceiptDescriptorRejected('personal-history-bound practice needs a separate constraint binding')
        for exercise in practice.exercises:
            effect=effect_lookup.get(exercise.effect_identity)
            if (type(effect) is not IdentifiedEffect or type(effect.effect) is not PracticeEffect
                    or effect.effect.target_id!=target_id or effect.effect.skill!=exercise.skill_name
                    or effect.effect.experience!=exercise.experience
                    or exercise.action_id!=exercise.effect_identity.source_action_id):
                raise ReceiptDescriptorRejected('practice exercise is not causally linked to Target effect')
    return PortableTargetRecord(target_id,state.category,_position(view.position),
        _value(state))


def _portable_fence(fence, encounter, live_actions, future_action_ids):
    from interval_staging import StartFence,AuthorityReference
    if type(fence) is not StartFence:raise ReceiptDescriptorRejected('unknown boundary start-fence type')
    d=native_data(fence,(StartFence,))
    if set(d)!={f.name for f in fields(StartFence)}:raise ReceiptDescriptorRejected('unknown start-fence fields')
    choices=tuple(d['published_choices']);registered=tuple(d['registered_action_ids']);started=tuple(d['started_action_ids'])
    known=set(live_actions)|set(future_action_ids)
    if any(x not in known for x in registered+started):raise ReceiptDescriptorRejected('start fence references missing Action')
    if type(d['metadata']) not in (dict,MappingProxyType):raise ReceiptDescriptorRejected('start-fence metadata is not closed')
    if set(d['metadata'])!=set(registered):raise ReceiptDescriptorRejected('start-fence Action coverage is incomplete')
    # Authenticate process-local anchors against the live graph, then omit them.
    for aid,meta in d['metadata'].items():
        action=live_actions.get(aid)
        if action is None:continue
        if type(meta) not in (dict,MappingProxyType):raise ReceiptDescriptorRejected('start-fence Action metadata is opaque')
        ref=meta.get('_encounter')
        from activities import RunAction,SpotAction
        if type(action) is SpotAction:
            if type(ref) is not AuthorityReference or (ref.role,ref.key,ref.identity)!=('encounter',encounter.id,id(encounter)):
                raise ReceiptDescriptorRejected('start-fence process anchor is stale or forged')
        elif type(action) is RunAction and ref is not None:
            raise ReceiptDescriptorRejected('RunAction has an unsupported encounter process anchor')
        allowed={'parent_event_id','end_time','_activity_started'}
        if type(action) is SpotAction:allowed.add('_encounter')
        else:allowed.add('start_position')
        if set(meta)-allowed:
            raise ReceiptDescriptorRejected('unknown start-fence Action metadata field')
        if meta.get('parent_event_id')!=encounter.id or meta.get('end_time')!=action.end_time or meta.get('_activity_started') is not True:
            raise ReceiptDescriptorRejected('start-fence metadata disagrees with live Action')
        if type(action) is RunAction and _position(meta.get('start_position'))!=_position(action.start_position):
            raise ReceiptDescriptorRejected('RunAction start-position fence is stale')
    return (_finite(d['time'],'start fence time'),d['phase'],choices,registered,started)


def _rng_descriptor(encounter, history, rng_scope):
    from atomic_publication import RNGCursor
    from transactional_progression import _BINDINGS
    if rng_scope!='exclusive_encounter':raise ReceiptDescriptorRejected('explicit exclusive_encounter RNG scope assertion required')
    binding=_BINDINGS.get(id(encounter))
    if binding is None or binding.encounter() is not encounter or type(binding.rng_owner) is not RNGCursor:
        raise ReceiptDescriptorRejected('private caller-owned RNGCursor is required')
    owner=binding.rng_owner
    if sum(1 for item in _BINDINGS.values() if item.rng_owner is owner)!=1:
        raise ReceiptDescriptorRejected('RNGCursor is shared by multiple transactional Encounters')
    state=native_data(owner,(RNGCursor,))['state']
    if tuple(state)!=tuple(history[-1].rng_state):raise ReceiptDescriptorRejected('latest receipt RNG state is stale')
    return ('caller-cursor','exclusive_encounter-asserted'),_value(state)


def _movement_activation_for_receipt(encounter):
    """Return the already-admitted native activation record, if present."""
    from checkpoint_inventory import CheckpointRejected
    try:
        from checkpoint_adapters import _movement_activation_state
        return _movement_activation_state(encounter)
    except CheckpointRejected as exc:
        raise ReceiptDescriptorRejected('Arena movement activation is inconsistent') from exc


def describe_committed_receipt_chain(world, encounter, *, quiescent=False,
                                     rng_scope=None):
    """Capture a bounded consecutive Run/Spot or Arena movement receipt chain."""
    from universe import Universe
    from encounter import Encounter
    from atomic_publication import coordinated_access
    from encounter_inspection import inspect_encounter
    from action_choice import _Accepted,ChoiceBook
    from activities import RunAction,SpotAction
    from transactional_progression import mode_of
    if type(world) is not Universe or type(encounter) is not Encounter or encounter.universe is not world:
        raise ReceiptDescriptorRejected('native Universe/Encounter roots required')
    if quiescent is not True:raise ReceiptDescriptorRejected('explicit quiescent read ownership assertion required')
    if mode_of(encounter)!='transactional':raise ReceiptDescriptorRejected('explicit transactional Encounter required')
    with coordinated_access(world):
        try:view=inspect_encounter(encounter)
        except Exception as exc:
            raise ReceiptDescriptorRejected(f'live receipt authentication/anchor validation failed: {exc}') from exc
        history=encounter.__dict__.get('_atomic_interval_history')
        if type(history) is not list or not 1 <= len(history) <= 4096:
            raise ReceiptDescriptorRejected('one to 4096 committed boundaries are supported')
        if view.boundary!=history[-1].boundary or view.latest_boundary!=view.boundary:
            raise ReceiptDescriptorRejected('inspection and committed receipt cursors disagree')
        if view.objective or view.objective_use or view.recipients:
            raise ReceiptDescriptorRejected('objective facts and observer recipients are outside this subset')
        world_data=object.__getattribute__(world,'__dict__')
        if type(world_data.get('id')) is not str or type(encounter.id) is not str:
            raise ReceiptDescriptorRejected('Universe/Encounter requires stable logical IDs')
        action_ids=tuple(aid for row in view.timeline for aid in row.action_ids)
        if len(set(action_ids))!=len(action_ids) or set(action_ids)!=set(view.actions):
            raise ReceiptDescriptorRejected('missing, duplicate, or unreceipted committed Action')
        movement_activation=None
        movement_only_boundaries=tuple(index for index,row in enumerate(history)
                                       if not row.action_ids)
        if movement_only_boundaries:
            movement_activation=_movement_activation_for_receipt(encounter)
            if movement_activation is None:
                raise ReceiptDescriptorRejected('Action-free boundary lacks native movement activation')
            if movement_only_boundaries != tuple(range(len(history))):
                raise ReceiptDescriptorRejected(
                    'Action-free movement must be one complete consecutive initial history')
            if (len(history) > 1 and any(
                    history[index-1].boundary + 1 != history[index].boundary
                    for index in range(1, len(history)))):
                raise ReceiptDescriptorRejected(
                    'movement-only history contains a gap or duplicate boundary')
        live_actions={}
        action_actors={}
        effects_by_boundary={};actions_by_boundary={};targets_by_boundary={}
        for row in history:
            if type(row.action_ids) is not tuple or type(row.effect_ids) is not tuple:
                raise ReceiptDescriptorRejected('unreviewed native receipt collections')
            actions_by_boundary[row.boundary]=row.action_ids
            effects_by_boundary[row.boundary]=row.effect_ids
            targets_by_boundary[row.boundary]=[]
        for aid in action_ids:
            live=world.event_history.get(aid)
            item=view.actions[aid]
            if type(live) not in (RunAction,SpotAction):
                raise ReceiptDescriptorRejected('non-native Run/Spot Action in receipt history')
            live_actions[aid]=live;action_actors[aid]=live.actor_id
            if item.resolved_boundary not in actions_by_boundary or aid not in actions_by_boundary[item.resolved_boundary]:
                raise ReceiptDescriptorRejected('Action resolved outside its receipt boundary')
        effect_lookup={identity:row for identity,row in view.effects.items()}
        if len(effect_lookup)!=sum(len(x) for x in effects_by_boundary.values()):
            raise ReceiptDescriptorRejected('missing or duplicate committed effects')
        if any(view.effects.get(eid) is None for rows in effects_by_boundary.values() for eid in rows):
            raise ReceiptDescriptorRejected('receipt effect identity is missing')
        future_choices=[];future_action_ids=set();committed_choices={}
        book=encounter._choice_book
        if type(book) is not ChoiceBook or book.encounter is not encounter:raise ReceiptDescriptorRejected('unknown ChoiceBook owner')
        with book.lock:
            for cid,record in book._choices.items():
                if type(record) is not _Accepted or record.view.id!=cid:
                    raise ReceiptDescriptorRejected('unknown choice or choice record type')
                if record.view.state=='accepted':
                    if record.view.first_start<=view.latest_boundary:
                        raise ReceiptDescriptorRejected('accepted choice is not wholly future')
                    try:portable=describe_accepted_choice(world,encounter,cid)
                    except ChoiceDescriptorRejected as exc:raise ReceiptDescriptorRejected(str(exc)) from exc
                    if set(portable.action_ids)&(set(action_ids)|future_action_ids):
                        raise ReceiptDescriptorRejected('accepted future Action ID is duplicated')
                    future_action_ids.update(portable.action_ids);future_choices.append(portable)
                elif record.view.state=='finished':
                    ids=tuple(member.action.id for member in record.members)
                    if not ids or not set(ids)<=set(action_ids) or tuple(record.view.action_ids)!=ids:
                        raise ReceiptDescriptorRejected('finished ChoiceBook record is not fully represented by receipts')
                    committed_choices[cid]=PortableCommittedChoice(cid,record.view.version,record.origin,ids)
                else:raise ReceiptDescriptorRejected('executing/cancelled choice requires a broader adapter')
        if encounter.pending_action_list:
            raise ReceiptDescriptorRejected('active pending Actions require a broader lifecycle adapter')
        if set(encounter.finished_action_list)!=set(action_ids) or encounter.cancelled_action_list:
            raise ReceiptDescriptorRejected('Action lifecycle queues are outside the bounded receipt chain')
        life_choice={}
        for aid in action_ids:
            from observer_proposals import LifecycleEffect
            life=[row.effect for row in view.actions[aid].effects if type(row.effect) is LifecycleEffect]
            if len(life)!=1:raise ReceiptDescriptorRejected('Action must have exactly one lifecycle effect')
            life_choice[aid]=life[0].choice_id
        if set(life_choice.values())!=set(committed_choices):
            raise ReceiptDescriptorRejected('committed choice and lifecycle references disagree')
        for cid,choice in committed_choices.items():
            if set(choice.action_ids)!={aid for aid,c in life_choice.items() if c==cid}:
                raise ReceiptDescriptorRejected('committed choice member references disagree')
        future_choices=tuple(sorted(future_choices,key=lambda c:c.choice_id))
        committed=tuple(committed_choices[k] for k in sorted(committed_choices))
        rng_owner,rng_final=_rng_descriptor(encounter,history,rng_scope)
        boundary_rows=[]
        timeline={row.boundary:row for row in view.timeline}
        for receipt_index,receipt in enumerate(history):
            br=timeline.get(receipt.boundary)
            if br is None or br.start!=receipt.inspection.start:
                raise ReceiptDescriptorRejected('missing boundary chronology record')
            aids=tuple(receipt.action_ids);eids=tuple(receipt.effect_ids)
            if tuple(br.action_ids)!=aids or tuple(br.effect_ids)!=eids:
                raise ReceiptDescriptorRejected('boundary ordered identity coverage mismatch')
            if not aids:
                meta=receipt.inspection
                expected_start_only = (receipt_index == 0 and
                                       movement_activation is not None)
                expected_continuation = (receipt_index > 0
                    and not history[0].action_ids
                    and history[receipt_index - 1].boundary + 1 == receipt.boundary)
                if (not (expected_start_only or expected_continuation) or eids
                        or meta.actions or meta.action_anchors or meta.effects
                        or type(meta.participants) is not tuple or not meta.participants
                        or len(set(meta.participants))!=len(meta.participants)
                        or set(meta.participants)!=(set(encounter.being_list)
                            |set(encounter.non_being_object_list))
                        or set(meta.target_anchors)!=set(meta.participants)
                        or set(meta.entities)!=set(meta.participants)):
                    raise ReceiptDescriptorRejected(
                        'initial movement-only boundary has inconsistent Action, effect, or Entity coverage')
            portable_actions=[]
            for aid in aids:
                item=view.actions[aid]
                own=tuple(row for row in item.effects if row.identity.boundary==receipt.boundary)
                own_ids=tuple(row.identity for row in own)
                if any(eid not in eids for eid in own_ids):raise ReceiptDescriptorRejected('Action effect crosses receipt boundary')
                portable_actions.append(_portable_action(item,live_actions[aid],world,encounter,receipt.boundary,own_ids))
            portable_effects=tuple(_portable_effect(view.effects[eid],encounter.id,receipt.boundary,set(aids)) for eid in eids)
            # Keep effects in the issuer's exact order; all keys must be unique.
            if len({row[0] for row in portable_effects})!=len(portable_effects):raise ReceiptDescriptorRejected('duplicate effect identity')
            for target_id,rows in view.histories.items():
                target_views=tuple(x for x in rows if x.boundary==receipt.boundary)
                if target_views:
                    if len(target_views)!=1:raise ReceiptDescriptorRejected('duplicate Target history at boundary')
                    targets_by_boundary[receipt.boundary].append(_portable_target(target_views[0],target_id,receipt.boundary,effect_lookup,action_actors))
            if not targets_by_boundary[receipt.boundary]:raise ReceiptDescriptorRejected('missing Target-owned receipt history')
            start_fences=tuple(_portable_fence(f,encounter,live_actions,future_action_ids) for f in receipt.inspection.starts)
            portable_targets=tuple(sorted(targets_by_boundary[receipt.boundary],key=lambda x:x.target_id))
            if not aids:
                participant_ids=tuple(sorted(receipt.inspection.participants))
                if tuple(row.target_id for row in portable_targets)!=tuple(sorted(participant_ids)):
                    raise ReceiptDescriptorRejected(
                        'initial movement-only boundary lacks complete participant Target history')
                receipt_type = (PortableMovementOnlyBoundaryReceipt
                    if receipt_index == 0 else PortableContinuingMovementBoundaryReceipt)
                schema = (MOVEMENT_ONLY_BOUNDARY_SCHEMA
                    if receipt_index == 0 else CONTINUING_MOVEMENT_BOUNDARY_SCHEMA)
                boundary_rows.append(receipt_type(schema,receipt.boundary,
                    _finite(receipt.inspection.start,'receipt.start'),participant_ids,
                    portable_targets,start_fences,_value(receipt.rng_state)))
            else:
                boundary_rows.append(PortableBoundaryReceipt(receipt.boundary,_finite(receipt.inspection.start,'receipt.start'),
                    aids,tuple(_value(eid) for eid in eids),
                    tuple(replace(action,effect_ids=tuple(_value(eid) for eid in action.effect_ids)) for action in portable_actions),portable_effects,
                    portable_targets,start_fences,_value(receipt.rng_state)))
        descriptor=PortableReceiptChain(DESCRIPTOR_SCHEMA,world.id,encounter.id,
            _finite(encounter.start_time,'Encounter.start_time'),tuple(boundary_rows),committed,future_choices,rng_owner)
        validate_receipt_descriptor(descriptor)
        return descriptor


def validate_receipt_descriptor(value):
    """Validate closed fields, chronology, causal references, and future choices."""
    d=_closed(value,PortableReceiptChain)
    if d['schema']!=DESCRIPTOR_SCHEMA:raise ReceiptDescriptorRejected('unknown committed-receipt schema version')
    _id(d['universe_id'],'Universe');_id(d['encounter_id'],'Encounter')
    start_time=_decoded_number(d['start_time'],'Encounter start time')
    if type(d['receipts']) is not tuple or not 1 <= len(d['receipts']) <= 4096:
        raise ReceiptDescriptorRejected('receipt chain must contain one to 4096 rows')
    if d['rng_ownership']!=('caller-cursor','exclusive_encounter-asserted'):
        raise ReceiptDescriptorRejected('ambiguous or unsupported RNG ownership descriptor')
    prior=None;all_actions=set();all_choices=set();lifecycle_choices={}
    for receipt_index,receipt in enumerate(d['receipts']):
        movement_receipt = type(receipt) in (
            PortableMovementOnlyBoundaryReceipt, PortableContinuingMovementBoundaryReceipt)
        if movement_receipt:
            _closed(receipt,type(receipt))
            initial = type(receipt) is PortableMovementOnlyBoundaryReceipt
            expected_schema = (MOVEMENT_ONLY_BOUNDARY_SCHEMA if initial
                               else CONTINUING_MOVEMENT_BOUNDARY_SCHEMA)
            if receipt.schema!=expected_schema:
                raise ReceiptDescriptorRejected('unknown movement-only boundary version')
            if initial != (receipt_index == 0):
                raise ReceiptDescriptorRejected('initial and continuing movement receipt order is invalid')
            if type(receipt.boundary) is not int or receipt.boundary<1:
                raise ReceiptDescriptorRejected('invalid movement-only boundary')
            expected_start = (start_time if initial else prior)
            if _decoded_number(receipt.start,'movement-only receipt start')!=expected_start:
                raise ReceiptDescriptorRejected('movement-only receipt start does not continue Encounter chronology')
            expected_boundary = (math.floor(start_time)+1 if initial else
                                 (prior+1 if prior is not None else None))
            if receipt.boundary!=expected_boundary:
                raise ReceiptDescriptorRejected('movement-only receipt is not chronologically consecutive')
            if not initial and (not d['receipts'] or
                    type(d['receipts'][0]) is not PortableMovementOnlyBoundaryReceipt):
                raise ReceiptDescriptorRejected('continuing movement receipt lacks its initial activation receipt')
            if not initial and _decoded_number(receipt.start,'continuing movement receipt start') != prior:
                raise ReceiptDescriptorRejected('continuing movement receipt does not start at prior boundary')
            if (type(receipt.participant_ids) is not tuple or not receipt.participant_ids
                    or any(type(entity_id) is not str or not entity_id for entity_id in receipt.participant_ids)
                    or len(set(receipt.participant_ids))!=len(receipt.participant_ids)):
                raise ReceiptDescriptorRejected('movement-only participant identity set is invalid')
            _id_set=set(receipt.participant_ids)
            if type(receipt.targets) is not tuple or not receipt.targets:
                raise ReceiptDescriptorRejected('movement-only boundary lacks Target-owned history')
            target_ids=tuple(row.target_id for row in receipt.targets
                             if type(row) is PortableTargetRecord)
            if len(target_ids)!=len(receipt.targets) or target_ids!=tuple(sorted(_id_set)):
                raise ReceiptDescriptorRejected('movement-only Target history does not cover participants exactly')
            if not initial and (receipt.participant_ids != d['receipts'][0].participant_ids
                    or target_ids != tuple(row.target_id for row in d['receipts'][0].targets)):
                raise ReceiptDescriptorRejected('continuing movement participant/Target coverage changed')
            if not initial and receipt.rng_after != d['receipts'][0].rng_after:
                raise ReceiptDescriptorRejected('movement-only boundary unexpectedly changed RNG state')
            for target in receipt.targets:
                _closed(target,PortableTargetRecord);_id(target.target_id,'Target')
                if target.category not in ('being','weapon','armor'):
                    raise ReceiptDescriptorRejected('movement-only Target category is not a supported Entity')
                if type(target.state) is not tuple or not target.state or target.state[0]!='target.candidate/1':
                    raise ReceiptDescriptorRejected('unknown movement-only Target state descriptor')
                state_fields=target.state[1]
                if (type(state_fields) is not tuple or
                        ('target_id',('string',target.target_id)) not in state_fields or
                        ('category',('string',target.category)) not in state_fields):
                    raise ReceiptDescriptorRejected('movement-only Target identity/category link is invalid')
                _validate_encoded(target.state)
                if target.position==('null',):pass
                elif type(target.position) is tuple and len(target.position)==2 and target.position[0]=='cartesian':
                    if type(target.position[1]) is not tuple or len(target.position[1])!=3:
                        raise ReceiptDescriptorRejected('invalid movement-only Target position')
                    for number in target.position[1]:_validate_encoded(number)
                else:raise ReceiptDescriptorRejected('unknown movement-only Target position version')
                _check_target_effect_links(target,(),{})
            for fence in receipt.start_fences:
                if (type(fence) is not tuple or len(fence)!=5 or type(fence[1]) is not str
                        or any(type(seq) is not tuple or any(type(x) is not str for x in seq)
                               for seq in fence[2:])):
                    raise ReceiptDescriptorRejected('unknown movement-only start-fence descriptor fields')
                _validate_encoded(fence[0])
            _validate_encoded(receipt.rng_after)
            prior=receipt.boundary
            continue
        _closed(receipt,PortableBoundaryReceipt)
        if type(receipt.boundary) is not int or receipt.boundary<1:raise ReceiptDescriptorRejected('invalid receipt boundary')
        if prior is not None and receipt.boundary!=prior+1:raise ReceiptDescriptorRejected('receipt boundaries are missing, duplicate, or out of order')
        expected_start=start_time if prior is None else prior
        if _decoded_number(receipt.start,'receipt start')!=expected_start:
            raise ReceiptDescriptorRejected('receipt start does not continue committed chronology')
        if prior is None and receipt.boundary!=math.floor(start_time)+1:
            raise ReceiptDescriptorRejected('initial receipt boundary does not follow Encounter start')
        prior=receipt.boundary
        if type(receipt.action_ids) is not tuple or not receipt.action_ids or len(set(receipt.action_ids))!=len(receipt.action_ids):raise ReceiptDescriptorRejected('invalid receipt Action order')
        if type(receipt.actions) is not tuple or tuple(row.action_id for row in receipt.actions)!=receipt.action_ids:raise ReceiptDescriptorRejected('receipt Action coverage/order mismatch')
        if len(set(receipt.effect_ids))!=len(receipt.effect_ids) or tuple(row[0] for row in receipt.effects)!=receipt.effect_ids:
            raise ReceiptDescriptorRejected('receipt effect coverage/order mismatch')
        if all_actions.intersection(receipt.action_ids):raise ReceiptDescriptorRejected('Action ID occurs in multiple receipts')
        all_actions.update(receipt.action_ids)
        for action in receipt.actions:
            _closed(action,PortableCommittedAction)
            _id(action.action_id,'Action');_id(action.actor_id,'Action actor')
            if action.adapter not in ('native.run-action/1','native.spot-action/1'):raise ReceiptDescriptorRejected('unknown committed Action adapter')
            declaration_keys=tuple(key for key,_ in action.declaration)
            if declaration_keys!=('event_type','strategy','parameters','display_name','parent_encounter_id'):
                raise ReceiptDescriptorRejected('unknown committed Action declaration fields')
            if action.declaration[-1][1]!=d['encounter_id']:
                raise ReceiptDescriptorRejected('Action declaration is linked to another Encounter')
            if action.declaration[0][1] not in ('run','spot') or (action.adapter=='native.run-action/1')!=(action.declaration[0][1]=='run'):
                raise ReceiptDescriptorRejected('Action event type/adapter disagreement')
            if (action.target_id is not None)!=(action.adapter=='native.spot-action/1'):
                raise ReceiptDescriptorRejected('Action logical Target reference disagrees with native family')
            if action.target_id is not None:_id(action.target_id,'Spot Target')
            strategy=action.declaration[1][1]
            if type(strategy) is not tuple or tuple(k for k,_ in strategy)!=('attack','defense','timing','extra_damage'):
                raise ReceiptDescriptorRejected('Action Strategy schema is unknown')
            for _,number in strategy:_validate_encoded(number)
            if type(action.declaration[2][1]) is not tuple:raise ReceiptDescriptorRejected('Action parameter declaration is malformed')
            params=dict(action.declaration[2][1])
            expected_params=(('minimum_distance','practice_experience','start_position') if action.adapter=='native.run-action/1'
                             else ('max_distance','practice_experience','declared_roll'))
            if tuple(params)!=expected_params:raise ReceiptDescriptorRejected('native Action parameter set is incomplete or reordered')
            for _,item in action.declaration[2][1]:
                if type(item) is tuple and item and item[0] in ('integer','binary64','null','boolean','string'):
                    if item[0]!='null':_validate_encoded(item)
            _validate_encoded(action.declaration[3][1]);_id(action.declaration[4][1],'Action Encounter')
            _validate_encoded(action.start);_validate_encoded(action.end)
            _validate_encoded(action.metadata)
            if action.outcome not in ('unplaced','no_movement','success','partial','out_of_range','unmodeled_target','no_clear_path','failure'):
                raise ReceiptDescriptorRejected('unknown committed Run/Spot outcome')
            action_start=_decoded_number(action.start,'Action start')
            action_end=_decoded_number(action.end,'Action end')
            if action_start>action_end or not expected_start<action_end<=receipt.boundary:
                raise ReceiptDescriptorRejected('Action timing is inconsistent with its receipt boundary')
            if type(action.effect_ids) is not tuple or any(type(x) is not tuple or x not in set(receipt.effect_ids) or x[3]!=action.action_id for x in action.effect_ids):raise ReceiptDescriptorRejected('invalid Action effect link')
            for effect_ref in action.effect_ids:_validate_encoded(effect_ref)
        action_by_id={row.action_id:row for row in receipt.actions}
        for action in receipt.actions:
            expected_refs=tuple(eid for eid,_ in receipt.effects if eid[3]==action.action_id)
            if action.effect_ids!=expected_refs:raise ReceiptDescriptorRejected('Action causal effect coverage is incomplete or out of order')
        if set(eid for action in receipt.actions for eid in action.effect_ids)!=set(receipt.effect_ids):
            raise ReceiptDescriptorRejected('receipt Action effect coverage is incomplete')
        for effect_id,payload in receipt.effects:
            if type(effect_id) is not tuple or len(effect_id)!=6 or effect_id[0]!='effect-id' or effect_id[2]!=receipt.boundary or effect_id[3] not in receipt.action_ids:
                raise ReceiptDescriptorRejected('broken effect-to-Action/receipt reference')
            if type(payload) is not tuple or payload[0] not in ('effect.awareness/1','effect.practice/1','effect.action-outcome/1','effect.lifecycle/1'):
                raise ReceiptDescriptorRejected('unknown receipt effect version')
            _validate_encoded(effect_id);_validate_encoded(payload)
            fields=_tagged_fields(payload,payload[0]);source=_tagged_string(fields.get('source_action_id'),'effect source Action')
            action=action_by_id.get(source)
            if action is None or effect_id[3]!=source:raise ReceiptDescriptorRejected('effect payload source Action link is broken')
            if payload[0]=='effect.awareness/1':
                if (action.adapter!='native.spot-action/1'
                        or _tagged_string(fields.get('target_id'),'awareness observer')!=action.actor_id
                        or _tagged_string(fields.get('observed_id'),'observed Target')!=action.target_id
                        or effect_id[4]!='effect'):
                    raise ReceiptDescriptorRejected('awareness effect does not match its Spot Action')
            elif payload[0]=='effect.practice/1':
                params=dict(action.declaration[2][1])
                if (_tagged_string(fields.get('target_id'),'practice Being')!=action.actor_id
                        or _tagged_string(fields.get('skill'),'practice skill')!=action.declaration[0][1]
                        or _decoded_number(fields.get('experience'),'practice experience')!=_decoded_number(params['practice_experience'],'declared practice experience')
                        or effect_id[4]!='effect'):
                    raise ReceiptDescriptorRejected('practice effect does not match its native Action')
            elif payload[0]=='effect.action-outcome/1':
                if (_tagged_string(fields.get('action_id'),'outcome Action')!=source
                        or _tagged_string(fields.get('outcome'),'Action outcome')!=action.outcome
                        or effect_id[4]!='lifecycle'):
                    raise ReceiptDescriptorRejected('Action outcome effect link is inconsistent')
            else:
                if (_tagged_string(fields.get('action_id'),'lifecycle Action')!=source
                        or _tagged_string(fields.get('status'),'lifecycle status')!='finished'
                        or _decoded_number(fields.get('boundary'),'lifecycle boundary')!=receipt.boundary
                        or _decoded_number(fields.get('nominal_end'),'lifecycle nominal end')!=_decoded_number(action.end,'Action end')
                        or effect_id[4]!='lifecycle'):
                    raise ReceiptDescriptorRejected('Action lifecycle effect link is inconsistent')
                if source in lifecycle_choices:raise ReceiptDescriptorRejected('Action has duplicate lifecycle effects')
                lifecycle_choices[source]=_tagged_string(fields.get('choice_id'),'lifecycle Choice')
        if type(receipt.targets) is not tuple or not receipt.targets:raise ReceiptDescriptorRejected('missing Target-owned history')
        tids=set()
        for target in receipt.targets:
            _closed(target,PortableTargetRecord);_id(target.target_id,'Target')
            if target.target_id in tids:raise ReceiptDescriptorRejected('duplicate Target receipt row')
            tids.add(target.target_id)
            if type(target.state) is not tuple or not target.state or target.state[0]!='target.candidate/1':
                raise ReceiptDescriptorRejected('unknown Target state descriptor')
            state_fields=target.state[1]
            if (type(state_fields) is not tuple or
                    ('target_id',('string',target.target_id)) not in state_fields or
                    ('category',('string',target.category)) not in state_fields or
                    target.category not in ('being','weapon','armor')):
                raise ReceiptDescriptorRejected('Target state identity/category link is invalid')
            _validate_encoded(target.state)
            _check_target_effect_links(target,receipt.effects,action_by_id)
            if target.position==('null',):pass
            elif type(target.position) is tuple and len(target.position)==2 and target.position[0]=='cartesian':
                if type(target.position[1]) is not tuple or len(target.position[1])!=3:raise ReceiptDescriptorRejected('invalid Target position')
                for number in target.position[1]:_validate_encoded(number)
            else:raise ReceiptDescriptorRejected('unknown Target position version')
        for fence in receipt.start_fences:
            if (type(fence) is not tuple or len(fence)!=5 or type(fence[1]) is not str
                    or any(type(seq) is not tuple or any(type(x) is not str for x in seq) for seq in fence[2:])):
                raise ReceiptDescriptorRejected('unknown start-fence descriptor fields')
            _validate_encoded(fence[0])
        _validate_encoded(receipt.start)
        _validate_encoded(receipt.rng_after)
    committed_ids=set()
    for choice in d['committed_choices']:
        _closed(choice,PortableCommittedChoice);_id(choice.choice_id,'Choice')
        if choice.choice_id in all_choices or type(choice.version) is not int or choice.version<1:raise ReceiptDescriptorRejected('ambiguous committed choice')
        all_choices.add(choice.choice_id)
        if type(choice.action_ids) is not tuple or not choice.action_ids or not set(choice.action_ids)<=all_actions:raise ReceiptDescriptorRejected('committed choice has missing Action links')
        committed_ids.update(choice.action_ids)
    if committed_ids!=all_actions:raise ReceiptDescriptorRejected('committed choice coverage is incomplete')
    action_choice={aid:choice.choice_id for choice in d['committed_choices'] for aid in choice.action_ids}
    if set(lifecycle_choices)!=all_actions or lifecycle_choices!=action_choice:
        raise ReceiptDescriptorRejected('committed Choice references disagree with Action lifecycle effects')
    future_ids=set()
    for choice in d['accepted_future_choices']:
        choice_data=_validate_future_choice(choice)
        def prim(x):return x is None or type(x) in (str,bool,int) or type(x) is tuple and all(prim(y) for y in x)
        if not prim(choice_data):raise ReceiptDescriptorRejected('future choice contains a native handle')
        action_ids=choice_data[5]
        if type(action_ids) is not tuple or future_ids.intersection(action_ids) or all_actions.intersection(action_ids):
            raise ReceiptDescriptorRejected('ambiguous accepted future Action references')
        if _decoded_number(choice_data[6],'future choice start')<=prior:
            raise ReceiptDescriptorRejected('accepted choice is not wholly future to the receipt chain')
        future_ids.update(action_ids)
    # The complete result graph is primitive tuples only; no native handles/classes survive.
    def primitive(x):
        if x is None or type(x) in (str,bool,int):return True
        return type(x) is tuple and all(primitive(y) for y in x)
    if not primitive(_receipt_data(value)):
        raise ReceiptDescriptorRejected('non-data receipt root')
    return True


def plan_receipt_rebinding(descriptor):
    """Return obligations only; never allocate objects or issue/authenticate receipts."""
    validate_receipt_descriptor(descriptor)
    entity_ids=set();action_ids=[];choice_ids=[];boundaries=[]
    for receipt in descriptor.receipts:
        boundaries.append(receipt.boundary)
        if type(receipt) in (PortableMovementOnlyBoundaryReceipt,
                             PortableContinuingMovementBoundaryReceipt):
            entity_ids.update(receipt.participant_ids)
        if type(receipt) is PortableBoundaryReceipt:
            for action in receipt.actions:
                action_ids.append(action.action_id);entity_ids.add(action.actor_id)
                if action.target_id is not None:entity_ids.add(action.target_id)
        for row in receipt.targets:
            entity_ids.add(row.target_id)
            state=_tagged_fields(row.state,'target.candidate/1')
            entity_ids.update(_reference_set(state['aware_of'],'Target awareness'))
    for choice in descriptor.accepted_future_choices:
        data=choice.to_data()
        for member in data[7]:
            action_ids.append(member[2])
            fields_data=member[3]
            for key,reference in fields_data:
                if key in ('actor_id','target_id') and type(reference) is tuple and len(reference)==2 and reference[0]=='entity':
                    entity_ids.add(reference[1])
    choice_ids.extend(row.choice_id for row in descriptor.committed_choices)
    choice_ids.extend(row.to_data()[1] for row in descriptor.accepted_future_choices)
    return ReceiptRebindingPlan(REBINDING_SCHEMA,descriptor.content_digest,descriptor.universe_id,
        descriptor.encounter_id,tuple(sorted(entity_ids)),tuple(action_ids),tuple(choice_ids),
        tuple(boundaries),_STEPS)


def _receipt_data(value):
    return (value.schema,value.universe_id,value.encounter_id,value.start_time,
        tuple(row.to_data() for row in value.receipts),
        tuple(row.to_data() for row in value.committed_choices),
        tuple(row.to_data() for row in value.accepted_future_choices),value.rng_ownership)
