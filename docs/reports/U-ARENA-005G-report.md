# U-ARENA-005G — explicit source location and native two-second Draw

## Result

Implemented a bounded, opt-in native Draw path for an explicitly authored carried Dagger and a named free hand. The Draw is a genuine native `ReadyWeaponAction` Choice in the existing transactional Encounter path. It remains pending through the first one-second boundary and publishes readiness atomically at the second. Ordinary generated Arena Beings and the one-second ground Pick up flow are unchanged.

No NPC Generator source, generated Being anatomy, default equipment, Quick-draw behavior, general container mechanics, or checkpoint serialization was added. The only executable demonstration is a deterministic test-authored scenario; a live Chrome Arena was not launched.

## Adopted rules and separate timings

Adopted Encounter revision 61 controls. Appendix I, Weapons says ordinary drawing takes two seconds unless a weapon description specifies otherwise; it separately gives Quick-draw plus advanced weapon skill as an essentially no-time exception. Revision 61 also says post-strike re-readying takes one-third of the weapon's timing, rounded down. The Ready section repeats these distinctions and says retrieving/preparing an object can vary and is referee-adjudicated. See [revision 61, Weapons](../encounters/encounters-working-draft-adopted-r61.md#weapons) and [revision 61, Ready](../encounters/encounters-working-draft-adopted-r61.md#ready).

The implementation uses the ordinary two-second rule for this explicit Dagger. It does not make a one-second initial Ready Action from withdrawn revision 66. Quick-draw is not implemented as an instant Action; a Being with Quick-draw and advanced skill in the weapon is rejected from this fixed two-second path. Post-strike re-readying remains a separate calculation and future lifecycle.

The ground Pick up rule remains revision 64's distinct one-second Action for a free ground Object. Pick up changes native custody and position only. It does not set a source location, hand, or readiness; the browser leaves Draw unavailable after ordinary ground pickup because that Object still has no authored drawable source location.

## Native state representation

Inspection found the native Being already stores `current.body_parts` as a mapping from named slot to native Object ID. The generated templates in this path have no hand slots, and this change does not infer or add any for them. A test fixture explicitly authors `right hand: None` on the test Being.

The Object model already has an instance-specific `current.tags` dictionary, but it has no physical sheath entity or typed carried storage-location field. The minimal added native contract uses one strict record in the Dagger's existing tags:

```json
{"universe.native_draw_location":{"kind":"worn_sheath","owner_id":"<native-being-id>"}}
```

This is explicit per-instance source-location evidence linked to a native Being identity. It is not a sheath Object, a new anatomy or carrying rule, or a default for possessions. The reader rejects malformed records; action admission and publication also require that the record owner matches the actor, the same Weapon is in the actor's possession and parent custody, and the selected native hand exists and is free. The owner reference is checked against the Being and Weapon identities already in native state. Ground pickup writes no such evidence.

The existing `current.tags` field means no new Python instance field or checkpoint inventory field was introduced. Successful Draw consumes the source-location record in the same atomic publication that sets the selected `body_parts` slot and native ready-weapon list. The same native Weapon identity remains possessed, parented to the Being, and at the same weight. A same-boundary strike cannot use a weapon that has not yet been published as readied. The transaction tests cover contention, Choice undo, and injected publication rollback.

## Reproducible demonstration

The deterministic test fixture creates a positive-HP generated Arena Being, a native Dagger, exact possession and parent custody, a test-authored owner-linked worn-sheath record, and an explicitly free right hand. It activates the Encounter, opens the player-owned observer view, submits the browser/native Draw Choice, and advances once per second:

| Native boundary | Action | Authoritative inventory and hand state |
|---|---|---|
| Choice accepted | Draw executing, 2 seconds remaining | Dagger carried; not readied; right hand remains empty; source record remains |
| +1 second | Draw executing, 1 second remaining | Dagger still carried; not readied; right hand remains empty; source record remains |
| +2 seconds | Draw completed successfully | Same Dagger remains in possession and parent custody, is readied in right hand, and source record is consumed atomically |

The native HTTP/session test drives `/api/generated/ready-weapon` and two `/api/generated/advance` requests through the actual Arena handler and checks the native state at both boundaries. The shipped JavaScriptCore harness runs the page's inline script, opens the character popup, enables Draw only for an explicitly test-authored drawable fixture, selects the represented hand, verifies the request body contains only the opaque handle and hand, and checks the popup/inventory after each one-second response. The harness uses fake fetch responses for browser-side state transitions; the paired HTTP test verifies the real handler/session/Encounter path. A live browser session was not launched.

Ordinary generated Beings remain without authored hands or source locations. The test does not alter generation, launcher profiles, NPC Generator behavior, or other Beings' private inventory/perception. The character popup uses the existing player-only projection and opaque public handles. Terminal tracing remains redacted.

## Post-strike re-readying remains separate

The existing pure helper is still tested against native weapon-table values: Dagger range/swing/thrust timing 4 gives `floor(4/3) = 1` second; Longsword swing timing 6 gives `floor(6/3) = 2` seconds. The configured Repeating crossbow row yields zero arithmetically, but it has no adopted revision-61 weapon-table row; that config-only value creates no zero-duration Action and is not treated as adopted data. No post-strike readiness lifecycle is connected here.

## Checkpoint boundary

`test_checkpoint_inventory` passed. No checkpoint code or allowlist was changed, and the new record lives in an already represented `current.tags` mapping. The strict Arena checkpoint suites were run and continue to show the existing boundary: the six S6/S7 candidate cases error at `arena_state_candidate.py:654` with `ArenaStateRejected: Encounter has an unrepresented native field`; the unrepresented fields are `arena_activation`, `arena_activation_enabled`, and `arena_movement_activation`. The two multi-process continuation cases exit with status 1 during server startup without captured output. These activation fields and failures predate this change and are documented by U-ARENA-005E. The checkpoint state schema was not broadened to make them pass.

## Validation

All Python commands below used the repository source, examples, tests, and sibling NPC Generator checkout on `PYTHONPATH`.

- `python -m unittest test_arena_ready_weapon -q` — **8 passed**, 4.949 seconds. Includes source-location validation, explicit hand admission, +1/+2 boundaries, ground-Pick-up separation, same-boundary strike rejection, contention, Choice undo, publication rollback, and table-derived re-ready timing.
- `python -m py_compile src/weapon.py src/action_evaluation.py src/activities.py src/atomic_publication.py src/encounter_inspection.py src/arena_browser_session.py` — passed.
- `python -m unittest test_arena_ready_weapon test_arena_ground_pickup test_arena_initialization test_generated_arena_browser test_action_settlement test_atomic_publication test_interval_staging test_transactional_progression -q` — **288 passed**, 116.165 seconds. Covers the browser HTTP and JavaScriptCore harnesses plus movement, pickup, Choice/snapshot settlement, atomic publication, and transactional progression regressions.
- `python -m unittest test_checkpoint_inventory test_arena_local_checkpoint test_arena_s7_checkpoint -q` — **39 tests: 31 passed, 6 errors, 2 failures**, 25.474 seconds. The checkpoint inventory tests passed; all eight non-inventory failures are the existing strict Arena activation-field refusals described above.
- An initial combined unittest invocation omitted the bare-module `tests/` path and produced three test-module import errors; it was rerun with `src`, `examples`, `tests`, and the NPC Generator paths, producing the 288-test passing result above.
- `git diff --check` — passed before the commits.

## Commits

- `9566f3c feat(arena): model explicit native weapon draw location`
- `78ed48c feat(arena): expose two-second native Draw in browser`

No push was performed.

## Remaining decisions

This slice establishes a test-authored typed location record, not a general item-location system or physical sheath object. Rules/data owners still need to decide whether a future production Arena should author sheath entities, which native templates have hands, and how general worn/container locations are modeled. Quick-draw scheduling and the post-strike re-ready state transition remain outside this work.
