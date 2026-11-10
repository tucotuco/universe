# U-ARENA-006 Engineering Report

## Status

**General Arena Save/Load is not complete yet.** The browser provides real local file download/upload and replaces the current session only after validation. It restores pristine generated Arenas and movement-only activated Arenas across server processes, including the supported ground Object profile. Those restored sessions can continue with native movement. Saving or restoring after an Action such as Pick up or Draw is still refused by the native checkpoint contract. The feature must therefore be treated as a verified partial implementation, not general Arena persistence.

## Implemented and verified

- Added a canonical, bounded JSON save envelope (`universe.generated-arena-save/1`) around the strict native checkpoint and an Arena session record. Decoding rejects unknown/duplicate fields, noncanonical JSON, digest mismatches, invalid base64, malformed metadata, excessive size/tree depth, and invalid embedded native wire.
- Added shipped **Save Encounter** and **Load Encounter** controls. Save downloads `universe-arena.json`; Load uses the browser file picker. The HTTP endpoint accepts only bounded binary files. Loading stages and validates a separate native graph before atomically replacing the current session; rejected data leaves the old session active.
- Preserved session names, map dimensions and world premise, seed/source records, ground-Object source/identity bindings, display-name overrides, accepted destination plan, movement sequence, and selected visible Entity.
- Added owner-controlled import for the existing movement-only receipt prefix with any supported Arena Objects. Typed Object originals/current state, native identity/custody/position, each Entity's committed Target history, process-local receipt anchors, Encounter awareness, observer-owned perception ledgers, and RNG cursor are rebuilt from validated checkpoint data without replaying boundaries or regenerating Being data.
- A fresh process can load a movement-only checkpoint with eight ground combat Objects, advance normally, save again, and continue at the next boundary. Movement plans remain bound to the original decision, destination, rate, facing policy, map, and current native Encounter.

## Explicit remaining blocker

The current checkpoint closure and restoration adapters cover movement-only receipts and a bounded Run/Spot Action subset. Pick up and ReadyWeaponAction are not yet covered as portable pending declarations or committed receipt Actions/effects. The first authentic ground Pick up commit is currently rejected at capture with:

> `This Arena state cannot be saved yet; native checkpoint validation refused it: missing closed-field adapter: activities.PickUpAction`

After adding PickUpAction/ReadyWeaponAction to the event type catalog to expose the next validator boundary, capture still fails closed until their exact native field adapters, choice descriptors, effect/action receipt encodings, Target/observer state rebinding, and reconstruction paths are reviewed and implemented. The restored movement path also assumes every historical receipt is Action-free and returns to quarantine during its owner-controlled next-step proof. General repeated play across mixed movement and Action history therefore still needs a trusted, indefinitely usable restoration path. No unsupported Action or history was dropped to make a save appear successful.

This is an implementation dependency in the checkpoint machinery; no Encounter timing or simulation-rule decision is being requested. The browser reports the native refusal and retains the current Encounter.

## Browser demonstration

Using the actual shipped browser code in a new isolated local session:

1. Open the generated Arena, select **Generate Encounter**, and use **Save Encounter** to download a file.
2. Stop and restart the loopback Arena server.
3. Select **Load Encounter** and choose the downloaded file. The browser displayed “Encounter loaded. Native state and observer evidence restored.” at native time zero.
4. Clicked a map hex, confirmed the server accepted a Walk/turn destination, then clicked **Advance 1 second**. The page reported native time 1 and showed the player's updated authoritative Cartesian position/facing.

The smoke used an ephemeral loopback port. The first normal sandbox bind attempt failed with `PermissionError`; the server was then launched with narrowly scoped loopback permission. No external host was bound. The smoke download is `<LOCAL_HOME_PATH>`.

## Test evidence

Passed:

- `PYTHONPATH=src:tests:.venv/lib/python3.12/site-packages .venv/bin/python -m unittest tests.test_arena_persistence -q` — **3 passed**. Covers pristine ground Object restoration, and three-process repeatable movement continuation both with no Objects and with eight typed ground Objects. Compares native position/facing, RNG, Object IDs/types/positions/history lengths, and receipt-history counts with uninterrupted execution.
- `PYTHONPATH=src:examples:tests:.venv/lib/python3.12/site-packages .venv/bin/python -m unittest tests.test_generated_arena_browser tests.test_arena_ground_objects tests.test_arena_persistence -q` — **42 passed**.
- `PYTHONPATH=src:tests:.venv/lib/python3.12/site-packages .venv/bin/python -m unittest tests.test_checkpoint_bounded_closure tests.test_checkpoint_movement_continuation tests.test_checkpoint_receipt_descriptors tests.test_checkpoint_projection tests.test_checkpoint_wire -q` — **33 passed**.
- `python -m py_compile` over the modified persistence/checkpoint/session/test modules — passed.
- `git diff --check` — passed.
- Separate real-browser download → server restart → file load → map destination → native one-second progression smoke — passed.

Additional failure characterization:

- Captured an authentic completed native Pick up in a generated ground-Dagger Arena. Saving was refused with the closed-field-adapter message above; no file was emitted and the session remained active.

The full repository suite was not run. Pending Draw, post-Draw, post-Pick-up load, mixed Action/movement restore, observer-history ground-to-carried persistence, save rollback injection, and an uninterrupted-versus-restored Action-bearing comparison remain unverified and unsupported.

## User instructions

From the repository root, launch the generated Arena locally:

```sh
PYTHONPATH=../npc-generator .venv/bin/python examples/generated_arena_browser.py --port 8000
```

Open `http://127.0.0.1:8000/`. Generate, then use the Save/Load controls. At this implementation stage, save/load is supported before activation and during supported Action-free movement history; an Action-bearing state produces an explicit refusal. The checked-in authored Draw scenario can be started with `--authored-draw-scenario`, but Draw persistence is not yet implemented.

## Commits

- `7b43efe` Close Arena checkpoint over native Objects
- `5936dce` Document Arena persistence implementation status
- `f4021c0` Add generated Arena save and load at time zero
- Additional Object-inclusive movement restore work is being validated for a focused commit; no changes were pushed.
