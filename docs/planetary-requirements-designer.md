# Planetary requirements and interactive designer

**Status:** second bounded planetary experiment; *not* a general constraint engine,
full inverse orbital solver, or replacement for the Keplerian ephemeris.

## Motivation

A world may already establish that a village has a ~30-hour solar day and
~11.45 hours of winter daylight at 40°N without specifying axial tilt, an
orbital year, lunar masses, or a complete star system. The first question
"when does the Sun set here?" should realize only properties needed to answer
it. The world builder should be able to try alternative admissible answers
without committing any of them until explicitly choosing one.

The experiment separates four operations:

| Operation | Meaning |
|---|---|
| `inspect(demand, site, time)` | Read what can be derived from already known parameters; list missing requirements. **No mutation**. |
| `preview(demand, trial, seed, candidate_index)` | Draw an admissible candidate from declared priors, respecting evaluable world conditions; **no mutation**. |
| `commit(proposal)` | Revalidate a current proposal, then establish only the necessary missing parameters. Reject incompatible or stale proposals. |
| `add_condition(condition)` | Impose a world-level fact with an explicit tolerance; reject if it conflicts with already established parameters. |

`src/planetary_requirements.py` implements this small contract with its own
state and constraint checking, modeled on the earlier realization experiments.
It does **not yet** bind those commitments into `RealityLedger` or replace the
fully specified `PlanetarySystem`. Those are separate future integration tasks.

## Run the visual designer

From the Universe repository root (standard library only):

```sh
python examples/planetary_designer.py --open
```

If the browser does not open automatically, visit the printed local URL.
The server listens only on `127.0.0.1` and restricts cross-origin writes.

1. **Inspect known facts** for daylight duration or approximate time until
   sunset at the selected latitude and simulation day.
2. Move a slider or enter a value to **try** a parameter, or leave it unchecked
   so the designer samples it when necessary.
3. **Preview candidate**; the sky visualization and seasonal daylight curve
   update, but the world is unchanged. **Another candidate** explores a
   different admissible sample.
4. **Commit this candidate** to establish only the parameters necessary for
   that question. Already committed parameters cannot be changed by sliders.
5. **Export committed world** to save a versioned JSON description; restart
   later with `python examples/planetary_designer.py --load FILE --open`.

You can also impose a new solar-day or daylight-duration condition. Existing
commitments are validated; incompatible imposed conditions are rejected.

Run tests:

```sh
python -m unittest discover tests -p 'test_planetary_requirements.py'
bash run_tests.sh
```

## The reduced model and its limits

Parameters are deliberately few: mean solar day (hours), axial tilt (degrees),
season phase relative to northern winter solstice (degrees), local solar hour
angle (degrees, 0 = noon), and optionally an orbital year (days). A mean solar
day may instead be **derived**, with no extra commitment, from known prograde
sidereal rotation and orbital-year periods:

`1 / solar_day_hours = 1 / sidereal_rotation_hours - 1 / (24 * orbital_year_days)`.

At epoch `t=0`, approximate daylight requires a solar day, axial tilt, season
phase, and latitude. The sunset question additionally requires the local solar
hour angle. A query at a nonzero epoch also needs the orbital year to advance
seasonal phase. No individual intervening days are simulated. Longitude is
replaced by the **local hour angle** in this experiment; coupling to the
planetary body-fixed longitude and inertial frame is deferred.

The declination/daylight model assumes a *circular orbit*, *constant mean solar
motion*, *spherical body*, and *flat astronomical horizon*. It deliberately
ignores eccentricity, changing orbital velocity, atmosphere, terrain,
refraction, eclipses and solar angular diameter. A polar day or night yields
"no sunset in this idealized day," **not** an invented time until the next
seasonal sunset. The local-solar approximation is not a precision ephemeris.

These narrow parameters describe an **approximate astronomical surface
behavior**. They do not by themselves establish a physically complete orbital
system. A future implementation must reconcile them with the full Keplerian
model, and cannot silently override already committed astronomical facts.

### Conditional realization and preservation

`examples/planetary_design_conditions.json` establishes season phase and
current local hour angle; it also imposes a 30 ± 0.2 h solar day and
11.45 ± 0.45 h of winter daylight at latitude 40°N. It leaves solar-day length
and axial tilt unresolved. The designer can find compatible pairs from
explicit priors and commit only those two. It need not establish a sidereal
period, orbital year, stellar mass, planet mass, moons, or climate.

Future nonzero-time inquiries may require the orbital year. These can be
answered directly once the year is established, without stepping through all
previous simulation days.

A preview can fail when no candidate meets the constraints and declared prior
ranges within the bounded search budget. That means **no compatible proposal
was found**, not a mathematical proof that none exists. Committed facts remain
unchanged in either case. Constraints that still depend on unresolved
parameters are retained for future checks; this experiment does not prove the
joint feasibility of every collection of partially evaluated conditions.

The builder may impose a condition as objective world truth. An Agent's
**Observation** is a different source of evidence: its Perception can be
mistaken and must not silently become an imposed world condition. A future
model should support imperfectly known constraints from inhabitants.

## Next related work

- General dependency discovery and conditional realization across subsystems,
  with domain solvers rather than a single global randomizer.
- Couple local solar hour angle, longitude, frame transformations and the
  higher-fidelity `PlanetarySystem` ephemeris.
- Quantify uncertainty and feasibility of partially specified conditions,
  including search bounds and posterior distributions.
- Connect observationally inferred calendars and astronomy to Agent-relative
  knowledge. See [the two-moon inverse-design experiment](planetary-two-moon-observations.md).
