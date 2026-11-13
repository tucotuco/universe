# U-CAP-001 — General Action composition closeout

**Status: DONE (bounded).** Assignment: [U-CAP-001](../../assignments/archive/U-CAP-001.md). The full U-CAP-001 acceptance criteria are met for the eligible native Action families currently supported by the generated Arena. Revision 69 Draw, nonconditional weapon Ready, Delay, eligible pause/resume, composition, interruption, repetition and persistence are integrated. Broader native Actions and optional variants remain in their existing task IDs; they do not block this bounded assignment. No rule decision remains outstanding for this scope.

## Codex execution intervals

| Session | Start (ISO 8601) | End (ISO 8601) | Elapsed (ISO 8601 duration) |
|---|---|---|---|
| U-CAP-001 implementation closeout | `2026-11-12T23:48:41-08:00` | `2026-11-13T00:31:37-08:00` | `PT42M56S` |
| Permanent development-process amendment | `2026-11-13T00:36:28-08:00` | `2026-11-13T00:39:01-08:00` | `PT2M33S` |
| Revision 69 rules and Draw/Ready/Delay implementation | `2026-11-13T01:39:08-08:00` | `2026-11-13T02:40:29-08:00` | `PT1H1M21S` |
| U-CAP-001 archival workflow and reference updates | `2026-11-13T08:29:35-08:00` | `2026-11-13T08:35:32-08:00` | `PT5M57S` |

The first two intervals are carried forward from the actual prior closeouts. The last two intervals lasted `PT1H1M21S` and `PT5M57S`. Total active execution time across these four recorded intervals is `PT1H52M47S`; total calendar time from the first Start to the final End is `PT8H46M51S`.

## Rules, implementation and boundaries

Revision 69 is controlling in [the adopted rules package](../../encounters/README.md) and [the r69 supplement](../../encounters/encounters-consistency-decisions-r69.md). It replaces conditional-trigger Ready. Ready creates only a motion-specific weapon preparation; it creates no target, event trigger, condition watcher or later Action commitment. Ordinary Draw takes two seconds and does not Ready the weapon. Ready lasts through Delay and is consumed when the weapon is next used; matching Strike timing receives the adopted reduction with a one-second minimum. Event readiness and assumed drawable locations/hands remain outside scope.

Delay is a native one-second wait Action that records its selected defense. Repeating Delay waits to a later declaration boundary. An eligible pending Action can be paused only between committed seconds and resumed under its original identity with its saved remaining active duration. Spellcasting and momentum-dependent Actions, including strikes and charge, are rejected. The paused lifecycle is omitted from due Action resolution, validated in native interval preflight, and preserved by native Arena Save/Load.

The general generated-Arena composer submits through native Choice validation and publication. It exposes the eligible supported catalog, ordered timing, target handles, strategy/resource allocation, priority, status, cancellation and persistence. It does not manufacture source locations, hand occupancy, unsupported Action families or readiness of Events. No conditional Ready interpretation remains in the active implementation or user-facing controls.

## Repository and preservation

This execution began at HEAD `33ba09f68fc0d11a612b8b1ebc1fb3380f07f14e` on local `main`, after the prior task/report interval commit. Only U-CAP-001 source, tests, and its report/register state were changed. Pre-existing untracked assignment inputs and Arena/save/report files remain untouched. `.venv`, ignored `legacy/`, saved-world data, independent repositories and all backups remain protected.

## Acceptance verification matrix

| U-CAP-001 criterion | Result | Verified evidence / boundary |
|---|---|---|
| Reconcile original U-ARENA-018 minimum and Sections A–D | Met | [Parent closeout](../U-ARENA-018-closeout.md), commit `51249f5`; U-ARENA-018 is DONE (bounded), with Stun/Subdue and optional Disarm variants separate. |
| General ordered composer for every eligible Action in the supported Arena catalog | Met (bounded) | Native Choice remains the single validator/publication path. Generated UI exposes action families with complete native Arena submission contracts, opaque observer handles, timing, resources, priority and reasons. General HTTP composer tests and earlier shipped-browser Touch + Dagger Swing interaction are retained. |
| Mixed-duration overlap, sequential work, contention, resources, priority, simultaneous effects and RNG safety | Met | `tests.test_action_choices`; generated HTTP overlap/no-skill refusal preserves RNG state; mixed Touch + Thrust test verifies component timing/penalty and simultaneous outcomes. |
| Interruption, cancellation and repeat-until-abort | Met | Native Choice regressions; generated general program cancellation; Multiple Touch repeated-cycle test restores, executes a fresh-identity cycle and cancels the successor. |
| Accepted, running mixed-duration, aborted and repeating program persistence through a fresh process | Met | `test_general_action_program_http_accepts_sequential_and_validated_overlap` restores an accepted not-yet-started program. `test_general_action_program_composes_mixed_duration_touch_and_melee` now saves/restores that program while running, then saves/restores its aborted state. `test_native_multiple_touch_cycle_survives_live_and_recurring_fresh_process_saves` covers repeated cycles in child processes. |
| Revision-69 Draw, Ready, Delay and nonconditional Ready | Met (supported weapons) | Native and generated HTTP/session controls cover two-second Draw, motion options, readiness persistence, Ready → Delay → Strike, Longsword 6/2/4-second timing, ordinary/unready and repeated Strike timing, and consumption after use. No Event-readying or unsupported drawable facts are offered. |
| Eligible pause/resume with remaining duration and prohibited momentum pause | Met | Six-second Spot pauses after two committed seconds, waits three seconds, resumes the same identity for four remaining seconds and resolves at the shifted boundary. Paused state is Save/Load-restored in a fresh Python process. Strike pause refusal has focused coverage. |
| Observation privacy, rollback, competing resources, retained defense and no-cost maintenance regressions | Met in the shared Choice/interval cohort | `tests.test_action_choices` and existing Action settlement/atomic publication cases. The generated projection contains no native Action IDs; forged handles and rejected declarations remain refused without RNG advancement. |
| Actual browser attempt and shipped-control evidence | Attempted; HTTP/session verified | Chrome opened the generated Arena at seed `20261140`; Generate produced the ordinary equipped Encounter and the page displayed Pause/Resume controls. Before the first observed/action boundary, the player popup correctly reported Action availability as unknown, so this visit did not claim an Action click. The ordinary HTTP/session control tests and prior recorded seeded composer browser interaction supply the executable evidence; no file-picker Load claim is made. |
| Unimplemented Actions outside assignment | Separate OPEN/PARTIAL scope | Stun/Subdue, optional Disarm branches, other Object/weapon variants and any later contest between joint Object holders remain under their existing IDs. They do not require a missing rule decision for this assignment. |

## Reproduction and test results

Focused checks (repository `.venv`, Python `-B`):

- `PYTHONPATH=src:examples .venv/bin/python -B -m unittest tests.test_action_choices tests.test_arena_ready_weapon tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_generated_ready_delay_http_controls_and_visible_motion_timing tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_pause_resume_http_controls_keep_action_identity_and_remaining_time` — **79 tests passed** in 15.476 s. An earlier run exposed a missing weapon in the newly added negative pause-test fixture; the fixture was corrected and the full focused command rerun successfully.
- `PYTHONPATH=src:examples .venv/bin/python -B -m unittest tests.test_arena_persistence tests.test_arena_checkpoint_activation` — **8 tests passed** in 12.148 s.
- Four focused generated HTTP tests for sequential/overlapping composition, cancellation, mixed-duration Actions and Grapple + Break-hold — **4 passed** in 4.253 s.
- Extended fresh-process mixed-duration accepted → running → aborted Save/Load test — **1 passed** in 3.110 s.
- `test_actual_shipped_javascript_runs_fresh_authored_draw_scenario` and `test_native_multiple_touch_cycle_survives_live_and_recurring_fresh_process_saves` — **2 passed** in 3.307 s.
- Python compile check for the touched runtime, Arena and test modules passed before final commit. The full repository suite was not run.

The actual Chrome interaction was a live local generated Arena session. The full temporal transitions were exercised through native tests, HTTP routes and separate Python subprocesses; these evidence levels are distinguished above. The extension's local-file Load limitation was not used to infer Save/Load success; fresh-process native serialization supplied that proof.

## Task register and process

`TASKS.md` transitions in the closeout commit:

- `U-CAP-001`: ACTIVE → DONE (bounded), with this complete acceptance matrix.
- `U-ACT-007` Delay: OPEN/ACTIVE → DONE (bounded).
- `U-ACT-013` Multiple actions: PARTIAL/ACTIVE → DONE (bounded for supported native Arena catalog); broader native Action families remain separate.
- `U-ACT-015` Ready: PARTIAL/ACTIVE → DONE (bounded for weapons); other Objects require separately established preparation and Event readiness is not adopted.
- `U-ACT-035` Draw: DONE (bounded) clarified to distinguish Draw from Ready and require represented source/hand facts.
- `U-UI-001`, Stun/Subdue, optional Disarm variants and other open Actions remain unchanged.
- Idea inbox check: `docs/ideas/inbox/` does not exist; no intake note or ID mapping was available. No new idea was inferred.
- No new assignment was created or started. `TASKS.md` records no implementation program ACTIVE and leaves U-CAP-002 as the next candidate.

The permanent [development-process document](../../process/DEVELOPMENT-PROCESS.md) requires actual timezone-qualified ISO 8601 Start/End timestamps and calculated elapsed durations in both reports and chat, per execution interval. The archival workflow execution interval is recorded below.

## Git, safety and closeout

- Rules supplement commit: `43bf86d727af4b632050de10ab52d145d78bb8da` (`Adopt revision 69 Draw Ready and Delay rules`).
- Implementation commit: `3b07d78` (`Implement Draw Ready and Delay Actions`). It contains 20 explicitly staged source/test files; `git diff --cached --check` passed and `tools/check_publication_safety.py --staged` reported 20 files, 0 findings.
- The source assignment was first committed at its original path in `17efa06` because it was untracked; `eb5effc0b37c1141937fcf68f5edb60381ee1781` then records both Git-aware moves, the process amendment, and maintained-reference updates. The moves are detected as renames (assignment 93%, report 85%).
- At the start of this archival execution HEAD was `6924777151bd955907379cca4f2167aaaf630cd1`; the archive/reference commit produced HEAD `eb5effc0b37c1141937fcf68f5edb60381ee1781`. The timestamped report closeout is a following report-only local commit.
- `git diff --cached --check` passed; `.venv/bin/python -B tools/check_publication_safety.py --staged` reported 7 staged files, 0 findings. Local Markdown links in all five changed documentation files were checked and resolve. The pre-existing unrelated untracked assignment files, saved Arena JSON and `docs/reports/U-REPO-010-report.md` were preserved and not staged. `.venv`, ignored `legacy/`, saved-world data, independent repositories and backups were not modified.
- No remote push or history rewrite was performed.

## Remaining limits

There is no genuine rule or external blocker for the accepted U-CAP-001 scope. Unimplemented Action families, optional Disarm variants, Event readiness, unrepresented drawable locations/hands, and broader world/UI/persistence work are precisely bounded and tracked separately. This assignment is complete (bounded).
