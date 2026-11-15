# U-OBS-001 — Playable perception and observer-owned evidence

## Current status

**ACTIVE — acceptance criteria remain incomplete.** Observer-owned current and historical evidence, committed motion intervals, visibility transitions, and a bounded target-free Spot lifecycle are implemented. The explicit authored native Spot flow succeeds and survives fresh-process Save/Load. The served-browser route accepts Spot but the live exercise performed in this execution resolved `no_clear_path`; do not claim browser acceptance. Search/Listen execution, incidental event discovery, and Action/Event evidence remain open. No new Encounter rules were adopted.

## Execution interval

- Start: **2026-11-14T22:34:58-08:00** (captured at first repository inspection)
- End: **2026-11-14T23:44:32-08:00** (captured from the execution clock immediately before closeout)
- Elapsed: **PT1H9M34S**

## Criterion matrix

| Assignment area | Verified | Remaining |
| --- | --- | --- |
| A — native discovery contract | Adopted discovery aptitudes and integer Hearing modifiers have closed helpers/tests. Native Spot is six seconds, target-free where the authored scenario permits; success and failure outcomes are exercised. Default/explicit DC and fail-closed unmodeled targets remain tested. | Native Search/Listen Actions, authored audibility/examination evidence, meaningful incidental opportunity processing, and Action/Event discovery receipts. |
| B — observer evidence | Each Being owns a strict current/known evidence ledger. Authored opaque geometry suppresses initial perception; later visibility transitions preserve last-seen position/time. Committed movement-segment evidence is sourced from the native movement receipt, not inferred velocity. The generated Spot test proves one observer learns the other while the target observer does not learn the actor. | Apparent Action/Event evidence and broader independently divergent perception cases. Ordinary generated Beings still have no adopted geometry model. |
| C — Arena and browser | The opt-in prepublication scenario authors an explicit target Sphere and opaque screen. The player projection omits the hidden target until native Spot succeeds and exposes no internal target ID. Browser control submits the native Choice. | The served Chrome run in this execution did not reach the successful native Spot outcome; see live verification below. Search/Listen controls remain unimplemented. |
| D — persistence, privacy, regression | Strict checkpoint schema preserves visibility transitions and old no-motion/motion encodings. The native test saves after Spot and restores in a separate OS process, comparing observer ledgers, awareness, time/boundary, RNG cursor and Spot outcome. Both observers retain distinct knowledge. Existing combat-mode cohorts remain green from prior focused checks. | Pending/failed Search and Listen persistence, observed Action/Event continuation, and successful browser discovery continuation. |

## Current implementation evidence

- `src/arena_perception.py` separates currently observable evidence from latest known evidence and computes obstruction only from explicitly represented opaque shapes. The generated Arena defaults remain unobstructed unless a scenario authors opacity.
- `src/atomic_publication.py` records loss/restoration of visibility at the committed boundary. Newly discovered Spot evidence is published only to the acting Being on successful native resolution.
- `src/checkpoint_arena_perception.py` and `src/checkpoint_fields.py` encode visibility boundaries while retaining strict compatibility paths for prior evidence versions. Native snapshot allowlisting includes only the represented `VisualOcclusion` and `AwarenessEffect` types required by this scenario.
- `src/arena_authored_spot_scenario.py` creates an opt-in, prepublication fixture: an explicitly placed opaque screen and a target Sphere with authored low DC. It does not infer generated Being anatomy. `GeneratedArenaSession`, persistence, and `examples/arena_web.py` expose this scenario and its target-free Spot control.
- The browser projection shows only observer-authorized visible entities and history, with visible/last-known labels and opaque handles. It does not include the hidden target's native ID or name before discovery.

## Native and persistence demonstration

`tests.test_generated_arena_spot_readiness.TestGeneratedArenaSpotReadiness.test_authored_spot_exercise_discovers_natively_and_restores_fresh_process` generates seed 73111, confirms the hidden target is omitted from initial current evidence and observer awareness, moves the observer to a clear modeled sightline, and accepts the target-free six-second Spot Choice. The action request/result omit target identity. At completion, only the acting observer gains awareness and a location receipt. The test saves the Encounter and compares a digest of exact time, boundary, observer awareness, encoded observer ledgers, RNG cursor and Spot outcome after a separate `python -S` process loads it. The digest matches.

## Served Chrome verification

- Served the current checkout at `http://127.0.0.1:50520/` and a fresh session at `http://127.0.0.1:50521/`; both used the actual generated Arena HTML/JavaScript and HTTP/session routes in Chrome.
- Generated the explicit “Spot exercise · authored opaque screen” scenario at seed 73111 with no autonomous opponent strategy. Before Spot, the observer’s list omitted “Obscured Target”; it showed only its permitted evidence and the opaque screen.
- A live route to hex `(2, 2)` committed native movement and the browser exposed the native Spot button without adding the target to the visible list. The Spot Choice was accepted and ran for six native seconds. That route remained obstructed, and the native result was `no_clear_path`; no hidden identity was disclosed.
- A subsequent attempt to select the fixture test’s `(2, 0)` route was refused by native movement prerequisites in the browser; no time or position changed. This differs from the passing session-level test, where that route commits and clears the authored sightline. The discrepancy needs a focused browser-route investigation before a successful served-Chrome discovery can be claimed. The `no_clear_path` run is not presented as the successful acceptance scenario.

## Focused verification

Latest combined focused command:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=src:examples:tests:../npc-generator .venv/bin/python -B -m unittest tests.test_spot_action tests.test_generated_arena_spot_readiness tests.test_checkpoint_arena_perception tests.test_arena_persistence.TestArenaPersistence.test_observer_current_view_and_history_restore_in_fresh_process tests.test_arena_persistence.TestArenaPersistence.test_observed_motion_interval_survives_fresh_process_save_load tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_actual_shipped_javascript_handlers_order_sprint_update_before_immediate_advance -q
```

**28 tests passed in 11.857 seconds.** This includes Spot timing/privacy, authored occlusion, two-observer knowledge divergence, visibility checkpoint encoding, observer current/history and motion Save/Load, fresh-process native discovery, plus the shipped-JavaScript movement handler. No full repository suite was run.

Earlier focused evidence retained from the prior execution:

- `tests.test_arena_initialization tests.test_arena_opponent_attack` — 19 passed in 53.885 seconds.
- Motion-evidence cohort (`test_spot_action`, `test_generated_arena_spot_readiness`, `test_checkpoint_arena_perception`, observer history Save/Load, and motion Save/Load) — 24 passed in 6.767 seconds before the authored live Spot integration was added.
- `examples/generated_arena_spot_geometry.py` — explicit native Spot success at t=6 with observer-owned evidence, and DC 100 failure at t=6 without awareness/evidence.
- The generated-browser cohort previously ran 72 tests with one subprocess import-path error; the exact failed test passed after adding explicit child `PYTHONPATH`. The full 72-test cohort was not repeated.

## Limits and task state

- Acoustic attenuation, audibility evidence, Search accessibility, ordinary generated Being geometry, acceleration, visual uncertainty, and generally applicable hiding rules are absent and were not invented.
- Search and Listen remain `not_implemented`; Spot remains fail-closed without represented target geometry and clear line of sight.
- U-OBS-001 is still the sole ACTIVE development program. U-ACT-037 remains DONE (bounded), U-ACT-038 OPEN, U-SPOT-002 OPEN, U-ACT-039 VERIFY. No Search-specific stable ID was identified or created. U-CAP-008A and U-PLAYTEST-001 remain archived and consumed.
- The accepted frozen release under `~/Projects/universe-arena-playtest/U-CAP-008A-2026-11-14/` remains unchanged. This work did not alter other repositories, the `.venv`, ignored `legacy/`, backups, or user saves.
- Unrelated staged U-CAP-002/U-CAP-003 archive deletions and the staged U-THROW-001 rename remain untouched and excluded. `docs/assignments/universe-arena.json` remains untracked and untouched.

## Commits and safety

- `37b7c3590ba384558665c97637af2eee69983bf6` — archive accepted U-PLAYTEST-001 and resume U-OBS-001.
- `8af74cd325f59305d34f5160bc230c7d6df84abb` — observer history and discovery rule helpers.
- `3bd338505af230be9d034bc3b0e39f326718e6d5` — persist observer-owned motion evidence.
- `8ee46646b1217704b2292c5786c53055b9222df5` — authored opaque-geometry visibility transitions, generated-Arena Spot control, strict persistence support, and native/fresh-process regression coverage. The staged publication-safety audit passed with 17 files and 0 findings; commit used explicit `--only` scope, excluding five unrelated staged archive paths.
- `e2099b7e231d0947069e359d2f851d22a0287041` — reconcile the sole ACTIVE task and this criterion/report status. Its staged publication-safety audit passed with 8 files and 0 findings; commit used explicit `--only` scope.
- `54568af7978428d281e409f7549b243073b58ec5` — record verified commit evidence in this report; its staged publication-safety audit passed with 7 files and 0 findings.
- At the last status inspection, HEAD was `54568af7978428d281e409f7549b243073b58ec5`; the only staged entries were the five pre-existing archive paths (four removals and one rename), and `docs/assignments/universe-arena.json` remained protected and untracked. The final staged audit passed with 7 paths and 0 findings.
- No push or history rewrite was attempted.
