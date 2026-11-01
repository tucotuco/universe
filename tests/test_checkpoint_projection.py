"""Pure projection tests for one committed native Run boundary."""
import base64
import json
from dataclasses import FrozenInstanceError
from pathlib import Path
import random
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from checkpoint_projection import ProjectionRejected, project_quarantined_spot_boundary
from checkpoint_reconstruction import ReconstructionRejected, reconstruct_initial_run_spot
from checkpoint_wire import (DecodedRunSpotWire, decode_run_spot_wire,
    encode_run_spot_envelope)


def _build_wire(kind='run', *, simultaneous=False, future=False):
    """Build source authority only in a child; return bytes and native summary."""
    import random
    from activities import RunAction, SpotAction
    from atomic_publication import RNGCursor
    from checkpoint_envelope import assemble_native_run_spot_envelope
    from test_checkpoint_reconstruction import build_source

    world, encounter, cursor, _, _ = build_source(future=future)
    actor, observed = (world.get_object_by_id(i) for i in encounter.being_list)
    # The previous C6 fixture credited fictional Spot XP. Keep the native
    # definition available, but begin this Run scenario with no Spot practice.
    actor.skill_experience.pop('spot', None)
    actor.current.skills.skills.pop('spot', None)
    if kind == 'run':
        action = RunAction(world, actor.id, 0, 1, .5, experience=4)
        encounter.schedule_choice((action,))
        encounter.step(1, velocities={actor.id: (1, 0, 0)})
    elif kind == 'spot':
        # A deliberate Spot cannot commit at boundary 1 under revision 60.
        action = SpotAction(world, actor.id, observed.id, 0.0, duration=6,
                            die_roll=13)
        encounter.schedule_choice((action,))
        encounter.step(1)
    elif kind == 'two-boundaries':
        for start in (0, 1):
            encounter.schedule_choice((RunAction(world, actor.id, start, 1, .5,
                                                  experience=4),))
            encounter.step(1, velocities={actor.id: (1, 0, 0)})
    else:
        raise AssertionError(kind)
    before = (encounter.time, tuple(encounter.finished_action_list),
              tuple(actor.skill_use_history), cursor.state, random.getstate())
    envelope = assemble_native_run_spot_envelope(
        world, encounter, quiescent=True, rng_scope='exclusive_encounter')
    after = (encounter.time, tuple(encounter.finished_action_list),
             tuple(actor.skill_use_history), cursor.state, random.getstate())
    assert before == after
    summary = {}
    if kind == 'run':
        batch = actor.skill_use_history[-1]
        summary = {'experience': batch.experience, 'level_before': batch.level_before,
            'level_after': batch.level_after, 'time': batch.time,
            'action_ids': [exercise.action_id for exercise in batch.exercises]}
    return encode_run_spot_envelope(envelope), summary


def committed_run_wire(*, simultaneous=False, future=False, kind='run'):
    """Encode a genuine native Run source in a separate Python process."""
    script = r'''
import base64,json,sys
sys.path.insert(0,sys.argv[1]);sys.path.insert(0,sys.argv[2])
from test_checkpoint_projection import _build_wire
wire,summary=_build_wire(sys.argv[3],simultaneous=sys.argv[4]=='1',future=sys.argv[5]=='1')
print(json.dumps({'wire':base64.b64encode(wire).decode('ascii'),'summary':summary}))
'''
    proc = subprocess.run([sys.executable, '-c', script, str(ROOT / 'src'),
        str(ROOT / 'tests'), kind, '1' if simultaneous else '0', '1' if future else '0'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(ROOT), check=False)
    if proc.returncode:
        raise AssertionError(proc.stderr.decode('utf-8', errors='replace'))
    result = json.loads(proc.stdout)
    return base64.b64decode(result['wire']), result['summary']


# Existing restoration tests still import this helper; its source is now the
# legitimate Run boundary so their remaining Spot-specific refusal is visible.
committed_spot_wire = committed_run_wire


class TestQuarantinedSpotProjection(unittest.TestCase):
    def test_native_run_practice_projection_is_reproducible_and_detached(self):
        wire, native_batch = committed_run_wire()
        decoded = decode_run_spot_wire(wire)
        global_rng = random.getstate()
        first = project_quarantined_spot_boundary(decoded)
        second = project_quarantined_spot_boundary(decoded)
        self.assertEqual(first.to_data(), second.to_data())
        self.assertEqual(random.getstate(), global_rng)
        self.assertEqual(first.boundary, 1)
        self.assertEqual(len(first.actions), 1)
        self.assertEqual({row.start for row in first.actions}, {('integer', '0')})
        self.assertEqual({row.end for row in first.actions}, {('integer', '1')})
        self.assertEqual(first.actions[0].outcome, 'success')
        actor_id = first.actions[0].actor_id
        actor_target = next(row for row in first.targets if row.target_id == actor_id)
        self.assertEqual(actor_target.position[1][0], ('binary64', float(1.125).hex()))
        self.assertEqual(len(actor_target.practice_exercises), 1)
        self.assertEqual(len(actor_target.practice_transitions), 1)
        transition = actor_target.practice_transitions[0]
        self.assertEqual(transition.effect_ids,
                         tuple(row.effect_id for row in actor_target.practice_exercises))
        self.assertEqual({row.experience for row in actor_target.practice_exercises},
                         {('integer', '4')})
        self.assertEqual(transition.experience_before, ('integer', '0'))
        self.assertEqual(transition.experience_after, ('integer', '4'))
        self.assertEqual(len(actor_target.batch_practice), 1)
        batch = actor_target.batch_practice[0]
        self.assertEqual(batch.skill, 'run')
        self.assertEqual(batch.experience, ('integer', '4'))
        self.assertEqual(batch.outcome, 'simultaneous')
        self.assertEqual(native_batch['experience'], 4)
        self.assertEqual(native_batch['level_before'], 0)
        self.assertEqual(native_batch['level_after'], 0)
        self.assertEqual(native_batch['time'], 1)
        self.assertEqual([row.action_id for row in actor_target.practice_exercises],
                         native_batch['action_ids'])
        self.assertEqual(len(first.effects), 3)
        practice_effect = next(row for row in first.effects if row.kind == 'effect.practice/1')
        self.assertEqual(practice_effect.identity[3], first.actions[0].action_id)
        self.assertEqual(practice_effect.identity,
                         actor_target.practice_exercises[0].effect_id)
        self.assertEqual(first.rng_after, decoded.envelope_data[8][4][0][8])
        self.assertTrue(first.quarantined)
        self.assertEqual(len(first.committed_choices), 1)
        self.assertFalse(hasattr(first, 'encounter'))
        self.assertFalse(hasattr(first, 'universe'))
        with self.assertRaises(FrozenInstanceError):
            first.boundary = 2
        with self.assertRaises(TypeError):
            first.targets[0].state_data[1] = ()

    def test_run_projection_imports_target_owned_practice_once(self):
        from frozen_practice import (freeze_imported_run_practice,
            merge_imported_practice_uses, CandidatePracticeUse)
        from action_evaluation import EffectIdentity
        from experience import BatchSkillUse
        wire, _ = committed_run_wire()
        projection = project_quarantined_spot_boundary(decode_run_spot_wire(wire))
        prefix = freeze_imported_run_practice(projection)
        merged = merge_imported_practice_uses(prefix, prefix.target_id)
        self.assertEqual(len(merged), 1)
        use = merged[0]
        self.assertIs(type(use), BatchSkillUse)
        self.assertEqual((use.being_id, use.skill_name, use.experience, use.time),
                         (prefix.target_id, 'run', 4, 1))
        self.assertEqual(use.exercises[0].action_id, projection.actions[0].action_id)
        self.assertEqual(use.exercises[0].effect_identity,
            EffectIdentity(*projection.actions[0].effect_ids[0][1:]))
        later = CandidatePracticeUse(EffectIdentity(prefix.encounter_id, 2,
            'future-run-action', 'effect', 0), 'run', 2, 'future-run-action', 2, 2, 'success')
        suffix = BatchSkillUse(prefix.target_id, 'run', 2, 0, 0, 2, (later,))
        self.assertEqual([row.time for row in merge_imported_practice_uses(
            prefix, prefix.target_id, (suffix,))], [1, 2])

    def test_source_encoded_projection_succeeds_in_separate_process(self):
        wire, _ = committed_run_wire()
        expected = project_quarantined_spot_boundary(decode_run_spot_wire(wire)).to_data()
        script = r'''
import json,random,sys
sys.path.insert(0,sys.argv[1])
from checkpoint_wire import decode_run_spot_wire
from checkpoint_projection import project_quarantined_spot_boundary
before=random.getstate()
p=project_quarantined_spot_boundary(decode_run_spot_wire(sys.stdin.buffer.read()))
assert random.getstate()==before
assert 'atomic_publication' not in sys.modules
assert 'encounter' not in sys.modules
assert p.quarantined
assert not hasattr(p,'universe') and not hasattr(p,'encounter')
print(json.dumps(p.to_data(),separators=(',',':')))
'''
        proc = subprocess.run([sys.executable, '-c', script, str(ROOT / 'src')],
            input=wire, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(ROOT), check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode('utf-8', errors='replace'))
        self.assertEqual(json.loads(proc.stdout), json.loads(json.dumps(expected)))

    def test_one_boundary_reconstruction_refusal_is_unchanged(self):
        wire, _ = committed_run_wire()
        with self.assertRaisesRegex(ReconstructionRejected, 'committed boundaries are refused'):
            reconstruct_initial_run_spot(decode_run_spot_wire(wire))

    def test_rejects_unknown_version_broken_links_and_future_choices(self):
        wire, _ = committed_spot_wire(simultaneous=False)
        decoded = decode_run_spot_wire(wire)
        data = list(decoded.envelope_data)
        data[0] = 'universe.native-run-spot-checkpoint-envelope/unknown'
        with self.assertRaisesRegex(ProjectionRejected, 'invalid detached checkpoint data'):
            project_quarantined_spot_boundary(DecodedRunSpotWire(
                decoded.schema, tuple(data), decoded.wire_digest))

        data = list(decoded.envelope_data)
        chain = list(data[8]); rows = list(chain[4]); row = list(rows[0])
        actions = list(row[4]); action = list(actions[0])
        action[2] = 'missing-logical-actor'
        actions[0] = tuple(action); row[4] = tuple(actions); rows[0] = tuple(row)
        chain[4] = tuple(rows); data[8] = tuple(chain)
        with self.assertRaisesRegex(ProjectionRejected, 'invalid detached checkpoint data'):
            project_quarantined_spot_boundary(DecodedRunSpotWire(
                decoded.schema, tuple(data), decoded.wire_digest))

        future_wire, _ = committed_run_wire(future=True)
        with self.assertRaisesRegex(ProjectionRejected, 'future choices'):
            project_quarantined_spot_boundary(decode_run_spot_wire(future_wire))

    def test_rejects_nonspot_and_multiple_boundaries(self):
        run_wire, _ = committed_run_wire()
        decoded = decode_run_spot_wire(run_wire)
        data = list(decoded.envelope_data)
        chain = list(data[8]); rows = list(chain[4]); row = list(rows[0])
        actions = list(row[4]); action = list(actions[0])
        action[1] = 'native.spot-action/1'
        actions[0] = tuple(action); row[4] = tuple(actions); rows[0] = tuple(row)
        chain[4] = tuple(rows); data[8] = tuple(chain)
        spot_decoded = DecodedRunSpotWire(decoded.schema, tuple(data), decoded.wire_digest)
        with self.assertRaises(ProjectionRejected):
            project_quarantined_spot_boundary(spot_decoded)

        two_wire, _ = committed_run_wire(kind='two-boundaries')
        with self.assertRaisesRegex(ProjectionRejected, 'exactly one committed integer boundary'):
            project_quarantined_spot_boundary(decode_run_spot_wire(two_wire))


if __name__ == '__main__':
    unittest.main()
