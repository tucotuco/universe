"""Bounded real-file NPC skill import into the native melee path."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from abilities import Abilities
from being import BeingDefinition, BeingInstance
from encounter import Encounter
from library import Library
from melee_combat import MeleeStrike
from npcgen_being_adapter import create_npcgen_v2_native_being
from skill import Skills
from spatial.state import CartesianPosition
from universe import Universe


FIXTURE = ROOT / "tests/fixtures/external/npcgen-npc-native-skill-candidate.json"
FIXTURE_SHA256 = "e59b55a6c22f822d65716215b64bccf0c1f2c7a42d49036092580d7c470241ae"


def _library():
    return Library(config_dir=str(ROOT / "src/config"))


def _zero_skill_control(world, source_record):
    """Create a same-ability, no-acquired-weapon-skill comparison Being."""
    scores = source_record["sheet"]["abilities"]["scores"]
    abilities = Abilities(
        strength=scores["Str"], intelligence=scores["Int"], wisdom=scores["Wis"],
        dexterity=scores["Dex"], constitution=scores["Con"], charisma=scores["Cha"],
    )
    definition = BeingDefinition(
        "native zero-skill control", length=1.7, weight=70, hit_points=10,
        hit_dice="1d8", alignment="Neutral", armor_class=11, challenge_rating=1,
        abilities=abilities, skills=Skills(),
    )
    being = BeingInstance(definition, name="Control")
    world.add_object(being)
    return being


def _one_melee_attempt(imported):
    raw = FIXTURE.read_bytes()
    record = json.loads(raw)
    world = Universe("NPC import integration", library=_library())
    actor = (create_npcgen_v2_native_being(world, raw) if imported
             else _zero_skill_control(world, record))
    target_id = world.make_being("Human", "Target")
    target = world.get_object_by_id(target_id)
    actor.set_position(CartesianPosition(0, 0, 0))
    target.set_position(CartesianPosition(1.5, 0, 0))
    # The source record does not grant equipment. This Dagger is supplied
    # explicitly by the test scenario so the native MeleeStrike can execute.
    dagger_id = world.make_weapon_for_being(actor.id, "Dagger", "Test Dagger")
    world.arm_being(actor.id, dagger_id, "right hand")
    encounter = Encounter(world, difficulty_class=10, start_time=0)
    encounter.add_being(actor.id)
    encounter.add_being(target_id)
    encounter.mark_aware(actor.id, target_id)
    encounter.decide_to_act(actor.id, target_id, "fight")
    strike = MeleeStrike(encounter, actor.id, target_id, dagger_id,
                         motion="thrust", reach=2)
    encounter.schedule_action(strike)
    with patch("action.roll_dice", side_effect=[8, 4]):
        encounter.step(duration=4)
    return world, actor, target, strike


class TestNpcgenNativeBeingIntegration(unittest.TestCase):
    def setUp(self):
        self.raw = FIXTURE.read_bytes()
        self.record = json.loads(self.raw)

    def test_fixture_is_exact_source_and_creates_native_skilled_being(self):
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), FIXTURE_SHA256)
        original = deepcopy(self.record)
        world = Universe("import source preservation", library=_library())
        being = create_npcgen_v2_native_being(world, self.raw)

        self.assertIsInstance(being, BeingInstance)
        self.assertIs(world.get_object_by_id(being.id), being)
        self.assertNotIn("id", self.record["state"])  # native ID is independently created
        self.assertEqual(being.name, "Tobe")
        self.assertEqual((being.STR(), being.INT(), being.WIS(), being.DEX(),
                          being.CON(), being.CHA()), (12, 11, 16, 12, 9, 14))
        self.assertEqual(being.FIT(), 9)  # native Abilities convention: FIT follows CON
        self.assertEqual(being.get_skill_level("armed combat"), 1)
        self.assertEqual(being.get_weapon_skill_level("Dagger"), 2)
        self.assertEqual(being.original.hit_points, 23)
        self.assertEqual(being.get_hit_points(), 23)
        self.assertEqual(being.skill_experience, {})
        self.assertEqual(being.skill_use_history, [])
        self.assertEqual(being.weapons, [])
        self.assertEqual(being.possessions, [])
        self.assertEqual(self.record, original)
        self.assertEqual(self.raw, FIXTURE.read_bytes())

    def test_imported_dagger_rank_changes_real_native_melee_outcome(self):
        imported_world, imported, imported_target, imported_strike = _one_melee_attempt(True)
        control_world, control, control_target, control_strike = _one_melee_attempt(False)

        self.assertEqual(imported.get_weapon_skill_level("Dagger"), 2)
        self.assertEqual(control.get_weapon_skill_level("Dagger"), 0)
        self.assertEqual(imported_strike.hit_type, "normal")  # roll 8 + native rank 2 meets DC 10
        self.assertEqual(control_strike.hit_type, "miss")     # same roll, zero weapon rank
        self.assertLess(imported_target.get_hit_points(), 10)
        self.assertEqual(control_target.get_hit_points(), 10)
        self.assertIs(imported_world.get_object_by_id(imported.id), imported)
        self.assertIs(control_world.get_object_by_id(control.id), control)
        self.assertEqual(imported_strike.get_instrument().current.obj_type, "Dagger")

    def test_unknown_or_unsupported_skill_data_refuses_without_registration(self):
        cases = []
        null_skills = deepcopy(self.record)
        null_skills["state"]["skills"] = None
        cases.append(("unknown null", null_skills))
        bool_rank = deepcopy(self.record)
        bool_rank["state"]["skills"]["skills"]["armed combat"] = True
        cases.append(("boolean rank", bool_rank))
        zero_rank = deepcopy(self.record)
        zero_rank["state"]["skills"]["weapon_skills"]["Dagger"] = 0
        cases.append(("zero rank", zero_rank))
        extra_rank = deepcopy(self.record)
        extra_rank["state"]["skills"]["skills"]["unmapped skill"] = 1
        cases.append(("unsupported skill", extra_rank))
        conflicting_sheet = deepcopy(self.record)
        conflicting_sheet["sheet"]["skills"]["weapon_skills"]["Dagger"] = 3
        cases.append(("conflicting sheet", conflicting_sheet))
        missing_hp = deepcopy(self.record)
        del missing_hp["state"]["hps"]
        cases.append(("missing HP", missing_hp))
        unresolved_hp = deepcopy(self.record)
        unresolved_hp["state"]["hps"] = None
        cases.append(("unresolved HP", unresolved_hp))
        boolean_hp = deepcopy(self.record)
        boolean_hp["state"]["hps"] = True
        cases.append(("boolean HP", boolean_hp))
        negative_hp = deepcopy(self.record)
        negative_hp["state"]["hps"] = -1
        cases.append(("negative HP", negative_hp))
        fractional_hp = deepcopy(self.record)
        fractional_hp["state"]["hps"] = 23.0
        cases.append(("fractional HP", fractional_hp))
        conflicting_hp = deepcopy(self.record)
        conflicting_hp["sheet"]["hit_points"] += 1
        cases.append(("conflicting sheet HP", conflicting_hp))
        missing_sheet_hp = deepcopy(self.record)
        del missing_sheet_hp["sheet"]["hit_points"]
        cases.append(("missing sheet HP", missing_sheet_hp))
        boolean_sheet_hp = deepcopy(self.record)
        boolean_sheet_hp["sheet"]["hit_points"] = True
        cases.append(("boolean sheet HP", boolean_sheet_hp))

        for label, record in cases:
            with self.subTest(label=label):
                world = Universe("refusal", library=_library())
                before = set(world.object_registry.object_instances)
                with self.assertRaises(ValueError):
                    create_npcgen_v2_native_being(
                        world, json.dumps(record, separators=(",", ":")).encode("utf-8"))
                self.assertEqual(set(world.object_registry.object_instances), before)


if __name__ == "__main__":
    unittest.main()
