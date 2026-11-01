> **Historical R4.7 report (not the adopted R4.9 standard).** It used earlier individualized or disabled fatigue-check conversion. For current checks, use [Universal Grapple Validation](UNIVERSAL-GRAPPLE-VALIDATION.md) and the [research appendix](APPENDIX-UNIVERSAL-FATIGUE-TABLE.md).

# Physical-fatigue check modifier — two-bout Grapple experiment (R4.7)

**Status:** proposed numerical rule; experimental implementation only. Does not supersede Encounters R60 or ratify the coefficient.

## Rule under test

Continue to track only immediate Q and endurance B. Use the existing Revision 4 physically available output `M(Q,B)` and calculate:

`fatigue_penalty = floor(5 * (1-M(Q,B)) + 0.5)`

Use **one** nonnegative integer penalty on every physically demanding check or opposed contest, whether initiating, maintaining, escaping, defending or resisting. In the presently implemented Grapple subset this includes opposed Touch (d20), Grab, Grapple, Escape, Break hold, and Hold maintenance (3d6). Subtract the penalty from that participant's existing score. Do not change ability values, skill levels, or base Fitness. Apply no additional separate physical-fatigue ability penalty or old categorical fatigue penalty. Mental checks are outside this model.

The penalty is computed against the **shared pre-resolution Q/B snapshot**; exertion from simultaneous actions is committed afterwards. Q and B remain the only persistent fatigue values.

### Table for manual play

`FATIGUE-CONTEST-TABLE.md` and `fatigue-contest-table-f12.csv` contain the full 11×11 grid at 10 percentage-point spacing for a reference Fitness 12 human. At the table, round displayed Q and B to the nearest 10% before the lookup. This coarse lookup can differ by one point from full-precision digital calculation near modifier boundaries. The reference table is an approximation for other Fitness values; the engine uses each Being's actual profile.

## Exact comparison, same seed 20261026

Both experiments use the same action demands (Grapple demand 0.70), abilities, two 180-second bouts and 30-second rest. Only the physical-contest penalty switch changes.

| Measure | No contest fatigue penalty (R4.6 behavior) | Penalty enabled (R4.7) |
|---|---:|---:|
| Grapple control transitions | 11 | 15 |
| Opposed checks | 435 | 413 |
| Opposed checks with at least one nonzero penalty | 0 | 133 |
| Fitness 12 Q at 180s | 42.87% | 48.10% |
| Fitness 12 Q at 210s | 63.86% | 67.17% |
| Fitness 12 Q at 390s | 24.64% | 28.49% |
| Fitness 12 B at 390s | 98.17% | 98.22% |
| Fitness 16 Q at 180s | 91.50% | 90.98% |
| Fitness 16 Q at 210s | 95.00% | 94.69% |
| Fitness 16 Q at 390s | 84.49% | 81.97% |
| Fitness 16 B at 390s | 98.91% | 98.86% |

At the R4.7 end-of-bout checkpoint, the derived integer penalty is **−1** for Fitness 12 and **0** for Fitness 16. At the end of the intervening 30-second rest, both have zero derived penalty. An opposed check involving a fatigued defending participant receives the penalty identically to an attack or initiated check.

**Interpretation caution:** the resulting different contest outcomes change subsequent action histories and fatigue. A larger number of control transitions in this one seeded run does not mean the new modifier always produces more transitions, nor does a slightly higher ending Q mean that fatigue makes a Being stronger. Across 25 different seeds, mean control transitions were 8.44 without the modifier and 8.28 with it (the latter greater in 10 runs, smaller in 11, equal in 4). We therefore interpret the new rule as affecting the contests, not as systematically increasing control changes.

### Known limitations

- Rule scale 5 is provisional; there is no empirical basis yet for the exact contest modifier magnitude.
- This is a resolved *Grapple subset*. It has no damage, movement, takedowns, pins, or full tactics. It is not a complete combat match simulation.
- Grapple physical effort of 0.70 remains unchanged. The workbench distinguishes ability to declare the required effort from the derived physical-check penalty on resolution. These model different questions but arise from the same reserve state; avoid adding the old fatigue effects again.
- Passive check resistance is now penalized when fatigued, but the present simplified resolver does not independently allocate extra fatigue work for every passive resistance check. That workload requires its own physical-demand audit before full combat integration.
- Long-term B remains near 100% over six minutes; longer combat engagements and repeated battles are required to test accumulated fatigue sensitivity.
- Paper lookup uses one common reference table; exact per-Being profile computations remain available digitally and should be reviewed before deciding whether a single paper table is acceptable across species.

## Testing

Run `python3 -m unittest discover -s tests -v` and `node tests/test_resolved_grapple_ui.js`. Tests validate derived rounding, initiating/defending penalties, all implemented physical check types, reproducibility, editable YAML controls, and the comparison on identical seeds.
