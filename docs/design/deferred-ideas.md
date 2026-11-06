# Universe — deferred ideas and implementation status

**Review checkpoint:** 2026-10-19, after the compact combat UI increment (the
567-test checkpoint reported for that patch). This is a consolidated **living
backlog**, not a declaration that the general architecture is complete. It
reflects the uploaded repository baseline and subsequent development patches;
verify against the user's local checkout when synchronizing again.

This is a historical planning backlog. Current tasks, source, and adopted
Encounter rules supersede its status statements. The older source documents it
references are retained as history or in the private archive; none of its
proposals is an adopted simulation rule.

**Statuses:** **Demonstrated** = exercised by implemented tests/examples within
specified limits; **Partial** = working limited mechanism with important missing
cases or broader integration; **Deferred** = principle or planned experiment,
not implemented in its intended general form. A row can name more than one
status to make the boundary clear. Items are organized by area, not priority.

| Idea / capability | Where we stand |
|---|---|
| **Foundations — builder and discoverer**: interaction determines which aspects of a self-building world are realized | **Guiding goal; partially demonstrated.** Interactive inquiry selectively realizes a Being's history; live combat is explorable, but no general self-developing world. See [realization contract](../experiments/discovery/realization-contract-experiment.md) and [interactive discovery](../experiments/discovery/interactive-discovery.md). |
| **Foundations — cross-domain resolution on demand** across composition, space, time, and history | **Partial.** Shared `RealityLedger` supports inspect/propose/validate/commit; Group formation and limited Being back-story use it. General cross-subsystem refinement remains **deferred**. |
| **Foundations — coarse/fine consistency and conditional realization** | **Partial.** Fixed quotas, conditional formation attributes, and small historical constraints are tested. Joint inference across domains, scales, and alternative histories remains **deferred**. |
| **Foundations — historical queries and selective retrospective refinement** | **Partial.** Dated Group membership and original composition are queryable; a Being can acquire narrowly constrained past episodes. General historical health, skills, positions, causal processes, and later-event compatibility remain **deferred**. See [Group](../experiments/discovery/historical-group-realization.md) and [Being](../experiments/discovery/historical-being-realization.md) experiments. |
| **Foundations — temporal/causal consistency**: established past or future facts *may* constrain newly realized detail | **Partial.** Skill non-decline is an *explicitly optional* illustrative rule; speed bounds are a narrow probe. A general causal/process model and conditional temporal refinement remain **deferred**. |
| **Foundations — authoritative state and atomic rejection** of inadmissible realizations | **Demonstrated locally.** Ledger rejects impossible proposals without changing committed facts; broader cross-Entity transactions and authority boundaries remain **deferred**. |
| **Foundations — reproducibility, provenance, and replay** | **Partial.** Keyed generators, committed fact revisions, independent combat RNG and checked combat command journals exist. World-wide stochastic-state management, portable replays across engine versions, and durable provenance for all simulations remain **deferred**. |
| **Foundations — general Universe save/load and resume** | **Deferred.** `PersonalHistory` can export facts; combat sessions can be saved/reloaded/replayed, but neither is a full Universe/Encounter serialization of arbitrary interacting Entities. |
| **Foundations — shared world clock and event/state reconstruction** | **Partial.** Encounter advances one-second steps and scenarios synchronize local clocks. Global simulation time, event-sourced reconstruction, concurrent subsystem lifecycles and long-duration histories remain **deferred**. |
| **Foundations — self-consistency across broad simulation systems** | **Deferred beyond narrow probes.** Test cross-scale invariants with geography, physics, populations, and personal history before claiming a general rule engine. |
| **World scale — spatial indexing and continuous 3D physical space** | **Demonstrated foundational slice.** Continuous coordinates are authoritative; ISEA cells and Encounter-local frames are derived representations. General multiresolution planetary geography and spatial state persistence remain **deferred**. See [working decisions](../history/working-decisions.md). |
| **World scale — terrain and environment refinement** | **Deferred.** Generate landforms, obstacles, climate effects, light and local detail constrained by coarser established terrain and Encounter facts. No integrated terrain generator yet. |
| **World scale — integrated systems** (astronomy, planets, climate, ecosystems, evolution, settlements, economies and civilizations) | **Long-term vision; deferred.** No integrated simulation chain exists yet; resolution-on-demand is intended to link these systems. |
| **World scale — physical trajectories and motion refinement** | **Partial.** Position, velocity, 3D geometry, range, and simple movement are modeled; interpolation with collision, terrain, acceleration, physical locomotion and precise movement histories remains **deferred**. |
| **Groups — general, scalable hierarchical statistical Groups** | **Partial.** Configured nomadic households, quotas, and conditional attribute chains exist. Recursive nested groups, flexible schemas, realistic correlations and large-population efficiency remain **deferred**. |
| **Groups — mixed-origin evolving composition** | **Partial.** Original cohort constraints remain intact through membership changes; current residents are counted separately. Conditional inference over arrivals, nonrandom departures and unresolved evolving populations remains **deferred**. |
| **Groups — memberships and affiliations** | **Partial.** Group-owned join/leave history; Being may exist outside any Group. Eligibility, multiple simultaneous affiliations, overlapping group types, and group hierarchies remain **deferred**. |
| **Groups — population lifecycle and unknown-member changes** | **Deferred.** Births, deaths, aging, household changes, migration of unresolved members, and population turnover are not yet modeled as general historical transitions. |
| **Groups — heterogeneous individuals and social relations** | **Partial.** Original adults can become real Beings. Children, livestock, dogs, kinship, partnerships, institutional affiliations and individual relationship histories remain **deferred**. |
| **Groups — collective motion versus independent individuals** | **Partial.** Moving Group centers, footprints, and selected member positions exist; co-movement policies, detachment, density, independent member trajectories and geometric collisions remain **deferred**. |
| **Beings — generated personal histories, aging and life processes** | **Partial.** Limited narrative episodes and nondeclining skill facts can be retrospectively committed. Aging, injury/healing timelines, skill decay, memories, relationships and causally generated biographies remain **deferred**. |
| **Beings — capabilities, practice, training and experience** | **Partial.** Skill exercise, XP, progressive ranks, action histories and weapon XP work. Configurable learning policies, skill transfer, trainers/teaching, long-term adaptation and biologically/physically grounded capabilities remain **deferred**. |
| **Observation — Reality → Observation → Perception → Belief** | **Demonstrated separation; partial sensing.** Observation can interrogate and realize facts; perception/testimony can be wrong; belief keeps provenance. Real sight, hearing, attention, illumination, occlusion, and inference from gestures remain **deferred**. |
| **Observation — fallible, correlated and communicated evidence** | **Partial.** Noisy Group estimates, evidence revisions, explicit reinterpretation and source identity exist. Calibrated uncertainty, dependent evidence, misidentification, trust and deliberate fabrication remain **deferred**. |
| **Discovery — independently checking testimony** | **Partial.** The explorer can compare conflicting accounts, but cannot yet independently investigate the underlying Episode to establish which account was accurate. Motive and deliberate lying remain **deferred**. |
| **Social worlds — myth, legend, religion and shared narratives** | **Conceptual direction; deferred.** Fallible testimony and evidence provide a foundation; cultural transmission, communal beliefs, institutions, incentives and changes in traditions have no implemented model. |
| **Social worlds — trust, teaching and communication** | **Partial.** Evidence can be shared with provenance; practice and reinterpretation exist. Source credibility, intentional persuasion, teacher/student Actions, collective belief dynamics and language/conversation models remain **deferred**. |
| **Agents — choices, goals and inquiry planning** | **Partial.** Guided evidence-driven inquiry and a simple Raider combat policy exist. General autonomous goal selection, planning, learning from consequences and decision-making under imperfect knowledge remain **deferred**. |
| **Combat — timed Actions and concurrent movement** | **Demonstrated for melee.** Swing/thrust preparation, interrupts, sustained Guard and independent movement run on Encounter time. More general overlapping/conflicting action scheduling remains **deferred**. |
| **Combat — simultaneous resolution** | **Partial.** Equal-time strikes freeze attack eligibility first; injury, equipment effects and multi-target consequences are still applied sequentially. A general multi-phase resolution contract remains **deferred**. |
| **Combat — skill-effort distribution** | **Partial.** Offense, defense, speed/timing and damage allocations work for a bounded weapon-skill pool; a general cost/effort model covering all Actions remains **deferred**. |
| **Combat — specific, timed parry and dodge** | **Demonstrated provisional mechanics.** Each reaction is directed at one designated incoming strike and must be ready by impact; 3-second dagger parry and 2-second dodge. Physical defensive arcs, competing attacks and realistic reactions remain **deferred**. See [current rules](../history/combat-attack-specific-ui.md). |
| **Combat — expanded action repertoire** | **Deferred.** Feints, blocks, shield use, grapple, trip, disarm, cover, ranged attacks, multiple defense targets and other draft Actions need coherent scheduling, skill and consequence definitions. |
| **Combat — detailed engagement geometry** | **Deferred.** Facing, reach in physical units, anatomical envelopes, swept weapon paths, stance, balance, collisions and environment-dependent contact are not yet modeled; the current reach ring is provisional. |
| **Combat — localized injury, protection and healing** | **Partial.** Weapon damage, armor wear and Being HP exist. Anatomical impact sites, protection coverage, pain, bleeding, incapacitation mechanisms, treatment and lasting impairment remain **deferred**. |
| **Combat — exertion and fatigue** | **Partial.** `Exertion` increases fatigue and can penalize accuracy or incapacitate. Recovery, equipment load, exertion by action, defense/movement penalties and sustained-condition modeling remain **deferred**. |
| **Combat — sensory presentation and decisions** | **Partial.** The observer-filtered map shows perceived opponent actions and limited range/position; NPC behavior is simple. Facing, actual pose/feint recognition, uncertainty over attacks and realistic adversarial tactics remain **deferred**. |
| **Combat — player interface and encounter history** | **Demonstrated prototype.** Live browser combat, compact command panel, keyboard cardinal movement, Being hover/click details, nearby history, effort popup and replay are implemented; browser presentation still needs real-user evaluation and UX iteration. See [compact UI](../history/compact-combat-ui.md). |
| **Combat — larger encounters and tactical autonomy** | **Deferred.** Multiple combatants, formations, multi-attack targeting, allies, autonomous tactical goals and larger battles are not yet integrated. |
| **Engineering — reliable regression, reproducible patches and documentation** | **Partial.** The engineering baseline removed eight legacy test failures; the latest reported checkpoint is 567 passing tests. Keep changes based on a known user commit, update this backlog and verify actual local checkout. Current notes retain older, sometimes superseded experimental rules. See [engineering baseline](../reports/engineering-baseline.md). |

## Principles that should not be lost

- **Builder and discoverer:** world generation should leave room for real inquiry and surprise while maintaining coherence with established commitments.
- **Groups own memberships; Beings exist independently:** departure and joining are separate occurrences and need not be paired.
- **Observation interrogates objective reality; Perception and Belief are Agent-relative.** Neither testimony nor belief automatically changes reality.
- **Refinement is conditional:** prior or subsequent facts constrain a proposal only to the extent that actual rules establish a constraint. Impossible proposals are rejected without rewriting commitments.
- **Historical formation statistics are not the current population.** A Group's original quotas coexist with moving and changing membership; unobserved details are not fabricated merely to complete a report.
- **A physical simulation must be grounded in time and space:** movement and another Action can coexist; weapon range is checked at impact, not when preparation begins; defenses are directed at designated attacks and apply if ready at impact.
- **Skills, fatigue, experience, and consequences belong to the same simulation.** An Action should not award XP for an attempt that never occurred.

## Maintenance and source-of-truth notes

1. This is an **index of outstanding intentions and partial implementations**. It does not override the actual source or tests. Update an entry as soon as an increment changes its status.
2. Preserve historical experiment notes rather than rewriting them as if they had always specified later behavior. **Later combat changes supersede some early documents** (e.g. initiation-time reach checks and one-second defensive reactions). For current melee readiness, consult [impact and reactions](../history/combat-impact-and-reactions.md), [attack-specific targeting](../history/combat-attack-specific-ui.md) and the code/tests.
3. A combat **command journal** is not a general Universe archive. A simulated narration is not automatically a validated structured historical Event. Distinguish tested behavior from conceptual aspirations.
4. Before the next handoff, record the user's exact `git log -1`, `git status -sb`, local full-suite result, and any untracked work intentionally retained. The latest conversation noted a modified `src/library.py` and untracked example/preview/save files; this index does not modify them.
