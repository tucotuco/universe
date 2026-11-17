# Native history bridge — current findings

**Status: U-PER-SCALE-001 remains ACTIVE and incomplete.** Native Save/Load now preserves logical ReproductionGroup records and registered Being bindings by stable ID, alongside prior selected Group, PersonalHistory-fact, observation, combat, and pending-Action slices. The newest focused cases include observer-owned successful Being/Object Spot evidence and native Search/Listen continuation. The architecture and family matrix remain far from the full acceptance gate.

## Problems first

- The new native Save still stores both a whole committed receipt/Target object graph and a fact-history log. It is functional but not the requested compact snapshot + lossless independent history architecture. The tested 64-Action native Saves are 7.68/8.01/11.24 MB at 2/20/200 registered Beings; the current graph remains larger than the independent fact history. A 200-quiet-boundary history was reduced 86.28% by eliminating repeated RNG tuples, but the graph is still about 4.84 MB. No full proportional-growth or cutover claim is made.
- Family closure remains incomplete. The native tests cover pending Delay, Dagger MeleeStrike, Stun interruption/recovery, StatisticalGroup facts, two observer-owned Group observations, ReproductionGroup logical facts and ObjectRegistry-bound Being identity, one PersonalHistory fact/validator continuation, and literal `EpisodeFacts` plus a bound listener account for completed AskAboutPast. Reproduction linked-Being identity is preserved but has not yet continued through all supported realization workflows. Other supported Actions, movement/equipment variations, PersonalHistory mutation/query parity, Arena-perception observer APIs, cross-Encounter ownership and historical consumer parity remain unverified or unsupported. LocationEvidenceLedger and ObjectObservationLedger now have focused fresh-process tests.
- `export_save()` can persist external observer recipients only when the host passes explicit `RecipientBinding` values. Missing bindings fail closed. Ordinary app/Arena Save/Load has not been cut over to this API; `/12` behavior remains unchanged.
- The portable graph is source-compatible and includes Library definitions through its graph, but the new native schema has not yet demonstrated legacy `/10`–`/12` migration, the complete adversarial/corruption portfolio, or crash recovery for an incremental durable journal.
- There is no adopted-rule ambiguity or external dependency blocking this work. The remaining scope is engineering: expand safe family adapters/tests, normalize history without losing inspection semantics, prove scale and compatibility, then integrate behind the existing reader.

## Current architecture and verified behavior

`src/native_history.py` records an initial inspection projection, ordered atomic presence/value deltas, Action/Event/Effect causality, timing, RNG state, target/objective facts and observer projections. `NativeHistoryRecorder` appends after successful native publication only. First native export idempotently attaches a recorder; strict load verifies and restores the authenticated recorder so future committed boundaries append automatically. It does not resolve Actions. Native query integrity, preimages, order, duplicate IDs, append ownership and rollback behavior have focused tests.

`src/native_persistence.py` is a headless byte/file API. It uses `src/native_graph_snapshot.py` with schema `universe.native-encounter-graph/1`, not the Arena `/12` tag allowlist. It strictly checks the closed `FIELD_ADAPTERS` schema, graph references, portable callback recipe vocabulary, durable observer bindings, canonical bytes, duplicate keys, size/depth/node bounds and outer digest. Restore preserves logical IDs, reconstructs `StatisticalGroup` keyed RNG, `RealityLedger` validators, `PersonalHistory` validators, recipient identity anchors, ReproductionGroup facts and Being request bindings, native receipts and progression ownership without rerunning Actions. A separate combined Reproduction/Being checkpoint advances to v4 to represent the already implemented `BeingInstance.size_category` field while retaining strict v1–v3 readers. The old `src/arena_native_snapshot.py` import remains a compatibility shim for unchanged `/12` callers.

### End-to-end scenarios

| Scenario | Evidence |
|---|---|
| Pending Delay Choice | Fresh process loads, checks the pending Choice and continues with `Encounter.step(1)`; time, RNG, HP, logical IDs, receipt and history digest match. |
| Consequential Dagger MeleeStrike | Native damage commits; another strike remains pending; fresh process continues with matching HP, RNG, Action identity, receipt and history. |
| Stun interruption/recovery | Seeded native Stun commits `stunned_until`, interrupts a later accepted strike, and strict fresh-process continuation reaches recovery with exact state/history match. |
| StatisticalGroup | Captured committed household count and composition survive fresh-process Load; keyed queries return the same facts and a new native Delay continues with matching history and RNG. |
| Two observers of a StatisticalGroup | Two separately bound `BeliefLedger`s retain distinct owner IDs, evidence and Action references. Fresh-process Load validates both private ledgers, then continues natively with exact receipt/history match. Process-local `ledger_identity` and `RecipientIdentity.object_identity` values are rebuilt, not persisted. |
| AskAboutPast testimony | The adopted literal `EpisodeFacts` recipe is retained; one explicitly bound listener account carries its HeardAccount, owner ID and account-recipient Action identity through Save/Load. A fresh process continues with native Delay and matches RNG, account record and normalized native history. Arbitrary callback functions remain refused by the existing objective evaluator. |
| ReproductionGroup and native Being binding | A world authors a logical group and exact-ID native Being before creating an Encounter. Native Save restores the group's parent/offspring facts, the same `C1` Object identity, and the materialization request keyed to that exact restored Being in a fresh OS process. Separate native Delay execution continues at the next boundary. |
| PersonalHistory | A committed historical Fact and its owner validator survive a native Save and fresh-process Delay continuation. This does not establish PersonalHistory mutation-history/query parity. |

Group/observer acceptance was enabled by a narrow, exact recipe correction: the statistical-group RNG factory now has a stable reviewed closure code; native restore rebinds Group and PersonalHistory validators and the keyed provider, restores subject-ledger and recipient pointer anchors, and checks recipe multiplicity/owners against restored runtime objects. A historical projection had also retained `SubjectRealityCandidate.ledger_identity`, a process address; the projection now omits it and resolves the owner by stable subject ID. No Group sample or native Action was regenerated during Save/Load.

## Production boundary and compatibility

`src/arena_persistence.py` remains production `/12` and still requires `GeneratedArenaSession`. Its decoder/restore imports the compatibility shim, which delegates its existing default Arena schema to `native_graph_snapshot`; the native schema is separate. The exact pre-bridge `/12` compatibility tuple is retained for migration into current code. Focused v10/v11 archive migration, compact graph corruption, and exact segmented archive tests pass after the refactor. This does not yet prove that the new native API accepts those legacy files or that ordinary Universe/Arena interfaces use it.

## Verification in the current continuation

| Command | Result |
|---|---|
| `.venv/bin/python -B -m unittest discover -s tests -p 'test_native_persistence.py'` | 7 passed, 19.123 s. Includes Group facts, observer-owned evidence, three existing continuation families, duplicate-key/integrity and no-overwrite cases. |
| `.venv/bin/python -B -m unittest discover -s tests -p 'test_native_history.py'` | 10 passed, 6.507 s. Includes two distinct observer history projections. |
| `.venv/bin/python -B -m unittest discover -s tests -p 'test_checkpoint_adapters.py'` | 48 passed, 20.460 s. |
| Five focused `test_arena_persistence` tests: compact native graph corruption; pinned v4 migration; v10 migration; v11 migration; exact segmented archive/partial-history refusal | 5 passed, 7.887 s. |
| `.venv/bin/python -B -m unittest discover -s tests -p 'test_persistence_capability_matrix.py'` | 3 passed (previously verified; registry contents unchanged). |
| `.venv/bin/python -B -m unittest discover -s tests -p 'test_reproduction_checkpoint.py'` | 13 passed, 0.919 s. |
| `.venv/bin/python -B -m unittest discover -s tests -p 'test_reproduction_being_bridge.py'` | 6 passed, 0.096 s. |
| `.venv/bin/python -B -m unittest discover -s tests -p 'test_reproduction_being_checkpoint.py'` | 14 passed, 1.706 s, including legacy v1–v3 reader fixtures and subprocess continuation. |
| `.venv/bin/python -B -m unittest discover -s tests -p 'test_native_persistence.py'` | 10 passed, 22.258 s, including fresh-process ReproductionGroup facts and Being binding. |
| `.venv/bin/python -B -m unittest discover -s tests -p 'test_native_history.py'` | 10 passed, 6.632 s. |
| `.venv/bin/python -B -m unittest discover -s tests -p 'test_checkpoint_adapters.py'` | 48 passed, 19.587 s. |
| `py_compile` across checkpoint adapters/inventory, native graph/history/persistence, statistical Group and affected tests | Passed in the final check for this code increment. |
| `git diff --check` | Passed in the final check for this code increment. |

The 48-test checkpoint adapter suite tests data recipes/refusals; it is not itself Save/Load evidence. The two Arena legacy migrations above exercise `/12`, not native schema migration. The combined Reproduction/Being v1–v3 tests are a separate legacy reader. The expensive full 64-Action baseline is prior evidence at 272.770 seconds; it was not rerun during this continuation.

An adjacent observer regression run initially exposed a stale test fixture: two same-observer simultaneous Group observations had no adopted Multi-action skill/priority declarations, and a generic `Action(event_type='delay')` was still asserted unsupported after Delay became a native supported family. The fixture now declares the adopted skill and penalties and checks that Delay is captured without live resolution. `test_observer_lifecycle_proposals.py` then passed all 44 tests; no simulation or observer rules changed.

## Next implementation gate

1. Add the remaining currently supported state/action families with explicit closed validators/rehydration and native legal-action continuations; do not turn matrix rows green solely from type registration.
2. Replace duplicate old receipt/Target graph persistence with lossless initial-state + commit/Event/Effect history and a complete resumable current snapshot. Reconstruct existing historical readers on demand and compare at each boundary.
3. Expand corruption, crash-recovery, multi-Encounter/RNG and legacy migration tests; prove deterministic continued behavior and observer privacy.
4. Measure quiet/action/registry scaling against `/12`, then integrate the new API into ordinary Save/Load behind a tested dual-reader strategy.

No push or `/12` implementation change occurred in this continuation. Exact code commits and repository preservation/audit evidence are in `docs/reports/U-PER-SCALE-001-report.md`.


## 2026-11-16 continuation addendum

The exact field catalog's original 152-type count is a dated measurement of its audit fixture. Subsequent reviewed implementation added five closed schemas (ChoiceDraft, ObjectObservation, ObjectObservationLedger, ObjectObservationEffect, ObjectEvidenceProjection); the current `FIELD_ADAPTERS` and executable type registry contain 157 types. The live capability matrix was regenerated from that registry and is guarded by tests. LocationEvidenceLedger and ObjectObservationLedger each have a successful provenance-checked fresh-process restoration case; Object evidence tests distinct observer outcomes and continues a native projectile. A Search-success/Listen-failure sequence with adopted explicit accessibility/audibility tags saves with a pending Listen and resumes with exact Action outcomes, awareness, RNG and native history. Native history schema `/2` uses strict references for an unchanged RNG cursor and retains a validated lossless `/1` upgrader. On the 200-quiet-boundary scenario the history record shrank from 1,547,608 to 212,318 bytes while strict fresh-process continuation remained equal. The 64-Action runner also continued exactly with 2, 20, and 200 registry Beings. The full receipt/Target graph is still stored, so full persistence criteria remain unfulfilled; there is no identified rules or external blocker.

### 2026-11-16 continuation — quiet-span history `/3`

**Problems first.** The `/2` history still recorded one row per quiet boundary (212,318 bytes for 200); every row repeated numeric scheduler, entity-boundary and time cursors despite having no Action/Event/effect or domain-state change. The enclosing graph still dominates Save size, and this improvement does not close complete state-family coverage or production integration.

`native_history/3` now stores committed `TargetCandidate` facts directly from immutable Target records instead of the derived `TargetInspection` read model. It coalesces two or more adjacent empty-event rows only when the full changed-path set consists exclusively of root time/boundary, entity inspection-boundary, or scheduler revision numeric cursors; every cursor must advance at a constant rate, participants must remain identical, and RNG must be unchanged. Spans carry the shared time/participant facts and end-state digest. Validation constrains cursor paths, preimages, range, time increments, participant shape and digest. `state_at`, `events_at`, `rng_state_at`, legacy `/1` and `/2` upgrade, and post-span append expand the exact logical boundary semantics without resolving Actions. Any changed domain field or Action/Event/Effect remains an ordinary row.

First native export now captures history locally and attaches the automatic recorder only after the complete bundle passes candidate consistency, integrity and size checks. A forced portable-size refusal confirms it leaves no recorder attached; successful export still attaches and resumes on native Load.

Standalone `native_history.write()` no longer uses the fixed `<name>.tmp` path. It creates a private unique temp beside the destination, fsyncs its contents, atomically links without replacement, fsyncs the parent directory, and cleans the temp on prepublication errors. An injected link fault left the destination and directory empty, and an immediate retry succeeded. The writer still stores one complete history object; this is crash-safe file publication, not an independently appendable journal.

The 200-quiet-boundary headless Save/Load scenario is 26,705 history bytes, 6,477,004 bytes total; strict fresh-process Load and Delay continuation matched uninterrupted control at **50.015s** scenario, **2.828s** export, and **3.110s** fresh-process Load+continue. Relative to `/2`, history fell **87.42%** and total Save fell **2.79%**; relative to `/1`, history fell **98.27%** and total Save fell **19.02%**. The 64-Action fresh-process comparisons also passed under `/3` with 2/20/200 registered Beings: each committed 129 boundaries and retained 1,171,895 history bytes; Save sizes were 7,627,390/7,951,582/11,179,594 bytes, and fresh-process Load+continue took 6.743/6.600/7.485s. Same-Encounter Action identities and objective continuation matched in all three runs.

Focused verification: `test_native_history.py` **14 passed in 14.242s**; `test_native_persistence.py` **17 passed in 54.646s**; capability matrix **3 passed**; the previous related increment's field-registry **30**, adapter **48**, and Arena legacy integrity/pinned-v4/v10/v11 **5** tests were green. The current `/3` 64-Action runs at 2/20/200 registered Beings and 200-quiet-boundary fresh-process run passed. No user-rule or external blocker is identified. History remains a parallel query record beside the runtime graph; this slice is committed separately and does not authorize cutover.

### Full-capability continuation — every-boundary verification

The scale acceptance runner now compares reconstructed history against the live committed receipts at every logical boundary before exporting a Save. For each boundary it checks the exact TargetCandidate map, time and boundary number, schedule, objective facts and use, projectile state, ordered Action and Effect identities, and RNG cursor. Quiet spans are queried at each covered boundary. The 64-Action Dagger Feint run checked all **129** native boundaries; a 200-quiet-boundary run checked all **200**. Each strict fresh-process Load and Delay continuation matched the uninterrupted control.

| Scenario | Boundaries checked | Graph | History | Save | Scenario / export / fresh continuation | Peak RSS |
|---|---:|---:|---:|---:|---|---:|
| 64 Dagger Feints | 129 | 4,842,737 B | 1,171,895 B | 7,629,026 B | 77.348 / 23.233 / 5.893 / 7.766 s | 176,717,824 |
| 200 quiet boundaries | 200 | 4,837,012 B | 26,705 B | 6,476,204 B | 45.081 / 1.279 / 2.764 / 3.472 s | 162,955,264 |

Timing column order is simulation / historical queries / Save export / fresh-process Load+continue. Query time measures the explicit per-boundary state/Event/RNG comparisons.

Verification: `test_native_history.py` **15 passed in 17.755s** (including a checker positive case over Action and quiet-span boundaries and a deliberate mismatch refusal); `test_native_persistence.py` **17 passed in 60.984s**; capability matrix **3 passed**; both scale runner commands passed; Python compilation and `git diff --check` passed. These results supersede prior timing/byte measurements for the 2-Being current `/3` action and quiet fixtures only. They improve history-fidelity evidence but do not make the runtime receipt/Target graph redundant, close other historical readers, or demonstrate production integration. U-PER-SCALE-001 remains ACTIVE and no rule or external blocker is identified.
