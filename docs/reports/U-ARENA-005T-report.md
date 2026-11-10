# U-ARENA-005T — Repeatable Arena movement checkpoint report

## Outcome

Implemented and verified the requested bounded three-process continuation:

1. Process A generates the supported two-Being 5×5 Arena with root seed `20261120` and starting experience `10000`, accepts a Walk/turn destination plan to cell `(0, 0)`, commits boundary 1, and captures the native checkpoint and accepted movement plan.
2. Process B decodes those bytes in a fresh interpreter, reconstructs and validates boundary 1, imports its authentic native receipt and Target records, advances with ordinary `Encounter.step` to boundary 2, and captures a second native checkpoint plus the continuing plan.
3. Process C decodes only process B's checkpoint and plan in another fresh interpreter, reconstructs boundary 2 without replay, advances to boundary 3, and matches process A's uninterrupted native execution through boundary 3.

The integration test checks that `npcgen` is not imported by either restore process. The comparison includes logical Encounter identity, boundaries and receipt timeline, full-precision Being positions, posture and facing, original/current native Being projections, Awareness, per-Being Target-history fingerprints, observer-owned perception ledgers, movement activation, RNG state, Choice count, pending/finished/cancelled Action queues, and the exact accepted plan. The saved plan retains its destination, selected Walk rate, turn-facing policy, decision identity, cell/layout and world premise; its checkpoint cursor advances from 1 to 2.

The restored graph remains quarantined after each imported step. The proof establishes repeatable persistence for this bounded movement-only case, not general Arena save/load or unrestricted continuation.

## Implementation

- Added a closed `/2` continuing movement-only receipt descriptor. It is accepted only as boundary 2 immediately following the authentic `/1` activation receipt. Both rows must have the same participant/Target identities, consecutive chronology, no Actions, effects, Choices, or start fences, and identical RNG state.
- Extended projection, wire validation, identity binding, and native reconstruction to validate both receipts and each Being's ordered boundary-1 and boundary-2 Target records. Restoration rebuilds Target-owned history and process-local receipt/Target anchors against the reconstructed native objects; it does not issue or replay historical movement.
- Extended the restoration-owner-only progression path to continue from the boundary represented by the imported receipt prefix. The movement plan's boundary must match that prefix, and native movement still resolves through the ordinary transactional Encounter pipeline.
- Added a narrow owner-controlled boundary-2 capture operation. It requires the exact just-continued imported graph and accepted plan, verifies native inspection and that the destination remains in transit, then uses the existing coordinated checkpoint capture and wire encoder. Capture of quarantined state remains denied to ordinary callers. Runtime quarantine markers are temporarily excluded from checkpoint data and restored in `finally`; a failure test confirms that state, receipt history, RNG and quarantine markers remain unchanged.
- Kept checkpoint readiness flags false. The implementation does not add readiness claims, general save/load, new gameplay records, or a broader receipt allowlist.

## Validation

Final focused/adjacent command:

```text
PYTHONPATH=src:tests .venv/bin/python -m unittest \
  tests.test_checkpoint_movement_continuation \
  tests.test_checkpoint_receipt_descriptors \
  tests.test_checkpoint_wire \
  tests.test_checkpoint_projection \
  tests.test_checkpoint_movement_binding \
  tests.test_checkpoint_restore_preparation \
  tests.test_transactional_progression \
  tests.test_movement_intent \
  tests.test_arena_state_admission \
  tests.test_checkpoint_envelope \
  tests.test_arena_checkpoint_activation -v
```

Result: **132 tests passed in 113.959 seconds**. This includes the three-process boundary-1 → boundary-2 capture → boundary-3 restore proof; forged boundary-2 receipt, Target, RNG, and interval-order rejection; mismatch-plan refusal; injected progression failure; and injected boundary-2 capture failure with unchanged native state.

Additional checks passed:

```text
PYTHONPATH=src:tests .venv/bin/python -m py_compile \
  src/arena_movement_plan_checkpoint.py src/atomic_publication.py \
  src/checkpoint_binding.py src/checkpoint_envelope.py src/checkpoint_inventory.py \
  src/checkpoint_projection.py src/checkpoint_receipts.py \
  src/checkpoint_restore_preparation.py src/checkpoint_wire.py src/encounter.py \
  src/transactional_progression.py tests/test_checkpoint_movement_continuation.py

git diff --check
```

The environment has no `pytest` module (`.venv/bin/python -m pytest` returned `No module named pytest`), so validation used the repository's `unittest` runner. No loopback-dependent test was needed. During development, the first adjacent run exposed a private receipt-shape compatibility expectation in an existing test; the private import record was adjusted to retain the singular latest-receipt field alongside its validated receipt chain, and the final complete focused/adjacent rerun passed.

## Restrictions and next dependency

This increment captures and resumes boundary 1 and boundary 2 only. The boundary-2 plan can authorize the boundary-2 → boundary-3 step, after which the Encounter remains quarantined. A subsequent portable boundary would require another explicitly bounded receipt/capture contract and its restoration-owner checks; this work does not claim that contract. Action-bearing boundaries, other Encounter histories, general-purpose Arena persistence, and checkpoint readiness remain outside the demonstrated scope.

## Commit

- `14b437b2385855e88e8a733f1369e3f8c269cf63` — `Support repeated Arena movement checkpoint continuation`

No push was performed. Pre-existing unrelated worktree changes were left untouched.
