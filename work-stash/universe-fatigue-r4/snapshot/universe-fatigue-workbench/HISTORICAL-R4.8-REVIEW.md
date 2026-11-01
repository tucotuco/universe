> **Historical document — superseded by R4.9.** The former configurable PCFS and individualized tables described below are no longer active. See [Appendix — Universal Table](APPENDIX-UNIVERSAL-FATIGUE-TABLE.md).

# Fatigue Workbench R4.8 — Manual play and contested-check sensitivity

**Status:** Experimental fatigue calibration, not ratified rules. The Revision 4 mathematical engine remains unchanged.

## 1. Workbench changes

- The **Scenario Activity Editor** now appears **above Reference Parameters**.
- The former `contest_penalty_scale` is formally named **Physical Check Fatigue Sensitivity (PCFS)**, stored as `physical_check_fatigue_sensitivity` in the scenario YAML, default **5.0**. Existing files using the old key remain importable, but using both keys in a single scenario is rejected.
- PCFS is visible as a slider (0–20) in Combat D, with its numeric setting displayed. The selected Being's resulting *current* check penalty appears beside the graph. Increasing PCFS alters the dice penalty, not the underlying fatigue equation; it may indirectly change Q/B by changing the encounter's decisions and successful actions.
- The comparison section highlights action-seconds spent grappling and recovering, and counts infeasible actions to make non-monotonic final reserve results intelligible.
- **Export manual-play reference card** (currently enabled for Combat D only) generates a Markdown sheet for the selected Being with an 11×11 Q/B penalty table and precomputed activity/recovery lookup tables based on the *actual selected configuration*.
- A sample generated reference card for the default grappler is included in the package.

## 2. What does PCFS mean?

The game-mechanical rule is:

`penalty = floor(PCFS × (1 - M(Q,B)) + 0.5)`

where `M` is current maximum available physical output as a fraction of that Being's fresh peak. PCFS has units **contest/check points for a complete fractional loss of available peak output**. Thus at PCFS = 5, 20 percentage points of lost output correspond to one penalty point *before rounding*; this is not a metabolic constant or a claim that muscular strength falls linearly with game check success.

Apply the resulting modifier **once** to every physically demanding check or opposed contest. Do not also reduce underlying ability values or apply the old fatigue-state penalties. Mental checks are unaffected. The modifier is evaluated using the shared pre-action fatigue snapshot.

## 3. Do we need twenty tables?

**No fixed catalog is required.** The table is derived from Q, B, PCFS, and the Being's effective physiological parameters: fresh sustainable output, sustainable/peak floors, and the fast-reserve response exponent. Fitness can influence some of those physiological parameters, as can Run skill when it applies to running and inherited physiological definitions. Strength and Dexterity influence the *underlying contest modifiers* but do not directly select the Q/B fatigue table in this implementation.

Under the bundled parameter defaults, among the 121 lookup cells, the generic human Fitness 12 table differs from the human Fitness 6 table in only **1 cell**, from human Fitness 20 in **4 cells**, and from the illustrative equine profile (Fitness 15) in **9 cells**. These are **specific consequences of the current proposed configuration**, not universal similarity guarantees. A general reference table may be a useful quick approximation, while an exact printed table can be generated for a Being or physiological reference when needed.

## 4. How to track activity fatigue on paper

The contest lookup solves the *effect* of fatigue, not its accumulation. Activity-specific cards must supply the changes to Q and B. The new manual-card exporter generates them from the same R4 `evolve` calculation used by the simulator; they are not arbitrary fixed deductions.

For example, with the default Fitness 12 human, starting Q=100%, B=100%, and executing the configured six-second Grapple control effort at normalized demand 0.70, the card predicts Q≈**97.0%**, B≈**99.96%**. If the starting Q were 50% (B still approximately 100%), the analogous update is Q≈**47.0%**, B≈**99.96%**. A 30-second rest starting Q≈50% restores Q to approximately **68%**.

The activity tables use 10%-step starting Q and 25%-step starting B bands for convenient lookup, with final Q to 0.1% and B to 0.01% to expose small contributions. The numbers are approximations when looking up between bands and cannot preserve perfect resolution under repeated manual rounding. **Never round B to whole percentages after each 1–6 second action and discard the remainder:** that would prevent gradual accumulated fatigue in paper play. For travel, update B over meaningful longer blocks; for combat, track fractional B or accept explicitly coarser, less accurate resolution.

The only persistent variables remain Q and B. Neither the modifier nor the action-work cost is an additional tracked resource. If the workload is infeasible, the cell is marked `X` and the character must take a legal alternative; the required action is not silently downgraded.

## 5. Explaining Fitness 10 versus 10.5 (default seeded Combat D)

| Fitness | Final Q% | Seconds grappling | Seconds recovering | Infeasible declarations |
|---|---:|---:|---:|---:|
| 10.0 | 25.34 | 121 | 40 | 40 |
| 10.5 | 21.67 | 127 | 18 | 18 |

At Fitness 10, the combatant is forced to recover much more frequently. That can leave *more unused reserve at the end* even though the combatant performs fewer strenuous actions. In addition, changing the fatigue-generated roll modifier can alter who wins a check, which changes subsequent actions. A fixed random seed permits exact replay of **one configuration**; divergent action paths do not ensure that every subsequent check consumes the same dice. Therefore, final Q alone is not a monotone measure of combat success.

For controlled physiological testing, prescribe the same external action schedule; for actual combat trials, inspect action opportunities, successful contests and achieved objectives in addition to Q and B.

## 6. Verification

Run `python3 -m unittest discover -s tests -p 'test_*.py' -v`; run `node tests/test_r48_ui.js` and the existing Node tests if available. Manual cards can also be generated from the command line:

```bash
python3 manual_cards.py --config config.yaml --scenario combat_d_live_grapple --actor 'Grappler Fitness 12' --output my-fatigue-card.md
```

R4.8 does **not** change physiological equations, original 0.70 Grapple workload, the 180/30/180 bout schedule, or the strict Roman legionary and objective-based equine validation rules.
