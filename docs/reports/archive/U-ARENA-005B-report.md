# U-ARENA-005B Engineering Report

## Result

Added a contextual Action selector to the player's Character popup. It shows all 53 entries from the checked-in `src/config/actions.tsv` plus three generated-Arena Actions (Run, Spot, and Pick up), for 56 potential Actions. Rows are grouped by target type and show one of `available`, `unavailable`, or `not implemented`, with a concise user-facing reason. The selector is scrollable, remembers whether it was expanded, and disables every row except a currently admitted Run or Pick up.

The catalog projection is rebuilt from current native session state for every response. It reads the TSV schema strictly, but does not treat a catalog label as evidence that an Action can execute. For Run, Spot, and Pick up it verifies the exact native scheduler preparer and transactional resolver registrations. The UI exposes Run only while it can be the first native player Choice. Spot is marked unavailable because generated Beings have no target geometry for the native resolver. Pick up availability is based on the selected observer-authorized Entity handle, current evidence, free ground state, same committed reference-point hex, Encounter activation, and the native PickUpAction scheduling path. Its read-only preflight is shared with the existing Object popup; submission still creates and schedules the native PickUpAction, and settlement remains in native Encounter advancement.

The browser has no generic Action submission endpoint. Ready weapon stays visibly disabled because initial readying timing and ready-state semantics are not adopted. Legacy Grab object is kept distinct from the adopted revision 64 Pick up Action. Throw explains that its existing native resolver has limited parameter requirements that this Arena does not collect. Other catalog rows explain that no complete generated-Arena client contract is connected. No combat, initial equipment distribution, initial readying, hand capacity, or new Action effects were added.

## Behavior and privacy

- Generate starts with Run available, Spot unavailable, and Pick up unavailable until a currently selected perceived ground Object satisfies the native preflight. Run becomes unavailable once an Action or movement activates the Encounter.
- Selecting a remote Object leaves Pick up unavailable with the same-hex reason. After committed movement into its hex, the selector and Object popup agree that Pick up is available. Selecting Pick up schedules the existing native Action; it becomes unavailable while resolving and after the Object is carried. The updated native inventory remains visible in the Character popup.
- The selector uses observer-owned current evidence and opaque handles. The target summary contains only the visible display name, generic type, and presence state. It does not return native IDs, generator records, opponent private state, receipts, or hidden Object information. No read-only projection advances native time, changes ChoiceBook state, updates evidence history, or consumes RNG.
- Entity inspection and selector use do not choose a map destination. Existing movement-rate and facing-policy synchronization, one-second native movement, terminal trace events, pickup, and inventory refresh remain on their established routes.
- Unsupported actions are disabled in the shipped page, and the backend has no `/api/generated/action` route that accepts caller-chosen catalog names. Forged or stale opaque handles are rejected by the existing Pick up endpoint and availability is refreshed from session state.

## Verification

The shipped generated-Arena JavaScript ran in the JavaScriptCore mock-DOM/fetch harness. The scenario opened the player's Character popup, checked the complete catalog and disabled unsupported rows, invoked Run through the selector and committed one native second, selected an Object without changing the movement destination, checked remote Pick up remained unavailable, moved to the Object, confirmed selector/Object-popup eligibility agreed, submitted Pick up through the selector, advanced one native second, and checked the carried inventory and post-pickup availability. The direct HTTP/session checks separately covered the authoritative catalog projection, read-only state, unknown generic-Action route, native Run, Pick up acceptance and settlement, and custody/inventory projection.

Commands and results:

- `PYTHONPATH=tests .venv/bin/python -m unittest test_generated_arena_browser` — **28 tests passed** in 7.765 seconds, including the shipped JavaScriptCore harness and native handler/session scenarios.
- `PYTHONPATH=tests .venv/bin/python -m unittest test_arena_ground_pickup` — **9 tests passed** in 5.977 seconds.
- `PYTHONPATH=tests .venv/bin/python -m unittest test_movement_intent test_action_choices` — **77 tests passed** in 4.383 seconds.
- `PYTHONPATH=tests .venv/bin/python -m unittest test_arena_acquisition_boundary` — **1 test passed** in 0.359 seconds.
- From `tests/`: `PYTHONPATH=../src:.. ../.venv/bin/python -m unittest test_perception` — **7 tests passed** in 0.046 seconds. It emitted environment warnings about pyenv shim permissions and the relative virtualenv prefix; the tests passed.
- `.venv/bin/python -m py_compile src/arena_browser_session.py examples/arena_web.py tests/test_generated_arena_browser.py tests/test_arena_acquisition_boundary.py tests/test_movement_intent.py` — passed.
- `git diff --check` — passed.

A separate visual browser smoke test was not run: the existing Chrome session had the user's Arena open on port 8000, and the shipped JavaScriptCore harness plus native HTTP/session coverage exercised the interaction without changing that live Encounter. For a manual macOS smoke on a separate port, run from the repository root:

```sh
PYTHONPATH=../npc-generator .venv/bin/python examples/generated_arena_browser.py --port 8001 --ground-loadout-profile tests/fixtures/arena/test_ground_loadout_profile.json
```

Then open `http://127.0.0.1:8001/`, generate the Encounter, open **Character → Actions**, select the fixture Dagger, move to its hex, and pick it up.

## Decisions still needed for initial weapon readying

U-ARENA-004V established that current transactional admission rejects the legacy `ready weapon` proposal and has no native initial-readying settlement. Revision 61's one-third-Action timing concerns re-readying after an attack; it does not define an initial carried-Dagger-to-readied-Dagger transition. A future implementation needs adopted decisions for:

1. Whether initial readiness is a distinct Action and what its duration/timing is, including when the committed transition becomes visible to simultaneous Actions.
2. The required preconditions and legal state transition: which carried weapons can be readied, what counts as a valid held/readied state, and how already-readied items behave.
3. The native representation of weapon-in-hand/readied state and its relationship to possession, equipment slots, weapon skill selection, checkpoint reconstruction, and observer projection.
4. Whether hands or other body parts have capacity constraints, how multiple weapons and shields contend for those slots, and what prerequisites follow. No hand/body-slot rule currently authorizes this Arena to decide those cases.
5. The native transactional contract: scheduler/Choice admission, reservation/contention behavior, Action resolution, and atomic state publication or rollback for a readying transition.

The next implementation milestone should adopt those decisions and add a native transactional readiness contract before enabling the selector row. Until then, the browser accurately presents it as not implemented.

## Commit and workspace disposition

- `0296400` — `Add native contextual Action selector to Arena`.
- The report is delivered separately; unrelated pre-existing deletions and untracked files remain untouched. No push was performed.
- No checkpoint suite or full repository suite was run; neither is in this assignment's focused verification scope.
