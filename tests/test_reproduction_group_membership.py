"""Partial ReproductionGroup membership and atomic elaboration regressions."""
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from field_observation import BeliefLedger
from library import Library
from reproduction_checkpoint import (
    ReproductionCheckpointValidationError, encode_reproduction_checkpoint,
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

        # H cannot be silently merged into G when completion collides.
        h_proposal = ReproductionGroupElaborationProposal("H", ("A",), ("B",), True)
        before_refusal = final
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "already belongs"):
            w.resolve_reproduction_group_elaboration(
                h_proposal, request_key="h-colliding-completion", expected_revision=final.revision,
            )
        self.assertEqual(w.reproduction_group_snapshot(), before_refusal)

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

    def test_completed_set_collision_is_refused_without_merging_or_losing_facts(self):
        w = world()
        create(w, "G", ("A", "B"), ("X",), complete=True, key="g")
        create(w, "H", ("A",), ("Y",), complete=False, key="h")
        before = w.reproduction_group_snapshot()
        proposal = ReproductionGroupElaborationProposal("H", ("A",), ("B",), True)
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "already belongs"):
            prepare_reproduction_group_elaboration(w, proposal)
        self.assertEqual(w.reproduction_group_snapshot(), before)
        self.assertEqual(w.get_reproduction_group("H").offspring_ids, ("Y",))

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

    def test_checkpoint_v1_refuses_partial_state_and_elaboration_history(self):
        w = world()
        create(w, "G", ("A",), ("X",), complete=False, key="g")
        with self.assertRaisesRegex(ReproductionCheckpointValidationError, "incomplete parent membership"):
            encode_reproduction_checkpoint(w)
        revision = w.reproduction_group_snapshot().revision
        w.resolve_reproduction_group_elaboration(
            ReproductionGroupElaborationProposal("G", ("A",), ("B",), True),
            request_key="complete-g", expected_revision=revision,
        )
        # V1's complete-group wire cannot faithfully carry the amendment request history.
        with self.assertRaisesRegex(ReproductionCheckpointValidationError, "does not preserve parent-membership"):
            encode_reproduction_checkpoint(w)


if __name__ == "__main__":
    unittest.main()
