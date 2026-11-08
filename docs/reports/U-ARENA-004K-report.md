# U-ARENA-004K — Native movement-rate and intent foundation

## Disposition

Implemented a native movement-rate evaluator and bounded, one-second movement
intent path into the existing transactional Encounter movement phase. The
vertical slice commits a real 0.9144 m displacement before a co-resolving
`RunAction` observes it. This proof is limited to an explicitly authored test
fixture. It does not establish generalized movement through a generated Arena,
and it does not enable a browser destination control. No NPC Generator files
were changed and nothing was pushed.

## Authority reviewed

- `docs/encounters/README.md` confirms adopted r61 as the controlling movement
  rules, with r62 and r63 as limited supplements.
- `docs/encounters/encounters-working-draft-adopted-r61.md`, Movement and
  Movement Rates Table: race/Fitness sprint; category ratios; MMR factors;
  fatigue-category ceilings; backward, crouching, lying, and concurrent-Action
  caps; the heavy-load table; and Run skill's one-foot-per-second per-level
  addition to maximum speed.
- r62 does not provide destination locomotion. r63 retains full-precision
  metric spatial positions and does not adopt a new movement lattice.
- `src/spatial/state.py` stores position only. `src/encounter.py` accepts
  velocity vectors and advances through its boundary lifecycle. The guarded
  `choose_movement()` remains unimplemented. `src/interval_staging.py` stages
  motion before boundary Actions. `RunAction` records start position and
  reports displacement; it does not create movement.
- `docs/reports/U-ARENA-004I-report.md`,
  `docs/reports/U-ARENA-004J-report.md`, and the existing design record
  establish transactional Arena activation and the preceding destination
  movement blocker.

## Changes

- Added `src/movement_intent.py` with `MovementRateConditions`,
  `MovementIntent`, structured rate/preflight results, and explicit refusal
  codes. Rates use the participating Being's race, native Fitness and Strength,
  Run skill rank, and native physical-fatigue level. A missing ordinary Run
  skill is rank zero. The evaluator applies r61 ratios and caps and converts
  yards per second to meters per second at 0.9144 without rounding coordinates.
- Terrain multiplier, hampered multiplier, carried mass, posture, direction,
  and concurrent demanding-Action status are mandatory explicit inputs. There
  are no production-neutral defaults. Unsupported race or carrying-capacity
  values, invalid context, incapacitating fatigue, nonpositive resulting speed,
  invalid actors/destinations, and unsupported interval/direction cases refuse.
- `Encounter.step` and `step_transactionally` accept an optional
  `MovementIntent` independently of Action Choices. Under the existing
  publication boundary, preflight derives one velocity for exactly one native
  second and feeds the existing transactional movement staging path. The
  `EncounterStep` now reports the committed movement decision ID. The legacy
  nontransactional path rejects movement intents. Intent and velocity cannot
  be combined.
- A movement intent applies only to the next untouched integer boundary. It is
  not persisted: a caller must submit a new intent to change or continue
  movement; omitting one means no destination-derived movement for that
  interval. It cannot initiate an Encounter or register an Action. An interval
  that could reach the destination refuses with `arrival_unsupported`, because
  adopted arrival behavior is not implemented here.
- Updated `tests/test_arena_destination_movement_blocker.py` to preserve the
  position-only/presentation-grid boundary while recognizing the new explicit
  native intent API. Added `tests/test_movement_intent.py` for formulas,
  fail-closed inputs, atomic rejection, RNG/observer isolation, and the
  movement-before-Action proof.
- Updated `docs/design/U8-Arena-destination-movement.md` with the implemented
  contract, its proof limits, and unresolved rule/context decisions.

## Executable proof and rate evidence

Run the focused proof with:

```sh
.venv/bin/python -m unittest tests.test_movement_intent tests.test_arena_destination_movement_blocker -v
```

The fixture authors the moving Elf at `(0,0,0)` and the second Being's
reference point at `(0,100,0)` meters. It expressly declares the test corridor
from `(0,0,0)` to `(20,0,0)` clear for the demonstration. That declaration is a
test-world premise; neither the Arena grid nor the reference-point locations
prove clearance, and the implementation does not define Being volumes or
perform collision checks. The fixture also expressly supplies neutral
Plains/Road and unhampered multipliers, fresh physical fatigue, zero carried
mass, standing posture, forward alignment, and a concurrent demanding Action.
It asserts the generated fixture has no native possessions or weapons before
using the zero-mass premise.

For the fixture Elf (Fitness 14, Strength 13, PFL 0, no encumbrance), r61 gives
a sprint of 14/2 = 7 yd/s. Its Strength heavy-load upper bound is 150 lb, so
with the authored zero encumbrance and unit terrain/hampering factors, MMR is
also 7 yd/s. At Run rank zero the evaluator returns:

| Category | yd/s | m/s |
| --- | ---: | ---: |
| Sprint | 7 | 6.4008 |
| Run | 14/3 | 4.2672 |
| Jog | 3.5 | 3.2004 |
| Hustle | 7/3 | 2.1336 |
| Walk | 1.75 | 1.6002 |

The test fixture installs an adopted Run skill definition because the
installed native skill dictionary does not contain `Run`; it sets rank 3 using
the native skill API and verifies all five category ratios again. The rule's
three-foot increment raises sprint to 8 yd/s, with category rates derived from
that maximum. This is fixture setup only; no skill dictionary or Generator
content was changed in production.

For the committed-motion proof, the chosen walk category is 1.75 yd/s, but the
co-resolving Run Action imposes r61's usual one-yard-per-second cap. The step
reports decision `arena-move-1`, commits X displacement of exactly 0.9144 m at
Encounter time 1, then the existing RunAction reports success using that
displacement. Y and Z remain unchanged. Both participants' Awareness lists,
global RNG, and the Arena-owned RNG cursor remain unchanged. No target-free
activation or Action Choice semantics were changed.

The invalid-intent test confirms unknown movement context, a destination
reachable within the requested interval, and a stale boundary all refuse
without changing Encounter time, player position, event-history keys/values,
pending Actions, Choice state, RNG, or the actor's Awareness. The successful
motion proof separately checks that both participants retain empty Awareness.

## Verification

All commands used the repository `.venv`. The focused proof command above
passed **7 tests** in **1.16 s** after the final rate-boundary and fixture
assertions.

Adjacent regressions, run from `src/` because the legacy tests load config and
fixture modules relative to that working directory:

```sh
../.venv/bin/python -m unittest discover -s ../tests -p 'test_transactional_progression.py' -v
../.venv/bin/python -m unittest discover -s ../tests -p 'test_running_action.py' -v
../.venv/bin/python -m unittest discover -s ../tests -p 'test_encounter_spatial.py' -v
```

Results: transactional progression **61 passed** (28.21 s); RunAction **8
passed** (0.79 s); Encounter spatial bridge **10 passed** (0.78 s). Together
with the latest focused group, **86 tests passed**. These are targeted regressions,
not a full-suite run. The generated browser/activation and position-only
blocker tests are included in the focused group.

An initial invocation using system `python` rather than `.venv/bin/python`
failed because that interpreter cannot import the installed `npcgen`
dependency. A first attempt to run older adjacent tests from the repository
root also failed due their documented relative-import/config assumptions; the
same tests passed from `src/` using the `.venv`. These were invocation
environment errors, not code failures.

Syntax and Git checks:

```sh
.venv/bin/python -m py_compile src/movement_intent.py src/encounter.py src/transactional_progression.py tests/test_movement_intent.py tests/test_arena_destination_movement_blocker.py
git diff --check
```

`py_compile` passed for both changed runtime modules and both test modules;
`git diff --check` passed with no whitespace errors.

## Remaining decisions and smallest next slice

This implementation establishes rate arithmetic and a one-interval target
vector, not a generally validated movement system. `SpatialState` has no
orientation, so `direction="forward"` is an explicit supplied premise rather
than a relation verified against facing. A destination vector cannot yet be
classified authoritatively as forward, backward, or hex-direction movement.
Runtime does not establish a path's terrain or clearance, Being occupied-space
semantics, obstacles, connected Grab/Hold movement, or path-dependent
hampering. Carried mass, posture, and competing-Action restrictions also lack a
unified authoritative movement snapshot. Movement rates above supported
carrying-capacity table values fail closed. The Arena grid remains only a
presentation/initial-placement overlay.

Before GUI exposure, choose among these rule/contract options:

1. **Facing:** adopt persistent native orientation plus a coordinate-to-rule
   direction mapping; or keep Arena movement disabled until such orientation
   exists; or permit a caller-attested forward alignment only for authored
   scenarios and keep it out of generated-play UI.
2. **Arrival:** stop/clamp at the destination within an interval; allow the
   selected rate to pass the point and apply a new next-boundary intent; or
   require one-interval destinations and add a rule for partial speed/time.
   The current implementation refuses possible arrival and does not choose
   among these.
3. **Clearance:** adopt native shape/occupied-space and path tests; explicitly
   constrain an initial production Arena to a separately adopted movement
   space model; or continue limiting proof to authored clear-corridor fixtures.

The next GUI-capable slice should follow only after those inputs and rules are
settled: build a native movement snapshot/preflight that can prove direction,
movement conditions, arrival, and path legality under the selected contract;
then add browser submission of that accepted one-second movement intent. Keep
the browser free of independent rate or ETA calculations.

## Git state and delivery

At task start, the checkout already contained unrelated tracked deletions and
untracked user materials, including handoff/design/report files, saved
examples, legacy material, and workspace JSON. They were preserved and were
not staged. Only the following task paths are intended for commits:

```text
src/movement_intent.py
src/encounter.py
src/transactional_progression.py
tests/test_movement_intent.py
tests/test_arena_destination_movement_blocker.py
docs/design/U8-Arena-destination-movement.md
docs/reports/U-ARENA-004K-report.md
```

No Generator source, adopted rules, generated browser routes, unrelated
workspace material, or remote Git state is changed.

Implementation commits: `805b3f9 Add native Arena movement intents` and
`5905e8d Cover adopted carrying-capacity bounds`. The design record and this
report are committed separately after final documentation checks.
