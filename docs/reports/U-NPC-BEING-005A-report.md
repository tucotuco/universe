# U-NPC-BEING-005A — Native customary physical units and NPC measurements

**Status:** completed within the bounded assignment scope.
**Binding policy:** `docs/assignments/U-NPC-BEING-005A-28-inch-reach.md` (the requested alias `U-NPC-BEING-005A.md` was absent; this supplied 28-inch policy file explicitly supersedes earlier 005A drafts).
**No push.**

## Changes

- Established near `BeingDefinition` that native Being stature/length is inches and body weight is pounds. `src/config/beings.tsv` now names the field `length_inches`; its 27 prior feet-valued stature entries were converted by 12 (Human 5.75 ft → 69 in). Weight entries were retained in pounds. The loader accepts the explicit schema name.
- Documented that `WeaponDefinition` stores length in inches and weight in pounds. `WeaponDictionary.load()` converts the source weapon table's feet-valued length to inches at the loader boundary; the source table remains unchanged (Dagger 1.25 ft → 15 in, Aklys 2 ft → 24 in). `ObjectInstance.set_geometry()` now clarifies that native physical dimensions do not create world-space geometry.
- Extended the fixture-only NPC adapter to require finite, positive numeric `state.height`/`state.weight`, reject booleans, absent/null/invalid values and incompatible explicit unit annotations, and cross-check against the fixture's two-decimal `sheet.age.height_inches` / `weight_pounds` projections. It imports those values directly to native `BeingDefinition.length` / `weight`. Fixture bytes and SHA-256 remain unchanged: `e59b55a6c22f822d65716215b64bccf0c1f2c7a42d49036092580d7c470241ae`.
- The terminal and browser developer views label source and native stature in inches, body weight in pounds, positions in yards, and authored collision geometry in meters. The NPC still receives the Arena-authored `Sphere(0.5)` and Arena-supplied Dagger; importing physical measurements does not infer geometry. The opponent and its scenario values, HP, AC, position and geometry remain unchanged.
- Updated bounded `AgentDuel` Reach: measured personal reference arm length is `(15/37) × max(height,length)` inches; a pure helper accepts an explicit known size category and implements the adopted estimates D=3.5, T=7, S=14, M=28, L=56, H=112, G=224, C=448 inches when no positive measurement exists. The current AgentDuel Human has a measured length and does not infer category from the existing `size_category()` stub. Weapon inches are added, then total Reach converts to meters for Encounter impact comparisons. UI ranges/positions convert to yards; the AI's internal distance and Reach inputs remain meters. The legacy shared-Reach session path remains unchanged.
- Updated focused tests and task status. The real Arena still publishes a native transactional Dagger Thrust with its established result.

## Verification

- Starting point: branch `main`, HEAD `ffe4b82b8dc3dc2a4c26d33029cc44d89b8042d4`, empty index. The pre-existing working tree already contained user-managed documentation deletions and untracked materials; none were restored, moved, staged, or removed.
- Focused pre-change baseline: **11 tests passed** (the adapter and Arena tests available before this increment).
- Final focused command: `cd tests && PYTHONPATH=..:../src:../examples python -m unittest test_npcgen_being_integration test_npc_being_arena test_npc_being_arena_web test_being test_weapon test_ai_encounter.AIEncounterTest` — **47 tests passed in 3.312 seconds**. This includes loopback-only browser tests. No full regression or long Ari/Bex persistence battery was run, per the bounded assignment.
- `python -m py_compile` passed for all 13 changed Python source/example/test files. `git diff --check` and staged `git diff --cached --check` passed.
- `printf '\n' | python examples/npc_being_arena.py` completed. Native Action `npc-being-arena/action/one-dagger-thrust` committed at boundary 4 with outcome `normal`, metadata distance 1.5 m, causal body damage 4, Target HP 10→6, and native receipt boundaries 1–4.
- Implementation commit: `db255e28d3e2a40b4f89e5af8eaf74fbdeea9fa8` (`Map NPC physical attributes to native Being units`). Documentation/status commit: this report and the two task-status files are committed together; the commit hash is available from Git rather than embedded in its own report.

## Limits and follow-up

This is not a repository-wide dimensional migration. `src/config/objects.tsv`, generic Object dimensions/weights and legacy fixture literals whose physical meaning or source units are not established were not rewritten. In particular, pre-existing generic Arena definitions keep their authored numeric values rather than receiving a guessed conversion. Their unit intent should be reviewed where they become behaviorally relevant. `ObjectDefinition` remains shared across subtypes, so enforcement is documented at subtype/load boundaries rather than applied as a global conversion.

The Reach work is limited to `AgentDuel`; the general `TacticalDuel` constant and throwing trajectory/velocity model were not changed. The helper supports category fallback, but the engine's `size_category()` implementation remains a stub; `AgentDuel` uses measured dimensions in its current Human scenario and refuses if neither a valid measurement nor an explicitly supplied category is available. Revision-60 documents were not edited: the old 3/8-height glossary text, old 0.800 m / interim 30-inch references, eight-category table and throwing denominator need a separately controlled editorial synchronization. No claim is made that throwing calibration has been updated.

## Git preservation

The 14 implementation paths were committed explicitly in `db255e28d3e2a40b4f89e5af8eaf74fbdeea9fa8`. The task register, Encounter topic and this report are committed separately. The previously present documentation migration and unrelated untracked paths remain untouched; no saved JSON, `legacy/`, `.agents/`, `.claude/`, independent NPC project or adopted revision-61 document was staged. No full-suite run, push, reset, clean or stash was performed.

### Exact remaining `git status --short` after the documentation commit

```text
 D docs/ai-encounter-experiment.md
 D docs/armed-melee-increment.md
 D docs/combat-attack-specific-ui.md
 D docs/combat-controls-and-persistence.md
 D docs/combat-engagement-and-effort.md
 D docs/combat-impact-and-reactions.md
 D docs/compact-combat-ui.md
 D docs/deferred-ideas.md
 D docs/encounter-resolve-actions-architectural-audit.md
 D docs/encounter-snapshot-transaction-dependency-analysis.md
 D docs/encounter-timeline-choice-damage-characterization.md
 D docs/encounters_adopted_r60/README.md
 D docs/encounters_adopted_r60/assets/encounters-timeline-tracker-p66.png
 D docs/encounters_adopted_r60/encounters-check-inventory-r22.csv
 D docs/encounters_adopted_r60/encounters-check-inventory-r22.md
 D docs/encounters_adopted_r60/encounters-consistency-decisions-r60.md
 D docs/encounters_adopted_r60/encounters-implementation-checklist.md
 D docs/encounters_adopted_r60/encounters-outstanding-todo.md
 D docs/encounters_adopted_r60/encounters-rule-issues-r60.md
 D docs/encounters_adopted_r60/encounters-saving-check-audit-r7.md
 D docs/encounters_adopted_r60/encounters-skill-specification-audit-r25.md
 D docs/encounters_adopted_r60/encounters-working-draft-adopted-r60.md
 D docs/encounters_adopted_r60/es-041-strength-force-calibration-r60.md
 D docs/encounters_adopted_r60/revision-59-to-60.diff
 D docs/encounters_adopted_r60/tools/generate_outstanding_todo.py
 D docs/encounters_adopted_r60/tools/update_encounters_toc.py
 D docs/engineering-baseline.md
 D docs/geographical-requirements-designer.md
 D docs/handoffs/universe-6-to-7.md
 D docs/historical-being-realization.md
 D docs/historical-evidence-archive-index.md
 D docs/historical-group-realization.md
 D docs/inhabited-world-first-scene.md
 D docs/integrated-discovery.md
 D docs/interactive-discovery.md
 D docs/lantern-cross-domain-inquiry.md
 D docs/late-tributary-terrain-refinement.md
 D docs/live-tactical-combat.md
 D docs/planetary-requirements-designer.md
 D docs/planetary-two-moon-observations.md
 D docs/realization-contract-experiment.md
 D docs/terrain-from-watershed.md
 D docs/universe4-authoritative-decisions-2026-10-27.md
 D docs/universe4-checkpoint-compatibility-contract-draft.md
 D docs/universe4-class-a-addendum-t5-f2-h2-v2-2026-10-27.md
 D docs/universe4-class-a-decisions-2026-10-27.md
 D docs/universe4-increment5d2c1-report.md
 D docs/universe5-increment5e3b-cleanup-manifest.tsv
 D docs/universe5-increment5e3b-cleanup-report.md
 D docs/universe5-increment5e3g-cleanup-actions.tsv
 D docs/universe5-increment5e3g-cleanup-report.md
 D docs/universe5-increment5e3h-cleanup-report.md
 D docs/universe5-increment5e3h-final-disposition.tsv
 D docs/universe5-increment5e3i-task-adoption-report.md
 D docs/universe5-transition-handoff.md
 D docs/universe7-increment-u-loc-002a-report.md
 D docs/universe7-u-arena-001-report.md
 D docs/watershed-topology-realization.md
 D docs/working-decisions.md
?? .agents/
?? .claude/
?? docs/assignments/
?? docs/design/deferred-ideas.md
?? docs/design/deferred-npc-skill-development.md
?? docs/design/planetary-requirements-designer.md
?? docs/design/universe-playground-integration-roadmap.md
?? docs/encounters/
?? docs/experiments/
?? docs/reports/U-ARENA-001-report.md
?? docs/reports/U-ARENA-002-report.md
?? docs/reports/U-ARENA-003-report.md
?? docs/reports/engineering-baseline.md
?? examples/saved/
?? legacy/
?? universedocs.tar.gz
?? workspace/ai-encounter.json
?? workspace/combat-session.json
?? workspace/universe-planetary-world.json
```
