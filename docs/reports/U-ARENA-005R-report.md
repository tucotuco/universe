# U-ARENA-005R Engineering Report

## Outcome

Implemented the requested private restoration-owner import for the authentic initial Arena movement boundary. In a fresh Python process, real checkpoint wire now materializes a native quarantined Encounter at boundary 1, restores each participant's Target-owned interval record, rebinds Target anchors to the newly constructed native objects, registers a new process-local receipt anchor, and passes `encounter_inspection.inspect_encounter` without replaying movement or observations.

The imported graph is **inspection-only**. Its progression mode is `quarantined_inspection`; the ordinary `step_transactionally` route refuses it, and a before/after snapshot proves the refusal changes no Encounter, Target, RNG, or receipt-history state. This is not trusted live continuation, portable authorization, or general Arena save/load. Captured readiness flags remain `(inventory_validated=True, closure_validated=False, portable_schema_defined=False, restore_verified=False)`.

The fresh-process reproduction uses seed `20261120`, 10,000 shared starting XP, a 5 × 5 Arena, a real accepted destination, and its actual committed 0→1 wire. The child asserts `npcgen` is absent from `sys.modules`. It reconstructs the native Encounter and inspector views from the saved record; it does not call the movement publisher, evaluate the interval, or create Actions or Choices.

## Native import boundary

The import is deliberately split across existing owners:

- `checkpoint_restore_preparation._import_quarantined_movement_boundary` is the sole orchestrator. A private module authority token gates the native receipt and progression bindings; there is no caller-facing receipt-registration API.
- `checkpoint_binding._materialize_quarantined_movement_native` first applies the strict detached movement binder, then reconstructs only the two recorded Being definitions/instances, native TargetCandidate values, observer-owned ledgers, movement activation, RNG cursor, and the quarantined Encounter shell. The native Being original/current definitions stay distinct. No character generation occurs.
- The restoration owner rebuilds exactly one TargetIntervalRecord at each Being's Target history, then derives new anchors from each reconstructed Being, current definition, spatial state, history list, and Target record. It restores the committed receipt fields and inspection record from the checkpoint and substitutes only the process-local Target anchors that cannot survive a process boundary.
- `atomic_publication._register_quarantined_movement_import` validates the exact 0→1 chronology, activation, committed receipt, RNG equality, two participant/Target coverage, Target ownership, and every new anchor before registering the receipt's owner/fingerprint in the existing process-local registry. It does not manufacture an IntervalCandidate or call `publish_interval_candidate`.
- `transactional_progression._bind_quarantined_movement_inspection` accepts only that private import, and `encounter_inspection.inspect_encounter` applies its normal receipt, receipt-fingerprint, Target-ownership, history, and current-state checks. Inspection admits this explicit quarantined mode; ordinary transactional admission remains unchanged. The progression function still refuses quarantined state before any stepping work.

Construction is private and unexposed until the checks complete. If an owner or inspection step fails after registration, the import path removes the private progression and receipt bindings and clears staged Target history. A forged Action-bearing receipt fails before receipt registration and leaves the original source session's Encounter, movement plan, positions, Target histories, RNG, and committed receipt registry unchanged.

## Fresh-process comparison

The new child-process regression compares the imported native result with the live source for:

- logical Universe, Encounter, participant, Being, and Target identities;
- full-precision Cartesian positions, posture, hex facing, and individualized original/current definition projections;
- native Target-record fingerprints and inspector Target-history fingerprints;
- receipt boundary and stored event fields (empty Actions/effects/notifications; committed RNG; boundary 0→1; participants);
- movement activation, Awareness, and independently encoded observer evidence for both participants;
- RNG state and empty Action/Choice state.

Target-record, receipt, and progression-owner object addresses are necessarily process-local and are rebuilt. The imported receipt fingerprint is therefore newly computed against the imported receipt and new anchors; the source's logical receipt fields and Target values remain identical. Native inspection validates the new fingerprint/anchors in the child. The exact boundary remains quarantined after inspection.

## Remaining save/resume dependency

The next gate for trusted executable restoration is complete semantic closure and explicit host authorization for the native Encounter/Universe graph; the current envelope still marks `closure_validated=False` and `restore_verified=False`. In addition, the accepted `GeneratedArenaSession._movement_plan` (destination, rate, facing policy, and decision ID) remains outside the reconstructed native graph, so a live session cannot safely continue its existing intention from this import alone. A later movement-only boundary also needs its own strict receipt contract: only the authentic initial Action-free boundary is currently admitted. No continuation or boundary-2 comparison is claimed.

## Tests and checks

- `PYTHONPATH=src:tests .venv/bin/python -m unittest tests.test_checkpoint_movement_binding` — **4 passed**, 7.560 s. Covers fixed-seed detached binding, fresh-process native import/inspection, malformed movement receipt rejection, and forged-event atomicity.
- `PYTHONPATH=src:tests .venv/bin/python -m unittest tests.test_checkpoint_adapters tests.test_checkpoint_arena_perception tests.test_checkpoint_identity_binding tests.test_checkpoint_movement_binding tests.test_checkpoint_projection tests.test_checkpoint_receipt_descriptors tests.test_checkpoint_reconstruction tests.test_checkpoint_restore_preparation tests.test_checkpoint_wire tests.test_encounter_inspection tests.test_transactional_progression tests.test_arena_checkpoint_activation tests.test_arena_state_admission` — **217 passed**, 167.261 s. This includes existing Run/Spot receipt paths, reconstruction/restore controls, and Arena admission isolation.
- `PYTHONPATH=src:tests .venv/bin/python -m py_compile src/atomic_publication.py src/checkpoint_binding.py src/checkpoint_reconstruction.py src/checkpoint_restore_preparation.py src/encounter_inspection.py src/transactional_progression.py tests/test_checkpoint_movement_binding.py` — passed.
- `git diff --check` — passed.

The first broad test attempt found a regression: a new eager Encounter import violated the existing detached Arena-admission isolation test. The constructors were made lazy, and the corrected 217-test suite passes. An earlier test invocation also omitted `tests` from `PYTHONPATH`; the corrected command above passes the full adapter module. There were no remaining test failures. No loopback-dependent tests were required.

## Commit and scope

- `2c1667c` — Import quarantined Arena movement boundary natively.

Unrelated pre-existing deletions and untracked files remain untouched. No NPC Generator files were changed, and nothing was pushed.
