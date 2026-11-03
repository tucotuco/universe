"""Partial ReproductionGroup membership and atomic elaboration regressions."""
from pathlib import Path
import hashlib
import json
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from field_observation import BeliefLedger
from library import Library
from reproduction_checkpoint import (
    ReproductionCheckpointValidationError,
    decode_reproduction_checkpoint, encode_reproduction_checkpoint,
    restore_reproduction_checkpoint,
)
from reproduction_group import (
    InjectedReproductionGroupFailure, ReproductionGroupElaborationProposal,
    ReproductionGroupProposal, ReproductionGroupPublicationError,
    StaleReproductionGroupRevision, prepare_reproduction_group,
    prepare_reproduction_group_elaboration,
)
from universe import Universe


def world():
    return Universe("partial membership", library=Library(config_dir=str(ROOT / "src/config")))


def create(w, group, parents, children, *, complete, key):
    return w.publish_reproduction_group(
        prepare_reproduction_group(ReproductionGroupProposal(
            group, parents, children, f"author:{key}", parents_complete=complete,
        )), request_key=key, expected_revision=w.reproduction_group_snapshot().revision,
    )


def retag_checkpoint(envelope):
    unsigned = {key: value for key, value in envelope.items() if key != "sha256"}
    canonical = json.dumps(unsigned, sort_keys=True, ensure_ascii=True,
                           separators=(",", ":"), allow_nan=False)
    envelope["sha256"] = hashlib.sha256(canonical.encode("ascii")).hexdigest()
    return json.dumps(envelope, sort_keys=True, ensure_ascii=True, indent=2) + "\n"


class ReproductionGroupMembershipTests(unittest.TestCase):
    def test_partial_groups_with_overlapping_known_members_remain_distinct_until_completion(self):
        w = world()
        create(w, "G", ("A",), ("X", "SIB"), complete=False, key="g")
        create(w, "H", ("A",), ("Y",), complete=False, key="h")
        snapshot = w.reproduction_group_snapshot()
        self.assertEqual(snapshot.group_id_by_parent_set, ())
        self.assertEqual(snapshot.known_parents("X"), ("A",))
        self.assertIs(snapshot.parents_complete_for("X"), False)
        self.assertEqual(snapshot.known_full_siblings("X"), ("SIB",))
        # Same current subset does not mean same exact parents or same group.
        self.assertEqual(snapshot.known_shared_parent_relatives("X"), (("Y", ("A",), ("A",)),))

        before_ids = (snapshot.groups[0].group_id, snapshot.groups[0].offspring_ids)
        add_b = ReproductionGroupElaborationProposal("G", ("A",), ("B",), False)
        result = w.resolve_reproduction_group_elaboration(
            add_b, request_key="g-add-b", expected_revision=snapshot.revision,
        )
        after_add = w.reproduction_group_snapshot()
        self.assertEqual(result.parent_ids, ("A", "B"))
        self.assertIs(result.parents_complete, False)
        self.assertEqual(after_add.group_id_by_parent_set, ())
        self.assertIs(after_add.parents_complete_for("X"), False)
        self.assertEqual((after_add.groups[0].group_id, after_add.groups[0].offspring_ids), before_ids)
        self.assertEqual(after_add.known_parents("X"), ("A", "B"))

        # Completing a singleton is valid and differs from incomplete {A}.
        create(w, "A-only", ("A",), ("SINGLETON-CHILD",), complete=True, key="singleton")
        before_complete = w.reproduction_group_snapshot()
        self.assertIn((("A",), "A-only"), before_complete.group_id_by_parent_set)
        complete = ReproductionGroupElaborationProposal("G", ("B", "A"), (), True)
        result = w.resolve_reproduction_group_elaboration(
            complete, request_key="g-complete", expected_revision=before_complete.revision,
        )
        final = w.reproduction_group_snapshot()
        self.assertIs(result.parents_complete, True)
        self.assertEqual(final.known_parents("X"), ("A", "B"))
        self.assertIs(final.parents_complete_for("X"), True)
        self.assertIn((("A", "B"), "G"), final.group_id_by_parent_set)
        h = next(group for group in final.groups if group.group_id == "H")
        self.assertEqual(h.offspring_ids, ("Y",))

        # A completion collision is the merge trigger. H no longer remains an
        # independent authoritative group, but its ID and receipt still resolve.
        h_proposal = ReproductionGroupElaborationProposal("H", ("A",), ("B",), True)
        merged_receipt = w.resolve_reproduction_group_elaboration(
            h_proposal, request_key="h-merge", expected_revision=final.revision,
        )
        merged = w.reproduction_group_snapshot()
        self.assertEqual(merged_receipt.group_id, "H")  # immutable H provenance
        self.assertEqual(w.canonical_reproduction_group_id("H"), "G")
        self.assertIs(w.get_reproduction_group("H"), w.get_reproduction_group("G"))
        self.assertNotIn("H", {group.group_id for group in merged.groups})
        self.assertEqual(w.get_reproduction_group("G").offspring_ids, ("X", "SIB", "Y"))
        self.assertEqual(dict(merged.group_id_by_offspring)["Y"], "G")
        self.assertEqual(w.resolve_reproduction_group_elaboration(
            h_proposal, request_key="h-merge", expected_revision=final.revision,
        ), merged_receipt)
        self.assertEqual(w.reproduction_group_snapshot(), merged)

    def test_complete_singleton_parent_set_merges_with_incomplete_singleton(self):
        w = world()
        create(w, "complete-singleton", ("A",), ("X",), complete=True, key="g")
        create(w, "partial-singleton", ("A",), ("Y", "Z"), complete=False, key="h")
        before = w.reproduction_group_snapshot()
        receipt = w.resolve_reproduction_group_elaboration(
            ReproductionGroupElaborationProposal("partial-singleton", ("A",), (), True),
            request_key="resolve-singleton", expected_revision=before.revision,
        )
        after = w.reproduction_group_snapshot()
        self.assertEqual(receipt.group_id, "partial-singleton")
        self.assertEqual(after.group_id_by_parent_set, (( ("A",), "complete-singleton"),))
        self.assertEqual(w.get_reproduction_group("complete-singleton").offspring_ids, ("X", "Y", "Z"))
        self.assertEqual(w.canonical_reproduction_group_id("partial-singleton"), "complete-singleton")
        self.assertNotIn("partial-singleton", {row.group_id for row in after.groups})

    def test_authored_partial_merge_preserves_positive_progressive_period_history(self):
        from reproduction_generation import (
            ProgressiveReproductionRequest, TestOnlyIntervalReproductionProfile,
        )
        w = world()
        profile = TestOnlyIntervalReproductionProfile("merge-periods", "1", ((1, 1),))
        generated = w.resolve_progressive_reproduction(
            ProgressiveReproductionRequest(("A", "B"), 8, 1, profile),
            request_key="AB-through-T1", expected_revision=0,
        )
        create(w, "H", ("A",), ("Y",), complete=False, key="h")
        history_before = w._reproduction_group_registry._progressive_histories[("A", "B")]
        origin_ticks_before = dict(w._reproduction_group_registry._offspring_origin_ticks)
        before = w.reproduction_group_snapshot()
        w.resolve_reproduction_group_elaboration(
            ReproductionGroupElaborationProposal("H", ("A",), ("B",), True),
            request_key="merge-H", expected_revision=before.revision,
        )
        survivor = w.get_reproduction_group(generated.group_id)
        self.assertEqual(survivor.offspring_ids, (*generated.all_offspring_ids, "Y"))
        self.assertEqual(
            w._reproduction_group_registry._progressive_histories[("A", "B")], history_before,
        )
        self.assertEqual(
            {key: value for key, value in w._reproduction_group_registry._offspring_origin_ticks.items()
             if key != "Y"},
            origin_ticks_before,
        )
        restored = world()
        restore_reproduction_checkpoint(restored, encode_reproduction_checkpoint(w))
        self.assertEqual(restored.canonical_reproduction_group_id("H"), generated.group_id)
        self.assertEqual(restored.get_reproduction_group(generated.group_id).offspring_ids, survivor.offspring_ids)

    def test_merge_rolls_back_each_write_phase_in_place_and_retries(self):
        from reproduction_group import _ELABORATION_PHASES, _MERGE_PHASES
        for phase in _ELABORATION_PHASES + _MERGE_PHASES:
            with self.subTest(phase=phase):
                w = world()
                create(w, "G", ("A", "B"), ("X",), complete=True, key="g")
                create(w, "H", ("A",), ("Y",), complete=False, key="h")
                registry = w._reproduction_group_registry
                names = (
                    "_groups_by_id", "_group_id_aliases", "_group_id_by_parent_set",
                    "_group_id_by_offspring", "_parent_set_by_offspring",
                    "_person_id_reservations", "_group_id_reservations", "_requests",
                )
                refs = tuple(getattr(registry, name) for name in names)
                before = w.reproduction_group_snapshot()
                rng_before = random.getstate()
                proposal = ReproductionGroupElaborationProposal("H", ("A",), ("B",), True)
                with self.assertRaises(InjectedReproductionGroupFailure):
                    w.resolve_reproduction_group_elaboration(
                        proposal, request_key="merge-H", expected_revision=before.revision,
                        _fail_after=phase,
                    )
                self.assertEqual(w.reproduction_group_snapshot(), before)
                self.assertTrue(all(getattr(registry, name) is ref for name, ref in zip(names, refs)))
                self.assertEqual(random.getstate(), rng_before)
                self.assertEqual(w.canonical_reproduction_group_id("H"), "H")
                result = w.resolve_reproduction_group_elaboration(
                    proposal, request_key="merge-H", expected_revision=before.revision,
                )
                self.assertEqual(result.group_id, "H")
                self.assertEqual(w.canonical_reproduction_group_id("H"), "G")

    def test_zero_period_scope_prevents_completion_without_disturbing_history(self):
        from reproduction_generation import (
            ProgressiveReproductionRequest, TestOnlyIntervalReproductionProfile,
        )
        w = world()
        zero_profile = TestOnlyIntervalReproductionProfile("merge-zero", "1", ((0, 1),))
        w.resolve_progressive_reproduction(
            ProgressiveReproductionRequest(("A", "B"), 4, 0, zero_profile),
            request_key="zero-AB", expected_revision=0,
        )
        create(w, "H", ("A",), ("Y",), complete=False, key="h")
        before = w.reproduction_group_snapshot()
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "generation scope"):
            w.resolve_reproduction_group_elaboration(
                ReproductionGroupElaborationProposal("H", ("A",), ("B",), True),
                request_key="resolve-H", expected_revision=before.revision,
            )
        self.assertEqual(w.reproduction_group_snapshot(), before)

    def test_idempotent_replay_stale_candidates_and_request_key_conflicts(self):
        w = world()
        create(w, "G", ("A",), ("X",), complete=False, key="g")
        proposal = ReproductionGroupElaborationProposal("G", ("A",), ("B",), False)
        revision = w.reproduction_group_snapshot().revision
        candidate = prepare_reproduction_group_elaboration(w, proposal)
        first = w.elaborate_reproduction_group(
            candidate, request_key="add-b", expected_revision=revision,
        )
        snapshot = w.reproduction_group_snapshot()
        replay = w.resolve_reproduction_group_elaboration(
            proposal, request_key="add-b", expected_revision=revision,
        )
        self.assertIs(replay, first)
        self.assertEqual(w.reproduction_group_snapshot(), snapshot)
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "different normalized"):
            w.resolve_reproduction_group_elaboration(
                ReproductionGroupElaborationProposal("G", ("A",), ("C",), False),
                request_key="add-b", expected_revision=revision,
            )
        create(w, "other", ("C",), ("Y",), complete=True, key="other")
        with self.assertRaises(StaleReproductionGroupRevision):
            w.elaborate_reproduction_group(candidate, request_key="stale", expected_revision=revision)

    def test_authored_group_id_may_equal_membership_operation_marker(self):
        w = world()
        created = create(w, "elaborate-membership", ("A",), ("X",), complete=False, key="create-marker")
        encoded = encode_reproduction_checkpoint(w)
        target = world()
        restore_reproduction_checkpoint(target, encoded)
        self.assertEqual(target.get_reproduction_group("elaborate-membership").group_id,
                         "elaborate-membership")
        replay = target.publish_reproduction_group(
                prepare_reproduction_group(ReproductionGroupProposal(
                    "elaborate-membership", ("A",), ("X",), "author:create-marker",
                    parents_complete=False,
                )), request_key="create-marker", expected_revision=0,
            )
        self.assertEqual((replay.group_id, replay.parent_ids, replay.offspring_ids,
                          replay.parents_complete, replay.revision),
                         (created.group_id, created.parent_ids, created.offspring_ids,
                          created.parents_complete, created.revision))

    def test_completed_set_collision_from_parent_resolution_merges_without_losing_facts(self):
        w = world()
        create(w, "G", ("A", "B"), ("X",), complete=True, key="g")
        create(w, "H", ("A",), ("Y",), complete=False, key="h")
        before = w.reproduction_group_snapshot()
        proposal = ReproductionGroupElaborationProposal("H", ("A",), ("B",), True)
        receipt = w.resolve_reproduction_group_elaboration(
            proposal, request_key="merge-H", expected_revision=before.revision,
        )
        after = w.reproduction_group_snapshot()
        self.assertEqual(receipt.group_id, "H")
        self.assertEqual(w.canonical_reproduction_group_id("H"), "G")
        self.assertEqual(w.get_reproduction_group("G").offspring_ids, ("X", "Y"))
        self.assertNotIn("H", {row.group_id for row in after.groups})

    def test_faults_at_every_elaboration_write_group_restore_aliases_and_allow_retry(self):
        from reproduction_group import _ELABORATION_PHASES
        for phase in _ELABORATION_PHASES:
            with self.subTest(phase=phase):
                w = world()
                create(w, "G", ("A",), ("X", "SIB"), complete=False, key="g")
                registry = w._reproduction_group_registry
                names = (
                    "_groups_by_id", "_group_id_by_parent_set", "_group_id_by_offspring",
                    "_parent_set_by_offspring", "_person_id_reservations", "_group_id_reservations",
                    "_requests",
                )
                aliases = tuple(getattr(registry, name) for name in names)
                before = w.reproduction_group_snapshot()
                rng_before = random.getstate()
                ledger = BeliefLedger("observer")
                belief_before = (ledger.evidence, ledger.belief_history, ledger.inquiry_history)
                proposal = ReproductionGroupElaborationProposal("G", ("A",), ("B",), False)
                with self.assertRaises(InjectedReproductionGroupFailure):
                    w.resolve_reproduction_group_elaboration(
                        proposal, request_key="retry", expected_revision=before.revision,
                        _fail_after=phase,
                    )
                self.assertEqual(w.reproduction_group_snapshot(), before)
                self.assertEqual(tuple(getattr(registry, name) for name in names), aliases)
                self.assertTrue(all(getattr(registry, name) is alias for name, alias in zip(names, aliases)))
                self.assertEqual(random.getstate(), rng_before)
                self.assertEqual((ledger.evidence, ledger.belief_history, ledger.inquiry_history), belief_before)
                result = w.resolve_reproduction_group_elaboration(
                    proposal, request_key="retry", expected_revision=before.revision,
                )
                self.assertEqual(result.parent_ids, ("A", "B"))
                self.assertEqual(w.reproduction_group_snapshot().revision, before.revision + 1)

    def test_checkpoint_v3_round_trips_merge_aliases_and_historical_membership(self):
        w = world()
        create(w, "G", ("A", "B"), ("X",), complete=True, key="g")
        create(w, "H", ("A",), ("Y",), complete=False, key="h")
        before = w.reproduction_group_snapshot()
        merge = ReproductionGroupElaborationProposal("H", ("A",), ("B",), True)
        receipt = w.resolve_reproduction_group_elaboration(
            merge, request_key="merge-H", expected_revision=before.revision,
        )
        encoded = encode_reproduction_checkpoint(w)
        detached = decode_reproduction_checkpoint(encoded)
        self.assertEqual(detached.wire_version, 3)
        self.assertEqual(detached.group_id_aliases, (("H", "G"),))
        self.assertEqual(detached.group_id_reservations, ("G", "H"))
        target = world()
        restore_reproduction_checkpoint(target, encoded)
        self.assertEqual(target.canonical_reproduction_group_id("H"), "G")
        self.assertEqual(target.get_reproduction_group("H"), target.get_reproduction_group("G"))
        self.assertNotIn("H", {row.group_id for row in target.reproduction_group_snapshot().groups})
        self.assertEqual(target.get_reproduction_group("G").offspring_ids, ("X", "Y"))
        revision = target.reproduction_group_snapshot().revision
        replay = target.resolve_reproduction_group_elaboration(
            merge, request_key="merge-H", expected_revision=before.revision,
        )
        self.assertEqual(
            (replay.group_id, replay.parent_ids, replay.offspring_ids, replay.source_reference,
             replay.request_key, replay.revision, replay.parents_complete),
            (receipt.group_id, receipt.parent_ids, receipt.offspring_ids, receipt.source_reference,
             receipt.request_key, receipt.revision, receipt.parents_complete),
        )
        self.assertEqual(target.reproduction_group_snapshot().revision, revision)
        create_replay = target.publish_reproduction_group(
            prepare_reproduction_group(ReproductionGroupProposal(
                "H", ("A",), ("Y",), "author:h", parents_complete=False,
            )), request_key="h", expected_revision=0,
        )
        self.assertEqual(target.canonical_reproduction_group_id(create_replay.group_id), "G")
        self.assertEqual(target.reproduction_group_snapshot().revision, revision)
        final = world()
        restore_reproduction_checkpoint(final, encode_reproduction_checkpoint(target))
        self.assertEqual(final.canonical_reproduction_group_id("H"), "G")
        self.assertEqual(final.get_reproduction_group("G").offspring_ids, ("X", "Y"))

    def test_v3_alias_corruption_is_rejected_not_repaired(self):
        w = world()
        create(w, "G", ("A", "B"), ("X",), complete=True, key="g")
        create(w, "H", ("A",), ("Y",), complete=False, key="h")
        w.resolve_reproduction_group_elaboration(
            ReproductionGroupElaborationProposal("H", ("A",), ("B",), True),
            request_key="merge", expected_revision=2,
        )
        original = json.loads(encode_reproduction_checkpoint(w))
        for alias_rows, records in (
            ([], original["payload"]["groups"]),
            ([["H", "MISSING"]], original["payload"]["groups"]),
            ([["H", "G"]], original["payload"]["groups"] + [
                {**original["payload"]["groups"][0], "group_id": "H"}
            ]),
        ):
            with self.subTest(alias_rows=alias_rows, group_count=len(records)):
                forged = json.loads(json.dumps(original))
                forged["payload"]["indexes"]["group_id_aliases"] = alias_rows
                forged["payload"]["groups"] = records
                with self.assertRaises(ReproductionCheckpointValidationError):
                    decode_reproduction_checkpoint(retag_checkpoint(forged))

    def test_v2_requires_explicit_completeness_and_validates_membership_history(self):
        w = world()
        create(w, "G", ("A",), ("X",), complete=False, key="g")
        w.resolve_reproduction_group_elaboration(
            ReproductionGroupElaborationProposal("G", ("A",), ("B",), True),
            request_key="complete-g", expected_revision=1,
        )
        encoded = encode_reproduction_checkpoint(w)
        group_omission = json.loads(encoded)
        group_omission["payload"]["groups"][0].pop("parents_complete")
        with self.assertRaisesRegex(ReproductionCheckpointValidationError, "missing or unknown fields"):
            decode_reproduction_checkpoint(retag_checkpoint(group_omission))

        authored_omission = json.loads(encoded)
        authored_omission["payload"]["authored_requests"][0]["result"].pop("parents_complete")
        with self.assertRaisesRegex(ReproductionCheckpointValidationError, "missing or unknown fields"):
            decode_reproduction_checkpoint(retag_checkpoint(authored_omission))

        forged = world()
        create(forged, "G", ("A",), ("X",), complete=False, key="g")
        forged_completeness = json.loads(encode_reproduction_checkpoint(forged))
        forged_completeness["payload"]["groups"][0]["parents_complete"] = True
        with self.assertRaisesRegex(ReproductionCheckpointValidationError, "inconsistent"):
            decode_reproduction_checkpoint(retag_checkpoint(forged_completeness))

        altered_history = json.loads(encoded)
        history = next(row for row in altered_history["payload"]["authored_requests"]
                       if row["request_key"] == "complete-g")
        history["normalized_request"][3] = ["C"]  # contradicts the committed A -> A,B transition
        with self.assertRaisesRegex(ReproductionCheckpointValidationError, "inconsistent"):
            decode_reproduction_checkpoint(retag_checkpoint(altered_history))

        with self.assertRaisesRegex(ReproductionCheckpointValidationError, "digest mismatch"):
            decode_reproduction_checkpoint(encoded.replace('"parents_complete": true', '"parents_complete": false', 1))


if __name__ == "__main__":
    unittest.main()
