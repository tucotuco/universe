# Universe: an inhabited world at dusk

**Status:** bounded integration experiment, not an inhabited-world simulator or
production game. This is a deliberate pivot away from increasingly detailed
single-domain experiments. The goal is to make several existing Universe
subsystems cooperate during one person-centered inquiry.

## Run it

From the repository root, with Python (standard library only):

```sh
python examples/inhabited_scene.py --open
```

The server prints its `http://127.0.0.1:<port>/` address. The browser should
open automatically. Press Ctrl-C to stop. The map displays **provisional
baseline heights** in unresolved terrain tiles; these are not established
objective terrain. Click a point near the traveler (within 300 m of the
character) and choose **Survey local ground** to realize the one required tile.

A useful sequence is:

1. Inspect the world panel before taking an action: the caravan exists, but
   neither its total composition nor any individuals have been realized.
2. **Scan surroundings**. The traveler becomes aware of the caravan and
   companion using a range-only proxy, but learns no exact counts.
3. **Ask companion**. The companion makes its own sampled observation through
   an Encounter Action, and communicates its fallible report to the traveler.
4. **Observe caravan**. The traveler's own Encounter Action may succeed or
   fail. On success the statistical group realizes aggregate numbers, *not*
   individual Beings; the sensor samples noisy evidence and the observer's
   BeliefLedger forms estimates. Compare the objective panel to the belief panel.
5. **Approach caravan**. Advance the encounter and move 180 m. Observe again.
   Earlier evidence remains in the history even when estimates change.
6. **Consider the sky**. Dusk is an established environmental condition, but
   an exact sunset time is correctly reported as undetermined. No planetary
   parameters are silently invented.

Export the world history using the upper-right button; reload a previously
exported `universe-inhabited-scene.json` with:

```sh
python examples/inhabited_scene.py --load universe-inhabited-scene.json --open
```

A save contains a *replayable command journal* and a normalized expected state.
The loader replays actions from the original conditions using the existing
subsystems and rejects contradictory or tampered histories. This is intentionally
not generic serialization of all `Universe`, `Being` or `Encounter` objects.

## Actual integration (and what remains separate)

| Concern | Authoritative owner | What the interface exposes |
| --- | --- | --- |
| Local relief | `GeographicalDesign` | Unresolved/committed tiles and numeric objective elevation after a geographically scoped survey |
| Aggregate nomadic group | `StatisticalGroup` | Lazily committed household/count state, *no* individual realized unless separately demanded |
| People, position, time, awareness | `Universe` + `Encounter` | Traveler/companion Beings, kinematic movement, directed awareness |
| Observation | `ObserveGroupAction` + its sampled observation/interpretation | Chance of failed observation, evidence from an explicit range-based proxy, spotting practice |
| Personal belief and testimony | `BeliefLedger` | Inferred counts, evidence provenance, communicated vs firsthand reports, disputed categories |
| Known environment | `RealityLedger` | The stipulated `dusk` daypart and village identity, distinct from an astronomical ephemeris |
| Cross-domain history | `InhabitedScene` coordinator | Query/action sequence and per-action newly realized facts without duplicating domain owners |

The coordinator does **not** insert generated group counts or terrain heights
into another reality store: each domain remains its own authority. The
`RealityLedger` currently represents only environmental conditions. A future
single world-wide provenance/reconciliation service must not become a competing
source of truth.

### Critical distinctions

* **Unresolved** is not zero, false, or empty. Before a successful group
  observation the group has a persistent identity and footprint, but no
  realized population totals. Its individual member count remains zero even
  after totals are realized.
* **Demand-driven realization** occurs when needed, not just when rendering a
  map or opening an information panel. `inspect` and map rendering are pure.
  A survey commits only a target tile; an observation success commits counts.
* **Perception is not fact transfer.** An instrument samples a statistical
  group, possibly incorrectly. The observer may fail; a companion's independent
  evidence is transmitted with its source. No person receives `group.counts()`
  directly as knowledge.
* **History retains disagreement.** Observations are not revised to match
  subsequently established aggregate values. Numeric belief summaries are
  heuristic, not calibrated uncertainty distributions.
* **Known dusk is not computed sunset.** The qualitative world fact does not
  establish star positions, local solar time, atmospheric color, or exact
  visibility. When asked for sunset, the system explains what is missing.

## Limitations and next work

The encounter's local 3D coordinates are explicitly registered to an x/y
regional map origin, but z heights are *not* coupled to GeographicalDesign;
kinematic movement is not terrain-constrained. Neither optical visibility nor
hearing, lighting, weather, line-of-sight through terrain, subjective narrative
generation, settlement sociology, detailed individual interactions, nor
physical sky dynamics are implemented. The map uses x/y registration and
coarse symbolic markers, not visibility modeling. The companion "talk" step
is an independently sampled report via an observation Action, **not** a
natural-language social conversation. Observations are intentionally scoped
to one statistical group, not arbitrary scene objects.

The strongest next questions are *cross-subsystem dependencies*: What is the
minimum physical detail needed to decide whether a person can see a lantern on
an opposite hillside? How should light, terrain, time, embodied position,
social knowledge and fallible observation interact without each module
silently establishing facts owned by another? The scene is intended as an
instrument for answering those questions, not a promise that the answers
are already implemented.

## Tests

```sh
python -m unittest discover tests -p 'test_inhabited_scene.py' -v
bash run_tests.sh
```

Browser rendering is intentionally a separate manual acceptance step.


## Next cross-domain experiment

The [hillside lantern inquiry](lantern-cross-domain-inquiry.md) extends this
scene with bounded geographical visibility, lighting and fallible observation.
