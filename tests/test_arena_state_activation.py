import base64
import json
import random
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from activities import RunAction
from arena_history_admission import (
    ExpectedArenaBinding, ExpectedArenaScenario,
    _host_authorize_arena_history, _prepare_arena_history_view,
)
from arena_history_prefix import capture_arena_history_prefix, decode_arena_history_prefix
from arena_state_candidate import (
    capture_arena_post_spot_state, decode_arena_post_spot_state,
)
from arena_state_admission import (
    ArenaStateAdmissionRejected,
    ExpectedArenaSource, _host_authorize_arena_state, _prepare_arena_state,
    _private_native_beings,
)
from arena_state_activation import (
    ArenaActivationRejected, IMPORTED_TRUST, NATIVE_TRUST,
    _activate_local_arena, _compose_committed_inspection,
    _host_authorize_local_activation,
)
from atomic_publication import PublicationFailure, RNGCursor
import atomic_publication as publication
from encounter import BoundaryInvariantError
from encounter_inspection import InspectionRejected
from universe import Universe
from library import Library


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from examples.npc_encounter_arena import build_arena
ARI = "arena/being/ari"
BEX = "arena/being/bex"
RUN_ID = "npc-arena/action/run-ari-boundary-7"
SCENARIO = ExpectedArenaScenario(
    "0", "npc-arena/encounter/1", "npc-arena/action/spot-ari-bex",
    ARI, BEX, "0x0.0p+0", 6,
)


def admitted_arena():
    source = build_arena(die_roll=20)
    prefix = capture_arena_history_prefix(source)
    candidate = capture_arena_post_spot_state(source, prefix)
    payload = prefix.payload()
    bindings = tuple(ExpectedArenaBinding(
        row["binding_key"], row["source_sha256"], row["display_name"],
        row["native_being_id"], row["native_definition_name"], tuple(row["position"]),
    ) for row in payload["npc_bindings"])
    history_cap = _host_authorize_arena_history(
        prefix, expected_content_sha256=prefix.content_sha256,
        expected_scenario=SCENARIO, expected_bindings=bindings,
    )
    history = _prepare_arena_history_view(prefix, history_cap)
    sources = tuple(ExpectedArenaSource(
        row.binding_key,
        (ROOT / "examples" / "npc_candidates" /
         f"{row.binding_key.split('-')[1]}.npcgen.json").read_bytes(),
    ) for row in bindings)
    state_cap = _host_authorize_arena_state(
        candidate, prefix, history, expected_content_sha256=candidate.content_sha256,
        expected_scenario=SCENARIO, expected_bindings=bindings,
        expected_sources=sources,
    )
    state = _prepare_arena_state(
        candidate, prefix, history, state_cap,
        expected_content_sha256=candidate.content_sha256,
        expected_scenario=SCENARIO, expected_bindings=bindings,
        expected_sources=sources,
    )
    return source, prefix, candidate, history, state, sources


def receipt_count_for(encounter):
    return sum(1 for reference, owner, _ in publication._COMMITTED_RECEIPTS.values()
               if reference() is not None and owner() is encounter)


def run_boundary7(world, encounter, rng):
    rng_before = rng.state
    action = RunAction(world, ARI, 6, 1, 0.5, experience=4, id=RUN_ID)
    choice = encounter.schedule_choice((action,))
    step = encounter.step(1, velocities={ARI: (1, 0, 0), BEX: (0, 0, 0)})
    inspection = encounter.inspect_committed(7)
    action_view = inspection.action(RUN_ID)
    target = inspection.target(ARI)
    practice = tuple({
        "being_id": use.being_id,
        "skill": use.skill_name,
        "experience": use.experience,
        "time": use.time,
        "causal_action_ids": tuple(row.action_id for row in use.exercises),
    } for use in target.practice_history)
    effects = tuple((row.identity.encounter_id, row.identity.boundary,
                     row.identity.source_action_id, row.identity.channel, row.identity.slot,
                     type(row.effect).__name__) for row in action_view.effects)
    return {
        "encounter_id": inspection.encounter_id,
        "boundary": inspection.boundary,
        "timeline_boundaries": tuple(row.boundary for row in inspection.timeline),
        "action_id": action_view.declaration.id,
        "actor_id": action_view.declaration.actor_id,
        "target_id": action_view.declaration.target_id,
        "choice_id": action_view.lifecycle.choice_id,
        "outcome": action_view.facts.outcome,
        "metadata": tuple(action_view.facts.metadata),
        "effect_ids": effects,
        "ari_position": tuple(world.get_object_by_id(ARI).get_position().as_tuple()),
        "bex_position": tuple(world.get_object_by_id(BEX).get_position().as_tuple()),
        "ari_hp": world.get_object_by_id(ARI).get_hit_points(),
        "bex_hp": world.get_object_by_id(BEX).get_hit_points(),
        "ari_awareness": tuple(sorted(encounter.awareness[ARI])),
        "bex_awareness": tuple(sorted(encounter.awareness[BEX])),
        "ari_practice": practice,
        "finished_actions": tuple(encounter.finished_action_list),
        "accepted_choice_id": choice.id,
        "step_end": step.end_time,
        "rng_unchanged": rng.state == rng_before,
    }


class TestArenaTrustedLocalActivation(unittest.TestCase):
    def test_b1_or_untrusted_state_alone_cannot_activate(self):
        source, prefix, candidate, history, state, _ = admitted_arena()
        source_encounter = source["encounter"]
        prefix_bytes, candidate_bytes = prefix.to_bytes(), candidate.to_bytes()
        source_rng = source["rng"].state
        receipts_before = receipt_count_for(source_encounter)
        with self.assertRaises(ArenaActivationRejected):
            _host_authorize_local_activation(history, rng_seed=90210)
        with self.assertRaises(ArenaActivationRejected):
            _host_authorize_local_activation(candidate, rng_seed=90210)
        self.assertTrue(state.quarantined)
        self.assertEqual(state.view.committed_boundary, 6)
        self.assertEqual(receipt_count_for(source_encounter), receipts_before)
        self.assertEqual(source["rng"].state, source_rng)
        self.assertEqual(prefix.to_bytes(), prefix_bytes)
        self.assertEqual(candidate.to_bytes(), candidate_bytes)
        _private_native_beings(state)

    def test_activation_cap_is_bound_opaque_single_use_and_duplicate_refuses(self):
        _, _, _, _, state, _ = admitted_arena()
        capability = _host_authorize_local_activation(state, rng_seed=90210)
        with self.assertRaises(TypeError):
            __import__("pickle").dumps(capability)
        with self.assertRaises(ArenaActivationRejected):
            _host_authorize_local_activation(state, rng_seed=90210)
        module_rng_before = random.getstate()
        fresh = _activate_local_arena(state, capability)
        self.assertEqual(random.getstate(), module_rng_before)
        self.assertEqual(fresh.encounter.time, 6)
        self.assertEqual(fresh.encounter.progression_mode, "transactional")
        self.assertEqual(fresh.encounter.__dict__.get("_atomic_interval_history", []), [])
        with self.assertRaises(ArenaActivationRejected):
            _activate_local_arena(state, capability)
        with self.assertRaises(ArenaActivationRejected):
            _host_authorize_local_activation(state, rng_seed=90210)
        with self.assertRaises(ArenaStateAdmissionRejected):
            _private_native_beings(state)
        self.assertTrue(state.quarantined)  # detached B3-era view remains historical.

    def test_mismatched_b3_result_consumes_capability_without_world_mutation(self):
        _, _, _, _, first, _ = admitted_arena()
        _, _, _, _, second, _ = admitted_arena()
        cap = _host_authorize_local_activation(first, rng_seed=90210)
        with self.assertRaises(ArenaActivationRejected):
            _activate_local_arena(second, cap)
        # A failed cross-binding has not transferred or unquarantined either graph.
        self.assertTrue(_private_native_beings(first))
        self.assertTrue(_private_native_beings(second))
        self.assertTrue(first.quarantined and second.quarantined)

    def test_native_run_publishes_boundary_7_without_importing_old_receipts(self):
        _, prefix, candidate, _, state, sources = admitted_arena()
        prefix_before, candidate_before = prefix.to_bytes(), candidate.to_bytes()
        active = _activate_local_arena(
            state, _host_authorize_local_activation(state, rng_seed=90210))
        encounter, world, rng = active.encounter, active.world, active.rng
        self.assertEqual(encounter.start_time, 6)
        self.assertEqual(encounter.time, 6)
        self.assertEqual(encounter.last_processed_boundary, 6)
        self.assertEqual(encounter.__dict__.get("_atomic_interval_history", []), [])
        self.assertEqual(receipt_count_for(encounter), 0)
        self.assertEqual(tuple(world.event_history), ("0", encounter.id))
        self.assertEqual(set(world.object_registry.object_instances), {ARI, BEX})
        with self.assertRaises(InspectionRejected):
            encounter.inspect_committed()
        rng_before = rng.state
        self.assertEqual([row[0] for row in active.source_provenance],
                         ["arena-ari", "arena-bex"])
        self.assertEqual({row[1] for row in active.source_provenance},
                         {__import__("hashlib").sha256(source.source_bytes).hexdigest()
                          for source in sources})
        result = run_boundary7(world, encounter, rng)
        self.assertEqual(encounter.time, 7)
        self.assertEqual(encounter.last_processed_boundary, 7)
        self.assertEqual(encounter.finished_action_list, [RUN_ID])
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["ari_position"], (1.0, 0.0, 0.0))
        self.assertEqual(result["bex_position"], (3.0, 0.0, 0.0))
        self.assertEqual(result["ari_awareness"], (BEX,))
        self.assertEqual(result["bex_awareness"], ())
        self.assertEqual(result["ari_practice"], ({
            "being_id": ARI, "skill": "run", "experience": 4,
            "time": 7, "causal_action_ids": (RUN_ID,),
        },))
        self.assertEqual(receipt_count_for(encounter), 1)
        self.assertEqual(len(encounter._atomic_interval_history), 1)
        self.assertEqual(encounter._atomic_interval_history[0].boundary, 7)
        self.assertEqual(rng.state, rng_before)  # Run has no random draws.
        composed = _compose_committed_inspection(active)
        self.assertEqual(tuple(row.boundary for row in composed.timeline), tuple(range(1, 8)))
        self.assertEqual(tuple(row.provenance for row in composed.timeline[:6]),
                         (IMPORTED_TRUST,) * 6)
        self.assertEqual(composed.timeline[6].provenance, NATIVE_TRUST)
        self.assertEqual(tuple(row.action_id for row in composed.actions),
                         ("npc-arena/action/spot-ari-bex", RUN_ID))
        self.assertEqual(prefix.to_bytes(), prefix_before)
        self.assertEqual(candidate.to_bytes(), candidate_before)
        self.assertEqual(tuple(encounter._atomic_interval_history[0].action_ids), (RUN_ID,))
        # Native inspection is deliberately not extended with imported claims.
        self.assertEqual(tuple(row.boundary for row in encounter.inspect_committed().timeline), (7,))
        self.assertEqual({row.source_bytes for row in active.imported_history.npc_bindings},
                         {source.source_bytes for source in sources})

    def test_native_fault_rolls_back_rng_movement_and_receipts_then_retries(self):
        _, prefix, candidate, _, state, _ = admitted_arena()
        prefix_before, candidate_before = prefix.to_bytes(), candidate.to_bytes()
        active = _activate_local_arena(
            state, _host_authorize_local_activation(state, rng_seed=90210))
        encounter, world, rng = active.encounter, active.world, active.rng
        action = RunAction(world, ARI, 6, 1, 0.5, experience=4, id=RUN_ID)
        encounter.schedule_choice((action,))
        original = publication.publish_interval_candidate

        def injected(enc, interval, **kwargs):
            return original(enc, interval, _fail_after="targets", **kwargs)

        before_rng = rng.state
        before_positions = tuple(world.get_object_by_id(identity).get_position().as_tuple()
                                 for identity in (ARI, BEX))
        with patch.object(publication, "publish_interval_candidate", injected):
            with self.assertRaises(PublicationFailure) as caught:
                encounter.step(1, velocities={ARI: (1, 0, 0), BEX: (0, 0, 0)})
        self.assertEqual(encounter.time, 6)
        self.assertEqual(encounter.last_processed_boundary, 6)
        self.assertEqual(tuple(world.get_object_by_id(identity).get_position().as_tuple()
                               for identity in (ARI, BEX)), before_positions)
        self.assertEqual(rng.state, before_rng)
        self.assertEqual(encounter.__dict__.get("_atomic_interval_history", []), [])
        self.assertEqual(receipt_count_for(encounter), 0)
        encounter.recover_transactional_progression(caught.exception.recovery_token)
        encounter.step(1, velocities={ARI: (1, 0, 0), BEX: (0, 0, 0)})
        inspected = encounter.inspect_committed(7)
        self.assertEqual(inspected.action(RUN_ID).facts.outcome, "success")
        self.assertEqual(world.get_object_by_id(ARI).get_position().as_tuple(), (1.0, 0.0, 0.0))
        self.assertEqual(receipt_count_for(encounter), 1)
        self.assertEqual(prefix.to_bytes(), prefix_before)
        self.assertEqual(candidate.to_bytes(), candidate_before)
        self.assertEqual(tuple(active.imported_history.boundaries), tuple(range(1, 7)))

    def test_ordinary_advanced_time_constructor_refusal_is_unchanged(self):
        world = Universe("constructor refusal", library=Library(
            config_dir=str(ROOT / "src" / "config")))
        with self.assertRaises(BoundaryInvariantError):
            from encounter import Encounter
            Encounter(world, difficulty_class=15, start_time=0, time=6, id="bad-restore")
        self.assertEqual(tuple(world.event_history), ("0",))
        self.assertEqual(world._choice_books, [])
