# U-THROW-006 — Native Spot observes an airborne Object

**Result:** Complete within the assigned scope. Implementation commit: `c9fe309bc38de42ad6f0a979d196b22a385c0d11` (`Add transactional Spot evidence for flying Objects`). No push.

## Demonstrated chronology

`examples/native_throw_spot.py` extends the existing native Throw/Run scene. The Throw releases the Object at t=4; a separate native Run and projectile movement commit at t=5; two ordinary six-second Spots that started at t=0 resolve together at t=6, after the Object has moved to `(21.873386730586, 0.0, 3.6259867305859963)` meters. With the explicitly authored fixture geometry, transparent projectile occlusion, target DC 15, and seed 5, the normal checks roll 20 and 9: the first Spot succeeds and the second fails. Only the successful Spotter receives Awareness and one immutable, owner-held Object observation recording the Object identity, t=6 position, boundary/time, causal Action, and existing `in_flight` status. The Runner receives no automatic knowledge. The Object lands at t=7; the historical t=6 observation remains unchanged.

The example labels committed Encounter views as developer/GM ground truth and reads Agent-relative evidence only from that Spotter's own `ObjectObservationLedger`. It does not report a Spot skill or award Spot XP. The t=6 receipt contains both Spot Action identities; Throw and Run results remain in their original boundary receipts.

## Changes

- Added `src/object_observation.py` with a frozen `ObjectObservation` and observer-owned ledger. This records only the modeled Object position and optional native projectile status; lookup returns historical evidence and never reads current Reality.
- Extended native `SpotAction` scheduling and its declaration signature with an optional, owner-validated Object evidence ledger for a participating native Object. The existing Spot evaluator remains responsible for the ordinary roll, DC, visibility and Awareness.
- Extended frozen evaluation, observer candidate validation, atomic publication and committed inspection with typed Object evidence effects/projections. Projectile status is derived from the existing flight descriptor at the evaluated integer boundary. Evidence is published in the same interval transaction and receipt as the successful Spot.
- Committed inspection now resolves recipient handles for accepted future Actions as well as already-resolved Actions. The candidate can carry unchanged recipient projections for pending Actions before their resolution.
- Added `examples/native_throw_spot.py`, `tests/test_native_throw_spot.py`, and bounded status entries in `TASKS.md` and `docs/tasks/encounter-engine.md`.

## Verification

- New focused tests: **5 passed** (`PYTHONDONTWRITEBYTECODE=1 python -m unittest tests.test_native_throw_spot -v`).
- Directly affected regression set: **374 passed** in 143.438 s (`PYTHONPATH=tests PYTHONDONTWRITEBYTECODE=1 python -m unittest test_native_throw_spot test_native_throw_arena test_native_throw_concurrent_run test_throwing test_spot_action test_spot_group_evidence test_group_observation_action test_group_spot_world_realization test_transactional_group_member_spot test_belief_revision test_action_evaluation test_action_settlement test_action_choices test_interval_staging test_atomic_publication test_encounter_inspection`). This includes Spot failure, evidence isolation, read-only inspection, target/effect provenance, Throw/Run flight, and publisher rollback/retry coverage.
- Runnable example: **passed** (`PYTHONDONTWRITEBYTECODE=1 python examples/native_throw_spot.py`); printed the t=4 through t=7 chronology and observer-specific evidence described above.
- Python compilation: **passed** for all nine changed Python files (`python -m py_compile` on the changed source, example, and test files).
- `git diff --check`: **passed**, including the staged implementation diff.
- One initial grouped unittest invocation omitted `PYTHONPATH=tests` and produced three import-loader errors for sibling test modules. Rerunning the same set with the repository's required test-module path passed all 374 tests; no test was removed or weakened.
- The complete suite was not rerun, as directed. The prior U-THROW-005 full discovery reported 1,759 tests with 43 failures and 125 errors. The prior report attributes some failures to unavailable loopback binding and moved documentation, but leaves other failures unclassified; this report makes no global-green claim.

## Spatial precision note

The active revision-61 text says movement-state coordinates are committed to 0.1-meter precision. Revision-62 says that adopted metric precision is unchanged. The existing native U-THROW-005 example and this slice preserve the committed Run position at x=101.25 m after a 1.25 m displacement. This is a confirmed rule/source discrepancy. U-THROW-006 does not change global coordinate rounding.

## Preservation

The implementation commit contains exactly the scoped 11 paths: seven source files, one example, one test file, and two task-status documents. No unrelated paths were staged. The pre-existing tracked documentation deletions and untracked `.agents/`, `.claude/`, assignment/design/encounter documents, `legacy/`, saved examples, workspace JSON, archive, and other files were left untouched. Repository remains on `main`; the report closeout is committed separately. No push was performed.

## Limits

This is a narrow native Object Spot evidence adapter, not a general Entity perception model, category-directed search, Event observation, sustained Attention, prediction, or persistence format. It reports only the Object identity, snapshot position, and already modeled projectile flight status; it does not create new sensing checks or rules.
