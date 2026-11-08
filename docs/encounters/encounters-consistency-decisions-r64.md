# Encounters — ground Pick up Action (Revision 64 supplement)

**Adopted:** 8 November 2026, by explicit task instruction. **Applies to:** the generated Arena's initial unobstructed environment only, under revision 61 as supplemented by revisions 62 and 63. This supplement adds a bounded ground-object Action; it does not revise the distinct rules for grabbing an object held by another Being or Wrestling it away.

## Pick up

`Pick up` is a distinct native Action for acquiring one free, unheld ground Object. It is not `Grab object` against an Object held by another Being and is not `Wrest`.

- A normal attempt lasts **one second** and resolves at its scheduled integer boundary. A valid attempt may fail with an ordinary Action outcome. Interruption before that boundary has no possession effect.
- For the generated Arena's explicitly unobstructed initial environment, an Object is accessible when the Being's and free ground Object's authoritative Cartesian reference positions map to the **same one-yard hex address** at the movement-before-Action snapshot. A different address is inaccessible. This is a coarse Arena gameplay access convention only; it is not body contact, reach, collision, or clearance geometry, and it does not apply to other Encounter scenarios.
- A successful pickup transfers the same registered Object identity to the Being's carried possessions. It is not held, readied, wielded, worn, armed, shield-active, or protective. The Object remains unequipped and grants no combat benefit. Its weight is included in the carried load and must not cause the total to exceed the Being's applicable heavy-load maximum under the existing carrying-capacity rules.
- The native custody representation is exclusive: the carrier's `possessions` contains the Object ID, the Object's `parent_container_id` names that carrier, and the carried Object has no independent world-space position. Its prior position is cleared at commit; the Object follows its carrier through the custody relation. Its native Object ID and weight are unchanged. This creates no hand/limb slot and no readiness state.
- All attempts resolving at one boundary use the common post-movement, pre-Action snapshot. If at least two otherwise eligible attempts target the same free Object, every eligible attempt resolves `contested`, and the Object remains on the ground. An ineligible attempt does not join that contest; if exactly one attempt is eligible, it succeeds. This procedure is deterministic and consumes no random draw. A targeted ground Object is not exclusively reserved at Choice acceptance; ordinary reservations remain for actively used instruments.
- The operator may author a test Action with a known native Object ID. This does not establish observer knowledge, awareness, or permission to expose that Object. Player projections remain governed by observer-owned evidence.

Revision 64 does **not** adopt initial `Ready weapon` timing, a ready-hand/body-part representation, armor donning, or shield readying. The existing after-attack re-ready timing is unchanged and cannot be generalized to initial readiness.

## Implementation boundary

The new Action uses the native Choice/schedule/one-second snapshot/effect/atomic-publication path. A successful effect changes Being possession and Object custody together. It uses the existing shared-snapshot rule for same-second contention. The same-hex convention is not a collision or physical-interaction model and cannot be used outside this bounded Arena mode without further adoption.
