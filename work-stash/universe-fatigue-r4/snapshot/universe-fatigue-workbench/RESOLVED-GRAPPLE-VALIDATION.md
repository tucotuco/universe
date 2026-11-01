> **Historical R4.6 report (not the adopted R4.9 standard).** It used earlier individualized or disabled fatigue-check conversion. For current checks, use [Universal Grapple Validation](UNIVERSAL-GRAPPLE-VALIDATION.md) and the [research appendix](APPENDIX-UNIVERSAL-FATIGUE-TABLE.md).

# Encounters Grapple resolution: R4.6 baseline (fatigue check modifiers disabled)

**Status: experimental partial combat resolver.** This extends the R4.5.1 controlled fatigue drills with a *new* resolved grappling encounter. It does not replace adopted Encounters R60 and does not introduce additional fatigue reserves. The R4 engine file is unchanged.

## Reference objective and assumptions

- Two three-minute grappling bouts, with 30 seconds of complete separation and low-effort recovery between bouts. Both actors continue across the entire 390-second schedule even after an individual prescribed action becomes infeasible.
- Two Medium Beings are in close reach and aware of one another throughout the match. Movement, injuries, damage, disarms, weapons, positional Takedown/Reverse/Pin, and the Combat Strategy timing allocation are deliberately disabled.
- Initial contact is **Touch, 1 second** for unwilling Beings within reach, using opposed d20 + attack level vs d20 + defense level, followed by a separate **Grab, 1 second**, using an opposed 3d6 check. Neither is automatically successful.
- Physical **Grab/Hold** is independent of **Grapple**. Each physical Hold is checked at six-second intervals with the opposed Grab check. The one special substitution at the coincident **first** Grapple check is observed. Losing a physical Hold does not automatically end an already-established Grapple.
- Grapple uses **one opposed 3d6 check** for the two participants, each adding Improved Grapple, the better Strength/Dexterity bonus, and any armor modifier. A declaring Escaper also adds Escape Artist. Tie preserves the current control position. Timing is six seconds without acceleration.
- Grapple Escape ends the opponent's least restrictive established Grapple on victory, but **does not break** any physical Hold. Breaking a Hold is a separate one-second 3d6 + Strength bonus contest. Action changes do not retroactively invalidate same-second outcomes.
- A simple, explicitly experimental action-choice policy tries to obtain Grapple control, Escape when controlled, or Break hold when independently gripped; otherwise it tries Touch/Grab. If the needed declared exertion is not feasible, the actor spends that second recovering. The opponent continues. This baseline test retains the R60 check modifiers **without** a derived fatigue dice penalty. **R4.7 adds the optional test rule** described in `GRAPPLE-CHECK-FATIGUE-VALIDATION.md`, which applies one Q/B-derived modifier to every physically demanding check, including passive resistance.
- All action outcomes are evaluated against the same pre-second states. Q and B consequences commit together after outcome resolution. Opposed dice use a configurable fixed random seed for repeatability; changing the seed changes the contest history.

These rules constitute a useful **genuine check-and-control subset**, not the full Encounters combat resolver. In particular, the one shared control position intentionally represents only the **least restrictive** Grapple control state, so no claims are made about takedown, pin, reverse, reach, multi-grappler positional effects, or combat winners.

## Default action costs and skills

The original 0.70 Grapple requirement and 1.10 slow-wear parameter are retained. Other physical demands are YAML-defined and provisional, not empirical measurements. Configuration includes action costs (Touch, Grab, Grapple, Escape, Break hold, Rest, Recover), five skill/check properties per Being, three fixed phases, and a random seed. The initial Being values are Fitness 12 versus Fitness 16, Strength 13, Dexterity 12, Improved Grapple 4, Escape Artist 2, and attack/defense levels of 2. All may be modified without altering the engine.

The first 3-minute bout and the second 3-minute bout are separated by 30 seconds of recovery. At bout separation the existing Grapple and physical Grabs are deliberately released, but neither Q nor B is reset.

## Sample deterministic result — seed 20261026

| Moment | Fitness 12 Q | Fitness 12 B | Fitness 16 Q | Fitness 16 B |
|---|---:|---:|---:|---:|
| End of bout 1, 180 s | 42.9% | 99.0% | 91.5% | 99.5% |
| After rest, 210 s | 63.9% | 99.0% | 95.0% | 99.5% |
| End of bout 2, 390 s | **24.6%** | **98.2%** | **84.5%** | **98.9%** |

The resolved control changes 11 times during the two bouts. Both participants make Touch attempts, separate Grab attempts, six-second Grapple checks, individual Hold-maintenance Grab checks, Escapes, and Break-hold attempts. Workloads, dice results, legal actions, and outcomes are available in the collapsible encounter log.

**Do not compare these results directly with the previous 171-second failure of the controlled 0.70 Grapple drill.** The old drill required the same continuous exertion as if grappling had been successfully established and sustained. The new experiment incorporates unsuccessful attempts, Break holds, Escapes, and other action choices, so it imposes a different actual workload while preserving the individual 0.70 Grapple demand.

### Verified infeasibility behavior

For a test-only increased Grapple demand of **0.75**, the Fitness 12 participant encounters multiple infeasible Grapple declarations, but the 390-second encounter **does not stop**. The other participant's action and fatigue timeline continues to 390 seconds. This checks that failing a chosen action is not silently interpreted as failing the entire combat objective. It does **not** prescribe which tactic a real agent would select instead; the workbench's fallback policy is a test hypothesis.

## Limits and next steps

1. Validate the baseline probability and time distribution of initial Touch/Grab, and qualify with positional/reach checks.
2. Add normal combat strategy/timing allocations, other Grapple positions and their permitted transitions, movement and multiple attackers.
3. Derive or test capability limitations on contested defense rather than introducing arbitrary fatigue penalties.
4. Restore hits/injury/damage once fatigue and control outcomes have been separated and validated.
5. Couple this subset to the actual Universe Encounter action scheduler before claiming full combat integration. The current engine and workbench reside in this package only.

## Verification

Run `python3 -m unittest discover -s tests -p 'test_*.py' -v`, `node tests/test_abilities_ui.js`, and `node tests/test_resolved_grapple_ui.js` (Node optional). The test suite includes the old strict legion, equine endurance, and scripted-combat regressions, plus real opposed checks, fixed-seed replay, split Hold/Escape semantics, action infeasibility without stopping the encounter, and schema validation. The browser screenshot test is not considered passed if Chromium times out in the environment.
