# U-ARENA-004Z Engineering Report

## Result

The generated Arena now returns an allowlisted `character` view of the controlled native Being in every active session response. The view is computed under `GeneratedArenaSession`'s lock and the Universe coordinated native read boundary. It is rebuilt from committed state on every response; there is no browser-owned inventory cache. The opposing Being still appears only through its observer-limited Entity evidence. No Reality/GM endpoint was added.

The browser displays an open-by-default, collapsible **Your Being — Character** panel after Generate and keeps it independent of selected map/list entities. It renders server-returned values with `textContent`. Each accepted state response redraws the sheet, so movement, pickup, rename, Run, Generate replacement, and other accepted server changes refresh it from the same committed view. Failed native advancement and failed Generate retain their prior native/session state and do not publish a speculative inventory change.

## Native field inventory and authority

| Character data | Native source and projection | Unsupported or deliberately un-derived |
|---|---|---|
| Name, type, race | Session player-name presentation field; `BeingInstance.current.obj_type` and `.race` | No NPC Generator source record or provenance is exposed. |
| Age and class/level allocation | Not represented in the native Arena Being | The `npcgen_arena_adapter` imports explicit supported measurements, abilities, skills, HP, race template, and total XP. It does not import age or class/level allocation. The sheet says these are unavailable. |
| Stature and body weight | Current native Being definition: `length` in inches and `weight` in pounds | Values are validated as finite and positive; no legacy feet values or raw Generator JSON are read. |
| Total XP | `BeingInstance.get_experience()` from current native definition state | Class-specific XP is not represented natively and is labeled unavailable. |
| Abilities | Current native ability dictionary, including `FIT`/Fitness | No new or derived ability scores. |
| Skill ranks and practice | Current native ordinary and weapon-skill maps; per-skill `BeingInstance.skill_experience` | Age-derived starting ranks remain ranks. No practice or training history is inferred; recorded practice XP is shown separately. |
| Condition | Current HP, native state map, posture, legacy fatigue level, and Q/B physical-fatigue reserves | The imported initial HP is not a modeled maximum; maximum HP is shown as unavailable. Q/B physiology is marked unresolved when there is no profile. The legacy discrete fatigue field is labeled separately from Q/B. |
| Position and movement | Current native Cartesian position in meters, hex reference-point occupancy, twelve-way facing, native posture, and accepted session movement plan | No browser speed formula or ETA. A rate is evaluated by the native movement engine at each committed boundary; the sheet displays category, policy, destination, and remaining distance only when a plan exists. No separate native encumbrance category is stored. |
| Inventory and equipment | Native `possessions`, `weapons`, current body-part references, current armor ID, registered `ObjectInstance`/`WeaponInstance`/`ArmorInstance` identities, current pound weights, and `parent_container_id` descendants | No inferred readiness or equipment. A picked-up weapon with no native held/body-part reference is “carried; not readied.” Native weapon body-part references are labeled held; armor IDs are labeled equipped armor; shield body-part references are identified as held shield references. |

Inventory resolves every ownership/equipment reference against the current Universe Object registry, checks custody and spatial state, validates native subtype/name/type/weight, traverses supported parent-container contents, and deduplicates aliases by native Object identity. Separate same-type Objects remain separate rows with separate opaque handles. If custody, registration, or weight is malformed, the sheet reports inventory as unavailable and shows no partial rows; it does not silently drop an Object. Session display-name overrides are applied only to projected names. Native IDs, source item IDs, and Generator bytes are omitted.

## Browser and transaction evidence

The explicit equipment fixture remains opt-in. The JavaScriptCore shipped-handler scenario generates at 10,000 XP on a 10×5 map, verifies an initial empty inventory and populated character groups, inspects the Dagger marker, renames it, clicks the background hex, changes the rate after the destination plan, serializes rate updates before Advance, and displays the exact native committed post-pickup projection after the one-second Pick up settles. It checks that the carried row retains the display name and says **carried; not readied**. The post-pickup UI fixture is taken from the same native session after its server-side movement and PickUpAction transaction; the browser event/fetch layer itself remains mocked.

Direct handler/session tests additionally verify exact native identity continuity, empty inventory before pickup, one matching inventory row after pickup, native weight and carried mass, unchanged armor/body-part/weapon-ready references, movement and inventory refresh after another committed step, and fail-closed output for a missing native reference or malformed weight. A rollback-injection test confirms the inventory projection remains unchanged after a failed publication and updates only after recovery and a later committed pickup. A two-Dagger test verifies same-type instances remain distinct. Read-only projection tests compare repeated results and confirm no change to Encounter time, simulation RNG, event history, or observer history; inspection of the opponent does not expose either Being's private character fields.

## Validation

- `PYTHONPATH=tests .venv/bin/python -m unittest test_generated_arena_browser test_arena_ground_pickup test_movement_intent test_arena_destination_movement_blocker test_generated_arena_spot_readiness` — **61 tests passed** in 17.765 seconds.
- `.venv/bin/python -m py_compile src/arena_browser_session.py examples/arena_web.py tests/test_generated_arena_browser.py tests/test_arena_ground_pickup.py tests/test_movement_intent.py tests/test_arena_destination_movement_blocker.py tests/test_generated_arena_spot_readiness.py` — passed.
- `git diff --check` — passed.

The prior U-ARENA-004Y run had three stale destination/Spot assertions: the generated destination route was expected to be absent and initial passive Awareness was expected to be empty. The test-only commit `cabda00` updates these assertions to the already adopted movement and r65 perception contracts. The affected five tests now pass within the 61-test command above; no production behavior was changed to satisfy the stale assumptions.

Activated-Arena checkpoint save/resume remains unsupported and fail-closed. The prior U-ARENA-004X checkpoint run recorded **39 tests: 31 passed, 6 errors, 2 failures**: six exact-closure refusals (`ArenaStateRejected: Encounter has an unrepresented native field`) and two HTTP continuation subprocesses that exited before readiness. This increment did not alter checkpoint serialization and did not rerun those suites.

No live browser/listener session is claimed. The shipped JavaScript was exercised through JavaScriptCore mock-DOM/fetch, and native mutations were exercised through direct handler/session tests. Please run the Mac smoke procedure below and check that the inventory appears after your real-browser pickup.

## Manual Mac smoke procedure

From the Universe repository root, launch the UI with the explicit test loadout:

```sh
ARENA_TRACE_UI=1 PYTHONPATH=../npc-generator .venv/bin/python examples/generated_arena_browser.py --ground-loadout-profile tests/fixtures/arena/test_ground_loadout_profile.json
```

Generate **10,000 XP / 10 columns / 5 rows**. Open **Your Being — Character** and confirm identity, abilities including Fitness, skills, total XP, current condition, native position/facing, and **No items carried**. Inspect and rename the visible Dagger, move into its hex, change Walk to Sprint after destination selection, and advance to exact arrival. Choose **Pick up** and advance one native second. Confirm the ground marker disappears and the same renamed Dagger appears once under **Carried Objects and equipment**, with status **carried; not readied** and its pound weight included in represented carried weight. Move again and confirm the character position updates while the inventory remains stable.

## Scope and commits

No NPC Generator files, combat or equipment rules, pickup/movement mechanics, default loadout, Being geometry, collision, perception rules, or checkpoint behavior were changed. Implementation is committed as `6a93613`; the independently tested obsolete-expectation update is `cabda00`. The next practical step is the manual browser smoke above, followed by any rule-backed additions to native character data only when the corresponding native fields are adopted and modeled.
