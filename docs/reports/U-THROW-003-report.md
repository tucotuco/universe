# U-THROW-003 — Native Throw integration boundary

## Status: partial / blocked

The assignment's required native Throw and chronological landing could not be safely completed within the current closed Action/transaction architecture. A runnable fixture now reproduces the native refusal and prints a separately labeled pure drag-free flight projection. **No Throw Action was accepted or completed, no release or landing was published, and no native Throw receipt exists.**

## Source-grounded blocker

The example constructs a real native base `Action` with `event_type="throw"`, an actor, and a registered Object instrument, then sends it through `Encounter.propose_choice()` and `Encounter.validate_choice()`. Validation returns `invalid_schedule: unsupported transactional base Action activity`; the Action is not registered, no active-Object reservation is made, and Encounter time/RNG/Object state remain unchanged.

The refusal is consistent with the current source contracts:

- `src/transactional_progression.py::validate_action_contract` admits exact reviewed Action classes and explicitly limits the base `Action` activity to `swing` and `thrust` (lines 263–298). There is no `ThrowAction` adapter.
- `src/action_evaluation.py` maps only reviewed combat, melee, defense, Run and Spot families and excludes `throw` from its native event/family checks. `src/action_settlement.py::_FAMILIES` likewise has no Throw proposal family. A custom subclass or completion callback would fail the existing closed-family/callback checks; bypassing them would not be a native transaction.
- `src/scheduling.py::PreparedSchedule.from_action` reserves an instrument only for the existing active-use event types (`swing`, `thrust`, `parry`). There is no approved Throw release/handoff adapter.
- `src/spatial/state.py::SpatialState` stores position only. `Encounter.step()` accepts caller-supplied velocities for that call, and `transactional_progression.step_transactionally()` stages those inputs; neither persists an independent projectile velocity/flight state after the thrower releases an Object. No candidate or publisher effect advances a launched Object or records landing chronology.

These are two linked gaps: a closed native Throw evaluation/publication family, and authoritative per-interval projectile flight state. Adding only a calculator, manually changing Object positions in an example, or scheduling external velocities would not demonstrate the required native release-to-landing lifecycle.

## Safe bounded work delivered

- `src/throwing.py` now provides an immutable `DragFreeTrajectoryProjection` and `project_drag_free_trajectory(...)`. This is a pure calculation only: explicit azimuth/elevation, positive release height, flat landing plane, fixed `g=10 m/s²`, full-precision SI positions/velocity, and yard-based input/output velocity/range. It rejects missing/nonfinite/nonpositive velocity, unsupported angles, invalid positions and a release point not above the landing plane. It does not model collision, damage, drag, wind, bounce, RNG, persistence, or authoritative mutation.
- `examples/native_throw_arena.py` builds a one-Being/one-Object transactional Encounter and demonstrates normal native Choice validation refusing the Throw. It then prints a distinct pure trajectory projection. The Object remains at its initial authoritative position; projected flight positions are never presented as committed state.
- `tests/test_native_throw_arena.py` covers the exact native refusal and absence of Action registration/reservation/time advance/RNG change, trajectory units and positive landing solution, determinism, and invalid projection inputs. Existing `tests/test_throwing.py` continues to cover mass response, category/reference-arm rules, skill modifier and input checks.
- `TASKS.md` and `docs/tasks/encounter-engine.md` now mark U-THROW-003 blocked at this integration boundary.

The fixture authors Strength 10, Throw level 1, a 69-inch Being, and a 1-pound Object. Under the adopted Strength-10 data, the Object is below the 50-pound maximum throwable weight and within the 4-second preparation bracket (one-tenth of the 33-pound light-load upper limit). Those checks make the projected case representative; they do not bypass the native refusal or claim that the engine enforces these eligibility limits.

## Example output

Command:

```text
PYTHONDONTWRITEBYTECODE=1 python examples/native_throw_arena.py
```

Observed output:

```text
Authored inputs: Strength=10; Throw level=1; height=69 in; Object weight=1 lb
Native transaction admission: refused [invalid_schedule]: unsupported transactional base Action activity
accepted=False; pending_actions=[]; reservations=(); action_registered=False
projectile_authoritative_position=(0.0, 0.0, 0.9) m (unchanged; no release)
Pure projected trajectory only (not committed native state):
release speed=16.914720128 yd/s = 15.466820085 m/s
flight time=2.337306188 s after hypothetical release
landing position=(25.562401076005166, 0.0, 0.0) m
horizontal range=27.955381754 yd (25.562401076 m)
```

The example also prints the explicit seed 141, authored 45-degree elevation/0-degree azimuth, projected positions through the exact fractional landing time, and states that no Action completion, receipt, practice, committed flight frame, or landing is claimed. The fixture consumes no RNG; it does not demonstrate RNG transfer.

## Smallest safe next implementation boundary

A subsequent approved implementation should add one reviewed exact `ThrowAction` contract through the existing proposal/scheduling/evaluation/settlement/publisher path. Its accepted schedule must reserve the specific Object for the four-second interval. The completion-boundary candidate should atomically transfer the Object from carried/ready state to an immutable flight state containing the release snapshot, SI velocity, authored direction, launch boundary and exact projected impact time. Each later integer interval should derive that Object's movement from its last committed flight state; the first boundary that crosses impact should publish the landing position and exact subsecond impact timestamp together. Earlier snapshots must remain unchanged, and other Actions may observe only the committed post-movement state at their integer boundary.

The existing spatial state preserves floating-point positions without rounding (`CartesianPosition` and `integrate_position`); no new rounding rule was added. A remaining design check is whether a flight impact inside an interval should become visible to Actions only at the next integer boundary, as implied by the existing coordinator, or whether any additional within-interval interaction is required. Do not add a subsecond Action clock, target roll, damage, practice award, collision/interception, bounce, drag, or wind in that first vertical slice without separate rule authorization.

## Verification

- Focused command: `PYTHONPATH=tests python -m unittest tests.test_native_throw_arena tests.test_throwing tests.test_action_choices tests.test_action_evaluation tests.test_action_settlement tests.test_transactional_progression tests.test_npc_being_arena -q` — **226 tests passed**, 29.364 seconds.
- The focused selection includes native Choice reservation behavior, frozen evaluation/settlement, transactional progression, the existing NPC Dagger/Reach path, and Throw reference math. The long HTTP persistence suites and full ~1,761-test suite were not run, as directed.
- Example command above — completed and showed the expected native refusal and separate pure projection.
- Changed Python files (`src/throwing.py`, `examples/native_throw_arena.py`, `tests/test_native_throw_arena.py`) compiled using Python's `compile()` builtin without bytecode output.
- `git diff --check` and staged-diff whitespace checks passed. New/changed source and report files had no trailing-whitespace matches.

## Commits and repository preservation

- `0efe55923a1c2195fe3fd7f383f99f18f1292b6c` — `Add bounded Throw trajectory blocker fixture` (five exact paths: `TASKS.md`, `docs/tasks/encounter-engine.md`, `src/throwing.py`, `examples/native_throw_arena.py`, `tests/test_native_throw_arena.py`). Parent: `10876be5fb98e303bb32ded2e984e2efc9a9b11e`.
- No push. The report is a separate documentation closeout path.
- Work began on `main` at `10876be5fb98e303bb32ded2e984e2efc9a9b11e`, with an empty index. Existing user-managed deletions, untracked `docs/encounters/`, `.agents/`, `.claude/`, `legacy/`, saved JSON/workspace files, and other untracked artifacts were not staged or altered. No Encounter rules, Arena, MeleeStrike, checkpoint, Observation/Belief, or legacy files were changed.

U-THROW-003 remains blocked until the native Action/effect adapter and persistent chronological projectile lifecycle can be safely integrated. This report does not claim the assignment's native Throw completion criteria are met.
