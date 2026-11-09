# Revision 66 record — initial weapon-readying proposal not adopted

**Authority correction (U-ARENA-005F):** This file was previously mislabeled as an adopted supplement. The user challenged the proposed universal one-second initial Ready weapon duration. No revision-66 initial weapon-readying rule is adopted, and none of this file's additional implementation assumptions should be treated as authoritative.

## Controlling revision-61 rules

Revision 61, Appendix I, **Weapons**, states that drawing a weapon ordinarily takes **2 seconds**, unless the weapon description specifies otherwise. Its Quick-draw exception applies only when the Being has Quick-draw and advanced skill in that weapon. The same section separately states that re-readying a weapon **after an attack** takes one-third of the weapon's timing, rounded down. Revision 61, **Ready**, repeats both distinctions and describes other Object preparation as variable and referee-adjudicated.

The adopted weapons table supplies the applicable attack-motion timings. In the Hand Weapons Table, Dagger has range, swing, and thrust timings of 4 seconds, so its post-strike re-ready time is floor(4/3) = **1 second**. In the Swords Table, Longsword swing timing is 6 seconds, so its post-strike re-ready time is floor(6/3) = **2 seconds**. These values describe post-strike re-readying; neither value replaces the ordinary 2-second draw rule.

## Authority of the former proposal

The former text proposed a one-second Arena Ready weapon Action, required an explicitly represented empty hand, limited the Object to Dagger, and prescribed same-boundary contention behavior. The one-second initial-readying duration is contradicted by revision 61 and is withdrawn. The other hand-selection, weapon-scope, and contention choices were implementation assumptions in that proposal; they were not independently adopted by the user or revision 61 and are not rules.

The implementation machinery remains in the repository as unadopted code, but the Arena browser does not offer the Action. Native possession and parent custody do not say whether an Object is in a drawable location or stored inside another carried Object. The current Being templates also do not define hands. Therefore no draw transition can be inferred from current Arena state. This record adds no drawable-location field, hand state, retrieval timing, or default equipment.

The pure table-derived post-strike helper added under U-ARENA-005F is an implementation utility, not a new adopted rule. It does not schedule Actions or change attack readiness.
