#!/usr/bin/env python3
"""Run the bounded, explicitly test-only Universe reproduction demo.

The weighted count rows and integer ticks below are demonstration inputs,
not adopted biological, calendar, fertility, or historical rules.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from library import Library
from reproduction_generation import (
    StatisticalReproductionRequest,
    TestOnlyOffspringCountDistribution,
    prepare_statistical_reproduction,
)
from universe import Universe


def run_case(name: str, parents: tuple[str, ...], seed: int,
             distribution: TestOnlyOffspringCountDistribution) -> dict:
    world = Universe(name, library=Library(config_dir=str(ROOT / "src/config")))
    request = StatisticalReproductionRequest(
        parent_ids=parents,
        seed=seed,
        horizon_tick=8,
        eligible_origin_ticks=(1, 3, 5, 8),
        distribution=distribution,
    )
    candidate = prepare_statistical_reproduction(world, request)
    outcome = world.publish_statistical_reproduction(
        candidate,
        request_key=f"demo:{name}",
        expected_revision=candidate.base_revision,
    )
    snapshot = world.reproduction_group_snapshot()
    return {
        "case": name,
        "distribution_schema": outcome.distribution_schema,
        "seed": seed,
        "count": outcome.count,
        "group_id": outcome.group_id,
        "parent_ids": list(outcome.parent_ids),
        "offspring": [
            {"id": child, "origin_tick": tick}
            for child, tick in zip(outcome.offspring_ids, outcome.origin_ticks)
        ],
        "coverage_scope": outcome.coverage_scope,
        "parent_offspring_enumeration_complete": outcome.parent_offspring_enumeration_complete,
        "registry_revision": snapshot.revision,
        "published_group_count": len(snapshot.groups),
        "algorithm": outcome.algorithm,
    }


def main() -> None:
    distribution = TestOnlyOffspringCountDistribution(
        "v1-demo-counts", "1", ((0, 1), (2, 3))
    )
    output = [
        run_case("two-parent-positive", ("P-A", "P-B"), 5, distribution),
        run_case("asexual-zero", ("P-SINGLE",), 2, distribution),
    ]
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
