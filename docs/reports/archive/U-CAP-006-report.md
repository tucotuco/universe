# U-CAP-006 — Tactical weapon control and deception report

**Status:** ACTIVE pending ChatGPT review. The adopted post-roll landing choice, including the user-approved revision-70 zero-distance exception, is implemented through native state, generated Arena controls, atomic custody transfer, inspection receipts, and fresh-process persistence. Keep this report and assignment in the active directories until ChatGPT accepts and consumes the closeout.
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
- A winning margin of 1–2 gives `maximum_landing_hexes == 0`. Revision 70 now allows the exact defender cell when the defender is its sole represented occupant.

### Rule-question clarification interval

- Start: `2026-11-14T10:25:54-08:00` (`2026-11-14T18:25:54Z`), captured when responding to the request for clarification.
- End: `2026-11-14T10:26:20-08:00` (`2026-11-14T18:26:20Z`), captured immediately before this clarification closeout.
- Elapsed: `PT26S` (calculated from the recorded start and end).
- The concrete case was a successful Disarm roll with margin 1 or 2. The clarification and adopted answer are retained here; the resolution is documented in the following interval and revision 70.

### Zero-distance ruling implementation

- Start: `2026-11-14T10:27:22-08:00` (`2026-11-14T18:27:22Z`), captured when implementing the user's clarified choice.
- End: `2026-11-14T10:50:02-08:00` (`2026-11-14T18:50:02Z`), captured immediately before documentation closeout.
- Elapsed: `PT22M40S` (calculated from the captured start and end).
- Across all four recorded intervals, active execution time is `PT2H20M24S`; calendar time from the first Start to this End is `PT10H29M52S`.
- The user selected allowing the same Weapon to share the defender's hex when the roll-derived range is zero. Adopted revision 70 permits this only when the defender is the sole Being/Object occupying that represented cell. Every positive-distance landing remains vacant-only; unknown and otherwise occupied cells remain unavailable.
- Native landing enumeration, receipt inspection, generated HTTP selection, observer evidence, and fresh-process restoration now accept exactly that case. Focused native and generated tests verify same-Weapon release into the defender's cell and agreement between persisted inspection/perception evidence.

## Acceptance matrix

| Criterion | Result | Evidence and bounded cases |
|---|---|---|
| A. Disarm and custody | **Implemented under revision 70** | Armed and unarmed opposed rolls, grappled +5 exception, adopted Ranseur/Flail/conditional Lasso/Whip bonuses, gauntlet immunity, explicit owner-linked Locked-gauntlet attachment refusal, margin-five unarmed same-ID transfer to a selected empty hand, Ready-state clearing, custody conflict and later weapon unavailability are implemented. Positive-range drops use a persisted post-roll choice of a vacant represented cell. For a zero-hex limit, the same Weapon may land in the defender's represented cell only when the defender is its sole occupant. Native and generated tests cover the exception, custody transition, observer evidence, receipt, and fresh-process restoration. |
| B. Break weapon and Feint | **Implemented for supported facts; bounded branches** | Break weapon covers an opponent attacking the actor, attacking a third Being, and defending with a designated Parry weapon; uses the opponent's actual weapon, swing timing, native hardness/HP, interruption and later-boundary availability. Successful and failed attempts, Parry linkage persistence and generated HTTP continuation are tested. Magic-target saves fail closed because saving bonuses are absent. Unarmed Break remains unavailable because native body durability as a weapon is not represented. Armed/unarmed Feint uses adopted timing and ordinary attack resolution without Feint damage, applies the one-use same-target follow-up bonus, and is shown in generated Arena controls with fresh-load coverage. Tests cover different-Action forfeiture, overlap with an opposing Action, and no same-boundary retroactive effect. No generic hit-interruption rule was introduced without adopted support. |
| C. Held-Object Grab and Wrest | **Implemented for adopted rules** | Distinct Object-Grab defense/DC, one-second Strength contest, same-ID custody transfer, ties/failures, release/interruption, stale custody, holder weapon conflict, simultaneous same-snapshot three-Being co-holding, late-fault rollback and fresh-process persistence are covered. No later contests between simultaneous co-holders were invented. |
| D. Generated Arena and persistence | **Implemented for the supported variants** | Shipped JavaScript exposes opaque-handle controls for armed/unarmed Disarm, Break weapon, armed/unarmed Feint, Object Grab and Wrest. Automated generated-Arena HTTP tests execute native Choices and verify the exact same Object identity across saves and fresh Python processes. Pending, resolved, failure, interruption, custody, readiness, receipts, and RNG continuation are covered by focused tests. The earlier Chrome check only opened/rendered the page; no manual combat outcome is claimed. |

**Overall:** The user resolved destination timing by selecting after the opposed roll and adopted the narrow zero-distance same-cell exception in revision 70. Criteria A–D are implemented for supported facts and covered by focused native/generated tests. U-CAP-006 remains ACTIVE pending ChatGPT review; unarmed Break and magic-target saving remain bounded by missing native facts.

## Adopted Disarm landing rule

Revision 70 resolves the former edge. For a winning margin of 1–2, the Weapon may share the defender's represented hex if no other Being or ground Object occupies it. The same Object identity is released from the hand and positioned at that cell. The exception does not apply to positive-range landings, other occupants, or unknown locations.

## Implementation and runnable Arena evidence

- Disarm Take is a typed `DisarmTakeEffect`. The common-snapshot evaluator proposes it only for unarmed Disarm with margin at least five and a declared currently free native hand. Atomic publication clears the prior holder's hand/inventory references, places the **same Weapon Object ID** in the recipient hand/inventory, updates its owner anchor, and clears any previous owner's Ready-preparation tag. Insufficient margin or an omitted hand uses the supported drop route. A later accepted attack with the released weapon resolves unavailable.
- Locked-gauntlet refusal depends on an explicit owner-linked native Weapon tag authored through `author_locked_gauntlet_weapon_attachment`; no relation is inferred from names or carried equipment. The tag is validated against a native held target Weapon, a native owned `Locked gauntlet`, and persists as ordinary native Weapon tags.
- Generated test setup: `tests/fixtures/arena/empty.json`, generated Arena equipment mode `equipped`, player Unarmed combat rank `1`, authored high Attack / zero defender Defense for deterministic success, both Beings positioned within represented native reach, and an observer-owned opaque handle for the defender's Weapon. POST `/api/generated/disarm` with `{handle, motion:"thrust", unarmed:true, hand:<free hand>}`, save while executing, then restore in a fresh Python process. Expected receipt outcome is `disarmed_taken`; the same Weapon ID is in the selected player hand and the defender hand is empty. The exact test is `test_generated_arena_exposes_and_accepts_unarmed_disarm`.
- Related generated demonstrations: `test_disarm_http_pending_save_load_commits_exact_weapon_to_ground`, `test_break_weapon_http_choice_restores_pending_actual_weapon_action`, `test_armed_feint_uses_browser_route_and_pending_save_load`, `test_unarmed_feint_is_composed_by_shipped_ui_and_survives_fresh_load`, and `test_generated_http_grab_and_fresh_process_wrest_preserves_object_identity`.
- Actual Chrome evidence is limited to opening and rendering the generated Arena UI. Native result/persistence evidence comes from automated generated HTTP route tests, not a manual browser fight.

## Focused verification

Focused command: the 36 report-listed methods were loaded into a `unittest.TestSuite` and run with `unittest.TextTestRunner(verbosity=1)` under `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B`. Final rerun after the occupancy regression: **36 tests passed in 60.287 seconds**, 0 failures, 0 errors. This includes native and generated zero-range landing, overlapping Feint, fresh-process persistence, and the previous Disarm/Break/Feint/Grab/Wrest regressions.

The cohort verifies all independently supported U-CAP-006 outcomes, including revision-70 same-cell landing, overlapping Feint, and fresh-process restoration. Exact test methods:

- Native Disarm: `test_native_disarm_persists_post_roll_landing_then_releases_same_weapon_atomically`, `test_successful_sub_three_margin_lands_on_defender_hex_by_adopted_exception`, `test_disarm_applies_adopted_ranseur_bonus`, `test_gauntlet_cannot_be_disarmed_without_random_draw`, `test_weapon_attached_to_authored_locked_gauntlet_cannot_be_disarmed`, `test_native_unarmed_disarm_uses_arm_profile_and_opposed_attack_roll`, `test_native_unarmed_disarm_takes_same_weapon_only_at_five_point_margin`, `test_native_unarmed_disarm_hand_choice_drops_on_margin_below_five`, `test_grappled_disarm_defender_loses_the_five_point_defense_bonus`, and `test_disarm_custody_loss_blocks_accepted_later_attack_with_that_weapon`.
- Break weapon: `test_native_break_weapon_uses_pending_attack_motion_and_disables_it_next_boundary`, `test_native_break_weapon_failed_attempt_preserves_both_weapons`, `test_break_weapon_against_opponent_attacking_a_third_being_omits_their_damage`, `test_break_weapon_automatically_hits_opponents_designated_parry_weapon`, and `test_break_weapon_fails_closed_for_magic_target_without_magic_saving_facts`.
- Feint: `test_native_armed_feint_is_half_timing_nondamaging_and_bonus_is_one_followup`, `test_native_unarmed_feint_uses_authored_arm_profile_and_same_target_followup`, `test_armed_feint_requires_advanced_weapon_skill_before_choice_mutation`, `test_selected_different_action_forfeits_successful_feint`, and `test_feint_overlaps_opponent_attack_without_same_boundary_retroactivity`.
- Generated Arena: `test_disarm_http_pending_save_load_commits_exact_weapon_to_ground`, `test_generated_zero_range_disarm_lands_in_defender_hex_and_restores`, `test_generated_arena_exposes_and_accepts_unarmed_disarm`, `test_break_weapon_http_choice_restores_pending_actual_weapon_action`, `test_armed_feint_uses_browser_route_and_pending_save_load`, and `test_unarmed_feint_is_composed_by_shipped_ui_and_survives_fresh_load`.
- Object Grab/Wrest: `test_object_grab_uses_holder_defense_and_plus_five_dc`, `test_generated_http_grab_and_fresh_process_wrest_preserves_object_identity`, `test_failed_and_tied_wrest_leave_same_object_in_holder_hand`, `test_holder_weapon_attack_competing_with_wrest_preserves_custody`, `test_same_boundary_object_grabs_establish_independent_receipts`, `test_three_being_simultaneous_wrest_shares_same_object_and_persists`, `test_wrest_late_publication_fault_restores_custody_receipts_and_rng`, `test_same_boundary_disarm_prevents_wrest_transfer`, `test_earlier_disarm_invalidates_accepted_future_wrest_with_three_beings`, and `test_cancelled_pending_wrest_keeps_receipt_custody_and_rng`.

The positive-range generated Disarm test saves while the Action is pending, resolves and chooses a clear landing in a fresh process through the HTTP route, then saves again and verifies the resolved receipt in another fresh process. The zero-range generated test restores the pending Action, resolves margin 1, selects the defender's cell through HTTP, saves, and verifies the ground location and observer evidence in another fresh process. Full repository suite was not run. An exploratory interruption assertion was removed after confirming ordinary damage does not itself cancel a pending Feint under current interruption contracts; no generic damage-interruption rule was invented. The final overlap test verifies an opposing Action resolving at the same boundary, with no retroactive Feint effect.

`py_compile` passed for all modified Python modules and tests. The local Markdown link checker verified 94 links in maintained files with zero broken links. `git diff --check` and `git diff --cached --check` passed. Staged publication-safety audits found zero issues. No manual Chrome combat result is claimed; browser evidence is the automated shipped JavaScript/HTTP/session route. The assignment's full repository suite was not run.

## Commits and repository state

- `3491e795be85da536617dfad2878be842e2d08b0` — archive accepted U-CAP-005 and install U-CAP-006; maintained references and task-ID collision reconciliation.
- `f81791d` — initial tactical Disarm custody implementation and focused tests.
- `554efbef84b9582b2da6480d4cfdedddfc233a10` — supported U-CAP-006 implementation, persistence, generated controls, regression tests and TASKS reconciliation before revision 70. The zero-distance implementation and documentation commits are recorded below.
- `748b82ad34a4702b3edb07d7ebd6cbfd84d4993f` — clarify the zero-distance decision in the active report before the user's answer.
- `f9d3ceb19e696ec23e349e0ec65e6d838da73c84` — implement the revision-70 same-cell exception in landing validation and receipt inspection; update TASKS; 11-file staged audit had zero findings.
- `13183efa6108be4f537a02612c08a52eaeb7e69d` — add the final regression that refuses the defender cell when a second Being also occupies it; 7-file staged audit had zero findings.
- The user's five staged archive paths remain staged and must not enter U-CAP-006 commits: U-CAP-002/U-CAP-003 assignment/report archival entries plus the U-THROW-001 patch rename.
- No push, `reset`, cleanup or history rewrite occurred. A report-only closeout commit follows this update; its hash and the final repository HEAD are included in the chat closeout.

## TASKS state

Before this continuation, U-CAP-006 was ACTIVE with positive-range landing selection complete and zero-range location unresolved; U-ACT-008 was PARTIAL for that same issue; U-ACT-010 still listed Feint overlap coverage. Afterward, U-CAP-006 remains the sole ACTIVE program pending ChatGPT review, U-ACT-008 records revision-70 landing rules, and U-ACT-010 records overlap/nonretroactivity coverage. No new idea/task ID was needed. `TASKS.md` is included in implementation commit `f9d3ceb19e696ec23e349e0ec65e6d838da73c84`. U-CAP-005 remains accepted/consumed and archived. Unarmed Break and missing magic-save bonuses remain bounded without invented body durability or saving facts.

## Final repository state

The latest implementation HEAD before documentation closeout is `13183efa6108be4f537a02612c08a52eaeb7e69d`. Revision-70 rule/assignment/report documentation is included in the closeout commit; its hash and final HEAD are reported in chat. The five user-staged historical archive paths remain untouched and excluded. No unrelated unstaged changes remain. Keep this report and assignment active pending ChatGPT review.
