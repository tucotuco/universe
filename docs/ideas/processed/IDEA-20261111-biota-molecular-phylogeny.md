# Idea intake — Evolutionary biota, abstract molecular sequences, and phylogenetic taxon traits

**Intake ID:** `IDEA-SUB-20261111-001`
**Archived repository path:** `docs/ideas/processed/IDEA-20261111-biota-molecular-phylogeny.md`
**Submitted:** 2026-11-11
**Origin:** Universe user discussion
**Intake status:** PROCESSED — registered in `TASKS.md` as U-IDEA-051; retained here as detail/provenance, not a second task list or adopted rule.
**Proposed type:** IDEA (future worldbuilding / evolutionary biology).
**Likely related entries:** `U-IDEA-016` (ecology, species ranges and evolution); `U-IDEA-002` (cross-domain statistical-to-realized refinement); `U-GEO-001` (planet/environment); `U-GEN-001` (conditional generation); `U-GRP-005` (populations); `U-IDEA-025` (multispecies populations).
**Register ID:** `U-IDEA-051` (assigned during the U-DOC-001 reconciliation after checking existing IDs and related concepts).

## User's proposal (faithful statement)

> Establish a simplified biota Molecular Sequence mechanism that determines taxon traits and can be expressed in phylogenetic trees, enabling on-demand Being generation consistent with a planet's evolutionary history.

## Why it belongs in Universe

Rather than generating each species or Being's traits independently, a world could generate organisms from **shared, inherited evolutionary constraints**. Organisms in related taxa would tend to have coherent shared characters because of common ancestry; trait differences could be explained by sequence changes and lineage history. The planet's known environments and evolutionary timescales would constrain which biota can plausibly exist at a given place and time. The user wants a tractable *simplified* mechanism, not necessarily a full biological/genomic simulator.

## Candidate conceptual architecture — questions to explore, not adopted rules

1. **Abstract heritable molecular sequence.** Define a compact inherited sequence, loci, modules, or symbols per ancestral lineage. It may be stylized rather than literal nucleotide data. The amount of molecular detail is resolved only when a trait, relationship, or historical query demands it.
2. **Sequence-to-trait expression.** A versioned, reproducible interpretation maps sequence variants (and, when relevant, interactions and environment) to taxon-level traits: body plan, physiology, reproduction, sensory capabilities, growth patterns, ecological tolerances, etc. Distinguish inherited potential from environmentally conditioned expression and individual variation. Do not assume a single gene independently controls each trait.
3. **Phylogenetic inheritance.** Taxa occupy a branching lineage structure with common ancestors; descendants inherit compatible ancestral features and accumulate differences. A tree can expose relationships and character evolution without materializing every organism or ancestral sequence. If hybridization/horizontal transfer is ever desired, recognize that a tree is a simplifying assumption and phylogenetic networks may be a later extension.
4. **Planetary evolutionary context.** Lineage divergence and trait distributions should be consistent with known geological/environmental chronology, habitats, migration, extinction, and speciation events—without inventing arbitrary planetary facts prematurely.
5. **Resolution on demand.** Begin with coarse taxon/lineage/statistical constraints. When a Being is requested, realize its taxon, compatible inherited traits, individual variation, and any necessary lineage facts deterministically. Preserve existing committed Beings, taxa, population aggregates, and observations when later refining the evolutionary tree or molecular representation.
6. **Evidence and uncertainty.** An investigator's fossil, anatomical, or molecular observations and inferred taxonomy/phylogeny must remain distinct from objective evolutionary history. Do not reveal a complete true tree automatically to in-world observers.

## Illustrative future demonstration (NOT authorized now)

A small fictional planet has two related terrestrial taxa and one ancestral lineage, with an established environmental transition. A seeded lineage/sequence sketch yields shared ancestral characters plus a reproducible derived trait in one branch. Generate one Being from each taxon; both have traits consistent with the tree, the sequence-to-trait mapping and the planet's known history. A later inquiry resolves another ancestral trait without changing the already generated Beings or contradicting environmental constraints. Show an observer-facing inferred tree separately from objective lineage facts. This is a *possible* first experiment, not a required engineering assignment.

## Open design decisions to defer

- How symbolic versus literal is the Molecular Sequence, and what relationship does it have to physical genetics? Is the model intended for Earth-like biology, arbitrary alien biochemistry, or both?
- What are the minimal trait ontology, inheritance/mutation rates, branching-time model and environmental-expression contracts? How is correlated inheritance represented efficiently?
- Are species/taxa objective lineages, human/Agent classifications, or both? What does a tree represent when taxonomic beliefs differ from objective genealogy?
- How can a partial phylogenetic tree be extended under known extinct taxa/fossils, observed traits, biogeography and already-realized Beings without incoherent retroactive changes?
- How should this integrate with NPC Generator initial traits and Universe's live Being, and which project owns the source taxon/sequence generation?

## Intake processing record

This file is **an idea submission, not an instruction to implement** evolutionary biology or change `npcgen`, Encounter rules, or live code.

The U-DOC-001 reconciliation compared this proposal with U-IDEA-016 (broad ecology/evolution) and U-IDEA-002/003 (cross-domain refinement/correlated sampling). It retained the specific inherited molecular-sequence → trait → phylogeny → planetary-history concept as a separate IDEA, U-IDEA-051. The entry remains speculative and unauthorized; no design, biological rule, or `npcgen` behavior has been adopted. This note was moved from `ideas/inbox/` after the TASKS.md registration was staged and validated. Other inbox files are unaffected.
