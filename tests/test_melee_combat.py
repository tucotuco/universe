"""First real melee exchanges on the persistent Encounter timeline."""

import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath('../src'))

from encounter import Encounter
from library import Library
from melee_combat import MeleeStrike
from spatial.geometry import Sphere
from spatial.occlusion import VisualOcclusion
from spatial.state import CartesianPosition
from universe import Universe


class TestMeleeCombat(unittest.TestCase):
    def setUp(self):
        self.world = Universe('Duel', library=Library(config_dir='../src/config'))
        self.a_id = self.world.make_being('Human', 'Attacker')
        self.b_id = self.world.make_being('Human', 'Defender')
        self.a = self.world.get_object_by_id(self.a_id)
        self.b = self.world.get_object_by_id(self.b_id)
        self.a.set_position(CartesianPosition(0, 0, 0))
        self.b.set_position(CartesianPosition(1.5, 0, 0))
        self.blade = self.world.make_weapon_for_being(self.a_id, 'Dagger', 'Knife')
        self.world.arm_being(self.a_id, self.blade, 'right hand')
        self.armor_id = self.world.make_armor_for_being(self.b_id, 'Leather armor', 'Vest')
        self.armor = self.world.get_object_by_id(self.armor_id)
        self.encounter = Encounter(self.world, difficulty_class=10, start_time=0)
        self.encounter.add_being(self.a_id)
        self.encounter.add_being(self.b_id)
        self.encounter.mark_aware(self.a_id, self.b_id)
        self.encounter.decide_to_act(self.a_id, self.b_id, 'fight')

    def strike(self, **kwargs):
        values = {'motion': 'thrust', 'reach': 2}
        values.update(kwargs)
        return MeleeStrike(self.encounter, self.a_id, self.b_id, self.blade, **values)

    def test_timing_damage_armor_and_persistent_result(self):
        strike = self.strike()
        self.assertEqual(strike.end_time, 4)  # Dagger thrust, from draft table
        self.encounter.schedule_action(strike)
        with patch('action.roll_dice', side_effect=[17, 4]):
            for _ in range(3):
                self.assertFalse(self.encounter.step().completed_action_ids)
            self.assertEqual(self.encounter.step().completed_action_ids, (strike.id,))
        self.assertEqual(strike.hit_type, 'normal')
        self.assertEqual(self.b.get_hit_points(), 7)  # pierce stops 1 of 4
        self.assertEqual(self.armor.hit_points(), 26)  # 4 points exceed armor hardness
        self.assertEqual(strike.resolution.outcome, 'normal')
        self.assertEqual(strike.combat_result.target_hp_before, 10)
        self.assertEqual(strike.combat_result.target_hp_after, 7)
        self.assertEqual(json.loads(strike.to_json())['combat_result']['outcome'], 'normal')
        self.assertIn(strike.id, self.encounter.finished_action_list)
        with self.assertRaises(RuntimeError):
            strike.resolve(10)

    def test_type_based_weapon_skill_contributes_to_attack(self):
        self.a.set_weapon_skill_level(self.world.get_weapon_dictionary(), 'Dagger', 3)
        strike = self.strike()
        self.encounter.schedule_action(strike)
        with patch('action.roll_dice', side_effect=[8, 4]):
            self.encounter.step(duration=4)
        self.assertEqual(strike.hit_type, 'normal')  # 8 + 3 >= DC 10

    def test_miss_does_not_damage_objects(self):
        strike = self.strike()
        self.encounter.schedule_action(strike)
        with patch('action.roll_dice', return_value=3):
            self.encounter.step(duration=4)
        self.assertEqual(strike.resolution.outcome, 'miss')
        self.assertEqual(self.b.get_hit_points(), 10)
        self.assertEqual(self.armor.hit_points(), 30)

    def test_target_moves_out_of_reach_before_resolution(self):
        strike = self.strike()
        self.encounter.schedule_action(strike)
        self.encounter.step(duration=1, velocities={self.b_id: (3, 0, 0)})
        self.encounter.step(duration=3)
        self.assertEqual(strike.combat_result.outcome, 'out_of_reach')
        self.assertEqual(self.b.get_hit_points(), 10)

    def test_weapon_removed_during_attack(self):
        strike = self.strike()
        self.encounter.schedule_action(strike)
        self.a.body_part_remove_object('right hand')
        self.encounter.step(duration=4)
        self.assertEqual(strike.combat_result.outcome, 'weapon_unavailable')
        self.assertEqual(self.b.get_hit_points(), 10)

    def test_fallen_target_is_not_attacked(self):
        strike = self.strike()
        self.encounter.schedule_action(strike)
        self.b.set_hit_points(0)
        self.encounter.step(duration=4)
        self.assertEqual(strike.combat_result.outcome, 'target_down')

    def test_requires_actual_held_weapon_and_supported_motion(self):
        self.a.body_part_remove_object('right hand')
        with self.assertRaisesRegex(ValueError, 'does not hold'):
            self.encounter.schedule_action(self.strike())
        self.world.arm_being(self.a_id, self.blade, 'right hand')
        invalid = MeleeStrike(self.encounter, self.a_id, self.b_id, self.blade,
                              motion='swing', reach=2)
        self.assertEqual(invalid.end_time, 4)  # dagger swing is also supported
        spike = self.world.make_weapon_for_being(self.a_id, 'Armor spike', 'Spike')
        self.world.arm_being(self.a_id, spike, 'left hand')
        with self.assertRaisesRegex(ValueError, 'does not support'):
            self.encounter.schedule_action(MeleeStrike(
                self.encounter, self.a_id, self.b_id, spike, motion='swing', reach=2))
        with self.assertRaises(ValueError):
            self.strike(reach=0)

    def test_blocked_and_unknown_path_refuse_schedule(self):
        obstacle_id = self.world.make_object('Brick', 'Wall proxy')
        obstacle = self.world.get_object_by_id(obstacle_id)
        obstacle.set_position(CartesianPosition(.75, 0, 0))
        obstacle.set_geometry(Sphere(.3))
        obstacle.set_visual_occlusion(VisualOcclusion(1))
        self.encounter.add_object(obstacle_id)
        with self.assertRaisesRegex(ValueError, 'blocked'):
            self.encounter.schedule_action(self.strike())
        obstacle.set_visual_occlusion(VisualOcclusion(0))
        with self.assertRaisesRegex(ValueError, 'blocked'):
            self.encounter.schedule_action(self.strike())
        obstacle.set_geometry(None)
        with self.assertRaisesRegex(ValueError, 'uncertain_path'):
            self.encounter.schedule_action(self.strike())

    def test_cannot_attack_before_aware_or_from_distance(self):
        self.encounter.clear_awareness(self.a_id, self.b_id)
        with self.assertRaisesRegex(ValueError, 'not aware'):
            self.encounter.schedule_action(self.strike())
        self.encounter.mark_aware(self.a_id, self.b_id)
        self.b.set_position(CartesianPosition(20, 0, 0))
        with self.assertRaisesRegex(ValueError, 'out_of_reach'):
            self.encounter.schedule_action(self.strike())

    def test_reach_validation(self):
        for length in (None, '2', 0, -1, float('nan'), float('inf'), True):
            with self.subTest(length=length), self.assertRaises((TypeError, ValueError)):
                self.strike(reach=length)

    def test_fatal_confirmation_save_is_defender_not_attacker(self):
        strike = self.strike()
        actor_save = []
        target_save = []
        self.a.makes_save = lambda *args: actor_save.append(args) or True
        self.b.makes_save = lambda *args: target_save.append(args) or False
        with patch('action.roll_dice', side_effect=[20, 20]):
            self.assertEqual(strike.hit_result(10), 'fatal')
        self.assertEqual(actor_save, [])
        self.assertEqual(len(target_save), 1)


if __name__ == '__main__':
    unittest.main()
