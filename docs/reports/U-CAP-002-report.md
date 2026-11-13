# U-CAP-002 engineering report

**Status: ACTIVE — incomplete.** This report records verified progress only. The assignment remains open; the completed movement and Overrun paths do not satisfy the adopted End Run, Bull Rush, or Charge requirements.

## Current status

| Assignment area | Status | Evidence and remaining work |
|---|---|---|
| A. Occupied-space movement | **Implemented for represented native routes; partial integration** | Continuous metric paths reject known Being occupancy, modeled geometry intersections, unknown geometry and out-of-map passages before publication. Native velocity cannot bypass the same validator. Simultaneous conflicting destinations fail atomically; tests cover independent legal routes, rollback, facing, posture, and two- and three-Being same-destination contention with unchanged state and RNG. Pinned movement has a focused validator regression. Full movement-phase End Run, changing occupants, movement of a target during prepared maneuvers, and other simultaneous cases remain open. |
| B. End Run | **Not implemented** | Adopted rules specify three-second preparation, modified timing, movement-phase opposed Dexterity (or behind/immobilized Dexterity check), size modifier, tie/failure at origin, and a distinct unoccupied exit. The current one-boundary destination intent has no prepared-passage transaction that traverses an occupied hex at the completion boundary. This is implementation work, not a rule ambiguity. |
| B. Disengage | **Bounded ordinary movement** | Native withdrawal regressions show a scheduled strike becomes out of reach after movement in one route and remains eligible when the destination remains within reach in another. A generated-Arena route now schedules the opponent's strike before shipped destination controls move the player away; the strike resolves out of reach using postmovement positions. Movement uses the ordinary occupied-space validator; no extra attack or free-standing Disengage Action is invented. Broader simultaneous interactions remain open. |
| B. Overrun | **Bounded native and generated-Arena loop** | Four-second native contest applies STR, DEX, size, optional equipped-shield and Multiple-action priority modifiers; successful result makes the target prone without displacement. Eligibility refuses missing size, excessive size gap, bad facing/range/posture, tower-shield bearer and unsupported geometry. Generated Arena demonstrates legal approach → Overrun, absent-size refusal and pending/committed restoration in fresh OS processes. Charge/Bull-Rush continuation, represented stability/leg-count facts and unsupported displacement remain open. |
| B. Bull Rush | **Partial native and Arena contest** | Native Action and generated Arena resolve the adopted one-second forward Strength contest, relative-size modifier and restriction, optional equipped-shield bonus, zero attack/defense strategy, strict-tie failure, Multiple-action priority penalty, Yield nullification and tower-shield prohibition. Success has typed `success_pending_displacement` and never invents movement. Generated Arena pending Action restoration and resolution in a fresh OS process pass. Willing-target handling, +2 stability/multi-leg facts (not represented by native Being data), per-second continuation, concerted/mounted cases, and physical displacement remain open. |
| C. Charge and pole interception | **Partial native and generated declaration** | The native `MeleeStrike(charge=True)` now evaluates post-movement relative speed, refuses below 4 yd/s without attack RNG, and applies the adopted +2 hit and incremental damage. Charge declaration refuses while the actor is engaged by a pressing opponent. The generated Arena exposes an opaque-handle Charge selector and routes it to the same native Action; pending Charge survives Save/Load. Generated successful run-in culmination, prepared-pole interception, and Charge follow-up remain open. |
| D. Arena, persistence and browser | **Partial** | Generated Arena offers Overrun, Bull Rush and Charge routes. Pending Charge restoration is verified through the generated session codec; pending and committed Overrun checkpoints and pending Bull Rush continuation were restored across separate OS processes in earlier focused tests. A generated occupied-route refusal leaves time, positions and RNG unchanged; after cancelling the movement plan, those values restore identically in a fresh process. A prior actual Chrome attempt reached a safe movement refusal due to opposing route conflict; subsequent CDP operations timed out. No successful Chrome trajectory is claimed. |

## Reproducible generated-Arena Overrun path

Run the generated session through `tests.test_arena_melee_attack.TestArenaMeleeAttack.test_generated_overrun_uses_explicit_size_and_native_prone_resolution`. The deterministic fixture supplies explicit Medium size categories, generates the Arena, legally moves to a neighbor of the target, inspects the opposing Being through its opaque handle, selects Overrun, and advances four native one-second boundaries. The target becomes prone and both Being positions remain unchanged. `test_generated_overrun_refuses_when_required_size_facts_are_absent` verifies a refusal without clock, event, Choice or RNG change. `test_generated_overrun_pending_and_committed_state_restore_in_fresh_processes` saves the pending Action, loads and resolves it in a new OS process, saves the committed result, then reloads that result in another process. `test_generated_occupied_route_refusal_restores_unchanged_in_fresh_process` verifies an occupied destination cannot move either Being or consume RNG and that after cancelling the refused plan, the unchanged state survives fresh-process restore.

## Recent implementation and verification

- `tests.test_movement_intent` and `tests.test_arena_melee_attack`: **44 passed**, 30.286 seconds. This includes occupied/unknown/blocked route rejection, two- and three-actor simultaneous conflict and rollback, native ordinary withdrawal leaving/remains-in-reach, generated withdrawal followed by a postmovement out-of-reach strike, pinned-movement refusal, generated Overrun success/refusal, browser JavaScript/session integration, and fresh-process pending/committed Overrun restoration.
- `tests.test_movement_intent`, `tests.test_arena_melee_attack`, and focused native Bull Rush / size/tower-shield tests: **52 passed**, 26.557 seconds. The generated Bull Rush route includes the shipped JavaScript selector, observer handle, native one-second contest and pending-Action fresh-process restoration. Native contest tests verify success-pending, strict-tie failure with no position changes, advanced shield bonus, refusal for a target over one size category larger, Multiple-action priority penalty, and tower-shield refusal for both Bull Rush and Overrun. Generated occupied-route refusal, plan clear and unchanged-state fresh-process restore pass.
- Focused native Overrun checks in `tests.test_action_evaluation`: success, tie, advanced equipped shield and tower-shield declaration refusal passed. The focused combined invocation most recently ran 10 tests across native and Arena modules, all passed in 10.686 seconds.
- `py_compile` for the changed implementation and test modules passed. `git diff --check` passed.
- Current continuation re-ran `tests.test_arena_melee_attack`: **14 passed in 28.393 seconds**. Its generated Charge test checks the opaque target handle, served JavaScript click binding, native `MeleeStrike(charge=True)` scheduling and pending Save/Load with stable Action identity. The new test also passed alone in 0.885 seconds; ordinary-selector compatibility and Charge-selector integration passed together (2 tests, 1.944 seconds).
- A broader `tests.test_generated_arena_browser` run produced 3 failures and 1 error among 61 tests. The failing movement fixtures route through or end in a geometryless ground-Object cell; the occupied-path validator correctly returns `uncertain_path` and safely refuses. These fixtures require legal-route/expected-refusal reconciliation before that full module can be claimed green. This is repairable fixture/integration work, not an adopted-rule question; the fail-closed source behavior was retained.
- Historical evidence from earlier U-CAP-002 commits is not a result of this current execution interval: the movement/melee subset previously passed 38 tests; the `tests.test_action_evaluation` suite/class previously passed 125 tests in 113.703 seconds.

## Commits and repository safety

- `db2ffa0cc8513309b3c4e7aad6bde344508aef90` — Add native occupied-path validation.
- `b09bafaaa2939f696d6e37f14efdc71fee04f770` — Enforce occupancy on native velocity routes.
- `7c4f159e636b562eb417612013a20f75b0a293d3` — Add bounded native and Arena Overrun.
- `9bc881861fadc1cd339d3cbcb38f47666e1dfb25` — Test withdrawal reach after movement.
- `2621d13e674eadfde74e699074cf557c7c0860e6` — Cover pinned movement and Overrun shield limit.
- `c2fe6a5825cf263e9e4059e84b4bbe12cc23a98b` — Verify Overrun continuation across Arena restores.
- `157b7aba274a4a45855d537677b0c578b34465d4` — Integrate bounded native Bull Rush contest.
- `8f6736b19a28f0d3a1c7e8963523684bbba6b409` — Update U-CAP-002 Bull Rush status.
- `90b3007b003bcb0a7c2bc260c80db8e25c70ca39` — Verify Bull Rush shield bounds.
- `585c8a7f86773da37a2eecea8324d2857f2d7919` — Verify occupied-route refusal across restore.
- `12ee1b2` — Expose native Charge through generated Arena.
- `14af526` — Preserve ordinary melee request payload.
- `d657f18` — Verify generated Charge checkpoint persistence.
- For each recent commit, staged `git diff --cached --check` and `tools/check_publication_safety.py --staged` passed with zero findings. The staged-safety scan also saw a pre-existing staged historical rename, which was left out of these scoped commits.
- Branch: `main`. Remote: `origin` points to `https://github.com/tucotuco/universe.git`. No push was made. The unrelated staged move of `docs/reports/U-THROW-001-rule-sync-proposal.patch` into `docs/reports/archive/` remains untouched. Current uncommitted changes are the intended `TASKS.md` and this report update; no unrelated working-tree files are modified.

## Remaining work and blockers

No user decision is currently required. End Run's adopted rule is specific; its movement-phase passage, contest, interruption, and persistence transaction remain unimplemented. Charge's native relative-motion rules and generated declaration are implemented, but successful generated run-in culmination and pole interception remain open. Bull Rush Yield nullification is tested; willingness/continued contest and displacement remain open. Missing body stability/leg-count and exact collision/displacement facts bound only those specific cases. The generated-browser fixture failures are independently repairable. Continue all of this work and retain ACTIVE status; missing implementation and outdated fixture assumptions are not external blockers.

## Execution intervals

All timestamps below use ISO 8601 and the explicit local offset (`America/Los_Angeles`, UTC−08:00 on 2026-11-13). Earlier intervals are listed separately; no missing end time or duration is estimated.

| Interval | Start | End | Elapsed |
|---|---|---|---|
| Earlier continuation (recorded start) | 2026-11-13T09:28:38-08:00 | Not captured | Not calculable |
| Earlier continuation (recorded start) | 2026-11-13T09:57:07-08:00 | Not captured | Not calculable |
| Current execution | 2026-11-13T10:20:30-08:00 | Pending closeout | Pending closeout |

The overall assignment began before these recorded intervals; its original start timestamp is unavailable in this execution context and is not fabricated here. Update the current interval's End and Elapsed immediately before final closeout.
