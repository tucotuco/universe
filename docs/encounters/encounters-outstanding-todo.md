# Encounters — outstanding to-do (open items only)

**Current adopted baseline: revision 61, supplemented on the listed subjects by revision 62.** This outstanding-only list is generated from the historical [revision-60 issue register](encounters-rule-issues-r60.md); the [revision-62 issue supplement](encounters-rule-issues-r62.md) records current throwing-status changes. This list contains **only work not yet completed**.

The list is generated from active issue statuses. Update the issue register first, then run `python tools/generate_outstanding_todo.py`. No entries here constitute an adopted rule.

## Rule decisions

- [ ] **[ES-048](encounters-rule-issues-r60.md#es-048--skill-check-and-opposed-check-terminology-normalization) — Skill-check and opposed-check terminology normalization.** Audit the remaining individual inventory rows for exact naming and correct section cross-references, without introducing new dice mechanics. Coordinate missing/incomplete skill definitions with ES-049 and apply the now-adopted discovery-action terminology.
- [ ] **[ES-041](encounters-rule-issues-r60.md#es-041--grapple-opposed-check-formula-and-timing) — Grapple opposed-check formula and timing.** Continue the **non-throwing** Being-level force-capacity model in newtons for Pull, Bull rush, leverage, traction, exertion and resultant-force movement; review coupled multiple-grip constraints and remaining Grapple position terminology. Throwing reference geometry and the yd/s velocity formula are adopted in revision 62 (see the [current supplement](encounters-rule-issues-r62.md)); trajectory conventions remain as adopted in revision 60. At implementation time, regression-test calculations and the transition from historical lookup tables; review drag/wind only with launched projectiles.

## Other documentation and source checks

- [ ] **[ES-008](encounters-rule-issues-r60.md#es-008--printable-timeline-and-unexplained-blank-pages) — Printable timeline and unexplained blank pages.** Blank pp. 40–44, 61, and 67 have not been classified; these should not be deleted or treated as missing rules without author confirmation.
- [ ] **[ES-049](encounters-rule-issues-r60.md#es-049--missing-or-incomplete-skill-specifications) — Missing or incomplete skill specifications.** Develop complete implementable skill specifications: ability, prerequisites, skill-zero behavior, roll conditions, fixed DC or opposed procedure, action duration, modifiers, outcomes and links. Approve balancing choices before inserting new mechanics into authoritative rules.
- [ ] **[ES-033](encounters-rule-issues-r60.md#es-033--zero-skill-fallback-and-ability-contests) — Zero-skill fallback and ability contests.** Review all undefined or incompletely specified skills under ES-049; provide governing ability, procedure, timing and relevant DCs without altering the adopted level-zero fallback.
- [ ] **[ES-047](encounters-rule-issues-r60.md#es-047--validate-converted-tables-and-dense-passages-against-source-pdf) — Validate converted tables and dense passages against source PDF.** Systematically review dense source tables, source URLs, and formatted passages against the original PDF; fix transcription-only defects separately from author-approved mechanics.

## Implementation and regression verification

These were identified against an earlier reconstructed Universe code snapshot; **reverify against the current checkout** before making changes.

- [ ] **[ES-020](encounters-rule-issues-r60.md#es-020--weapon-skill-appears-to-be-counted-twice-for-accuracy) — Weapon skill appears to be counted twice for accuracy.** Introduce a single explicit strategy-budget function and make the attack roll depend on the allocated attack points and explicitly documented modifiers. Reproduce A’s need for a 13 to hit B in the p. 16 example.
- [ ] **[ES-021](encounters-rule-issues-r60.md#es-021--strategy-budget-omits-combat-skill-and-ability-modifiers) — Strategy budget omits combat skill and ability modifiers.** Derive the budget from action type, skills, attributes, fatigue, equipment and magic. Check the p. 16 and p. 17 examples.
- [ ] **[ES-022](encounters-rule-issues-r60.md#es-022--extra-damage-is-added-as-a-fixed-number-instead-of-rolled) — Extra damage is added as a fixed number instead of rolled.** Make damage dice injectable and separately log weapon roll(s) and extra-damage roll; use worked examples and distribution tests.
- [ ] **[ES-023](encounters-rule-issues-r60.md#es-023--parry-uses-a-different-opposed-roll-mechanism) — Parry uses a different opposed-roll mechanism.** Implement the published attack-check modifier, or explicitly amend the source if an opposed test is desired.
- [ ] **[ES-024](encounters-rule-issues-r60.md#es-024--parry-skill-prerequisites-and-weapon-weight-exception-omitted) — Parry skill prerequisites and weapon-weight exception omitted.** Eligibility and weight tests for novice versus qualified combatants, light versus heavy incoming weapons.
- [ ] **[ES-025](encounters-rule-issues-r60.md#es-025--dodge-uses-an-opposed-roll-contest-rather-than-the-specified-strategy-rule) — Dodge uses an opposed-roll contest rather than the specified strategy rule.** Define and test the published defense-level/timing pipeline, including Tumble bonuses and armor penalties.
- [ ] **[ES-026](encounters-rule-issues-r60.md#es-026--parry-preparation-selects-fastest-weapon-motion-without-source-authority) — Parry preparation selects fastest weapon motion without source authority.** With the general ES-013 readiness principle already adopted, determine which weapon attack motion governs a specific Parry preparation (or whether the defender chooses); test the resulting timing.
- [ ] **[ES-027](encounters-rule-issues-r60.md#es-027--shield-routine-implements-one-of-two-contradictory-versions) — Shield routine implements one of two contradictory versions.** ES-002/ES-003 now select the p. 28 procedure; verify the existing code implements all current shield interception, absorption, HP damage, and simultaneous-use details, with regression tests.
- [ ] **[ES-028](encounters-rule-issues-r60.md#es-028--fatal-hit-saving-throw-inherits-the-attack-dc) — Fatal-hit saving throw inherits the attack DC.** Align the implementation with the revision-4 fatal-hit Fortitude saving throw default of DC 20, and record that DC in the combat log.
- [ ] **[ES-029](encounters-rule-issues-r60.md#es-029--backwardsideways-movement-and-reach-engagement-differ-from-draft-geometry) — Backward/sideways movement and reach engagement differ from draft geometry.** Build a narrowly specified spatial combat model and verify engagement before adding more action types.
- [ ] **[ES-030](encounters-rule-issues-r60.md#es-030--exact-full-simultaneity-is-not-yet-guaranteed) — Exact full simultaneity is not yet guaranteed.** Two lethal same-time strikes, two simultaneous hits on one shield, and simultaneous weapon breakage should follow one agreed rule independent of processing order.

## Deferred design

- [ ] **[ES-045](encounters-rule-issues-r60.md#es-045--multi-hex-being-reach-and-engagement-geometry) — Multi-hex Being reach and engagement geometry.** Define occupied-body geometry, origins for reach, facing, and engagement when a Being occupies multiple hexes. Preserve the adopted center-to-center rule for ordinary single-hex Beings.
- [ ] **[ES-046](encounters-rule-issues-r60.md#es-046--weapon-specific-minimum-effective-striking-distance) — Weapon-specific minimum effective striking distance.** When weapon Object statistics support it, evaluate whether individual weapons/attack motions need a minimum striking distance; do not impose a universal minimum in the meantime.

---

Check for freshness: `python tools/generate_outstanding_todo.py --check`.
