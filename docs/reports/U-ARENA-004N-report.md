# U-ARENA-004N — Facing policies and the demanding-Action cap

## Outcome

The native movement path does not yet have enough authoritative facing state
to implement either **turn toward movement** or **maintain facing while
moving** as legal facing-aware choices. I left movement resolution and
orientation state unchanged, recorded the precise blockers, and added a test
that proves the current snapshot lacks facing inputs. No orientation encoding,
turn target, or turn commitment was invented.

The one-yard-per-second cap is already in the r61 rate evaluator when its
explicit `concurrent_demanding_action=True` input is supplied. It is not
automatically applied to arbitrary generated Arena Actions because native
Actions do not have a general demanding/non-demanding classification.

The earlier 004L integration test incorrectly marked the co-resolving
`RunAction` as another demanding Action. `RunAction` observes and reports
movement produced by the Encounter step; it does not move the Being. The test
now keeps the explicit demand condition false for that observer. A generated
Elf with FIT 14, STR 13, Run rank zero, no load, and the test's neutral
environment/posture premises therefore walks at 1.75 yd/s (1.6002 m/s) for
that native second. The 1 yd/s demanding-Action premise is tested separately.

## Adopted-rule and native-contract audit

| Question | Finding |
| --- | --- |
| Does r61 adopt movement while performing another demanding Action? | Yes. It says an individual can normally move one yard in any unobstructed direction while performing another demanding Action, subject to specific Action exceptions (`docs/encounters/encounters-working-draft-adopted-r61.md:557`). One yard converts to 0.9144 m. This is a maximum allowance, not a minimum movement guarantee or one-hex teleport. |
| Is the allowance present in the movement rate arithmetic? | Yes. `src/movement_intent.py:evaluate_movement_rate` appends a 1.0 yd/s cap when the explicitly supplied `MovementRateConditions.concurrent_demanding_action` is true. Other limits still reduce the result; the focused test confirms lying posture yields 0.5 yd/s (0.4572 m/s). |
| Is demanding status resolved for every generated Arena Action? | No. The movement caller supplies a Boolean premise; Encounter Action/Choice state has no universal demanding-action field or classification. Current runtime does not infer this value from pending Actions. A specific native Action can have an adopted exception, but the current contract does not generalize such classifications. |
| Was `RunAction` a valid reason for the earlier test's `demanding=True` premise? | No. `src/activities.py:76-91` describes it as observing the step's displacement and never moving the Being. The 004L test was measuring ordinary locomotion with a co-resolving displacement observer, not independently performing another locomotor-demanding Action. The condition is now false in that integration proof. |
| Can both facing policies be safely applied now? | No. r61 describes six side facings and six point facings (twelve orientations), front/behind/flank sectors, the one-second facing-change timing, and the usual one-yard-per-second cap outside the front (`...adopted-r61.md:726-740`). Native instance fields are only raw `front_facing` and `top_facing` integers; constructor comments call them “1-6 on hex” and “up” (`src/object.py:114-115`). There is no reviewed mapping for twelve orientations, no facing getter/setter or consumer, and generated facing defaults are not established by encounter rules. |
| Can a turn be committed atomically with movement and seen by later Actions? | Not in the current transactional contract. The common `EvaluationSnapshot` does not include either facing field (`src/action_evaluation.py` Being snapshot construction), and the interval stage/publication contract changes positions and other listed effect state but no orientation (`src/transactional_progression.py:428-438`, `src/interval_staging.py:522-543,656-693`). A facing mutation cannot currently participate in the common pre-action/post-movement snapshot and publication guarantees. |
| What additional turn-selection decision is missing? | A movement vector is continuous, while r61 supplies twelve legal facing orientations. The adopted text does not specify which orientation to commit when the desired travel vector lies between them (including an exact midpoint tie). “Turn toward” cannot silently pick one without deciding this rule. |

## Implemented test corrections and bounded proof

The generated Arena movement proof in `tests/test_movement_intent.py` now
separates the two cases:

1. **Ordinary movement with `RunAction` as observer:** the authored open-space
   corridor and explicit Plains/Road, unhampered, standing, forward premises
   remain test-only. The demand condition is false because the co-resolving
   RunAction measures displacement. Native walk commits 1.75 yd (1.6002 m) in
   one second; the hex projection changes from `(0,0)` to `(2,1)`. The exact
   committed Cartesian position remains the displayed position, the RunAction
   succeeds, and hidden opponent identity/position remains absent from the
   public view.
2. **Another demanding Action supplied as a test premise:** rate arithmetic
   caps walk and sprint at 1.0 yd/s, exactly 0.9144 m/s, not 1 meter per
   second. A stricter lying-posture cap remains 0.5 yd/s. This test does not
   pretend to classify or schedule a native demanding Action.
3. **Current direction limitation:** backward rate is capped at 1 yd/s;
   `sideways` currently refuses with `unsupported_direction`. The test confirms
   why a maintain-facing lateral case cannot be claimed from the current
   direction enum.
4. **Facing-state blocker check:** the generated native Being reports default
   raw fields `(front_facing=1, top_facing=0)`, but the common pre-action
   snapshot contains neither. No code writes those values during movement.
5. Existing stale/arrival/unknown-input refusal assertions continue to check
   time, positions, history, pending Choices, public view, Arena/global RNG,
   and Awareness remain unchanged.

No GUI movement was enabled. Native positions remain continuous and metric;
the transaction still resolves movement before other boundary Actions.
Observer projection remains player-allowlisted. The tests explicitly author
open-space and rate premises and do not infer clearance from empty hexes.

## Remaining work and recommended next increment

Before either facing policy can affect committed movement, the native contract
needs all of the following:

- A validated twelve-orientation value with a documented mapping to `front`,
  `side`, and `behind` relative to the hex lattice; generated initial facing
  must be authoritatively selected or remain explicitly unknown.
- A movement-direction-to-orientation selection rule, including exact
  midpoint ties for continuous vectors, or another adopted way to choose the
  target facing.
- A common snapshot field and staged orientation update that commits
  atomically with movement and is visible to the same second's post-movement
  Action snapshot.
- A general Action-demand classification (with per-Action exceptions) before
  runtime can infer the concurrent-demand cap from pending Choices.

The next bounded native increment should add an adopted, versioned facing
representation and staged facing effect, then test **maintain-facing forward**
and **maintain-facing backward/side** rate categories on authored geometry.
Only after a direction-to-target-facing rule is decided should it add
turn-and-move. Keep destination browser controls disabled until arrival and
clearance are also adopted; no facing implementation can resolve those gaps.

## Verification

Commands, working directories, and results:

```sh
# Repository root
.venv/bin/python -m unittest tests.test_movement_intent -q
# 12 tests passed in 1.879 s

# Working directory: src/
../.venv/bin/python -m unittest discover -s ../tests -p 'test_running_action.py' -q
# 8 tests passed in 0.071 s
../.venv/bin/python -m unittest discover -s ../tests -p 'test_action_evaluation.py' -q
# 47 tests passed in 0.426 s
../.venv/bin/python -m unittest discover -s ../tests -p 'test_transactional_progression.py' -q
# 61 tests passed in 31.789 s

# Repository root
.venv/bin/python -m py_compile src/movement_intent.py src/arena_hex_map.py tests/test_movement_intent.py
git diff --check
```

All **128 targeted tests** passed. Python emitted environment `pyenv rehash`
and `sys.prefix` warnings, but all commands exited successfully. The full suite
was not run.

## Git and preservation

Only `tests/test_movement_intent.py`, the active movement design document, and
this report are task-owned changes. Existing tracked documentation deletions
and untracked handoff, design/report, saved-example, legacy, and workspace
materials were preserved and not staged. No changes were made to
`npc-generator`, adopted rules, or native movement/transaction code. No push
was performed. The verified test commit is `98fe0d5` (`Correct Arena movement
demand premise`). This report and the active design update are committed
separately.
