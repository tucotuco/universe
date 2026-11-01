"""Integrated Group evidence, independent world realization, and discovery."""
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from action_evaluation import AwarenessEffect, DamageEffect, PracticeEffect
from examples.group_spot_world_realization import _execute


class TestGroupSpotWorldRealization(unittest.TestCase):
    def test_group_evidence_world_realization_discovery_and_thrust(self):
        state = _execute()
        encounter = state['encounter']
        world, group, member = state['world'], state['group'], state['member']
        observer_one, observer_two = state['observers']

        # The Agent's successful Group Spot provides aggregate evidence and
        # awareness of the Group only. It has no member/slot disclosure.
        self.assertEqual(state['group_spot_record'].facts.outcome, 'success')
        self.assertEqual(set(state['evidence'].reports), {'visible_count'})
        self.assertIsNone(state['evidence'].reported_position)
        self.assertNotIn(member.id, repr(state['evidence']))
        self.assertTrue(encounter.is_aware(observer_two.id, group.id))
        self.assertEqual(state['awareness_after_group_spot'], (False, False))
        self.assertFalse(state['ledgers'][0].evidence)

        # This authored objective requirement names the already-counted slot
        # independently of Spot or any Agent choice.
        requirement = state['world_requirement']
        self.assertIsNone(requirement['trigger_action_id'])
        self.assertEqual((requirement['group_id'], requirement['household'],
                          requirement['category'], requirement['index']),
                         (group.id, 0, 'adults', 0))
        self.assertEqual(state['candidate'].member_id, member.id)
        self.assertEqual(state['candidate'].first_eligible_boundary, 8)
        self.assertIs(world.get_object_by_id(member.id), member)
        self.assertIn(member.id, encounter.being_list)
        self.assertEqual(group.counts(), state['counts_before'])

        # The new Being was absent from boundary 7's shared snapshot and no
        # observer learned its identity at realization. It first appears in
        # the next boundary's snapshot.
        self.assertNotIn(member.id,
                         state['boundary_seven'].pre_action_snapshot.entities)
        self.assertEqual(state['boundary_seven_awareness'], (False, False))
        self.assertIn(member.id,
                      state['boundary_eight'].pre_action_snapshot.entities)
        self.assertEqual(state['boundary_seven_receipt'].action_ids, ())
        self.assertEqual(state['boundary_seven_receipt'].effect_ids, ())
        self.assertNotIn(member.id, world.event_history)

        # The identity-free adapter response does not reveal its bound target.
        self.assertTrue(state['attention_result'].accepted)
        self.assertFalse(hasattr(state['attention_result'], 'target_id'))
        self.assertEqual((state['attention_spot'].start_time,
                          state['attention_spot'].end_time), (8, 14))
        self.assertNotIn(member.id, state['awareness_before_attention'])
        self.assertEqual(state['attention_record'].facts.outcome, 'success')
        self.assertIn(member.id,
                      encounter.aware_beings(observer_two.id))
        self.assertFalse(encounter.is_aware(observer_one.id, member.id))
        awareness = [row.effect for row in state['attention_record'].effects
                     if type(row.effect) is AwarenessEffect]
        self.assertEqual(len(awareness), 1)
        self.assertEqual((awareness[0].target_id, awareness[0].observed_id),
                         (observer_two.id, member.id))

        # The subsequent native Thrust obtains its target from the observer's
        # committed Awareness, then publishes normal causal Target effects.
        strike, record = state['thrust'], state['inspection'].action(
            state['thrust'].id)
        self.assertEqual(strike.target_id, state['thrust_target_id'])
        self.assertIn(strike.target_id, state['awareness_after_attention'])
        self.assertEqual(record.facts.outcome, 'normal')
        self.assertEqual(member.get_hit_points(), state['target_hp_before'] - 4)
        damage = [row for row in record.effects
                  if type(row.effect) is DamageEffect]
        self.assertEqual(len(damage), 1)
        self.assertEqual(damage[0].effect.target_id, member.id)
        self.assertEqual(damage[0].identity.source_action_id, strike.id)
        practice = [row for row in record.effects
                    if type(row.effect) is PracticeEffect]
        self.assertEqual(len(practice), 1)
        self.assertEqual((practice[0].effect.target_id,
                          practice[0].effect.skill,
                          practice[0].effect.experience),
                         (observer_two.id, 'Dagger', 10))
        self.assertEqual(practice[0].identity.source_action_id, strike.id)
        self.assertEqual(observer_two.get_skill_experience('Dagger'), 10)
        self.assertEqual(group.counts(), state['counts_before'])
        self.assertIn(strike.id, state['thrust_receipt'].action_ids)

    def test_world_request_is_independent_even_when_group_spot_fails(self):
        state = _execute(group_spot_roll=1)
        self.assertEqual(state['group_spot_record'].facts.outcome, 'failure')
        self.assertIsNone(state['evidence'])
        self.assertEqual(state['world_requirement']['trigger_action_id'], None)
        self.assertIs(state['world'].get_object_by_id(state['member'].id),
                      state['member'])
        self.assertEqual(state['group'].counts(), state['counts_before'])
        self.assertEqual(state['boundary_seven_awareness'], (False, False))

    def test_realization_publication_fault_rolls_back_then_retries(self):
        state = _execute(inject_realization_fault=True)
        self.assertEqual(state['realization_rollback'],
                         {'phase': 'adult_group_member', 'restored': True})
        self.assertEqual(state['boundary_seven_awareness'], (False, False))
        self.assertEqual(state['group'].counts(), state['counts_before'])
        self.assertIs(state['world'].get_object_by_id(state['member'].id),
                      state['member'])
        self.assertEqual(state['candidate'].member_id, state['member'].id)


if __name__ == '__main__':
    unittest.main()
