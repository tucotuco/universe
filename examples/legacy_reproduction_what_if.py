"""Run a pinned, isolated HYPOTHETICAL legacy-count publication experiment."""
from __future__ import annotations

import argparse
from fractions import Fraction
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from explore_legacy_reproduction import PARSER_VERSION, SAMPLER_VERSION
from legacy_reproduction_what_if import (
    HYPOTHETICAL_INTERPRETATION, profile_math,
    run_one_episode_what_if,
)


def _fraction(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator} ({float(value):.6f})"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--human-seed", type=int, default=5)
    parser.add_argument("--darkelf-seed", type=int, default=1)
    args = parser.parse_args(argv)
    if args.human_seed < 0 or args.darkelf_seed < 0:
        parser.error("seeds must be nonnegative")

    print("!!! HYPOTHETICAL / NOT ADOPTED !!!")
    print(HYPOTHETICAL_INTERPRETATION)
    print("Count weights are source data; this demo assumes one draw for one exact parent set in one abstract episode.")
    print("No lifetime/per-period rate, calendar, age, gender, survival, or Being/population inference.")
    print(f"V7 reader={PARSER_VERSION}; sampler={SAMPLER_VERSION}; V8 adapter={WHAT_IF_VERSION}")

    rng_before = random.getstate()
    for label, seed in (("human", args.human_seed), ("darkelf", args.darkelf_seed)):
        result = run_one_episode_what_if(label, seed=seed)
        p_zero, mean = profile_math(result.profile)
        outcome = result.outcome
        print(f"\nscenario={label}; source={result.profile.source_path}; sha256={result.profile.sha256}")
        print(f"p_zero={_fraction(p_zero)}; weighted_candidate_mean={_fraction(mean)} (mathematical only)")
        print(f"seed={seed}; draw_count={result.table_draw}; exact_parents={result.parent_ids}; episode={result.episode_label}")
        print(f"world=disposable isolated Universe; before_revision={result.revision_before}; after_revision={result.revision_after}")
        print(f"abstract API origin tokens={list(outcome.origin_ticks)}; tokens are not dates or durations")
        print(f"published_count={outcome.count}; group_id={outcome.group_id}; offspring_ids={list(outcome.offspring_ids)}")
        print(f"parent_set={outcome.parent_ids}; enumeration_complete={outcome.parent_offspring_enumeration_complete}")
        print(f"idempotent_replay_same_result={result.replayed_outcome == outcome}; revision_after_replay={result.revision_after_replay}")
        print(f"Encounter=0; native Objects={len(result.world.object_registry.object_instances)}; no user Universe is accepted")
    print(f"global_python_rng_unchanged={random.getstate() == rng_before}")


WHAT_IF_VERSION = "one-draw-one-parent-set-one-abstract-episode/1"


if __name__ == "__main__":
    main()
