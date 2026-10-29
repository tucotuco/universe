"""Explicit developer-only presentation of already detached native inspection.

No live graph access, ownership conversion, I/O, sampling, evaluation or replay.
Acquire a view through Encounter.inspect_committed() before calling these pure
functions. Formatting a DTO is not authentication of an Encounter or receipt.
"""
from dataclasses import dataclass, fields
from html import escape
import json
from types import MappingProxyType

from encounter_inspection import (EncounterInspection, ActionInspection,
    TargetInspection, BoundaryInspection, ObjectiveInspection, detached)
from action_evaluation import UnsupportedEvaluation, EvaluationIntegrityError
from interval_staging import QueueProjection
from observer_proposals import BeliefProjection, AccountsProjection, ReservationReleaseEffect

LABEL = ('Developer / omniscient / read-only / same-process committed inspection; '
         'NOT a player or AI perspective; NOT a save or replay')
_SCHEMA = 'native-committed-inspection-v1'
_AUDIENCE = 'omniscient inspection; not observer-filtered policy or replay'
_MAX_NODES = 100_000
_MAX_DEPTH = 40
_MAX_STRING = 65_536
_MAX_OUTPUT = 8 * 1024 * 1024


class PresentationRejected(ValueError):
    """Unsupported DTO/audience or explicit presentation size limit exceeded."""


def _require(condition, message):
    if not condition:
        raise PresentationRejected(message)


class _Budget:
    def __init__(self):
        self.nodes = 0

    def visit(self, depth):
        self.nodes += 1
        _require(depth <= _MAX_DEPTH and self.nodes <= _MAX_NODES,
                 'presentation view limit exceeded; no partial output produced')


def _immutable(value, budget, depth=0):
    """After the native closed copier succeeds, reject mutable DTO contents."""
    budget.visit(depth)
    kind = type(value)
    if value is None or kind in (bool, int, float):
        return
    if kind is str:
        _require(len(value) <= _MAX_STRING, 'presentation string limit exceeded; no truncation')
    elif kind is MappingProxyType:
        for key, item in value.items():
            _immutable(key, budget, depth+1); _immutable(item, budget, depth+1)
    elif kind in (tuple, frozenset):
        for item in value:
            _immutable(item, budget, depth+1)
    else:
        _require(kind not in (dict, list, set), 'presentation requires a frozen native DTO')
        # Type/fields have already passed encounter_inspection.detached's closed
        # native adapters. No arbitrary __str__, repr, serializer or constructor.
        for item in object.__getattribute__(value, '__dict__').values():
            _immutable(item, budget, depth+1)


def _checked(view):
    _require(type(view) is EncounterInspection, 'native EncounterInspection required')
    data = object.__getattribute__(view, '__dict__')
    _require(type(data.get('schema')) is str and data['schema'] == _SCHEMA,
             'unsupported inspection schema')
    _require(type(data.get('audience')) is str and data['audience'] == _AUDIENCE,
             'only omniscient developer inspection is supported')
    try:
        copy = detached(view)  # Reuse native opaque-value refusal, not receipt authentication.
        _immutable(view, _Budget())
    except (UnsupportedEvaluation, EvaluationIntegrityError, RecursionError, AttributeError, KeyError) as exc:
        raise PresentationRejected('unsupported or incomplete frozen inspection data') from exc
    for field, cls in (('actions',ActionInspection), ('targets',TargetInspection),
                       ('objective',ObjectiveInspection)):
        mapping = getattr(copy,field)
        _require(type(mapping) is MappingProxyType and all(type(v) is cls for v in mapping.values()),
                 'incomplete inspection display mapping')
    _require(type(copy.encounter_id) is str and type(copy.boundary) is int
        and type(copy.latest_boundary) is int and copy.latest_boundary >= copy.boundary >= 1,
        'incomplete inspection scope')
    _require(type(copy.timeline) is tuple and bool(copy.timeline)
        and all(type(row) is BoundaryInspection for row in copy.timeline)
        and copy.timeline[-1].boundary == copy.boundary, 'incomplete committed timeline display')
    _require(type(copy.histories) is MappingProxyType and set(copy.histories) == set(copy.targets)
        and all(type(rows) is tuple and rows and all(type(row) is TargetInspection for row in rows)
                for rows in copy.histories.values()), 'incomplete Target history display')
    _require(type(copy.schedule) is QueueProjection, 'incomplete committed schedule display')
    _require(all(type(getattr(copy,field)) is MappingProxyType for field in ('effects','recipients'))
        and type(copy.objective_use) is tuple and type(copy.participants) is tuple,
        'incomplete inspection display collections')
    return copy


def _scalar(value):
    kind = type(value)
    if value is None:
        return 'unavailable'
    if kind is str:
        # Quoted ASCII text makes embedded newlines, terminal escapes and bidi
        # controls inert too. HTML escaping is applied separately at its sink.
        return json.dumps(value, ensure_ascii=True)
    if kind is bool:
        return 'true' if value else 'false'
    if kind is int:
        try:
            return str(value)
        except ValueError as exc:
            raise PresentationRejected('numeric presentation limit exceeded') from exc
    if kind is float:
        return format(value, '.17g')
    raise PresentationRejected('unsupported scalar display value')


def _describe(value, depth=0):
    """Reviewed human-readable structure, not JSON/checkpoint serialization."""
    kind = type(value)
    if value is None or kind in (str, int, float, bool):
        return _scalar(value)
    if kind is MappingProxyType:
        if not value:
            return '(empty)'
        rows = sorted(((_describe(key),item) for key,item in value.items()),key=lambda pair:pair[0])
    elif kind in (tuple, frozenset):
        if not value:
            return '(none)'
        values = sorted(value,key=_describe) if kind is frozenset else value
        rows = [(str(index),item) for index,item in enumerate(values)]
    else:
        data=object.__getattribute__(value,'__dict__')
        rows=[(field.name,data[field.name]) for field in fields(kind)]
    lines=[] if kind in (MappingProxyType,tuple,frozenset) else [kind.__name__]
    for key,item in rows:
        description=_describe(item,depth+1)
        lines.append(key+': '+description.replace('\n','\n  '))
    return '\n'.join(lines)


@dataclass(frozen=True)
class _Section:
    anchor: str
    title: str
    summary: tuple
    details: tuple  # (heading, already safely described text)


def _sections(view):
    """Temporary presentation layout only; no result store or simulation rules."""
    scope = _Section('scope','Identity and committed scope',(
        'Encounter: '+_scalar(view.encounter_id),
        'Selected committed boundary: '+_scalar(view.boundary),
        'Latest committed boundary at acquisition: '+_scalar(view.latest_boundary),
        'Historical selection: '+('yes; selected state is not the latest checkpoint' if view.boundary < view.latest_boundary else 'no'),
        'Coverage: '+str(len(view.timeline))+' committed boundaries; '+str(len(view.actions))+' Actions; '+str(len(view.effects))+' effects.',
        'This document formats an acquired DTO; it does not reauthenticate the live Encounter.',
        'No paths or intermediate physical positions are inferred. Missing data is unavailable.',
    ),(('Participants',_describe(view.participants)),))
    timeline=[]
    for row in view.timeline:
        timeline.append(('Boundary '+str(row.boundary)+' | interval '+_scalar(row.start)+' -> '+str(row.boundary),
            'Due Action IDs:\n'+_describe(row.action_ids)+'\nEffect IDs:\n'+_describe(row.effect_ids)
            +'\nStart fences (including after-settlement starts):\n'+_describe(row.start_fences)))
    action_details=[]; defense_details=[]; lifecycle=[]
    actions=sorted(view.actions.items(),key=lambda pair:(pair[1].resolved_boundary,
        pair[1].declaration.priority,pair[1].declaration.order,pair[0]))
    for aid,action in actions:
        declaration=action.declaration
        lines=('Actor: '+_scalar(action.facts.actor_id), 'Targets:\n'+_describe(action.facts.target_ids),
            'Family: '+_scalar(declaration.family), 'Outcome: '+_scalar(action.facts.outcome),
            'Nominal start: '+_scalar(declaration.start)+'; nominal end: '+_scalar(declaration.nominal_end)
                +'; nominal deadline boundary: '+_scalar(declaration.boundary),
            'Actual resolution boundary: '+_scalar(action.resolved_boundary),
            'Actual ordinary damage by recipient/component:\n'+_describe(action.damage_by_target),
            'Fatal effect Target references (not ordinary damage):\n'+_describe(action.fatal_targets),
            'Own causal effect IDs:\n'+_describe(tuple(row.identity for row in action.effects)),
            'Recorded calculation metadata:\n'+_describe(action.facts.metadata))
        action_details.append(('Action '+_scalar(aid),'\n'.join(lines)))
        if action.defenses:
            defense_details.append(('Strike '+_scalar(aid)+' | all designated defenses',_describe(action.defenses)))
        lifecycle.append(('Action '+_scalar(aid),_describe(action.lifecycle)))
    targets=[]; histories=[]; practices=[]; observations=[]; accounts=[]; beliefs=[]
    for tid,target in sorted(view.targets.items()):
        state=target.state
        targets.append(('Target '+_scalar(tid)+' | '+_scalar(target.properties.name),
            'Category: '+_scalar(state.category)+'\nTarget HP before: '+_scalar(state.starting_hp)
            +'\nTarget HP after: '+_scalar(state.projected_hp)
            +'\nActual damage: '+_scalar(state.actual_damage)
            +'\nFatal floor reduction (Target-owned; applied once): '+_scalar(target.fatal_floor_reduction)
            +'\nFatal effect IDs:\n'+_describe(state.fatal_effect_ids)
            +'\nSelected-boundary position:\n'+_describe(target.position)
            +'\nIncoming ordinary damage by Action/component:\n'+_describe(target.damage_by_action)
            +'\nIncoming effect references (protection is not another damage charge):\n'+_describe(tuple(row.identity for row in state.incoming))
            +'\nOutgoing effect references:\n'+_describe(state.outgoing_effect_ids)
            +'\nPre-action properties (resulting practice is separate):\n'+_describe(target.properties.pre_action)))
        for row in view.histories[tid]:
            histories.append(('Target '+_scalar(tid)+' | boundary '+str(row.boundary),
                'Target HP before: '+_scalar(row.state.starting_hp)+'\nTarget HP after: '+_scalar(row.state.projected_hp)
                +'\nActual damage: '+_scalar(row.state.actual_damage)+'\nFatal floor reduction: '+_scalar(row.fatal_floor_reduction)
                +'\nPosition:\n'+_describe(row.position)+'\nCausal damage:\n'+_describe(row.damage_by_action)
                +'\nIncoming effect references:\n'+_describe(tuple(effect.identity for effect in row.state.incoming))
                +'\nHistorical awareness:\n'+_describe(row.state.aware_of)
                +'\nHistorical outgoing effects:\n'+_describe(row.state.outgoing_effect_ids)
                +'\nHistorical pre-action properties:\n'+_describe(row.properties.pre_action)
                +'\nTarget-owned practice transitions:\n'+_describe(None if row.state.practice_state is None else row.state.practice_state.transitions)
                +'\nObserver changes at this historical boundary:\n'+_describe(row.state.observer_state)))
        practice=state.practice_state
        if practice is not None:
            practices.append(('Target '+_scalar(tid)+' | practice and rank ownership',
                'Resulting ordinary levels:\n'+_describe(practice.ordinary_levels)
                +'\nResulting weapon levels:\n'+_describe(practice.weapon_levels)
                +'\nResulting skill experience:\n'+_describe(practice.skill_experience)
                +'\nPractice baselines:\n'+_describe(practice.baselines)
                +'\nCurrent-batch causal exercises:\n'+_describe(practice.exercises)
                +'\nCurrent-batch Target transitions:\n'+_describe(practice.transitions)
                +'\nComplete Target-owned SkillUse / BatchSkillUse history:\n'+_describe(target.practice_history)))
        observations.append(('Observer Target '+_scalar(tid),
            'Awareness:\n'+_describe(state.aware_of)+'\nEvidence and interpretation changes at selected boundary:\n'+_describe(state.observer_state)))
        if state.observer_state is not None and state.observer_state.heard_accounts:
            accounts.append(('Heard accounts by '+_scalar(tid),_describe(state.observer_state.heard_accounts)))
    for identity,projection in sorted(view.recipients.items(),key=lambda pair:_describe(pair[0])):
        if type(projection) is BeliefProjection:
            beliefs.append(('Belief recipient '+_describe(identity),_describe(projection)))
        elif type(projection) is AccountsProjection:
            accounts.append(('Account recipient '+_describe(identity),_describe(projection)))
        else:
            raise PresentationRejected('unsupported recipient presentation')
    reality=[('Objective subject '+_scalar(key),_describe(value)) for key,value in sorted(view.objective.items())]
    reality.append(('Objective requests, consumers and supporting provenance',_describe(view.objective_use)))
    releases=tuple(row for _,row in sorted(view.effects.items(),key=lambda pair:_describe(pair[0]))
                   if type(row.effect) is ReservationReleaseEffect)
    lifecycle.append(('Committed schedule, reservations and reference roles',_describe(view.schedule)))
    lifecycle.append(('Settled active-Object releases; after-settlement handoffs',_describe(releases)))
    effects=[('Effect '+_describe(key),_describe(row.effect)) for key,row in sorted(view.effects.items(),key=lambda pair:_describe(pair[0]))]
    return (scope,
        _Section('timeline','Chronological committed timeline',('Due sets and start fences are recorded data; no interpolated paths.',),tuple(timeline)),
        _Section('actions','Actions: causality and outcomes',('Action summaries contain own contributions, not resulting Target state.',),tuple(action_details)),
        _Section('targets','Targets: selected-boundary resulting state',('HP, resulting state and historical transitions belong to Targets.',),tuple(targets)),
        _Section('history','Target-owned historical transitions',('Earlier results come from the selected frozen history, never current live HP.',),tuple(histories)),
        _Section('defenses','All designated defenses',('Eligibility, success/failure, association and legitimate practice remain distinct.',),tuple(defense_details)),
        _Section('practice','Target-owned practice and experience',('Causal exercises remain distinct; a batch transition is not sequential Action rank gain.',),tuple(practices)),
        _Section('reality','Shared objective Reality',('Committed facts/revisions are objective; no missing truth is realized here.',
            'established_before describes the fact\'s latest represented reconciliation, not whether it is committed.'),tuple(reality)),
        _Section('observers','Observer-specific evidence and interpretation',('Different observations or Beliefs do not imply objective contradiction.',),tuple(observations)),
        _Section('beliefs','Belief recipients',('Subjective evidence/readings are separate from shared objective facts.',),tuple(beliefs)),
        _Section('testimony','Testimony and heard accounts',('A heard account is not an assertion of objective historical truth.',),tuple(accounts)),
        _Section('lifecycle','Lifecycle, cancellation and resource handoffs',('The schedule describes the selected commit, not later planning edits.',),tuple(lifecycle)),
        _Section('effects','Complete causal effect index',('Protection/interception and fatal flags are not additional ordinary HP damage.',),tuple(effects)))


def _bounded(text):
    _require(len(text) <= _MAX_OUTPUT, 'presentation output limit exceeded; no partial output produced')
    return text


def _layout(view):
    try:
        return _sections(_checked(view))
    except (AttributeError, KeyError, IndexError, TypeError) as exc:
        raise PresentationRejected('incomplete or unsupported inspection display fields') from exc


def format_inspection_text(view):
    """Pure terminal-safe text for a supported frozen omniscient developer DTO."""
    sections=_layout(view)
    lines=[LABEL,'','Complete view within fixed presentation limits; no silent truncation.']
    for section in sections:
        lines.extend(('',section.title,'='*len(section.title),*section.summary))
        for heading,description in section.details:
            lines.extend(('',heading,description))
        if not section.details:
            lines.append('(none recorded)')
    return _bounded('\n'.join(lines)+'\n')


_CSS = '''body{font:16px/1.5 system-ui,sans-serif;max-width:90rem;margin:2rem auto;padding:0 1rem;color:#172333;background:#f8fafc}
header{border-left:6px solid #995500;padding:1rem;background:#fff3cd}nav{display:flex;flex-wrap:wrap;gap:.8rem;margin:1rem 0}
section{border-top:1px solid #b8c4d4;padding:1rem 0}details{background:white;border:1px solid #cbd5e1;border-radius:4px;margin:.6rem 0;padding:.6rem}
summary{cursor:pointer;font-weight:600;white-space:pre-wrap;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:.88rem}
a{color:#174f80}h2{scroll-margin-top:1rem}@media print{body{max-width:none}details{break-inside:avoid}}'''


def render_inspection_html(view):
    """Return an inert offline HTML document; no I/O, links to players or scripts."""
    sections=_layout(view)
    output=['<!doctype html>','<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
        '<title>Developer committed Encounter inspection</title><style>'+_CSS+'</style></head><body>',
        '<header><h1>'+escape(LABEL,quote=True)+'</h1><p>Complete view within fixed presentation limits; no silent truncation.</p></header>',
        '<nav aria-label="Inspection sections">']
    for section in sections:
        output.append('<a href="#'+section.anchor+'">'+escape(section.title,quote=True)+'</a>')
    output.append('</nav><main>')
    for section in sections:
        output.append('<section id="'+section.anchor+'"><h2>'+escape(section.title,quote=True)+'</h2>')
        output.extend('<p>'+escape(line,quote=True)+'</p>' for line in section.summary)
        for heading,description in section.details:
            output.append('<details><summary>'+escape(heading,quote=True)+'</summary><pre>'+escape(description,quote=True)+'</pre></details>')
        if not section.details:
            output.append('<p>(none recorded)</p>')
        output.append('</section>')
    output.append('</main></body></html>')
    return _bounded('\n'.join(output)+'\n')
