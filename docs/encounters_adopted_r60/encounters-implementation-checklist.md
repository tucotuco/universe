# Encounters rules — implementation checklist

**Reference baseline:** `Encounters Working Draft.pdf` (67 physical/printed pages) and the reconstructed Universe combat code including `universe-ai-encounter-feedback-fixes.patch`. This is an evidence-based *source-code audit*, not a certified conformance test.

**Checklist semantics:** `[x]` means implemented for the bounded AI armed-duel scenario (not necessarily complete for all encounters). Unchecked items are either **PARTIAL**, **DIVERGENT** (code disagrees with the draft), or **NOT IMPLEMENTED**. Checkbox should be checked only after correcting and testing against the written rules.

**Inventory:** 119 capabilities/rules: 7 bounded implementations; 27 partial; 6 divergent; 79 not implemented. Categories are auditing units, not claims that every sentence of the draft has been separately enumerated.

## Priorities

1. Resolve **DIVERGENT** mechanics first (strategy pool, attack modifier, extra damage, parry, dodge). These change outcomes even in today’s two-combatant duel.
2. Add test fixtures reproducing the printed armed examples before enlarging scope.
3. Implement general defense choice, reach/engagement and simultaneous action timing.
4. Expand weapons, shield, armor, movement, special actions, then new combat types.
5. Keep the AI as decision-maker with the same legal-action validator, not as authority on combat results.

## Encounter initialization and awareness (pp. 6–8)

- [ ] **Encounter as an event with participating Beings** — **PARTIAL** · PDF p. 6. `src/encounter.py`; initial human–Raider pair is seeded, not a general group encounter.
- [ ] **Encounter distance from terrain/weather conditions** — **NOT IMPLEMENTED** · PDF p. 6. No table-driven initial distance resolution.
- [ ] **Spotting modifiers and spotting skill checks** — **PARTIAL** · PDF p. 7. Range-limited geometric awareness, not the spotting modifiers.
- [ ] **Hearing modifiers and hearing skill checks** — **NOT IMPLEMENTED** · PDF p. 7. No general sound propagation or hearing DC.
- [ ] **Surprise detection, advantages and duration** — **NOT IMPLEMENTED** · PDF p. 8. Seeded opponent pair; no formal surprise phase.
- [ ] **Encounter from different independent observers** — **PARTIAL** · PDF p. 8. Separate perceived-opponent snapshots, but no full party encounter logic.

## Time, position and movement (pp. 8–10)

- [x] **One-second combat progression** — **IMPLEMENTED (bounded)** · PDF p. 8. `src/encounter.py`, `src/tactical_duel.py`; each submitted action advances one game second.
- [ ] **Optional six-second rounds** — **NOT IMPLEMENTED** · PDF p. 8. Only one-second stepping in playable encounter.
- [ ] **Simultaneous-time resolution** — **PARTIAL** · PDF p. 8. Preimpact strike eligibility is frozen; not all concurrent effects resolved as an exact simultaneous batch.
- [ ] **Hex-grid occupancy and 12 facing directions** — **NOT IMPLEMENTED** · PDF p. 9. Continuous 2-D coordinates, eight movement directions, no hex-facings.
- [ ] **Movement rates (walk, jog, run, etc.)** — **PARTIAL** · PDF p. 9. Fixed walking increment and a dodge displacement; not table/fitness-based all rates.
- [x] **Movement during prepared attack** — **IMPLEMENTED (bounded)** · PDF p. 9. Position changes can affect range at impact.
- [ ] **Acceleration/deceleration and inertia** — **NOT IMPLEMENTED** · PDF p. 9. No full kinematic acceleration model.
- [ ] **Standing/kneeling/prone posture changes** — **NOT IMPLEMENTED** · PDF p. 9. No player-available pose actions.
- [ ] **Terrain/overland movement penalties** — **NOT IMPLEMENTED** · PDF p. 10. Encounter board does not execute terrain table.
- [ ] **Surface incline and obstruction penalties** — **NOT IMPLEMENTED** · PDF p. 10. Not enforced in playable duel.
- [ ] **Load/carrying-capacity movement effects** — **PARTIAL** · PDF p. 10. `Exertion` tracks light load; no movement penalty table.

## Core attack mechanics (pp. 11–15)

- [x] **d20 attack check versus a difficulty class** — **IMPLEMENTED (bounded)** · PDF p. 11. `src/action.py:roll_hits`, `hit_result` and `MeleeStrike`.
- [ ] **Full Attack Modifier Table** — **NOT IMPLEMENTED** · PDF p. 11. Missing flanking, posture, concealment, shield-hand and much of target size.
- [ ] **Natural-20 threat, critical confirmation and fatal attempt** — **PARTIAL** · PDF p. 12. Core sequence exists; fatal saving throw uses encounter attack DC, not an explicit fortitude DC.
- [ ] **Natural-1 critical failure sequence** — **PARTIAL** · PDF p. 12. Self-hit / weapon drop methods exist; no exhaustive regression against all conditions.
- [x] **Weapon attack motion restrictions** — **IMPLEMENTED (bounded)** · PDF p. 12. `MeleeStrike.on_schedule()` validates swing/thrust against weapon data.
- [ ] **Free-space sweep/trajectory test for swinging** — **NOT IMPLEMENTED** · PDF p. 12. Only a direct geometry ray is checked; no swept arc.
- [ ] **Bludgeon/pierce/slash penetration and armor** — **PARTIAL** · PDF p. 12. `src/armor.py` supports types; scenario has a single armor item and excludes many cases.
- [ ] **Entangle penetration and hindrance** — **NOT IMPLEMENTED** · PDF p. 12. No general entanglement mechanism in duel.
- [ ] **Nonarmor material hardness and object damage** — **PARTIAL** · PDF p. 12. Weapon/object classes carry hardness; no general object-strike playable action.
- [ ] **Facing/front/flank/behind rules** — **NOT IMPLEMENTED** · PDF p. 12. No hex orientation; defense zero from behind not supported.
- [ ] **Weapon-specific attack reach** — **PARTIAL** · PDF p. 13. `src/ai_duel.py:_reach_for` calculates personal+weapon reach; facing/contact geometry omitted.
- [ ] **Engagement and contested approach against long reach** — **NOT IMPLEMENTED** · PDF p. 13. No attack roll to penetrate >3-ft reach advantage.
- [ ] **Disengagement and undefended interruption** — **NOT IMPLEMENTED** · PDF p. 13. Retreating does not invoke general engaged-opponent rules.
- [ ] **Flanking bonus and rear attacks** — **NOT IMPLEMENTED** · PDF p. 13. No multiple-opponent/facing logic.
- [ ] **Saving throws for physical harm** — **PARTIAL** · PDF p. 14. `Being` saving throws and fatal attempt; injury recovery checks absent.
- [ ] **Hit-point injury and incapacity** — **PARTIAL** · PDF p. 14. HP loss and helpless state; full 0/negative HP timelines incomplete.
- [ ] **Natural and magical healing** — **NOT IMPLEMENTED** · PDF p. 14. No healing path in the duel.
- [ ] **Diancecht’s Saving Salve** — **NOT IMPLEMENTED** · PDF p. 14. Not in the playable encounter.
- [ ] **Subdual and separate nonlethal damage** — **NOT IMPLEMENTED** · PDF p. 15. Only ordinary weapon damage.
- [ ] **Massive damage, recoil and action interruption** — **NOT IMPLEMENTED** · PDF p. 15. No 90% death/50% recoil thresholds.

## Strategy, armed action and dice (pp. 15–17)

- [ ] **Allocation across attack, defense, extra damage, timing** — **PARTIAL** · PDF p. 15. Action dialog and `Strategy`; pool and applicability do not match all source rules.
- [ ] **Full strategy point budget from skills, attributes, magic** — **DIVERGENT** · PDF p. 15. Playable duel uses only weapon skill for pool; document adds combat skill and ability modifiers.
- [ ] **Attack accuracy via chosen strategy allocation** — **DIVERGENT** · PDF p. 16. `Action.roll_hits` also adds weapon skill directly, on top of strategy attack, unlike worked example.
- [x] **Defense level applied to hit check** — **IMPLEMENTED (bounded)** · PDF p. 16. Attacker roll in `Action.roll_hits` subtracts defender strategy defense.
- [ ] **Extra damage roll of 1dN, constrained by combat skill** — **DIVERGENT** · PDF p. 16. `Action.do_normal_hit` and critical-hit path add the allocated integer, not roll 1dN.
- [x] **Triangular strategy cost for faster attacks** — **IMPLEMENTED (bounded)** · PDF p. 16. `Strategy.timing_adjustment` implements 1+2+…+n seconds; minimum one second.
- [x] **Weapon table timing by swing and thrust** — **IMPLEMENTED (bounded)** · PDF p. 16. `Action` schedules weapon-specific `St()`/`Tt()`; scenario supports both.
- [ ] **Armed combat skill adds to strategy resource** — **DIVERGENT** · PDF p. 16. Scenario points use weapon skill only, not armed-combat skill.
- [ ] **Armed examples reproducible as acceptance tests** — **NOT IMPLEMENTED** · PDF p. 16. No worked-example fixture matching the published rolls and allocations.
- [ ] **Unarmed combat actions and doubled skill pool** — **NOT IMPLEMENTED** · PDF p. 17. Playable opponent restricted to armed duel.
- [ ] **Ki and damage to unarmed attacker** — **NOT IMPLEMENTED** · PDF p. 17. Not supported.

## Ranged and mounted combat (pp. 17–23)

- [ ] **Archery bows/crossbows and projectile timing** — **NOT IMPLEMENTED** · PDF p. 18. Weapon definitions exist, no playable ranged shot resolver.
- [ ] **Ballista and pellet bows** — **NOT IMPLEMENTED** · PDF p. 18. No ranged scenario.
- [ ] **Catapult/trebuchet attacks** — **NOT IMPLEMENTED** · PDF p. 19. No siege action.
- [ ] **Throwing trajectory and velocity** — **NOT IMPLEMENTED** · PDF p. 19. No thrown-object physics solver.
- [ ] **Time in flight, distance and range increments** — **NOT IMPLEMENTED** · PDF p. 20. Not used by combat engine.
- [ ] **Strength/weight throwing tables** — **NOT IMPLEMENTED** · PDF p. 21. No table-calculated thrown object.
- [ ] **Missed projectile deviation and scatter** — **NOT IMPLEMENTED** · PDF p. 22. Not used in playable encounter.
- [ ] **Throwing modifiers, distance and conditions** — **NOT IMPLEMENTED** · PDF p. 23. No full ranged DC pipeline.
- [ ] **Mounted combat, ride checks, mount speed** — **NOT IMPLEMENTED** · PDF p. 23. No mount in encounter.

## Physical and mental fatigue (pp. 23–26)

- [ ] **Physical exertion/fatigue level tracker** — **PARTIAL** · PDF p. 24. `src/exertion.py`; duel runs periodic combat checks but not all activity transitions.
- [ ] **Fatigue modifies attack capacity** — **PARTIAL** · PDF p. 24. `MeleeStrike.roll_hits` applies Exertion adjustment; not all derived capacity effects.
- [ ] **Recovery from physical fatigue and exertion** — **NOT IMPLEMENTED** · PDF p. 24. No rest/recovery mode.
- [ ] **Mental stress, mental fatigue, concentration** — **NOT IMPLEMENTED** · PDF p. 25. Not integrated into AI duel.
- [ ] **Mental recovery** — **NOT IMPLEMENTED** · PDF p. 26. No mental stress pipeline.

## Equipment, armor and weapons (pp. 26–39)

- [ ] **Time to don/doff armor and ready shield** — **NOT IMPLEMENTED** · PDF p. 26. Equipment is preassigned and cannot be donned in encounter.
- [ ] **Shields as passive protection** — **PARTIAL** · PDF p. 27. `Action` has shield-resolution code; neither duel combatant uses a shield.
- [ ] **Shield impact location, breakage, magical bonus** — **NOT IMPLEMENTED** · PDF p. 27. Not tested in current scenario.
- [ ] **Armor stops selected penetration damage** — **PARTIAL** · PDF p. 28. `src/armor.py`; Raider leather armor receives damage.
- [ ] **Armor itself loses durability** — **PARTIAL** · PDF p. 28. `Action._resolve_damage_to_target_armor`; no exhaustive armor-table tests.
- [ ] **Armor-specific agility and action check penalties** — **NOT IMPLEMENTED** · PDF p. 28. Not generally applied.
- [ ] **All armor materials and body coverage** — **NOT IMPLEMENTED** · PDF p. 29. Only existing scenario equipment is instantiated.
- [ ] **Weapon groups and transfer of weapon skills** — **PARTIAL** · PDF p. 29. Weapon definitions and specific skill levels; transfer rules incomplete.
- [ ] **Weapon length/weight and reach** — **PARTIAL** · PDF p. 31. Length used in `ai_duel.py`; grip/size/facing constraints absent.
- [ ] **Weapon damage/timing tables for all weapon groups** — **PARTIAL** · PDF p. 31. Weapon dictionaries exist; only dagger/longsword used in playable duel.
- [ ] **Special weapon abilities: hooks, entanglement, etc.** — **NOT IMPLEMENTED** · PDF p. 34. Not in resolver.
- [ ] **Individual weapon-specific exceptions** — **NOT IMPLEMENTED** · PDF p. 39. No full text-to-code conformance audit.

## Skills and experience (pp. 45–50)

- [ ] **Skill and experience state on Beings** — **PARTIAL** · PDF p. 45. `src/skill.py`, `src/experience.py`, `src/being.py`.
- [ ] **Experience from legitimate combat attempts** — **PARTIAL** · PDF p. 45. `MeleeStrike` awards practice; full draft advancement system not validated.
- [ ] **Experience thresholds and saving throw advances** — **NOT IMPLEMENTED** · PDF p. 45. Not verified against the complete Experience Table.
- [ ] **Starting skills and racial aptitude** — **NOT IMPLEMENTED** · PDF p. 46. Scripted character setup; no full character creator.
- [ ] **Armed combat skill and specialization** — **PARTIAL** · PDF p. 47. Weapon levels tracked but combined resource rules differ.
- [ ] **Armor/ambidexterity and armor proficiency** — **NOT IMPLEMENTED** · PDF p. 47. No advanced armor use or multiweapon actions.
- [ ] **Balance, terrestrial/aerial/aquatic prerequisites** — **NOT IMPLEMENTED** · PDF p. 47. Not enforced generally.
- [ ] **Blind-fight, extraordinary saves/toughness** — **NOT IMPLEMENTED** · PDF p. 48. Not available in the encounter.
- [ ] **Improved grapple, Ki, escape artist** — **NOT IMPLEMENTED** · PDF p. 48. No grapple/Ki actions.
- [ ] **Quick draw, multi-action, Ride, Run** — **NOT IMPLEMENTED** · PDF p. 49. Not represented as selectable rules actions.
- [ ] **Shield, Stun, Throw and Tumble progression** — **PARTIAL** · PDF p. 50. Tumble practice from dodge; special action effects mostly absent.

## Attack action catalog (pp. 51–59)

- [ ] **Break hold** — **NOT IMPLEMENTED** · PDF p. 51. No holding/grapple state.
- [ ] **Break weapon** — **NOT IMPLEMENTED** · PDF p. 51. No deliberate break-weapon command.
- [ ] **Bull rush** — **NOT IMPLEMENTED** · PDF p. 51. No opposed shove action.
- [ ] **Charge** — **NOT IMPLEMENTED** · PDF p. 52. No compound movement/strike action.
- [ ] **Coup de grace** — **NOT IMPLEMENTED** · PDF p. 52. No special helpless-target finish.
- [ ] **Delay** — **NOT IMPLEMENTED** · PDF p. 52. Wait advances one second but not general delayed-action mechanic.
- [ ] **Disarm** — **NOT IMPLEMENTED** · PDF p. 53. No disarm attempt.
- [ ] **End run** — **NOT IMPLEMENTED** · PDF p. 53. No end-run flanking maneuver.
- [ ] **Feint** — **NOT IMPLEMENTED** · PDF p. 53. No deception/feint contest.
- [ ] **Grab** — **NOT IMPLEMENTED** · PDF p. 53. No grapple precursor.
- [ ] **Grapple** — **NOT IMPLEMENTED** · PDF p. 54. No holds, contested maneuvers or escape.
- [ ] **Multiple actions** — **NOT IMPLEMENTED** · PDF p. 55. Only one new committed tactical action per selection.
- [ ] **Overrun** — **NOT IMPLEMENTED** · PDF p. 56. No overrun movement.
- [ ] **Ready** — **NOT IMPLEMENTED** · PDF p. 56. Attack preparation exists; general conditional ready/trigger absent.
- [ ] **Shield bash** — **NOT IMPLEMENTED** · PDF p. 57. No shield-wielded attack.
- [ ] **Shoot** — **NOT IMPLEMENTED** · PDF p. 57. No ranged attacks.
- [ ] **Strike: swing and thrust** — **PARTIAL** · PDF p. 57. Playable and timed; modifiers, accuracy strategy and extra damage diverge.
- [ ] **Strike an object** — **NOT IMPLEMENTED** · PDF p. 58. No deliberate object target.
- [ ] **Stun** — **NOT IMPLEMENTED** · PDF p. 58. No stun special attack.
- [ ] **Subdue** — **NOT IMPLEMENTED** · PDF p. 59. No nonlethal counter.
- [ ] **Throw** — **NOT IMPLEMENTED** · PDF p. 59. No throwing action.
- [ ] **Touch** — **NOT IMPLEMENTED** · PDF p. 59. No explicit touch action.
- [ ] **Trip** — **NOT IMPLEMENTED** · PDF p. 59. No trip action.
- [ ] **Two-handed strike** — **NOT IMPLEMENTED** · PDF p. 59. No grip mode or multiplier.
- [ ] **Undefended attack** — **NOT IMPLEMENTED** · PDF p. 59. No general special-case attack modifier from occupied victim.
- [ ] **Wrest** — **NOT IMPLEMENTED** · PDF p. 59. No object-wrest contest.

## Defense catalog (p. 60)

- [ ] **Block using shield** — **NOT IMPLEMENTED** · PDF p. 60. No playable active shield block.
- [ ] **Deflect missile** — **NOT IMPLEMENTED** · PDF p. 60. No projectile deflection.
- [ ] **Disengage** — **NOT IMPLEMENTED** · PDF p. 60. No disengage mechanic, only ordinary movement.
- [ ] **Dodge** — **DIVERGENT** · PDF p. 60. Timed attack-target reaction exists, but code uses opposed d20 in place of described defense/timing allocation.
- [ ] **Parry** — **DIVERGENT** · PDF p. 60. Timed reaction exists, but code uses opposed d20 rather than +2 defense and omits required skill gate.
- [ ] **Yield** — **NOT IMPLEMENTED** · PDF p. 60. No one-second backward step with -1 attack modifier.

## General authoring and definitions (pp. 62–66)

- [ ] **Glossary definitions as programmatically checked terms** — **NOT IMPLEMENTED** · PDF p. 62. No systematic ontology or rule vocabulary validation.
- [ ] **Unlabeled 60-cell number grid** — **NOT IMPLEMENTED** · PDF p. 66. Appears to be a source worksheet, not executable encounter logic.

## Audit protocol for subsequent development

- For every change: identify a paragraph/table and page, normalize the rule as an acceptance condition, implement it with source traceability, and add deterministic positive/negative tests.
- Separate **draft defect** from **implementation defect**. Do not silently amend the rule text to fit current code.
- Distinguish the full engine library from features actually exposed to human and AI players.
- For stochastic rules, inject a controllable dice stream so the published worked examples can be reproduced exactly.
- Every completed checkbox should cite its test(s) and, if the rule was clarified, a linked editorial decision.

## Evidence inspected

`src/action.py`, `src/melee_combat.py`, `src/melee_defense.py`, `src/tactical_duel.py`, `src/ai_duel.py`, `src/strategy.py`, `src/exertion.py`, `src/weapon.py`, `src/armor.py`, `src/encounter.py`, `src/being.py`, and `docs/ai-encounter-experiment.md` from the reconstructed post-feedback Universe checkpoint. The user’s local checkout may have further changes; reconcile before accepting checkboxes as current.
