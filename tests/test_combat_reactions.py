"""Range-at-impact, action continuity and timed defensive reaction tests."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]
from spatial.state import CartesianPosition
from tactical_duel import TacticalDuel
from melee_defense import MeleeDefense


class TestCombatReactions(unittest.TestCase):
    def test_range_checked_only_at_resolution_even_if_out_of_range_when_scheduled(self):
        game = TacticalDuel(17)
        game.foe.set_position(CartesianPosition(2.7, 0, 0))
        state = game.choose('thrust')
        self.assertIsNotNone(state['player']['pending'])
        self.assertEqual(state['player']['pending']['due'], 4)
        # The Raider may advance into range before impact.
        for _ in range(3):
            game.choose('wait')
        results = [r for h in game.history for r in h['results'] if r['actor'] == game.player.id]
        self.assertEqual(len(results), 1)
        self.assertNotEqual(results[0]['outcome'], 'out_of_reach')
        self.assertEqual(game.player.get_skill_experience('Dagger'), 10)

    def test_out_of_range_at_impact_fails_without_experience(self):
        game = TacticalDuel(17)
        game.foe.set_position(CartesianPosition(2.7, 0, 0))
        game.choose('thrust')  # known target; currently beyond reach
        game.foe.set_position(CartesianPosition(20, 0, 0))
        for _ in range(3):
            game.choose('wait')
        self.assertTrue(any(r['outcome'] == 'out_of_reach'
                            for h in game.history for r in h['results']
                            if r['actor'] == game.player.id))
        self.assertEqual(game.player.get_skill_experience('Dagger'), 0)

    def test_guard_persists_across_movement_and_log_reflects_stance(self):
        game = TacticalDuel(17)
        game.choose('guard')
        state = game.choose('northwest')
        self.assertEqual(state['player']['action_state'], 'Guarding (sustained)')
        self.assertEqual(state['player_cues']['guard'], '▣')
        self.assertEqual(state['player_cues']['movement'], '↖')
        self.assertEqual(game.player.strategy.defense, 2)
        self.assertIn('guarding', state['history'][-1]['player_activity'])
        self.assertIsNone(game._pending(game.player))
        state = game.choose('wait')
        self.assertEqual(state['player']['action_state'], 'Guarding (sustained)')
        state = game.choose('cancel')
        self.assertEqual(state['player']['action_state'], 'Idle')
        self.assertEqual(game.player.strategy.defense, 0)

    def test_swing_and_movement_remain_concurrent_in_map_and_log(self):
        game = TacticalDuel(17)
        game.choose('swing')
        strike = game._pending(game.player)
        state = game.choose('west')
        self.assertIs(game._pending(game.player), strike)
        self.assertEqual(state['player_cues']['attack'], '⚔')
        self.assertEqual(state['player_cues']['movement'], '←')
        self.assertIn('preparing swing', state['history'][-1]['player_activity'])
        self.assertNotIn(strike.id, game.encounter.cancelled_action_list)

    def _ready_incoming_strike(self):
        game = TacticalDuel(17)
        for _ in range(2):
            game.choose('wait')
        self.assertEqual(game._pending(game.foe).end_time, 6)
        return game

    def test_parry_deflects_simultaneous_impact_and_both_exercise_weapons(self):
        game = self._ready_incoming_strike()
        before = game.player.get_hit_points()
        state = game.choose('parry')
        defense = game._pending(game.player)
        self.assertEqual(defense.ready_at, 5)
        self.assertEqual(defense.end_time, 6)
        self.assertEqual(defense.target_action_id, game._pending(game.foe).id)
        for _ in range(2): game.choose('wait')
        with patch('melee_defense.roll_dice', side_effect=[20, 1]):
            state = game.choose('wait')
        self.assertEqual(game.player.get_hit_points(), before)
        results = game.history[-1]['results']
        self.assertIn('parried', [r['outcome'] for r in results])
        self.assertIn('deflected', [r['outcome'] for r in results])
        self.assertEqual(game.player.get_skill_experience('Dagger'), 10)
        self.assertEqual(game.foe.get_skill_experience('Longsword'), 10)
        defense = next(game.world.get_event_by_id(i) for i in game.encounter.finished_action_list
                       if isinstance(game.world.get_event_by_id(i), MeleeDefense))
        self.assertEqual(defense.resolution.outcome, 'deflected')
        self.assertIn('Scout parry:', str(state['history'][-1]['results']))
        self.assertNotIn('foe_choice', str(state['history']))

    def test_failed_parry_still_earns_practice_and_cannot_block(self):
        game = self._ready_incoming_strike()
        game.choose('parry')
        for _ in range(2): game.choose('wait')
        with patch('melee_defense.roll_dice', side_effect=[1, 20]):
            game.choose('wait')
        self.assertIn('failed', [r['outcome'] for r in game.history[-1]['results']])
        self.assertNotIn('parried', [r['outcome'] for r in game.history[-1]['results']])
        self.assertEqual(game.player.get_skill_experience('Dagger'), 10)

    def test_dodge_moves_and_can_escape_reach_without_automatic_hit(self):
        game = self._ready_incoming_strike()
        game.foe.set_position(CartesianPosition(1.9, 0, 0))
        before = game.player.get_position()
        state = game.choose('dodge')
        self.assertAlmostEqual(game.player.get_position().x, before.x)
        for _ in range(2): state = game.choose('wait')
        state = game.choose('wait')
        self.assertAlmostEqual(game.player.get_position().x, before.x - .5)
        self.assertEqual(state['player_cues']['movement'], '←')
        self.assertEqual(game.player.get_skill_experience('tumble'), 10)
        self.assertEqual(game.foe.get_skill_experience('Longsword'), 0)
        self.assertIn('out_of_reach', [r['outcome'] for r in game.history[-1]['results']])
        self.assertIn('evaded', [r['outcome'] for r in game.history[-1]['results']])

    def test_reaction_without_imminent_strike_gains_no_experience(self):
        game = TacticalDuel(17)
        with self.assertRaisesRegex(ValueError, 'No currently perceived incoming attack'):
            game.choose('parry')
        with self.assertRaisesRegex(ValueError, 'No currently perceived incoming attack'):
            game.choose('dodge')
        self.assertEqual(game.player.get_skill_experience('Dagger'), 0)
        self.assertEqual(game.player.get_skill_experience('tumble'), 0)
        self.assertEqual(game.encounter.time, 0)

    def test_unarmed_parry_rejected_without_interrupting_attack(self):
        game = TacticalDuel(17)
        game.choose('swing')
        previous = game._pending(game.player)
        game.player.body_part_remove_object('right hand')
        with self.assertRaisesRegex(ValueError, 'requires a held weapon'):
            game.choose('parry')
        self.assertIs(game._pending(game.player), previous)
        self.assertEqual(game.encounter.time, 1)

    def test_reaction_allocation_validation_is_atomic(self):
        game = TacticalDuel(17)
        game.choose('swing')
        pending = game._pending(game.player)
        with self.assertRaisesRegex(ValueError, 'defensive effort'):
            game.choose('parry', {'attack': 1, 'defense': 0, 'timing': 0, 'extra_damage': 0})
        self.assertIs(game._pending(game.player), pending)
        self.assertEqual(game.encounter.time, 1)
        state = game.choose('dodge', {'attack': 0, 'defense': 2, 'timing': 0, 'extra_damage': 0})
        self.assertEqual(game.player.strategy.defense, 2)
        self.assertEqual(game.encounter.cancelled_action_list[-1], pending.id)
        self.assertIn('dodge', state['history'][-1]['player_choice'])

    def test_reactions_survive_checked_save_replay_and_resume(self):
        game = self._ready_incoming_strike()
        game.choose('parry')
        for _ in range(2): game.choose('wait')
        # Save while a named defensive action is pending, too.
        session = game.to_session()
        restored = TacticalDuel.from_session(json.loads(json.dumps(session)))
        self.assertEqual(restored._journal_signature(), game._journal_signature())
        self.assertEqual(restored.player.get_skill_experience('Dagger'),
                         game.player.get_skill_experience('Dagger'))
        self.assertEqual(restored.player.get_skill_experience('tumble'),
                         game.player.get_skill_experience('tumble'))
        self.assertEqual(restored._pending(restored.player).target_action_id,
                         restored._pending(restored.foe).id)
        for command in ('wait', 'northwest'):
            restored.choose(command)
            game.choose(command)
        self.assertEqual(restored._journal_signature(), game._journal_signature())

    def test_viewer_has_reactions_and_distinct_current_action(self):
        html = (ROOT / 'examples/live_combat_template.html').read_text()
        self.assertIn('data-command="parry"', html)
        self.assertIn('data-command="dodge"', html)
        self.assertIn('p.action_state', html)
        self.assertIn('h.player_activity', html)
        self.assertIn('data.player_cues', html)


if __name__ == '__main__':
    unittest.main()
