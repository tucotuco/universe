# U-ARENA-005P Engineering Report

## Result

Implemented a strict, quarantined binding step for the authentic initial Arena movement-only boundary. The result binds the two participant identities and their Target-owned history references to the already validated portable receipt, while keeping checkpoint readiness false. It is a detached identity sidecar, not a restored or executable Encounter.

The fixed seed `20261120`, starting experience `10000`, and `5 × 5` Arena produced boundary 1 after accepting a destination and advancing one second. Its descriptor was `universe.committed-movement-only-boundary/1`, with participants and two Target records, no Actions, no Choices, no effects, and the native committed RNG state. Strict envelope assembly and wire decoding succeeded.

## Implementation

- The envelope and wire validators now recognize the exact seven-field movement-only receipt alongside the existing nine-field Action receipt. They retain the existing closed descriptor validation, require the movement receipt to be the first boundary, preserve chronological boundary ordering, require its participant set to match the closed identity set, and do not relax any Action-bearing receipt checks.
- Added a detached movement projection that checks the 0→1 Encounter cursor, enabled Arena movement-activation phase, participant membership, activation actor/decision/time, Target identities and awareness, observer evidence, empty Action/Choice lifecycle, and receipt/envelope RNG agreement.
- Added `bind_quarantined_movement_boundary`. It uses the existing graph and individualized-original validators, checks each participant against its registry key, validates the registered template-derived original and distinct current definition, and requires exactly one matching native `TargetIntervalRecord` per participant. Each stored TargetCandidate is reconstructed only for an exact comparison with its portable receipt representation; the record itself is not reissued or attached to a new live Being.
- The binding sidecar retains stable participant and Target-record graph references, both observers' separately decoded Arena ledgers, original/current definition projections, movement activation data, and the exact RNG cursor state. Native movement-only Action, Choice, and effect collections must be empty.
- Extended the existing closed graph value decoder for `frozenset` and reviewed practice/observer record values needed to compare Target-owned state. These additions do not invoke simulation, observation, or RNG.
- Added a fresh-process regression using the actual generated Arena wire bytes. The child process decodes and binds without importing or invoking `npcgen`; it verifies the same Universe/Encounter/Being/Target identities, individualized definition values, activation record, two independent observer ledgers, committed RNG, and empty Action/Choice/effect sets.

## Validation and failure handling

The focused regression rejects a wrong boundary, missing and duplicate portable Targets, missing and duplicate native Target history records, a mutated Target state, a wrong movement activation phase, a second Action-free boundary, and invented Action or Choice data. It confirms these failures do not change source time, positions, movement activation, Target history, awareness, RNG, movement plan, or Choice state.

The final adjacent checkpoint run passed **107 tests in 76.673 seconds** across movement binding, Arena perception, identity binding, reconstruction, adapters, receipt descriptors, wire, envelope, projection, and restore preparation. The focused two-test movement-binding suite passed in **4.041 seconds**. A separate wire/envelope/receipt-descriptor run passed **20 tests in 13.906 seconds**. `py_compile` passed for all changed Python modules and the new test; `git diff --check` passed. An initial command named the nonexistent `tests.test_checkpoint_receipts` module and failed at test discovery; the corrected suite used `tests.test_checkpoint_receipt_descriptors` and passed.

The exact Arena envelope remains:

```text
inventory_validated=True
closure_validated=False
portable_schema_defined=False
restore_verified=False
```

Its diagnostics still include:

- `receipt_rebinding_required` on `CommittedBoundaryRecord.action_anchors`: “Native identity/digest anchors require new authenticated identity-preserving issuance on restore.”
- `receipt_rebinding_required` on `CommittedBoundaryRecord.target_anchors`: the same reason.
- `semantic_closure_adapter_incomplete`: remaining whole-Universe closure, Library catalog/alias, fresh Choice signature, receipt issuance, and restoration work.
- `bounded_run_spot_closure_verified`: the current bounded capture passes its limited field/definition/alias checks; this is not readiness.

The movement sidecar confirms the data needed to bind the existing stable Target references and verify their contents, but it does **not** satisfy native receipt authentication or atomically issue replacement anchor records into a reconstructed Encounter. The `receipt_rebinding_required` diagnostics therefore remain outstanding. No native `PublishedInterval` was fabricated, and no Target history was dropped or re-observed.

## Next dependency

The next checkpoint dependency is the existing native receipt issuer/rebinding boundary: after the whole native graph is reconstructed, it must authenticate and register the movement-only committed receipt against the reconstructed participant and Target identities, preserving exact Target-owned storage references and committed RNG. The current detached binder intentionally stops before this step.

The generated Arena session also keeps its accepted destination movement plan in `GeneratedArenaSession._movement_plan`, outside the native checkpoint graph. Exact Arena continuation will additionally need a reviewed binding for that existing plan (destination, rate, facing policy, and movement decision identity) and the native session/Encounter ownership relationship. This report does not infer or create that contract.

## Commits

- `ce13809` — Accept initial movement-only checkpoint projection.
- `c937dd2` — Bind movement-only Arena Target identities.
- The report is delivered in a separate documentation commit.

No push was performed. Pre-existing unrelated deletions and untracked files in the checkout were preserved.
