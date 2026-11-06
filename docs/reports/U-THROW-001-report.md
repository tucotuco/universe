# U-THROW-001 — Throwing reference-length calculation

## Outcome

Implemented and tested an inactive, pure throwing-velocity helper. The checkout contains no active native Throw velocity calculator, Throw Action, or projectile trajectory calculation to update. The helper follows this assignment's 28-inch reference denominator and measured-arm priority but is not connected to gameplay. The required authoritative-document synchronization is **blocked** because the active revision-61 rulebook and related documents are in the user-moved, untracked `docs/encounters/` directory. I left that directory untouched and supplied an unapplied, whitespace-checked proposed revision-62 patch.

## Source findings

- [`src/melee_combat.py`](../../src/melee_combat.py) contains the shared `reference_arm_length_inches()` helper used by the 005B Reach calculation. It uses `(15/37) × max(positive height, positive length)` and requires an explicit size-category code when neither positive dimension is available.
- No Throw velocity calculator or Throw Action exists under `src/`; searches for the adopted velocity equation, 0.08081 constant, velocity-versus-weight calculation, and throw-specific release calculation found none. The engine's `src/spatial/state.py` integration is general constant-velocity movement, not projectile trajectory. `src/statistical_group.py` motion is group motion, not projectile launch.
- The active working text is [`docs/encounters/encounters-working-draft-adopted-r61.md`](../encounters/encounters-working-draft-adopted-r61.md), but it is untracked. It still identifies revision 59's 0.800 m Medium reference and `sqrt(L / 0.800 m)` as current. The untracked `docs/encounters/README.md` still summarizes revision 60 as current, and the current issue/to-do documents are also untracked. Meanwhile, their former tracked location `docs/encounters_adopted_r60/` appears as user-managed deletions. This is an in-progress documentation move, not permission to replace those files.
- No `30-inch` or `30 inch` reference was found in the current r61 working text or the inspected consistency record. The proposed patch labels any such interim value in residual historical notes as superseded, without altering earlier dated records.
- Because no production trajectory calculation exists, there is no active yd/s-to-m/s calculation boundary to update. The proposed rule text states the required conversion for a future integration: multiply yards/second by `0.9144` to obtain meters/second. Spatial state remains meters. No conversion or projectile engine was added here.

## Changes

- Added [`src/throwing.py`](../../src/throwing.py), a pure helper for `Vmax` and smooth-model release velocity in yards/second. It accepts explicit Strength, Throw skill level, projectile pounds, the heavy-load numerical reference in pounds, and either positive measured dimensions or an explicit size category. It reuses the existing measured-arm helper, maps full category names to its existing one-letter codes, gives Throw a one-time +1 modifier at levels 1+, and uses `sqrt(L_inches / 28 inches)`.
- The helper does not enforce the separate maximum throwable weight, create a Throw Action, schedule or publish effects, consume RNG, or calculate trajectory. It does not infer size category, body geometry, fatigue or physical force.
- Added [`tests/test_throwing.py`](../../tests/test_throwing.py) covering the category table, Medium's 28-inch fallback, measured 69-inch dimension precedence, missing/invalid reference refusal, reference factor 1 at 28 inches, `sqrt(2)` scaling at 56 inches, one-time Throw modifier, weight response, and the 5 yd/s threshold.
- Updated [`TASKS.md`](../../TASKS.md) and [`docs/tasks/encounter-engine.md`](../tasks/encounter-engine.md) to distinguish the pure calculation from blocked authoritative synchronization and absent native Throw integration.
- Added [`U-THROW-001-rule-sync-proposal.patch`](U-THROW-001-rule-sync-proposal.patch), a proposed revision-62 addendum and narrowly scoped rulebook/README/to-do edits. `git apply --check` passes against the current moved documents. The patch is **not applied**.

## Numerical verification

- `reference_arm_inches(size_category="Medium")` → `28 in`.
- A measured 69-inch Being uses `69 × 15/37` → approximately `27.973 in`, ahead of a supplied category estimate.
- With Strength 10, Throw level 1, projectile 5 lb and heavy-load reference 100 lb, Medium release speed is `22.5 × exp(-((0.05/0.08081)^0.6010))` yd/s. The same inputs at Large (56 in) produce exactly `sqrt(2)` times that speed.
- At Strength 10, maximum velocity is 20 yd/s with no acquired Throw skill and 22.5 yd/s at any level 1 or higher. Projectile weight 20 lb produces less speed than 1 lb under the same reference.
- The adjacent-hex helper returns true at 5 yd/s and false below 5 yd/s. The independent maximum-weight table remains outside this helper.

## Verification

- Focused command, from `tests/`:

  ```sh
  PYTHONPATH=..:../src:../examples python -m unittest \
    test_throwing \
    test_ai_encounter.AIEncounterTest.test_reference_arm_length_prefers_larger_measured_dimension_and_medium_fallback \
    test_ai_encounter.AIEncounterTest.test_reach_is_weapon_and_body_specific_and_applies_at_impact \
    test_npc_being_arena.TestNpcBeingArena.test_one_operator_action_is_native_transactional_and_one_shot \
    test_npc_being_arena.TestNpcBeingArena.test_measured_reach_boundary_is_in_range_and_immediately_above_is_not \
    test_npc_being_arena.TestNpcBeingArena.test_out_of_reach_is_committed_without_damage_or_rng_advance \
    test_melee_combat.TestMeleeCombat.test_target_moves_out_of_reach_before_resolution \
    test_being.TestBeingDefinition.test_init \
    test_weapon.TestWeaponDefinition.test_constructor_with_valid_values
  ```

  **15 tests passed in 1.867 seconds.** The initial invocation used two nonexistent test class names and therefore did not execute those selectors; the corrected command above passed.
- Python compilation for `src/throwing.py` and `tests/test_throwing.py` — passed.
- `git diff --check` — passed.
- `git apply --check --unidiff-zero docs/reports/U-THROW-001-rule-sync-proposal.patch` — passed; this checks patch applicability only and does not modify the user-owned docs. The zero-context flag is required by the whitespace-clean proposal format.
- The new U-THROW-001 links in `TASKS.md`, `docs/tasks/encounter-engine.md`, and this report resolve. A broader relative-link check also found pre-existing links in those files to the deleted former locations under `docs/encounters_adopted_r60/`, `docs/handoffs/`, and the old historical archive index. These are part of the user's in-progress documentation move and were not repaired here.
- No full regression was run. There is no runnable Throw Action or throwing demo to claim.

## Documentation blocker and next step

The requested authoritative update would change user-moved untracked `docs/encounters/` content, while the original tracked `docs/encounters_adopted_r60/` paths are already deleted in the user's working tree. The assignment explicitly says not to overwrite or broadly stage that move. Therefore the active r61 text remains unchanged and still states the old 0.800 m denominator; the new source helper is an isolated calculation and must not be described as gameplay behavior. The exact proposed update is available in the patch file for the documentation owner to review and apply. Until then, this increment is **partially delivered / documentation-blocked**, not a complete adopted-rules synchronization.

The smallest follow-up is to authorize applying the proposed revision-62 patch to the current documentation tree and to its revision/status indexes, then separately decide whether to build a native Throw Action and connect release velocity to metric trajectory calculations.

## Git and preservation

Starting state: branch `main`, HEAD `6faca7f1949fcf848dee47f9034a1651cbafa81c`, empty index. Existing user-managed deletions, untracked directories, legacy content, independent projects, and saved JSON were preserved. The only changes authored in this increment are `src/throwing.py`, `tests/test_throwing.py`, the two task-status files, this report, and the unapplied patch artifact. No files under `docs/encounters/` or `docs/encounters_adopted_r60/` were edited, staged, moved, or restored. No push, reset, clean, or stash was performed.

Implementation/test commit: `eeeafcd248d8741edd9b16209b9f56a4446d44e5`. The report and task-status documentation are in the second commit; its actual hash is given in the delivery response rather than embedded in its own content.


### Exact final `git status --short` before the report-only commit refresh

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
