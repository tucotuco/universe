"""Runnable world-only U-REL-001V3 multigenerational reproduction proof.

All count profiles and period indices are explicitly test-only. Periods are
abstract integer ticks; they encode no calendar or biological rule.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from library import Library
from reproduction_generation import (
    ProgressiveReproductionRequest,
    TestOnlyIntervalReproductionProfile,
)
from universe import Universe


PROFILE = TestOnlyIntervalReproductionProfile(
    "u-rel-001v3-demo", "1", ((0, 1), (1, 2), (2, 3))
)


def new_world(name):
    return Universe(name, library=Library(config_dir=str(ROOT / "src/config")))


def resolve(world, parents, seed, horizon, key, profile=PROFILE):
    request = ProgressiveReproductionRequest(tuple(parents), seed, horizon, profile)
    return world.resolve_progressive_reproduction(
        request, request_key=key, expected_revision=world.reproduction_group_snapshot().revision,
    )


def main():
    world = new_world("multigenerational on demand")

    ab = resolve(world, ("A", "B"), 0, 1, "AB-through-T1")
    c1, c2 = ab.all_offspring_ids
    print(f"{ab.parent_ids} seed=0 through T1 counts={[row.count for row in ab.added_periods]} children={ab.all_offspring_ids}")

    ad = resolve(world, ("A", "D"), 0, 0, "AD-through-T0")
    c3 = ad.all_offspring_ids[0]
    print(f"{ad.parent_ids} seed=0 through T0 counts={[row.count for row in ad.added_periods]} children={ad.all_offspring_ids}")

    ce = resolve(world, (c1, "E"), 2, 1, "C1E-through-T1")
    grandchild = ce.all_offspring_ids[0]
    print(f"{ce.parent_ids} seed=2 through T1 counts={[row.count for row in ce.added_periods]} children={ce.all_offspring_ids}")

    old_ab_ids = ab.all_offspring_ids
    ab_t2 = resolve(world, ("B", "A"), 0, 2, "AB-extension-through-T2")
    print(f"{ab_t2.parent_ids} extension T2 counts={[row.count for row in ab_t2.added_periods]} "
          f"prefix preserved={ab_t2.all_offspring_ids[:len(old_ab_ids)] == old_ab_ids}")

    view = world.reproduction_group_snapshot()
    full = view.known_full_siblings(c1)
    half = view.known_half_siblings(c1)
    grandparent_paths = view.known_grandparent_paths(grandchild)
    print(f"known parents: {c1} <- {view.known_parents(c1)}; {c3} <- {view.known_parents(c3)}")
    print(f"known full siblings of {c1}: {full}")
    print(f"known half siblings of {c1}: {half}; shared-parent facts={view.known_shared_parent_relatives(c1)}")
    print(f"known grandparent paths of {grandchild}: {grandparent_paths}")

    zero_world = new_world("zero outcome")
    zero_profile = TestOnlyIntervalReproductionProfile("u-rel-001v3-zero", "1", ((0, 1),))
    zero = resolve(zero_world, ("ZERO-PARENT",), 4, 0, "zero-only", zero_profile)
    print(f"zero-only result count={zero.added_periods[0].count}; groups={len(zero_world.reproduction_group_snapshot().groups)}")

    singleton_world = new_world("single-parent outcome")
    one_profile = TestOnlyIntervalReproductionProfile("u-rel-001v3-one", "1", ((1, 1),))
    one = resolve(singleton_world, ("ASEXUAL-PARENT",), 5, 0, "single-parent", one_profile)
    print(f"singleton parent set={one.parent_ids}; children={one.all_offspring_ids}")

    if (len(view.groups) != 3 or view.known_parents(c1) != ("A", "B")
            or c2 not in full or c3 not in half
            or (c1, ("A", "B")) not in grandparent_paths
            or not ab_t2.added_periods[0].count
            or ab_t2.all_offspring_ids[:len(old_ab_ids)] != old_ab_ids
            or zero.group_id is not None or zero_world.reproduction_group_snapshot().groups
            or one.group_id is None or world.object_registry.object_instances
            or world._choice_books or set(world.event_history) != {"0"}):
        raise SystemExit("multigenerational reproduction invariant failed")
    print("native Beings/Objects=0; Encounters=0; observers/Beliefs=0; population links=0")
    print("relative queries are derived from known groups only; no completeness claim")


if __name__ == "__main__":
    main()
