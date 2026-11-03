"""Run the world-only U-REL-001V9 reverse ancestry-generation example.

The parent cardinality is caller-authored and sibling counts are explicitly
test-only. No biological or calendar interpretation is implied.
"""
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ancestor_generation import ResolveParentsRequest, resolve_parents
from library import Library
from reproduction_generation import TestOnlyOffspringCountDistribution
from reproduction_group import ReproductionGroupProposal, prepare_reproduction_group
from universe import Universe


SIBLING_PROFILE = TestOnlyOffspringCountDistribution(
    "u-rel-001v9-additional-siblings", "1", ((0, 1), (1, 2), (2, 1))
)


def main():
    world = Universe("V9 reverse ancestor generation", library=Library(config_dir=str(ROOT / "src/config")))
    initial = prepare_reproduction_group(ReproductionGroupProposal(
        "RG-V9-PQ", ("P", "Q"), ("C",), "u-rel-001v9:existing-P-and-child",
    ))
    world.publish_reproduction_group(initial, request_key="v9:existing-descendant", expected_revision=0)
    before = world.reproduction_group_snapshot()
    assert before.known_parents("P") is None

    request = ResolveParentsRequest("P", parent_count=2, seed=0,
                                    additional_sibling_distribution=SIBLING_PROFILE)
    rng_before = random.getstate()
    result = resolve_parents(world, request, request_key="v9:resolve-P-parents",
                             expected_revision=before.revision)
    after = world.reproduction_group_snapshot()
    replay = resolve_parents(world, request, request_key="v9:resolve-P-parents")

    print("V9 test-only reverse ancestor generation; no adopted biological or calendar rules")
    print(f"test_profile={SIBLING_PROFILE.distribution_id}@{SIBLING_PROFILE.version}; seed={request.seed}; "
          f"parent_count={request.parent_count}; sampled_additional_siblings={len(result.offspring_ids) - 1}")
    print(f"P={request.person_id}; existing child=C; generated exact parents={result.parent_ids}")
    print(f"published group={result.group_id}; first offspring={result.offspring_ids[0]}; "
          f"known full siblings of P={after.known_full_siblings('P')}")
    print(f"known grandparent paths of C={after.known_grandparent_paths('C')}")
    print(f"P and C identities conserved; enumeration_complete={after.groups[1].offspring_enumeration_complete}; "
          f"idempotent_replay={replay == result}; revision={before.revision}->{after.revision}")
    print(f"native Objects={len(world.object_registry.object_instances)}; Encounters={len(world._choice_books)}; "
          f"global_rng_unchanged={random.getstate() == rng_before}")

    if (after.known_parents("P") != result.parent_ids
            or result.offspring_ids[0] != "P"
            or after.known_full_siblings("P") != result.offspring_ids[1:]
            or after.known_grandparent_paths("C") != (("P", result.parent_ids),)
            or after.known_parents("C") != ("P", "Q")
            or next(group for group in after.groups if group.group_id == result.group_id)
            .offspring_enumeration_complete is not False
            or replay != result or len(after.groups) != 2
            or world.reproduction_group_snapshot().revision != after.revision
            or world.object_registry.object_instances or world._choice_books
            or set(world.event_history) != {"0"} or random.getstate() != rng_before):
        raise SystemExit("V9 reverse ancestor-generation invariant failed")


if __name__ == "__main__":
    main()
