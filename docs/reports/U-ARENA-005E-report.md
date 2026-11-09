# U-ARENA-005E — historical native initial weapon-readying implementation

> **Superseded by U-ARENA-005F.** This report's original claim that the user approved a universal one-second initial Ready weapon Action was incorrect. The user challenged that duration and did not approve the revision-66 weapon-readying proposal. Revision 61 governs: ordinary drawing is normally two seconds, post-strike re-readying is weapon-motion-specific, and other retrieval/preparation is variable. The browser now fails closed because native custody does not identify a drawable location. This document below records the implementation and tests as they existed at the time, not current adopted behavior.

## Result and rule authority

At the time, I recorded the bounded Arena implementation in a revision-66 supplement and described it as adopted. That authority statement was incorrect. Revision 66 is now corrected as a non-adopted implementation proposal. Its one-second initial-readying timing was wrong; the hand and contention provisions were also not independently adopted. The previously implemented transactional machinery remains in code but the Arena browser disables the Action while drawable-location state is absent.

The first supported weapon is the native ordinary Dagger. The Being must already possess that exact WeaponInstance. The browser requires the player to select an explicitly represented `left hand` or `right hand` whose native body-part slot is empty. The current model has no independent per-hand function flag; the implementation uses only a present empty native hand slot, which is the evidence available to existing native hand-use logic. No hand is inferred from race or presentation.

## Native implementation

`ReadyWeaponAction` has an exact Action type, integer start second, one-second duration, native Choice scheduling, and an explicit hand field covered by Choice declaration validation. Snapshot evaluation checks positive HP and native helplessness, exact Dagger type, actor possession, container custody, absence from held/readied references, and the selected free hand. Unsupported or stale eligibility produces an ordinary no-transition outcome. The resolver consumes no RNG.

A typed `ReadyWeaponEffect` is reconciled against the common pre-Action snapshot. Duplicate eligible claims for the same actor hand or Weapon make every conflicting claim `contested`. Atomic publication revalidates custody and hand state, then appends the same Weapon ID to `Being.weapons` and writes that ID into the selected `Being.current.body_parts` slot. Possession, parent custody, spatial state, and weight do not change. Post-write checks and committed inspection validate the same identity and native references. The Choice and interval publication systems retain their existing rollback and retry behavior.

The player's character sheet derives readiness from native body-part state and shows `readied in right hand`; the carried Object remains in `possessions`. Inventory and movement encumbrance count the Object once across possession, weapon, and hand references. The browser Action selector supplies the opaque Object handle and explicit free-hand choice. The server rechecks all prerequisites. The Action result remains player-only; the opponent's inventory and equipment are not projected. Terminal tracing records the UI request, accepted hand choice, and committed outcome without printing native IDs or Generator provenance.

## End-to-end demonstration

The deterministic test profile creates one native ground Dagger and uses a positive-HP generated Being. The test world explicitly adds `right hand: None` to the player's existing native body-part map; it does not add hand state to Arena generation. The shipped JavaScriptCore harness then runs the browser sequence: select the Dagger's hex, advance native movement, Pick up, see the carried-only inventory state, choose `right hand`, submit Ready weapon, advance one second, and see `readied in right hand` in the open character popup. A separate HTTP handler/session integration test performs the real server request and native publication.

The committed before/after state is:

| State | `possessions` | `weapons` | `body_parts` | Dagger custody / weight |
|---|---|---|---|---|
| After Pick up | same Dagger ID | empty | `right hand: None` | parent is player; 1 lb |
| After Ready | same Dagger ID | same Dagger ID | `right hand: same Dagger ID` | parent is player; 1 lb |

The native `armed_with` view sees the Dagger only after Ready commits. A same-boundary strike cannot use the uncommitted Ready: native strike scheduling refuses the Dagger while the pre-Action state still has an empty hand. No attack, armor, or shield effect is applied by Ready.

## Cases and boundaries verified

- Ground or unselected Objects cannot be readied; the ordinary browser flow requires Pick up first.
- A missing, occupied, or non-left/right hand is unavailable. A non-Dagger Weapon is outside this first supported mapping.
- A downed Being is unavailable for voluntary Ready.
- Two simultaneous same-Weapon/same-hand claims both settle `contested`; neither changes the hand or weapon list.
- Withdrawing the accepted Choice before it starts leaves the Weapon carried and unready.
- An injected publication failure after target writes rolls back hand, weapon list, time, RNG, inventory, and custody; explicit recovery and retry commit once.
- Revision-65 player and opponent perception ledgers remain observer-owned. The player's sheet shows only the player's equipment.
- No body geometry, collision, hand inference, default equipment, weapon-readying combat effect, or checkpoint support was added. NPC Generator source was not modified.

## Generated-template limitation

The installed NPC Generator import and current Arena initialization produce empty `Being.current.body_parts` maps for the generated Human/High Elf candidates. The task prohibits synthesizing hands from race or appearance, so a normally generated Arena currently presents Ready weapon as unavailable. The browser enables it only when native state already contains a supported empty hand slot. The successful browser test supplies that slot as an explicitly authored test-world premise. Adding authoritative hand state to generated Being templates requires a separate native data/rules decision.

## Revision-65 test correction

The stale time-zero Awareness expectation in `test_arena_initialization.py` was corrected in its own commit. For both XP 0 and XP 12,000 subcases the test now asserts reciprocal native Awareness and separate observer-owned evidence containing only the other Being. No production initialization behavior changed.

## Validation

Python import path for these commands includes the sibling, read-only `<LOCAL_HOME_PATH>` checkout because `npcgen` is not installed into the default interpreter.

- `PYTHONPATH=<LOCAL_HOME_PATH>:$PYTHONPATH python -m py_compile src/activities.py src/action_evaluation.py src/action_settlement.py src/observer_proposals.py src/interval_staging.py src/atomic_publication.py src/scheduling.py src/action_choice.py src/transactional_progression.py src/encounter_inspection.py src/arena_browser_session.py src/arena_ui_trace.py examples/arena_web.py tests/test_arena_ready_weapon.py tests/test_generated_arena_browser.py` — passed.
- `PYTHONPATH=<LOCAL_HOME_PATH>:$PYTHONPATH python -m unittest tests.test_arena_ready_weapon tests.test_arena_ground_pickup tests.test_generated_arena_browser tests.test_arena_initialization -q` — **53 tests passed in 19.517 s**. This includes the shipped JavaScriptCore interaction on macOS, HTTP/session wiring, native Pick up, Ready, rollback/retry, contention, movement, and the two corrected Awareness subcases.
- After the final armor-custody eligibility guard, `PYTHONPATH=<LOCAL_HOME_PATH>:$PYTHONPATH python -m unittest tests.test_arena_ready_weapon tests.test_generated_arena_browser -q` — **37 tests passed in 12.551 s**.
- `PYTHONPATH=<LOCAL_HOME_PATH>/src:<LOCAL_HOME_PATH>/examples:<LOCAL_HOME_PATH>/tests:<LOCAL_HOME_PATH> python -m unittest test_action_settlement test_atomic_publication test_interval_staging test_transactional_progression test_checkpoint_inventory test_checkpoint_choice_descriptors -q` — **268 tests passed in 94.396 s**.
- `PYTHONPATH=<LOCAL_HOME_PATH>:$PYTHONPATH python -m unittest tests.test_arena_local_checkpoint tests.test_arena_s7_checkpoint -q` — **9 tests run; 6 errors and 2 failures**. Six checkpoint candidate cases stop at `arena_state_candidate.py:654` with `ArenaStateRejected: Encounter has an unrepresented native field`; inspection identifies the unlisted native fields as `arena_activation`, `arena_activation_enabled`, and `arena_movement_activation`. The two multiprocess continuation cases exit during server startup with exit code 1 and no captured output. These are existing activation/checkpoint inventory gaps; I did not add those fields or change the checkpoint schema, as instructed.
- `git diff --check` — passed.

## Commits

- `fc06b52 test(arena): align initialization with revision 65 perception`
- `e265ce4 feat(arena): add transactional native weapon ready action`
- The final commit groups browser-flow coverage, the revision-66 rule record, and this report after verification.

## Mac usage

The historical Mac demonstration described above is no longer valid. Current behavior disables Ready weapon because templates define no hands and custody does not identify whether a carried Object is drawable. See the corrective [U-ARENA-005F report](U-ARENA-005F-report.md) for current rule authority and browser behavior.
