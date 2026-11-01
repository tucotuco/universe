"""Inactive native shared objective Reality (Universe 4 Increment 5B2).

No observer checks/noise, evidence, testimony, completion, ledger commit, or
world publication. A companion is explicitly a supported-native fragment.
"""
from dataclasses import dataclass, field, replace
import math
from types import MappingProxyType, MethodType

from action_evaluation import (EvaluationSnapshot, EvaluationIntegrityError,
    UnsupportedEvaluation, native_data, freeze)
from frozen_practice import (FrozenHistoryFact, _copy_key, validate_history_constraints)
from realization import Fact, FactKey, CommittedFact, RealityLedger, ImpossibleRealization


def _check(test, reason):
    if not test:
        raise EvaluationIntegrityError(reason)


def _thaw(value):
    if type(value) is MappingProxyType:
        return {k: _thaw(v) for k, v in value.items()}
    if type(value) is tuple:
        return [_thaw(v) for v in value]
    return value


@dataclass(frozen=True)
class DeclaredObjectiveFact:
    key: FactKey
    value: object
    origin: str


@dataclass(frozen=True)
class EpisodeFacts:
    """Reviewed literal Fact recipe; never invents a narrative or training rank.

    Native AskAboutPastAction accepts this callable just like a literal-return
    generator. Pure capture reads its detached declarations without calling it.
    Arbitrary Python generators and subclasses are not adapters.
    """
    facts: tuple

    def __post_init__(self):
        _check(type(self.facts) is tuple, 'literal episode facts must be a tuple')
        copied = []
        for fact in self.facts:
            _check(type(fact) is Fact, 'literal recipe requires native Facts')
            key = _copy_key(fact.key)
            _check(type(fact.origin) is str and bool(fact.origin.strip()), 'invalid fact origin')
            copied.append(DeclaredObjectiveFact(key, freeze(fact.value), fact.origin))
        object.__setattr__(self, 'facts', tuple(copied))

    def __call__(self, history, view):
        # Legacy explicit use remains possible. Pure evaluation never calls this.
        return tuple(Fact(f.key, _thaw(f.value), f.origin) for f in self.facts)


@dataclass(frozen=True)
class ObjectiveActionInput:
    action_id: str
    family: str
    recipe: tuple = ()
    coarse_range: float | None = None


@dataclass(frozen=True)
class FrozenGroupObjective:
    group_id: str
    seed: int
    formation_time: float
    ledger_identity: int
    revision: int
    composition: object
    records: tuple
    cached_counts: object


@dataclass(frozen=True)
class FrozenObjectiveInputs:
    actions: object
    groups: object


@dataclass(frozen=True)
class ObjectiveContext:
    snapshot: EvaluationSnapshot
    native_snapshot: EvaluationSnapshot
    schema: str = 'native-objective-context-v1-inactive'
    observer_inputs: object = None


@dataclass(frozen=True)
class ObjectiveFact:
    key: FactKey
    value: object
    established: bool
    committed_revision: int | None
    origins: tuple
    requesting_action_ids: tuple
    supporting_keys: tuple = ()


@dataclass(frozen=True)
class SubjectRealityCandidate:
    subject_id: str
    ledger_identity: int
    base_revision: int
    facts: object
    counts: object = None

    def fact(self, key):
        return self.facts[key]


@dataclass(frozen=True)
class ObjectiveRequestResult:
    action_id: str
    subject_id: str
    requested_key: FactKey
    status: str
    supporting_keys: tuple


@dataclass(frozen=True)
class ObjectiveDraw:
    group_id: str
    stream_parts: tuple
    value: int


@dataclass(frozen=True)
class ObjectiveCandidate:
    subjects: object
    requests: object
    draws: tuple
    context: ObjectiveContext = field(repr=False, compare=False)
    companion: object = field(repr=False, compare=False)
    validation: str = 'objective_validated_against_native_practice_fragment'
    ready_for_publication: bool = False
    missing_dependencies: tuple = ('5B3_observer_checks_evidence_belief_testimony_and_lifecycle',
        '5C_whole_interval_publication_and_recovery', 'D7_checkpoint_replay_compatibility')

    def subject(self, subject_id):
        return self.subjects[subject_id]


def objective_action_data(action):
    """Read only reviewed declaration fields; retain no generator/observer handle."""
    from group_observation import ObserveGroupAction, SampledGroupObservation
    from history_conversation import AskAboutPastAction
    from field_interpretation import FieldInterpreter
    from activities import SpotAction
    if type(action) not in (ObserveGroupAction, AskAboutPastAction, SpotAction):
        raise UnsupportedEvaluation('unreviewed objective Action')
    data = object.__getattribute__(action, '__dict__')
    if any(callable(v) for k, v in data.items() if k != 'generate'):
        raise UnsupportedEvaluation('opaque objective Action override')
    if type(action) is AskAboutPastAction:
        recipe = data['generate']
        if type(recipe) is not EpisodeFacts:
            raise UnsupportedEvaluation('history requires reviewed literal EpisodeFacts; opaque generators are unsupported')
        # Copy primitives again; no mutable recipe value escapes.
        rd = native_data(recipe, (EpisodeFacts,))
        _check(type(rd['facts']) is tuple, 'opaque literal fact set')
        copied = []
        for fact in rd['facts']:
            fd = native_data(fact, (DeclaredObjectiveFact,))
            _check(type(fd['origin']) is str and bool(fd['origin']), 'invalid literal origin')
            copied.append(DeclaredObjectiveFact(_copy_key(fd['key']), freeze(fd['value']), fd['origin']))
        facts = tuple(copied)
        return data, ObjectiveActionInput(data['id'], 'history_request', facts)
    if type(action) is SpotAction:
        from statistical_group import StatisticalGroup
        world = object.__getattribute__(data['universe'], '__dict__')
        group = world['object_registry'].object_instances.get(data['target_id'])
        if (type(group) is not StatisticalGroup or data.get('group_fully_visible') is not True
                or data.get('ledger') is None):
            raise UnsupportedEvaluation('exact Spot-to-Group evidence requires a fully visible Group premise and owner BeliefLedger')
        from field_observation import BeliefLedger
        if type(data['ledger']) is not BeliefLedger or data['ledger'].observer_id != data['actor_id']:
            raise UnsupportedEvaluation('exact Spot-to-Group evidence ledger owner mismatch')
        return data, ObjectiveActionInput(data['id'], 'spot')
    observer = native_data(data['observer'], (SampledGroupObservation,))
    native_data(data['interpreter'], (FieldInterpreter,))
    freeze(observer)  # Reject opaque nested sensor configuration, do not sample it.
    coarse = observer['coarse_range_m']
    _check(type(coarse) in (int, float) and math.isfinite(coarse) and coarse > 0, 'invalid native range')
    return data, ObjectiveActionInput(data['id'], 'observe_group', coarse_range=coarse)


def _frozen_group(group):
    from statistical_group import StatisticalGroup, validate_composition_records
    data = native_data(group, (StatisticalGroup,))
    _check(type(data['seed']) is int and type(data['formation_time']) in (int, float)
        and math.isfinite(data['formation_time']), 'invalid group key/formation time')
    config = data['config']
    _check(type(config) is dict, 'opaque group configuration')
    composition = freeze(config['composition'])
    ledger = data['_composition_reality']; ld = native_data(ledger, (RealityLedger,))
    validators = ld['_validators']
    if (type(validators) is not tuple or len(validators) != 1 or type(validators[0]) is not MethodType
            or validators[0].__self__ is not group
            or validators[0].__func__ is not StatisticalGroup._validate_composition_facts):
        raise UnsupportedEvaluation('custom composition validator requires a pure adapter')
    _check(type(ld['_records']) is dict and type(ld['_revision']) is int and ld['_revision'] >= 0, 'invalid group ledger')
    records = []
    for key, record in ld['_records'].items():
        copied_key = _copy_key(key); rd = native_data(record, (CommittedFact,))
        _check(copied_key == _copy_key(rd['key']), 'composition key/record mismatch')
        _check(type(rd['revision']) is int and 1 <= rd['revision'] <= ld['_revision'], 'invalid composition revision')
        _check(type(rd['origin']) is str and bool(rd['origin']), 'invalid composition origin')
        records.append(FrozenHistoryFact(copied_key, freeze(rd['value']), rd['origin'], rd['revision']))
    revisions = [r.revision for r in records]
    _check(revisions == sorted(revisions) and set(revisions) == set(range(1, ld['_revision'] + 1)), 'inconsistent group revisions')
    validate_composition_records(data['id'], data['formation_time'], records)
    return FrozenGroupObjective(data['id'], data['seed'], data['formation_time'], id(ledger), ld['_revision'],
        composition, tuple(records), freeze(data['_counts']))


def capture_objective_inputs(objects, action_inputs, entity_ids):
    from statistical_group import StatisticalGroup
    groups = {key: _frozen_group(objects[key]) for key in entity_ids if type(objects[key]) is StatisticalGroup}
    return FrozenObjectiveInputs(MappingProxyType(dict(action_inputs)), MappingProxyType(groups))


def capture_objective_context(encounter, boundary, *, rng_state=None, _stage=None,
                              _restore_context=None):
    """Opt-in complete frozen read set, with explicitly separated Action coverage."""
    from action_evaluation import capture_snapshot
    snapshot = capture_snapshot(encounter, boundary, rng_state=rng_state, _objective=True,
        _stage=_stage,_restore_context=_restore_context)
    inputs = snapshot.objective_inputs
    excluded = tuple(sorted(key for key in snapshot.actions if key in inputs.actions
                     and snapshot.actions[key].family in ('observe_group', 'history_request')))
    native = replace(snapshot, actions=MappingProxyType({k: a for k, a in snapshot.actions.items() if k not in excluded}),
        objective_inputs=None, omitted_objective_action_ids=excluded)
    return ObjectiveContext(snapshot, native)


def evaluate_native_companion(context):
    from action_evaluation import evaluate_snapshot
    from action_settlement import reconcile_boundary
    _check(type(context) is ObjectiveContext, 'native objective context required')
    return reconcile_boundary(context.native_snapshot, evaluate_snapshot(context.native_snapshot))


def _key_order(key):
    return (key.entity_id, key.time is not None, 0 if key.time is None else key.time, key.attribute, key.detail)


def _counts(group, facts):
    from statistical_group import StatisticalGroup
    root_key = FactKey(group.group_id, 'household_count', group.formation_time)
    root = facts.get(root_key)
    _check(root is not None and type(root.value) is int and root.value >= 0, 'missing/invalid household root')
    totals = {key: 0 for key in StatisticalGroup.CATEGORIES}
    for index in range(root.value):
        key = FactKey(group.group_id, 'household', group.formation_time, str(index))
        if key not in facts:
            raise ImpossibleRealization('aggregate cache lacks supporting household facts')
        for category, value in facts[key].value.items():
            totals[category] += value
    totals['humans'] = totals['adults'] + totals['children']; totals['households'] = root.value
    return totals


def _group_candidate(group, action_ids):
    from statistical_group import _draw_cdf, composition_rng, validate_composition_records, StatisticalGroup
    facts = {r.key: ObjectiveFact(r.key, r.value, True, r.revision, (r.origin,), action_ids) for r in group.records}
    if group.cached_counts is not None:
        expected_keys = set(StatisticalGroup.CATEGORIES) | {'humans', 'households'}
        _check(type(group.cached_counts) is MappingProxyType and set(group.cached_counts) == expected_keys
            and all(type(v) is int and v >= 0 for v in group.cached_counts.values()), 'invalid aggregate cache values')
        if dict(group.cached_counts) != _counts(group, facts):
            raise ImpossibleRealization('aggregate cache contradicts committed composition')
    draws = []
    def draw(points, parts):
        # Same native CDF and exact seed token; only detached list data is used.
        value = _draw_cdf([list(pair) for pair in points], composition_rng(group.seed, group.group_id, *parts))
        draws.append(ObjectiveDraw(group.group_id, parts, value))
        return value
    root = FactKey(group.group_id, 'household_count', group.formation_time)
    if root not in facts:
        value = draw(group.composition['households_cdf'], ('household_count',))
        facts[root] = ObjectiveFact(root, value, False, None, ('formation_cdf',), action_ids)
    _check(type(facts[root].value) is int and facts[root].value >= 0, 'unresolved/invalid committed household root')
    for index in range(facts[root].value):
        key = FactKey(group.group_id, 'household', group.formation_time, str(index))
        if key not in facts:
            value = {category: draw(group.composition['per_household'][category+'_cdf'], ('household', index, category)) for category in StatisticalGroup.CATEGORIES}
            facts[key] = ObjectiveFact(key, freeze(value), False, None, ('formation_cdf',), action_ids)
    validate_composition_records(group.group_id, group.formation_time, tuple(facts.values()))
    totals = _counts(group, facts)
    supports = tuple(k for k in facts if k != root)
    facts[root] = replace(facts[root], supporting_keys=supports)
    return SubjectRealityCandidate(group.group_id, group.ledger_identity, group.revision, MappingProxyType(facts), freeze(totals)), tuple(draws)


def _history_candidate(history, requested, practice):
    facts = {r.key: ObjectiveFact(r.key, r.value, True, r.revision, (r.origin,), ()) for r in history.records}
    supports = {}
    # Do not regenerate established requested episodes, as native ask() does.
    known = frozenset(facts)
    for action_id, key, recipe in sorted(requested, key=lambda item: item[0]):
        if key in known:
            related = []
            value = facts[key].value
            if 'skill' in value:
                related.append(FactKey(history.being_id, 'skill_rank', key.time, value['skill']))
            supports[action_id] = tuple(related)
            for used in (key, *related):
                _check(used in facts, 'known episode missing supporting rank')
                f = facts[used]
                facts[used] = replace(f, requesting_action_ids=tuple(sorted(set(f.requesting_action_ids) | {action_id})))
            continue
        _check(any(f.key == key for f in recipe), 'literal generator did not propose requested episode')
        supports[action_id] = tuple(sorted((f.key for f in recipe if f.key != key), key=_key_order))
        for declared in recipe:
            previous = facts.get(declared.key)
            if previous is not None:
                # Native JSON value types distinguish int/bool and list/object.
                if type(previous.value) is not type(declared.value) or previous.value != declared.value:
                    raise ImpossibleRealization('conflicting objective claim for '+repr(declared.key))
                origins = previous.origins if previous.established else tuple(sorted(set(previous.origins) | {declared.origin}))
                facts[declared.key] = replace(previous, origins=origins,
                    requesting_action_ids=tuple(sorted(set(previous.requesting_action_ids) | {action_id})))
            else:
                facts[declared.key] = ObjectiveFact(declared.key, declared.value, False, None, (declared.origin,), (action_id,))
    uses = practice.prior_uses + practice.transitions
    validate_history_constraints(history.being_id, history.earliest, history.known_through,
        history.nondeclining_skills, tuple(facts.values()), uses)
    for action_id, key, _ in requested:
        fact = facts[key]
        combined = set(fact.supporting_keys) | set(supports[action_id])
        facts[key] = replace(fact, supporting_keys=tuple(sorted(combined, key=_key_order)))
    return SubjectRealityCandidate(history.being_id, history.ledger_identity, history.revision,
        MappingProxyType(dict(sorted(facts.items(), key=lambda pair: _key_order(pair[0]))))), supports


def build_objective_candidate(context, companion, *, active_requests=None):
    """All-or-nothing objective fragment, jointly checked against native practice.

    Observation d20/evidence and group-observation XP are deliberately uncomputed.
    Group requests are potential dependencies, not successful observations.
    """
    from action_settlement import BoundaryCandidate
    _check(type(context) is ObjectiveContext and context.schema == 'native-objective-context-v1-inactive', 'invalid objective context')
    _check(type(companion) is BoundaryCandidate and companion.source_snapshot is context.native_snapshot,
        'unrelated/forged companion snapshot')
    snapshot = context.snapshot; native = context.native_snapshot
    _check(type(snapshot) is EvaluationSnapshot and type(native) is EvaluationSnapshot, 'invalid common snapshot types')
    _check(type(snapshot.objective_inputs) is FrozenObjectiveInputs, 'missing objective inputs')
    excluded = tuple(sorted(key for key, action in snapshot.actions.items()
        if action.family in ('observe_group', 'history_request')))
    spot_group_requests = {key for key, declared in snapshot.objective_inputs.actions.items()
        if declared.family == 'spot' and snapshot.actions[key].family == 'spot'}
    _check(type(native.omitted_objective_action_ids) is tuple
        and len(native.omitted_objective_action_ids) == len(set(native.omitted_objective_action_ids))
        and set(native.omitted_objective_action_ids) == set(excluded)
        and set(native.actions) == set(snapshot.actions)-set(excluded), 'incompatible fragment coverage')
    _check(native.encounter_id == snapshot.encounter_id and native.boundary == snapshot.boundary
        and native.entities is snapshot.entities and native.practice_inputs is snapshot.practice_inputs
        and native.awareness is snapshot.awareness and native.fatigue is snapshot.fatigue
        and native.physiology is snapshot.physiology and native.rng_state is snapshot.rng_state
        and native.difficulty == snapshot.difficulty and native.objective_inputs is None
        and all(native.actions[k] is snapshot.actions[k] for k in native.actions), 'different common read boundary')
    _check(set(snapshot.objective_inputs.actions) == set(excluded) | spot_group_requests
        and {k for k, a in snapshot.actions.items() if a.family in ('observe_group','history_request')} == set(excluded),
        'missing/extra objective declaration')
    for key, declared in snapshot.objective_inputs.actions.items():
        _check(type(declared) is ObjectiveActionInput and declared.action_id == key
            and declared.family == snapshot.actions[key].family, 'objective request/declaration identity mismatch')
    # Require the exact candidate producer, not matching IDs alone. Reconcile is
    # deterministic and write-free; compare the supplied projection to a fresh
    # reduction of its already-calculated evaluation (no reevaluation/draws).
    _check(companion.evaluation is not None and companion.evaluation.snapshot is native, 'missing companion evaluation provenance')
    from action_settlement import reconcile_boundary, TargetCandidate
    _check(type(companion.targets) is MappingProxyType and type(companion.actions) is MappingProxyType
        and type(companion.effects) is MappingProxyType and all(type(t) is TargetCandidate for t in companion.targets.values()), 'opaque companion projection')
    _check(reconcile_boundary(native, companion.evaluation) == companion, 'companion contents contradict native evaluation')
    if active_requests is not None:
        _check(type(active_requests) is frozenset and active_requests.issubset(snapshot.objective_inputs.actions), 'invalid active objective selection')
    requests, group_requests, history_requests = {}, {}, {}
    for aid, incoming in snapshot.objective_inputs.actions.items():
        action = snapshot.actions[aid]
        if action.boundary != snapshot.boundary or action.lifecycle != 'pending':
            continue
        _check(action.start < snapshot.boundary, 'objective Action not started')
        subject = action.target_id
        distance = snapshot.distance(action.actor_id, subject)
        group_request = incoming.family in ('observe_group', 'spot')
        key = (FactKey(subject, 'household_count', snapshot.objective_inputs.groups[subject].formation_time)
               if group_request else FactKey(subject, 'episode', action.data['episode_time'], action.data['topic']))
        if incoming.family == 'spot':
            # Native Spot's geometric discovery result is the only success gate;
            # this adapter adds no Group-specific range or success check.
            status = None
        else:
            limit = incoming.coarse_range if incoming.family == 'observe_group' else action.data['max_distance']
            status = 'unplaced' if distance is None else 'out_of_range' if distance > limit else None
        if status is None and incoming.family == 'history_request' and subject not in snapshot.awareness.get(action.actor_id, ()):
            status = 'not_aware'
        if status is not None:
            requests[aid] = ObjectiveRequestResult(aid, subject, key, status, ())
            continue
        if active_requests is not None and aid not in active_requests:
            requests[aid] = ObjectiveRequestResult(aid, subject, key, 'not_required', ())
            continue
        if group_request:
            group_requests.setdefault(subject, []).append(aid)
        else:
            history = snapshot.practice_inputs.beings[subject].history
            _check(history is not None and history.earliest <= key.time <= history.known_through, 'episode outside frozen history window')
            history_requests.setdefault(subject, []).append((aid, key, incoming.recipe))
    subjects, draws = {}, []
    for subject in sorted(group_requests):
        aids = tuple(sorted(group_requests[subject]))
        candidate, new_draws = _group_candidate(snapshot.objective_inputs.groups[subject], aids)
        subjects[subject] = candidate; draws.extend(new_draws)
        root = FactKey(subject, 'household_count', snapshot.objective_inputs.groups[subject].formation_time)
        for aid in aids:
            requests[aid] = ObjectiveRequestResult(aid, subject, root, 'potential_observation_dependency', tuple(k for k in candidate.facts if k != root))
    for subject in sorted(history_requests):
        history = snapshot.practice_inputs.beings[subject].history
        practice = companion.target(subject).practice_state
        candidate, supports = _history_candidate(history, history_requests[subject], practice)
        subjects[subject] = candidate
        for aid, key, _ in history_requests[subject]:
            requests[aid] = ObjectiveRequestResult(aid, subject, key, 'objective_only', supports[aid])
    return ObjectiveCandidate(MappingProxyType(subjects), MappingProxyType(dict(sorted(requests.items()))),
        tuple(draws), context, companion)


def revalidate_complete_objective(objective, boundary):
    """Reuse already constructed facts; no new group samples or recipes."""
    from observer_proposals import validate_complete_context
    validate_complete_context(objective.context)
    _check(boundary.source_snapshot is objective.context.snapshot
        and boundary.evaluation.observer_context is objective.context,
        'full practice belongs to a different objective boundary')
    for subject, candidate in objective.subjects.items():
        frozen = objective.context.snapshot.practice_inputs.beings.get(subject)
        if frozen is not None and frozen.history is not None:
            h = frozen.history; practice = boundary.target(subject).practice_state
            validate_history_constraints(subject, h.earliest, h.known_through,
                h.nondeclining_skills, tuple(candidate.facts.values()), practice.prior_uses + practice.transitions)
    return replace(objective, companion=boundary,
        validation='objective_validated_against_complete_supported_practice',
        missing_dependencies=('5C_whole_interval_staging_publication_and_recovery', 'D7_checkpoint_replay_compatibility'))
