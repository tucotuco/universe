"""Agent-facing attention intent keeps native target binding private."""
import json
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from action_evaluation import AwarenessEffect
from activities import SpotAction
from atomic_publication import RNGCursor, PublicationFailure
from attention_intent import AttentionIntentResult, accept_spot_attention
from encounter import Encounter
from library import Library
from spatial import CartesianPosition, Sphere
from spatial import VisualOcclusion
from statistical_group import StatisticalGroup
from universe import Universe


def _scenario(*, targets=1, known_indices=(), discovery_dc=1, seed=5302,
              with_group=True, end_time=None):
    world = Universe('Attention intent', library=Library(config_dir=str(ROOT / 'src/config')))
    actor_id = world.make_being('Human', 'Observer')
    actor = world.get_object_by_id(actor_id)
    actor.set_position(CartesianPosition(0, 0, 0))
    actor.set_geometry(Sphere(.5))
    target_ids = []
    for index in range(targets):
        target_id = world.make_being('Human', f'Target {index}')
        target = world.get_object_by_id(target_id)
        target.set_position(CartesianPosition(100 + index, 0, 0))
        target.set_geometry(Sphere(.5))
        target.current.discovery_dc = discovery_dc
        target_ids.append(target_id)
    known = {target_ids[index] for index in known_indices}
    awareness = {actor_id: known} if known else None
    encounter = Encounter(world, 15, 0, end_time=end_time, initiated=True,
                          awareness=awareness,
                          id='attention-intent-encounter')
    world.add_event(encounter)
    encounter.add_being(actor_id)
    for target_id in target_ids:
        encounter.add_being(target_id)
    group = None
    if with_group:
        config = json.loads((ROOT / 'examples/nomadic_group.json').read_text())
        config['group_id'] = 'attention-unresolved-group'
        group = StatisticalGroup('Unresolved aggregate', config['group_id'], config,
                                 config['seed'])
        group.set_geometry(Sphere(.5))
        group.set_visual_occlusion(VisualOcclusion(0.0))
        world.add_object(group)
        encounter.add_object(group.id)
    cursor = RNGCursor(random.Random(seed).getstate())
    encounter.enable_transactional_progression(quiescent=True, rng_owner=cursor)
    return world, encounter, actor, tuple(target_ids), group, cursor


def _accepted_spot(encounter):
    records = tuple(encounter._choice_book._choices.values())
    members = tuple(member.action for record in records for member in record.members)
    return next(action for action in members if type(action) is SpotAction)


class TestAttentionIntent(unittest.TestCase):
    def test_unique_unfamiliar_being_is_privately_bound_to_native_six_second_spot(self):
        world, encounter, actor, targets, group, cursor = _scenario()
        target_id = targets[0]
        initial_time, initial_rng = encounter.time, cursor.state
        initial_events = set(world.event_history)

        result = accept_spot_attention(encounter, actor.id)

        self.assertEqual(result, AttentionIntentResult(True, 'accepted'))
        self.assertEqual(set(vars(result)), {'accepted', 'status'})
        self.assertNotIn(target_id, repr(result))
        self.assertEqual(encounter.time, initial_time)
        self.assertEqual(cursor.state, initial_rng)
        self.assertEqual(set(world.event_history), initial_events)
        self.assertEqual(encounter.aware_beings(actor.id), [])
        spot = _accepted_spot(encounter)
        self.assertEqual((spot.actor_id, spot.target_id), (actor.id, target_id))
        self.assertEqual((spot.start_time, spot.end_time), (0, 6))
        self.assertNotEqual(spot.target_id, actor.id)
        self.assertGreater(group.counts()['adults'], 1)
        self.assertNotIn(group.id, encounter.being_list)

        encounter.step(6)
        receipt = encounter._atomic_interval_history[-1]
        inspection = encounter.inspect_committed()
        record = inspection.action(spot.id)
        self.assertEqual(record.resolved_boundary, 6)
        self.assertEqual(record.facts.outcome, 'success')
        self.assertEqual(record.facts.target_ids, (target_id,))
        self.assertEqual(len([row for row in record.effects
                              if type(row.effect) is AwarenessEffect]), 1)
        self.assertEqual(encounter.aware_beings(actor.id), [target_id])
        self.assertEqual(encounter.aware_beings(target_id), [])
        self.assertIn(spot.id, receipt.action_ids)
        self.assertNotEqual(cursor.state, initial_rng)

    def test_zero_and_multiple_candidates_refuse_without_ids_time_actions_or_rng(self):
        for count in (0, 2):
            with self.subTest(candidate_count=count):
                world, encounter, actor, _, _, cursor = _scenario(
                    targets=count, with_group=False)
                before = (encounter.time, cursor.state, set(world.event_history),
                          tuple(encounter.pending_action_list),
                          tuple(encounter._choice_book._choices))
                result = accept_spot_attention(encounter, actor.id)
                after = (encounter.time, cursor.state, set(world.event_history),
                         tuple(encounter.pending_action_list),
                         tuple(encounter._choice_book._choices))
                self.assertEqual(result, AttentionIntentResult(False, 'not_accepted'))
                self.assertNotIn('target_id', vars(result))
                self.assertNotIn('action_id', vars(result))
                self.assertEqual(before, after)

    def test_known_beings_are_excluded_and_far_target_has_no_new_range_cap(self):
        world, encounter, actor, targets, _, _ = _scenario(
            targets=2, known_indices=(0,), with_group=False)
        result = accept_spot_attention(encounter, actor.id)
        self.assertTrue(result.accepted)
        self.assertEqual(_accepted_spot(encounter).target_id, targets[1])
        self.assertGreater(encounter.distance_between_entities(actor.id, targets[1]), 100)

    def test_all_known_or_invalid_actor_is_refused(self):
        _, encounter, actor, targets, _, _ = _scenario(
            targets=1, known_indices=(0,), with_group=False)
        self.assertFalse(accept_spot_attention(encounter, actor.id).accepted)
        self.assertFalse(accept_spot_attention(encounter, 'not-a-participant').accepted)

    def test_unschedulable_intent_does_not_leave_target_bearing_draft(self):
        world, encounter, actor, _, _, cursor = _scenario(
            targets=1, end_time=3, with_group=False)
        before = (encounter.time, cursor.state, set(world.event_history))
        result = accept_spot_attention(encounter, actor.id)
        self.assertEqual(result, AttentionIntentResult(False, 'not_accepted'))
        self.assertEqual(before, (encounter.time, cursor.state, set(world.event_history)))
        self.assertFalse(encounter._choice_book._drafts)
        self.assertFalse(encounter._choice_book._choices)

    def test_bound_target_does_not_retarget_when_it_moves_during_six_seconds(self):
        _, encounter, actor, targets, _, _ = _scenario(
            targets=1, discovery_dc=21, with_group=False)
        result = accept_spot_attention(encounter, actor.id)
        self.assertTrue(result.accepted)
        spot = _accepted_spot(encounter)
        bound_id = spot.target_id
        for _ in range(6):
            encounter.step(1, velocities={bound_id: (1, 0, 0)})
        record = encounter.inspect_committed().action(spot.id)
        self.assertEqual(spot.target_id, bound_id)
        self.assertEqual(record.declaration.target_id, bound_id)
        self.assertEqual(record.facts.outcome, 'failure')
        self.assertEqual(encounter.aware_beings(actor.id), [])
        self.assertEqual(record.facts.target_ids, (bound_id,))

    def test_spot_publication_failure_rolls_back_awareness_and_rng_then_retries(self):
        _, encounter, actor, targets, _, cursor = _scenario(
            targets=1, discovery_dc=1, with_group=False)
        self.assertTrue(accept_spot_attention(encounter, actor.id).accepted)
        spot = _accepted_spot(encounter)
        for _ in range(5):
            encounter.step(1)
        before = (encounter.time, cursor.state, tuple(encounter.aware_beings(actor.id)),
                  tuple(encounter.pending_action_list),
                  tuple(id(row) for row in encounter._atomic_interval_history))
        import atomic_publication
        publisher = atomic_publication.publish_interval_candidate

        def fail_after_observers(owner, candidate, **kwargs):
            return publisher(owner, candidate, _fail_after='observers', **kwargs)

        with patch.object(atomic_publication, 'publish_interval_candidate',
                          fail_after_observers):
            with self.assertRaises(PublicationFailure) as caught:
                encounter.step(1)
        after = (encounter.time, cursor.state, tuple(encounter.aware_beings(actor.id)),
                 tuple(encounter.pending_action_list),
                 tuple(id(row) for row in encounter._atomic_interval_history))
        self.assertEqual(before, after)
        encounter.recover_transactional_progression(caught.exception.recovery_token)
        encounter.step(1)
        self.assertIn(targets[0], encounter.aware_beings(actor.id))
        self.assertEqual(encounter.inspect_committed().action(spot.id).facts.outcome,
                         'success')


if __name__ == '__main__':
    unittest.main()
