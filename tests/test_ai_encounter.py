"""Constrained human-vs-AI Encounter with actual authoritative combat actions."""
import copy
from http.server import HTTPServer
import json
from pathlib import Path
import sys
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]
from ai_duel import AgentDuel, OpenAIPolicy, TacticalPolicy
from ai_encounter import main as app_main
from live_combat import make_handler
from melee_combat import MeleeStrike
from melee_defense import MeleeDefense


class Constant:
    def __init__(self, command, effort=None):
        self.command, self.effort = command, effort
        self.inputs = []

    def decide(self, data):
        self.inputs.append(copy.deepcopy(data))
        return {'command': self.command, 'reason': 'Observed tactics',
                'effort': self.effort}


class AIEncounterTest(unittest.TestCase):
    def test_all_policy_commands_checked_against_same_engine_commands(self):
        game = AgentDuel()
        observation = game.observation()
        self.assertIn('swing', observation['legal'])
        self.assertIn('thrust', observation['legal'])
        self.assertIn('guard', observation['legal'])
        self.assertIn('north', observation['legal'])
        self.assertIn('cancel', observation['legal'])
        self.assertNotIn('parry', observation['legal'])
        self.assertTrue(set(observation['legal']) <= set(game.COMMANDS))

    def test_policy_cannot_read_hidden_opponent_hp_or_skills(self):
        policy = Constant('guard')
        game = AgentDuel(policy=policy)
        game.choose('wait')
        snapshot = policy.inputs[0]
        self.assertEqual(set(snapshot['opponent']), {'observed', 'distance', 'bearing', 'incoming', 'weapon', 'armor'})
        self.assertNotIn('hp', json.dumps(snapshot['opponent']).lower())
        self.assertNotIn('weapon_skill', json.dumps(snapshot['opponent']))

    def test_reach_is_weapon_and_body_specific_and_applies_at_impact(self):
        game = AgentDuel(policy=Constant('wait'))
        state = game.state()
        self.assertAlmostEqual(state['ranges']['scout'],
            (.375 * game.player.original.length + 1.25) / 3, places=4)
        self.assertAlmostEqual(state['ranges']['raider'],
            (.375 * game.foe.original.length + 3.5) / 3, places=4)
        self.assertFalse(state['range']['in_range'])
        self.assertTrue(state['range']['opponent_in_range'])
        game.choose('thrust')
        self.assertAlmostEqual(game._pending(game.player).reach, state['ranges']['scout'], places=3)
        opponent = AgentDuel(policy=Constant('thrust'))
        opponent.choose('wait')
        self.assertAlmostEqual(opponent._pending(opponent.foe).reach,
                               state['ranges']['raider'], places=3)

    def test_visible_equipment_without_leaking_private_vitals(self):
        game = AgentDuel(policy=Constant('wait'))
        view = game.state()
        self.assertEqual(view['foe']['weapon'], 'Longsword')
        self.assertEqual(view['foe']['armor'], 'Leather armor')
        self.assertIsNone(view['foe']['hp'])
        observed = game.observation()
        self.assertEqual(observed['opponent']['weapon'], 'Dagger')
        self.assertEqual(observed['opponent']['armor'], 'None')

    def test_reaction_readiness_reports_attack_specific_preparation(self):
        game = AgentDuel(policy=Constant('thrust'))
        self.assertNotIn('parry', game.state()['player_legal'])
        self.assertIn('No observed incoming', game.state()['reaction_readiness']['parry'])
        game.choose('wait')
        state = game.state()
        self.assertIn('parry', state['player_legal'])
        self.assertIn('dodge', state['player_legal'])
        self.assertIn('Ready:', state['reaction_readiness']['parry'])
        game.policy = Constant('wait')
        game.choose('wait')
        game.choose('wait')
        self.assertNotIn('parry', game.state()['player_legal'])
        self.assertIn('dodge', game.state()['player_legal'])
        self.assertIn('Too late', game.state()['reaction_readiness']['parry'])

    def test_wait_and_movement_do_not_reallocate_pending_attack_effort(self):
        game = AgentDuel(policy=Constant('wait'))
        chosen = {'attack': 1, 'defense': 1, 'timing': 0, 'extra_damage': 0}
        game.choose('thrust', chosen)
        strike = game._pending(game.player)
        self.assertEqual(game.player.strategy.attack, 1)
        self.assertEqual(game.player.strategy.defense, 1)
        game.choose('west')
        self.assertEqual(game._pending(game.player).id, strike.id)
        self.assertEqual(game.player.strategy.attack, 1)
        self.assertEqual(game.player.strategy.defense, 1)

    def test_http_401_has_actionable_message_and_no_retry(self):
        from urllib.error import HTTPError
        policy = OpenAIPolicy('test', api_key='unused')
        attempts = []
        def unauthenticated(payload, timeout=None):
            attempts.append(payload)
            raise HTTPError('https://api.openai.com/v1/responses', 401,
                            'Unauthorized', {}, None)
        # Exercise the real HTTP error interpreter without contacting a service.
        from unittest.mock import patch
        with patch('ai_duel.urlopen', side_effect=unauthenticated):
            game = AgentDuel(policy=policy)
            game.choose('wait')
            game.choose('wait')
        self.assertEqual(len(attempts), 1)
        self.assertIn('HTTP 401', game.ai_decisions[0]['fallback'])
        self.assertIn('Check the API key', game.ai_decisions[1]['fallback'])

    def test_foe_uses_real_melee_action_and_timing(self):
        game = AgentDuel(policy=Constant('thrust'))
        game.choose('wait')
        pending = game._pending(game.foe)
        self.assertIsInstance(pending, MeleeStrike)
        self.assertEqual(pending.actor_id, game.foe.id)
        self.assertEqual(pending.event_type, 'thrust')
        self.assertGreater(pending.end_time, game.encounter.time)

    def test_foe_guard_uses_real_being_strategy(self):
        game = AgentDuel(policy=Constant('guard'))
        game.choose('wait')
        self.assertGreater(game.foe.strategy.defense, 0)
        self.assertIsNone(game._pending(game.foe))

    def test_foe_movement_really_changes_position(self):
        game = AgentDuel(policy=Constant('west'))
        before = game.foe.get_position().x
        game.choose('wait')
        self.assertLess(game.foe.get_position().x, before)

    def test_foe_can_choose_real_targeted_dodge(self):
        game = AgentDuel(policy=Constant('wait'))
        game.choose('thrust')
        self.assertIsInstance(game._pending(game.player), MeleeStrike)
        game.policy = Constant('dodge')
        game.choose('wait')
        self.assertIsInstance(game._pending(game.foe), MeleeDefense)
        self.assertEqual(game._pending(game.foe).kind, 'dodge')
        self.assertEqual(game._pending(game.foe).target_action_id,
                         game._pending(game.player).id)

    def test_removed_incoming_attack_does_not_cause_partial_step_failure(self):
        game = AgentDuel(policy=Constant('wait'))
        game.choose('thrust')
        game.policy = Constant('dodge')
        game.choose('cancel')  # same second the opponent independently decided to dodge
        self.assertEqual(game.encounter.time, 2)
        self.assertEqual(len(game.commands), 2)

    def test_opponent_effort_uses_same_strategy_and_budget(self):
        effort = {'attack': 0, 'defense': 1, 'timing': 0, 'extra_damage': 0}
        game = AgentDuel(policy=Constant('guard', effort))
        game.choose('wait')
        self.assertEqual(game.foe.strategy.defense, 1)
        too_much = dict(effort, defense=100)
        policy = Constant('guard', too_much)
        game = AgentDuel(policy=policy)
        game.choose('wait')
        self.assertIsNotNone(game.ai_decisions[-1]['fallback'])
        self.assertLessEqual(game.foe.strategy.defense, 1)

    def test_invalid_model_command_falls_back_without_modifying_rulebook(self):
        game = AgentDuel(policy=Constant('teleport'))
        game.choose('wait')
        self.assertIn('unavailable', game.ai_decisions[-1]['fallback'])
        self.assertIn(game.ai_decisions[-1]['choice']['command'], game.COMMANDS)

    def test_incorrect_player_effort_does_not_invoke_model_or_advance(self):
        policy = Constant('wait')
        game = AgentDuel(policy=policy)
        with self.assertRaises(ValueError):
            game.choose('north', {'attack': 1, 'defense': 0, 'timing': 0,
                                  'extra_damage': 0})
        self.assertEqual(policy.inputs, [])
        self.assertEqual(game.encounter.time, 0)

    def test_legacy_session_still_replays_with_original_shared_reach(self):
        old = AgentDuel(policy=Constant('thrust'), legacy_reach=True)
        for command in ('wait', 'wait', 'thrust', 'west', 'wait'):
            old.choose(command)
        record = old.to_session()
        self.assertEqual(record['version'], 1)
        restored = AgentDuel.from_session(record)
        self.assertEqual(restored.state()['reach_profile'], 'legacy shared reach')
        self.assertEqual(restored.state()['ranges']['scout'], 2)
        self.assertEqual(restored.state()['ranges']['raider'], 2)
        self.assertEqual(restored._journal_signature(), old._journal_signature())
        self.assertEqual(restored.to_session(), record)

    def test_replay_persists_model_decisions_and_never_calls_policy(self):
        game = AgentDuel(policy=Constant('west'))
        for cmd in ('wait', 'thrust', 'north', 'wait'):
            game.choose(cmd)
        session = json.loads(json.dumps(game.to_session()))
        unused = Constant('teleport')
        restored = AgentDuel.from_session(session, policy=unused)
        self.assertEqual(len(unused.inputs), 0)
        self.assertEqual(restored._journal_signature(), game._journal_signature())
        self.assertEqual(restored.ai_decisions, game.ai_decisions)

    def test_fallback_provenance_survives_save_and_replay(self):
        original = AgentDuel(policy=Constant('teleport'))
        original.choose('wait')
        session = original.to_session()
        restored = AgentDuel.from_session(session)
        self.assertEqual(restored.state()['ai_last']['fallback'],
                         original.state()['ai_last']['fallback'])
        self.assertEqual(restored.timeline()[-1]['ai_last']['fallback'],
                         original.state()['ai_last']['fallback'])

    def test_tampered_decisions_fail_replay(self):
        game = AgentDuel()
        for _ in range(3): game.choose('wait')
        session = game.to_session()
        session['ai_decisions'][0]['choice']['command'] = 'guard'
        with self.assertRaises(ValueError):
            AgentDuel.from_session(session)

    def test_tactical_policy_is_deterministic(self):
        a, b = AgentDuel(87), AgentDuel(87)
        for action in ['wait', 'wait', 'swing', 'west', 'wait', 'wait']:
            a.choose(action)
            b.choose(action)
        self.assertEqual(a.to_session(), b.to_session())

    def test_openai_policy_only_sends_observation_and_parses_structured_choice(self):
        captured = []
        def send(body):
            captured.append(body)
            return {'output': [{'type': 'message', 'content': [
                {'type': 'output_text', 'text': json.dumps({'command': 'guard',
                    'reason': 'Defend this second', 'effort': None})}]}]}
        game = AgentDuel(policy=OpenAIPolicy('test-model', api_key='test-key', transport=send))
        game.choose('wait')
        self.assertEqual(game.ai_decisions[-1]['choice']['command'], 'guard')
        self.assertEqual(captured[0]['model'], 'test-model')
        self.assertIn('weapon_skill', captured[0]['input'])
        self.assertNotIn('OPENAI_API_KEY', captured[0]['input'])

    def test_model_transport_failure_has_safe_local_fallback(self):
        def fail(_): raise OSError('Disconnected')
        game = AgentDuel(policy=OpenAIPolicy('test', api_key='test', transport=fail))
        game.choose('wait')
        self.assertIn('Disconnected', game.ai_decisions[-1]['fallback'])
        self.assertEqual(game.encounter.time, 1)


class AIEncounterHTTPTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = AgentDuel()
        cls.server = HTTPServer(('127.0.0.1', 0), make_handler(
            cls.game, template_path=ROOT / 'examples' / 'ai_encounter_template.html'))
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(2)

    def post(self, path, body, origin=None):
        req = Request(self.base + path, data=json.dumps(body).encode(), method='POST',
                      headers={'Content-Type': 'application/json',
                               'Origin': origin or self.base})
        return json.load(urlopen(req, timeout=5))

    def test_page_displays_real_ai_controls_and_reasons(self):
        text = urlopen(self.base, timeout=5).read().decode()
        self.assertIn('Autonomous opponent', text)
        self.assertIn('data-command="thrust"', text)
        self.assertIn('data-command="parry"', text)
        self.assertIn('aiReason', text)
        for control in ('beginning','end','play','pause','stop','pace','commitEffort'):
            self.assertIn('id="'+control+'"', text)

    def test_browser_turn_advances_and_returns_ai_decision(self):
        result = self.post('/choose', {'command': 'wait'})
        self.assertEqual(result['time'], 1)
        self.assertIn('ai_last', result)
        self.assertIn('choice', result['ai_last'])

    def test_origin_protection_and_no_time_advance(self):
        before = self.game.encounter.time
        with self.assertRaises(HTTPError) as err:
            self.post('/choose', {'command': 'wait'}, origin='https://hostile.example')
        self.assertEqual(err.exception.code, 403)
        self.assertEqual(self.game.encounter.time, before)


if __name__ == '__main__':
    unittest.main()
