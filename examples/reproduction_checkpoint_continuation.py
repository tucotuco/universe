"""Save and continue a test-only reproduction registry across Python processes.

Run this file without arguments for a subprocess-driven save/restore proof, or
use ``--phase save|resume|baseline`` for an inspectable manual sequence.
No native Being, population, Encounter, calendar or Agent state is persisted.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from library import Library
from reproduction_checkpoint import (
    CHECKPOINT_VERSION, encode_reproduction_checkpoint, logical_reproduction_checkpoint_digest,
    restore_reproduction_checkpoint,
)
from reproduction_generation import (
    ProgressiveReproductionRequest, TestOnlyIntervalReproductionProfile,
)
from universe import Universe


PROFILE = TestOnlyIntervalReproductionProfile(
    "u-rel-001v4-demo", "1", ((0, 1), (1, 2), (2, 3))
)
ZERO_POSITIVE_PROFILE = TestOnlyIntervalReproductionProfile(
    "u-rel-001v4-zero-positive", "1", ((0, 1), (1, 1))
)


def new_world(name: str) -> Universe:
    return Universe(name, library=Library(config_dir=str(ROOT / "src/config")))


def resolve(world, parents, seed, period, key, profile=PROFILE):
    request = ProgressiveReproductionRequest(tuple(parents), seed, period, profile)
    return world.resolve_progressive_reproduction(
        request, request_key=key, expected_revision=world.reproduction_group_snapshot().revision,
    )


def establish_prefix(world):
    ab = resolve(world, ("A", "B"), 0, 1, "AB-through-T1")
    c1 = ab.all_offspring_ids[0]
    ad = resolve(world, ("A", "D"), 0, 0, "AD-through-T0")
    ce = resolve(world, (c1, "E"), 2, 1, "C1E-through-T1")
    zero = resolve(world, ("ZERO-PARENT",), 5, 0, "zero-parent-through-T0", ZERO_POSITIVE_PROFILE)
    if any(row.count for row in zero.added_periods) or zero.group_id is not None:
        raise AssertionError("zero-only prefix unexpectedly created offspring or a group")
    if len({ab.group_id, ad.group_id, ce.group_id}) != 3:
        raise AssertionError("connected multigenerational fixture did not publish three groups")
    return {"c1": c1, "ab_key": "AB-through-T1"}


def continue_from_prefix(world, ids):
    # The cached retry must return before any deterministic period draw is asked for.
    import reproduction_generation
    retry_request = ProgressiveReproductionRequest(("A", "B"), 0, 1, PROFILE)
    before = world.reproduction_group_snapshot().revision
    from unittest.mock import patch
    with patch.object(reproduction_generation, "_period_draw", side_effect=AssertionError("cached retry drew")):
        retry = world.resolve_progressive_reproduction(
            retry_request, request_key=ids["ab_key"], expected_revision=before,
        )
    if world.reproduction_group_snapshot().revision != before:
        raise AssertionError("idempotent retry changed the registry revision")
    if ids["c1"] not in retry.all_offspring_ids:
        raise AssertionError("idempotent retry did not return the established offspring")

    before_ab = world.reproduction_group_snapshot().groups
    ab = resolve(world, ("B", "A"), 0, 2, "AB-extension-through-T2")
    if ab.all_offspring_ids[:len(retry.all_offspring_ids)] != retry.all_offspring_ids:
        raise AssertionError("AB extension rewrote its established prefix")
    if before_ab[0].group_id not in {row.group_id for row in world.reproduction_group_snapshot().groups}:
        raise AssertionError("AB group identity was not preserved")

    zero = resolve(world, ("ZERO-PARENT",), 5, 1, "zero-parent-through-T1", ZERO_POSITIVE_PROFILE)
    if zero.group_id is None or not any(row.count for row in zero.added_periods):
        raise AssertionError("zero-to-positive extension did not realize a group")
    history = next(row for row in world.reproduction_group_snapshot().progressive_histories
                   if row.parent_ids == ("ZERO-PARENT",))
    if history.periods[0].count != 0 or history.periods[0].offspring_ids:
        raise AssertionError("zero prefix unexpectedly contained offspring")
    return {"ab": ab, "zero": zero}


def summary(world):
    view = world.reproduction_group_snapshot()
    groups = sorted(view.groups, key=lambda row: row.parent_ids)
    first_ab = next(group.offspring_ids[0] for group in groups if group.parent_ids == ("A", "B"))
    ad_child = next(group.offspring_ids[0] for group in groups if group.parent_ids == ("A", "D"))
    ce_group = next(group for group in groups if "E" in group.parent_ids)
    grandchild = ce_group.offspring_ids[0]
    return {
        "revision": view.revision,
        "groups": [
            {"group_id": row.group_id, "parents": list(row.parent_ids), "offspring": list(row.offspring_ids)}
            for row in groups
        ],
        "request_keys": list(view.request_keys) + sorted(
            key for key in _all_request_keys(world) if key not in view.request_keys
        ),
        "known_kinship": {
            "AB_child_parents": list(view.known_parents(first_ab) or ()),
            "AB_full_siblings": list(view.known_full_siblings(first_ab)),
            "AB_half_siblings": list(view.known_half_siblings(first_ab)),
            "AD_child_parents": list(view.known_parents(ad_child) or ()),
            "grandparent_paths": [[parent, list(grandparents)]
                                  for parent, grandparents in view.known_grandparent_paths(grandchild)],
        },
    }


def _all_request_keys(world):
    registry = world._reproduction_group_registry
    return set(registry._requests) | set(registry._generation_requests) | set(registry._progressive_requests)


def write_new(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(content)


def phase_save(checkpoint: Path):
    world = new_world("V4 source process")
    establish_prefix(world)
    write_new(checkpoint, encode_reproduction_checkpoint(world))
    print(f"SAVE pid={os.getpid()} revision={world.reproduction_group_snapshot().revision} "
          f"groups={len(world.reproduction_group_snapshot().groups)} "
          f"format=reproduction-v{CHECKPOINT_VERSION}")


def phase_resume(checkpoint: Path, output: Path):
    world = new_world("V4 fresh restore process")
    restore_reproduction_checkpoint(world, checkpoint.read_text(encoding="utf-8"))
    result = continue_from_prefix(world, {"c1": next(
        group.offspring_ids[0] for group in world.reproduction_group_snapshot().groups
        if group.parent_ids == ("A", "B")), "ab_key": "AB-through-T1"})
    write_new(output, encode_reproduction_checkpoint(world))
    print(f"RESUME pid={os.getpid()} revision={world.reproduction_group_snapshot().revision} "
          f"AB-added={sum(row.count for row in result['ab'].added_periods)} "
          f"zero-added={sum(row.count for row in result['zero'].added_periods)} "
          f"digest={logical_reproduction_checkpoint_digest(output.read_text(encoding='utf-8'))}")
    print("SUMMARY=" + json.dumps(summary(world), sort_keys=True, separators=(",", ":")))


def phase_baseline(output: Path):
    world = new_world("V4 uninterrupted baseline process")
    ids = establish_prefix(world)
    result = continue_from_prefix(world, ids)
    write_new(output, encode_reproduction_checkpoint(world))
    print(f"BASELINE pid={os.getpid()} revision={world.reproduction_group_snapshot().revision} "
          f"AB-added={sum(row.count for row in result['ab'].added_periods)} "
          f"zero-added={sum(row.count for row in result['zero'].added_periods)} "
          f"digest={logical_reproduction_checkpoint_digest(output.read_text(encoding='utf-8'))}")
    print("SUMMARY=" + json.dumps(summary(world), sort_keys=True, separators=(",", ":")))


def run_demo():
    with tempfile.TemporaryDirectory(prefix="u-rel-001v4-") as temp:
        root = Path(temp)
        source, resumed, baseline = root / "reproduction-v1.json", root / "resumed-v1.json", root / "baseline-v1.json"
        script = str(Path(__file__).resolve())

        def invoke(*args):
            completed = subprocess.run([sys.executable, script, *args], check=True, text=True,
                                       capture_output=True, cwd=ROOT)
            print(completed.stdout, end="")
            return completed.stdout

        save_out = invoke("--phase", "save", "--checkpoint", str(source))
        resume_out = invoke("--phase", "resume", "--checkpoint", str(source), "--output", str(resumed))
        baseline_out = invoke("--phase", "baseline", "--output", str(baseline))
        save_pid = int(next(line.split("pid=")[1].split()[0] for line in save_out.splitlines() if line.startswith("SAVE")))
        resume_pid = int(next(line.split("pid=")[1].split()[0] for line in resume_out.splitlines() if line.startswith("RESUME")))
        baseline_pid = int(next(line.split("pid=")[1].split()[0] for line in baseline_out.splitlines() if line.startswith("BASELINE")))
        if save_pid == resume_pid or resume_pid == baseline_pid:
            raise SystemExit("process boundary proof failed")
        resumed_summary = json.loads(next(line[8:] for line in resume_out.splitlines() if line.startswith("SUMMARY=")))
        baseline_summary = json.loads(next(line[8:] for line in baseline_out.splitlines() if line.startswith("SUMMARY=")))
        restored_digest = logical_reproduction_checkpoint_digest(resumed.read_text(encoding="utf-8"))
        baseline_digest = logical_reproduction_checkpoint_digest(baseline.read_text(encoding="utf-8"))
        if resumed_summary != baseline_summary or restored_digest != baseline_digest:
            raise SystemExit("fresh-process continuation differs from uninterrupted baseline")
        print(f"COMPARE distinct source/resume processes={save_pid}!={resume_pid}; "
              f"logical histories and known kinship equal=True; digest={restored_digest}")
        print("Only logical reproduction records restored; native Beings/Objects=0; Encounters=0")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("demo", "save", "resume", "baseline"), default="demo")
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.phase == "demo":
        run_demo()
    elif args.phase == "save":
        if args.checkpoint is None:
            parser.error("--phase save requires --checkpoint")
        phase_save(args.checkpoint)
    elif args.phase == "resume":
        if args.checkpoint is None or args.output is None:
            parser.error("--phase resume requires --checkpoint and --output")
        phase_resume(args.checkpoint, args.output)
    else:
        if args.output is None:
            parser.error("--phase baseline requires --output")
        phase_baseline(args.output)


if __name__ == "__main__":
    main()
