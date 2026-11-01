# Planetary systems: first light and gravitational forcing

**Status:** bounded, deterministic first experiment; not a full planetary simulation.

## Why this is a cross-scale foundation

A star, a rotating planet, and its moons supply physical boundary conditions for
local and cultural systems. This is a useful new test of Universe's
**resolution-on-demand** architecture, because queries for a particular place
and time should not require realizing an entire world in full detail.

| Planetary driver | Downstream uses (not yet implemented) |
|---|---|
| Planet spin and orbital period | Local diurnal cycles; solar days; sidereal calendars; biological rhythms |
| Axial tilt, orbital shape and latitude | Insolation, daylight duration, seasons, seasonal ecology, climate |
| Moon orbits and illumination geometry | Lunar phases, nocturnal light, animal behavior, observational calendars |
| Stellar/lunar gravitational forcing | Tide-generating potential; later tides, coastal navigation and habitats |
| Eclipses, orbital precession and secular changes | Long-term cultural and ecological events; future refinement |

The planet determines *physical opportunities and constraints*, not the cultural
response. Calendars, customs, rituals, myths and biological adaptations must be
modeled or realized separately through appropriate histories and observations.

## First implementation

- `src/planetary_system.py`: **pure, read-only** Keplerian ephemeris for one
  star, one rotating spherical planet, and zero or more moons; SI units.
- `examples/planetary_analogue.json`: fully declared Earth-like demonstration
  parameters, with `t=0` near northern winter solstice (not an authoritative
  mapping to any Earth civil date).
- `examples/planetary_first_light.py`: query eight points in a planetary year
  for surface latitude and longitude.
- `tests/test_planetary_system.py`: orbit geometry, latitude-dependent
  illumination, seasons, polar day/night, lunar phases, tide forcing,
  reproducibility and invalid-model rejection.

Run from the repository root:

```sh
python examples/planetary_first_light.py
python examples/planetary_first_light.py --latitude -40 --longitude 90
python -m unittest discover tests -p 'test_planetary_system.py'
```

**Frame:** origin at the primary star, inertial +z normal to the reference
orbital plane, lengths in meters, epochs in elapsed seconds. Orbits have
inclination, node and periapsis orientation. Planet locations are relative to
the star; moon locations are relative to the planet. A site's latitude and
longitude are **body-fixed**; the spin-axis direction and planet rotation
transform its surface normal into the inertial frame. The current continuous
3D spatial kernel and local Encounter frames are not yet wired to these
frames; any future coupling must be an explicit coordinate transformation.

**Queries:** `PlanetarySystem.state_at(time_s, latitude_deg, longitude_deg)`
derives local solar altitude, stellar flux and incident illumination, solar
declination, approximate daylight duration, a mean solar day length, moon
altitudes and illuminated fractions, and quadrupole tide-generating potentials.
The query returns a frozen value object and does not modify time, draw random
numbers, commit facts, or make information available to an Agent.

**Compatibility:** the supplied orbital periods must match Newtonian two-body
periods from the masses and semimajor axes to within 2%, admitting small
mean-element departures; this is not full gravitational integration. Per-body
masses, radius, and luminosity are specified, not inferred statistically.

## Scientific boundaries

1. **Daylight hours** assume solar declination changes negligibly during a
   solar day, and the solar day is derived from mean orbital motion. They are
   not exact sunrise/sunset times. Atmospheric refraction, terrain blocking,
   twilight, eclipses and solar angular radius are not yet included.
2. **Tidal potential** is the quadrupole gravitational forcing at a spherical
   site (in m²/s²); it is **not** ocean height or a prediction of tides.
   Seabed geometry, hydrodynamics, continental boundaries, rotation, resonance,
   and time-lag effects will determine realized water level later.
3. **Orbits** follow fixed, independent two-body ellipses. This excludes
   mutual perturbations, barycentric corrections, secular evolution, axial
   precession, resonances, orbital locking, orbital decay, and multi-star
   configurations. Our example is an *analogue*, not a precision Solar System
   ephemeris.
4. Planetary terrain, atmosphere, climate, and local weather do not exist yet.
   Insolation is an incoming **forcing**, not temperature or weather.

## Resolution-on-demand implications

The configuration is a **committed coarse physical model**. Given that model,
quantities such as solar altitude at a specified time and location are fully
determined calculations; retrieving them should not be confused with a
stochastic collapse or an Agent's perception. Future planetary features may
be unresolved—for example, atmospheric opacity, exact shoreline shape,
impact events, or moons' long-term interactions—and can be conditionally
realized only when queried or encountered. Their commitments must respect
established solar cycles, orbital samples, climate histories and downstream
Events where applicable.

In particular, an upgrade from this analytic model to N-body integration must
not silently reinterpret **committed** earlier positions or calendar facts.
The model version, approximation bounds, and any facts asserted as exact
objective reality will need careful separation. It may be appropriate to
store coarse model state with a declared tolerance instead of pretending the
first Kepler approximation is a fully resolved immutable trajectory.

## Next suggested experiments

1. Tie planetary frame/time queries to a point on the spatial grid, then
   render an **interactive local sky, horizon and daylight cycle**. This is a
   useful concrete Observation vs Perception experiment.
2. Support multiple planetary bodies orbiting the star without conflating
   orbital ephemeris with local climate or terrain.
3. Derive planetary gravity and a physically consistent hydrostatic/geoid
   reference surface; start a low-resolution radiation/temperature budget.
4. Model lunar eclipse/shadow/illumination as physical geometry, not as
   a cultural or observational fact.
5. Add a candidate climate/ecology driver and test whether later refinement
   preserves established seasonal conditions, migrations and Event histories.
