# U-CAP-006 — Tactical weapon control and deception report

**Status:** ACTIVE. Supported implementation and verification are committed, but acceptance criterion A remains incomplete pending the landing-location rule clarification below. Keep this report and assignment in the active directories until ChatGPT accepts and consumes the closeout.
**Assignment:** [U-CAP-006](../assignments/U-CAP-006.md)
**Repository:** Universe repository, branch `main`
**Publication:** No push or history rewrite performed.

## Execution interval

- Start: `2026-11-14T00:20:10-08:00` (captured at execution start; `2026-11-14T08:20:10Z`).
- End: `2026-11-14T01:28:46-08:00` (captured immediately before closeout; `2026-11-14T09:28:46Z`).
- Elapsed: `PT1H8M36S` (calculated from the recorded start and end).

## Acceptance matrix

| Criterion | Result | Evidence and bounded cases |
|---|---|---|
| A. Disarm and custody | **Partial; farther landing unresolved** | Armed and unarmed opposed rolls, grappled +5 exception, adopted Ranseur/Flail/conditional Lasso/Whip bonuses, gauntlet immunity, explicit owner-linked Locked-gauntlet attachment refusal, identity-preserving ground drop, margin-five unarmed same-ID transfer to a selected empty hand, Ready-state clearing, custody conflict and later weapon unavailability are implemented. Generated HTTP controls and fresh-process Save/Load cover ground-drop and hand-transfer routes. Exact farther landing selection/clearance and its relationship to post-roll margin are not implemented; see the decision required below. |
| B. Break weapon and Feint | **Implemented for supported facts; bounded branches** | Break weapon covers an opponent attacking the actor, attacking a third Being, and defending with a designated Parry weapon; uses the opponent's actual weapon, swing timing, native hardness/HP, interruption and later-boundary availability. Successful and failed attempts, Parry linkage persistence and generated HTTP continuation are tested. Magic-target saves fail closed because saving bonuses are absent. Unarmed Break remains unavailable because native body durability as a weapon is not represented. Armed/unarmed Feint uses adopted timing and ordinary attack resolution without Feint damage, applies the one-use same-target follow-up bonus, and is shown in generated Arena controls with fresh-load coverage. |
| C. Held-Object Grab and Wrest | **Implemented for adopted rules** | Distinct Object-Grab defense/DC, one-second Strength contest, same-ID custody transfer, ties/failures, release/interruption, stale custody, holder weapon conflict, simultaneous same-snapshot three-Being co-holding, late-fault rollback and fresh-process persistence are covered. No later contests between simultaneous co-holders were invented. |
| D. Generated Arena and persistence | **Implemented for the supported variants** | Shipped JavaScript exposes opaque-handle controls for armed/unarmed Disarm, Break weapon, armed/unarmed Feint, Object Grab and Wrest. Automated generated-Arena HTTP tests execute native Choices and verify the exact same Object identity across saves and fresh Python processes. Pending, resolved, failure, interruption, custody, readiness, receipts, and RNG continuation are covered by focused tests. Chrome in this execution was used only to open/render the generated Arena page; no manual combat outcome is claimed. |

**Overall:** Do not close U-CAP-006 yet. A farther Disarm landing is an explicit acceptance requirement and the adopted rule does not say when the exact landing cell is chosen relative to the opposed roll or how an over-range selection resolves. Current baseline drops the Object in the defender's hex; this does not demonstrate the assigned vacant-destination clearance requirement.

## Decision required to complete criterion A

The adopted Disarm text provides a maximum distance of one hex per full three points of winning margin, but no exact destination-selection phase. The assignment also requires a specified destination and says an occupied/unknown landing location is not legal. The current rule does not establish whether the target defender's occupied hex is a permitted default, or how to settle a farther destination selected before the random margin is known.

Minimal choices:

1. **Declare a destination before the contest.** If the contest margin permits it, land at that vacant hex; otherwise clamp to the nearest vacant hex on the selected direction within the permitted radius (and use an explicitly defined fallback if none exists). This is a one-boundary transaction, but adds an over-range/fallback rule.
2. **Choose after the contest.** Resolve the opposed roll, then require selection of a vacant in-range hex before publishing custody. This preserves the full post-roll choice, but adds a pending resolution choice and its timing, interruption and Save/Load state.

Please also confirm whether the defender's occupied hex is allowed as a zero-distance landing. The assignment's clearance clause currently excludes occupied landing locations, while the existing baseline/test route uses the defender's hex. No destination mechanic or occupancy exception is assumed pending this decision. All independent implementations and tests are complete for this interval.

## Implementation and runnable Arena evidence

- Disarm Take is a typed `DisarmTakeEffect`. The common-snapshot evaluator proposes it only for unarmed Disarm with margin at least five and a declared currently free native hand. Atomic publication clears the prior holder's hand/inventory references, places the **same Weapon Object ID** in the recipient hand/inventory, updates its owner anchor, and clears any previous owner's Ready-preparation tag. Insufficient margin or an omitted hand uses the supported drop route. A later accepted attack with the released weapon resolves unavailable.
- Locked-gauntlet refusal depends on an explicit owner-linked native Weapon tag authored through `author_locked_gauntlet_weapon_attachment`; no relation is inferred from names or carried equipment. The tag is validated against a native held target Weapon, a native owned `Locked gauntlet`, and persists as ordinary native Weapon tags.
- Generated test setup: `tests/fixtures/arena/empty.json`, generated Arena equipment mode `equipped`, player Unarmed combat rank `1`, authored high Attack / zero defender Defense for deterministic success, both Beings positioned within represented native reach, and an observer-owned opaque handle for the defender's Weapon. POST `/api/generated/disarm` with `{handle, motion:"thrust", unarmed:true, hand:<free hand>}`, save while executing, then restore in a fresh Python process. Expected receipt outcome is `disarmed_taken`; the same Weapon ID is in the selected player hand and the defender hand is empty. The exact test is `test_generated_arena_exposes_and_accepts_unarmed_disarm`.
- Related generated demonstrations: `test_disarm_http_pending_save_load_commits_exact_weapon_to_ground`, `test_break_weapon_http_choice_restores_pending_actual_weapon_action`, `test_armed_feint_uses_browser_route_and_pending_save_load`, `test_unarmed_feint_is_composed_by_shipped_ui_and_survives_fresh_load`, and `test_generated_http_grab_and_fresh_process_wrest_preserves_object_identity`.
- Actual Chrome evidence is limited to opening and rendering the generated Arena UI. Native result/persistence evidence comes from automated generated HTTP route tests, not a manual browser fight.

## Focused verification

Final combined cohort command:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest <32 explicitly named tests>
```

Result: **32 tests passed in 51.495 seconds.** The 32 tests were:

- `TestActionEvaluation.test_native_disarm_releases_same_weapon_into_defender_hex_atomically`
- `TestActionEvaluation.test_disarm_applies_adopted_ranseur_bonus`
- `TestActionEvaluation.test_gauntlet_cannot_be_disarmed_without_random_draw`
- `TestActionEvaluation.test_weapon_attached_to_authored_locked_gauntlet_cannot_be_disarmed`
- `TestActionEvaluation.test_native_unarmed_disarm_uses_arm_profile_and_opposed_attack_roll`
- `TestActionEvaluation.test_native_unarmed_disarm_takes_same_weapon_only_at_five_point_margin`
- `TestActionEvaluation.test_native_unarmed_disarm_hand_choice_drops_on_margin_below_five`
- `TestActionEvaluation.test_grappled_disarm_defender_loses_the_five_point_defense_bonus`
- `TestActionEvaluation.test_disarm_custody_loss_blocks_accepted_later_attack_with_that_weapon`
- `TestActionEvaluation.test_native_break_weapon_uses_pending_attack_motion_and_disables_it_next_boundary`
- `TestActionEvaluation.test_native_break_weapon_failed_attempt_preserves_both_weapons`
- `TestActionEvaluation.test_break_weapon_against_opponent_attacking_a_third_being_omits_their_damage`
- `TestActionEvaluation.test_break_weapon_automatically_hits_opponents_designated_parry_weapon`
- `TestActionEvaluation.test_break_weapon_fails_closed_for_magic_target_without_magic_saving_facts`
- `TestActionEvaluation.test_native_armed_feint_is_half_timing_nondamaging_and_bonus_is_one_followup`
- `TestActionEvaluation.test_native_unarmed_feint_uses_authored_arm_profile_and_same_target_followup`
- `TestActionEvaluation.test_armed_feint_requires_advanced_weapon_skill_before_choice_mutation`
- `TestGeneratedArenaBrowser.test_disarm_http_pending_save_load_commits_exact_weapon_to_ground`
- `TestGeneratedArenaBrowser.test_generated_arena_exposes_and_accepts_unarmed_disarm`
- `TestGeneratedArenaBrowser.test_break_weapon_http_choice_restores_pending_actual_weapon_action`
- `TestGeneratedArenaBrowser.test_armed_feint_uses_browser_route_and_pending_save_load`
- `TestGeneratedArenaBrowser.test_unarmed_feint_is_composed_by_shipped_ui_and_survives_fresh_load`
- `TestNativeObjectWrest.test_object_grab_uses_holder_defense_and_plus_five_dc`
- `TestNativeObjectWrest.test_generated_http_grab_and_fresh_process_wrest_preserves_object_identity`
- `TestNativeObjectWrest.test_failed_and_tied_wrest_leave_same_object_in_holder_hand`
- `TestNativeObjectWrest.test_holder_weapon_attack_competing_with_wrest_preserves_custody`
- `TestNativeObjectWrest.test_same_boundary_object_grabs_establish_independent_receipts`
- `TestNativeObjectWrest.test_three_being_simultaneous_wrest_shares_same_object_and_persists`
- `TestNativeObjectWrest.test_wrest_late_publication_fault_restores_custody_receipts_and_rng`
- `TestNativeObjectWrest.test_same_boundary_disarm_prevents_wrest_transfer`
- `TestNativeObjectWrest.test_earlier_disarm_invalidates_accepted_future_wrest_with_three_beings`
- `TestNativeObjectWrest.test_cancelled_pending_wrest_keeps_receipt_custody_and_rng`

`git diff --check` and `git diff --cached --check` passed. Staged publication-safety audit: `files=23 findings=0 result=PASS`. The staged set included the five already-staged historical archive changes, which remain excluded from the implementation commit.

## Commits and repository state

- `3491e795be85da536617dfad2878be842e2d08b0` — archive accepted U-CAP-005 and install U-CAP-006; maintained references and task-ID collision reconciliation.
- `f81791d` — complete tactical Disarm custody transfer; includes supported implementation, persistence adapters and focused tests.
- Implementation `HEAD` before the documentation closeout: `f81791d`. The documentation closeout commit follows this report update; its full hash is the final repository `HEAD` reported in the Codex chat closeout.
- The user's five staged archive paths remain staged and must not enter U-CAP-006 commits: U-CAP-002/U-CAP-003 assignment/report archival entries plus the U-THROW-001 patch rename.
- No push, `reset`, cleanup or history rewrite occurred.

## TASKS state

`TASKS.md` retains U-CAP-006 as the sole ACTIVE program. U-ACT-008 remains PARTIAL only for the unresolved farther landing selection/clearance; the margin-five take and explicit locked-gauntlet attachment refusal are now implemented. Unarmed Break and missing magic-save bonuses remain bounded without invented body durability or saving facts. U-CAP-005 remains accepted/consumed and archived.

## Final repository state

At documentation closeout, the only staged paths outside U-CAP-006 remain the five historical archive entries listed above. The implementation `HEAD` is `f81791d`; the documentation commit hash is reported in the final Codex chat. Execution interval recorded above. Keep this report active pending the landing decision and later ChatGPT review.
