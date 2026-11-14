# U-CAP-003 engineering report

**Status: ACTIVE — bounded outcome implemented and submitted for ChatGPT acceptance.** Criteria A–D below have evidence for the supported equipment-to-combat lifecycle. Keep this assignment and report in their active directories until ChatGPT accepts and consumes them. Do not archive or push them in this execution. U-CAP-002 remains accepted DONE (bounded); its staged archive changes are unrelated pre-existing user staging and are preserved.

## Acceptance matrix

| Criterion | Outcome | Evidence and bounded scope |
|---|---|---|
| A. Draw, Ready, hands and weapon use | **Supported outcome verified; bounded** | Generated unequipped medium Being draws an explicitly sheathed Longsword, prepares a declared motion, then completes a two-handed strike after fresh-process Save/Load. A second generated scenario holds a Medium shield while drawing/preparing the Longsword: one-handed attack is accepted, two-handed use is refused, and the resolved strike consumes preparation. Native checks cover represented hands, size, two-handed damage, weapon-specific preparation and resource contention. Exceptional Quick-draw with advanced weapon skill is refused because its adopted essentially-no-time duration has no integer-second scheduler representation; ordinary Draw remains two seconds. |
| B. Shields and equipment resources | **Supported outcome verified; bounded** | Generated Medium-shield bash resolves after fresh-process restore. Native rules use the shield's represented motion, damage and penetration, explicit dominant-hand evidence, adopted off-hand modifier, and tower-shield refusal. Forearm buckler attachment is explicit, protective, leaves its hand available and applies its adopted same-hand penalty. Multiple Action hand claims prevent overlapping Draw/Ready/strike or two-hand conflicts. General Don/Remove shield transitions remain bounded: shield source/strap attachment and the applicable ST input are not represented, so no generic time or instantaneous transfer is invented. |
| C. Object strikes and durability | **Supported outcome verified with modeled facts** | A native Strike Object test supplies explicit Sphere geometry for the Being, immobility and a no-intersection/no-unmodeled-entity physical path to a real hardwood Object. The successful critical applies hardness and destroys the actual target. Fresh-process restore preserves its Object ID, zero HP, completed Action and critical receipt. A same-boundary two-attacker test applies hardness per blow against the shared pre-action snapshot and atomically totals both blows through destruction. Generated Arena's geometryless-participant Object path remains `uncertain_path`; a regression verifies HP and RNG do not change. The successful native case establishes that the operation is implementable when legitimate geometry and clearance are present; no Arena geometry was fabricated. |
| D. Generated Arena, composition and persistence | **Supported outcome verified; bounded** | Generated NPC scenarios and the shipped Arena controls demonstrate the two non-Dagger configurations above and a fresh-process-resolved shield bash. Tests cover opaque observer handles, native Choice validation, pending Draw resume/commit, cancelled Draw restore, pending prepared strike, completed/readiness-consumed strike restore, shield identity, Object destruction/receipt restore and generated Object refusal without state or RNG mutation. HTTP and shipped-JavaScript tests exercise the visible controls. A live Chrome smoke generated the encounter and inspected its character/Action panel; default generated player evidence left specific Action availability unknown, so no live Chrome combat resolution is claimed. This does not replace the generated-session/HTTP/shipped-JavaScript lifecycle evidence. |

No adopted-rule question is outstanding. Quick-draw timing and general shield Don/Remove remain bounded by absent scheduler representation and authored transition inputs; neither blocks the implemented supported loop. The generated Object-strike fixture has not been relaxed: geometryless Being interference remains uncertain and fails closed. A successful native clear-path case and the generated shield-bash alternative satisfy the supported Object/shield outcome without invented geometry.

## Execution time

| Execution interval | Start (ISO 8601 with offset) | End (ISO 8601 with offset) | Elapsed (ISO 8601 duration) |
|---|---|---|---|
| Earlier partial session | 2026-11-13T15:37:40-08:00 | Not recorded | Unknown; not estimated |
| Earlier continuation | 2026-11-13T17:09:04-08:00 | 2026-11-13T17:22:47-08:00 | PT0H13M43S |
| Current continuation | 2026-11-13T17:35:37-08:00 | 2026-11-13T18:12:53-08:00 | PT0H37M16S |

The first interval's start was captured but its end was not. Other earlier intervals were not recorded. No missing interval has been estimated. The current interval's start was captured when this continuation began; its end was captured from the clock immediately before final closeout, and elapsed time was calculated from those timestamps.

## Implementation and verification

- Native `MeleeStrike` carries two-handed and shield-bash declarations through Choice, snapshots, checkpoints and resolution. Eligibility depends on represented hands, explicit size and actual shield/weapon occupancy. A one-size-larger weapon requires both hands without a damage bonus; ordinary same-size-or-smaller weapons use the adopted `floor(1.5 × weapon damage)` unless explicitly tagged as designed for two-handed use.
- Draw remains a separate two-second Action, requires native custody, an explicit drawable source and an explicitly free represented hand; it does not Ready the weapon. Ready is motion-specific preparation, uses adopted timing and is consumed by the next Action using that weapon. Fresh-process tests now verify pending Draw continuation, committed Draw, cancellation with unchanged custody/source, pending prepared attacks and resolved attacks with preparation consumed.
- Multiple-action resource validation derives hand claims from the native Action declarations. A two-handed strike claims both hands; a one-handed strike, Draw and Ready claim the relevant weapon hand. The new Ready-plus-strike test rejects simultaneous same-hand use and exposes only the hand label in its diagnostic.
- Shield bash uses the equipped native shield's configured motion and damage data, rejects tower shields and applies the adopted off-hand penalty from explicit dominant-hand evidence. Explicit buckler attachment preserves protection and hand availability. Generated bash resolves in a fresh OS process with the same shield and target IDs.
- The Object-strike success test now asserts its authored Being Sphere geometry and empty physical path classification before resolving. The same-boundary durability regression now makes two individually hardness-clearing blows destroy the shared target; both effects publish from the common snapshot. Existing fresh-process destruction evidence retains the same native Object ID and Action receipt.
- The live Chrome smoke generated a regular Arena encounter and opened its character's equipment and Actions panel. The panel reported Action availability unknown from player-authorized evidence for that default participant. A subsequent attempt to load an explicit prepared demo save ended when the computer-use continuation expired, so no manual Chrome combat outcome is claimed. No browser-side state injection or weakening of native path checks was used.

Focused verification from the repository root, except the native melee fixture that requires `tests/` as its working directory. Commands use the repository `.venv` with bytecode and user-site writes disabled:

| Command | Result |
|---|---|
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_action_choices tests.test_checkpoint_choice_descriptors` | **69 passed** |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_action_evaluation` | **117 passed** |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_arena_ready_weapon` | **26 passed**; includes fresh-process pending Draw/commit and cancelled Draw restoration |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_generated_arena_browser` | **61 passed** |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_arena_melee_attack` | **17 passed** |
| From `tests/`: `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=../tests:../src:../examples ../.venv/bin/python -B -m unittest test_melee_combat` | **11 passed** |

The six suites total 301 passing tests. No full repository suite was run. A prior adjacent `tests.test_arena_persistence` run reported two fixture errors (`test_pending_pickup_save_load_keeps_exact_one_second_boundary` and `test_repeatable_three_process_continuation_with_ground_objects`) because selected paths cross geometryless ground Objects and the adopted strict movement validator correctly refuses `uncertain_path`. Those movement fixtures were not changed and the strict validator was not relaxed for U-CAP-003.

## Current task register

- U-CAP-003 remains the single ACTIVE program pending ChatGPT's acceptance, not because of an unfinished independently supported equipment/combat implementation item. This report is an acceptance submission; do not archive it or the assignment yet.
- Keep broader stable Action IDs and their own scopes accurate: general shield Don/Remove remains open under U-ACT-016; generated Object-strike geometry is bounded under U-ACT-019; broader two-handed combinations remain under U-ACT-025. U-CAP-002 remains DONE (bounded) with its archived references.
- Keep the broader Encounter program ACTIVE. Do not start U-CAP-004 or reprioritize work under this report.

## Git, audits and preservation

- Repository branch: local `main`; no push was attempted.
- Current continuation started from `ccb02511c751499c53595ba2771b3369078d2152`.
- New focused-test commit: `fc420054231c6c553e221e26da56e0989db468e0` (`Verify weapon lifecycle persistence and object contention`). It includes only `tests/test_action_choices.py`, `tests/test_action_evaluation.py` and `tests/test_arena_ready_weapon.py`.
- TASKS/report closeout commit: `4415fa6b50456e692383122efae7c47b28700010` (`Submit bounded U-CAP-003 outcome for review`). It includes only `TASKS.md` and `docs/reports/U-CAP-003-report.md`; a final report-only commit records the exact end timestamp and is named in the chat closeout.
- Existing implementation and integration evidence remains in commits `a209cb7be83cf8ab4a5d94f1d766116eb96c4cfc`, `1b7be0bb238f3600a7456fe7094480bd5d9f5c6d`, `2737eea72f2b026af0f9f493c9037330bd9d7cd8`, `bb81f798fffb1c0fc4bb22ff7761e5127cbc01dd`, `fe88ed3a3a6cae77fed2323739cfbcdc89e8bfaf`, and `00451bd830bed3a2a80f0f75aafa3f34be368ca4`.
- Before the focused-test commit, the staged path inventory was reviewed. `git diff --check` and `git diff --cached --check` passed; `.venv/bin/python -B tools/check_publication_safety.py --staged` returned `staged-audit files=7 findings=0 result=PASS`. `git commit --only` included only the three reviewed test files.
- Before the TASKS/report closeout commit, the staged path inventory was reviewed; `git diff --check` and `git diff --cached --check` passed, and the staged publication audit returned `staged-audit files=6 findings=0 result=PASS`. `git commit --only` included only TASKS and the active U-CAP-003 report.
- Pre-existing staged paths remain untouched: deletion of `docs/assignments/U-CAP-002.md`, deletion of `docs/reports/U-CAP-002-report.md`, and the staged U-THROW-001 patch archive rename. No unrelated staged archival content was committed.
- `.venv`, ignored `legacy/`, local saved-world data, `npc-generator`, repository backups, and `universe-geology` were not modified. No history rewrite or push occurred.
- This report and the active assignment remain unarchived pending ChatGPT review and acceptance. The final report-only timestamp correction is the closing local commit; its hash and final HEAD are recorded in the chat closeout. No U-CAP-003 file is left unstaged.
