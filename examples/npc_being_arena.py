"""Opt-in one-action native Arena for the external NPC skill fixture.

Run from the repository root with ``python examples/npc_being_arena.py``.
This is a local developer terminal demonstration, not a game UI or importer API.
"""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from abilities import Abilities
from atomic_publication import RNGCursor
from being import BeingDefinition, BeingInstance
from encounter import Encounter
from library import Library
from melee_combat import MeleeStrike
from npcgen_being_adapter import create_npcgen_v2_native_being
from skill import Skills
from spatial import CartesianPosition, Sphere
from universe import Universe


METERS_TO_YARDS = 1 / 0.9144


FIXTURE = ROOT / "tests/fixtures/external/npcgen-npc-native-skill-candidate.json"
EXPECTED_FIXTURE_SHA256 = "e59b55a6c22f822d65716215b64bccf0c1f2c7a42d49036092580d7c470241ae"
DEMO_ACTION_ID = "npc-being-arena/action/one-dagger-thrust"
DEMO_ENCOUNTER_ID = "npc-being-arena/encounter/one-thrust"
DEMO_SEED = 72002


@dataclass
class NpcBeingArena:
    world: Universe
    encounter: Encounter
    source_record: dict
    source_sha256: str
    npc: BeingInstance
    opponent: BeingInstance
    dagger_id: str
    strike: MeleeStrike
    rng: RNGCursor
    submitted: bool = False
    choice: object = None
    committed_result: object = None

    def developer_view(self):
        source_state = self.source_record["state"]
        native_scores = {
            "Str": self.npc.STR(), "Int": self.npc.INT(), "Wis": self.npc.WIS(),
            "Dex": self.npc.DEX(), "Con": self.npc.CON(), "Cha": self.npc.CHA(),
        }
        source_scores = self.source_record["sheet"]["abilities"]["scores"]
        if native_scores != source_scores:
            raise RuntimeError("native ability projection differs from the validated source scores")
        native_skills = {
            "armed combat": self.npc.get_skill_level("armed combat"),
            "Dagger": self.npc.get_weapon_skill_level("Dagger"),
        }
        if (native_skills["armed combat"] != source_state["skills"]["skills"]["armed combat"]
                or native_skills["Dagger"] != source_state["skills"]["weapon_skills"]["Dagger"]):
            raise RuntimeError("native skills differ from validated source ranks")
        return {
            "audience": "local omniscient developer view; not an Agent observation",
            "source_sha256": self.source_sha256,
            "source_derived": {"display_name": source_state["name"],
                               "abilities": source_scores, "skills": source_state["skills"],
                               "physical": {
                                   "stature_inches": source_state["height"],
                                   "stature_source_path": "state.height",
                                   "body_weight_pounds": source_state["weight"],
                                   "body_weight_source_path": "state.weight",
                               },
                               "initial_hit_points": {
                                   "value": source_state["hps"], "source_path": "state.hps",
                                   "meaning": "generated initial HP value; not a maximum-HP or Hit Dice mapping",
                               }},
            "npc_native": {
                "name": self.npc.name, "id": self.npc.id,
                "abilities": native_scores, "skills": native_skills,
                "initial_HP": self.npc.original.hit_points,
                "current_HP": self.npc.get_hit_points(),
                "length_inches": self.npc.original.length,
                "weight_pounds": self.npc.original.weight,
                "position": tuple(value * METERS_TO_YARDS
                                   for value in self.npc.get_position().as_tuple()),
                "position_unit": "yard",
                "geometry": self.npc.geometry.to_dict(),
                "geometry_unit": "meter",
                "equipment": [self.world.get_object_by_id(self.dagger_id).name],
            },
            "opponent_arena_authored": {
                "name": self.opponent.name, "id": self.opponent.id,
                "definition": self.opponent.current.obj_type,
                "initial_HP": self.opponent.original.hit_points,
                "current_HP": self.opponent.get_hit_points(),
                "AC": self.opponent.get_armor_class(),
                "position": tuple(value * METERS_TO_YARDS
                                   for value in self.opponent.get_position().as_tuple()),
                "position_unit": "yard",
                "geometry": self.opponent.geometry.to_dict(),
                "geometry_unit": "meter",
            },
            "arena_authored": {
                "NPC native definition/geometry/position":
                    "generic test baseline apart from source-derived initial HP; Sphere(0.5); (0, 0, 0)",
                "opponent": "Arena-authored initial/current HP 10, AC 11, generic test definition; Sphere(0.5); (1.5, 0, 0)",
                "equipment": "native Dagger explicitly supplied and equipped for this demo; not in source possession list",
                "encounter DC": 10,
                "action strategy": {"attack": 0, "defense": 0, "timing": 0, "extra_damage": 0},
            },
            "progression_mode": self.encounter.progression_mode,
        }

    def submit_thrust(self):
        """Accept the one fixed Choice without advancing or consuming RNG."""
        if self.submitted:
            raise RuntimeError("the one Arena thrust has already been submitted")
        choice = self.encounter.schedule_choice((self.strike,))
        self.choice = choice
        self.submitted = True
        return {
            "accepted": True,
            "action_id": self.strike.id,
            "choice_id": choice.id,
            "choice_state": choice.state,
            "start_time": self.strike.start_time,
            "scheduled_end_time": self.strike.end_time,
            "encounter_time": self.encounter.time,
        }

    def advance_to_commit(self):
        """Advance this fixed scenario to impact and read the publisher result."""
        if not self.submitted:
            raise RuntimeError("submit the fixed thrust before advancing")
        if self.committed_result is not None:
            raise RuntimeError("the one Arena thrust has already committed")
        self.encounter.step(self.strike.end_time - self.encounter.time)
        inspection = self.encounter.inspect_committed(self.strike.end_time)
        action = inspection.action(self.strike.id)
        self.committed_result = {
            "action_id": self.strike.id,
            "choice_id": action.lifecycle.choice_id,
            "boundary": action.resolved_boundary,
            "outcome": action.facts.outcome,
            "metadata": dict(action.facts.metadata),
            "causal_damage": dict(action.damage_by_target.get(self.opponent.id, {})),
            "target_id": self.opponent.id,
            # Result displays come from the immutable committed Target projection,
            # never from a later live read of the Being.
            "target_hp_after": inspection.target(self.opponent.id).state.projected_hp,
            "native_receipt_boundaries": tuple(
                row.boundary for row in self.encounter.__dict__.get("_atomic_interval_history", ())),
            "progression_mode": self.encounter.progression_mode,
        }
        return dict(self.committed_result)

    def resolve_one_thrust(self):
        """Terminal convenience: accept then publish the one fixed Action."""
        self.submit_thrust()
        return self.advance_to_commit()


def build_arena(*, seed=DEMO_SEED):
    """Build an unstarted, transactional Encounter from the exact v2 fixture."""
    raw = FIXTURE.read_bytes()
    source_sha256 = hashlib.sha256(raw).hexdigest()
    if source_sha256 != EXPECTED_FIXTURE_SHA256:
        raise ValueError("NPC fixture bytes differ from the reviewed U-NPC-BEING-001 fixture")
    source_record = json.loads(raw.decode("utf-8"))

    world = Universe("NPC Being native Arena", library=Library(config_dir=str(ROOT / "src/config")))
    npc = create_npcgen_v2_native_being(world, raw)
    npc.set_geometry(Sphere(0.5))
    npc.set_position(CartesianPosition(0, 0, 0))

    # All opponent properties are scenario authorship, not NPC source data.
    opponent_definition = BeingDefinition(
        "NPC Being Arena opponent", length=1.7, weight=70, hit_points=10,
        hit_dice="1d8", alignment="Neutral", armor_class=11,
        challenge_rating=1, abilities=Abilities(), skills=Skills(),
    )
    opponent = BeingInstance(opponent_definition, name="Arena opponent",
                             id="npc-being-arena/being/opponent")
    opponent.set_geometry(Sphere(0.5))
    opponent.set_position(CartesianPosition(1.5, 0, 0))
    world.add_object(opponent)

    dagger_id = world.make_weapon_for_being(npc.id, "Dagger", "Arena-supplied Dagger")
    if dagger_id is None or not world.arm_being(npc.id, dagger_id, "right hand"):
        raise RuntimeError("native Arena could not provide the test-authored Dagger")

    encounter = Encounter(world, difficulty_class=10, start_time=0,
                          initiated=True, id=DEMO_ENCOUNTER_ID)
    world.add_event(encounter)
    encounter.add_being(npc.id)
    encounter.add_being(opponent.id)
    encounter.mark_aware(npc.id, opponent.id)
    encounter.decide_to_act(npc.id, opponent.id, "fight")
    rng = RNGCursor(random.Random(seed).getstate())
    encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
    strike = MeleeStrike(encounter, npc.id, opponent.id, dagger_id,
                         motion="thrust", reach=2)
    strike.id = DEMO_ACTION_ID
    return NpcBeingArena(world, encounter, source_record, source_sha256,
                         npc, opponent, dagger_id, strike, rng)


def _format_developer_view(view):
    npc = view["npc_native"]
    opponent = view["opponent_arena_authored"]
    source = view["source_derived"]
    return "\n".join((
        "NPC → NATIVE BEING ARENA — local developer-only inspection",
        "The displayed record is not an Agent observation; no full source record is exposed.",
        f"Fixture SHA-256: {view['source_sha256']}",
        f"Source-derived name: {source['display_name']}",
        f"Source-derived abilities: {source['abilities']}",
        f"Source-derived acquired ranks: {source['skills']}",
        f"Source-derived stature={source['physical']['stature_inches']} in; "
        f"body weight={source['physical']['body_weight_pounds']} lb",
        f"Native Being: {npc['name']} ({npc['id']}) abilities={npc['abilities']} skills={npc['skills']}",
        f"Source-derived initial HP={source['initial_hit_points']['value']} ({source['initial_hit_points']['source_path']}); "
        f"native stature={npc['length_inches']} in, body weight={npc['weight_pounds']} lb; "
        f"current HP={npc['current_HP']}, position={npc['position']} yd, "
        f"geometry={npc['geometry']} {npc['geometry_unit']}, "
        f"equipment={npc['equipment']}",
        f"Arena-authored opponent: {opponent['name']} ({opponent['id']}), "
        f"initial/current HP={opponent['initial_HP']}/{opponent['current_HP']}, "
        f"AC={opponent['AC']}, position={opponent['position']} yd, "
        f"geometry={opponent['geometry']} {opponent['geometry_unit']}",
        "Action: one native Dagger thrust; default supplied Strategy is all zero.",
        "Progression: native opt-in transactional Encounter; publication is per crossed second.",
    ))


def main():
    arena = build_arena()
    print(_format_developer_view(arena.developer_view()))
    input("Press Enter once to accept the single fixed Thrust and advance to impact: ")
    result = arena.resolve_one_thrust()
    print("\nNative committed result")
    print(f"  Action={result['action_id']} Choice={result['choice_id']} boundary={result['boundary']}")
    print(f"  outcome={result['outcome']} metadata={result['metadata']}")
    print(f"  Target={result['target_id']} HP after={result['target_hp_after']} "
          f"causal damage={result['causal_damage']}")
    print(f"  progression={result['progression_mode']} native receipt boundaries="
          f"{result['native_receipt_boundaries']}")


if __name__ == "__main__":
    main()
