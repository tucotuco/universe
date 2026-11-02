"""Read-only explorer for historical weighted offspring-count CSVs.

This tool treats each row as a weighted candidate value. It is deliberately
separate from Universe reproduction generation and never publishes world
state. It reads legacy files as bytes/data; it does not import legacy code.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import hashlib
import io
from pathlib import Path
import random
import re
from collections import Counter


PARSER_VERSION = "legacy-weighted-count-csv/1"
SAMPLER_VERSION = "integer-cumulative-randrange/1"
INTERPRETATION = "UNRESOLVED / EXPERIMENTAL"
_INTEGER = re.compile(r"^[+-]?[0-9]+$")


class ProfileValidationError(ValueError):
    """The source is not a supported, unambiguous weighted-count CSV."""


@dataclass(frozen=True)
class WeightedCountProfile:
    source_path: str
    sha256: str
    rows: tuple[tuple[int, int], ...]  # (weighted candidate value, relative weight)

    @property
    def total_weight(self) -> int:
        return sum(weight for _value, weight in self.rows)

    def normalized_rows(self) -> tuple[tuple[int, int, float], ...]:
        total = self.total_weight
        if total <= 0:
            raise ProfileValidationError("profile total weight must be positive")
        return tuple((value, weight, weight / total) for value, weight in self.rows)


def _validate_profile(profile: WeightedCountProfile) -> None:
    if type(profile) is not WeightedCountProfile:
        raise TypeError("profile must be a WeightedCountProfile")
    if type(profile.source_path) is not str or not profile.source_path:
        raise ProfileValidationError("profile source path must be nonempty text")
    if (type(profile.sha256) is not str or len(profile.sha256) != 64
            or any(char not in "0123456789abcdef" for char in profile.sha256)):
        raise ProfileValidationError("profile SHA-256 must be lowercase hexadecimal")
    if type(profile.rows) is not tuple or not profile.rows:
        raise ProfileValidationError("profile rows must be a nonempty immutable tuple")
    values = set()
    for index, row in enumerate(profile.rows):
        if type(row) is not tuple or len(row) != 2:
            raise ProfileValidationError(f"profile row {index} must be a (value, weight) pair")
        value, weight = row
        if type(value) is not int or value < 0:
            raise ProfileValidationError(f"profile row {index} value must be a nonnegative integer")
        if type(weight) is not int or weight < 0:
            raise ProfileValidationError(f"profile row {index} weight must be a nonnegative integer")
        if value in values:
            raise ProfileValidationError(f"profile contains duplicate candidate value {value}")
        values.add(value)
    if sum(weight for _value, weight in profile.rows) <= 0:
        raise ProfileValidationError("profile total weight must be positive")


def load_weighted_profile(source: str | Path) -> WeightedCountProfile:
    """Validate one exact UTF-8 ``weight,value`` table without rewriting it."""
    path = Path(source)
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise ProfileValidationError(f"cannot read source {path}: {exc}") from exc
    try:
        text = content.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ProfileValidationError(f"source is not strict UTF-8: {path}") from exc
    try:
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        header = next(reader)
    except (StopIteration, csv.Error) as exc:
        raise ProfileValidationError("source must have a CSV header and data rows") from exc
    if header != ["weight", "value"]:
        raise ProfileValidationError("expected exact CSV header: weight,value")
    rows: list[tuple[int, int]] = []
    seen_values: set[int] = set()
    try:
        for line_number, fields in enumerate(reader, start=2):
            if len(fields) != 2:
                raise ProfileValidationError(f"row {line_number} must have exactly two columns")
            weight_text, value_text = (field.strip() for field in fields)
            if not _INTEGER.fullmatch(weight_text):
                raise ProfileValidationError(f"row {line_number} weight is not an integer")
            if not _INTEGER.fullmatch(value_text):
                raise ProfileValidationError(f"row {line_number} value is not an integer")
            weight, value = int(weight_text), int(value_text)
            if weight < 0:
                raise ProfileValidationError(f"row {line_number} weight must be nonnegative")
            if value < 0:
                raise ProfileValidationError(f"row {line_number} candidate count must be nonnegative")
            if value in seen_values:
                raise ProfileValidationError(f"row {line_number} duplicates candidate value {value}")
            seen_values.add(value)
            rows.append((value, weight))
    except csv.Error as exc:
        raise ProfileValidationError(f"CSV syntax error: {exc}") from exc
    if not rows:
        raise ProfileValidationError("profile must contain at least one data row")
    if sum(weight for _value, weight in rows) <= 0:
        raise ProfileValidationError("profile total weight must be positive")
    return WeightedCountProfile(
        path.as_posix(), hashlib.sha256(content).hexdigest(), tuple(rows)
    )


def sample_weighted_values(profile: WeightedCountProfile, *, seed: int, draws: int) -> tuple[int, ...]:
    """Sample using a private PRNG and integer cumulative weights."""
    _validate_profile(profile)
    if type(seed) is not int:
        raise TypeError("seed must be an integer")
    if type(draws) is not int or draws < 0:
        raise ValueError("draws must be a nonnegative integer")
    total = profile.total_weight
    if total <= 0:
        raise ProfileValidationError("profile total weight must be positive")
    cumulative: list[tuple[int, int]] = []
    ceiling = 0
    for value, weight in profile.rows:
        ceiling += weight
        cumulative.append((ceiling, value))
    rng = random.Random(seed)
    result = []
    for _ in range(draws):
        point = rng.randrange(total)
        result.append(next(value for ceiling, value in cumulative if point < ceiling))
    return tuple(result)


def _render_profile(profile: WeightedCountProfile, *, seed: int, draws: int) -> str:
    samples = sample_weighted_values(profile, seed=seed, draws=draws)
    counts = Counter(samples)
    lines = [
        f"source: {profile.source_path}",
        f"sha256: {profile.sha256}",
        f"interpretation: {INTERPRETATION} (weighted candidate offspring-count values only)",
        f"parser: {PARSER_VERSION}; sampler: {SAMPLER_VERSION}",
        f"explicit seed: {seed}; draws: {draws}; total relative weight: {profile.total_weight}",
        f"distinct candidate values: {[value for value, _weight in profile.rows]}",
        f"zero candidate value present: {any(value == 0 for value, _weight in profile.rows)}",
        "weights (value:relative:normalized): " + ", ".join(
            f"{value}:{weight}:{fraction:.6f}" for value, weight, fraction in profile.normalized_rows()
        ),
        f"seeded draw sequence: {list(samples)}",
        f"sample histogram: {dict(sorted(counts.items()))}",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", nargs="+", required=True, help="one or more historical weighted CSV paths")
    parser.add_argument("--seed", type=int, required=True, help="explicit local sampling seed")
    parser.add_argument("--draws", type=int, default=20, help="draw count per source (default: 20)")
    args = parser.parse_args(argv)
    if args.draws < 1:
        parser.error("--draws must be positive for CLI output")
    try:
        profiles = [load_weighted_profile(path) for path in args.source]
    except ProfileValidationError as exc:
        parser.error(str(exc))
    for index, profile in enumerate(profiles):
        if index:
            print()
        print(_render_profile(profile, seed=args.seed, draws=args.draws))
    print("authority: read-only exploration; no Universe/Reality publication or adopted biological rule")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
