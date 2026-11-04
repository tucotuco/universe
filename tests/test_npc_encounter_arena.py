import hashlib
import json
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from activities import SpotAction
from arena_npc_import import ArenaBindingBook, NPCandidate, NPCandidateError
from atomic_publication import PublicationFailure, publish_interval_candidate
from encounter import Encounter
from library import Library
from spatial import CartesianPosition, Sphere
from universe import Universe
from examples.npc_encounter_arena import build_arena, format_arena


FIXTURES = ROOT / "examples" / "npc_candidates"


def make_world():
    return Universe("Arena import test", library=Library(config_dir=str(ROOT / "src" / "config")))


class NPCandidateImportTests(unittest.TestCase):
    def test_real_generator_exports_keep_exact_source_and_provenance(self):
        for filename, expected_name, expected_seed in (
                ("ari.npcgen.json", "Ari", 71401), ("bex.npcgen.json", "Bex", 71402)):
            source = (FIXTURES / filename).read_bytes()
            candidate = NPCandidate.from_json(source)
            self.assertEqual(candidate.source_bytes, source)
            self.assertEqual(candidate.content_sha256, hashlib.sha256(source).hexdigest())
            self.assertEqual(candidate.display_name, expected_name)
            self.assertEqual(candidate.generation_seed, expected_seed)
            self.assertEqual(candidate.engine_version, "2.1.0")
            self.assertRegex(candidate.rules_hash, r"^sha256:[0-9a-f]{64}$")
            detached = candidate.source_record_copy()
            detached["state"]["name"] = "Edited copy"
            self.assertEqual(candidate.source_record_copy()["state"]["name"], expected_name)

    def test_rejects_malformed_unsupported_and_inconsistent_exports(self):
        original = json.loads((FIXTURES / "ari.npcgen.json").read_text())
        cases = []
        cases.append((b"{broken", "invalid UTF-8 NPC Generator JSON"))
        bad = dict(original, schema_version=2)
        cases.append((json.dumps(bad).encode(), "unsupported npcgen-npc schema_version"))
        bad = dict(original, surprise=True)
        cases.append((json.dumps(bad).encode(), "fields differ"))
        bad = json.loads(json.dumps(original))
        bad["engine"]["rules_hash"] = "sha256:bad"
        cases.append((json.dumps(bad).encode(), "engine.rules_hash"))
        bad = json.loads(json.dumps(original))
        bad["state"]["seed"] += 1
        cases.append((json.dumps(bad).encode(), "state.seed must match"))
        with self.assertRaisesRegex(NPCandidateError, "duplicate JSON object key"):
            NPCandidate.from_json(b'{"format":"npcgen-npc","format":"npcgen-npc"}')
        for payload, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(NPCandidateError, message):
                NPCandidate.from_json(payload)

    def test_nested_extension_data_remains_opaque_and_lossless(self):
        record = json.loads((FIXTURES / "ari.npcgen.json").read_text())
        record["state"]["future_source_field"] = {"values": [1, "verbatim", None]}
        payload = json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode()
        candidate = NPCandidate.from_json(payload)
        self.assertEqual(candidate.source_bytes, payload)
        self.assertEqual(candidate.source_record_copy()["state"]["future_source_field"],
                         {"values": [1, "verbatim", None]})

    def test_bindings_are_explicit_idempotent_and_do_not_alias_by_digest(self):
        world = make_world()
        book = ArenaBindingBook(world)
        candidate = NPCandidate.from_file(FIXTURES / "ari.npcgen.json")
        first_position = CartesianPosition(2, 3, 0)
        first = book.bind(candidate, binding_key="first-person",
                          native_being_id="arena-test/being/1",
                          native_definition_name="Human", position=first_position,
                          geometry=Sphere(0.5))
        self.assertIs(book.bind(candidate, binding_key="first-person",
                                native_being_id="arena-test/being/1",
                                native_definition_name="Human", position=first_position,
                                geometry=Sphere(0.5)), first)
        duplicate_source_candidate = NPCandidate.from_json(candidate.source_bytes)
        second = book.bind(duplicate_source_candidate, binding_key="second-person",
                           native_being_id="arena-test/being/2",
                           native_definition_name="Human",
                           position=CartesianPosition(4, 3, 0), geometry=Sphere(0.5))
        self.assertEqual(first.source_sha256, second.source_sha256)
        self.assertNotEqual(first.native_being_id, second.native_being_id)
        self.assertEqual(len(world.object_registry.object_instances), 2)

    def test_binding_conflicts_and_existing_object_collisions_refuse(self):
        world = make_world()
        book = ArenaBindingBook(world)
        candidate = NPCandidate.from_file(FIXTURES / "ari.npcgen.json")
        binding = book.bind(candidate, binding_key="ari", native_being_id="arena-test/ari",
                            native_definition_name="Human", position=CartesianPosition(0, 0, 0))
        with self.assertRaisesRegex(NPCandidateError, "different source or native setup"):
            book.bind(candidate, binding_key="ari", native_being_id="arena-test/ari",
                      native_definition_name="Human", position=CartesianPosition(1, 0, 0))
        with self.assertRaisesRegex(NPCandidateError, "already bound to another candidate"):
            book.bind(candidate, binding_key="another-binding", native_being_id="arena-test/ari",
                      native_definition_name="Human", position=CartesianPosition(2, 0, 0))
        self.assertEqual(world.get_object_by_id(binding.native_being_id).id, binding.native_being_id)

        collision_world = make_world()
        collision_world.make_being("Human", "Existing")
        # Register an exact ID so this check exercises collision refusal rather
        # than relying on generated identifiers.
        from being import BeingInstance
        existing = BeingInstance(collision_world.get_being_definition("Human"), "Existing",
                                 id="arena-test/collision")
        collision_world.add_object(existing)
        with self.assertRaisesRegex(NPCandidateError, "collides with an existing"):
            ArenaBindingBook(collision_world).bind(
                candidate, binding_key="new", native_being_id="arena-test/collision",
                native_definition_name="Human", position=CartesianPosition(0, 0, 0))

    def test_only_name_maps_to_native_being_and_native_defaults_remain_active(self):
        result = build_arena()
        for binding in result["candidate_bindings"]:
            candidate = result["candidates"]["ari" if binding.display_name == "Ari" else "bex"]
            being = result["encounter"].universe.get_object_by_id(binding.native_being_id)
            source = candidate.source_record_copy()["state"]
            native_definition = result["encounter"].universe.get_being_definition("Human")
            self.assertEqual(being.name, source["name"])
            self.assertEqual(being.get_hit_points(), native_definition.hit_points)
            self.assertEqual(being.original.obj_type, "Human")
            self.assertEqual(being.possessions, [])
            self.assertEqual(being.skill_experience, {})
            self.assertEqual(being.weapons, [])
            self.assertEqual(being.get_hit_points(), 10)
            self.assertNotEqual(being.get_hit_points(), source["hps"])


class NativeArenaEncounterTests(unittest.TestCase):
    def test_two_candidates_resolve_native_spot_and_show_committed_result(self):
        first = build_arena()
        second = build_arena()
        for result in (first, second):
            self.assertEqual(result["action"].facts.outcome, "success")
            self.assertEqual(result["action"].resolved_boundary, 6)
            self.assertEqual(result["committed_boundary_count"], 6)
            self.assertEqual(result["committed_boundaries"], (1, 2, 3, 4, 5, 6))
            self.assertEqual(dict(result["action"].facts.metadata)["effective_dc"], 15)
            self.assertEqual(dict(result["action"].facts.metadata)["roll"], 20)
            ari, bex = result["candidate_bindings"]
            self.assertEqual(result["spot_awareness"][ari.native_being_id], (bex.native_being_id,))
            self.assertEqual(result["spot_awareness"][bex.native_being_id], ())
            observer = result["encounter"].universe.get_object_by_id(ari.native_being_id)
            self.assertEqual(observer.get_skill_experience("spot"), 0)
            self.assertFalse(any(type(row.effect).__name__ == "PracticeEffect"
                                 for row in result["action"].effects))
            self.assertTrue(result["rng_unchanged"])
        self.assertEqual(first["being_positions"], second["being_positions"])
        self.assertEqual(first["action"].facts, second["action"].facts)
        self.assertIn("developer inspection", format_arena(first))
        self.assertIn("source provenance", format_arena(first))

    def test_failed_native_spot_commits_without_awareness(self):
        result = build_arena(die_roll=1)
        self.assertEqual(result["action"].facts.outcome, "failure")
        for binding in result["candidate_bindings"]:
            self.assertEqual(result["spot_awareness"][binding.native_being_id], ())
        self.assertEqual(result["committed_boundary_count"], 6)

    def test_publisher_failure_rolls_back_and_retry_commits_same_action(self):
        result = build_arena(resolve=False)
        encounter = result["encounter"]
        rng = result["rng"]
        action = result["spot_action"]
        rng_before = rng.state
        objects_before = dict(encounter.universe.object_registry.object_instances)
        receipts_before = tuple(encounter.__dict__.get("_atomic_interval_history", ()))
        publisher = publish_interval_candidate

        def fail_after_observers(owner, candidate, **kwargs):
            if candidate.boundary == 6:
                return publisher(owner, candidate, _fail_after="observers", **kwargs)
            return publisher(owner, candidate, **kwargs)

        with patch("atomic_publication.publish_interval_candidate", fail_after_observers):
            with self.assertRaises(PublicationFailure) as caught:
                encounter.step(6)
        self.assertEqual(caught.exception.phase, "observers")
        self.assertFalse(caught.exception.rollback_errors)
        self.assertEqual(dict(encounter.universe.object_registry.object_instances), objects_before)
        self.assertEqual(receipts_before, ())
        self.assertEqual(len(encounter._atomic_interval_history), 5)
        self.assertEqual(tuple(r.boundary for r in encounter._atomic_interval_history), (1, 2, 3, 4, 5))
        self.assertEqual(rng.state, rng_before)
        ari, bex = result["candidate_bindings"]
        self.assertEqual(tuple(encounter.aware_beings(ari.native_being_id)), ())
        self.assertEqual(tuple(encounter.aware_beings(bex.native_being_id)), ())

        encounter.recover_transactional_progression(caught.exception.recovery_token)
        encounter.step(1)
        committed = encounter.inspect_committed(6).action(action.id)
        self.assertEqual(committed.facts.outcome, "success")
        self.assertEqual(tuple(encounter.aware_beings(ari.native_being_id)), (bex.native_being_id,))
        self.assertEqual(tuple(encounter.aware_beings(bex.native_being_id)), ())
        self.assertEqual(len(encounter._atomic_interval_history), 6)


if __name__ == "__main__":
    unittest.main()
