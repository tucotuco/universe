# U-ARENA-011 — Hex-occupancy reach for native melee against Beings

**Project:** Universe 9 (`universe` repository)<br>
**Owner:** Codex<br>
**Install at:** `docs/assignments/U-ARENA-011.md`<br>
**Report:** `docs/reports/U-ARENA-011-report.md`<br>
**Type:** Bounded native rules integration and playable demonstration<br>
**Supersedes:** Earlier U-ARENA-011 assignment requesting test-only Being geometry

## Desired outcome

A properly equipped Arena Being can attempt a native Swing or Thrust against an observed target Being **without requiring modeled 3-D Being body geometry**. For melee against a Being in a hex-based Encounter, an attack has the spatial possibility of affecting that Being when its legal reach **enters the hex occupied by the target at impact**. A reach envelope reaching into that hex is an eligibility condition, **not an automatic hit**. Native attack/defense rolls, consequences, scheduling, simultaneous resolution, and other applicable constraints remain authoritative.

This is a deliberate hex-scale combat abstraction, **not** an inference that the target's physical body occupies the whole hex. Do not generate bodies, collision volumes, or invented dimensions from stature, mass, or race.

## Controlling decision

1. **At impact**, determine the target Being's occupied hex from the target's authoritative continuous metric position using existing hex-grid geometry and deterministic boundary handling. Do not substitute a rendered marker or center-to-center approximation for the actual hex containing that position.
2. Compute whether the attacker's **existing native melee reach** can enter the interior of that target hex from the attacker's authoritative impact-time location. Interpret *enter* as a nonzero interior overlap, not mere edge or vertex tangency. Use the existing regular hex geometry (one yard across flats), the established unit conversion, and any already-adopted attack direction/facing restrictions; introduce no new attack arc or hand/reach rule. The target's center/reference point need not lie within reach.
3. If reach enters the occupied hex, absence of a Being `Geometry3D` must **not** cause `uncertain_path` merely because the target has no modeled body volume. For the initially unobstructed Arena, the target hex can be reached without a separately modeled Being shape. Preserve any independently established barriers, action prerequisites, defense, and other combat restrictions; do not declare paths clear through known obstacles.
4. If reach does not enter the target hex, use the existing native `out_of_reach` result at impact; do not reject an otherwise well-formed attack simply for being distant when scheduled.
5. This rule addresses **Being targets in hex-based melee**. Do not change non-Being collision tests, projectile physics, visibility, movement, or combat outside a defined hex context. Apply it in the native Encounter melee path, not as a browser-side hit calculation or an Arena-only fake result.

If the current native resolver needs a distinction between *reach can enter occupied hex* and *the attack actually hits*, keep the existing attack/defense decision machinery. Do **not** add a shortcut that awards damage for hex overlap alone. If no lawful hit/damage mechanism exists after removing the body-path gate, characterize the missing contract and stop rather than inventing a probability.

## Deferred geometry boundary

This hex-occupancy rule is **only a melee targetability abstraction**. Physical Being geometry remains a planned and important component of the Encounter model, particularly for line-of-sight, concealment/cover, thrown Objects, and missile-weapon trajectories and interception. Do not use the hex-reach result as a substitute for visibility, cover, or projectile collision, and do not delete or generalize away existing geometry infrastructure. Record any concrete geometry dependency identified during implementation as deferred work; do not resolve it under this assignment.

## Work

1. **Inspect first:** Review U-ARENA-010's `MeleeStrike` impact pipeline, why it yielded `uncertain_path`, existing hex coordinate/occupancy utilities, reach and facing computation, result variants, applicable Encounter rules, and save snapshot admission. Confirm whether current native checks conflate reach with target-volume path interception. Identify the narrowest code seam for the new rule.
2. **Implement the occupancy reach gate** as a small reusable native spatial/melee operation, with deterministic numeric and hex-boundary behavior. Use only authoritative impact-time positions and already defined hex orientation/scale. Avoid geometry generation, new fighting mechanics, speculative obstacle handling, and browser-specific combat logic.
3. **Demonstrate a native armed exchange** starting from the actual `npcgen.api.arena_ready_being(...)`-created Dagger and unchanged Arena UI/HTTP submission. Select a reproducible seed/scenario where legal reach enters the opponent's occupied hex. Advance through genuine native scheduling/resolution; report the real outcome, including any attack/defense result and HP consequence. Do not force dice or invent effects just to obtain damage.
4. **Regression controls:** Include (a) reach enters the target's hex even though the target reference point is farther than reach; (b) reach does not enter and native `out_of_reach` occurs at impact; (c) equal-hex cases and deterministic edge/boundary cases; (d) scheduling while initially distant, movement, then impact assessment; and (e) a standard default generated Being with `geometry=None` that no longer fails merely on that ground. Verify unchanged refusal for absent/unready Dagger and unobserved target.
5. **Persistence and privacy:** Save an accepted attack while pending, load without calling `npcgen`, and compare completion to uninterrupted play, including native Object and Action identity, state, RNG cursor, result and observer evidence. Keep original source NPC facts hidden from opponents; do not leak native IDs or private condition through browser feedback. Preserve independent ground-loadout behavior and existing saves.
6. **Browser smoke:** Exercise the native HTTP/session path and shipped JavaScript handler. Attempt a real-browser final attack click if readily feasible; explain any tool limitation rather than declaring it tested.

## Acceptance evidence and limits

- A generated equipped Being can submit Swing/Thrust and reach resolution against another generated Being based on hex occupancy, without invented body geometry or an `uncertain_path` arising solely from missing Being geometry.
- Hex reach is **not** automatic hit or damage; ordinary native strike outcomes and constraints remain operative. Include a genuine resulting example, whether hit or miss, and document any current engine limit preventing a positive consequence.
- Focused new tests and nearby regressions, with exact command, count, and elapsed time; `py_compile` and `git diff --check`. Do not run the full suite for this bounded change.
- Commit only the coherent implementation/tests and report closeout. Preserve unrelated dirty files and historical Git state. Do not change `npc-generator`, rewrite history, or push.

## Report format

1. **Result / where we stand**
2. **Native impact contract before and after** (including the hex-overlap definition and numeric boundary behavior)
3. **Executable armed-exchange example and controls**, with actual native outcomes
4. **Save/Load, observer evidence, and browser verification**
5. **Known limits / any rule decision still needed**
6. **Tests, timings, commits, and working-tree preservation**
