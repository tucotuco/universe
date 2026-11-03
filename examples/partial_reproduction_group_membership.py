"""V10R: progressively resolve parent membership on stable ReproductionGroups.

This world-only example treats known parent membership as positive Reality but
marks whether each group's full parent set is established. No Being, Encounter,
Observation or Belief is created or changed.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from library import Library
from reproduction_group import (
    ReproductionGroupElaborationProposal, ReproductionGroupProposal,
    prepare_reproduction_group,
)
from universe import Universe


def publish(world, group_id, parents, offspring, *, complete, key):
    candidate = prepare_reproduction_group(ReproductionGroupProposal(
        group_id, parents, offspring, f"author:{key}", parents_complete=complete,
    ))
    return world.publish_reproduction_group(
        candidate, request_key=key, expected_revision=world.reproduction_group_snapshot().revision,
    )


def elaborate(world, group_id, prior, added, *, complete, key):
    return world.resolve_reproduction_group_elaboration(
        ReproductionGroupElaborationProposal(group_id, prior, added, complete),
        request_key=key, expected_revision=world.reproduction_group_snapshot().revision,
    )


def main():
    world = Universe("V10R partial parent membership", library=Library(config_dir=str(ROOT / "src/config")))
    # X's already-established child shows that X can later parent another group.
    publish(world, "G", ("A",), ("X", "SIB"), complete=False, key="g")
    publish(world, "H", ("A",), ("Y",), complete=False, key="h")
    publish(world, "G-child", ("X", "Q"), ("C",), complete=True, key="g-child")
    initial = world.reproduction_group_snapshot()
    g_id, g_children = "G", initial.groups[0].offspring_ids

    print("V10R world-only partial ReproductionGroup membership; no biological or calendar rules")
    print(f"initial G: known parents of X={initial.known_parents('X')}; complete={initial.parents_complete_for('X')}")
    print(f"initial H: known parents of Y={initial.known_parents('Y')}; complete={initial.parents_complete_for('Y')}")
    print(f"completed-parent-set index before resolution={initial.group_id_by_parent_set}")
    print(f"known shared-parent relative of X={initial.known_shared_parent_relatives('X')}")

    added = elaborate(world, "G", ("A",), ("B",), complete=False, key="g-add-b")
    middle = world.reproduction_group_snapshot()
    print(f"after adding B: G parents={middle.known_parents('X')}; complete={middle.parents_complete_for('X')}; "
          f"exact-set index={middle.group_id_by_parent_set}")

    # Marking complete does not add a parent, and is distinct from incomplete {A}.
    publish(world, "A-only", ("A",), ("SINGLETON-CHILD",), complete=True, key="singleton")
    completed = elaborate(world, "G", ("A", "B"), (), complete=True, key="g-complete")
    final = world.reproduction_group_snapshot()
    print(f"completed G: stable id={completed.group_id}; offspring={completed.offspring_ids}; "
          f"parents={final.known_parents('X')}; complete={final.parents_complete_for('X')}")
    print(f"completed exact-set index={final.group_id_by_parent_set}")
    print(f"known grandparent path of C={final.known_grandparent_paths('C')}")

    before_collision = final
    try:
        elaborate(world, "H", ("A",), ("B",), complete=True, key="h-collision")
    except ValueError as exc:
        print(f"H completion collision refused: {exc}")
    else:
        raise SystemExit("a duplicate completed exact parent set was accepted")
    after_collision = world.reproduction_group_snapshot()
    print(f"collision left groups/revision unchanged={after_collision == before_collision}")
    print(f"native Objects={len(world.object_registry.object_instances)}; Encounters={len(world._choice_books)}; "
          f"event keys={tuple(world.event_history)}")

    g = world.get_reproduction_group(g_id)
    if (g.group_id != g_id or g.offspring_ids != g_children
            or final.known_parents("X") != ("A", "B")
            or final.parents_complete_for("X") is not True
            or final.known_parents("C") != ("Q", "X")
            or final.known_grandparent_paths("C") != (("X", ("A", "B")),)
            or after_collision != before_collision
            or world.object_registry.object_instances or world._choice_books
            or tuple(world.event_history) != ("0",)):
        raise SystemExit("V10R partial-membership invariant failed")


if __name__ == "__main__":
    main()
