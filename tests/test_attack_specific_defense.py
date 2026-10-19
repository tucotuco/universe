"""Defensive action targets a single attack and must be ready at its impact."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]
from tactical_duel import TacticalDuel
from melee_defense import MeleeDefense
from melee_combat import MeleeStrike


class TestAttackSpecificDefense(unittest.TestCase):
    def duel_with_attack(self, seconds=1):
        duel = TacticalDuel(17)
        for _ in range(seconds): duel.choose('wait')
        self.assertTrue(duel.state()['perceived_incoming_attack'])
        return duel

    def test_parry_targets_one_strike_and_waits_until_impact(self):
        duel = self.duel_with_attack()
        threatened = duel._pending(duel.foe)
        duel.choose('parry')
        reaction = duel._pending(duel.player)
        self.assertIsInstance(reaction, MeleeDefense)
        self.assertEqual(reaction.target_action_id, threatened.id)
        self.assertEqual(reaction.ready_at, 4)
        self.assertEqual(reaction.end_time, threatened.end_time)
        self.assertEqual(duel.player.get_skill_experience('Dagger'), 0)
        for _ in range(3): duel.choose('wait')
        self.assertEqual(duel._pending(duel.player), reaction)
        with patch('melee_defense.roll_dice', side_effect=[20, 1]):
            duel.choose('wait')
        self.assertEqual(duel.player.get_skill_experience('Dagger'), 10)
        self.assertEqual(threatened.defended_by, reaction.id)

    def test_dodge_displacement_only_at_designated_impact(self):
        duel = self.duel_with_attack(3)
        start = duel.player.get_position().x
        duel.choose('dodge')
        self.assertEqual(duel.player.get_position().x, start)
        duel.choose('wait')
        self.assertEqual(duel.player.get_position().x, start)
        duel.choose('wait')
        self.assertAlmostEqual(duel.player.get_position().x, start - duel.DODGE_PER_SECOND)
        self.assertEqual(duel.player.get_skill_experience('tumble'), 10)

    def test_too_late_to_parry_rejects_and_keeps_existing_attack(self):
        duel = self.duel_with_attack(4)  # enemy strike due at 6
        duel.choose('thrust')
        old = duel._pending(duel.player)
        time = duel.encounter.time
        with self.assertRaisesRegex(ValueError, 'cannot be ready'):
            duel.choose('parry')
        self.assertEqual(duel.encounter.time, time)
        self.assertIs(duel._pending(duel.player), old)

    def test_defense_does_not_retarget_to_new_strike(self):
        duel = self.duel_with_attack()
        strike = duel._pending(duel.foe)
        duel.choose('parry')
        defense = duel._pending(duel.player)
        duel.encounter.cancel_action(strike.id)
        # New incoming strike replaces the canceled one and resolves on the
        # same timestamp. The defense must not switch target implicitly.
        new_strike = MeleeStrike(duel.encounter, duel.foe.id, duel.player.id,
                                 duel.foe_weapon, motion='swing', reach=duel.REACH)
        duel.encounter.schedule_action(new_strike)
        new_strike.end_time = strike.end_time
        for _ in range(4): duel.choose('wait')
        self.assertEqual(defense.result, 'no_threat')
        self.assertEqual(duel.player.get_skill_experience('Dagger'), 0)
        self.assertIsNone(new_strike.defended_by)

    def test_defense_requires_existing_perceived_strike(self):
        duel = TacticalDuel(17)
        with self.assertRaisesRegex(ValueError, 'No currently perceived incoming attack'):
            duel.choose('dodge')
        self.assertEqual(duel.encounter.time, 0)

    def test_save_resume_preserves_specific_target_and_randomness(self):
        duel = self.duel_with_attack(2)
        duel.choose('parry')
        saved = duel.to_session()
        self.assertEqual(saved['version'], 3)
        resumed = TacticalDuel.from_session(json.loads(json.dumps(saved)))
        self.assertEqual(resumed._pending(resumed.player).target_action_id,
                         resumed._pending(resumed.foe).id)
        for _ in range(3):
            duel.choose('wait'); resumed.choose('wait')
        self.assertEqual(duel._journal_signature(), resumed._journal_signature())

    def test_v2_no_reaction_session_remains_replayable(self):
        duel = TacticalDuel(17)
        duel.choose('thrust')
        duel.choose('wait')
        saved = duel.to_session()
        saved['version'] = 2
        resumed = TacticalDuel.from_session(json.loads(json.dumps(saved)))
        self.assertEqual(resumed._journal_signature(), duel._journal_signature())

    def test_ui_keyboard_dialog_and_target_cue_present(self):
        html = (ROOT / 'examples/live_combat_template.html').read_text()
        for token in ('ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight',
                      'id="beingDetails"', 'openBeingDetails', 'renderedData',
                      'perceived_incoming_attack', 'aria-label', 'id="beingDetails"'):
            self.assertIn(token, html)
        self.assertNotIn('<div id="player"></div>', html)
        self.assertNotIn('<div id="foe"></div>', html)


if __name__ == '__main__':
    unittest.main()
