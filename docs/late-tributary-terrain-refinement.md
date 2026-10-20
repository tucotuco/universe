# Adding tributaries after terrain has been established

**Status:** bounded operational experiment. One or more surface-flow tributaries can be
committed after some (but not all) terrain tiles have been realized. They use
existing geometry rather than eroding channels through it. The purpose is to
test consistency between *topological* and *geometrical* refinement.

## The demand

A partly realized landscape already has a fixed main river and two tributaries.
Some terrain tiles contain committed elevation fields; other tiles still have
ranges of admissible elevations. A later exploration asks whether a previously
unrepresented stream can descend from a selected source to the known network.

A new stream must not move an existing river, revise a committed elevation, or
silently assume that provisional terrain elevations will stay fixed.

The new `LateTributaryDesign` takes a **snapshot** of an exported
`DrainageTerrainDesign`, whose watershed is itself an immutable, authoritative
input. It does *not* rewrite the original `WatershedDesign` journal. The new
tributaries belong to a separately versioned **extension layer**, with a graph that
shares an actual confluence node with the old directed watershed. This is a
concrete compositional approach to an existing problem: the old terrain
constructor uses a lower envelope of river potentials; inserting a new channel
into that constructor directly could lower or otherwise change already
committed terrain, which would be unacceptable.

## Requirements and proposal

`preview(x_km, y_km, candidate_index)`:

1. Finds a nearest established channel in the actual terrain surface.
2. Determines the intersected 2 km tiles along the source-to-channel trace.
3. Creates a **scratch terrain world**, realizing *only those intersected tiles*
   which were unresolved, using the existing deterministic tile generator and
   its imposed elevation conditions.
4. Repeats the tile-coverage check if the newly realized relief changes the
   confluence or route.
5. Accepts a proposal only if the source lies above its confluence, the path
   is monotonically downhill, and its route no longer depends on an unresolved
   tile. The existing river-bed geometry is retained exactly.

A candidate *does not mutate objective reality*. Other candidate indices may
produce different relief and sometimes a different channel approach. `commit`
recomputes and checks the proposal before atomically replacing the terrain
snapshot and adding the new branch. If any condition fails, no changes are made.

This resolves an important ordering issue: a tributary can be discovered after
terrain is committed, **but its bed cannot depend on elevations that may
subsequently be realized differently**. Here, the minimal current commitment
unit is an entire touched tile; a future refinement engine should be able to
commit only a narrow channel corridor while preserving admissible alternatives
outside it.

## Topology and geometry

The original channel geometry is unchanged. The extended graph splits an original
channel edge at each new confluence, if necessary. Each new branch points toward
its shared node; the established river graph still leads to the bay. No cycles are
introduced. The new branch's physical bed is the **existing height field
restricted to its source-to-confluence horizontal line**; the stored sequence
of surface samples serves as a visualization and graph approximation, not a
piecewise-linear redefinition of the exact continuous height field.

No physical incision or bank geometry is created, and a down-gradient flow path
is not proof of a perennial river. Watershed membership, source flow,
precipitation, channel discharge, and the stability of the channel over time
are deliberately outside this experiment.

The extension layer now supports **multiple independently joining late tributaries**
committed in discovery order. Each joins one of the original channels. Two or
more late tributaries may split the same original channel edge at different
confluences, in either order; the single-outlet directed graph is rebuilt and
checked before committing. New late channels that cross or pass within
10 metres of an earlier late channel are rejected. Joins between late branches, river-course incision,
and tributaries that change the already established original topology remain
outside the experiment.

Each accepted tributary is a separately validated extension, not an instruction
to recompute old terrain. Its traversed unresolved tiles are committed
atomically using the current deterministic terrain configuration. A later
tributary can reuse those tiles but must never resample them. Saving records an
ordered journal and a list of late tributaries. Earlier version-1 exports
with one late tributary remain readable and are upgraded on export.

## Try it

```sh
python examples/late_tributary_designer.py --open
```

The default landscape starts with the main river and two tributaries committed,
but only two of eight terrain tiles realized. Click a source point (try `1,-1`
for a route that requires realizing another tile, or `3,-1` for a route wholly
in already committed terrain), then Preview, Another candidate, and Commit.
After committing, choose another source and repeat, e.g. use `1,-1` followed
by `3,-1` or reverse that order; both alternatives preserve the original
river network and produce the same terrain when candidate indices are fixed.
The map distinguishes existing rivers, proposed tributary, established tiles
and unresolved terrain. Export the resulting world from the UI and reload it:

```sh
python examples/late_tributary_designer.py \
  --load universe-late-tributary-world.json --open
```

Or begin with the actual world saved by the preceding terrain designer:

```sh
python examples/late_tributary_designer.py \
  --terrain universe-drainage-terrain-world.json --open
```

A candidate may legitimately be rejected when no acceptable downhill route
exists, when the source lies too close to a known channel, or if it depends on
conditions the bounded model cannot satisfy. Rejection does not mutate reality.
The version-2 save format contains the original terrain state, the resulting
state, all committed late branches, and an ordered commitment journal; loading replays the journal
and rejects tampered or incompatible data.

## Tests and next questions

Focused tests verify that: inspection/preview is noncommitting; previously
committed elevations and the original channel graph do not change; any touched
unresolved tiles are resolved atomically; the tributary's downhill path joins a
shared directed graph node; invalid and forged proposals are rejected; and
export/reload reproduces committed reality. The local HTTP API is also tested.

Remaining architectural questions include (1) a **corridor-level** rather than
tile-level resolution unit, (2) junctions and crossings **between** late
tributaries, (3) incompatibility diagnostics for late tributaries imposed at
fixed locations, (4) refining uncommitted river *topology* and terrain
simultaneously without a precommitted trunk, and (5) hydrology and
geomorphology when adding a stream
actually requires changing landforms. These are recorded as deferred work, not
as completed capabilities.
