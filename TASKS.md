# Universe — Task Register

> Adopted 2026-11-01 from the 5E3I seed after reconciliation with the live
> repository. Keep this index compact; topic files hold scope and acceptance
> detail. A completed checkbox means only the bounded deliverable stated here.

## ACTIVE — one development objective

- [ ] **U-REL-001 · ACTIVE — Design and test a bounded family-relationship generation-on-demand experiment.** The D1 source audit is complete; no family rules or implementation are adopted. Obtain decisions on relationship semantics, chronology, identity, and generation scope before the smallest world-only proof. See [generation and Attention](docs/tasks/generation-and-attention.md).

## NEXT

- [ ] **U-REL-002 · PLANNED — Test kinship consistency under partial realization.** Select a second small scenario only after U-REL-001 yields approved rules and a passing first example. See [generation and Attention](docs/tasks/generation-and-attention.md).

## DONE — bounded, demonstrated milestones

- [x] **U-OPS-001 — Commit the tested Encounter CORE baseline (5E3A).** Commit `e169660c2b39e028b2bba337a35fde1bc22acd13`, 83 paths, tree `31a08dc6036a6a127d7506ea9cc3603c3338fcea`; its isolated candidate passed 1,573 HTTP-inclusive and 400 focused tests. See [workflow](docs/tasks/repository-workflow.md).
- [x] **U-OPS-002 — Complete repository cleanup and historical archiving (5E3B–5E3H).** Verified private recovery archives, grouped historical evidence, portable index, adopted-r60 sources and four preserved local-data files. 5E3H commit: `379219223686d841fdff70702cd43a45423b8758`. See [workflow](docs/tasks/repository-workflow.md) and the [archive index](docs/historical-evidence-archive-index.md).
- [x] **U-OPS-003 — Preserve interrupted work separately (5E3F).** Commit `03c5e9a874c88ac21686b0c0da58d24a736a4cd4` contains the tracked `work-stash/`; 78 snapshots were checksum-verified. Not pushed. See [work-stash](work-stash/README.md).
- [x] **U-OPS-004 — Install this task register and five topic files (5E3I).** Completed by the commit that adds this register; the commit is identifiable by this report and subject `Establish Universe task register and development roadmap` (self-hash is intentionally not embedded). See [workflow](docs/tasks/repository-workflow.md).
- [x] **U-OPS-005 — Audit and independently verify the CORE candidate (5E2V–5E2Z / 5E3A).** The 83-path CORE candidate passed in a clean export before the exact candidate was committed. See [workflow](docs/tasks/repository-workflow.md).
- [x] **U-OPS-006 — Publish sanitized local history to the intended GitHub repository (5E3J–5E3K).** The normal fast-forward push was independently verified; current `main` and its `origin/main` tracking ref both identify `a22c284909d7f64c14cad919518f9da319bcf1ed`. This does not back up private `ARCHIVE_ROOT` material. See [repository workflow](docs/tasks/repository-workflow.md).
- [x] **U-ENG-001 — Native one-second transactional Encounter progression for supported cases.** Boundary coordination, common post-movement snapshots, candidate evaluation, atomic publication, rollback and deterministic RNG handling are implemented for the supported native subset. This does not prove every combat combination. See [Encounter engine](docs/tasks/encounter-engine.md).
- [x] **U-PER-001 — Bounded fresh-process Run continuation (5E1J6).** One imported historical Run boundary plus one new Run boundary; imported practice is not replayed and the new interval gets a native receipt. This Run-only case consumes no RNG and does not establish stochastic replay or general save/load. See [Encounter engine](docs/tasks/encounter-engine.md).
- [x] **U-SPOT-001 — Rule-correct deliberate Spot (5E1J1).** Six-second Action, target discovery DC (15 by default), one check and no Spot skill XP. This does not establish category-directed sensing. See [Encounter engine](docs/tasks/encounter-engine.md).
- [x] **U-GRP-001 — Exact aggregate Group evidence under the interim observation rule (5E2C).** A successful supported Spot records exact aggregate evidence only for that observer; no hidden individual identity or coordinate disclosure. See [generation and Attention](docs/tasks/generation-and-attention.md).
- [x] **U-GRP-002 — Trusted atomic realization of one already-counted adult (5E2G–5E2I).** Detached candidate, optional explicit geometry, stable identity, conserved Group count, next-boundary eligibility and rollback. Realization alone grants no Awareness. See [generation and Attention](docs/tasks/generation-and-attention.md).
- [x] **U-GRP-003 — Narrow identity-free Spot adapter (5E2S).** The adapter accepts only a unique eligible unfamiliar participating Being; it is not the general Spot or Attention specification. See [generation and Attention](docs/tasks/generation-and-attention.md).
- [x] **U-GRP-004 — Integrated Group observation, independent realization, discovery and Thrust example (5E2U).** The bounded example records Group count 28, independently realizes one counted adult, later discovers that Being, and resolves Thrust for 4 damage and 10 Dagger XP. Group obstruction classification was corrected in 5E2M. Agent interest does not yet select an unresolved member. See [generation and Attention](docs/tasks/generation-and-attention.md).
- [x] **U-LOC-001 — Initial waypoint belief and landmark counterfactual experiment (5E1F–5E1G).** Demonstrated in interrupted work, not part of the committed CORE implementation; snapshots remain under `work-stash/`. See [generation and Attention](docs/tasks/generation-and-attention.md).
- [x] **U-INT-001 — Narrow spatial Encounter and motion demonstrations.** Continuous position, derived TriFold context and simple Run movement are demonstrated in bounded examples; this is not global geography or terrain integration. See [broader Universe roadmap](docs/tasks/broader-universe.md).

## OPEN — capabilities requiring follow-up

- [ ] **U-ARC-001 — Decode selected historical formats and establish provenance/rights before reuse.** The static assessment is available, but opaque NPC/session formats, data provenance, and licensing were not resolved; legacy material remains untrusted reference only. See [generation and Attention](docs/tasks/generation-and-attention.md) and the [historical archive index](docs/historical-evidence-archive-index.md).

- [ ] **U-GRP-005 — Generalize Group semantics beyond the population prototype.** `StatisticalGroup` may remain an `ObjectInstance` subtype; mixed-object `ObjectGroup` semantics and a rename are separate decisions. See [generation and Attention](docs/tasks/generation-and-attention.md).
- [ ] **U-GRP-006 — Agent-interest-triggered private selection of unresolved members.** Aggregate Belief does not provide a hidden member ID. Define authority, selection, timing and observer-information rules first. See [generation and Attention](docs/tasks/generation-and-attention.md).
- [ ] **U-ATT-001 · DEFERRED, strategic priority — Persistent mutable Attention.** Define whether Agents attend to categories, known entities, Groups or happenings. Events (such as moonrise) remain a distinct ontology from Objects. Attention is not guaranteed discovery. See [generation and Attention](docs/tasks/generation-and-attention.md).
- [ ] **U-SPOT-002 — Category-directed discovery and Search.** Current native Spot is target-directed; candidate selection, multiple matches and broader Search semantics remain unapproved. See [Encounter engine](docs/tasks/encounter-engine.md).
- [ ] **U-PER-002 — General file-based save/load and deterministic continuation.** Extend beyond the bounded Run-only demonstration to mixed Actions, observers, stochastic state and broader Universe data. See [Encounter engine](docs/tasks/encounter-engine.md).
- [ ] **U-RULE-001 — Resolve or retire provisional `ObserveGroupAction` skill/XP behavior.** The experimental Group sampler is not the adopted six-second Spot rule. Do not infer sensing mechanics from the prototype. See [Encounter engine](docs/tasks/encounter-engine.md).
- [ ] **U-LOC-002 — Action-acquired location evidence.** Define a supported observer-owned location/evidence effect before adding waypoints derived from sensed Objects. See [broader Universe roadmap](docs/tasks/broader-universe.md).
- [ ] **U-UI-001 — Observer-facing Encounter presentation.** Adapt inspection to individual knowledge and committed effects; developer-omniscient traces are not player perception. See [broader Universe roadmap](docs/tasks/broader-universe.md).

## DEFERRED — strategic roadmap

- [ ] **U-PHY-001 — Integrate revision-4 physiology/fatigue.** Reconcile Q/B state, PCFS=5, recovery and simultaneous physical work. Experimental workbench remains separate. See [Encounter engine](docs/tasks/encounter-engine.md) and [work-stash status](work-stash/universe-fatigue-r4/STATUS.md).
- [ ] **U-PHY-002 — Verify broader combat and force rules.** Continue the open revision-60 issue register; do not treat the task bridge as rule authority. See [the r60 issue bridge](docs/tasks/encounters-r60-open-issues.md).
- [ ] **U-GEO-001 — Multiresolution geography and environment.** Integrate terrain, climate, hydrology, ecology and local refinement against established objective constraints. See [broader Universe roadmap](docs/tasks/broader-universe.md).
- [ ] **U-AST-001 — Infer a two-satellite system from observations.** Build coherent orbit parameters from in-world periods and apparent sizes. See [broader Universe roadmap](docs/tasks/broader-universe.md).
- [ ] **U-GEN-001 — Interactive statistical/CDF design and constraint propagation.** Explore correlated attributes while preserving minimum commitments and reproducibility. See [broader Universe roadmap](docs/tasks/broader-universe.md).
- [ ] **U-AGENT-001 — Broader Agent autonomy and social knowledge.** Develop goals, planning, communication and histories from observer-owned evidence rather than omniscience. See [broader Universe roadmap](docs/tasks/broader-universe.md).

## Revision-60 issue status

The live adopted register and generated queue are authoritative. The seed claimed 20 outstanding issues and included ES-053, but **ES-053 is absent** from both current authoritative files; the generated queue contains 19 entries. The topic bridge preserves all 19 actual open/deferred entries and records this discrepancy without inventing an issue. See [the issue bridge](docs/tasks/encounters-r60-open-issues.md).

## Evidence hierarchy

1. [Adopted r60 rules and issue register](docs/encounters_adopted_r60/README.md) are normative.
2. Current Git source and tests define implemented behavior; a bounded fixture is not a general guarantee.
3. [The historical archive index](docs/historical-evidence-archive-index.md) locates old evidence; private archive files are not GitHub backups.
4. [The tracked work-stash](work-stash/README.md) preserves unfinished work and does not certify it as production.
5. Topic task documents provide acceptance detail and links.
