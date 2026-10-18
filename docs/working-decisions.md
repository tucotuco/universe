# Universe working decisions

This short record is maintained with the code; it should not require separate user upkeep.

## Current direction

- Complete a small Encounter-centered vertical slice before building a general Universe framework.
- Continuous 3D coordinates are authoritative. ISEA cells and local Encounter grids are derived overlays, not the physical space.
- An Encounter is initiated by awareness **and** a decision to act. Perception is directed and its result should retain its basis.
- Provisional Encounter environments may be generated independently of a planet's terrain. Their generated details should be retainable as constraints or evidence for eventual broader world generation; do not assume they are already consistent with an uninstantiated world.
- Terrain synthesis and consistency-preserving refinement are deferred, not discarded.
- Use skill definitions and existing Action/Event IDs. An Action's `required_skill` is a prerequisite, not proof that the skill was exercised.
- Being-instance skill-use records capture history and per-skill earned experience. The initial progression curve follows the Encounter draft's increasing cost by rank; its awards and future replacement with configurable policies remain explicit.
- Ordinary skills can be practiced from rank zero. Extraordinary skills need prior training. Non-progressive skills can be used and recorded, but not improved by progressive-rank practice.

## Implemented Action-to-practice bridge

- Actions may return `ActionResolution(outcome, skill_exercises)` to record actual skill exercise and resolver-assigned XP automatically when completed; legacy Action resolvers returning `None` yield no automatic experience. Rewards and result classifications are not inferred from prerequisites or success; policy-based awards remain deferred.

## Next work
- Later: define configurable award policies based on exercised capability, effort, and outcome, without imposing arbitrary values at this stage.
- Model richer Event and Agent-relative Experience histories, then decide how experience relates to abilities, weapon-category transfer, learning and temporary capability modifiers.
- Eventually add context-constrained entity generation, scalable statistical groups and resolution-on-demand detail.

## First concrete noncombat Action

- `RunAction` is an intentionally provisional motion-based activity: the Encounter
  applies movement; the Action measures straight-line displacement from its
  scheduling position and reports `success`, `partial`, or `no_movement`.
- Only nonzero displacement counts as exercised `run`. Experience is set per
  activity by its caller and attributed to that Action; no automatic award policy,
  gait model, or terrain model is implied.
- Distance traveled along a curving or returning route and verification of actual
  running gait remain deferred until movement histories / movement modes exist.

## Provisional observational skill

- Add `spot` as an **explicitly new**, ordinary progressive skill in the
  existing skill catalog; the original Encounter draft had spotting *checks*,
  not an independently progressive spotting skill. This choice is provisional.
- `SpotAction` uses a bounded modeled 3D geometric-path gate and an adjustable
  d20 check (current `spot` rank versus Encounter difficulty). It deliberately
  does not claim to model light, terrain, eyesight, or complete visibility.
- An unsuccessful attempt still exercises the capability; XP is an explicit
  scenario amount, not a general learning rule. The Action returns an
  observation **only on success**, and the Encounter commits directed awareness
  after skill-use validation. Thus progression can improve later performance.
- Explicit die rolls support deterministic tests/replay. Configurable check
  distributions and generalized sensory checks remain future work.

## Integrated Encounter demonstration

- `examples/integrated_encounter.py` is a deterministic four-second scenario
  exercising movement, opaque Entity geometry, geometric sightline checks,
  scheduled Actions, directed awareness, and two independent skill histories.
- All physical geometry is provisional Encounter input, not automatically
  generated terrain. It is suitable as future constraint input when world
  generation and terrain refinement are developed.
- Fixed rolls and deliberately illustrative XP awards validate causal order;
  they do not constitute realistic visual perception, Agent choice, physical
  running mechanics, or a general experience-award policy.
- Next priorities: richer Agent-relative Event/Experience history and actual
  capability-aware Agent decisions; terrain synthesis remains deferred.
