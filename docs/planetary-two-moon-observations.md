# Deferred experiment: two moons inferred from inhabitants' observations

**Status: pinned for subsequent development; not implemented.**

## The proposed discovery problem

Start with a world that has **two distinct moons**, but do not specify their
complete orbital states. Instead, begin with constraints stated from within
the world: inhabitants have observed that the moons have different apparent
angular sizes and that their apparent cycles repeat at different periods.
Those facts (or their reports) should help determine which physically possible
moon systems remain admissible.

We should be able to explore at least two directions:

1. **World-imposed conditions:** The builder establishes, as objective facts,
   specified apparent sizes and periods at a stated observational epoch and
   reference location. Realize an orbital configuration consistent with them.
2. **Observer evidence:** Inhabitants claim or estimate those quantities from
   repeated observations, with uncertainty and possibly systematic mistakes.
   Keep Observations, Perceptions, Beliefs, and objective orbital reality
   distinct. Observers can refine their models over generations.

## Important underdetermination

- A period may mean a **sidereal orbital period**, synodic phase cycle,
  rise-to-rise interval, or recurrence relative to another moon or star. The
  interpretation and observational reference frame matter.
- Apparent angular diameter constrains approximately the ratio of physical
  diameter to distance, not either quantity alone. It varies over noncircular
  orbits and with the observer's location.
- Orbital periods constrain a combination of gravitational mass and orbital
  size (Kepler's third law under the two-body approximation), not a unique
  mass-and-distance assignment.
- Inclination, eccentricity, mutual interactions, orbital resonances, nodal
  precession, eclipses and visibility can produce additional measurable
  constraints if/when an inquiry requires them.
- Long-term stability of a two-satellite configuration may require physical
  checks absent from the first-light independent Kepler models; do not claim
  stability merely because individual orbits fit observations.

## Suggested first executable acceptance test

Define a planet with known mass and rotation, but incompletely specified moons.
Impose *two observed lunar phase-cycle periods* and *two apparent angular
sizes* with tolerances. Preview several distinct physically admissible
configurations **without committing**. Select and commit one, then query moon
positions and phases at remote past/future times. Revisit the original four
conditions and test consistency. A second pass should treat the same numbers
as **fallible in-world observations**, rather than objective imposed truth.

This should become a useful stress test for demand-driven parameter inference,
perception versus reality, historical consistency, and computational cost of
long-time orbital integration under perturbations.
