# Appendix — Evidence and reasoning for the universal physical-fatigue check table

**Status:** Adopted simplification for the Universe/Encounters *physical-check modifier*, October 26, 2026. This does not ratify the separate numerical calibration of all Q/B depletion, recovery, locomotion, or action-workload parameters. **Scope:** physical fatigue; mental fatigue is not changed.

## A. Question and competing designs

The earlier candidate computed a check penalty for each Being from the *Being-specific* instantaneous physical output `M(Q,B)`, with `D = round_half_up(5 × [1−M])`. Because Fitness, inherited physiology, and applicable skills can affect the continuous-output parameters, that design implied many printed Q/B tables. We asked whether those differences materially improved tabletop results relative to a single **reference-defined** standard table.

Fitness is a trainable individual ability reflecting conditioning. It is **not an entire physiological profile**: an equine and a human with Fitness 12 need not have the same workload response or depletion/recovery constants. Q/B dynamics and ability to supply required work therefore remain individual. The experiment below tests *only the integer penalty conversion*, not the validity of a shared physiological response.

## B. Computational sensitivity audit

Using the candidate R4.8 defaults, calculate penalties for the 11 × 11 grid of Q and B remaining from 100% down to 0% in 10-point intervals. For each cell, compare the individualized score computed from a profile's `M(Q,B)` with the reference human Fitness 12 table. The reference values are `c0=.60`, `f_c=.25`, `f_p=.55`, `n=2`, and a check conversion coefficient of 5 with nonnegative round-half-up. Other fatigue parameters (depletion and recovery times) **do not enter this lookup directly**.

| Comparison | Disagreeing cells (121 total) | Maximum difference | Grid agreement |
|---|---:|---:|---:|
| Human, Fitness 6 | 1 | 1 check point | 120/121 = 99.2% |
| Human, Fitness 12 (reference) | 0 | 0 | 100% |
| Human, Fitness 20 | 4 | 1 check point | 117/121 = 96.7% |
| Illustrative equine, Fitness 15 | 9 | 1 check point | 112/121 = 92.6% |

The differing cells are scattered around rounding boundaries; there is no observed multi-point discrepancy on the tested grid. These are **internal model comparisons**, calculated from our provisional configurations, **not observed human/horse equivalence data** and not evidence that every conceivable physiology is close to the reference. A configured exceptional physiology could disagree much more strongly.

In addition, our two-bout seeded resolved-Grapple comparison (180 s bout, 30 s rest, 180 s bout, Grapple demand .70) showed physical-check penalties changing the check sequence while preserving the two-reserve fatigue engine. The R4.7 sensitivity coefficient 5 produced meaningful but not overwhelming effects. That experiment supported choosing the scale 5 as a **game rule**, but did not scientifically calibrate each check point against a measured loss of force or accuracy.

## C. External physiological foundation — and its limits

Research on **critical power / W′** supports modeling sustainable output and a finite capacity for efforts above it, followed by recovery at lower workloads; this supports the broad distinction between fatigue history and task feasibility. Reviews emphasize assumptions and limitations, particularly outside controlled exercise. The R4 implementation is an abstract, configurable extension to heterogeneous activity and other Being types, rather than a literal equation for all organisms:

- Poole et al. (2016), *Critical Power: An Important Fatigue Threshold in Exercise Physiology*, <https://pmc.ncbi.nlm.nih.gov/articles/PMC5070974/>.
- Chorley and Lamb (2020), *The Application of Critical Power, the Work Capacity above Critical Power (W′), and Its Reconstitution*, <https://pmc.ncbi.nlm.nih.gov/articles/PMC7552657/>.
- Review of simulated elite fencing competition (29 fencers), reporting progressive declines in measured muscle torque and rate of torque development across bouts: <https://pubmed.ncbi.nlm.nih.gov/37574844/>.

These sources support fatigue-dependent performance and the utility of reduced-order models; **none establishes that a given Q/B pair must imply the same dice penalty for a human and a horse**. That is intentionally a **game-design standardization**, selected to reduce paper bookkeeping.

## D. Adopted universal mechanical definition

Let Q and B be reserve fractions in `[0,1]`. For check modifiers **only**, define the standardized reference curve:

```text
C_std(B) = 0.60 × (0.25 + 0.75 × B)
H_std(B) = 1 − 0.45 × (1 − B)
M_std(Q,B) = C_std(B) + [H_std(B) − C_std(B)] × [1 − (1 − Q)^2]
Penalty magnitude D = floor(5 × [1 − M_std(Q,B)] + 0.5)
```

`D` is nonnegative and is subtracted **once** from both initiating and defending/resisting physical checks or contests. No extra fatigue-only dice roll, reduced base Strength or Dexterity score, additional penalty for passive resistance, or fatigue-level category multiplier is permitted. PCFS (the former label for coefficient 5) is now a **fixed rule constant**, not a configuration property. The reference is **not used for action feasibility**, which still derives from each Being's own `M(Q,B)` and the action's real workload.

The 10%-step printed table is an approximate manual lookup; the digital simulator uses the same universal equation at the unrounded Q/B state. At exact rounding thresholds and between tabulated bands, tabletop and digital results can differ by one point. Use the exact equation only when the discrepancy matters. This printed table is identical for **all Fitness values, Being types, skills, and physically demanding activities**.

## E. Why this limits proliferation

1. One standard penalty chart is printed **once** for the rules, rather than once per Fitness/species/activity.
2. Only **Q and B** are persistent fatigue quantities. The check penalty is derived at resolution time.
3. Physiological configuration remains available for **Q/B evolution, physical capabilities, activity costs, and recovery**. Those effects can still vary widely across Beings.
4. The harder tabletop problem—updating Q and B without evaluating coupled equations—**is not solved by universalizing the penalty chart**. We retain the experimental activity-card exporter as a test instrument while designing a small, broadly reusable set of workload and recovery aids. Combat's very small per-action changes in B must not be rounded away.
5. The standard table is binding by design even if future physiological tuning would have produced a different individualized penalty. Exceptional physiology would require an explicit later rules decision rather than silently generating another table.

## F. Findings and remaining validation

**Adopted:** one shared 11×11 check table, standardized reference curve, coefficient 5 fixed, no Q/B table per Being. **Retained:** individual action feasibility and Q/B evolution using inherited physiological configuration, scenario objectives and non-negotiable workload requirements. **Still under evaluation:** numeric workload and recovery calibration across activities, manual activity-card ergonomics, physical-check outcomes in more complete combat resolution, and how a unified tabletop activity table can use the existing Encounters activity definitions without proliferation.

The internal sensitivity audit justifies the **simplification within the candidate parameter space tested**. It does not imply a validated, species-independent biological law.
