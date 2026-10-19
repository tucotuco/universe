# Melee impact rules, action continuity, and defensive reactions

This increment follows the 542-test combat engagement/effort checkpoint. It changes attack scheduling, implements bounded one-second parry/dodge reactions, and makes active actions visible in the Scout log and UI. `Encounter`, `Action`, `BeingInstance`, held Weapons and ordinary `SkillUse` remain authoritative.

## Reach at impact only

An aware attacker holding a compatible weapon can schedule a swing/thrust even if the target is currently out of reach or behind an obstruction. The attack takes its usual time and can be canceled/replaced during preparation. **Only at resolution**, after the interval's movement, does `MeleeStrike` check target readiness, equipment availability, reach and the physical path. An out-of-reach or blocked strike causes no attack roll, hit, damage or weapon XP. By contrast, an attempted strike that misses or is successfully parried/dodged still earns its normal weapon XP. Awareness at scheduling remains a separate precondition, not a reach check.

Guard is a *sustained Being strategy* (`defense` effort), not an unfinished one-second Action. Movement and waiting do not end it; beginning an attack/reaction or explicitly canceling replaces it. Attacks remain scheduled while moving. The browser now reports `Guarding (sustained)`, pending attack/reaction with due time, or the action completed in the current second; the event log reports the Scout's current activity independently from movement. Movement, attack, guard and reaction cues occupy distinct map positions. If a Swing completes during a step, the UI says so instead of ambiguously showing `Idle`.

## Parry and Dodge — designated attacks and readiness at impact

`MeleeDefense` targets the **identity of one pending incoming `MeleeStrike`**, not the attacker or whichever attack comes next. The current duel UI binds to the single attack being prepared by the Raider if its source is currently perceived. The objective action ID is kept in the Encounter; the Scout UI receives only an apparent incoming-attack cue, not a complete adversary action specification.

- **Parry:** preparation is the faster of the held weapon's configured swing/thrust times, minus one second (minimum one). With the Scout's dagger, that is **three seconds**. A parry readied before the chosen strike remains committed to that strike until its impact; then a provisional weapon-skill contest can deflect it. An interrupted/canceled strike does not cause the parry to switch to a later attack.
- **Dodge:** preparation is **two seconds**. The 0.5-unit displacement occurs in the second the designated strike impacts, not at the moment the player declares the dodge. This can avoid the blow by moving out of reach; otherwise a provisional `tumble` contest may defend. Ordinary movement can proceed while the dodge is prepared; Dodge itself can be canceled/replaced.
- **Eligibility and practice:** if the designated strike cannot be defended in time, the proposed defensive action is rejected without canceling the Being's existing action or advancing time. A completed defense against a real threat can earn 10 XP for its relevant weapon or `tumble` skill. If the designated strike was canceled or rendered irrelevant, the defense resolves `no_threat` without XP. Both defenses run before their target's strike at the same scheduled impact instant.

This is an initial interpretation of the draft's timing convention; no weapon-path trajectory, facing, or multiple-threat coordination is represented. The command journal now has **version 3**. Its replay reconstructs target selection deterministically from the observed state, and checks resulting states; version-1/2 sessions are accepted structurally, but those involving reactions governed by changed timing rules can fail semantic replay verification. Version-2 sessions without such reactions remain replayable when outcomes match. The new design does not rewrite old saved histories.

## Remaining boundaries

No facing, anatomically grounded defensive arcs, weapon-length collision geometry, complex movement collisions, feints, blocking, shields used as parrying instruments, multi-attacker allocation, full simultaneous consequences or complete fatigue accounting. The visual model's reach ring is a provisional reference-point distance. Perceptions remain narrower than objective audit state. This milestone establishes scheduling, physical displacement, a contest, actual practice XP and historical traceability—not a finished tactical combat model.
