# U-CAP-008 — Two-sided generated Arena combat closeout

**Status:** Implementation acceptance criteria demonstrated; assignment remains ACTIVE pending ChatGPT review and acceptance.
**Assignment:** [`U-CAP-008`](../../assignments/archive/U-CAP-008.md)
**Repository:** Universe `main`; no push.
**Controlling Encounter rules:** adopted through revision 70 and applicable adopted supplements.

## Execution interval

- **Start time:** 2026-11-14T16:05:18-08:00 (America/Los_Angeles; captured when this execution began).
- **End time:** To be recorded immediately before final closeout.
- **Elapsed time:** To be calculated from the recorded Start and End timestamps.
- This was one continuous execution interval; active execution time equals the interval. No earlier start was inferred.

## Outcome

U-CAP-008's primary outcome was demonstrated in the actually served Chrome Arena using ordinary generated Beings and native Encounter state. The implementation adds user-visible melee result feedback derived from committed native receipts. The browser does not set facing, hit, damage, HP, or the opponent's Action state. Seed 14 is reproducible without patching rolls or changing NPC Generator data.

The player's generated Being and the independently generated opponent each had an actually represented Dagger in the native equipped inventory. The Chrome run used the normal generated-Being path (10000 starting experience, 10 × 5 map, `equipped`, `attack_only`, root seed 14, default ground profile), not an authored scenario. The actual server accepted a native Walk destination with `facing_policy=turn`. At native time 1 the player's committed position was `(6.86, 1.37, 0.0)` metres, presented as hex `(8, 1)`, facing orientation 5 of 12; the opponent had approached into represented reach. The player selected a legal four-second Dagger Thrust against the observer-authorized target.

At time 5 the native committed strike outcome was `normal` and its receipt contained a nonzero `DamageEffect` of 1. The opponent's HP changed from 17 to 16. The shipped browser displayed: **“Thrust · Dagger hit; native damage committed after 4 seconds.”** The independent `attack_only` opponent Thrust also resolved at that boundary; its native consequence reduced the player's HP from 25 to 23. Target inspection did not reveal the opponent's HP, XP, skill ranks, or native Being ID. At time 6 a subsequent opponent Thrust remained pending. The browser Save action produced the portable Encounter payload; the exact 2,362,407-byte response payload was read by a separate Python OS process without regeneration. That process verified seed 14, the time-6 checkpoint, the committed player hit and both HP results, then legally advanced to time 9 and verified that the pending opponent Action completed. This demonstrates both committed and pending combat restoration in the same exact fresh-process continuation.

The live Chrome encounter then continued from time 6. The player composed and submitted native **Ready Object · thrust** on the same held Dagger; it was accepted for time 6–7 and completed at time 7. While this ordered program was accepted, a second standalone Ready submission was correctly refused with “native Ready Choice was not accepted; Arena state is unchanged”; it did not replace or mutate the accepted program. The selected Dagger Thrust's displayed timing changed from four to three seconds. The player submitted that target-specific Thrust at time 7; at time 10 the UI showed **“Thrust · Dagger hit; native damage committed after 3 seconds.”** The opponent's strategy continued independently with another Thrust underway. Thus the same browser-played encounter included a real preparation Action followed by use of its prepared motion, as well as the initial committed hit and independent opponent response. No hit or state was injected.

## Acceptance matrix

| Criterion | Result | Evidence |
|---|---|---|
| A1 — Trace ordinary generated combat prerequisites and provenance | **Met** | Served Chrome seed 14 through ordinary generation; both native generated participants had an equipped Dagger. The test independently verifies native weapon identity. `npc-generator` was not modified. |
| A2 — Lawful movement, facing, reach and correction of the earlier refusal | **Met** | In Chrome, selected map hex `(8,1)`, Walk, and adopted `turn` facing policy; native state reported position/facing and target entered reach. The previous U-CAP-007 `not_facing` result was a valid native refusal; it is resolved here by the existing lawful movement/facing control, not by weakening facing or reach. |
| A3 — Select weapon Action and observe useful result without leaking target state | **Met** | Chose native Dagger Thrust through the shipped control. Browser feedback names the motion/weapon, reports native hit and committed damage, and reports timing. Target sheet remained observer-limited; focused privacy regression passed. |
| A4 — Scenario-authored facts only where required | **Met** | No authored scenario or generated-Being override was required. The ordinary generated/equipped path supplied the represented weapon prerequisite. |
| B1 — Reconcile prior `not_facing` demonstration | **Met** | The earlier refusal remains a genuine native result. Chrome reproduced the playable correction path using the server-accepted Walk + Turn control; no native eligibility rule was changed. |
| B2 — Consequential successful Chrome attack | **Met** | Seed 14 Chrome run; native `normal`, 1-point `DamageEffect`, opponent HP 17→16 at time 5. After actual Ready and preparation-sensitive timing changed 4→3 seconds, the follow-up native Thrust also displayed a committed hit at time 10. No forced roll, injected browser state or post-publication mutation. |
| B3 — Independent lawful opponent Action | **Met** | Existing `attack_only` strategy scheduled its own native Thrust; it resolved at time 5 and reduced player HP 25→23. A second opponent Thrust was pending at save time. |
| B4 — Preserve atomicity, interruption, defense, resource and privacy rules | **Met for this bounded exchange** | Both same-boundary Actions were resolved by the unchanged native common-snapshot Encounter. The implementation only projects committed native result facts. Existing focused melee, movement, Action-composition, observer privacy and persistence tests passed; no unrelated combat family was expanded. |
| C1 — Exact browser-created payload, fresh process, continuation | **Met** | Saved the exact payload served by the live Chrome Arena Save route (2,362,407 bytes); a separate Python OS process restored the same Encounter at time 6 and continued it to time 9. No NPC regeneration. Completed and pending Actions, identities, seed and HP were checked. |
| C2 — Shipped route, stale/forged handles, target selection and safe displays | **Met** | Shipped-JavaScript ordering and HTTP/session Action route passed. Focused regressions verified forged/stale handle refusal, valid opaque-handle selection, observer-safe inspection, and unavailable Action displays. The actual Chrome hit was initiated through the shipped controls. |
| C3 — Focused regression coverage | **Met for the changed path** | Seventeen distinct focused tests passed in five groups below, including seeded hit/fresh-process test, movement, Ready timing, Action composition, JavaScript control ordering, HTTP Save/Load, scenario selection/validation, failed/stale Choice handling and observer privacy. No full repository suite was run. |
| C4 — Reproducible human walkthrough | **Met** | Exact launch settings, browser interaction, boundary results and fresh-process continuation are documented below. |
| D — Task state, scope, safety and closeout | **Met, pending review** | U-CAP-007's accepted files were moved to archive and maintained references corrected. `TASKS.md` keeps U-CAP-008 ACTIVE pending review and does not close broader open Actions. Implementation is locally committed; scoped documentation closeout and required audits are recorded in Git. Unrelated staged paths and the untracked Arena save are preserved. No push. |

## Reproduction walkthrough and evidence levels

### Actual served Chrome

Launch from the Universe repository root:

```sh
PYTHONPATH=../npc-generator .venv/bin/python -B examples/generated_arena_browser.py --port 8008 --trace-ui
```

In Chrome open `http://127.0.0.1:8008/`. Generate an ordinary Arena with starting experience `10000`, map `10 × 5`, equipment `equipped`, opponent strategy `attack_only`, root seed `14`, and default ground profile. On the map choose destination `(8,1)`, rate `walk`, facing policy `turn`, and advance one native second. Verify the player is at represented hex `(8,1)` with native position `(6.86,1.37,0.0)` and facing 5/12; the opponent is now in reach. Open the opponent's observer-authorized target sheet and confirm private combat values remain unknown. From the player's own Action catalog choose Dagger `Thrust` against that opaque target handle and advance to time 5. The browser reports the native hit and damage consequence; the native opponent independently resolves its Thrust at that boundary. Advance to time 6, when its next Thrust is pending, and use **Save Encounter**. After fresh-process verification, continue the same live encounter: select the player's own held Dagger and submit **Ready Object · thrust** as a one-component native program; advance to time 7. Reselect the opponent and note Dagger Thrust now has three-second timing. Submit it through the native Action composer and advance to time 10; the shipped page reports the second native hit. The opponent strategy is independently underway again.

Chrome's Save control confirmed the portable download. The browser extension did not expose a manual file-picker Load interaction, so this report does not claim one. To verify the exact downloaded bytes, the 2,362,407-byte response from the live Save endpoint was read by a fresh Python OS process. That process restored time 6, checked the same seed, committed native strike facts, player/opponent HP and pending opponent Action, then advanced the restored Encounter to time 9 until that Action completed. No extension permission was changed. The report distinguishes the actual Chrome playthrough from this fresh-process verification.

### Shipped-JavaScript / HTTP and native fixtures

The focused browser-session suite exercises the same generated Arena JavaScript, opaque-handle routes, native Choice publication, generated Actions and portable Save/Load. The new end-to-end fixture verifies the exact seed-14 native weapon IDs/types, movement/facing and reach, player and opponent Actions, nonzero damage receipt, privacy projection, and a subprocess that restores and continues the same save. These tests corroborate the real-browser observation; they are not represented as a Chrome run.

## Focused verification

All commands used `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1` and the repository `.venv`.

**Generated browser/session group — 4 passed:**

```sh
PYTHONPATH=tests:src:examples:../npc-generator .venv/bin/python -B -m unittest \
  test_generated_arena_browser.TestGeneratedArenaBrowser.test_seeded_two_sided_browser_combat_hit_and_fresh_process_continuation \
  test_generated_arena_browser.TestGeneratedArenaBrowser.test_attack_only_browser_requests_drive_native_approach_and_thrust \
  test_generated_arena_browser.TestGeneratedArenaBrowser.test_actual_shipped_javascript_handlers_order_sprint_update_before_immediate_advance \
  test_generated_arena_browser.TestGeneratedArenaBrowser.test_pristine_arena_portable_save_load_and_native_activation -v
```

Result: **Ran 4 tests in 10.592s — OK.**

**Native melee and native-backed Arena route group — 4 passed** (run from `tests/`, where legacy fixtures resolve their relative config paths):

```sh
PYTHONPATH=.:../src:../examples:../../npc-generator ../.venv/bin/python -B -m unittest \
  test_melee_combat.TestMeleeCombat.test_timing_damage_armor_and_persistent_result \
  test_melee_combat.TestMeleeCombat.test_miss_does_not_damage_objects \
  test_arena_melee_attack.TestArenaMeleeAttack.test_native_strike_browser_route_and_pending_completed_save_load \
  test_arena_melee_attack.TestArenaMeleeAttack.test_attack_from_behind_uses_adopted_zero_target_defense -v
```

Result: **Ran 4 tests in 7.065s — OK.**

**Movement, composed Action, stale/forged selection and privacy group — 4 passed** (run from `tests/`):

```sh
PYTHONPATH=.:../src:../examples:../../npc-generator ../.venv/bin/python -B -m unittest \
  test_generated_arena_browser.TestGeneratedArenaBrowser.test_opt_in_draw_scenario_http_first_choice_and_forged_stale_refusal \
  test_generated_arena_browser.TestGeneratedArenaBrowser.test_display_name_overlay_is_safe_observer_scoped_and_replacement_atomic \
  test_generated_arena_browser.TestGeneratedArenaBrowser.test_destination_movement_activates_without_action_and_arrives_from_native_commits \
  test_generated_arena_browser.TestGeneratedArenaBrowser.test_general_action_program_composes_mixed_duration_touch_and_melee -v
```

Result: **Ran 4 tests in 6.627s — OK.**

**Ready timing and refusal/rollback group — 3 passed** (run from `tests/`):

```sh
PYTHONPATH=.:../src:../examples:../../npc-generator ../.venv/bin/python -B -m unittest \
  test_generated_arena_browser.TestGeneratedArenaBrowser.test_generated_ready_delay_http_controls_and_visible_motion_timing \
  test_generated_arena_browser.TestGeneratedArenaBrowser.test_native_invalid_first_choice_leaves_unstarted_arena_unchanged \
  test_generated_arena_browser.TestGeneratedArenaBrowser.test_movement_activation_rolls_back_without_choice_or_rng_changes -v
```

Result: **Ran 3 tests in 1.500s — OK.**

**Authored-scenario/ordinary-generation control group — 2 passed** (run from `tests/`):

```sh
PYTHONPATH=.:../src:../examples:../../npc-generator ../.venv/bin/python -B -m unittest \
  test_generated_arena_browser.TestGeneratedArenaBrowser.test_opt_in_scenario_selection_and_exact_fresh_process_continuation \
  test_generated_arena_browser.TestGeneratedArenaBrowser.test_actual_shipped_javascript_runs_fresh_authored_draw_scenario -v
```

Result: **Ran 2 tests in 3.465s — OK.**

Total: **17 distinct focused tests passed.** The first attempt to run the native-melee pair from the repository root failed because those older fixtures resolve `../src/config/*.tsv` relative to `tests/`; rerunning the identical pair from the test directory loaded fixtures and all tests passed. This was a test working-directory issue, not an implementation failure. The complete repository test suite was not run.

## Implementation, scope and limitations

`src/arena_browser_session.py` now projects a completed melee result label, weapon display name and a boolean indicating a positive committed native `DamageEffect`; it retains the native outcome, duration and impact distance. `examples/arena_web.py` renders that receipt-backed information in the shipped UI. It does not expose damage amount, opponent HP, native IDs or hidden Being facts. `tests/test_generated_arena_browser.py` adds the seeded, subprocess-backed regression. Native movement, orientation, attack, timing, opponent strategy, RNG and persistence implementations were already present and were not bypassed or relaxed.

Bounded limitation: a manual browser file-picker Load was not demonstrated because the extension's local file upload capability is unavailable in this session. The exact payload returned by the live browser Save route was independently restored in a fresh Python OS process and continued. No uncertainty remains for the assignment's required fresh-process Save/Load continuation. Broader Shoot, Deflect, Throw variants, other open Actions, shield transitions, general combat expansion, and local `src/location.py` issues are separate `TASKS.md` work and were not pulled into U-CAP-008.

## Task state, Git and safety

- U-CAP-007 is accepted DONE (bounded); its assignment and consumed report are archived under `docs/assignments/archive/` and `docs/reports/archive/`. `git mv` was used, and content is preserved. The explicit scoped commit recorded archived-path additions in `f9989536b994593f5d5890f993220f1cc12a94b4` and active-path removals in `958843c55586f2f3a92a1b5045a9e5837c387877`, rather than one rename-detection commit; original source-path history remains reachable, but Git does not infer path continuity across those commits. No history rewrite was authorized or performed. `TASKS.md`, this assignment, the maintained continuation handoff, and the archived assignment's own links point to the archived paths.
- `TASKS.md` records the verified U-CAP-008 result but leaves it **ACTIVE pending ChatGPT acceptance**. No broader Action or active program was marked DONE.
- Implementation commit: `56d00a4596d2a5d159e60c1f116d961b2e07155f` (`Show native melee consequences in generated Arena`).
- Documentation/archive commits: `f9989536b994593f5d5890f993220f1cc12a94b4` (TASKS, handoff, active assignment/report and archived copies) and `958843c55586f2f3a92a1b5045a9e5837c387877` (active source-path removals).
- Five pre-existing user-staged historical archive paths remain untouched by the scoped implementation commit: four U-CAP-002/U-CAP-003 active-path deletions and the U-THROW-001 patch archive rename. The untracked, structurally valid but incompatible `docs/assignments/universe-arena.json` save remains unmodified and unstaged.
- Before the documentation commit, `git diff --cached --check` passed and `tools/check_publication_safety.py --staged` reported `staged-audit files=13 findings=0 result=PASS`. The implementation commit was scoped to the three reviewed code/test paths. Final documentation audit and worktree/index evidence will be recorded below.
- No push, force operation, save mutation, environment replacement, or unrelated repository modification occurred.

### Final closeout evidence

- Maintained-link check covered `TASKS.md`, the continuation handoff, active U-CAP-008 assignment, archived U-CAP-007 assignment, and this report: **5 files checked, 0 missing links**. `git diff --check` passed.
- Final staged publication-safety audit before the report closeout commit: **`staged-audit files=10 findings=0 result=PASS`**; `git diff --cached --check` passed. The audit included the four reviewed documentation updates and preserved the five pre-existing historical archive paths.
- HEAD before this final report correction: `958843c55586f2f3a92a1b5045a9e5837c387877`. Substantive commits: `56d00a4596d2a5d159e60c1f116d961b2e07155f` (native receipt projection, shipped UI result and seeded subprocess regression), `f9989536b994593f5d5890f993220f1cc12a94b4` (accepted U-CAP-007 archived copies, U-CAP-008 assignment/report, TASKS and handoff), and `958843c55586f2f3a92a1b5045a9e5837c387877` (U-CAP-007 active source removals). The final report correction is a separate scoped documentation commit; its resulting HEAD is supplied in the Codex closeout.
- After the scoped commit, the index is expected to retain only the five pre-existing staged archive paths: deletions of the U-CAP-002/U-CAP-003 assignments and reports, plus the U-THROW-001 patch archive rename. `docs/assignments/universe-arena.json` remains untracked and untouched. No U-CAP-008 implementation or report files remain unstaged.
- **End time:** 2026-11-14T16:44:49-08:00 (America/Los_Angeles; captured immediately before final report closeout).
- **Elapsed time:** PT39M31S, calculated from the recorded Start and End timestamps.
