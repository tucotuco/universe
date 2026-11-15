# U-CAP-008A — Arena versus Arena

## Current result

**Implementation outcome met for U-CAP-008A; awaiting ChatGPT acceptance.** The assignment and report remain active until that review. No remaining independently implementable acceptance item is known. The generated Arena now has Player vs Arena and Arena vs Arena modes. Arena vs Arena selects attack_only or defense_only separately for Being A and Being B. Both use the existing native decision helpers, Choice scheduler, movement intents, and atomic Encounter publisher. A bounded spectator runner advances at most ten native seconds and can be paused between boundaries.

Start: **2026-11-14T17:19:13-08:00** (recorded at execution start). End and elapsed are pending final closeout.

## Authority and repository state

- Repository: active Universe checkout, branch main.
- Starting HEAD: 5062199c15b44e0b9a2526a3f4116de757ff9f8d.
- Adopted Encounter authority: revision 70 and applicable adopted supplements. This assignment changes control ownership, not combat resolution.
- U-CAP-008 was accepted DONE (bounded) before this assignment. Its assignment/report are moved with git mv to docs/assignments/archive/U-CAP-008.md and docs/reports/archive/U-CAP-008-report.md; maintained task and handoff links now point there.
- The installed assignment refers to a previously drafted U-CAP-009 perception assignment, but no such file or historical path exists in this checkout. The stable U-CAP-009 in the live register is already general global simulation time/events. To preserve stable-ID identity and the requested deferral without overwriting the register, perception remains DEFERRED under U-OBS-001; neither perception nor global-time work is being executed.
- Initial unrelated staged state is being preserved: removals of active U-CAP-002/U-CAP-003 assignment/report copies and the U-THROW-001 patch archive move. The untracked docs/assignments/universe-arena.json remains untouched and unstaged.

## Implemented

- Added server-authoritative encounter_mode and two strategy slots. Legacy opponent_strategy remains for Player vs Arena compatibility. Invalid mode/strategy combinations are rejected before replacing the active candidate.
- Generalized existing attack/defense decision and scheduling helpers to either participant. In Arena vs Arena both decisions are derived before either controller's proposal is scheduled, then sent through the existing native scheduler. Decisions read the acting Being's own current Awareness/evidence and native state.
- When starting an unactivated Arena-vs-Arena Encounter, the first native Run Choice activates the Encounter using the existing native activation contract; no client-issued Being Action is needed.
- Both movement intents use one pre-movement snapshot. If independently legal approaches choose the same hex, a deterministic pairwise resolver chooses the minimum-cost distinct pair from both controllers' computed legal options; if no pair exists, both defer. No initiative is assigned by loop order.
- Added an explicitly labeled read-only spectator/referee chronology for committed melee and defense Actions and native damage. It is distinct from Being observation ledgers and is never consulted by strategy code. The ordinary observer view continues to use Being A's own ledger.
- Added a ten-second maximum browser spectator run, one-second Advance, and Pause between committed boundaries. A stable/no-legal-action refusal stops the run. Manual movement and Action controls are hidden in spectator mode, and the generated HTTP server rejects manual Being endpoints in that mode.
- Bumped generated Arena checkpoint schema to /7, preserving exact mode and per-Being strategy assignments. Schemas /6, /5, and /4 migrate explicitly to Player vs Arena, with only the historical opponent strategy assigned to Being B. Strict canonical bytes, checksum and native validation remain in force.
- Focused coverage tests ordinary seed-14 A-v-A combat, per-side native Actions, committed damage, HTTP manual-control refusal with unchanged time/Choices/RNG, invalid-mode transactional replacement, JSON-safe view projection, and exact uninterrupted-versus-fresh-process continuation.

## Served Chrome demonstration

- Server: examples/arena_web.py via serve_local(0) on loopback; served URL during demonstration: http://127.0.0.1:64008/.
- Inputs: root seed 14; starting XP 1000; map 5 × 5; equipped generated Beings; ordinary NPC generation; mode Arena vs Arena; Being A attack_only; Being B defense_only. No tactical command was issued for either Being.
- Chrome selected the two distinct strategies, generated both Beings, and ran the bounded spectator control for ten seconds. The page displayed native Action results and the separate spectator chronology.
- Native timeline: Being B accepted native Dodge preparation at t=0, ready at t=2; Being A scheduled native Dagger Thrust at t=2, resolved normally at t=6 for 2 HP damage; Being B's native Dodge failed at t=6; Being A's next Thrust, scheduled at t=6, resolved normally at t=10 for 4 HP damage. Being B independently scheduled further native Dodge preparations. Native HP at t=10 was [6, 4] (Being A, Being B).
- The browser Save Encounter control was clicked. Exact endpoint bytes from that served session were captured for fresh-process verification: 3,318,101 bytes; SHA-256 16f7a3645ec24d69ca14b0ff72e90885642f388cf5868e83a3253490876865bf. The pre-existing user Arena download was not touched.
- A separate OS process loaded those exact bytes with GeneratedArenaSession.load_encounter_bytes (no regeneration), restored mode/strategies, both participant IDs, native time 10 and HP [6,4], then advanced three more native seconds to t=13 with the same controllers and native Action chronology. Focused coverage also compares uninterrupted and restored continuation.

## Acceptance matrix (current)

| Area | Status | Evidence / remaining check |
|---|---|---|
| Default Player vs Arena retained | Met | Mode remains the default; accepted U-CAP-008 seed-14 served-Chrome evidence is preserved. Existing generated-browser regressions cover human movement/Action and opponent behavior. |
| Two modes, independent strategies, server validation | Met in implementation | Browser showed A=attack_only, B=defense_only; invalid pair refuses without replacing active session. |
| Independent decisions, common snapshot, deterministic native scheduling | Met in implementation | Actor-specific native controllers; common-snapshot pairwise movement conflict handling; fixed-seed/fresh-process focused test. |
| Actual native combat and nonzero committed effect in served Chrome | Met | Chrome seed-14 timeline; Being A Thrust committed 2 and 4 damage at boundaries 6 and 10. Being B independently scheduled native Dodge. |
| Spectator controls and stable stopping | Met in implementation | One-second step; bounded ten-second run; Pause between boundaries; stop on refusal/no legal Action. |
| Observation/privacy separation | Met in implementation | Controllers use their own ledgers; spectator chronology is labeled separate and read-only; no native IDs exposed. |
| Exact fresh-process checkpoint continuation | Met | Served-session save SHA above; separate process restored at t=10 and continued to t=13. |
| Backward Save/Load compatibility | Met | Schema 7 validates mode/controller fields; legacy schemas 4–6 migrate to Player vs Arena. Legacy fixture and all eight Arena persistence tests pass. |
| Scoped commits, final focused results, worktree/index inventory | Met | Code commit ef71e42514094d2372b976be5d64acf3ea077fa9; documentation/archive commit and final audits are recorded below. |

## Focused verification

All commands ran with the repository .venv, no user-site imports, and bytecode writes disabled.

1. P-vs-A and opponent regression cohort:

    PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 .venv/bin/python -B -m unittest tests.test_arena_opponent_attack tests.test_arena_vs_arena tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_seeded_two_sided_browser_combat_hit_and_fresh_process_continuation tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_generate_page_exposes_profile_chooser_upload_and_native_equipment_mode tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_attack_only_browser_requests_drive_native_approach_and_thrust -q

   **19 passed** in 63.839 s.

2. Full focused Arena persistence module:

    PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 .venv/bin/python -B -m unittest tests.test_arena_persistence -q

   **8 passed** in 14.903 s.

3. Final implementation/UI/persistence smoke:

    PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 .venv/bin/python -B -m unittest tests.test_arena_vs_arena tests.test_arena_opponent_attack.TestArenaOpponentAttack.test_old_arena_save_schema_loads_with_autonomous_strategy_disabled tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_generate_page_exposes_profile_chooser_upload_and_native_equipment_mode tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_actual_shipped_javascript_handlers_order_sprint_update_before_immediate_advance tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_seeded_two_sided_browser_combat_hit_and_fresh_process_continuation -v

   **8 passed** in 18.526 s. A subsequent focused run after final controller tie-cost and legacy-fixture refinements ran Arena-vs-Arena, schema-migration, page, and shipped-JavaScript tests: **7 passed** in 14.560 s.

4. Python compilation passed for examples/arena_web.py, src/arena_browser_session.py, src/arena_persistence.py, and changed Python tests. Markdown link check: **71 checked, 0 broken**. git diff --check passed. Staged publication-safety audit: **16 staged files, 0 findings**.

No full repository suite was run; the assignment calls for focused checks, and no unrelated subsystem was changed.

## Task state and publication safety

- TASKS.md: U-CAP-008 → DONE (bounded), with archived links; U-CAP-008A → sole ACTIVE assignment; perception remains deferred under U-OBS-001; the established U-CAP-009 global-time ID is preserved.
- No push, force operation, or history rewrite.
- Local implementation commit: ef71e42514094d2372b976be5d64acf3ea077fa9 (Arena mode, scheduler, persistence and focused tests). Documentation/archive commit: pending.\n- No push. The pre-existing four U-CAP-002/U-CAP-003 staged removals and U-THROW-001 patch archive rename remain outside these commits. The untracked docs/assignments/universe-arena.json remains untouched.\n- Final HEAD, final staged/untracked inventory, documentation commit hash and actual End/Elapsed timestamps will be filled after the scoped documentation commit and last safety audit.
