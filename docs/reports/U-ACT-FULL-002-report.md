# U-ACT-FULL-002 engineering report

**Status:** ACTIVE — ChatGPT review and acceptance are still required. The passive-shield overload allocation edge below needs a narrow rule decision; the wider Action Completeness Gate remains FUTURE/unpassed.

## Execution interval

- Start: **2026-11-15T13:06:40-08:00** (captured when this execution began).
- End: pending; capture immediately before closeout.
- Elapsed: pending; calculate from the captured interval.

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
| Passive capacity and defender pre-outcome allocation | BLOCKED pending a rule decision | Same-boundary overload is rejected before rolls, RNG, time, or state mutation. The rule says the bearer selects excess attacks; the Action-information rule says same-second opponent Action choices are not knowable and defenses use only perceived information. No adopted text defines what attack identities can be presented to the defender or when this allocation occurs. Exact options are below. |
| Active Block interaction | MET for represented native shield/timing cases | Focused native tests verify shield-size timing, attack penalty, adopted stopping bonus, and refusal for wrong timing or missing shield; existing Block and maneuver restrictions remain intact. |
| Real served-Chrome Don → combat → Remove contrast | PARTIAL | Chrome used seed `20261115`, Player vs Arena, 10,000 starting XP, 5×5 map, `attack_only`, equipped loadout plus the authored one-Small-shield ground profile. Tobe reached shield hex `(2,4)` by native Walk, picked up the same named Small shield, and selected native Don for left hand at t=5. Don succeeded at t=31; an opposing native Thrust resolved normal at t=33. The player-owned Chrome sheet showed 15 HP at t=50 with the Small shield held in the left hand. Remove Shield was accepted at t=50 and succeeded at t=60; the next opposing Thrust resolved normal at t=61. At t=97 the own-Being sheet showed 0 HP and the same Small shield carried but not readied. The player-owned sheet exposes Being HP and hand/custody state, but the UI does not expose shield HP, native Object ID, interception roll, or event-effect receipt; therefore the browser path proves real actions and the contrast, while exact interception is separately verified by native generated-Arena tests. No hidden roll is inferred from the UI result label. |
| Pending/completed strict fresh-process persistence and deterministic continuation | MET for supported states | Fresh OS-process regression restores a pending generated-Arena strike with the same shield identity and commits its hit/effect; a separate Don/Remove native generated-Arena test restores pending Don, completed Don, and pending Remove and verifies same Object custody/hand state at continuation. Allocation checkpoints remain inapplicable until the blocked Choice exists. |
| Seed-14 Player-vs-Arena and Arena-vs-Arena, observer privacy, Search/Listen regressions | MET | Existing three-test cohort remained green; see exact command below. These protections did not change. |
| 52-row matrix, TASKS, local audited commits and report | PARTIAL | Matrix and canonical task state updated. Local scoped commits and actual hashes are pending this report closeout; assignment remains ACTIVE. |

## Rules and implementation

Controlling sources are the [adopted r61 Shields](../encounters/encounters-working-draft-adopted-r61.md#shields), [Strike](../encounters/encounters-working-draft-adopted-r61.md#strike-swing-or-thrust), [critical/fatal hits](../encounters/encounters-working-draft-adopted-r61.md#threat-critical-hit-fatal-hit), [Block](../encounters/encounters-working-draft-adopted-r61.md#block), and [one-second simultaneous resolution](../encounters/encounters-working-draft-adopted-r61.md#one-second-action-and-defense-resolution); issue resolutions [ES-002](../encounters/encounters-rule-issues-r60.md#es-002--passive-shield-interception-d10-versus-d6), [ES-003](../encounters/encounters-rule-issues-r60.md#es-003--passive-shield-absorption-and-shield-damage-have-different-formulas), and [ES-015](../encounters/encounters-rule-issues-r60.md#es-015--critical-hits-shields-armor-and-universal-state-commitment). Revision 70 remains controlling where applicable; withdrawn revision 66 is not authoritative.

`src/action_evaluation.py` now snapshots only positive-HP borne shields, computes ordinary shield interception/transfer/durability, keeps critical extra damage outside equipment protection, and safely refuses same-boundary capacity overflow before outcome or RNG. `src/action_settlement.py` validates adopted shield durability loss. Atomic publication commits grouped same-boundary object and Being effects. A shield at zero HP is useless in later snapshots; overkill can leave its stored HP below zero, preserving original object custody/identity. Block continues through the native defense evaluator.

### Exact native receipts

- Deterministic targeted Throw hit (`test_native_throw_arena.NativeThrowTests.test_thrown_weapon_hit_applies_common_snapshot_shield_and_armor_effects`, RNG seed 116): ordinary incoming damage **3**; size-2 Small shield intercepted and passed **1** to armor; shield durability loss was **1**; armor received 1 and stopped it. The test asserts these exact values and the native shield/armor effect provenance.
- Seed-14 generated Arena pending-strike fresh-process continuation (`test_generated_arena_browser.TestGeneratedArenaBrowser.test_pending_passive_shield_hit_restores_and_commits_in_fresh_process`): after fresh OS-process reload, a normal hit had ordinary incoming damage **2**; the size-2 shield intercepted it, passed **0**, and lost **0 HP**. The exact same shield ID survived reload; Action boundary ended at t=5. This is the shield-effect persistence receipt, distinct from the actual Chrome walkthrough.
- Critical regression: regular component 4 against size-2 shield; shield intercepts and takes 2 durability, 2 goes to armor, and the additional critical component bypasses armor/shield. The test asserts the effect amounts.
- Same-boundary destruction: two size-2-shield interceptions each apply 2 HP loss from incoming 4, even when the first cumulative commit crosses zero. Both receive the shared pre-action protection; a later-boundary attack receives no shield ProtectionEffect.
- Three simultaneous incoming attacks against shield size 2 are refused before any attack roll; assertions verify RNG, time, and shield state stay unchanged. This is intentionally not reported as a completed bearer allocation.

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

No additional regressions were changed to make these suites pass. The broader repository suite was not run. A pre-existing `src/location.py` syntax error and legacy fixture incompatibilities previously documented in TASKS were not touched by this shield increment.

## Narrow rule decision required

Two adopted statements must be reconciled before implementing over-capacity bearer allocation:

- Shields (r61, p. 28): if attacks in a round exceed shield size, the bearer must decide which attacks the shield defends against.
- Action clock/information (r61, p. 9) and simultaneous resolution: a combatant cannot know an opponent’s Action choice in the same second it is chosen, and defense Choices use only information that combatant can perceive; outcomes remain common-snapshot/simultaneous.

The missing rule is specifically **which attacker/attack identities the bearer may see when choosing the shield-covered subset, and when that choice can be made**. This code refuses overload safely until this is adopted. Minimal alternatives:

1. **Prior-round observable allocation:** the bearer selects only among attacks already perceived before the simultaneous resolution round; unknown same-round attacks cannot be selected. This preserves information timing but can leave the simultaneous batch without a complete assignment.
2. **Pre-outcome revealed allocation:** reveal the scheduled same-boundary incoming attack identities to the bearer and require a shield allocation before any attack/defense roll. This completes the choice and preserves simultaneous outcomes, but explicitly carves out an exception to same-second Action secrecy for only this defense Choice.

No other work in this assignment depends on this choice; all independently supported mechanics and verification above are complete. Once selected, implement the typed persisted allocation/ownership path, observer-filtered UI and regression coverage without changing outcomes by declaration order.

## Repository and closeout

- Acceptance remains **ACTIVE**, not DONE. U-ACT-GATE-001 remains FUTURE/unpassed.
- `docs/encounters/action-implementation-coverage.md` holds the variant-level evidence and explicit allocation blocker; `TASKS.md` retains the sole ACTIVE program and remaining rows.
- Implementation commit: `037e03914753ab5e42d53da8278e7dc33d2cba01` (`Implement passive shield protection effects`). The commit contains only the two native implementation files, six focused test files, and the authored shield profile. It left the five unrelated staged historical archive paths and user save unchanged.
- Before that commit, `git diff --cached --check` passed and `tools/check_publication_safety.py --staged` reported `files=14 findings=0 result=PASS`; `git commit --only` kept the unrelated archive paths out of the commit. The documentation closeout commit and final exact HEAD/status are pending.
- No push is authorized or planned. Final HEAD, complete staged/worktree inventory, documentation whitespace/publication-safety results, and final execution interval will be recorded immediately before closeout.
