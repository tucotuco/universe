# Combat controls, fatigue and checked session journals

This extends the first live tactical Encounter (the 516-test checkpoint) without
introducing a separate combat game state. `TacticalDuel` orchestrates genuine
`Encounter`, `MeleeStrike`, `BeingInstance`, equipment, practice and `Exertion`.

## Play, save, resume, review

```sh
python examples/live_combat.py --open
python examples/live_combat.py --save <save-file> --open
python examples/live_combat.py --load <save-file> --open
python examples/live_combat.py --replay <save-file> --open
```

Use the **Save encounter** button while playing. The default save destination
is `workspace/combat-session.json` (relative to the repository); override with
`--save`. Browser requests never choose filesystem paths. The **Review
timeline** button, arrows and slider inspect the observed state of any
completed second, including the start; **Return to current** resumes live
control. `--replay` starts in read-only timeline mode. Observer filtering is
applied to every historical frame; developer `--audit` deliberately exposes
objective state.

Save files are **versioned command journals** containing a seed, ordered player
commands, and a checksum of the resulting world state at each step. Loading
replays all commands against the **same simulation version** and refuses
mismatches. This restores current state, combat events, skill experience,
fatigue, equipment damage, pending actions, and the full viewer timeline. A
save operation restores the active RNG state after verification; it must not
change the continuing fight. The file is written via same-directory atomic
replacement. This is **not** generic Encounter or Universe snapshot
serialization, and migration between engine revisions is not implemented.
External modifications to a live Being outside recorded commands cause the
save verification to reject rather than silently omit changes. Session files
are local and may include a reproducible description of objective reality.

## Interruptible actions

`thrust`, `swing`, `guard`, and `cancel` may interrupt the Scout's unfinished
attack. An interrupted Action remains in the Universe's Event registry and in
the Encounter's `cancelled_action_list`, with a cancellation time and reason;
it is removed from the pending schedule. It does not inflict damage or award
XP. A replacement attack is validated **before** the former action is canceled,
so invalid replacement requests do not erase it. Each successful command,
including an interruption, advances one second. A finished attack cannot be
undone. The Raider's simple policy does not yet feint or interrupt its attacks.

Movement commands now cover N, NE, E, SE, S, SW, W and NW. Diagonal speed is
normalized, so each step covers `.25` Encounter units in one second. Movement
remains an instantaneous-velocity placeholder without acceleration, obstacles
or collision handling.

## Observer-facing visual feedback

The map shows action symbols beside participants: crossed swords for an
unfinished attack, a guard symbol for defense, and arrows for movement in the
current second. When a geometric path and range cue exists, the Scout receives
**apparent**, not infallible, descriptions of Raider movement and attack
preparation. This currently approximates gesture perception from close
proximity and modeled geometry: lighting, facing, deceptive feints and actual
body motion have not been implemented. Unobserved opponent plans, numeric HP,
skills, XP and fatigue never enter the normal browser response.

Player HP is displayed as current/maximum. The log distinguishes impact and
experience. The **audit** log gives exact objective HP damage, target/actor,
and armor durability change. In the **ordinary explorer** view, exact opponent
HP and armor changes are withheld because the provisional observation model
cannot measure them; the Scout can see its own HP and armor effects.
Anatomical impact location is still *unknown*: the present damage model
applies damage to Being HP and equipment, not modeled body parts.

## Fatigue and experience

The existing `Exertion` class gives a light-load combat check interval of six
seconds. Every due check uses the Being's CON via `Exertion.check`; a failed
check increases the Being's fatigue level, up to 5. Increasing fatigue has
existing level names (`fresh`, `winded`, `tired`, `weary`, `exhausted`,
`incapacitated`), and fatigue adjustment is applied to melee hit likelihood.
Level 5 makes the Being helpless and ends this duel. Combat XP is still
awarded only when a weapon attempt actually occurs, never on cancellation.
Fatigue currently has **no recovery model**, variable load, movement-speed
penalty below incapacitation, or separate defense penalties. These are
important follow-up rule integration tasks, not silently improvised here.
Fatigue checks occur **after** resolving the current second's strikes, so
new fatigue affects subsequent actions.

## Technical boundaries

Same-time strikes freeze attack eligibility but resolve equipment and damage
sequentially. Reach is provisional, and neither the tactical AI nor perception
system is a full decision model. Neither the UI nor the new command journal
replaces the objective Entity state, the existing Action timeline or progressive
skills. Run `bash run_tests.sh` from the repository root.
