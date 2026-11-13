# U-ARENA-005M — Action-free movement boundary receipt

## Where we stand

The initial movement-only boundary now has a distinct, closed receipt representation. The exact seed-`20261120`, 10,000-XP, 5×5 generated Arena passes strict receipt construction, validation, and identity-rebinding planning without inventing an Action, Choice, effect, or receipt link. Strict checkpoint capture advances past U-ARENA-005L's Action-only refusal and reaches the next native identity gate:

```text
Being original definition is not the matching registered Library definition
```

The candidate remains partial and non-authorizing: `inventory_validated=True`, while `closure_validated=False`, `portable_schema_defined=False`, and `restore_verified=False`. No portable checkpoint, live Encounter restore, or cross-process continuation is established.

## Observed committed boundary

The focused reproduction commits boundary 1 at Encounter time 1, from start time 0, through the existing first-player-movement activation record. Its authenticated `PublishedInterval` and `CommittedBoundaryRecord` contain:

| Native evidence | Boundary-1 value |
| --- | --- |
| Action/effect identity sequences | `action_ids == ()`; `effect_ids == ()`; committed Action/effect maps and Action anchors are empty. |
| Choice and lifecycle state | No committed or accepted Choice, pending Action, finished Action, or cancelled Action is created by first movement. The native ChoiceBook remains empty. |
| Participant/Target records | The two participating Being IDs are present as the complete participant set, in `meta.participants`, `meta.entities`, and `meta.target_anchors`. Each has one authentic Target-owned interval-history row with the post-movement position and native Target state. |
| Activation | `ArenaMovementActivation` identifies this Encounter and a participating actor, retains the existing movement decision ID, records start time 0, and uses `first_player_movement`. The strict existing activation validator also requires `initiated=True`, Arena activation enabled, and no first-Choice or target-directed initiation record. |
| RNG | The committed interval's RNG snapshot equals the private Encounter `RNGCursor` state. Existing exclusive-cursor ownership checks run; that exact final state is included in the descriptor. |
| Observer evidence | Both observer-owned revision-65 ledgers still pass the separate native ledger adapter. Their current evidence and ordered history remain in the checkpoint inventory; the movement receipt does not regenerate or replace perception. |

The native inspector verifies committed receipt issuance/fingerprint, Encounter and boundary chronology, Target anchor and Target-history identity, full participant coverage, and the latest committed cursor. The receipt builder additionally verifies empty Action/effect coverage and that every participant has exactly one Target record. This is a target-free interval with real native movement publication, not missing or dropped Action data.

## Receipt contract

`src/checkpoint_receipts.py` adds `PortableMovementOnlyBoundaryReceipt` with the nested schema `universe.committed-movement-only-boundary/1`. It carries only the initial committed boundary and start time, participant IDs, the already-published Target records, start fences, and committed RNG state. Existing movement activation fields remain in their existing native Encounter representation and are checked through the same `_movement_activation_state` validator used by strict inventory admission; no parallel activation proof, signature, or token is introduced.

The new form is admitted only as the first committed boundary at `floor(Encounter.start_time) + 1`, and only when the exact native movement activation is present and consistent. Its participant IDs must be unique and exactly covered by sorted Being Target rows. Its start, positions, Target state, start fences, and RNG values use the existing closed encodings. It has no Action/effect fields; its `action_ids` accessor is the empty tuple for downstream inventory bookkeeping only.

`PortableBoundaryReceipt` and its nonempty Action, causal-effect, Choice-lifecycle, and Target-owned-history requirements are unchanged. A later Action-bearing boundary can follow the initial movement-only record. An Action-free record in any later position, a second Action-free boundary, or an Action-free boundary without movement activation is refused. Thus empty Actions are not a general bypass for malformed Run/Spot history.

The descriptor remains inactive data. Its rebinding plan records the participant Entity IDs and boundary; it does not issue receipts, restore native identities, or authorize continuation.

## Falsification and no-mutation checks

The generated Arena regression validates the movement-only descriptor and its rebinding plan, then rejects malformed nested version, noninitial boundary, empty participant set, missing Target coverage, duplicate Target coverage, and a repeated Action-free receipt. It also temporarily substitutes an unissued copy of the native `PublishedInterval` and disables the movement activation flag; both are rejected by existing receipt-authentication/activation consistency checks, and the authentic source values are restored.

Before and after the exact capture and these refusal probes, the test compares Encounter time and processed boundary, both Beings' full-precision positions, postures and facings, activation records and flags, the accepted session movement plan, RNG state, ChoiceBook counter/revision/drafts/registered/choice/state maps, pending/finished/cancelled Action queues, committed interval history, Encounter Awareness, and both observers' current and historical evidence. The comparison is unchanged. The existing Action-bearing Run/Spot receipt tests remain controls for nonempty Action, effect, lifecycle, Target, Choice, RNG, and forged-history cases.

## Next dependency

The exact capture now fails at `src/checkpoint_adapters.py` while closing the selected native Being graph. That code requires each `BeingInstance.original` to be the exact `BeingDefinition` object indexed under its type in the world's registered `Library.being_dictionary`. The generated Arena's Being original fails that identity lookup. The strict check is retained; this increment does not register, replace, or alias generated definitions to make capture pass.

The candidate also continues to report existing `receipt_rebinding_required` and `semantic_closure_adapter_incomplete` diagnostics. Beyond the immediate Being-definition identity mismatch, live restoration still needs the authorized native Encounter reconstruction and required receipt/Target identity rebinding, an exact cross-process RNG/Choice owner contract, and the session-owned `_MovementPlan` (destination, rate, facing policy, and decision identity). Observer-ledger continuation and transactional atomic publication must remain validated through those steps. No save/resume claim is made.

## Validation

Commands ran from the repository root with Python 3.14.3 and `PYTHONPATH=src:tests:examples:../npc-generator`, unless stated otherwise.

| Command | Result |
| --- | --- |
| `python -m unittest test_checkpoint_arena_perception test_checkpoint_receipt_descriptors test_arena_checkpoint_activation test_checkpoint_adapters -q` | 61 tests passed in 24.764 s. Covers the real movement-only boundary, malformed descriptor variants, strict capture's next refusal, activation consistency, existing Action-bearing Run/Spot controls, and ledger adapters. |
| Exact boundary-1 test `test_checkpoint_arena_perception.ArenaPerceptionCheckpointTests.test_activated_capture_closes_action_free_receipt_and_reaches_next_blocker` | 1 test passed in 0.610 s after adding the complete state immutability comparison. |
| Adjacent checkpoint, reconstruction, movement, atomicity, activation, inspection and perception command: `python -m unittest test_encounter_inspection test_checkpoint_inventory test_checkpoint_envelope test_checkpoint_reconstruction test_checkpoint_restore_preparation test_checkpoint_restore_continuation test_movement_intent test_atomic_publication test_arena_target_free_activation test_arena_state_activation test_perception -q` | 204 tests ran: 197 passed and 7 errored during legacy `test_perception` setup because its relative `../src/config/*.tsv` paths are resolved from the repository root. No implementation assertion failed in those seven cases. |
| Legacy perception rerun from its expected working directory: `PYTHONPATH=../src:../examples:../../npc-generator python -m unittest test_perception -q` (run from `tests/`) | 7 tests passed in 0.046 s. |
| `python -m py_compile src/checkpoint_receipts.py src/checkpoint_adapters.py tests/test_checkpoint_arena_perception.py tests/test_arena_checkpoint_activation.py tests/test_checkpoint_receipt_descriptors.py` | Passed. |
| `git diff --check` | Passed. |

No loopback-dependent HTTP test was needed or run; no elevated test execution was requested. No full repository suite or fresh-process restoration was attempted because strict capture remains partial at the Being-definition identity gate.

## Commit

- `9f26dd3` — `Describe initial movement-only Arena receipt`
- The report is recorded in its own documentation commit.

No NPC Generator source was changed. Pre-existing unrelated worktree changes were preserved. No push was made.
