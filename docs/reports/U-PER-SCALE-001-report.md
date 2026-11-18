# U-PER-SCALE-001 — Engineering report

**Problems first — status ACTIVE and incomplete.** Native History `/12` is paired with strict native graph `/2`; recipient recipe `/2` records and validates each stable binding's Action-field origin, while strict recipe `/1` recovery matches its stable hash to a registered Event or accepted Choice reference. `/11` captures boundary-zero Entity state at the true pre-movement start fence; `/12` adds stable recipient-store identities and graph `/2` reconstructs per-boundary observer recipient maps, typed receipt shells, ChoiceBook lookup caches, Encounter fatigue-frame display caches, and eligible projectile interval caches from validated facts. Strict history `/1`–`/11` upgrades preserve unavailable boundary-zero facts. Graph recipe `choice-book-indexes/1` now omits `_registered`/`_states` caches and reconstructs them from accepted Choices, native Actions and scheduler lists; `fatigue-frame-history/1` omits repeated Q/B frame lists and rebuilds them from committed fatigue/physiology facts; `projectile-interval-history/1` omits per-Object interval lists only when validated receipt order is unambiguous. The current snapshot and pending commitments remain complete; the 159-type field matrix is source-linked but not closed end-to-end for every reachable field/history consumer. The generated Arena HTTP Save now uses native snapshots for progressed transactional sessions and retains `/12` for all legacy-mode sessions; focused fresh-process pending/committed route coverage passes. A final focused UI smoke, broad family/query parity, corruption/security, compatibility and integration coverage remain open. No unresolved rule or external blocker is identified; remaining work is engineering. U-PER-SCALE-001 remains ACTIVE and sole.

**Latest query parity gap:** the portable Objective candidate/use facts existed, but they did not expose the cumulative `Encounter.inspect_committed().objective` consumer projection without consulting the Encounter graph. `NativeHistoryQuery.objective_inspection_at()` now incrementally folds recorded Group/PersonalHistory candidates and use rows and returns detached `ObjectiveInspection`/`ObjectiveFactInspection` records, omitting only process-local ledger addresses. It matches native inspection for Group and PersonalHistory Action boundaries, a following quiet boundary, and a fresh-process Save/Load continuation. This closes one reader contract only; the matrix remains open and production `/12` remains unchanged.

Verification for the query increment: `test_native_history test_persistence_capability_matrix test_native_persistence.NativePersistenceTests.test_personal_history_facts_and_validator_resume_in_fresh_process` passed **37 tests / 26.949s**. This includes Group/PersonalHistory Action and quiet cuts, the strict fresh-process Save/Load, full inspection parity at the saved cut and after continuation, and reverse/detached query behavior. No Action resolution or current-graph access is used by the query after capture.

The reader and focused regressions are committed as `9649ce9` (`Add graph-free native inspection reader`). The 25-family inspection comparison is committed with the existing source-linked fixtures; no production persistence writer, loader, or Arena code changed.

The composite inspection cursor also now has explicit reverse-order coverage: after reading every boundary forward, the native history regression re-reads the complete inspection from latest to earliest and checks each cut against the live source. That focused test passed **1 / 1.546s**; this adds cursor-reset evidence without changing serialized bytes.

The composite inspection cursor also now has explicit reverse-order coverage: after reading every boundary forward, the native history regression re-reads the complete inspection from latest to earliest and checks each cut against the live source. That focused test passed **1 / 1.546s**; this adds cursor-reset evidence without changing serialized bytes.

**Complete committed-inspection projection for tested histories:** the first composed-reader integration check exposed a real query-fold mistake: a compact quiet span was skipped while assembling Target history, so Targets present at those committed cuts were omitted. The query now expands each quiet boundary only while producing the read result, rebuilds TargetInspection properties from the matching Entity context and receipt facts, and folds cumulative Actions/Effects, observer bindings/accounts, objective facts/uses, schedule, timeline, and Disarm receipts. It returns the same `EncounterInspection` projection as the live native inspector with only process-local ledger addresses omitted by the existing `_plain` adapter. The native generated 25-family continuation gate checks this entire record at every committed boundary and passed **25 tests / 127.920s**. The PersonalHistory case checks full projection parity before Save, after fresh-process Load, and after native continuation as part of the **37-test / 26.949s** history/matrix/fresh-process gate. No production Save/Load path changed. This reader remains partial for families/legacy histories not represented by the current query record set.

`NativeHistoryQuery.skill_use_history_at()` now projects cumulative `SkillUse` and `BatchSkillUse` records from validated Being TargetCandidate practice facts. At the initial boundary it reads the first committed candidate's explicit pre-action `prior_uses`; it does not inspect the current Being or resolve Actions. The pending Run continuation checks boundaries 0–3 against native source state, with boundary-zero/current comparisons repeated in a fresh OS process. Repeated practice `prior_uses` remain duplicated in TargetCandidate history; this reader does not close the practice-family storage or general personal-history query gaps.

The defined-but-not-produced follow-up observer facts now have strict record-level contracts. Native history closed-tag validation round-trips `InquiryProposal`, `InquiryRecord`, and `EvidenceReassessment`; it refuses unknown decision reasons, duplicate/empty evidence identities, empty Action identities, and an interpretation tied to another observation. This covers portable record shape/value validation only. These records remain without a native Action/publication producer, and no inquiry or reassessment behavior was inferred.

Verification after the practice query and follow-up record contract changes: `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_history test_persistence_capability_matrix -v` — **36 passed / 22.929s**; `py_compile` and `git diff --check` passed. The specific pending-Run fresh-process continuation also passed **1 / 2.543s** after adding the boundary-zero query check.

Local commits: `64ecf98` adds the committed skill-use query; `51d2b6c` derives the initial pre-action projection; `5cc6f8e` adds strict defined follow-up observer-record contracts. All were scoped, staged-audited and kept separate from the five unrelated staged archival paths. No push.


## Problems-first — ChoiceBook and fatigue projections still duplicated in the graph

The `/2` graph had already replaced several per-boundary histories with authenticated native fact rows, but two further graph fields repeated derivable state. ChoiceBook `_registered` and `_states` are lookup caches: accepted Choice records retain the declarations and PreparedSchedule packets, while registered Events and the scheduler lists retain the exact identities/lifecycle. Encounter `fatigue_frame_history` repeats Q/B, physiology ID, check modifier, and each interval's start/end already recorded in the committed Entity/fatigue context. Both were omitted only after source-to-fact equality checks.

The new `choice-book-indexes/1` recipe derives registration/lifecycle indexes during strict Load, rejecting malformed or ambiguous Choice/Action/scheduler relationships. The `fatigue-frame-history/1` recipe reconstructs each frame from committed native boundary starts, Entity fatigue and versioned physiology facts; it does not recompute fatigue or resolve Actions. Existing `last_fatigue_frame` and its physiology profiles remain in the resumable current snapshot. Native graph writers without complete current-schema fatigue facts retain the full graph field; old graph recipes remain readable. Corrupt ChoiceBook cache state refuses export without attaching a recorder.

Verification: the focused affected gate `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_persistence test_checkpoint_adapters test_native_history test_native_draw_persistence test_native_scenario test_persistence_capability_matrix -v` passed **181 tests / 382.876s** after both recipes. The fatigue-focused suite, run from the expected `tests/` working directory, passed **9 tests / 0.081s**; an initial invocation from the repository root failed to load its relative test configuration and was rerun successfully in the suite's declared working directory. The fresh-process pending-Run test checks that the graph contains an empty fatigue list while the restored three-frame history exactly matches uninterrupted execution through a changing physiology profile. The ChoiceBook regression verifies export refusal on stale derived indexes, no recorder mutation on refusal, empty cache wire rows, exact future Choice/action identities and fresh-process continuation. Python compilation and `git diff --check` passed.

The 64-Action scale runner (same generated native scenario, 2 registered Beings, 129 committed boundaries) completed 64 real Feint Actions, checked every historical boundary, exported, strict-loaded in a fresh OS process, continued one Delay, and matched uninterrupted state/RNG/history. With both cache recipes enabled, the runner measured an un-compacted graph of **4,851,815 B** and a current graph of **978,015 B** (**79.84% reduction**) for 64 Actions / 129 boundaries; the Save is **2,497,216 B**. On the same source, the ChoiceBook-only candidate reduced graph bytes from 4,851,815 B to 4,839,687 B (**12,128 B**). The run took **61.246 s** for scenario authoring, **2.301 s** for all-boundary history queries, **14.017 s** to export, and **8.663 s** for fresh-process Load+continue; peak RSS was **209,993,728 bytes**. The 200-quiet-boundary current run retained **34,563 B** history, with **623,024 B** graph and **865,410 B** Save; scenario/query/export/fresh-process continuation took **41.307 / 0.941 / 3.379 / 3.443 s**, and peak RSS was **76,857,344 bytes**. Both scale runs compared the resumed continuation against uninterrupted control and passed.

Scoped implementation commits: `d4dfd3d` (ChoiceBook index derivation/compaction) and `97f9bff` (fatigue-frame derivation/compaction). These are not assignment completion: the 159-type capability matrix remains open for end-to-end reader parity and currently supported families, durable independently recoverable history, full corruption/security breadth, and normal application `/12` Save/Load cutover. No unresolved rules or external blocker is identified.

## Problems-first — compact projectile interval state where receipts determine exact order

The projectile history stored as `ObjectInstance`/`WeaponInstance._atomic_projectile_history` repeated `ProjectileBoundaryState` values already present in each committed receipt and History `/12` boundary. Recipe `projectile-interval-history/1` now authenticates the exact source list against all relevant restored `CommittedBoundaryRecord.projectile_states`, then writes an empty cache node; Load reconstructs the list from those same facts before `inspect_encounter()`. Current `_projectile_flight` remains saved. Objects without the optional field keep it absent. If one Object has states from multiple Encounter roots, no global order field exists, so Save leaves that Object history graph-backed by disabling this recipe for the bundle. This preserves existing behavior rather than imposing an unsupported ordering.

Verification and measurements: seed-116 released shielded projectile graph **805,416 B → 644,404 B**, saving **161,012 B**; complete Save **925,959 B**. The native hit/shield and miss fresh-process scenarios assert compact wire rows, exact projectile states, cached-history validation, actual committed consequences and deterministic continuation. Mutating the source list refuses Save and leaves fact history unchanged. The high-risk affected gate passed **181 tests / 381.862s**. Final strict-absence/callback-free guards then passed the focused projectile hit/miss, `/10`–`/11` migration and matrix check: **6 tests / 12.413s**, with compilation and diff checks clean. The 64-Action and 200-quiet measurements in the preceding current increment are unchanged by this Projectile-only fixture recipe. Commit `7c3a3c7` contains implementation and tests.

This remains an incomplete ACTIVE program: complete family/query parity, durable independently recoverable history, full hostile-file/resource-limit breadth and normal application Save/Load cutover are still outstanding, and no rule/external blocker is identified.

## Problems-first — authenticate recipient binding origins across graph versions

The recipient binding hash alone did not make its source reference explicit in the native graph. Recipe `/2` now stores the pinned Action-field origin with each external host binding. Strict Load recomputes the digest and verifies that the referenced registered Event or accepted Choice Action field points to the exact restored recipient. Prior graph recipe `/1` remains supported: Load recovers the origin by matching its existing digest to registered Action references and refuses when no unique match exists. The test synthesizes a valid prior-recipe Save, confirms strict migration and canonical continuation, then re-seals a forged binding identity and confirms refusal.

The full affected integration gate passed **180 tests / 423.641s**: native persistence, checkpoint adapters, native history, native Draw/Action continuations, native scenarios, and the capability matrix. The additional current/prior recipe, collision and forged-identity gate passed **7 tests / 12.721s**. `py_compile` passed for all changed modules and tests. Implementation commit `1271410` records this compatibility and integrity correction; scoped companion commits are `9bb2a23` and `045855c`. These results resolve recipient-origin validation only. The full family/query matrix, broad adversarial corpus, crash-recoverable history, production API cutover and application-level UI gate remain open.

## Problems-first — stable observer-recipient identity and history reconstruction

The owner-fact compaction could not safely use `(role, owner)` alone: two independent BeliefLedgers owned by one Being must remain distinct. The first implementation hashed all registered Action-field references, which distinguished concurrent stores but changed identity when another Action later reused the same store. Focused tests reproduced the key instability, including completed AskAboutPast receipts, multiple Encounter roots and a same-owner, two-ledger continuation.

History schema `/12` records a stable `binding_id` computed from the first canonical Action-field reference and retained in a weak per-Universe process registry. Later Actions cannot re-key a recipient. Native graph `/2` writes the stable ID in the closed host-binding descriptor, validates the descriptor shape and digest, rebinds process-local `RecipientIdentity` keys to the exact durable host object, and reconstructs per-boundary recipient projections and `CommittedBoundaryRecord` shells from authenticated history. Legacy role/owner-only recipient facts migrate only when exactly one host binding matches; ambiguous mappings fail closed. Legacy native Save verification permits only this derived identity metadata to differ: it compares state, Events/Effects, Entity context, receipt facts and RNG at every boundary before attaching the restored recorder.

This work exposed and fixed a real legacy read bug: with an explicitly unavailable initial Entity projection, `fatigue_context_at(0)` must be unavailable too. It now returns `None`, and `boundary_facts_at(0)` retains that result without dereferencing absent Entity data.

Verified after first-reference pinning: from `tests/`, `PYTHONPATH=.:../src:../examples ../.venv/bin/python -B -m unittest test_native_persistence test_native_history test_persistence_capability_matrix -v` — **100 passed / 227.780s**. The same-owner test schedules a pending later ObserveGroup Action with an earlier-sorting ID and confirms the previously persisted ledger binding does not change. A strict malformed host-binding-ID regression plus the same-owner case and full capability matrix passed **5 / 2.592s**. The adjacent `test_native_draw_persistence test_persistence_capability_matrix` run passed **28 / 129.034s**; it preceded first-reference pinning, while the final 100-test native suite exercises the current Save/Load path. `py_compile` passed for all changed Python modules/tests. The initial integration gate exposed and corrected observer-recipient restoration failures; the final full run is green. Production Arena `/12` Save/Load is untouched. Source, tests, matrix, findings and report changes are pending scoped audits and commits.

## Problems-first — exact boundary-zero Entity baseline and legacy fidelity

The prior recorder used the first committed receipt as `initial.entities`. That receipt is already post-movement when the first `Encounter.step()` moves a Being, so the historical query at boundary zero returned the post-movement coordinate. This was a native-history implementation defect; the rules and initial native snapshot already distinguish authored start state from committed movement.

Native progression now supplies the validated pre-action `EvaluationSnapshot` captured at the first transaction fence. A closed adapter detaches EntityInspection data there, including time-derived stun/subdual state at the authored Encounter start. `/11` records whether this exact start projection is available. New transactional Encounters retain it in `NativeHistoryQuery` and the resumable Save; strict `/1`–`/10` upgrades keep the old first-receipt anchor only for delta reconstruction, mark boundary-zero Entity state unavailable, and never infer or relabel it. The `/4` legacy fixture now models its fatigue-less source facts precisely. This does not change the legacy Event/Effect identities or native resolver.

Verified results:

- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_persistence -v` — **59 passed / 193.085s**, including old `/1`, `/4`, `/5`, `/6`, `/9` history upgrades, accepted graph-writer fingerprints and `/10`–`/12` Arena readers.
- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_history test_native_scenario -v` — **33 passed / 26.101s**. The movement regression proves boundary 0 at `(0,0,0)`, boundary 1 at `(1,0,0)`, and the same facts after strict Load in a fresh OS process.
- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_draw_persistence -v` — **25 passed / 136.261s**, including all-boundary native Action family and continuation comparisons under history `/11`.
- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_persistence_capability_matrix -v` — **3 passed / 0.006s** after updating the schema assertion and source-matrix Arena classification.
- `.venv/bin/python -m py_compile src/native_history.py src/native_persistence.py src/transactional_progression.py tests/test_native_history.py tests/test_native_persistence.py tests/test_native_scenario.py` — passed. Initial safety audit for implementation commit `577b34c` reported **0 findings**; the commit was scoped to the listed source/tests/docs and preserved all five unrelated staged archive paths.
- A follow-up audit found no direct `/10` native-history Save test. Added `test_native_history_v10_save_migrates_without_inventing_initial_entities`: `/10` upgrades to `/11` without publishing boundary-zero Entity data, committed boundary facts match the uninterrupted control, a fresh OS process continues through native Delay, and migrated Save→Load→Save is byte-identical. Focused result: **1 passed / 4.911s**. The matrix now requires live local source/test links for all 159 rows; the first audit found zero missing evidence links and zero broken targets, and the enforcement test passes in the **3-test matrix suite**.

Remaining acceptance is not met: complete family/query parity, durable independently recoverable history, broad adversarial security and legacy migration coverage, and normal application Save/Load cutover remain open. The matrix and native integration findings need to distinguish proven `/11` initial-state behavior from unavailable pre-`/11` boundary-zero facts. This is a verified implementation increment, not assignment completion.

## Problems-first — reconstruct committed boundary records instead of persisting graph rows

Although most receipt payloads had already moved into native history, strict Saves still carried one `PublishedInterval` and one `CommittedBoundaryRecord` graph node per committed boundary. Those nodes duplicated an authenticated commit stream and kept historical projections coupled to an object graph. The new `committed-boundary-history/1` native adapter omits both per-boundary nodes for histories whose receipt maps contain no observer-owned recipient projection. Strict Load validates native history, builds exact ordered receipt shells from each fact row, restores Entity/action/effect/objective/schedule/projectile facts, then rebinds Target/action anchors and runs the existing committed inspection validator. It does not re-evaluate old Actions. The same-Encounter IDs and strict graph/legacy compatibility remain unchanged.

The first integration run demonstrated why recipient identity must be part of the durable fact contract: 11 observer/account tests exposed alias-shape losses when only owner-split history was available. That limitation has since been resolved. Current graph recipe `/2` binds each stable recipient ID to its pinned Action-field origin; strict Load rebuilds exact owner-separated recipient projections and typed receipt shells from history while preserving shared account-list identity. Prior recipe `/1` remains readable by deriving its origin from a matching registered Event or accepted Choice reference. The final current and prior recipe regressions pass; see the problems-first section at the report top.

Verified integration after the correction:

- `test_native_persistence` — **60 passed / 220.013s**, including same-Encounter and multiple-Encounter fresh-process Save/Load, `/1`–`/10` native-history migrations, accepted Arena `/10`–`/12` readers, observer-owned evidence and the omitted-receipt-node assertion.
- `test_native_draw_persistence` — **25 passed / 144.919s**, all current tested native Action continuations.
- `test_native_history` — **31 passed / 26.068s**.
- `test_checkpoint_adapters test_persistence_capability_matrix` — **53 passed / 21.455s**.
- The 11 observer/account cases from the first red full run passed after enabling the strict receipt-retention condition (**11 passed / 47.078s**). `.venv` compilation and `git diff --check` pass.

Fresh `/11` graph measurements are recorded in the following subsection. Complete recipient-map reconstruction, the remaining matrix families, adversarial compatibility breadth and application cutover are open. No source-rule decision is needed.

### Latest `/11` boundary-graph compaction measurements

The first post-change measurements establish the effect of omitting both per-boundary native receipt object families. The accepted `--registry-count` scale command measures 64 actual Feint Actions, 129 committed boundaries, full boundary-by-boundary history comparison, strict fresh-process native Load, one additional Delay, and comparison against uninterrupted continuation. In the 200-Being registry profile, uncompacted graph size was **7,527,151 B**; the exported graph was **3,789,953 B** (a **49.65%** graph reduction), fact history was **1,193,049 B**, and the complete Save was **6,246,468 B**. Scenario, history-query, export, and fresh-process Load+continue took **71.169 s**, **2.798 s**, **13.529 s**, and **9.959 s**; peak RSS was **225,525,760 bytes**. All 129 boundary checks and same-Encounter continuation matched.

For comparison, current reruns at 2 and 20 registered Beings measured graph reduction from **4,859,442 B to 1,128,349 B (76.78%)** and **5,094,837 B to 1,370,227 B (73.11%)**, respectively; each retained **1,193,049 B** history and had exact 129-boundary/fresh-process parity. Their complete Save sizes were **2,697,664 B** and **3,020,168 B**. The older measurements in the preceding table reflect pre-`/11` graph compaction and are retained as historical comparison only.

Strict 200-quiet-boundary runs at registry sizes 2, 20 and 200 all retained **34,563 B** history, queried all cuts, and matched fresh-process continuation. Their graph/Save bytes were **838,392 / 1,152,566**, **1,080,373 / 1,475,210**, and **3,500,991 / 4,702,698**, respectively. Scenario / query / export / fresh Load+continue times were **47.150 / 1.061 / 2.413 / 3.722 s**, **40.606 / 0.932 / 2.219 / 3.430 s**, and **41.118 / 0.952 / 3.009 / 3.818 s**; peak RSS was **79,773,696**, **80,330,752**, and **127,549,440 bytes**. These runs use the new `--quiet-registry-count 200 <count>` harness option; constant history size reflects the same two active Entities and nonparticipant registry growth remaining in the snapshot.

These scale profiles contain no observer-recipient maps, so they do not measure the additional storage cost of those maps. A separate three-root observer/account fixture verifies that their graph maps and typed receipt shells are reconstructed from history, including shared-list alias identity. The profiles still establish storage reduction and resumption only for their represented families; they do not close the matrix, general historical-reader parity, adversarial archive portfolio, or `/12` application-writer cutover.

### Focused verification for this increment

- Five strict Save/Load regressions covering omitted receipt nodes and multi-Encounter observer recipient/account bindings: **5 passed / 23.848s**.
- `test_native_history` in its required isolated process: **31 passed / 22.865s**.
- `test_persistence_capability_matrix` in its own process: **3 passed / 0.017s**.
- Python compilation of all changed native persistence modules and `git diff --check`: passed.
- The combined native-history + matrix invocation originally failed because matrix collection imports `arena_native_snapshot` before the test's process-wide absence assertion. The test now snapshots the process baseline and rejects only Arena modules newly imported by `capture()`. Combined result: **34 passed / 22.585s**; the isolated native-history run also passed **31 / 22.865s**.
- Boundary reconstruction is committed as `832812bad76d43e933872d99aee8b9a6695b44e3`; the quiet-scale harness and results are committed as `ee11afb`. The import-isolation regression correction was committed as `c677501`.
- Historical baseline before recipient-origin recipe `/2`: full `test_native_persistence` passed **60 / 220.265s**; that intermediate shared-account test retained receipt shells. It is superseded by the current **180-test** integration gate and origin-aware graph recipe `/2` evidence at the report top. The current shared-account fixture checks the compact wire shape, strict restoration, alias identity and listener-private queries.
- The complete native Action continuation suite after selective observer compaction passed **25 / 142.034s**. `test_native_history` plus capability matrix passed **34 / 22.585s** after the import-isolation fix. This historical suite predates recipient recipe `/2`; see the current exact gate and migration test above.
- Current reruns after selective compaction: checkpoint adapters **50 passed / 21.451s**; native history plus capability matrix **34 passed / 25.162s**; Python compilation and `git diff --check` passed. The first combined invocation omitted `PYTHONPATH` and failed at test discovery; rerunning with the repository import path passed. The selective compaction source/test/docs update is staged for a separate scoped commit; no source/test failure remains.

## Current continuation — self-contained definition coverage

### Problems first

The portable graph already bundled the configured Library, but its proof only exercised a Human and Dagger. The matrix therefore did not substantiate Object and Armor definition identity or prove that those definition families load without repository configuration files. This is a coverage gap in the evidence, not a known graph-restore failure.

### Correction and verification

Expanded `test_native_save_is_self_contained_for_shared_library_definitions` with an equipped Gauntlet Armor and a registered Linen pillow Object, using their exact bundled ArmorDictionary/ObjectDictionary definitions. Its child process blocks reads beneath `src/config`, performs strict fresh-process Load, verifies each original definition is the exact object in the corresponding restored Library dictionary, checks the canonical graph node set is unchanged by load, then continues the pending Delay and compares native outcome/RNG/history. It also resolves exact ActionDefinition and SkillDefinition object identity in the restored ActionDictionary and SkillDictionary. The source-linked matrix now records Human, Dagger, Armor, Object, Action and Skill definition evidence on their concrete type rows.

Verification: `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_native_save_is_self_contained_for_shared_library_definitions -v` — **1 passed / 1.748s**. Current code HEAD is `cc692942c64e790fab7a67fd37c12154a5350f2c` (selective observer receipt compaction). This added test and matrix/report reconciliation are pending scoped documentation/test commit. This improves the immutable-definition evidence but does not establish all family behavior, definition evolution rules, every observer-binding combination or production `/12` writer cutover; U-PER-SCALE-001 remains ACTIVE.

The same regression now also checks the configured ActionDefinition (`break weapon (armed)`) and SkillDefinition (`unarmed combat`) resolve to the exact bundled ActionDictionary/SkillDictionary objects after strict Load. Re-run: **1 passed / 1.692s**. Canonical graph nodes remain unchanged and configuration reads remain blocked. This extends shared-definition portability evidence across all six Library definition dictionaries; it does not complete mutable family or historical read coverage. This work was committed as `339bc93`.

Exercising the public skill accessors exposed two existing defects: both `Library.get_skill_definition()` and `Universe.get_skill_definition()` called a nonexistent `SkillDictionary.get_object_definition()`. Both now delegate to the actual `get_skill_definition()` method. The same fresh-process regression exercises both public accessors and the dictionary accessor, verifying they return the same bundled definition. Re-run after both fixes: **1 passed / 1.817s**. The fixes and report/TASKS correction were committed as `a0d1bd3`.

### Adjacent verification reconciliation

`PYTHONPATH=.:../src:../examples:../../npc-generator ../.venv/bin/python -B -m unittest test_skill -v` from `tests/` passes **9 / 0.014s**. `test_movement_intent` passes **53 of 54 / 17.784s**; its one failure, `test_intent_moves_before_co_resolving_run_observer_at_native_boundary`, expects an older exact set of Arena public projection keys and reports twelve additional keys (`projectiles`, `arena_strategies`, `encounter_mode`, `manual_controls_available`, `disarm_landing_choice`, `spot_action`, `search_available`, `discovery_actions`, `observation_history`, `listen_available`, `authored_scenario_id`, `spectator_projection`). The exact failure reproduces from a clean `git archive` of baseline `06c8661`; no movement or Arena projection source changed in this increment. This is recorded as a pre-existing stale assertion, not attributed to native persistence. No Arena behavior or test was changed.

## Current continuation — broader headless scenario authoring

### Problems first

The native scenario builder could author Beings, Weapons and explicit geometry, but common Object and Armor setups still required tests to reach around it and mutate `Universe` directly. Its proposed carried-Object helper also needed care: the existing `Universe.make_object_for_being` records an inventory possession but does not set `parent_container_id`, so calling that physical custody would invent a fact.

### Correction and verification

`NativeScenarioBuilder` now exposes `make_object`, `make_possession_object`, `make_armor`, and `set_placement`. Placement accepts only explicitly supplied positions/geometries; it never derives world geometry from definition dimensions. The possession helper delegates to the existing Universe operation and its docstring calls out the list-only relationship. The headless persistence smoke now uses these methods to author a placed pillow, worn Gauntlet Armor and a separate inventory possession, then strict-loads and checks all identities and relationships while importing no Arena application or npcgen modules.

Verification: `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_scenario -v` — **2 passed / 2.461s**; module compilation and `git diff --check` passed. This improves the reusable test/scenario API and explicit-state fidelity, but leaves broad field-family and historical-read parity, archive recovery/security, migrations and application cutover open. Current code HEAD at this increment is `e2b0883`; the builder/test/docs changes are pending their own scoped commit. U-PER-SCALE-001 remains ACTIVE.

## Current continuation — independent native re-execution parity

### Problems first

The 64-Action scale runner checked each history cut against receipts from the same Encounter, but no compact reusable fixture independently re-executed a consequential native sequence and compared its recorded meaning at every boundary. Comparing full `EncounterInspection` wrappers directly is invalid because they intentionally contain process-local anchors.

### Correction and verification

The native scenario builder now accepts an explicit Being identity for independently authored test worlds. A new headless replay fixture instantiates two separate native Encounters with the same authored identities, seed, Run Action and Delay Action. It compares every portable `boundary_facts_at`, `state_at`, `events_at`, and RNG cursor at boundary 0, movement/practice boundary 1, and quiet/Delay boundary 2. The comparison retains literal IDs here by authoring stable identities; process-local receipt anchors are excluded, consistent with the assignment's semantic-comparison rule.

Verification: `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_scenario -v` — **3 passed / 3.522s**; module compilation and `git diff --check` passed. The complete supported-family replay portfolio remains open; this is not a substitute for broad matrix closure. Current code HEAD at this increment is `79d0da6`; scenario-builder identity and replay changes are pending their own scoped commit. U-PER-SCALE-001 remains ACTIVE.

## Current continuation — committed receipt compaction and no-time Disarm history

### Problems first

A strict Save after choosing the post-roll Disarm landing previously carried `disarm-landing-facts/1` in the native graph but its attached history recorder was stale: the choice changes custody and position without advancing Encounter time, so the interval-only append path never added its committed receipt to the current cut. Load therefore reconstructed an empty Disarm index. This was an implementation gap, not a missing rule. A second storage duplication remained in `PublishedInterval`: committed Action/Effect IDs, RNG cursor and notification intents were represented both in history and every saved receipt.

### Correction and verification

Native graph `/2` now compacts the repeated publication fields and authenticated Disarm landing index, rebuilding both before receipt/history validation. `record_committed_disarm_landing()` makes a no-time choice amend only the existing latest history boundary after the native publication succeeds. It verifies that the origin, boundary count, all prior expanded rows, event/effect projection, timeline and RNG remain unchanged, while the exact current-cut landing fact is added. A recording failure leaves the native committed choice intact but marks the recorder failed closed for subsequent Saves, matching interval-recording failure behavior. The no-time landing remains its own receipt; no Action resolution or time advance is invented.

`test_pending_disarm_landing_choice_restores_and_commits_same_weapon` now checks the immediate same-boundary history query, post-choice strict Save/Load and byte-identical resave, continued native Delay state/history/RNG, plus a fresh-process Load of the pending choice followed by lawful landing selection and continuation. Re-sealed dangling-Being corruption remains rejected. Prior native graph `/2` writers are still covered by the pinned full-receipt-fact and Entity-only migration fixtures.

Current focused verification:

- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_persistence -v` — **58 passed / 197.965s**.
- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_draw_persistence -v` — **25 passed / 134.121s**, including all-boundary facts, Action/Effect order, targets, entities, recipients, objectives, scheduler, RNG and continuation for the 25 implemented Action scenarios.
- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_history -v` — **30 passed / 24.452s**.
- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_checkpoint_adapters -v` — **50 passed / 20.773s**.
- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_persistence_capability_matrix -v` — **3 passed / 0.008s**.
- Disarm Save/Load regression alone — **1 passed / 5.935s**; compacted receipt publication-fact and prior-writer focused cases — **4 passed / 14.098s** before the continuation assertion was added.

The history, adapter and matrix suites must run in separate processes: a combined invocation fails the history test's explicit “Arena application has not been imported” assertion because the matrix test imports Arena's field allowlist. Each suite passes in isolation; this is test-process import-order coupling, not a history implementation failure. The final report will retain this distinction.

Current controlled scale reruns use the same lawful 64-Feint/129-boundary scenario and fresh-process continuation at each registry size:

| Registry Beings | Graph bytes (uncompacted → final) | History bytes | Save bytes | Reduction | Scenario / query / export / fresh-load+continue (s) | Peak RSS bytes |
|---:|---:|---:|---:|---:|---:|---:|
| 2 | 4,853,146 → 1,554,196 | 1,193,015 | 3,265,426 | 67.98% | 65.741 / 2.594 / 10.617 / 8.974 | 203,358,208 |
| 20 | 5,095,978 → 1,796,450 | 1,193,015 | 3,588,430 | 64.75% | 73.617 / 2.917 / 11.732 / 9.353 | 183,468,032 |
| 200 | 7,522,170 → 4,215,975 | 1,193,015 | 6,814,462 | 43.95% | 73.897 / 2.479 / 13.299 / 10.121 | 237,469,696 |

Each run resolved 64 actual Actions, checked all 129 cuts, preserved same-Encounter IDs, and matched uninterrupted control after fresh-process Load and continuation. The current 200-quiet-boundary run checked all cuts and fresh-process continuation: **34,529 history bytes; 1,504,437 graph bytes; 2,040,592 Save bytes; 49.328s scenario; 1.496s query; 2.832s export; 3.856s Load+continue; 75,972,608 peak RSS bytes**. The process-resource profile is practical for these controlled fixtures. It does not itself prove every native family or ordinary Arena cutover.

### Acceptance status

| Gate | Current evidence | Status |
|---|---|---|
| Closed field/source catalog | Exact 159-type registry equality and source-linked row table | **Open:** registry/row equality is not per-family end-to-end closure |
| Native Actions and state families | 25 headless continuation scenarios; 58 native Save/Load cases; Groups, reproduction, history, observation, projectile, defense, custody, combat and pending workflows | **Open:** other reachable field readers/subtypes and full matrix evidence remain |
| Historical fidelity | Every portable boundary fact compared against receipt inspection for each of 25 scenarios; query, identity, causal order and observer owner checks | **Open:** complete historical consumer parity across every reachable family is not yet established |
| Fresh-process restoration | Pending, running, interrupted, simultaneous, changed-RNG and current-state continuation cases; exact IDs retained | **Open:** portfolio does not yet establish “any presently supported state” across all 159 types |
| Replay, corruption, rollback, compatibility | Current-version replay and strict migration/corruption/fault cases exist; `/10`–`/12` Arena readers remain tested | **Open:** assignment-wide adversarial and legacy migration matrix is incomplete |
| Scale | 2/20/200 registered Beings, 64 Actions/129 cuts, and 200 quiet boundaries all pass exact continuation | **Pass for measured profiles** |
| Application integration | Native API exists; accepted legacy Arena formats remain readable | **Open:** ordinary Arena writing still uses `/12`, pending general native gate |

No unresolved mechanics or external prerequisite currently blocks the open gates. Revision `4c9569b` compacts publication/Disarm receipt projections and adds the no-time boundary update. The report, matrix, findings and canonical task state are being updated in a separate documentation commit. No push has occurred.

## Current problems-first addendum — Group-owned membership continuation

The exact closed native field matrix was missing `statistical_group.MembershipChange`; consequently any Group with dated membership facts was refused as unsupported. Adding its exact schema also revealed a missing `MembershipChange.to_dict()` required by the existing `StatisticalGroup.state_at()` API. The initial test additionally registered the independently moving Group as an Encounter target and advanced it outside Encounter publication, correctly triggering the native `unreceipted position change` guard. The test now keeps the Group in the same Universe Save but outside the Encounter; no Encounter movement or visibility guard was weakened.

Strict capture and rehydration now validate ordered Group-owned membership history against its current snapshot, reject malformed owner/category/identity/time/transition sequences, and preserve join/leave/rejoin records. A fresh OS process restores those records, queries five historical times, advances Group motion, and independently continues a pending native Encounter Delay; Group time/position/velocity, Being non-teleportation, Encounter RNG and history match the uninterrupted control. Focused verification after the adapter and reader corrections:

- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_persistence -v` — **40 passed / 117.186s**, including legacy `/10`–`/12` compatibility and the fresh-process Group membership/continuation case.
- `... -m unittest test_native_persistence.NativePersistenceTests.test_statistical_group_facts_and_keyed_realization_resume_in_fresh_process -v` — **1 passed / 1.809s**.
- `... -m unittest test_group_membership_changes -v` — **12 passed / 0.128s**; `test_evolving_group_composition -v` — **8 passed / 0.156s**; `test_historical_group_realization -v` — **5 passed / 0.029s**.
- `... -m unittest test_checkpoint_adapters -v` — **50 passed / 19.038s**; `... -m unittest test_persistence_capability_matrix -v` — **3 passed / 0.009s**.

This remains a bounded family increment. The runtime receipt/Target graph is still duplicated beside fact history; complete 159-type historical-reader parity, durable journal recovery, application Save/Load cutover and broad rejection/migration coverage remain open. No rule or external blocker is identified; U-PER-SCALE-001 remains ACTIVE.

### Current extension — materialized Group-member identity and motion

**Gap and correction.** The initial closed registry covered `StatisticalGroup` and `MembershipChange` but omitted the exact `GroupMember` materialization record. That meant a Group with a realized cohort Being could not strictly Save/Load. The closed registry now admits the five exact `GroupMember` fields. `validate_membership_history()` checks canonical member key/ID, committed household/category/index facts, and consistency between the materialization map, realized Being registry, and motion-attached identities. It recomputes the exact deterministic keyed placement offset without calling lazy `member()` realization and requires the reviewed RNG provider (with no instance shadow). Forged-ID and finite-but-altered-offset Saves are refused before publication.

The fresh-process Group scenario now realizes an original adult member before Save, keeps a separate incoming Being through join/leave/rejoin, creates statistical `GroupMember` placement records for children, livestock and dogs without inventing native BeingInstances, advances the Group after Load, and checks the original member's continued Group motion while the incoming Being does not teleport. The child-category and animal *Being realization* APIs remain explicitly unsupported. Before continuation, it also proves canonical Save→Load→Save byte equality. The ReproductionGroup alias/merge/native-Being-binding scenario now proves the same canonical byte equality, exact Encounter ID, alias identity and idempotent materialization retry before a later native Delay. The Group-observer fixture was made reproducible after a full-suite run showed that its default Action-derived random key made the expected successful observations depend on generated IDs; it now supplies a stable explicit `random_key` whose adopted keyed rolls succeed.

Latest verification before nonadult statistical member cases: `.venv/bin/python -B -m unittest test_native_persistence` — **40 passed / 115.555s**. With forged-offset rejection added, the focused Group continuation plus checkpoint adapters and Group-membership tests passed **63 / 20.519s**. After canonical byte-equivalence, the Group and ReproductionGroup cases passed **2 / 3.772s**. The updated Group case with child/livestock/dog statistical identities also passes **1 / 2.267s**. The matrix remains 159 exact field-adapter types. This improves Group current-snapshot materialization and world-generation-state round-trip evidence; nonadult Being realization, broad history-reader parity, duplicate receipt/Target graph removal, journal recovery, and application cutover remain open. U-PER-SCALE-001 remains ACTIVE.

### Adversarial membership reconciliation

Extending the validator's comparison set to every identity mentioned by either current registries or dated membership history initially missed one historical identity when it had already been removed from both current maps. A negative incoming-member regression exposed this immediately; validation now compares all identities from the original cohort, incoming/current maps, and history, while separately checking that motion attachment equals original realized members that have never left. The Group fresh-process test now proves rejection of a forged departure, missing Group-motion attachment, and missing current incoming-member binding in addition to forged member identity/placement and malformed transition history. Corrected focused run: native Group continuation + `test_group_membership_changes` + `test_checkpoint_adapters` — **63 passed / 21.049s**. A pre-correction run failed exactly at the new missing-incoming-map assertion; no test was weakened.

## Problems-first addendum — Reproduction binding and PersonalHistory facts

The existing ReproductionGroup fresh-process fixture restored the logical Group and bound Being but only checked identity. It now saves a Group whose offspring `C1` has an authored native `BeingInstance` and an exact request record, then loads in a fresh OS process, retries the identical materialization request through the supported read-only retry path, and resolves a native Delay. The uninterrupted and restored paths match literal Being/request/Action identities, Group revision, outcome, RNG and canonical Encounter history digest. The alias resolves to the original canonical Group with the merged offspring list after strict restore. This does not bypass `materialize_reproductive_offspring()`'s rule that *new* bindings require the native no-Encounter context. The existing API rejects new creation after an Encounter exists; only the identical already-committed request is retryable there.

The PersonalHistory continuation now stores two dated rank facts: rank 1 at t=-5, then an Episode and rank 2 at t=-1 in one RealityLedger transaction. It queries exact-date facts and the episode, reruns the validator in a new process, then continues Delay with equal PersonalHistory bytes, RNG and native history. Exact focused results: ReproductionGroup logical registry plus binding continuation **2 passed / 2.544s**; PersonalHistory multi-fact continuation **1 passed / 1.720s**. These close selected current-snapshot facts, not all Group/Reproduction/PersonalHistory mutation histories or graph-free history reconstruction.

### Progressive ReproductionGroup history round-trip

The native recipe previously had no direct fresh-process continuation fixture for the implemented progressive-history branch. The new case uses the existing explicit test-only interval profile, publishes an initial two-period prefix and its one-period extension using the ordinary Universe registry APIs before Encounter creation, then Saves after a native Delay. Canonical Load→Save equality and an independently launched OS process preserve the complete semantic registry projection: seed/profile/schema/algorithm/scope digest, contiguous periods and stable generated Person IDs, Group identity/parent/offspring/source/revision, request keys, and progressive scope. The child then commits the next native Delay; logical Encounter/Action IDs, result, RNG and complete native history digest match uninterrupted execution. This is strictly persistence of existing test-profile-generated facts; it does not introduce or claim a production reproduction profile.

Verification: `PYTHONPATH=tests:src:../examples:../npc-generator .venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_progressive_reproduction_history_restores_and_continues_in_fresh_process -v` — **1 passed / 1.702s**; combined progressive + capability-matrix/API command — **4 passed / 1.706s**. Compilation and `git diff --check` pass. U-PER-SCALE-001 remains ACTIVE; history/query parity across these world-owned records and overall persistence cutover are still open.

### One-shot statistical reproduction outcomes

The portable reproduction registry also contains the V1 one-shot statistical outcome branch. A new headless fixture publishes a positive result and a separate zero-offspring result before creating the Encounter, then Saves after a native Delay. Fresh-process strict restore preserves each request's exact scope/provenance, seed, distribution schema/version and algorithm, positive generated IDs and origin ticks, the zero result with no Group/offspring, the parent-set scopes and idempotency keys. Canonical Save→Load→Save is byte-identical. The child continues another native Delay and matches the uninterrupted result, RNG and native-history digest.

Verification: `PYTHONPATH=tests:src:../examples:../npc-generator .venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_statistical_reproduction_outcomes_resume_with_positive_and_zero_results -v` — **1 passed / 1.676s**; both reproduction cases plus matrix/API gate — **5 passed / 3.383s**. A first child-process assertion compared a Python tuple to the JSON-list shape before JSON normalization; correcting this test-only comparison made the strict regression pass. No reproductive rule was changed. U-PER-SCALE-001 remains ACTIVE.


**Program:** U-PER-SCALE-001 is the sole ACTIVE implementation program. U-ACT-GATE-001 remains FUTURE/unpassed, U-NET-001 remains DEFERRED, and U-ACT-FULL-003 remains DEFERRED. Shield completion is the next implementation priority; ranged Actions follow the shared 3-D geometry work.

**Repository:** active Universe checkout; no push performed.

**Execution intervals (America/Los_Angeles):**

| Interval | Start | End | Elapsed |
|---|---|---|---|
| Initial implementation | 2026-11-15T16:42:40-08:00 | 2026-11-15T17:52:06-08:00 | PT1H9M26S |
| Extended operational verification | 2026-11-15T18:19:20-08:00 | 2026-11-15T19:08:18-08:00 | PT48M58S |
| Sufficiency addendum continuation | 2026-11-15T20:39:02-08:00 | 2026-11-16T03:09:14-08:00 | PT6H30M12S |
| Exact serialized-field diagnostic audit | 2026-11-16T04:16:02-08:00 | 2026-11-16T04:24:43-08:00 | PT8M41S |
| Headless initial/delta proof | 2026-11-16T04:59:08-08:00 | 2026-11-16T05:13:46-08:00 | PT14M38S |
| Full native-history capability continuation | 2026-11-16T18:34:14-08:00 | End not recorded | Elapsed unavailable; no estimate added |
| Native action-family breadth continuation | 2026-11-16T21:04:56-08:00 | End not recorded | Elapsed unavailable; no estimate added |
| Arena activation and native `/12` migration slice | 2026-11-16T21:30:36-08:00 | End not recorded | Elapsed unavailable; no estimate added |

| Native headless resume slice | 2026-11-16T10:46:06-08:00 | 2026-11-16T11:27:35-08:00 | PT41M29S |

| Faithful replay continuation | 2026-11-16T11:56:50-08:00 | 2026-11-16T12:35:58-08:00 | PT39M8S |
| Native history bridge continuation | 2026-11-16T13:49:14-08:00 | End not recorded | Elapsed unavailable; no estimate added |
| Full native bridge continuation | 2026-11-17T06:10:55Z | Not recorded in the prior closeout | Elapsed unavailable; no estimate added |
| Native observer-knowledge and scheduler-history continuation | 2026-11-17T09:06:49Z | End not recorded | Elapsed unavailable; no estimate added |
| Native projectile-history integration continuation | 2026-11-17T15:34:30Z | End not recorded | Elapsed unavailable; no estimate added |
| Native publication receipt and scale continuation | 2026-11-17T19:15:12Z | IN PROGRESS | Recorded at closeout |

## Problems-first — cumulative observer-recipient history in `/10`, with strict `/9` migration

### Gap

Every-boundary receipt comparison exposed two related defects that had passed selected-cut observer tests. Native history stored the recipient projection touched by each receipt as if it were the complete recipient state, so a later quiet receipt could erase a testimony account from historical query. Also, `AccountsProjection` dropped the listener ID, making `observer_facts_at(boundary, listener_id)` unable to return the listener's own received account. A shared account list created a further privacy risk if one listener's account data were exposed to another listener.

### Correction

Native history schema `/10` now folds recipient updates forward to the last committed projection. `FrozenAccounts` and `AccountsProjection` carry all registered listener IDs for an explicitly shared list. The stable history reader emits distinct per-listener account/effect projections, so `observer_facts_at()` remains owner-filtered even when the in-world container is shared. The `AccountsProjection.listener_ids` field is optional in the graph adapter to preserve decoding of older native graph records.

The strict `/9` history upgrade replays old boundary-local recipient deltas into a cumulative read state. It recovers a testimony owner only where the legacy `HeardAccount` already carries `listener_id`; an empty ownerless legacy list is left ownerless. New validation checks the recipient role, participant IDs, listener/projection consistency and account/listener identity. A re-sealed forged listener ID is rejected.

### Evidence

The heterogeneous three-Encounter native Save now compares owner-specific recipient facts against the authoritative receipt projections at every cut from boundary 0 through the latest boundary, both before Save and after a fresh process loads and advances each Encounter. It also builds a realistic old `/9` boundary-local testimony stream, upgrades it, and checks every historical listener query plus preservation of the known initial scheduler projection. A two-listener simultaneous AskAboutPast test shares one received-account list and verifies that each listener sees only their own account at the committed Action boundary and after a later quiet boundary.

Exact verification:

- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_persistence` — **39 passed / 114.127s** (includes strict old `/10`–`/12` Arena readers, native Save/Load, and fresh-process continuations).
- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_native_save_combines_object_and_location_recipients` — **1 passed / 10.075s**, including all-cut owner queries, `/9` upgrade, tampered owner rejection and fresh-process continuation.
- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_completed_ask_about_past_and_listener_accounts_resume_with_binding` — **1 passed / 1.615s**; a checksummed native `/1` file with `/9` recipient rows loads in a fresh process, recovers the listener from the recorded HeardAccount, and continues exactly.
- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_history.NativeHistoryTests.test_shared_testimony_container_remains_listener_separated_in_history` — **1 passed / 1.536s**.
- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_history -v` — **28 passed / 21.060s**; `test_checkpoint_adapters -v` — **50 passed / 19.317s**.
- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_draw_persistence -v` — **25 passed / 116.775s**; all current Action-history parity fixtures remain green with schema `/10`.
- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_persistence_capability_matrix` — **3 passed / 0.024s**.

Remaining gaps are still material: the 157-type family inventory is not closed end-to-end, history remains coupled to the runtime receipt/Target graph, durable append-journal crash recovery is not proven, broad state-family and corruption/scale portfolios remain, and the successful native path has not been cut over to ordinary application Save/Load. These are engineering gaps with no external or adopted-rule blocker identified; U-PER-SCALE-001 stays ACTIVE.

## Problems-first — shared testimony recipient restore

### Gap and correction

A new native Save/Load case for one physical `received_accounts` list shared by two AskAboutPast listeners initially failed in `native_graph_snapshot` rehydration. Capture and binding validation correctly admitted the declared two-listener owner set, but restore then incorrectly required every account in the shared list to belong to the current Action's actor. The restore validator now checks each account against the complete authenticated binding owner set; each individual Action still must reference that binding as one of its declared listeners. Same-list alias identity is preserved. This was an implementation mismatch, not an adopted-rule ambiguity.

### Evidence

The new `NativePersistenceTests.test_shared_testimony_binding_restores_listener_aliases_without_cross_exposure` commits two simultaneous lawful AskAboutPast Actions with different listener-specific facts into one explicitly bound list. It saves, loads in a fresh OS process, proves both restored Actions reference the same Python list, queries each listener independently at the committed boundary, advances a quiet boundary, and compares RNG plus canonical history to the uninterrupted run. The focused test passes **1 / 1.875s**. Its initial failing run reproduced the single-listener restore predicate; the corrected run passes. The broader current observer gap is still open: other supported recipient families and complete caller/privacy/query parity are not closed. No external or rules blocker is identified.

Regression verification after the correction:

- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_persistence -v` — **40 passed / 116.441s**.
- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_history -v` — **28 passed / 21.299s**.
- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_checkpoint_adapters -v` — **50 passed / 18.992s**.
- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_persistence_capability_matrix -v` — **3 passed / 0.007s**.
- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_faithful_replay -v` — **5 passed / 8.616s**; playback, identity-map refusal, tamper refusal, and fresh-process same-version replay remain green.
- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_draw_persistence -v` — **25 passed / 116.564s**; all 25 implemented Action continuation scenarios retain all-boundary history parity after the restore change.
- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_arena_persistence -v` — **22 passed / 375.021s**, including 64 lawful native Feints, 2/20/200 registry scaling, strict `/10` and `/11` migration, current `/12` compatibility, and history integrity. Python emitted the expected duplicate `snapshot.json` warning from the duplicate-entry corruption test; that test passed.
- `.venv/bin/python -B -m py_compile src/native_graph_snapshot.py tests/test_native_persistence.py` and `git diff --check` — passed.

The history and adapter suites were run as separate processes to avoid their known test import isolation interaction.

Implementation commit: `5a6447cac7d984087bc37caf0a6e5f17f99673db` (restore validator, regression, matrix, TASKS and findings). Before commit, `git diff --cached --check` passed and `python3 tools/check_publication_safety.py --staged` reported `files=12 findings=0 result=PASS`; `git commit --only` named six reviewed paths, so the five unrelated pre-staged archival operations were excluded.

## Problems-first — missing ordered timeline query

The history format retained boundary starts, Action/Effect identities and start fences, but offered no API to reconstruct the ordered `EncounterInspection.timeline` view without reading the runtime receipt graph. This was a missing historical reader, not missing source facts. Added `NativeHistoryQuery.timeline_at()` and its module-level API. It returns detached tagged `BoundaryInspection` rows in exact order; a quiet span is expanded only in the returned query and remains compact in storage. The Action-family comparison helper now checks timeline plus full target-history, entity, objective/use, scheduler, recipient, projectile, receipt, Action and Effect projections at each checked native boundary.

Evidence: the 25-scenario native Action Save/Load suite passed with the expanded per-boundary comparisons (**25 / 119.286s**). The initial-boundary and quiet-span timeline cases passed **2 / 5.098s**. Capability-matrix/API validation passed **3 / 0.027s**. The comparison verifies the query result against `_plain(Encounter.inspect_committed(boundary).timeline)` for all available committed boundaries; boundary zero is explicitly the empty tuple because the native inspector has no committed receipt there. Code/test/matrix commit: `1f51349721ce8789647fd001e97fb912fd278812`. Before commit, staged check and publication safety passed (`files=11 findings=0`); explicit commit paths excluded all unrelated pre-staged archival changes. This closes a specific query/API gap, not graph-free `Encounter.inspect_committed`, complete family coverage, durable journaling, or production cutover.

## Current `/10` scale rerun

The current `/10` native API was measured using the same native scale runner and fixture at all registry sizes. It resolved 64 lawful Feint Actions, checked every one of 129 logical boundaries, then strictly restored and continued in a fresh OS process. Each child matched same-Encounter identifiers, native HP, RNG and history against uninterrupted control. The 200-quiet-boundary case also compared all logical cuts and continued exactly.

| Registered Beings | Actions / boundaries | Graph bytes | History bytes | Save bytes | Scenario seconds | Query seconds | Export seconds | Fresh-process Load + continuation seconds | Peak RSS bytes |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 64 / 129 | 4,853,536 | 1,193,015 | 7,664,546 | 62.035 | 2.293 | 4.431 | 6.221 | 182,697,984 |
| 20 | 64 / 129 | 5,102,250 | 1,193,015 | 7,996,162 | 60.354 | 2.290 | 4.528 | 6.347 | 183,943,168 |
| 200 | 64 / 129 | 7,526,564 | 1,193,015 | 11,228,582 | 60.566 | 2.437 | 5.327 | 6.612 | 225,263,616 |

The 200-quiet-boundary `/10` run checked all 200 cuts and produced **34,529 history bytes**, **4,853,760 graph bytes**, **6,506,356 total Save bytes**, **0.940s query**, **2.641s export**, **2.976s fresh-process Load + continuation**, and **157,253,632 peak RSS bytes**. The native simulation and strict Save/Load are reliable at this workload; the runtime graph still occupies 4–6 times as much as the 64-Action fact history and remains present beside it. The result therefore strengthens operation evidence without satisfying the compact, graph-free architecture requirement.

Exact commands: `.venv/bin/python -B examples/native_persistence_scale.py`, the same command with `--registry-count 20` and `--registry-count 200`, and `.venv/bin/python -B examples/native_persistence_scale.py --quiet-boundaries 200`. All four completed successfully.


## Native action-family continuation — contact history and Break Weapon

### Problems first

- U-PER-SCALE-001 remains ACTIVE. Native history `/5` still represents the selected historical inspection families, while the resumable Save contains the separate full receipt/Target graph. The historical read model is not yet equivalent for every currently implemented Action, state family or consumer; graph-free reconstruction, native-format legacy migration/resave, durable journal recovery, and ordinary application Save/Load cutover are still open.
- No rule ambiguity or external dependency was found in this increment. It adds fresh-process evidence for native contact state and both Break Weapon miss and successful-break handling; it does not claim that remaining Action variants or full matrix rows are complete.

### Contact sequence and dependent Action continuation

`tests/test_native_draw_persistence.py::NativeDrawPersistenceTests.test_headless_touch_grab_trip_history_continues_after_fresh_process_load` uses the Arena-independent `NativeScenarioBuilder`, ordinary seed 7, represented positions/radii, explicit awareness, standing posture, and medium size categories. The engine commits Touch at t=1 and Being Grab at t=2; the Trip declaration cites the exact Grab Action ID and remains accepted when the Save is made. The uninterrupted run and a fresh OS process both resolve the Trip at t=4 as successful and set the target's posture to lying. The test compares literal Action/source IDs, each outcome, posture, RNG, and the complete canonical native-history digest. No roll is injected and no contact or body-geometry rule is altered.

### Break Weapon miss, successful break, and dependent Action

`tests/test_native_draw_persistence.py::NativeDrawPersistenceTests.test_headless_break_weapon_failure_preserves_later_attack_after_restore` uses standard configured Dagger definitions, ordinary seed 1, a represented pending attack by the weapon holder, and a scheduled Break Weapon resolved in the preceding second. The native Break Weapon roll is a miss; neither Dagger changes durability. Both accepted Choices are in the initial Save. A fresh OS process restores them, resolves the same Break Weapon result, and then resolves the holder's later Strike with the same outcome as uninterrupted execution; it is not `weapon_unavailable`. The comparison covers logical Action/weapon IDs, weapon HP, RNG and full history digest. This is the failure-path continuation; no weapon hardness/HP was changed and no roll was scripted. A complementary native success path uses an ordinary configured Bastard sword against a standard configured Dagger with seed 3: the committed Break Weapon receipt reports `broken`, the Dagger reaches 0 HP, and the later accepted Strike resolves `weapon_unavailable`. Both uninterrupted and fresh-process paths preserve literal Action/weapon IDs, HP, RNG and complete history digest.

### Focused result

`.venv/bin/python -B tests/test_native_draw_persistence.py -v` — **11 passed in 64.418s**, covering native Draw, shield Don/Remove, Ready/consumption, simultaneous pickup contention, Object strike and simultaneous durability, Subdue, Feint/follow-up, Touch→Grab→Trip, Break Weapon failure/later attack, and successful standard-weapon break/later attack. The Touch→Grab→Trip case also passed alone in **3.280s**; the successful Break Weapon case passed alone in **4.839s**. Python compilation and `git diff --check` passed for the current changes. These results are incremental; the report's architectural and acceptance status remains incomplete.

## Latest continuation — native observer evidence and Search/Listen

### Problems first

- The complete acceptance gate remains open: native files still include the committed receipt/Target graph beside native fact history, there is no generalized delta-only historical read model, no production `Universe`/Arena Save/Load cutover, and action/state/observer family, legacy native migration, scale, and crash-recovery evidence remain incomplete.
- No adopted rule choice or external dependency blocks this work. These are remaining engineering and verification requirements; U-PER-SCALE-001 remains ACTIVE.
- Two observer-evidence omissions were real adapter gaps, not rule gaps: LocationEvidence and ObjectEvidence recipients were not durably bound. Object Spot also contained registered-domain `ChoiceDraft`, `ObjectObservationEffect`, and `ObjectEvidenceProjection` values missing from the exact field registry. Native Save had correctly failed closed on them.

### Completed and verified in this continuation

Added explicit host recipient bindings for LocationEvidenceLedger and ObjectObservationLedger. Capture and restore check observer identity, mapping ownership, registered Being/Object identity, source Spot identity, successful source resolution, and Encounter/boundary provenance. Existing object identity, source Action identity, observations, pending projectile state, and RNG survive fresh-process restore. The two distinct Object observers retain separate outcomes; a failed Spot did not manufacture evidence. Registered exact field schemas for `ChoiceDraft`, `ObjectObservation`, `ObjectObservationLedger`, `ObjectObservationEffect`, and `ObjectEvidenceProjection`; regenerated the 157-type capability table and its equality test.

A native Search at an explicitly represented `arena_search_accessible=True` target succeeds; a subsequent Listen at an explicitly `arena_audible=True` target fails from a declared roll. Saving with the Listen Choice pending and resuming in a fresh OS process preserves the committed Search awareness, exact Action IDs/outcomes, RNG, and normalized complete history equal to uninterrupted native execution. No Arena UI/server or `npcgen` is imported by native child processes.

### Native history `/2` and extended headless scale verification — 2026-11-16

#### Problems first

- U-PER-SCALE-001 remains ACTIVE. Native Save still serializes the whole receipt/Target runtime graph beside fact history; native historical query only covers tested inspection projections; no ordinary `Universe` or Arena Save/Load cutover, complete Action/state-family parity, crash recovery, or native `/10`–`/12` migration is demonstrated.
- The prior 200-quiet-boundary probe showed each row repeated the same roughly 6.7 KB RNG cursor. This was representational redundancy, not a rule gap. Native history `/2` stores a strict reference when a boundary's RNG cursor is unchanged, and `rng_state_at` recovers the exact cursor.
- `/1` history remains accepted and is upgraded losslessly to `/2` before continuation. A fresh Load of a `/1` outer native Save upgrades, resumes automatic post-publication recording, continues with the same Action ID, and produces the same `/2` Save bytes as uninterrupted execution.
- No rule, authorization, or external blocker is outstanding. The full receipt graph, complete general historical readers, production integration, and other all-family work remain engineering requirements.

#### Measured 64-Action native continuation by registry size

The reproducible [`native_persistence_scale.py`](../../examples/native_persistence_scale.py) resolves 64 lawful Dagger Feints against an explicitly positioned and aware native target, saves after 128 resolved intervals, restores in a fresh OS process, and continues with the same Delay ID. It verifies complete committed Action count, Being registry size, same-Encounter history/ID digest, RNG, HP and time against uninterrupted execution. Only the first two registered Beings are Encounter participants; extra Beings are realized Universe registry entries. No Arena, browser/session, or `npcgen` imports occur in the child process.

| Registered Beings | Actions / boundaries | Graph bytes | Fact-history bytes | Total Save bytes | Export seconds | Fresh-process load+continue seconds | Peak RSS (macOS bytes) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 64 / 129 | 4,836,836 | 1,232,823 | 7,682,086 | 4.483 | 6.995 | 254,787,584 |
| 20 | 64 / 129 | 5,084,609 | 1,232,823 | 8,012,450 | 4.582 | 7.147 | 177,848,320 |
| 200 | 64 / 129 | 7,503,051 | 1,232,823 | 11,237,038 | 5.400 | 7.310 | 245,071,872 |

The 64-Action workload continued exactly in all three fresh processes. Fact-history bytes are constant across registry sizes while graph/Save size rises with registered Beings. At 2 Beings, however, the runtime graph is 3.92 times the fact-history bytes; 7.68 MB total is not the requested compact architecture.

#### Quiet-boundary growth before and after RNG-reference encoding

The same 200-boundary no-Action fixture was measured under the old `/1` representation and the new `/2`; strict load and an ordinary Delay at boundary 201 matched uninterrupted control in both runs.

| Quiet boundaries | History version | Graph bytes | Fact-history bytes | Total Save bytes | Scenario seconds | Export seconds | Fresh-process load+continue seconds |
|---:|---|---:|---:|---:|---:|---:|---:|
| 200 | `/1` repeated RNG | 4,837,613 | 1,547,608 | 7,997,907 | 40.694 | 2.960 | 4.324 |
| 200 | `/2` prior-cursor reference | 4,837,822 | 212,318 | 6,662,897 | 41.213 | 2.866 | 4.407 |

The `/2` fact history is **86.28% smaller** and its total Save **16.69% smaller** for the same quiet run. This removes repeated RNG payload; it does not yet replace the receipt/Target runtime graph with compact state or merge quiet boundaries into spans.

#### Focused verification

| Command | Result |
|---|---|
| `PYTHONPATH=tests .venv/bin/python -B -m unittest discover -s tests -p 'test_native_persistence.py'` | 16 passed in 45.383s |
| `PYTHONPATH=tests .venv/bin/python -B -m unittest discover -s tests -p 'test_native_history.py'` | 11 passed in 5.977s |
| `PYTHONPATH=tests .venv/bin/python -B -m unittest discover -s tests -p 'test_checkpoint_inventory.py'` | 30 passed in 12.179s |
| `PYTHONPATH=tests .venv/bin/python -B -m unittest discover -s tests -p 'test_checkpoint_adapters.py'` | 48 passed in 18.431s |
| `PYTHONPATH=tests .venv/bin/python -B -m unittest discover -s tests -p 'test_persistence_capability_matrix.py'` | 3 passed |
| Selected `/12` archive integrity/corruption, pinned v4, and fresh-process v10/v11 migration tests | 5 passed in 6.962s; Python `zipfile` emitted its expected duplicate-entry warning in the corruption fixture |

The Arena `/12` compatibility checks above remain evidence for the legacy Arena reader; they do **not** demonstrate migration through the separate native Save API. Native `/1` to `/2` upgrade is instead covered by `test_native_history.py` and `test_native_persistence.py`. This continuation has no standalone native `/10`–`/12` compatibility claim.

### Quiet-span history `/3` continuation — 2026-11-16

#### Problems first

- U-PER-SCALE-001 remains ACTIVE and incomplete. Even when no Action, Event, Effect, or domain property changed, `/2` used one full row per committed boundary (212,318 bytes for 200 quiet boundaries). The saved receipt/Target graph still dominates total Save bytes, and native history is not the ordinary production Save path.
- This is a persistence representation gap, not an adopted-rule ambiguity. Full state-family/query parity, durable history recovery, legacy migration through the native API, and ordinary app/Universe Save/Load remain open engineering work.

#### Implemented and measured

Native history `/3` retains the `/1` and `/2` readers and losslessly upgrades them. It references an unchanged RNG cursor and coalesces only consecutive rows with no Action/Event/Effect facts, unchanged RNG, identical participant/starts facts, and numeric changes limited to root time/boundary, entity inspection-boundary or scheduler-revision cursors. Span validation checks exact path allowlists, numeric preimages and increments, chronology, participants, end-state digest, and unchanged RNG. `state_at`, `events_at`, `rng_state_at`, and recorder append preserve the logical boundary view. Any Action/Event/Effect or changed domain property stays as an ordinary atomic row.

The reproducible 200-boundary headless quiet fixture was rerun through strict fresh-process Save/Load and a native Delay continuation. It exactly matched uninterrupted time, RNG, HP and semantic history. The 64-Action scenario was rerun through native `/3`, also matching the uninterrupted control and same-Encounter identities.

| Scenario | Graph bytes | Fact-history bytes | Total Save | Scenario | Export | Fresh-process Load+continue | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|
| 200 quiet boundaries | 4,837,612 | 26,705 | 6,477,004 | 50.015s | 2.828s | 3.110s | 160,251,904 |
| 64 lawful Feint Actions, 129 boundaries, 2 registered Beings | 4,841,511 | 1,171,895 | 7,627,390 | 69.952s | 4.718s | 6.743s | 184,516,608 |
| 64 lawful Feint Actions, 129 boundaries, 20 registered Beings | 5,084,653 | 1,171,895 | 7,951,582 | 70.222s | 5.039s | 6.600s | 177,324,032 |
| 64 lawful Feint Actions, 129 boundaries, 200 registered Beings | 7,505,664 | 1,171,895 | 11,179,594 | 72.043s | 5.749s | 7.485s | 229,261,312 |

History now records native `TargetCandidate` facts rather than derived `TargetInspection` views; the 64-Action fact-history record fell from 1,232,823 to 1,171,895 bytes for the same legal workload. The 200-boundary history is **87.42% smaller than `/2`** and **98.27% smaller than `/1`**. Total Save fell **2.79% from `/2`** and **19.02% from `/1`**. All three prior `/3` 64-Action registry cases continued identically in fresh processes. Their fact-history bytes remain equal across registry sizes because they contain the same Action/event workload; the graph grows with the registered Being population. The graph still contains the whole receipt/Target history, so this is not the requested final architecture.

Focused results after native `TargetCandidate` history: `test_native_history.py` — **14 passed in 14.242s**; `test_native_persistence.py` — **17 passed in 54.646s**; `test_persistence_capability_matrix.py` — **3 passed**. A forced portable-size refusal verifies the first native Save does not attach a recorder; an injected prepublication history-file link fault leaves no destination or temp and immediate retry succeeds. The 64-Action native scale scenarios passed for registered Being counts **2, 20, and 200** under this payload; the 200-quiet-boundary Save/Load continuation also passed. History tests check each boundary against committed native `TargetCandidate` records, RNG, participants, Events, strict refusal of invalid span paths, strict `/1` and `/2` migration including v2 quiet-span upgrade, and append after/through a compressed span. Earlier in this same execution, field inventory — **30 passed in 12.179s**; checkpoint adapters — **48 passed in 18.431s**; selected Arena `/12` integrity/corruption/pinned-v4/v10/v11 compatibility — **5 passed in 6.962s**. These do not claim native-format `/10`–`/12` migration. `py_compile`, relative Markdown links, and `git diff --check` passed. No push was performed.

## Latest continuation — revised full native-history bridge

### Problems first

- The assignment is not complete. Current `/12` persistence is generated-Arena-only; `Universe.save_to_file()/load_from_file()` explicitly refuses transactional/Encounter restoration. The broad inventory and adapter recipes are not production capture/restore.
- The fact-history API now supports strict historical projections, authenticated append, and opt-in in-memory recording after successful native publication. Its headless Save/Load wrapper restores tested Run/Delay and Dagger-Melee fixtures, but it still relies on the restricted graph adapter and redundantly stores old receipt/Target histories. This does not replace the generic native object graph or provide arbitrary native restoration.
- No user rule decision or external integration is currently required. Remaining work is engineering scope: durable crash-safe history, complete native snapshot/rehydration including Reality/observer adapters, native history-consumer parity, legacy coexistence, all-family tests, and scaling.
- The previously interrupted 64-Feint Arena persistence invocation was rerun and passed: **1 passed in 272.770s**. Keep this as the slow existing `/12` baseline, not as evidence that the new compact persistence architecture is complete.

### Native history component and measured current baseline

Implemented `src/native_history.py` as a fact-only, Arena-session-independent history component. It exports authenticated initial state plus atomic presence/value changes, committed Action/Event and Effect identity batches, per-boundary target state, objective/observer projections, schedule/timing and RNG receipt facts. It validates/reconstructs selected historical boundaries without native Action resolution; Save output does not contain Python addresses for recipient or ledger anchors. `tests/test_native_history.py` exercises quiet t=2, successful zero-entity-change Delay at t=3, the simultaneous two-Run commit at t=4, identity/multiplicity, tamper/preimage/reorder refusal, write-without-overwrite behavior, read-only capture, and the lack of Arena application imports. A 4-boundary sample is 101,735 canonical bytes; changes per boundary are 44/12/12/27, with 1/0/1/2 Action identities. This is a foundational history component, not a complete Save/Load implementation.

The current production `/12` 64-Action baseline was rerun without interruption: `PYTHONPATH=tests .venv/bin/python -B -m unittest test_arena_persistence.TestArenaPersistence.test_64_lawful_native_feint_resolutions_segment_history_and_resume` — **1 passed in 272.770s**. The run demonstrates its existing strict continuation but confirms the unacceptable long graph-history serialization/export path. The task is to replace that cost with normalized native history while preserving all history facts and current Save/Load behavior during integration.

### Authenticated incremental append

Added `append_committed(log, encounter)` and an opt-in `NativeHistoryRecorder`. Recorder attachment captures a validated committed prefix; transactional progression feeds it only after the publisher returns successfully and after the progression lock is released. A simultaneous batch remains one receipt. An injected rollback after the commit marker produces no recorder entry. The recorder is in-memory, not a durable journal; if inspection/append fails after native publication it marks itself failed and future Save refuses until recovery. Tests: `.venv/bin/python -B -m unittest discover -s tests -p 'test_native_history.py'` — **9 passed in 5.838s**, covering append, automatic post-commit recording, rollback, and historical/query integrity. It still uses the existing native historical inspection projection and is not an all-family record layer.

### Headless native Save/Load integration slice

Added `src/native_persistence.py` with byte export/load and path read/write APIs. The bundle carries the native graph, canonical fact history, and a top-level integrity digest. The file writer uses an exclusive temporary file, fsync, and atomic no-overwrite hard-link publication; a repeated write preserves the existing bytes. An attached recorder supplies committed history without recapturing it. This path imports no Arena session/server/browser or `npcgen`; it reuses the existing strict typed graph snapshot adapter, whose present allowlist remains limited and Arena-named. The native graph currently redundantly retains its old receipt/Target graph, so this proves same-Encounter continuation, not the compact architecture/scaling acceptance. On the four-boundary Run/Delay fixture with a pending Delay Choice, exported wire measured **1,247,342 bytes**. A fresh OS process restored its same logical Universe/Encounter, retained the pending Choice, continued via ordinary `Encounter.step(1)`, and matched the uninterrupted control's time, RNG, Being HP, Action receipt IDs, and canonical native-history digest. A second Arena-independent test performs a native Dagger MeleeStrike with committed damage, saves with a further MeleeStrike pending, then restores in a fresh process and continues to t=8; the original and restored control match RNG, HP, receipt identity, and full history digest. A third native scenario produces a real Stun using seed 6, saves after the committed condition interrupted a later accepted MeleeStrike, and continues through stun expiry in a fresh process; time, RNG, HP, condition timestamp, cancellation, and history digest match. The tests also verify fail-closed refusal without live-state mutation for StatisticalGroup and observer-owned recipient scenarios: native conditional-attribute/RealityLedger validator reconstruction and durable external recipient rebinding are not implemented. The child asserted no `arena_browser_session`, `arena_server`, or `npcgen` imports. Exact latest tests: `.venv/bin/python -B -m unittest discover -s tests -p 'test_native_persistence.py'` — **5 passed in 15.656s**; `.venv/bin/python -B -m unittest discover -s tests -p 'test_native_history.py'` — **9 passed in 5.838s**; `.venv/bin/python -B -m unittest discover -s tests -p 'test_persistence_capability_matrix.py'` — **3 passed**; the executable type registry now exactly matches all 157 field adapters. Also `.venv/bin/python -B -m unittest discover -s tests -p 'test_checkpoint_inventory.py'` — **30 passed in 14.012s**, and `test_checkpoint_adapters.py` — **48 passed in 20.816s**; module/test `py_compile` passes. Strict top-level digest, duplicate-key, no-overwrite and fresh-process continuation checks are included. This API is not wired into ordinary production Save/Load, is not a generic native closure, and has not passed legacy-format, adversarial graph, observer-family, or scale acceptance.

### Current native family integration — 2026-11-16

#### Problems first

- The native Save still stores both a whole committed receipt/Target object graph and a fact-history log. It is functional and strict for tested families, but it does not yet meet the compact current-snapshot plus independently retained history architecture.
- Tested native families now include Delay, Dagger MeleeStrike, Stun, StatisticalGroup and Group observation with two observer-owned BeliefLedgers, logical ReproductionGroup records and linked native Being IDs, plus a PersonalHistory Fact/validator. Other supported Action families, PersonalHistory mutation/query parity, reproduction-linked Being/Group-member realization continuation, AskAboutPast account delivery, Object/Location Evidence and native Search/Listen now have focused fresh-process cases; Arena-perception observer APIs, every recipient combination, multi-Encounter ownership and complete historical-reader parity remain open.
- External observer recipients require explicit `RecipientBinding` values; missing bindings are rejected. The new API is not connected to ordinary Universe/Arena Save/Load. Native `/10`–`/12` coexistence, crash-safe journal recovery and scale acceptance remain open.
- No user-rule or external blocker is outstanding; these remain engineering requirements and U-PER-SCALE-001 stays ACTIVE.

#### Implemented and verified

Separated the common graph codec into `src/native_graph_snapshot.py` and kept `src/arena_native_snapshot.py` as the `/12` compatibility import. Native schema `universe.native-encounter-graph/1` uses the closed native type registry rather than the Arena `_ARENA_TAGS` allowlist. `native_persistence.export_save()` captures through native field adapters and accepts explicit recipient bindings; `write_save()` forwards the bindings. Restore validates host references and callback recipe multiplicity/owners, then rebuilds the audited StatisticalGroup keyed RNG provider, Group/PersonalHistory Reality validators, subject-ledger anchors, observer recipient IDs, receipts and progression ownership. It does not replay prior Actions. The `/12` schema remains a distinct path.

### Reproduction and PersonalHistory native adapters — current continuation

#### Problems first

- U-PER-SCALE-001 remains ACTIVE. Native files still duplicate historic receipt/Target object graphs beside fact-history deltas; new native Save is not the production reader; compact scaling, historical query parity and full Action/state-family coverage are not demonstrated.
- This increment covers selected logical ReproductionGroup records, native offspring Being identity bindings and a committed PersonalHistory fact. It does not cover reproduction-linked Being creation/Group-member realization continuation, all PersonalHistory mutation/query cases, or other unresolved Group generation workflows.
- `/10`–`/12` Arena compatibility through the new API, crash recovery, definition portability independent of current Library content, and served application integration remain open.

#### Implemented and verified

Native capture now serializes the existing logical ReproductionGroup checkpoint as a bounded integrity-checked recipe with a process-neutral world identity. It preserves stable Person/Group/request IDs and restores them into the same Encounter's Universe. A companion exact-ID binding table maps recorded offspring IDs to the restored native `BeingInstance` nodes and reconstructs request records only after validating the Being identity, definition signature, reservation and request consistency. The source registry must pass its existing invariant validator. Fresh-process tests author the group and native Being before publishing the Encounter, restore both identities, then continue with a native Delay. A second fresh-process scenario demonstrates logical ReproductionGroup restore and continuation; PersonalHistory committed facts and the owner validator likewise survive a fresh-process Delay continuation. An initial test fixture incorrectly attempted to publish a ReproductionGroup after an Encounter existed; the authoritative registry correctly refused that operation. The fixture now authors the group first, matching the current no-Encounter publication rule, then creates the Encounter.

The adjacent combined Reproduction/Being checkpoint suite revealed that `BeingInstance.size_category` had been added at commit `2688be7` while the standalone checkpoint's accepted field contract remained fixed. The checkpoint now emits version 4 and the `/2` Being contract including `size_category=None`; strict versioned readers retain v1–v3 support. Legacy tests now represent their actual old v1/v2/v3 wire shapes instead of retagging a current payload without removing new fields. No reproduction rules or native Being properties were changed.

| Focused command | Result |
|---|---|
| `.venv/bin/python -B -m unittest discover -s tests -p 'test_native_persistence.py'` | 10 passed, 22.258 s. Covers current native continuations plus ReproductionGroup facts/Binding and PersonalHistory facts/validator in fresh processes. |
| `.venv/bin/python -B -m unittest discover -s tests -p 'test_native_history.py'` | 10 passed, 6.632 s. |
| `.venv/bin/python -B -m unittest discover -s tests -p 'test_checkpoint_adapters.py'` | 48 passed, 19.587 s. |
| `.venv/bin/python -B -m unittest discover -s tests -p 'test_reproduction_checkpoint.py'` | 13 passed, 0.919 s. |
| `.venv/bin/python -B -m unittest discover -s tests -p 'test_reproduction_being_bridge.py'` | 6 passed, 0.096 s. |
| `.venv/bin/python -B -m unittest discover -s tests -p 'test_reproduction_being_checkpoint.py'` | 14 passed, 1.706 s, including v1–v3 compatibility, rollback and two-process continuation. |
| `.venv/bin/python -B -m unittest discover -s tests -p 'test_persistence_capability_matrix.py'` | 3 passed. |
| `py_compile` for changed persistence sources, tests and subprocess example; `git diff --check` | Passed. |

This execution adds four audited local commits through `7d866d0c6b75b3962c39e40bea2435e2d713f849`: `b5be6d25` (Group/observer callbacks and bindings), `bbbfe293` (logical registry adapter), `e402fe71` (native Being binding serialization and combined schema compatibility), and `7d866d0c` (restoration of native registry bindings). Five unrelated user-staged archive paths remain outside these commits. No push occurred. The source-linked matrix reflects only partial family coverage; this is not a gate closeout.

Fresh OS process tests now restore and continue pending Delay, consequential Dagger MeleeStrike, Stun interruption/recovery, StatisticalGroup keyed facts, two separately owned Group-observation ledgers, logical ReproductionGroup records, a native offspring Being binding, and a PersonalHistory fact. The Group/observer case compares IDs, RNG, committed receipt IDs and normalized history digest against uninterrupted native execution. Its child imports no Arena browser/session/snapshot/server or `npcgen` modules. `native_history` omits the process-local `SubjectRealityCandidate.ledger_identity`; restore resolves it by stable Group subject ID.

Focused evidence:

- `.venv/bin/python -B -m unittest discover -s tests -p 'test_native_persistence.py'` — 7 passed, 19.123s.
- `.venv/bin/python -B -m unittest discover -s tests -p 'test_native_history.py'` — 10 passed, 6.507s.
- `.venv/bin/python -B -m unittest discover -s tests -p 'test_checkpoint_adapters.py'` — 48 passed, 20.460s.
- Five focused Arena persistence regressions (compact graph corruption, pinned v4 migration, v10 and v11 migrations, exact segmented archive and partial-history refusal) — 5 passed, 7.887s.
- Capability-matrix registry tests — 3 passed in a separate run during this continuation.
- Python compile checks and `git diff --check` pass for changed native code and tests.

These are selected family results, not completion. The 1.03–1.22 MB scenario bundles still contain duplicate graph/history material; no scale claim is made.

### Verified source audit

Installed the revised full-capability assignment at its canonical `docs/assignments/U-PER-SCALE-001-NATIVE-HISTORY-BRIDGE.md` path without changing the user-provided `-REVISED.md` source. Added the initial 152-row exact field inventory and family status matrix at [`persistence-capability-matrix.md`](../design/persistence-capability-matrix.md), plus the problems-first [`native history bridge findings`](../design/persistence-native-history-bridge-findings.md). The source audit traces the production Arena encoder/decoder, checkpoint candidate, Arena restore, atomic publication/rollback, native inspection, and legacy Universe save refusal.

Focused verification: `test_checkpoint_inventory.py` — 30 passed; `test_checkpoint_adapters.py` — 48 passed. The combined package-style test command was interrupted and is not evidence. No production Save/Load implementation changed in this audit phase. The full acceptance matrix remains open and U-PER-SCALE-001 remains sole ACTIVE.

## Latest continuation — faithful native replay

### Problems first

- The bounded assignment objective is demonstrated, but it does not close U-PER-SCALE-001. Production `/12` remains unchanged and graph-backed; general persistence, long-run scale, full native historical receipt APIs, and served Arena Save/Load remain open.
- The fixed-seed native timeline did not happen to produce a failed/unproductive Action. No roll was forced and no rules changed; that optional branch is explicitly **unproven**.
- This read model preserves the declared native projection and Event/Effect chronology, not every runtime object or receipt API. Directed awareness actually represented in the fixture is compared; broader observer evidence/belief history is not claimed.

### Outcome and evidence

Installed the revised [faithful-replay assignment](../assignments/U-PER-SCALE-001-FAITHFUL-REPLAY.md) at its canonical path while preserving the byte-identical user-provided revised source. Added separate-process historical playback and current-version native re-execution to the existing Arena-independent fixture. The replay input manifest now records legal Action declarations, Choice grouping, timing, movement inputs and RNG seed. The recording includes an independent full native-state snapshot oracle at every boundary, so historical reconstruction checks the declared values/presence against original native state at t=1–9. Playback itself reconstructs from initial state plus ordered atomic changes, Event-only/quiet boundaries and cumulative Event history without native Action resolution. Native re-execution starts a new Encounter and resubmits only those declarations through ordinary `Encounter.step()` and transactional publication. At each boundary, the comparator checks typed/present fields, delta ordering, Event multiplicity/order/causality, Action outcomes, receipt Effect identities, observer awareness and RNG cursor.

Independent generated Action/Event and Choice IDs are compared through a validated one-to-one mapping; stable Being, Object, Encounter and parent references remain fixed. The nine-entry mapping covers five Action/Event identities and four Choice identities. Its remapping is consistent through Event rows, Choice packets, scheduler state and receipt references. The five t=8 EffectIdentity entries retain source Action, boundary, channel, slot, order and multiplicity; the source Action reference follows the validated map.

| Boundary | Native result | Entity property changes | All paths | Delta bytes |
|---:|---|---:|---:|---:|
| 1 | Run success | 4 | 8 | 2,906 |
| 2 | quiet | 0 | 4 | 546 |
| 3 | successful zero-Being/Object-diff Delay Event | 0 | 4 | 1,732 |
| 4 | two successful simultaneous Runs, shared receipt | 6 | 10 | 6,945 |
| 5 | quiet; scheduler pending-list change | 0 | 5 | 685 |
| 6 | quiet | 0 | 4 | 546 |
| 7 | quiet | 0 | 4 | 546 |
| 8 | native Dagger thrust, normal | 4 | 10 | 19,251 |
| 9 | quiet after strike | 0 | 4 | 546 |

The t=8 native receipt records Ada's `DamageEffect` against Bram for 4 body damage and her Dagger `PracticeEffect`; Bram HP changes 10→6. At t=4 both Run events and both position changes are one native atomic commit. The t=3 Delay event retains its `DelayDefenseEffect` despite no Being/Object property delta.

Recorded canonical UTF-8 sizes: initial state 9,020 bytes; t=4 checkpoint snapshot 10,748; t=9 snapshot 11,388; all nine delta/Event records 33,703 (Event arrays 7,651; property-change arrays 24,918); nine redundant full native snapshots retained as verification oracles 94,649; whole recording including verification oracles 266,521. Playback itself needs only initial state plus deltas/Events. One measured playback query set took 24.2 ms including validation, native re-execution plus semantic comparison 2.37 s, fresh-process strict checkpoint rehydration 47.5 ms, and child process plus t=4→9 continuation 1.76 s. Native step calls ranged 219–290 ms in that sample. Full boundaries, state digests, commands, exclusions and semantic-reference audit are in [faithful replay findings](../design/persistence-faithful-replay-findings.md).

### Assignment acceptance and verification

| `U-PER-SCALE-001-FAITHFUL-REPLAY` bounded criterion | Result |
|---|---|
| Historical playback in separate OS process, queries include quiet/Event-only/simultaneous/combat boundaries | Met for the declared projection; native `Encounter.step()` is patched to fail during playback test. |
| Reconstructed state/presence matches independently captured native snapshots, including observer awareness | Met at all t=1–9; selected queries also cover t=2/3/4/7/8/9. |
| Two simultaneous Actions remain one atomic boundary | Met at t=4. |
| Consequential native combat, causal Effects and receipt correspondence | Met at t=8, HP 10→6, five ordered receipt EffectIdentity records. |
| Separate-process native rerun matches each boundary under identity mapping | Met at t=1–9 for the same Python/source/config/rules; RNG cursor matches. This is a current-version test, not cross-version replay. |
| Corruption, chronology, preimage, unexpected path and identity refusal | Met for tested checksum changes, broken references, malformed timestamp, missing/reordered commit, bad preimage, duplicate path/Effect, unknown property path and ambiguous generated-ID mapping. |
| Fresh-process checkpoint resume | Met from t=4 through t=9, with terminal state, RNG and receipts equal to uninterrupted control. |
| Optional naturally failed Action | Not reached; explicitly unproven. |
| Generic historical native receipt objects and production persistence migration | Excluded; not claimed. `/12` unchanged. |

Focused checks:

| Command | Result |
|---|---|
| `.venv/bin/python -B -m unittest tests.test_faithful_replay tests.test_native_headless_resume tests.test_persistence_headless_delta` | 13 passed, 22.121s. Includes separate OS processes for record, playback, native rerun and checkpoint resume. |
| `.venv/bin/python -B -m unittest discover -s tests -p 'test_action_choices.py'` | 63 passed, 0.646s. |
| `.venv/bin/python -B -m unittest discover -s tests -p 'test_atomic_publication.py'` | 70 passed, 42.761s. |
| `python -m py_compile examples/encounter_delta_headless.py examples/native_headless_resume.py tests/test_faithful_replay.py` | Passed. |
| `git diff --check` | Passed. |

An initial attempt to invoke adjacent tests as package modules used an incorrect singular module name and lacked the `tests` directory on the import path; it produced import errors, not test failures. The corrected discovery commands above passed. An early new-test draft also encoded two wrong expectations (Delay has a retained effect, and Choice IDs may remain equal); both assertions were corrected to reflect observed native data and the adopted ID clarification. The final focused test set passes. No entire repository suite or long Arena persistence suite was run; no baseline claim is made about the previously reported transactional progression mismatches.

`TASKS.md` remains U-PER-SCALE-001 sole ACTIVE, U-ACT-GATE-001 FUTURE/unpassed, U-NET-001 DEFERRED and U-ACT-FULL-003 DEFERRED. No implementation priority changed. This bounded assignment is complete; the broader program is not accepted or archived. Production `/12`, Arena operation, user saves, independent `npc-generator`, frozen Playtest Edition and pre-staged historical archive operations remain outside the diff.

### Commits and audits

- `d95371bad1f15eef00be4cd832bc036460898651` — recorded declarations, time-indexed historical playback, native same-version rerun, generated-ID mapping and focused acceptance tests.
- `58542acc5c1066278ad457227b8392d05b37dbd6` — independent native-state snapshots at every boundary, comparison against reconstructed playback and snapshot-tamper refusal.
- `cd136c0282b3fb3743946cbf83e37c864f022ca2` — canonical assignment installation, findings, `TASKS.md` reconciliation and engineering-report update.
- `a9212da20161d630f47464e655aaea89dc281638` — exact state projection fields, fail-closed exclusions and sufficiency assessment.
- The final report-time/audit correction is the subsequent report-only closeout commit; its hash is the final repository HEAD reported in the Codex closeout.

Staged publication-safety audit passed with **0 findings** for the implementation commits (9 staged paths, then 8), documentation commit (10), and post-commit preserved stage (6). Explicit-path commits excluded the five user-staged archive operations. `git diff --check`, staged whitespace check and local Markdown-link check (88 links, 0 missing) passed. Branch `main`; HEAD at documentation closeout was `cd136c0282b3fb3743946cbf83e37c864f022ca2`. Tracked worktree had no remaining assignment changes, while the five user-staged archive operations and seven user untracked files remained. The untracked revised assignment was copied byte-for-byte to the canonical assignment path; the revised source remains preserved. The two untracked save files, prior user assignments, process standard and all user data remain unmodified. No push.

After the report audit, `a9212da20161d630f47464e655aaea89dc281638` added the exact projection/exclusion list and sufficiency assessment; its staged safety scan passed with 0 findings across 7 staged paths, and its three local Markdown links resolved. The final report-only commit records the execution interval and this closeout; its exact hash is the final HEAD in the Codex response. The five staged archive operations and seven untracked user files remain untouched.

## Prior continuation — native headless resume (extended by faithful replay above)

### Problems first

- This continuation closes only the bounded native-resume experiment. It does **not** close U-PER-SCALE-001: production `/12` remains graph-backed, history is reassembled on Load, served Chrome Open remains unverified, and the prototype depends on an exact matching source/config/rules checkout. It also does not recreate historical native `CommittedBoundaryRecord` objects; their committed Event/delta facts remain in the lossless experimental history, while future native receipts are created normally.
- The accepted closure is one quiescent two-Being Encounter with pinned Human/Dagger definitions, settled Run/Delay history, no pending/cancelled Actions or open Choice, and a supported Dagger thrust as the next Action. Other historical Action families, arbitrary object kinds, active schedules, personal-history values, and general native receipt queries are excluded and fail closed where checked.
- No production persistence code or `/12` behavior changed. The source change is a narrow native restore-owner hook, not a general Save/Load API. U-PER-SCALE-001 remains sole ACTIVE; no user decision or external blocker is outstanding for this bounded slice.

### Verified outcome

The headless resume helper writes a strict, sealed checkpoint at t=4 from the existing native initial+delta/Event representation. A separate OS process validates it before creating Universe/Encounter objects; restores current Being/Object state, observer awareness, RNG, settled ChoiceBook, scheduler cursor, and historical Run/Delay Event identities without resolving prior Actions; then continues five boundaries via ordinary `Encounter.step()` and native transactional publication. Canonical resumed and uninterrupted results match for current state, chronology, identities, ChoiceBook, future receipts, RNG and observer-specific awareness.

At t=8, native `action-native-dagger-strike` (`MeleeStrike`, thrust, Dagger, Ada→Bram) resolves `normal`. The native proposal contains `DamageEffect(source_action_id=action-native-dagger-strike, target_id=being-bram, amount=4, component=body)` plus Dagger practice; the atomic before/after fact is Bram HP 10→6. Receipt identities include boundary-8 effect slots 0/1, lifecycle slots 0/1, and release slot 0. Boundary 9 is quiet. Final t=9 state digest: `7b8c21204747e03396539954930c177adeb164bd5ce5a64da4e5aa41b1c8694a`.

The child process imports none of `arena_native_snapshot`, Arena session/controller/server packages, or `npcgen`. Compatibility pins Python, `src/*.py`, `src/config/*.json`, and Encounter rule Markdown; the configured Library definitions are reloaded and profile-checked. Unknown/missing closure fields, corrupted checksum, compatibility mismatch, malformed preimage, missing/reordered commits, and dangling references reject before Universe construction. Full field/readers table, commands, component sizes and boundaries are in [native resume findings](../design/persistence-headless-resume-findings.md). The original delta findings now link to this later result and retain clearly labeled historical byte measurements.

The boundary-4 sealed experimental checkpoint is **39,062 bytes**: initial state 9,020; delta stream including Events 12,134 (Event subcomponent 5,914 and change-array subcomponent 5,711); native current-state snapshot 10,748; settled action-history subcomponent 5,910; Choice/scheduler metadata 708; compatibility metadata 190; zero embedded definition bytes (definitions are pinned external dependencies). These subcomponents overlap and are not additive. In one fresh child sample validation/rehydration took 48.9 ms, whole process plus continuation 1.77 s, and `ru_maxrss` reported 51.2 MB platform units. Five native step calls in a separate control sample took approximately 269–350 ms each. These are fixture measurements, not scale claims.

### Acceptance matrix for `U-PER-SCALE-001-NATIVE-HEADLESS-RESUME`

| Criterion | Result |
|---|---|
| Fresh OS process restores native state without Arena runtime or replaying old Actions | Met for the declared pinned closure; prior Action/Event identities are materialized as historical evidence. |
| Continue the ordinary native Encounter for ≥2 boundaries and compare with uninterrupted control | Met for boundaries 5–9; state, IDs, chronology, future receipts, RNG, ChoiceBook and observer views match. |
| Preserve initial state + atomic deltas + Events, including zero-diff Event and simultaneous batch | Met; independent replay equals every recorded native boundary and the resume checkpoint. |
| Demonstrate a lawful consequential non-position property change | Met; boundary-8 native DamageEffect changes HP 10→6 with committed effect identity. |
| Reject malformed/incompatible/incomplete history transactionally | Met for tested field closure, checksum, compatibility, cursor, reference, preimage and chronology cases before graph construction. |
| Keep `/12` unchanged and report measured evidence/limitations | Met; no production persistence source/format changed. |

Focused verification: `.venv/bin/python -m unittest tests.test_native_headless_resume tests.test_persistence_headless_delta -v` — **8 passed, 16.783 s**; `py_compile` on both headless runners and `src/transactional_progression.py` passed. No full repository or Arena browser suite was run. Exact acceptance evidence and implementation details are in the linked findings. The scoped implementation and documentation commits, publication-safety audit, final HEAD and working-tree status are recorded at closeout below.

The adjacent `.venv/bin/python -m unittest test_transactional_progression -v` could not import the suite's sibling fixture; rerunning with `PYTHONPATH=tests` executed 61 tests and reported **55 passed, 4 errors, 2 failures** in 34.815 s. The four errors are existing tests scheduling overlapping Actions without the adopted acquired Multi-action skill. The two failures expect `UnsupportedEvaluation` for unsupported starting graphs during mode selection. None calls the new private resume hook, and this diff adds that hook without changing existing progression code. These discrepancies were not reproduced against a separately checked-out baseline in this time-boxed slice; they remain separately documented and were not changed here.

**Execution interval:** Start `2026-11-16T10:46:06-08:00`; End `2026-11-16T11:27:35-08:00`; elapsed `PT41M29S`.

**Current addendum disposition:** Current portable save schema `/12` (archive `/3`) stores the native resumable graph, compatibility-bound immutable definitions, and independently validated commit-boundary history. Completed native Action roots are now stored with their exact boundary segments and restored before strict native inventory validation. At t=300: snapshot 23,813 nodes / 331,315 bytes; definitions 51,921 / 560,106; history 1,139,080 / 12,815,153; compressed archive 2,968,730 bytes. Snapshot falls 39.3% (16,517 nodes / 214,795 bytes) versus `/11`, with no loss of Action identity or history. The 64+1 Feint run, 169 quiet boundaries, strict fresh-process Load→Save, and t=301 continuation pass. Supported `/10` and `/11` archives migrate through fresh processes. Chrome `/12` Save produced the served UI download confirmation; Open-file Load remains unverified because extension local-file access is disabled. HTTP/session Save/Load, transactional rejection, and interrupted-export preservation pass. The 2/20/200 curve concerns registry Beings, not active combatants. The assignment remains ACTIVE: state is still a recursive native graph, completed Choice settlement wrappers remain in current state, Load eagerly reassembles history, active Encounter participation is two Beings, and served Chrome Open is unverified.

## Exact field audit (diagnostic only)

**Problems first:** in the sampled one-Action/one-quiet sequence, the quiet commit added a 26,003-byte committed-history segment even though the resume snapshot remained exactly 12,036 nodes / 151,861 bytes. That segment added 27 owned graph rows and updated boundary/time/visibility freshness on two existing observer evidence rows. The Action boundary added 79,487 net history bytes and 179 segment-owned graph rows plus one completed Action root. Existing immutable commit projections are measurably reused: six receipt references and one of two TargetCandidate state references are identical across adjacent boundaries. These facts identify what is new versus restated but do not establish which freshness or receipt fields can safely be omitted. No persistence code or save fixture changed.

The exhaustive schema and observed-field matrix is in the new [persistence node field catalog](../design/persistence-node-field-catalog.md). It derives the 109-node-type generated-Arena allowlist (104 typed node types plus five containers) from `arena_native_snapshot._ARENA_TAGS` and `checkpoint_fields.FIELD_ADAPTERS`, then records exact allowed/required properties and actual t=0/t=1/t=2 fields. The shared field registry contains 48 additional types excluded from the Arena allowlist; the catalog lists them separately. The requested `docs/assignments/U-PER-SCALE-001-EXACT-FIELD-AUDIT.md` was absent from the checkout; this audit follows the scope provided in the user request. U-PER-SCALE-001 remains the sole ACTIVE program.

**Active execution time across five sessions:** PT8H51M55S. **Total calendar span:** PT12H31M06S from first recorded Start to last End; four inter-session gaps total PT3H39M11S and are excluded from active execution time.

The original interval established a fixed-size graph-reference encoding and corrected four checkpoint-adapter cases. The latest interval followed up because that first format still failed strict Save at t=91. Its results supersede the earlier report's t=67-only reliability conclusion.

## Sufficiency architecture and current verification

The addendum changes the target from “stay under one million nodes” to “persist only resumable facts, plus lossless history once.” This execution added a bounded portable archive, moved ten reviewed append-only history field families into ordered history segments, and made native committed inspection index Target records once instead of repeatedly rescanning each Target's full prefix. This continuation also reuses equal immutable projections across consecutive committed inspection and Target records. Receipt identity, boundary, fields, event references and history ordering remain present; only equal immutable subvalues share an in-memory graph node. The read fence recognizes only the closed frozen history fields by sequence identity; mutable fatigue frames remain content-checked. Strict inspection and checkpoint capture still validate row contents, receipt fingerprints, schema compatibility and cross-references. No native combat rule, Action eligibility, RNG algorithm or structural safety cap was relaxed.

The source audit separates four classes. Entity/Object/condition/custody/position state, RNG cursor, pending Actions and Choices, scheduler state, current observer awareness, unresolved facts and the current fatigue frame affect the next legal boundary and remain in the snapshot. Completed receipts, per-Target interval records, past fatigue frames and observer history remain durable in ordered segments. Shared immutable definitions are now in `definitions.json`, referenced by the same native identities from the snapshot/history; they are not regenerated from a current Library. Locks, pointer anchors, signature caches and display handles are rebuilt or stored only as stable IDs. The current-state representation remains a closed, compatibility-bound native graph table, not a field-minimal Arena domain-row model. The field audit omits 15 proved process-local/derived fields from the resumable document: Universe synchronization and the verified-empty reproduction registry; ChoiceBook lock and draft/validation caches; quiescent Encounter transaction flags; the absent Arena physiology registry; and coordinator clocks that must exactly equal `Encounter.time`. Restore recreates these fields. The source-linked inventory records the readers and checks. A fail-closed per-type field gate at capture, encoding, decoding and restore requires every native tag to have an explicit `FIELD_ADAPTERS` allowed/required contract; unknown fields, missing current-schema fields, duplicate field names, malformed pairs and unreviewed tags refuse. Restore requires every ordinary field and permits omission only for the explicit `ARENA_REBUILT_FIELDS` set. This closes accidental runtime-field expansion but does not itself transform the remaining graph into domain rows.

The `/12` archive carries reviewed immutable `*Definition` records in `definitions.json` and keeps exact references from the native graph. It stores completed Action roots in their commit-boundary segments. Generic Event rows and accepted ChoiceBook settlement structures remain in the compatibility-bound graph because current native consumers still resolve them.

The alternative explicit native field adapter does not currently certify the whole Arena closure: a direct read-only t=0 `capture_checkpoint_candidate(..., native_adapters=True)` probe returned `bounded_run_spot_closure_verified` together with `semantic_closure_adapter_incomplete`. `checkpoint_fields.RUN_SPOT_FIELD_CLOSURE` deliberately says it does not close unrelated Library dictionaries, all Universe aliases, receipt reissuance/anchors or general restoration. The general inventory diagnostic likewise says its semantic closure is incomplete. This explains why a compact hand-authored current-state restore could not be substituted safely in this continuation without implementing and validating new adapter/reconstruction coverage. The ordinary production path therefore remains the exact closed-type native schema; this gap is explicitly still open, not described as an accepted normalized model.

| Category | Before segmented archive | Current `/12` representation | Authority / exact fact kept |
|---|---|---|---|
| Current Being/Object state, custody, equipment, position, conditions, pending schedules/Choices, RNG and observer current knowledge | Native snapshot | Native snapshot | Authoritative input to future simulation; stable native IDs and current values retained. |
| Encounter boundary receipts and Target interval projections | Embedded prefixes in native snapshot | One ordered segment attachment per committed boundary | Durable committed record, including Action/effect identity and target-owned state. |
| Fatigue frames | Embedded Encounter list | One ordered segment record per boundary, with latest frame still available after reassembly | Prior frames remain historical; latest frame is future-relevant. |
| Observer perception history | Embedded ledger history list | Ordered per-boundary ledger attachments | Observer-specific evidence and provenance retained without omniscient reconstruction. |
| Equal immutable committed inspection projections | Detached separately in consecutive interval receipts | Reuse prior projection only when complete frozen value equality holds | Receipt identity, boundary and changed fields remain unique; no historical facts are omitted. |
| Equal immutable Target candidate state | Copied into every Target interval record | Reuse prior `TargetCandidate` only when its full value is equal | `TargetIntervalRecord` owner/boundary remains unique; changed outgoing effect identities are kept distinct. |
| Completed native Action roots | Native snapshot graph | Stable root in the exact committed-boundary history segment; absent from snapshot | Loader checks event identity, Action type, resolved state and boundary, then restores the same Action before strict inspection. |
| Generic Event rows and accepted Choice settlements | Native snapshot graph | Remain in native snapshot graph | ChoiceBook, history conversation, Action follow-up, restoration and inspection still resolve these identities. |
| Immutable `*Definition` records | Native snapshot graph | Separate compatibility-bound `definitions.json`; snapshot and history keep exact graph references | Definition type allowlist is explicit; content is included once, never regenerated from a newer Library. |
| Runtime locks, object addresses, cached signatures and browser handles | Reconstructed or session metadata | Reconstructed or stable-ID session metadata | Not authoritative facts; no raw address is persisted. |

### Current acceptance matrix

The first `/11` 5×5, 10,000-XP generated Arena measured a resume snapshot of 145,906 bytes / 11,645 wire nodes, a separate definition table of 548,728 bytes / 50,625 nodes, and 458 bytes of history in a 220,070-byte archive. The prior `/10` 2-Being measurement was 624,702 snapshot bytes / 49,179 nodes and a 213,151-byte archive. Thus the resume-only document is substantially smaller while definitions remain self-contained and exact; total archive size is slightly larger because the separate document carries its own schema and metadata. The fixture seed/profile differ from some earlier t=0 attribution values, so this is a format observation, not a controlled before/after percentage.

| Addendum requirement | Status | Evidence / remaining work |
|---|---|---|
| Field-by-field necessity/readers audit | Partial | [Inventory](../design/persistence-sufficiency-inventory.md) traces next-boundary vs historical role, ownership, source readers and shared definitions, and includes row attribution. The 2/20/200 registry curve measures unplaced Beings plus equipment, not active Encounter scaling. |
| Resumable snapshot separated from durable history | Partial | `/12` stores snapshot, immutable definitions, and digest-checked ordered history segments. Completed Action roots move to history; generic Events and accepted choice settlements remain in snapshot. History is eagerly reassembled at Load; this is not yet a compact domain-row/current-state reference model. |
| Resume-only growth plateau after action burst | Met for current 2-Being Arena case | After 65 Feints, t=131→300 advances 169 lawful quiet boundaries: snapshot stays 23,813 nodes / 331,315 bytes; definitions stay 51,921 / 560,106; history grows from 5,949,893 to 12,815,153 bytes. |
| At least 64 lawful combat resolutions | Met for the adopted Feint slice | 64 in-range Feints produced native `success`/`failure` Attack Roll receipts, followed by a 65th Action. Feint is nondamaging by rule; HP stays 81/97. This test does not establish a 64-hit damage workload or multi-opponent combat scale. |
| Exact multiple fresh-process continuation | Met for tested boundaries | Existing seed-14 branches verify t=67→72, t=91→92 and t=100→101. Generated-Arena regression saves after 64 Actions and at t=300; independent processes restore/resave exact bytes and continue t=131/t=301 identically. Stable Being/Object/Action IDs, receipts, observer history, RNG and HP are checked. |
| Proportionate lossless history and strict integrity | Met for the tested archive contract | t=300 has 300 contiguous segments, 1,139,080 history wire nodes and 12,815,153 history bytes. Missing, extra, altered/truncated segment, definitions, bad digest/CRC/path, unsupported schema/type and cursor mismatch refuse without replacing live state. Limits unchanged: 1,000,000 nodes per document, 10,000,000 aggregate nodes, 64 MiB aggregate decoded data/archive, bounded entries and compression ratio. |
| Crash/failure recovery | Met for preserving the caller's previous complete portable artifact; no autosave claim | Tests inject an export exception and kill a fresh OS process with `os._exit(73)` during history-entry writing. The previously complete `.uarena` held by the caller remains byte-identical and a second fresh OS process strictly loads/resaves it byte-identically. The source live candidate also remains unchanged on caught failure. This does not test an in-place local save-file replacement or autosave. Truncated/corrupt Load is transactional. There is no autosave/durable append journal: a crash before the user downloads a new complete artifact loses post-save progress, while the last complete file remains recoverable. |
| Legacy compatibility and prior regressions | Met for focused supported schemas | Native v3/pinned v4 and portable `/10`/`/11` migrations pass in fresh processes; 48 checkpoint-adapter tests and prior t=91/t=100 continuations pass. The current-format focused cohort also passes transactional segment rejection and 2/20/200 registry persistence. |
| Ordinary browser file Save/Load | Partial | Current served Chrome `/12` Save displayed “Encounter downloaded as a portable native save archive.” Open-file Load was blocked because the extension local-file permission is disabled. No current `/12` browser reload is claimed. The old 223,484-byte artifact is confirmed `/10` only; HTTP/session and native strict Save/Load pass. |
| World-size, memory and normal load-time scaling | Partial | Current `/12` strict fresh-process registry curve passes at 2/20/200 BeingInstances, with 0/18/198 WeaponInstances recorded in their inventories. All additional Beings are unplaced and non-participating. Resume snapshot bytes are 145,562 / 302,833 / 1,879,939; nodes are 11,621 / 24,294 / 151,014. Definitions are 551,452 / 709,564 / 2,290,684 bytes. Full portable archives are 220,106 / 311,891 / 1,202,866 bytes. At 200, create/save peak RSS is 131,104,768 bytes and Save is 0.949s; fresh Load is 0.618s, exact resave 0.931s, Load-worker peak RSS 112,787,456 bytes. Combat/perception still supports two participants. At t=300, fresh Load+exact-resave is 18.820s with 278,773,760 peak RSS.

### Extended scenario measurements

The run uses the published generated-Arena/native Encounter path, 5,000,000 XP, a fixed seed, empty ground-equipment profile, actual represented 0.2 m separation, and Difficulty Class 1 as prepublication scenario inputs. Each of the 64 Feints resolved to a native success or failure Attack Roll; no out-of-reach results were counted. A 65th Feint was chosen through the Arena session route after strict fresh-process restoration. Feint is nondamaging in the adopted rule, so preserving both Being HP at 81/97 is the expected consequence, not suppressed damage. The Action sequence and history remain persisted.

| Boundary | Feint Actions resolved | Action roots in history | Snapshot nodes | Snapshot bytes | History segments | History nodes | History bytes | Full archive bytes |
|---:|---:|---:|---:|---:|---:|---:|---:|
| t=129 (after 64 Feints) | 64 | 65 | 23,643 | 328,686 | 129 | 522,542 | 5,843,925 | not emitted in test log |
| t=131 (after 65th Feint) | 65 | 66 | 23,813 | 331,315 | 131 | 531,648 | 5,949,893 | not emitted in test log |
| t=300 (169 quiet boundaries later) | 65 | 66 | 23,813 | 331,315 | 300 | 1,139,080 | 12,815,153 | 2,968,730 |

At t=131→300 `/12` snapshot and definitions are byte- and node-stable. History increases 6,865,260 bytes over 169 commits (about 40,623 bytes/boundary). Decoded snapshot+definitions+history total 13,706,574 bytes; the ZIP is 2,968,730 bytes (4.62:1). Versus `/11`, snapshot falls 39.3% (16,517 nodes / 214,795 bytes), history increases 297,125 bytes because completed Actions now reside in boundary segments, and compressed archive falls 5,743 bytes. In the latest run Save took 4.938s; fresh-process strict Load plus exact resave took 18.820s; peak RSS was 278,773,760 bytes. These are measurements of the two-Being fixture, not projections.

History composition at t=300: 300 Encounter interval receipts, 300 fatigue frames, 600 Being Target records, 600 Armor Target records, 600 Weapon Target records, 11 observer-history records, zero skill-use records and 66 completed Action roots. History segment wire nodes total 1,139,080. Field rows remain exact and identity-linked; row category bytes are diagnostic and not additive to archive bytes. A fresh 10,000-XP, 10×5 empty-loadout t=0 Arena was measured through the live capture path: 637,923 native wire bytes and 2,369 graph rows. The ten largest canonical row groups are in the linked inventory; ordered-map rows account for 384,216 attributed bytes, followed by WeaponDefinition (112,614) and BeingDefinition (77,885).

The new t=300 snapshot diagnostic attributes the ten largest graph-row categories as follows. It counts canonical row bytes by owning node type; these numbers exclude surrounding list/manifest syntax and are not additive to `snapshot.json` bytes.

| Current snapshot row type | Rows | Canonical row bytes |
|---|---:|---:|
| Native list containers | 61 | 247,762 |
| Native ordered-map containers | 313 | 159,417 |
| Native tuple containers | 211 | 37,971 |
| Completed `action.Action` instances | 0 | 0 (roots are in history) |
| `EffectIdentity` instances | 132 | 48,800 |
| `ActionProposal` records | 66 | 48,747 |
| `PreparedSchedule` records | 66 | 47,427 |
| `LifecycleEffect` records | 66 | 43,182 |
| ChoiceBook `_Accepted` records | 66 | 36,765 |
| `ChoiceView` records | 66 | 25,213 |

Under `/11`, completed Action rows were 65 / 79,434 canonical bytes. Under `/12`, those rows are absent from snapshot and the tuple group falls from 474 / 88,508 to 211 / 37,971 bytes. The remaining 66-choice settlement records stay in current state because native ChoiceBook, history conversation, restoration and inspection still resolve them. Immutable definition records remain separately bounded.

| History closure category | Before sharing: rows / canonical bytes | After sharing: rows / canonical bytes | Byte reduction |
|---|---:|---:|---:|
| Encounter interval receipt closure | 49,133 / 25,290,613 | 4,844 / 10,433,789 | 58.7% |
| Being Target state closure | 7,266 / 2,912,394 | 2,129 / 814,630 | 72.0% |
| Armor Target state closure | 1,800 / 754,584 | 604 / 200,238 | 73.5% |
| Weapon Target state closure | 1,800 / 753,984 | 604 / 200,236 | 73.4% |
| Fatigue frames | 1,200 / 379,582 | 1,200 / 379,582 | 0% |
| Observer history | 13 / 9,047 | 13 / 9,047 | 0% |

The repeated receipt/Target projection categories fall because exact immutable state is shared. Fatigue changes with time and stays distinct; observer history count/bytes do not change in this quiet two-observer fixture. Canonical closure bytes are diagnostic row sums; ZIP member framing and encoder-shared syntax make them non-additive to archive bytes.

### World-size registry curve

The native Arena contract still admits exactly two Encounter participants and two observer ledgers. Separately, the existing `Universe.add_object`/`ObjectRegistry` accepts additional native `BeingInstance` records that are not assigned a location or encounter participation. A test now measures this supported persisted-object path at 2/20/200 Beings. For each added Being it creates one native `WeaponInstance` and appends its stable ID to `Being.weapons`, using the existing `BeingDefinition` and Dagger definition; it does not invent distinct provenance, position, perception, group membership or combat behavior. Every archive is loaded and re-saved in a fresh OS process and compared byte-for-byte.

| Realized Beings in Universe registry | Added Weapons | Snapshot bytes/nodes | Portable file bytes | Create/save peak RSS | Save time | Fresh-load peak RSS | Strict Load / exact resave |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 0 | 145,576 / 11,621 (+ 551,452 definition bytes) | 220,072 | 51,494,912 bytes | 0.216s | 47,185,920 bytes | 0.125s / 0.184s |
| 20 | 18 | 302,843 / 24,294 (+ 709,564 definition bytes) | 311,868 | 56,672,256 bytes | 0.285s | 49,250,304 bytes | 0.165s / 0.333s |
| 200 | 198 | 1,879,948 / 151,014 (+ 2,290,684 definition bytes) | 1,202,879 | 114,114,560 bytes | 1.184s | 111,165,440 bytes | 0.593s / 0.923s |

Memory is per-worker `ru_maxrss` and includes Arena generation/strict restoration, on this macOS host. The 20/200 cases are valid world-registry persistence growth, not 20/200 active Encounter participants; the current source contract does not support scaling simulation/perception participants beyond two. The portable file stays far below the unchanged 64 MiB byte and 1,000,000-node per-document limits at 200 objects. The one focused test command and exact per-process values appear below.

### Focused verification this execution

- `UNIVERSE_PER_SCALE_METRICS=1 ../.venv/bin/python -B -m unittest test_arena_persistence.TestArenaPersistence.test_64_lawful_native_feint_resolutions_segment_history_and_resume` (cwd `tests`) — 1 passed, 315.714s. At t=300: snapshot 23,813 nodes / 331,315 bytes; definitions 51,921 / 560,106; 300 history segments, 1,139,080 history wire nodes / 12,815,153 bytes; 2,968,730-byte archive. Save 4.938s; fresh-process Load+exact resave 18.820s; peak RSS 278,773,760 bytes. t=131→300 adds 169 history segments while snapshot/definitions remain fixed; byte-exact t=301 continuation passes.
- `../.venv/bin/python -B -m unittest test_arena_persistence.TestArenaPersistence.test_segmented_portable_archive_is_exact_and_rejects_partial_history_transactionally test_arena_persistence.TestArenaPersistence.test_supported_segmented_v10_archive_migrates_in_fresh_process test_arena_persistence.TestArenaPersistence.test_supported_segmented_v11_archive_migrates_in_fresh_process test_arena_persistence.TestArenaPersistence.test_native_world_registry_persistence_size_curve_2_20_200` (cwd `tests`) — 4 passed, 21.941s.
- `UNIVERSE_PER_SCALE_METRICS=1 ../.venv/bin/python -B -m unittest test_arena_persistence.TestArenaPersistence.test_native_world_registry_persistence_size_curve_2_20_200` (cwd `tests`) — 1 passed, 6.059s; exact `/12` size/time/RSS measurements above.
- `.venv/bin/python -B -m unittest discover -s tests -p 'test_checkpoint_adapters.py'` — 48 passed, 24.429s (prior focused cohort; current changes do not modify those adapters).
- `.venv/bin/python -B -m unittest test_generated_arena_browser.TestGeneratedArenaBrowser.test_http_save_and_load_use_binary_portable_file_and_atomic_replacement` — 1 passed, 0.711s. Four current `/12` browser regressions also passed (seeded two-sided combat continuation, pending shield Save/Load, shield allocation privacy, pristine Arena Save/Load) in 15.217s. These tests use the browser/server harness; they are not manual Chrome Open-file evidence.
- Current served Chrome `/12`: clicking Save displayed “Encounter downloaded as a portable native save archive.” The extension refused local-file selection for Open because local-file access is disabled. No browser permission changed and no Chrome `/12` Load is claimed.
- `UNIVERSE_PER_SCALE_METRICS=1 .venv/bin/python -m unittest tests.test_arena_persistence.TestArenaPersistence.test_native_world_registry_persistence_size_curve_2_20_200` — 1 passed, 6.808s; independent create and load OS processes at 2/20/200 native Beings, all archives exact-resave, with 0/18/198 WeaponInstances. Snapshot and definitions metrics are in the world-size table above.
- `.venv/bin/python -m unittest tests.test_arena_persistence.TestArenaPersistence.test_segmented_portable_archive_is_exact_and_rejects_partial_history_transactionally` — 1 passed, 5.615s with the per-type field-schema gate enabled; canonical round-trip, injected exception leaves native committed state unchanged, a worker killed mid-export leaves the prior full file byte-identical and a fresh worker loads/resaves it exactly, and missing/extra/altered/truncated history preserves candidate identity and save bytes.
- `.venv/bin/python -m unittest tests.test_arena_persistence.TestArenaPersistence.test_current_snapshot_requires_reviewed_per_type_field_schemas tests.test_arena_persistence.TestArenaPersistence.test_portable_snapshot_omits_rebuilt_quiescent_runtime_fields` — 2 passed, 2.381s; unknown/missing/duplicate/unreviewed data refuse, and all 15 reconstructed fields are omitted, restored, and byte-identically resaved. Their aggregate measured t=300 saving is 853 bytes / 59 wire nodes.
- Focused `test_generated_arena_browser` shield-allocation, Draw timing and Ready/Delay HTTP controls — 3 passed within a 4-test command (the fourth was the generated Throw pending/in-flight strict fresh-process save/load); total 4 passed, 8.001s with the per-type field-schema gate enabled.
- `.venv/bin/python -m unittest tests.test_arena_persistence.TestArenaPersistence.test_pinned_native_v4_schema_migrates_to_current_compact_wire` — 1 passed, 1.225s.
- `.venv/bin/python -m unittest discover -s tests -p 'test_arena_opponent_attack.py' -k old_arena_save_schema_loads_with_autonomous_strategy_disabled` — 1 passed, 0.805s.
- `.venv/bin/python -m unittest discover -s tests -p 'test_checkpoint_adapters.py'` — 48 passed, 20.070s with the per-type field-schema gate and adapters enabled.
- `.venv/bin/python -m unittest discover -s tests -p 'test_atomic_publication.py'` — 70 passed, 49.115s after this continuation's changes.
- `.venv/bin/python -m unittest discover -s tests -p 'test_interval_staging.py'` — 57 passed, 17.744s after this continuation's changes.
- `PYTHONPATH=tests .venv/bin/python -m unittest test_encounter_inspection.TestCommittedInspection` — 32 passed, 15.871s after this continuation's changes. The full `test_encounter_inspection.py` cohort had 42 passes and one failure in an earlier run: `test_shield_can_be_negative_and_has_separate_causal_damage` expected shield HP −7/8 damage, while the unchanged native resolver and committed Target receipt produce −3/4. No shield/combat resolver file was changed; the exact failure remains outside this persistence assignment.
- `.venv/bin/python -m unittest discover -s tests -p 'test_generated_arena_browser.py' -k http_save_and_load_use_binary_portable_file_and_atomic_replacement` — 1 passed, 0.667s before the one-pass grouping optimization; rerun follows below.
- `.venv/bin/python -m unittest discover -s tests -p 'test_arena_vs_arena.py' -k two_controllers_native_consequence_and_fresh_process_continuation` — 1 passed, 10.028s.
- Gate-enabled rerun of `test_arena_vs_arena.py -k two_controllers_native_consequence_and_fresh_process_continuation` — 1 passed, 10.769s.
- Gate-enabled rerun of `test_generated_arena_browser.py -k seeded_two_sided_browser_combat_hit_and_fresh_process_continuation` — 1 passed, 7.479s.
- `py_compile` passed for changed Python modules. Full repository suite was not run.

Continuation verification after the one-pass history row grouping:

- The full `tests.test_arena_persistence.TestArenaPersistence` class ran 21 tests in 439.707s; all 21 passed. The combined command also named `tests.test_checkpoint_adapters` as a package-style module, which failed to import because `tests/` is not a package on this invocation. This runner error did not affect the 21 persistence tests. The adapter file was then rerun through unittest discovery: 48/48 passed in 20.070s.
- Earlier `/11` 64-Action and `/11` 2/20/200 runs are historical evidence only; the current `/12` replacements and exact results are listed above and in the current-format metrics run.
- After one-pass history grouping, the Arena-vs-Arena consequence/fresh-process test passed (1, 10.057s), HTTP portable Save/Load replacement passed (1, 0.552s), and seeded two-sided browser combat with fresh-process continuation passed (1, 7.487s).

Those rows above are preserved as earlier `/11` evidence. The current `/12` results replace only the explicitly labeled current-format measurements. No full persistence-class rerun or repository-wide suite was run in this continuation.

### Remaining acceptance work

1. Replace the remaining recursive native graph snapshot with a compact Arena-specific authoritative state record and stable references to immutable definitions. Completed Actions now have history roots; accepted Choice settlement and generic Event structures need a consumer-by-consumer sufficiency audit before any further extraction.
2. Extend the measured 20/200 world-object curve to active Encounter participants only if the native/adopted participant and observer contract supports it. Current Arena source fixes exactly two participants and initializes exactly two observer ledgers; do not invent group or observation rules to bypass this.
3. Reduce strict t=300 Load time further and measure repeated Save/Load memory under normal browser operation.
4. Add an interrupted-export/process-kill recovery demonstration if a durable local publication path is introduced; the current portable in-memory archive has transactional rejection evidence but no persistent append journal.

The top-ten t=0 attribution is complete. Current served Chrome `/12` Save is confirmed by its UI message. Open-file Load is unverified because local-file access is disabled in the browser extension. Legacy `/10` Chrome restoration was separately verified; no current `/12` browser reload or long-history browser walkthrough is claimed.

No shield mechanics, ranged Actions, new Encounter rules or multiple-Encounter persistence were implemented. U-PER-SCALE-001 remains ACTIVE.

## Earlier graph-only outcome (superseded by the segmented archive)

The t=91 concern is resolved by a second lossless checkpoint-format improvement. Ordinary strict Save/Load now succeeds for the terminal seed-14 combat encounter at t=91 and for later t=100 state; fresh OS processes reproduce the exact checkpoint and deterministic next interval. A continuous control and fresh-process branches match full serialized state, including native time, Being/Object and Action identity, HP/equipment, receipts, observer evidence and RNG continuation. The strict structural cap remains 1,000,000 nodes.

The adopted 2026-11-15 multiple-shield passive-protection rule is authoritative in the effective Encounter supplement and linked from the Encounter README. No shield behavior was implemented in this persistence assignment.

## Earlier v5 compression acceptance matrix (superseded by the current addendum matrix above)

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
| `git diff --check` and `git diff --cached --check` | Passed; the scoped staged safety audit returned zero findings for seven intended files and five pre-staged archive paths. |

Legacy native v3 migration, pinned native v4 migration, malformed compact symbols/references, duplicate/dangling graph IDs and unsupported types are exercised in `test_arena_persistence.py`. The earlier standalone runs of those specific tests passed; they are also part of the persistence regression cohort. No whole-suite green claim is made.

## Scope, task state and preservation

- `TASKS.md` retains U-PER-SCALE-001 as the sole ACTIVE program and advances U-PER-002 with the verified t=300/65-Action bounded snapshot evidence, pending report review. U-ACT-GATE-001 remains FUTURE/unpassed; U-NET-001 remains DEFERRED; U-ACT-FULL-003 remains DEFERRED. Shield completion is next; ranged Actions remain after shared geometry.
- The inbox check found no files under `docs/ideas/inbox/`.
- The five pre-staged user archive paths remain unchanged and excluded from these commits: deletions of U-CAP-002/U-CAP-003 assignment and report files, and the U-THROW-001 patch rename into archive. Untracked `docs/assignments/universe-arena.json` and `docs/assignments/universe-arena.uarena` remain untouched. `.venv`, ignored `legacy/`, saved worlds, independent `npc-generator`, repository backups and the frozen Playtest Edition were not modified.
- No shield implementation or geometry, ranged Action, combat-mechanics, observer privacy or NPC generation work was added. Save/Load preserves represented observer evidence and combat state.

## Headless initial-state/delta proof — 2026-11-16

### Problems first

- Historical status at the initial/delta-only milestone: the proof was narrower than the 109-node Arena schema and did not establish general Action/Choice rehydration or a portable native save. The later bounded fresh-process resume is reported above; it does not change these general limits.
- At the prior checkpoint, `checkpoint_inventory` marked its closure incomplete with `restore_verified=False`, and `require_complete()` refused because it had no restore support. The same-process `arena_native_snapshot` probe (920,938 bytes) did not test fresh-process continuation. These statements describe the earlier delta-only experiment; the bounded two-Being native resume was subsequently implemented and verified in the latest continuation.
- The demonstration exercises one successful moving Run, one no-effect successful Delay, three quiet boundaries, and two same-boundary Run Actions. It does not cover damage, failed combat, newly acquired observer evidence, fatigue/conditions/equipment evolution, entity birth/removal, arbitrary Event consumers, or pending future Choices. Those are unresolved production field/history coverage, not a blocker to this bounded proof.
- The earlier 26,003-byte quiet history segment is from a different generated-Arena fixture; no direct same-scenario storage comparison exists.

### Accomplished and tested

Added [`examples/encounter_delta_headless.py`](../../examples/encounter_delta_headless.py) and its independent [`test_persistence_headless_delta.py`](../../tests/test_persistence_headless_delta.py). The runner authors fixed Being/Encounter IDs, positions, geometry, awareness and private RNG seed, then uses the ordinary native `Encounter.step()` → transactional staging → atomic publication route. It does not import or call Arena session/controller/browser/server, Chrome, `npcgen` or GUI code. The recorder does not evaluate Actions or mutate the live graph.

It captures the declared current-state closure: stable Encounter and Being identities, participant ordering, definition keys, position with explicit null/presence, HP, ordered possession/weapon references, directed awareness by observer, pending Action IDs, RNG cursor, and boundary/time metadata. Completed native Action Events are recorded separately with Action/Event IDs, type, parent, actor/target, timing, native outcome and committed effect identities, even when no current-state property changes. Each boundary's property diff is one before/after change set; the two simultaneous movements are attached to the same native committed receipt. Boundary 7's full experimental projection replays byte-identically from the initial state and seven ordered deltas.

| Boundary | Native event(s) | State-property delta | Actual/replay SHA-256 prefix | Delta bytes |
|---:|---|---|---|---:|
| 1 | Run, success | Ada position `[0,0,0]` → `[1,0,0]` | `b7f521a5b02f` | 563 |
| 2 | Quiet | none | `b7f521a5b02f` | 130 |
| 3 | Delay, success | none (zero-diff Event retained) | `b7f521a5b02f` | 451 |
| 4 | Two Runs, same native receipt | Ada `[1,0,0]` → `[2,0,0]`; Bram `[2,0,0]` → `[1,0,0]` | `931378bdfeee` | 1,015 |
| 5 | Quiet | none | `931378bdfeee` | 130 |
| 6 | Quiet | none | `931378bdfeee` | 130 |
| 7 | Quiet | none | `931378bdfeee` | 130 |

The exact field audit, full SHA-256 values, risk analysis and source links are in [`persistence-headless-delta-findings.md`](../design/persistence-headless-delta-findings.md). Seven quiet/action commits retain precise boundary time even if their domain diff is empty; boundaries 5–7 cost 130 bytes apiece in canonical JSON. Initial state is 7,320 bytes, the seven deltas 2,557 bytes (1,261 Event-array bytes and 406 diff-array bytes, including empty arrays), selected full experimental snapshot 7,352 bytes, and total uncompressed artifact 17,320 bytes. A sampled runner execution used 1,590.151 ms in native steps and 1.225 ms in capture/diff/hash. These are one small fixture, not a universal performance estimate.

Focused validation: `.venv/bin/python -B -m unittest tests.test_persistence_headless_delta -v` — **4 passed, 6.770s**; it independently launches the CLI twice and confirms deterministic canonical bytes, compares reconstructed and actual state after every boundary, retains the zero-diff Delay Event, checks directed observer views and same-receipt simultaneous Actions, and rejects altered preimages, duplicate paths/commits, missing commits and reordering. `.venv/bin/python -B examples/encounter_delta_headless.py` passed (7 native boundaries / 4 Events). `py_compile` for the two new Python files and `git diff --check` passed. No full repository, browser or extended Arena suite was run; no production persistence source was modified.

### Acceptance against this bounded proof; current standing

| Bounded proof requirement | Result |
|---|---|
| Runnable independent native runner; no second resolver | Met |
| Initial realized state and typed stable property paths | Met for the enumerated closure; definitions are referenced by Library key |
| Atomic property diffs and causally associated Events, including zero-diff Event | Met for the tested native commits |
| Reconstruct and compare each Action/quiet boundary; full snapshot | Met for all seven tested boundaries and the selected boundary-7 projection |
| Simultaneous batch where native contract supports it | Met as one two-Action commit receipt with one atomic two-Being diff; not a contested combat test |
| Deterministic rerun and malformed chronology/preimage refusal | Met |
| Storage/execution measurements | Met for this fixture; no direct generated-Arena baseline comparison |
| Fresh-process native resumability | Historical status in the prior delta-only closeout; now demonstrated for the explicitly bounded closure in the latest continuation above. Generic/production restoration remains open. |

The initial/delta experiment was complete at that earlier milestone. Its lack of restoration was closed only for the bounded native resume fixture described above. **Recommendation remains: do not integrate the delta representation into production yet.** Exact excluded field families and the absence of generic rehydration mean broader sufficiency remains unproven. Continue U-PER-SCALE-001 as sole ACTIVE; keep U-ACT-GATE-001 FUTURE/unpassed, U-NET-001 DEFERRED, and do not move on to shield work under this incomplete persistence program. No production Save/Load, rule, Arena mode, observer evidence or history was changed.

### Commits and closeout

- `221cf3820af5ddab08db0223df0e0558e938b570` — add deterministic headless native Encounter delta runner and focused regressions.
- `d6757cfe3aeafab1c207d6aa97a51b0edc0e0042` — validate stream chronology, boundary/time agreement, and duplicate property-path refusal.
- TASKS/findings/report closeout documentation is committed separately after these implementation commits. The five unrelated staged archival paths remained excluded. No push was performed.

The latest report's code-only/progress conclusions are superseded only within the scope of this dated experiment; U-PER-SCALE-001 remains ACTIVE and unaccepted pending its broader persistence criteria.

## Commits

- `5076e497d3b92cf31a77fd4d59c112ffa4fe2387` — register U-PER-SCALE-001, archive accepted U-ACT-FULL-002 assignment/report, integrate the adopted shield supplement, and reconcile program priorities.
- `240668f867bbda3469b60a34a98effc5cba3819d` — introduce compact long-running checkpoint graph identities and initial regressions.
- `17c147ad4ddab102dce52acd4cd7e301dc00a132` — earlier report closeout for the initial t=67 milestone, now superseded by this follow-up evidence.
- `d345ed525217571acbd68861c016824af69c8e80` — compact repeated-string/pair inventory encoding, unique-node capture limit correction, terminal-continuation handling, extended fresh-process regressions, and TASKS reconciliation.
- `a561e78909b084ce758b1f8829e0c5951c08f858` — `/10` segmented portable snapshot/history archive, strict archive checks, incremental Target-history inspection, append-only read-fence identity checks, generated 64-Action/t=300 fresh-process regression, and source-linked sufficiency inventory.
- `8fe46b1bec68105306528123187795b0f2167979` — equal-value inspection/Target history sharing, 2/20/200 world-registry growth with exact fresh-process round trips, archive interruption/process-kill recovery, and their tests and measurements.
- `1a4199c` — fail-closed Arena snapshot field allowlists/required-field checks, per-type coverage additions, and focused negative-schema regressions.
- `ef01b913a129c17a58a2a17e831d84702eab5c9e` — portable save/archive `/12` and `/3`, completed Action roots in commit-boundary history, strict `/11` migration fixture, and extended exact continuation regressions.
- `c20b3bde4c122683884c43442eb8a3a26e2670a0` — reconcile TASKS, the source-linked sufficiency inventory, `/12` acceptance evidence, exact world-size measurements and browser limitation.

**Historical closeout at the `/12` milestone:** latest implementation commit at that time was `ef01b913a129c17a58a2a17e`. The current report status and faithful-replay continuation above supersede that milestone summary.


## Prior milestone closeout — native headless resume slice (superseded by faithful replay above)

- Implementation commits: `0de182cef463bc0d161752a17a0b060caa7aa12d` — bounded Arena-independent native Encounter resume, native HP consequence and focused tests; `71280b060bd8fa26157505d754972d06fe8ff155` — missing-checkpoint-metadata regression.
- `TASKS.md`, prior delta findings, this engineering report, and `docs/design/persistence-headless-resume-findings.md` were reviewed together. Documentation commit: `2c8d21d19c78096f307ccf3e5d72d611ea2fe8a4` — reconcile TASKS, previous findings, this report and the new native resume findings.
- Final focused run: **8 passed in 16.783 s**; `py_compile` and `git diff --check` passed. A direct fresh-CLI write/resume command also reached t=9 with Bram HP 6, zero forbidden Arena imports, 46.558 ms strict load/rehydration and 48,300,032 peak-RSS platform units. The 61-test adjacent transactional suite result and non-baseline-reproduced six mismatches are above.
- `tools/check_publication_safety.py --staged` passed before the implementation commit (11 staged paths, 0 findings). After the scoped commit, the five unrelated historical archive operations remain staged and unchanged; the safety check again passed (6 staged paths, 0 findings). No unrelated staged paths entered the implementation commit. The user-provided assignment, archive save artifacts, process standard and other untracked files were preserved.
- Active time across six recorded sessions is `PT9H33M24S`; total calendar span is `PT18H44M55S`, with `PT9H11M31S` between sessions excluded. No push or history rewrite. U-PER-SCALE-001 remains sole ACTIVE; this bounded native resume is verified, while the broader program is not complete.

## Full-capability continuation — history fidelity at scale

### Problems first

- Acceptance remains open: native Saves still duplicate the runtime receipt/Target graph beside fact history. Existing native inspection reads that graph; the fact log does not yet reconstruct every implemented inspection family or all state needed for equivalent arbitrary queries.
- Broad current-state family coverage, native `/10`–`/12` migration, crash recovery, and ordinary application Save/Load integration remain unproven. No user-rule or external blocker has been found.

### New verification

`examples/native_persistence_scale.py` now checks reconstructed `state_at`, `events_at`, and `rng_state_at` against native committed receipts before Save. It compares TargetCandidates, EntityInspection context, boundary/time, schedule, objective facts/use, projectile states, ordered Action/Effect IDs and exact RNG at every logical boundary. The read session keeps one index entry per persisted segment, so compressed quiet spans stay compact in memory. Quiet spans are expanded by the query API. A focused regression verifies Action plus quiet-span checks and rejects a deliberately mismatched query result.

| Scenario | Checked native boundaries | Native Actions | Graph bytes | History bytes | Save bytes | Scenario / export / fresh-process continuation | Peak RSS |
|---|---:|---:|---:|---:|---:|---|---:|
| Dagger Feint scale (/4) | 129 | 64 | 4,835,058 | 1,179,083 | 7,625,974 | 74.060 / 1.313 / 5.022 / 6.821 s | 180,862,976 |
| Quiet intervals (/4) | 200 | 0 | 4,837,221 | 33,154 | 6,482,929 | 45.431 / 0.630 / 2.810 / 3.170 s | 154,320,896 |

Timing column order is simulation / historical queries / Save export / fresh-process Load+continue. The query check constructs `NativeHistoryQuery` once and reads each state, event/effect, RNG and EntityInspection context boundary; its cost is measured separately from simulation.

Both strict fresh-process Loads and native Delay continuations matched uninterrupted controls. The runs extend history proof to high-activity and quiet-span scale, but do not resolve graph duplication or establish all-family query parity.

The validated read session reduced the 129-boundary comparison from 29.705 s to 1.313 s and the 200-quiet-boundary comparison from 2.180 s to 0.630 s in these reruns; all returned projections remained equal to the native receipts.

Focused results in this continuation: `PYTHONPATH=tests .venv/bin/python -B -m unittest discover -s tests -p 'test_native_history.py'` — **16 passed, 16.878s**; the same command for `test_native_persistence.py` — **17 passed, 60.984s**; `test_persistence_capability_matrix.py` — **3 passed**. The 64-Action and 200-quiet-boundary runner commands both passed. Python compile and `git diff --check` passed. The runner-verification commit is `4e1be20d56746a2460e4c1b7529fca4a6c63aa9d`; schema `/4`, sparse EntityInspection history and query APIs are in `3f8e6644c2b43a12772c81e2b32a18f1e0c7af26`. Both scoped commits passed the staged publication-safety audit with zero findings. The five unrelated staged archive paths remain unchanged and were excluded. No production `/12` code or format changed.

### Full-capability continuation — in-progress RunAction restoration

**Problems first.** The native family matrix still has broad unclosed coverage, and its `RunAction` row previously described only Arena graph capture with no native historical or continuation evidence. This was an evidence gap for a supported movement Action; it does not resolve duplicate graph/history storage or the full acceptance gate.

Added `NativePersistenceTests.test_running_action_history_and_pending_continuation_in_fresh_process`. It schedules a native `RunAction` at t=0, applies ordinary Encounter velocity inputs through t=1, and saves while that Action remains unresolved. The fixture carries a registered `human-r4` physiology profile, Q/B fatigue state, and configured Exertion values. A separate OS process uses strict `load_path()`, verifies the pending Action's original start position, current Being position, saved fatigue view and exact resolved-profile version, then continues via ordinary `Encounter.step()` to t=2. The resumed result exactly matches the uninterrupted control for position, Run outcome, PracticeEffect source Action ID, earned XP and skill-use facts, Q/B state, restored/following fatigue frames, Exertion values, receipt Action IDs, RNG state, and canonical full-history digest. `NativeHistoryQuery.entity_context_at()` also returns the actor's position at t=1 and t=2. No historical Action was resolved again and no Arena/npcgen dependency was used.

Final focused verification: `PYTHONPATH=tests .venv/bin/python -B -m unittest discover -s tests -p 'test_native_persistence.py'` — **18 passed in 52.602s**; the same discovery command for `test_native_history.py` — **16 passed in 17.006s**; `test_persistence_capability_matrix.py` — **3 passed in 0.006s**. From `tests/`, `PYTHONPATH=../src ../.venv/bin/python -B -m unittest test_running_action` — **8 passed in 0.076s**. The test was first invoked from the repository root and errored because this legacy fixture loads `../src/config` relative to its working directory; rerunning from its expected `tests/` directory passed without code changes. Python compilation, `git diff --check`, and Markdown relative-link checks (4 maintained files, 0 broken links) passed. Implementation/docs/test commit: `56c782f` (`Verify native RunAction and fatigue continuation`). The staged audit passed with 11 staged entries and 0 findings; the commit explicitly named only the five owned files, preserving all unrelated staged archive paths. The `RunAction`, Being, Encounter, Exertion, physical-fatigue, and physiology rows in the capability matrix now link tested native state and explicitly retain graph-backed history and broader state parity as limitations.

### Full-capability continuation — fatigue facts in history schema `/5`

**Problems first.** Schema `/4` retained EntityInspection and Q/B in the live committed receipt graph, but the separate fact history omitted Q/B and the resolved physiology versions used at that boundary. That prevented standalone historical queries from proving these represented temporal facts and made the old report's fatigue family coverage a Save/Load-only claim. The serializer also needed explicit compatibility semantics for older logs that never recorded these facts.

`prepare_record()` now binds the receipt's frozen physical-fatigue view and ordinary/running resolved-physiology records into each Being's existing EntityInspection context. History schema `/5` validates the exact Q/B shape and resolved-profile identifiers, modes and version hashes. Both `fatigue_context_at()` and `NativeHistoryQuery.fatigue_context_at()` provide boundary reads. `/4` remains readable; upgrade preserves its EntityInspection context and explicitly marks Q/B/profile facts unavailable. `/1`–`/3` remain accepted and explicitly lack EntityInspection facts. On native Save migration, `/4` history is compared against the restored graph after stripping only the new `/5` fatigue facts; the recorder then binds to full authenticated facts from that graph. No current or prior fact is synthesized from future state.

The RunAction scenario now spans t=1–3: save at t=1 while Run is pending; restore in a fresh process; commit 250 Run XP and rank 1 at t=2; then capture a quiet t=3 frame. Historical position, configured Exertion, Q/B values, frozen ordinary/running profile versions, and exact profile-version change after rank-up match the uninterrupted control. Outcome, PracticeEffect source ID, XP, receipt identity, RNG and native history digest also match.

Final focused checks for this code revision: `test_native_persistence.py` **19 passed in 62.274s**; `test_native_history.py` **17 passed in 19.198s**; `test_atomic_publication.py` **70 passed in 45.929s**; `test_persistence_capability_matrix.py` **3 passed**. The two affected larger adjacent suites remain red on the same unrelated cases: `test_encounter_inspection.py` **42 passed, 1 failed of 43** (negative shield damage projection); `test_action_evaluation.py` **140 passed, 1 failed of 141** (Touch fixture's third Being is out of reach). I reproduced both against the unmodified `src/encounter_inspection.py` from baseline HEAD `a0062420c005820e1a2833adafffb2b6473723fd`, with the same outcomes. Neither behavior is changed by the history projection, and I made no combat-rule or fixture changes. The tested `/5` 64-Action and 200-quiet-boundary storage/continuation runs are still pending. The native receipt/Target graph remains duplicated; full family closure and production cutover remain open.

### `/5` extended scaling verification

**Problems first.** The native fact stream is compact for quiet time, but the resumable graph still includes the committed receipt/Target/inspection graph. The new measurements validate the current native APIs for these scenarios; they do not prove full family coverage or production cutover.

Reran the headless scale program on the `/5` code. The 64-Action Dagger Feint scenario checks all 129 committed boundaries against native receipts, then saves, strictly loads in a fresh OS process, continues with Delay, and compares exact Encounter/Action identity, history digest, RNG and resulting state with uninterrupted execution. Registered-Beings scaling uses additional realized but unplaced registry Beings; it does not assert 200 active combatants. The 200-boundary quiet case checks each logical boundary and exact fresh-process continuation.

| Scenario | Registered Beings | Boundaries | Graph B | History B | Save B | Simulation / query / export / load+continue s | Peak RSS platform units |
|---|---:|---:|---:|---:|---:|---|---:|
| 64 Dagger Feints | 2 | 129 | 4,843,222 | 1,180,038 | 7,637,817 | 67.035 / 1.082 / 5.104 / 6.660 | 176,717,824 |
| 64 Dagger Feints | 20 | 129 | 5,079,888 | 1,180,038 | 7,953,369 | 66.949 / 1.124 / 4.762 / 6.784 | 184,827,904 |
| 64 Dagger Feints | 200 | 129 | 7,507,644 | 1,180,038 | 11,190,377 | 67.325 / 1.136 / 5.676 / 7.207 | 231,571,456 |
| 200 quiet boundaries | 2 | 200 | 4,837,692 | 34,109 | 6,484,512 | 44.458 / 0.767 / 2.792 / 3.156 | 148,422,656 |

The fact-history byte count remains constant across the 2/20/200 registry Action scenarios because the additional Beings do not participate; graph and total Save bytes increase with their serialized definitions/instances. The quiet stream is 34,109 bytes for 200 boundaries, while the graph remains 4,837,692 bytes. No one-million-node or portable-byte refusal occurred. Production `/12` is unchanged. These measurements supersede only the `/4` fixtures' byte/timing values, not their code or accepted `/12` measurements.

The existing focused results on this `/5` change remain `test_native_persistence.py` 19 passed (62.274s), `test_native_history.py` 17 passed (19.198s), `test_atomic_publication.py` 70 passed (45.929s), and `test_persistence_capability_matrix.py` 3 passed. Scale commands passed for 2/20/200 registered Beings and 200 quiet boundaries. `test_encounter_inspection.py` remains 42/43 and `test_action_evaluation.py` 140/141; each lone failure was reproduced using baseline `src/encounter_inspection.py` at HEAD `a0062420c005820e1a2833adafffb2b6473723fd`. The failures are the shield negative-damage projection expectation and a third-Being Touch fixture that is out of reach. They are not caused by `/5` and no rules/test relaxation was made.

U-PER-SCALE-001 remains ACTIVE. Historical read parity for all supported consumers, the general supported-family inventory, native migration of accepted `/10`–`/12` Saves, durable append-journal crash recovery, and ordinary app Save/Load integration remain unverified. No user-rule or external blocker has been identified.

### Legacy archive reading through the native API

`native_persistence.load_legacy_arena_save()` now provides an explicit coexistence reader for strict generated-Arena `/10`, `/11`, and `/12` archives. It calls the existing portable decoder for archive validation/migration, then restores the decoded typed inventory through the reviewed graph restorer. It creates no Arena session and does not import the browser, server, or `npcgen`; it does not rewrite the source file or claim native-format conversion. Fresh processes read committed `/10` and `/11` fixtures and a generated `/12` Save. The `/12` fixture contains a completed native RunAction; one ordinary `Encounter.step(1)` after restore matches uninterrupted control for logical IDs, time, position, Action outcome, RNG and complete native-history digest. All three version cases pass. Native-wire conversion and parity for new history authored before the `/12` migration point remain open.

The complete Arena persistence suite was also rerun after `/5`: `PYTHONPATH=tests .venv/bin/python -B -m unittest discover -s tests -p 'test_arena_persistence.py'` — **22 passed in 448.291s**. It emitted Python's duplicate `snapshot.json` warning from an intentional malformed-archive test; the strict refusal test passed. `test_checkpoint_adapters.py` — **48 passed in 24.137s**. The native persistence suite now passes **21 tests in 64.428s**, including three legacy-version subprocess subcases and the pending-flight case below. The legacy-reader-only run was **1 test passed** (three version subcases, 1.361s).

After extending the legacy `/12` subcase to continue its settled RunAction and adding the explicit PersonalHistory reader assertions, the full native persistence suite passed again: **21 tests in 67.760s**.

### Pending projectile to shield interception across native restore

The native persistence tests now save after a real Throw Action releases a Dagger but before its flight arrives. Seed 116 produces a native hit on an armored Being with a donned Small shield. The control and fresh OS process both continue via ordinary `Encounter.step()` until impact and compare logical history digest, RNG, Action/Effect history, target HP, shield HP, interception status and the exact incoming/passed protection values and shield durability. The test asserts that the result is a hit and the shield did intercept it. Focused command: `PYTHONPATH=tests .venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_projectile_shield_interception_continues_after_native_fresh_process_load` — **1 passed, 4.143s**. The remaining Throw/Shoot/Deflect variant matrix is open; this closes only the tested pending-flight/shield-interception continuation path.

PersonalHistory's supported `inspect_episode()` and `facts_at()` readers are now called in the fresh-process Save/Load continuation test, and the committed historical constraint is revalidated there. `PYTHONPATH=tests .venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_personal_history_facts_and_validator_resume_in_fresh_process` passed **1 test in 2.619s**. This verifies query parity for the saved ledger fact itself; it does not create a per-Encounter mutation timeline for direct RealityLedger changes that occur outside an atomic Action.

The corruption test now changes a committed property preimage and recomputes both the history and outer Save digests. Strict Load still rejects the record by causal preimage validation. `PYTHONPATH=tests .venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_strict_outer_integrity_and_duplicate_keys_are_rejected` passed **1 test in 1.590s**. This supplements digest, duplicate-key and native graph/history cross-checks; the full adversarial portfolio remains open.

### Reusable headless native scenario authoring

`src/native_scenario.py` adds a reusable `NativeScenarioBuilder` for native setup state and declarations. It creates the ordinary `Universe`, `Encounter`, explicit deterministic RNG owner and native progression binding; it provides represented Being position/geometry/HP, awareness, equipment and participant helpers, and accepts real Action/Choice objects. It delegates all scheduling, evaluation, atomic publication and timing to the existing engine and contains no resolver logic. `tests/test_native_scenario.py` launches it in a fresh process, commits a Delay, strictly Save/Loads through the native API, checks the historical event and same Encounter identity, and confirms no Arena application/server/browser or npcgen imports. Command: `PYTHONPATH=tests .venv/bin/python -B -m unittest discover -s tests -p 'test_native_scenario.py'` — **1 passed, 1.044s**. This provides a general fixture harness; the accepted Action-family coverage and historical gaps remain as shown in the matrix.

### Native custody continuation — simultaneous co-holding Wrest

**Problems first.** The native graph has committed ObjectGrip transfer effects and the existing native/legacy checkpoint tests prove three-Being co-holding in the Arena checkpoint. Native Save/Load had not independently exercised this legal state, so the native co-custody behavior was an unclosed current-family row. This test does not remove the larger duplicated receipt/Target graph or provide all-family historical query parity.

Using only `NativeScenarioBuilder` and native `Action`, the test authors a holder and two challengers with represented reach/geometry and a single Dagger Object. Both challengers simultaneously Grab the same held Object, then schedule simultaneous Wrest contests that both succeed under the scripted native roll stream. Native Save occurs after the shared-custody transfer. An independent OS process uses strict `native_persistence.load_path()`, checks the same Object logical ID, both exact holder/hand pairs, both original Wrest Action IDs and the stable custody anchor, then schedules the same Delay Action and steps through the ordinary Encounter. Time, RNG, Action IDs, custody, Object ID and canonical full-history digest equal uninterrupted execution. The child `PYTHONPATH` contains only `src` and `examples`, and the child does not import Arena/browser/server or `npcgen` modules.

Focused verification: `PYTHONPATH=tests .venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_simultaneous_three_being_wrest_coholding_restores_and_continues -v` — **1 passed in 2.995s**; full `PYTHONPATH=tests .venv/bin/python -B -m unittest discover -s tests -p 'test_native_persistence.py'` — **23 passed in 71.174s**. The matrix and TASKS now identify the demonstrated scenario. The remaining matrix and production cutover are still open; this is a verified family increment, not assignment completion.

### Native pending-choice continuation — post-roll Disarm landing

**Problems first.** The pending Disarm landing is a distinct user choice after an Action's opposed roll. A saved tag alone was insufficient evidence: the native restorer must recreate the lawful landing-choice handler and preserve the same target weapon and committed action receipt. This was not previously covered through the native Save API.

The Arena-independent fixture uses `NativeScenarioBuilder`, the represented native hex layout, and the normal Disarm Action. Seeded rolls produce `landing_choice_pending`; the test saves before selection. A fresh OS process strictly loads the native Save, validates the same pending tag and action identity, obtains legal options from `disarm_landing_options()`, chooses the same first option as uninterrupted control through `choose_disarm_landing()`, then continues with a native Delay. Both paths agree on logical weapon/action IDs, dropped location and custody, time, RNG and authenticated history digest. No Arena session or alternate Action resolver is used. This does not claim every Disarm margin, contested/invalid choice or all Action families are covered.

Focused command: `PYTHONPATH=tests .venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_pending_disarm_landing_choice_restores_and_commits_same_weapon -v` — **1 passed in 2.829s**. The full `PYTHONPATH=tests .venv/bin/python -B -m unittest discover -s tests -p 'test_native_persistence.py'` suite then passed **23 tests in 71.174s**, including both the pending Disarm choice and simultaneous co-holding cases. All-family query parity, graph deduplication, crash recovery and production cutover remain open.

### Native initial Save and deferred history start

**Problems first.** `native_history.capture()` requires a published boundary, so native Save previously refused a valid Encounter before its first `Encounter.step()`. That excluded an initial authoritative snapshot containing accepted pending Actions/Choices. Emitting a synthetic time-zero commit would have invented history and distorted adopted timing.

The native Save now records `history: null` only when the complete authenticated native graph is at its exact pre-first-boundary cursor. Strict Load validates the graph, requires the absence of receipts and unchanged start/time/boundary cursors, restores transactional progression including accepted declarations, and attaches a deferred recorder. The first successful native publication initializes history from its genuine committed receipt; no event is fabricated and a failed initial export does not attach the recorder. Ordinary committed-history Saves retain their existing strict history cross-check and recorder restoration.

The fresh-process regression saves an accepted same-Being two-Action Touch composition before the first boundary, including adopted priority penalties `(0, 3)`. After strict Load, both Actions resolve through ordinary `Encounter.step(1)` and the same logical Action/Choice IDs, priority declarations, RNG, outcome facts and canonical history digest match uninterrupted execution. The child imports no Arena app/server/browser or `npcgen`. The same test confirms a rejected initial export leaves no recorder attached and an accepted Save attaches only a deferred recorder after full candidate validation. `.venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_multiple_action_choice_and_simultaneous_touch_resume_from_initial_save -v` — **1 passed in 1.619s**. The complete native persistence suite then passed **24 tests in 76.080s**; `test_native_history.py` passed **17 in 18.582s**; `test_native_scenario.py` passed **1 in 1.323s**; capability-matrix validation passed **3 in 0.025s**. A non-initiated Encounter cannot enable transactional progression under the current `_preflight` contract, so initial native Save applies to an initiated Encounter at its starting boundary; this work does not change Encounter initialization rules.

### Deterministic repeated Multiple-action IDs

**Problems first.** Fresh-process continuation of a saved accepted successor Choice matched the native state and RNG but produced different Action IDs after the cycle completed. `ChoiceBook._repeat_completed_programs()` cloned each repeated component with the process-random `uuid4()` identity from `Identifiable`; that violated exact same-Encounter Save/Load continuation even though the declaration, order, and resolution were the same. The persisted ChoiceBook counter already made successor Choice IDs stable.

Repeated component IDs now use UUIDv5 over the persisted Encounter ID, the completed parent Choice ID, resolution boundary, and stable member key. This is only identity derivation for already-declared repeat cycles; action timing, priority, eligibility, rolls, resolution, and initial Action identifiers are unchanged. The test authors a two-Touch Multiple-action program, resolves one full cycle, saves with the automatically accepted next cycle, then resumes the next cycle in a fresh OS process. It compares literal Action/Choice IDs, Action states/outcomes, priority penalties, RNG and history digest against uninterrupted execution. Focused command `PYTHONPATH=tests .venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_repeating_multiple_action_successor_choice_resumes_natively -v` — **1 passed in 2.013s**. Regression checks: `test_action_choices.py` — **63 passed in 1.468s**; `test_multiple_action_rules.py` — **5 passed**; full native persistence suite — **25 passed in 78.810s**. This corrects deterministic repeat identity for the tested native program; other repeatable Action subclasses and broader declared compositions still need family-by-family parity coverage.

### Native Draw and Shield Don/Remove continuation

**Problems first.** `ReadyWeaponAction` and `ShieldEquipmentAction` already had reviewed native transactional evaluators, effects, restore adapters and Arena tests, but their scheduling guards unnecessarily required `arena_activation_enabled`. This contradicted the assignment's Arena-independent native API and meant those supported committed equipment transitions could not be authored by `NativeScenarioBuilder`. No Action timing, equipment eligibility, custody rule, or resolution behavior needed changing.

Both schedule guards now require the same native transactional Encounter contract already used by the evaluator. The Draw guard still accepts the explicit first-choice generated-Arena legacy route and all remaining eligibility checks stay in place: exact carried custody, authored worn-sheath source, and a represented free hand. Shield Don/Remove still requires exact carried Shield identity, a represented hand, adopted shield swing timing, non-Tower Don, and the existing held-state conditions for Remove.

`tests/test_native_draw_persistence.py` authors these cases using only `NativeScenarioBuilder`, native definitions and the normal `Encounter.step()`/native Save APIs. It saves the accepted Draw Choice at t=0 before any committed receipt, then compares uninterrupted execution with a fresh OS process through t=2. It compares same Action/Weapon IDs, finished state, hand, possession/weapons lists, parent custody, RNG and authenticated history digest. It separately saves pending Shield Don at t=0 and pending Shield Remove after the Don commit; each fresh-process path finishes through ordinary native steps and matches the uninterrupted control for the same identities, hand/bear state, carried custody, RNG and history. This directly verifies pending-choice start, delayed effects and equipment state without importing Arena.

Verification at the Draw/Don increment: `.venv/bin/python tests/test_native_draw_persistence.py` — **2 passed in 23.889s**. `PYTHONPATH=src:examples:tests .venv/bin/python -B -m unittest test_arena_ready_weapon.TestArenaReadyWeapon.test_shield_don_remove_native_browser_choices_and_pending_fresh_process_restore test_arena_ready_weapon.TestArenaReadyWeapon.test_tower_shield_don_is_refused_by_adopted_wielding_rule test_native_draw_persistence -v` — **4 passed in 47.504s**. The authored Arena Draw, committed-at-two-second-boundary Draw, and Arena pending Draw fresh-process regressions also passed in focused runs; the pending subprocess required the repository source `PYTHONPATH`, which was present on the corrected invocation. Matrix rows for Draw, Shield Don/Remove and their effects now identify this native test. These increments close only those Action rows; no broad coverage claim is made.

### Native Pick up and simultaneous custody contention

**Problems first.** `PickUpAction` had the same unnecessary Arena-activation gate despite already relying on the ordinary native snapshot evaluator and a self-contained bounded hex convention (`map_width_cells`, `map_height_cells`, and explicit native positions). That blocked native construction and persistence; the evaluator's adopted same-hex, positive-weight, capacity, common-snapshot contention, and single-custody rules were already defined.

The guard now admits a native transactional Encounter without Arena activation. It still uses the Action's declared bounded map dimensions and native coordinates, and the existing eligibility evaluator remains authoritative. A headless scenario declares two different Beings at the same represented hex, one ground Dagger, and two simultaneous Pick up Actions. Both Actions resolve `contested`; the Object retains its original identity, position and no-owner state. An initial Save before the first boundary restores both accepted Choices and the exact Actions into a fresh process; the native resolver reaches the same no-custody result, RNG state and history digest.

Verification after adding Pick up: `.venv/bin/python -B tests/test_native_draw_persistence.py -v` — **3 passed in 24.780s**, including simultaneous Pick up contention/restore. `PYTHONPATH=src:examples:tests .venv/bin/python -B -m unittest test_arena_ground_pickup -v` — **9 passed in 5.533s**. After the complete Draw/Shield/Pick up changes, the full native persistence suite passed **25 tests in 66.390s**, native history passed **17 in 15.889s**, native scenario builder passed **1 in 0.962s**, and the capability matrix passed **3**. The focused Arena Shield Don/Remove, Tower-shield refusal and native equipment suite passed **4 tests in 47.504s**. Existing Arena Draw regression cases passed, including the fresh-process pending Draw case with the required source `PYTHONPATH`. This only broadens native scheduling for Pick up; its coarse hex-cell access is not a general body-contact or reach model. Other Action families and complete historical parity remain open.

### Native Ready preparation and consumption by Strike

**Problems first.** The capability matrix previously had no headless fresh-process path that joined the timed Ready Action, its committed preparation fact, later Strike consumption, and restoration of that pending Strike. This left the readiness lifecycle only graph- and Arena-tested.

The new native scenario uses a held Longsword with its ordinary weapon definition and a legal two-second swing Ready. It saves the accepted Ready Choice at t=0, then a fresh process commits it and matches the uninterrupted preparation record, RNG and history digest. The control then schedules a native swing Strike and saves that pending Choice. A second fresh process restores it, resolves through the ordinary evaluator, consumes the exact preparation, and matches same-Encounter IDs, outcome, Being HP, weapon ownership, RNG and canonical history. This exercises the effect and actual consuming Action without adding timing or combat semantics.

Verification: `.venv/bin/python -B tests/test_native_draw_persistence.py -v` — **4 passed in 33.327s**, including Draw, simultaneous Pick up contention, Ready-to-Strike consumption, and Shield Don/Remove. Capability-matrix validation passed **3 tests** after updating the Draw, ReadyPreparation/Consumption, Shield and Pick up evidence rows. The adjacent Arena regressions for Ready, Shield Don/Remove, pending Draw and the full ground Pick up suite passed together: **12 tests in 38.268s**. Other supported Action variants and historical reader parity remain incomplete.

### Native Object strike with ordinary geometry and damage

**Problems first.** The capability matrix had no native fresh-process continuation for Object-strike damage, even though Action evaluation supports hardness, durability, and a `DamageEffect(component='object')`. A first exploratory fixture incorrectly added the attacker's held weapon as an Encounter participant; the actual physical-path validator then correctly classified that extra unmodeled volume as `uncertain_path`. The test was corrected to retain the instrument in the native inventory/Being relationship, not as an independent active path obstacle. No path rule or uncertainty gate was bypassed.

The Arena-independent scenario uses a Longsword and an explicitly represented hardwood Object with the existing ObjectDefinition dimensions, hardness and HP. The native `Encounter.physical_path()` reports no intersections and no unmodeled Entities. Seed 5 under the ordinary persisted RNG produces a normal native Object hit, a single Object-component damage effect, and the existing hardness reduction from 6 HP to 2 HP. The test saves while the exact Action is accepted and pending, then a fresh OS process strictly restores and resolves through the same common-snapshot evaluator. It compares Action/Object identities, outcome, damage amount, resulting HP and location/custody, RNG and canonical history digest with uninterrupted execution.

Verification: `.venv/bin/python -B tests/test_native_draw_persistence.py -v` — **5 passed in 36.483s**. Two adjacent existing object-strike tests (normal native hardness and the legacy `/12` destroyed-object round trip) passed in **2.566s**. The capability matrix now cites the limited generic `Action` event-type coverage and Object `DamageEffect` evidence. Other `Action` event types remain separately open; this is not full generic Action coverage.

The same fixture now also covers two simultaneous Object strikes against one low-HP, hardness-1 target. Both ordinary seeded rolls hit in one common-snapshot boundary; their separately recorded Object damage effects are 5 and 6 after applying hardness independently, and the atomic state becomes -8 HP. A fresh process restores both accepted Choices and Actions from the pre-first-boundary Save and reproduces exact action identities, per-Action outcomes/effects, single target identity and location, final durability, RNG and history. Focused command `.venv/bin/python -B tests/test_native_draw_persistence.py NativeDrawPersistenceTests.test_headless_simultaneous_object_strikes_preserve_common_snapshot_durability -v` — **1 passed in 3.846s**. No roll values are injected and no durability order is selected.

After adding the simultaneous case, `.venv/bin/python -B tests/test_native_draw_persistence.py -v` passed **6 tests in 44.037s**; `PYTHONPATH=src:examples:tests .venv/bin/python -B -m unittest test_action_evaluation.TestActionEvaluation.test_simultaneous_object_strikes_apply_hardness_per_blow_and_sum_atomically` passed **1 test in 1.397s**; capability-matrix validation passed **3 tests in 0.008s**.

### Native Subdue burden and continuation

**Problems first.** The existing native persistence cases exercised Stun's timed condition/interruption but not Subdual's separate cumulative burden, half body damage, recovery anchor, and subsequent continuation. Those facts are distinct in the adopted model and cannot be treated as a Stun flag or ordinary HP damage.

The headless test uses the native `declare_subdue()` path, a held Club, explicit awareness and a stated Encounter difficulty class. With deterministic RNG seed 5 and no mocked rolls, the ordinary engine produces a critical, 4 points of body HP loss, and a separate 9-point `SubdualEffect`. The Being retains `subdual_damage=9`, a t=5 recovery anchor, and `subdual_unconscious=false`. A strict initial Save restores the accepted Action in a fresh process and reproduces those facts, RNG, and history. The control then schedules a one-second Delay; a second Save with a committed Subdue receipt and pending Delay restores in another process and exactly matches the unchanged Subdual burden, HP, state, RNG and history after continuation.

Verification: `.venv/bin/python -B tests/test_native_draw_persistence.py NativeDrawPersistenceTests.test_headless_subdual_burden_and_continuation_restore_exactly -v` — **1 passed in 6.216s**. This covers the supported Subdue damage/burden and pending continuation shape, not one-hour recovery advancement, unconscious interruption, every armor/critical outcome, or all Subdual consumer queries. Those variants remain open for matrix closure.

The full increment after adding Subdue passed: `.venv/bin/python -B tests/test_native_draw_persistence.py -v` — **7 tests in 44.544s**; the adopted native Subdue damage/burden test — **1 in 1.261s**; capability-matrix validation — **3 in 0.005s**.

### Native zero-diff Feint and linked follow-up

**Problems first.** A Feint that succeeds without changing an Entity property is still a meaningful committed Event: the successful declaration grants one adopted follow-up bonus to its same-target Strike. Save/Load therefore must preserve the Feint Event facts and the follow-up's exact `feint_source_action_id`, without treating the zero-diff boundary as absent or re-evaluating the old Feint.

The Arena-independent case uses native Dagger skill and seed 3. A successful Feint records an empty effects tuple and leaves target HP unchanged. The control then schedules a same-target native Strike with the Feint's literal Action ID as its source and saves with that Strike accepted/pending. Fresh-process Load validates the source Feint and follows its pending Strike through normal evaluation. The Action IDs, source reference, hit outcome/effects, target HP, RNG, and authenticated history digest match uninterrupted execution. This confirms meaningful zero-diff Event retention for this supported profile, not all other Action event types.

Verification: `.venv/bin/python -B tests/test_native_draw_persistence.py NativeDrawPersistenceTests.test_headless_feint_and_one_followup_continue_with_original_action_identity -v` — **1 passed in 3.831s**. The Action matrix row now cites both one zero-diff Feint profile and native Object-strike profiles while retaining its explicit partial-coverage qualification.

Latest family-increment integration: the existing adopted Feint success/one-use follow-up regression passed **1 test in 1.525s**; the complete Arena-independent native family file passed **8 tests in 47.195s**; capability-matrix validation passed **3 tests in 0.006s**.

## Generated Arena first-Choice restoration and `/12` native migration

### Problems first

- Before this increment, a generated Arena saved after its first accepted Run Choice could be read through the `/12` path but could not be exported as the native format. Full native inventory rejected `ArenaActionActivation`, and strict native restore lacked an owner-bound reconstruction recipe for observer-owned Arena perception ledgers.
- `/10` and `/11` pristine fixtures remain strict legacy-reader/coexistence cases only. The native writer requires ordinary transactional progression, which an uninitiated pristine legacy Encounter does not yet establish. No adopted rule defines a migration-time first Action; do not synthesize one.
- The full native history/query model, durable history-journal recovery, all-family parity, and production ordinary Save/Load cutover remain incomplete. U-PER-SCALE-001 stays ACTIVE; no rule or external blocker is identified.

### Delivered in this increment

`ArenaActionActivation` is now admitted only in full native capture after validation against the exact generated Arena Encounter, actor, first accepted Choice, start cursor, single Action identity and shared event-history object. The narrower bounded Run/Spot checkpoint still refuses this activation. Observer ledgers are serialized as owner-bound native recipes and restored only after checking the exact participant/awareness owner, registered Being identity, current Entity/visible sets, time and boundary; the restored ledger must re-encode identically before being attached to its owner.

A fresh-process native test generates seed 20261116, declares the actual first Run Choice, saves before resolution, then compares uninterrupted native `Encounter.step(1)` against a fresh OS process loading the native Save. It checks literal World, Encounter, actor, Action, Choice and activation identities, outcome, position, RNG and canonical history digest; the child imports no Arena app, server or npcgen module. A separate `/12` migration test loads a generated and advanced Arena file with the legacy reader, exports the same logical Encounter in native format, strict-loads it, and requires byte-identical canonical Save→Load→Save plus identical activation, awareness, observer-ledger history, RNG and World/Encounter IDs.

The adjacent checkpoint perception test's old expected refusal was reproduced on committed baseline `307f378`: the exact bounded Run/Spot subset already emitted `bounded_run_spot_closure_verified`, while `semantic_closure_adapter_incomplete` independently kept the whole candidate unready. The test now asserts that exact state (including `closure_validated`, `portable_schema_defined`, and `restore_verified` remaining false); this changes no checkpoint admission behavior.

### Verification

- `PYTHONPATH=tests .venv/bin/python -B -m unittest discover -s tests -p 'test_native_persistence.py' -v` — **27 passed in 77.763s**.
- `PYTHONPATH=tests .venv/bin/python -B -m unittest discover -s tests -p 'test_arena_persistence.py'` — **22 passed in 407.729s** (includes the 64-Action/quiet-history cases; Python zipfile emitted the existing duplicate `snapshot.json` warning in its tamper fixture).
- `PYTHONPATH=tests .venv/bin/python -B -m unittest discover -s tests -p 'test_native_history.py'` — **17 passed in 18.049s**.
- `PYTHONPATH=tests .venv/bin/python -B -m unittest discover -s tests -p 'test_checkpoint_adapters.py'` — **48 passed in 21.182s**.
- `PYTHONPATH=tests .venv/bin/python -B -m unittest discover -s tests -p 'test_checkpoint_arena_perception.py' -v` — **7 passed in 2.378s**.
- `PYTHONPATH=tests .venv/bin/python -B -m unittest discover -s tests -p 'test_persistence_capability_matrix.py'` — **3 passed**.
- `.venv/bin/python -B tests/test_native_draw_persistence.py -v` — previously verified in this active continuation: **11 passed in 64.418s**.
- `git diff --check` passed before this report edit. Staged publication-safety and scoped commit evidence will be recorded after reviewing the staged paths.

The generated `/12`→native conversion is now demonstrated for a first-Run Choice state, not every `/12` Action/state family. `/10`–`/11` still have tested strict reader coexistence but not native resave. The report, matrix and TASKS entry continue to identify duplicate runtime receipt/Target history, incomplete graph-free historical query parity, journal recovery, broad family coverage, and production app cutover as open engineering work.

## Native restoration of pristine state and first-Choice continuation

### Problems first

- Strict native restoration previously left pristine snapshots in the process-local legacy progression mode. A history-free native Save therefore could not attach its deferred recorder, including after an explicit `/10`/`/11` migration.
- Rebinding pristine native state alone made native Arena activation fail: direct `ChoiceBook.publish()` is intentionally forbidden on transactional Encounters, while the existing authorized first-Choice path had only selected transactional mode after publication.
- U-PER-SCALE-001 remains ACTIVE. This closes one initial-state lifecycle gap; it does not finish the selected-family historical model, duplicate receipt/Target graph removal, durable journal recovery, or application cutover.

### Resolution and evidence

Full native graph restore now binds pristine graphs to the restored authenticated private RNG cursor under the existing restoration authority. The `/10`–`/12` legacy reader retains its former pristine nontransactional behavior. For a native restored Arena, the first Choice path validates the exact current RNG binding and wraps ChoiceBook publication in a private, thread-local scope requiring the active publication lock, exact Encounter activation record and accepted first Choice. Only the required internal publication calls are exempted from the general transactional direct-call guard. An unsuccessful activation preserves the prior binding; the migration test passes a foreign RNG cursor first and verifies no initiation, Action registration, or pending-queue mutation.

Accepted pristine `/10` and `/11` fixtures explicitly switch to the existing transactional mode before native export, without advancing time or generating an Action. Native Save→strict Load is canonical; in a fresh OS process each file then accepts a same-identity first Delay and commits through `Encounter.step(1)`. Control and fresh-child comparisons cover World/Encounter/Being/Action IDs, first-Choice activation, result, position/HP, awareness, RNG and canonical native-history digest. Children import no Arena app, server or npcgen module.

Post-change verification: native persistence **28 passed / 78.024s**; native history **17 / 17.350s**; checkpoint adapters **48 / 20.559s**; checkpoint Arena perception **7 / 2.501s**; Arena target-free activation **3 / 0.655s**; destination/movement blocker **2 / 0.390s**; pristine `/10`–`/11` migration continuation **1 / 3.227s**. These are focused gates; they do not establish all supported Action families or ordinary production Save/Load integration. The immediately preceding generated-Arena persistence suite passed **22 / 407.729s** before this native-only pristine binding change.

## Automatic Hold history identity and Grapple continuation

### Problems first

- A same-Encounter Save taken after an established physical Grip but before a due maintenance boundary generated an automatic Hold with a fresh random Action ID after Load. The uninterrupted path used a different UUID. Current posture, Grip and RNG could match, while the final committed native history row differed in the Hold's Action/Event/Effect references. This is a real Save/Load history fidelity defect; it is not a rule ambiguity.
- The broad historical/query matrix, graph-free history reconstruction, durable history journal, all implemented family parity and application Save/Load cutover remain open. U-PER-SCALE-001 remains the sole ACTIVE program.

### Correction and evidence

`transactional_progression._schedule_automatic_hold_check()` now assigns each no-cost maintenance Action a deterministic UUIDv5 from the exact Encounter ID, Grip ID and due boundary. These are the complete authoritative inputs that distinguish one automatic maintenance check. The Action still enters the same native scheduler, evaluator and atomic publisher; no gameplay timing, roll, Action cost or Hold rule changes. Its identity now remains stable when the same logical Encounter is restored and resumed.

The Arena-independent native test commits Touch, Being Grab and initial Grapple, exports a strict native Save with a pending Takedown Choice, and lets the due automatic Hold and Takedown resolve at the same boundary. The parent runs uninterrupted; a fresh OS process strict-loads and continues through `Encounter.step(6)`. Both paths match World/Encounter/Being/Action/source IDs, accepted Choice, committed outcome, posture, physical Grip, Grapple control, RNG, every native-history boundary digest, the final boundary row and canonical history digest. The failing version was first instrumented to compare recursive leaf paths: all differences were references to the maintenance Hold's random UUID in the final boundary. After deterministic identity, the exact history comparison passes.

Verification after the correction: `.venv/bin/python -B tests/test_native_draw_persistence.py -v` — **12 passed in 65.669s**; `PYTHONPATH=tests .venv/bin/python -B -m unittest discover -s tests -p 'test_native_persistence.py' -v` — **28 passed in 77.418s**; `PYTHONPATH=tests .venv/bin/python -B -m unittest discover -s tests -p 'test_checkpoint_adapters.py' -v` — **48 passed in 20.698s**; `PYTHONPATH=tests .venv/bin/python -B -m unittest discover -s tests -p 'test_native_history.py' -v` — **17 passed in 16.442s**; `PYTHONPATH=tests .venv/bin/python -B -m unittest discover -s tests -p 'test_persistence_capability_matrix.py' -v` — **3 passed in 0.006s**; existing automatic-Hold and Multiple Grapple/Break-hold tests — **2 passed in 2.816s**; native physical work — **17 passed in 0.120s**. At that point the broader Action-evaluation test `test_native_touch_grab_hold_break_grapple_and_escape_use_separate_receipt_state` still failed at its later Touch (expected `touched`, actual `out_of_reach`); a temporary `git archive` of committed baseline `79f6ead` reproduced the same fixture failure (**1 failed in 20.464s**). The fixture is corrected with represented hex centers in a later section below. The temporary baseline was created under `/tmp`, and no source or user data was changed. The preceding test invocation from repository root for `test_native_physical_work.py` used a path-dependent config and failed to import the fixture; the corrected invocation from `tests/` passed all 17 tests.

### Scope status

The native matrix's `action.Action` and `GrappleStateEffect` rows now cite the fresh-process initial Grapple→Takedown case. This is a tested supported profile only: it does not close all Grapple escape/recovery combinations, every native historical reader, general Action-family parity, graph duplication, durable journaling, accepted legacy migration for every family, or the normal production API cutover. Neither the capability matrix nor U-PER-SCALE-001 is marked complete. No push was made.

**Execution interval:** Start `2026-11-17T06:10:55Z`; End **IN PROGRESS**; elapsed **to be calculated at closeout**.

## Failed and successful Grapple Escape restoration

### Problems first

- Native Action evaluation already described a failed Grapple Escape as a `control/maintain` effect and the specialized settlement branch already required that existing control identity, participants, and `boundary + 6` check. The preceding generic Grapple Effect gate nevertheless allowed failed outcomes only for automatic Hold and failed initial Grapple. Consequently a legal failed Escape was rejected atomically as `Grapple state effect requires a native Being contact Action`. This was missing settlement admission, not missing adopted semantics.
- At the time of this settlement correction, the older Touch/Grab/Grapple chain still failed at its later test-line-735 Touch as `out_of_reach`; it is now repaired as a fixture geometry issue in the following section.

### Narrow correction

`src/action_settlement.py` now admits a failed Escape only when it is the exact Grappling-family `grapple escape`, the proposal outcome is `failed`, and its effect has `kind=control`, `operation=maintain`, the Action's declared control ID, the reversed controller/escapee attribution required by the control record, `boundary + 6`, and no position transition. The later Escape-specific settlement checks remain in force. This allows the already implemented effect semantics to commit; it adds no new outcome, bonus, timing, or transition.

Two seeded Arena-independent native cases now save after the Escape Choice is accepted and continue in separate OS processes. With ordinary definition-backed checks, the low-skill escapee fails against the established top control: the same Grapple ID and position remain, the next check advances six seconds, and concurrent automatic Grip maintenance/history also matches. With represented Escape Artist skill 20, a standing-position Escape succeeds and releases exactly that control while retaining the independently verified Grip state. Both compare literal Entity/Action IDs, result, Grip/control projection, posture, RNG, all boundary history digests, and canonical history bytes against uninterrupted execution.

Verification after the settlement correction: `.venv/bin/python -B tests/test_native_draw_persistence.py -v` — **14 passed in 79.337s**; focused successful and failed Grapple Escape tests — **2 passed in 17.231s**; existing automatic Hold and Multiple Grapple/Break-hold tests — **2 passed in 2.816s**; capability-matrix validation passed **3 tests** after the GrappleStateEffect row was updated. The Action-evaluation chain regression reproduced on baseline and is subsequently repaired in the geometry section below; it was not masked by the narrow settlement fix. U-PER-SCALE-001 remains ACTIVE: reverse-from-pin escape, pin-bottom escape, all recovery histories, full supported Action/query parity, graph-free history, durable journal, complete migration families, and production API cutover remain open.

## Correct the baseline Grapple fixture using represented geometry

**Problems first.** The pre-existing Action-evaluation sequence had failed at its third-party Touch even on committed baseline `79f6ead`. The test had used `_place_disarm_hexes()` to place the original participants on a declared map, then placed subsequent attackers at floating coordinates `(0.4,0,0)`, `(0.5,0,0)` and `(0.6,0,0)`. At that point those coordinates were not within represented reach of target B. Relaxing the native reach/path checks would have hidden the fixture defect.

The test now retains its explicit `ArenaHexLayout`, asserts B's cell is `(6,5)`, and places each additional Being on a distinct neighbor cell center: `(5,5)` for the original attacker; `(7,5)`, `(7,4)`, `(6,4)`, and `(5,4)` for the subsequent attackers. This preserves represented clearance, all original seeded/mocked roll inputs, the four-attacker capacity rule, and the fifth-attempt refusal. No movement, contact, or Grapple rule changed.

The previously failing full Touch→Grab→Hold→Break hold→Grapple→Escape→multi-attacker sequence now passes. `PYTHONPATH=tests .venv/bin/python -B -m unittest tests.test_action_evaluation.TestActionEvaluation.test_native_touch_grab_hold_break_grapple_and_escape_use_separate_receipt_state tests.test_action_evaluation.TestActionEvaluation.test_automatic_hold_maintenance_tie_releases_only_that_grip tests.test_action_evaluation.TestActionEvaluation.test_declared_multiple_grapple_and_break_hold_do_not_interrupt_control -v` — **3 passed in 27.023s**. The full affected Action-evaluation suite also passes: `PYTHONPATH=tests .venv/bin/python -B -m unittest discover -s tests -p 'test_action_evaluation.py' -v` — **141 passed in 97.291s**. This resolves the verified baseline fixture failure. The native matrix and production persistence gates remain open.

## Charge and forced-movement continuation after fresh-process restore

**Problems first.** The Action matrix had coverage for Charge and Bull Rush/Overrun outcomes separately, but no Arena-independent fresh-process proof that their adopted source links and committed consequences survive a native Save between the continued Actions. This is a persistence coverage gap; the displacement rules themselves remain bounded where the world has no represented legal destination.

Two seeded native scenarios now use the ordinary `NativeScenarioBuilder`, accepted Action choices, native `Encounter.step()`, strict portable Save/Load and fresh OS child processes. Seed 5 commits an actual Charge movement and critical strike, saves before its source-linked Bull Rush resolves, then both uninterrupted and restored paths commit `success_pending_displacement`. Exact World/Encounter/Being/Weapon/Action identities, positions, HP, RNG and every native-history row match; the target remains at its original represented position because no displacement destination was authored. Seed 3 saves after a successful Bull Rush with an accepted Overrun Choice pending. After restore the same Rush source identity is retained; the continuation receives its adopted prepared duration and commits the target's prone result while leaving both represented positions unchanged. This records the supported rule consequence without adding force-to-distance or speculative geometry.

Verification: the targeted Charge→Bull Rush fresh-process case passed (**1 test / 2.043s**); the targeted Bull Rush→Overrun case passed (**1 / 4.236s**); then `.venv/bin/python -B tests/test_native_draw_persistence.py -v` passed **16 tests in 85.106s**, covering the two new continuation cases together with the prior 14 native equipment, Object, weapon-control, deception, Subdue and Grapple profiles. `git diff --cached --check` passed; the staged publication-safety audit passed with 0 findings, including the preserved unrelated staged paths; scoped local commit `20cf775` contains only the five reviewed files. The expanded `action.Action` matrix row links both tests and remains partial: other implemented Action branches and all-family native historical/query parity are not covered by these two cases.

### Represented Charge→Overrun landing after fresh-process restore

**Problems first.** Charge→Overrun previously had rule/evaluation evidence for an actual one-hex landing, but the native persistence suite did not cover that geometry-bearing continuation across Save/Load. A no-map test could only preserve the pending or unchanged-position result and would not establish the adopted displacement where the layout actually supplies an open destination.

The new seed-3 scenario uses an explicit `ArenaHexLayout`, represented cell centers, authored facing and an ordinary Charge velocity. It commits the normal Charge at t=2, accepts an Overrun Choice referencing that exact Charge, exports the strict native Save, then continues both uninterrupted and in a fresh OS process through t=8. Native resolution chooses the adopted forward neighboring hex using the represented layout; the test independently computes the same forward neighbor from the pre-Overrun target cell and verifies the truncated destination, prone posture, IDs, HP, RNG and every history row. No Arena application/session or invented geometry is involved.

The focused Charge→Overrun fresh-process case passed **1 test / 5.241s**. The full 18-test `.venv/bin/python -B tests/test_native_draw_persistence.py -v` suite then passed in **103.945s**, including the Charge failure case added in the following section. The capability matrix now links Charge→Overrun alongside the bounded Charge→Bull Rush and Bull Rush→Overrun continuations. These tests improve selected movement/Action coverage only; U-PER-SCALE-001 remains ACTIVE, with all-family historical queries, duplicate receipt graph removal, durable journal/recovery, broad legacy migration and ordinary production API cutover still open.

## Failed Charge persistence branch

**Problems first.** The persisted Charge profile had a normal hit and a normal Charge continuation, but did not prove the adopted insufficient-relative-speed refusal through a pending native Choice and fresh-process Load. Without this branch, the matrix demonstrated continuation but not the ordinary no-damage failure state.

The new Arena-independent seed-19 case saves the accepted Charge at t=0, then supplies represented native movement below the adopted relative-speed threshold through the ordinary `Encounter.step(2, velocities=...)` API. It commits `insufficient_charge_speed` and leaves target HP unchanged. An OS child strict-loads the pending Choice, supplies the same velocity to the same native step, and compares literal World/Encounter/Being/Weapon/Action IDs, outcome, both positions, both HP values, RNG and canonical complete history digest against uninterrupted execution. This does not alter the Charge threshold or synthesize a miss roll.

The focused failed-Charge continuation passed **1 test / 1.809s**. The complete native Action-persistence suite passed **18 tests in 103.945s** with this failure branch included. U-PER-SCALE-001 remains ACTIVE, with selected continuation evidence only and the broad native-history/application gates still open.

## Native fatal-effect continuation

**Problems first.** The capability-matrix `FatalEffect` row said that no native restore evidence existed. The Action is legally reachable through Coup de grâce and has an implemented fatal settlement effect, so its history must survive the native Save path. This was a concrete matrix/test gap, not a missing rule.

A seed-1 Arena-independent fixture authors a helpless target using the configured Stun state, a represented carried Dagger and a pending native Coup de grâce. The strict Save is taken after the Choice is accepted and before resolution. Parent and fresh OS child both commit `fatal`; inspection reports exactly one `FatalEffect`, the same target in `fatal_targets`, and HP at or below the adopted fatal floor. They match literal World/Encounter/Being/Weapon/Action identities, effect identity `(Encounter, boundary, Action, channel, slot)`, ordered effect types, HP, RNG and complete canonical native-history digest. This demonstrates native Save/Load for `FatalEffect` while leaving legacy `/12` Arena admission as a distinct boundary.

The focused fatal-effect continuation passed **1 test / 5.238s**. The matrix and `TASKS.md` now link this evidence. The integrated `.venv/bin/python -B tests/test_native_draw_persistence.py -v` rerun passes **19 tests in 108.716s**, including this fatal-effect case. Scoped commits: `101ad3d` (Charge success/failure and Overrun continuations) and `6c73000` (FatalEffect restore). U-PER-SCALE-001 remains ACTIVE; this selected family does not resolve general historical inspection parity, duplicate runtime graph persistence, durable journal recovery, or normal application cutover.

## Resisted Bull Rush failure after native restoration

**Problems first.** The persistence coverage included successful pending displacement, Charge continuation and the adopted Overrun result, but a resisted one-second Bull Rush failure had only evaluation evidence. The requirement is to preserve the committed contest result and no-movement consequence, not to manufacture displacement.

A seed-1 `NativeScenarioBuilder` encounter with represented facing, equal medium size and equal Strength commits the ordinary failed Bull Rush contest. The test saves its accepted pending Choice, then compares uninterrupted execution with a fresh OS process strict-loading the same native Save and resolving via `Encounter.step(1)`. Both paths retain the same Action and Being IDs, `failed` receipt, unchanged positions and HP, RNG state and canonical native-history digest. No forced roll or special permission is used.

The focused test `test_headless_failed_bull_rush_restores_the_resisted_contest_without_movement` passed **1 test / 1.586s**. The full `.venv/bin/python -B tests/test_native_draw_persistence.py -v` suite passed **21 tests in 108.304s** with both negative forced-movement branches included. Capability-matrix validation passed **3 tests**; `git diff --check` passed. U-PER-SCALE-001 remains ACTIVE.

## Failed Overrun after native restoration

**Problems first.** A successful Overrun continuation had fresh-process evidence, but its ordinary failed contest branch did not. The target's standing posture and absence of displacement are part of the committed result and need the same restoration proof.

A seed-1 Arena-independent native fixture saves an accepted four-second Overrun Choice before resolution. The ordinary unpatched contest fails. Parent and fresh OS process agree on the `failed` Action receipt, standing target, unchanged represented positions and HP, exact RNG and canonical native-history digest. The case uses the same represented facing, size category and abilities as the already tested contest and changes no contest rules.

Focused test `test_headless_failed_overrun_restores_standing_without_displacement` passed **1 / 2.663s**. The full `.venv/bin/python -B tests/test_native_draw_persistence.py -v` suite passed **21 tests in 108.304s** with both failed forced-movement branches included. Capability-matrix validation passed **3 tests**. U-PER-SCALE-001 remains ACTIVE.

## Query the retained initial native boundary

**Superseded:** the initial boundary query note below was written before the `/6` origin-cursor extension. Use the later `/6` section for current behavior.

## Native history schema `/6`: exact initial RNG cursor

**Problems first.** The initial projection could be read at boundary 0, but `/5` lacked the pre-first-commit RNG cursor. That state cannot be derived from later cursors or committed dice results. Leaving the query unavailable contradicted the assignment's requirement to preserve every authoritative RNG stream at arbitrary boundaries.

Entering transactional progression now records the exact state from the already validated RNG owner in optional Encounter field `_native_rng_origin_state`. Schema `/6` stores its canonical tuple encoding in the initial history record, validates it with a private `random.Random.setstate()` call, and returns detached data through both `rng_state_at(0)` and `NativeHistoryQuery.rng_state_at(0)`. First-boundary SAME-RNG markers are anchored to this origin. The field is optional in the graph adapter so `/10`–`/12` and older native graph fixtures remain admissible. History `/1`–`/5` remain strict readers; upgrades mark an origin absent from those old history records as `null`, never infer it from later state. Where the same saved native graph independently carries the new exact origin field, strict Load validates the legacy history against the graph and binds the recorder to the graph's current `/6` facts.

The new Save/Load regression checks the origin in a fresh OS process, while explicit `/1`, `/4`, and `/5` migration tests compare historical facts and verify that unavailable legacy origins remain unavailable after standalone history upgrade. The added optional Encounter field initially made the bounded Run/Spot closure's audited A/D/T/U field table stale; two affected checkpoint tests reproduced this mismatch, and the closure policy now classifies the origin as authoritative. The two targeted regressions and the complete checkpoint-adapter suite are green.

Verified results for this increment: `tests/test_native_history.py -v` — **18 passed / 18.962s**; `tests/test_native_persistence.py -v` — **30 passed / 88.393s**; `tests/test_checkpoint_adapters.py -v` — **48 passed / 23.303s** after repairing the A/D/T/U policy; `tests/test_persistence_capability_matrix.py -v` — **3 passed / 0.018s**; `/1`, `/4`, `/5`, and exact-origin persistence focused tests — **3 passed / 8.226s** (before the added child-process assertion); history `/5` upgrade plus native Save graph rebinding — **2 passed / 3.557s**. The fresh-process origin assertion passed separately (**1 / 1.530s**) after the full-suite run. The Arena-independent Action-family suite passed **21 / 111.909s** in this execution. The overall assignment remains ACTIVE: native history still duplicates committed receipt/Target graph, all-family historical reader parity remains incomplete, durable journal/crash recovery is unverified, and ordinary application Save/Load has not been cut over.

## Cumulative committed Action/Effect history query

**Problems first.** `events_at(boundary)` exposed the facts committed on one boundary, but native history had no reusable query that reconstructed the cumulative committed Action and Effect view consumed by `Encounter.inspect_committed`. This left an implemented historical reader dependent on the persisted receipt graph even where the same facts were already in the fact log.

`NativeHistoryQuery.committed_actions_at(boundary)` now folds only prior committed Action/Event/Effect rows through a validated boundary. It preserves the ordered unique Action and Effect identity lists and the exact ActionInspection/IdentifiedEffect records, including multiple distinct Effects. It does not run any Action, inspect current Encounter state or expose pending declarations. The bounded fixture compares both its Action and Effect mappings and causal identity order against `Encounter.inspect_committed(boundary)` at every boundary, including zero and a quiet interval; returned projections are detached.

`.venv/bin/python -B tests/test_native_history.py -v` passes **19 tests / 17.818s** after this addition. `tests/test_persistence_capability_matrix.py -v` passes **3 / 0.019s**. This is a verified cumulative committed Action/Effect read model for the tested fixture, not full historical-reader parity. Other state-family readers, duplicated receipt retention, durable journal/crash recovery and production Save/Load cutover remain open; U-PER-SCALE-001 stays ACTIVE.

## Observer-owned recipient history projection

**Problems first.** The history log retains observer-specific recipient projections, but there was no direct historical read that selected one observer's facts without returning the other observer's rows. The existing two-observer test proved distinct storage, not the consumer projection.

`NativeHistoryQuery.observer_facts_at(boundary, observer_id)` and its one-shot wrapper now return only rows whose persisted stable owner ID equals the requested ID, as detached values. The regression commits two distinct Group-observation Actions in the same native interval and proves each query sees only its own owner's projection; an unknown owner returns an empty result. The API is a projection helper and does not authenticate whether a caller is entitled to request a given observer ID; caller authorization remains a consumer responsibility.

The focused observer regression passed (**1 / 1.463s**). With both new query APIs, `tests/test_native_history.py -v` passes **19 / 18.299s** and `tests/test_persistence_capability_matrix.py -v` passes **3 / 0.020s**. The changes are not yet committed. Broader observer family parity, history graph deduplication, crash recovery and normal application cutover remain open.

## Historical Action/Effect query: simultaneous and zero-diff receipts

**Problems first.** The cumulative Action/Effect query had been compared with only the four-boundary Run/Delay history fixture. That was insufficient evidence for same-boundary multiple Effects or for a committed Action Event that leaves entity properties unchanged.

Two Arena-independent native continuation fixtures now compare `NativeHistoryQuery.committed_actions_at()` to `Encounter.inspect_committed()` directly. The simultaneous Object Strike fixture checks both Action rows, the combined Effect map, and all six receipt Effect identities at its shared boundary. The Feint fixture verifies the committed Feint row and identities while the target HP remains unchanged and Feint has no Action-fact Effects; its existing fresh-process Strike follow-up and source-Action identity assertions still run. These tests use the existing evaluator, common-snapshot publisher and native receipt. No history or combat rules changed.

Verification: the two focused tests passed (**2 / 8.514s**); `.venv/bin/python -B tests/test_native_history.py -v` passed **19 / 19.496s**; `.venv/bin/python -B tests/test_persistence_capability_matrix.py -v` passed **3 / 0.020s**. This extends only the tested receipt shapes. Full Action-family historical-reader parity, duplicated runtime receipt/Target retention, durable incremental crash recovery, broad legacy migration, and production Save/Load cutover remain open; U-PER-SCALE-001 stays ACTIVE.

## Incremental cumulative Action/Effect query

**Problems first.** `committed_actions_at()` previously scanned every persisted segment for every request. A repeated historical query session should not perform a fresh full-prefix fold for each increasing boundary.

The query now retains one cumulative Action/Effect projection and consumes only newly reached commit rows for monotonically increasing requests. Quiet spans advance the cursor without adding facts. A backward request resets the fold and remains correct; no per-boundary cache or additional persisted state is created. The regression checks all boundaries in both forward and reverse order, including a quiet interval and boundary zero. The simultaneous Object Strike and zero-entity-diff Feint fresh-process fixtures also pass against the incremental fold.

Verification after the change: `.venv/bin/python -B tests/test_native_history.py -v` — **19 passed / 18.717s**; focused simultaneous Object Strike and Feint continuation tests — **2 passed / 9.248s**; `.venv/bin/python -B tests/test_persistence_capability_matrix.py -v` — **3 passed / 0.056s**. This establishes correctness, not a query latency claim. Full historical consumer parity and graph-free Save/Load cutover remain open, along with durable journal recovery and broad family coverage.

## Strengthened scale verification of cumulative Action/Effect history

**Problems first.** The existing scale runner checked every state, per-boundary Event receipt, TargetCandidate, schedule, objective projection, projectile state, EntityInspection context and RNG cursor, but it did not compare the cumulative Action/Effect reader against the native inspection across the long Action run. This left a gap between the focused receipt-shape tests and extended-history acceptance.

`examples/native_persistence_scale.py::_verify_history_boundaries()` now compares `committed_actions_at()` Action/Effect ID order and mappings with the authoritative `Encounter.inspect_committed()` for every boundary. It retains the existing exact per-boundary state/Event/context/RNG checks. The runner continues to use the existing native evaluator/publisher, then strict-loads from a fresh OS process, continues one Delay and compares the result to uninterrupted execution.

| Scenario | Actual resolved work | Checked boundaries | Graph bytes | Fact-history bytes | Save bytes | Simulation / verification / export / fresh-process continuation |
|---|---:|---:|---:|---:|---:|---:|
| 64 Dagger Feints, 2 registered Beings | 64 Actions | 129 | 4,858,269 | 1,180,091 | 7,657,930 | 67.853 / 2.491 / 5.794 / 6.728 s |
| Quiet span | 0 Actions | 200 | 4,854,570 | 34,162 | 6,507,069 | 44.246 / 1.004 / 2.765 / 3.275 s |

Both scale commands passed. Each fresh process reported the same saved logical Encounter and matched its uninterrupted continuation; the quiet case checked all 200 logical boundaries represented partly by compressed spans. The Action case establishes cumulative Action/Effect history parity for the Feint profile at scale, not every implemented Action family. The significant graph component remains duplicated historical receipt/Target state and resumable state; this result does not establish the required compact production format. Multiple Encounters, broader historical consumer parity, native legacy migration/resave, durable recovery and ordinary application cutover remain open.

Verification: `.venv/bin/python -B examples/native_persistence_scale.py` passed; `.venv/bin/python -B examples/native_persistence_scale.py --quiet-boundaries 200` passed; the strengthened verifier's native-history unit test passed (**1 / 4.394s**); full `.venv/bin/python -B tests/test_native_history.py -v` passed **19 / 18.554s**; `.venv/bin/python -B tests/test_persistence_capability_matrix.py -v` passed **3 / 0.005s**; compilation of the verifier/query and tests passed. The scale implementation and this report/TASKS/matrix update are prepared for an audited commit; U-PER-SCALE-001 remains ACTIVE.


## Current continuation — native committed receipt facts

### Problems first

- U-PER-SCALE-001 remains ACTIVE. Native history is still paired with the full `_atomic_interval_history` and `_atomic_target_history` runtime graph in the portable Save; consumers such as `Encounter.inspect_committed()` still depend on that graph. This increment improves fidelity of the independent history stream but does not remove duplicate history, reconstruct all historical readers from deltas, cover every field family, complete durable recovery, or cut over ordinary app Save/Load.
- Legacy history `/1`–`/6` is kept strict. History-only upgrade does not invent notification or Disarm landing facts. Native Save Load may recover those facts only from the independently authenticated receipt graph that those legacy Saves actually contain.
- No rules decision or external blocker prevents further persistence engineering.

### Receipt-fact extension

Native history schema `/7` now captures `PublishedInterval.notification_intents` and the `DisarmLandingReceipt` rows committed at each boundary. `NativeHistoryQuery.receipt_facts_at()`, `notification_intents_at()` and `disarm_landings_at()` return detached tagged facts; rows upgraded from older history carry `receipt_facts_available=false`, so absence is not misrepresented as an empty known receipt. Newly appended rows record their own availability, allowing mixed known/unknown history without relabeling old boundaries. The top-level `receipt_facts_complete` marker is validated against all regular rows and quiet spans. Quiet-span compaction only combines rows with matching availability.

The current strict validator checks closed record types, field allowlists, Action references, unique source chronology, Disarm boundary identity, integer landing cells, nonnegative range, canonical digests and tamper refusal. `native_persistence.load_save()` accepts `/6` by comparing the current graph-derived history with a normalized `/6` projection, then installs the authenticated graph-derived facts for continued native recording. No existing `/12` behavior changed.

### Verification

- `.venv/bin/python -B -m unittest discover -s tests -p 'test_native_history.py'` — **21 passed / 22.622s**, including exact current receipt parity, `/6` history upgrade with RNG-origin preservation, and appending new known facts after an older boundary while keeping its unavailable marker.
- `.venv/bin/python -B -m unittest discover -s tests -p 'test_native_persistence.py'` — **31 passed / 89.307s**, including strict native `/6` Save restoration and pending post-roll Disarm landing continuation with exact receipt parity.
- Focused recheck of `/6` native Save and pending Disarm — **2 passed / 4.914s**; after stricter dangling-reference checks, the Disarm case passed again (**1 / 2.675s**).
- The full field-family matrix and acceptance gate remain open; the matrix now identifies `/7` and links the new receipt evidence.

This execution preserved the four unrelated staged historical archive paths and all pre-existing untracked assignments/saves. Commits: `cad52c2` records schema `/7`, queries, tests, matrix and report; `9f13351` tightens receipt references and adds the dangling-Being refusal regression. Both passed explicit-path `git commit --only`; staged publication-safety audits reported 0 findings (14 and 8 staged files respectively), while preserving the five existing archive operations. HEAD after these increments is `9f13351`.


### Historical Target and Action queries

`NativeHistoryQuery.target_at()` and `target_history_at()` expose the committed `TargetCandidate` facts directly from the validated delta reconstruction; `committed_action_at()` returns the latest committed `ActionInspection` through a selected boundary. These complement `state_at()` and cumulative Action/Effect history without consulting the current Encounter graph or resolving old Actions. The four-boundary native fixture now compares every Target fact and ordered Target history with the authenticated `TargetIntervalRecord` values, and compares each Action projection with `Encounter.inspect_committed()`. Focused checks: `test_native_inspection_boundaries_round_trip_as_atomic_history` and `test_committed_action_effect_read_model_matches_inspection_at_each_boundary` — **2 passed / 1.475s**. Full state-at-time and Action/Target consumer parity across the implemented matrix remains open.

### Schema `/7` scale rerun

The actual 64-Action seed scenario was rerun through the strict fresh-process path after the `/7` format change. It committed 64 Actions/129 boundaries and compared authoritative target, Event, Action, Effect, observer context and RNG views at every boundary; the child preserved same-Encounter IDs and matched uninterrupted continuation. Save **7,665,648 bytes** (graph **4,854,434**, history **1,192,921**), history verification **2.847s**, export **5.493s**, fresh-process load/continue **7.801s**, scenario **75.039s**, reported peak RSS **172,294,144 platform units**.

The 200-quiet-boundary strict fresh-process rerun also matched uninterrupted continuation: Save **6,507,786 bytes** (graph **4,854,985**, history **34,323**), all 200 boundaries checked, history verification **1.026s**, export **2.892s**, fresh-process load/continue **3.282s**, scenario **53.235s**, peak RSS **158,449,664 platform units**.

At 20 registered Beings the 64-Action strict fresh-process run passed with Save **7,994,376 bytes** (graph **5,100,981**, history **1,192,921**), all 129 boundaries checked, scenario **69.942s**, history verification **2.823s**, export **4.972s**, and load/continue **7.007s**. At 200 registered Beings it also passed with Save **11,229,788 bytes** (graph **7,527,538**, history **1,192,921**), all 129 boundaries checked, scenario **68.266s**, history verification **2.503s**, export **5.875s**, and load/continue **7.330s**; peak RSS **226,377,728 platform units**. The suite includes an ordinary native post-load Delay compared against uninterrupted execution. These measurements remain a combined graph+history save and do not establish the requested graph-free architecture.

## Native history schema `/8` — passive Arena observer-knowledge reads

### Problems first

- Before this continuation, native history recorded observer-owned recipient projections, but passive `ArenaPerceptionLedger` evidence was only present in the resumable graph. A standalone history reader could not recover each participant's recorded view at a historical boundary.
- This change closes only that passive Arena evidence stream. It does not close general perception history, all recipient combinations, graph-free Save/Load, durable journaling, multi-Encounter ownership, or ordinary application Save/Load cutover. U-PER-SCALE-001 remains ACTIVE; no adopted rule or external blocker was found.

### Implemented capability

Native history `/8` stores the initial passive Arena observer-evidence map once and sparse per-boundary changes from the native `ArenaPerceptionLedger._history`. The capture reads committed evidence rows and their recorded `visibility_boundary`; it does not infer observer knowledge from objective Entity state or redo sightline evaluation. Each change is keyed by logical observer and Entity ID. Repeated updates for the same observer/Entity/boundary, nonparticipant owners, dangling subjects, invalid record types and out-of-range boundaries are rejected. `NativeHistoryQuery.observer_knowledge_at(boundary, observer_id)` returns a detached owner-only view; the all-owner form is a data projection, not an access-control boundary.

Schema `/1`–`/7` remains strictly readable. A history-only upgrade marks passive observer history unavailable (`None`) rather than inventing it. When a valid `/7` Save contains the previously authenticated graph ledger, strict native Load can compare the `/7` history against the graph, reconstruct `/8` from those actual retained ledger rows, and resave to the exact current canonical bytes. A pending recorder captures the first committed timeline, and an attached recorder appends subsequent committed observer changes only after native publication.

### Verification

| Command | Result |
|---|---|
| `.venv/bin/python -B -m unittest discover -s tests -p 'test_native_history.py'` | **21 passed / 22.111s**, including strict legacy upgrades, unavailable-history behavior, atomic append, rollback and query checks. |
| `.venv/bin/python -B -m unittest discover -s tests -p 'test_native_persistence.py'` | **32 passed / 91.966s**, including generated `/12` two-observer parity at boundaries 0–2, fresh-process strict restore, `/7` graph-backed upgrade and byte-identical canonical resave. |
| `.venv/bin/python -B -m unittest discover -s tests -p 'test_persistence_capability_matrix.py'` | **3 passed / 0.007s**, including `/8` and the public query API. |
| Focused attached-recorder test | **1 passed / 0.920s**; initial export, ordinary generated Arena Run, then a native Delay append match ledger evidence at each boundary. |
| Focused `/6` Save and `/7` migration regressions | **2 passed / 3.877s** after correcting the `/6` historical fixture to remove the new `/8` field. |

The first full native-persistence run exposed one stale `/6` fixture that retained the `/8` observer-history field. The fixture was corrected to construct the real old wire schema; the full 32-test suite then passed. Production `/12` was not edited. The existing 64-Action and 200-quiet scale results above were not rerun because this change only adds sparse Arena evidence history and the strict native persistence suite covers the affected migration and restore paths.

The source-linked matrix and bridge findings describe this as partial observer-history capability. Remaining acceptance gaps include all-family current-state/receipt reconstruction, multi-Encounter support, durable history journal/crash recovery, graph/history de-duplication, comprehensive corruption/scaling tests for the new architecture, and production Save/Load integration. No whole-repository suite was run.

## Native EntityInspection query API

### Problems first

Native history already stored sparse, digest-checked `EntityInspection` contexts, but callers could only retrieve the complete context map. There was no stable per-Entity query matching `entity_at`/history access patterns. Treating an absent row as historical absence would also be incorrect for schema `/1`–`/3`, which never recorded those contexts.

### Result

`NativeHistoryQuery.entity_at(entity_id, boundary)` and `entity_history_at(entity_id, boundary)` now return detached committed `EntityInspection` projections through the validated sparse context stream. Unknown Entity IDs return no row; legacy schemas without context return `None` for the family and are not filled from current state. The API explicitly limits its contract to recorded inspection fields; it does not claim every Being/Object runtime property is historically represented.

### Verification

The four-boundary fixture compares each per-Entity read with its exact native committed `EntityInspection` source, checks initial-boundary data, detached results, unknown identity handling and legacy-unavailable behavior. `.venv/bin/python -B -m unittest discover -s tests -p 'test_native_history.py'` — **23 passed / 20.527s**. The first run exposed a test-only off-by-one in mapping logical boundary to stored receipt index; correcting that expectation made the full focused history suite pass. No production `/12`, combat rule, or application Save/Load path changed. Matrix status remains partial, and overall U-PER-SCALE-001 remains ACTIVE.

## Native objective fact and fact-use query

### Problems first

The generic state delta retained committed `ObjectiveInspection` and fact-use records, but native readers had no direct APIs for those rows. That left the history/causality contract hidden inside a broad state mapping and lacked direct receipt parity for the resolution-on-demand family.

### Result and evidence

`NativeHistoryQuery.objective_at(boundary)` and `objective_use_at(boundary)` now return detached facts directly from validated history, without reading current Reality state or replaying a Group observation. A native `ObserveGroupAction` fixture checks both APIs at boundary 0 and the committed boundary against `CommittedBoundaryRecord.inspection.objective` and `.objective_use`; the non-empty committed rows are confirmed. `test_native_history.py`: **24 passed / 21.347s**, including this test plus per-Entity query and legacy-unavailable regressions. This is direct query coverage for one implemented Group-observation profile; all realization branches and graph-free reconstruction remain open.

## Scheduler, Action-status and Choice-status history queries

### Problems first

History deltas already retained the native `QueueProjection`, but callers had no stable API to read committed schedule or status values. That made pending future Choices, registered Action lifecycle, and finished status harder to compare with the authoritative transaction receipt.

### Result and verification

`NativeHistoryQuery.schedule_at`, `action_state_at`, and `choice_state_at` now return detached committed lifecycle projections. A native scenario schedules simultaneous Run/Delay Actions plus a later accepted Run; after boundary 1, the first two are finished and the future Choice remains accepted. These reads match the committed `QueueProjection` while the future Action remains unregistered. Commands: full `test_native_history.py` — **25 passed / 24.180s**; `test_persistence_capability_matrix.py` — **3 passed / 0.025s**. The exact pre-first-commit gap is resolved for schema `/9` native captures; historical schemas `/1`–`/8` and legacy Arena graphs explicitly report the unavailable fact. Generic full-world/multiple-Encounter and production application gates remain open.

## Native history `/9`: exact initial scheduler baseline

### Problems first

The initial scheduler query gap affected pending accepted Choices: a Save made before the first boundary could resume natively, but its first history commit needed to retain the exact time-zero pending/finished/cancelled queues, registrations, reservations, Action states, Choice states, and scheduler revision. A post-commit queue is not a substitute. The migration audit also found that pre-`/9` `initial_schedule` was sourced from the first committed receipt, so those versions cannot truthfully answer the pre-first-commit scheduler state. The first upgrade implementation also shallow-copied nested maps and could invalidate the authenticated input digest while adding fields.

### Correction

Schema `/9` adds `initial.initial_schedule_available` and validates the exact closed `QueueProjection` record when it is available. The first transactional progression captures that baseline within the publication boundary before the first commit; a pending native Save starts a resumed recorder from its authenticated pending queue. Upgrades deep-copy the authenticated history, preserve pre-`/9` scheduler data as an internal replay anchor for its existing delta rows, and mark boundary-zero scheduler availability false. Historical queries sanitize unavailable baseline fields, while later committed `schedule_at(n)` values continue to match native receipts. Imported `/10`–`/12` graphs that lack the pre-commit queue likewise return `None` at boundary zero; no later state is inferred.

### Verification

- `cd src && PYTHONPATH=../tests:../examples python -m unittest test_native_history` — **26 passed / 21.102s**. This covers exact initial accepted Choice state, unavailable legacy boundary zero, immutable upgrade input, quiet-span compatibility, and strict marker validation.
- `cd src && PYTHONPATH=../tests:../examples:../../npc-generator python -m unittest test_native_persistence` — **32 passed / 79.060s**, including same-Encounter continuation, strict native Save/Load, `/1`–`/8` history migration, accepted `/10`–`/12` graph migration and the generated `/12` upgrade path.
- `cd src && PYTHONPATH=../tests:../examples python -m unittest test_persistence_capability_matrix` — **3 passed / 0.026s**. `python3 -m py_compile` on the changed modules/tests and `git diff --check` passed.
- The full integrated persistence run first had one subprocess fingerprint mismatch while the source file was being edited; with the source held fixed, the exact full suite reran green. The earlier missing sibling `npcgen` import path was also corrected for test setup only; the sibling repository remained read-only.
- Commit hashes, final HEAD/tree state and exact execution interval will be recorded at the next closeout update.

This closes the initial scheduler-history gap only. The current Save still serializes runtime receipt/Target history beside fact history, and significant field-family query parity, durable journal recovery, and the ordinary application Save/Load cutover remain open. U-PER-SCALE-001 stays ACTIVE; no rule or external blocker has been found.

### Native historical projection follow-through

**Problems first.** The current history reader exposed projectile trajectory records only through the broad `state_at()` mapping, and the matrix did not demonstrate that an AskAboutPast-created PersonalHistory fact-use projection was absent before its committed Action. These are query/coverage gaps; they do not require a rule change or Arena dependency.

`NativeHistoryQuery.projectile_state_at(object_id, boundary)` and its module-level wrapper now return the exact detached trajectory fact recorded at that boundary, or `None` if the history did not record a projectile there. The shielded-flight regression checks every committed boundary from pre-flight through interception against the source `CommittedBoundaryRecord`, then retains the existing fresh-process continuation comparison. A second history fixture commits `AskAboutPastAction` with a literal `EpisodeFacts` source: the PersonalHistory subject candidate is absent at boundary 0, appears at boundary 1, and its objective-use rows match the native receipt. The query remains usable after the fixture scope is released; it does not call the live Reality ledger.

Verification: `.venv/bin/python -B -m unittest discover -s tests -p 'test_native_history.py'` — **27 passed / 20.604s**; the focused `test_projectile_shield_interception_continues_after_native_fresh_process_load` — **1 passed / 4.069s** (two consecutive runs). The first PersonalHistory assertion initially assumed the inspection candidate's revision field; source inspection showed the closed fact is a `SubjectRealityCandidate` with nested `ObjectiveFact` rows, so the regression now compares the full detached projection to the authoritative receipt rather than asserting a nonexistent field. The full PersonalHistory/reproduction and timed-projectile families remain partial/open; this does not establish graph-free historical view parity or production cutover.

The preceding schema `/9` initial scheduler correction is committed as `6eedac71055c69c5f18a3f674549355478795049`; this projection follow-through is `73a1841e89e1e2d1f65269dac36997b848f221cd`. U-PER-SCALE-001 remains ACTIVE.

### Native Save with a pristine companion Encounter

**Problems first.** A full Universe graph can contain multiple registered Encounters and ChoiceBooks, while native Save historically admitted only one. The previous restore path also inferred the selected Encounter from class order, which is unsafe when the selected root is not the first Encounter in event history. A fully progressed companion cannot yet be resumed correctly because the current native Save API has one selected Encounter RNG/history stream.

**Correction.** Native Save now validates and retains all registered Encounter/ChoiceBook ownership, but admits additional Encounters only when they are pristine and have no separate transactional RNG binding. The Save's explicit root role identifies the selected Encounter. Restore rebuilds every ChoiceBook, shares the restored Universe scheduling lock, repairs Action and AuthorityReference links across the registry, restores committed receipt anchors for each Encounter, and restores selected-Encounter native services based on the explicit root. It refuses a progressed companion before publishing a Save, without mutating the selected or companion state.

**Verification.** `test_native_persistence.test_native_save_restores_a_pristine_companion_encounter_and_refuses_progressed_one` creates the companion first to verify root selection independent of registry order, saves the selected Encounter, and loads in a fresh OS process. Both Encounter IDs and two ChoiceBooks survive; both Choices share the restored Universe lock; the selected Encounter resumes its saved RNG, the caller explicitly binds a valid RNG to the previously pristine companion, and each continues through the native scheduler. Outcome, time, RNG cursor and encoded native-history digest match uninterrupted control for both. After progressing the companion, Save refusal is asserted and before/after selected/companion state is identical.

Focused verification after this increment: `test_native_persistence` **33 passed / 83.098s**; `test_checkpoint_adapters` **48 passed / 18.685s**; `test_persistence_capability_matrix` **3 passed / 0.006s**. `git diff --check` and Python bytecode compilation of the changed modules/tests passed. The native-history suite had **27 passed / 20.604s** immediately before this increment; the multi-Encounter change does not modify its history codec/query implementation. The capability matrix now describes this exact limit. This establishes safe coexistence and a native continuation for a newly initialized companion, not resumability for every progressed Encounter in the Universe. Independent Encounter cursors/histories, arbitrary registry families and definitions, full historical consumer parity, durable journal recovery, and production Save/Load integration remain open.

**This initial pristine-companion limit is superseded below.**

## Native Save `/2`: independent progressed Encounter streams

### Problems first

The full Universe graph already retained every registered Encounter and ChoiceBook, but native Save authenticated only one Encounter's RNG cursor and history. Restoring a progressed companion therefore risked silently losing its independently owned deterministic continuation. Binding an arbitrary caller RNG after Load did not meet same-Universe resumability.

### Implementation

Native Save now uses `/2` only when the Universe has multiple registered Encounters. It retains the established `/1` bytes and strict reader for the common single-Encounter case. `/2` adds a canonical sorted Encounter table containing each Encounter's logical ID, validated RNG cursor and committed history (or `null` at its exact initial boundary); the selected Encounter ID remains explicit. The shared strict graph still contains every Encounter, ChoiceBook, Action/reference and immutable registry node. The graph restorer accepts separately decoded private cursors for the companion Encounters, binds each to ordinary native progression before committed receipt inspection, validates scheduler declarations, and restores a recorder per Encounter. `native_persistence.rng_owner_for(encounter)` exposes an already validated process-local owner to native clients that need to advance a nonselected Encounter. Each world Encounter must already have its own transactional RNG owner; absent or shared owners are refused.

The `/2` reader validates canonical outer integrity, sorted unique Encounter IDs, exact graph-registry identity equality, each RNG state using Python's strict `setstate` validator, the selected cursor against the cursor stored in the graph, committed history owner IDs, native history against each restored receipt projection, and cross-Encounter graph links. It does not re-resolve prior Actions. The `/1` native format remains readable and writable for one-Encounter Universes; accepted `/10`–`/12` Arena readers remain unchanged.

### Verification

`test_native_persistence.NativePersistenceTests.test_native_save_restores_and_continues_multiple_encounters` exercises a companion created before the selected root, independent cursors, fresh-process Save/Load from the initial companion boundary, continuation of both through the native scheduler, a second Save after both committed receipts, and fresh-process continuation again. It checks Encounter IDs, ChoiceBook count/shared lock identity, Action outcomes, boundary times, RNG states and encoded history digests against uninterrupted control. Re-sealed altered outer files prove duplicate Encounter rows and a mismatched companion RNG cursor are rejected; strict Save→Load→Save byte equivalence also passes.

The first implementation exposed that candidate revalidation omitted the caller-provided selected RNG argument. The read-set check was corrected to resolve the selected cursor from its verified live binding during revalidation; the focused multi-Encounter regression then passed. This was an implementation defect, not a missing rule. The final strengthened tests include tampering, Save/Load byte equivalence, and distinct recipient bindings. Combined command `cd src && PYTHONPATH=../tests:../examples:../../npc-generator ../.venv/bin/python -m unittest test_native_persistence test_checkpoint_adapters test_persistence_capability_matrix -v` passed **84 tests / 102.837s** (33 native persistence, 48 checkpoint adapters, 3 matrix). Latest command covering both multi-Encounter continuations plus checkpoint-adapter and matrix suites passed **53 tests / 28.776s**. Python compilation and `git diff --check` pass. No Arena, browser or `npcgen` import was added to this native path.

**Limits remain material.** The native graph and fact history still duplicate committed receipt/Target projections. `/2` requires distinct private RNG owners and does not support a shared/module stream for a Universe with multiple Encounters. One multi-Encounter observer-recipient profile is now tested; other recipient-role combinations remain open. Full Action/state-family historical reconstruction, reusable portable definitions, durable journal crash recovery, broad scale/security portfolio and application Save/Load cutover remain open. This increment does not close U-PER-SCALE-001. Previous committed increment: `3b9e7aff73fa33cabb603621abf1c186f44a0fac`; schema `/2` implementation: `569ebe7595cfd8308cdbba07917dbf01ee40e77b`.

## Multi-Encounter observer-recipient continuation

### Problems first

The `/2` Save table stores each Encounter's independent scheduler/history/RNG state, but caller-owned observer evidence is supplied as a Universe-scoped tuple of `RecipientBinding` records. The multi-Encounter regression had only proven a shared graph and two independent histories; it had not shown that binding and rehydrating different observer-owned stores on different Encounter roots preserves their ownership across Load.

### Verification

`test_native_save_restores_recipient_bindings_for_multiple_encounters` creates two independent transactional Encounters with distinct Being observers, represented Object geometry, pending native Object-Spot Actions, independent RNG cursors and separate `ObjectObservationLedger` values. The second Encounter is the selected root while another precedes it in Universe event order. An initial boundary commits in the selected Encounter, then `/2` exports both explicit recipient bindings. A fresh OS process restores the two Encounter roots and histories, continues both six-second Spots through the ordinary native scheduler, and compares results, RNG, observer-specific observation identities/provenance/positions, and encoded history digests with uninterrupted control. Each observation remains in its owning observer's ledger. The test passes as part of the latest **53-test / 28.776s** integration command. It initially exposed two fixture issues: Object-Spot requires an exact `ObjectInstance` rather than a `WeaponInstance`, and pending Action `_encounter` is a rehydrated runtime link only after the scheduler advances; the corrected fixture uses the exact Object type and steps through its owning restored Encounter. Neither required engine-rule weakening.

This evidence narrows the remaining multi-Encounter recipient gap: distinct ObjectEvidence ledgers on two pending Object-Spot Actions, distinct LocationEvidenceLedgers on Being-Spot Actions, distinct BeliefLedgers on successful Group-observation Actions, and distinct listener-account lists on literal AskAboutPast Actions now restore across independent roots. Mixed/shared recipient combinations remain uncertified. A prototype that reused one mutable StatisticalGroup across two concurrently progressing Encounters was correctly refused by the current `_preflight` ownership rule (`shared cross-Encounter physical/recipient ownership requires a world coordinator`); no adopted rule authorizes shared mutable Group state across separate schedulers, so Group tests use independently owned instances. This does not close multi-Encounter family coverage, graph/history duplication, durable journal recovery, portability, or production cutover.

`test_native_save_restores_location_ledgers_across_multiple_encounters` authors two independent Encounter roots with separate observers, targets, transactional RNG owners and pending six-second Spot Actions. The selected root is the second registry entry. Each explicit `RecipientBinding` attaches a distinct `LocationEvidenceLedger`; after fresh-process load both normal schedulers resolve their own Spots. The test compares outcome, evidence identity, observer and Being IDs, source Action, Encounter, boundary, time, position and basis, plus per-Encounter RNG and committed-history digests, against uninterrupted control. Result: **1 passed / 6.193s**. Full native persistence verification after adding this case: `PYTHONPATH=tests:src:../npc-generator .venv/bin/python -m unittest test_native_persistence` — **35 passed / 95.152s**. Group quota implementation: `c66c9b7b6684a2502778d731189c4985eaae6db9`; this test and matrix/report updates are committed as `981fe5ebf53dcf8cb6106b9855e271c9b05587f2`.

`test_native_save_restores_distinct_group_beliefs_across_encounters` creates two native Encounter roots with separately owned StatisticalGroups and observers. Each accepted `ObserveGroupAction` writes a distinct bound `BeliefLedger`; `/2` strict Save/Load in a fresh process restores each observer's noisy observation and belief history, each Group's committed RealityLedger facts, and both private Encounter RNG cursors. Each restored Encounter then commits a native Delay. Evidence, belief chronology, Group facts, Action outcomes, RNG and native history are compared against uninterrupted execution. The focused case passed **1 test / 2.543s**. Full `PYTHONPATH=tests:src:../npc-generator .venv/bin/python -m unittest test_native_persistence` passed **36 tests / 98.088s**. The profile and matrix evidence are committed as `197f8198d7fd006ce3fa991bfc9b7cfd2fa8c072`.

`test_native_save_restores_listener_accounts_across_encounters` then covers two independent literal `AskAboutPastAction` declarations with separate `PersonalHistory` Facts and listener account lists. The `/2` Save binds both lists explicitly. A fresh OS process restores account Action/listener/speaker/topic/time/words and exact source Facts, then commits a Delay in both Encounter roots; outcomes, account payloads, history Facts, per-root RNG and committed-history digests match uninterrupted control. Focused case: **1 passed / 2.567s**. Full `PYTHONPATH=tests:src:../npc-generator .venv/bin/python -m unittest test_native_persistence` passed **37 tests / 100.252s**. The test and matrix/report updates are committed as `eb266139d04a867f3b611b9676ab7847b30c2ef7`.

## Problems-first — exact conditional formation-branch validation

### Gap

The closed native checkpoint adapter preserved `ConditionalAttributes` data but previously admitted any conditional CDF branch when a committed attribute depended on a formation quota trait. It emitted `conditional_external_assignment_validation_pending`. The source rules already define exact keyed cohort assignment in `StatisticalGroup._adult_formation_assignments`, so this was an adapter validation gap rather than an undefined rule. Capture must not invoke `ConditionalAttributes.resolve` or realize any additional group facts.

### Change and evidence

The adapter now derives the exact quota assignment with the reviewed native method only if every household composition fact needed for that cohort assignment is already committed. It checks that the implementation and keyed RNG provider are unmodified and not shadowed on the instance, then validates the committed value against its exact true/false CDF branch. An incomplete household ledger or changed provider is refused before any sampling. The regression compares raw state before and after capture and patches `resolve` to fail if called. The companion negative case constructs an incomplete source and proves the adapter refuses without mutation.

Updated matrix rows: `conditional_attributes.ConditionalAttributes` and `statistical_group.StatisticalGroup`. The fresh-process native Save/Load test now includes a committed quota-conditioned `voice` attribute and confirms the same exact value before continuing native Delay. Its historical fact stream still does not expose the complete Group/ConditionalAttributes state at arbitrary Encounter boundaries, so both rows remain partial.

Verification command `PYTHONPATH=tests:src:../npc-generator .venv/bin/python -m unittest test_native_persistence test_checkpoint_adapters test_group_conditional_refinement test_persistence_capability_matrix` — **95 passed / 108.792s**. This included the current `/2` multi-Encounter continuations, strict native graph persistence, all checkpoint adapter cases, Group quota and conditional attribute fresh-process continuation, and automated capability-matrix checks. Compatibility command `PYTHONPATH=tests:src .venv/bin/python -m unittest test_group_member_realization_candidate test_evolving_group_composition test_correlated_group_attributes` — **22 passed / 0.486s**. After adding the explicit no-resolver assertion to the exact-branch test, the three true/false, incomplete-source and malformed-quota regressions passed on the final code: **3 passed / 0.422s**.

This remains a selected native snapshot/restore slice. It does not satisfy historical `ConditionalAttributes` reconstruction/query parity at arbitrary Encounter boundaries, all StatisticalGroup fields, graph-free persistence, production Save/Load integration, or the overall U-PER-SCALE-001 gate. Implementation and evidence are committed as `c66c9b7b6684a2502778d731189c4985eaae6db9` (Validate and restore group formation quotas); unrelated staged archive paths remain staged and were excluded from that commit.

## Problems-first — combined heterogeneous recipients in a multi-Encounter Save

### Gap

Separate `/2` continuation tests covered ObjectEvidence, LocationEvidence, BeliefLedger and AskAboutPast account bindings, but no one portable Save combined heterogeneous recipient adapters. The remaining gap was their interaction inside a shared Universe graph and Restore—not an adopted-rule ambiguity.

### Verification

`test_native_save_combines_object_and_location_recipients` now authors three independent native Encounter roots in one Universe: a successful Object Spot with an explicitly bound `ObjectObservationLedger`, a Being Spot with a distinct `LocationEvidenceLedger`, and completed AskAboutPast testimony with a bound listener-account list and source PersonalHistory. One `/2` Save selected from the Location Spot root contains all three distinct recipient roles. An independent OS process strictly loads the bundle and advances each original Action through its normal Encounter scheduler. For all roots, the uninterrupted and restored paths match Action outcome, actual recipient payload/provenance, observer-scoped `NativeHistoryQuery.observer_facts_at()` projections at boundaries 0, 1 and 6, independent RNG cursor and canonical native-history digest. No Action is rerun during Load, and no observer ledger is inferred from objective world state.

The focused test passed: `PYTHONPATH=tests:src:../npc-generator .venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_native_save_combines_object_and_location_recipients -v` — **1 passed / 9.063s**. The complete headless native Save/Load suite passed after integration: `PYTHONPATH=tests:src:../npc-generator .venv/bin/python -B -m unittest test_native_persistence` — **38 passed / 109.631s**. Matrix tests passed: `PYTHONPATH=tests:src:../npc-generator .venv/bin/python -B -m unittest test_persistence_capability_matrix` — **3 passed / 0.010s**.

Adjacent strict adapter and query regressions also pass: `PYTHONPATH=tests:src:../npc-generator .venv/bin/python -B -m unittest test_checkpoint_adapters` — **50 passed / 19.845s**; `PYTHONPATH=tests:src:../npc-generator .venv/bin/python -B -m unittest test_native_history` — **27 passed / 21.293s**.

This closes only the tested mixed bundle. It does not enumerate every possible binding-role combination, authorize shared mutable Group state across independent schedulers, or close general observer privacy/query parity. Duplicate receipt/Target graph storage, full history-family coverage, durable journal recovery, portable reusable definitions, broad corruption/scale gates and ordinary production Save/Load integration remain open. No external or rules blocker is identified; U-PER-SCALE-001 stays ACTIVE. Test/matrix/report implementation commit: `59d80cc6e4e30fc753e92e60c8b37247fa871e04`. Before commit, `git diff --cached --check` passed and `python3 tools/check_publication_safety.py --staged` reported `files=11 findings=0 result=PASS`; the commit used explicit paths and excluded all five unrelated staged archive paths. The unrelated staged entries remain staged.

## Problems-first — self-contained shared Library definitions

### Gap

The matrix had no executable proof that a portable native Save contains its exact shared Library definition graph and that a fresh process can load it without falling back to the authoring checkout's `src/config` files. Graph schema admission alone was insufficient evidence. Canonical native Save→Load→Save equivalence was also not asserted for this fresh initial-state case.

### Correction and evidence

Added `test_native_save_is_self_contained_for_shared_library_definitions`. The parent authors a native Human with a Dagger from the configured Library, equips the exact registered Weapon definition, declares a pending Delay, and makes a native initial `/1` Save. A fresh OS process runs in a temporary working directory. It blocks `builtins.open` and `io.open` for the repository's `src/config` tree while leaving reviewed native method fingerprints intact, strict-loads the portable Save, verifies the Being and Weapon `original` references are the exact objects in the restored Library dictionaries, performs canonical Save→Load→Save byte comparison, and then continues the pending Action through `Encounter.step(1)`. Time, Action ID/outcome, RNG and committed-history digest match uninterrupted control. This directly tests the Library graph embedded in the Save rather than relying on config during rehydration.

Verification: `PYTHONPATH=tests:src:../npc-generator .venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_native_save_is_self_contained_for_shared_library_definitions -v` — **1 passed / 1.522s**; full `test_native_persistence` — **39 passed / 111.178s**; `test_persistence_capability_matrix` — **3 passed / 0.006s**. `git diff --check` and the scoped staged publication-safety audit passed; commit `98e95481b4187de9c3ce8148e66db42d21805b07` excluded all five unrelated staged archive paths.

This proves the current native graph's self-contained Library definitions and alias identity for the tested Human/Dagger world, not full family coverage, separate reusable definition records, legacy rules evolution, or arbitrary external definition types. Existing graph/history duplication, native historical coverage, crash-safe durable history, broad corruption/scale requirements and ordinary application cutover remain open. U-PER-SCALE-001 remains ACTIVE.

## Problems-first — Action-family historical query parity

### Gap

The 21 existing headless native continuation fixtures established same-Encounter Save/Load, Action consequences, RNG and full history digest for a broad set of supported families. They did not all independently compare the history read API against the authoritative receipt at each committed cut. That left a gap between successful continuation evidence and the assignment's historical query parity criterion.

### Correction and evidence

`NativeDrawPersistenceTests._assert_history_matches_receipts()` now reconstructs a native fact log after each original uninterrupted scenario and walks every committed boundary. At each boundary it compares cumulative Action and Effect maps and their ordered logical identities to `Encounter.inspect_committed(boundary)`, boundary-local Action/Effect IDs to the `PublishedInterval`, TargetCandidate state to `TargetIntervalRecord`, EntityInspection context to the boundary receipt, and scheduler state to the same receipt. The check runs across all 21 native continuation scenarios: Draw; shield Don/Remove; Pick Up contention; Ready preparation and consumption; Object strikes including simultaneous durability; Subdual; Feint/follow-up; Touch→Grab→Trip; Grapple/Takedown and both Escape outcomes; Charge/Bull Rush/Overrun including successes and failures; Fatal Coup; and Break Weapon success/failure. These use existing ordinary native resolutions; no result is injected and no mechanics or production serialization changed.

Verification: `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_draw_persistence -v` — **25 passed / 116.868s** after adding prepared/targeted Dodge, Parry, shield Block and Yield Save/Load cases. `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_scenario` — **1 passed / 0.939s** after the headless builder began forwarding movement/progression inputs. The source-linked matrix records this evidence while retaining OPEN status: the action inventory is not exhaustive, observer recipient and defined-record parity remains incomplete, the query still depends on the receipt graph, and production graph-free Save/Load has not been integrated. Test/report commit is pending scope-specific staged checks. U-PER-SCALE-001 remains the sole ACTIVE program.

## Problems-first — unresolved native Throw miss continuation

### Gap

The native projectile matrix had fresh-process evidence for a shielded successful hit but not for the supported miss branch. Without a miss continuation, the preserved `miss_direction`, `miss_unresolved` status, and zero-damage consequence were not proven across Save/Load. No rules gap was involved: the ordinary projectile resolver already records these facts.

### Correction and evidence

Added `test_missed_projectile_continues_with_native_unresolved_destination`. It builds the existing Arena-independent native Throw scene, replaces only its accepted initial Choice with an ordinary targeted Throw, and sets the owned RNG to seed 0. The native action releases at t=4; the test saves with flight still in progress and both uninterrupted and fresh-process executions continue to impact. Both report `miss`, direction 7, status `miss_unresolved`, zero impact damage, the same Object position and landing projection, unchanged target HP, identical RNG, and identical complete native-history digest. At every committed boundary, `NativeHistoryQuery.projectile_state_at()` matches the corresponding committed receipt; no destination is synthesized from the miss direction.

### Verification

- `PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_missed_projectile_continues_with_native_unresolved_destination -v` — **1 passed / 3.861s**.
- `.venv/bin/python -B tests/test_native_draw_persistence.py -v` — **25 passed / 118.781s**, with receipt-level historical query parity across every boundary in its Action-family continuation fixtures.
- `PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest discover -s tests -p 'test_native_persistence.py' -v` — **42 passed / 120.341s** before adding the new miss case; the added test passed separately as above.
- `PYTHONPATH=src:examples .venv/bin/python -B tests/test_native_throw_arena.py -v` — **13 passed / 19.094s**; capability-matrix gates — **3 passed / 0.005s**; test-module `py_compile` and `git diff --check` passed.

The projectile matrix now records supported hit and miss continuation. Target-moved/fatal projectile branches, other supported Action/state families, graph-free historical reconstruction, durable journal recovery, application Save/Load cutover, complete native migration/security/scale gates remain open. Commit evidence and the full final focused result will be added after scoped staging/audit. U-PER-SCALE-001 remains ACTIVE; no rules or external blocker is identified.

## Problems-first — target movement during saved projectile flight

### Gap

The new native miss case did not cover the distinct supported `target_moved` resolution. Directly setting a target's position after release would be an unreceipted mutation and could not establish a lawful persistence case. The native `Encounter.step()` already accepts committed movement inputs before each boundary, so the fixture can use ordinary represented movement without altering the attack rule.

### Correction and evidence

Added `test_target_movement_during_projectile_flight_restores_natively`. A targeted Throw is released at t=4 and saved while airborne. Both uninterrupted and fresh OS process paths move the target by the same native per-second velocity for boundaries 5–7, then advance to projectile arrival at t=8. The target ends at `(8.0, 0.6, 0.0)`; the ProjectileFlight records `target_moved`, `landed`, zero impact damage, no target HP change, and the unchanged projectile landing position. RNG and complete native-history digest match exactly. `projectile_state_at()` matches the receipt at every checked boundary.

### Verification

`PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_target_movement_during_projectile_flight_restores_natively -v` — **1 passed / 3.860s**. This adds target-moved continuation only; fatal Throw/Coup-de-grace continuation and the broad graph-free history, journal, security, scaling, migration and application cutover gates remain open. U-PER-SCALE-001 remains ACTIVE.

## Problems-first — held-Weapon projectile release and Coup de grace

### Root cause

The fatal-Throw path exposed three native integration omissions. First, `Encounter.inspect_committed()` authorized spatial identity changes only for Pick Up, Drop and post-roll Disarm landing, even though a validated `ProjectileReleaseEffect` installs the held Weapon's release-position `SpatialState`. Second, `_expected_body_parts()` did not account for that same committed effect removing the released Weapon from its holder's hand. After those inspection checks were corrected, the native Save rejected the released `WeaponInstance`: its exact field adapter omitted the existing optional `_projectile_flight` and `_atomic_projectile_history` state, and the measured-projectile-position validation recognized only `ObjectInstance`. These were implementation/schema gaps, not undefined projectile rules.

### Correction

The inspector now authorizes release-position identity transitions only when backed by a committed `ProjectileReleaseEffect`, and reconstructs the actor's hand state by removing that released Object. The closed `WeaponInstance` adapter now admits the same two optional projectile fields as the already-supported `ObjectInstance`, with its strict optional-field contract. Native restore treats a released Weapon projectile as an exact trajectory position when validating represented spatial measurements. No object type or arbitrary runtime field was admitted.

### End-to-end outcome

`test_thrown_coup_de_grace_restores_critical_consequences` creates a lawful held Dagger Throw against an aware helpless Being at the represented one-yard range. At t=4, the committed release is inspectable and Saveable with the Weapon airborne. A fresh OS process restores the same Encounter and Action IDs, advances through impact, and matches uninterrupted flight status/outcome, HP, body and critical-bypass DamageEffects, release Effect identity, RNG and complete native-history digest. The target reaches -3 HP; the ordinary native resolution is `hit` with its committed Coup de grace critical-bypass consequence.

### Verification

- `test_native_throw_arena.NativeThrowTests.test_inspection_accepts_committed_weapon_projectile_release_transition` — **1 passed / 0.896s**.
- `test_native_persistence.NativePersistenceTests.test_thrown_coup_de_grace_restores_critical_consequences` — **1 passed / 4.018s**.
- `test_encounter_inspection` — **42 passed, 1 known failure / 23.828s**. The sole failure is `test_shield_can_be_negative_and_has_separate_causal_damage`, previously reproduced against baseline commit `a0062420c005820e1a2833adafffb2b6473723fd`; it is unrelated to projectile inspection and remains unchanged.

Final affected-suite verification for this continuation: `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest discover -s tests -p 'test_native_persistence.py' -v` — **45 passed / 131.620s**; `PYTHONPATH=src:examples .venv/bin/python -B tests/test_native_throw_arena.py -v` — **14 passed / 20.779s**; `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest discover -s tests -p 'test_checkpoint_adapters.py' -v` — **50 passed / 19.675s**; `.venv/bin/python -B tests/test_persistence_capability_matrix.py -v` — **3 passed / 0.006s**. The capability-matrix test confirms the documentation's exact closed-field inventories against the executable adapter registry. The existing inspection suite result above is the previously verified baseline failure, not a new failure. This continuation also retains the earlier 25-test Action-family historical receipt parity suite and its explicitly partial matrix assessment.

This closes the held-Weapon release inspection and tested thrown Coup consequence path only. The broad family, graph-free history, durable journal, application cutover, full corruption/security/migration and scaling gates remain open. U-PER-SCALE-001 remains ACTIVE.

## Problems-first — held-Weapon shield and Armor continuation

### Gap and result

The earlier shielded-projectile Save/Load fixture used a stone, so it did not exercise the implemented thrown-Dagger → shield → Armor durability chain. The accepted native Throw test already establishes a legitimate seed and represented equipment; the persistence fixture now uses the same seed-116 Dagger path. It saves after the committed release, restores in a fresh OS process, and continues through impact using the ordinary native resolver. The uninterrupted and restored receipts match: shield ProtectionEffect incoming 3 / passed 1 / intercepted, shield durability 1; Armor ProtectionEffect incoming 1 / passed 0, Armor durability 1 and Armor HP decreasing by exactly 1; target HP, projectile result, RNG and full history digest also match. No defense or damage outcome is synthesized.

The same assertion pass now checks canonical byte-identical Save→Load→Save at the in-flight Weapon cut and checks `NativeHistoryQuery.target_at()` against each committed native TargetIntervalRecord for the thrown Weapon, shield, Armor and target Being, in both the uninterrupted authority and the restored fresh process.

Verification: `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_projectile_shield_interception_continues_after_native_fresh_process_load -v` — **1 passed / 4.346s**; `.venv/bin/python -B tests/test_persistence_capability_matrix.py -v` — **3 passed / 0.006s**; test module compilation and `git diff --check` pass. This closes only that shield/Armor projectile fixture; general Being/Armor query parity and graph-free history remain open. Relevant local commits in this continuation are `1acdd7690c47c4ee316b339fd52712cba20fa30e` (Group member placements), `6d95c8224217ef76f578d7b1aad76e5bf3650f8b` (unresolved Throw misses), `df24d71ea04ded968f031c884724b10cbdd56fe7` (native held-Weapon release and Coup-de-grace persistence), `22d41ec1c67a92de90f8e91d494bed7471bad299` (shield/Armor projectile consequences), and `4c2a94addd3239e8089ca56e312321a14495d13d` (per-boundary restored Target history parity). U-PER-SCALE-001 remains ACTIVE.

## Problems-first — rollback preserves prior portable Save

The prior rollback test proved that the in-memory native-history recorder did not append a receipt after a failed publication, but it did not check that a previously completed portable artifact stayed byte-for-byte intact or that the faulted in-memory cut remained fail-closed. `test_rolled_back_publication_has_no_appendable_history_receipt` now keeps a complete Save file from immediately before a commit-marker fault, records the RNG cursor, and injects the existing post-marker publication failure. Rollback restores time/RNG and the recorder cursor; the existing file remains byte-identical; the prior history object remains at the prior boundary; the uncommitted boundary cannot be appended; and `export_save` refuses the faulted in-memory Encounter until explicit recovery. This is the intended integrity boundary: it does not claim the quarantined runtime is Saveable before recovery.

Verification: the focused `test_rolled_back_publication_has_no_appendable_history_receipt` passed **1 / 2.676s**; full `test_native_history.py` passed **28 / 22.515s**; capability-matrix gate passed **3 / 0.005s**; test compilation and `git diff --check` passed. The atomic-receipt matrix records this narrow safety result. All-family journal crash recovery and production cutover remain open; no rule decision is needed.

## Problems-first — fatal targeted Throw consequence branch

The projectile matrix had fresh-process continuation for hit, unresolved miss and target movement, but not for the separately represented fatal impact. There is no rules gap: `resolve_targeted_throw_arrival()` records a `FatalEffect` and returns `fatal` when the adopted Coup de grace Fortitude check fails. A deterministic seed search over native encounters found seed 0. The new test saves an actually held Dagger after its committed Coup de grace release, restores it in a fresh OS process, and continues the ordinary resolver through the impact. Both processes match the `fatal` ProjectileFlight result, `landed` status, original Throw Action outcome `released`, body damage 4, critical-bypass damage 4, same FatalEffect identity/target, negative target HP, RNG and full history digest. `projectile_state_at()` matches each committed projectile receipt from boundary 0 through impact. No roll, result or position is injected.

Verification: `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_thrown_coup_de_grace_fatal_outcome_restores_with_causal_damage -v` — **1 passed / 3.998s**; `.venv/bin/python -B tests/test_persistence_capability_matrix.py -v` — **3 passed / 0.005s**; module compilation and `git diff --check` pass. The matrix now has native fresh-process evidence for the represented `ProjectileFlight` impact outcomes hit, miss, fatal and target_moved; the complete persistence assignment remains ACTIVE for its other families, graph-free bridge, compatibility, durability and application gates.

## Problems-first — pending targeted Throw Choice continuation

The projectile cases saved after the Weapon had already been released. That did not establish restoration of the accepted Choice and held Weapon state before any release/flight facts existed. Added a native initial-state Save scenario with a pending held-Dagger targeted Throw Choice. The Save correctly has no committed history yet; strict fresh-process Load restores the accepted Choice and Weapon custody, then the ordinary scheduler releases the Dagger and resolves its hit at impact. Uninterrupted and child-process paths match Action identity/outcome, flight status/result, target HP, weapon position, RNG and full history digest. At each boundary, cumulative native Action/Effect and timeline projections match `Encounter.inspect_committed()`.

Verification: `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_pending_targeted_throw_choice_restores_before_release_and_impact -v` — **1 passed / 5.226s**. This closes the initial pending Throw cut only; the broader Action, registry, historical graph and application gates remain open.

### Affected integration gate

After adding both the fatal-impact and pre-release pending-Choice fixtures, `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest discover -s tests -p 'test_native_persistence.py' -v` passed **47 / 142.282s**; `PYTHONPATH=src:examples .venv/bin/python -B tests/test_native_throw_arena.py -v` passed **14 / 20.759s**; `.venv/bin/python -B tests/test_persistence_capability_matrix.py -v` passed **3 / 0.006s**. The native-history suite passed **28 / 22.515s** after the rollback-safety assertion. Module compilation and `git diff --check` pass. This does not close the matrix's open non-projectile families or the complete persistence architecture.

## Problems-first — simultaneous projectile impact continuation

The existing simultaneous Throw regression established order-independent arrival handling but did not Save in flight or compare the common impact receipt after strict fresh-process restoration. Added `test_simultaneous_projectile_arrivals_restore_as_one_native_boundary`. Two ordinary Throw Actions release against one represented target; the portable native Save is taken with both flights pending. The uninterrupted and a separate OS process both advance to boundary 7, where the two represented flight times are resolved atomically. Both projectile outcomes and per-projectile damage, target HP, the two projectile state identities in the common receipt, ordered receipt Effects, RNG, complete history digest, and each cumulative Action/Effect/timeline query through the boundary match. The adopted resolver and projectile physics are unchanged.

Focused verification: `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_simultaneous_projectile_arrivals_restore_as_one_native_boundary -v` — **1 passed / 4.517s**. The simultaneous-arrival and existing shielded-impact cases pass together (**2 / 8.710s**). This is one additional atomic continuation case; it does not close broad family parity, graph-free reconstruction, durable history journaling, legacy/security breadth, or production Save/Load integration. U-PER-SCALE-001 remains ACTIVE.

## Problems-first — Target query boundary-zero type safety

At boundary zero, the history initial map contains `EntityInspection`, while `target_at()` promises a `TargetCandidate` from a committed Target receipt. The query returned the initial mapping without checking its record type. It now rejects a Target query where no committed `TargetCandidate` was recorded; initial entity data stays queryable through the Entity API. This is a historical-read correctness fix, not a missing Encounter rule.

Verification: boundary-zero refusal **1 / 0.973s**, normal target receipt round-trip **1 / 1.110s**, and complete native history suite **29 / 22.012s**. The complete native persistence module, including the two-flight atomic arrival case, passed **48 / 149.924s**. Native graph/receipt duplication, broad matrix closure, durable journal/recovery, security breadth and production cutover remain open; no external or rule blocker has been found.

## Problems-first — native Save filesystem publication faults

The native portable writer's atomic path had no injected checks at the link publication boundary. `test_native_file_write_recovers_across_pre_and_post_link_faults` now confirms that a pre-link failure leaves no destination or temporary file and a subsequent write succeeds; a post-link directory-fsync failure is reported as after publication, and the exact linked artifact remains present and passes strict `load_path()`. This is API failure injection only; it does not claim simulated power-loss behavior across filesystems or a separate append-journal architecture.

Focused result: **1 passed / 3.486s**; the complete native persistence suite passed **49 / 150.088s**. Recent scoped commits for this continuation include `041c6b38db1f062b439ac0c287fc6b0a7e10bb59` (simultaneous projectile receipt continuation) and `314ce4546022fb35950780972e857c8ebca99c6e` (Target query boundary-zero type safety); the file-write regression and current report/matrix changes are pending their own audited commit.


## Problems-first — atomic boundary fact reconstruction

The native history API had individual readers for Action/Event/Effect, Targets, Entity context, objective/recipient state, scheduler, projectiles, RNG, observer knowledge, fatigue and receipt facts, but no single graph-independent operation that returned the complete stored commit row. This made consistency review across those independently stored families inconvenient and did not give consumers one immutable point-in-time cut.

`NativeHistoryQuery.boundary_facts_at(boundary)` now composes the full portable boundary payload from the validated fact history alone, with no access to the live Encounter. It carries stable IDs and causation, TargetCandidate/EntityInspection records, objective/use/recipients, queue and Choice projection, projectile state, time, ordered Action/Event/Effect facts, RNG, notification/Disarm facts and observer/fatigue context. Process-local object anchors are intentionally absent; prior history schemas that did not record a field return its established unavailable marker, not a reconstructed guess.

`test_native_history.py` compares the API to the source payload at every standard-fixture boundary. `test_native_draw_persistence.py` uses the same source-receipt comparison in its 25-scenario action-family helper. Focused test **1 / 1.043s**; complete history module **30 / 22.430s**; Action-family suite **25 / 120.448s**. The method is a read-model increment; old receipt/Target runtime history remains duplicated in the portable graph, so the full acceptance gate and cutover remain open. The Save publication fault test's commit is `71ed98956881355b2ef061fa94a11fade63da859` (full native persistence: **49 / 150.088s**). Current query-code/test/report change awaits its own audit and commit.

## Problems-first — compact native Target history and exact `/1` migration

Native fact history already held the exact `TargetCandidate` at every committed boundary, but the resumable graph also stored each target's `TargetIntervalRecord` rows. This duplicated one complete history family in the portable Save.

Full-native graph `/2` now writes Target-owned histories as empty lists while retaining their authoritative `TargetCandidate` records exactly once in the validated native history. The compaction adapter admits only reviewed Being/Object/Weapon/Armor/StatisticalGroup Target rows, validates owner and record types before omitting them, and seals the actual source list in the freshness read set. Strict restore requires a complete history for every Encounter, checks contiguous receipts, exact receipt Entity coverage, Effect identity/content and observer owner bindings, re-materializes the same `TargetIntervalRecord`s, preserves field absence for registered inactive Entities, and then exercises the existing receipt anchors and `inspect_encounter`. The ordinary action resolver is not replayed. Generated-Arena production `/12` Save/Load is unchanged.

Native graph `/1` remains a strict migration input for its exact known writer fingerprints, including the immediately prior committed HEAD `bfc28668a4bb33a158a8a24e92b92233a944c475`. The dedicated test uses its exact compatibility fingerprint and uncompact graph fields, restores the history and Target rows, and verifies byte-identical canonical re-save as the current compact graph `/2`. The complete native persistence cohort also covers accepted Arena `/10`, `/11`, and `/12` read/migration paths.

On the same lawful 64-Feint, 129-boundary scenario, the uncompact and compact capture candidates were both measured at the same cut:

| Registered Beings | Graph before | Graph `/2` | Target bytes removed | Reduction | History | Total Save | Sim / query / export / fresh-process continue (s) | Peak RSS platform units |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 4,859,053 B | 4,270,139 B | 588,914 B | 12.12% | 1,193,015 B | 6,886,682 B | 61.053 / 2.336 / 7.724 / 6.718 | 198,017,024 |
| 20 | 5,096,360 B | 4,507,699 B | 588,661 B | 11.55% | 1,193,015 B | 7,203,430 B | 60.135 / 2.315 / 8.063 / 7.205 | 203,112,448 |
| 200 | 7,526,897 B | 6,937,851 B | 589,046 B | 7.83% | 1,193,015 B | 10,443,630 B | 60.379 / 2.311 / 9.822 / 7.457 | 243,990,528 |

All three ran 64 actual Actions and checked all 129 history boundaries; each fresh process continued through ordinary native `Encounter.step()` and matched uninterrupted same-Encounter IDs, HP, time, RNG and history. A separate 200-quiet-boundary case checked every cut and matched fresh-process Delay continuation: **34,529 history bytes**, **4,697,590 graph bytes**, **6,298,132 Save bytes**; simulation/query/export/continuation **40.713 / 0.933 / 2.628 / 3.355s**, peak RSS **158,875,648** platform units.

The transactional-progression diagnostics were compared in clean source trees. `tests/test_transactional_progression.py` ran on current source and on a temporary `git archive` of pre-resume commit `b2c8b1b654d55298eb336267f67454e0a4dd9810`: both produced **55 passed, 4 errors, 2 failures** (current **22.414s**, baseline **22.289s**). The same four overlapping-Action fixtures reject declarations that lack adopted acquired Multi-action skill; the two unsupported-initial-graph tests expect refusals not produced by baseline source. These are verified pre-existing failures, not caused or changed by this assignment. No rule or test was weakened.

One earlier full native persistence run reported a stale-candidate refusal in the repeating Multi-action successor fixture. Review found compact capture had removed the synthetic empty Target list from the dependency seal without adding the actual omitted source list. The seal now contains the real list identity/type; the focused repeating-choice test and the full native persistence module pass. The defect was corrected as a genuine persistence adapter regression, not dismissed as baseline noise. The final native suite after restoring the scale helper's explicit measurement count returned **51 passed / 175.065s**.

This increment removed duplicate Target records. EntityInspection compaction is now also integrated; the remaining `CommittedBoundaryRecord` graph includes other receipt projections which still require field-by-field reconstruction and strict validation. All-family historical-reader/restore parity, durable append-journal recovery, broad adversarial coverage and production Save/Load cutover remain incomplete. U-PER-SCALE-001 remains ACTIVE.

## Problems-first — EntityInspection receipt-history de-duplication

### Gap and correction

Target-history compaction left every committed receipt's complete EntityInspection dictionary in the native Save graph even though those exact typed facts were already recorded in the authenticated history stream. The same projection has to be validated at every commit cut, including distinctions between absent fields and registered Entities whose source value is empty.

Native graph `/2` now carries an explicit adapter marker when both Target and Entity histories are compacted. The adapter only omits a receipt's `entities` map after type/owner checks and binds its canonical source contents into the snapshot freshness seal. Strict Load requires a complete history set for each Encounter, validates receipt-chain and Entity coverage, restores typed facts with registered-owner/category/shape checks, then reconstructs Target histories and anchors before the existing full `inspect_encounter` validation. Histories that predate exact EntityInspection capture retain their old receipt graph projection; no later state is used to infer past facts. A migration regression pins the immediate Target-only graph `/2` writer fingerprint (`af95b65227b2fb59a24f157d6f5ae8882e4f6d4586bec58470b5e3f5e3651468`) and verifies strict migration and canonical current re-save. Arena production `/12` output remains untouched.

### Verification and measurement

The 64 lawful-Feint/129-boundary scale workload was recaptured with uncompacted, Target-only and Target+Entity graph candidates. Strict fresh-process Load and ordinary Encounter continuation match all 129 uninterrupted cuts, preserving same-Encounter identity, HP, time, RNG and history. Entity context saves a further **19,291 / 19,304 / 24,124 bytes** at 2/20/200 registered Beings. Combined graph reduction is **608,402 / 607,900 / 612,983 bytes** (**12.52% / 11.93% / 8.15%**) and current total Saves are **6,861,818 / 7,177,810 / 10,405,682 bytes**. The retained fact history is **1,193,015 bytes** in each Action run.

A separate 200-quiet-boundary run compares every query cut and fresh-process continuation: graph **4,687,649 B**, history **34,529 B**, total Save **6,284,876 B**; simulation/query/export/Load+continue **47.045 / 1.017 / 3.818 / 3.789s**, peak RSS **150,290,432** platform units.

Current focused verification for the integrated implementation: native persistence **54 passed / 192.788s**; Draw/Action continuation **25 passed / 131.532s**; native history **30 passed / 25.812s**; checkpoint adapters **50 passed / 21.975s**; capability matrix **3 passed**; targeted Entity/legacy/multi-Encounter and Entity/StatisticalGroup cases **5 / 17.888s** and **4 / 13.980s**. Module compilation and `git diff --check` pass. A full-suite failure exposed a synthetic empty-list identity collision across separate Encounter captures; the adapter now excludes each synthetic token from reused identity caches, and the multiple-Encounter regression passes. No rule or accepted Save behavior was changed.

### Problems still open

Two receipt projections (Target and Entity) are now deduplicated, but Actions/Effects, Objective, schedule, projectile, recipient and other recorded receipt facts remain copied in graph receipts. The full capability matrix still contains open family and query/rehydration rows. Durable append-journal recovery, complete corruption/security coverage, native `/10`–`/12` migration breadth and ordinary application Save/Load cutover have not passed. These are remaining implementable acceptance work, not a genuine rule or external blocker. U-PER-SCALE-001 remains ACTIVE.

**Commit evidence:** this section and the verified Entity compaction implementation are pending the current scoped local commit. Do not push.

## Problems-first — compact native committed receipt facts in strict graph `/2`

### Problem and correction

The latest graph still serialized duplicate per-boundary Action declarations/results, identified Effects, Objective candidate facts and uses, scheduler/fence projections, participant lists, and projectile states, although the exact facts are present in authenticated native history. These were the next large repeated graph payload after Target and EntityInspection compaction. Restoration also requires binding process-local `RecipientIdentity`, scheduler `AuthorityReference`, and Objective ledger addresses to the exact restored owners; merely decoding address-free values would leave a superficially loadable but unusable graph.

Native graph `/2` now omits those eight receipt projections under explicit `committed-receipt-facts/1`, only when complete EntityInspection history is also available. Capture validates each closed source shape and seals its canonical source digest against recapture. Strict restoration requires history for every Encounter, validates exact receipt-boundary coverage, reconstructs typed Actions, Effects, Objective candidate facts, uses, starts, participants, scheduler state and projectile maps, and rebinds the process-local identities from registered native owners. It then continues through existing anchor reconstruction and `inspect_encounter` validation; no prior Action is rerun. Older `/1` and `/2` writers without the marker keep their original receipt payloads and migrate strictly. The ordinary Arena `/12` writer is unchanged.

An initial focused run exposed that Objective history contains `SubjectRealityCandidate`, not the derived public `ObjectiveInspection` view. The loader was corrected to restore and bind the candidate to its exact Group/PersonalHistory RealityLedger, preserving the candidate type expected by live receipt validation. Four fresh-process Objective and observer regressions then passed. A further stale-candidate regression changes an omitted receipt source after capture and confirms checkpoint revalidation refuses it.

### Verification

- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_persistence -v` — **56 passed / 193.193s**. This includes strict Objective/observer restoration, pending and completed Action continuation, simultaneous combat, shared/independent owners, self-contained definitions, corruption checks, and accepted Arena `/10`–`/12` migration. The additional source-projection freshness regression passed separately (**1 / 1.298s**).
- `... -m unittest test_native_history -v` — **30 passed / 25.659s**.
- `... -m unittest test_checkpoint_adapters -v` — **50 passed / 22.021s**.
- `... -m unittest test_persistence_capability_matrix -v` — **3 passed / 0.036s**.
- `PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest test_native_draw_persistence -v` — **25 passed / 138.110s** across native Action-family Save/Load and continuation cases.

Scale uses 64 lawful Feint resolutions and checks all **129** committed boundaries against native receipts before exporting, then strictly loads in a fresh OS process, continues through ordinary Delay, and compares exact same-Encounter IDs, RNG, HP, time and full history digest with uninterrupted control. No Arena or npcgen module is imported by the child.

| Registered Beings | Uncompacted graph | Target+Entity graph | Receipt facts saved | Final graph | Total graph reduction | History | Save | Sim / query / export / Load+continue (s) | Peak RSS |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 4,853,595 B | 4,265,254 B | 716,774 B | 3,548,480 B | 26.89% | 1,193,015 B | 5,924,470 B | 67.227 / 2.480 / 11.493 / 9.243 | 203,685,888 |
| 20 | 5,095,518 B | 4,507,430 B | 716,842 B | 3,790,588 B | 25.61% | 1,193,015 B | 6,247,282 B | 66.624 / 2.468 / 12.017 / 8.455 | 186,875,904 |
| 200 | 7,527,736 B | 6,938,493 B | 727,605 B | 6,210,888 B | 17.49% | 1,193,015 B | 9,474,346 B | 66.044 / 2.684 / 14.068 / 9.317 | 248,184,832 |

A current-code quiet-boundary rerun checked all **200** boundaries and matched fresh-process continuation: graph **4,580,680 B**, history **34,529 B**, Save **6,142,252 B**; simulation/query/export/Load+continue **47.547 / 0.988 / 3.578 / 3.943s**, peak RSS **175,390,720**. These graph-size improvements measure this repeated-receipt slice; they do not establish bounded total Save growth for arbitrary new state or complete history sufficiency.

### Remaining work

The graph still retains per-receipt Objective-recipient projections, the identity-bearing receipt shells and complete current simulation state. Some registered field families and historical readers still lack full native scenario evidence. Durable append-journal crash recovery, the broad adversarial/security portfolio, general production `/10`–`/12` cutover and the final application Save/Load path remain open. There is no adopted-rule or external blocker. U-PER-SCALE-001 remains ACTIVE.

**Implementation commit:** `88e7d3f` (`Compact native committed receipt facts`). The scoped safety audit passed with zero findings; the five pre-staged historical archive paths were preserved and excluded from this commit.


## Problems-first — observer belief fields and inquiry reachability

### Findings

The multi-Encounter BeliefLedger test previously established fresh-process evidence and belief-history restoration, but did not compare interpretation fields or the sampler/interpreter configuration. It also left these concrete field-catalog rows marked as having no native restore evidence. The native observer transaction stores its committed observation and interpretation in the observer-owned ledger; `ObserveGroupAction.field_observation` and `.field_interpretation` are resolution scratch slots and remain unset on the transactional route. They are not the authoritative committed evidence and must not be mistaken for lost state.

An attempted extension using `InquiryPolicy.propose()` followed by `BeliefLedger.record_inquiry()` after accepted scheduling was correctly refused at Save with `InspectionRejected: unreceipted Belief change`. The helper is not wired to an atomic native publication effect; the native inspector rejects out-of-band observer mutations. I removed that probe rather than bypassing receipt validation. `InquiryProposal`, `InquiryRecord`, and `EvidenceReassessment` remain defined/policy-side shapes without native transactional producers. This is an implementation gap in the scaffold-to-native integration, not an ambiguity in persistence serialization or an adopted rule decision.

### Correction and verification

Extended `test_native_save_restores_distinct_group_beliefs_across_encounters` to compare the complete configured `SampledGroupObservation` and `FieldInterpreter`, every FieldObservation field, all noisy CountReport values, original/current FieldInterpretation fields, chronological BeliefRevision provenance, separate observer ownership, Group Reality records, RNG, native-history digest and native Delay continuation for both roots after strict fresh-process Load. The matrix now distinguishes tested native state from Inquiry/Reassessment scaffolding that cannot currently enter committed state.

- `PYTHONPATH=.:../src:../examples:../../npc-generator ../.venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_native_save_restores_distinct_group_beliefs_across_encounters -v` (from `tests/`) — **1 passed / 3.550s**.
- The same test plus `test_persistence_capability_matrix` initially exposed the matrix's executable Arena-classification check after an evidence row was improved; no implementation test failed. After restoring the required source classification phrase, `test_persistence_capability_matrix` — **3 passed / 0.019s**.
- `git diff --check` — passed.

The field-level evidence is corrected; the full assignment remains incomplete. In particular, receipt-backed reassessment/inquiry Actions do not exist, and general historical query parity, remaining state families, strict corruption/security breadth, durable append-journal recovery, broad migration coverage and ordinary application Save/Load cutover still require implementation. No rule or external blocker is established. U-PER-SCALE-001 remains the sole ACTIVE program.

**Commit:** `8bc4540` (`Verify native observer interpretation restoration`) records the initial test/matrix/report/TASKS increment. A subsequent focused regression now also compares owner-filtered `observer_facts_at()` at boundaries 0, 1, and 2 against the uninterrupted controls, testing historical as well as restored current ledger values.


The historical recipient query comparison was added after the initial commit: `PYTHONPATH=.:../src:../examples:../../npc-generator ../.venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_native_save_restores_distinct_group_beliefs_across_encounters test_persistence_capability_matrix -v` (from `tests/`) — **4 passed / 4.213s**. This checks each observer-owned Group BeliefLedger view at boundaries 0/1/2, including no evidence before observation, the owner-only committed projection at boundary 1, and the unchanged projection through boundary 2. The follow-up documentation/test diff is pending scoped commit.


## Problems-first — native local spatial-frame continuation

### Gap and correction

The source-linked matrix listed `spatial.frame.LocalFrame` in the strict native graph contract, but only geometry/unit tests—not Save/Load continuation—supported the row. Encounter-local coordinate frame is future-relevant because later legal movement may declare a local velocity. A save that retains only global Being positions would not be sufficient to continue that command.

Added `test_native_local_frame_movement_resumes_in_fresh_process`: a native Encounter uses a translated, rotated, right-handed frame, commits one local-velocity Run, saves, and then independently commits a second local-velocity Run. An OS child strictly loads the first boundary and executes the same ordinary native Action. The test compares exact frame origin/axes, global and local Being positions, Action identities, RNG and full native-history digest against the uninterrupted control. The test derives the transformed global displacement from the declared LocalFrame axes; it does not infer frame data from position or geometry.

- `PYTHONPATH=.:../src:../examples:../../npc-generator ../.venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_native_local_frame_movement_resumes_in_fresh_process -v` (from `tests/`) — **1 passed / 2.000s**; paired with the 3-test capability matrix in one invocation, **4 passed / 2.051s**.
- `git diff --check` — passed.

The matrix now cites this evidence. Remaining spatial geometry concerns include historical query support for every LocalFrame-bearing context and all legal frame transitions; this scenario proves exact current-frame restoration and continuation only. Commit `74a5b60` is the verified observer-history baseline. This local-frame test and report/TASKS/matrix updates remain pending a scoped commit. No ordinary Arena Save path was changed; U-PER-SCALE-001 remains ACTIVE.


## Problems-first — objective fact/provenance restoration and historical queries

### Gap and correction

Several matrix rows for objective facts and atomic provenance still said there was no native restore path. Existing coverage did restore Group Reality and PersonalHistory ledgers, but it did not compare the historical objective query surfaces at each committed boundary or assert the restored literal AskAboutPast declaration recipe. This left a real evidence gap between current graph restoration and the facts-only history API.

Extended the two-root Group observer test to compare owner-independent `objective_at()` and `objective_use_at()` at boundaries 0/1/2 against the uninterrupted controls, along with every `ObjectiveCommitProvenance` field (Encounter/boundary/key/revision/origins/requesters/consumers). Extended the separate multi-listener AskAboutPast case to verify strict Load reconstructs the exact `EpisodeFacts` and `DeclaredObjectiveFact` types, key/value/origin, and the same historical objective-fact/use projections at boundaries 0/1/2. Updated the matrix for these tested contracts, including `ObjectiveFact`, `SubjectRealityCandidate`, `RealityLedger`, `Fact`, `FactKey`, and `CommittedFact`, with source/test citations.

- Targeted Group-belief + AskAboutPast continuation and executable matrix gate: **5 passed / 8.398s**.
- Complete `test_native_history`: **31 passed / 25.886s**, including authoritative Group objective fact/use query parity and PersonalHistory boundary visibility.
- `git diff --check` — passed.

The independent rotated-frame continuation and matrix gate were committed as `a42c44b`. This objective-family extension is pending scoped commit. It does not close all native field families or historical consumers; application Save/Load cutover, broad security/compatibility gates, other reader parity, receipt-backed inquiry/reassessment integration and durable journal recovery remain open. U-PER-SCALE-001 remains ACTIVE; no rule-choice blocker was found.


## Problems-first — owner-bound LastSeenLocation projection

### Gap and correction

The source matrix described both native location records as unsupported even though successful Spot evidence already survives strict Save/Load. However, the materialized `LastSeenLocation` answer is derived from the immutable owner ledger and was not checked after restore. Treating it as a separately persisted mutable record would duplicate history and risk exposing another observer's sample.

Extended the actual native Spot fresh-process case to compare the derived LastSeenLocation's owner, Being, exact position/time/boundary, source Action and observation identity against the restored observation row. The source-linked matrix now states that the immutable `BeingLocationObservation` is persisted, while `LastSeenLocation` is derived on demand from the one owner's records.

- `PYTHONPATH=.:../src:../examples:../../npc-generator ../.venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_spot_location_evidence_restores_with_owner_and_provenance test_persistence_capability_matrix -v` (from `tests/`) — **4 passed / 3.123s**.
- `git diff --check` — passed.

Objective-fact restoration and query coverage is committed as `c4ec5b4`. The LastSeenLocation regression plus matrix/report/TASKS update remains pending a scoped commit. Broader observer history/privacy combinations and complete production application cutover are still open; U-PER-SCALE-001 remains ACTIVE.


## Problems-first — fatigue and physiology matrix reconciliation

The matrix had contradictory prose: its implementation evidence already referenced restored Q/B values, per-boundary fatigue contexts, pending Run continuation, and selected physiology profile hashes, while some row statuses still said “no production native restore path.” Those conclusions understated existing tested support and obscured what remains a separate simulation-mechanics question.

Reconciled `FrozenFatigueFrame`, `FrozenFatigueView`, `PhysicalFatigueState`, `Exertion`, `PhysiologyDefinition`, `PhysiologyRegistry`, `ResolvedPhysiology`, and `universe_physical_fatigue_r4.Profile` against the existing pending-Run Save/Load test. The rows now distinguish exact current-state restore and time-qualified history from unproven activity/fatigue settlement behavior; no new mechanics are claimed.

- `PYTHONPATH=.:../src:../examples:../../npc-generator ../.venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_running_action_history_and_pending_continuation_in_fresh_process test_persistence_capability_matrix -v` (from `tests/`) — **4 passed / 2.462s**.
- `git diff --check` — passed.

The LastSeenLocation test/documentation increment is committed as `571bea5`. This fatigue/physiology matrix and report/TASKS reconciliation is pending scoped commit. U-PER-SCALE-001 remains ACTIVE; the matrix still contains many supported-state families and application/history/security gates requiring work.


## Problems-first — explicit native geometry and occlusion state

The closed type matrix included sphere, global-axis box, Cartesian/SpatialState and declarative opacity, but its generic “only exercised fields” rows did not cite a native Save/Load case. Geometry and visual opacity are separate represented facts; using geometry to infer occlusion would exceed the model.

Added `test_native_spatial_primitives_round_trip_and_continue`, which explicitly authors a radius-.37 Sphere, a 1.25 × 2.5 × 3.75 global-axis Box, and independent opacity .375. It performs a strict Save, loads in a fresh OS process, checks exact concrete geometry types and values, then continues through a native Delay and compares positions, RNG, Action identity and complete history digest with uninterrupted control. No sightline, cover, or optical rule is introduced.

- `PYTHONPATH=.:../src:../examples:../../npc-generator ../.venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_native_spatial_primitives_round_trip_and_continue test_persistence_capability_matrix -v` (from `tests/`) — **4 passed / 1.639s**.
- `git diff --check` — passed.

Fatigue/physiology matrix reconciliation is committed as `08dee4c`. The geometry test and matrix/report/TASKS update are pending scoped commit. LocalFrame continuation remains separately tested under `a42c44b`; U-PER-SCALE-001 remains ACTIVE.


## Problems-first — Being abilities, state flags, speed and posture

The live field catalog admits ability maps, per-Being state flags, movement speeds, and posture, but the native scenario coverage did not demonstrate those state families across a strict process boundary. A generic graph round-trip was insufficient evidence that legal, future-relevant state survives native rehydration and continuation.

Added `test_native_being_abilities_states_speed_and_posture_restore`. It authors explicit STR 13/FIT 9, integer ambulation speed 5, the configured `prone` state and consistent `lying` posture before the first committed boundary; the native historical `entity_at()` projection confirms the committed abilities/state/posture at boundaries 0 and 1; strict native Save is loaded in a fresh OS process; the child checks exact values and continues with ordinary native Delay. Uninterrupted and restored outcomes compare exact Encounter identity/time, complete ability/state/posture/speed projection, RNG, Action identity and native-history digest. A first fixture attempt used fractional speed 4.75; source normalization showed supported speeds are integer-valued, so the fixture was corrected to 5 without changing implementation or semantics.

- From `tests/`, `PYTHONPATH=.:../src:../examples ../.venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_native_being_abilities_states_speed_and_posture_restore test_native_persistence.NativePersistenceTests.test_running_action_history_and_pending_continuation_in_fresh_process test_persistence_capability_matrix -v` — **5 passed / 4.398s**.
- `git diff --check` — passed.

The field rows now cite the focused source and test. This verifies these configured Being fields for native restoration and continuation and checks abilities/state/posture through the supported historical EntityInspection query; it does not establish every legal combination or claim movement speed is a field of the narrower EntityInspection projection. The complete capability matrix, all-family historical read parity, durable journal recovery, compatibility/security breadth and production application Save/Load cutover remain open implementation work. U-PER-SCALE-001 remains ACTIVE with no rules or external blocker identified. The initial current-state test and matrix update are committed as `fe5c04c`; the historical query and mid-Run Skill/Practice reconciliation are committed as `c85968d`; the nonparticipant scenario and expanded registry matrix rows are under the current scoped audit and commit.

### Execution interval

- Start: `2026-11-17T22:55:59Z`.
- End: pending actual closeout timestamp.
- Elapsed: pending calculation from the recorded timestamps.

## Problems-first — Arena passive-perception history duplicated in native graph

The native `/2` graph still serialized the full `ArenaPerceptionLedger` history despite schema `/8` already retaining its observer-owned initial evidence and sparse committed updates. A direct equality test initially showed that `observer_knowledge_at(latest)` is not a substitute for the ledger's *current* projection: current rows refresh `boundary` and `time` on quiet commits even when no meaningful history row is appended. Reconstructing the current view from older history would therefore invent a stale timestamp. The graph now stores exact current evidence plus a compact ordered `(Entity ID, visibility boundary)` history index; evidence rows are reconstructed only from the authenticated history at their recorded boundary. Strict ledger validation checks every identity, order reference, observer owner, Entity, Awareness set and current physical projection. Pre-first-commit Saves retain their full ledger recipe, and older history schemas without observer facts keep the previous complete graph recipe.

The fresh-process test compares a full-ledger graph and history-backed compact graph made from the same current snapshot (**654,248 → 652,801 graph bytes, 1,447 B saved**), verifies the evidence nodes are absent from the compact graph, checks exact current/history ledger encoding and stable IDs, and continues with a native Delay. Its first Action boundary contains a real represented movement and committed observer evidence; the later Delay refreshes exact current evidence without adding a misleading historical row. Duplicate order references and dangling Entity references are refused. Compatibility covers a generated `/12` Arena Save and a reconstructed valid pre-compaction graph carrying history `/7`; the latter reports observer history unavailable instead of inferring it.

- From `tests/`, `PYTHONPATH=.:../src:../examples:../../npc-generator ../.venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_native_save_reconstructs_arena_perception_from_committed_history test_native_persistence.NativePersistenceTests.test_arena_observer_knowledge_appends_only_committed_evidence_changes test_native_persistence.NativePersistenceTests.test_generated_v12_arena_save_migrates_to_canonical_native_save test_native_persistence.NativePersistenceTests.test_generated_arena_first_choice_native_save_round_trips_and_continues test_persistence_capability_matrix -v` — **7 passed / 9.889s**. The dedicated `test_checkpoint_arena_perception` suite passed **7/7 / 2.453s**. The adjacent native history and checkpoint adapter gate passed **86/86 / 231.307s**. Earlier **4/4 / 8.636s** result predates the movement-evidence case and duplicate/dangling order checks.
- `/12` production Save/Load is unchanged. This closes one graph-duplication family only; remaining state/query-family coverage, durable journal recovery, broader compatibility/security and application cutover remain open. U-PER-SCALE-001 remains ACTIVE.
- The implementation, regression tests, matrix, TASKS and findings/report updates are awaiting explicit-path safety audit and a local commit. This compacting step does not close the remaining matrix or assignment acceptance criteria; no rules or external blocker is identified.

### Execution interval

- Start: `2026-11-17T22:55:59Z`.
- End: pending actual closeout timestamp.
- Elapsed: pending calculation from the recorded timestamps.


## Problems-first — preserve registered Universe entities outside an Encounter

The matrix requires native Saves to preserve Universe-level state without imposing an Arena participant allowlist. Existing scenarios contained weapons/scenery outside selected Encounter membership, but no focused fresh-process assertion proved a separate Being and standalone Object remain registered, identity-stable, and untouched while the selected Encounter continues.

Added `test_native_save_preserves_registered_nonparticipants_in_fresh_process`. It registers an INT 14, HP 23 Being at an authored position and a standalone Linen pillow at a separate position, leaves both outside the Encounter membership lists, strictly saves, and loads in a new OS process. The child confirms their IDs, exact shared definition identities, current properties, and continued nonparticipation, then runs an ordinary native Delay for a participant. The test compares the Universe/Encounter IDs, participant set, outsider state, RNG, Action receipt and complete native-history digest against uninterrupted execution.

- From `tests/`, `PYTHONPATH=.:../src:../examples ../.venv/bin/python -B -m unittest test_native_persistence.NativePersistenceTests.test_native_save_preserves_registered_nonparticipants_in_fresh_process -v` — **1 passed / 2.104s**; the corrected combined Being, Run/Practice, nonparticipant and matrix gate — **6 passed / 5.922s**. An initial combined matrix run rejected status descriptions that omitted the test-enforced Arena-schema classification phrase; the descriptions were corrected and the combined suite rerun green.
- `git diff --check` — passed.



## Problems-first — native history input limits and publication fault boundary

The prior native-history test set checked digest tampering, duplicate Action facts, reordered rows, existing-file refusal, and pre-link interruption, but did not explicitly prove the portable decoder's structural limits reject before publication or classify a directory-fsync failure after the atomic publication point. These are narrow safety gaps in the journal artifact API; they do not establish full production crash recovery.

Added `test_history_parser_enforces_duplicate_and_resource_limits_before_write` to reject duplicate JSON keys, node/depth/boundary/byte-limit violations, and to verify a size refusal creates neither destination nor temporary artifact. Added `test_directory_sync_failure_leaves_only_complete_published_history`: inject failure on the directory `fsync` after the no-overwrite link, assert the API reports failure after atomic publication, then strictly decode the complete destination and confirm the temporary name is gone. The append-before/after-native-publication tests remain unchanged.

The follow-up `test_history_refuses_resealed_duplicate_effects_and_forged_observer_owner` goes beyond digest mismatch: it reseals a duplicate Effect identity and a recipient owner change, then verifies native semantic validation rejects both against receipt and stable binding facts.

- From `tests/`, `.venv` interpreter via `../.venv/bin/python -m unittest test_native_history.NativeHistoryTests.test_history_parser_enforces_duplicate_and_resource_limits_before_write test_native_history.NativeHistoryTests.test_directory_sync_failure_leaves_only_complete_published_history` — **2 passed / 0.999s**.
- Focused integration: `test_native_history`, `test_persistence_capability_matrix`, and PersonalHistory strict fresh-process continuation — **40 passed / 26.355s**.
- The publication-fault case is an API-level injected directory-sync failure, not physical power-loss testing. `/12` production Save/Load remains untouched; durable append recovery and full adversarial/migration coverage remain open.
- Commits carrying the reader proof: `9649ce9`, `73cef99`, `a6ab6bf`; parser/publication tests are in `2ef00eb`; the resealed semantic attacks and resulting count updates are pending scoped audit and commit.

No incompatible rule or external blocker is identified. U-PER-SCALE-001 remains the sole ACTIVE program; production Save/Load cutover remains gated on the complete capability matrix, compatibility and application integration criteria.


## Problems-first — observer Effect and pending-recipient historical parity

Several `observer_proposals` rows in the source matrix still understated native support as “no production native restore path.” Those types include committed receipt Effects (`ObservationEffect`, `InterpretationEffect`, `BeliefAcquisitionEffect`, `LocationObservationEffect`, `AccountDeliveryEffect`, `TestimonyEffect`, Action/lifecycle outcomes), a derived `ObjectiveUse` view, and `FrozenLocationEvidence`, which is an interval-staging input rather than durable state. The missing evidence was exact composite historical inspection parity for these consequential observer receipts, including a pending native recipient restored before the Action commits.

Expanded the pending Spot/LocationEvidence fresh-process scenario so it saves while Spot is still accepted and the recipient ledger is empty, loads the same pending Action and ledger in an OS child, commits Spot, then continues with Delay. At boundaries 6 and 7, `NativeHistoryQuery.inspect_committed_at()` exactly matches `Encounter.inspect_committed()` in uninterrupted and restored processes. The legacy AskAboutPast/listener-account scenario now compares the full committed inspection at both the Action and subsequent quiet boundaries before and after strict fresh-process Load. The two independent Group-observer fixture also compares the complete committed inspection, covering distinct observer Effect and projection identities.

- `test_spot_location_evidence_restores_with_owner_and_provenance`, `test_completed_ask_about_past_and_listener_accounts_resume_with_binding`, and `test_two_observers_keep_distinct_group_evidence_in_native_history` — **3 passed / 8.096s**.
- The final combined gate (`test_native_history`, capability matrix, pending-Spot fresh-process persistence, and AskAboutPast/legacy listener fresh-process persistence) passed **41 tests / 31.094s**. The first integration attempt rejected changed matrix classification phrases; the status text was restored to the registry test's required “Arena snapshot schema” / “Outside Arena snapshot schema” wording, and the full gate then passed.
- These comparisons hash/compare the full normalized inspection projection; they do not infer missing observations or alter observer authorization. The matrix now marks `FrozenLocationEvidence` as transient staging input and cites native receipt/query evidence for committed observer families.
- These test, matrix, TASKS and report changes are pending scoped commit. Prior verification commits through `6790f44` are listed in TASKS; no rule or compatibility decision is needed. General matrix closure and application cutover remain open.


## Problems-first — repeated composite inspection revisited old history cuts

The new graph-free `inspect_committed_at()` returned exact projections but its first implementation rebuilt every prior TargetInspection row for each chronological request. The output itself contains cumulative history, but repeated traversal of already processed cuts was unnecessary. Added a per-query in-memory fold of Target histories and Disarm receipts: increasing reads visit only newly crossed logical cuts, reverse reads reset to the history origin, and every returned projection remains detached. This query-only cache does not change the portable schema or production `/12` path.

The shared scale verifier now compares the complete normalized `EncounterInspection` against the authoritative native inspector at every receipt cut, in addition to state, Target, Event/Effect, schedule, objective, recipient, RNG and projectile fields. The 204-boundary quiet-plus-Action regression confirms full inspection parity even for cuts represented by compact quiet spans. The 25-scenario native Action suite reran with the composite query check and passed.

| Scenario | Actions / cuts | Graph bytes | History bytes | Save bytes | Composite history query | Native reference inspection | Other timings | Result |
|---|---:|---:|---:|---:|---:|---:|---|---|
| Lawful Dagger Feint scale, fresh-process strict continuation | 64 / 129 | 4,859,640 → 978,538 (79.86% reduction) | 1,193,049 | 2,497,916 | 16.526s | 84.261s | simulation 60.436s; export 13.954s; child Load+continue 8.607s; peak RSS 211,337,216 platform units | exact per-cut inspection and same-Encounter continuation pass |
| Action boundary then 200 quiet intervals, per-cut source comparison | 1 / 204 | not measured | not measured | not measured | combined test 174.285s | included in combined test | setup and both inspections included; no fresh-process Save in this unit case | exact inspection parity at all 204 cuts |

The scale runner's `history_query_seconds` is the complete read-validation envelope, not query-only time; it was 106.568s in the 64-Action run and includes the native reference-inspection loop (84.261s) plus other fact checks. This avoids attributing native-source comparison cost to the history reader. The 25-Action suite passed **25/25 in 126.232s**. After enlarging the quiet-span case from 12 to 204 cuts, the current history/matrix/pending-Spot/legacy-AskAboutPast focused integration gate passed **41/41 in 196.733s**; the 204-cut case separately passed **1/1 in 174.285s**. The earlier 41-test timings (31.094/32.099s) were from before that extension. The isolated query portion of the 64-Action gate took 16.526s versus 84.261s for live native reference inspection, though full reference parity across hundreds of cuts remains a slow verification operation.

Still incomplete: the matrix contains many current persistent families without scenario-level continuation coverage; production `/12` Save/Load cutover, durable history journaling/recovery, full accepted legacy Save migration breadth, and general current-snapshot minimization remain open. This query improvement does not close U-PER-SCALE-001; no rules or external blocker has been identified.


## Problems-first — broad native integration regression after registry coverage

The recent matrix/test increments touched native graph interpretation and added registered nonparticipants; isolated passing cases were not sufficient to establish that the wider migration, privacy, atomicity, and Action continuation portfolio remained intact.

Ran the complete focused native persistence module after those changes. It exercises pending and completed Actions, current native Save/load, strict outer integrity and duplicate-key refusal, receipt/Target/Entity compaction and source-seal refusals, `/1`–`/12` history/graph migration, multiple Encounter/observer roots, history/evidence ownership, legacy Arena `/10`–`/12` coexistence, Groups/ReproductionGroups, projectiles, simultaneous combat, native Save file fault recovery, the new Being history and nonparticipant cases, and the source-linked matrix.

- From `tests/`, `PYTHONPATH=.:../src:../examples ../.venv/bin/python -B -m unittest test_native_persistence -v` — **64 passed / 227.530s**.
- The pyenv shim printed `cannot rehash` because its global shims path is not writable; the repository `.venv` interpreter continued and all tests completed successfully.
- The previously verified adjacent combined gate (Being, Run/Practice, nonparticipant, matrix): **6 passed / 5.922s**.

This verifies the changed code/tests against the native persistence portfolio and known legacy inputs at that revision. Its statement that observer-heavy projections remained graph-backed is superseded by recipient recipe `/2` and commit `1271410` above. History API parity, durable journaling, full corruption/security and cross-version migration breadth, and ordinary application Save/Load cutover remain open. Production cutover remains correctly sequenced after the general native gate. No user rule or external blocker has been identified; U-PER-SCALE-001 stays ACTIVE.

## Problems-first — delayed projectile branches lacked full inspection parity

The native query already exposed projectile-state receipts, and separate Throw tests proved fresh-process hit/miss/movement/simultaneous outcomes. They did not compare the *whole* historical `EncounterInspection` against native authoritative receipts for those delayed branches. This left a concrete consumer-parity gap despite field-level projectile assertions.

Added a shared test assertion and applied it to the shield-protection hit, unresolved miss, target-moved flight, and two-projectile simultaneous-arrival continuations. Parent and strict child-process paths now compare `NativeHistoryQuery.inspect_committed_at(boundary)` with `Encounter.inspect_committed(boundary)` at every committed cut, while retaining their existing projectile state, damage, target, RNG and history checks. The strict child scripts independently perform the same comparison. No resolver, Save schema or `/12` behavior changed.

- From `tests/`, `PYTHONPATH=tests:src:examples:../npc-generator ../.venv/bin/python -B -m unittest -v test_native_persistence.NativePersistenceTests.test_projectile_shield_interception_continues_after_native_fresh_process_load test_native_persistence.NativePersistenceTests.test_missed_projectile_continues_with_native_unresolved_destination test_native_persistence.NativePersistenceTests.test_target_movement_during_projectile_flight_restores_natively test_native_persistence.NativePersistenceTests.test_simultaneous_projectile_arrivals_restore_as_one_native_boundary` — **4 passed / 20.582s**. An initial test-harness edit placed one assertion at the wrong indentation inside an embedded child script; the focused rerun after correction passed all four cases.
- Matrix rows for `ThrowAction` and `CommittedBoundaryRecord` now cite these composite-query results. Other Action/state-family rows, legacy breadth, journal recovery and application cutover remain open.
- Test and documentation changes are pending scoped safety audit and commit. No adopted-rule or external blocker is identified; U-PER-SCALE-001 remains ACTIVE.

### Execution interval

- Start: `2026-11-17T22:55:59Z`.
- End: pending actual closeout timestamp.
- Elapsed: pending calculation from the recorded timestamps.


### Post-commit integration verification — Arena ledger compaction

After commit `704e393327a92abc114ccf27d5e1e96249df1b8c`, the complete `test_native_persistence` module passed **69/69 in 253.683s**, including accepted `/10`–`/12` reads, native history upgrades, pending and settled continuation, observer ownership, projectile/simultaneous combat, file-write fault recovery, strict integrity, and the new Arena compaction case. The focused Arena/legacy/matrix gate passed **7/7 in 9.889s**; `test_checkpoint_arena_perception` passed **7/7 in 2.453s**; adjacent `test_native_history` and `test_checkpoint_adapters` passed **86/86 in 231.307s**. This validates the code commit and keeps `/12` production behavior unchanged. It does not establish the full capability matrix or application cutover. U-PER-SCALE-001 remains ACTIVE.


## Problems-first — ordinary Arena Save now consumes native persistence

The native snapshot/history API had not been selected by the generated Arena's normal HTTP Save button, leaving the application disconnected from the new portable native artifact. The endpoint now uses native `export_save()` for supported transactional encounters and emits a canonical, integrity-checked Arena-session wrapper containing the native Save plus only the Arena metadata needed to rebuild map/profile/controller state. Every legacy-mode session keeps emitting the established `/12` archive. Strict legacy readers for `/10`–`/12` remain available, and the old direct `/12` compatibility method remains. The envelope requires an exact schema/field set and canonical digest; it bounds decompression, rejects trailing zlib members/data, validates the session record before calling native strict Load, then atomically installs the fully validated session.

The focused route regression creates and accepts the first native Run Choice, saves that pending Choice through `/api/generated/save`, and requires a fresh OS process to load and emit identical bytes. It then commits the Run at boundary 1, Saves through the same endpoint again, and proves a new OS process restores the resolved Action/history and emits identical bytes; `/api/generated/load` accepts both pending and committed artifacts. It additionally verifies malformed session metadata never reaches native Load, the decompression limit is enforced before Load, compressed trailing data is rejected, a legacy `/10` session still yields `/12`, and Arena-vs-Arena strategies round-trip. The existing fresh-process Feint regression also had a stale fixture that decoded the ZIP `/12` Save as UTF-8. Its subprocess now base64-transports exact bytes and decodes before Load; behavior assertions are unchanged.

- After stable native graph node ordering, `test_native_persistence`, `test_native_draw_persistence`, and `test_persistence_capability_matrix`: **97 passed / 370.306s**.
- `test_generated_arena_browser.TestGeneratedArenaBrowser.test_http_save_and_load_use_binary_portable_file_and_atomic_replacement`: **1 passed / 7.897s** after covering pending and committed Save/Load cuts, inspection-history parity, and accepted `/10` fallback.
- Full `test_generated_arena_browser`: **78 tests, 2 failures / 142.660s**. `test_actual_shipped_javascript_runs_fresh_authored_draw_scenario` and `test_passive_refresh_refuses_later_unmodeled_geometry_without_partial_publication` both reproduce on a clean detached checkout at `d148caa8977c672588977417dc2548bbc60a95b7`, before this integration. The previous stale Feint binary-fixture failure is repaired. No new browser suite failure is attributable to these persistence changes.
- The `/12` production persistence module had passed **22/22 / 405.599s** during this continuation before the adapter work; the strict legacy route remains covered by the full generated-browser run. No `/12` reader/writer code was changed. The executed manual UI smoke did not reach Save/Load: a Delay before native initiation was correctly refused, and the browser tool expired while verifying the download. It is not claimed as a passing UI check.

Native consumer integration is committed as `820c4d1adfb2a8293e829e649e4180cba1ec89fe`; the expanded committed-boundary history-query assertion and all-legacy `/12` fallback are pending the next scoped commit. The assignment's all-or-nothing gate remains unmet. The matrix still identifies supported Action, Choice, transient-effect, scheduler, Event, history and observer families without complete scenario/query evidence; durable committed-history recovery, broad accepted-file adversarial/compatibility coverage and final cutover UI verification remain open. No authoritative rules question or external blocker has been found. Keep U-PER-SCALE-001 sole ACTIVE; do not start shields, ranged Actions, U-ACT-GATE-001 or U-NET-001.

## Problems-first — post-Action quiet recording and built-in definition breadth

The recorder's post-Save append path formerly re-authenticated all earlier Action/Target receipts at every later boundary. That full-chain inspection is correct for the public standalone append contract, but it made a long quiet tail after an Action burst unnecessarily expensive. The internal recorder now authenticates its cached prefix digest and exact new `PublishedInterval`, verifies Action/lifecycle/effect links and the Target anchor/fingerprint before each append, then performs full-chain validation at every Action boundary and every 32nd quiet boundary. Save export and Load remain full strict validation. Cache changes commit transactionally only after append and scheduled validation succeed; a changed cached prefix is rejected before append/export. These checks retain rollback and publication semantics.

The lawful native Feint profile resolved 64 Actions (128 committed cuts), saved, continued through 200 quiet cuts to t=328, then committed Delay at t=329. It compared all 329 committed cuts with authoritative native receipts and loaded in separate OS processes at both the post-Action and post-quiet cuts. Same Encounter IDs, Action identities, state, time, RNG and history matched uninterrupted control. Quiet-tail measurements:

| Registered Beings | Graph before/after | History before/after | Save before/after | Growth | 329-cut query | Export | Post-quiet child Load + continuation | Peak RSS (platform units) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 978,538 / 978,538 B | 1,193,049 / 1,194,913 B | 2,497,916 / 2,499,780 B | 1,864 B | 101.95 s | 15.43 s | 14.159 s | 278,151,168 |
| 20 | 1,220,621 / 1,220,621 B | 1,193,049 / 1,194,913 B | 2,820,692 / 2,822,556 B | 1,864 B | 109.28 s | 15.611 s | 18.305 s | 242,270,208 |
| 200 | 3,639,614 / 3,639,614 B | 1,193,049 / 1,194,913 B | 6,046,016 / 6,047,880 B | 1,864 B | 96.414 s | 19.763 s | 13.126 s | 266,764,288 |

Fresh-process continuation from the post-Action Save crossed the 200 quiet boundaries and committed Delay in 202.72 / 196.124 / 197.667 seconds at 2 / 20 / 200 registered Beings; each matched uninterrupted control. Scenario times were 181.328 / 185.06 seconds for quiet continuation and 69.241 / 72.55 seconds for the 64-Action setup at 20 / 200; the 2-Being run recorded 182.542 and 70.445 seconds. The graph is registry-dependent but constant across the quiet interval; history and total Save each add exactly 1,864 bytes of committed time/receipt facts for the 200 quiet boundaries across all registry sizes.

The source-linked Universe/Library row now also has an exhaustive built-in entity-definition case. `test_native_save_round_trips_every_built_in_entity_definition_family` places all 27 current Being, 27 Object, 141 Weapon and 20 Armor definitions in one Arena-independent root (215 instances; Human alone participates), then strict-loads in a fresh process with `src/config` reads blocked. Each identity, class, name and shared Library definition identity matches; canonical Save→Load→Save is byte-identical. **1 passed / 1.770s.** This closes only the checked-in definitions inventory; custom definitions and all relationship/field combinations remain open.

Committed integration evidence through `242fa7b390bf3c14f4b83da712e276c746d6538d` is the native persistence/Draw/scenario/matrix gate **100 passed / 383.314s**, native-history plus HTTP Save/Load **38 passed / 114.325s**, and five focused fast-append/mutated-prefix/`/1` migration/`/4` migration/pending-Disarm regressions **5 passed / 22.529s**. The new definition-family test then passed **1 / 1.770s**. A served Chrome session generated seed 14 and displayed the native-archive download confirmation after Save. Direct browser UI Load did not complete; the focused HTTP route does prove pending and committed Save/Load in fresh OS processes with exact bytes.

This increment does not close the program: custom/caller-defined state, family-complete native historical-query parity, remaining pending/multi-Encounter/observer combinations, full adversarial/compatibility breadth remains acceptance work; the revised assignment requires atomic Save publication and rollback isolation, not a separate crash-recovery journal. No rules or external blocker is established; U-PER-SCALE-001 remains ACTIVE. The working tree retains the five unrelated staged archive changes and untracked user saves; no push occurred.

### Current execution interval

- Start: `2026-11-18T08:23:11Z`.
- End: pending actual closeout timestamp.
- Elapsed: pending calculation from the recorded timestamps.
