"""An explorer encounters a Group and discovers a herder's unresolved past.

Run: python examples/integrated_discovery.py [--audit]

By default the narrative prints only listener-accessible evidence; --audit is
an out-of-world developer inspection of objective reality, not Agent knowledge.
This scaffold uses range to gate communication, not modeled hearing or speech.
"""
import argparse
from pathlib import Path
import hashlib
import json
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src')]

from encounter import Encounter
from field_observation import BeliefLedger
from group_observation import ObserveGroupAction
from history_conversation import AskAboutPastAction
from library import Library
from realization import Fact
from spatial.state import CartesianPosition
from statistical_group import StatisticalGroup
from universe import Universe


def propose_childhood(seed, topic):
    """Supply alternate admissible stories, not a preselected biography.

    Choices are keyed by identity/topic so generation order and unrelated
    discovery cannot perturb the proposal. This is a fixture-generation policy;
    much richer causal models will eventually replace it.
    """
    mentors = ('an older sister', 'a patient aunt', 'a caravan scout', 'a grandparent')
    places = ('the rocky ford', 'a wind-scoured ridge',
              'the marsh crossing', 'the riverbank')
    details = ('during a difficult migration', 'before the spring rains',
               'while searching for lost livestock', 'after a sudden storm')

    def generate(history, view):
        identifier = f'{seed}|{history.being.id}|{topic}'
        value = int.from_bytes(hashlib.sha256(identifier.encode()).digest()[:16], 'big')
        rng = random.Random(value)
        description = ('Learned to run with ' + rng.choice(mentors) + ' near ' +
                       rng.choice(places) + ', ' + rng.choice(details) + '.')
        return (
            Fact(history.episode_key(10, topic),
                 {'description': description, 'skill': 'run', 'rank_after': 1},
                 'seeded_conditional_life_history'),
            Fact(history.skill_key(10, 'run'), 1, 'seeded_conditional_life_history'),
        )
    return generate


def run_scenario(seed=391):
    config = json.loads((ROOT / 'examples' / 'nomadic_group.json').read_text())
    world = Universe('First explorable Universe', library=Library(
        config_dir=str(ROOT / 'src' / 'config')))
    group = StatisticalGroup(config['group_name'], config['group_id'], config,
                             seed=config['seed'])
    world.add_object(group)
    herder = group.realize_being(world, 0, 'adults', 0, name='Traveling herder')
    herder.set_skill_level(world.get_skill_dictionary(), 'run', 2)
    later_use = herder.record_skill_use(world.get_skill_dictionary(), 'run', 0,
                                        time=50, action_id='journey-before-meeting')
    history = herder.begin_personal_history(earliest=0, known_through=104,
                                             nondeclining_skills=('run',))
    assert history.inspect_episode(10, 'early_running') is None
    # Time 100; original group members still follow the group's coarse motion.
    group.advance(100)
    observer_id = world.make_being('Human', 'Explorer')
    observer = world.get_object_by_id(observer_id)
    p = herder.get_position()
    observer.set_position(CartesianPosition(p.x + 2, p.y, p.z))
    observer.set_skill_level(world.get_skill_dictionary(), 'spot', 6)
    belief = BeliefLedger(observer.id)
    heard = []

    encounter = Encounter(world, difficulty_class=10, start_time=100)
    encounter.add_being(observer.id)
    encounter.add_being(herder.id)
    encounter.add_object(group.id)
    perception = encounter.perceive_within(observer.id, 1000)
    assert encounter.is_aware(observer.id, herder.id)
    assert encounter.decide_to_act(observer.id, herder.id,
                                    'investigate people and their stories')

    def follow_group_for_one_second():
        # A deliberate motion policy for this *scenario*, not a consequence
        # of the observer's Group membership. Keep Group and Encounter clocks
        # aligned and let the explorer travel alongside the herder.
        before = group.get_position()
        group.advance(1)
        after = group.get_position()
        velocity = tuple(b - a for a, b in zip(
            before.as_tuple(), after.as_tuple()))
        encounter.step(1, velocities={observer.id: velocity})

    # Group observation: a fallible perception/interpretation, not exact counts.
    survey = ObserveGroupAction(
        world, observer.id, group.id, start_time=100,
        seed=seed, random_key='explorer-survey',
        observation=config['action_observation']['sensor'],
        interpretation=config['interpretation'],
        experience={'success': 12, 'failure': 18}, ledger=belief)
    encounter.schedule_action(survey)
    follow_group_for_one_second()

    # The explorer asks about the Being's past. Objective life detail is
    # conditionally generated *on demand*, not known in advance.
    first = AskAboutPastAction(world, observer.id, herder.id, encounter.time,
                               episode_time=10, topic='early_running',
                               generate=propose_childhood(seed, 'early_running'),
                               received_accounts=heard)
    encounter.schedule_action(first)
    follow_group_for_one_second()

    # A subsequent account of the same past can disagree with reality, but
    # hearing it doesn't establish either truth or deliberate deception.
    second = AskAboutPastAction(
        world, observer.id, herder.id, encounter.time,
        episode_time=10, topic='early_running',
        generate=lambda *_: (_ for _ in ()).throw(
            AssertionError('committed history must not be resampled')),
        substituted_claim='I learned to run entirely alone, far from any settlement.',
        received_accounts=heard)
    encounter.schedule_action(second)
    follow_group_for_one_second()

    return {'world': world, 'group': group, 'herder': herder,
            'observer': observer, 'encounter': encounter, 'perception': perception,
            'belief': belief, 'survey': survey, 'history': history,
            'first': first, 'second': second, 'heard': heard,
            'later_use': later_use}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=391,
                        help='world generation seed for unresolved episode details')
    parser.add_argument('--audit', action='store_true',
                        help='display objective-history developer inspection')
    options = parser.parse_args()
    scene = run_scenario(seed=options.seed)
    print('Observed group:', (None if scene['survey'].field_observation is None
                              else {k: v.estimate for k, v in
                                    scene['survey'].field_observation.reports.items()}))
    for account in scene['heard']:
        print('Explorer heard:', account.words)
    print('Same episode materialized once:', scene['first'].newly_realized,
          'revisited:', scene['second'].newly_realized)
    print('Two accounts agree:', scene['heard'][0].words == scene['heard'][1].words)
    print('Explorer is not automatically told which account was accurate.')
    if options.audit:
        fact = scene['history'].inspect_episode(10, 'early_running')
        print('[Developer-only audit] Objective episode:', fact.value['description'])
        print('[Developer-only audit] Established rank:',
              scene['history'].reality.view().get(scene['history'].skill_key(10, 'run')))
