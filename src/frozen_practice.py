"""Frozen native practice inputs and inactive Target-owned batch progression.

No skill awards, facts, publication, callbacks, or stochastic operations. New
exercises describe causes; one per-skill Target transition owns resulting rank.
"""
from dataclasses import dataclass, fields
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


def capture_practice_inputs(world, objects, entity_views):
    """Reviewed raw native reads only; no dictionary/history methods execute."""
    from action_evaluation import native_data, freeze
    from library import Library
    from skill import SkillDictionary
    from being import BeingInstance
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
    for key, view in entity_views.items():
        if view.category != 'being':
            continue
        being = objects[key]; data = native_data(being, (BeingInstance,))
        _check(type(data['skill_use_history']) is list, 'opaque skill-use history')
        prior = tuple(_copy_use(use) for use in data['skill_use_history'])
        duplicate_keys = [(aid,use.skill_name) for use in prior for aid in practice_action_ids(use)]
        _check(all(type(use) is not BatchSkillUse or use.being_id == key for use in prior), 'batch history Target mismatch')
        _check(len(set(duplicate_keys)) == len(duplicate_keys), 'duplicate existing Action/skill history')
        history = None if data['personal_history'] is None else _capture_history(being, data['personal_history'], prior)
        beings[key] = FrozenBeingPractice(key, _rank_map(view.data['skills']),
            _rank_map(view.data['weapon_skills']), _rank_map(freeze(data['_skill_practice_baselines'])),
            _xp_map(freeze(data['skill_experience'])), prior, history)
    return FrozenPracticeInputs(MappingProxyType(definitions), MappingProxyType(beings))


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
