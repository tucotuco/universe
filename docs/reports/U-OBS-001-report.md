# U-OBS-001 — Playable perception and observer-owned evidence

## Current outcome

**ACTIVE — acceptance criteria remain incomplete.** This execution adds truthful observer-history presentation, adopted discovery aptitude/modifier helpers, and verification repairs. It does not claim a complete playable discovery lifecycle. No new Encounter rules were adopted.

### Execution interval

- Start: **2026-11-14T22:34:58-08:00** (captured at first repository inspection)
- End: pending immediate closeout capture
- Elapsed: pending calculation from the captured timestamps

## Assignment and program state

- U-PLAYTEST-001 was accepted DONE and consumed by ChatGPT. Its assignment/report were Git-moved to `docs/assignments/archive/U-PLAYTEST-001.md` and `docs/reports/archive/U-PLAYTEST-001-report.md`; maintained references and `TASKS.md` were repaired in commit `37b7c3590ba384558665c97637af2eee69983bf6`.
- The frozen external release at `~/Projects/universe-arena-playtest/U-CAP-008A-2026-11-14/` was left unchanged. No other repository, backup, `.venv`, ignored `legacy/`, or local save was modified.
- `TASKS.md` retains U-OBS-001 as the sole ACTIVE program. U-ACT-037 remains DONE (bounded), U-ACT-038 is corrected to OPEN, U-SPOT-002 remains OPEN, and U-ACT-039 remains VERIFY. No Search-specific stable ID was found, so none was invented or recycled.
- The unrelated pre-existing staged archive deletions and U-THROW-001 rename remain staged and excluded from this work. `docs/assignments/universe-arena.json` remains untracked and untouched.

## Criterion status

| Area | Verified result | Remaining acceptance work |
| --- | --- | --- |
| A — native contract | Existing six-second native Spot, target-free `accept_spot_attention`, exact default/explicit DC, success/failure, no Spot XP, and fail-closed missing geometry are verified. Adopted Search/Spot/Listen racial bonuses and Hearing DC inputs now have closed helpers and tests. | Search/Listen transactional Actions, authored audibility/examination evidence, incidental event-triggered checks, and current native location/event receipt adapters. |
| B — evidence/knowledge | Revision-65 Arena ledger stores observer-owned current evidence and immutable change history; interval publication derives from the same committed snapshot. Generated UI now separates the current entity view from that Being’s history. Public history uses opaque handles and only rows in that observer’s ledger. | Supported loss-of-perception/stale-vs-current state, Action/Event observation, sound/occlusion models, and a committed same-world demonstration of divergent observer evidence remain absent. Do not manufacture these facts. |
| C — generated Arena/Chrome | Arena Action catalog now reports Search/Listen as `not_implemented` and Spot as `unavailable` with bounded reasons. Served Chrome generated seed 20261114: generated the ordinary Arena, opened the observer’s visible Being, and verified the history panel showed the initial observer-owned record while private fields remained `Unknown`. | A successful native discovery cannot be exercised through ordinary generated Arena: r65 already exposes the unobstructed opponent, and generated Beings have no represented geometry. Existing test-only prepublication geometry proves native Spot success/failure, not browser discovery. No browser Action/Event or stale-tracking sequence was claimed. |
| D — privacy/persistence/regressions | AI privacy and initial Arena perception tests passed. A new fresh-OS-process generated-Arena Save/Load test verifies exact current/history projections. Strict per-ledger checkpoint encoding remains closed; a stale checkpoint assertion was corrected to match the actual fail-closed Encounter field-policy refusal. | Pending discovery receipts, failed/acquired Search/Listen receipts, last-known vs currently-visible Save/Load, observed opponent Action/Event continuation, and both-mode regression for those perception features. |

## Evidence and limits

- Native Spot fixture: `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 .venv/bin/python -B examples/generated_arena_spot_geometry.py` — DC 1 succeeds at t=6 with one observer gaining awareness and one location receipt; DC 100 fails at t=6 without awareness/evidence. Fixture uses explicit test-only Sphere geometry and an already initiated native Encounter; it is not production NPC geometry or a generated-Arena UI flow.
- Generated Arena public history is projected from `player.native.being._arena_perception_ledger.history`; native Entity IDs are replaced by the session opaque handle. Current view remains from the same observer ledger. Search/Listen catalog entries disclose fixed implementation state, not hidden-target counts or identities.
- Chrome served from this checkout at `http://127.0.0.1:50519/`: generated seed 20261114, opened the visible Being’s dialog; it showed its observed name/position and reported unobserved race, age, statistics, skills and condition as unknown. The dedicated observation-history panel displayed the time-zero record. This browser check was not a discovery action and is reported as such.
- Persistence test `tests.test_arena_persistence.TestArenaPersistence.test_observer_current_view_and_history_restore_in_fresh_process` compares the current and historical observer projections before Save and after a separate `python -S` process loads the save. This is initial Arena evidence only, not pending or failed discovery receipts.
- Baseline cohort findings: `tests.test_generated_arena_browser` initially ran 72 tests with one subprocess import-path error; that isolated child now receives explicit `src` PYTHONPATH and the exact failing test passes. The full 72-test cohort was not repeated. `tests.test_arena_opponent_attack` and `tests.test_arena_initialization` passed 19 tests together. A checkpoint closure test had expected an obsolete `bounded_run_spot_closure_verified` diagnostic; current strict field policy correctly refuses on uncovered `encounter.Encounter` fields. The test now asserts that precise refusal; no checkpoint acceptance/fingerprint rule was weakened.
- No sound attenuation, hearing opportunity source, visual blocking, generated Being geometry, acceleration, uncertainty or event-observability model was added. Rules and source facts required for those demonstrations are not represented.

## Exact verification commands

- `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 .venv/bin/python -B -m unittest tests.test_spot_action tests.test_generated_arena_spot_readiness tests.test_checkpoint_arena_perception -q` — **20 tests passed** after the initial repair iteration.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 .venv/bin/python -B -m unittest tests.test_arena_initialization tests.test_arena_opponent_attack -q` — **19 tests passed** in 53.885 s.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 .venv/bin/python -B -m unittest tests.test_arena_persistence.TestArenaPersistence.test_observer_current_view_and_history_restore_in_fresh_process -q` — **1 test passed**.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 .venv/bin/python -B -m unittest tests.test_generated_arena_browser -q` — **72 tests, 1 subprocess import-path error**; corrected the test child environment. The exact failed case then passed:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 .venv/bin/python -B -m unittest tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_generated_multiple_grapple_break_program_uses_native_choice_and_abort -q` — **1 test passed**. Full cohort not rerun.
- Final combined focused rerun: `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 .venv/bin/python -B -m unittest tests.test_spot_action tests.test_generated_arena_spot_readiness tests.test_checkpoint_arena_perception tests.test_arena_persistence.TestArenaPersistence.test_observer_current_view_and_history_restore_in_fresh_process tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_generated_multiple_grapple_break_program_uses_native_choice_and_abort -q` — **22 tests passed** in 8.587 s.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 .venv/bin/python -B examples/generated_arena_spot_geometry.py` — both the explicit native Spot success and failure scenarios reproduced at boundary 6.

## Changes in this execution

- `src/discovery.py`: apply adopted Elf/Half-elf aptitude bonuses to Search, Spot and Listen; add Gnome/Halfling Listen +2; define closed Hearing DC conditions and impossible silence/deaf cases.
- `src/arena_browser_session.py` and `examples/arena_web.py`: expose this observer’s known observation history separately from current evidence and report Search/Listen as not implemented in the generated-Arena Action catalog.
- Tests: adopted discovery aptitude/Hearing table, generated UI privacy/status, strict checkpoint refusal, subprocess `PYTHONPATH` repairs, and fresh-process observer-evidence Save/Load.

## Commits and repository safety

- Prior archival/resumption commit: `37b7c3590ba384558665c97637af2eee69983bf6`.
- This execution’s implementation/documentation commit and audit result: pending.
- No push was authorized or attempted.
- Final status, staged path inventory, `git diff --cached --check`, publication-safety audit result, focused rerun, and final commit hash will be inserted immediately before closeout.
