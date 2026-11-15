# U-ACT-FULL-001 engineering report

**Status:** ACTIVE; only a bounded equipment cluster has been implemented and the Action Completeness criteria remain open. Keep this report active pending ChatGPT review.

## Execution interval

- Start: **2026-11-15T10:54:27-08:00** (recorded when this execution began).
- End: pending; capture immediately before closeout.
- Elapsed: pending; calculate from the recorded timestamps.

## Current outcome and source audit

- U-OBS-001 was accepted DONE (bounded). Its assignment and consumed report remain at `docs/assignments/archive/U-OBS-001.md` and `docs/reports/archive/U-OBS-001-report.md`. Its observer-owned evidence, native Search/Spot/Listen and persistence remain bounded. The documented gaps—general acoustic propagation, multiple-candidate and general Object/Event discovery, generated Being geometry, arbitrary Event perception and rolled incidental Spot/Listen—remain future Action Gate work.
- U-ACT-FULL-001 is the sole ACTIVE implementation program. U-ACT-GATE-001 remains FUTURE/unpassed and U-NET-001 remains DEFERRED. Both Arena modes, observer-specific knowledge and the frozen Playtest Edition are unchanged.
- The source-linked matrix is [action-implementation-coverage.md](../encounters/action-implementation-coverage.md). It has **52 Action/variant rows: 42 PARTIAL, 3 OPEN, 5 BLOCKED, 1 VERIFY, 1 NOT AN INDEPENDENT ACTION, 0 FULL**. The stable inventory distinguishes bounded prior DONE assignments from rule-complete Actions; no row was upgraded to FULL. The matrix records exact source links, model prerequisites, implementation paths and focused tests. U-ACT-040 and U-ACT-041 were checked before use.
- Revision 61 defines shield Don and Remove time from the Shield's swing timing: `ST × 5` and `ST × 2`. A newly added native `ShieldEquipmentAction` implements those transitions for ordinary configured shields. Don requires exclusive carried custody and a free represented hand; Remove requires the shield borne in that hand. Both reserve the same Object and hand, evaluate from the common boundary snapshot, and publish the equipment/hand transition atomically. Don adds the existing Shield Object to the same Being's equipped weapon list and represented hand. Remove clears those states but retains the Object in that Being's carried possessions. The adopted text directs no drop on Remove, so the transition does not invent a ground destination.
- The shield's held-state feeds the existing `shielded_with` and shield-dependent Action validation. The regression verifies that after Don the native Action catalog no longer says Block is unavailable because there is no equipped shield, and after Remove it again refuses Block on that precise prerequisite. Existing shield Bash and two-handed resource regressions continue to pass. An unborne carried shield is not protective. A tower shield is refused for ordinary Don under r61; planting one for cover remains unavailable because native ground cover geometry is not represented.
- This new equipment cluster is **PARTIAL**, not FULL. We have not implemented passive shield-size attack allocation; shield strap/source transitions and tower set-down/cover remain unavailable; generic armor Don/Remove lacks armor-part composition, fit and partial-don hit-die state. Exceptional Quick-draw is blocked by r69's essentially no-time result without adopted integer-boundary scheduling semantics. Generic Ready Object remains referee-timed. These are independent limitations, not reasons to invent a physical transition.

## Served Chrome walkthrough

Actual served browser: `http://127.0.0.1:51864/`, generated seed **20261159**. This encounter used the served Arena and a represented Small shield at hex `(3,3)`; no browser-side hand/custody edit was made.

1. Submitted a movement destination to `(3,3)` in the served map and advanced the native movement boundary. The shield remained a ground Object with its own opaque handle.
2. Selected that shield and submitted the native Pick up choice; the receipt reported `Pick up resolved: success.` at native time **2 seconds**.
3. Opened Tobe's native equipment controls, selected the left hand and submitted `Don Shield (25 s)`. At native time **27 seconds**, the receipt reported `Don Shield resolved: success.` The visible character sheet listed `left hand: Small shield`, and the carried-equipment view showed the same shield as held equipment. The Block catalog no longer failed for absence of an equipped shield.
4. Selected that same Small shield, chose the represented left hand and submitted `Remove Shield (10 s)`. At native time **37 seconds**, the receipt reported `Remove Shield resolved: success.` The sheet showed `left hand: empty`, `right hand: Dagger`, and the same shield still carried; Block then failed closed with `No native shield is equipped in a functioning arm.`

The result was inspected after the final boundary in the actual Chrome tab. The native receipts and character/equipment view agree; the Object was not duplicated, released or renamed. Player-authorized opaque handles were used. No opponent Action was enabled by this equipment-only encounter; opponent contention was not part of this shield transition.

## Persistence, conflicts and regression results

- A pending Don checkpoint was loaded in a fresh OS process, advanced through the adopted duration, and verified against the exact shield ID, exact actor possession, `parent_container_id`, no ground position, hand reference, equipment-list reference and committed success receipt. A completed Don checkpoint was separately loaded in a fresh process with the same identity and custody assertions.
- A pending Remove checkpoint was separately loaded in a fresh process, advanced to its boundary, and verified to clear the represented hand and equipment reference while retaining the exact Object identity and carried custody, with a committed success receipt.
- A focused Choice regression schedules two overlapping Don candidates. It proves the native validator reserves the same shield Object across different hands and independently rejects two shields claiming one hand. This leaves simultaneous resource allocation and RNG behavior to native Choice validation, not the browser.
- Focused shield/weapon plus compatibility command:

  `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_arena_ready_weapon.TestArenaReadyWeapon.test_shield_don_remove_native_browser_choices_and_pending_fresh_process_restore tests.test_arena_ready_weapon.TestArenaReadyWeapon.test_tower_shield_don_is_refused_by_adopted_wielding_rule tests.test_arena_ready_weapon.TestArenaReadyWeapon.test_generated_arena_exposes_native_shield_bash_and_persists_pending_choice tests.test_arena_ready_weapon.TestArenaReadyWeapon.test_generated_medium_shield_bash_resolves_after_fresh_process_restore tests.test_arena_ready_weapon.TestArenaReadyWeapon.test_generated_long_sword_draw_ready_with_shield_blocks_two_handed_use tests.test_action_choices.TestActionChoices.test_shield_equipment_reserves_both_selected_hand_and_same_shield_object`

- Result after adding exact completed-Don and pending-Remove fresh-process checks: in the consolidated command below, the six shield/weapon tests passed alongside five protected Arena/perception regressions.
- Two early failures occurred while extending the test harness, not in production behavior: the test first tried to identify the player's private Action catalog through an observer-visible entity handle (the player is intentionally not exposed as another public entity); it was corrected to read the player's own authorized catalog. A later fresh-process assertion selected the earlier completed Don from Action history instead of matching the pending Remove Action ID; the assertion was corrected to require that exact ID. The final combined test run below passed.
- Seed-14 regression command:

  `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_arena_vs_arena.TestArenaVsArena.test_two_controllers_native_consequence_and_fresh_process_continuation tests.test_arena_vs_arena.TestArenaVsArena.test_player_vs_arena_remains_default_and_server_rejects_manual_action_in_spectator_mode tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_seeded_two_sided_browser_combat_hit_and_fresh_process_continuation tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_authored_search_and_listen_http_controls_preserve_target_privacy tests.test_observer_lifecycle_proposals.TestObserverLifecycleProposals.test_two_observers_one_truth_distinct_evidence_belief_and_practice`

- Result in the final combined regression command below: all five passed. This preserves Player-vs-Arena default behavior and verifies seed-14 spectator mode, two independently acting Arena strategies with a native consequence/fresh-process continuation, a real seed-14 Player-vs-Arena hit plus opponent Action with fresh-process continuation, and Search/Listen privacy plus distinct observer knowledge.
- Final combined command was the shield/weapon command above followed by the five seed-14/observer tests below. **11 passed in 83.050 s.** No test was skipped within that command.
- Python syntax check of all affected native modules and `examples/arena_web.py` passed using `python3 -m py_compile` (no diagnostics).
- Earlier broad diagnostic (211 tests, 158.372 s) had one stale physical-contact adjacency fixture and 15 legacy overlapping-Action fixtures rejected because they lack adopted Multiple-action declarations. These were recorded before this equipment change and were not weakened or altered. The repository-wide suite was not rerun.

## Remaining independently tracked clusters

1. Passive shield-size allocation and target selection before attack outcomes; shield durability/parallel-impact integration where adopted; tower shield set-down/cover geometry. Do not assign attacks at random or derive missing geometry.
2. Armor Don/Remove requires represented armor-part composition, wearer fit and the adopted partial-don hit-die state. Exceptional Quick-draw requires an adopted integer-boundary rule; generic Ready Object still requires a case-specific referee duration.
3. Ranged Shoot, generic Throw and Deflect: adopted projectile velocity/ammunition/release facts and representable impact or deflection paths are missing in the blocked scopes.
4. Pull, forced movement and later Charge/Bull-Rush/Overrun continuations remain bounded by actual force/displacement and geometry facts.
5. Contested custody/grappling, including unspecified subsequent contests among simultaneous co-holders, remains bounded.
6. Advanced weapon, armor/Object, magical-save, general discovery/acoustics and Action Gate audits remain at their matrix statuses.

No new rule question is required to complete the ordinary-shield Don/Remove slice. The omitted outcomes are precisely listed with the missing adopted rule or data in the matrix; independently supported work above has been delivered. The broader assignment remains ACTIVE.

## Git, task register and publication safety

- `TASKS.md` records U-ACT-FULL-001 as sole ACTIVE; U-ACT-GATE-001 remains FUTURE and U-NET-001 remains DEFERRED. U-ACT-016 now records the shield equipment result without upgrading the Action to FULL.
- Prior in-scope documentation commits: `6ffa4cdcad342539c0831db8f7df4b2af9dce66d` (activation and accepted U-OBS archival reconciliation), `5923020` (initial matrix audit), `9c4e8f4` (matrix/catalog reconciliation). Scoped implementation commit: `ab85638b489134d373a4ce6ec2cd6dbfd8601f89` (`Add native shield Don and Remove Actions`). Matrix/TASKS/report commit hashes are recorded after final audit below.
- Preserved in the Git index and excluded from U-ACT-FULL commits: four U-CAP-002/U-CAP-003 active-path deletion entries and the `U-THROW-001-rule-sync-proposal.patch` archive rename. The untracked `docs/assignments/universe-arena.json` remains untouched. The frozen Playtest release and other repositories were not changed.
- Final closeout will record actual HEAD, explicit intended paths, full status/index listing, `git diff --cached --check`, the staged publication-safety audit result, and local commit hashes. No push was authorized or performed.
