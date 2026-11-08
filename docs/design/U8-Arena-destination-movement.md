# Universe 8 Arena destination movement

## U-ARENA-004J finding: blocked on native movement contract

The generated Arena can accept the U-ARENA-004I native Run Choice and advance
one second, but it cannot yet accept a legitimate destination-derived movement
Choice. No production movement feature is added by this finding.

`SpatialState` stores only a continuous Cartesian position. `Encounter.step`
accepts an optional caller-supplied mapping of Entity IDs to three-component
velocities, integrates those vectors as constant velocity, and commits movement
before crossed integer-boundary Action resolution. That is a native kinematic
primitive, but it does not represent a player destination, choose a rate,
maintain velocity, cap motion at arrival, or check an unobstructed path.
`Encounter.choose_movement()` is a guarded stub. `RunAction` records its starting
position and reports displacement supplied by Encounter motion; it does not
produce that motion.

The generated native Elf has native `sprint()` value 0 and only an `armed
combat` skill. Its Fitness and race could participate in the adopted r61 speed
formula, but Universe does not currently derive/store that movement speed:
`Speed` still marks actual speed incorporation as TODO. Rules r61 define rate
categories, race/Fitness sprint values, Run-skill increments, and MMR modifiers
for terrain, hampering, physical fatigue, heavy load, and encumbrance. There is
no implemented native movement operation applying those inputs to a destination
and interval. Revision 63 preserves full-precision metric coordinates; it does
not add a movement controller.

## Existing behavior and proof boundary

The reproducible proof activates the generated Encounter through the ordinary
ChoiceBook proposal/validation/acceptance/publication path, then calls native
`step(1)` without inventing a velocity. The Encounter commits t=1; Run resolves
`no_movement`, and the player's native position and Awareness remain unchanged.
The native velocity input can move an entity when supplied (covered by the
existing Encounter movement tests), but translating a destination into such a
vector, movement rate, arrival stop, and collision/path result is not a native
Choice or Action contract. The generated browser therefore has no destination
route, arrow, speed, or ETA.

## Minimum decision and next implementation seam

Before Arena destination control can be implemented, adopt or explicitly
authorize a native movement-intent contract that names a permitted rate (or a
documented default), specifies how the destination constrains motion and
arrival, and defines path/occupied-space handling. The existing rule text gives
movement-rate formulas but does not settle how this generated continuous Arena
represents an unobstructed path and occupied Being space: its hexes are
presentation/initial-placement only, and generated Being geometry is absent.

The minimum next engineering slice after that decision is a native Movement
Choice/resolver that derives legal per-interval velocity from existing race,
Fitness, Run skill, load, fatigue, environment, and adopted path rules, then
feeds the existing movement-before-Action phase. Only that native resolver may
ground speed and ETA display. Do not derive a velocity or arrival time in the
browser, treat cells as collision geometry, or use `RunAction` as a movement
resolver.

## U-ARENA-004K: bounded movement-rate and intent foundation

The native `movement_intent` service now implements rate derivation from r61
and a one-second destination intent for already-initiated transactional
Encounters. `MovementIntent` is a distinct value containing actor ID,
full-precision `CartesianPosition`, selected rate category, decision ID, and
target boundary. It is supplied separately from `ChoiceBook` Action Choices.
`Encounter.step` preflights it under the existing transactional publication
boundary, converts it to a one-second velocity, and passes that vector through
the existing movement staging/integration path. `EncounterStep` reports the
movement decision ID. Staging still moves before Actions resolved at the
boundary. No movement value is stored on `SpatialState`, and no destination is
retained after that one-boundary request.

The evaluator uses native race, Fitness, Run rank (missing ordinary Run skill
means rank zero), legacy physical fatigue level, and Strength. r61 contributes
the race-specific base sprint, Run's one-foot-per-second per-level maximum
speed increment, rate-category ratios, MMR, fatigue category ceilings,
heavy-load and encumbrance factor, posture and backward caps, and the usual
one-yard-per-second cap during a concurrent demanding Action. It converts
yards per second to meters per second at 0.9144 without rounding position.
Terrain, hampering, encumbrance, posture, direction, and Action demand are
required explicit `MovementRateConditions`; there are no neutral defaults.
Unsupported race/Strength table values, invalid or absent conditions, fatigue
incapacity, and nonpositive resulting rates refuse explicitly.

Movement is an interval decision, not a persistent path. To change direction or
category, submit a new intent for the next untouched boundary; omitting an
intent means no destination-derived movement on that interval. There is no
implicit arrival clamp: an intent is refused if the selected interval could
reach its destination. This avoids inventing endpoint behavior. The interface
also refuses simultaneous caller velocities, non-one-second duration, stale
boundary references, and uninitiated/nontransactional Encounters. It does not
register an Action, activate an Encounter, add Awareness, or alter the target-
free activation record.

### Verified proof boundary and remaining decisions

Focused tests author a neutral Plains/Road, unhampered, fresh, unencumbered,
standing, forward-aligned test case and a clear 20-meter corridor. The authored
fixture places the player at `(0,0,0)` and opponent reference point at
`(0,100,0)` meters, but expressly does **not** infer clearance or collision
safety from those points. A selected walk while a one-second `RunAction` is
pending derives 1 yd/s due to the concurrent-Action cap, commits 0.9144 meters
at t=1 through the native movement phase, then the Run observer succeeds on
that displacement. The generated browser still has no destination route. This
is a test-fixture proof of the native integration seam, not proof that generated
Arena corridors are traversable.

Unresolved before generated-player movement can be safely enabled:

- **Facing and direction:** the Being's native `SpatialState` has no
  orientation. Adopt a facing source/relative-direction mapping or restrict
  movement to a rule-backed direction that can be proven. The test explicitly
  premises forward alignment; runtime does not establish it.
- **Destination completion:** adopt what happens when a step reaches or passes
  a destination (stop, clamp, or preserve category motion), and what constitutes
  a revised/withdrawn destination at a boundary. The current contract refuses
  an interval that could arrive and retains no destination.
- **Clearance and occupied space:** adopt Being geometry/reference-point
  semantics and path/obstacle/occupied-space handling, including the
  movement-while-connected cases in r61. The current intent does not test
  collision or path clearance.
- **World context:** provide an authoritative source for terrain and hampering
  along a proposed path, carried mass, posture, and whether other Actions limit
  movement. These factors are explicit caller inputs today; production Arena
  has not established them as a coherent native snapshot.
- **Non-forward directions:** r61 expresses these limits using hex movement,
  while r63 Arena coordinates remain continuous meters and the Arena grid is a
  presentation overlay. Adopt the direction-to-rate mapping before enabling
  sideways/oblique movement.

Until those decisions and authoritative inputs exist, keep browser destination
submission, ETA, and speed indicators disabled. The next GUI-capable slice is
not a UI route: first add adopted direction/destination/clearance and context
decisions, then validate that native snapshot in the transactional movement
preflight and add tests before exposing it to the player.

## U-ARENA-004L: derive supported inputs from native Being state

The previous 004K observation that the native skill dictionary lacked `Run`
was a capitalization error. The schema and installed `src/config/skills.tsv`
already define lowercase `run` as ordinary and progressive, matching r61's
Run skill header. Skill names are case-sensitive. The movement evaluator now
validates that exact native definition before interpreting a missing Being
rank (`None`) as zero; a missing/malformed definition refuses. This changes no
Generator output, rank, experience, or practice history.

`derive_native_movement_inputs` now reads race, Fitness, Strength, Run rank,
legacy discrete physical-fatigue level, and represented carried mass from
native Being/Universe state. The carried-mass reader deduplicates the native
possession, weapon, armor, and held-object IDs, resolves their native pound
weights, and includes represented contents through `parent_container_id`.
Unknown IDs, non-finite/negative weights, and unsupported Being-as-gear
references refuse. An empty represented inventory resolves to known 0 lb. The
helper is read-only and runs under the existing transactional publication
boundary before movement staging. It reads Being fields, item weights, and
container links from the common frozen pre-action snapshot, which closes over
represented inventories and nested contents. A regression captures a 1.5 lb
Brick, mutates its live weight afterward, and confirms movement still uses the
snapshot's 1.5 lb. Rate arithmetic still feeds the same native
movement-before-Action pipeline.

Generated-Arena tests now use `GeneratedArenaSession.generate()` and its
approved `choose_run()` activation, then submit a direct one-second native
MovementIntent in a test. The test sets a labeled clear corridor and forward
alignment premise, plus Plains/Road, unhampered, standing posture, and the
co-resolving Run Action's demanding classification. It verifies that the
session projection exposes only the player allowlist, the t=1 position and Run
outcome commit, and both global and Arena RNG remain unchanged. A no-change
test covers refusal. No destination route was added to the browser.

Remaining context gaps are unchanged: no authoritative terrain/hampering map,
posture model, direction-to-coordinate mapping, demanding-Action classification,
generated body geometry, collision/clearance contract, or destination-arrival
rule. The test premises do not establish production movement legality.
