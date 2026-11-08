"""Versioned combined checkpoint for one pristine native Being binding.

This is deliberately separate from the reproduction-only format: the latter
continues to reject a world whose logical Person IDs overlap native Objects.
The combined format supports one explicitly authored, otherwise untouched
Being and is not general Universe or Being persistence.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from being import BeingDefinition, BeingInstance
from abilities import Abilities
from skill import Skills
from speeds import Speed
from states import States
from strategy import Strategy
from exertion import Exertion
from physical_fatigue import PhysicalFatigueState

from reproduction_being_bridge import (
    ReproductionBeingBridgeError, _NativeBeingBindingRecord, _definition_signature,
)
from reproduction_checkpoint import (
    CHECKPOINT_SCHEMA as REPRODUCTION_SCHEMA,
    CHECKPOINT_VERSION as REPRODUCTION_VERSION,
    REGISTRY_CONTRACT, ReproductionCheckpointValidationError,
    _canonical as _reproduction_canonical, _registry_data,
    decode_reproduction_checkpoint, restore_reproduction_checkpoint,
    logical_reproduction_checkpoint_digest,
)


COMBINED_SCHEMA = "universe-reproduction-native-being-checkpoint"
COMBINED_VERSION = 3
LEGACY_COMBINED_VERSION = 1
PREVIOUS_COMBINED_VERSION = 2
BEING_CONTRACT = "authored-pristine-being-instance/1"
_RESTORE_PHASES = (
    "reproduction_groups", "reproduction_indexes", "reproduction_aliases", "reproduction_authored_requests",
    "reproduction_v1_records", "reproduction_v2_records", "reproduction_revision",
    "reproduction_consistency", "reproduction_complete", "object_registry",
    "binding_index", "request_index", "combined_consistency",
)


class CombinedBeingCheckpointError(ValueError):
    """Malformed, unsupported, stale, or incompatible combined checkpoint."""


class InjectedCombinedBeingCheckpointFailure(RuntimeError):
    """Private deterministic fault injection for combined restore."""


@dataclass(frozen=True)
class DetachedCombinedBeingCheckpoint:
    reproduction_checkpoint: str
    person_id: str
    name: str
    request_key: str
    definition_json: str
    wire_version: int = COMBINED_VERSION


def _fail(message):
    raise CombinedBeingCheckpointError(message)


def _strict(value, fields, label):
    if type(value) is not dict or set(value) != set(fields):
        _fail(f"{label} has missing or unknown fields")
    return value


def _reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=True,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise CombinedBeingCheckpointError(f"combined checkpoint is not closed JSON data: {exc}") from exc


def _definition_data(definition):
    if type(definition) is not BeingDefinition:
        _fail("only an exact native BeingDefinition is supported")
    try:
        return json.loads(_definition_signature(definition))
    except (ReproductionBeingBridgeError, json.JSONDecodeError) as exc:
        raise CombinedBeingCheckpointError(f"Being definition is not supported closed authored data: {exc}") from exc


def _definition_from_data(data):
    keys = {
        "obj_type", "length", "width", "height", "weight", "cost", "hardness",
        "hit_points", "is_magical", "tags", "weapon_categories", "discovery_dc",
        "race", "experience", "hit_dice", "alignment", "armor_class",
        "challenge_rating", "max_speed", "abilities", "skills", "senses",
        "vulnerabilities", "resistances", "immunities", "languages", "psionics",
        "spells", "traits", "states", "actions", "reactions", "body_parts",
        "armor_id", "physiology_id",
    }
    row = _strict(data, keys, "Being definition")
    speed = _strict(row["max_speed"], {"speeds"}, "Being speed")
    abilities = _strict(row["abilities"], {"abilities"}, "Being abilities")
    skills = _strict(row["skills"], {"skills", "weapon_skills"}, "Being skills")
    states = _strict(row["states"], {"states"}, "Being states")
    speed_values = _strict(
        speed["speeds"], {"ambulate", "burrow", "climb", "fly", "swim"}, "Being speed values"
    )
    ability_values = _strict(
        abilities["abilities"], {"STR", "DEX", "CON", "INT", "WIS", "CHA", "FIT"},
        "Being ability values",
    )
    for label, values in (("speed", speed_values), ("ability", ability_values)):
        if any(type(value) is not int or value < 0 for value in values.values()):
            _fail(f"Being {label} values must be nonnegative native integers")
    for label in ("skills", "weapon_skills"):
        values = skills[label]
        if type(values) is not dict or any(
                type(name) is not str or not name.strip()
                or type(level) is not int or level < 0 for name, level in values.items()):
            _fail("Being skill maps must contain named nonnegative integer levels")
    state_values = states["states"]
    if type(state_values) is not dict or any(
            type(name) is not str or not name.strip() or type(value) is not bool
            for name, value in state_values.items()):
        _fail("Being state map must contain named Boolean values")
    native_speed, native_abilities, native_skills, native_states = Speed(), Abilities(), Skills(), States()
    native_speed.speeds = speed["speeds"]
    native_abilities.abilities = abilities["abilities"]
    native_skills.skills = skills["skills"]
    native_skills.weapon_skills = skills["weapon_skills"]
    native_states.states = states["states"]
    try:
        definition = BeingDefinition(
            row["obj_type"], row["length"], row["weight"], row["hit_points"],
            row["hit_dice"], row["alignment"], row["armor_class"], row["challenge_rating"],
            row["width"], row["height"], row["cost"], row["hardness"], row["is_magical"],
            row["tags"], row["weapon_categories"], row["experience"], native_speed,
            native_abilities, native_skills, row["senses"], row["vulnerabilities"],
            row["resistances"], row["immunities"], row["languages"], row["psionics"],
            row["spells"], row["traits"], native_states, row["actions"], row["reactions"],
            row["body_parts"], row["armor_id"], row["physiology_id"], row["race"],
            row["discovery_dc"],
        )
    except Exception as exc:
        raise CombinedBeingCheckpointError(f"native BeingDefinition reconstruction refused: {exc}") from exc
    if _canonical(_definition_data(definition)) != _canonical(data):
        _fail("Being definition does not round-trip through reviewed native construction")
    return definition


def _instance_signature(being):
    """Closed semantic signature of fields relevant to the pristine contract."""
    if type(being) is not BeingInstance:
        _fail("combined checkpoint supports exactly one native BeingInstance")
    expected_fields = {
        "id", "name", "type", "top_facing", "front_facing", "hex_facing", "original", "current",
        "parent_container_id", "spatial_state", "geometry", "visual_occlusion",
        "possessions", "weapons", "strategy", "physical_fatigue", "physiology_id",
        "fatigue_level", "effective_fitness", "exertion", "skill_experience",
        "skill_use_history", "_skill_practice_baselines", "personal_history", "_posture",
    }
    if set(being.__dict__) != expected_fields:
        _fail("Being has unknown or missing instance state")
    original = _definition_data(being.original)
    current = _definition_data(being.current)
    if original != current:
        _fail("only an unmodified authored Being definition is supported")
    if not isinstance(being.name, str) or not being.name.strip():
        _fail("a nonempty authored Being name is required")
    if type(being.id) is not str or not being.id:
        _fail("native Being ID must be a nonempty string")
    if (type(being.type) is not str or being.type != "BeingInstance"
            or type(being.top_facing) is not int or being.top_facing != 0
            or type(being.front_facing) is not int or being.front_facing != 1
            or being.hex_facing is not None
            or being.get_posture() is not None
            or being.parent_container_id is not None or being.spatial_state is not None
            or being.geometry is not None or being.visual_occlusion is not None
            or type(being.possessions) is not list or being.possessions != []
            or type(being.weapons) is not list or being.weapons != []):
        _fail("only a pristine, unplaced, unequipped Being with unknown hex facing is supported")
    if (type(being.strategy) is not Strategy
            or _canonical(being.strategy.__dict__) != _canonical(Strategy().__dict__)):
        _fail("modified or unsupported Being strategy is outside this checkpoint")
    if type(being.physical_fatigue) is not PhysicalFatigueState or being.physical_fatigue != PhysicalFatigueState():
        _fail("modified physical fatigue is outside this checkpoint")
    if (being.physiology_id != being.original.physiology_id
            or type(being.fatigue_level) is not int or being.fatigue_level != 0
            or type(being.effective_fitness) is not type(being.current.FIT())
            or being.effective_fitness != being.current.FIT()):
        _fail("modified fatigue or fitness state is outside this checkpoint")
    if (type(being.exertion) is not Exertion
            or _canonical(being.exertion.__dict__) != _canonical(Exertion().__dict__)):
        _fail("modified or unsupported exertion is outside this checkpoint")
    if (type(being.skill_experience) is not dict or being.skill_experience != {}
            or type(being.skill_use_history) is not list or being.skill_use_history != []
            or type(being._skill_practice_baselines) is not dict
            or being._skill_practice_baselines != {} or being.personal_history is not None):
        _fail("Being practice or personal history is outside this checkpoint")
    return {
        "id": being.id, "name": being.name, "type": being.type,
        "original_definition": original, "current_definition": current,
        "state_contract": BEING_CONTRACT,
    }


def _nested_reproduction_checkpoint(registry):
    from reproduction_checkpoint import CHECKPOINT_SCHEMA, CHECKPOINT_VERSION
    payload = _registry_data(registry)
    envelope = {
        "schema": CHECKPOINT_SCHEMA,
        "version": CHECKPOINT_VERSION,
        "registry_contract": REGISTRY_CONTRACT,
        "source_world_identity": registry.world_identity,
        "payload": payload,
    }
    envelope["sha256"] = hashlib.sha256(_reproduction_canonical(envelope).encode("ascii")).hexdigest()
    text = json.dumps(envelope, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + "\n"
    decode_reproduction_checkpoint(text)
    return text


def _bound_being(world):
    registry = world._reproduction_group_registry
    registry._assert_consistent()
    if len(registry._native_beings_by_person_id) != 1 or len(registry._native_being_requests) != 1:
        _fail("combined checkpoint supports exactly one native Being binding")
    if len(world.object_registry.object_instances) != 1:
        _fail("combined checkpoint refuses unrelated or unsupported native Objects")
    person_id, being = next(iter(registry._native_beings_by_person_id.items()))
    request_key, record = next(iter(registry._native_being_requests.items()))
    if (world.get_object_by_id(person_id) is not being or record.being is not being
            or record.person_id != person_id or record.request_key != request_key):
        _fail("native Being binding references are inconsistent")
    signature = _instance_signature(being)
    if person_id not in registry._group_id_by_offspring:
        _fail("bound Being is not an established logical offspring")
    all_request_keys = (set(registry._requests) | set(registry._generation_requests)
                        | set(registry._progressive_requests))
    if request_key in all_request_keys:
        _fail("native binding request collides with reproduction request identity")
    expected_normalized = (person_id, being.name, _definition_signature(being.original))
    if record.normalized_request != expected_normalized:
        _fail("native binding request does not match the Being's authored definition")
    return person_id, being, request_key, signature


def encode_combined_being_checkpoint(world) -> str:
    """Export one native Being plus its complete reproduction registry."""
    from encounter import Encounter
    from transactional_progression import is_quarantined
    with world._schedule_lock:
        if is_quarantined(world):
            _fail("quarantined Universes cannot export combined checkpoints")
        if (world._choice_books or set(world.event_history) != {"0"}
                or any(isinstance(event, Encounter) for event in world.event_history.values())):
            _fail("combined checkpoint is a no-Encounter world-only format")
        registry = world._reproduction_group_registry
        if registry._world is not world:
            _fail("reproduction registry ownership is inconsistent")
        person_id, being, request_key, state = _bound_being(world)
        reproduction = _nested_reproduction_checkpoint(registry)
        envelope = {
            "schema": COMBINED_SCHEMA,
            "version": COMBINED_VERSION,
            "being_contract": BEING_CONTRACT,
            "reproduction_checkpoint": reproduction,
            "being": {
                "person_id": person_id,
                "name": being.name,
                "request_key": request_key,
                "definition": state["original_definition"],
                "state": state,
            },
        }
        envelope["sha256"] = hashlib.sha256(_canonical(envelope).encode("ascii")).hexdigest()
        text = json.dumps(envelope, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + "\n"
        decode_combined_being_checkpoint(text)
        return text


def decode_combined_being_checkpoint(text) -> DetachedCombinedBeingCheckpoint:
    if type(text) is not str:
        _fail("combined checkpoint input must be text")
    try:
        envelope = json.loads(text, object_pairs_hook=_reject_duplicates)
    except CombinedBeingCheckpointError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise CombinedBeingCheckpointError(f"combined checkpoint JSON is invalid: {exc}") from exc
    _strict(envelope, {"schema", "version", "being_contract", "reproduction_checkpoint", "being", "sha256"},
            "combined envelope")
    if (envelope["schema"] != COMBINED_SCHEMA or type(envelope["version"]) is not int
            or envelope["version"] not in (LEGACY_COMBINED_VERSION, PREVIOUS_COMBINED_VERSION, COMBINED_VERSION)):
        _fail("unsupported combined checkpoint schema or version")
    if envelope["being_contract"] != BEING_CONTRACT:
        _fail("unsupported native Being reconstruction contract")
    unsigned = {key: value for key, value in envelope.items() if key != "sha256"}
    digest = hashlib.sha256(_canonical(unsigned).encode("ascii")).hexdigest()
    if type(envelope["sha256"]) is not str or envelope["sha256"] != digest:
        _fail("combined checkpoint digest mismatch; digest is corruption detection, not authentication")
    if type(envelope["reproduction_checkpoint"]) is not str:
        _fail("embedded reproduction checkpoint must be text")
    try:
        reproductive = decode_reproduction_checkpoint(envelope["reproduction_checkpoint"])
    except ReproductionCheckpointValidationError as exc:
        raise CombinedBeingCheckpointError(f"embedded reproduction checkpoint refused: {exc}") from exc
    expected_reproduction_version = envelope["version"]
    if reproductive.wire_version != expected_reproduction_version:
        _fail("combined and embedded reproduction checkpoint versions are incompatible")
    row = _strict(envelope["being"], {"person_id", "name", "request_key", "definition", "state"}, "Being record")
    for name in ("person_id", "name", "request_key"):
        if type(row[name]) is not str or not row[name].strip():
            _fail(f"Being {name} must be nonempty text")
    if row["person_id"] not in dict(reproductive.group_id_by_offspring):
        _fail("native Being identity is not a referenced published offspring")
    keys = ({key for key, _norm, _result in reproductive.authored_requests}
            | {key for key, _norm, _inputs, _result in reproductive.generation_requests}
            | {key for key, _norm, _inputs, _result in reproductive.progressive_requests})
    if row["request_key"] in keys:
        _fail("native binding request key collides with a reproduction request")
    definition = _definition_from_data(row["definition"])
    if type(row["state"]) is not dict:
        _fail("Being state record must be an object")
    expected = {
        "id": row["person_id"], "name": row["name"], "type": "BeingInstance",
        "original_definition": _definition_data(definition),
        "current_definition": _definition_data(definition),
        "state_contract": BEING_CONTRACT,
    }
    if _canonical(row["state"]) != _canonical(expected):
        _fail("Being state is not the supported pristine authored state")
    if not row["person_id"] or not row["name"]:
        _fail("Being identity and name are required")
    return DetachedCombinedBeingCheckpoint(
        envelope["reproduction_checkpoint"], row["person_id"], row["name"], row["request_key"],
        _canonical(row["definition"]), envelope["version"],
    )


def restore_combined_being_checkpoint(world, checkpoint, *, _fail_after=None):
    """Atomically restore the reproduction registry and one real native Being."""
    if type(checkpoint) is str:
        candidate = decode_combined_being_checkpoint(checkpoint)
    elif type(checkpoint) is DetachedCombinedBeingCheckpoint:
        # Frozen Python records are still constructible by callers. Re-run the
        # complete wire validator instead of treating the record's type as a
        # proof that it came from the decoder.
        try:
            definition_data = json.loads(checkpoint.definition_json)
            state = {
                "id": checkpoint.person_id, "name": checkpoint.name, "type": "BeingInstance",
                "original_definition": definition_data, "current_definition": definition_data,
                "state_contract": BEING_CONTRACT,
            }
            envelope = {
                "schema": COMBINED_SCHEMA, "version": checkpoint.wire_version,
                "being_contract": BEING_CONTRACT,
                "reproduction_checkpoint": checkpoint.reproduction_checkpoint,
                "being": {"person_id": checkpoint.person_id, "name": checkpoint.name,
                          "request_key": checkpoint.request_key,
                          "definition": definition_data, "state": state},
            }
            envelope["sha256"] = hashlib.sha256(_canonical(envelope).encode("ascii")).hexdigest()
            candidate = decode_combined_being_checkpoint(json.dumps(envelope, sort_keys=True))
        except CombinedBeingCheckpointError:
            raise
        except Exception as exc:
            raise CombinedBeingCheckpointError(f"detached combined checkpoint is malformed: {exc}") from exc
    else:
        _fail("restore requires validated detached combined checkpoint data")
    if _fail_after is not None and _fail_after not in _RESTORE_PHASES:
        _fail("unknown combined restore fault phase")
    definition = _definition_from_data(json.loads(candidate.definition_json))
    being = BeingInstance(definition, name=candidate.name, id=candidate.person_id)
    if _canonical(_instance_signature(being)) != _canonical({
            "id": candidate.person_id, "name": candidate.name, "type": "BeingInstance",
            "original_definition": _definition_data(definition),
            "current_definition": _definition_data(definition), "state_contract": BEING_CONTRACT}):
        _fail("native Being constructor does not reproduce the supported checkpoint state")

    from reproduction_checkpoint import _compatible_context
    with world._schedule_lock:
        registry = _compatible_context(world, require_empty=True)
        undo = registry._capture_undo()
        object_map = world.object_registry.object_instances
        objects_before = dict(object_map)
        try:
            repro_phase = _fail_after.removeprefix("reproduction_") if _fail_after in {
                "reproduction_groups", "reproduction_indexes", "reproduction_aliases", "reproduction_authored_requests",
                "reproduction_v1_records", "reproduction_v2_records", "reproduction_revision",
                "reproduction_consistency"} else None
            restore_reproduction_checkpoint(world, candidate.reproduction_checkpoint, _fail_after=repro_phase)
            if _fail_after == "reproduction_complete":
                raise InjectedCombinedBeingCheckpointFailure("injected failure after reproduction restoration")
            if world.get_object_by_id(candidate.person_id) is not None:
                _fail("native identity collided after reproduction registry restore")
            world.object_registry.add_object(being)
            if world.get_object_by_id(candidate.person_id) is not being:
                _fail("native ObjectRegistry refused reconstructed Being")
            if _fail_after == "object_registry":
                raise InjectedCombinedBeingCheckpointFailure("injected failure after ObjectRegistry publication")
            registry._native_beings_by_person_id[candidate.person_id] = being
            if _fail_after == "binding_index":
                raise InjectedCombinedBeingCheckpointFailure("injected failure after native binding publication")
            normalized = (candidate.person_id, candidate.name, _definition_signature(definition))
            registry._native_being_requests[candidate.request_key] = _NativeBeingBindingRecord(
                candidate.request_key, candidate.person_id, normalized, being,
            )
            if _fail_after == "request_index":
                raise InjectedCombinedBeingCheckpointFailure("injected failure after native request publication")
            registry._assert_consistent()
            if _fail_after == "combined_consistency":
                raise InjectedCombinedBeingCheckpointFailure("injected failure after combined consistency validation")
        except BaseException as exc:
            object_map.clear()
            object_map.update(objects_before)
            registry._restore_undo(undo)
            if isinstance(exc, InjectedCombinedBeingCheckpointFailure):
                raise
            if _fail_after is not None and _fail_after.startswith("reproduction_"):
                raise InjectedCombinedBeingCheckpointFailure(
                    f"injected combined rollback through embedded reproduction phase {_fail_after}"
                ) from exc
            raise CombinedBeingCheckpointError(f"combined restoration rolled back: {exc}") from exc
    return being


def combined_being_checkpoint_digest(checkpoint_text: str) -> str:
    candidate = decode_combined_being_checkpoint(checkpoint_text)
    return hashlib.sha256(_canonical({
        "reproduction_digest": logical_reproduction_checkpoint_digest(candidate.reproduction_checkpoint),
        "person_id": candidate.person_id, "name": candidate.name,
        "request_key": candidate.request_key, "definition": json.loads(candidate.definition_json),
    }).encode("ascii")).hexdigest()
