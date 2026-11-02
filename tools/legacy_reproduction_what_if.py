"""HYPOTHETICAL adapter from two hash-pinned legacy tables to a disposable Universe.

This experiment assigns one weighted count draw to one exact parent set in
one author-selected abstract episode. It does not assign historical meaning,
modify a user Universe, or adopt a species rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from explore_legacy_reproduction import (
    PARSER_VERSION, SAMPLER_VERSION, WeightedCountProfile,
    load_weighted_profile, sample_weighted_values,
)
from library import Library
from reproduction_generation import (
    StatisticalReproductionRequest, TestOnlyOffspringCountDistribution,
)
from universe import Universe


HYPOTHETICAL_INTERPRETATION = (
    "HYPOTHETICAL / NOT ADOPTED: one table draw is assigned to one exact "
    "parent set in one author-selected abstract episode"
)
PINNED_TABLES = {
    "human": (
        "legacy/src/data/offspring_human_wlist.csv",
        "9763d3587340c2b4acc475af7c23a960d49930e1c8e18878658f617876b221a7",
    ),
    "darkelf": (
        "legacy/src/data/offspring_darkelf_wlist.csv",
        "e0fabb178a4faa032f05f0243f82c057e92a428cffae63d59d7459ee38314b45",
    ),
}
WHAT_IF_DISTRIBUTION_VERSION = "v8-single-observed-draw/1"
WHAT_IF_PUBLISHER_PROFILE = "test-only-count-bound-from-historical-table/1"


class WhatIfIntegrationError(ValueError):
    """Refuse an unsupported source or inconsistent publisher result."""


@dataclass(frozen=True)
class WhatIfResult:
    species_label: str
    profile: WeightedCountProfile
    source_expected_sha256: str
    seed: int
    parent_ids: tuple[str, ...]
    episode_label: str
    table_draw: int
    world: Universe
    outcome: object
    replayed_outcome: object
    revision_before: int
    revision_after: int
    revision_after_replay: int


def load_pinned_profile(species_label: str) -> WeightedCountProfile:
    try:
        relative, expected_sha = PINNED_TABLES[species_label]
    except KeyError as exc:
        raise WhatIfIntegrationError("only the pinned human and darkelf tables are supported") from exc
    path = ROOT / relative
    try:
        path.resolve(strict=True).relative_to((ROOT / "legacy/src/data").resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise WhatIfIntegrationError("pinned legacy table path is unavailable or escaped its data directory") from exc
    profile = load_weighted_profile(path)
    if profile.sha256 != expected_sha:
        raise WhatIfIntegrationError(
            f"pinned source digest changed for {relative}: expected {expected_sha}, got {profile.sha256}"
        )
    if PARSER_VERSION != "legacy-weighted-count-csv/1" or SAMPLER_VERSION != "integer-cumulative-randrange/1":
        raise WhatIfIntegrationError("V7 reader/sampler version changed; review and repin before this experiment")
    return replace(profile, source_path=relative)


def profile_math(profile: WeightedCountProfile) -> tuple[Fraction, Fraction]:
    total = profile.total_weight
    if total <= 0:
        raise WhatIfIntegrationError("pinned profile has no positive weight")
    zero_weight = sum(weight for value, weight in profile.rows if value == 0)
    weighted_sum = sum(value * weight for value, weight in profile.rows)
    return Fraction(zero_weight, total), Fraction(weighted_sum, total)


def run_one_episode_what_if(
    species_label: str,
    *,
    seed: int,
    parent_ids: tuple[str, ...] = ("V8-PARENT-A", "V8-PARENT-B"),
    episode_label: str = "abstract-episode-0",
) -> WhatIfResult:
    """Draw once, then publish that fixed count through the typed test-only API.

    The existing V1 publisher requires distinct abstract origin ticks. The
    generated tick tokens are simply `0..count-1` for this what-if episode;
    they are not dates, durations, or a historical timing interpretation.
    """
    profile = load_pinned_profile(species_label)
    if type(seed) is not int or seed < 0:
        raise WhatIfIntegrationError("seed must be a nonnegative integer")
    if type(parent_ids) is not tuple or not parent_ids or any(type(p) is not str or not p.strip() for p in parent_ids):
        raise WhatIfIntegrationError("provide one explicit exact parent identity tuple")
    if len(set(parent_ids)) != len(parent_ids):
        raise WhatIfIntegrationError("parent identities must be unique")
    if type(episode_label) is not str or not episode_label.strip():
        raise WhatIfIntegrationError("episode label must be explicit text")

    count = sample_weighted_values(profile, seed=seed, draws=1)[0]
    # A degenerate test-only distribution carries the already-sampled count
    # into the native validator/publisher without another count choice/reroll.
    distribution_id = f"v8-what-if-{species_label}-{profile.sha256[:16]}-seed-{seed}"
    distribution = TestOnlyOffspringCountDistribution(
        distribution_id, WHAT_IF_DISTRIBUTION_VERSION, ((count, 1),)
    )
    abstract_origin_ticks = tuple(range(count))
    horizon_tick = max(0, count - 1)
    request = StatisticalReproductionRequest(
        parent_ids, seed, horizon_tick, abstract_origin_ticks, distribution,
    )
    world = Universe(
        f"V8 disposable what-if: {species_label} seed {seed}",
        library=Library(config_dir=str(ROOT / "src/config")),
    )
    before = world.reproduction_group_snapshot()
    request_key = f"v8:{species_label}:{profile.sha256}:{seed}:{episode_label}"
    outcome = world.resolve_statistical_reproduction(
        request, request_key=request_key, expected_revision=before.revision,
    )
    after = world.reproduction_group_snapshot()
    replayed = world.resolve_statistical_reproduction(
        request, request_key=request_key, expected_revision=after.revision,
    )
    after_replay = world.reproduction_group_snapshot()
    if (outcome.count != count or len(outcome.offspring_ids) != count
            or (count == 0 and (outcome.group_id is not None or outcome.offspring_ids))
            or (count > 0 and (outcome.group_id is None or not outcome.offspring_ids))
            or outcome.parent_ids != tuple(sorted(parent_ids))
            or outcome.parent_offspring_enumeration_complete is not False
            or replayed != outcome or after.revision != before.revision + 1
            or after_replay.revision != after.revision):
        raise WhatIfIntegrationError("typed publisher result did not preserve the bounded what-if contract")
    return WhatIfResult(
        species_label, profile, PINNED_TABLES[species_label][1], seed,
        tuple(sorted(parent_ids)), episode_label, count, world, outcome, replayed,
        before.revision, after.revision, after_replay.revision,
    )
