# U-PER-SCALE-001 — Engineering report

**Status:** ACTIVE; extended persistence work is implemented and verified, pending ChatGPT review. Do not archive or mark the assignment complete before acceptance.

**Program:** U-PER-SCALE-001 is the sole ACTIVE implementation program. U-ACT-GATE-001 remains FUTURE/unpassed, U-NET-001 remains DEFERRED, and U-ACT-FULL-003 remains DEFERRED. Shield completion is the next implementation priority; ranged Actions follow the shared 3-D geometry work.

**Repository:** active Universe checkout; no push performed.

**Execution intervals (America/Los_Angeles):**

| Interval | Start | End | Elapsed |
|---|---|---|---|
| Initial implementation | 2026-11-15T16:42:40-08:00 | 2026-11-15T17:52:06-08:00 | PT1H9M26S |
| Extended operational verification | 2026-11-15T18:19:20-08:00 | 2026-11-15T19:07:16-08:00 | PT47M56S |

**Active execution time:** PT1H57M22S across the two recorded intervals. **Total calendar span:** PT2H24M36S from the first start to the final end; the gap between intervals is not active execution time.

The original interval established a fixed-size graph-reference encoding and corrected four checkpoint-adapter cases. The latest interval followed up because that first format still failed strict Save at t=91. Its results supersede the earlier report's t=67-only reliability conclusion.

## Current outcome

The t=91 concern is resolved by a second lossless checkpoint-format improvement. Ordinary strict Save/Load now succeeds for the terminal seed-14 combat encounter at t=91 and for later t=100 state; fresh OS processes reproduce the exact checkpoint and deterministic next interval. A continuous control and fresh-process branches match full serialized state, including native time, Being/Object and Action identity, HP/equipment, receipts, observer evidence and RNG continuation. The strict structural cap remains 1,000,000 nodes.

The adopted 2026-11-15 multiple-shield passive-protection rule is authoritative in the effective Encounter supplement and linked from the Encounter README. No shield behavior was implemented in this persistence assignment.

## Acceptance matrix

| Requirement | Result | Evidence |
|---|---|---|
| Reproduce ordinary strict refusal at t=91 | Met | The prior identity-only native v4 writer produced a 1,062,228-node outer checkpoint at t=91 (native payload 11,625,696 bytes; outer save 15,540,071 bytes). The unchanged ordinary loader refused it with `native Arena state exceeds structural limits`. The analysis input was preserved outside the repository as a temporary artifact, not in user save storage. |
| Correct structural amplification without dropping history or relaxing limits | Met | Native schema `/5` and outer save schema `/9` use a per-checkpoint sorted scalar-string symbol table, compact typed-string indices, and flattened ordered-map/field pairs. Decode first applies the unchanged strict tree/depth/byte admission to the compact wire form, validates indices and pair structure, expands losslessly, then runs the ordinary graph allowlist and restoration validators. Writer admission also counts its actual emitted wire before returning. |
| Strict fresh-process Save/Load beyond the prior failure | Met | At t=91 and t=100, fresh OS processes load through the ordinary production loader, immediately re-save byte-identically, advance one interval, and produce bytes identical to uninterrupted execution at t=92 and t=101. The regression also branches at t=67 and verifies exact t=72 continuation. |
| Extended workload and preserved consequences | Met (equivalent-history clause) | The controlled seed-14 scenario resolves 91 committed intervals and 22 actual melee attacks before a combatant reaches −2 HP. It cannot lawfully continue to 64 attacks after death. It preserves all combat consequences, observers and history and is larger than the prior 67-interval/16-attack threshold; continuation to t=100/101 checks sustained post-terminal checkpoint reliability without inventing new combatants or suppressing facts. |
| Exact uninterrupted/fresh-process equivalence | Met | The regression compares full canonical save bytes at checkpoints and after continuation, and asserts stable Being/Object/Action IDs, combat HP, equipment/custody, pending/completed Action records, event receipts, observer-ledger state and RNG ownership/cursor through the production restore path. |
| Compatibility and strict rejection | Met | Exact pinned v3 native compatibility migrates; a synthetic exact pinned v4 graph fixture migrates to compact v5. Unknown fingerprints fail closed. Existing corrupt graph ID/reference/type and compact symbol/table validation regressions pass. A preserved historical v3 Arena input loads and re-saves through outer `/9`, native `/5`. An intermediate, uncommitted schema-4 fingerprint is intentionally not accepted. |
| Adapter diagnostics | Met | All four previously reported adapter cases were reproduced against pre-change baseline `e83c8f31c6583b52fbe2bc3edd9759403458bfff` and corrected narrowly; the affected adapter suite now passes 48 tests. See diagnosis below. |
| Multi-shield adoption integrated, not implemented | Met | The effective [dated Encounter supplement](../encounters/encounters-adopted-supplement-2026-11-15.md) records the adopted shared-boundary allocation and durability rule after revision 70; [Encounter README](../encounters/README.md) links and identifies it as controlling. |

## Root cause and correction

The first correction replaced repeatedly embedded traversal-path identities with fixed-size owned-node digests. That removed the dominant quadratic path-prefix amplification, but exact t=91 testing exposed a second count issue: the v4 native inventory tree had 1,062,191 nodes even though its graph node table had only 27,844 unique nodes. Repeated `('string', value)` wrappers plus nested key/value and class-field pair containers expanded the serialized tree beyond the cap. This was a genuine write/read-boundary failure; it was not a byte-limit or restore failure.

The schema `/5` compact inventory encodes the repeated typed-string vocabulary once in a sorted symbol table; negative integer tokens reference table entries. Ordered maps and class fields encode pairs as flat sequences. The decoder counts and bounds the compact serialized representation before expansion, validates the table (sorted, unique strings, at most 250,000 entries), validates each negative reference and even pair count, then reconstructs the exact prior typed inventory for the unchanged semantic validators and adapters. The format preserves every historical receipt, snapshot, observer fact, identity and RNG field. It changes representation, not simulation state.

During extension past t=100, inventory capture also encountered a separate implementation guard: it counted every scalar traversal visit against the 250,000 unique-owned-node limit. Changed capture to enforce that limit on unique emitted graph nodes while retaining recursion/depth protection and the final 1,000,000-node wire admission. Neither node limit was increased or bypassed. Native opponent scheduling after the player died was adjusted to treat the native `combatants must be able to participate` refusal as ordinary controller unavailability; it does not create a failed Action or modify native combat eligibility.

## Growth and strict-load measurements

The original v4 t=91 measurement and the compact v5 measurements below come from the same seed-14 Arena scenario and native history. Counts are decoded JSON values/containers at the production strict boundary; bytes are UTF-8 checkpoint bytes. Depth is maximum JSON nesting.

| Native time | Receipts / committed intervals | Resolved Actions | v5 tree nodes | v5 native bytes | v5 outer-save bytes | Depth |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 50,459 | 641,331 | 894,217 | 10 |
| 10 | 10 | 2 | 119,824 | 1,457,325 | 1,982,243 | 13 |
| 20 | 20 | 5 | 192,544 | 2,318,829 | 3,130,915 | 13 |
| 35 | 35 | 10 | 306,421 | 3,669,555 | 4,931,883 | 13 |
| 50 | 50 | 13 | 424,468 | 5,067,485 | 6,795,791 | 13 |
| 67 | 67 | 18 | 568,655 | 6,785,608 | 9,086,623 | 13 |
| 91 | 91 | 24 | 783,335 | 9,343,874 | 12,497,643 | 13 |
| 92 | 92 | 24 | 792,017 | 9,446,046 | 12,633,871 | 13 |
| 100 | 100 | 24 | 861,473 | 10,263,460 | 13,723,759 | 13 |

At t=91, v5 is 278,893 nodes below the unchanged cap (27.9% headroom), compared with v4's 62,228-node overage. At t=100 the same history remains 138,527 nodes below cap. History is not pruned: receipts equal committed intervals at every measured boundary; the 22 melee attacks and all resulting state/evidence remain represented. The extended t=91 checkpoint is 49.25% more intervals and 37.5% more attacks than the prior t=67/16-attack failure report. Its strict save succeeds; exact future equivalence is verified at more than one post-threshold boundary.

## Adapter diagnosis against baseline

The four cases were run in an isolated checkout of pre-change `e83c8f3`; baseline outcomes were one error and three failures (`EFFF`), not new regressions.

| Case | Verified cause and narrow correction |
|---|---|
| `test_container_cycles_and_shared_entity_state_refuse` | A cyclic nested evaluation tag escaped as `RecursionError`; active container identities now cause controlled `EvaluationIntegrityError`. Shared live entity state remains refused. |
| `test_hex_facing_requires_unknown_or_canonical_integer` | Capture failed earlier because Run/Spot field closure omitted Arena-owned Disarm landing receipt. That receipt is explicitly outside the partial Run/Spot certificate; Arena persistence uses its own typed adapter, allowing the facing validator to be exercised. |
| `test_movement_activated_arena_remains_outside_bounded_checkpoint` | Expected obsolete diagnostic. The test now asserts current bounded-closure certificate, partial/non-resumable status and no mutation; completeness is not claimed. |
| `test_unstarted_arena_opt_in_is_outside_the_initiated_checkpoint_path` | Expected an interval-validation error from inventory-only capture. The test now asserts partial capture and unchanged source state; production interval eligibility is unchanged. |

## Focused verification

Focused tests only; the full repository suite was not run.

| Command | Result |
|---|---|
| `UNIVERSE_PER_SCALE_METRICS=1 .venv/bin/python -m unittest discover -s tests -p 'test_arena_persistence.py' -k extended_seed14_combat_checkpoint_stays_strict_and_continues_exactly` | 1 test passed, 293.111s. Printed all measurements above; covered t=67→72, strict t=91→92 and t=100→101 branches. |
| `.venv/bin/python -m unittest discover -s tests -p 'test_checkpoint_adapters.py'` | 48 tests passed, 21.511s. |
| `.venv/bin/python -m unittest discover -s tests -p 'test_arena_vs_arena.py' -k two_controllers_native_consequence_and_fresh_process_continuation` | 1 test passed, 11.857s. |
| `.venv/bin/python -m unittest discover -s tests -p 'test_generated_arena_browser.py' -k seeded_two_sided_browser_combat_hit_and_fresh_process_continuation` | 1 test passed, 7.490s. |
| `python3 -m py_compile src/arena_browser_session.py src/arena_native_snapshot.py src/arena_persistence.py src/checkpoint_inventory.py tests/test_arena_persistence.py` | Passed. |
| `git diff --check` | Passed before final staging; will rerun with staged audit. |

Legacy native v3 migration, pinned native v4 migration, malformed compact symbols/references, duplicate/dangling graph IDs and unsupported types are exercised in `test_arena_persistence.py`. The earlier standalone runs of those specific tests passed; they are also part of the persistence regression cohort. No whole-suite green claim is made.

## Scope, task state and preservation

- `TASKS.md` retains U-PER-SCALE-001 as the sole ACTIVE program and advances U-PER-002 with verified 101-interval evidence, pending report review. U-ACT-GATE-001 remains FUTURE/unpassed; U-NET-001 remains DEFERRED; U-ACT-FULL-003 remains DEFERRED. Shield completion is next; ranged Actions remain after shared geometry.
- The inbox check found no files under `docs/ideas/inbox/`.
- The five pre-staged user archive paths remain unchanged and excluded from these commits: deletions of U-CAP-002/U-CAP-003 assignment and report files, and the U-THROW-001 patch rename into archive. Untracked `docs/assignments/universe-arena.json` remains untouched. `.venv`, ignored `legacy/`, local saves, independent `npc-generator`, repository backups and the frozen Playtest Edition were not modified.
- No shield implementation or geometry, ranged Action, combat-mechanics, observer privacy or NPC generation work was added. Save/Load preserves represented observer evidence and combat state.

## Commits

- `5076e497d3b92cf31a77fd4d59c112ffa4fe2387` — register U-PER-SCALE-001, archive accepted U-ACT-FULL-002 assignment/report, integrate the adopted shield supplement, and reconcile program priorities.
- `240668f867bbda3469b60a34a98effc5cba3819d` — introduce compact long-running checkpoint graph identities and initial regressions.
- `17c147ad4ddab102dce52acd4cd7e301dc00a132` — earlier report closeout for the initial t=67 milestone, now superseded by this follow-up evidence.
- `d345ed525217571acbd68861c016824af69c8e80` — compact repeated-string/pair inventory encoding, unique-node capture limit correction, terminal-continuation handling, extended fresh-process regressions, and TASKS reconciliation.
- The current report is committed separately after a scoped staged audit; its commit is the report-only closeout directly following `d345ed525217571acbd68861c016824af69c8e80` in `git log`.

**Current closeout:** implementation commit `d345ed525217571acbd68861c016824af69c8e80` is verified. Assignment and report remain active pending ChatGPT review. No push was performed.
