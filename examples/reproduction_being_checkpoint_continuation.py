"""Save and continue one logical-offspring/native-Being graph across processes.

Run with no arguments for the subprocess proof, or inspect the save/resume
phases with ``--phase save|resume --checkpoint PATH``. The fixture is
test-only reproduction data plus one explicitly authored, pristine Being.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from abilities import Abilities
from being import BeingDefinition
from library import Library
from reproduction_being_bridge import materialize_reproductive_offspring
from reproduction_being_checkpoint import (
    CombinedBeingCheckpointError, combined_being_checkpoint_digest,
    decode_combined_being_checkpoint, encode_combined_being_checkpoint,
    restore_combined_being_checkpoint,
)
from reproduction_checkpoint import encode_reproduction_checkpoint
from reproduction_generation import ProgressiveReproductionRequest, TestOnlyIntervalReproductionProfile
from skill import Skills
from universe import Universe


PROFILE = TestOnlyIntervalReproductionProfile(
    "u-rel-001v6-demo", "1", ((0, 1), (1, 2), (2, 3))
)


def new_world(label):
    return Universe(label, library=Library(config_dir=str(ROOT / "src/config")))


def authored_definition():
    skills = Skills()
    skills.skills = {"authored craft": 2}
    return BeingDefinition(
        "V6 explicitly authored native Being", 1.8, 70, 10, "1d8", "Neutral", 10, 0,
        abilities=Abilities(strength=14), skills=skills, physiology_id="authored:unresolved-v1",
    )


def resolve(world, parents, through, key):
    return world.resolve_progressive_reproduction(
        ProgressiveReproductionRequest(tuple(parents), 7, through, PROFILE),
        request_key=key, expected_revision=world.reproduction_group_snapshot().revision,
    )


def establish(world):
    ab = resolve(world, ("P", "Q"), 1, "PQ-through-T1")
    child = ab.all_offspring_ids[0]
    resolve(world, ("P", "R"), 0, "PR-through-T0")
    resolve(world, (child, "S"), 1, "child-S-through-T1")
    return child


def bind(world, child):
    return materialize_reproductive_offspring(
        world, child, being_definition=authored_definition(), name="Authored offspring C",
        request_key="bind-C", expected_revision=world.reproduction_group_snapshot().revision,
    )


def _assert_v4_refusal(world):
    try:
        encode_reproduction_checkpoint(world)
    except ValueError as exc:
        if "logical reproduction IDs collide with native Objects" not in str(exc):
            raise
    else:
        raise AssertionError("reproduction-only checkpoint accepted a materialized offspring")


def phase_save(path):
    world = new_world("V6 source process")
    child = establish(world)
    being = bind(world, child)
    _assert_v4_refusal(world)
    checkpoint = encode_combined_being_checkpoint(world)
    path.write_text(checkpoint, encoding="utf-8")
    print(f"SAVE pid={__import__('os').getpid()} child={child} native={type(being).__name__}:{being.id}")
    print(f"groups={len(world.reproduction_group_snapshot().groups)} format=combined-json-v{1}")
    print("V4 reproduction-only refusal=preserved; combined checkpoint written")


def continue_prefix(world, child):
    # This completed bridge retry uses the restored Being's own native
    # definition. It must return the same instance without another allocation.
    being = world.get_object_by_id(child)
    retry = materialize_reproductive_offspring(
        world, child, being_definition=being.original, name=being.name,
        request_key="bind-C", expected_revision=world.reproduction_group_snapshot().revision,
    )
    if retry is not being:
        raise AssertionError("idempotent bridge retry replaced the restored Being")
    before = world.reproduction_group_snapshot()
    result = resolve(world, ("Q", "P"), 2, "PQ-extension-through-T2")
    after = world.reproduction_group_snapshot()
    group_before = next(row for row in before.groups if row.parent_ids == ("P", "Q"))
    group_after = next(row for row in after.groups if row.parent_ids == ("P", "Q"))
    if group_after.group_id != group_before.group_id or group_after.offspring_ids[:len(group_before.offspring_ids)] != group_before.offspring_ids:
        raise AssertionError("continuation changed established identity or parentage")
    if result.all_offspring_ids[:len(group_before.offspring_ids)] != group_before.offspring_ids:
        raise AssertionError("continuation did not preserve the committed offspring prefix")
    return being


def phase_resume(path):
    checkpoint = path.read_text(encoding="utf-8")
    candidate = decode_combined_being_checkpoint(checkpoint)
    resumed = new_world("V6 fresh restore process")
    being = restore_combined_being_checkpoint(resumed, candidate)
    child = candidate.person_id
    if resumed.get_object_by_id(child) is not being:
        raise AssertionError("ObjectRegistry did not resolve the reconstructed native instance")
    resumed_being = continue_prefix(resumed, child)

    # Independent uninterrupted control: the Being is authored through the
    # normal native bridge from the same inputs, before the same T2 request.
    baseline = new_world("V6 uninterrupted control")
    baseline_child = establish(baseline)
    baseline_being = bind(baseline, baseline_child)
    if baseline_child != child:
        raise AssertionError("same-seed control generated a different logical identity")
    continue_prefix(baseline, baseline_child)
    resumed_digest = combined_being_checkpoint_digest(encode_combined_being_checkpoint(resumed))
    baseline_digest = combined_being_checkpoint_digest(encode_combined_being_checkpoint(baseline))
    if resumed_digest != baseline_digest:
        raise AssertionError("fresh-process continuation differs from uninterrupted control")
    if (resumed_being.id != baseline_being.id
            or resumed_being.original.obj_type != baseline_being.original.obj_type
            or resumed_being.original.hit_points != baseline_being.original.hit_points
            or resumed_being.original.STR() != baseline_being.original.STR()
            or resumed_being.original.skills.skills != baseline_being.original.skills.skills):
        raise AssertionError("native Being identity or authored attributes changed")
    # Corruption is rejected before any target world is supplied or modified.
    try:
        decode_combined_being_checkpoint(checkpoint.replace('"version": 1', '"version": 2', 1))
    except CombinedBeingCheckpointError:
        pass
    else:
        raise AssertionError("unsupported checkpoint version was accepted")
    print(f"RESTORE pid={__import__('os').getpid()} child={child} native={type(being).__name__}:{being.id}")
    print(f"registry identity={resumed.get_object_by_id(child) is being}; idempotent bridge retry=same instance")
    print(f"continued groups={len(resumed.reproduction_group_snapshot().groups)}; established parentage preserved=true")
    print(f"native authored attributes preserved=true; uninterrupted digest match={resumed_digest == baseline_digest}")
    print(f"digest={resumed_digest}; unsupported-version refusal=true")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("save", "resume"))
    parser.add_argument("--checkpoint", type=Path)
    args = parser.parse_args()
    if args.phase:
        if args.checkpoint is None:
            parser.error("--checkpoint is required with --phase")
        (phase_save if args.phase == "save" else phase_resume)(args.checkpoint)
        return
    with tempfile.TemporaryDirectory(prefix="u-rel-001v6-") as directory:
        path = Path(directory) / "combined-checkpoint.json"
        save = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--phase", "save",
                               "--checkpoint", str(path)], check=True, text=True, capture_output=True)
        resume = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--phase", "resume",
                                 "--checkpoint", str(path)], check=True, text=True, capture_output=True)
        print(save.stdout, end="")
        print(resume.stdout, end="")
        if "SAVE pid=" not in save.stdout or "RESTORE pid=" not in resume.stdout:
            raise AssertionError("subprocess phases did not report independent process identities")
        save_pid = int(save.stdout.split("SAVE pid=", 1)[1].split()[0])
        resume_pid = int(resume.stdout.split("RESTORE pid=", 1)[1].split()[0])
        if save_pid == resume_pid:
            raise AssertionError("save and restore ran in the same process")
        print(f"separate Python processes=true (save pid={save_pid}, restore pid={resume_pid})")


if __name__ == "__main__":
    main()
