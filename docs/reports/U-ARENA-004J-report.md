# U-ARENA-004J engineering report

## Disposition

The requested destination-movement slice is **blocked by the current native
movement contract**. No production code or browser behavior was changed. The
generated Arena remains able to use the U-ARENA-004I target-free Run Choice and
advance one native second, but that Run result is only a displacement
measurement; it is not a movement command. I added a reproducible proof,
focused blocker tests, and the design record at
`docs/design/U8-Arena-destination-movement.md`.

## Inspected authority and implementation

- Adopted r61 movement rules, supplemented by r62/r63, state that movement
  rates depend on race, Fitness, and Run skill; r61 specifies sprint/run rate
  relationships and the maximum-movement-rate modifiers for terrain,
  hampering, physical fatigue, load, and encumbrance. See
  `docs/encounters/encounters-working-draft-adopted-r61.md:542-561,2367-2373`.
  Revision 63 retains full-precision metric Cartesian positions and yard-based
  presentation; it adds no motion controller. See
  `docs/encounters/encounters-consistency-decisions-r63.md:5-13`.
- `SpatialState` stores only `position`; its documentation explicitly leaves
  persistent velocity and orientation for later (`src/spatial/state.py:116-134`).
  Native `integrate_position` computes constant-velocity displacement from a
  caller-provided vector (`src/spatial/state.py:149-154`).
- `Encounter.step(duration, velocities, velocity_frame, ...)` requires a
  caller-supplied Entity-to-vector mapping for motion and integrates it before
  dispatching each crossed integer boundary (`src/encounter.py:1173-1179,
  1212-1255`). The transactional staging path likewise consumes velocity
  vectors and stages movement before Action resolution (`src/interval_staging.py:449-464,646-663`).
- The built-in `Encounter.choose_movement()` is a guarded stub and returns
  `None` (`src/encounter.py:1380-1387`).
- `RunAction` explicitly observes displacement made by Encounter velocities
  and never moves its actor; its resolver reports `no_movement` at zero
  displacement (`src/activities.py:76-89,138-159`).
- `BeingInstance.sprint()` returns `current.max_speed.sprint()`
  (`src/being.py:630-635`), while `src/speeds.py:8-20` still marks actual
  speed incorporation as TODO. In the reproducible generated sample, the
  controlled Being is an Elf with Fitness 14, has native `sprint()==0`, and
  has only `armed combat` in its skill map (no Run skill). The adopted rules
  would derive base Elf sprint from Fitness, but the live native speed field
  does not contain that derived rate.
- U-ARENA-004F's one-yard-cell map is initial placement/presentation only. It
  does not supply path, obstruction, or collision data, and generated Beings
  have no adopted physical geometry mapping. Treating cells as movement space
  or inventing point/body collision semantics would exceed this assignment.

Together these APIs support externally authored velocity integration, not a
native player Choice containing a destination. Destination-to-direction,
permitted movement rate, movement stopping/arrival behavior, and path/occupied
space legality are absent. A destination arrow's speed or ETA therefore cannot
be grounded in current native state.

## Reproducible blocker proof

From the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python examples/generated_arena_destination_movement_blocker.py
```

The script initializes a 0-XP 5×5 generated candidate (seed `20261107`),
checks the native `choose_movement()` hook and the `Encounter.step` signature,
accepts Run through the existing native activation/Choice path, and advances
one native second without supplying a movement vector. The command printed this
result (Encounter and Being UUIDs are intentionally not included in the
diagnostic):

```text
{'choice_state': 'executing', 'activation_kind': 'first_player_choice', 'time_seconds': 1, 'run_outcome': 'no_movement', 'position_unchanged': True, 'native_sprint_value': 0, 'generated_skill_names': ['armed combat'], 'spatial_state_fields': ['position'], 'step_parameters': ['duration', 'velocities', 'velocity_frame', 'adult_member_candidate'], 'destination_api_available': False, 'choose_movement_result': None}
```

The exact deterministic sample starts at `(4.1148, 1.3716, 0.0)` meters and
remains there at t=1. No velocity is authored in this proof. Existing native
velocity tests demonstrate that supplying a caller-selected vector to
`Encounter.step` moves a Being, but that vector is not a destination Choice and
does not validate speed or path legality.

An in-memory generated browser route test POSTs to the absent destination route
and gets HTTP 404 with the empty session unchanged. No browser destination UI,
arrow, speed, ETA, or movement route is claimed. No loopback server or browser
visual smoke test was run.

## Minimum decision and recommended next slice

The destination-selection preference is already clear. Before implementing it,
the minimum remaining contract decision is to specify (1) which native movement
rate is selected by a destination-only Choice (or whether the player must also
choose Walk/Run/etc.), (2) what the native resolver does at arrival within a
one-second interval, and (3) what authoritative path/occupied-space model
applies in this Arena when its square cells are presentation-only and generated
Being geometry is absent. The adopted rate formulas can then be implemented as
native calculations; do not substitute the current zero `Speed` field, choose
an arbitrary vector, or infer geometry from the display grid.

After those decisions, implement a native Movement Choice/resolver that uses
the adopted r61 rate factors and native one-second movement-before-Action
phase. Only then connect destination submission, arrow, and any speed/ETA to
the generated player projection. The observer-safe projection must continue to
omit the unaware opponent and its private position/state.

## Validation and repository state

Focused blocker, native frame/velocity, and Run tests:

```sh
cd tests
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=../src:../examples ../.venv/bin/python -m unittest test_arena_destination_movement_blocker test_encounter_frame test_running_action -v
```

Result: **14 tests passed in 0.425 seconds**. The two new blocker tests verify
that native state/API lacks a destination contract, the generated Run Choice
still advances transactionally without displacement or Awareness, and the
browser endpoint refuses an unsupported destination request without mutation.
The remaining tests verify supported native velocity-frame integration and
Run's existing displacement-observer semantics.

`git diff --check` passed. No full suite was run. No application features,
native movement rules, NPC Generator files, or U-ARENA-004A publication history
were changed. The checkout contained unrelated pre-existing deletions and
untracked files; they were preserved and not staged. No push was made.

Task-owned commit `4506703` contains the executable proof, blocker tests, and
design record; this report is committed separately after verification. No
production changes are left uncommitted.
