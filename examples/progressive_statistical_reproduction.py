"""Run the U-REL-001V2 progressive, test-only reproduction example.

The profile and integer periods below are reproducibility fixtures only. They
are not species, calendar, age, fertility, or gestation rules.
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
    "u-rel-001v2-demo", "1", ((0, 1), (1, 2), (2, 3))
)


def world(name):
    return Universe(name, library=Library(config_dir=str(ROOT / "src/config")))


def resolve(target, seed, horizon, key):
    request = ProgressiveReproductionRequest(("PARENT-A", "PARENT-B"), seed, horizon, PROFILE)
    return target.resolve_progressive_reproduction(
        request, request_key=key,
        expected_revision=target.reproduction_group_snapshot().revision,
    )


def describe(result):
    rows = tuple((row.period, row.count, row.offspring_ids) for row in result.added_periods)
    return (f"periods={rows}; parents={result.parent_ids}; group={result.group_id}; "
            f"all_offspring={result.all_offspring_ids}; global_history_complete="
            f"{result.parent_global_history_complete}")


def main():
    split = world("progressive split")
    t1 = resolve(split, seed=0, horizon=1, key="split-T1")
    t1_ids = t1.all_offspring_ids
    print("T1:", describe(t1))

    t2 = resolve(split, seed=0, horizon=2, key="split-T2")
    print("T2 extension:", describe(t2))
    print("T1 offspring preserved:", t2.all_offspring_ids[:len(t1_ids)] == t1_ids)

    direct_world = world("progressive direct T2")
    direct = resolve(direct_world, seed=0, horizon=2, key="direct-T2")
    equivalent = (t2.scope_digest == direct.scope_digest
                  and t2.group_id == direct.group_id
                  and t2.all_offspring_ids == direct.all_offspring_ids
                  and split.reproduction_group_snapshot().progressive_histories[0].periods
                  == direct_world.reproduction_group_snapshot().progressive_histories[0].periods)
    print("Direct T2:", describe(direct))
    print("Split equals direct through T2:", equivalent)

    zero_then_positive = world("zero then positive")
    zero_req = ProgressiveReproductionRequest(("PARENT-SOLO",), 12, 0, PROFILE)
    zero = zero_then_positive.resolve_progressive_reproduction(
        zero_req, request_key="zero-T0", expected_revision=0,
    )
    print("T0 zero-only:", describe(zero), "groups=", len(zero_then_positive.reproduction_group_snapshot().groups))
    positive_req = ProgressiveReproductionRequest(("PARENT-SOLO",), 12, 1, PROFILE)
    positive = zero_then_positive.resolve_progressive_reproduction(
        positive_req, request_key="positive-T1", expected_revision=1,
    )
    print("T1 extension after zero:", describe(positive))
    print("Group created after first positive period:", positive.group_id is not None)

    if not equivalent or not t1_ids or zero.group_id is not None or positive.group_id is None:
        raise SystemExit("progressive reproduction example invariant failed")


if __name__ == "__main__":
    main()
