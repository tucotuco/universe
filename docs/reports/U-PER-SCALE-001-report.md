# U-PER-SCALE-001 — Engineering report

**Status:** implementation and stated acceptance evidence complete; awaiting ChatGPT review. Keep this report and assignment active until accepted.

**Program:** U-PER-SCALE-001 is the sole ACTIVE implementation program.

**Repository:** `~/Projects/universe`; no push performed.

**Start:** 2026-11-15T16:42:40-08:00

**End:** 2026-11-15T17:52:06-08:00

**Elapsed:** PT1H9M26S
**Execution interval:** one continuous interval; actual start was captured at execution start.

## Outcome

The long-running generated Arena checkpoint failure was reproduced at the original 67-second seed-14 combat boundary, explained at the graph-encoding level, and corrected without raising the one-million-node limit, dropping history, weakening validation, or regenerating Beings. The ordinary strict production loader restores a checkpoint in a fresh OS process and continues the exact same five-second future as an uninterrupted session. The checkpoint-adapter diagnostic cohort was compared with the pre-change baseline and reconciled. The adopted multiple-shield rule was integrated into the effective Encounter documentation only; no shield behavior was implemented here.

## Acceptance evidence

| Criterion | Result | Evidence |
|---|---|---|
| Establish the former strict-load failure and structural cause | Met | The generated seed-14 one-shield combat case at native t=67 was reproduced against pre-change HEAD `e83c8f31c6583b52fbe2bc3edd9759403458bfff`. The ordinary loader rejected its 1,551,653-node decoded tree with “native Arena state exceeds structural limits.” The native payload was 13,082,557 bytes and the outer save 17,482,555 bytes, both below the existing byte cap. The bottleneck was tree-node amplification, not bytes. |
| Correct losslessly while retaining strict admission | Met | Synthetic owned-node identities are now deterministic SHA-256 digests of their traversal address. Domain IDs and explicit reference edges remain unchanged. Native schema `/4` accepts only the exact prior `/3` compatibility fingerprint for migration, validates the old graph, then translates legacy path identities before normal current validation. Outer schema `/8` retains `/7` through `/4` admission. Node/byte/depth limits and allowlists were not relaxed. |
| Prove exact ordinary-loader continuation in a fresh OS process | Met | The committed regression creates the actual generated Arena, carries and dons the authored shield, runs the 67-second common-boundary history, strictly saves, then loads with `GeneratedArenaSession.load_encounter_bytes` in a fresh Python OS process. The child advances five seconds; its complete save bytes equal the uninterrupted control’s t=72 bytes. Both outputs retain 72 receipts, the same Being IDs and native consequences. |
| Demonstrate meaningful before/after growth and preserve combat/observer history | Met | See measurements below. The same t=67 fixed run retains 67 committed interval records, all 16 autonomous melee Actions, original Object identity/equipment, combat HP consequences, and observer-specific perception ledgers. A committed continuation reaches native t=91 with 22 attack Actions, when the player is at -2 HP and combat has killed them; the exact adopted seed/profile therefore cannot lawfully sustain 64 attacks. Maximum JSON depth remains 13. The fixed 768,440-node tree has 231,560 nodes of margin under the unchanged cap. |
| Verify Arena modes and strict compatibility/regressions | Met | Focused PvA, Arena-vs-Arena, generated browser/session, legacy snapshot and adapter cohorts passed; exact commands are listed below. Four adapter failures/errors were also run at baseline and classified with evidence. |
| Integrate the adopted multi-shield rule without implementing it | Met | The 2026-11-15 adoption is authoritative in `docs/encounters/encounters-adopted-supplement-2026-11-15.md`, linked from the Encounter README. It preserves revision 61/70 history and explicitly leaves multi-shield behavior unimplemented. |

### Growth measurements

The baseline is the same generated Arena seed/profile and exact sequence captured before changing the checkpoint encoder. Tree nodes count every decoded JSON value/container using the production structural walker. Depth is maximum JSON nesting. Baseline outer-save and native-payload byte counts are both shown; post-change values are explicitly identified as native-payload bytes where measured.

| Native boundary | Baseline tree nodes | Baseline outer bytes | Baseline native bytes | Fixed tree nodes | Fixed native bytes |
|---:|---:|---:|---:|---:|---:|
| t=0 | 102,612 | 1,093,665 | 790,915 | — | — |
| t=10 | 296,253 | 3,239,015 | 2,399,902 | — | — |
| t=20 | 500,971 | 5,532,839 | 4,120,270 | — | — |
| t=35 | 820,722 | 9,139,223 | 6,825,059 | 484,789* | 5,238,567* |
| t=50 | 1,149,774 | 12,876,115 | 9,627,728 | — | — |
| t=67 | 1,551,653 | 17,482,555 | 13,082,557 | 768,440 | 8,365,692 |

`*` t=35 is the actual previously accepted checkpoint loaded through the pinned v3 migration and re-saved with v4. At t=67 the comparable generated fixed scenario reduces the decoded tree by 783,213 nodes (50.5%) and native bytes by 4,716,865 (36.1%), while retaining the history and state payload. The observed uncompressed tree growth still follows retained facts/history; the pathological repeated path-prefix cost is removed rather than postponed by a larger cap. At the prior t=35 boundary the baseline passed at 820,722 nodes; by t=50 it already failed the one-million limit.

The baseline’s native graph contained about 20,329 owned nodes at t=67, but represented those nodes and their references using complete traversal paths. Repeatedly embedding each owned node’s full path in reference tuples multiplied path-prefix elements across the accumulated inspection/history graph (about 427,267 decoded values in node identity paths and about 487,828 among nested references in the instrumented breakdown). This explains why the roughly 15–19k additional decoded values per committed interval compounded into 1.55 million at t=67. The v4 token is fixed-size per synthetic node/reference, while explicit domain IDs and the graph edges remain available for identity-preserving restoration.

### Adapter diagnosis against baseline

All four cases were run in an isolated checkout of pre-change `e83c8f3` before repair; baseline outcome was one error and three failures (`EFFF`), rather than a new regression:

| Case | Baseline observation | Reconciliation |
|---|---|---|
| `test_container_cycles_and_shared_entity_state_refuse` | A cyclic nested evaluation tag escaped as `RecursionError`, which the contract did not classify as a controlled refusal. | `freeze()` now tracks active container identities and raises `EvaluationIntegrityError` for a cycle; shared live native entity state remains refused. |
| `test_hex_facing_requires_unknown_or_canonical_integer` | The capture failed earlier because the Run/Spot field closure omitted the Arena-owned Disarm landing receipt, so the intended malformed-facing diagnostic was never reached. | Marked that receipt explicitly out of scope for the partial Run/Spot certificate; the Arena checkpoint has its own typed adapter. The test now reaches and verifies the facing validator. |
| `test_movement_activated_arena_remains_outside_bounded_checkpoint` | The assertion expected the obsolete diagnostic “movement-activated Arena has no committed boundary history.” Current adapter correctly reports certified field closure but remains non-resumable/partial. | Updated the test to assert the current bounded-closure certificate plus partial status and no mutation. No completeness claim was added. |
| `test_unstarted_arena_opt_in_is_outside_the_initiated_checkpoint_path` | The assertion expected `IntervalIntegrityError`, although inventory capture does not resolve an interval or enforce initiated Encounter timing. | Updated the test to verify inventory-only partial capture and unchanged source state. The production interval rule is unchanged. |

## Focused verification

All commands used the preserved repository `.venv`; no whole-repository suite was run.

| Command | Result |
|---|---|
| `.venv/bin/python -m unittest discover -s tests -p 'test_checkpoint_adapters.py'` | 48 tests passed, 20.439s. |
| `.venv/bin/python -m unittest discover -s tests -p 'test_arena_persistence.py'` | 12 tests passed, 163.163s. Includes t=67 strict save, fresh-process exact t=72 continuation, and the t=91 terminal/22-attack bound. |
| `.venv/bin/python -m unittest discover -s tests -p 'test_arena_vs_arena.py' -k two_controllers_native_consequence_and_fresh_process_continuation` | 1 test passed, 11.349s. |
| `.venv/bin/python -m unittest discover -s tests -p 'test_generated_arena_browser.py' -k seeded_two_sided_browser_combat_hit_and_fresh_process_continuation` | 1 test passed, 7.082s. |
| `python3 -m py_compile src/action_evaluation.py src/arena_native_snapshot.py src/arena_persistence.py src/checkpoint_fields.py src/checkpoint_inventory.py tests/test_arena_persistence.py tests/test_checkpoint_adapters.py` | Passed. |
| `git diff --check` | Passed. |

The new regression also rejects corrupt graph references and identity encodings: duplicate identities, dangling references, malformed owned-node digests, and unsupported type tags. Existing `/3` legacy input was admitted only under its exact pinned source/rule/runtime compatibility fingerprint, migrated, and emitted in the current representation. A different/unknown fingerprint still fails closed.

## Scope, limits, data preservation

- The one-million-node structural admission limit, 250,000-node inventory cap, 64 MiB byte cap, depth guard, graph allowlist, strict checksum/canonical JSON checks, and no-mutation behavior remain unchanged.
- No combat, shield, observer-privacy, Arena scheduling, or NPC generation rule was changed. U-ACT-FULL-003 remains deferred. The multi-shield rule was documented but not implemented.
- U-ACT-GATE-001 remains FUTURE/unpassed; U-NET-001 remains DEFERRED; U-PER-SCALE-001 remains the sole ACTIVE program pending review.
- The staged historical U-CAP archive changes and untracked `docs/assignments/universe-arena.json` were preserved and excluded from these commits. The working `.venv`, ignored `legacy/`, local saved-world data, independent `npc-generator`, backups, and frozen Playtest Edition were not modified.
- The idea inbox was absent at startup; it will be checked again before the final TASKS commit.

## Commits

- `5076e497d3b92cf31a77fd4d59c112ffa4fe2387` — register U-PER-SCALE-001, archive accepted U-ACT-FULL-002 assignment/report, integrate the dated shield adoption, and reconcile program priorities.
- `240668f867bbda3469b60a34a98effc5cba3819d` — compact long-running Arena checkpoint references; includes focused regressions and the U-PER-002 status reconciliation in TASKS.md.

### Closeout audit

The implementation and TASKS reconciliation are committed as `240668f867bbda3469b60a34a98effc5cba3819d`. The report-only commit was separately staged and scoped; `git diff --cached --check` passed and `python3 tools/check_publication_safety.py --staged` reported `files=7 findings=0 result=PASS` (the five pre-existing user archive paths remained in the staged set). Exact final HEAD/report commit is recorded in the Codex closeout. The unrelated archive changes and untracked Arena save remain untouched. No push was authorized or performed.
