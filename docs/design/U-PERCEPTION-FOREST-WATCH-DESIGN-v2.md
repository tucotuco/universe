# Universe — Forest-Watch Encounter Instantiation, Awareness, and Deferred Perception Design

**Status:** Design/requirements record, **not** an adopted Encounter rule, executable implementation specification, or authorization to change code.\
**Revision:** 2 — incorporates the forest-watch discussion and subsequent decisions of 6 November 2026.\
**Replaces for planning purposes:** `U-PERCEPTION-FOREST-WATCH-DESIGN.md` (the initial exploration).\
**Related deferred note:** `docs/design/deferred-object-event-perception.md`.\
**Immediate work:** `U-REPO-001` (track `docs/encounters/` and plan regression triage), followed by reassessment.\
**Higher-priority candidate after housekeeping:** reproducible **on-demand Encounter instantiation**. Awareness/visibility tracking is another strong candidate; no next functional increment is yet authorized.

## 1. Decisions and boundaries

### Confirmed direction

1. **Retain the interim perceptual simplification.** A successful Spot or Listen obtains *accurate objective information about properties that are currently perceptible*. It does **not** disclose every property of the objective Entity, prove an identity, expose hidden Action state, or confer continuing knowledge of future Reality. No numeric observation error/quality/noise model is adopted at present.
2. **Observations are time-bound.** Accurate knowledge of the *current* location, motion, or other changing property can be **lost when tracking/contact is interrupted**. The observer retains the true *historical fact that was observed* and any ensuing Belief, but cannot refresh it from hidden Reality. A last-seen velocity need not remain the target's current velocity; a previous exact observation need not remain exact **current knowledge**.
3. **Awareness is observer state and has targets.** An observer has a set of targets for which current awareness/contact is maintained, with modality and other context as needed. “Was discovered previously,” “currently aware/visually tracking,” and “believes it is nearby” are different claims.
4. **Trying to maintain awareness is an Action.** Working name **Remain Aware** (or Maintain Awareness). Like Hold following Grab, it follows discovery by Spot; unlike a purely passive visibility flag, it represents intentional continued attention. An ongoing Action may be compatible with other Actions, including readying a bow; compatibility and effort must be evaluated, not automatically denied.
5. **A target must disappear from the observer's current visibility/awareness representation when that contact is broken**, regardless of cause (occlusion, concealment, darkness, silence, distraction, loss of attention, etc.). It does **not** disappear from objective Reality, immutable observation history, or the observer's remembered beliefs. This separation offers a foundation for fog of war.
6. **Awareness target-list size is a promising factor in interruptions.** The number of concurrently attended targets may affect whether contact is maintained following disturbance. This is a proposed dependency, **not an adopted capacity, die roll, probability, automatic loss, or fixed threshold**.
7. Preserve the existing distinction between **Reality, Observation, and Belief**; observer-isolated evidence, one-second atomic Encounter boundaries, deterministic sampling/retry, and accurate full-precision metric internal positions. User-facing game distances remain yards; physical Being lengths inches and weights pounds.

### Explicitly deferred

- Quantitative perception inaccuracy, property-specific confidence, probabilistic position/velocity estimates, distributions of possible current locations, and how uncertainty grows mathematically.
- How a successful visual observation estimates speed/direction from an observation interval; the temporal/perceptibility requirements are unresolved. Do not infer velocity solely from a single position sample or leak the private objective velocity merely because it is stored.
- Attention capacity, distraction penalties, multi-target loss rules, sensing modality dynamics, and Action concurrency/effort accounting.
- Detailed Hide in Shadows, Move Silently, Listen, recognition, fear, threat and response mechanics.
- A general observer-facing track-ID schema, full Event/phenomenon perception, exact Action identification, and cross-process persistence for awareness/attention states.

## 2. Priority: instantiate an Encounter on demand

This is the most important *new* architectural requirement revealed by the forest-watch example. The underlying Encounter cannot be assumed to contain two fully constructed Beings in known positions before the world needs them.

**Case:** A lone Elven Fighter in leather armor, armed with a longbow, is on nighttime watch in a forest camp and scanning for potential danger. A world-level random check indicates a potential Encounter with **one Being**. Universe must resolve exactly enough objective Reality for detection, Action, and subsequent observation to work, using prior world constraints.

### Proposed instantiation sequence (subject to later design review)

1. **World-level demand.** A potential Encounter becomes relevant at a definite simulation time. The single-Being constraint is objective and must not be treated as an observer discovery or an automatic successful Spot.
2. **Constrained candidate resolution.** Conditionally realize a plausible lone human female Thief, in leather armor with two daggers, moving and attempting to Spot. The illustration prescribes this result; a general system would sample it reproducibly from world and encounter distributions, satisfying established population, identity, history, gear, activity, geography, and chronology constraints. Resolve only what is required, retaining unresolved statistical attributes where possible.
3. **Environmental placement.** Determine the candidate's possible approach region using road access, vegetation/obstructions, terrain traversability, lighting, and any authored probabilistic preference for the road over dense forest. Choose approach direction and movement consistently with those constraints; do not teleport the candidate into implausible terrain or fabricate inconsistent earlier travel.
4. **Asymmetric sensory opportunity.** Assess the Fighter's and Thief's ability to detect one another independently under the same world state. In this illustration the Fighter's potential detection distance is greater, so the Thief is instantiated at that threshold along a plausible incoming route and is initially outside the Thief's detection envelope for the Fighter. Neither potential detectability nor realization confers actual Awareness.
5. **Time and discovery checks.** At the appropriate opportunity the Fighter fails a Spot check. The Thief advances. She later has an eligible Spot opportunity and fails. At the Fighter's next eligible Spot completion, his check succeeds. Distinguish **incidental discovery opportunities** from deliberate **six-second Spot Actions**; neither repeated free checks every second nor retroactive Action success should be inferred. Discovery must operate on an area/sector or other lawful unknown-target criterion without requiring the hidden target's identity.
6. **Atomic visibility and history.** Realization, movement, choices and observation follow native Encounter timing and transaction rules. A rejected or rolled-back interval cannot publish half-realized identity, leaked Awareness, partial Object evidence or inconsistent RNG. Later disclosure of the Being's exact identity or current position must be independently warranted.

### Essential questions for the first executable instantiation slice

- When is a potential encounter check made, what does its result guarantee, and what is the minimum objective Entity/state required before any Spot checks?
- What constraints govern candidate count, composition, terrain-conditioned placement and movement? What does it mean to instantiate *at* a perceptibility boundary while preserving historical causal consistency?
- Are the two observer-specific potential detection ranges computed from a shared candidate world state, and how is the first eligible discovery event selected chronologically?
- Which facts can remain statistical until perception or a subsequent Action demands them? How does the NPC Generator supply a generated Being without inventing unsupported native class/gear/history semantics?
- What is the minimal runnable demonstration of **one world-demanded Encounter** becoming one objectively present moving Being, with two independent unsuccessful/successful Spot opportunities and no observer knowledge leakage?

These are candidate development requirements, **not settled probability tables, encounter-rate rules, or permission to implement a speculative world generator**.

## 3. The forest-watch case: Reality, tracking, loss and reacquisition

The following stages illustrate the contracts; they do not impose additional check frequencies or observation-error distributions.

| Stage | Objective Reality | Observer-relative consequence |
| --- | --- | --- |
| Watch begins | Fighter guards a forest camp; possible routes and sensory conditions are established | Fighter may deliberately scan without knowing a hidden Being's ID |
| Demand/instantiation | One Thief is realized on a plausible approaching route at the Fighter's perceptibility limit | No automatic Fighter or Thief Awareness |
| Fighter's first opportunity | Thief approaches and is potentially detectable | Fighter fails Spot; remains unaware of this Thief |
| Thief's first opportunity | Thief enters her own potential detection range | Thief fails Spot; no Awareness leaked |
| Fighter discovers target | Thief is objectively 87 m away and approaching at 1 m/s | Successful Spot reveals only perceptible attributes: e.g., *unidentified medium humanoid on the road*; position and motion may be available under the current perceptibility/temporal rule |
| Fighter readies bow | Thief continues moving | Fighter tries to **Remain Aware** while readying; compatible simultaneous attention is possible, subject to later effort rules |
| Thief discovers Fighter | Thief succeeds at her independent Spot | Thief can choose to conceal herself; Fighter does not learn her intentions |
| Thief hides/goes silent | Thief leaves the road, finds effective concealment or becomes otherwise imperceptible | Fighter's **current track disappears** when contact is broken; no automatic new target position/velocity appears |
| Pursuit/search | Thief may move hidden toward camp; Fighter watches and listens | Last-seen evidence persists; present whereabouts are unknown or only believed; renewed Spot/Listen may reacquire |
| Voice call | Thief recognizes the Fighter and calls out | Fighter may receive auditory evidence, recognize voice/person and revise threat Belief; reciprocity is not automatic |

**Source-versus-observer example:** Reality may contain an 87 m range and 1 m/s velocity. The phrase “about 100 yards, about one yard per second” is an illustrative *future perceptual estimate/presentation*, **not** a newly adopted observation-error mechanism. Under today's interim exact-perceptible-property rule, the internal observation of a discernible property remains accurate, and user-facing customary-unit rounding is a display operation only.

## 4. Proposed awareness and attention lifecycle

A conceptual state machine, **not a finalized implementation schema**:

- **Undiscovered:** The observer has never obtained the target through a valid sensory discovery or other justified evidence.
- **Currently aware / in sensory contact:** A particular target is in the observer's current awareness target set, with modality-specific perceptibility, and can supply fresh observations when the relevant attention is maintained. Awareness does not grant permanent line of sight or omniscience.
- **Attempting to Remain Aware:** The observer undertakes an explicit ongoing attention Action directed at one or more awareness targets or a lawful watched area. The Action can overlap bow preparation, moving, or other activity when the combined demands permit; the allowed overlaps and costs are deferred.
- **Contact broken:** The target is **removed from the current awareness/visibility list** when a justified break occurs. Reasons may include occlusion, silence, concealment, distraction, overload, attention diverted or target movement beyond sensory limits. The target remains objectively real and historically known.
- **Belief without contact:** The observer can retain a last-seen state and infer that the target may still be nearby. Accurate current position and velocity cannot be assumed; they are not silently refreshed from Reality. History does not become false because a target subsequently moves.
- **Reacquired:** A valid fresh Spot, Listen or other perception event re-establishes contact to the same suspected or recognized target, subject to later track-association/identification rules.

### Target list and disruption

Awareness should name its **targets** at an observer-relative level, even when the true Being's identity is unknown. A disturbance may degrade or end attention to some targets; **the number of attended targets** is a sensible possible determinant of overload and selective loss. Other candidate inputs include salience, motion, proximity, conditions, urgency, competing Actions and sensory modality. None is assigned a numerical rule yet.

**Fog of war:** Current visibility is a projection of justified, live observer contact. When contact is broken, the target vanishes from the **currently visible/contactable layer**, not from the world or observation history. Last-seen markers, possible-region Beliefs and explicit “unknown” current state are separate observer-side representations. A hidden Object must never continue to move on the observer's screen as though it were still watched merely because Reality keeps updating it.

### Hold/Grab analogy and limits

Spot establishes discovery, just as Grab establishes contact; **Remain Aware** deliberately attempts to sustain perceptual contact, somewhat as Hold attempts to sustain a grip. Unlike physical grips, maintaining several targets may draw on a shared attention capacity, and perception can be disrupted by loss of sensory availability even when the observer remains attentive. No automatic repeated Spot roll or mandatory periodic Remain Aware roll follows from the analogy alone.

## 5. Deferred observation and uncertainty elaborations

These are explicit research/design requirements while the interim simplification remains in effect:

1. **Property-specific perceptibility:** Detection of an Object or Event does not imply recognition of sex, species, occupation, possessions, private Action, motive or exact identity. Visible appearance, general form, location, motion and recognized activity may have independent perceptibility constraints.
2. **Time support for motion:** Distinguish an instantaneous position, a movement observed over an interval, and a speed/direction inference. Model reference frame, duration, timing, sensory modality and precision. Do not derive observed velocity merely by copying an inaccessible Reality field from one instantaneous sample.
3. **Accuracy versus freshness:** An observation can accurately record past position and velocity yet give no reliable *current* value following tracking interruption. When further observations stop, current knowledge may become unavailable even though immutable historical evidence remains accurate. This qualitative loss is required **now**; a numerical uncertainty-growth model is **later**.
4. **Track loss and attention:** Distinguish interrupted attention, broken line of sight, concealment, sensory darkness, auditory masking and target disappearance; the current track must be withdrawn when the relevant conditions no longer support it, not merely marked with an ever-growing timestamp.
5. **Possible positions:** Eventually, a Belief may represent a time-dependent reachable region or distribution conditioned on terrain and plausible movement. No Gaussian error, fixed probability tail, constant-speed extrapolation or numeric fear parameter is currently adopted.
6. **Object/Event generality:** A flying projectile and moving thief are Objects (including Being as Object). An alarm, sound, flash, fire front or shout may be an Event/phenomenon, with different spatial and temporal support; do not force all Events into Object point-position/velocity fields or automatically reveal their causes.
7. **Activity versus intent:** Noticing an outward activity, such as bow-readiness or concealment movement, is not the same as identifying a privately scheduled native Action, its intended Target, future result or causal reason.
8. **Observer isolation and identity continuity:** Different observers may retain different tracks/evidence. A low-information “medium humanoid” target handle must be compatible with later recognition as a known person without retroactively exposing secret identity before recognition. Independent testimony is evidence, not automatic truth.
9. **Threat and fear:** A known potential danger that disappears can remain threatening precisely because location and intent are uncertain. Future fear/vigilance mechanics must be grounded in observer Belief, not hidden true hostility.
10. **Transaction and persistence:** Any contact-loss, renewed evidence or Belief change must be staged and published consistently with simultaneous-action snapshots and rollback. Historical evidence may never consult live Reality to silently update itself. Portable checkpoint closure for attention/contact records is a later engineering requirement.

## 6. Development sequence and housekeeping

**Do now:** Execute `U-REPO-001` and assess its report. Explicitly track the current authoritative `docs/encounters/` package in Git without blindly staging the larger documentation move, and produce an evidence-based regression-failure triage plan. The prior full discovery produced 1,759 tests: 1,591 passed, 43 failures and 125 errors; some causes are known (loopback-server permission and paths moved in the documentation reorganization), others unclassified. Do not call the suite green or classify all failures as environmental without evidence.

**Then reassess** which independently green executable slice provides the most value:

- **Candidate A — On-demand Encounter instantiation (currently higher priority):** World-driven single-Being demand, constraint-consistent placement/approach, observer-asymmetric perceptibility, unknown-target Spot opportunities, no leakage or historical contradictions.
- **Candidate B — Targeted awareness/visibility lifecycle:** Discover a generic moving Being; undertake Remain Aware while performing compatible activity; preserve a live target set until justified interruption; remove the target from current visibility when contact breaks; retain historical evidence and last-seen Belief; then reacquire.

Do **not** execute the earlier `U-OBS-BELIEF-001` as if it already addressed these general questions. Its last-seen data requirements remain useful, but it is deferred for prioritization after housekeeping. Neither candidate has yet become an approved next Codex implementation assignment.

## 7. Authority and scope

This note elaborates the user's forest-watch case and the prior deferred Object/Event perception requirements. It is a record of direction and questions, not a substitute for the controlling Encounter revision-61 baseline with revision-62 and revision-63 supplements or for actual source inspection. In case of conflict, later explicit adopted decisions and checked-in implementation/report evidence govern. The unfinished documentation migration and broad-suite verification are independent open workstreams.
