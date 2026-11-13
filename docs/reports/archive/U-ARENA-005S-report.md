# U-ARENA-005S Engineering Report

## Outcome

Completed a bounded, trusted cross-process continuation from the authentic Arena boundary 1 to boundary 2. The restored Encounter advances through the ordinary `Encounter.step` → transactional progression → interval staging/publication path using the same accepted destination, rate, and facing policy as the uninterrupted session. Native inspection validates both committed boundaries. The existing U-ARENA-005R import remains quarantined; the result stays quarantined after its one authorized boundary-2 step and rejects any subsequent ordinary step.

This demonstrates this specific generated two-Being scenario and one-boundary continuation. It does not establish general Arena save/load or set global checkpoint-readiness flags. The source checkpoint still has `(inventory_validated=True, closure_validated=False, portable_schema_defined=False, restore_verified=False)`. The second movement-only receipt is native committed history for this live imported graph; it is not claimed to be portable under the initial-only movement receipt schema.

## Exact accepted session plan

Added `arena_movement_plan_checkpoint.py`, a closed, canonical, versioned, pointer-free representation of the real `GeneratedArenaSession._movement_plan`. Capture is restricted to a completed initial boundary-1 movement-activated Arena with an unarrived accepted plan. It preserves Universe/Encounter/actor IDs, the activation's movement decision ID, accepted time and boundary, exact destination Cartesian coordinates, hex cell and rectangular layout, rate, facing policy, movement sequence, and the generated Arena's explicit Plains/Road movement premise. It rejects unsupported layouts/premises and mismatches between the accepted destination and its adopted hex-cell center. The codec rejects unknown fields, duplicate JSON keys, non-finite values, unsupported policy/rate values, invalid chronology, and non-canonical wire.

The fixed reproduction uses seed `20261120`, 10,000 starting XP, and a 5 × 5 layout. The player begins with 18 HP at `(3.6955036030289565, 3.2004, 0.0)`. The actual accepted plan is decision `arena-movement-1`, Walk, turn-facing, destination hex `(0,0)` at `(0.5279290861469939, 0.4572, 0.0)`. After boundary 1 the player remains in transit at `(3.0042821747896817, 2.6017846835046257, 0.0)` and the session retains the plan. The uninterrupted boundary-2 position is `(2.313060746550407, 2.003169367009251, 0.0)`; the fresh child produces the same full-precision value.

## Trusted admission and native continuation

The restoration owner first performs the U-ARENA-005R strict reconstruction and native inspection. A private, one-use host approval is bound to that exact imported handle and canonical plan; approval is process-local and is not persisted provenance or a signature. Before execution, the owner rechecks the native receipt/Target inspection and fingerprint chain, activation and participant identities, plan-to-actor/Encounter/decision binding, full-precision destination/cell/layout correspondence, positive-HP actor state, two reconstructed Beings with distinct original/current definitions, exact registered participant coverage, and independent observer-owned ledgers. It also requires the imported RNG cursor and the native Encounter's ChoiceBook, pending/finished/cancelled Action lists, schedule state, and event closure to match this supported empty-Action/empty-Choice boundary.

After all checks, a private scope temporarily binds ordinary transactional progression to the imported receipt and its exclusive RNG cursor. It does not clear quarantine markers, replay boundary 1, create an Action or Choice, regenerate perception, or call the publisher to issue a replacement historical receipt. It creates the boundary-2 `MovementIntent` from the stored plan and calls `Encounter.step(1, movement_intent=..., movement_conditions=...)`. The native movement engine stages and publishes the new boundary normally; its new receipt is registered through the existing successful publication path. The host scope then closes while the reconstructed graph remains quarantined, preventing further progression without another reviewed restoration operation.

Injected step failure verifies that boundary, positions, Target histories, RNG, and receipt registry remain unchanged and the inspection-only binding is restored. A mismatched player/plan is refused before progression admission and leaves both source session state and imported native state unchanged. The host approval is consumed once.

## Fresh-process equivalence

The child receives actual boundary-1 checkpoint wire and the separately captured accepted-plan wire. It asserts `npcgen` is not imported, reconstructs and inspects boundary 1, obtains explicit host authorization for that exact plan, then advances exactly one native second. The comparison against uninterrupted execution includes:

- Encounter and participant identities, boundary/time cursor, and committed timeline boundaries 1 and 2;
- full-precision positions, facing, posture, and original/current Being definition projections;
- both Target-owned histories, in boundary order, with matching native fingerprints;
- the same activation record and Awareness for each participant;
- separately encoded observer evidence for each Being, preserving ledger history order;
- RNG state, empty Choice state, and empty pending/finished/cancelled Action state.

Process-local Object, definition-current, Target storage/record, receipt, and transactional binding addresses are rebuilt in the child and are intentionally not compared as portable values. The native inspector validates the rebuilt receipt and Target anchors before and after boundary 2.

## Remaining scope

The trusted admission is deliberately bounded to the generated 5 × 5 rectangular Arena, the explicit unobstructed Plains/Road multipliers, two native Beings, no pending Actions or Choices, and the initial movement-only boundary. The generated browser session itself is not reconstructed as a general resumable UI session; this increment carries only the actual accepted movement plan needed for the demonstrated next native second. General checkpoint closure/authorization remains false, and the existing portable receipt contract still refuses later Action-free movement boundaries. No boundary-2 save/restore, later continuation, or browser Save/Load flow is claimed.

## Tests and checks

- `PYTHONPATH=src:tests .venv/bin/python -m unittest tests.test_checkpoint_movement_continuation` — **3 passed**, 7.422 s. Covers real fixed-seed source generation, still-in-progress plan capture, fresh-process boundary-1→2 equivalence without `npcgen`, plan mismatch/no mutation, failed-step rollback, and post-step quarantine.
- `PYTHONPATH=src:tests .venv/bin/python -m unittest tests.test_checkpoint_movement_continuation tests.test_checkpoint_movement_binding tests.test_movement_intent tests.test_transactional_progression tests.test_encounter_inspection tests.test_checkpoint_receipt_descriptors tests.test_checkpoint_restore_preparation tests.test_checkpoint_reconstruction tests.test_checkpoint_arena_perception tests.test_checkpoint_identity_binding tests.test_arena_checkpoint_activation tests.test_arena_state_admission` — **180 passed**, 141.006 s. Includes the U-ARENA-005R fresh-process import and existing native Run/Spot and Arena admission controls.
- `PYTHONPATH=src:tests .venv/bin/python -m py_compile src/arena_movement_plan_checkpoint.py src/checkpoint_restore_preparation.py src/transactional_progression.py tests/test_checkpoint_movement_continuation.py` — passed.
- `git diff --check` and `git diff --cached --check` — passed.

No loopback tests were required. No test failures remain.

## Commits and worktree

- `208f854` — Continue trusted Arena movement from restored boundary.

Pre-existing unrelated dirty/deleted files were preserved. No NPC Generator changes were made and nothing was pushed.
