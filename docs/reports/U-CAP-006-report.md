# U-CAP-006 — Tactical weapon control and deception report

**Status:** ACTIVE. The adopted post-roll landing choice is implemented through native state, generated Arena controls, atomic custody transfer, inspection receipts, and fresh-process persistence. Acceptance criterion A remains incomplete only for a successful Disarm margin of 1–2, where the zero-hex maximum leaves no unoccupied legal destination. Keep this report and assignment in the active directories until ChatGPT accepts and consumes the closeout.
**Assignment:** [U-CAP-006](../assignments/U-CAP-006.md)
**Repository:** Universe repository, branch `main`
**Publication:** No push or history rewrite performed.

## Execution interval

- Start: `2026-11-14T00:20:10-08:00` (captured at execution start; `2026-11-14T08:20:10Z`).
- End: `2026-11-14T01:28:46-08:00` (captured immediately before closeout; `2026-11-14T09:28:46Z`).
- Elapsed: `PT1H8M36S` (calculated from the recorded start and end).

### Current continuation

- Start: `2026-11-14T09:06:44-08:00` (`2026-11-14T17:06:44Z`), captured when this execution resumed.
- End: `2026-11-14T09:55:26-08:00` (`2026-11-14T17:55:26Z`), captured immediately before documentation closeout.
- Elapsed: `PT48M42S` (calculated from the captured start and end).
- User decision applied: choose a Disarm landing **after** the opposed roll and persist the pending landing choice.
- The choice is attached to the exact Weapon Object as a strict native tag; it records the committed source Action, actor, prior holder, opposed margin, maximum distance, and origin cell. Scheduling and Encounter progression stop until the choice is resolved. Generated Arena lists only vacant represented cells within the rolled range, uses the player's opaque observed Weapon handle, and posts the selected cell through `/api/generated/disarm-landing`.
- The selected cell is applied in a same-time atomic publication: the prior holder's hand, weapon inventory and possession references are cleared; the same Weapon receives the chosen represented position; old Ready state and the pending tag are cleared. A typed `DisarmLandingReceipt` authorizes inspection of the same-boundary spatial/custody transition and is restored only after source Action, margin, cell, map and Object checks.
- The same publication refreshes each participating observer's existing evidence for this already-visible Weapon, so the generated Arena immediately shows the selected ground cell. A regression assertion checks the post-choice view; pending and resolved checkpoint restoration still validate both current observer ledgers.
- A winning margin of 1–2 gives `maximum_landing_hexes == 0`. The origin is occupied by the defender, and no other cell is in range. Because adopted text and criterion A disallow occupied landings, the system preserves the pending state and refuses progression rather than inventing an exception or destination. This is the only presently identified user decision needed for Disarm acceptance.

### Rule-question clarification interval

- Start: `2026-11-14T10:25:54-08:00` (`2026-11-14T18:25:54Z`), captured when responding to the request for clarification.
- End: `2026-11-14T10:26:20-08:00` (`2026-11-14T18:26:20Z`), captured immediately before this clarification closeout.
- Elapsed: `PT26S` (calculated from the recorded start and end).
- The concrete case is a successful Disarm roll with margin 1 or 2. Its adopted limit is zero hexes, and the defender occupies the only cell at that distance. Option 1 allows the weapon to land in that same cell alongside the defender, as a narrow exception to the assignment's vacant-cell rule. Option 2 keeps the weapon in the defender's hand and treats the Disarm as having no custody effect despite the successful roll, then lets the Encounter continue. The question asks which gameplay result should apply.

## Acceptance matrix

| Criterion | Result | Evidence and bounded cases |
|---|---|---|
| A. Disarm and custody | **Partial only at zero distance** | Armed and unarmed opposed rolls, grappled +5 exception, adopted Ranseur/Flail/conditional Lasso/Whip bonuses, gauntlet immunity, explicit owner-linked Locked-gauntlet attachment refusal, margin-five unarmed same-ID transfer to a selected empty hand, Ready-state clearing, custody conflict and later weapon unavailability are implemented. Positive-range drops now resolve after the roll through a persisted, vacancy-checked destination choice and a same-ID atomic transfer. Generated HTTP and fresh-process tests cover pending and resolved choices. A margin of 1–2 has a zero-hex limit but no vacant destination; the occupied-origin conflict is the remaining rule blocker. |
| B. Break weapon and Feint | **Implemented for supported facts; bounded branches** | Break weapon covers an opponent attacking the actor, attacking a third Being, and defending with a designated Parry weapon; uses the opponent's actual weapon, swing timing, native hardness/HP, interruption and later-boundary availability. Successful and failed attempts, Parry linkage persistence and generated HTTP continuation are tested. Magic-target saves fail closed because saving bonuses are absent. Unarmed Break remains unavailable because native body durability as a weapon is not represented. Armed/unarmed Feint uses adopted timing and ordinary attack resolution without Feint damage, applies the one-use same-target follow-up bonus, and is shown in generated Arena controls with fresh-load coverage. A focused test confirms choosing a different Action forfeits the benefit. |
| C. Held-Object Grab and Wrest | **Implemented for adopted rules** | Distinct Object-Grab defense/DC, one-second Strength contest, same-ID custody transfer, ties/failures, release/interruption, stale custody, holder weapon conflict, simultaneous same-snapshot three-Being co-holding, late-fault rollback and fresh-process persistence are covered. No later contests between simultaneous co-holders were invented. |
| D. Generated Arena and persistence | **Implemented for the supported variants** | Shipped JavaScript exposes opaque-handle controls for armed/unarmed Disarm, Break weapon, armed/unarmed Feint, Object Grab and Wrest. Automated generated-Arena HTTP tests execute native Choices and verify the exact same Object identity across saves and fresh Python processes. Pending, resolved, failure, interruption, custody, readiness, receipts, and RNG continuation are covered by focused tests. Chrome in this execution was used only to open/render the generated Arena page; no manual combat outcome is claimed. |

**Overall:** Do not close U-CAP-006 yet. The user resolved destination timing by selecting after the opposed roll; exact over-range selection is therefore not applicable. Criterion A is blocked only by the adopted zero-distance limit for margins 1–2 versus the assignment's vacant-cell requirement.

## Remaining rule decision

The post-roll persisted choice has been implemented as directed. One edge still has no legal destination: a winning margin of 1 or 2 authorizes a maximum of zero hexes, while the defender occupies the only zero-distance hex and criterion A prohibits occupied landing locations.

Choose one:

1. **Allow same-cell landing only at zero distance.** The dropped Weapon occupies the defender's hex alongside them, without displacement; this is a narrow exception to the vacancy requirement.
2. **No custody effect at zero distance.** The Weapon stays in the defender's hand and the Disarm has no effect, despite the successful roll; the Encounter continues. This preserves the vacancy requirement.

All independent supported-range implementation, tests, persistence and regression work is complete. The answer is needed only to resolve this zero-distance contradiction; no other branch depends on it.

## Implementation and runnable Arena evidence

- Disarm Take is a typed `DisarmTakeEffect`. The common-snapshot evaluator proposes it only for unarmed Disarm with margin at least five and a declared currently free native hand. Atomic publication clears the prior holder's hand/inventory references, places the **same Weapon Object ID** in the recipient hand/inventory, updates its owner anchor, and clears any previous owner's Ready-preparation tag. Insufficient margin or an omitted hand uses the supported drop route. A later accepted attack with the released weapon resolves unavailable.
- Locked-gauntlet refusal depends on an explicit owner-linked native Weapon tag authored through `author_locked_gauntlet_weapon_attachment`; no relation is inferred from names or carried equipment. The tag is validated against a native held target Weapon, a native owned `Locked gauntlet`, and persists as ordinary native Weapon tags.
- Generated test setup: `tests/fixtures/arena/empty.json`, generated Arena equipment mode `equipped`, player Unarmed combat rank `1`, authored high Attack / zero defender Defense for deterministic success, both Beings positioned within represented native reach, and an observer-owned opaque handle for the defender's Weapon. POST `/api/generated/disarm` with `{handle, motion:"thrust", unarmed:true, hand:<free hand>}`, save while executing, then restore in a fresh Python process. Expected receipt outcome is `disarmed_taken`; the same Weapon ID is in the selected player hand and the defender hand is empty. The exact test is `test_generated_arena_exposes_and_accepts_unarmed_disarm`.
- Related generated demonstrations: `test_disarm_http_pending_save_load_commits_exact_weapon_to_ground`, `test_break_weapon_http_choice_restores_pending_actual_weapon_action`, `test_armed_feint_uses_browser_route_and_pending_save_load`, `test_unarmed_feint_is_composed_by_shipped_ui_and_survives_fresh_load`, and `test_generated_http_grab_and_fresh_process_wrest_preserves_object_identity`.
- Actual Chrome evidence is limited to opening and rendering the generated Arena UI. Native result/persistence evidence comes from automated generated HTTP route tests, not a manual browser fight.

## Focused verification

Latest focused cohort: `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B`, using `unittest.TestSuite` and `unittest.TextTestRunner(verbosity=1)` over the 34 explicit methods listed below. The final rerun after adding post-choice observer-view assertions completed **34 tests in 49.835 seconds**, 0 failures, 0 errors.

This cohort verifies all independently supported U-CAP-006 outcomes after the post-roll landing implementation. Exact test methods:

- Native Disarm: `test_native_disarm_persists_post_roll_landing_then_releases_same_weapon_atomically`, `test_successful_sub_three_margin_has_no_clear_legal_landing`, `test_disarm_applies_adopted_ranseur_bonus`, `test_gauntlet_cannot_be_disarmed_without_random_draw`, `test_weapon_attached_to_authored_locked_gauntlet_cannot_be_disarmed`, `test_native_unarmed_disarm_uses_arm_profile_and_opposed_attack_roll`, `test_native_unarmed_disarm_takes_same_weapon_only_at_five_point_margin`, `test_native_unarmed_disarm_hand_choice_drops_on_margin_below_five`, `test_grappled_disarm_defender_loses_the_five_point_defense_bonus`, and `test_disarm_custody_loss_blocks_accepted_later_attack_with_that_weapon`.
- Break weapon: `test_native_break_weapon_uses_pending_attack_motion_and_disables_it_next_boundary`, `test_native_break_weapon_failed_attempt_preserves_both_weapons`, `test_break_weapon_against_opponent_attacking_a_third_being_omits_their_damage`, `test_break_weapon_automatically_hits_opponents_designated_parry_weapon`, and `test_break_weapon_fails_closed_for_magic_target_without_magic_saving_facts`.
- Feint: `test_native_armed_feint_is_half_timing_nondamaging_and_bonus_is_one_followup`, `test_native_unarmed_feint_uses_authored_arm_profile_and_same_target_followup`, `test_armed_feint_requires_advanced_weapon_skill_before_choice_mutation`, and `test_selected_different_action_forfeits_successful_feint`.
- Generated Arena: `test_disarm_http_pending_save_load_commits_exact_weapon_to_ground`, `test_generated_arena_exposes_and_accepts_unarmed_disarm`, `test_break_weapon_http_choice_restores_pending_actual_weapon_action`, `test_armed_feint_uses_browser_route_and_pending_save_load`, and `test_unarmed_feint_is_composed_by_shipped_ui_and_survives_fresh_load`.
- Object Grab/Wrest: `test_object_grab_uses_holder_defense_and_plus_five_dc`, `test_generated_http_grab_and_fresh_process_wrest_preserves_object_identity`, `test_failed_and_tied_wrest_leave_same_object_in_holder_hand`, `test_holder_weapon_attack_competing_with_wrest_preserves_custody`, `test_same_boundary_object_grabs_establish_independent_receipts`, `test_three_being_simultaneous_wrest_shares_same_object_and_persists`, `test_wrest_late_publication_fault_restores_custody_receipts_and_rng`, `test_same_boundary_disarm_prevents_wrest_transfer`, `test_earlier_disarm_invalidates_accepted_future_wrest_with_three_beings`, and `test_cancelled_pending_wrest_keeps_receipt_custody_and_rng`.

The generated Disarm test saves while the Action is pending, resolves and chooses a clear landing in a fresh process through the HTTP route, then saves again and verifies the resolved receipt in another fresh process. The prior 32-test cohort is historical and superseded by this 34-test result. Full repository suite was not run.

`py_compile` passed for all modified Python modules and the generated Arena entry point. `git diff --check` and `git diff --cached --check` passed after the observer-view correction. The staged publication-safety audit is recorded with the final scoped commits. No manual Chrome combat result is claimed; browser evidence here is the automated shipped JavaScript/HTTP/session route.

## Commits and repository state

- `3491e795be85da536617dfad2878be842e2d08b0` — archive accepted U-CAP-005 and install U-CAP-006; maintained references and task-ID collision reconciliation.
- `f81791d` — initial tactical Disarm custody implementation and focused tests.
- `554efbef84b9582b2da6480d4cfdedddfc233a10` — complete all independently supported U-CAP-006 implementation, persistence, generated controls, regression tests, and TASKS reconciliation. This is the implementation HEAD; 34 focused tests passed, `py_compile` and diff checks passed, and the 27-file staged publication-safety audit had zero findings. The report-only commit's 7-file staged audit also had zero findings.
- The user's five staged archive paths remain staged and must not enter U-CAP-006 commits: U-CAP-002/U-CAP-003 assignment/report archival entries plus the U-THROW-001 patch rename.
- No push, `reset`, cleanup or history rewrite occurred. A report-only closeout commit follows this update; its hash and the final repository HEAD are included in the chat closeout.

## TASKS state

`TASKS.md` retains U-CAP-006 as the sole ACTIVE program. U-ACT-008 remains PARTIAL only for the unresolved farther landing selection/clearance; the margin-five take and explicit locked-gauntlet attachment refusal are now implemented. Unarmed Break and missing magic-save bonuses remain bounded without invented body durability or saving facts. U-CAP-005 remains accepted/consumed and archived.

## Final repository state

At implementation closeout, `HEAD` is `554efbef84b9582b2da6480d4cfdedddfc233a10`; the report-only closeout commit hash and final HEAD are reported in the final Codex chat. The only remaining staged paths are the five previously staged historical archive entries listed above. The working tree contains no unrelated unstaged edits. Keep this report and assignment active pending the zero-distance rule decision and later ChatGPT review.
