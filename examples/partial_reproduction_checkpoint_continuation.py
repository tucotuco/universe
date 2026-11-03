"""V11 fresh-process save/restore and progressive parent-membership proof.

The reproduction checkpoint is an integrity-checked data format, not an
authentication mechanism or general Universe save file.
"""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import tempfile
import random

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from abilities import Abilities
from being import BeingDefinition
from library import Library
from reproduction_being_bridge import materialize_reproductive_offspring
from reproduction_being_checkpoint import (
    COMBINED_VERSION, decode_combined_being_checkpoint,
    encode_combined_being_checkpoint, restore_combined_being_checkpoint,
)
from reproduction_checkpoint import (
    CHECKPOINT_VERSION, decode_reproduction_checkpoint,
    encode_reproduction_checkpoint, logical_reproduction_checkpoint_digest,
    restore_reproduction_checkpoint,
)
from reproduction_group import (
    ReproductionGroupElaborationProposal, ReproductionGroupProposal,
    prepare_reproduction_group,
)
from skill import Skills
from universe import Universe


def new_world(name):
    return Universe(name, library=Library(config_dir=str(ROOT / "src/config")))


def create(world, group_id, parents, offspring, *, complete, key):
    candidate = prepare_reproduction_group(ReproductionGroupProposal(
        group_id, parents, offspring, f"v11:{key}", parents_complete=complete,
    ))
    return world.publish_reproduction_group(
        candidate, request_key=key, expected_revision=world.reproduction_group_snapshot().revision,
    )


def elaborate(world, group_id, prior, additions, *, complete, key):
    return world.resolve_reproduction_group_elaboration(
        ReproductionGroupElaborationProposal(group_id, prior, additions, complete),
        request_key=key, expected_revision=world.reproduction_group_snapshot().revision,
    )


def initial_world(label):
    world = new_world(label)
    create(world, "G", ("A",), ("X", "SIB"), complete=False, key="create-G")
    create(world, "H", ("A",), ("Y",), complete=False, key="create-H")
    create(world, "G-child", ("X", "Q"), ("C",), complete=True, key="create-child")
    return world


def authored_definition():
    skills = Skills()
    skills.skills = {"authored craft": 2}
    return BeingDefinition(
        "V11 explicitly authored native Being", 1.8, 70, 10, "1d8", "Neutral", 10, 0,
        abilities=Abilities(strength=14), skills=skills, physiology_id="authored:v11-fixture",
    )


def bind(world, person_id):
    return materialize_reproductive_offspring(
        world, person_id, being_definition=authored_definition(), name="Authored X",
        request_key="bind-X", expected_revision=world.reproduction_group_snapshot().revision,
    )


def _complete_path(world):
    partial = next(group for group in world.reproduction_group_snapshot().groups if group.group_id == "G")
    added = elaborate(world, "G", partial.parent_ids, ("B",), complete=False, key="G:add:B")
    # Idempotent replay returns the historical result without a new revision.
    at_add = world.reproduction_group_snapshot()
    replay = elaborate(world, "G", ("A",), ("B",), complete=False, key="G:add:B")
    assert replay == added and world.reproduction_group_snapshot() == at_add
    complete = elaborate(world, "G", ("B", "A"), (), complete=True, key="G:complete")
    create(world, "A-singleton", ("A",), ("SINGLETON",), complete=True, key="create-singleton")
    return added, complete


def _logical_authored_state(world):
    snapshot = world.reproduction_group_snapshot()
    groups = tuple(
        (row.group_id, row.parent_ids, row.offspring_ids, row.source_reference,
         row.revision, row.parents_complete)
        for row in snapshot.groups
    )
    requests = tuple(
        (key, record.normalized_request,
         (record.result.group_id, record.result.parent_ids, record.result.offspring_ids,
          record.result.source_reference, record.result.request_key,
          record.result.revision, record.result.parents_complete))
        for key, record in sorted(world._reproduction_group_registry._requests.items())
    )
    return snapshot.revision, groups, requests


def phase_initial_save(path):
    world = initial_world("V11 process 1")
    checkpoint = encode_reproduction_checkpoint(world)
    path.write_text(checkpoint, encoding="utf-8")
    snapshot = world.reproduction_group_snapshot()
    print(f"SAVE pid={os.getpid()} schema=reproduction-v{CHECKPOINT_VERSION} revision={snapshot.revision}")
    print(f"G=({snapshot.known_parents('X')}, complete={snapshot.parents_complete_for('X')}); "
          f"H=({snapshot.known_parents('Y')}, complete={snapshot.parents_complete_for('Y')}); "
          f"descendant C parents={snapshot.known_parents('C')}")


def phase_extend(path):
    target = new_world("V11 process 2 fresh Universe")
    restored = restore_reproduction_checkpoint(target, path.read_text(encoding="utf-8"))
    if target.get_reproduction_group("G").parents_complete:
        raise AssertionError("one known parent was incorrectly treated as a complete singleton")
    before = restored
    _complete_path(target)
    after = target.reproduction_group_snapshot()
    try:
        elaborate(target, "H", ("A",), ("B",), complete=True, key="H:collides-with-G")
    except ValueError:
        pass
    else:
        raise AssertionError("overlapping H was silently merged into completed G")
    if target.reproduction_group_snapshot() != after:
        raise AssertionError("failed duplicate completion changed authoritative state")
    path.write_text(encode_reproduction_checkpoint(target), encoding="utf-8")
    group = target.get_reproduction_group("G")
    print(f"EXTEND pid={os.getpid()} restored_revision={before.revision} current_revision={after.revision}")
    print(f"same G id={group.group_id}; offspring={group.offspring_ids}; parents={group.parent_ids}; "
          f"complete={group.parents_complete}; collision_refused=true; checkpoint=reproduction-v{CHECKPOINT_VERSION}")


def phase_verify(path):
    target = new_world("V11 process 3 second fresh Universe")
    target_snapshot = restore_reproduction_checkpoint(target, path.read_text(encoding="utf-8"))
    group = target.get_reproduction_group("G")
    revision = target_snapshot.revision
    before_rng = random.getstate()
    replay = elaborate(target, "G", ("A",), ("B",), complete=False, key="G:add:B")
    after_replay = target.reproduction_group_snapshot()
    if after_replay.revision != revision or replay.parent_ids != ("A", "B"):
        raise AssertionError("restored membership request did not replay idempotently")
    if random.getstate() != before_rng:
        raise AssertionError("idempotent membership replay changed RNG")
    before_conflict = after_replay
    try:
        elaborate(target, "G", ("A",), ("C",), complete=False, key="G:add:B")
    except ValueError:
        pass
    else:
        raise AssertionError("conflicting request-key reuse was accepted")
    if target.reproduction_group_snapshot() != before_conflict:
        raise AssertionError("conflicting replay changed authoritative state")

    control = initial_world("V11 uninterrupted control")
    _complete_path(control)
    if _logical_authored_state(target) != _logical_authored_state(control):
        raise AssertionError("restored facts, request receipts, or revisions differ from uninterrupted control")
    resumed_digest = logical_reproduction_checkpoint_digest(encode_reproduction_checkpoint(target))
    control_digest = logical_reproduction_checkpoint_digest(encode_reproduction_checkpoint(control))
    if resumed_digest != control_digest:
        raise AssertionError("fresh-process membership continuation differs from uninterrupted control")
    if (group.group_id != "G" or group.offspring_ids != ("X", "SIB")
            or group.parent_ids != ("A", "B") or not group.parents_complete
            or target.reproduction_group_snapshot().known_parents("C") != ("Q", "X")
            or target.reproduction_group_snapshot().known_grandparent_paths("C") != (("X", ("A", "B")),)):
        raise AssertionError("restored membership or derived descendant facts changed")
    print(f"VERIFY pid={os.getpid()} revision={revision}; replay_revision_unchanged=true; "
          f"conflicting_key_refused=true; request_keys={target.reproduction_group_snapshot().request_keys}")
    print(f"same uninterrupted logical state={resumed_digest == control_digest}; digest={resumed_digest}; "
          f"facts_and_request_receipts_match=true; revisions_match=true; "
          f"G complete={target.get_reproduction_group('G').parents_complete}")


def phase_combined_save(path):
    world = initial_world("V11 combined save")
    being = bind(world, "X")
    encoded = encode_combined_being_checkpoint(world)
    path.write_text(encoded, encoding="utf-8")
    print(f"COMBINED-SAVE pid={os.getpid()} schema=combined-v{COMBINED_VERSION} "
          f"native={type(being).__name__}:{being.id}; G complete={world.get_reproduction_group('G').parents_complete}")


def phase_combined_extend(path):
    target = new_world("V11 combined extend process")
    candidate = decode_combined_being_checkpoint(path.read_text(encoding="utf-8"))
    being = restore_combined_being_checkpoint(target, candidate)
    if target.get_reproduction_group("G").parents_complete or target.get_object_by_id("X") is not being:
        raise AssertionError("combined checkpoint lost partial semantics or native identity")
    original_definition = being.original
    _complete_path(target)
    if being.original is not original_definition or being.id != "X":
        raise AssertionError("membership elaboration changed the existing native Being")
    path.write_text(encode_combined_being_checkpoint(target), encoding="utf-8")
    print(f"COMBINED-EXTEND pid={os.getpid()} G complete={target.get_reproduction_group('G').parents_complete}; "
          f"native identity stable={being.id}; re-saved=combined-v{COMBINED_VERSION}")


def phase_combined_verify(path):
    target = new_world("V11 combined restore process")
    candidate = decode_combined_being_checkpoint(path.read_text(encoding="utf-8"))
    being = restore_combined_being_checkpoint(target, candidate)
    group = target.get_reproduction_group("G")
    if (being.id != "X" or target.get_object_by_id("X") is not being
            or being.original.obj_type != "V11 explicitly authored native Being"
            or group.parent_ids != ("A", "B") or not group.parents_complete):
        raise AssertionError("combined restore did not preserve native Being and completed group")
    print(f"COMBINED-VERIFY pid={os.getpid()} BeingInstance={being.id}; authored type={being.original.obj_type}; "
          f"G=({group.parent_ids}, complete={group.parents_complete})")


def run_subprocess(script, phase, path):
    return subprocess.run(
        [sys.executable, str(script), "--phase", phase, "--checkpoint", str(path)],
        check=True, text=True, capture_output=True,
    ).stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("save", "extend", "verify", "combined-save", "combined-extend", "combined-verify"))
    parser.add_argument("--checkpoint", type=Path)
    args = parser.parse_args()
    phases = {
        "save": phase_initial_save, "extend": phase_extend, "verify": phase_verify,
        "combined-save": phase_combined_save, "combined-extend": phase_combined_extend,
        "combined-verify": phase_combined_verify,
    }
    if args.phase:
        if args.checkpoint is None:
            parser.error("--checkpoint is required with --phase")
        phases[args.phase](args.checkpoint)
        return

    script = Path(__file__).resolve()
    with tempfile.TemporaryDirectory(prefix="u-rel-001v11-") as directory:
        path = Path(directory) / "reproduction-v2.json"
        outputs = [run_subprocess(script, phase, path) for phase in ("save", "extend", "verify")]
        print("".join(outputs), end="")
        pids = [int(output.split("pid=", 1)[1].split()[0]) for output in outputs]
        if len(set(pids)) != len(pids):
            raise AssertionError("reproduction phases did not use three fresh Python processes")

        combined_path = Path(directory) / "combined-v2.json"
        combined_outputs = [run_subprocess(script, phase, combined_path)
                            for phase in ("combined-save", "combined-extend", "combined-verify")]
        print("".join(combined_outputs), end="")
        combined_pids = [int(output.split("pid=", 1)[1].split()[0]) for output in combined_outputs]
        if len(set(combined_pids)) != len(combined_pids):
            raise AssertionError("combined checkpoint phases did not use three fresh Python processes")
        print(f"separate processes=true reproduction={pids}; combined-native={combined_pids}")


if __name__ == "__main__":
    main()
