# Combat engagement feedback and effort allocation

This experiment extends the 531-test encounter-control checkpoint. The authoritative world remains `Encounter`/`BeingInstance`/`MeleeStrike`, with the browser showing an observer-filtered projection. No free-standing combat-state model has been introduced.

## Independent movement and action

Movement never cancels a pending attack by itself. A Being can move during preparation. Melee range and path must be valid **at scheduling and again at impact**; an initiated attack that loses reach before impact resolves `out_of_reach` without weapon XP. An out-of-range attack request is rejected before advancing time or canceling any earlier attack. Other requirements (awareness, carried weapon, non-incapacitation) also apply. Movement arrows and attack/guard indicators occupy separate positions around each Being on the map. A star indicates an Action completed in the displayed second; a sword indicates an unfinished attack. The dashed reach ring is currently a reference-position limit in provisional Encounter units, **not** an anatomically correct weapon envelope.

## Strategy distribution

The UI exposes the existing `Strategy` attributes `attack`, `defense`, `timing`, and `extra_damage` as integer allocations. The current prototype caps their sum at the Scout's *Dagger skill rank* (initially two). Offensive points contribute to the existing hit-roll calculation; defensive points to opponents' hit rolls; timing points use `Strategy.timing_adjustment()` to shorten the chosen Action (minimum one second); damage points use existing hit-damage handling. An allocation applies when issuing an attack and persists as the actor's combat stance until changed; movement does **not** reallocate effort. `Guard` interrupts attack preparation and assigns the configured defense amount, or the previous two-point default if none was configured. Allocations are validated before canceling an existing pending action.

This is an explicit experimental budget interpretation of the draft's Strategy, not a fully validated general rule for all skills and actions. In particular, no parry, dodge, feint, block, reactive timing, or detailed engagement geometry has yet been implemented. Defensive reaction actions should eventually use the same scheduler and resource/skill accounting; their timing, eligibility, interactions with existing actions, possible movement, fatigue, and XP must be specified deliberately.

## Observation and damage

When the target is currently detected through the geometric-path perception model, the UI shows present distance, provisional melee reach, and whether the path is clear and in range. The map highlights the reference-position line and reach ring. It does not show hidden information about an unobserved foe.

By **explicit combat-interface convention**, the Scout learns exact HP damage caused by their own completed strikes and measured armor durability damage caused by those strikes. The client also receives a broad characterization (`light`, `substantial`, `severe`) of HP damage **relative to the opponent's modeled maximum endurance**. This is intentionally an approximation, not a revelation of the actual max or remaining HP; it is a provisional gameplay information rule, not a claim that real observers know exact physiological damage. Anatomical hit locations remain unmodeled. The developer audit still has exact objective states.

## Saved Encounters

Journal format version 2 stores player commands (including explicit effort allocations), the Raider's **actual** decision descriptions, and a structured Raider action summary for every simulated second (movement vector, pending attack motion/due time, and completed outcomes). Checksums validate reproduced state, including skill allocations and the Encounter-local random sequence; mismatches reject loading. Legacy command-only version 1 sessions are still accepted and checked. This still reconstructs a **specific seeded duel using unchanged engine rules**; it is not arbitrary Event persistence or a cross-version migration system.

The duel now keeps its own random sequence, isolating combat outcomes from unrelated worlds or temporary save verification. Existing `Action` timing, experience, armor and fatigue continue to be authoritative. The full suite remains available through `bash run_tests.sh`.

## Planned action-menu evolution

A broadly extensible UI should offer actions by function rather than accumulating dozens of main buttons:

- **Movement:** step, reposition, evade, retreat; spatial prerequisites and concurrent actions.
- **Offense:** swing, thrust, feint, grapple; target/instrument and effort allocations.
- **Defense/reaction:** guard, parry, block, dodge; reaction windows and potential interruptions.
- **Awareness/interaction:** assess an adversary, observe surroundings, communicate, use or manipulate equipment.

Each action can eventually expose eligibility, expected duration, current interruptions/conflicts, strategy allocation, fatigue cost, and applicable skill XP before committing a choice. The immediate UI only implements timed melee, guard, waiting, movement, and cancellation; listing future possibilities here does not imply they exist.
