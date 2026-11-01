"""Combat replay integration, perception boundary, and weapon practice."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'examples'))

from armed_duel import make_duel
from combat_visual import main, render, simulate, snapshot
from melee_combat import MeleeStrike


class TestCombatVisual(unittest.TestCase):
    def test_weapon_skills_registered_for_experience(self):
        world, encounter, scout, raider, _, _ = make_duel()
        definitions = world.get_skill_dictionary()
        for weapon in ('Dagger', 'Longsword'):
            self.assertTrue(definitions.get_skill_definition(weapon)['is_progressive'])
        self.assertIsNone(definitions.get_skill_definition('Nonexistent sword'))

    def test_success_records_skill_exercise_and_time(self):
        world, encounter, scout, raider, _, actions = make_duel()
        with patch('action.roll_dice', side_effect=[17, 4]):
            encounter.step(duration=4)
        self.assertEqual(actions[0].resolution.skill_exercises[0].skill_name, 'Dagger')
        self.assertEqual(actions[0].resolution.skill_exercises[0].experience, 10)
        self.assertEqual(scout.get_skill_experience('Dagger'), 10)
        self.assertEqual(scout.skill_use_history[-1].time, 4)
        self.assertEqual(scout.skill_use_history[-1].action_id, actions[0].id)

    def test_missed_attempt_records_practice(self):
        _, encounter, _, raider, _, actions = make_duel()
        with patch('action.roll_dice', return_value=3):
            encounter.step(duration=6)
        self.assertEqual(actions[1].combat_result.outcome, 'miss')
        self.assertEqual(raider.get_skill_experience('Longsword'), 10)
        self.assertEqual(raider.skill_use_history[-1].outcome, 'miss')

    def test_out_of_reach_earns_no_xp(self):
        _, encounter, scout, _, _, actions = make_duel()
        encounter.step(duration=1, velocities={actions[1].actor_id: (10, 0, 0)})
        encounter.step(duration=3)
        self.assertEqual(actions[0].combat_result.outcome, 'out_of_reach')
        self.assertEqual(actions[0].resolution.skill_exercises, ())
        self.assertEqual(scout.get_skill_experience('Dagger'), 0)

    def test_dropped_weapon_earns_no_xp(self):
        _, encounter, scout, _, _, actions = make_duel()
        scout.body_part_remove_object('right hand')
        encounter.step(duration=4)
        self.assertEqual(actions[0].combat_result.outcome, 'weapon_unavailable')
        self.assertEqual(scout.get_skill_experience('Dagger'), 0)

    def test_replay_timeline_matches_real_damage_xp_and_movement(self):
        trace = simulate(17)
        frames = trace['frames']
        self.assertEqual([frame['time'] for frame in frames], list(range(7)))
        self.assertEqual(frames[1]['beings'][1]['position'], [1.5, .2, 0.0])
        self.assertEqual(frames[2]['beings'][1]['position'], [1.5, .4, 0.0])
        self.assertEqual(frames[4]['beings'][1]['hp'], 7)
        self.assertEqual(frames[4]['beings'][0]['experience'], 10)
        self.assertEqual(frames[6]['beings'][1]['experience'], 10)
        self.assertEqual(frames[6]['events'][0]['outcome'], 'miss')

    def test_initial_range_perception_provides_awareness(self):
        frames = simulate(17)['frames']
        first, second = frames[0]['beings']
        self.assertIn(second['id'], first['aware_of'])
        self.assertIn(first['id'], second['aware_of'])
        self.assertEqual(len(frames[0]['events']), 2)

    def test_snapshot_does_not_mutate_combat(self):
        world, encounter, scout, raider, _, _ = make_duel()
        before = (encounter.time, scout.get_hit_points(), raider.get_hit_points(),
                  len(scout.skill_use_history), len(raider.skill_use_history))
        snapshot(world, encounter, (scout, raider), ('Dagger', 'Longsword'))
        after = (encounter.time, scout.get_hit_points(), raider.get_hit_points(),
                 len(scout.skill_use_history), len(raider.skill_use_history))
        self.assertEqual(before, after)

    def test_template_defaults_to_limited_view_and_no_false_bearing(self):
        html = render(simulate(17))
        self.assertIn('perspective.value = all[0].id', html)
        self.assertIn('Range alone gives no bearing', html)
        self.assertIn('Developer audit', html)
        self.assertIn('Recorded skill uses', html)
        self.assertNotIn('__COMBAT_TRACE__', html)

    def test_replay_can_be_written_without_browser(self):
        with tempfile.TemporaryDirectory() as directory:
            result = main(['--seed', '17', '--output', str(Path(directory) / 'duel.html')])
            self.assertTrue(result.is_file())
            self.assertIn('Time', result.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
