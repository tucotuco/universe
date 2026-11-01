# Encounters — skill definition and implementability audit (Revision 25)

**Status:** Author-review work list, **not adopted new skill mechanics**. Source is the 67-page original and the Revision 25 working rules. Related issues: **ES-033, ES-049, ES-048**, plus resolved ES-050/ES-051. Every named skill referenced in an action, an equipment entry, or the Racial Aptitude Table must either have an implementable definition or be explicitly identified as not a skill. No default abilities, DCs, prerequisites or times are invented here.

## 1. Referenced skills without a defining section

| Skill or family | Source context / existing consequence | What must be specified to implement it |
|---|---|---|
| **Climb** | pp. 9, 30, 39, 46, 50: vertical movement, armor check penalty, +2 from Nekode, Halfling +10% XP aptitude | Governing ability; progressive? untrained handling; climb speed, timing, surface DCs, falling, assistance, modifier stacking |
| **Hide** | p. 30 armor penalty; concealment rules elsewhere; “Hide” in armor is a material name, not this skill | Governing ability, prerequisites for concealment, whether opposed by skill-free Spotting checks or fixed DC, movement timing, detection effects |
| **Move Silently** | pp. 30, 46: armor penalty; Halfling +5% XP aptitude | Governing ability, opposed versus skill-free Hearing or a specified DC, movement speed and action timing, failure detection |
| **Pick Pockets** | p. 30 armor penalty | Governing ability, checks vs targets, detection mechanism, duration, target/item size and failure consequences |
| **Swim** | p. 30 armor penalty; Swimming timing appears elsewhere; Aquatic combat qualification is a *different* skill | Governing ability, movement speed and time, water conditions/DCs, drowning/fatigue/armor consequences, level-zero behavior |
| **Use Rope** | p. 48 Escape Artist: tied-ropes DC = 20 + binder’s Use Rope level | Governing ability, knots/binding DC, duration, binding vs escaping, untrained use, when rope or materials matter |
| **Handle Animal** | p. 49 Ride Difficulty Table: `+1/4 ranks` | Governing ability, what ranks mean and when bonus is applied/rounded, handling versus training, DCs, durations and failure outcomes |
| **Jump** | p. 46 Racial Aptitude Table: Halfling +10% XP; action appears implicitly in movement | Governing ability, horizontal/vertical distance equations, timing, DCs or ability checks, takeoff/landing constraints |
| **Appraise** | p. 46 Dwarf +10% XP racial aptitude | Governing ability, item-value and authenticity DCs, time, error margins, untrained ability fallback |
| **Search (ACTION, not skill)** | p. 46 Elf +10%, Half-elf +5% racial action aptitude | Resolved in ES-050: deliberate 6-second d20 action against Entity DC (default 15); racial +10% means +2 roll, +5% means +1; accessible 6-second Search range. Incidental Search is not introduced |
| **Alchemy** | p. 46 Gnome +10% XP racial aptitude | Governing ability, recipe and ingredient requirements, crafting time, DCs, success/failure and hazard consequences |
| **Stone/metal/gem crafts** | p. 46 multiple Dwarf/Gnome craft aptitudes | Define generic Craft family versus separate skill names, governing ability, recipe complexity/DC, tools/materials, timing, quality/failure and XP aptitude applicability |
| **Magic, Illusion** | p. 46 Elf/Gnome racial aptitudes; magic elsewhere uses mana/spells | State whether these are independent learnable skills, specializations, or references to an external magic subsystem. Define complete spell use and skill-resolution interface if retained |

### Important exclusions / aliases

- **Search, Spot, and Listen are actions**, not skills. Spot and Listen resolve with d20 against **Entity discovery DC (15 by default)** plus integer DC-table adjustments. Deliberate attempts are six-second actions; incidental perception checks are triggered by environmental opportunities, consume no action time, and are not voluntary actions. Search is deliberate six-second discovery against Entity DC (15 by default). ES-050 and ES-051 are resolved.
- Their p. 46 Racial Aptitude percentages **must be applied to successful resolution**, not to XP-learning costs. Each +10% aptitude converts to +2 and each +5% aptitude to +1 on the d20 roll; Half-elf Search/Spot/Listen entries are now +5%, and Halfling retains +10% Listen (ES-050 revised in r25).
- **Axes, swords, bows, picks, hammers, Throw**: weapon skill groups or a defined combat skill, not necessarily missing new skills. Treat weapon-family XP aptitudes separately from absent standalone skill definitions.
- **Balance, Ride, Tumble, Escape Artist** are defined in Appendix II, but need targeted completeness checks below rather than being mislabeled as wholly missing.
- **Nekode, shield, armor and weapon entries** may reference skills without creating separate skill definitions themselves.

## 2. Existing skill descriptions with outstanding implementability checks

| Defined skill | Already stated | Verify or supply |
|---|---|---|
| **Balance** | Dexterity; DC table; check every six seconds; speed half; modifiers and failure ranges | Overlap between “failure by up to five” and “failure by five or more”; exact DC composition, when off-balance state ends, precision of fall |
| **Escape Artist** | Dexterity, progressive, 1 min attempt; DC table; armor; grapple escape skill contribution | Explicit interaction with opposed Grapple skill check, choosing between Improved Grapple and Escape Artist, binding/Grab prerequisites |
| **Ride** | Dexterity, progressive, mount type; many DCs, mounted combat cap, mounts/coordination | Rounding of +1/4 Handle Animal ranks, low-skill transfer, failure outcomes and timing for every Ride table row |
| **Tumble** | Dexterity, progressive, DC table, armor, light-load limit, Dodge benefit | Exact failure consequences for each maneuver, DC vs movement-mode prerequisites, bonus rounding |
| **Run** | Progressive, +1 foot/s per level and stamina effects, armor penalty | Definition of task check (if any), fatigue test integration, effect under environmental movement limits |
| **Improved Grapple/Grapple** | Strength or Dexterity (best advantage); opposed 3d6 + level + ability modifier, armor and special Grapple state | Hold/takedown/reverse/pin/escape transitions, Escape Artist substitution, timing acceleration and strategy-point effects, multi-attacker bonuses and tie tests |
| **Blind-fight** | Non-progressive, miss chance modification and -4 attack consequence | Reconcile special blind condition effects with general Attack Modifiers table and no-double-application |
| **Ambidexterity** | Special skill/advantage; off-hand Dexterity -3; training improvement every 2 experience levels | Precisely define training achievement, eligible actions, when skill is acquired versus earned and cost consequences |
| **Armor/Shield** | Training, proficiency categories, armor penalties, passive shield use | Define any training/prerequisite ambiguity and whether any actually require skill checks (do not invent one) |
| **Other trained combat and weapon skills** | Combat and weapon levels, strategy pools, weapon timing | Confirm no duplicate skill bonus in attack resolution; environment qualification/Ride cap, action timing and validation tests |

## 3. Cross-cutting specification needed for every actual skill

Each implementable skill entry should include all applicable fields, with **Not applicable** expressly stated where appropriate:

1. **Identity and category:** canonical name, progressive/non-progressive, ordinary/extraordinary, separate skill versus action or alias.
2. **Governing ability/abilities**, including the zero-skill fallback or a hard prerequisite for trained-only use.
3. **Resolution procedure:** fixed-DC skill check, opposed skill check, ability contest, attack roll, ability check, passive modification, or deterministic result. If a roll is required, exact dice, comparison and tie rule.
4. **Eligible context and target, modifiers and DC:** terrain/environment, gear, size, assistance, armor, visibility and explicit stacking.
5. **Timing:** when declared, preparation/action seconds, frequency of reevaluation, and whether movement is permitted.
6. **Success/failure and state effects:** precise consequences, damage or movement if applicable, persistence and expiration; simultaneous-resolution compatibility.
7. **Improvement and XP costs:** training, racial aptitude effects and any skill-family inheritance; all percentage modifiers applied in their correct domain.
8. **References/tests:** section anchors and at least one trained/untrained case and a boundary case.

**Do not infer numeric DCs or new mechanics by copying D&D conventions without author approval.** Source-absent specification fields must remain open until deliberately designed.

## 4. Percentage and integer modifier audit

| Source table | Entries | Domain | Author decision / outcome |
|---|---|---|---|
| **Spotting Modifiers** (p. 7) | +1, +3, -5, etc. | **Integer DC adjustment** | Already usable: d20 >= 15 + sum of applicable table DC adjustments. No extra skill modifier |
| **Hearing Modifiers** (p. 7) | +1 through +6; impossible | **Integer DC adjustment / impossible** | Already usable: d20 >= 15 + modifiers; 'impossible' precludes success under specified condition |
| **Encounter Distance** (p. 6) | 50%, 75%, 10%, 25% | **Distance multiplier** | Do not turn into DC adjustment; determines initial detection geometry |
| **Racial Aptitude** (p. 46) | +5%, +10% | **Skill rows:** XP learning-cost reduction. **Search/Spot/Listen action rows:** improvement to action success. | Action aptitude +10% grants +2; +5% grants +1. Half-elf has +5% each Search/Spot/Listen and Halfling has +10% Listen (ES-050 resolved). |
| **Terrain / Hampered Movement** (p. 9) | e.g., ×75%, ×50% | **Movement speed multiplier** | Do not turn into DC adjustment; separate from Combat qualification |
| **Combat concealment / miss chance** | % concealment; % chance to miss | **Probability / combat modifier**, not a generic skill-check DC | Follow its own combat procedure; distinct from perception DC |

## 5. Prioritized author decisions

1. **Triggered detection timing** (ES-051, resolved r25): Meaningful environmental opportunities can trigger incidental Spot/Listen checks at no action time; no voluntary automatic rerolls.
2. **Missing movement and stealth skills** (ES-049): Climb, Swim, Jump, Hide, Move Silently, Pick Pockets. Supply abilities, DCs, time and failure consequences.
3. **Manipulation, animal, crafting and research skills** (ES-049): Use Rope, Handle Animal, Appraise, Alchemy, crafts, Magic/Illusion. Search is defined as a discovery action under resolved ES-050.
4. **Completeness review of partially specified skills**, using the generic check taxonomy (ES-049/ES-048) and itemized inventory.
5. **Regression matrix**: tests for skill level 0, race-specific aptitudes, percent semantics, conditional armor penalties, and actual action-resolution timing.

See the **[to-do-only list](encounters-outstanding-todo.md)** for active tracked work. This is an audit and work plan; no new source-absent numerical mechanics have been adopted.
