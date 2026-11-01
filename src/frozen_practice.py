"""Frozen native practice inputs and inactive Target-owned batch progression.

No skill awards, facts, publication, callbacks, or stochastic operations. New
exercises describe causes; one per-skill Target transition owns resulting rank.
"""
from dataclasses import dataclass, fields
import hashlib
import json
import math
from types import MappingProxyType, MethodType

from experience import SkillUse, BatchSkillUse, practice_action_ids, level_from_practice
from realization import FactKey, ImpossibleRealization


class PracticeValidationError(ValueError):
    """Invalid practice or contradiction with established personal history."""


@dataclass(frozen=True)
class FrozenHistoryFact:
    key: FactKey
    value: object
    origin: str
    revision: int


@dataclass(frozen=True)
class FrozenHistory:
    being_id: str
    ledger_identity: int
    revision: int
    earliest: float
    known_through: float
    nondeclining_skills: frozenset
    records: tuple


@dataclass(frozen=True)
class FrozenBeingPractice:
    being_id: str
    ordinary_levels: object
    weapon_levels: object
    baselines: object
    skill_experience: object
    prior_uses: tuple
    history: FrozenHistory | None


@dataclass(frozen=True)
class FrozenPracticeInputs:
    definitions: object
    beings: object
    schema: str = 'native-frozen-practice-v1'


@dataclass(frozen=True)
class ImportedPracticePrefix:
    """Detached, validated imported Target practice; never live Being history.

    This is a structural/semantic adapter for a quarantined boundary-1 Run
    fixture. Its digest is a stable read-dependency token, not proof of
    checkpoint origin or receipt issuance.
    """
    universe_id: str
    encounter_id: str
    choice_id: str
    boundary: int
    target_id: str
    action_ids: tuple
    uses: tuple
    content_digest: str
    schema: str = 'universe.imported-run-practice-prefix/1'

    def to_data(self):
        _validate_imported_prefix(self)
        return _imported_prefix_data(self)


class ImportedPracticeRejected(PracticeValidationError):
    """Imported practice is outside the closed one-boundary Spot contract."""


@dataclass(frozen=True)
class CandidatePracticeUse:
    effect_identity: object
    skill_name: str
    experience: int
    action_id: str
    nominal_end: float
    resolved_at: int
    outcome: str


@dataclass(frozen=True)
class CandidateSkillTransition:
    being_id: str
    skill_name: str
    time: int
    level_before: int | float
    level_after: int | float
    baseline: int | float
    experience_before: int
    experience_after: int
    effect_ids: tuple


@dataclass(frozen=True)
class PracticeProjection:
    being_id: str
    ordinary_levels: object
    weapon_levels: object
    baselines: object
    skill_experience: object
    prior_uses: tuple
    exercises: tuple
    transitions: tuple
    history_revision: int | None

    def level(self, skill):
        value = self.ordinary_levels.get(skill)
        return (self.weapon_levels.get(skill) if value is None else value) or 0


def _check(test, message):
    if not test:
        raise PracticeValidationError(message)


def _name(value):
    _check(type(value) is str and bool(value.strip()), 'skill/identity must be a native nonempty string')
    return value


def _numeric(value):
    _check(type(value) in (int, float) and (type(value) is int or math.isfinite(value)), 'non-finite/opaque practice number')
    return value


def _rank(value):
    _check(_numeric(value) >= 0, 'negative rank/baseline')
    return value


def _xp(value):
    _check(type(value) is int and value >= 0, 'practice XP must be a nonnegative integer (not bool)')
    return value


def _rank_map(value):
    _check(type(value) in (dict, MappingProxyType), 'opaque rank mapping')
    return MappingProxyType({_name(k): _rank(v) for k, v in value.items()})


def _xp_map(value):
    _check(type(value) in (dict, MappingProxyType), 'opaque XP mapping')
    return MappingProxyType({_name(k): _xp(v) for k, v in value.items()})


def _copy_use(use):
    from action_evaluation import native_data, freeze
    if type(use) is BatchSkillUse:
        from action_evaluation import EffectIdentity
        data = native_data(use, (BatchSkillUse,))
        _name(data['being_id']); _name(data['skill_name']); _xp(data['experience'])
        _rank(data['level_before']); _rank(data['level_after'])
        _check(type(data['time']) is int and data['time'] > 0 and data['action_id'] is None
            and data['outcome'] == 'simultaneous' and type(data['exercises']) is tuple, 'invalid native batch history')
        exercises = []
        for item in data['exercises']:
            row = native_data(item, (CandidatePracticeUse,))
            effect = EffectIdentity(**freeze(native_data(row['effect_identity'], (EffectIdentity,))))
            args = {k:freeze(v) for k,v in row.items() if k != 'effect_identity'}
            _check(args['skill_name'] == data['skill_name'] and args['resolved_at'] == data['time']
                and effect.boundary == data['time'] and effect.source_action_id == args['action_id'], 'batch exercise identity mismatch')
            _name(args['action_id']); _xp(args['experience']); _numeric(args['nominal_end'])
            exercises.append(CandidatePracticeUse(effect, **args))
        _check(bool(exercises) and sum(x.experience for x in exercises) == data['experience']
            and len({x.action_id for x in exercises}) == len(exercises), 'invalid batch exercise coverage')
        return BatchSkillUse(data['being_id'], data['skill_name'], data['experience'], data['level_before'],
            data['level_after'], data['time'], tuple(exercises))
    data = freeze(native_data(use, (SkillUse,)))
    _name(data['skill_name']); _xp(data['experience'])
    _rank(data['level_before']); _rank(data['level_after'])
    if data['action_id'] is not None:
        _name(data['action_id'])
    if data['time'] is not None:
        _numeric(data['time'])
    _check(data['outcome'] is None or type(data['outcome']) is str, 'invalid skill-use outcome')
    return SkillUse(**{f.name: data[f.name] for f in fields(SkillUse)})


def _import_number(value, label):
    """Decode the projection's exact tagged number without coercive hooks."""
    _check(type(value) is tuple and len(value) == 2
        and value[0] in ('integer', 'binary64'), label + ' is not a tagged number')
    if value[0] == 'integer':
        text = value[1]
        _check(type(text) is str, label + ' integer is not text')
        try: result = int(text)
        except ValueError as exc: raise ImportedPracticeRejected(label + ' integer is malformed') from exc
        _check(str(result) == text, label + ' integer is not canonical')
        return result
    text = value[1]
    _check(type(text) is str, label + ' binary64 is not text')
    try: result = float.fromhex(text)
    except ValueError as exc: raise ImportedPracticeRejected(label + ' binary64 is malformed') from exc
    _check(math.isfinite(result) and result.hex() == text,
           label + ' binary64 is not canonical and finite')
    return result


def _import_record(value, tag, names, label):
    _check(type(value) is tuple and len(value) == 2 and value[0] == tag
        and type(value[1]) is tuple, label + ' has an unsupported record schema')
    rows = value[1]
    _check(all(type(row) is tuple and len(row) == 2 and type(row[0]) is str for row in rows)
        and tuple(row[0] for row in rows) == names,
        label + ' has missing, reordered, or unknown fields')
    return dict(rows)


def _import_mapping(value, label):
    _check(type(value) is tuple and len(value) == 2 and value[0] == 'mapping'
        and type(value[1]) is tuple, label + ' is not a closed mapping')
    result = {}
    for row in value[1]:
        _check(type(row) is tuple and len(row) == 2 and type(row[0]) is str
            and row[0] not in result, label + ' has an invalid/duplicate key')
        result[row[0]] = row[1]
    return result


def _projection_to_batch(sidecar):
    """Validate and detach the one supported sidecar batch into native frozen input."""
    from action_evaluation import EffectIdentity
    from checkpoint_binding import QuarantinedSpotHistoricalSidecar, BINDING_SCHEMA
    from checkpoint_projection import (QuarantinedSpotBoundaryProjection,
        PROJECTION_SCHEMA, PracticeExerciseProjection, PracticeTransitionProjection,
        BatchPracticeProjection, TargetProjection, SpotActionProjection, EffectProjection)

    _check(type(sidecar) is QuarantinedSpotHistoricalSidecar
        and sidecar.schema == 'universe.quarantined-spot-history-sidecar/1',
        'unsupported imported Spot sidecar')
    projection = sidecar.projection
    _check(type(projection) is QuarantinedSpotBoundaryProjection
        and projection.schema == PROJECTION_SCHEMA and projection.quarantined is True
        and projection.boundary == 1 and _import_number(projection.start, 'boundary start') == 0,
        'only the quarantined start-0/boundary-1 Spot projection is supported')
    _check(type(projection.actions) is tuple and len(projection.actions) == 2
        and all(type(row) is SpotActionProjection for row in projection.actions),
        'import requires exactly two native Spot Action records')
    actions = projection.actions
    actor_id, observed_id = actions[0].actor_id, actions[0].observed_id
    action_ids = tuple(action.action_id for action in actions)
    _check(type(actor_id) is str and actor_id and type(observed_id) is str
        and observed_id and actor_id != observed_id
        and all(action.actor_id == actor_id and action.observed_id == observed_id
                for action in actions), 'Spot Action actors/Targets disagree')
    _check(sidecar.being_identity_ids == (actor_id, observed_id)
        and sidecar.action_identity_ids == action_ids
        and sidecar.action_effect_links == tuple((action.action_id, action.effect_ids)
                                                  for action in actions)
        and sidecar.target_identity_ids == tuple(target.target_id for target in projection.targets),
        'sidecar identity/reference indexes disagree with the projection')
    _check(type(projection.committed_choices) is tuple and len(projection.committed_choices) == 1
        and type(projection.committed_choices[0]) is tuple
        and len(projection.committed_choices[0]) == 4,
        'committed Choice coverage is unsupported')
    choice_id, _version, _origin, choice_actions = projection.committed_choices[0]
    _check(type(choice_id) is str and choice_id == sidecar.choice_id
        and choice_actions == action_ids, 'Choice identity/membership is inconsistent')

    _check(type(projection.effects) is tuple
        and all(type(row) is EffectProjection for row in projection.effects),
        'unsupported projected effect collection')
    effects = {}
    for effect in projection.effects:
        _check(type(effect.identity) is tuple and len(effect.identity) == 6
            and effect.identity[0] == 'effect-id', 'malformed effect identity')
        _check(effect.identity not in effects, 'duplicate effect identity')
        effects[effect.identity] = effect

    _check(type(projection.targets) is tuple and len(projection.targets) == 2
        and all(type(row) is TargetProjection for row in projection.targets),
        'exact actor and observed-Being Target projections are required')
    targets = {target.target_id: target for target in projection.targets}
    _check(set(targets) == {actor_id, observed_id}, 'Target ownership/reference set is inconsistent')
    target = targets[actor_id]
    _check(type(target.batch_practice) is tuple and len(target.batch_practice) == 1
        and all(not row.batch_practice for row in projection.targets if row.target_id != actor_id),
        'exactly one actor-owned simultaneous practice batch is supported')
    batch = target.batch_practice[0]
    _check(type(batch) is BatchPracticeProjection and sidecar.batch_practice == (batch,),
        'sidecar batch differs from the actor Target projection')
    _check(batch.target_id == actor_id and batch.skill == 'spot'
        and batch.outcome == 'simultaneous' and len(batch.exercises) == 2,
        'unsupported Target, skill, outcome, or batch exercise coverage')
    transition_rows = target.practice_transitions
    _check(type(transition_rows) is tuple and len(transition_rows) == 1
        and type(transition_rows[0]) is PracticeTransitionProjection,
        'one Target-owned simultaneous transition is required')
    transition = transition_rows[0]
    boundary_time = _import_number(batch.time, 'batch time')
    _check(type(boundary_time) is int and boundary_time == projection.boundary
        and transition.target_id == actor_id and transition.skill == batch.skill
        and transition.time == batch.time
        and transition.level_before == batch.level_before
        and transition.level_after == batch.level_after,
        'Target transition timing/ranks disagree with its batch')
    _check(type(batch.exercises) is tuple
        and batch.exercises == target.practice_exercises
        and tuple(row.effect_id for row in batch.exercises) == transition.effect_ids,
        'batch exercise order/references differ from Target transition')

    exercise_uses = []
    seen_causes = set()
    for exercise in batch.exercises:
        _check(type(exercise) is PracticeExerciseProjection
            and exercise.skill == batch.skill and exercise.action_id in action_ids,
            'practice exercise has an unsupported skill or Action identity')
        key = (exercise.action_id, exercise.skill)
        _check(key not in seen_causes and exercise.effect_id not in seen_causes,
            'duplicate Action/skill or effect cause')
        seen_causes.add(key); seen_causes.add(exercise.effect_id)
        effect_identity = exercise.effect_id
        _check(type(effect_identity) is tuple and len(effect_identity) == 6
            and effect_identity[0] == 'effect-id'
            and effect_identity[1] == projection.encounter_id
            and effect_identity[2] == projection.boundary
            and effect_identity[3] == exercise.action_id
            and effect_identity[4] == 'effect'
            and type(effect_identity[5]) is int,
            'practice effect identity does not match its historical Action/boundary')
        effect = effects.get(effect_identity)
        _check(effect is not None and effect.kind == 'effect.practice/1',
            'practice effect reference is missing or has the wrong family')
        payload = _import_record(effect.payload, 'effect.practice/1',
            ('source_action_id', 'target_id', 'skill', 'experience'), 'practice effect')
        _check(payload['source_action_id'] == ('string', exercise.action_id)
            and payload['target_id'] == ('string', actor_id)
            and payload['skill'] == ('string', exercise.skill)
            and payload['experience'] == exercise.experience,
            'practice exercise does not match its causal effect payload')
        _check(_import_number(exercise.experience, 'exercise experience') >= 0
            and _import_number(exercise.resolved_at, 'exercise boundary') == projection.boundary,
            'exercise award or chronological boundary is invalid')
        action = next(row for row in actions if row.action_id == exercise.action_id)
        _check(exercise.nominal_end == action.end
            and _import_number(action.end, 'Action end') <= projection.boundary
            and _import_number(action.end, 'Action end') > _import_number(action.start, 'Action start')
            and exercise.outcome == action.outcome,
            'exercise timing/outcome differs from its source Action')
        amount = _import_number(exercise.experience, 'exercise experience')
        _check(type(amount) is int, 'native BatchSkillUse requires integer exercise awards')
        exercise_uses.append(CandidatePracticeUse(
            EffectIdentity(effect_identity[1], effect_identity[2], effect_identity[3],
                           effect_identity[4], effect_identity[5]),
            exercise.skill, amount, exercise.action_id,
            _import_number(exercise.nominal_end, 'nominal Action end'),
            _import_number(exercise.resolved_at, 'exercise boundary'), exercise.outcome))

    total = sum(row.experience for row in exercise_uses)
    batch_experience = _import_number(batch.experience, 'batch experience')
    before_xp = _import_number(transition.experience_before, 'pre-batch experience')
    after_xp = _import_number(transition.experience_after, 'post-batch experience')
    _check(type(batch_experience) is int and batch_experience == total
        and type(before_xp) is int and type(after_xp) is int
        and after_xp == before_xp + total,
        'simultaneous exercise totals disagree with Target practice transition')

    state = _import_record(target.state_data, 'target.candidate/1',
        ('target_id', 'category', 'starting_hp', 'projected_hp', 'actual_damage',
         'fatal_effect_ids', 'incoming', 'outgoing_effect_ids', 'aware_of',
         'practice_state', 'observer_state'), 'Target candidate')
    practice = _import_record(state['practice_state'], 'practice.projection/1',
        ('being_id', 'ordinary_levels', 'weapon_levels', 'baselines', 'skill_experience',
         'prior_uses', 'exercises', 'transitions', 'history_revision'), 'Target practice state')
    _check(practice['being_id'] == ('string', actor_id)
        and practice['history_revision'] == ('null',)
        and practice['prior_uses'] == ('sequence', ()),
        'personal-history-bound or preexisting practice history is unsupported')
    _check(type(practice['exercises']) is tuple and practice['exercises'][0] == 'sequence'
        and len(practice['exercises'][1]) == 2,
        'Target state has unsupported extra/missing practice exercises')
    _check(type(practice['transitions']) is tuple and practice['transitions'][0] == 'sequence'
        and len(practice['transitions'][1]) == 1,
        'Target state has unsupported extra/missing practice transitions')
    exercise_fields = ('effect_identity', 'skill_name', 'experience', 'action_id',
                       'nominal_end', 'resolved_at', 'outcome')
    for encoded_exercise, exercise in zip(practice['exercises'][1], batch.exercises):
        row = _import_record(encoded_exercise, 'practice.exercise/1', exercise_fields,
                             'Target state practice exercise')
        _check(row['effect_identity'] == exercise.effect_id
            and row['skill_name'] == ('string', exercise.skill)
            and row['experience'] == exercise.experience
            and row['action_id'] == ('string', exercise.action_id)
            and row['nominal_end'] == exercise.nominal_end
            and row['resolved_at'] == exercise.resolved_at
            and row['outcome'] == ('string', exercise.outcome),
            'Target state practice exercise differs from the imported causal row')
    transition_fields = ('being_id', 'skill_name', 'time', 'level_before', 'level_after',
                         'baseline', 'experience_before', 'experience_after', 'effect_ids')
    encoded_transition = _import_record(practice['transitions'][1][0],
        'practice.transition/1', transition_fields, 'Target state practice transition')
    _check(encoded_transition['being_id'] == ('string', transition.target_id)
        and encoded_transition['skill_name'] == ('string', transition.skill)
        and encoded_transition['time'] == transition.time
        and encoded_transition['level_before'] == transition.level_before
        and encoded_transition['level_after'] == transition.level_after
        and encoded_transition['baseline'] == transition.baseline
        and encoded_transition['experience_before'] == transition.experience_before
        and encoded_transition['experience_after'] == transition.experience_after
        and encoded_transition['effect_ids'] == ('sequence', transition.effect_ids),
        'Target state transition differs from imported batch provenance')
    _check(_import_mapping(practice['skill_experience'], 'Target skill experience').get(batch.skill)
        == transition.experience_after,
        'materialized Target experience does not equal the committed transition')
    for mapping_name in ('ordinary_levels', 'weapon_levels'):
        _import_mapping(practice[mapping_name], 'Target ' + mapping_name)
    rank_rows = (_import_mapping(practice['ordinary_levels'], 'Target ordinary levels'),
                 _import_mapping(practice['weapon_levels'], 'Target weapon levels'))
    ranks = [rows[batch.skill] for rows in rank_rows if batch.skill in rows]
    _check(len(ranks) == 1 and ranks[0] == transition.level_after,
        'materialized Target rank does not equal the committed transition')
    _check(_import_mapping(practice['baselines'], 'Target practice baselines').get(batch.skill)
        == transition.baseline,
        'materialized Target baseline disagrees with the committed transition')

    batch_use = BatchSkillUse(actor_id, batch.skill, batch_experience,
        _import_number(batch.level_before, 'batch level before'),
        _import_number(batch.level_after, 'batch level after'), boundary_time,
        tuple(exercise_uses), outcome='simultaneous')
    # Reuse the exact validator used by live native frozen-practice capture.
    copied = _copy_use(batch_use)
    return actor_id, action_ids, copied


def _practice_use_data(use):
    if type(use) is BatchSkillUse:
        return ('batch', use.being_id, use.skill_name, use.experience,
            use.level_before, use.level_after, use.time,
            tuple((row.effect_identity.encounter_id, row.effect_identity.boundary,
                   row.effect_identity.source_action_id, row.effect_identity.channel,
                   row.effect_identity.slot, row.skill_name, row.experience, row.action_id,
                   row.nominal_end, row.resolved_at, row.outcome) for row in use.exercises))
    return ('skill', use.skill_name, use.experience, use.level_before, use.level_after,
            use.action_id, use.time, use.outcome)


def _imported_prefix_data(prefix):
    return (prefix.schema, prefix.universe_id, prefix.encounter_id, prefix.choice_id,
        prefix.boundary, prefix.target_id, prefix.action_ids,
        tuple(_practice_use_data(row) for row in prefix.uses))


def _prefix_digest(data):
    raw = json.dumps(data, ensure_ascii=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode('ascii')).hexdigest()


def _validate_imported_prefix(prefix):
    _check(type(prefix) is ImportedPracticePrefix
        and prefix.schema == 'universe.imported-run-practice-prefix/1',
        'unknown imported-practice prefix/schema')
    _check(type(prefix.universe_id) is str and prefix.universe_id
        and type(prefix.encounter_id) is str and prefix.encounter_id
        and type(prefix.choice_id) is str and prefix.choice_id
        and type(prefix.target_id) is str and prefix.target_id
        and type(prefix.boundary) is int and prefix.boundary == 1,
        'invalid imported-practice logical root or boundary')
    _check(type(prefix.action_ids) is tuple and len(prefix.action_ids) == 1
        and all(type(row) is str and row for row in prefix.action_ids)
        and len(set(prefix.action_ids)) == 1,
        'invalid imported-practice Action identity set')
    _check(type(prefix.uses) is tuple and len(prefix.uses) == 1,
        'exactly one imported batch is supported')
    use = _copy_use(prefix.uses[0])
    _check(type(use) is BatchSkillUse and use.being_id == prefix.target_id
        and use.time == prefix.boundary and use.skill_name == 'run'
        and tuple(row.action_id for row in use.exercises) == prefix.action_ids,
        'imported batch ownership, chronology or causal Action order is inconsistent')
    _check(type(prefix.content_digest) is str and len(prefix.content_digest) == 64
        and prefix.content_digest == _prefix_digest(_imported_prefix_data(prefix)),
        'imported-practice prefix digest is stale')
    return use


def freeze_imported_run_practice(projection):
    """Convert one immutable Run projection into validated frozen prior-use data.

    The operation reads only the detached projection, preserves the native
    causal IDs, and never awards XP or mutates native history.
    """
    from action_evaluation import EffectIdentity
    from checkpoint_projection import (QuarantinedRunBoundaryProjection,
        PROJECTION_SCHEMA, RunActionProjection, TargetProjection, EffectProjection,
        BatchPracticeProjection, PracticeExerciseProjection,
        PracticeTransitionProjection)
    try:
        sidecar = None
        from checkpoint_binding import QuarantinedRunHistoricalSidecar
        if type(projection) is QuarantinedRunHistoricalSidecar:
            sidecar = projection
            _check(sidecar.schema == 'universe.quarantined-run-history-sidecar/1',
                'unsupported historical Run sidecar schema')
            projection = sidecar.projection
        _check(type(projection) is QuarantinedRunBoundaryProjection
            and projection.schema == PROJECTION_SCHEMA and projection.quarantined is True
            and projection.boundary == 1 and _import_number(projection.start, 'boundary start') == 0,
            'only the quarantined start-0/boundary-1 Run projection is supported')
        _check(type(projection.actions) is tuple and len(projection.actions) == 1
            and type(projection.actions[0]) is RunActionProjection,
            'exactly one native Run Action is required')
        action = projection.actions[0]
        _check(action.outcome in ('success', 'partial'),
            'Run Action did not produce a movement practice outcome')
        action_ids = (action.action_id,)
        _check(type(projection.targets) is tuple and len(projection.targets) == 2
            and all(type(row) is TargetProjection for row in projection.targets),
            'exact two participant Target projections are required')
        targets = {row.target_id: row for row in projection.targets}
        _check(len(targets) == 2 and action.actor_id in targets,
            'Run Target identity is missing or ambiguous')
        target = targets[action.actor_id]
        _check(type(target.batch_practice) is tuple and len(target.batch_practice) == 1
            and all(not row.batch_practice for row in projection.targets if row.target_id != action.actor_id),
            'exactly one actor-owned practice batch is supported')
        batch = target.batch_practice[0]
        _check(type(batch) is BatchPracticeProjection and batch.target_id == action.actor_id
            and batch.skill == 'run' and batch.outcome == 'simultaneous'
            and len(batch.exercises) == 1 and batch.exercises == target.practice_exercises,
            'unsupported Run Target practice batch')
        _check(type(target.practice_transitions) is tuple
            and len(target.practice_transitions) == 1,
            'exactly one Target-owned Run practice transition is required')
        transition = target.practice_transitions[0]
        _check(type(transition) is PracticeTransitionProjection
            and transition.target_id == action.actor_id and transition.skill == 'run'
            and transition.time == batch.time
            and transition.level_before == batch.level_before
            and transition.level_after == batch.level_after
            and transition.effect_ids == tuple(row.effect_id for row in batch.exercises),
            'Target practice transition does not match the Run batch')
        exercise = batch.exercises[0]
        _check(type(exercise) is PracticeExerciseProjection and exercise.skill == 'run'
            and exercise.action_id == action.action_id and exercise.outcome == action.outcome
            and exercise.nominal_end == action.end
            and _import_number(exercise.resolved_at, 'exercise boundary') == projection.boundary,
            'Run exercise causality or chronology is inconsistent')
        _check(type(projection.effects) is tuple
            and all(type(row) is EffectProjection for row in projection.effects),
            'unsupported effect collection')
        matching = tuple(row for row in projection.effects if row.identity == exercise.effect_id)
        _check(len(matching) == 1 and matching[0].kind == 'effect.practice/1',
            'Run exercise has no unique causal practice effect')
        payload = _import_record(matching[0].payload, 'effect.practice/1',
            ('source_action_id', 'target_id', 'skill', 'experience'), 'Run practice effect')
        _check(payload['source_action_id'] == ('string', action.action_id)
            and payload['target_id'] == ('string', action.actor_id)
            and payload['skill'] == ('string', 'run')
            and payload['experience'] == exercise.experience,
            'Run exercise differs from its causal practice effect')
        state = _import_record(target.state_data, 'target.candidate/1',
            ('target_id', 'category', 'starting_hp', 'projected_hp', 'actual_damage',
             'fatal_effect_ids', 'incoming', 'outgoing_effect_ids', 'aware_of',
             'practice_state', 'observer_state'), 'Target candidate')
        practice = _import_record(state['practice_state'], 'practice.projection/1',
            ('being_id', 'ordinary_levels', 'weapon_levels', 'baselines', 'skill_experience',
             'prior_uses', 'exercises', 'transitions', 'history_revision'), 'Target practice state')
        _check(practice['history_revision'] == ('null',)
            and practice['prior_uses'] == ('sequence', ()),
            'personal-history-bound or preexisting practice history is unsupported')
        xp = _import_number(exercise.experience, 'Run experience')
        before = _import_number(transition.experience_before, 'pre-Run experience')
        after = _import_number(transition.experience_after, 'post-Run experience')
        xp_value = _import_number(_import_mapping(practice['skill_experience'],
            'Target experience').get('run'), 'materialized Run experience')
        _check(type(xp) is int and after == before + xp and xp_value == after,
            'Target-owned Run experience transition is inconsistent')
        ranks = [_import_mapping(practice[name], 'Target rank mapping').get('run')
                 for name in ('ordinary_levels', 'weapon_levels')]
        ranks = [value for value in ranks if value is not None]
        rank_after = _import_number(transition.level_after, 'Target Run rank after')
        _check((len(ranks) == 1 and ranks[0] == transition.level_after)
            or (not ranks and rank_after == 0),
            'materialized Target Run rank differs from its transition')
        effect = exercise.effect_id
        _check(type(effect) is tuple and len(effect) == 6 and effect[:5] ==
            ('effect-id', projection.encounter_id, projection.boundary, action.action_id, 'effect'),
            'Run effect identity does not match Action and boundary')
        _check(effect in action.effect_ids,
            'Run Action effect references do not match its practice cause')
        use = CandidatePracticeUse(EffectIdentity(effect[1], effect[2], effect[3], effect[4], effect[5]),
            'run', xp, action.action_id, _import_number(exercise.nominal_end, 'Run end'),
            projection.boundary, action.outcome)
        batch_use = _copy_use(BatchSkillUse(action.actor_id, 'run', xp,
            _import_number(batch.level_before, 'Run rank before'),
            _import_number(batch.level_after, 'Run rank after'), projection.boundary,
            (use,), outcome='simultaneous'))
        choice_id, _version, _origin, choice_actions = projection.committed_choices[0]
        _check(choice_actions == action_ids, 'committed Choice does not identify the Run Action')
        provisional = ImportedPracticePrefix(projection.universe_id, projection.encounter_id,
            choice_id, projection.boundary, action.actor_id, action_ids, (batch_use,), '')
        prefix = ImportedPracticePrefix(provisional.universe_id, provisional.encounter_id,
            provisional.choice_id, provisional.boundary, provisional.target_id,
            provisional.action_ids, provisional.uses,
            _prefix_digest(_imported_prefix_data(provisional)))
        _validate_imported_prefix(prefix)
        if sidecar is not None:
            participant_ids = tuple(sorted(targets))
            expected_links = tuple((row.action_id, row.effect_ids)
                                   for row in projection.actions)
            expected_targets = tuple(row.target_id for row in projection.targets)
            _check(sidecar.choice_id == prefix.choice_id
                and sidecar.being_identity_ids == participant_ids
                and sidecar.action_identity_ids == action_ids
                and sidecar.action_effect_links == expected_links
                and sidecar.target_identity_ids == expected_targets
                and sidecar.batch_practice == (batch,),
                'Run sidecar identity, causal link, Target, Choice, or batch index is inconsistent')
        return prefix
    except ImportedPracticeRejected:
        raise
    except (AttributeError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise ImportedPracticeRejected('malformed imported Run practice prefix') from exc


def freeze_imported_spot_practice(sidecar):
    """Compatibility import name for the strict Run-only sidecar adapter."""
    return freeze_imported_run_practice(sidecar)


def merge_imported_practice_uses(prefix, being_id, native_suffix=()):
    """Return immutable chronological prior uses without writing Being history."""
    try:
        imported = _validate_imported_prefix(prefix)
        _check(type(being_id) is str and being_id == prefix.target_id,
            'imported practice belongs to another Being')
        _check(type(native_suffix) in (tuple, list),
            'native practice suffix must be a closed tuple/list')
        copied = tuple(_copy_use(row) for row in native_suffix)
        previous_time = prefix.boundary
        seen = set()
        for use in (imported,):
            _check(type(use) in (SkillUse, BatchSkillUse), 'unsupported practice history row')
            if type(use) is BatchSkillUse:
                _check(use.being_id == being_id, 'native batch practice belongs to another Target')
            for action_id in practice_action_ids(use):
                key = (action_id, use.skill_name)
                _check(key not in seen, 'duplicate historical Action/skill practice cause')
                seen.add(key)
        for use in copied:
            _check(type(use) in (SkillUse, BatchSkillUse), 'unsupported practice history row')
            if type(use) is BatchSkillUse:
                _check(use.being_id == being_id, 'native batch practice belongs to another Target')
            _check(type(use.time) in (int, float) and math.isfinite(use.time)
                and use.time > prefix.boundary and use.time >= previous_time,
                'native practice suffix must be chronological and later than imported history')
            previous_time = use.time
            for action_id in practice_action_ids(use):
                key = (action_id, use.skill_name)
                _check(key not in seen, 'duplicate historical Action/skill practice cause')
                seen.add(key)
        return (imported,) + copied
    except ImportedPracticeRejected:
        raise
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ImportedPracticeRejected('invalid imported/native practice merge') from exc


def _copy_key(key):
    from action_evaluation import native_data, freeze
    data = freeze(native_data(key, (FactKey,)))
    _name(data['entity_id']); _name(data['attribute'])
    _check(type(data['detail']) is str, 'opaque fact detail')
    if data['time'] is not None:
        _numeric(data['time'])
    return FactKey(**data)


def validate_history_constraints(being_id, earliest, known_through,
                                 nondeclining_skills, records, uses):
    """Extracted native PersonalHistory rules; no realization/interpolation.

    Accepts native legacy uses or Target-owned per-boundary skill transitions.
    Existing fact order and legacy timestamps retain their original meaning.
    """
    ranks, episodes, values = {}, [], {}
    for record in records:
        key, value = record.key, record.value
        values[key] = value
        if (key.entity_id != being_id or key.time is None
                or not earliest <= key.time <= known_through or not key.detail):
            raise ImpossibleRealization('historical fact outside Being\'s inquiry window')
        if key.attribute == 'skill_rank':
            if key.detail not in nondeclining_skills or type(value) is not int or value < 0:
                raise ImpossibleRealization('invalid historical skill rank')
            ranks.setdefault(key.detail, []).append((key.time, value))
        elif key.attribute == 'episode':
            if (not isinstance(value, (dict, MappingProxyType)) or not value.get('description')
                    or not isinstance(value['description'], str)
                    or set(value) - {'description', 'skill', 'rank_after'}):
                raise ImpossibleRealization('invalid historical episode')
            if ('skill' in value) != ('rank_after' in value):
                raise ImpossibleRealization('training episode requires skill and rank_after')
            episodes.append(record)
        else:
            raise ImpossibleRealization('unsupported historical fact type')
    for episode in episodes:
        value = episode.value
        if 'skill' in value:
            key = FactKey(being_id, 'skill_rank', episode.key.time, value['skill'])
            if (value['skill'] not in nondeclining_skills or type(value['rank_after']) is not int
                    or value['rank_after'] < 0 or key not in values or values[key] != value['rank_after']):
                raise ImpossibleRealization('training episode disagrees with historical rank')
    for skill, dated in ranks.items():
        dated.sort()
        if any(left[1] > right[1] for left, right in zip(dated, dated[1:])):
            raise ImpossibleRealization('nondeclining skill decreases between committed facts')
        relevant = [use for use in uses if use.skill_name == skill and use.time is not None]
        for time, rank in dated:
            for use in relevant:
                if time < use.time and rank > use.level_before:
                    raise ImpossibleRealization('historical rank exceeds later known pre-action rank')
                if time >= use.time and rank < use.level_after:
                    raise ImpossibleRealization('historical rank predates no later known skill gain')


def _capture_history(being, history, prior):
    from action_evaluation import native_data, freeze, UnsupportedEvaluation
    from personal_history import PersonalHistory
    from realization import RealityLedger, CommittedFact
    data = native_data(history, (PersonalHistory,))
    _check(data['being'] is being, 'history attached to a different Being')
    earliest, known = _numeric(data['earliest']), _numeric(data['known_through'])
    _check(earliest <= known, 'invalid established history bounds')
    _check(type(data['nondeclining_skills']) is frozenset, 'opaque nondeclining-skill set')
    nondeclining = frozenset(_name(k) for k in data['nondeclining_skills'])
    ledger = data['reality']; ld = native_data(ledger, (RealityLedger,))
    validators = ld['_validators']
    if (type(validators) is not tuple or len(validators) != 1
            or type(validators[0]) is not MethodType
            or validators[0].__self__ is not history
            or validators[0].__func__ is not PersonalHistory._validate):
        raise UnsupportedEvaluation('custom historical validators require a reviewed pure adapter')
    revision = ld['_revision']
    _check(type(revision) is int and revision >= 0 and type(ld['_records']) is dict, 'invalid history ledger metadata')
    records = []
    for key, record in ld['_records'].items():
        copied_key = _copy_key(key)
        rd = native_data(record, (CommittedFact,))
        _check(copied_key == _copy_key(rd['key']), 'ledger key/record identity mismatch')
        _check(type(rd['revision']) is int and 1 <= rd['revision'] <= revision, 'invalid fact revision')
        origin = _name(rd['origin'])
        records.append(FrozenHistoryFact(copied_key, freeze(rd['value']), origin, rd['revision']))
    revisions = [r.revision for r in records]
    _check(revisions == sorted(revisions) and set(revisions) == set(range(1, revision + 1)), 'inconsistent established commitment ordering/revision')
    frozen = FrozenHistory(being.id, id(ledger), revision, earliest, known, nondeclining, tuple(records))
    validate_history_constraints(frozen.being_id, earliest, known, nondeclining, frozen.records, prior)
    return frozen


def _capture_practice_inputs(world, objects, rows, imported_prefix=None):
    """Shared reviewed copy/validation path for native and prepared captures."""
    from action_evaluation import native_data, freeze
    from library import Library
    from skill import SkillDictionary, Skills
    from being import BeingInstance, BeingDefinition
    library = native_data(world.library, (Library,))
    dictionary = native_data(library['skill_dictionary'], (SkillDictionary,))
    raw_definitions = freeze(dictionary['skills'])
    definitions = {}
    for skill, definition in raw_definitions.items():
        _name(skill)
        _check(type(definition) is MappingProxyType and type(definition.get('is_ordinary')) is bool
            and type(definition.get('is_progressive')) is bool, 'unsupported skill definition flags')
        definitions[skill] = definition
    beings = {}
    for key, view in rows:
        being = objects[key]; data = native_data(being, (BeingInstance,))
        _check(type(data['skill_use_history']) is list, 'opaque skill-use history')
        prior = tuple(_copy_use(use) for use in data['skill_use_history'])
        if imported_prefix is not None and key == imported_prefix.target_id:
            # Import through the established chronology, causal-ID and copy
            # validator. This records prior use only; it never applies XP.
            prior = merge_imported_practice_uses(imported_prefix, key, prior)
        duplicate_keys = [(aid,use.skill_name) for use in prior for aid in practice_action_ids(use)]
        _check(all(type(use) is not BatchSkillUse or use.being_id == key for use in prior), 'batch history Target mismatch')
        _check(len(set(duplicate_keys)) == len(duplicate_keys), 'duplicate existing Action/skill history')
        history = None if data['personal_history'] is None else _capture_history(being, data['personal_history'], prior)
        if view is None:
            current = native_data(data['current'], (BeingDefinition,))
            skills = native_data(current['skills'], (Skills,))
            ordinary_levels = freeze(skills['skills'])
            weapon_levels = freeze(skills['weapon_skills'])
        else:
            ordinary_levels, weapon_levels = view.data['skills'], view.data['weapon_skills']
        beings[key] = FrozenBeingPractice(key, _rank_map(ordinary_levels),
            _rank_map(weapon_levels), _rank_map(freeze(data['_skill_practice_baselines'])),
            _xp_map(freeze(data['skill_experience'])), prior, history)
    return FrozenPracticeInputs(MappingProxyType(definitions), MappingProxyType(beings))


def capture_practice_inputs(world, objects, entity_views):
    """Reviewed raw native reads only; no dictionary/history methods execute.

    The public evaluator contract is unchanged. Both this ordinary path and
    the prepared-checkpoint adapter below use the identical validators and
    immutable ``FrozenBeingPractice`` representation.
    """
    return _capture_practice_inputs(world, objects,
        ((key, view) for key, view in entity_views.items() if view.category == 'being'))


def _capture_prepared_practice_inputs(world, objects, being_ids, imported_prefix):
    """Private read-only bridge for the exact quarantined C3/C4 Spot graph."""
    from being import BeingInstance
    if (type(being_ids) is not tuple or not being_ids
            or len(set(being_ids)) != len(being_ids)
            or any(type(key) is not str or type(objects.get(key)) is not BeingInstance
                   for key in being_ids)):
        raise ImportedPracticeRejected('prepared frozen practice requires unique native Being identities')
    if type(imported_prefix) is not ImportedPracticePrefix:
        raise ImportedPracticeRejected('validated imported Spot prefix is required')
    _validate_imported_prefix(imported_prefix)
    if imported_prefix.target_id not in being_ids:
        raise ImportedPracticeRejected('imported practice Target is outside the prepared Being set')
    return _capture_practice_inputs(world, objects,
        ((key, None) for key in being_ids), imported_prefix)


def project_practice(snapshot, being_id, rows, actions, proposals):
    """Reduce all this Being's qualified awards from one common starting state.

    A rank transition is at the actual integer resolution boundary. Nominal
    ends remain on causal exercises. Never emit artificial sequential SkillUse
    ranks or reinterpret existing legacy SkillUse timestamps.
    """
    from action_evaluation import PracticeEffect
    inputs = snapshot.practice_inputs
    _check(type(inputs) is FrozenPracticeInputs and type(inputs.schema) is str and inputs.schema == 'native-frozen-practice-v1', 'missing/unsupported frozen practice closure')
    _check(type(inputs.beings) is MappingProxyType and type(inputs.definitions) is MappingProxyType, 'practice lookups must be frozen native mappings')
    _check(being_id in inputs.beings, 'missing Being practice view')
    before = inputs.beings[being_id]
    _check(type(before) is FrozenBeingPractice and before.being_id == being_id, 'practice Being identity mismatch')
    ordinary, weapon = dict(_rank_map(before.ordinary_levels)), dict(_rank_map(before.weapon_levels))
    _check(ordinary == snapshot.entities[being_id].data['skills'] and weapon == snapshot.entities[being_id].data['weapon_skills'], 'practice ranks disagree with common evaluation reads')
    xp, baselines = dict(_xp_map(before.skill_experience)), dict(_rank_map(before.baselines))
    prior_keys = {(aid,use.skill_name) for use in before.prior_uses for aid in practice_action_ids(use)}
    exercises, by_skill = [], {}
    for row in rows:
        effect = row.effect
        if type(effect) is not PracticeEffect:
            continue
        skill = _name(effect.skill); _xp(effect.experience)
        _check(skill in inputs.definitions, 'unknown practiced skill definition: '+skill)
        definition = inputs.definitions[skill]
        rank = ordinary.get(skill)
        rank = (weapon.get(skill) if rank is None else rank) or 0
        _check(definition['is_ordinary'] or rank != 0, 'extraordinary skill requires pre-batch training: '+skill)
        key = (effect.source_action_id, skill)
        _check(key not in prior_keys, 'Action/skill practice already recorded')
        prior_keys.add(key)
        use = CandidatePracticeUse(row.identity, skill, effect.experience, effect.source_action_id,
            actions[effect.source_action_id].nominal_end, snapshot.boundary, proposals[effect.source_action_id].outcome)
        exercises.append(use); by_skill.setdefault(skill, []).append(use)
    transitions = []
    for skill in sorted(by_skill):
        uses = by_skill[skill]
        rank = ordinary.get(skill)
        rank = (weapon.get(skill) if rank is None else rank) or 0
        baseline = baselines.get(skill, rank)
        total = xp.get(skill, 0) + sum(use.experience for use in uses)
        after = max(rank, level_from_practice(baseline, total)) if inputs.definitions[skill]['is_progressive'] else rank
        if after > rank:
            (weapon if skill in weapon else ordinary)[skill] = after
        baselines.setdefault(skill, rank); xp[skill] = total
        transitions.append(CandidateSkillTransition(being_id, skill, snapshot.boundary, rank, after,
            baseline, before.skill_experience.get(skill, 0), total, tuple(use.effect_identity for use in uses)))
    if before.history is not None:
        h = before.history
        validate_history_constraints(being_id, h.earliest, h.known_through,
            h.nondeclining_skills, h.records, before.prior_uses + tuple(transitions))
    return PracticeProjection(being_id, MappingProxyType(dict(sorted(ordinary.items()))),
        MappingProxyType(dict(sorted(weapon.items()))), MappingProxyType(dict(sorted(baselines.items()))),
        MappingProxyType(dict(sorted(xp.items()))), before.prior_uses, tuple(exercises), tuple(transitions),
        None if before.history is None else before.history.revision)
