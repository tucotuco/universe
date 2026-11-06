# Encounter revision-60 issue bridge — authoritative open items

Back to [TASKS.md](../../TASKS.md).

This checklist mirrors, but does not control, the [adopted issue register](../encounters/encounters-rule-issues-r60.md) and its [generated outstanding queue](../encounters/encounters-outstanding-todo.md). Preserve the register's wording and status; do not close an issue because adjacent tests pass. Update the source register first, then regenerate the queue and reconcile this bridge. The current controlling package baseline is revision 61 with revision 62 and 63 supplements; this file retains its r60 issue IDs.

## Rule decisions

| State | ID | Register status / bounded remaining scope |
|---|---|---|
| [ ] | [ES-048](../encounters/encounters-rule-issues-r60.md#es-048--skill-check-and-opposed-check-terminology-normalization) | Partially resolved: generic checks adopted in revision 22; local wording and cross-reference audit remains open. No new dice rules. |
| [ ] | [ES-041](../encounters/encounters-rule-issues-r60.md#es-041--grapple-opposed-check-formula-and-timing) | Still open after partial revisions: non-throwing Being force capacity, mapping force to acceleration/displacement, multiple-grip coupling and remaining Grapple terminology. Adopted throwing calibration remains normative. |

## Documentation and source checks

| State | ID | Register status / bounded remaining scope |
|---|---|---|
| [ ] | [ES-008](../encounters/encounters-rule-issues-r60.md#es-008--printable-timeline-and-unexplained-blank-pages) | Partially resolved: p. 66 interpretation adopted; blank pp. 40–44, 61 and 67 remain unclassified. |
| [ ] | [ES-049](../encounters/encounters-rule-issues-r60.md#es-049--missing-or-incomplete-skill-specifications) | Specification required: complete missing/incomplete skill definitions without inventing unapproved mechanics. |
| [ ] | [ES-033](../encounters/encounters-rule-issues-r60.md#es-033--zero-skill-fallback-and-ability-contests) | General rule resolved in revision 6; review remaining incomplete individual skill definitions under ES-049. |
| [ ] | [ES-047](../encounters/encounters-rule-issues-r60.md#es-047--validate-converted-tables-and-dense-passages-against-source-pdf) | Editorial verification pending: compare converted tables and dense passages with the source PDF. |

## Implementation and regression verification

The register describes implementation mismatches or partial implementation; reverify against current code/tests before changing anything.

| State | ID | Register status / bounded remaining scope |
|---|---|---|
| [ ] | [ES-020](../encounters/encounters-rule-issues-r60.md#es-020--weapon-skill-appears-to-be-counted-twice-for-accuracy) | Implementation mismatch: weapon skill/accuracy budget and p. 16 example. |
| [ ] | [ES-021](../encounters/encounters-rule-issues-r60.md#es-021--strategy-budget-omits-combat-skill-and-ability-modifiers) | Implementation mismatch: strategy budget and p. 16–17 examples. |
| [ ] | [ES-022](../encounters/encounters-rule-issues-r60.md#es-022--extra-damage-is-added-as-a-fixed-number-instead-of-rolled) | Implementation mismatch: rolled, separately attributed extra damage. |
| [ ] | [ES-023](../encounters/encounters-rule-issues-r60.md#es-023--parry-uses-a-different-opposed-roll-mechanism) | Implementation mismatch: Parry procedure versus adopted attack-check modifier. |
| [ ] | [ES-024](../encounters/encounters-rule-issues-r60.md#es-024--parry-skill-prerequisites-and-weapon-weight-exception-omitted) | Implementation mismatch: Parry prerequisites and weapon-weight exception. |
| [ ] | [ES-025](../encounters/encounters-rule-issues-r60.md#es-025--dodge-uses-an-opposed-roll-contest-rather-than-the-specified-strategy-rule) | Implementation mismatch: Dodge defense-level/timing, Tumble and armor penalties. |
| [ ] | [ES-026](../encounters/encounters-rule-issues-r60.md#es-026--parry-preparation-selects-fastest-weapon-motion-without-source-authority) | Implementation interpretation: determine the governing Parry preparation motion or defender choice. |
| [ ] | [ES-027](../encounters/encounters-rule-issues-r60.md#es-027--shield-routine-implements-one-of-two-contradictory-versions) | Implementation/source reconciliation: verify adopted p. 28 shield procedure and simultaneous use. |
| [ ] | [ES-028](../encounters/encounters-rule-issues-r60.md#es-028--fatal-hit-saving-throw-inherits-the-attack-dc) | Implementation/unspecified source interpretation: fatal-hit Fortitude DC and combat log. |
| [ ] | [ES-029](../encounters/encounters-rule-issues-r60.md#es-029--backwardsideways-movement-and-reach-engagement-differ-from-draft-geometry) | Implementation mismatch: movement and reach/engagement geometry. |
| [ ] | [ES-030](../encounters/encounters-rule-issues-r60.md#es-030--exact-full-simultaneity-is-not-yet-guaranteed) | Partial implementation: order-independent simultaneous lethal strikes, shield hits and breakage. |

## Deferred rule design

| State | ID | Register status / bounded remaining scope |
|---|---|---|
| [ ] | [ES-045](../encounters/encounters-rule-issues-r60.md#es-045--multi-hex-being-reach-and-engagement-geometry) | Deferred rule design: multi-hex Being occupancy, reach origins, facing and engagement. |
| [ ] | [ES-046](../encounters/encounters-rule-issues-r60.md#es-046--weapon-specific-minimum-effective-striking-distance) | Deferred rule design: assess weapon-specific minimum distance when source data supports it. |

## Reconciliation note

The task seed said there were 20 outstanding entries and included ES-053. The live r60 issue register has no ES-053 entry, and the generated queue lists **19** items: the 19 IDs above. The task index follows the authoritative register and does not invent ES-053. If a future authoritative revision adds it, add it here with its adopted status and link.
