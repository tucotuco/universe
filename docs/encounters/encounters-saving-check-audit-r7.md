# Encounters — saving throws, ability checks, contests, and zero-skill fallback audit (revision 7)

**Authoritative working rules:** encounters-working-draft-adopted-r7.md. This supersedes the classification of Fitness as a skill/saving throw in revision 5. Page references refer to the original Encounters PDF. No Universe engine implementation is changed.

## Adopted resolution procedures

| Procedure | Dice | Success | DC? |
| --- | --- | --- | --- |
| Fortitude (Constitution-based), Reflex (Dexterity-based), Will (Wisdom-based) saving throws | d20 plus applicable modifiers | Modified total ≥ specified DC | Yes, default 20 unless another is specified |
| Fitness check (trainable ability) | **3d6** | Sum ≤ current effective Fitness | **No** |
| Improving Fitness after one week of above-normal activity | **3d6** against Constitution | Sum ≤ Constitution; Fitness cannot exceed Constitution | **No** |
| Ordinary ability check | Rule-specified Nd6 | Sum ≤ named ability score | No |
| Ability contest, including Trip | Each side **3d6 + its relevant ability bonus**, plus specified action modifiers | Higher total wins; tie preserves status quo unless action says otherwise | No |
| Ordinary skill check when level > 0 | d20 plus relevant skill/ability modifiers | Modified total ≥ skill/action DC | Yes |
| Ordinary skill check when level = 0 | Default **3d6** (unless action/skill states otherwise) | Sum ≤ **ability defined for the skill** | No |
| Door-breaking Strength check | **Nd6 specified by the door** | Sum ≤ effective Strength after applicable ram bonuses | No |

**Scope:** The zero-skill fallback applies to ordinary skill checks, not to Fortitude/Reflex/Will saves or to automatic trained/untrained prerequisites. A rule that makes a skill a prerequisite (e.g., specialist techniques) does not necessarily authorize an ability check to substitute for it.

## Governing-ability audit for zero-skill fallback

| Skill | Evidence in PDF/Markdown | Governing ability | Status |
| --- | --- | --- | --- |
| **Balance** | PDF p. 47, `Balance (Ordinary, Progressive; Dexterity)` | **Dexterity** | Defined; fallback is 3d6 ≤ Dexterity |
| **Escape Artist** | PDF p. 48, `Escape artist (Ordinary, Progressive; Dexterity)` | **Dexterity** | Defined; fallback is 3d6 ≤ Dexterity |
| **Ride** | PDF pp. 24, 49–50; Ride skill checks against DCs | **Dexterity** | **Resolved r7:** zero-level ordinary skill-check fallback is 3d6 ≤ Dexterity; mounted-combat prerequisite of Ride ≥1 remains in force |
| **Tumble** | PDF pp. 24, 50; Tumble skill checks and difficulty table | **Dexterity** | **Resolved r7:** zero-level ordinary skill-check fallback is 3d6 ≤ Dexterity |

### Additional referenced skills without governing-ability definitions

The document names **Use Rope** (Escape Artist DC), **Handle Animal** (Ride DC), and **Climb, Hide, Move Silently, Pick Pockets, and Swim** (armor-check penalties), but does not provide their complete skill entries or governing abilities within this draft. These are **documentation gaps**, not demonstrations that a zero-level fallback is actually invoked by a fully defined action. Their definitions may reside elsewhere; they should not be assigned an ability by assumption.

Other listed skills such as **Armed Combat, Archery, Throwing, Armor, Run, Improved Grapple, and Stun** either have dedicated combat/ability mechanics or prerequisites and should not automatically be treated as generic d20 skill checks with an ability fallback. Audit them action-by-action when implementing those mechanics.

## Changes to previously open issues

- **ES-031:** Fitness is a *trainable ability*, not a skill. There is **no Fitness saving-throw modifier** to calculate. The Fitness check is 3d6 ≤ current effective Fitness. The conflicting intermediate revision-5 treatment is historical only.
- **ES-032:** Constitution improvement check is now **3d6 ≤ Constitution**, with the Fitness maximum capped by Constitution.
- **ES-033:** Default skill-level-zero fallback is **3d6 against the skill's governing ability**, unless explicitly overridden. The dice question is resolved; the Ride and Tumble ability mappings are resolved in revision 7.
- **Trip:** Contest of attacker's Strength versus defender's choice of Strength or Dexterity. Each side rolls 3d6 plus the applicable ability bonus and specified circumstance bonuses. A tie does not trip.
- **Door Strength checks:** Still use the door's own Nd6, not universal 3d6.

## Remaining documentation questions

- **Ride prerequisite:** At least one level of Ride is required to participate in mounted combat. The new Dexterity fallback applies only where a zero-level ordinary skill check is otherwise permissible; it does not waive that prerequisite.
- **Other referenced skills:** Should the skills named without full definitions in this draft be documented here or cross-referenced to another skills standard? No governing abilities have been assigned to those skills by inference.

Both formerly open governing-ability assignments (Ride and Tumble) are now resolved; no Universe engine code changed.
