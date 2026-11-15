# U-CAP-007 — Generated Arena Actions: engineering closeout

**Status:** DONE (bounded), submitted for ChatGPT review; this report and the assignment remain in the active directories pending review/consumption.

**Controlling Encounter rules:** revision 70.

**Repository:** active Universe checkout, local `main`; no push.

## Execution interval

- Start time: `2026-11-14T11:21:02-08:00` (recorded when this execution began; America/Los_Angeles).
- End time: `2026-11-14T15:46:43-08:00` (America/Los_Angeles; captured immediately before this final report-only closeout correction).
- Elapsed time: `PT4H25M41S` (calculated from the recorded start and end timestamps).

## Outcome

U-CAP-007's supported generated-Arena browser outcome is implemented and demonstrated. The browser can show the player's currently derived native Action catalog while inspecting an opposing Being, preserve the opponent's observer-limited character projection, submit Actions through existing native routes, and save portable native state. An explicitly opt-in, reproducible Ordinary Dagger Draw scenario supplies only its stated scenario facts before Encounter publication; ordinary generation remains available and does not silently substitute those facts.

The central defect was projection plumbing: the opponent Being popup rendered `selected_being` with no Action context, even though the server's public state contained the player's `action_catalog`. The popup therefore showed Actions as unknown and exposed no way to select the player's Actions against that target. The UI now renders the observer-safe opponent sheet and, separately, the player's server-generated catalog labeled `Your Actions targeting <Being>`. It displays available/unavailable/not-implemented status and reasons. Opaque handles remain server-issued, all declarations are revalidated by the existing native routes and validators, and the UI adds no combat resolver.

## Action inventory reconciliation

The target popup's `67 potential` count is the number of native Action-catalog entries in the generated profile at the observed state; it is not a claim that all 67 are executable. Each entry uses the server-projected status: `available` means its connected native contract currently accepts a Choice, `unavailable` means a supported Action is blocked by represented current facts, and `not implemented` means the catalog label has no connected generated-Arena submission/resolution contract. Target-specific controls use opaque handles and current observer evidence. Existing U-ACT entries and their narrower OPEN/partial limits remain unchanged; U-CAP-007 adds visibility and selection for already-supported Actions, not implementation of every catalog item.

## Acceptance matrix

| Criterion | Result | Evidence |
|---|---|---|
| A — Identify/fix Action availability and observer projection | PASS | Reproduced on served Chrome. Target Being popup now renders the player's 67-potential Action catalog while unknown opponent skills, conditions, hands, inventory, XP and other private facts remain unknown. Updated shipped-JavaScript harness asserts the catalog appears without inventory/XP leakage. Native validation remains authoritative. |
| B — Reproducible supported scenario and consequential sequence | PASS (bounded) | Opt-in `Ordinary Dagger Draw · authored carried Dagger` keeps normal generation intact. Chrome generated seed `20261126`, XP `10000`, map `10×5`, unequipped protagonists, and no autonomous opponent behavior. Native Run activated the Encounter; a Sprint movement plan committed two segments. Draw completed successfully at time 3 and left the same Dagger readied in the left hand. Dagger Thrust was accepted at time 4 and resolved at time 8 as `not_facing`; the visible result, target, action time, identity and position were real native state. No damage/geometry or success was fabricated. |
| C.1 — Exact persistence and fresh-process continuation | PASS | `test_opt_in_scenario_selection_and_exact_fresh_process_continuation` writes an executing Draw save, restores it in a separate Python OS process, advances both native seconds, saves completion, then restores the completed save in a second Python OS process and verifies the same scenario and readied Dagger. Additionally, the completed save downloaded by Chrome was loaded in a fresh Python OS process: restored time 8, scenario `ordinary-dagger-draw`, position `(3.69, 2.28, 0)`, Dagger `readied in left hand`, Draw `success`, Thrust `not_facing`. That process legally accepted Delay and advanced the same Encounter to time 9 with Delay `success`. The save retained native identity/provenance and RNG cursor. Existing portable-save regression verifies player/opponent native identity, current/original state, positions, awareness and perception-ledger history, plus RNG cursor equality and exact movement continuation across a fresh session. |
| C.2 — Served JavaScript/HTTP and local Chrome walkthrough | PASS (Load method bounded) | Actual Chrome generated the opt-in scenario, opened the player and opposing Being panels, selected a Dagger Action, advanced native time, showed Draw success and Thrust's native `not_facing` result, and used Save Encounter. The downloaded Chrome save was subsequently restored and continued as detailed above. The browser extension's `fileChooser.setFiles` refused to choose a local save because its global “Allow access to file URLs” permission is disabled. No extension permission was changed. The HTML Load control and HTTP/native portable-load routes are covered by `test_http_save_and_load_use_binary_portable_file_and_atomic_replacement`; loading was not manually clicked in Chrome. |
| D.1 — Project state and bounded Action inventory | PASS | `TASKS.md` records U-CAP-007 as DONE (bounded; review pending), preserves narrower OPEN Action families, and links this active report. U-CAP-006 archive state and revision 70 remain controlling. This work repairs Action visibility and does not implement unrelated combat Actions. |
| D.2 — Report/evidence | PASS | This report records browser-vs-test evidence, exact test names, limitations, commits and repository/index status. |
| D.3 — Focused verification | PASS | Eight focused tests passed; exact invocations and results are below. No full repository suite was run. |

## Scenario facts and safety boundaries

- The selectable scenario is hidden unless a configured, validated scenario is available. Selecting it explicitly sets unequipped generated protagonists and disables autonomous opponent actions; changing back selects ordinary generation and its normal equipment/strategy defaults.
- The generated NPC specifications still come from the independent `npc-generator`. Before Encounter publication, the authored scenario creates one native Dagger owned by the generated player, records explicit scenario provenance, supplies the stated worn-sheath source and free-hand starting condition, and places it in carried custody.
- Persistence schema advanced to `universe.generated-arena-save/6`; previous schema 5 and 4 remain readable. Schema 6 requires explicit scenario metadata, and Load cross-checks scenario metadata against the owner-linked native Dagger source tag. No NPC regeneration occurs on Load.
- The Action selector consumes the server's player-authorized projection. The target Being sheet continues to withhold unobserved character facts; selecting its panel does not promote unknown facts to known values.
- The actual Chrome strike outcome was `not_facing`. This is reported as the native outcome, not a successful hit or damage demonstration. Drawing the Dagger, movement, elapsed time, native Action scheduling, target result, Save/Load, and legal post-load Delay continuation are the demonstrated supported capability.
- Chrome file-selection automation would require granting the extension local-file access. That permission was not changed; the exact browser-created save was instead verified through a separate fresh Python process and the shipped HTTP/native Load contract tests.

## Focused tests

All eight tests passed, in three focused invocations:

```text
test_generated_arena_browser.TestGeneratedArenaBrowser.test_opt_in_scenario_selection_and_exact_fresh_process_continuation — ok
test_generated_arena_browser.TestGeneratedArenaBrowser.test_actual_shipped_javascript_handlers_order_sprint_update_before_immediate_advance — ok
test_generated_arena_browser.TestGeneratedArenaBrowser.test_actual_shipped_javascript_runs_fresh_authored_draw_scenario — ok
test_generated_arena_browser.TestGeneratedArenaBrowser.test_character_sheet_reads_native_state_without_history_or_opponent_disclosure — ok
test_generated_arena_browser.TestGeneratedArenaBrowser.test_generate_returns_only_player_allowlist_and_rename_preserves_native_identity — ok
test_generated_arena_browser.TestGeneratedArenaBrowser.test_strict_server_inputs_and_failed_regeneration_leave_active_session_unchanged — ok
test_generated_arena_browser.TestGeneratedArenaBrowser.test_pristine_arena_portable_save_load_and_native_activation — ok
test_generated_arena_browser.TestGeneratedArenaBrowser.test_http_save_and_load_use_binary_portable_file_and_atomic_replacement — ok
Ran 3 tests in 4.894s — OK
Ran 3 tests in 0.499s — OK
Ran 2 tests in 1.893s — OK
```

Exact invocations:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest test_generated_arena_browser.TestGeneratedArenaBrowser.test_opt_in_scenario_selection_and_exact_fresh_process_continuation test_generated_arena_browser.TestGeneratedArenaBrowser.test_actual_shipped_javascript_handlers_order_sprint_update_before_immediate_advance test_generated_arena_browser.TestGeneratedArenaBrowser.test_actual_shipped_javascript_runs_fresh_authored_draw_scenario -v
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest test_generated_arena_browser.TestGeneratedArenaBrowser.test_character_sheet_reads_native_state_without_history_or_opponent_disclosure test_generated_arena_browser.TestGeneratedArenaBrowser.test_generate_returns_only_player_allowlist_and_rename_preserves_native_identity test_generated_arena_browser.TestGeneratedArenaBrowser.test_strict_server_inputs_and_failed_regeneration_leave_active_session_unchanged -v
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest test_generated_arena_browser.TestGeneratedArenaBrowser.test_pristine_arena_portable_save_load_and_native_activation test_generated_arena_browser.TestGeneratedArenaBrowser.test_http_save_and_load_use_binary_portable_file_and_atomic_replacement -v
```

Additional exact-file fresh-process check: loaded the save downloaded by Chrome into a new `GeneratedArenaSession`, verified persisted scenario, time, position, Dagger identity/custody, completed Draw and Thrust receipts and RNG cursor, then scheduled and completed native Delay at time 9. The actual result was Draw `success`; Thrust `not_facing`; Delay `success`.

## Commits and repository audit

- `02f72d2dd94f07198515489e9fc8b6adb4221763` — archived accepted U-CAP-006 closeout, reconciled TASKS/handoff, and installed U-CAP-007 assignment.
- `a5cff346a4363c3e0525ba652177c03fe78ca324` — completed U-CAP-006 active-path removals after its archive copies.
- `73171f8ed904bb20e3306e451ba62a71814f6de1` — `Make generated Arena Actions playable`; six reviewed source/test paths only.
- `843135e8f244d0afd534439d3969064935aa1b8a` — `Close out U-CAP-007 generated Arena browser`; scoped TASKS and report commit.

Before the implementation commit, `git diff --cached --check` passed and `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 .venv/bin/python -B tools/check_publication_safety.py --staged` reported `staged-audit files=12 findings=0 result=PASS`. The implementation commit used `git commit --only` for the six reviewed files.

Five unrelated user-staged historical archive paths remain staged and unchanged:

```text
D docs/assignments/U-CAP-002.md
D docs/assignments/U-CAP-003.md
D docs/reports/U-CAP-002-report.md
D docs/reports/U-CAP-003-report.md
R docs/reports/U-THROW-001-rule-sync-proposal.patch -> docs/reports/archive/U-THROW-001-rule-sync-proposal.patch
```

`docs/assignments/universe-arena.json` is also untracked in the worktree; it was preserved and not staged or inspected as part of this assignment. No push occurred. After the two U-CAP-007 commits, `HEAD` was `843135e8f244d0afd534439d3969064935aa1b8a`; the tracked worktree was clean and exactly the five historical archive paths above remained staged. The untracked Arena save remained untouched. A final report-only timestamp correction follows this closeout commit.

## Bounded limitation and review disposition

The generated opponent profile does not gain invented body geometry, skill, equipment, or behavioral Actions. Many catalog rows correctly remain unavailable or not implemented. The tested Dagger Thrust completed as `not_facing`; this assignment does not change orientation, attack, or damage rules. Manual selection of the downloaded save in Chrome remains unverified because the extension's local-file permission is off, although the exact Chrome-produced file was loaded in a fresh Python process and continued, and the browser Load route has focused atomic Save/Load coverage. U-CAP-007 is submitted as DONE (bounded) for ChatGPT review; the broader Action program stays open as recorded in `TASKS.md`.
