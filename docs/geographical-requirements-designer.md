# Demand-driven geographical realization: first experiment

**Status:** bounded prototype; not a geological or continental generator, full
watershed model, general inverse terrain solver, or integration with the
existing `RealityLedger` and icosahedral spatial index.

## Purpose

Test the same inspect / preview / commit distinction used by
`docs/planetary-requirements-designer.md` in a spatially continuous domain.
Geography differs from astronomy: local detail often cannot be calculated
uniquely from a few global parameters, but it can be **constrained** by
established relief, drainage connectivity, spatial boundaries, and known points.

## World, units and established conditions

The initial world has east/north coordinates in kilometers, elevations in
meters above sea level, and an 8 km by 4 km demonstrator region:

- A known river source at `(0, 0)` at 1400 m above sea level, and a known
  mouth `(8, 0)` at zero elevation on a straight regional coastline.
- A continuous fixed downhill river bed, with modest predefined lateral
  meandering; a continuous valley cross-section slopes up away from the river.
- The continental setting is *not* generated: these macro-scale facts are
  initial commitments, not findings of a coupled erosion model.
- An x/y tiling of 2 km square **refinement indexes**. Elevation remains a
  continuous function of x/y, not a set of discontinuous cell heights.

## Operations

| Operation | Meaning |
| --- | --- |
| `inspect(x, y)` | Report known exact elevation or an unresolved local detail with a coarse estimate; never commit anything. |
| `preview(tile, candidate_index, amplitude_m=None)` | Generate a candidate local relief field, optionally with a designer-selected amplitude; never commit anything. |
| `add_condition({x_km,y_km,target_m,tolerance_m})` | Add an objective point-elevation constraint if consistent with existing facts. |
| `commit(proposal)` | Validate current conditions and revision, then establish one tile's local relief permanently. |
| `state()` / `restore()` | Export a versioned, ordered condition-and-commit journal; replay and validate on restore. |

Local relief is a bounded smooth function that is **zero at the tile
boundaries, on the established river centerline, and at the coast**. This
ensures exact height continuity across refined/unrefined neighboring tiles
and preserves the original river elevations and connected outlet regardless
of realization order. It does not guarantee continuous derivatives, nor
physically plausible drainage everywhere away from the modeled channel.

A query at an uncommitted interior point returns the *coarse estimate*, not a
falsely precise realized height. A query at a fixed boundary or river
centerline can already be answered exactly. A query that requires interior
detail identifies only its containing unresolved tile. A world-level
condition at an unrefined point limits the amplitude of any admissible local
realization. Preview samples from the feasible interval or tests a manual
choice; an impossible condition or realization is rejected without mutation.

## Interactive designer

```sh
python examples/geographical_designer.py --open
```

Click the map to select an elevation query and its tile. Inspect committed
facts; preview local relief, try another seed or change the signed local
amplitude, and explicitly commit a selected candidate. The map distinguishes
uncommitted coarse estimates, uncommitted preview relief, and permanently
committed tiles. You can impose a point-elevation condition, examine a
fixed river profile, and export the resulting world as JSON. Restore it with:

```sh
python examples/geographical_designer.py --load universe-geographical-world.json --open
```

The web server uses only the standard library and binds to loopback. The
preview and commitment path uses the same Python model as unit tests, rather
than a JavaScript-only terrain mock-up.

## What this demonstrates

1. Inquiries into a world with only macroscopic geographic commitments can
   explicitly report missing local facts rather than inventing exact answers.
2. Local relief may be sampled and inspected without changing established
   objective reality.
3. Refinement in separate tiles commutes with respect to established local
   elevations and preserves all shared boundary heights and the riverbed.
4. Contradictory proposed details or world-imposed point elevations are
   rejected without changing established state.
5. A subsequent reload retains the chosen facts and the order in which they
   became committed.

## Deferred work and limitations

- **Cross-scale refinements:** a single tile has at most one realized relief
  level. Hierarchical sub-tile realization, along with guaranteed projections
  of *all* committed coarse quantities, requires additional work.
- **Physically generated hydrology:** the already committed channel is
  geometrically connected and downhill, but arbitrary terrain slopes,
  watersheds, tributaries, floodplains and drainage capture are not solved.
- **General geographic constraints:** coastline shapes, mountain divides,
  conservation laws, sediment transport, glaciation and changes through time.
- **World integration:** reproject regional coordinates into the existing
  global continuous 3D coordinates and icosahedral spatial index; coordinate
  elevation, horizon profiles and downstream effects with planetary daylight,
  climate, ecology, travel, settlements and Encounters.
- **Demand-driven choices:** a full requirements engine should choose the
  minimum valid representation and precision appropriate for the requested
  question, rather than the fixed 2 km refinement unit used here.
- **Observation versus objective fact:** a map lookup here is a designer
  inquiry; it does not automatically establish a Being's perception or belief.
- **Versioned scientific assumptions:** candidate refinement uses a smooth
  demonstrator function, not tested geomorphological processes, and is not a
  guarantee that the generated landscape would arise naturally.

The important common architectural pattern is **a demand identifies missing
requirements; a trial elaboration respects existing facts; and only an
explicitly accepted elaboration becomes objective reality**.
