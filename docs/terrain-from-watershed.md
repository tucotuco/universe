# Constructing terrain from committed drainage

**Status:** operational *bounded regional experiment*, not a general terrain,
hydraulic or geomorphological model. The central result is a continuous surface
whose downhill directions lead to an already committed directed channel network.

## Motivation and authoritative reality

This experiment connects the previous [river network](watershed-topology-realization.md)
with the earlier [continuous terrain refinement](geographical-requirements-designer.md).
It reverses the usual direction of derivation: river locations, bed heights and
confluences are established *first*; an admissible surrounding terrain is then
conditionally realized without changing any of that geography.

The source is a complete exported `WatershedDesign` state, including its ordered
journal. The terrain design copies and freezes the network on construction. It
requires the main stem to exist but does not require both potential tributaries.
Its source state and provenance remain embedded in every saved terrain world.
If the underlying watershed is subsequently changed through an external
reference, the terrain design rejects further use rather than silently rewriting
already established elevations. Adding tributaries after terrain realization
will need an explicit compatibility workflow in later development.

Coordinates are planar east/north **kilometres** in the bounded region
`x = 0..8`, `y = -2..2`. Elevations are **metres**. The 2 × 2 km tiles
organize resolution requests, not the fundamental geometry. There is no claim
of global Earth curvature, connection to the icosahedral spatial index,
subsurface geology or erosion history.

## Constructive drainage-consistent surface

Each river segment has linearly interpolated, already committed bed height
`z(s)`. For a surface query `p`, consider the closest horizontal point `q`
on every channel segment, and evaluate

`H_segment(p) = z(q) + K(p) × distance(p, q)`.

The terrain height is the **minimum** of those continuous segment potentials.
`K(p)` begins at 1,500 metres per kilometre and may vary slightly under a
committed *tile-local* relief multiplier. The multiplier is smooth and vanishes
at tile edges (`sin²(πu) sin²(πv)` in normalized tile coordinates). Its
coefficient is bounded to 0..0.08. Every tile can be independently previewed,
constrained and committed; the precise height field is continuous everywhere.

For the bounded test network, the imposed slope exceeds the differences between
bed heights divided by horizontal separation. This yields **exact channel-bed
heights** at every channel point, including tributary junctions. Off-channel,
following the active segment potential toward its closest channel point gives
a downhill direction. Repeating that operation reaches a channel; its
established directed edges continue descending to the bay. The application
provides a constructive downhill witness and tests a set of such routes.

This is **not** a physical watershed derivation from rainfall, erosion, sediment,
river discharge, groundwater or conservation. No claim is made that generated
ridge heights or valley widths are realistic. The minimization construction
produces drainage-consistent local slopes; a subsequent hydrological model
could operate on the resulting terrain.

## Unresolved versus established

Initially, no 2 km relief tile is committed. There is a range of admissible
heights at most off-channel points, *not* an already established sampled map.
The viewer uses the minimum-allowed baseline to visualize uncommitted areas,
with a subdued overlay and explicit warning that their local relief is unresolved.

| Operation | Meaning |
| --- | --- |
| `inspect(x, y)` | If tile unresolved, report the attainable elevation interval; do not commit. |
| `add_condition({...})` | Impose a known elevation with tolerance, restricting the tile's allowable relief coefficients. |
| `preview(tile, index)` | Propose one admissible tile strength, without committing it. |
| `commit(proposal)` | Validate the proposal against the current revision, conditions and network before recording it. |
| `elevation(x, y)` | Evaluate the baseline or committed surface. For unresolved tiles the baseline is **not** authoritative objective elevation. |
| `downhill_witness(x, y)` | Trace a descending path to a channel and the established bay; label it provisional if any visited tiles are unresolved. |
| `dumps()` / `loads()` | Preserve the watershed snapshot and ordered terrain commitments; revalidate on restoration. |

Committing an interior tile's relief cannot change any other tile, a shared
tile boundary, any river bed, or a confluence. Different orders of committing
disjoint tile proposals with equal per-tile candidate indices yield the same
resulting surface. A conflicting elevation constraint, a tampered proposal,
or a stale preview is rejected before mutation. Exact observational elevations
that cannot be achieved by this *limited relief family* are rejected; the
prototype does not invent an arbitrary new terrain model to satisfy them.

## Designer

Start with an illustrative main river and two committed tributaries:

```sh
python examples/terrain_from_watershed.py --open
```

Or consume the **actual saved river network** from the previous designer:

```sh
python examples/terrain_from_watershed.py \
  --watershed universe-watershed-world.json --open
```

Click the map to inspect an unresolved location. Select a tile, preview an
alternative and commit it. A known elevation and tolerance can be imposed at
a map location. **Trace downhill to bay** displays a constructive descent;
provisional traversals are labeled as such. The browser never commits merely
because the map was displayed. Export and reload the committed terrain with:

```sh
python examples/terrain_from_watershed.py \
  --load universe-drainage-terrain-world.json --open
```

The designer uses only the Python standard library and a localhost HTTP
server. Unit tests cover model invariants, journal replay, and the HTTP API;
visual rendering requires assessment in a local browser.

## Next questions / deferred work

- Establish an efficient **compatibility test for new tributaries** against
  existing terrain commitments, instead of always freezing topology first.
- Permit richer multi-resolution relief fields, rivers with arbitrary orientation,
  multiple outlets, lakes, changing sea levels, soil and rock constraints.
- Hydrologically derive catchments, runoff, channel discharge, flooding and
  erosional/depositional processes; preserve conservation across resolutions.
- Derive local horizons for the planetary Sun and Moon model, including
  temporally evolving shorelines and landscapes.
- Reconcile local continuous coordinates with Universe's global spatial kernel,
  and allow geographical observation through fallible Agent perception.
- Generalize the constraints contract only after more than one physical
  subsystem demonstrates a common need.
