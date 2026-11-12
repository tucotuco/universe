# Armed melee — first integrated combat increment

This increment pivots from exploration-driven realization toward detailed,
personal-scale battles. It preserves the existing `Universe`, `BeingInstance`,
`WeaponInstance`, `ArmorInstance`, `Action`, and `Encounter` implementations;
`MeleeStrike` is a constrained `Action` on the ordinary Encounter timeline,
not a second world state.

Run from the repository root:

```sh
python examples/armed_duel.py --seed 17
bash run_tests.sh
```

## Demonstrated behavior

- Two persistent Human Beings hold separately instantiated weapons; a real
  ArmorInstance can absorb damage and lose durability.
- A Being decides to act toward an aware opponent; swing/thrust action timing
  comes from the weapon configuration. The Encounter advances in explicit
  one-second steps, completing actions only when due.
- Attacks use the existing draft-derived d20 resolution, weapon damage,
  combat Strategy, shield/armor mechanisms, and hit-point mutation.
- Weapon skill is looked up by weapon type, not UUID; a potentially fatal
  hit calls for a defender saving throw. An attack roll of 1 uses its *second*
  roll to determine which critical-failure branch applies.
- Scheduling requires participation, awareness, a weapon actually held by
  the attacker, a supported attack motion, a positive explicit reach, and an
  unobstructed modeled reference-point segment (even transparent solid objects
  block a strike). Damage is re-gated at action completion
  when combatants can have moved, dropped weapons, or fallen in the interval.
- Completed Actions retain an outcome, relative distance, and both Beings'
  hit-point snapshots; the Encounter maintains its existing Event history.

## Deliberate limits and next increments

This is the **first melee exchange**, not a complete battle ruleset. The
Encounter's position frame has not yet established its unit relationship to
weapon lengths (listed in feet in the draft), body reach, or body-part geometry.
`MeleeStrike(reach=...)` therefore *requires* an explicit range limit in
Encounter coordinate units; no hidden conversion or fabricated reach is used.
A straight segment between Being reference points is only a conservative
provisional clearance check, **not** a swept-volume test for swing/thrust
geometry. Any intervening modeled object blocks a strike, even if transparent;
unmodeled potential obstacles also prevent committing the attack. Facing, space
for a swing, shields/cover geometry, stance, engagement, disengagement,
acceleration and collision remain to be developed.

The draft calls for simultaneous effects in one-second rounds; the current
Encounter processes due Actions serially, even if they share a completion time.
The implementation does not yet solve that simultaneity issue. Saving throws,
critical hits, shield mechanics and damage use the existing legacy code except
for the three explicit corrections noted above. No AI combatant chooses these
actions, skill XP is not awarded by this increment, and combat history is not
yet a fully restorable world snapshot. World-wide random state/replay policy
also remains deferred: the example sets Python's RNG seed for one-process
reproducibility.

**Next recommended combat increment:** simultaneous action resolution and
position/facing/reach commitments, followed by defensive reactions and
meaningful movement choices. The detail should be developed from the
*Encounters Working Draft* rather than inventing replacement combat rules.
