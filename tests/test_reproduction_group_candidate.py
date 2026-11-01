"""Focused tests for pure, nonpublishing ReproductionGroup candidates."""
from dataclasses import FrozenInstanceError
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reproduction_group import (
    PreparedReproductionGroupCandidate,
    ReproductionGroupProposal,
    ReproductionGroupValidationError,
    prepare_reproduction_group,
)


def proposal(group="RG-PQ", parents=("P", "Q"), offspring=("C1",), source="author:rg0"):
    return ReproductionGroupProposal(group, parents, offspring, source)


class ReproductionGroupCandidateTests(unittest.TestCase):
    def test_nonempty_parent_set_and_one_offspring_prepare_immutable_candidate(self):
        candidate = prepare_reproduction_group(proposal())
        self.assertIs(type(candidate), PreparedReproductionGroupCandidate)
        self.assertEqual(candidate.group_id, "RG-PQ")
        self.assertEqual(candidate.parent_ids, ("P", "Q"))
        self.assertEqual(candidate.offspring_ids, ("C1",))
        self.assertFalse(candidate.offspring_enumeration_complete)
        with self.assertRaises(TypeError):
            PreparedReproductionGroupCandidate(
                "RG", ("P",), ("C1",), "author", offspring_enumeration_complete=True
            )
        with self.assertRaises(FrozenInstanceError):
            candidate.group_id = "other"
        self.assertFalse(hasattr(candidate, "being"))
        self.assertFalse(hasattr(candidate, "encounter"))

    def test_parent_order_canonicalizes_and_different_set_does_not(self):
        pq = prepare_reproduction_group(proposal(parents=("P", "Q")))
        qp = prepare_reproduction_group(proposal(group="RG-QP", parents=("Q", "P")))
        pr = prepare_reproduction_group(proposal(group="RG-PR", parents=("P", "R")))
        self.assertEqual(pq.parent_set_key, qp.parent_set_key)
        self.assertNotEqual(pq.parent_set_key, pr.parent_set_key)

    def test_single_parent_asexual_set_is_valid_without_invented_second_parent(self):
        candidate = prepare_reproduction_group(proposal(group="RG-P", parents=("P",), offspring=("A1",)))
        self.assertEqual(candidate.parent_ids, ("P",))
        self.assertEqual(candidate.offspring_ids, ("A1",))
        self.assertFalse(hasattr(candidate, "gender"))

    def test_multiple_children_do_not_claim_enumeration_completeness(self):
        candidate = prepare_reproduction_group(
            proposal(offspring=("C1", "C2"))
        )
        self.assertEqual(candidate.offspring_ids, ("C1", "C2"))
        self.assertIs(candidate.offspring_enumeration_complete, False)
        self.assertFalse(hasattr(candidate, "complete_through"))

    def test_empty_parent_or_offspring_set_refuses_without_placeholder(self):
        empty_parent_proposal = proposal(parents=())
        empty_offspring_proposal = proposal(offspring=())
        with self.assertRaisesRegex(ReproductionGroupValidationError, "at least one exact parent"):
            prepare_reproduction_group(empty_parent_proposal)
        with self.assertRaisesRegex(ReproductionGroupValidationError, "at least one offspring"):
            prepare_reproduction_group(empty_offspring_proposal)
        self.assertEqual(empty_parent_proposal.parent_ids, ())
        self.assertEqual(empty_offspring_proposal.offspring_ids, ())

    def test_same_parent_identity_can_be_reused_across_proposals(self):
        first = prepare_reproduction_group(proposal(group="RG-PQ", parents=("P", "Q")))
        second = prepare_reproduction_group(proposal(group="RG-PR", parents=("P", "R"), offspring=("C2",)))
        self.assertIn("P", first.parent_ids)
        self.assertIn("P", second.parent_ids)

    def test_repeated_parent_and_duplicate_offspring_identities_refuse(self):
        with self.assertRaisesRegex(ReproductionGroupValidationError, "repeated parent identity"):
            prepare_reproduction_group(proposal(parents=("P", "P")))
        with self.assertRaisesRegex(ReproductionGroupValidationError, "duplicate offspring identity"):
            prepare_reproduction_group(proposal(offspring=("C1", "C1")))

    def test_invalid_candidates_cannot_bypass_preparation_invariants(self):
        with self.assertRaisesRegex(ReproductionGroupValidationError, "canonical"):
            PreparedReproductionGroupCandidate("RG", ("Q", "P"), ("C1",), "author")
        parents = ["P"]
        offspring = ["C1"]
        candidate = PreparedReproductionGroupCandidate("RG", parents, offspring, "author")
        parents.append("MUTATED")
        offspring.clear()
        self.assertEqual(candidate.parent_ids, ("P",))
        self.assertEqual(candidate.offspring_ids, ("C1",))

    def test_proposal_freezes_input_lists_and_preparation_is_deterministic_pure(self):
        parents = ["Q", "P"]
        children = ["C1", "C2"]
        authored = ReproductionGroupProposal("RG-PQ", parents, children, "author:rg0")
        parents.append("MUTATED")
        children.clear()
        before_random = random.getstate()
        first = prepare_reproduction_group(authored)
        second = prepare_reproduction_group(authored)
        self.assertEqual(first, second)
        self.assertEqual(authored.parent_ids, ("Q", "P"))
        self.assertEqual(authored.offspring_ids, ("C1", "C2"))
        self.assertEqual(random.getstate(), before_random)
        with self.assertRaises(FrozenInstanceError):
            authored.parent_ids = ("R",)

    def test_native_objects_and_invalid_data_containers_are_rejected(self):
        class PersonLike:
            id = "P"

        with self.assertRaisesRegex(ReproductionGroupValidationError, "identifier string"):
            ReproductionGroupProposal("RG", (PersonLike(),), ("C1",), "author")
        with self.assertRaisesRegex(ReproductionGroupValidationError, "tuple or list"):
            ReproductionGroupProposal("RG", {"P", "Q"}, ("C1",), "author")


if __name__ == "__main__":
    unittest.main()
