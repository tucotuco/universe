"""Combat usability, observer boundaries, exertion and checked session journal."""
import http.client
import json
import math
import random
import sys
import tempfile
import threading
import unittest
from http.server import HTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]
from tactical_duel import TacticalDuel
from melee_combat import MeleeStrike
from live_combat import make_handler


class TestTacticalUsability(unittest.TestCase):
    def test_replace_thrust_with_swing_retains_historical_cancellation(self):
        game = TacticalDuel()
        game.choose('thrust')
        prior = game._pending(game.player)
        game.choose('swing')
        self.assertNotEqual(prior.id, game._pending(game.player).id)
        self.assertIn(prior.id, game.encounter.cancelled_action_list)
        self.assertNotIn(prior.id, game.encounter.finished_action_list)
        self.assertEqual(prior.cancellation_reason, 'interrupted')
        self.assertEqual(game.player.get_skill_experience('Dagger'), 0)
        self.assertEqual(game.encounter.time, 2)

    def test_guard_interrupts_and_cancel_does_not_exercise_weapon(self):
        game = TacticalDuel()
        game.choose('thrust')
        game.choose('guard')
        self.assertIsNone(game._pending(game.player))
        self.assertEqual(game.player.strategy.defense, 2)
        self.assertEqual(game.player.get_skill_experience('Dagger'), 0)
        game.choose('thrust')
        game.choose('cancel')
        self.assertIsNone(game._pending(game.player))
        self.assertEqual(len(game.encounter.cancelled_action_list), 2)
        self.assertEqual(game.player.get_skill_experience('Dagger'), 0)

    def test_invalid_replacement_preserves_first_attack(self):
        game = TacticalDuel()
        game.choose('thrust')
        game.choose('west')
        game.choose('west')
        before = game._pending(game.player)
        # Move the target far without advancing time; a rejected request
        # must not erase the player's original unfinished action.
        from spatial.state import CartesianPosition
        game.foe.set_position(CartesianPosition(20, 0, 0))
        with self.assertRaises(ValueError):
            game.choose('swing')
        self.assertIs(game._pending(game.player), before)
        self.assertEqual(game.encounter.time, 3)

    def test_eight_directions_have_equal_distance(self):
        for direction in TacticalDuel.DIRECTION:
            with self.subTest(direction=direction):
                game = TacticalDuel()
                p = game.player.get_position()
                game.choose(direction)
                q = game.player.get_position()
                self.assertAlmostEqual(math.hypot(q.x - p.x, q.y - p.y), .25)
                self.assertIn(direction, game.state()['history'][-1]['player_choice'])

    def test_maximum_hp_and_fatigue_visible_only_for_player(self):
        game = TacticalDuel()
        data = game.state()
        self.assertEqual(data['player']['hp_max'], 10)
        self.assertEqual(data['player']['fatigue_state'], 'fresh')
        self.assertEqual(data['player']['fatigue_next_check'], 6)
        self.assertNotIn('fatigue', data['foe'])
        self.assertIn('hp_max', game.state(audit=True)['foe'])

    def test_opponent_apparent_action_has_no_exact_secret_inference(self):
        game = TacticalDuel()
        response = game.choose('wait')
        self.assertIn('apparent_action', response['foe'])
        self.assertIn('prepare', response['foe']['apparent_action'])
        self.assertNotIn('foe_choice', str(response['history']))
        self.assertIn('foe_cue', response['history'][-1])
        self.assertNotIn('weapon_skill', response['foe'])

    def test_completed_hit_reports_hp_and_armor_loss(self):
        game = TacticalDuel(17)
        game.choose('thrust')
        game.choose('wait')
        game.choose('wait')
        with patch('action.roll_dice', side_effect=[15, 4]):
            game.choose('wait')
        info = game.state()['history'][-1]['results']
        self.assertTrue(info)
        self.assertIn('HP dealt to Raider', info[0])
        self.assertIn('relative to estimated endurance', info[0])
        self.assertNotIn('10→', info[0])
        audit = game.state(audit=True)['history'][-1]['results'][0]['text']
        self.assertIn('Raider:', audit)
        self.assertIn('HP damage', audit)
        self.assertIn('armor:', audit)
        self.assertIn('weapon XP', audit)

    def test_exertion_check_at_six_seconds_advances_being_fatigue(self):
        game = TacticalDuel(17)
        game.encounter.difficulty_class = 999  # prevent normal attacks interrupting the test
        with patch.object(game.player.exertion, 'check', return_value=False), \
             patch.object(game.foe.exertion, 'check', return_value=True):
            for _ in range(6):
                game.choose('wait')
        self.assertEqual(game.player.get_fatigue_level(), 1)
        self.assertEqual(game.player.exertion.get_end_time(), 12)
        self.assertEqual(game.foe.get_fatigue_level(), 0)
        self.assertIn('fatigue', str(game.state()['history'][-1]['results']))
        self.assertNotIn('Raider fatigue check', str(game.state()['history'][-1]))

    def test_fatigue_level_reduces_hit_probability(self):
        game = TacticalDuel()
        game.player.set_strategy(attack=0, defense=0)
        action = MeleeStrike(game.encounter, game.player.id, game.foe.id,
                             game.player_weapon, motion='thrust', reach=2)
        self.assertTrue(action.roll_hits(11, 12))
        game.player.set_fatigue_level(2)
        self.assertFalse(action.roll_hits(11, 12))
        game.player.set_fatigue_level(5)
        self.assertTrue(game.ended())

    def test_saved_session_replays_and_continues_without_rng_perturbation(self):
        game = TacticalDuel(17)
        for c in ('thrust', 'northeast', 'guard', 'swing', 'wait'):
            game.choose(c)
        current_rng = random.getstate()
        data = game.to_session()
        self.assertEqual(random.getstate(), current_rng)
        restored = TacticalDuel.from_session(data)
        self.assertEqual(restored._signature(), game._signature())
        self.assertEqual(len(restored.timeline()), 6)
        self.assertEqual(restored.timeline()[0]['time'], 0)
        self.assertEqual(restored.timeline()[-1]['time'], 5)
        for frame in restored.timeline():
            if frame['foe']:
                self.assertIsNone(frame['foe']['hp'])
        restored.choose('wait')
        self.assertEqual(restored.encounter.time, 6)

    def test_continued_encounter_matches_uninterrupted_sequence(self):
        game = TacticalDuel(17)
        for c in ('thrust', 'northeast', 'guard', 'swing', 'wait'):
            game.choose(c)
        journal = game.to_session()
        game.choose('wait')
        uninterrupted = game._signature()
        resumed = TacticalDuel.from_session(journal)
        resumed.choose('wait')
        self.assertEqual(resumed._signature(), uninterrupted)

    def test_tampered_session_fails_without_partial_world_commit(self):
        game = TacticalDuel()
        game.choose('guard')
        data = game.to_session()
        data['checks'][0] = 'bad fingerprint'
        with self.assertRaisesRegex(ValueError, 'validation failed'):
            TacticalDuel.from_session(data)
        self.assertEqual(game.encounter.time, 1)
        with self.assertRaisesRegex(ValueError, 'Invalid session structure'):
            TacticalDuel.from_session({'seed': 17})
        with self.assertRaisesRegex(ValueError, 'Unsupported session'):
            TacticalDuel.from_session({**game.to_session(), 'version': 999})


class TestSavedTacticalHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.filename = Path(cls.tmp.name) / 'test-session.json'
        cls.game = TacticalDuel(17)
        cls.server = HTTPServer(('127.0.0.1', 0), make_handler(cls.game, save_path=cls.filename))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(3)
        cls.tmp.cleanup()

    def request(self, path, *, method='GET', origin=None, body=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=4)
        headers = {'Host': f'127.0.0.1:{self.server.server_port}'}
        if method == 'POST':
            headers['Origin'] = origin or f'http://127.0.0.1:{self.server.server_port}'
            headers['Content-Type'] = 'application/json'
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        data = json.loads(response.read())
        status = response.status
        conn.close()
        return status, data

    def test_save_reload_and_replay_http_are_filtered(self):
        self.game.choose('guard')
        code, status = self.request('/save', method='POST', body='{}')
        self.assertEqual(code, 200)
        self.assertTrue(self.filename.exists())
        with self.filename.open() as f:
            loaded = TacticalDuel.from_session(json.load(f))
        self.assertEqual(loaded._signature(), self.game._signature())
        code, replay = self.request('/timeline')
        self.assertEqual(code, 200)
        self.assertEqual(replay['frames'][-1]['time'], 1)
        for frame in replay['frames']:
            self.assertNotIn('foe_choice', str(frame['history']))
            self.assertNotIn('weapon_skill', frame['foe'])

    def test_read_only_replay_rejects_commands(self):
        other = HTTPServer(('127.0.0.1', 0), make_handler(
            TacticalDuel(17), replay_only=True))
        thread = threading.Thread(target=other.serve_forever, daemon=True)
        thread.start()
        try:
            conn = http.client.HTTPConnection('127.0.0.1', other.server_port, timeout=3)
            conn.request('POST', '/choose', body=b'{"command":"wait"}',
                         headers={'Host': f'127.0.0.1:{other.server_port}',
                                  'Origin': f'http://127.0.0.1:{other.server_port}',
                                  'Content-Type': 'application/json'})
            resp = conn.getresponse()
            self.assertEqual(resp.status, 400)
            self.assertIn(b'read-only', resp.read())
            conn.close()
        finally:
            other.shutdown()
            other.server_close()
            thread.join(3)

    def test_save_rejects_foreign_origin(self):
        code, _ = self.request('/save', method='POST', origin='https://other.invalid', body='{}')
        self.assertEqual(code, 403)


if __name__ == '__main__':
    unittest.main()
