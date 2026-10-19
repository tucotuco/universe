# Live tactical combat: first player-controlled encounter

This extends the 503-test combat visual replay. The browser no longer only
scrubs a prerecorded trace: each choice is submitted to a local Python server,
and the next one-second step is simulated by the existing authoritative
`Encounter`, `MeleeStrike`, `BeingInstance`, equipment and skill system.

## Try it

From the repository root with the Universe Python environment active:

```sh
python examples/live_combat.py --open
```

If the browser does not open automatically, visit the **exact** localhost URL
printed by the command. To use a stable port instead:

```sh
python examples/live_combat.py --port 8765 --open
```

`--seed 392` selects a different combat random stream. `--audit` is a developer
mode that exposes objective opponent state. Stop the server with Ctrl-C. This
is a local one-player prototype, not a multi-user/networked game. Nothing is
sent to an external service; the browser communicates with Python over
127.0.0.1. Each fresh start creates a new Encounter; saving/restoring is not
implemented.

## Controls

- **Thrust**, **swing**: schedule a real `MeleeStrike` with weapon-defined
  action duration. The default dagger thrust completes after four seconds.
  Only a completed real attempt awards weapon experience (10 XP per attempt,
  using the existing progressive-skill system). A canceled action awards none.
- **Guard**: commit the Scout to the actual existing defensive `Strategy`
  (+2 defense effort), which influences subsequent hit checks. It persists
  until the Scout attacks. No unmodeled defensive-skill XP is claimed.
- **North / South / East / West**: move 0.25 Encounter coordinate units over
  one second, even while an attack is pending. No terrain, collision,
  acceleration, or stamina simulation has been invented.
- **Wait**: advance one second without a new player action.

The Raider uses a minimal policy: strike if within explicit reach and a modeled
path is available, otherwise move toward an observed Scout. It is **not** a
complete Agent decision-making system. Range-limited geometric path perception
establishes a *current positional cue*, not physical eyesight or durable
tracking; non-observed opponent positions and private stats are withheld from
the standard HTTP response entirely. The default UI is therefore an
explorer-facing filtered view, not merely a visually hidden audit trace.

## Equal-time attacks

`Encounter.resolve_actions` now freezes **eligibility for an attempted melee
strike** for all Actions with the same completion time *before* the first
impact at that time. An attacker who is incapacitated by an equal-time strike
still executes their own already-completing strike and receives experience
for an attempt. A strike finishing at a **later** time can be canceled by
incapacitation at an earlier time.

This is a bounded simultaneous-eligibility improvement, not a fully simultaneous
physical-effects engine. Damage and armor/shield mutations still run in a
stable Event order; interactions with shared equipment, interrupts, area
effects and cumulative mitigations need a separate multi-phase resolution
contract. This distinction is deliberate and tested.

## Remaining limitations

Personal facing, impact contact geometry, action interrupts, body-specific
reach, actual vision/hearing, collision detection, environmental features,
opponent uncertainty and autonomous tactics are not established. Reach is
currently an explicit number in Encounter units, rather than a verified
conversion from the weapon lengths in the combat draft. The initial protective
body envelope is a `Sphere` used only for geometric-path detection.

The session is in-memory and single-process. The seed makes the local dice
sequence reproducible but does not define general Universe-wide RNG or save
semantics. Movement and guard are not yet separately recorded as persisted
Action Events, whereas melee strikes and their XP are.

## Validation

```sh
bash run_tests.sh
```

Expected against the 503-test visual replay checkpoint plus this patch:
**516 tests, all passing**. Browser endpoints have tests for correct use of
authoritative game state, current perception filtering, JSON command handling,
Origin and Host rejection, and failure without time advancement.
