# U-NPC-BEING-005B — Measured native melee Reach at impact

## Result

Implemented the bounded Reach correction and verified native in-range and out-of-range outcomes. The original Arena's 1.5 m fixed hit was invalid for the imported NPC's measured Reach. No melee publisher or resolution-order change was needed: the native live and frozen transactional evaluators already check the supplied Reach against center distance at impact. The Arena had supplied an unsupported hardcoded `reach=2`.

## Changes

- Added shared `reference_arm_length_inches()` and `effective_melee_reach_meters()` helpers in [`src/melee_combat.py`](../../src/melee_combat.py). They use positive native Being dimensions, the adopted `15/37` personal-arm formula, native inch-valued weapon length, and convert the resulting sum to meters. Collision geometry is not a Reach input.
- Reused the helper in [`src/ai_duel.py`](../../src/ai_duel.py); the existing legacy replay Reach path remains unchanged.
- Updated the terminal and loopback Arena to supply the calculated Reach. Its explicitly authored positive scene is now 0.75 m center-to-center with separate 0.25 m spheres; the geometry is not inferred from the imported body dimensions.
- Expanded [`tests/test_npc_being_arena.py`](../../tests/test_npc_being_arena.py) and adjusted [`tests/test_npcgen_being_integration.py`](../../tests/test_npcgen_being_integration.py) and [`tests/test_npc_being_arena_web.py`](../../tests/test_npc_being_arena_web.py) for dimensional consistency and impact behavior.
- Updated [`TASKS.md`](../../TASKS.md) and [`docs/tasks/encounter-engine.md`](../tasks/encounter-engine.md) to mark only this bounded increment complete.

## Demonstrated behavior

The pinned Tobe fixture remains unchanged (SHA-256 `e59b55a6c22f822d65716215b64bccf0c1f2c7a42d49036092580d7c470241ae`). At 49.59000015258789 inches stature, personal arm length is about 20.104 inches. Adding the native 15-inch Dagger gives about 35.104 inches, or 0.8916 m. At 1.5 m, the Arena's former fixed hit exceeded that Reach and must not damage the target.

The revised positive native scene places the opponent at 0.75 m. The runnable Arena commits the Dagger thrust at boundary 4 with `normal` outcome, 4 causal body damage, target HP 10→6, and publisher receipts for boundaries 1–4. The separate 1.5 m case commits `out_of_reach`, records 1.5 m distance, applies no damage, preserves target HP 10 and does not advance RNG. Tests also move the target into range before impact and out of range before impact; the committed status follows the post-movement impact position.

## Verification

- Focused command, run from `tests/` with loopback permission for the browser tests:

  ```sh
  PYTHONPATH=..:../src:../examples python -m unittest \
    test_npc_being_arena test_npcgen_being_integration test_melee_combat \
    test_action_evaluation test_transactional_progression \
    test_ai_encounter.AIEncounterTest test_being test_weapon \
    test_npc_being_arena_web
  ```

  **170 tests passed in 33.780 seconds.** A sandboxed attempt could not bind the browser tests' IPv4 loopback server; the same focused command was rerun with loopback permission and passed.
- `printf '\n' | python examples/npc_being_arena.py` — completed with a native boundary-4 result: normal, distance 0.75 m, 4 body damage, target HP 6, receipts 1–4.
- `python -m py_compile` for all changed Python files — passed.
- `git diff --check` and staged-diff whitespace checks — passed.
- No full regression suite or long Ari/Bex persistence battery was run, per the assignment's bounded verification instructions.

## Scope limits and preservation

The general `TacticalDuel` constant, throwing/projectile calculations, the r61 rules documents, Arena browser endpoints, NPC source fixture, and fixed Ari/Bex persistence behavior are unchanged. This does not derive contact distance from sphere radii, change Action duration, or add first-strike behavior.

The repository was on `main` at `b2cb737fa1715c09d4ed8971e995b23abc120d54` before this increment, with an empty index and pre-existing user-managed documentation deletions plus untracked work. Those paths were not restored, staged, moved, or removed. Only the seven implementation/example/test files and the three task/report documentation files listed above are in this increment's commit scope. No push, reset, clean, stash, or full-suite run was performed.

## Commits

The implementation/test change and the task/report update are committed separately. The implementation commit is the parent of the documentation commit; see the delivery summary for both actual commit IDs. The report does not embed its own commit hash.
