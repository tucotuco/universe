# Universe Fatigue Workbench R4.9 — Universal physical-check table

**Adopted update:** One physical-check fatigue penalty chart for *all* Beings and Fitness values; fixed PCFS coefficient **5** as a rule rather than a configuration parameter. Physiology still determines actual exertion, Q/B changes and action feasibility. The workbench retains an experimental on/off switch for A/B comparison only. The original R4 fatigue engine remains unchanged.

Read these resources first:

- [`APPENDIX-UNIVERSAL-FATIGUE-TABLE.md`](APPENDIX-UNIVERSAL-FATIGUE-TABLE.md): research, exact 121-cell sensitivity comparison, rationale, standardization boundaries, and unresolved issues.
- [`FATIGUE-CONTEST-TABLE.md`](FATIGUE-CONTEST-TABLE.md): one standard 11×11 physical-check penalty table; [`fatigue-contest-table-universal.csv`](fatigue-contest-table-universal.csv) for printing or reuse.
- [`UNIVERSAL-GRAPPLE-VALIDATION.md`](UNIVERSAL-GRAPPLE-VALIDATION.md): two-bout result with standard table vs comparison disabled.
- [`REVISION-4-SPEC.md`](REVISION-4-SPEC.md): existing R4 physiology, now with the adopted standardized physical-check conversion noted in Section 7.
- [`MANUAL-CARD-COMBAT-D-F12.md`](MANUAL-CARD-COMBAT-D-F12.md): demonstration of an **experimental, individualized activity/recovery lookup** for a Fitness 12 grappler. It refers to the **single separately printed universal check chart**, without duplicating it. Individual activity cards remain provisional; they are *not* evidence that separate check tables are needed.

## Start

```bash
python3 -m pip install -r requirements.txt
python3 workbench.py
```

Open http://127.0.0.1:8765, verify header **R4.9 · UNIVERSAL FATIGUE** and optionally `/api/build`. Stop an older server first. Keep this release in its own extracted folder; no browser asset caching is used.

The **Scenario Activity Editor remains above Reference Parameters**. Combat D keeps the original 0.70 Grapple workload, seed, abilities panel, outcomes and the two 180-second bouts with 30-second rest.

## Configuration migration

Older R4.7/R4.8 YAML entries with `physical_check_fatigue_sensitivity: 5` or `contest_penalty_scale: 5` are accepted when loaded and **removed during validation/export**, preserving the adopted value. Any other explicitly configured sensitivity is rejected with an explanation. The fixed check sensitivity is not an editable scenario parameter. The `fatigue_contest_penalty_enabled` switch is retained for controlled comparison only; enabled is the adopted rule.

## What remains configurable

Physiological inheritance, Fitness/abilities, recovery and depletion parameters, physical-output feasibility, activity workload, and combat action programs. Separate physiological profiles are needed for *effects on Q/B and feasibility*, **not for different physical-check charts**. Manual activity reference cards are experimental and currently supported only for Combat D. For each action's tiny B changes, do not round to whole percentages every second and lose all accumulated wear; use longer blocks or carry fractional remainders.

Existing Roman strict-duty, 160 km equine endurance, sprint, ultramarathon, Ironman and combat A–D scenarios are preserved with their respective validation limitations. Do not infer historical or athletic accuracy solely from a seeded scenario's internal feasibility result.

## Tests

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
for f in tests/*.js; do node "$f"; done
```

The R4 engine file's SHA-256 digest should match the R4.8 source exactly. This release changes only check-penalty interpretation, report/export code, documentation, tests and application identity. Digital code uses the reference equation at full precision; paper play looks up the nearest Q/B bands and is approximate at cell boundaries.
