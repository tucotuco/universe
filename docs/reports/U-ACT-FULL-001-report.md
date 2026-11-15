# U-ACT-FULL-001 engineering report

**Status:** ACTIVE; closeout criteria are not yet met. This report remains in the active reports directory until ChatGPT review and acceptance.

## Execution intervals

- Start: **2026-11-15T10:54:27-08:00** (recorded at execution start).
- End: pending; capture immediately before closeout.
- Elapsed: pending; calculate from recorded timestamps, not estimate.

## Assignment reconciliation and repository safety

- U-OBS-001 was accepted DONE (bounded). Its assignment and consumed report are in `docs/assignments/archive/U-OBS-001.md` and `docs/reports/archive/U-OBS-001-report.md`; its original perception limitations remain in TASKS and are preserved as future gate work.
- Verified U-ACT-FULL-001 unused before activation. It is the sole ACTIVE implementation program. U-ACT-GATE-001 remains FUTURE/unpassed; U-NET-001 remains DEFERRED. Both Arena modes, observer-specific knowledge and the frozen Playtest Edition remain protected.
- HEAD at the start: `33b11f7c4514d6d764e6baed6e4aac8c09b43df6`; assignment activation: `6ffa4cdcad342539c0831db8f7df4b2af9dce66d` (`Activate Action coverage assignment`); coverage milestone: `5923020` (`Audit adopted Encounter action variants`).
- The pre-existing index entries for U-CAP-002/U-CAP-003/U-OBS-001 active-path deletions and the U-THROW-001 patch rename are preserved and excluded from our commits. The untracked `docs/assignments/universe-arena.json` save remains untouched. No push.

## Acceptance matrix progress

The source-linked matrix is [action-implementation-coverage.md](../encounters/action-implementation-coverage.md). It enumerates 51 source-linked Action/variant rows: **40 PARTIAL, 4 OPEN, 5 BLOCKED, 1 NOT AN INDEPENDENT ACTION, 1 VERIFY, 0 FULL**. This is deliberately not a gate pass; prior DONE (bounded) implementations remain bounded. The matrix identifies implementation paths and focused tests per row, and gives the ordered remaining-cluster plan.

The inventory audit verified `U-ACT-040` and `U-ACT-041` unused, then registered mounted Dismount and Armor Don/Remove in the sole canonical `TASKS.md` register. Their exact missing mount/rider and armor-part state is recorded in the matrix. No other stable ID was recycled.

### Equipment/weapon findings

- Revision 61 does define shield `ST`: the Shields Table legend calls it the timing for swing attacks with that shield. Don Shield and Remove Shield use `ST × 5` and `ST × 2`, respectively. The earlier U-CAP-003 report statement that the `ST` input itself was absent was inaccurate; this report corrects that conclusion.
- A generic shield Don/Remove transition is still not implemented. Existing native state can express a carried shield, selected free hand, and a shield borne in a hand; the native evaluation, atomic custody projection, interrupt handling, browser contract, history and fresh-process test do not yet connect those states through the adopted timed Actions. The existing per-instance forearm buckler fact remains a separate representation and must not be generalized to other shields.
- A removed shield's destination (retained in carried possession versus released to the ground) is not specified by the adopted Action text. I have not silently chosen a physical transition. This question must be isolated if either outcome is necessary to finish the shield variant; donning a carried shield can be evaluated independently.
- Passive shield capacity is not compliant today: r61 limits passive defense to shield-size attacks in a round and requires the bearer to select which attacks receive protection when more attacks arrive. The evaluator currently samples shield identity randomly per attack. The common-snapshot rule additionally requires assignments before outcomes. This needs native allocation, a player choice surface and a persisted decision; randomized selection is not evidence of adopted allocation.
- Revision 69 adopts ordinary Draw at two seconds and Quick-draw with advanced weapon skill as essentially no-time. It expressly does not authorize inventing a zero-duration integer scheduler event. The current Draw adapter correctly fails closed for this exceptional branch. General Ready Object timing is referee-adjudicated and remains blocked without a supplied case-specific duration.

## Verification performed

Focused three-test check (the selected tests verify the prior bounded equipment loop, not new U-ACT-FULL closure):

`PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_arena_ready_weapon.TestArenaReadyWeapon.test_generated_medium_shield_bash_resolves_after_fresh_process_restore tests.test_arena_ready_weapon.TestArenaReadyWeapon.test_ground_pickup_remains_carried_unreadied_and_does_not_create_draw_location tests.test_arena_ready_weapon.TestArenaReadyWeapon.test_revision_61_re_ready_timing_uses_weapon_and_motion_table_values`

Result: **3 passed in 4.775 s**.

A broader local diagnostic run was also attempted:

`PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_arena_ready_weapon tests.test_action_evaluation tests.test_action_settlement`

It ran 211 tests in 158.372 s and failed: one physical-contact fixture now places the third Being at a stale nonadjacent coordinate after introducing a hex map (`test_native_touch_grab_hold_break_grapple_and_escape_use_separate_receipt_state`), and 15 legacy `test_action_settlement` fixtures are rejected at Choice validation because they schedule overlapping Actions without an acquired Multi-action declaration. No source or test code was changed in this diagnostic interval, so these are not regressions from U-ACT-FULL-001. They are not resolved by weakening the Multiple-action or path rules. The targeted selected equipment tests above passed.

The actual served Chrome tab is present at `http://127.0.0.1:51863/`. Its current generated encounter is a live user browser state and has no shield among its evidenced carried objects; it was inspected read-only and not mutated. No new Chrome gameplay claim is made in this report.

## Still required before acceptance

1. Implement and test the independently supported shield Don transition, shield Remove custody outcome once its destination is determined, interruption, shield/hand/Block/Bash constraints, native receipts and strict fresh-process persistence.
2. Implement adopted passive shield-size allocation and a pre-outcome player selection route, or keep the variant explicitly incomplete if its allocation interval is not established.
3. Audit other independently feasible equipment/weapon variants in the matrix, and deliver a genuinely new consequential native variant through shipped controls and actual served Chrome with exact Save/Load continuation.
4. Reconcile two-sided Arena, observer privacy, movement, checkpoint and Action-composition regressions for each new path. Repair stale fixtures only where source rules establish their intended semantics; do not relax Multiple-action or physical-path rules.
5. Update matrix counts, TASKS, exact command timings/results, Chrome walkthrough, persistence identity evidence, remaining clusters, final HEAD and worktree/index inventory. Commit only reviewed in-scope paths after staged whitespace and publication-safety audits.

## Commits and status changes

- `6ffa4cdcad342539c0831db8f7df4b2af9dce66d` — activation, U-OBS archival reference reconciliation and assignment installation. This commit preserved unrelated staged archive entries.
- `5923020` — committed the source-linked variant audit and removed the duplicated active-path U-OBS assignment/report copies while preserving their accepted archived copies. The matrix has since been expanded with newly reconciled catalog variants; those follow-up docs are uncommitted at this report revision.
- No new implementation variant has yet been committed. U-ACT-FULL-001 remains the only ACTIVE program; no Action Completeness gate status was changed.
- Publication was not authorized; nothing was pushed.
