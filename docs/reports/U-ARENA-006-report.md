# U-ARENA-006 Engineering Report

## Result

Implemented a portable, versioned Save/Load format for the generated Arena's currently supported native graph and browser session. Save and Load now include completed and pending Run, Pick up, and Draw Actions, movement plans, and mixed Action/movement histories. Loaded sessions resume ordinary native progression and can be saved and loaded repeatedly. The format is deliberately scoped to this Arena implementation and fails closed for unknown schemas, native types, fields, references, or runtime compatibility.

## Design and preserved state

- Replaced the Run/Spot checkpoint wire as the Arena file format with `universe.generated-arena-save/2`, containing a separate `universe.generated-arena-native-state/1` graph inventory and the Arena-owned session record. Canonical JSON, duplicate-key rejection, SHA-256 integrity, strict field sets, depth/node/file bounds, exact runtime compatibility, and an allowlisted native type closure reject incompatible or malformed files.
- The native graph is captured from the existing checkpoint inventory's authoritative state, including the exact Being and Object definitions/instances, identities, current and historical state, possessions, body-part/equipment state, Action/Choice objects and timing, Target histories, observer-owned perception, committed receipts, and RNG cursor. The browser sidecar preserves names, map/world premise, generated input evidence, Object source bindings, accepted movement destination/options, movement sequence, and current selection.
- Restoration allocates the captured native graph without calling npcgen or replaying a committed effect. Under restoration-owner-only hooks it rebinds process-local locks, Choice declaration signatures, native references, receipt identity anchors, and progression ownership. Native Encounter inspection validates committed history before the session is exposed. The restored graph then uses the ordinary progression pipeline for every subsequent second.
- Completed Action summaries are rebuilt from native inspection. Pending Actions are recovered from accepted native Choices as well as committed event history; this covers a pending Pick up, which the native scheduler holds in ChoiceBook before it appears in event history. No pending Action is synthesized.
- The accepted movement plan remains valid after subsequent plan changes; it is checked against the native Arena activation actor/time, map, destination, movement rules and checkpoint boundary rather than requiring its decision ID to be the first activation decision.
- Load stages a separate graph and session record, then replaces the live browser session only after validation. Version 1 files and unsupported type closures are rejected without replacing the active session.

This is a dedicated Arena save contract. It does not expand the supported general Universe checkpoint format and it does not claim to serialize arbitrary Encounter types or future Actions.

## Browser acceptance demonstrations

All demonstrations used the shipped Arena JavaScript in isolated Chrome tabs and a freshly launched local server on `127.0.0.1` ephemeral ports.

### Pick up → Save → Restart → Load → Continue

Generated an Arena with the explicit ground-loadout test profile, moved to a native ground Dagger, picked it up, and committed the one-second Action. Saved through **Save Encounter**, stopped the server, launched a fresh server, and loaded the downloaded version 2 file through **Load Encounter**. The loaded browser showed native time 2 and the carried Dagger. Selected a destination and advanced one second; time became 3 and the authoritative position changed to `(2.389259973808466, 1.805280332873052, 0)` m. The loaded Encounter was in the ordinary playable state.

### Pending Draw → Save → Restart → Load → Complete Draw

Generated the opt-in authored Draw scenario with its explicitly drawable carried Dagger and empty native hands. Selected the carried Dagger and **Draw (2 s)** in the character Action catalog, then advanced one second. Saved while the native Draw Choice was pending, stopped the server, launched a fresh server, and loaded the file into a new browser tab. The browser restored native time 1 and the pending Draw. Advancing one more second resolved it successfully at time 2. The character panel showed the same Dagger readied in the left hand; possession and Object identity remained intact.

### Mixed movement and Action history; repeated Save/Load

The integration regression compares uninterrupted play with save/load branches after native movement and completed Pick up. Both branches accept a further movement plan, commit it, save/load again, and advance another boundary. Positions, RNG state, receipt counts, Dagger custody/identity, and Target history match. Pending Pick up is separately saved/restored and completed at its exact one-second boundary. Pending Run is restored before its first boundary, then its result and position match uninterrupted execution. Pending Draw is separately restored with one second remaining and completes only at its native two-second boundary. Completed Draw and Run histories also round-trip.

## Verification

- `PYTHONPATH=src:examples:tests:.venv/lib/python3.12/site-packages .venv/bin/python -m unittest tests.test_arena_persistence tests.test_generated_arena_browser tests.test_arena_ground_objects -q` — **47 passed**.
- `PYTHONPATH=src:tests:.venv/lib/python3.12/site-packages .venv/bin/python -m unittest tests.test_checkpoint_bounded_closure tests.test_checkpoint_movement_continuation tests.test_checkpoint_receipt_descriptors tests.test_checkpoint_projection tests.test_checkpoint_wire -q` — **33 passed**.
- `py_compile` over all changed Python implementation and test modules — passed.
- `git diff --check` — passed.
- Real-browser Pick up and pending Draw restart workflows above — passed.
- One initial attempt to launch the local server inside the network-restricted sandbox was denied with `PermissionError`. Each browser smoke then used narrowly approved execution for only the server command, bound only to loopback on an OS-assigned port. All servers were stopped after use.

The full repository test suite was not run. Save files cover only the currently allowlisted generated Arena type and Action closure; a later native Action or new state type is rejected until deliberately added and verified.

## Files changed

- `src/arena_native_snapshot.py` — bounded Arena-only native graph encoding, validation, reconstruction, and restoration-owner binding.
- `src/arena_persistence.py` — version 2 portable file envelope and strict metadata validation.
- `src/arena_browser_session.py` — native graph Save/Load integration and restoration of completed/pending Run, Pick up, and Draw state.
- `src/atomic_publication.py`, `src/transactional_progression.py` — private restoration-owner receipt import and ordinary progression binding.
- `src/checkpoint_inventory.py` — closes the exact Pick up and Draw effect types needed by the Arena graph.
- `src/arena_movement_plan_checkpoint.py` — preserves later accepted movement plans across activation history.
- `tests/test_arena_persistence.py` — pending/completed Action, mixed-history repeated-save, native-state, and deterministic-continuation regressions.

## Commits

See the repository history for the verified implementation commits. No changes were pushed.
