# U-CAP-002 engineering report

**Status: DONE (bounded) — all U-CAP-002 assignment criteria are demonstrated or explicitly bounded at adopted-rule/data limits.** The required generated-Arena gameplay loop, native spatial and contest resolution, and fresh-process persistence are verified. No unresolved decision is needed to close this assignment: unsupported quantitative force-to-motion, mounted/concerted geometry and unmodeled path cases fail closed or remain typed as pending physical displacement. Related Action entries remain independently open where their wider scopes exceed this assignment. The assignment and this report remain in the active directories until ChatGPT reviews and consumes them.

## Current acceptance matrix

| Area | Result | Verification and limits |
|---|---|---|
| A. Occupied-space movement | **Implemented for represented routes** | Continuous metric paths, modeled geometry and cell occupancy reject blocked/occupied/unknown routes before publication. Independent legal paths, pinned movement, physical-Hold co-motion and separation restrictions, late conflicts, two-/three-Being destination contention, rollback/RNG preservation, and the terminal ground-Object contact convention are covered. No universal body footprint is inferred. |
| B. End Run | **Implemented and demonstrated** | Adopted three-second preparation with timing adjustment; passage in the completion movement phase; willing and resisting occupant branches; Dexterity/size and behind/immobilized checks; tie/failure origin retention; distinct legal exit; route/occupancy/change/interruption refusals; three-Being contention; generated exit control and pending/committed fresh-process Save/Load. This closes U-ACT-009 at its represented scope. |
| B. Disengage | **Bounded as ordinary movement** | Native and generated tests show withdrawal can leave a scheduled strike out of reach or remain in reach. No free Action, opportunity attack, or defense penalty is invented. |
| B. Overrun | **Implemented for supported standing cases and adopted follow-ups** | Four-second contest, action timing/priority, STR+DEX, relative size, explicit shield and named-leg modifiers, eligibility limits, and prone result. Immediate successful Charge or Bull Rush adds +1 and two seconds. Charge follow-up places the target one hex in the charge direction only when the modeled adjacent cell is clear; Bull Rush follow-up leaves the target prone in its occupied hex. Unsupported geometry returns a typed pending-displacement result. |
| B. Bull Rush | **Contest and continuation implemented; distance bounded** | Native/generated resisted contest, strict tie failure, size/shield/stability, Multiple-action priority and Yield. Explicit scenario-authored willingness produces automatic success without resistance dice. Successful Charge adds +2; a successful Bull Rush can continue next second with +1. Contest success remains `success_pending_displacement`; no force-to-motion distance, concerted/mounted geometry, or extraordinary stability is fabricated. |
| C. Charge and pole interaction | **Unmounted represented case integrated** | Native relative speed, +2 hit, adopted incremental damage and engagement refusal; generated opaque selector and legal run-in. Four-second Set Pole for supported spear/lance thrust persists through Save/Load. Successful same-boundary interception doubles pole damage and converts the charger's already scheduled attack to a normal attack. Charge → Bull Rush (+2) and Charge → Overrun (+1, +2 sec, one legal hex) are receipt-linked. Mounted cases remain bounded by absent mount/rider geometry. |
| D. Arena and persistence | **Generated gameplay and fresh-process continuation demonstrated** | Generated End Run includes a resisting passage across pending/committed fresh-process restore. Generated seed-12 Charge → Overrun exposes the six-second continuation, preserves the Charge receipt over pending Save/Load, resolves in a fresh OS process, and reloads the committed prone/position result in another process. These are HTTP/session/JavaScript harness tests; no successful actual-Chrome run is claimed. |

## Reproduction and verification

All commands use the preserved `.venv` and `-B` to avoid bytecode artifacts.

- Native evaluation: `.venv/bin/python -B -m unittest tests.test_action_evaluation` — **109 tests passed in 96.334s**.
- Native movement integration: `.venv/bin/python -B -m unittest tests.test_movement_intent` — **45 tests passed in 16.524s**, including pinned refusal, jointly moving held Beings without increased separation, movement toward a stationary holder, and refusal when a held Being increases separation.
- Native/generated movement, Arena Ready, Charge, End Run, Overrun, Bull Rush and pole integration: `.venv/bin/python -B -m unittest tests.test_movement_intent tests.test_arena_ready_weapon tests.test_arena_melee_attack.TestArenaMeleeAttack.test_generated_charge_selector_schedules_native_charge_without_exposing_ids tests.test_arena_melee_attack.TestArenaMeleeAttack.test_generated_arena_runs_in_and_resolves_a_legal_charge tests.test_arena_melee_attack.TestArenaMeleeAttack.test_generated_end_run_passage_and_fresh_process_continuation tests.test_arena_melee_attack.TestArenaMeleeAttack.test_generated_overrun_uses_explicit_size_and_native_prone_resolution tests.test_arena_melee_attack.TestArenaMeleeAttack.test_generated_overrun_pending_and_committed_state_restore_in_fresh_processes tests.test_arena_melee_attack.TestArenaMeleeAttack.test_generated_bull_rush_uses_native_strength_contest_and_pending_boundary tests.test_action_evaluation.TestActionEvaluation.test_set_pole_intercepts_charge_and_converts_chargers_scheduled_attack` — **67 tests passed in 90.150s**.
- Charge → Overrun position receipt and fresh-process Save/Load, explicit willing Bull Rush, repeated Bull Rush, and Bull Rush → Overrun: `.venv/bin/python -B -m unittest tests.test_arena_melee_attack.TestArenaMeleeAttack.test_generated_charge_overrun_continuation_restores_position_effect_in_fresh_processes tests.test_action_evaluation.TestActionEvaluation.test_explicitly_willing_bull_rush_skips_contest_draws_and_keeps_displacement_bounded tests.test_action_evaluation.TestActionEvaluation.test_successful_bull_rush_can_continue_next_second_with_adopted_one_point_bonus tests.test_action_evaluation.TestActionEvaluation.test_successful_bull_rush_overrun_gets_bonus_and_two_seconds_without_inventing_displacement` — **4 tests passed in 101.566s**.
- Syntax compiled in memory for **20 changed Python files**; `git diff --check` passed.
- Earlier broad focused run: 227 tests had 15 `test_action_settlement` errors from fixtures scheduling overlapping Actions without acquired Multi-action skill. One exact error was rerun against committed baseline code and reproduced unchanged (`ChoiceRejected: Overlapping Actions ... require acquired Multi-action skill`); it is a baseline fixture incompatibility, not an implementation regression. No full repository suite is claimed.

The generated Charge → Overrun test uses the deterministic seed-12 empty-ground profile, an ordinary walk to align, a legal sprint run-in to the target's neighboring cell, a successful native Charge, and an explicit Stop of the remaining movement plan before choosing the immediate continuation. The Action contest rolls are fixed only inside the test. Beings, skills and authoritative RNG are not mutated by browser controls.

### `uncertain_path` investigation

The first generated landing fixture was refused because `trace_physical_path` treated every participant with no position or geometry as an unknown obstacle, even for a one-cell transition with no intermediate cell. The landing validator now checks every participant's destination-cell occupancy, then traces only located entities with explicitly represented geometry. This retains refusal for occupied cells and modeled intersections without inventing a body footprint or treating unplaced equipment as an obstacle. The generated one-hex continuation now passes end to end.

## `TASKS.md`

- U-CAP-002 remains the sole ACTIVE program.
- U-ACT-009 End Run transitions to DONE (bounded) for its represented acceptance.
- U-ACT-003 Bull Rush records explicit-willing automatic success, repeated +1 continuation and Charge +2; unsupported force-to-motion and complex variants remain bounded.
- U-ACT-005 Charge records Set Pole interception and supported Bull Rush/Overrun follow-ups.
- U-ACT-014 Overrun records both continuation variants and the legal Charge landing.
- No new task or idea was created. `docs/ideas/inbox/` is absent; the processed idea remains untouched.

## Repository and safety

- Baseline before this continuation: `a458dffc8d078c61c26fc7b272751b3083cc608c` on `main`.
- The implementation/report commits and final HEAD are recorded after audited commits below.
- The user-staged historical move `docs/reports/U-THROW-001-rule-sync-proposal.patch` → `docs/reports/archive/U-THROW-001-rule-sync-proposal.patch` is preserved and excluded from U-CAP-002 commits.
- `docs/assignments/universe-arena.json` is absent as directed; no save or ignored/local data was staged. No sibling repository, backup, `.venv`, `legacy/`, or local saved-world data was changed.
- No push was made. Actual Chrome is not claimed; generated Arena HTTP/session and shipped JavaScript interaction paths are exercised by the named tests.

## Commits and audit

- `1694f62e0fe4ecef216c88b15e3754386a8d3b42` — Integrate bounded Charge and Bull Rush continuations. This commit contains 22 explicitly scoped implementation, test, `TASKS.md`, and report paths.
- `c53cae7ac28db645ae93e405792ee02c19999259` — Add focused regression coverage for physical-Hold movement. The complete `test_movement_intent` module passed after this commit.
- `9514d1b087b7796a7592e74e2499fe343c08f92f` — Close the bounded U-CAP-002 outcome in `TASKS.md` and align this report with the assignment matrix.
- Before commit: `git diff --cached --check` passed. `.venv/bin/python -B tools/check_publication_safety.py --staged` reported **24 staged paths, 0 findings, PASS**; the count included the user's independently staged archive rename. `git commit --only` explicitly excluded that rename.
- The movement-regression commit used the required staged audit (**3 staged paths, 0 findings, PASS**) and `git commit --only` excluded the user-staged rename. The `TASKS.md`/report closeout used the required staged audit (**4 staged paths, 0 findings, PASS**) and likewise excluded that rename.
- Immediately before final report interval/evidence closeout, `HEAD=9514d1b087b7796a7592e74e2499fe343c08f92f` on `main`; the final report-only commit will be directly above this verified tip. The resulting HEAD is included in the final Codex response because a commit cannot embed its own hash.
- Remote remains `origin` (`https://github.com/tucotuco/universe.git`); no push was made.
- No test weakened checkpoint fingerprints. The new `PositionEffect` type was added to the closed checkpoint field/type catalog and reconstructed through the existing fingerprinted format; generated pending and committed restores both pass.

## Execution intervals

Earlier starts whose ends were not captured are preserved without estimates. All times use the explicit `-08:00` offset for `America/Los_Angeles` on 2026-11-13.

| Interval | Start | End | Elapsed |
|---|---|---|---|
| Earlier continuation | 2026-11-13T09:28:38-08:00 | Not captured | Not calculable |
| Earlier continuation | 2026-11-13T09:57:07-08:00 | Not captured | Not calculable |
| Earlier continuation | 2026-11-13T10:20:30-08:00 | Not captured | Not calculable |
| Earlier continuation | 2026-11-13T12:07:23-08:00 | Not captured | Not calculable |
| Current execution | 2026-11-13T14:06:56-08:00 | 2026-11-13T15:21:15-08:00 | PT1H14M19S |

The assignment's original start predates the recorded intervals; it is unavailable and is not fabricated.
