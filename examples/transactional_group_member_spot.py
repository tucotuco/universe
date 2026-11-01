"""Runtime realization followed by an independent native Spot discovery.

Run from the repository root with ``python examples/transactional_group_member_spot.py``.
The printed timeline is omniscient developer inspection. The 5E2G realization
is a publisher operation, not an Action receipt; Run, Spot, and Thrust appear
in the native Action receipts.
"""
from copy import deepcopy
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from activities import RunAction, SpotAction
from atomic_publication import RNGCursor
from encounter import Encounter
from group_member_realization import (
    AdultMemberGeometryDescriptor,
    AdultMemberRequest,
    prepare_adult_member_candidate,
)
from library import Library
from melee_combat import MeleeStrike
from spatial import CartesianPosition, Sphere, VisualOcclusion
from statistical_group import StatisticalGroup
from universe import Universe


def _execute(*, inject_targeted_fault=False, spot_succeeds=True):
    config = deepcopy(json.loads((ROOT / "examples" / "nomadic_group.json").read_text()))
    config["group_id"] = "counted-member-group"
    config["motion"].update(position=[0, 0, 0], velocity=[0, 0, 0],
                            acceleration=[0, 0, 0])
    world = Universe("Transactional Group member Spot demonstration",
                     library=Library(config_dir=str(ROOT / "src" / "config")))
    observer_ids = [world.make_being("Human", name)
                    for name in ("Observer one", "Observer two")]
    observers = [world.get_object_by_id(identity) for identity in observer_ids]
    observers[0].set_position(CartesianPosition(0, -20, 0))
    # The second observer begins near the established group area. This is a
    # scenario placement, not location information acquired from Group counts.
    observers[1].set_position(CartesianPosition(1, 30, 0))
    for observer in observers:
        observer.set_geometry(Sphere(0.5))
    dagger_id = world.make_weapon_for_being(
        observers[1].id, "Dagger", "Observer two's dagger")
    world.arm_being(observers[1].id, dagger_id, "right hand")
    observers[1].set_weapon_skill_level(
        world.get_weapon_dictionary(), "Dagger", 5)

    group = StatisticalGroup("Counted group", config["group_id"], config,
                             config["seed"])
    # The aggregate is modeled as a transparent envelope so the existing
    # conservative geometric path tracer does not treat its missing shape as
    # unknown opacity. This is a scenario premise, not a Group sensing rule.
    group.set_geometry(Sphere(max(group.footprint_radius, 0.5)))
    group.set_visual_occlusion(VisualOcclusion(0.0))
    counts_before = group.counts()
    world.add_object(group)
    encounter = Encounter(world, difficulty_class=15, start_time=0,
                          initiated=True, id="runtime-member-spot-encounter",
                          awareness={observer_ids[1]: {observer_ids[0]}})
    world.add_event(encounter)
    for observer in observers:
        encounter.add_being(observer.id)
    encounter.add_object(group.id)
    # Seed 5302/5303 make the single native Spot check reproducibly succeed/fail;
    # the Agent intent itself supplies neither a target ID nor a roll.
    rng = RNGCursor(random.Random(5302 if spot_succeeds else 5303).getstate())
    rng_before = rng.state
    encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)

    first_run = RunAction(world, observers[0].id, 0, 1, 1, experience=3,
                          id="preexisting-observer-run")
    encounter.schedule_choice((first_run,))
    request = AdultMemberRequest(
        group.id, 0, "adults", 0, 1,
        geometry=AdultMemberGeometryDescriptor(sphere_radius=0.5),
    )
    candidate = prepare_adult_member_candidate(encounter, group, request)
    first_interval = encounter.prepare_interval_candidate(
        1, velocities={observers[0].id: (2, 0, 0)}, rng_owner=rng,
        adult_member_candidate=candidate,
    )
    if candidate.member_id in first_interval.pre_action_snapshot.entities:
        raise AssertionError("new adult leaked into boundary 1 shared snapshot")
    encounter.step(1, velocities={observers[0].id: (2, 0, 0)},
                   adult_member_candidate=candidate)
    member = world.get_object_by_id(candidate.member_id)
    if member is None or member.geometry != Sphere(0.5):
        raise AssertionError("publisher did not install the requested native geometry")
    if group.counts() != counts_before:
        raise AssertionError("runtime realization changed objective Group composition")
    if any(encounter.is_aware(observer.id, member.id) for observer in observers):
        raise AssertionError("realization itself granted Awareness")
    boundary_one_awareness = tuple(
        encounter.is_aware(observer.id, member.id) for observer in observers)
    boundary_one_receipt = encounter._atomic_interval_history[-1]

    member_run = RunAction(world, member.id, 1, 1, 1, experience=7,
                           id="realized-adult-run")
    encounter.schedule_choice((member_run,))
    second_interval = encounter.prepare_interval_candidate(
        2, velocities={member.id: (2, 0, 0)}, rng_owner=rng)
    if member.id not in second_interval.pre_action_snapshot.entities:
        raise AssertionError("realized adult was not eligible at the next boundary")
    encounter.step(1, velocities={member.id: (2, 0, 0)})
    boundary_two_receipt = encounter._atomic_interval_history[-1]
    if member.get_skill_experience("run") != 7:
        raise AssertionError("native Run practice was not applied to the realized Being")
    boundary_two_awareness = tuple(
        encounter.is_aware(observer.id, member.id) for observer in observers)

    # Observer two submits only an attention intent. Its initial Awareness of
    # observer one is scenario knowledge, leaving exactly one unfamiliar Being.
    awareness_before_spot = tuple(
        tuple(encounter.aware_beings(observer.id)) for observer in observers)
    if any(member.id in known_ids for known_ids in awareness_before_spot):
        raise AssertionError("realization or prior state exposed the individual before Spot")
    from attention_intent import accept_spot_attention
    attention_result = accept_spot_attention(encounter, observers[1].id)
    if not attention_result.accepted:
        raise AssertionError("unique unfamiliar Being should accept the attention intent")
    if hasattr(attention_result, 'target_id') or hasattr(attention_result, 'action_id'):
        raise AssertionError("Agent-facing attention result disclosed an internal identity")
    if any(encounter.is_aware(observer.id, member.id) for observer in observers):
        raise AssertionError("Spot Awareness appeared before the Action resolved")
    awareness_by_boundary = []
    spot = None
    for boundary in range(3, 9):
        encounter.step(1)
        if boundary == 3:
            # Trusted developer trace only: retrieve the accepted native Action
            # after its start fence; the Agent-facing result carries no ID.
            from activities import SpotAction
            spot = next(world.get_event_by_id(action_id)
                        for action_id in encounter.pending_action_list
                        if type(world.get_event_by_id(action_id)) is SpotAction)
        awareness_by_boundary.append((
            boundary,
            encounter.is_aware(observers[0].id, member.id),
            encounter.is_aware(observers[1].id, member.id),
        ))
    spot_receipt = encounter._atomic_interval_history[-1]
    spot_inspection = encounter.inspect_committed()
    spot_record = spot_inspection.action(spot.id)
    awareness_after_spot = tuple(
        tuple(encounter.aware_beings(observer.id)) for observer in observers)
    thrust_target_id = None
    thrust = None
    target_hp_before_thrust = None
    targeted_rollback = None
    thrust_receipt = None

    if spot_record.facts.outcome == "success":
        # This is the only source for the follow-up Action's target choice. The
        # latent slot ID is used below only for developer-side equality checks.
        known_targets = awareness_after_spot[1]
        newly_aware = tuple(target_id for target_id in known_targets
                            if target_id not in awareness_before_spot[1])
        if len(newly_aware) != 1:
            raise AssertionError("Spot must add exactly one observer-owned Being reference")
        thrust_target_id = newly_aware[0]
        if thrust_target_id != member.id:
            raise AssertionError("Spot Awareness does not identify the scenario target")
        if member.id in awareness_after_spot[0]:
            raise AssertionError("observer one inherited observer two's Awareness")

        target_hp_before_thrust = member.get_hit_points()
        thrust = MeleeStrike(encounter, observers[1].id, thrust_target_id, dagger_id,
                             motion="thrust", reach=2)
        encounter.schedule_choice((thrust,))
        if thrust.start_time != 8 or thrust.end_time != 12:
            raise AssertionError("native dagger thrust timing changed")
        for _ in range(3):
            encounter.step(1)
    else:
        if any(member.id in known_ids for known_ids in awareness_after_spot):
            raise AssertionError("failed Spot published an individual target reference")
        if inject_targeted_fault:
            raise ValueError("targeted-publication fault injection requires a successful Spot")

    if inject_targeted_fault:
        from unittest.mock import patch
        import atomic_publication
        from atomic_publication import PublicationFailure, target_interval_history

        before_fault = (
            member.get_hit_points(), member.get_skill_experience("run"),
            observers[1].get_skill_experience("Dagger"),
            tuple(observers[1].skill_use_history),
            tuple(member.skill_use_history), thrust.resolution,
            tuple(id(row) for row in target_interval_history(member)),
            tuple(id(row) for row in target_interval_history(observers[1])),
            tuple(encounter.pending_action_list), tuple(encounter.finished_action_list),
            tuple(id(receipt) for receipt in encounter._atomic_interval_history),
            rng.state,
        )
        publisher = atomic_publication.publish_interval_candidate

        def fail_after_target_writes(owner, candidate, **kwargs):
            return publisher(owner, candidate, _fail_after="targets", **kwargs)

        with patch.object(atomic_publication, "publish_interval_candidate",
                          fail_after_target_writes):
            try:
                encounter.step(1)
            except PublicationFailure as error:
                if error.phase != "targets" or error.rollback_errors:
                    raise
                rollback_token = error.recovery_token
            else:
                raise AssertionError("targeted Action fault injection did not fail")
        after_fault = (
            member.get_hit_points(), member.get_skill_experience("run"),
            observers[1].get_skill_experience("Dagger"),
            tuple(observers[1].skill_use_history),
            tuple(member.skill_use_history), thrust.resolution,
            tuple(id(row) for row in target_interval_history(member)),
            tuple(id(row) for row in target_interval_history(observers[1])),
            tuple(encounter.pending_action_list), tuple(encounter.finished_action_list),
            tuple(id(receipt) for receipt in encounter._atomic_interval_history),
            rng.state,
        )
        if before_fault != after_fault:
            raise AssertionError("failed targeted Action publication leaked state")
        encounter.recover_transactional_progression(rollback_token)
        encounter.step(1)
        targeted_rollback = {"phase": "targets", "restored": True}
    elif thrust is not None:
        encounter.step(1)
    if thrust is not None:
        thrust_receipt = encounter._atomic_interval_history[-1]
        if rng.state != thrust_receipt.rng_state:
            raise AssertionError("authoritative RNG differs from the committed Thrust receipt")
        inspection = encounter.inspect_committed()
    else:
        inspection = spot_inspection

    return {
        "world": world,
        "encounter": encounter,
        "group": group,
        "observers": observers,
        "member": member,
        "candidate": candidate,
        "first_interval": first_interval,
        "second_interval": second_interval,
        "first_run": first_run,
        "member_run": member_run,
        "spot": spot,
        "attention_result": attention_result,
        "thrust": thrust,
        "inspection": inspection,
        "counts_before": counts_before,
        "rng_before": rng_before,
        "rng": rng,
        "boundary_one_receipt": boundary_one_receipt,
        "boundary_two_receipt": boundary_two_receipt,
        "boundary_one_awareness": boundary_one_awareness,
        "boundary_two_awareness": boundary_two_awareness,
        "awareness_before_spot": awareness_before_spot,
        "awareness_after_spot": awareness_after_spot,
        "spot_receipt": spot_receipt,
        "thrust_receipt": thrust_receipt,
        "thrust_target_id": thrust_target_id,
        "targeted_rollback": targeted_rollback,
        "target_hp_before_thrust": target_hp_before_thrust,
        "awareness_by_boundary": tuple(awareness_by_boundary),
    }


def demo_data():
    state = _execute()
    world, encounter, group = state["world"], state["encounter"], state["group"]
    observers, member = state["observers"], state["member"]
    inspection = state["inspection"]
    spot_record = inspection.action(state["spot"].id)
    return {
        "presentation": "omniscient developer trace; not an Agent view or authenticated realization record",
        "geometry_premise": {
            "descriptor": "sphere",
            "radius_scenario_units": state["candidate"].geometry.sphere_radius,
            "meaning": "explicit visibility geometry for this scenario, not a Human default",
        },
        "chronology": {
            "boundary_1": {
                "candidate_absent_from_shared_snapshot": member.id not in
                    state["first_interval"].pre_action_snapshot.entities,
                "realized_and_registered_after_commit": world.get_object_by_id(member.id) is member,
                "participant_after_commit": member.id in encounter.being_list,
                "counts_conserved": group.counts() == state["counts_before"],
                "receipt_action_ids": state["boundary_one_receipt"].action_ids,
                "realization_has_its_own_action_or_receipt": False,
                "observer_awareness": state["boundary_one_awareness"],
            },
            "boundary_2": {
                "member_run_outcome": inspection.action(state["member_run"].id).facts.outcome,
                "run_experience_owned_by_member": member.get_skill_experience("run"),
                "receipt_action_ids": state["boundary_two_receipt"].action_ids,
                "observer_awareness_before_spot_resolution": state["boundary_two_awareness"],
            },
            "spot": {
                "initial_target_source": "Agent attention intent; world privately bound the unique unfamiliar participating Being",
                "agent_facing_acceptance": {
                    "accepted": state["attention_result"].accepted,
                    "status": state["attention_result"].status,
                    "discloses_target_identity": False,
                    "limitation": "trusted native/developer Python APIs remain omniscient",
                },
                "duration_seconds": state["spot"].end_time - state["spot"].start_time,
                "resolved_boundary": spot_record.resolved_boundary,
                "outcome": spot_record.facts.outcome,
                "roll": dict(spot_record.facts.metadata)["roll"],
                "awareness_by_boundary": state["awareness_by_boundary"],
                "aware_beings_before_resolution": state["awareness_before_spot"],
                "aware_beings_after_commit": state["awareness_after_spot"],
                "observer_one_aware": encounter.is_aware(observers[0].id, member.id),
                "observer_two_aware": encounter.is_aware(observers[1].id, member.id),
                "spot_experience_awarded": tuple(
                    observer.get_skill_experience("spot") for observer in observers),
                "receipt_action_ids": state["spot_receipt"].action_ids,
            },
            "targeted_thrust": {
                "action_id": state["thrust"].id,
                "actor_id": state["thrust"].actor_id,
                "target_id": state["thrust"].target_id,
                "target_source": "Encounter.aware_beings(observer_two.id) after Spot boundary 8 committed",
                "instrument_id": state["thrust"].instrument_id,
                "timing": (state["thrust"].start_time,
                           state["thrust"].end_time),
                "resolved_boundary": inspection.action(
                    state["thrust"].id).resolved_boundary,
                "outcome": inspection.action(state["thrust"].id).facts.outcome,
                "outcome_note": "Group aggregate extent is excluded from physical melee obstruction; native attack mechanics determine the result",
                "target_hp_before": state["target_hp_before_thrust"],
                "target_hp_after": member.get_hit_points(),
                "causal_effects": tuple(
                    {"identity": {
                         "encounter_id": row.identity.encounter_id,
                         "boundary": row.identity.boundary,
                         "source_action_id": row.identity.source_action_id,
                         "channel": row.identity.channel,
                         "slot": row.identity.slot,
                     },
                     "target_id": getattr(row.effect, "target_id", None),
                     "effect": type(row.effect).__name__}
                    for row in inspection.action(state["thrust"].id).effects),
                "receipt_action_ids": state["thrust_receipt"].action_ids,
                "counts_conserved": group.counts() == state["counts_before"],
                "rollback_recovered_before_retry": state["targeted_rollback"],
            },
        },
        "final": {
            "encounter_time": encounter.time,
            "group_counts": group.counts(),
            "rng_advanced_for_thrust": state["rng_before"] != state["rng"].state,
            "rng_matches_last_receipt": state["rng"].state == state["thrust_receipt"].rng_state,
        },
    }


if __name__ == "__main__":
    print(json.dumps(demo_data(), indent=2, sort_keys=True))
