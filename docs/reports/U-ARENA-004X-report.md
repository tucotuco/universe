# U-ARENA-004X — engineering report

## Result

Implemented the revised Arena perception and pickup assignment. The generated browser now shows the other Being at time zero, and shows every realized ground Object from its native position, whether near or far. This applies equally when the normal generated Arena has no equipment. The browser draws Beings as circles and Objects as triangles, lists their perceptible name/type/current state, and supports clicking a marker or list entry to inspect it.

The user-adopted rule is recorded as Encounter revision 65 in [the decision supplement](../encounters/encounters-consistency-decisions-r65.md), indexed from the [Encounter README](../encounters/README.md), and described in [the Arena perception design note](../design/generated-arena-perception.md). It supersedes the limited ground-Object discovery proposal. Revision 64's separate same-hex pickup access rule remains in force.

## Native evidence and transaction path

- Private Arena candidate creation seeds a separate observer-owned `ArenaPerceptionLedger` for each Being and initializes native `Encounter.awareness` for the other Being and each realized Object. This occurs at `t=0` without an Action, Spot roll, time advance, or game RNG draw.
- The ledger stores only observer/entity identity internally, perceptible name/type, current Cartesian position/present state, evidence basis, and boundary/time. Being type is projected as the generic “Being” so race/class data is not exposed. The browser reads the player ledger only; internal IDs and source/provenance data are replaced with session-local opaque handles.
- Native interval publication refreshes evidence in its observer phase from the common post-movement snapshot. Movement position changes and pickup custody changes publish atomically with the evidence. A carried Object remains in observation history and the visible entity list with no position, so its old ground marker disappears. Evidence is appended only for material changes, not repeated reads or unchanged boundaries. A failed interval leaves current evidence/history and public state unchanged.
- The Pick up button resolves an opaque handle through current player evidence, rechecks native Object type, custody, geometry state, position, and same-hex access, then submits the existing `PickUpAction` through the Encounter `ChoiceBook`. One native second settles it. No readying, equipping, hand-capacity, collision, or body-geometry behavior was added. Existing movement and carried-weight calculation remain native.
- A later nonempty geometry/occlusion model is not treated as clear visibility. The initial candidate rejects it, and a later boundary with added geometry fails closed before publication.

## Browser and tracing

The shipped page now draws and selects visible entity markers and lists, displays inspect details, enables Pick up only for an eligible same-hex ground Object, and reports the accepted/resolved native Action outcome. The route accepts only an opaque handle. Terminal tracing includes entity selection and pickup clicks plus server acceptance/refusal; traces can show perceptible item name/type but omit native IDs and Generator source identifiers.

Equipment remains opt-in. From the repository root, launch the generated shell with the authored test profile and tracing using:

```sh
PYTHONPATH=../npc-generator .venv/bin/python examples/generated_arena_browser.py --ground-loadout-profile tests/fixtures/arena/test_ground_loadout_profile.json --trace-ui
```

The normal launcher path still has no default gear, and Generate still accepts only starting XP and map dimensions. No NPC Generator source was changed. A real browser/listener smoke test was not completed: the checkpoint HTTP subprocess tests exited before emitting their readiness line in this environment. The shipped JavaScript was instead exercised through the JavaScriptCore mock-DOM/fetch harness, and the server routes through direct HTTP-handler tests; this report does not claim a real-browser run.

## Validation

- `python -m py_compile` over all changed Python modules and tests: passed.
- `PYTHONPATH=tests .venv/bin/python -m unittest test_arena_ground_pickup test_generated_arena_browser test_arena_ground_objects test_movement_intent -v`: **57 passed in 14.274 s**. This includes the shipped JS event harness, direct HTTP inspection/pickup, native pickup contention/rollback, movement while carrying, initial observer isolation, no-default-equipment visibility, and fail-closed geometry behavior.
- After the final stale-position validation was added, the two directly affected pickup tests passed: **2 passed in 1.173 s**.
- Adjacent command `PYTHONPATH=tests .venv/bin/python -m unittest test_interval_staging test_atomic_publication test_transactional_progression test_movement_intent test_arena_hex_map test_arena_ground_objects -v`: **214 passed in 80.189 s** before the final stale-position guard; the two directly affected pickup tests then passed afterward.
- `git diff --check` and `git diff --cached --check`: passed.
- Checkpoint command `PYTHONPATH=tests .venv/bin/python -m unittest test_checkpoint_inventory test_arena_local_checkpoint test_arena_s7_checkpoint -v`: **39 tests in 21.938 s; 31 passed, 6 errored, 2 failed**. Six Arena local/S7 capture cases refuse at the existing exact-closure check with `ArenaStateRejected: Encounter has an unrepresented native field` (the prior Arena activation/Encounter closure remains unsupported; the new per-Being perception ledger is also intentionally not serialized). The two HTTP continuation cases exited their subprocess before readiness output. No checkpoint inventory or serializer was broadened, so those paths remain fail-closed.

## Recommendation and commit

The next perception slice should wait until an obstruction/occlusion contract is adopted for Arena terrain. The current explicit open premise is implemented and other geometry fails closed; there is no inferred visibility through unknown geometry. Continue to keep pickup accessibility separate from discovery and do not add weapon readiness without its own adopted state/rule.

Implementation and rule/design changes: `850c887` (`Add native Arena perception and browser pickup`). This report is committed separately. No push was performed.
