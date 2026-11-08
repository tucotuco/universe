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
represents an unobstructed path and occupied Being space: its square cells are
presentation/initial-placement only, and generated Being geometry is absent.

The minimum next engineering slice after that decision is a native Movement
Choice/resolver that derives legal per-interval velocity from existing race,
Fitness, Run skill, load, fatigue, environment, and adopted path rules, then
feeds the existing movement-before-Action phase. Only that native resolver may
ground speed and ETA display. Do not derive a velocity or arrival time in the
browser, treat cells as collision geometry, or use `RunAction` as a movement
resolver.
