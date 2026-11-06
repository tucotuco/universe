# Encounters — adopted spatial-precision clarification (Revision 63)

**Adopted:** 6 November 2026. **Applies to:** revision-61 rules as supplemented by revision 62. This clarification supersedes only the former requirement to round authoritative movement-state coordinates to the nearest 0.1 m. Dated revision-59 through revision-62 decision text remains historical and is not silently rewritten.

## Authoritative positions

World-space Cartesian positions are represented in meters at native floating precision. Do not round or quantize coordinates at any movement or Encounter interval commitment boundary. Movement calculations, committed positions, frozen post-movement snapshots, action evaluation (including Reach), publication, inspection, and future calculations use the same authoritative value. No separately authoritative rounded position or exact/shadow coordinate is maintained.

Immutable-launch projectile trajectories retain their existing full-precision calculation, exact boundary positions, and fractional impact metadata. Successful Object Spot evidence records exactly the committed position from its boundary snapshot and remains historical evidence; later movement does not revise it.

## Units and presentation

Player-facing spatial distances continue to use yards. Internal positions, geometry, projectile trajectories, and location evidence remain metric. A displayed distance may convert to yards and round visually; presentation formatting never changes authoritative Reality or an observer's stored record. This rule sets no universal display precision. It does not change inches or pounds for physical attributes, the revision-62 Reach/reference-arm rules, Throw speed in yards per second, or any other unit convention.

## Scope

This clarification supersedes only revision 61's 0.1 m coordinate commitment rule and the corresponding movement wording. Other revision-61 rounding instructions (including HP, exertion, and damage), revision-62 decisions, action timing, movement mechanics, Reach, projectile physics, and perception rules are unchanged. It introduces no sensor error, location uncertainty, geometry inference, or physics rule.
