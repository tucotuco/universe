# Deferred development — NPC generator skills and skill development

**Status:** Deferred Universe integration capability; suitable for parallel work in the independent NPC generator after a separate scope decision. **Date:** 2026-11-04.

**Tracking:** The deferred concept is retained in the existing U-NPC-002 row in `TASKS.md`; the older integration roadmap is archived at `docs/design/archive/universe-playground-integration-roadmap.md`. Allocate a new task identifier only after checking the live registry for collisions. This note does **not** adopt new mechanics or authorize an implementation.

## Why this matters

The P0 reconnaissance (`universe-playground-p0-assessment.md`) found that the existing versioned `npcgen-npc` candidate export includes class/level/XP, six scores, and other developed character data, **but not a verified, discrete Universe-compatible skill list**. Universe has native skills and practice and an adopted revision-60 Encounter ruleset. An interactive Encounter Arena eventually needs a principled way to import developed NPC capabilities and, later, to represent changes caused by genuine simulation experience.

## Two independent development tracks

1. **NPC-generator track (potentially parallel):** Investigate rule sources and current candidate models; design and eventually implement structured skill generation, representation, display, editing and versioned export. This track can deliver meaningful results without changing Universe's Encounter engine. Do not silently infer a skill from class, level, or unstructured narrative.
2. **Universe / Encounter Arena track:** Initially import the full NPC source record losslessly as provenance and display unsupported fields as non-operational data. After separate review, map approved skills to native abilities/skills/practice and demonstrate their use by supported native Actions. Universe owns simulation consequences and subsequent experience, not the generator's source profile.

## Design questions to settle before skill mechanics

- What is the authoritative definition/identifier of each skill, its governing ability (if any), eligibility, initialization, proficiency/level and experience progression? How will definition/rule versions be recorded?
- Which candidate characteristics may influence initial skill acquisition? What historical assumptions about occupation, age, training, class or experience are appropriate? Do not mistake NPC-generator classes or XP for Universe's skill/practice rules.
- How are *skills*, *trainable abilities* (notably Fitness), *ordinary checks*, and *discovery Actions* (including deliberate Spot, Search and Listen) distinguished? The revision-60 rules and later decisions take precedence over legacy/provisional models.
- What information belongs in a generated starting profile versus an earned history of practice/events? How will user edits and provenance be preserved?
- How are version compatibility, unknown fields, invalid IDs, legacy exports, and round-trip fidelity handled? What is explicitly display-only until Universe mappings are validated?
- If Arena sessions later change skills, how is the authoritative result exposed back to a character editor without overwriting source-provenance or creating two competing owners of the same state?

## Suggested independently useful milestones (not yet assigned)

1. **NPC-S1 — Contract and rule alignment:** Audit current NPC generator schema/engine and Universe r60 skills, abilities and experience semantics. Propose a minimal versioned structured skill model, migration/backward-compatibility rules and sample fixture. Ask for approval of disputed rules.
2. **NPC-S2 — Generator demonstration:** Once approved, produce at least one seeded NPC with structured skills and explicit provenance, editable/exportable/reimportable with deterministic tests, without altering Universe gameplay.
3. **Arena-S3 — Approved native mapping:** In a separate Universe task, map one verified supported skill into a native Being, exercise the relevant existing Action, and verify history/persistence behavior. Keep unsupported values opaque and distinguish source data from authoritative state.

## Coordination and repository safety

- Keep the independent `npc-generator-web/` project separate from Universe simulation modifications. The P0 report found it nested and untracked, with no verified independent Git revision: verify its version-control arrangement before making parallel edits, and do not silently move or commit it into the Universe repository.
- Work in a separate NPC-generator chat/workspace if convenient; do not let the NPC track alter `src/` Encounter mechanics or `TASKS.md` concurrently with the Universe track. Transfer reviewed interface contracts and sample exports between tracks instead of sharing uncommitted code mutations.
- Retain complete `npcgen-npc` provenance; a source digest is a revision identity, not a native Being identifier.
- No adopted NPC-generator rule automatically becomes a Universe rule. No new skill progression, class, XP, or historical generation policy is adopted by this deferred note.

## Acceptance boundary for the deferred entry

This planning task is recorded when `TASKS.md` and the relevant topic/roadmap files link to this document, identify the NPC-generator skill track as **deferred / parallel-capable**, and preserve the current limited Arena's authority and import restrictions. Skill implementation remains separately authorized.
