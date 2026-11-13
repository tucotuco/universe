# U-ARENA-004P — Checkpoint closure for Arena activation and hex facing

## Result

The bounded native Run/Spot checkpoint now classifies the Encounter activation
fields and `BeingInstance.hex_facing` explicitly. It preserves accepted
unknown/authored facing states through fresh reconstruction and identity
binding, and refuses Arena activation or target-directed initiation states
that its current reconstruction path cannot resume. This is not general Arena
save/load. The adapter suite retains one independent dangling-equipment
diagnostic mismatch; it is documented below and was not broadened into this
change.

No unrelated working-tree material was staged or modified. The starting
checkout was `<LOCAL_HOME_PATH>`, branch `main`, at
`1777841695c1a69e49cb32be6a9b8aed6766a2df` (`1777841 Document native hex
facing slice`). Existing user-owned tracked deletions and untracked files were
present and preserved. No files in `npc-generator` were touched and no push was
made.

## Sources inspected

- `docs/assignments/U-ARENA-004P.md`, U-ARENA-004O and U-ARENA-004I reports,
  and `docs/design/U8-Arena-destination-movement.md`.
- Encounter README and adopted r61 plus the applicable r62/r63 supplements;
  these do not establish general Arena checkpoint/resume semantics.
- `src/encounter.py`, including `ArenaActionActivation`,
  `EncounterInitiation`, `arena_activation_enabled`, and the initiation/step
  paths; `src/being.py` and `src/hex_facing.py` for validated native facing.
- Checkpoint field/catalog/inventory, closure, candidate validation, binding,
  wire, envelope, and reconstruction code under `src/checkpoint_*.py`.
- The three requested checkpoint suites, the bounded-closure suite, movement
  and reproduction checkpoint tests, and atomic-publication regressions.

## Failure classification before edits

The three assignment-named suites were run with
`.venv/bin/python -m unittest discover -s tests -p '<suite>' -q` from the
repository root, before modifying source or tests. The actual failures showed
that activation-field rejection occurred in closed Encounter inventory
validation before the Being facing field was reached.

| Suite | Starting result | Root cause classification | Disposition |
|---|---:|---|---|
| `test_checkpoint_adapters.py` | 42 tests: 22 errors, 4 failures | The errors arose from the Encounter field allowlist rejecting `arena_activation` and `arena_activation_enabled`. Three failures were downstream expected-diagnostic assertions masked by that early rejection. One separate failure expected `dangling equipment`, but capture raised `EvaluationIntegrityError: unknown transitive Object identity` first. | Added the missing Encounter inventory contract and retained the independent dangling-reference failure for separate work. |
| `test_checkpoint_identity_binding.py` | 10 tests: 8 failures | Fixture capture stopped at the same strict Encounter allowlist, before identity binding reached the payload. | Corrected the contract; added binding coverage for `None` and authored facing. |
| `test_checkpoint_reconstruction.py` | 6 tests: 6 errors | Fixture capture stopped at the same Encounter allowlist, before reconstruction. | Corrected the contract; added fresh and separate-process facing reconstruction assertions. |

History inspection established that the two Arena fields already existed in
`Encounter` and the closed checkpoint adapter omitted them at pre-004O commit
`87d4203`; therefore that failure predates the facing change. The `hex_facing`
field and its general checkpoint binding/reconstruction were introduced by
004O, but 004O did not classify that new authoritative field in the Run/Spot
semantic closure. The `CommittedBoundaryRecord.projectile_states` field was
also already present (commit `ac4573d6`) and absent from its closed inventory;
the suite exposed this next inventory gap after Encounter validation was
repaired. Both closure omissions were corrected explicitly. I did not rewrite
or reset repository history.

## Contract and implementation

The checkpoint remains the existing bounded initiated Run/Spot checkpoint.
The closed Encounter inventory now includes both activation fields, the exact
fields of `ArenaActionActivation`, and the complete Encounter semantic closure
classification. The flag is required to be an exact Boolean. The accepted
subset has `arena_activation_enabled is False`, no `arena_activation`, and no
target-directed `initiation`. A non-null activation record is rejected because
the bounded reconstruction path does not restore its accepted Choice and
activation execution state. A target-directed initiation is rejected
separately, so it is not confused with target-free Arena activation.

An unstarted Arena (`initiated is False`) cannot enter this checkpoint path:
the existing capture preflight requires an initiated Encounter. An
activation-enabled Encounter is also explicitly refused by closure validation
and by wire binding/reconstruction, including an enabled state with no
activation record. The code never silently resets activation fields or
pretends an executing Arena has been resumed. The tests verify capture refusal
without mutating the source state.

`hex_facing` is required in the closed Being inventory and semantic closure.
For accepted snapshots, only `None` or an exact integer in `0..11` is valid;
`bool` is rejected despite being an `int` subclass. Capture, identity binding,
and fresh reconstruction preserve both explicit unknown and authored values;
reconstruction uses `set_hex_facing`. A missing field or malformed value
fails closed. Existing historical payloads without the newly required fields
are not migrated. The Run/Spot field-closure certificate is versioned from
`/1` to `/2`, and both envelope and wire validation require the new version.
The narrower reproduction/Being checkpoint remains unchanged and continues
its deliberate known-facing refusal.

The durable Arena movement design now records this checkpoint boundary in
`docs/design/U8-Arena-destination-movement.md`. No generation, GUI, movement,
perception, geometry, strategy, general persistence, or provenance behavior was
added.

## After results

All commands ran from the repository root using the project `.venv`.

| Command | Final result |
|---|---|
| `time .venv/bin/python -m unittest discover -s tests -p 'test_checkpoint_adapters.py' -q` | 47 tests: 46 passed, 1 failure, 0 errors, 0 skips; 18.831 s wall. Remaining failure is the independent dangling equipment diagnostic mismatch described below. |
| `time .venv/bin/python -m unittest discover -s tests -p 'test_checkpoint_identity_binding.py' -q` | 11 tests passed; 9.953 s wall. |
| `time .venv/bin/python -m unittest discover -s tests -p 'test_checkpoint_reconstruction.py' -q` | 7 tests passed; 3.147 s wall. Includes fresh-object and separate-process reconstruction of `None`, `2`, and `11` facing values. |
| `time .venv/bin/python -m unittest discover -s tests -p 'test_checkpoint_bounded_closure.py' -q` | 7 tests passed; 3.464 s wall. |
| `time .venv/bin/python -m unittest discover -s tests -p 'test_movement_intent.py' -q` | 16 tests passed; 3.101 s wall. |
| `time .venv/bin/python -m unittest discover -s tests -p 'test_reproduction_being_checkpoint.py' -q` | 13 tests passed; 1.985 s wall. |
| `time .venv/bin/python -m unittest discover -s tests -p 'test_atomic_publication.py' -q` | 70 tests passed; 40.186 s wall. |
| `.venv/bin/python -m py_compile ...` for all touched Python sources/tests | Passed. |
| closure coverage check for Encounter and BeingInstance | Exact: Encounter 39 allowed / 39 classified; BeingInstance 27 / 27; no missing or extra fields. |
| `git diff --check` | Passed. |

The remaining adapter failure is
`test_dangling_equipment_and_possessions_refuse`: its assertion expects a
`ValueError` containing `dangling equipment`, while the earlier action
evaluation preflight raises
`action_evaluation.EvaluationIntegrityError: unknown transitive Object
identity`. This is independent of Arena activation and facing. Changing
traversal/error precedence would broaden scope and risks weakening reference
validation, so it remains explicitly recorded rather than hidden or patched.

The full repository suite was not run. The three assignment-mandated suites
were rerun; adapter tests are not fully green because of the one independently
classified failure above.

## Commits and next slice

Implementation, regression tests, and the durable design update are in commit
`6b6453d` (`Reconcile bounded Arena checkpoint fields`). This report is
committed separately. No push was made.

Recommended next slice: decide and implement the native activation/Choice
state needed to resume an activated Arena, including its transactional
publication/rollback and observer projection contract, then extend the bounded
checkpoint only to that complete state. Keep target-directed Encounter
initiation a distinct state. Treat the dangling-equipment diagnostic as a
separate checkpoint-reference issue with its own invariant and regression.
