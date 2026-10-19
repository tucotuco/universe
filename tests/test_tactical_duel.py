"""Regression for a browser-controlled real Encounter and same-time attacks."""
import http.client
import json
import sys
import threading
import unittest
from http.server import HTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]
from tactical_duel import TacticalDuel
from armed_duel import make_duel
from melee_combat import MeleeStrike
from live_combat import make_handler


class TestTacticalDuel(unittest.TestCase):
    def test_no_scripted_strikes_or_experience_at_initialization(self):
        game = TacticalDuel(17)
        self.assertFalse(game.encounter.pending_action_list)
        self.assertEqual(game.player.get_skill_experience('Dagger'), 0)
        self.assertTrue(game.state()['observed_now'])
        self.assertIsNone(game.state()['foe']['hp'])
        self.assertEqual(game.state(audit=True)['foe']['hp'], 10)

    def test_attacks_consume_weapon_time_and_grant_xp_only_on_attempt(self):
        game = TacticalDuel(17)
        game.choose('thrust')
        self.assertEqual(game.state()['player']['pending']['due'], 4)
        for _ in range(3):
            game.choose('wait')
        self.assertEqual(game.encounter.time, 4)
        self.assertEqual(game.player.get_skill_experience('Dagger'), 10)
        self.assertEqual(len(game.player.skill_use_history), 1)
        self.assertEqual(game.player.skill_use_history[0].time, 4)

    def test_invalid_choice_and_double_attack_preserve_time(self):
        game = TacticalDuel(17)
        with self.assertRaisesRegex(ValueError, 'Unknown'):
            game.choose('look behind')
        self.assertEqual(game.encounter.time, 0)
        game.choose('thrust')
        with self.assertRaisesRegex(ValueError, 'in progress'):
            game.choose('thrust')
        with self.assertRaisesRegex(ValueError, 'unfinished'):
            game.choose('guard')
        self.assertEqual(game.encounter.time, 1)

    def test_movement_is_from_real_encounter_and_disables_out_of_range_attacks(self):
        game = TacticalDuel(17)
        start = game.player.get_position().x
        game.choose('west')
        self.assertAlmostEqual(game.player.get_position().x, start - .25)
        self.assertEqual(game.state()['player']['position'][0], start - .25)
        for _ in range(5):
            game.choose('west')
        self.assertGreater(game.encounter.distance_between_beings(game.player.id, game.foe.id), 2)
        with self.assertRaisesRegex(ValueError, 'out_of_reach'):
            game.choose('thrust')

    def test_guard_changes_real_defensive_strategy_and_attack_resets_it(self):
        game = TacticalDuel(17)
        game.choose('guard')
        self.assertEqual(game.player.strategy.defense, 2)
        game.choose('thrust')
        self.assertEqual(game.player.strategy.defense, 0)
        self.assertEqual(game.state()['player']['strategy']['defense'], 0)

    def test_guard_changes_real_hit_roll_odds(self):
        game = TacticalDuel(17)
        enemy = MeleeStrike(game.encounter, game.foe.id, game.player.id,
                            game.foe_weapon, motion='swing', reach=2)
        with patch('action.roll_dice', return_value=11):
            self.assertEqual(enemy.hit_result(12), 'normal')
        game.choose('guard')
        with patch('action.roll_dice', return_value=11):
            self.assertEqual(enemy.hit_result(12), 'miss')

    def test_player_state_has_no_hidden_opponent_skills_or_health(self):
        game = TacticalDuel(17)
        state = game.state()
        self.assertNotIn('weapon_skill', state['foe'])
        self.assertIsNone(state['foe']['xp'])
        self.assertNotIn('foe_choice', str(state['history']))
        self.assertEqual(game.state(audit=True)['foe']['weapon'], 'Longsword')

    def test_prior_hidden_enemy_events_stay_hidden_on_later_detection(self):
        game = TacticalDuel(17)
        game.history = [{'time': 3, 'player_choice': 'Scout waits.',
                         'foe_choice': 'Secret intention',
                         'foe_observed': False,
                         'results': [{'actor': game.foe.id, 'text': 'secret outcome'}]}]
        self.assertNotIn('secret outcome', str(game.state()['history']))
        self.assertIn('secret outcome', str(game.state(audit=True)['history']))

    def test_ended_game_rejects_action(self):
        game = TacticalDuel(17)
        game.player.set_hit_points(0)
        self.assertTrue(game.ended())
        with self.assertRaisesRegex(ValueError, 'ended'):
            game.choose('wait')

    def test_simultaneous_strikes_still_attempt_after_earlier_impact(self):
        world, encounter, scout, raider, _, initial = make_duel(schedule_attacks=False)
        # Opponent starts at t=0 with a six-second longsword swing.
        raider_strike = MeleeStrike(encounter, raider.id, scout.id,
                                   initial[1].instrument_id, motion='swing', reach=2)
        encounter.schedule_action(raider_strike)
        encounter.step(2)
        # Scout starts at t=2 with a four-second dagger thrust: same t=6 impact.
        scout_strike = MeleeStrike(encounter, scout.id, raider.id,
                                  initial[0].instrument_id, motion='thrust', reach=2)
        encounter.schedule_action(scout_strike)
        scout.set_hit_points(1)
        with patch('action.roll_dice', side_effect=[17, 4, 17, 4]):
            tick = encounter.step(4)
        self.assertEqual(tick.completed_action_ids, (raider_strike.id, scout_strike.id))
        self.assertLessEqual(scout.get_hit_points(), 0)
        self.assertEqual(scout_strike.resolution.skill_exercises[0].experience, 10)
        self.assertNotEqual(scout_strike.combat_result.outcome, 'unable_to_act')
        self.assertEqual(scout.get_skill_experience('Dagger'), 10)



class TestLocalCombatHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = TacticalDuel(17)
        cls.server = HTTPServer(('127.0.0.1', 0), make_handler(cls.game))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(3)

    def setUp(self):
        # HTTP tests are independent even when unittest changes their order.
        self.game = TacticalDuel(17)
        self.server.RequestHandlerClass = make_handler(self.game)

    def request(self, method, path, body=None, origin=None, host=None, kind=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        headers = {'Host': host or f'127.0.0.1:{self.server.server_port}'}
        if origin is not None:
            headers['Origin'] = origin
        if kind:
            headers['Content-Type'] = kind
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        output = response.read()
        status = response.status
        conn.close()
        return status, output

    def test_index_and_filtered_state(self):
        status, index = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn(b'Live combat', index)
        status, data = self.request('GET', '/state')
        self.assertEqual(status, 200)
        state = json.loads(data)
        self.assertIsNone(state['foe']['hp'])
        self.assertEqual(state['time'], 0)

    def test_reject_cross_origin_wrong_type_wrong_host_without_time_advance(self):
        url = f'http://127.0.0.1:{self.server.server_port}'
        for origin, host, kind, expected in (
            ('https://other.example', None, 'application/json', 403),
            (url, None, 'text/plain', 415),
            (url, 'malicious.example', 'application/json', 403),
        ):
            code, _ = self.request('POST', '/choose', body=b'{"command":"wait"}',
                                   origin=origin, host=host, kind=kind)
            self.assertEqual(code, expected)
        self.assertEqual(self.game.encounter.time, 0)

    def test_post_executes_real_encounter_step(self):
        origin = f'http://127.0.0.1:{self.server.server_port}'
        code, output = self.request('POST', '/choose', body=b'{"command":"wait"}',
                                   origin=origin, kind='application/json')
        self.assertEqual(code, 200)
        state = json.loads(output)
        self.assertEqual(state['time'], 1)
        self.assertEqual(self.game.encounter.time, 1)

if __name__ == '__main__':
    unittest.main()
