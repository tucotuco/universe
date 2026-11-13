# U-ARENA-005L — Minimal movement-activation checkpoint state

## Where we stand

The boundary-1 generated Arena now passes strict native inventory validation with both observer-owned perception ledgers and the existing movement-activation record represented. Capture returns a **partial, non-authorizing candidate**. It does not close the bounded receipt schema, define a portable Arena checkpoint, enable reconstruction, or authorize restoration. No fresh-process continuation or boundary-2 comparison is claimed.

The exact remaining boundary is the receipt descriptor's Action-only contract:

```text
Run/Spot receipt closure refused: missing, duplicate, or unreceipted committed Action
```

The first accepted movement is intentionally target-free and creates no Action or Choice. Its committed interval therefore has an empty Action identity sequence, which `describe_committed_receipt_chain` rejects at `src/checkpoint_receipts.py` before it can describe the boundary. This is the next genuine save/resume blocker. The candidate preserves this failure as a diagnostic; it does not manufacture an Action, Choice, or receipt link.

## Dependency audit and persistence treatment

| Existing field/reference | Actual role established from code | Minimum treatment in this increment |
| --- | --- | --- |
| `Encounter.arena_activation_enabled` | Selects Arena activation/transaction behavior and participates in native publication and observer-ledger handling. | Preserve the exact Boolean. A false value with a movement activation record is inconsistent. |
| `Encounter.initiated` | Enables progression of an activated Encounter. Movement activation sets it before transactional progression is enabled. | Preserve and require `True` when the movement activation record is present. |
| `Encounter.arena_activation` | Represents the separate first-player-Choice activation path. | Keep it `None` for movement activation; non-null remains outside this bounded Run/Spot subset. |
| `Encounter.initiation` | Represents target-directed Encounter initiation, distinct from target-free Arena movement. | Keep it `None`; a non-null record remains unsupported here. |
| `Encounter.arena_movement_activation` | Native typed record marking the first accepted player movement. Presence is used by activation guards to prevent a second initial activation. | Preserve all exact record fields in the closed native inventory and validate consistency with its owning Encounter. No new authorization/provenance layer is added. |
| Activation `encounter_id`, `actor_id`, `time`, `activation_kind` | Existing record consistency: the Encounter and participant must match, activation time must equal Encounter start time, and kind must be `first_player_movement`. | Validate those native references and phase facts; reject corruption without mutating live state. |
| Activation `movement_decision_id` | Stored on the native activation record and validated as a nonempty bounded string at activation. It is not consumed by subsequent native stepping and is not linked by the committed movement-only boundary receipt. | Preserve its exact value as existing native state. Do not add an authentication protocol or infer a receipt reference. |
| `_atomic_interval_history` / `CommittedBoundaryRecord` | Retains committed boundary chronology, ordered Action/effect IDs, RNG snapshot, and target anchors. | Preserve it under existing strict inventory checks. Movement activation requires committed boundary history, but the current receipt adapter cannot describe its Action-free boundary. |
| Receipt Action and Target anchors | Existing Run/Spot descriptor rebinding supports only authentic Run/Spot Actions, their Choices/effects, and Target-owned history. | Leave the descriptor strict. The movement-only empty Action set reaches its precise existing rejection; no anchor is invented or dropped. |
| `GeneratedArenaSession._movement_plan` | Session-owned accepted destination, rate, facing policy and decision identity used to continue destination movement. | Remains outside this native checkpoint candidate and is not serialized. It is an additional required dependency for a playable Arena resume after native checkpoint restoration is designed. |
| ChoiceBook and RNG owner | Native future scheduling and deterministic transactional progression are process-owned; receipt closure binds the supported Run/Spot subset to an exclusive caller cursor. | Preserved and compared during failed/partial capture. No new owner/rebinding contract is introduced here. |

The first movement remains distinct from first-Choice `arena_activation`: no Action or Choice is synthesized, and non-null first-Choice activation still refuses in this checkpoint subset.

## Implementation

`src/checkpoint_adapters.py` now validates movement activation as existing native state before serializing it. Validation requires an explicit Boolean activation flag; consistent `initiated`, movement-activation, first-Choice activation, and target-initiation phases; the exact native record type and closed fields; matching Encounter and participant IDs; a nonempty bounded decision ID; finite start-time equality; and the supported `first_player_movement` kind. It also requires a committed interval history when movement activation is present. These checks are consistency checks on the adopted record, not proof-of-origin or authentication machinery.

The capture tests now prove that the U-ARENA-005J seed-`20261120`, 10,000-XP, 5×5 Arena validates both observer ledgers and the activation record, then reports the exact Action-free receipt blocker. They compare state before and after including time, processed boundary, both Beings' position/posture/facing, activation state, session movement plan, RNG cursor, ChoiceBook and pending Actions, and both observers' current and historical evidence. Separate corruption cases cover required Encounter, actor, decision ID, time, kind, and phase consistency, and verify no mutation.

No checkpoint reconstruction or restore path was broadened. No movement plan, observer evidence, committed history, RNG, or Choice state is discarded, replayed, regenerated, or made resumable by this change.

## Validation

Commands ran from the repository root with Python 3.14.3 and `PYTHONPATH=src:tests:examples:../npc-generator`.

| Command | Result |
| --- | --- |
| `python -m unittest test_checkpoint_arena_perception test_arena_checkpoint_activation test_checkpoint_adapters -q` | 54 tests passed in 22.186 s. |
| `python -m unittest test_checkpoint_receipt_descriptors test_checkpoint_inventory test_checkpoint_envelope test_checkpoint_reconstruction test_checkpoint_restore_preparation test_checkpoint_restore_continuation test_movement_intent test_atomic_publication test_arena_target_free_activation test_arena_state_activation -q` | 161 tests passed in 106.160 s. |
| Targeted activation consistency, exact boundary-1 receipt-blocker, and activation suite | 3 tests passed in 1.508 s. |
| `python -m py_compile src/checkpoint_adapters.py tests/test_checkpoint_arena_perception.py tests/test_arena_checkpoint_activation.py tests/test_checkpoint_adapters.py` | Passed. |
| `git diff --check` | Passed. |

The first focused run exposed a stale test-instrumentation expectation of two
ledger-encoder calls; the strict inventory and receipt-closure preflight each
inspect both observer ledgers, producing four calls during capture. The
assertion was corrected and the rerun passed. This was a test expectation issue,
not an implementation or behavior failure.

No loopback-dependent HTTP test was run, so no elevated execution was required. The adjacent suite had no failures. No full repository suite or fresh-process restore was run because the receipt closure still refuses the movement-only boundary.

## Next dependency

The next increment needs a narrowly reviewed receipt representation for the already-committed native **movement-only** boundary, or a native continuation contract that safely resumes such a boundary without pretending it contains an Action. It must preserve chronology, existing target/observer history references, RNG and Choice state, and atomic-publication guarantees under strict validation. It must not manufacture Action/Choice semantics or weaken the existing Run/Spot descriptor. Once that native boundary is closed, the separate session movement plan and cross-process RNG/Choice ownership still need an exact continuation contract before a playable Arena save/resume can be claimed.

## Commits

- `7c7ed18` — `Preserve Arena movement activation in checkpoint inventory`
- `7f493ad` — `Report Arena movement activation checkpoint boundary`

No NPC Generator files were changed. Unrelated worktree changes were preserved. No push was made.
