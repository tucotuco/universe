# Equine endurance — Objective-based 160 km acceptance test

## Observed benchmark versus modeled test

An FEI 160 km result on 18 October 2024 reports 17.02 km/h average riding speed and 09:23:54 cumulative riding time. This is an **observed benchmark**, not a value predicted by the fatigue model. The workbench sets a 17.0 km/h riding pace as an independent externally required input to examine whether the chosen fatigue parameters can sustain it. That alone cannot validate the workload-to-speed mapping.

The **illustrative six-phase course** is 30 + 30 + 30 + 30 + 20 + 20 = 160 km, with five intervening 40/40/40/40/50 minute holds. These rest times satisfy the phase-length and hold guidelines reflected in 2026 FEI schedules. An **illustrative 15-hour elapsed limit** is imposed. It is **not** asserted as a historically documented deadline for the 2024 result, nor is the illustrative split of distances asserted as that actual event's course.

The rider and horse must meet the same course, speed, holds and deadline. The horse uses its own equine physical fatigue profile; the rider uses a human profile with low mounted-riding workload. No phase may be silently lengthened or lowered to achieve success. If the first participant cannot sustain the prescribed output, **both** histories stop at that point.

## Computed sensitivity results

All outcomes use the **candidate, nonempirical** equine speed-effort calibration (reference speed 17 km/h, corresponding effort 0.495, exponent 1.8, reference Fitness 15, Fitness sensitivity 0.65). Other physiology inputs are from the inherited `equine_illustrative` profile. They are not physiological measurements.

| Required riding speed | Horse Fitness | Fatigue-feasible 160 km + holds by 15 h? | Result |
| --- | ---: | --- | --- |
| 12.0 km/h | 15 | No | Covers 160 km, but misses the 15 h deadline |
| 14.0 km/h | 15 | Yes | Completes with approximately 14.93 h elapsed |
| 16.0 km/h | 15 | Yes | Completes with approximately 13.50 h elapsed |
| 17.0 km/h | 15 | Yes | Completes with approximately 12.91 h elapsed; horse Q approximately 82%, B approximately 65% |
| 17.5 km/h | 15 | No | Required output becomes infeasible before 160 km |
| 18.0 km/h | 15 | No | Required output becomes infeasible before 160 km |
| 17.0 km/h | 14 | No | A less-fit horse fails the identical assignment before 160 km |

**Interpretation:** The candidate model can represent a feasible high-end 160 km ride and nearby failure cases, while respecting hard distance, required pace, elapsed time and holds. This is a stronger functional test than assigning arbitrary exercise hours. However, the coefficients were *selected with this benchmark in mind*, so the successful 17 km/h result is **not independent empirical validation**. Further observed data are required to estimate sensible default equine physiology across populations and individuals.

## Exclusions

- Thermoregulation: **not modeled**.
- Veterinary clearance: **not modeled**; fatigue reserves cannot demonstrate soundness, pulse recovery or broader fitness to continue.
- Physiological energy balance, gastrointestinal function and veterinary illness: not inferred from Q and B.
- Weather effects: not modeled here.
- Course-grade/terrain effects: not included in the default course, although `wear` remains configurable for later nonthermal workload variation.

The candidate continues to use exactly two persistent physical fatigue values (Q and B) per Being. Distance, phase, time, and holds are **scenario progress and requirements**, not additional fatigue variables.

## Next quantitative validation

Collect multiple actual equine endurance results with phase distances, speeds, hold times, and whether horses were eliminated at veterinary checks. Then compare observed completion distributions against predictions across different reference Fitness and physiological-parameter distributions. The current test can establish feasibility consistency but cannot legitimately simulate or predict veterinary elimination.
