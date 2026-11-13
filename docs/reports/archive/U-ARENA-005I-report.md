# U-ARENA-005I Engineering Report

## Outcome

Added explicit empty hand locations to the native Human and High elf Being
templates and verified they flow into ordinary generated Arena Being instances.
The player Character popup now reports hand occupancy from that Being's current
native state. Other templates retain their existing unrepresented state. The
005H authored Draw fixture now requires a free hand from native template state
and no longer replaces or injects `current.body_parts`.

No NPC Generator files, equipment defaults, hand-capacity rules, new Actions,
stowing behavior, or Encounter timing rules were changed. Ground Pick up still
transfers custody only; it leaves the Dagger carried and unready without adding
drawable-location evidence.

## Anatomy authority and native path

The native source is the existing `BeingDefinition.body_parts` map in
`src/config/beings.tsv`. Its definition-layer meaning is a declared native
location; a `null` value means the location is represented and empty. The
existing `BeingInstance` constructor copies that definition into the distinct
mutable `current.body_parts` occupancy state. This uses the native anatomy
representation rather than an Arena-only race lookup or a new metadata field.

The TSV now declares exactly `left hand: null` and `right hand: null` for the
`Human` and `High elf` definitions. All other template rows declare no body
locations. `BeingDictionary.load` parses and validates this optional JSON map.
The normal native construction path copies it through `BeingDefinition.copy`
and `BeingInstance`; the NPC Generator adapter also retains those template
locations while continuing to refuse malformed anatomy, template armor, or
occupied template references it cannot map. It does not derive anatomy from the
Generator's race label.

Direct native tests verify Human and High elf definitions and instances have
exactly the two empty hand slots, Skeleton remains unrepresented, and changes to
an instance copy do not mutate the template. A separately authored occupied
template reference remains intact through instance construction. Deterministic
normal Arena tests use fixed seeds that select Human and High elf and compare
their native hand slots, source-derived abilities, hit points, total XP,
stature, and body weight. No extra generation RNG draw or history event was
introduced.

The 005H opt-in fixture now checks that `right hand` already exists and is free
on the generated Being. It preserves the other declared hand and fails closed
if the generated native template has no free right hand. Existing Draw still
uses the same native Weapon ID and custody. The two-second boundary remains
unchanged: at +1 the Dagger is carried/unready with the hand empty; at +2 the
same object is readied, its weight is still counted once, and the native
drawable-source record is consumed atomically.

## Player view, observer boundary, and Pick up

The Character projection now includes an allowlisted `anatomy` value derived
from the player's `current.body_parts`. The shipped Character popup renders
each represented left/right hand as empty or shows the occupied Object's
observer-authorized display name and type. It never returns native Object IDs.
When neither supported hand key is represented, the view reports
`Unknown / not represented`; malformed or unresolved occupied state is shown
as unavailable. Opponent Entity projections do not gain anatomy, inventory, or
other private Character fields.

Ground Pick up regressions verify the Dagger becomes carried, its parent
container and identity remain native, its weight is counted, both represented
hands stay empty, and `native_weapon_draw_location` remains absent. The Action
catalog continues to refuse Draw specifically because Pick up did not provide
a drawable source. A free hand does not change that result.

The JavaScriptCore test executes the shipped page and verifies the Character
popup shows `left hand: empty` and, after native Draw resolves, the same Dagger
as the right-hand occupant. Native HTTP/session tests cover Generate, inspect,
Draw selection, +1/+2 progression, player-only state, ground Pick up, stale or
forged requests, and replacement atomicity. A real Chrome smoke was not
repeated for 005I; U-ARENA-005H's earlier real-browser Draw smoke preceded the
new general template hand declarations and popup rendering.

## Checkpoint boundary

No new serialized native fields or checkpoint inventories were introduced.
The strict initial Run/Spot reconstruction preflight now allows only an empty
subset of the explicitly named `left hand` and `right hand` locations; occupied
body-part references, armor, and unsupported locations remain refused. This is
limited to representing the new empty template state and does not enable
activated-Arena save/resume or broaden the Arena-state admission contract.

The adjacent `test_arena_state_admission` suite still reports 9 existing errors
at `arena_state_candidate.py:654` (`Encounter has an unrepresented native
field`), before this anatomy path is reached. The blocker is the existing strict
Encounter activation-field boundary (`arena_activation`,
`arena_activation_enabled`, and `arena_movement_activation`). No checkpoint
schema or activation allowlist was changed. Arena-local and S7 checkpoint
continuation suites were not rerun for this assignment.

## Verification

Commands ran from `tests/` with the installed sibling NPC Generator source on
`PYTHONPATH`.

| Command/check | Result |
|---|---|
| `PYTHONPATH=../src:../examples:.:<LOCAL_HOME_PATH> python -m unittest test_being.TestBeingDictionary.test_humanoid_templates_declare_hands_and_instances_copy_the_state test_being.TestBeingInstance.test_instance_preserves_template_body_part_state_without_aliasing test_arena_ready_weapon.TestArenaReadyWeapon.test_opt_in_authored_scenario_draws_as_first_choice_and_regenerates_cleanly test_arena_ready_weapon.TestArenaReadyWeapon.test_ordinary_generated_human_and_high_elf_use_native_hand_templates test_arena_ready_weapon.TestArenaReadyWeapon.test_ground_pickup_remains_carried_unreadied_and_does_not_create_draw_location -q` | **5 passed** in 1.311 s. |
| `PYTHONPATH=../src:../examples:.:<LOCAL_HOME_PATH> python -m unittest test_generated_arena_browser.TestGeneratedArenaBrowser.test_actual_shipped_javascript_runs_fresh_authored_draw_scenario test_generated_arena_browser.TestGeneratedArenaBrowser.test_http_visible_object_selection_pickup_and_custody_use_native_action -q` | **2 passed** in 2.087 s; includes shipped JavaScriptCore and native HTTP/session integration. |
| `PYTHONPATH=../src:../examples:.:<LOCAL_HOME_PATH> python -m unittest test_checkpoint_reconstruction test_checkpoint_inventory -q` | **38 passed** in 17.649 s. |
| Adjacent sweep: `PYTHONPATH=../src:../examples:.:<LOCAL_HOME_PATH> python -m unittest test_being test_npcgen_arena_adapter test_npcgen_being_integration test_arena_initialization test_arena_ready_weapon test_generated_arena_browser test_arena_ground_objects test_arena_ground_pickup test_arena_state_admission test_checkpoint_reconstruction test_checkpoint_inventory test_action_settlement test_atomic_publication test_interval_staging test_transactional_progression -q` | **363 tests; 354 passed, 9 errors** in 136.263 s. All 9 errors are the pre-existing `test_arena_state_admission` Encounter-field rejection described above; the other included modules passed. |
| `python -m py_compile src/being.py src/npcgen_arena_adapter.py src/arena_authored_draw_scenario.py src/arena_browser_session.py src/checkpoint_reconstruction.py examples/arena_web.py tests/test_being.py tests/test_arena_ready_weapon.py tests/test_generated_arena_browser.py` | Passed. |
| `git diff --check` | Passed. |

## Commits

- `aabc60c feat(being): declare native hand slots for supported templates`
- `aa09b60 feat(arena): show native hand occupancy in character sheet`
- This report is committed separately.

Unrelated pre-existing dirty files and deletions were left unstaged. No push was
performed.
