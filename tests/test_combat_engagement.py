"""Engagement visibility, skill allocation, independent movement and complete duel journals."""
import copy
import http.client
import threading
from http.server import HTTPServer
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]
from spatial.state import CartesianPosition
from tactical_duel import TacticalDuel
from live_combat import make_handler


class TestCombatEngagement(unittest.TestCase):
    def test_movement_preserves_attack_and_both_map_indicators(self):
        game = TacticalDuel()
        game.choose('thrust')
        action = game._pending(game.player)
        state = game.choose('northwest')
        self.assertIs(game._pending(game.player), action)
        self.assertNotIn(action.id, game.encounter.cancelled_action_list)
        self.assertEqual(state['player_cues']['movement'], '↖')
        self.assertEqual(state['player_cues']['attack'], '⚔')
        self.assertIn('thrust', state['player']['pending']['motion'])

    def test_range_display_and_initiation_requires_reach(self):
        game = TacticalDuel()
        first = game.state()
        self.assertTrue(first['range']['in_range'])
        self.assertEqual(first['range']['distance'], 1.5)
        self.assertEqual(first['range']['reach'], 2.0)
        game.foe.set_position(CartesianPosition(3, 0, 0))
        game._observe()
        state = game.state()
        self.assertTrue(state['range'] is None or state['range']['status'] == 'out_of_reach')
        start = game.encounter.time
        with self.assertRaisesRegex(ValueError, 'out_of_reach'):
            game.choose('thrust')
        self.assertEqual(game.encounter.time, start)
        self.assertIsNone(game._pending(game.player))

    def test_out_of_range_at_impact_is_non_attempt_without_experience(self):
        game = TacticalDuel()
        game.choose('thrust')
        # Attacker started in range but movement creates a genuine failed reach.
        game.foe.set_position(CartesianPosition(2.9, 0, 0))
        for _ in range(3):
            game.choose('wait')
        self.assertEqual(game.player.get_skill_experience('Dagger'), 0)
        self.assertTrue(any(r['outcome'] == 'out_of_reach'
                            for h in game.history for r in h['results']
                            if r['actor'] == game.player.id))

    def test_strategy_allocation_changes_timing_and_is_budget_limited(self):
        game = TacticalDuel()
        config = {'attack': 1, 'defense': 0, 'timing': 1, 'extra_damage': 0}
        state = game.choose('thrust', config)
        self.assertEqual(state['player']['pending']['due'], 3)
        self.assertEqual(state['player']['strategy']['timing'], 1)
        self.assertEqual(state['player']['strategy']['attack'], 1)
        self.assertEqual(game._pending(game.player).strategy.timing, 1)
        self.assertEqual(game.encounter.time, 1)
        self.assertEqual(state['effort_pool'], 2)
        with self.assertRaisesRegex(ValueError, 'exceeds'):
            game.choose('swing', {'attack': 2, 'defense': 1, 'timing': 0,
                                  'extra_damage': 0})
        self.assertEqual(game.encounter.time, 1)
        self.assertEqual(game._pending(game.player).event_type, 'thrust')

    def test_effort_validation_does_not_mutate_encounter(self):
        game = TacticalDuel()
        bad = ({'attack': True, 'defense': 0, 'timing': 0, 'extra_damage': 0},
               {'attack': -1, 'defense': 0, 'timing': 0, 'extra_damage': 0},
               {'attack': 1, 'defense': 0},
               {'attack': 0, 'defense': 0, 'timing': 0, 'extra_damage': 99})
        for effort in bad:
            with self.subTest(effort=effort), self.assertRaises(ValueError):
                game.choose('thrust', effort)
        self.assertEqual(game.encounter.time, 0)
        self.assertEqual(game.encounter.pending_action_list, [])
        with self.assertRaises(ValueError):
            game.choose('guard', {'attack': 1, 'defense': 1,
                                  'timing': 0, 'extra_damage': 0})
        self.assertEqual(game.encounter.time, 0)
        with self.assertRaises(ValueError):
            game.choose('north', {'attack': 0, 'defense': 0,
                                  'timing': 0, 'extra_damage': 0})
        self.assertEqual(game.encounter.time, 0)

    def test_defensive_effort_available_to_attack_and_guard(self):
        game = TacticalDuel()
        game.choose('thrust', {'attack': 1, 'defense': 1, 'timing': 0, 'extra_damage': 0})
        self.assertEqual(game.player.strategy.defense, 1)
        game.choose('guard', {'attack': 0, 'defense': 1, 'timing': 0, 'extra_damage': 0})
        self.assertIsNone(game._pending(game.player))
        self.assertEqual(game.player.strategy.defense, 1)
        self.assertEqual(game.player.get_skill_experience('Dagger'), 0)

    def test_exact_own_damage_and_severity_but_no_hidden_opponent_total(self):
        game = TacticalDuel(17)
        game.choose('thrust')
        game.choose('wait')
        game.choose('wait')
        with patch('action.roll_dice', side_effect=[15, 4]):
            state = game.choose('wait')
        own = state['history'][-1]['results'][0]
        self.assertIn('HIT!', own)
        self.assertIn('3 HP dealt to Raider', own)
        self.assertIn('substantial', own)
        self.assertIn('4 armor durability damage', own)
        self.assertIsNone(state['foe']['hp'])
        self.assertNotIn('hp_max', state['foe'])

    def test_journal_contains_and_verifies_foe_choices_and_actions(self):
        game = TacticalDuel(17)
        game.choose('thrust', {'attack': 1, 'defense': 0, 'timing': 1, 'extra_damage': 0})
        game.choose('north')
        session = game.to_session()
        self.assertEqual(session['version'], 2)
        self.assertEqual(len(session['foe_actions']), 2)
        self.assertTrue(session['foe_actions'][0]['pending'])
        self.assertEqual(session['foe_actions'][0]['pending']['motion'], 'swing')
        self.assertEqual(session['foe_actions'][0]['decision'], session['foe_decisions'][0])
        restored = TacticalDuel.from_session(session)
        self.assertEqual(restored._journal_signature(), game._journal_signature())
        restored.choose('wait')
        game.choose('wait')
        self.assertEqual(restored._journal_signature(), game._journal_signature())
        bad = copy.deepcopy(session)
        bad['foe_actions'][0]['pending']['motion'] = 'thrust'
        with self.assertRaisesRegex(ValueError, 'validation failed'):
            TacticalDuel.from_session(bad)

    def test_legacy_command_only_version_one_journal_still_loads(self):
        game = TacticalDuel()
        game.choose('thrust')
        game.choose('north')
        legacy = {'format': 'universe.tactical-duel', 'version': 1,
                  'seed': game.seed, 'commands': list(game.commands)}
        other = TacticalDuel(game.seed)
        legacy['checks'] = []
        for cmd in legacy['commands']:
            other.choose(cmd)
            legacy['checks'].append(other._signature())
        restored = TacticalDuel.from_session(legacy)
        self.assertEqual(restored._signature(), game._signature())

    def test_viewer_exposes_separate_action_cues_and_effort_inputs(self):
        template = (ROOT / 'examples' / 'live_combat_template.html').read_text()
        self.assertIn('data.player_cues', template)
        self.assertIn('data.foe_cues', template)
        self.assertIn('data-effort="timing"', template)
        self.assertIn("rr.distance.toFixed(2)", template)
        self.assertIn('foe_actions', (ROOT / 'src' / 'tactical_duel.py').read_text())


if __name__ == '__main__':
    unittest.main()


class TestEffortHTTP(unittest.TestCase):
    def test_strategy_post_and_observer_view(self):
        game = TacticalDuel()
        server = HTTPServer(('127.0.0.1', 0), make_handler(game))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_port
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
            conn.request('POST', '/choose',
                         body=json.dumps({'command': 'thrust', 'effort': {
                             'attack': 1, 'defense': 0,
                             'timing': 1, 'extra_damage': 0}}),
                         headers={'Host': f'127.0.0.1:{port}',
                                  'Origin': f'http://127.0.0.1:{port}',
                                  'Content-Type': 'application/json'})
            res = conn.getresponse()
            data = json.loads(res.read())
            self.assertEqual(res.status, 200)
            self.assertEqual(data['player']['pending']['due'], 3)
            self.assertNotIn('foe_activity', str(data['history']))
            self.assertNotIn('foe_decisions', data)
            self.assertIn('range', data)
            conn.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(3)
