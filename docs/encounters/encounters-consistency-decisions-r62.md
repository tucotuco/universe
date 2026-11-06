# Encounters — cumulative adopted decision supplement (Revision 62)

**Adopted:** 5 November 2026. **Applies to:** revision-61 working rules. This addendum is controlling only for the unit/reference-arm/Reach/throwing matters below; revision 61 remains controlling otherwise. Earlier revision-59/60 records remain unchanged as historical decision provenance.

**Current status note (6 November 2026, adopted [revision 63](encounters-consistency-decisions-r63.md)):** The following Physical units and representation paragraph records the precision status at the time revision 62 was adopted. Revision 63 now supersedes that statement only as to authoritative spatial-coordinate precision: coordinates are not rounded at commitment boundaries. The yard-to-meter relation, metric coordinate units, and every other revision-62 decision remain unchanged. This note preserves, rather than rewrites, the dated revision-62 decision.

## Physical units and representation

- Being height/length, anatomical arm length, personal Reach, and calculated weapon Reach are expressed in **inches**. Being and Object weights are in **pounds**. Existing rules tables retain their published numeric values and source-unit labels; this decision does not rewrite tables.
- Movement, range, and other player-facing spatial distances are expressed in **yards**. World-space positions, collision geometry, and projectile trajectories remain metric. A yard is not a meter. The exact yard-to-meter relation and metric spatial precision already adopted remain unchanged.

## Reference arm length and Reach

If positive measured Being height or length is available, estimate anatomical arm length and personal Reach in inches as:

`personal_reach_inches = (15/37) × max(height_inches, length_inches)`.

No additional individual anatomical variation is modeled. If neither dimension is positive, use a **known explicit Size Category**, not a geometry estimate or unfinished engine stub:

| Size Category | Reference arm length |
| --- | ---: |
| Diminutive | 3.5 in |
| Tiny | 7 in |
| Small | 14 in |
| Medium | 28 in |
| Large | 56 in |
| Huge | 112 in |
| Gargantuan | 224 in |
| Colossal | 448 in |

These values are reference estimates, not individually measured limb facts. Effective weapon Reach is personal Reach plus the applicable weapon length. Reach is a **scalar distance used in calculations**, never a world coordinate. For ordinary single-hex Beings, the adopted center-to-center test, post-movement impact timing, and no-first-strike-precedence rule are unchanged.

## Throwing velocity

For `x = projectile_weight_lb / heavy_load_reference_lb`:

`Vmax_yd_s = 5 × (Strength + Throw_skill_modifier − 2) / 2`,

where Throw skill modifier is +1 at any acquired Throw level and 0 at level 0. Resolve `L_inches` from the measured-first reference-arm rule above, with explicit category fallback only when no positive measured dimension exists. Release velocity is:

`Vrelease_yd_s = Vmax_yd_s × exp(−(x / 0.08081)^0.6010) × sqrt(L_inches / 28 inches)`.

The heavy-load reference remains a numerical normalizer, not a physical causal rule. The 28-inch denominator makes Medium's reference factor 1. The prior 0.800 m Medium reference and metric size series, and the interim 30-inch anchor, are superseded as current anchors; their dated appearances remain historical. Preserve the independent maximum throwable-weight limit, the 5 yd/s effective-adjacent-hex threshold, Throw modifier, and square-root size scaling.

The revision-60 trajectory rules remain unchanged: `g = 10 m/s²`, variable/body-height release convention, SI trajectory calculations, no newly adopted drag or wind behavior. No player-facing implementation-conversion instructions are added. This supplement creates no native Throw Action, projectile physics resolver, or new eligibility rule.
