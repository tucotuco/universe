# R4.9 — Universal fatigue checks in two resolved Grapple bouts

**Scenario:** 180 s bout, 30 s separation/rest, 180 s bout. Fixed 0.70 Grapple requirement; R4 fatigue engine untouched; same seeded checks (20261026). Both initiating and resisting physical checks use a single universal modifier derived from Q/B. All combat scopes/limitations described in `RESOLVED-GRAPPLE-VALIDATION.md` remain.

| Check fatigue | Control changes | Final Q (Fitness 12) | Final Q (Fitness 16) | Outcome |
|---|---:|---:|---:|---|
| Disabled for A/B comparison | 11 | 24.64% | 84.49% | Both bouts resolved |
| Universal table enabled | 15 | 28.49% | 81.97% | Both bouts resolved |

Changing check modifiers alters the sequence of successful/unsuccessful actions, hence it can change exertion history and reserve remaining. **Final Q by itself is not a combat ranking.** The difference is produced by outcomes of opposed checks, not by extra fatigue states or a second penalty layer.

The standard table is exactly the same for the human Fitness 12 and Fitness 16 participants. Their physical action feasibility and reserve trajectories remain different because Fitness influences their actual physiological parameters and realized workload. The Workbench offers a temporary comparison checkbox, but **sensitivity 5 is fixed** and no longer a YAML parameter or slider.

This is still a resolved Grapple *subset*, not full Encounters combat: no positional pin/takedown/reverse, hits, damage or movement. See [`APPENDIX-UNIVERSAL-FATIGUE-TABLE.md`](APPENDIX-UNIVERSAL-FATIGUE-TABLE.md) for research, the 121-cell computational audit, and limits of the simplification.
