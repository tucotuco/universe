# Demand-driven drainage-network topology — bounded experiment

**Status:** operational regional prototype. The authoritative outputs are
connected river courses, directed junctions, and monotonically descending bed
elevations. This is **not** a full watershed, erosion or terrain-flow solver.

## Why this is a separate experiment

The preceding [geographical requirements experiment](geographical-requirements-designer.md)
starts with a fixed river course and conditionally refines nearby relief. This
experiment instead begins with **an unresolved river course**, a known mountain
source *region*, a riverside village and an outlet into an eastern bay. It tests
whether the **topology** of the drainage network can itself be realized in
stages without invalidating what was already committed.

It uses a separate world, not an extension of the previously committed fixed
river geometry. Neither experiment silently revises the other.

## Known facts and coordinates

- Continuous regional east/north frame, x in `[0, 8]` km, y in `[-2, 2]`
  km, with elevations in metres above sea level.
- The main river originates within a western mountain source *region*
  (not at a prechosen precise y coordinate), at approximately 1400 m.
- The main river **passes through** the known village at `(4, 0)` km,
  with an established river-bed elevation of 500 m.
- It reaches the eastern bay at `(8, -0.6)` km at sea level.
- Further main-river crossings may be imposed as locations plus tolerances,
  without generating the connecting channel.
- The existence and properties of two *potential* tributary branches are a
  bounded scenario choice. Their exact sources, course shapes, and confluence
  locations remain uncommitted until requested.

The prototype uses 0.5 km x-stations for its *graph vertices*. These stations
are a resolution limit of this experiment, not fundamental physical grid cells;
river courses between vertices are continuous piecewise-linear curves. It only
generates east-flowing paths: no general search over arbitrary drainage
orientation or complex topology is yet attempted.

## Inquiry and realization

| Operation | Result |
| --- | --- |
| `inspect('river_to_bay')` | Known answer, or a dependency on unresolved `main`; does not sample reality. |
| `inspect('north_tributary')` | Identifies missing main stem and/or northern tributary. |
| `inspect('whole_network')` | Reports all outstanding channel dependencies. |
| `add_condition({...})` | Commits a local main-stem crossing, rejecting incompatible anchors, other crossings, or geometrically unreachable positions. |
| `preview('main', candidate_index)` | Proposes a mountain-to-village-to-bay course; no commitment. |
| `commit(proposal)` | Atomically validates and establishes the selected course. |
| `preview('north' / 'south')` | After the main course is fixed, proposes one lateral tributary and a precise junction. |
| `network()` | Returns established channels, plus a directed, shared-node topology; can optionally show a proposed addition. |
| `dumps()` / `loads()` | Serializes the ordered constraint/commit journal, replays it, and rejects incompatible saved state. |

There is **no requirement** to realize an entire drainage network when an
inquiry asks only for the main river. The two tributaries can be requested
and committed in either order. Their keyed deterministic proposals depend
on the committed main stem, rather than on how many independent branches have
already been explored. A stale proposal is rejected rather than adapted
silently after a constraint or commitment changes.

### Network invariants and physical limits

- Directed edges are ordered toward the bay, strictly increasing in east
  coordinate and strictly decreasing in bed elevation. These restrictions
  ensure there are no cycles and no uphill reaches in *this bounded domain*.
- Every realized tributary ends at an **identical existing main-stem node**.
  The explicit graph's outlet can be reached from every realized source.
- Existing main-river vertices do not change as tributaries become known.
- A committed course cannot be resampled or displaced by newly proposed
  crossings. Inconsistent attempts are rejected before mutation.
- The bed-height interpolation is an imposed simple longitudinal rule, not
  a hydraulic estimate of actual river gradients, sediment transport,
  groundwater, annual discharge, flood behavior, or geomorphic history.
- The colored background of the designer is **schematic relief** and is not
  committed terrain elevation. A plausible directed network is not proof of
  a corresponding physically valid whole-surface drainage field.

## Interactive designer

```sh
python examples/watershed_designer.py --open
```

Use **Inspect** to discover missing prerequisites, choose **Main stem** and
**Preview** for alternative courses, and **Commit** one if acceptable. You can
first click the map to establish a crossing observation on the main river.
After the trunk is committed, preview either tributary. Committed courses are
blue; the selected uncommitted preview is gold. The channel elevation panel
shows bed elevations. Export the complete commitment journal as JSON and
reopen with:

```sh
python examples/watershed_designer.py --load universe-watershed-world.json --open
```

The browser communicates with the same Python model exercised by the unit
tests. It binds a local HTTP server to 127.0.0.1 and uses only the Python
standard library. The browser UI has not been validated with automated
Chromium rendering in the development environment.

## Future integrations / deferred ideas

- Connect this topology model with continuous elevation fields and the
  icosahedral spatial index. Ensure slopes and divides actually direct
  water into the committed channels everywhere, including tile boundaries.
- Add branching and merging in arbitrary directions, multiple catchments,
  distributary systems, inland drainage basins, lakes and dynamic channels.
- Permit demand-driven **number and existence** of tributaries; the present
  two-branch choice is scenario scaffolding, not an emergent ecological fact.
- Preserve established river position and altitude while realizing new
  tributary connections, finer geometry, basin area, flow, local horizon,
  surface traversability, erosion, and geological history.
- Add actual hydrologic routing, runoff, conservation and seasonal flooding,
  then couple climate, vegetation and settlement with the resulting terrain.
- Resolve and commit local geographic facts from a Being's Observation and
  generate imperfect Perceptions without equating either with omniscient
  geographical knowledge.
- Share a generalized requirements/constraints evaluator with planetary
  and personal-history systems when the necessary cross-domain contracts
  are demonstrated, rather than introducing one prematurely.
