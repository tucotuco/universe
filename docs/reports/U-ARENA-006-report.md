# U-ARENA-006 Engineering Report

## Outcome

General Arena Save/Load is **not yet usable**. The browser has no working Save/Load controls for generated Arenas, and the native cross-process restoration path cannot yet preserve the generated Arena's Object inventory or its native Action lifecycle. I did not expose a download/upload flow that would accept a file and then refuse to restore its authoritative state.

The requested `docs/assignments/U-ARENA-006.md` file is absent from the checkout. The implementation scope in the user's request was used as the task authority. The existing unrelated worktree deletions and untracked files were left untouched. No npc-generator files were modified and nothing was pushed.

## Verified implementation

The native checkpoint semantic closure now records generated Arena Objects alongside Being state. It validates exact Object registry identities, registered original definitions, separated original/current definitions, ground position versus carried custody, and Being possession references. The receipt descriptor now retains Object Target records for action-free movement boundaries, including weapon and armor categories. The closure schema is versioned as `native.run-spot-field-closure/5`.

Commit: `7b43efe Close Arena checkpoint over native Objects`.

Earlier movement-only persistence work in the current history is in `dd172cc Extend native Arena movement receipt chains`; it supports repeated movement-only continuation when the Encounter contains only Beings.

The following focused checks passed after the Object closure change:

- `tests.test_checkpoint_bounded_closure` and `tests.test_checkpoint_movement_continuation`: 14 tests passed.
- `tests.test_checkpoint_receipt_descriptors`, `tests.test_checkpoint_wire`, and `tests.test_checkpoint_projection`: 19 tests passed.
- Python compilation and `git diff --check` passed.

The new Arena Object test creates a generated equipment-profile Arena, commits its first movement boundary, captures the native envelope, encodes and decodes the strict wire form, and verifies that all eight ground Object identities and positions appear in the closure. This verifies capture and wire validation; it does not claim restoration.

## Remaining native blockers

1. `checkpoint_projection.project_quarantined_movement_boundary` still requires exactly two Encounter Being participants, equates receipt participant IDs with `encounter.being_list`, and rejects Object Target records. The real generated equipment Arena has two Beings plus eight typed Objects, and every Entity has a Target record at the committed movement boundary.
2. `checkpoint_binding._materialize_quarantined_movement_native` requires a registry of exactly two Beings. It reconstructs empty Object/Armor/Weapon dictionaries, discards their captured definitions, and only rebuilds Target histories and anchors for Beings. An Object-bearing graph therefore cannot become an inspection-valid native Encounter after process restart.
3. Pick up and Draw are not in the accepted-choice, committed-receipt, Target settlement, or native reconstruction adapters. Safe persistence must retain an accepted pending Action and Choice, and must preserve the later atomic settlement of Pick up or the two-second Draw. The existing Run/Spot adapters cannot represent those states.
4. Generated Arena session state is not part of the native checkpoint: the accepted movement plan and continuation sequence, map layout and world premise, encounter/player display names, Entity display-name overrides, and browser-visible selection state need a strict sidecar bound to the native Universe/Encounter identities. `GeneratedArenaSession` currently reports `load_available: false`; the generated page's Load button is disabled and there are no generated-Arena save/load HTTP routes.

These are implementation dependencies, not unresolved simulation-rule choices. A complete feature should first reconstruct typed Object definitions and instances with their exact identities, then import Object-owned Target histories and receipt anchors, then add native Pick up/Draw choice and receipt descriptors, then bind the Arena session sidecar and add browser file download/upload controls. Until that chain is implemented and tested through a fresh process, General Arena Save/Load must remain unavailable.
