# Universe — Current State, Tasks, and Ideas

> **Reconciled:** 2026-11-11. This register was reconciled against the actual checkout through `1237897` and the U-ARENA-018 report. It is a current-state document, **not a development log**. Repository reports record evidence but do not independently re-execute it.
>
> **Single point of departure:** **All significant completed capabilities, active work, open tasks, blocked dependencies, deferred tasks, and future ideas live here.** Reports, assignments, Git history, design notes, and archived experiments remain evidence/detail, **not competing task or idea registers**. New ideas are appended here even when not authorized for implementation. See [development process](docs/DEVELOPMENT-PROCESS.md).

## Reading this register

- **DONE** = the specifically described, *bounded* result has supporting engineering evidence. It does not certify the complete general capability.
- **ACTIVE** = the one current implementation program, subject to current checkout confirmation. **ASSIGNED** means an assignment exists but no verified result has yet been received.
- **PARTIAL** = some native/experimental capability works, but the stated full outcome is unfulfilled. **OPEN** = no accepted completion evidence. **BLOCKED** = a specific unresolved rule, authoritative data, or external prerequisite prevents the stated result. **DEFERRED** = retained but not in current implementation scope. **IDEA** = captured possibility, *not* approved or adopted. **VERIFY** = available evidence does not establish a reliable current status.
- **Stable IDs are permanent.** Retain original `U-*` IDs. Newly assigned `U-ACT-*`, `U-CAP-*`, `U-IDEA-*`, and `U-DOC-*` IDs identify inventory entries, not necessarily individual Codex assignments. Do not renumber when reprioritizing. A single assignment may advance many IDs.
- **One ACTIVE program**, not one active checkbox for every subtask. Work under it can touch several open entries. Keep titles and descriptions as *current state/next gap*, not dated incremental narratives. Source evidence belongs in linked reports and Git.
- A **rule or design decision** is not an implemented feature; **catalog visibility** is not an Action implementation; **HTTP/session tests** are not a manual Chrome playthrough; a completed narrow fixture is not general Universe capability.
- `docs/encounters/README.md` defines the current adopted Encounter rules and applicable supplements; older r60 issue/count descriptions in archived task files are *historical*, not today's authority. Do not silently close any ES issue here without reconciling its authoritative register.

## Current project snapshot

- **Vision:** a coherent Universe realized statistically and incrementally **on demand**, subject to constraints already established in Reality; distinguish authoritative **Reality**, observer-specific **Observation/Awareness**, and subjective **Belief**. World/Agent inquiry should produce legitimate surprise without violating committed facts. Beings are Objects; Events are a distinct ontology. See [broader world](docs/tasks/broader-universe.md), [generation and attention](docs/tasks/generation-and-attention.md).
- **Current executable center:** local generated Arena using independently maintained `npcgen` as initial-Being specification; native one-second transactional Encounter; continuous metric positions and one-yard regular-hex presentation; movement, initial equipment, observer-owned visibility, attacks/defenses, Object interactions, bounded physical Grapple and fresh-process Save/Load. See [Universe 8→9 handoff](docs/handoffs/universe-8-to-9.md) and [U-ARENA-018 report](docs/reports/U-ARENA-018-report.md).
- **Current incompleteness:** U-ARENA-018 remains partial; its report enumerates close-contact lifecycle, same-second cancellation/conflict, Action variants and browser gaps. Other open areas include remaining Combat Action entries/variants, general sensory perception, multi-Action scheduling, occupied-space/forced movement, targeted projectiles, physical work/fatigue, and general world persistence. Browser success and native test success are tracked separately.
- **Non-Arena progress:** deterministic ReproductionGroup/ancestry generation and partial membership; aggregate StatisticalGroup evidence and one counted member's realization; spatial examples and observer evidence. These are *bounded independent demonstrations*, not a unified general world-history generator.
- **Repository status:** U-REPO-007B previously published a sanitized range; the later Universe 8→9 audit reported many unpushed Arena commits and potentially revealing machine-local paths in historical committed reports. **No automatic push, force push, or history rewrite.** Confirm current branch, upstream, and status before drawing a newer conclusion.

## ACTIVE — current implementation program

- [ ] **U-REPO-008 — ACTIVE / BLOCKED at the publication gate.** Recovery bundle and isolated clone are verified; the reusable offline scanner and process policy are implemented and tested. The unpublished 156-commit range still needs sanitization. The verified published ancestor also contains machine-temporary-path findings, and U-REPO-008 requires a user decision before any rewrite or push proceeds.

## NEXT — candidate capability programs (ordered for discussion; not automatically authorized)

- [ ] **U-ARENA-018 — PARTIAL / OPEN; NEXT candidate for continuation.** Native Takedown, Reverse, Pin, Trip and kneeling state exist; the generated Arena in-app browser completed Touch→Grab→Grapple→Takedown and a pending-Grapple Save/Load continuation. Remaining items: voluntary Grip release, cancellation of later attacks after Trip, multi-grappler/simultaneous position conflicts, remaining position consequences, supported Stun/Subdue/unarmed Disarm work, and an eligible-player browser flow. The separate Chrome session reached Touch/Grab only. See the [assignment](docs/assignments/U-ARENA-018.md) and [report](docs/reports/U-ARENA-018-report.md).
- [ ] **U-CAP-001 — NEXT candidate: general Action composition.** Implement Multiple actions, declared shared resource/timing/strategy-point allocation, Delay, conditional Ready, and legal concurrent demanding Actions under common-snapshot resolution; reuse native Choice/transaction infrastructure. Dependencies: [U-ACT-007](#offensive-and-defensive-combat-action-inventory), [U-ACT-013](#offensive-and-defensive-combat-action-inventory), [U-ACT-015](#offensive-and-defensive-combat-action-inventory).
- [ ] **U-CAP-002 — NEXT candidate: authoritative occupied-space and forced-movement contract.** Resolve traversed/occupied hex clearance, contested displacement, posture/occupancy and simultaneous route interactions to unlock Bull rush, Overrun, End run, Charge and Disengage; do not invent body geometry or force physics.
- [ ] **U-CAP-003 — NEXT candidate: weapon/equipment completion.** Finish shield bash, two-handed handling, non-Dagger hand requirements, Object attack variants, readiness/possession and off-hand conflicts using native Object identities and adopted rules.
- [ ] **U-CAP-004 — NEXT candidate: targeted projectile and ranged combat.** Build target/impact/miss/interception, source-owned geometry/observation prerequisites, Shoot, general Throw, Deflect and applicable ranged Coup de grace; respect existing narrow per-second ballistic motion without pretending it is a full ranged attack.
- [x] **U-DOC-001 — DONE: adopt this reconciled current-state/idea register and development-process contract.** The reconciliation preserved previous IDs and captured the new biota/phylogeny idea below; it does not certify inaccessible conversation history.
- [ ] **U-DOC-002 — OPEN / verification: historical idea capture audit.** Continue checking accessible Universe conversation handoffs, archival/deferred-idea material, topic/design documents, and local notes for concepts absent from this register. Capture missing ideas here; do not infer approval from discussion alone. Completeness across inaccessible/lost conversations cannot be certified.

## DONE — bounded milestones and retained capabilities

### Repository, engine, history and world realization

- [x] **U-OPS-001 — DONE: verified original native Encounter CORE baseline.** Exact historical tested candidate committed; bounded scope. [repository workflow](docs/tasks/repository-workflow.md).
- [x] **U-OPS-002 — DONE: controlled historical cleanup and recovery archives.** Earlier source/provenance preserved; not general authorization to delete remaining local files.
- [x] **U-OPS-003 — DONE: separately committed interrupted work-stash.** Snapshots recoverable locally; private material is not thereby a published remote backup.
- [x] **U-OPS-004 — DONE: root task register and five topic files originally adopted.** **Its present content needs reconciliation**; this checkbox only certifies original creation.
- [x] **U-OPS-005 — DONE: original CORE candidate independently scoped and tested.** Historical baseline, not a claim that today's entire test suite is green.
- [x] **U-ENG-001 — DONE (bounded): one-second transactional Encounter.** Movement precedes equal-boundary Action resolution; common frozen snapshot, Target-owned effects, atomic publication/rollback, deterministic RNG and Action/Choice lifecycle for supported families.
- [x] **U-PER-001 — DONE (bounded): Run fresh-process checkpoint continuation.** General persistence now has its own open task [U-PER-002](#open--general-world-and-encounter-capabilities).
- [x] **U-SPOT-001 — DONE (bounded): deliberate native six-second Spot.** Discovery check and zero Spot XP, not general category search or all-senses perception.
- [x] **U-GRP-001 — DONE (bounded): exact observer-specific aggregate Group count.** Does not disclose members or full taxonomy.
- [x] **U-GRP-002 — DONE (bounded): independently authored realization of one already-counted adult.** Atomic, conserved, no automatic discovery.
- [x] **U-GRP-003 — DONE (bounded): identity-free unique-candidate Being Spot adapter.** Not general Search or a world realization trigger.
- [x] **U-GRP-004 — DONE (bounded): Group evidence → world realization → discovery → Thrust demonstration.** Integrated chronology and observer isolation in authored example.
- [x] **U-LOC-001 — DONE as historical experiment only: initial waypoint/landmark Belief.** Not automatically promoted from preserved work-stash to production.
- [x] **U-LOC-002A — DONE (bounded): observer-owned last-seen Being location from supported Spot.** Does not cover general Object/Event/motion or persistent reacquisition. [design](docs/design/deferred-object-event-perception.md).
- [x] **U-SPOT-002A — DONE (bounded): native target-free discovery/selection demonstration.** Narrow candidate restrictions; general U-SPOT-002 remains open.
- [x] **U-INT-001 — DONE (bounded): local spatial/motion and derived TriFold/ISEA examples.** Not multiresolution geography.
- [x] **U-REL-001 — DONE for the approved bounded ReproductionGroup generation program (V1–V12).** Seeded parent/offspring and reverse-ancestor realization, nonempty group invariants, one-parent reproduction, partial parent membership, consistency, collision/merge and versioned checkpoints demonstrated. Historical distributions are hypotheses, **not adopted species biology**. Broader kinship remains U-REL-002.
- [x] **U-WORLD-001A — DONE (bounded): one individual conserved across genealogy, counted population, native Being, place and Encounter.** One authored Human fixture, not arbitrary world integration.
- [x] **U-WORLD-001B — DONE (bounded): independent observer can Spot that same Being.** Explicit authored target/geometry, not general unprompted discovery.
- [x] **U-REPO-001–007B — DONE for specifically verified documentation/repository repairs and sanitized historical push.** Current remote publication of newer work is separately OPEN under U-OPS-006. [Universe 7→8 handoff](docs/handoffs/universe-7-to-8.md).

### Generated Arena and NPC integration

- [x] **U-ARENA-001–005 — DONE (bounded foundation): generated local Arena, per-observer presentation, native one-second advancement, movement/facing, ground Objects, Pick up, usable action selector and preservation tests.** Individual reports remain provenance, not rows required in this state register.
- [x] **U-ARENA-006–008 — DONE (bounded): expanded Arena session and NPC profiles.** Generator source record preserved losslessly; initial equipment and ground loadout profiles; hand/armor/Object state; character details, browser controls and strict Save/Load. See the [Universe 8→9 handoff](docs/handoffs/universe-8-to-9.md).
- [x] **U-ARENA-009 — DONE: shared `npcgen.api.arena_ready_being` equipment commitment integrated.** Universe controls catalog/anatomy/policy, validates returned initial kit, creates native Objects, and loads without regeneration. Initial Dagger/armor policy remains intentionally narrow.
- [x] **U-ARENA-010, U-ARENA-011, U-ARENA-012, U-ARENA-013 — DONE (bounded): armed Swing/Thrust, hex impact reach, native actor/opponent strike and autonomous attack-only approach policy with deterministic persistence.** Browser and persistence evidence is in the linked reports; no unmodeled body geometry, pathfinding or ground-object transparency is inferred. [011](docs/reports/U-ARENA-011-report.md) · [012](docs/reports/U-ARENA-012-report.md) · [013](docs/reports/U-ARENA-013-report.md).
- [x] **U-ARENA-014 — DONE (bounded): incoming-attack-specific Dodge and defense-only opponent.** Later generalized by U-ARENA-015.
- [x] **U-ARENA-015 — DONE for supportable defenses: Block, retained Dodge, retained Parry and Yield.** Deflect and Disengage remain open due to projectile/route prerequisites. [report](docs/reports/U-ARENA-015-report.md).
- [x] **U-ARENA-016 — DONE as a partial precursor, not the original all-Actions objective.** Native Touch, armed Feint and melee Coup de grace subsets were developed. **Do not treat the original 27-offense program as finished.**
- [x] **U-ARENA-016B — DONE for the assigned connected Object-combat slice.** Native Strike an object, armed Disarm, pending-attack Break weapon; Coup browser pathway; bounded persistence and browser-selector smoke. Remaining variants are still open. [report](docs/reports/U-ARENA-016B-report.md).
- [x] **U-ARENA-017 — DONE for basic transactional Grapple integration.** Touch→Grab→individually identified Hold/maintenance→Break hold; first Grapple→Escape; individual grip release after third-party HP damage; fresh-process continuation. Advanced positions, ordinary-browser interaction and broader multi-grappler cases remain open. [report](docs/reports/U-ARENA-017-report.md).

### Preserved earlier stable task IDs

- [x] **U-ARENA-002 — DONE (bounded): initial local native Encounter Arena.** Fixed Spot submission, native one-second progression, committed inspection, and separate GM/observer projections; later generated Arena work supersedes its prototype UI. See [Encounter engine](docs/tasks/encounter-engine.md).
- [ ] **U-ARENA-003 — PARTIAL / OPEN (historical checkpoint objective):** detached/host-accepted history, quarantined inspection, and fixed trusted-local continuation were demonstrated through U-ARENA-003C3; portable receipt trust, arbitrary stochastic state, and general Encounter/Arena checkpointing were not. Current persistence work is tracked under U-PER-002.
- [x] **U-ARENA-003A, U-ARENA-003B1, U-ARENA-003B2, U-ARENA-003B3, U-ARENA-003C1, U-ARENA-003C2, U-ARENA-003C3 — DONE within their bounded historical demonstrations.** These are not claims of general checkpoint restoration; their exact limits are summarized by U-ARENA-003 and U-PER-002.
- [x] **U-THROW-001, U-THROW-002, U-THROW-003, U-THROW-004, U-THROW-005, U-THROW-006 — DONE within bounded steps.** Pure calculation and rule synchronization; blocker characterization; four-second native release/flight/landing; simultaneous native Run during flight; and observer-owned Spot evidence of an airborne Object. General ranged attack and projectile targeting remain open under U-CAP-004 and U-ACT-022. See [Encounter engine details](docs/tasks/encounter-engine.md).
- [x] **U-NPC-BEING — DONE as the original bounded import umbrella.** The later U-NPC-001 row tracks the remaining complete Generator/native compatibility gap; this historical ID does not imply complete source-field simulation.
- [x] **U-OPS-001A — DONE for its historical authorized sanitized publication.** It does not mean the current local branch is published or authorize another push; see U-OPS-006.
- [ ] **U-LOC-002B — DEFERRED / not authorized: evidence-driven follow-up Action.** Broader evidence-driven location and motion behaviors remain within U-LOC-002's open scope.

## OPEN — general world and Encounter capabilities

### World, generation, identity, groups and history

- [ ] **U-REL-002 — PARTIAL / OPEN: general kinship consistency under partial realization.** V10–V12 covered partial memberships/merge; multi-generation, causal chronology, fertility/species assumptions and richer parent/offspring dependencies remain unapproved or absent.
- [ ] **U-GRP-005 — OPEN: generalized StatisticalGroup/ObjectGroup and nested mixed membership.** Prototype population-specific constraints are not a general hierarchical Group implementation; preserve population vs reproductive vs social membership distinctions.
- [ ] **U-GRP-006 — OPEN: Agent/context-directed realization of unresolved Group members.** Must privately select consistent individuals without leaking source IDs or inventing retroactive facts.
- [ ] **U-ATT-001 — DEFERRED / high strategic importance: persistent Agent Attention.** Maintain targets/categories/Events and discoverability through time; awareness is state, maintaining it is behavior; target count/capacity and interrupted contact need design. An Action should not imply omniscient state exposure.
- [ ] **U-SPOT-002 — OPEN: general category-directed Search and discovery.** Multiple candidates, unknown target identities, observation of Objects and Events, recognition vs identification, and observer-local knowledge; narrowly completed adapters do not close it.
- [ ] **U-RULE-001 — OPEN / VERIFY: remove or reconcile provisional `ObserveGroupAction` skill/XP.** Do not confuse it with the adopted six-second Spot (no Spot XP).
- [ ] **U-LOC-002 — PARTIAL / OPEN: general Action-acquired location and motion evidence.** Last-seen Being evidence exists; waypoints/velocity/event locations, history and loss-of-contact semantics remain open.
- [ ] **U-PER-002 — PARTIAL / OPEN: general file-based Universe/Being/Encounter persistence.** Arena's strict complex Action/equipment/observer checkpointing is substantial; cross-domain mutable Groups, world realization, multiple interacting Encounters, and portable forward compatibility remain unverified. Historical checkpoint test cohorts include baseline RNG-ownership/adapter failures that must not be hidden.
- [ ] **U-UI-001 — PARTIAL / OPEN: fully observer-facing world/Encounter presentation.** Arena works for bounded play; general Belief/evidence, noncombat world inquiry, replay and authentic ordinary-browser grappling are unfinished.
- [ ] **U-ARC-001 — OPEN: historical archive inventory/interpretation.** Retain provenance, rights/privacy review and opaque formats; legacy data is not authoritative biology or safe executable code.
- [ ] **U-NPC-001 — PARTIAL / OPEN: complete generator/native Being compatibility.** `npcgen` owns initial profile/age-derived skills; Universe imports validated known fields, preserves unsupported source fields, and owns subsequent experience. Expand live mappings only when adopted native semantics exist; independent `npc-generator` is maintained separately.
- [ ] **U-NPC-002 — DEFERRED: plausible retrospective personal/skill history conditioned on a *current* NPC profile.** Do not generate developmental history first or silently change age-driven initial skill-rank policy. [design](docs/design/deferred-npc-skill-development.md).
- [ ] **U-WORLD-002 — OPEN: on-demand Encounter instantiation from world circumstances.** Forest-watch scenario: statistically coherent place, population/participants, temporally/locally consistent realization and asymmetric observer discovery, without authoring everything in advance. [design](docs/design/U-PERCEPTION-FOREST-WATCH-DESIGN-v2.md).
- [ ] **U-OBS-001 — DEFERRED: general Object/Event/movement/Action observation.** Perceptible subject, velocity and outward Action evidence, event fronts, observation timing, interrupted tracking, reacquisition; acceleration and measurement uncertainty deferred. [design](docs/design/deferred-object-event-perception.md).
- [ ] **U-OBS-002 — DEFERRED: fallible observation and epistemic uncertainty.** Interim successful perception yields accurate currently *perceptible* facts; later noise, misidentification, conflicting/combined evidence, degrees of confidence, dependent testimony and Belief revision need explicit semantics.
- [ ] **U-GEN-002 — OPEN: robust statistical→realized correlated constraint propagation.** Shared sampling and atomic constraints across scale/time/history, reproducible ordering, partial facts, delayed conditional realization, reversible failed proposals and true cross-domain integrity.
- [ ] **U-HIST-001 — DEFERRED: generated objective histories consistent with the present.** Population cohorts and migration; ancestry; injury/healing/skill histories; retrospective events constrained by later facts and known observations; distinguish complete, absent and unresolved.

### Time, physical simulation, skills, equipment, and UI

- [ ] **U-PHY-001 — PARTIAL / OPEN: full revision-4 physiological work/fatigue integration.** Q/B reserves, inheritable profiles, Fitness-as-ability and PCFS=5 exist in bounded source/workbench; actual native performed-work providers, concurrent demand, physical infeasibility, recovery and unified atomic commit remain uncompleted. No manual fatigue bookkeeping and no double penalty.
- [ ] **U-PHY-002 — PARTIAL / OPEN: complete adopted Encounter combat/force rules.** Review against current adopted rules and ES issue register, not a stale r60 checklist; cover missing Combat Actions and force/penetration/equipment interactions. See [Combat inventory](#offensive-and-defensive-combat-action-inventory).
- [ ] **U-GEO-001 — DEFERRED: multiresolution geography and environment.** Authoritative continuous Cartesian positions; derived ISEA/TriFold frames; terrain/landforms/climate/hydrology/ecology, light, obstruction, settlement, localized conservation and world-scale refinement remain broader work.
- [ ] **U-AST-001 — DEFERRED: inverse two-satellite astronomy.** Infer coherent moon orbits and apparent sizes from in-world observed periods/relative appearance; maintain stable observational constraints; design interactive viewer later.
- [ ] **U-GEN-001 — DEFERRED: interactive statistical/CDF authoring and constraint design.** Visual exploration of distributions, correlations and which attributes must be fixed given other facts, without forcing premature realization.
- [ ] **U-AGENT-001 — PARTIAL / DEFERRED: autonomy and social intelligence.** Existing bounded NPC attack/defense strategies are not goal-driven agents; open planning, learning, trust, teaching, communication, social models and testimony-based inference.
- [ ] **U-CAP-005 — OPEN: full sensory geometry and obstruction.** Body widths/regions, occlusion, eye points, obstacles, collision, line of sight, illumination and movement-path clearance; avoid inferring 3-D shapes from stature or hex markers.
- [ ] **U-CAP-006 — OPEN: advanced injury and protection.** Body sites, armor coverage, shield wear, bleeding, pain, incapacitation, long-term injury, treatment and healing history; maintain atomic injury/damage rules.
- [ ] **U-CAP-007 — OPEN: expanded characters/equipment and effect semantics.** Explicit handedness/weapon grips, dual wield, armor don/doff, weapon Object material and hardness, carried/held/worn semantics, initial kit policies; no bonus from mere generator assignment or ground placement.
- [ ] **U-CAP-008 — OPEN: larger/multiple-Encounter social combat.** More than two Beings, allies, formations, multiple simultaneous attackers, multi-grappler control, tactics, organized encounters and spatial joins.
- [ ] **U-CAP-009 — OPEN: general global simulation time/events.** One-second Encounter chronology is bounded; global world clocks, asynchronous phenomena, Event life cycles, cross-Encounter scheduling, past-state reconstruction and event-history constraints are not general.
- [ ] **U-CAP-010 — OPEN: broader Being practice, skills and learning.** General skill eligibility/progression beyond bounded native exercises, actual practice-to-ability improvement, training/teaching, changing skill rank/aptitude, cost and fatigue from performed Actions. Independent initial NPC age-based ranks remain generator-owned.
- [ ] **U-CAP-011 — OPEN: richer Arena inspection, controls, replay and accessibility.** Genuine observer-appropriate Action explanations, status of Action preparations/retained effects, keyboard/navigation, perception losses, deterministic replay, and ordinary user testing.
- [ ] **U-CAP-012 — OPEN: save/replay compatibility, schema and version migration policy.** Authenticated authoritative provenance where required, preserved file transparency, schema-validated imports and carefully bounded compatibility; avoid database/online service by default.
- [ ] **U-OPS-006 — OPEN / publication hold: publish reviewed local changes safely.** Current audit found local-path disclosures in both unpublished history and already-published history. No push until the published-history finding is resolved by explicit user direction; any rewrite remains limited to specifically authorized scope.
- [ ] **U-OPS-007 — OPEN: full-suite confidence and regression/environment triage.** Prefer focused test suites per assignment; full HTTP-inclusive suite at meaningful milestones, record legitimate environment failures, and compare to independently tested baseline. No claim of full-suite green for recent Arena work.
- [ ] **U-DOC-003 — OPEN: consolidate authoritative Encounter ES issue status.** Use *current* rule README + issue register, correct obsolete r60-only task links, and preserve unverified/blocked issues without false closure.

## Offensive and defensive Combat Action inventory

**Authority:** adopted Appendix III/IV Combat Actions (revision-61 base plus applicable later supplements). **As-of U-ARENA-018 report**. This inventory is per named Action entry and scoped variant, not a guarantee that every source-described option is playable. `U-ACT-*` IDs are state-inventory IDs; a single program can implement many. Where an Action is a condition/umbrella rather than an independent command, label that honestly.

### Appendix III — Offensive and related Actions (27)

- [x] **U-ACT-001 — Break hold — DONE bounded.** One-second Strength-only contest against a named individual physical Grip, native atomic effect; advanced interference/other grapplers open.
- [ ] **U-ACT-002 — Break weapon — PARTIAL.** One-second attempt against an opponent's actual pending strike weapon, with prior-second cancellation and same-second nonretroactivity; other weapon-use situations missing.
- [ ] **U-ACT-003 — Bull rush — OPEN.** Opposed Strength and real forced movement/occupied-route consequences.
- [ ] **U-ACT-004 — Pull — BLOCKED quantitative force/controlled displacement.** Qualitative grip/contest rules exist; do not invent Strength-to-force or kinematics.
- [ ] **U-ACT-005 — Charge — OPEN.** Integrated run-in, relative velocity, timing, interceptions and damage consequences.
- [ ] **U-ACT-006 — Coup de grace — PARTIAL.** Native helpless-target melee automatic critical and Fortitude consequence, Arena route; ranged branches absent.
- [ ] **U-ACT-007 — Delay — OPEN.** Delay/pause/commit timing semantics; elapsed time is not itself a Delay Action.
- [ ] **U-ACT-008 — Disarm — PARTIAL.** Native armed opponent-held weapon Disarm and drop in defender's hex; unarmed/locked-gauntlet and direction/landing variants missing.
- [ ] **U-ACT-009 — End run — OPEN.** Occupied-hex passage, contested speed/position and full native legality.
- [ ] **U-ACT-010 — Feint — PARTIAL.** Armed native one-use +2 follow-up; unarmed/other variants absent and forfeiture rules require coverage.
- [x] **U-ACT-011 — Grab — DONE bounded against a Being after successful Touch.** Opposed Grab check creates separately identified Grip; object-held-by-another Grab remains open.
- [ ] **U-ACT-012 — Grapple — PARTIAL.** Initial six-second Grapple, separate Grip/Hold identities, Escape and bounded Takedown/Reverse/Pin transitions are native; multi-grappler and incompatible simultaneous position outcomes, voluntary release, remaining position consequences and complete browser interaction remain open.
- [ ] **U-ACT-013 — Multiple actions — OPEN.** Shared declarations, resource/strategy allocation and extra penalties.
- [ ] **U-ACT-014 — Overrun — OPEN.** Forced movement plus prone/size constraints.
- [ ] **U-ACT-015 — Ready — PARTIAL related capability.** Native two-second Draw exists; generalized Ready/trigger conditional Action not implemented. Do not equate them.
- [ ] **U-ACT-016 — Shield bash — OPEN.** Shield attack timing/damage and off-hand capacity, despite native shield Objects and Block.
- [ ] **U-ACT-017 — Shoot — OPEN.** Native targeted ranged/missile impact/observation.
- [x] **U-ACT-018 — Strike (Swing/Thrust) — DONE bounded armed melee.** Native time, reach, observer targeting, defense, HP/practice and Arena path; exotic/multiweapon variants remain broader work.
- [ ] **U-ACT-019 — Strike an object — PARTIAL.** Native known-hardness/HP unattended immobile nonmagical ground Object; attached, attended, moving, animated, magical and unknown-material cases unsupported.
- [ ] **U-ACT-020 — Stun — OPEN.** Skill, saving throw, interruption and recoverable condition are not implemented; U-ARENA-018 did not add a Stun branch.
- [ ] **U-ACT-021 — Subdue — OPEN.** Separate subdual damage and unconscious/recovery handling are not implemented; U-ARENA-018 did not add a Subdue branch.
- [ ] **U-ACT-022 — Throw — PARTIAL narrow native ballistic Action.** Per-second object motion exists; complete target hit/miss/interception and Arena parameters absent.
- [ ] **U-ACT-023 — Touch — PARTIAL.** Native unwilling-Being one-second opposed contact, hex reach and Arena; willing/consent/Dexterity and concurrent Action branches absent.
- [ ] **U-ACT-024 — Trip — PARTIAL.** Native Touch-identity prerequisite, two-second contest, size/Grip modifiers and atomic prone result are implemented and exposed in the Arena; nullifying an already-pending later-second attack and other prerequisite sources remain open.
- [ ] **U-ACT-025 — Two-handed strike — OPEN.** Explicit hand occupancy, weapon rules and two-hand damage semantics.
- [ ] **U-ACT-026 — Undefended attack — OPEN rule integration.** Verify whether it is an attack-resolution condition rather than independent schedulable Action; no unsupported synthetic command.
- [ ] **U-ACT-027 — Wrest — OPEN.** Grab of another Being's held Object, one-second contest and native custody transfer are not implemented; U-ARENA-018 confirmed the distinct held-Object Grab prerequisite is unsupported by current Being Grab and ground Pick up.

### Appendix IV — Defensive Actions (6)

- [x] **U-ACT-028 — Block — DONE bounded.** Held shield, size-dependent preparation and native protection; ordinary Arena eligibility constraints apply.
- [ ] **U-ACT-029 — Deflect — OPEN.** Requires projectile impact/miss tracking, interception and continuous observation.
- [ ] **U-ACT-030 — Disengage — OPEN.** Requires contested withdrawal, occupied-hex route clearance and true movement semantics.
- [x] **U-ACT-031 — Dodge — DONE bounded.** Native two-second prepared, retained, strike-specific commit; Multiple actions required for multiple defenses.
- [x] **U-ACT-032 — Parry — DONE bounded.** Native weapon-dependent preparation, eligibility and retained commit; multi-weapon variants depend on Multiple actions.
- [x] **U-ACT-033 — Yield — DONE bounded.** One-second backward movement and relevant attack penalty.

### Other named Actions and choices requiring explicit distinction

- [x] **U-ACT-034 — Pick up — DONE bounded.** Native one-second same-hex ground Object acquisition; does not ready/equip it.
- [x] **U-ACT-035 — Draw weapon — DONE bounded.** Two-second native draw for represented custody/hand/location prerequisites.
- [x] **U-ACT-036 — Run Action — DONE bounded.** Native `RunAction` for associated task/skill; distinct from continuous walk/jog/run/sprint **movement intention**.
- [x] **U-ACT-037 — Deliberate Spot — DONE bounded native, Arena availability contextual.** Six-second native observer discovery, separate from initial unobstructed automatic Arena perception.
- [ ] **U-ACT-038 — Listen — VERIFY native Arena availability.** Adopted perception Action; current generated Arena does not have independently established full sound/target contract.
- [ ] **U-ACT-039 — Remaining configured Action catalog — VERIFY.** `src/config/actions.tsv` previously contained 53 labels; a catalog label is not evidence of a supported transactional resolver. Audit executable variants without treating all labels as missing code or implementation.

## IDEAS — retained possibilities, not authorized work

**Everything below is intentionally within this single `TASKS.md`.** These are stable, specific ideas recovered from the earlier deferred-ideas register, handoffs, design notes, and Universe discussions. An idea can be explored without changing its status to ACTIVE, and accepted mechanics must still be adopted explicitly. Cross-references show relevant broader open work; they do not declare that any proposed algorithm or scientific model has been approved.

### Resolution on demand, causality, history and configuration

- [ ] **U-IDEA-001 — IDEA: builder-and-discoverer interaction.** World detail becomes realized as inquiry/actions genuinely require it, preserving undiscovered possibilities instead of filling the world in advance. Related U-GEN-002, U-AGENT-001.
- [ ] **U-IDEA-002 — IDEA: statistical-to-realized refinement across multiple domains.** Connect composition, geography, chronology, biology and social history with minimum commitments and shared conditional constraints.
- [ ] **U-IDEA-003 — IDEA: coarse/fine consistency and correlated sampling.** Fixed aggregate counts, joint distributions, and earlier/later observations constrain samples without freezing unnecessary details. Related U-GEN-001/002.
- [ ] **U-IDEA-004 — IDEA: retrospective event generation and temporal causal closure.** Newly generated history agrees with known future consequences, no impossible biographies or rewritten committed facts. Related U-HIST-001.
- [ ] **U-IDEA-005 — IDEA: original versus current cohorts.** Population at formation differs from later membership; conservation and migration history need not equate current people with the original quota.
- [ ] **U-IDEA-006 — IDEA: multi-scale event causation and world clocks.** Long-running phenomena, past/future state constraints and concurrent Events, without forcing Encounter's one-second frame onto every world phenomenon.
- [ ] **U-IDEA-007 — IDEA: derived facts and partial-query answers without needless realization.** Return what constraints establish (including counts/ranges) without materializing every constituent individual.
- [ ] **U-IDEA-008 — IDEA: reproducible keyed sampling with stable consumption/order.** Insertion order, observer choice and aborted proposals must not accidentally change already committed realizations.
- [ ] **U-IDEA-009 — IDEA: visual interactive constraint/distribution explorer.** CDFs, distributions and correlations, alternatives and effect of changing assumptions; distinguish designer knowledge from in-world evidence. Related U-GEN-001.
- [ ] **U-IDEA-010 — IDEA: configurable minimum-known-facts solver.** Identify which free variables must be committed for a requested outcome and leave the rest statistical.

### Planet, geography, ecology, populations

- [ ] **U-IDEA-011 — IDEA: inverse two-moon worldbuilding from observed evidence.** Residents know two periods and relative angular sizes; infer compatible orbits, planet constraints, and uncertainties rather than specifying all orbital parameters. Related U-AST-001.
- [ ] **U-IDEA-012 — IDEA: broader astronomy and planetary properties.** Stellar illumination, seasons, tides, calendar and sky appearances integrated with inhabited places and events.
- [ ] **U-IDEA-013 — IDEA: ISEA/TriFold planetary subdivision with local physical detail.** Derived map frames and continuous coordinates, consistent refinement and scale-dependent terrain generation.
- [ ] **U-IDEA-014 — IDEA: watershed-first terrain and hydrology.** Rivers/drainage/landform constraints coherent from global to local scales, not a decorative map.
- [ ] **U-IDEA-015 — IDEA: climate, weather, light and atmospheric processes.** Environment constrains movement, hearing, visibility, survival, populations and time-dependent events.
- [ ] **U-IDEA-016 — IDEA: ecology, species range and evolution.** Organisms, habitats and ecological constraints inform statistical population distributions and encounters.
- [ ] **U-IDEA-051 — IDEA: inherited molecular sequence, taxon traits and phylogenetic history.** Explore a simplified, reproducible heritable-sequence→trait model that is consistent with lineage/environment history and resolves on demand. This is distinct detail within (but not a duplicate of) broad ecology/evolution; no biology, genome model or `npcgen` behavior is adopted. Source intake: [IDEA-SUB-20261111-001](docs/ideas/processed/IDEA-20261111-biota-molecular-phylogeny.md).
- [ ] **U-IDEA-017 — IDEA: settlement, economics and civilization formation.** Labor, resources, travel, exchange, institutions and demographic history consistent with geography/environment.
- [ ] **U-IDEA-018 — IDEA: local obstruction and detailed collision.** Terrain, dense objects, visibility, articulated bodies and occupied space should be resolved only to the fidelity demanded.
- [ ] **U-IDEA-019 — IDEA: physically coherent trajectories.** Position/velocity history, acceleration where demanded, throwing and projectile arc, impacts and continuous interpolation with the committed one-second record.
- [ ] **U-IDEA-020 — IDEA: movement/locomotion tied to real physical work.** Distinguish displacement, facing, effort, capability, fatigue, terrain and balance without manual accounting.

### Groups, kinship and personal history

- [ ] **U-IDEA-021 — IDEA: nested and overlapping statistical/social Groups.** Parent-child membership hierarchies, mixed Being/Object members and multiple affiliations; avoid conflating statistical population with residence or kinship.
- [ ] **U-IDEA-022 — IDEA: unresolved-member births, deaths, migrations and turnover.** Update population totals and history without prematurely assigning identities.
- [ ] **U-IDEA-023 — IDEA: social/cultural versus reproductive relationships.** ReproductionGroup exactly denotes reproductive parent set/offspring; household, adoption, partnership, kinship interpretation and affiliations are independently modeled.
- [ ] **U-IDEA-024 — IDEA: historical ancestry/descendency under partial identity.** Generate from a child or parent, support one or variable parent cardinality, known absence vs unresolved lineage and nonduplicated parent sets.
- [ ] **U-IDEA-025 — IDEA: populations of different life stages and types.** Children, livestock, pets, multi-species/groups, diverse habitats and nonhuman physiological assumptions.
- [ ] **U-IDEA-026 — IDEA: collective Group movement and member detachment.** Group centers, footprint, member separation, density, co-moving subgroups and independent personal routes.
- [ ] **U-IDEA-027 — IDEA: aging, fertility, injury, healing and death as history.** Conditional generation of whole lives with biological constraints, not fixed dates invented without demand.
- [ ] **U-IDEA-028 — IDEA: NPC development narratives consistent with present state.** Generate a plausible past *after* age, attributes and current skill profile are fixed, not as the authority for those ranks. Related U-NPC-002.
- [ ] **U-IDEA-029 — IDEA: skills gained through actual experience and teaching.** Trainable abilities vs skills, practice, skill transfer, trainer-student Actions and future aptitudes without retconning current native state.
- [ ] **U-IDEA-030 — IDEA: contextual NPC character editing and inspectable generated source.** Explore compatible class/age/skills/equipment consequences in a designer before accepting the initial Being.

### Perception, Belief, social systems and autonomous Agents

- [ ] **U-IDEA-031 — IDEA: Attention as persistent limited action/state pair.** Attend to known individuals, categories, unknown phenomena or Events; capacity and distraction determine continuing contact, not an automatic discovery guarantee.
- [ ] **U-IDEA-032 — IDEA: tracking interrupted by concealment.** Preserve last observation and subsequent uncertainty; reappearance requires new contact and may not establish same identity automatically.
- [ ] **U-IDEA-033 — IDEA: perceived Actions and Events without leaking intentions.** An Agent observes outward activity/velocity while private scheduler states/targets remain hidden.
- [ ] **U-IDEA-034 — IDEA: calibrated fallible perception and dependent evidence.** Noise, misclassification, correlated information, interpretation, memory, confidence, revisions and contradictory witnesses when adopted; current exact-perceptible simplification remains until replaced.
- [ ] **U-IDEA-035 — IDEA: testimony, trust and independent verification.** Agents may observe conflicting accounts, check historical evidence, learn reliability, be mistaken or deliberately deceive; claims are not Reality.
- [ ] **U-IDEA-036 — IDEA: knowledge transfer and teaching.** Communication, shared evidence provenance, intentional persuasion, language, skill teaching and lasting effects on Belief and experience.
- [ ] **U-IDEA-037 — IDEA: emergent culture, tradition, myth and religion.** Social narratives, institutions and collective memory spread and change through testimony and experience.
- [ ] **U-IDEA-038 — IDEA: goal-directed Agent planning and exploration.** Decisions driven by subjective knowledge and preferences, environmental demands and consequences; no privileged omniscient policy inputs.
- [ ] **U-IDEA-039 — IDEA: autonomous attention/inquiry causing new world realization.** An Agent's legitimate interest triggers world-private constraint-satisfying detail generation, and only then observation if perceptible.
- [ ] **U-IDEA-040 — IDEA: uncertain historical and spatial waypoints.** Last-seen locations, motion hypotheses, map-making, path choices, search and loss/reacquisition, without live-world leaks.

### Combat, physiology, interaction, interface and provenance

- [ ] **U-IDEA-041 — IDEA: physically calibrated Strength/force model.** Force, leverage, friction, lifting, Pull and coordinated opponents grounded in an explicit rule/scientific choice instead of guessed Strength-to-newtons conversion.
- [ ] **U-IDEA-042 — IDEA: articulated bodies, reach envelopes and weapon arcs.** Stature/weight in inches/pounds; detailed anatomy resolved on demand; collision, minimum distance, orientation and posture where it matters.
- [ ] **U-IDEA-043 — IDEA: fatigue as automatically integrated physical work.** Q/B physiological reserves, recoveries and exercise overlap; no separate manual score bookkeeping and no double fatigue penalties.
- [ ] **U-IDEA-044 — IDEA: localized wounds and longer-term medical consequences.** Impact region, layered protection, incapacitation, pain/bleeding, treatment, scars and healing over world time.
- [ ] **U-IDEA-045 — IDEA: larger tactical encounters with multiple Beings.** Formation, flanking, multi-target defense, group autonomy, nearby neutral Entities, supplies and environmental consequences.
- [ ] **U-IDEA-046 — IDEA: player-facing continuous world inquiry interface.** Hex Arena is a vertical slice; future inspectable spatial/temporal exploration, map history, belief views, authoring tools and save/load of a world.
- [ ] **U-IDEA-047 — IDEA: general replay/diagnostics without observer leaks.** Developer-omniscient trace separate from a player's perceived record; reproducible choices, receipts, source versions and lawful replay across sessions.
- [ ] **U-IDEA-048 — IDEA: alternative deployment/persistence architecture only when justified.** Inspectable file artifacts presently preferred; database, distributed services and generalized persistence stacks should respond to genuine requirements, not be introduced prematurely.
- [ ] **U-IDEA-049 — IDEA: conservation across Realization, encounter and NPC generation.** Same logical Being and stable physical Object remain themselves across generated family, population, spatial region, perception, gameplay, history and save/resume.
- [ ] **U-IDEA-050 — IDEA: interactive world configuration that explains consequences.** Visual/scenario designer teaches what assumptions constrain the generated Universe, including incomplete specification and reversible previews, before committing facts.

## Governing implementation principles (brief index)

- **Adopted decisions outrank prototypes and prior reports.** See [Encounter README](docs/encounters/README.md). Design documents and `U-IDEA-*` items do not independently enact rules.
- **Resolution on demand; Reality / Observation / Belief separation; identity and aggregate conservation; deterministic RNG; atomic validation/publication/rollback; one-second Encounter chronology.** Preserve these invariants across domains and Action families.
- **Current state ≠ historical source.** `npcgen` supplies starting Being/profile; native Universe owns subsequent changes. Generator-chosen ground Objects confer no equipment effects until legitimately possessed/readied/equipped. Load never regenerates.
- **Observer view is evidence-bounded.** Never leak hidden identities/private Actions/Generator data to an Agent or player. Interim successful Spot/Listen gives accurate information about *perceptible* properties, not everything stored.
- **Engineering evidence matters.** Separate native test, HTTP/UI harness, live browser walkthrough and full-suite results; protect working native paths, source/IDs and strict checkpoints. Preserve early implementations by reusing/adapting them when compatible, without calling legacy sequential resolvers from transactional encounters.
- **File-based inspectability, small coherent commits, focused validation.** Preserve unrelated dirty files and independent repositories; never push or rewrite history without explicit authorization. Source of truth for implementation is actual code + tests; this document is the current navigational state and work priority.
- **Each Codex assignment explicitly states the `TASKS.md` rows to inspect/update; each report enumerates exact changes and verification.** Update the root register in the same meaningful capability commit rather than asking the user to merge status manually. [Process contract](docs/DEVELOPMENT-PROCESS.md).

## References and document roles

- **Only live consolidated state/idea register:** this `TASKS.md`.
- **Normative adopted Encounter rules/issues:** `docs/encounters/README.md` and linked rulebook/issue files (verify current revision and precedence).
- **Workflow and continuity contract:** `docs/DEVELOPMENT-PROCESS.md`.
- **Implementation details and evidence:** `docs/assignments/<ID>.md`, `docs/reports/<ID>-report.md`, Git commits/source/tests; `docs/tasks/` and `docs/design/` explain topics but **do not maintain competing canonical status lists**.
- **Historical material:** `docs/design/deferred-ideas.md`, earlier consolidated backlogs and dated handoffs are source material **incorporated into this file**, not a second current ideas register. Do not delete or rewrite them merely to avoid duplication; mark them archival/reference only during verified repository adoption.
- **Explicit limit:** This reconciliation incorporates accessible earlier idea records and reports, but cannot certify completeness of any deleted/inaccessible conversation or unreviewed local file. `U-DOC-002` keeps that gap visible and actionable.
