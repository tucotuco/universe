"""Bridge one test-generated logical offspring to one authored native Being.

The reproductive profile is test-only. Native Being properties are explicitly
authored below and are not inferred from the profile or genealogy.
"""
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from being import BeingDefinition, BeingInstance
from library import Library
from reproduction_being_bridge import materialize_reproductive_offspring
from reproduction_checkpoint import encode_reproduction_checkpoint, restore_reproduction_checkpoint
from reproduction_generation import StatisticalReproductionRequest, TestOnlyOffspringCountDistribution
from universe import Universe


def new_world(name):
    return Universe(name, library=Library(config_dir=str(ROOT / "src/config")))


def main():
    source = new_world("V5 logical source")
    profile = TestOnlyOffspringCountDistribution("v5-single-offspring", "1", ((1, 1),))
    request = StatisticalReproductionRequest(("P", "Q"), 17, 0, (0,), profile)
    outcome = source.resolve_statistical_reproduction(
        request, request_key="V5-PQ-one-child", expected_revision=0,
    )
    if outcome.count != 1 or outcome.group_id is None:
        raise SystemExit("test-only generation did not establish one logical offspring")
    child_id = outcome.offspring_ids[0]
    before = source.reproduction_group_snapshot()
    checkpoint = encode_reproduction_checkpoint(source)

    # Restore only the reproduction domain. Native materialization is a new,
    # separately authored operation in this process.
    target = new_world("V5 restored reproduction domain")
    restore_reproduction_checkpoint(target, checkpoint)
    restored_before = target.reproduction_group_snapshot()
    if restored_before.known_parents(child_id) != before.known_parents(child_id):
        raise SystemExit("restored logical parentage changed")

    authored_definition = BeingDefinition(
        obj_type="V5 explicitly authored native fixture",
        length=1.8,
        weight=70,
        hit_points=10,
        hit_dice="1d8",
        alignment="Neutral",
        armor_class=10,
        challenge_rating=0,
    )
    rng_before = random.getstate()
    being = materialize_reproductive_offspring(
        target, child_id, being_definition=authored_definition,
        name="Authored native offspring C", request_key="materialize-C",
        expected_revision=restored_before.revision,
    )
    repeated = materialize_reproductive_offspring(
        target, child_id, being_definition=authored_definition,
        name="Authored native offspring C", request_key="materialize-C",
        expected_revision=restored_before.revision,
    )
    after = target.reproduction_group_snapshot()
    if (not isinstance(being, BeingInstance) or being.id != child_id
            or target.get_object_by_id(child_id) is not being or repeated is not being
            or after != restored_before or random.getstate() != rng_before
            or len(target.object_registry.object_instances) != 1
            or set(target.event_history) != {"0"} or target._choice_books):
        raise SystemExit("native offspring identity bridge invariant failed")
    print(f"logical C={child_id}; parents={after.known_parents(child_id)}; group={outcome.group_id}")
    print(f"native BeingInstance.id={being.id}; same individual={being.id == child_id}; "
          f"ObjectRegistry lookup same instance={target.get_object_by_id(child_id) is being}")
    print(f"idempotent retry same instance={repeated is being}; reproductive facts unchanged={after == restored_before}")
    print(f"native Objects={len(target.object_registry.object_instances)}; Encounters=0; "
          "population/Observation/Belief effects=0")
    print("native properties came from the explicit BeingDefinition fixture; checkpoint restored genealogy only")


if __name__ == "__main__":
    main()
