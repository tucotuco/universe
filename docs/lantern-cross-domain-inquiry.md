# A lantern on the hillside: cross-domain demand-driven inquiry

**Status:** bounded integration experiment. This is **not** a complete optical,
lighting, atmospheric, geomorphological, or cognitive model. It deliberately
makes its approximations and the boundary between objective truth and evidence
visible. See [the inhabited-world experiment](inhabited-world-first-scene.md).

## Start the interactive scene

From the Universe repository root (Python standard library only):

```sh
python examples/inhabited_scene.py --open
```

The map shows a yellow lantern southeast of the traveler and a dashed sampled
sightline. The dashed line is yellow when terrain is unresolved, green when the
sampled geometric test is clear, and red when a sampled obstacle is proven.
The *Lantern visibility* panel separates sampled geometry, illumination,
missing geographical dependencies, and the traveler's evidence. Press **Look
for lantern**. A typical first attempt realizes exactly `terrain_tile:2,0`;
it does not instantiate caravan individuals or calculate the weather, orbit,
or complete terrain. Examine the *World history* and *Traveler* panels.

To compare two **different possible worlds**, stop the server and start a
new one with the *world-builder's* terrain candidate selection:

```sh
# Candidate 2, the default: sampled ray clears the terrain.
python examples/inhabited_scene.py --terrain-candidate 2 --open

# Candidate 11: a different permitted relief, blocking the sampled ray.
python examples/inhabited_scene.py --terrain-candidate 11 --open

# Light is off: the photo-detection condition can be settled without any
# terrain realization, even though the geometric ray remains unresolved.
python examples/inhabited_scene.py --lantern-unlit --open
```

These options **establish the scenario before a character acts**. They are
not choices the traveler makes to control reality. Restarting creates an
independent world rather than silently rewriting past commitments. Export
using *Export world history* and reload the JSON with:

```sh
python examples/inhabited_scene.py --load universe-inhabited-scene.json --open
```

Scene save version 2 records the world-builder configuration alongside the
action journal; old version-1 scene exports are accepted through verified
replay of their previous state projection. The file intentionally does not
serialize live Python objects.

## The actual dependency contract

1. The objective lamp is fixed to geographic coordinates `(5.8, -1.8)` km,
   has a 1.5 m mast and specified luminous intensity (7,000 candela), and is
   initially lit. It is anchored to ground whose exact height is not yet fixed.
   The traveler's eye is 1.7 m above the terrain at their current position.
2. `GeographicalDesign.elevation_bounds(x, y)` exposes the range of currently
   admissible heights, respecting committed relief and any terrain conditions.
   Calling it neither samples nor commits relief. Fixed tile boundaries have
   a single admissible elevation even before interior detail is established.
3. `LanternInquiry.assess(observer_km)` samples a straight eye-to-lamp ray at
   at most 25 m horizontal intervals. It interpolates endpoint height bounds
   and compares ray and terrain intervals at each interior sample. One
   **certainly blocking** sample is enough to prove obstruction at that point.
   A ray that clears all sampled bounds is marked `clear` **only within this
   discretized model**, not as a mathematical certificate for the continuous
   surface between samples. Otherwise geometry is `unresolved` and missing
   terrain tiles are identified. The assessment is read-only.
4. If a lit lamp is too weak under the model's fixed dusk threshold, it is not
   a detection candidate; resolving terrain would answer no additional part
   of the detection question. The inverse-square point-source illuminance
   model and exponential attenuation are explicitly provisional, not a
   physically calibrated model of atmospheric optical depth, background
   brightness, lamp orientation or the human visual system.
5. **Look for lantern** resolves missing tiles one by one (bounded by the
   eight available), re-assessing after each commitment, and stops as soon as
   the question is settled or the model cannot decide it. Preexisting
   commitments are retained. It never calls the group's `counts()` method.
6. Even if the physical proxy declares the lamp a detection candidate, the
   traveler receives a **fallible** direct sensory report, with a bounded
   probability of misses or false alarms. The resulting tentative belief and
   evidence identifiers are displayed separately from objective conditions.
   An apparent glow does not prove the lamp was seen; a missing glow does not
   prove the lamp was invisible.

The geometric result must be understood as `clear`, `blocked` or `unresolved`
**under a finite sampling scheme**. The UI and exported state include the
sampling step and caveats. Real curvature, terrain between samples, buildings,
foliage, stars/moons, atmospheric scattering, changing brightness, dark
adaptation, and rays refracted near the horizon are not represented.

## Why this is a more demanding integration test

The inquiry begins with a person and their question. To answer it, Universe
must discover dependencies on a fixed lamp, an observer position, objective
geography, environmental lighting assumptions, perceptual ability and
Agent-relative knowledge. It requests only the missing geographical detail
needed for the sampled light-path decision. Different legitimate terrain
realizations can give different outcomes without rewriting what was already
committed in either independent world.

This does not yet prove a *generalized* dependency planner: `LanternInquiry`
is a domain-specific coordinator. It demonstrates a candidate contract to
consider only after more cross-domain inquiries have exercised it. More
rigorous continuous line-of-sight bounds and richer lighting/perception models
would be worthwhile if those become demanded by other world interactions.

## Verification

```sh
python -m unittest discover tests -p 'test_lantern_inquiry.py' -v
python -m unittest discover tests -p 'test_inhabited_scene.py' -v
```

Regression checks include purity of inspection, tightened elevation bounds,
clear and occluded alternative worlds, non-realization when the lamp is off,
selective terrain commitment, fallible evidence separated from visibility,
replay/tamper rejection, and HTTP read-only and cross-origin checks.
