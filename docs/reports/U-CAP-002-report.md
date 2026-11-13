# U-CAP-002 engineering report

**Status: ACTIVE — incomplete.** This report records verified progress only. The assignment remains open; the completed movement and Overrun paths do not satisfy the adopted End Run, Bull Rush, or Charge requirements.

## Current status

| Assignment area | Status | Evidence and remaining work |
|---|---|---|
| A. Occupied-space movement | **Implemented for represented native routes; partial integration** | Continuous metric paths reject known Being occupancy, modeled geometry intersections, unknown geometry and out-of-map passages before publication. Native velocity cannot bypass the same validator. Simultaneous conflicting destinations fail atomically; tests cover independent legal routes, rollback, facing and posture. Pinned movement now has a focused validator regression. Full movement-phase End Run, changing occupants, movement of a target during prepared maneuvers, and broader simultaneous conflict cases remain open. |
| B. End Run | **Not implemented** | Adopted rules specify three-second preparation, modified timing, movement-phase opposed Dexterity (or behind/immobilized Dexterity check), size modifier, tie/failure at origin, and a distinct unoccupied exit. The current one-boundary destination intent has no prepared-passage transaction that traverses an occupied hex at the completion boundary. This is implementation work, not a rule ambiguity. |
| B. Disengage | **Bounded ordinary movement** | Native withdrawal regressions show a scheduled strike becomes out of reach after movement in one route and remains eligible when the destination remains within reach in another. A generated-Arena route now schedules the opponent's strike before shipped destination controls move the player away; the strike resolves out of reach using postmovement positions. Movement uses the ordinary occupied-space validator; no extra attack or free-standing Disengage Action is invented. Broader simultaneous interactions remain open. |
| B. Overrun | **Bounded native and generated-Arena loop** | Four-second native contest applies STR, DEX, size, optional equipped-shield and Multiple-action priority modifiers; successful result makes the target prone without displacement. Eligibility refuses missing size, excessive size gap, bad facing/range/posture, tower-shield bearer and unsupported geometry. Generated Arena demonstrates legal approach → Overrun, absent-size refusal and pending/committed restoration in fresh OS processes. Charge/Bull-Rush continuation, represented stability/leg-count facts and unsupported displacement remain open. |
| B. Bull Rush | **Not implemented** | Adopted rules define the one-second Strength contest, size/stability/shield modifiers, Yield nullification and continuation. No native Bull Rush Action or movement-phase displacement integration exists. The rule permits no invented displacement amount; contest work is independently implementable and remains outstanding. |
| C. Charge and pole interception | **Not implemented** | Existing snapshots do not provide the adopted initial/relative velocity contract needed to verify culmination speed and incremental relative-speed damage. There is no native Charge/ready-pole interception Action integration. Timing, frozen-snapshot simultaneous attacks and legal paths still require implementation where the data support them. |
| D. Arena, persistence and browser | **Partial** | Generated Arena offers the supported Overrun route and observer-safe refusal for missing size data. Pending and committed Overrun checkpoints were continued across separate Python processes. An actual Chrome attempt reached a safe movement refusal due to opposing route conflict; subsequent CDP operations timed out. HTTP/session tests are not represented as successful Chrome evidence. The required successful browser interaction remains unverified. |

## Reproducible generated-Arena Overrun path

Run the generated session through `tests.test_arena_melee_attack.TestArenaMeleeAttack.test_generated_overrun_uses_explicit_size_and_native_prone_resolution`. The deterministic fixture supplies explicit Medium size categories, generates the Arena, legally moves to a neighbor of the target, inspects the opposing Being through its opaque handle, selects Overrun, and advances four native one-second boundaries. The target becomes prone and both Being positions remain unchanged. `test_generated_overrun_refuses_when_required_size_facts_are_absent` verifies a refusal without clock, event, Choice or RNG change. `test_generated_overrun_pending_and_committed_state_restore_in_fresh_processes` saves the pending Action, loads and resolves it in a new OS process, saves the committed result, then reloads that result in another process.

## Recent implementation and verification

- `tests.test_movement_intent` and `tests.test_arena_melee_attack`: **43 passed**, 31.502 seconds. This includes occupied/unknown/blocked route rejection, simultaneous conflict and rollback, native ordinary withdrawal leaving/remains-in-reach, generated withdrawal followed by a postmovement out-of-reach strike, pinned-movement refusal, generated Overrun success/refusal, browser JavaScript/session integration, and fresh-process pending/committed Overrun restoration.
- Focused native Overrun checks in `tests.test_action_evaluation`: success, tie, advanced equipped shield and tower-shield declaration refusal passed. The focused combined invocation most recently ran 10 tests across native and Arena modules, all passed in 10.686 seconds.
- `py_compile` for the changed implementation and test modules passed. `git diff --check` passed.
- Historical evidence from earlier U-CAP-002 commits is not a result of this current execution interval: the movement/melee subset previously passed 38 tests; the `tests.test_action_evaluation` suite/class previously passed 125 tests in 113.703 seconds.

## Commits and repository safety

- `db2ffa0cc8513309b3c4e7aad6bde344508aef90` — Add native occupied-path validation.
- `b09bafaaa2939f696d6e37f14efdc71fee04f770` — Enforce occupancy on native velocity routes.
- `7c4f159e636b562eb417612013a20f75b0a293d3` — Add bounded native and Arena Overrun.
- `9bc881861fadc1cd339d3cbcb38f47666e1dfb25` — Test withdrawal reach after movement.
- `2621d13e674eadfde74e699074cf557c7c0860e6` — Cover pinned movement and Overrun shield limit.
- `c2fe6a5825cf263e9e4059e84b4bbe12cc23a98b` — Verify Overrun continuation across Arena restores.
- For each recent commit, staged `git diff --cached --check` and `tools/check_publication_safety.py --staged` passed with zero findings. The staged-safety scan also saw a pre-existing staged historical rename, which was left out of these scoped commits.
- Branch: `main`. Remote: `origin` points to `https://github.com/tucotuco/universe.git`. No push was made. The unrelated staged move of `docs/reports/U-THROW-001-rule-sync-proposal.patch` into `docs/reports/archive/` remains untouched. The latest status before the pending documentation commit showed only that staged rename plus the intended `TASKS.md` edit.

## Remaining work and blockers

No user decision is currently required. The adopted End Run, Bull Rush and Charge rules are sufficiently specific to implement their supported branches; missing transaction integration is not a rule blocker. Missing relative velocity, body stability/leg count and exact collision/displacement facts bound only those specific cases. Continue the independent native passage/contest integration, remaining simultaneous and interruption regressions, generated withdrawal flow, and any feasible pole/Charge cases before closeout. Keep this assignment ACTIVE until its acceptance matrix is satisfied or a genuine external blocker remains after that work.

## Execution intervals

All timestamps below use ISO 8601 and the explicit local offset (`America/Los_Angeles`, UTC−08:00 on 2026-11-13). Earlier intervals are listed separately; no missing end time or duration is estimated.

| Interval | Start | End | Elapsed |
|---|---|---|---|
| Earlier continuation (recorded start) | 2026-11-13T09:28:38-08:00 | Not captured | Not calculable |
| Earlier continuation (recorded start) | 2026-11-13T09:57:07-08:00 | Not captured | Not calculable |
| Current execution | 2026-11-13T10:20:30-08:00 | Pending closeout | Pending closeout |

The overall assignment began before these recorded intervals; its original start timestamp is unavailable in this execution context and is not fabricated here. Update the current interval's End and Elapsed immediately before final closeout.
