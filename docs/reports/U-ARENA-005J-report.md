# U-ARENA-005J — Activated Arena checkpoint investigation

## Outcome

The requested cross-process save, restore, second-boundary continuation, and
uninterrupted-run comparison are **not achieved**. The first strict native
checkpoint capture of a normally generated Arena after its first movement
boundary refuses before producing a checkpoint candidate. The refusal is
`CheckpointRejected: unknown native fields: being.BeingInstance:
_arena_perception_ledger`.

I did not remove or reset the ledger, strip activation state, write a native
object dump, or treat the existing quarantined inspection candidate as a live
Encounter. The activated run remains at its committed first boundary when
capture refuses. No checkpoint file is written, no second Python process is
asked to restore it, and no resumed execution is claimed.

## Work completed

- Added `arena_activation`, `arena_activation_enabled`, and
  `arena_movement_activation` to the historical detached Spot candidate's
  exact Encounter field inventory. That six-boundary candidate now explicitly
  requires activation to remain disabled and both activation records to be
  `None`. It continues to reject live Arena activation; this is a closed-field
  regression repair, not support for activated-state persistence.
- Updated the quarantined native Being reconstruction's exact field contract
  for the already-adopted `_posture` and `hex_facing` state. It retains those
  values and rejects unsupported posture/facing values. The historical
  candidate remains a quarantined inspection view with no live Encounter or
  continuation authority.
- Added a generated-Arena regression that activates by destination movement,
  commits one second, verifies nonzero movement and the two independent
  observer ledgers, then proves strict checkpoint refusal leaves time,
  position, movement plan, RNG cursor, and both evidence histories unchanged.
- Kept exact failure coverage for attempts to pass activated Encounter state
  through the old detached Spot candidate. Updated two adjacent assertions to
  recognize the shipped native inspection keys and its earlier, equally strict
  dangling-identity refusal.

The native movement activation record has the encounter ID, player ID,
movement decision ID, activation time, and `first_player_movement` kind. It
marks the first accepted target-free movement as the start of transactional
progression without creating an Action or Choice. The separate Action
activation record represents a first player Choice. Neither record may be
recomputed or discarded during restoration.

## Reproduction and observed state

Run from the repository root:

```sh
PYTHONPATH=src:examples:<LOCAL_HOME_PATH> python - <<'PY'
from arena_browser_session import GeneratedArenaSession
from checkpoint_inventory import capture_checkpoint_candidate

session = GeneratedArenaSession(root_seed_factory=lambda: 20261120)
session.generate({"starting_experience": "10000", "width_cells": "5", "height_cells": "5"})
candidate = session.active_candidate
encounter = candidate.encounter
player = candidate.participants[0].native.being
start = player.get_position()
origin = candidate.arena_map.layout.cell_at_position(start)
destination = next(a for a in candidate.arena_map.layout.addresses() if a != origin)
session.choose_destination({"column": destination.column, "row": destination.row,
                            "rate": "sprint", "facing_policy": "turn"})
session.advance_one_second()
print(encounter.time, encounter.last_processed_boundary, start.as_tuple(),
      player.get_position().as_tuple(), encounter.arena_movement_activation)
capture_checkpoint_candidate(candidate.universe, encounter, quiescent=True,
    rng_scope="exclusive_encounter", native_adapters=True)
PY
```

The command commits boundary 1, then exits with the exact `CheckpointRejected`
above. With the task's seed and current checkout, the generated player is a
Human with 18 HP, standing posture, facing 7, and explicit empty left and right
hand slots. Position changes from `(3.6955036030289565, 3.2004, 0.0)` in hex
cell `(4, 3)` to `(0.9306178900718578, 0.8059387340185027, 0.0)` in hex cell
`(1, 0)`, a displacement of `3.6576` yards. The movement activation record
uses decision ID `arena-movement-1`, actor equal to the generated player's
native ID, and time 0. Both observer-owned current ledgers contain the other
Being after the boundary.

| Phase | Result |
| --- | --- |
| Generate and inspect | Supported Human, positive HP, empty native hands; both Beings have independent initial Arena perception evidence. |
| Activate and commit | Native movement starts transactional Encounter progression and commits boundary 1 with nonzero displacement. |
| Capture | Refused before a valid checkpoint candidate exists: `_arena_perception_ledger` has no reviewed native checkpoint adapter. |
| Fresh-process restore | Not run; there is no portable, closed checkpoint to authorize or restore. |
| Boundary 2 and comparison | Not run; a quarantined inspection projection cannot continue the Encounter. |

For diagnosis only, capture through the inactive inventory mode
(`native_adapters=False`) returns a partial `universe.checkpoint-inventory-draft/1`
candidate. Its validation remains false. Diagnostics include two
`receipt_rebinding_required` entries for Action and Target identity anchors,
two unsupported native-value entries for observer-owned state, and
`semantic_closure_adapter_incomplete`. This inventory is not a checkpoint and
has no restore readiness.

## Exact next dependencies

1. Add a reviewed data adapter for `ArenaPerceptionLedger` and its immutable
   `ArenaPerceptionEvidence`, preserving observer ownership, durable observer
   and Entity bindings, current evidence, and boundary history. Validate those
   records against the current native world and committed boundary; do not
   reconstruct perception by observing again.
2. Extend the bounded checkpoint/import/reconstruction contract for the
   non-null movement activation and movement-only interval receipts. The
   existing `checkpoint_adapters.py` and `checkpoint_reconstruction.py` still
   reject activated/movement-activated Arenas in the Run/Spot subset. The
   movement decision and activation provenance must be authenticated and
   rebound, not replaced with a synthetic Action or Choice.
3. Persist the accepted `_MovementPlan`, currently owned by
   `GeneratedArenaSession`, with the checkpoint's authenticated session
   identity. A native Universe/Encounter graph alone cannot continue a
   selected destination plan. Preserve its destination, rate, facing policy,
   and decision ID exactly.
4. Once those closures exist, prove stable RNG/Choice ownership and receipt
   rebinding in a fresh process, then compare boundary 2 against a same-seed,
   same-input uninterrupted reference. The current detached candidate's
   process-local authorization and quarantined reconstruction do not meet this
   requirement.

No browser Save/Load control, general Arena save/load claim, new timing rule,
or change to movement/perception behavior was added.

## Validation

Commands used Python 3.14.3 and the installed `npcgen` package. The focused and
adjacent results are:

| Command or suite | Result |
| --- | --- |
| `test_arena_checkpoint_activation test_arena_state_admission` | 11 tests passed in 24.428 s. Includes strict activation refusal, stale/tamper cases, exact posture/facing restoration, generated movement, and no-mutation-on-refusal. |
| `test_arena_state_admission test_arena_state_candidate test_checkpoint_inventory test_checkpoint_adapters test_checkpoint_reconstruction test_checkpoint_restore_preparation test_checkpoint_restore_continuation test_checkpoint_receipt_descriptors test_checkpoint_identity_binding test_movement_intent` | 154 tests passed in 108.845 s. |
| `test_arena_target_free_activation test_arena_state_activation test_atomic_publication test_perception test_checkpoint_envelope test_checkpoint_wire test_arena_local_checkpoint test_arena_s7_checkpoint` | 108 tests ran; 106 passed and the two loopback HTTP subprocess tests failed to start because this environment denies binding `127.0.0.1` (`PermissionError: [Errno 1] Operation not permitted`). The separate `test_perception` run from its expected `tests/` working directory passed all 7 tests in 0.044 s. |
| `python -m py_compile` on the six changed Python files | Passed. |
| `git diff --check` | Passed before commit. |

The two environment-blocked tests were
`test_arena_local_checkpoint.ArenaOperatorHTTPContinuationTests.test_two_process_browser_save_approved_reopen_run_and_native_commit` and
`test_arena_s7_checkpoint.ArenaS7ThreeProcessHTTPContinuationTests.test_three_process_s6_s7_boundary8_matches_uninterrupted_native_run`.
No live browser test or full repository suite was run.

## Commit

- `43e7ae5` — `Keep Arena checkpoint admission exact and closed`

The repository's pre-existing unrelated changes were left unstaged. No push was
made.
