# U-ACT-FULL-002 engineering report

**Status:** ACTIVE — ChatGPT review and acceptance are still required. Both allocation semantics are now adopted and implemented for a single shield. Multiple-shield overload allocation remains bounded and fail-closed. The wider Action Completeness Gate remains FUTURE/unpassed.

## Execution interval

- Start: **2026-11-15T13:06:40-08:00** (captured when this execution began).
- End: **2026-11-15T14:17:59-08:00** (captured immediately before final closeout).
- Elapsed: **PT1H11M19S**.

### Allocation visibility decision interval

- Start: **2026-11-15T14:20:54-08:00** (captured when the user supplied the prior-round-observable allocation ruling).
- End: **2026-11-15T14:27:12-08:00** (captured immediately before this documentation closeout).
- Elapsed: **PT6M18S**.
- Result: Recorded the user's “prior-round observable” visibility choice and kept overload fail-closed while the no-cost question was presented.

### Allocation implementation interval

- Start: **2026-11-15T14:28:02-08:00** (captured at the start of implementation after the no-cost ruling).
- End: **2026-11-15T14:56:06-08:00** (captured immediately before this closeout).
- Elapsed: **PT28M04S**.
- Result: Added persisted defender allocation, observer-filtered Arena controls, strict restoration, focused simultaneous coverage, and report/task reconciliation. See exact tests and commits below.

## Scope and protected state

- U-ACT-FULL-001 was accepted DONE (bounded), archived with Git-aware moves, and reconciled before this assignment. Its 52-row source-linked Action coverage matrix remains intact; no Action is marked FULL.
- `U-ACT-FULL-002` was verified unused before registration and is the sole ACTIVE implementation program. U-ACT-GATE-001 remains FUTURE/unpassed; U-NET-001 remains DEFERRED.
- Both Arena combat modes, observer privacy, the frozen Playtest Edition, unrelated staged historical archive changes, and `docs/assignments/universe-arena.json` were preserved. No push or history rewrite was performed.
- The authored Arena profile `tests/fixtures/arena/uact-full-002-one-shield.json` adds one ordinary Small shield to the generated ground loadout; it does not alter body geometry, weapon profiles, attack outcomes, or native state after publication.

## Acceptance matrix

| Requirement | Status | Verification / bounded result |
|---|---|---|
| Archive accepted U-ACT-FULL-001, repair references, verify unique ID and preserve program status | MET | Maintained archived assignment/report links; this assignment is the sole ACTIVE entry. Gate and multiplayer statuses remain FUTURE and DEFERRED. |
| Passive interception and damage chain | MET for represented ordinary Shields | Native melee and targeted Throw use adopted `d10 ≤ shield size + 4`, stop at most shield size, pass the remainder to armor/Being, and apply only ordinary damage above size to shield HP. Miss, failed interception, and successful interception remain distinct. |
| Critical ordinary/extra components | MET | Native critical regression checks the ordinary component through shield and armor, extra critical damage bypassing both, and no extra durability loss. |
| Common-snapshot simultaneous protection and durability | MET | Two attacks share the pre-action shield; durability accumulates after both evaluations. A shield destroyed by the combined batch still protects in that boundary and is absent from later protection snapshots. |
| Passive capacity and defender pre-outcome allocation | MET for a single shield; multi-shield case bounded | User adopted prior-round-only visibility and no Action time/resource cost. A native Encounter record persists allocation to a subset of prior-round-observed pending strikes; the Arena presents only opaque handles from current observer evidence. For overload, selected attacks receive shield protection; unselected or same-round-hidden attacks do not. Overload with multiple shields still fails closed. |
| Active Block interaction | MET for represented native shield/timing cases | Focused native tests verify shield-size timing, attack penalty, adopted stopping bonus, and refusal for wrong timing or missing shield; existing Block and maneuver restrictions remain intact. |
| Real served-Chrome Don → combat → Remove contrast | PARTIAL | Chrome used seed `20261115`, Player vs Arena, 10,000 starting XP, 5×5 map, `attack_only`, equipped loadout plus the authored one-Small-shield ground profile. Tobe reached shield hex `(2,4)` by native Walk, picked up the same named Small shield, and selected native Don for left hand at t=5. Don succeeded at t=31; an opposing native Thrust resolved normal at t=33. The player-owned Chrome sheet showed 15 HP at t=50 with the Small shield held in the left hand. Remove Shield was accepted at t=50 and succeeded at t=60; the next opposing Thrust resolved normal at t=61. At t=97 the own-Being sheet showed 0 HP and the same Small shield carried but not readied. The player-owned sheet exposes Being HP and hand/custody state, but the UI does not expose shield HP, native Object ID, interception roll, or event-effect receipt; therefore the browser path proves real actions and the contrast, while exact interception is separately verified by native generated-Arena tests. No hidden roll is inferred from the UI result label. |
| Pending/completed strict fresh-process persistence and deterministic continuation | MET for represented shield states | Fresh OS-process regression now restores an exact pending allocation record alongside the generated-Arena strike and shield identity, then commits the hit/effect at t=5. A separate Don/Remove generated-Arena test restores pending Don, completed Don, and pending Remove and verifies same Object custody/hand state at continuation. |
| Seed-14 Player-vs-Arena and Arena-vs-Arena, observer privacy, Search/Listen regressions | MET | Existing three-test cohort remained green; see exact command below. These protections did not change. |
| 52-row matrix, TASKS, local audited commits and report | MET | Matrix, canonical task state, implementation and persistence are verified and committed; actual hashes and final repository state are recorded below. Assignment remains ACTIVE pending ChatGPT review. |

## Rules and implementation

Controlling sources are the [adopted r61 Shields](../encounters/encounters-working-draft-adopted-r61.md#shields), [Strike](../encounters/encounters-working-draft-adopted-r61.md#strike-swing-or-thrust), [critical/fatal hits](../encounters/encounters-working-draft-adopted-r61.md#threat-critical-hit-fatal-hit), [Block](../encounters/encounters-working-draft-adopted-r61.md#block), and [one-second simultaneous resolution](../encounters/encounters-working-draft-adopted-r61.md#one-second-action-and-defense-resolution); issue resolutions [ES-002](../encounters/encounters-rule-issues-r60.md#es-002--passive-shield-interception-d10-versus-d6), [ES-003](../encounters/encounters-rule-issues-r60.md#es-003--passive-shield-absorption-and-shield-damage-have-different-formulas), and [ES-015](../encounters/encounters-rule-issues-r60.md#es-015--critical-hits-shields-armor-and-universal-state-commitment). Revision 70 remains controlling where applicable; withdrawn revision 66 is not authoritative.

`Encounter.allocate_passive_shield_coverage` stores a no-time, no-resource defender choice in strict Encounter state. It accepts only a currently held living shield and unique native MeleeStrike identities that target the bearer, resolve on one future boundary, began before the preceding round, and target an attacker the bearer is aware of. The generated Arena offers opaque selection handles only for attacks visible in the player-owned current perception ledger; the HTTP route accepts no raw Action or Being IDs. The evaluator captures allocation data in the common snapshot, validates capacity and eligible identities before any rolls, applies passive protection only to selected attacks in an overloaded single-shield batch, and leaves unselected attacks unprotected without consuming shield-selection RNG. Strict checkpoint reconstruction restores the allocation record. Multiple-shield overload is still refused before rolls.

`src/action_evaluation.py` snapshots only positive-HP borne shields, computes ordinary shield interception/transfer/durability, and keeps critical extra damage outside equipment protection. `src/action_settlement.py` validates adopted shield durability loss. Atomic publication commits grouped same-boundary object and Being effects. A shield at zero HP is useless in later snapshots; overkill can leave its stored HP below zero, preserving original object custody/identity. Block remains a separately timed Action through the native defense evaluator.

### Exact native receipts

- Deterministic targeted Throw hit (`test_native_throw_arena.NativeThrowTests.test_thrown_weapon_hit_applies_common_snapshot_shield_and_armor_effects`, RNG seed 116): ordinary incoming damage **3**; size-2 Small shield intercepted and passed **1** to armor; shield durability loss was **1**; armor received 1 and stopped it. The test asserts these exact values and the native shield/armor effect provenance.
- Seed-14 generated Arena pending-strike fresh-process continuation (`test_generated_arena_browser.TestGeneratedArenaBrowser.test_pending_passive_shield_hit_restores_and_commits_in_fresh_process`): after fresh OS-process reload, a normal hit had ordinary incoming damage **2**; the size-2 shield intercepted it, passed **0**, and lost **0 HP**. The exact same shield ID survived reload; Action boundary ended at t=5. This is the shield-effect persistence receipt, distinct from the actual Chrome walkthrough.
- Critical regression: regular component 4 against size-2 shield; shield intercepts and takes 2 durability, 2 goes to armor, and the additional critical component bypasses armor/shield. The test asserts the effect amounts.
- Same-boundary destruction: two size-2-shield interceptions each apply 2 HP loss from incoming 4, even when the first cumulative commit crosses zero. Both receive the shared pre-action protection; a later-boundary attack receives no shield ProtectionEffect.
- Three simultaneous incoming attacks against shield size 2 with two prior-round-observed selections protect exactly those two; the unselected successful attack receives no shield effect. Repeating with reversed allocation choice list is unnecessary: the declared schedule determines stable action evaluation order, while the selection itself is an explicit action-ID subset and does not depend on rolls.
- The generated Arena HTTP control accepts one current opaque incoming-strike handle, preserves Encounter time and Action reservations, and records the exact target shield/action IDs natively. The route does not expose same-second hidden Actions.
- The generated Arena pending-hit test now saves at t=2 with allocation `(boundary=5, bearer, shield, (strike,))`; a fresh OS process verifies the exact record after load and commits the protected hit at t=5.

## Exact verification

All commands used `-B`, `PYTHONDONTWRITEBYTECODE=1`, and `PYTHONNOUSERSITE=1`; no full repository suite is claimed.

1. Shield native/effect cohort — **13 passed, 5.810s**:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=src:tests:examples .venv/bin/python -B -m unittest test_native_throw_arena.NativeThrowTests.test_thrown_weapon_hit_applies_common_snapshot_shield_and_armor_effects test_generated_arena_browser.TestGeneratedArenaBrowser.test_pending_passive_shield_hit_restores_and_commits_in_fresh_process test_action_evaluation.TestActionEvaluation.test_critical_extra_die_bypasses_protection test_action_evaluation.TestActionEvaluation.test_shield_interception_full_impact_and_armor_followthrough test_action_evaluation.TestActionEvaluation.test_shield_miss_passes_full_damage test_action_evaluation.TestActionEvaluation.test_shield_and_critical_rng_match_live test_action_evaluation.TestActionEvaluation.test_two_shield_impacts_share_snapshot_no_degradation test_action_evaluation.TestActionEvaluation.test_passive_shield_over_capacity_refuses_before_any_attack_roll test_action_evaluation.TestActionEvaluation.test_native_block_applies_hit_penalty_and_adopted_shield_stopping_bonus test_action_evaluation.TestActionEvaluation.test_native_block_refuses_wrong_timing_and_unshielded_actor test_action_settlement.TestActionSettlement.test_passive_shield_impacts_accumulate_below_zero test_action_settlement.TestActionSettlement.test_zero_hp_shield_is_useless_and_not_degraded test_atomic_publication.TestAtomicCombatPublication.test_passive_shield_commits_below_zero_and_retains_original_storage
```

2. Seed-14 both-mode, Search/Listen and privacy cohort — **3 passed, 23.562s**:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=src:tests:examples .venv/bin/python -B -m unittest test_generated_arena_browser.TestGeneratedArenaBrowser.test_seeded_two_sided_browser_combat_hit_and_fresh_process_continuation test_generated_arena_browser.TestGeneratedArenaBrowser.test_authored_search_and_listen_http_controls_preserve_target_privacy test_arena_vs_arena.TestArenaVsArena.test_two_controllers_native_consequence_and_fresh_process_continuation
```

3. Native shield Don/Remove pending/completed fresh-process continuity — **1 passed, 42.384s**:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=src:tests .venv/bin/python -B -m unittest test_arena_ready_weapon.TestArenaReadyWeapon.test_shield_don_remove_native_browser_choices_and_pending_fresh_process_restore
```

4. Allocation, generated HTTP control, persistence, critical/interception, durability, and atomic regressions — **10 passed, 7.957s**. Command:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=src:tests:examples .venv/bin/python -B -m unittest test_generated_arena_browser.TestGeneratedArenaBrowser.test_observer_safe_zero_cost_shield_allocation_control test_generated_arena_browser.TestGeneratedArenaBrowser.test_pending_passive_shield_hit_restores_and_commits_in_fresh_process test_action_evaluation.TestActionEvaluation.test_prior_round_shield_allocation_covers_only_selected_simultaneous_attacks test_action_evaluation.TestActionEvaluation.test_passive_shield_over_capacity_refuses_before_any_attack_roll test_checkpoint_adapters.TestNativeCombatClosureAdapters.test_negative_armor_and_passive_shield_remain_objects test_action_evaluation.TestActionEvaluation.test_two_shield_impacts_share_snapshot_no_degradation test_action_settlement.TestActionSettlement.test_passive_shield_impacts_accumulate_below_zero test_action_evaluation.TestActionEvaluation.test_critical_extra_die_bypasses_protection test_action_evaluation.TestActionEvaluation.test_shield_interception_full_impact_and_armor_followthrough test_action_evaluation.TestActionEvaluation.test_shield_miss_passes_full_damage
```

5. Seed-14 PvA combat + fresh process — **1 passed, 6.808s**; AvA combat + fresh process — **1 passed, 11.489s**; and Don/Remove continuation — **1 passed, 48.874s**, all using `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=src:tests:examples .venv/bin/python -B -m unittest` and the corresponding test names above. The Don/Remove invocation completed after one 30-second wait and one 16.831-second poll; total unittest time was 48.874s.

6. A combined 51-test checkpoint-adapter diagnostic initially reported **3 failures and 2 errors**. One error, `TestNativeCombatClosureAdapters.test_all_designated_defenses_are_preserved`, exposed the `MeleeStrike` field allowlist missing its already-declared `feint_source_action_id` and `shield_hand` fields. The allowlist was corrected narrowly; that test and `TestNativeCombatClosureAdapters.test_negative_armor_and_passive_shield_remain_objects` then passed together (**2 passed, 5.196s**). The four other diagnostic cases were rerun directly (**1 error, 3 failures, 0.986s**): `test_container_cycles_and_shared_entity_state_refuse` recurses on the deliberate cyclic tag fixture; `test_hex_facing_requires_unknown_or_canonical_integer`, `test_movement_activated_arena_remains_outside_bounded_checkpoint`, and `test_unstarted_arena_opt_in_is_outside_the_initiated_checkpoint_path` retain their stated expectation mismatches. They do not exercise passive shield allocation and were not weakened or changed. Their pre-existing status was not independently established in this execution. No full repository suite was run.

The actual served Chrome session was opened on the current `examples/arena_web.py` build at `http://127.0.0.1:51917/`; the new allocation HTTP route is covered by the focused HTTP-handler test. The previously recorded real Chrome Don → combat → Remove walkthrough remains the assignment’s served-browser interaction evidence. This follow-up did not repeat that walkthrough or claim Chrome screenshot/receipt access to hidden shield HP or rolls. A pre-existing `src/location.py` syntax error and legacy fixture incompatibilities previously documented in TASKS were not touched by this shield increment.

## Adopted allocation rulings and bounded case

The user adopted both missing allocation semantics during this assignment:

- **Visibility:** prior-round observable. The bearer can select only pending incoming Actions already perceived before the simultaneous resolution round. Same-round unseen Actions remain hidden and unselectable.
- **Cost:** no Action time or Action-capacity resource. The selection is a persisted choice input to passive shield coverage, not Block and not a separately timed Action.

Both are implemented for one actually held shield. The generated Arena issues opaque attack handles from the player-owned current perception ledger; Encounter validates native pending Action identities and stores the allocation; evaluation applies only the chosen subset when that shield's size would otherwise be exceeded. The existing fail-closed guard remains for overloads involving multiple shields because the adopted size/capacity text and current UI/data model do not yet provide a complete multi-shield distribution mechanism. This is a bounded implementation limit, not a remaining user decision. Same-boundary actions continue to evaluate from the common snapshot; no rolls determine allocation.

## Repository and closeout

- Acceptance remains **ACTIVE**, not DONE, pending ChatGPT review. U-ACT-GATE-001 remains FUTURE/unpassed.
- `docs/encounters/action-implementation-coverage.md` holds the variant-level evidence and explicit multi-shield limit; `TASKS.md` retains the sole ACTIVE program and remaining rows.
- Earlier verified commits remain: `037e03914753ab5e42d53da8278e7dc33d2cba01` (passive interception/durability), `50373ef992b199897faf81ec7073d198dfae329f` (initial coverage/report), `7ebc25058361cf531c64f56e15992059bfe14be6`, `380bb0f6115580ec1896ec15a0db3d9b84fc04e3`, and `35a5540aebb8afc40138cb2ebf818c518d3eea59` (prior report/timestamp closeouts).
- Allocation ruling/status documentation commit: `6599c0b2314f29b1d2fbeb4d0b9200ad0cac16d3` (`Record shield allocation visibility ruling`).
- Implementation commit: `d285ac34fa56bda4f2c9ccfd73c9818ebe438b24` (`Implement persisted passive shield allocation`). It contains only the native allocation/evaluation/snapshot/checkpoint code, generated Arena route/UI, and focused tests. `git diff --cached --check` passed and the staged publication-safety audit reported `files=14 findings=0 result=PASS`; `git commit --only` excluded preserved historical archive paths.
- Checkpoint schema follow-up: `dcc710eb4ccea79be4d44ff31d755ccdb7b847ef` (`Allow native strike persistence fields`). It admits only the already-native Feint-source and shield-hand fields; its two directly affected checkpoint regressions passed. The staged safety audit reported `files=7 findings=0 result=PASS` and the commit excluded preserved archive paths.
- The final report closeout records the documentation commit, exact final HEAD and execution interval. The scoped documentation commit is preceded by `git diff --cached --check` and the staged publication-safety audit.
- Preserved user index entries remain staged: deletions of `docs/assignments/U-CAP-002.md`, `docs/assignments/U-CAP-003.md`, `docs/reports/U-CAP-002-report.md`, `docs/reports/U-CAP-003-report.md`, and rename `docs/reports/U-THROW-001-rule-sync-proposal.patch` → `docs/reports/archive/U-THROW-001-rule-sync-proposal.patch`. Preserved untracked `docs/assignments/universe-arena.json` remains untouched. No unrelated task files are changed.
- No push is authorized or planned. The final interval and exact repository state will be captured at audited closeout.
