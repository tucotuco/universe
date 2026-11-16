# Adopted Encounter rule — Multiple-shield passive protection

**Adopted:** 2026-11-15, by express user decision
**Authority:** supplement to the effective adopted Encounter rules after revision 70; this is **not** a historical claim about what revision 61 originally contained.
**Integrate:** incorporate the substantive text below into the effective authoritative *Shields* section, with an adoption/reference note and working relative link from the current Encounter README/decisions register. Preserve any historical revision/source conventions used by the live repository. Do not treat this standalone note as a second implementation-status register.

## Canonical rule text

### Passive protection using multiple shields

When a Being legally bears more than one shield providing passive protection, **each shield has its own attack-coverage capacity, equal to that shield's size**. A single incoming attack may receive passive protection from **at most one shield**. Shields' interception chances, damage stopped and durability effects **do not stack** against the same attack.

The defender assigns eligible incoming attacks to individual borne shields before the attack outcomes are determined, without exceeding the capacity of any shield. For allocation choices, the previously adopted **prior-round-observable** restriction applies: the defender may deliberately assign only incoming Actions already perceptible to that defender in the preceding round; an Action first revealed during the resolving round cannot be retroactively selected. As already adopted, passive allocation is **not a timed Action and consumes no Action-capacity resource**.

For each lawfully assigned attack, the assigned shield alone performs the normal passive interception and protection procedure; each shield's hit-point loss belongs to that shield's persistent Object identity. All same-boundary attacks use the shared post-movement/pre-Action snapshot of shield eligibility, size, durability and allocation. All resulting effects commit together; destruction by combined damage does not retroactively cancel protection already valid at that boundary. Future boundaries use the committed post-damage shield state.

All existing equipment, hands, buckler, tower-shield, Active Block, awareness and physical legality requirements remain in force. **This rule does not make it automatically legal to wield two shields**, and does not imply that a shield can be in two hands or two places. One shield is never duplicated or shared as multiple independent protection resources.

## Illustrative case (not a new special rule)

A Being legally bears two size-2 shields. Five incoming attacks have been observed early enough to be lawfully allocated. The defender may assign attacks A and B to shield 1, C and D to shield 2, leaving E without passive shield coverage. A–D then use the normal interception rules independently, with each shield bearing its own durability loss. An attack is never intercepted sequentially by both shields.

## Implementation and interpretation boundary

The adoption establishes **at most one shield per attack**, independent capacities, pre-outcome assignment, prior-round observability and zero Action-time cost. It does **not** adopt an automatic priority between equally eligible shields, an additional sensing ability, unlimited passive coverage for previously unseen attacks, an additional defense roll, or new geometry. If the existing one-shield automatic path and an eligible multi-shield declaration leave a genuinely ambiguous case (for example, no assignment identifying which of two shields applies), preserve native fail-closed behavior and request only the precise missing decision—never choose by iteration order or hidden Object ID.

This rule is accepted independently of implementation. Action coverage remains `PARTIAL` until the applicable native, Arena, concurrency, privacy and fresh-process tests pass. Do not label shield Actions `FULL` merely by installing this text.
