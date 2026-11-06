# Universe — Deferred Design: Object, Event, Motion, and Action Perception

**Status:** DEFERRED design note; not an implementation assignment and not an amendment to the adopted Encounter rules.<br>
**Recorded:** 2026-11-04 (Universe 7)<br>
**Related work:** U-WORLD-001A/B; U-SPOT-002A; U-LOC-002A; proposed U-LOC-002B (deferred); broader U-SPOT-002, U-LOC-002, U-ATT-001, U-AGENT-001, U-PER-002.<br>
**Intended repository path:** `docs/design/deferred-object-event-perception.md`.

## 1. Purpose and decision

Defer the proposed **U-LOC-002B evidence-driven follow-up Action** as the next development increment. Its narrow example—using a previously observed location to choose a later Move—could be useful eventually, but it does **not** constitute a satisfactory model of perception or perception-driven behavior. Do not portray it as covering that broader subject.

Preserve the existing, tested **U-LOC-002A** result: a configured successful native Spot can atomically publish an immutable, observer-owned, time-stamped location observation for one Being, alongside Awareness, and `last_seen_location()` returns historical evidence rather than live Reality. That demonstration does **not** implement general perception of Objects, Events, velocity, or performed Actions.

This note records **requirements to investigate and questions to decide**, not new runtime rules, automatic disclosures, data schemas, or adopted physiology/perception mechanics.

## 2. What a Spot observation may concern

A future general perception model must consider these potentially distinct components, subject to perceptibility:

1. **Subject / phenomenon:** What was detected may be an **Object** (a Being is an Object) or an **Event**. Detecting something need not establish its specific identity, type, participants, cause, or full extent. An Object and an Event remain distinct ontological categories. A perceived Event is not automatically an Object, nor is an Event necessarily itself an Action being performed.
2. **Movement:** Observations may concern location and **velocity**, including speed and direction when meaningful. Acceleration is expressly **deferred** as a perception feature; it is difficult to assess observationally and is not required for the next design. The motion of some Events may instead have a changing spatial region/front; do not assign every Event a point velocity by fiat.
3. **Activity:** An Object may be engaged in a perceptible **Action**. The observer may recognize some outwardly apparent activity without access to the Action's hidden implementation state, private intent, scheduler entries, future consequences, or target identifiers. Perceived activity and a separately perceived Event require an explicit relationship when appropriate; they are not synonyms.

The three components are **not guaranteed to co-occur**, and their perceptibility, observation time support, and eventual uncertainty may differ. A successful Spot should not be interpreted as a universal dump of all authoritative state associated with the target.

## 3. Interim simplification versus future uncertainty

**Previously adopted interim simplification:** A successful Spot or Listen provides *accurate objective information about currently perceptible properties*. Observation-quality gradients, inaccurate estimates, noise, and probabilistic uncertainty were deferred; Spot has no progressive skill XP. This is a temporary implementation/modeling simplification, not a permanent assertion that perception is perfect in a general simulation.

**Current implications:**

- First decide whether a property is **perceptible under the applicable circumstances**. Exactness applies only to information that is perceptible. A property can be absent/unknown rather than inaccurate.
- Objective Reality must not be exposed merely because the engine stores it. Detection of an Object need not identify the Object, expose its genealogy, grant its precise current location indefinitely, or reveal its current/future Action.
- Different observers may acquire different evidence. Publication/materialization alone must not grant Awareness, Observation, or Belief.
- Future work may introduce **distinct uncertainties** for subject identification, position, velocity, and recognized Action, without conflating uncertainty with non-observability or with a subsequent Belief/inference.
- **Do not design or implement a particular uncertainty distribution, skill margin mapping, confidence score, or extra discovery roll in this note.** They remain to be decided.

## 4. Time and kinematic evidence

Observations need explicit temporal semantics: *when* a property was visible, *when* the observation was acquired/published, and whether it represents a moment, an interval, or multiple samples.

A location sample at one integer boundary does not, by itself, justify knowing an object's velocity. A future velocity observation needs an approved perceptibility/temporal rule: for example, discernible motion during the Spot interval or distinct evidence across observations. Whether instantaneous objective velocity can be reported under the interim perfect-perceptible-property rule remains **undecided**; do not silently derive it from engine access.

Similarly, recognizing an Action may depend on visible behavior over time rather than a single stored scheduler flag. Preserve the native Encounter semantics: movement first; simultaneous nonmovement Actions evaluated against a common post-movement, pre-Action snapshot; effects and observer consequences staged/committed atomically. Do not leak the outcomes of Actions that have not yet committed.

The existing six-second deliberate Spot timing, default DC 15, and zero Spot XP remain in force unless separately amended through the authoritative rules process.

## 5. Reality, Observation, Belief, and authority boundaries

- **Reality:** Objective Objects, Events, trajectories, and Action executions exist independently of who observes them.
- **Observation:** An observer-specific, time-grounded record of what that observer actually perceived. Its content must be limited to authorized, perceptible properties and preserve provenance.
- **Belief:** What the observer concludes or retains about Reality, potentially influenced by earlier observations, inference, testimony, and future contradictions. Belief need not equal current Reality. Future uncertainty modeling must specify whether a confidence belongs to observation evidence or inference, or both.

Trusted simulation code may internally identify eligible candidates or consult authoritative state to resolve an Action; that does not authorize revealing hidden identities/coordinates/activities to the simulated observer or to the observer-facing interface.

Location observation must remain historical. Movement after observation does not silently update the observer's previous evidence. No implicit knowledge sharing across observers.

## 6. Illustrative use cases — requirements, not settled rules

**A. Distant moving Being.** A Spotter sees an unfamiliar figure at a distance. Subject: some Object may be detected without specific identity/species. Movement: location and potentially direction/speed if perceptible during the relevant interval. Activity: running, carrying, striking, or another visible Action may be recognizable, but privately scheduled/intentional details are not automatically known. The figure can later move without updating the prior observation.

**B. Moving inanimate Object.** A flying stone can be an observed Object with location and possibly velocity. Observing its motion does not by itself establish that a particular Being threw it or which hidden Action caused it.

**C. Event as subject.** A flash, collapse, or explosion may be perceived as an Event with a locus, spatial extent, and temporal extent. Not all Events have a meaningful single-object position/velocity; participants, causes, and Actions that produced them might remain unknown.

**D. Incomplete evidence.** An observer can detect an Object without having enough information to infer velocity or identify its performed Action. Absence of evidence is not necessarily an erroneous estimate.

**E. Observer isolation.** Two observers sharing a scene may perceive different subsets of an Object/Event's properties; their evidence and Beliefs cannot be populated by a developer's global knowledge or by one another's observations unless separately justified.

**F. Transaction failure.** If a successful perception is due to publish a subject, motion, or activity observation together with Awareness, exceptional publication failure must not leave partial evidence, knowledge, RNG advancement, or lifecycle history; deterministic retry must remain possible.

## 7. Unresolved architectural decisions

Before an implementation scope that genuinely advances general perception, explicitly resolve only the decisions required by that scope:

1. **Perceptibility:** Which Object/Event attributes are observable in a particular visual/listening context? How does an unknown category differ from a known Object identity? How are occlusion, distance, apparent size, and temporal visibility treated?
2. **Object versus Event evidence:** What common observation concepts can be shared, and what must remain type-specific? How are observed Events linked to Objects, participating Beings, and Actions without making unsupported causal inferences?
3. **Velocity evidence:** Which frame of reference, units, duration, time sampling, and perceptibility prerequisites support an observed velocity vector? How are stationary/indeterminate states distinguished? **No acceleration perception yet.**
4. **Recognized Action:** What outwardly visible information is sufficient to recognize an Action? How are apparent activity, actual Action identity, commencement/completion, and currently unresolved simultaneous Actions distinguished? How does this relate to, but not expose, hidden scheduler state?
5. **Observation granularity:** Is successful Spot one discovery gate followed by property-level perceptibility, or are further checks needed? Do not invent additional rolls without an adopted rule. Avoid hardcoding current fixture assumptions as universal observation policy.
6. **Evidence and Belief:** Where should time-stamped Object/Event/location/velocity/Action evidence live? What can last-seen and history queries return without consulting live Reality? How will eventual uncertainty be represented and kept distinct from Belief?
7. **Persistence and presentation:** How should a future authorized checkpoint or UI preserve/show observer-limited evidence without revealing developer-only world state? Existing U-LOC-002A recipient is intentionally unsupported by portable checkpoint descriptors.
8. **Domain generality:** How will heterogeneous and unresolved StatisticalGroup members and newly realized Objects/Events participate without pre-resolving identities or violating population conservation?

## 8. Future development sequence (illustrative only)

A possible later sequence is: (a) agree on an Object/Event observation contract and temporal support; (b) prove a visible-motion observation without deriving velocity from a lone position sample; (c) prove recognition of one currently perceptible Action without exposing hidden scheduler state; (d) integrate distinct Object and Event examples; (e) add uncertainty/quality only after its rules are adopted; (f) test serialization, observer-facing presentation, and evidence-driven Action selection. These steps are **not approved Codex assignments or a fixed roadmap order**.

Any eventual executable increment should be narrow, independently green, and explicit about which of these concerns it *does not* implement. It should preserve existing r60 rules, transactional Encounter behavior, ReproductionGroup semantics, cross-layer identity, and Reality/Observation/Belief separation.

## 9. Task bookkeeping and preservation

- **U-LOC-002A:** Completed within its bounded historical Being-location evidence scope, as recorded in the current task register and topic files. Do not broaden its completion claim.
- **Proposed U-LOC-002B:** **DEFERRED / NOT AUTHORIZED** pending a richer discussion of perception and chosen next objective. Do not create a Codex implementation assignment from the earlier recommendation alone.
- **U-SPOT-002, U-LOC-002, U-ATT-001, U-AGENT-001, U-PER-002:** Remain open/deferred according to their authoritative task records. No claim that generalized perception or Agent behavior is complete.
- This note is cross-referenced from `TASKS.md`, `docs/tasks/encounter-engine.md`, `docs/tasks/generation-and-attention.md`, and `docs/tasks/broader-universe.md`. These links make the deferred design discoverable; they do not adopt its proposals or alter the Encounter rules.

## 10. Authority and sources

This note records the user's earlier Universe 7 direction. For current planning, read it with the [Universe 7 → 8 review handoff](../handoffs/universe-7-to-8.md), U-REPO-005/006 reports, current task register, and adopted Encounter package. This remains design only: it does not amend the r61 baseline or r62/r63 supplements, nor authorize implementation. Preserve the independent `npc-generator-web`, protected legacy archive, saved JSON/configurations, and unrelated user work.
