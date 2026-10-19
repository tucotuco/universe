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

## Statistical group / field observation experiment (2026-10)

- `StatisticalGroup` is an *aggregate Entity*, not a fully populated list of
  `BeingInstance`s. It participates in an existing Encounter via the
  `ObjectInstance` interface; the general Agent/Entity hierarchy is not being
  redesigned in this experiment.
- Group and household counts are drawn reproducibly from configuration CDFs.
  Household composition is internally resolved to calculate group totals, but
  individual identities and positions remain undefined until requested.
  A selected member currently becomes a lightweight `GroupMember` record,
  **not yet** a full Being with generated skills or back-story.
- Global Cartesian position, bounded footprint, velocity, and acceleration
  are objective aggregate state. Motion uses a provisional constant-acceleration
  step; reachable future group-center regions are conservative acceleration
  bounds, not probability densities, navigation plans, or terrain constraints.
  Members currently retain their offsets from the moving group center.
- **Reality / Observation / Belief are distinct.** Observations may cause
  objective count resolution but cannot set counts. Observer bias may persist
  across sightings; belief holds original evidence with provenance, including
  errors. Communication shares evidence IDs (deduplicated), not objective fact.
  Contradictory reports remain available as targets for follow-up observation.
- The example's `FieldObserver` is a *range-gated instrument scaffold* using
  controlled count and position errors. It is **not** a visual-detection model.
  The current `Encounter.perceive(RangePerception)` registers awareness on
  proximity alone for this test. Terrain, occlusion, group footprint visibility,
  illumination, and Scouts' perception capabilities are not simulated here.
- Repeated position observations yield an illustrative estimated velocity and
  linear belief prediction, distinct from the objective future reachable region.
  Count summaries assume a closed group over the 100-second demonstration;
  confidence weighting is **not** a validated Bayesian posterior, nor does it
  correct for correlated sensor biases. Future work must consider population
  turnover, uncertainty propagation, misidentification of groups, fabricated
  reports, and evidence dependencies.
- No general history/serialization of aggregate realization is implemented yet.
  Stable seed + CDF configuration reproduces composition and member offsets;
  restoring evolved state from a saved snapshot, and cross-scale consistent
  motion/history refinement, remain future work.

## Observer skill and interpretation: father / son experiment (2026-10)

- Group CDF/household machinery is reusable within the nomadic-group schema,
  **not yet** a fully generic recursive group composition engine.
- Raw observational evidence and observer-specific *interpretation* must be
  distinct; a Being's `spot` rank affects interpretation of ambiguous cues,
  never changes underlying group composition or rewrites original evidence.
- The provisional policy discounts dubious category candidates in proportion
  to Spotting rank, reaching full discount at a configurable expert threshold.
  Cue reliability is unknown: higher rank does not guarantee correct beliefs.
- Interpretations record the skill and rank used at the time, permitting
  historical reconstruction even after the Being gains further experience.
- Communicated evidence retains source identity and original interpretation;
  recipients do not silently re-run it using their own current skill.
  Broader models for teaching, trust, testimony, and skill acquisition follow.
- Reinterpretation of earlier observations after learning or from new
  communicated context is desirable, but is not implemented by this initial
  one-interpretation-per-sighting demonstration.
- Parent–child relationship is scenario metadata only for now; this does not
  introduce a general kinship graph or infer skills from family relationships.
- Initial skill ranks and positions are scenario configuration, not yet sampled
  from Being-generation distributions; field observations do not award XP.

## Action-mediated statistical-group observation (2026-10)

- The earlier `FieldObserver.observe()` experiment remains a **controlled-error**
  reference, not a realistic simulation. New `ObserveGroupAction` uses the
  existing Encounter schedule/resolve timeline, `spot` capability, experience
  history, and directed awareness, rather than bypassing Action resolution.
- The model tests observation feasibility (here only modeled distance) before
  rolling. Impossible/out-of-range attempts create neither fabricated evidence
  nor skill practice. Feasible failed checks *can* earn experience, and both
  success and failure awards are configurable; a later policy may consider
  difficulty, novelty, degree of success, and skill-specific learning rates.
- `SampledGroupObservation` converts *objective aggregate counts* into noisy
  evidence via seeded stochastic errors. Skill rank improves expected sensor
  precision. `FieldInterpreter` sees only that imperfect evidence and uses
  current skill to judge dubious classifications. Skilled conclusions are not
  guaranteed correct. These are **proxy sensing models**, not geometric LOS,
  physical optics, illumination, terrain, or actual individual detection.
- Successful completed Actions attach raw evidence and historical interpretation
  to the Action event and to the observing Being's BeliefLedger. The Encounter
  commits ordinary directed awareness and records skill-use XP. Failed checks
  produce skill-use history but no observed group composition. Evidence may
  commit group totals, while leaving all individual Beings unrealized.
- Reproducible sampling uses a scenario-controlled seed and stable observer
  key, independently of generated Action UUIDs and shared random sequences.
  The seed is *experimental*, not yet a general counterfactual-consistent
  stochastic world/physics mechanism.
- Communication still shares source observations and interpretations with
  provenance; it does not copy authoritative state. Evidence combination and
  discrepancy detection remain provisional (not calibrated Bayesian belief).
- This increment adds a completion hook for Actions to publish their evidence
  only after Encounter accepts Action resolution. Full transactional handling
  of arbitrary third-party completion hooks, generalized event-sourced history,
  adaptive investigation policy, and teacher/student learning are deferred.

## Evolving beliefs and immutable evidence provenance (2026-10)

- Distinguish *objective group reality*, *Agent-relative source observations*,
  *source interpretations at the skill level of the original observer*, and
  *later evolving beliefs*. Reconsideration never edits historical evidence or
  its original interpretation.
- `BeliefLedger` now records append-only `BeliefRevision` snapshots as new
  evidence arrives, when it is communicated, or after a Being explicitly
  reinterprets **its own** prior observation at a later skill level. Revisions
  retain triggering observation ID, contributors, time when known, and
  unresolved report discrepancies. The ledger can export evidence, original
  interpretations, reassessments, and belief history as JSON-compatible data.
- Communication passes **sourced evidence and the source interpretation**;
  it does not overwrite a recipient's knowledge or make a report objectively
  true. It does not automatically train the recipient. Later reinterpretation
  belongs to the original observer and is not retroactively attributed to the
  observation's earlier time or skill.
- Current count estimates remain simple uncertainty-weighted aggregates, not
  Bayesian posterior inference or calibrated confidence. Repeated correlated
  evidence and potentially changing group composition have not yet been
  addressed; snapshots preserve conflicting reports instead of pretending
  uncertainty necessarily decreases. Fully resolved spatial occupancy of
  individual Beings will require instantiating those individuals; statistical
  distributions can represent a group's aggregate footprint/density without
  resolving members.
- The guided practice award in `group_belief_revision.py` is an **explicit
  test input** to the existing skill-progression mechanism, not yet a simulated
  father-to-son teaching Action. Skill advancement enables a fresh, fallible
  reading of older evidence, yielding a new belief while retaining the
  original Experience and interpretation.


## Evidence-driven observations (2026-10)

- Fixed random seeds in `group_observation_encounter.py` exist for repeatable
  tests and comparisons. They do **not** make the sampling model nonrandom.
  Different configured seeds can produce different results; a seed is not a
  claim about physical reality or a substitute for uncertainty calibration.
- Before general decision-making, test a narrow and inspectable policy:
  conflict among recorded reports motivates a targeted inquiry; otherwise
  substantial *reported* relative uncertainty may motivate one. This heuristic
  reads only an Agent's BeliefLedger, never objective counts.
- Keep decision provenance (what discrepancy/evidence motivated an Action)
  distinct from original evidence, skill-dependent interpretations, and
  belief revisions. Planning an inquiry does not itself change a belief.
- A focused ObserveGroupAction reduces the **modeled noise** in the selected
  count category, without making it infallible. It still uses the existing
  Encounter timeline, feasibility/skill check, and experience recording.
  A failed follow-up can leave the discrepancy unresolved. There is no
  automatic repetition or general planner; that belongs to later work.
- Do not mistake interval nonoverlap or a relative half-width heuristic for
  Bayesian confidence. Correlated testimony, transmission reliability,
  unobserved group turnover, and observation costs are deferred.


## Statistical group -> Being realization (2026-10)

- A statistical group may commit composition counts and selected stable member
  identities without constructing every individual. `realize_being()` upgrades
  one adult human identity into a genuine `BeingInstance` registered with the
  Universe. It preserves the pre-existing identifier, initial placement,
  population totals, and repeated-reference identity. Existing Encounter
  Actions can then change that Being's skills and experience.
- For this initial bridge, `materialized_count` still counts lightweight member
  identities; `realized_being_count` distinguishes full Being instances.
- Group motion translates its realized members, preserving any prior relative
  position changes from Encounter actions. Group membership/detachment and
  reconciliation of aggregate footprints after independent movement are not
  implemented; the footprint is a provisional bound, not hard collision geometry.
- Children, livestock, and dogs require appropriate Being definitions and
  attribute-generation rules; mapping them to an adult Human would be false
  precision. These, aggregate updates from births/deaths/departures, proper
  lifecycle/serialization of the group's committed state, and higher-resolution
  historical back-stories remain deferred.

## Realized Being -> aggregate consequence projection (2026-10)

- The group's `counts()` describes its **committed baseline composition**, not a
  live count of healthy, present, or surviving individuals. A dead Being does
  not disappear from its historical cohort or retroactively change the CDF draw.
- `aggregate_state()` is a fresh, derived view of realized member status;
  unrealized members remain explicitly unresolved (not assumed alive or dead).
  Injured/incapacitated classifications overlap living status and are not
  additive population categories. Health status follows the legacy Being
  threshold of `hit_points <= -10` for death; these are game-system semantics,
  not a biological or general mortality model.
- `known_skill_state(skill)` exposes only realized members' current capability
  and recorded practice, **not** an inferred distribution for the entire group.
  Learning by an individual never updates the CDF of its uninstantiated peers.
- The demonstration uses a clearly labeled *scripted* health-change Action to
  show Encounter event -> individual state -> aggregate view. It is not a
  damage, combat, healing, or event-sourcing implementation. Event IDs persist
  in the Encounter; full state-transition histories and reconstruction do not.
- Deferred: arrivals/departures, birth/death changing active membership,
  moving bodies vs traveling group, group health distributions and uncertainty,
  historical population snapshots, causal state-change provenance and durable
  serialization/restore of the evolved group. Avoid silently treating baseline
  composition as current active membership before those policies exist.

## Fixed-quota conditional refinement experiment (2026-10)

- An optional `formation_traits.adults.<trait>.count` establishes a **fixed,
  formation-time quota** for one characteristic of the original adult cohort.
  A keyed, reproducible ranking assigns that trait to exactly that many member
  identities independently of the order in which Beings are realized.
  `initial_skills` may assign a starting level on becoming a Being; the original
  quota and assignments do not change if skills later improve or members die.
- `formation_trait_state()` reveals only the aggregate committed quota and
  its residual among unresolved members. It does not create their identities
  or presume their **current** skills. `known_skill_state()` continues to show
  only realized Beings' current capabilities. Such private generator state is
  **not** automatically known by observing Agents.
- **Model distinction:** this fixed quota is sampling without replacement.
  Realizing one qualified member reduces the number of qualifications remaining
  among unresolved members. Independent Bernoulli sampling at a fixed
  probability would **not** carry this conservation law. The same distinction
  eventually applies to correlated composition, household relationships, etc.
- This is an experiment in coherent original-cohort refinement, **not**
  general conditional inference. Cohort-specific quota counts, exactly assigned
  starting skill levels, a linear-size keyed ranking, and adult-human support
  are illustrative restrictions. Large-scale weighted assignments, correlated
  traits, proper time-stamped composition, births/deaths/membership transitions,
  skill acquisition histories predating realization, and inference over
  unresolved evolving members remain deferred.

## Correlated formation attributes experiment (2026-10)

- `formation_attributes.adults` allows a small declarative chain of CDF-based
  **formation-time** characteristics. Each characteristic can depend on at most
  one previously defined or recursively resolved characteristic, or an existing
  fixed-quota `formation_traits.adults` membership status. Missing conditional
  branches and cycles are rejected; other joint probability models remain deferred.
- Attributes are sampled with per-identity/per-attribute keyed randomness and
  committed only when requested (together with required parents), **without**
  creating a `GroupMember` or `BeingInstance`. Request order cannot change the
  sampled individual reality. Inspecting committed values samples nothing.
- The example (`age_band -> role -> years_in_role`) is illustrative, not a
  demographic or causal claim. It also conditions age on the group's prior
  exact `trained_spotter` quota. The original cohort and later learned skills
  remain separate. A generated attribute is *private objective state*, never
  automatically an observer's knowledge.
- Formation attribute commitments currently remain accessible through their
  originating group. Independent membership changes already preserve those
  facts in the origin Group; durable individual-level provenance will be needed
  before Group archival, removal, or migration can be supported.
- **Group membership design preference:** Groups are Entities that own membership
  relations. An inverse index for Being-to-Groups queries may eventually be
  derived but is not the authoritative source. Membership criteria, transitions,
  overlapping memberships and time validity remain deferred.

## Group-owned membership changes (2026-10)

- `StatisticalGroup` owns **current membership**: original cohort members minus
  those who have left, plus arrivals. A Being exists in the Universe independently
  of any Group; there is no authoritative Group list stored on the Being.
- `leave_being()` and `join_being()` are **independent operations** and record
  immutable, dated `MembershipChange` records (`leave` or `join`) in the affected
  Group's journal. An interval with no Group membership is valid. A returning
  native retains their original identity and formation provenance. No direct
  `transfer_being_to()` primitive is assumed; related departures and arrivals
  need not happen together or at the same simulation time.
- Formation `counts()` remain historical commitments. `current_counts()`,
  aggregate health, and known skills reflect current membership only.
  Departures and arrivals do not move Beings or change their health, abilities,
  existing Encounter actions, skill history, or original cohort CDF constraints.
  Rejoining does not automatically attach a Being to group movement.
- This experiment restricts caravan affiliation to **one StatisticalGroup at a
  time**, enforced by checking registered Groups at join time, and supports
  realized adult Beings only. This is a provisional constraint, not a claim
  about all future social, familial, institutional, or nested memberships.
- Operations take effect at the affected Group's current simulation time.
  Joins cannot precede the Being's last recorded membership transition across
  registered Groups. Synchronizing Group clocks is unnecessary; a canonical
  Universe time and historical replay/persistence remain future work.
- Membership eligibility, nonexclusive affiliation types, uninstantiated
  member departures, births, deaths, household restructuring, and automatic
  physical co-movement remain deferred. This is still an in-memory experiment.
