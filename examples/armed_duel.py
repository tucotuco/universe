"""First playable armed exchange using Universe Beings, Objects and Encounter.

From the project root: python examples/armed_duel.py --seed 17

Not yet a full tactical combat engine: see docs/armed-melee-increment.md.
"""

import argparse
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from encounter import Encounter
from library import Library
from melee_combat import MeleeStrike
from spatial.state import CartesianPosition
from universe import Universe


def make_duel():
    world = Universe('A clash at the ford', library=Library(config_dir=str(ROOT / 'src' / 'config')))
    scout_id = world.make_being('Human', 'Scout')
    raider_id = world.make_being('Human', 'Raider')
    scout = world.get_object_by_id(scout_id)
    raider = world.get_object_by_id(raider_id)
    scout.set_position(CartesianPosition(0, 0, 0))
    raider.set_position(CartesianPosition(1.5, 0, 0))

    dagger_id = world.make_weapon_for_being(scout_id, 'Dagger', 'Scout dagger')
    sword_id = world.make_weapon_for_being(raider_id, 'Longsword', 'Raider sword')
    world.arm_being(scout_id, dagger_id, 'right hand')
    world.arm_being(raider_id, sword_id, 'right hand')
    armor_id = world.make_armor_for_being(raider_id, 'Leather armor', 'Raider leather')
    scout.set_weapon_skill_level(world.get_weapon_dictionary(), 'Dagger', 2)
    raider.set_weapon_skill_level(world.get_weapon_dictionary(), 'Longsword', 1)
    scout.set_strategy(attack=1)
    raider.set_strategy(defense=1)

    encounter = Encounter(world, difficulty_class=12, start_time=0, name='Ford encounter')
    encounter.add_being(scout_id)
    encounter.add_being(raider_id)
    encounter.mark_aware(scout_id, raider_id)
    encounter.mark_aware(raider_id, scout_id)
    encounter.decide_to_act(scout_id, raider_id, 'attack')
    scout_strike = MeleeStrike(encounter, scout_id, raider_id, dagger_id,
                               motion='thrust', reach=2)
    raider_strike = MeleeStrike(encounter, raider_id, scout_id, sword_id,
                                motion='swing', reach=2)
    encounter.schedule_action(scout_strike)
    encounter.schedule_action(raider_strike)
    return world, encounter, scout, raider, armor_id, (scout_strike, raider_strike)


def run(seed=17):
    random.seed(seed)  # Demo repeatability; world-wide RNG policy is not yet implemented.
    world, encounter, scout, raider, armor_id, attacks = make_duel()
    print('Two human Beings face each other at the ford, 1.5 units apart.')
    print('Scout: dagger (thrust 4 seconds), weapon skill 2.')
    print('Raider: longsword (swing 6 seconds), weapon skill 1, leather armor.')
    print('Both decide to attack at time 0; their attack timing differs.')
    print()
    while encounter.pending_action_list:
        tick = encounter.step()
        print(f'Time {tick.end_time:g}: Scout {scout.get_hit_points()} HP; Raider {raider.get_hit_points()} HP')
        for action_id in tick.completed_action_ids:
            attack = world.get_event_by_id(action_id)
            record = attack.combat_result
            print('  ', world.get_object_by_id(record.actor_id).name,
                  record.motion, '->', record.outcome,
                  f'({record.target_hp_before} to {record.target_hp_after} target HP)')
    armor = world.get_object_by_id(armor_id)
    print(f'Raider armor durability remaining: {armor.hit_points()} HP')
    return world, encounter, attacks


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=17)
    run(parser.parse_args().seed)
