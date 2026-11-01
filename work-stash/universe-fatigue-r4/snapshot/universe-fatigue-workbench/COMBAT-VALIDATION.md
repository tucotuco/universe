# Encounters combat-fatigue calibration — R4.5.1

**Status: experimental; not a revision of adopted Encounters mechanics.** The unchanged Revision 4 physical-fatigue reference engine (`universe_physical_fatigue_r4.py`) supplies Q, B, sustainable output and maximum output. The new `combat_calibration.py` supplies declared action preparation times, fixed workload requirements, second-boundary fatigue application, and descriptive event logs. Configuration is in `config.yaml` and `combat-action-schema.yaml`.

## Test A — Weapon duel

Two otherwise comparable human combatants repeat a 6-second longsword strike, a 5-second prepared Parry and one second of delay. The Fitness 12 and Fitness 16 combatants execute identical actions (no wounds or contested outcomes). Timings are consistent with Encounters R60's example and Parry preparation rule. Exertion values are *illustrative*.

| Elapsed | Fitness 12 Q | Fitness 12 B | Fitness 16 Q | Fitness 16 B |
|---|---:|---:|---:|---:|
| 30 s | 91.2% | 99.9% | 98.6% | 99.9% |
| 120 s | 69.9% | 99.5% | 95.3% | 99.7% |
| 300 s | 39.2% | 98.7% | 91.0% | 99.2% |

The system computes a smooth capability divergence under a *fixed prescribed task*. Qualification at a workload limit is deliberately binary; the underlying Q/B curves are continuous. The relative workload-to-Fitness exponent is a hypothesis and may overstate this divergence.

## Test B — Aggressive versus defensive

Both human combatants have Fitness 13. The aggressive fighter declares consecutive 6-second longsword strikes. The defensive fighter prepares 5-second Parries, 2-second Dodges, and delay intervals. Each scripted incoming strike can consume one ready defense; there is no hit-resolution roll.

| Elapsed | Aggressive Q | Defensive Q | Aggressive B | Defensive B |
|---|---:|---:|---:|---:|
| 60 s | 88.8% | 100.0% | 99.7% | 99.9% |
| 180 s | 65.4% | 100.0% | 99.2% | 99.7% |
| 300 s | 40.5% | 100.0% | 98.6% | 99.5% |

**Interpretation:** an attack-intensive workload consumes more immediate reserve than waiting/defending in the authored programs. This is **not evidence that defensive fighting is always preferable**: threats, reach, actions needed to win, successful attacks, movement, and consequences of passive defense are deliberately absent.

## Test C — Grapple, rest, repeat (R4.5.1)

Each participant makes the scripted 4-second Touch preparation and separate 1-second Grab (both assumed successful), then repeats 6-second Grapple-control actions. **Bout 1 lasts 180 seconds, rest 30 seconds, and bout 2 lasts 180 seconds**, including a fresh Touch and Grab at the beginning of the second bout. Total **prescribed** duration: 390 seconds.

The activity demand remains **0.70**, wear **1.10**. With these unchanged demands, the Fitness 12 participant cannot sustain the full first bout. The shared drill **halts after 171 seconds**, when the next second of the Grapple control check becomes infeasible. The second grappler's timeline correctly ends at the same time. No rest or second-bout result is claimed for this default run.

| Elapsed | Fitness 12 Q | Fitness 12 B | Fitness 16 Q | Fitness 16 B | Outcome |
|---|---:|---:|---:|---:|---|
| 171s | 14.18% | 98.86% | 85.33% | 99.32% | Fitness 12 cannot sustain required 0.70 output in next second |

**Feasible sensitivity check, not the default scenario:** changing both combatants' Grapple-action demand to **0.64** in each bout permits completion through 390s (unchanged work durations and fixed rest). For the Fitness 12 participant:

| Elapsed | Q | B |
|---|---:|---:|
| 180s (bout 1 ends) | 62.38% | 99.02% |
| 210s (30s rest ends) | 76.20% | 99.02% |
| 390s (bout 2 ends) | 34.82% | 98.05% |

The original required effort is **never silently reduced**. The activity workload remains a provisional, configurable hypothesis. These tests demonstrate the stress/recovery effect of the shorter rest, not validated wrestling physiology or actual contest outcomes.

## Shared guarantees and important limits

- **No extra persistent fatigue state:** Q and B only. Temporary action readiness and the action clock are encounter machinery, not fatigue reserves.
- **No free work reduction:** a required normalized output is checked against available output every second; a failed attempt stops the shared drill and is reported.
- **Simultaneous action resolution:** decisions resolving in one second read the common pre-action snapshot; fatigue consequences are committed together afterward.
- **Action timing from YAML:** `combat-action-schema.yaml` encodes Strike (weapon), Parry (weapon−1), Dodge (2s), Grab (1s), Grapple (6s), and scenario-authored actions. No Combat Strategy timing reductions or Multi-action modifications are assumed.
- **Prearranged legal action scripts:** reach, positions, initial attack/Grab success, perception, weapon availability, strategy allocation, and successful Grapple-control transitions are not actually resolved.
- **No action-outcome effects:** attacks, dodges, and opposed Grapple contests do not inflict injuries, affect subsequent legal actions, or determine winners. Fatigue sensitivity can be calibrated independently before those effects are introduced.
- **Not an empirically calibrated combat-energy model:** normalized outputs, wear factors, and task/Fitness exponents are editable hypotheses, not measured combat physiology.
- **No thermoregulation**, per project decision.

## Next validation required

Integrate the action workload descriptor with the genuine Encounters action resolver and weapon table, preserving timing allocations, spatial prerequisites, attack results, defenses, true Grapple contests, and its universal same-second state-commitment rule. Only then can we assess combat outcomes, the tradeoff between aggression and defense, and tactical pacing. Those features are intentionally not claimed in this version.
