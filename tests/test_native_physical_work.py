"""Native Patch 2: exact work accounting + write-free R4 proposals."""
import json
import math
import os
import sys
import unittest
from dataclasses import fields

sys.path.insert(0, os.path.abspath('../src'))
from being import BeingDefinition
from encounter import Encounter
from encounter_fatigue_bridge import FrozenFatigueFrame, InsufficientOutput
from library import Library
from physical_work import WorkSegment, WorkTimeline
from physiology_registry import PhysiologyDefinition, PhysiologyRegistry
from universe import Universe
from spatial.state import CartesianPosition
from universe_physical_fatigue_r4 import (Profile, State, evolve, human_profile)


class NativeWorkFixture(unittest.TestCase):
    def setUp(self):
        self.world = Universe('native-work', library=Library(config_dir='../src/config'))
        self.encounter = Encounter(self.world, 30, 0)
        self.world.add_event(self.encounter)
        self.a = self.world.get_object_by_id(self.world.make_being('Human', 'A'))
        self.b = self.world.get_object_by_id(self.world.make_being('Human', 'B'))
        self.encounter.add_being(self.a.id)
        self.encounter.add_being(self.b.id)
        self.a.set_physiology_id('individual/a@1')
        self.b.set_physiology_id('human@r4')
        self.registry = PhysiologyRegistry([
            PhysiologyDefinition('human@r4', model='human-r4'),
            PhysiologyDefinition('species/human@1', parent_id='human@r4'),
            PhysiologyDefinition('population/a@1', parent_id='species/human@1',
                                 parameters={'fast_budget': 45}),
            PhysiologyDefinition('individual/a@1', parent_id='population/a@1'),
        ])
        self.encounter.set_physiology_registry(self.registry)
        self.encounter.initiated = True

    def work(self, a, b, start=0, end=1):
        return WorkTimeline(start, end,
                            {self.a.id: a, self.b.id: b},
                            participants=(self.a.id, self.b.id))

    def rest(self, start=0, end=1, mode='rest'):
        return WorkSegment(start, end, 0, mode=mode, sources=(mode,))


class TestNativeWorkContract(NativeWorkFixture):
    def test_declared_overlap_cannot_be_summed_or_doubled(self):
        motion = WorkSegment(0, 1, .3, sources=('movement',))
        swing = WorkSegment(0, 1, .3, sources=('strike',), outcome='failed')
        with self.assertRaisesRegex(ValueError, 'gap or overlapping'):
            self.work([motion, swing], [self.rest()])
        # An upstream work provider consolidates biomechanical work explicitly.
        combined = WorkSegment(0, 1, .38, sources=('movement', 'strike'), outcome='failed')
        timeline = self.work([combined], [self.rest()])
        self.assertEqual(len(timeline.segments(self.a.id)), 1)
        self.assertEqual(timeline.segments(self.a.id)[0].requested_u, .38)
        with self.assertRaisesRegex(ValueError, 'duplicate source'):
            WorkSegment(0, 1, .38, sources=('movement', 'movement'))

    def test_gaps_missing_beings_and_unrecorded_idle_rejected(self):
        with self.assertRaisesRegex(ValueError, 'cover each participating Being'):
            WorkTimeline(0, 1, {self.a.id: [self.rest()]},
                         participants=(self.a.id, self.b.id))
        with self.assertRaisesRegex(ValueError, 'gap or overlapping'):
            self.work([WorkSegment(0, .4, .4, sources=('work',)),
                       WorkSegment(.5, 1, .4, sources=('work',))], [self.rest()])
        with self.assertRaisesRegex(ValueError, 'gap or overlapping'):
            self.work([WorkSegment(.01, 1, .4, sources=('work',))], [self.rest()])
        with self.assertRaisesRegex(ValueError, 'work does not cover'):
            self.work([WorkSegment(0, .5, .4, sources=('work',))], [self.rest()])

    def test_failed_attempt_and_passive_resistance_are_recordable(self):
        failed = WorkSegment(0, .3, .72, mode='actual',
                             sources=('grab-attempt',), outcome='failed')
        resistance = WorkSegment(0, .3, .41, mode='actual',
                                 sources=('passive-resistance',))
        timeline = self.work([failed, self.rest(.3, 1)],
                             [resistance, self.rest(.3, 1)])
        self.assertEqual(timeline.to_dict()['beings'][self.a.id][0]['outcome'], 'failed')
        self.assertEqual(timeline.segments(self.b.id)[0].sources, ('passive-resistance',))

    def test_movement_plus_prepared_parry_needs_one_total(self):
        # Parry work includes its preparation rather than just its final check.
        movement = WorkSegment(0, 1, .23, sources=('movement',))
        parry = WorkSegment(.75, 1, .34, sources=('parry',))
        with self.assertRaisesRegex(ValueError, 'gap or overlapping'):
            self.work([movement, parry], [self.rest()])
        # Two valid descriptions: one consolidated interval or true time split.
        combined = self.work([WorkSegment(0, 1, .30,
                              sources=('movement', 'parry'))], [self.rest()])
        split = self.work([WorkSegment(0, .75, .23, sources=('movement',)),
                           WorkSegment(.75, 1, .30,
                                       sources=('movement', 'parry'))], [self.rest()])
        self.assertEqual(len(combined.segments(self.a.id)), 1)
        self.assertEqual(len(split.segments(self.a.id)), 2)

    def test_unresolved_physiology_fails_before_movement(self):
        self.b.set_physiology_id(None)
        self.a.set_position(CartesianPosition(0, 0, 0))
        with self.assertRaises(KeyError):
            self.encounter.step(velocities={self.a.id: (1, 0, 0)})
        self.assertEqual(self.a.get_position(), CartesianPosition(0, 0, 0))
        self.assertEqual(self.encounter.time, 0)

    def test_explicit_grapple_reference_not_general_combat_calibration(self):
        # Adopted 0.70 comes from a bounded Grapple experiment only.
        self.encounter.step()
        work = self.work([WorkSegment(0, 1, .70, wear=1.1,
                           sources=('grapple-reference',))], [self.rest()])
        proposals = self.encounter.propose_physical_fatigue(work)
        reference = evolve(State(), .70, 1, self.registry.resolve(self.a).profile,
                           wear=1.1, max_step=.25)
        self.assertEqual(proposals[self.a.id].after.q, reference.state.q)
        self.assertEqual(proposals[self.a.id].after.b, reference.state.b)

    def test_sleep_recovers_without_extra_persistent_meters(self):
        self.a.set_physical_fatigue(.3, .5)
        self.encounter.step()
        timeline = self.work([self.rest(mode='sleep')], [self.rest()])
        proposal = self.encounter.propose_physical_fatigue(timeline)[self.a.id]
        self.assertGreater(proposal.after.q, .3)
        self.assertGreater(proposal.after.b, .5)
        self.assertEqual(self.a.get_physical_fatigue().q, .3)

    def test_validate_work_syntax(self):
        bad = [(-.1, 'wear'), (math.nan, 'wear'), (1.1, 'requested_u')]
        for value, key in bad:
            params = {key: value}
            with self.assertRaises((ValueError, TypeError)):
                WorkSegment(0, 1, .3, sources=('x',), **params) if key == 'wear' else WorkSegment(0, 1, value, sources=('x',))
        with self.assertRaisesRegex(ValueError, 'zero muscular work'):
            WorkSegment(0, 1, .2, mode='sleep', sources=('sleep',))

    def test_split_intervals_preserve_work_and_rest_order(self):
        self.encounter.step()
        timeline = self.work(
            [WorkSegment(0, .5, .6, sources=('strike',)), self.rest(.5, 1)],
            [self.rest()])
        proposals = self.encounter.propose_physical_fatigue(timeline)
        profile = self.registry.resolve(self.a).profile
        reference = evolve(State(), .6, .5, profile, max_step=.25).state
        reference = evolve(reference, 0, .5, profile, max_step=.25).state
        self.assertAlmostEqual(proposals[self.a.id].after.q, reference.q, places=14)
        self.assertAlmostEqual(proposals[self.a.id].after.b, reference.b, places=14)
        averaged = evolve(State(), .3, 1, profile, max_step=.25).state
        self.assertNotAlmostEqual(proposals[self.a.id].after.q, averaged.q, places=10)
        # Read/write separation is absolute: proposals do not commit.
        self.assertEqual(self.a.get_physical_fatigue().q, 1)
        self.assertEqual(self.b.get_physical_fatigue().b, 1)

    def test_unsupported_required_work_is_atomic_and_all_out_caps(self):
        self.a.set_physical_fatigue(.0, .0)
        self.encounter.step()
        required = self.work([WorkSegment(0, 1, .99, sources=('required',))],
                             [WorkSegment(0, 1, .6, sources=('B legal',))])
        with self.assertRaisesRegex(InsufficientOutput, 'infeasible'):
            self.encounter.propose_physical_fatigue(required)
        self.assertEqual(self.b.get_physical_fatigue().q, 1.0)
        optional = self.work([WorkSegment(0, 1, 1, mode='all_out', sources=('attempt',))],
                             [self.rest()])
        proposed = self.encounter.propose_physical_fatigue(optional)
        self.assertTrue(proposed[self.a.id].capped)
        self.assertEqual(proposed[self.a.id].before.q, 0)
        self.assertEqual(self.a.get_physical_fatigue().q, 0)  # not committed

    def test_sustainable_required_uses_r4_and_failed_work_has_cost(self):
        self.encounter.step()
        failed = self.work([WorkSegment(0, 1, .6, mode='actual', outcome='failed',
                                        sources=('unsuccessful-grab',))], [self.rest()])
        proposed = self.encounter.propose_physical_fatigue(failed)
        reference = evolve(State(), .6, 1, self.registry.resolve(self.a).profile, max_step=.25)
        self.assertEqual(proposed[self.a.id].after.q, reference.state.q)
        self.assertEqual(proposed[self.a.id].after.b, reference.state.b)
        self.assertLess(proposed[self.a.id].after.q, 1)

    def test_native_frame_precedes_resolution_and_freezes_profile(self):
        self.encounter.step()
        frozen = self.encounter.last_fatigue_frame
        before = frozen.physiology(self.a.id).profile.fast_budget
        self.assertEqual(before, 45)
        self.a.set_physiology_id('human@r4')
        self.assertEqual(frozen.physiology(self.a.id).profile.fast_budget, 45)
        self.assertEqual(frozen.view(self.a.id).physiology_id, 'individual/a@1')
        proposed = self.encounter.propose_physical_fatigue(
            self.work([WorkSegment(0, 1, .8, sources=('attempt',))], [self.rest()]))
        reference = evolve(State(), .8, 1, frozen.physiology(self.a.id).profile, max_step=.25)
        self.assertEqual(proposed[self.a.id].after.q, reference.state.q)
        self.assertEqual(proposed[self.a.id].profile_versions[0],
                         frozen.physiology(self.a.id).version_hash)
        self.assertEqual(self.a.get_physical_fatigue().q, 1)

    def test_step_interval_alignment_and_serialization(self):
        self.encounter.step(.5)
        with self.assertRaisesRegex(RuntimeError, 'no Encounter fatigue snapshot'):
            self.encounter.propose_physical_fatigue(self.work([self.rest()], [self.rest()]))
        self.encounter.step(.5)
        with self.assertRaisesRegex(ValueError, 'work must end'):
            self.encounter.propose_physical_fatigue(self.work([self.rest(end=.5)], [self.rest(end=.5)], end=.5))
        good = self.work([self.rest()], [self.rest()])
        proposals = self.encounter.propose_physical_fatigue(good)
        self.assertEqual(proposals[self.a.id].after.q, 1.0)
        parsed = json.loads(self.world.to_json())
        self.assertNotIn('_physiology_registry', parsed['event_history'][self.encounter.id])
        self.assertIn('start', parsed['event_history'][self.encounter.id]['fatigue_frame_history'][0])


class TestVersionedPhysiology(NativeWorkFixture):
    def test_no_fallback_and_explicit_lineage(self):
        resolved = self.registry.resolve(self.a)
        self.assertEqual(resolved.lineage, ('human@r4', 'species/human@1',
                                             'population/a@1', 'individual/a@1'))
        self.assertEqual(resolved.profile.fast_budget, 45)
        self.assertEqual(self.registry.resolve(self.a).version_hash, resolved.version_hash)
        with self.assertRaises(KeyError):
            self.b.set_physiology_id('unknown@2')
            self.registry.resolve(self.b)

    def test_run_applies_only_to_running_physiology(self):
        self.a.current.skills.skills['run'] = 12
        a_normal = self.registry.resolve(self.a, mode='ordinary')
        a_running = self.registry.resolve(self.a, mode='running')
        self.assertEqual(a_normal.profile.fast_budget, 45)
        self.assertEqual(a_running.profile.fast_budget, 45)  # explicit override wins
        self.assertGreater(a_running.profile.slow_depletion, a_normal.profile.slow_depletion)
        self.assertNotEqual(a_running.version_hash, a_normal.version_hash)
        self.assertEqual(self.registry.resolve(self.b, mode='ordinary').profile,
                         human_profile(self.b.FIT(), running=False))

    def test_nonhuman_requires_explicit_full_profile(self):
        with self.assertRaisesRegex(ValueError, 'all R4 profile fields'):
            PhysiologyDefinition('equine@r4', model='parameterized-r4',
                                 parameters={'critical_fresh': .66})
        params = {name: getattr(Profile(), name) for name in (field.name for field in fields(Profile))}
        params['critical_fresh'] = .66
        reg = PhysiologyRegistry([PhysiologyDefinition('equine@r4', model='parameterized-r4',
                                                       parameters=params)])
        self.b.set_physiology_id('equine@r4')
        self.assertEqual(reg.resolve(self.b).profile.critical_fresh, .66)
        self.assertEqual(reg.resolve(self.b, mode='running').profile,
                         reg.resolve(self.b, mode='ordinary').profile)

    def test_redefinitions_are_not_mutable_and_invalid_chain_fails(self):
        with self.assertRaisesRegex(ValueError, 'already registered'):
            self.registry.register(PhysiologyDefinition('human@r4', model='human-r4'))
        reg = PhysiologyRegistry([
            PhysiologyDefinition('A@1', parent_id='B@1'),
            PhysiologyDefinition('B@1', parent_id='A@1')])
        self.a.set_physiology_id('A@1')
        with self.assertRaisesRegex(ValueError, 'cyclic'):
            reg.resolve(self.a)


if __name__ == '__main__':
    unittest.main()
