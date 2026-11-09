# Encounter consistency decisions — revision 66

## Generated Arena: initial weapon readying

**Adopted only for the bounded generated Arena interaction.** A positive-HP participant may take a distinct native, one-second `Ready weapon` Action after acquiring an ordinary supported one-handed weapon. Ground Objects still require the separate revision-64 Pick up Action and its same-hex accessibility rule.

The actor explicitly selects a currently free native left or right hand represented in its existing body-part state. A selected hand must be present in `Being.current.body_parts` and have no Object assigned. No hand is inferred from race, Being type, or appearance. Existing native data has no separate per-hand functional-status field; this supplement therefore relies only on explicitly represented hand slots and their empty/occupied value. If a hand slot is absent, readiness is unavailable. The generated Arena's current NPC Generator imports do not author hand slots, so this supplement does not add them.

For this first implementation, the eligible ordinary weapon is the native Dagger definition. Other one-handed weapon classifications, two-handed weapons, nonstandard manipulators, and shields are outside this bounded adoption. The player may not displace another Object. A failed eligibility check makes no equipment transition.

On success, one native transaction retains the same Object in the actor's carried `possessions`, adds that identity to the existing native `weapons` collection, and assigns it to the selected body-part slot. Carried weight counts the Object once. No armor or shield effect, attack, or other combat benefit is granted by Ready itself. A later Action may use the weapon only after this transition has committed. All Actions resolving at one boundary read the common pre-Action snapshot, so a weapon readied at that boundary is not ready to another Action at that same boundary.

Conflicting same-boundary claims for the same weapon or actor hand all fail as contested; the resolver does not choose a winner. Withdrawing an accepted Choice before it starts has no equipment effect. The current native step is an atomic one-second operation with no mid-second interruption window; no new interruption clock is adopted.

## Scope and implementation boundary

This is an Arena-only supplement to revision 61 and does not change general combat or equipment rules, revision 64 Pick up, revision 65 observer authority, or existing checkpoint formats. Readying updates the actor's own native sheet. It does not authorize observation of an opponent's private inventory or equipment. This supplement adopts no body geometry, collision, hand capacity beyond one assigned Object per represented slot, default equipment, automatic hand selection, or general weapon classification.
