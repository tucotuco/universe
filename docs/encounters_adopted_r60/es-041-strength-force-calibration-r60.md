> **Revision 59 update:** Earlier passages below document prior investigations and proposals, including the former 0.7865 m reference. They are historical and superseded where inconsistent with the adopted revision-59 decisions. See the ratified summary at the end.

# ES-041 — Objective Strength-to-force calibration evidence (Revision 57)

## Adopted decisions (Revisions 54–57)

Maximum physical force capacity is a **Being-level characteristic**, grounded primarily in Strength and bodily attributes. Calibrate against the abilities the rules already grant that Being, rather than imposing unrelated force values for Pull, Bull rush, lifting and throwing. The dice contest only decides whether a maneuver succeeds. Applied force is represented in newtons (N); the intrinsic capacity and contextually effective applied force remain distinct.

## 1. Static or quasi-static lifting reference

The Carrying Capacity Table, combined with the Throwing section's statement that a Being can pick up any load up to the heavy-load limit, gives a direct force *reference*: if a load weighing `W` pounds is supported against standard gravity, the upward force must match `W × 4.448221615 N` (neglecting acceleration). Derived values:

| Strength | Heavy-load maximum (lb) | Required upward support force (N) |
| ---: | ---: | ---: |
| 5 | 50 | 222 |
| 10 | 100 | 445 |
| 15 | 200 | 890 |
| 20 | 400 | 1,779 |
| 23 | 600 | 2,669 |

These are *not* proof that the Being's absolute maximum muscle force equals the values. The Being may exert greater forces briefly or lower forces for a different direction, grip, joint configuration, duration or traction. The sampled rows are for the existing table and do not establish scaling for every anatomy or size.

## 2. Dynamic throwing evidence and clarified limits

The Throwing Table lists **(a) maximum weight throwable at all** and **(b) maximum achievable launch velocity under favorable load conditions**; those values do not describe a single object thrown at both extremes. The Velocity versus Weight Table specifies what fraction of maximum velocity is possible for a given fraction of maximum liftable weight. Together they constrain kinetic energy, momentum and potentially muscular work; they **do not determine force uniquely** without launch acceleration length/time.

For illustration only, at Strength 10:

- Heavy-load capacity = `100 lb` and maximum projectile velocity in the table = `22.5 yd/s`.
- For a `5 lb` object (`5%` of heavy load), the weight-velocity table gives `47%` of maximum velocity: `10.575 yd/s ≈ 9.67 m/s`.
- The object mass is `2.268 kg` and kinetic energy is approximately `106 J`.
- **If** it accelerated from rest over `1 m` at constant average accelerating force, `F_avg = mv²/(2d) ≈ 106 N`. For a `0.5 m` path the estimate is `212 N`. These are conditional examples, not measurements or adopted game forces; varying stroke length yields different results.
- Throw skill can increase effective launch speed under the source rules. That cannot automatically be interpreted as increasing innate maximum force capacity rather than improving mechanics and efficiency.

### Strength-indexed evidence dataset (existing table values; calculated SI columns)

This comparison preserves the original carrying and throwing values for Strength 3–23; the reference support forces and meter-per-second velocity columns are conversions, **not newly adopted force-output rules**. The Throwing Table also extends to Strength 30, while the Carrying Capacity Table instead provides a `+5 → ×2` scaling convention above its listed range. Do not interpolate that convention into a distinct physical law without checking its meaning.

| Strength | Heavy-load limit (lb) | Lift reference (N) | Table max throw weight (lb) | Table max velocity (m/s) |
| ---: | ---: | ---: | ---: | ---: |
| 3 | 30 | 133 | 15 | 4.57 |
| 4 | 40 | 178 | 20 | 6.86 |
| 5 | 50 | 222 | 25 | 9.14 |
| 6 | 60 | 267 | 30 | 11.43 |
| 7 | 70 | 311 | 35 | 13.72 |
| 8 | 80 | 356 | 40 | 16.00 |
| 9 | 90 | 400 | 45 | 18.29 |
| 10 | 100 | 445 | 50 | 20.57 |
| 11 | 115 | 512 | 58 | 22.86 |
| 12 | 130 | 578 | 65 | 25.15 |
| 13 | 150 | 667 | 75 | 27.43 |
| 14 | 175 | 778 | 88 | 29.72 |
| 15 | 200 | 890 | 100 | 32.00 |
| 16 | 230 | 1023 | 115 | 34.29 |
| 17 | 260 | 1157 | 130 | 36.58 |
| 18 | 300 | 1334 | 150 | 38.86 |
| 19 | 350 | 1557 | 175 | 41.15 |
| 20 | 400 | 1779 | 200 | 43.43 |
| 21 | 460 | 2046 | 230 | 45.72 |
| 22 | 520 | 2313 | 265 | 48.01 |
| 23 | 600 | 2669 | 300 | 50.29 |

The listed maximum thrown weights are consistently approximately **half the corresponding heavy-load limits**. **Revision 55 confirms that this is an absolute throwability limit**, not the heaviest object that can reach the adjacent hex at 5 yd/s. A maximum-weight object may depart the hand at very low velocity. Therefore these weights are useful capacity constraints but do not by themselves establish the force required to achieve an effective throw or a maximum-distance trajectory.

## 3. Resolved definition; remaining throwing-velocity baseline question

**Resolved by the author (Revision 55):** The Throwing Table's `Max Weight` is the greatest weight that the Being can **throw at all**, **not** the heaviest object that reaches the minimum effective throwing velocity of `5 yd/s` for an adjacent hex. At Strength 10, 50 lb is the absolute throwability limit; the 100-lb heavy-load maximum is a separate lifting capability.

The previously flagged numerical combination is now **consistent** under that distinction: 50 lb is 50% of the lifted maximum, and at 4% of the table's `22.5 yd/s` maximum speed the 50-lb object's theoretical throw speed is `0.9 yd/s`. It does **not** satisfy the `5 yd/s` requirement for an effective adjacent-hex throw, but it can still be **thrown at all**. At 15% of lifted maximum (15 lb), 24% of `22.5 yd/s` is `5.4 yd/s`, so that table row is above the effective threshold. This illustrates the different constraints, not a new independently adopted maximum-effective-weight formula. Do not apply the maximum throw speed/distance columns to the maximum-weight object.

**Resolved in revision 56:** A progressive skill, once acquired, starts at **level 1**. The Throwing and Velocity-versus-Weight prose gives a one-time `+1` velocity modifier for having **any** Throw level; it does not accumulate by skill level. Thus at Strength 10, the tabulated `22.5 yd/s` is `5 × (10 + 1 − 2)/2`, the acquired-Throw baseline. An untrained ordinary throw at level 0 uses the same equation with modifier `0`, yielding `20 yd/s`. This reconciles the table and formula; the throwing table itself is unchanged. Other skill levels must not be silently treated as per-level velocity bonuses.

## 4. Standard arm length indexed by Size Category (revisions 57–58)

**Author's decision:** Arm length should be simplified by **basing the standard length on the Being's size class**, represented in this manuscript by **Size Category**. Use a single category-derived reference arm length for standard throwing-force calibration, rather than defining the arm length separately for each Being.

| Size Category | Numeric category | Standard arm length |
| --- | ---: | --- |
| Diminutive | 0 | To be calibrated (m) |
| Tiny | 1 | To be calibrated (m) |
| Small | 2 | To be calibrated (m) |
| Medium | 3 | **0.7865 m (78.65 cm)** — adopted |
| Large | 4 | To be calibrated (m) |
| Huge | 5 | To be calibrated (m) |
| Gargantuan | 6 | To be calibrated (m) |
| Colossal | 7 | To be calibrated (m) |

**Adopted Medium calibration (revision 58):** The standard arm length for **Medium (category 3)** is **0.7865 m = 78.65 cm**. Here, “arm length” is the straight-arm shoulder-tip (**acromion**) to middle-fingertip (**dactylion**) measurement, **including the hand**, not merely upper-arm length or shoulder-to-wrist length. The value comes from the *reported mean* of the adult-male ANSUR II sample; the independently tabulated male median is approximately 78.6 cm. The source population comprised **4,082 U.S. Army men**, not a statistically worldwide-representative sample. The chosen value is an empirical geometry default for **all Medium Beings in this rule model**, not a claim about any individual's anatomy. Use **0.7865 m** for calculations and **0.79 m** only as a rounded description. Sources: [U.S. Army ANSUR II database](https://ph.health.mil/topics/workplacehealth/ergo/Pages/Anthropometric-Database.aspx), [ANSUR II male percentiles](https://ergoassessment.cam/ansur-2-data-explorer/), and [published citation of the ANSUR II male mean (78.65 cm)](https://www.ibew.org.uk/dvarch/DV04307.pdf).

The manuscript's *effective size* factors (`0.5, 1, 2, 4, …, 64`) are game-mechanical Grab/Grapple quantities. **They cannot be repurposed as measured body lengths or a length scaling law**. Do not silently invent a reference-length table from those factors.

**Different quantities:** Reference arm length is a geometric property derived from Size Category. Projectile acceleration distance depends on the throwing motion and is **not specified just by arm length**. Deriving actual average force in newtons still requires an adopted physical relation between the category-derived reference geometry and the motion; the conditional `m v²/(2d)` formula has not become an action rule. Personal **combat reach** also retains its separate Reach-section semantics and center-to-center convention; this rule does not make it identical to reference arm length.

The size-indexed reference policy is **adopted**, and the **Medium** reference is now **0.7865 m**. Other seven numerical lengths, the scaling convention, how motion uses geometry, and any future nonstandard body-plan treatment are **open**, not automatically approved exceptions.

## 5. Proposed calibration workflow (not yet mechanical law)

1. Treat the meaning of maximum throwable weight and Throw skill modifier as confirmed; verify other table arithmetic and separately evaluate all physically relevant throwing assumptions.
2. Build the empirical reference pairs for each Strength score; convert pounds of supported weight to newtons, pounds mass to kg, velocities to m/s, and account for any source qualifications.
3. Retain the Medium anchor **0.7865 m** and populate the **remaining seven reference arm-length values in meters** based on a justified category scaling convention, rather than generating an independent individual arm length. Distinguish that reference geometry from throwing acceleration path and combat reach. Then specify any needed throwing-motion conversion and other body/technique factors (mass, force direction, grip, leverage, duration, footing/traction, and efficiency). These can make actual action force lower than intrinsic production capacity.
4. Fit or bound a smooth, monotonic **Being-level force-capacity** relationship against the evidence; check whether a single scalar suffices or a direction/duration-dependent capacity profile is necessary.
5. Validate lifting and throwing predictions independently before using the result for Pull and Bull rush.
6. Separately define reaction forces, friction, acceleration and distance from resulting forces, respecting the current one-second action schedule, physical constraints and 0.1 m spatial commitment.

Only the **Medium arm-length anchor (0.7865 m)** is numerically adopted. No other category-based arm length, Strength-to-N multiplier, throwing acceleration path, friction coefficient, or acceleration/displacement law is approved by Revision 58.

### Revision 58 additional acceptance tests

1. A Medium Being, regardless of Strength or Throw level, uses the standardized **0.7865 m** reference arm length.
2. The reference is **acromion to middle fingertip**, including the hand, and does not imply an upper-arm-only or shoulder-to-wrist measurement.
3. **0.79 m** is a rounded display of the **0.7865 m** modeling anchor; do not quietly substitute 0.79 m in precision-sensitive intermediate calculations.
4. The male ANSUR II sample is an anthropometric calibration reference, not a global population mean or the literal anatomy of every Medium Being.
5. The seven other size categories, trajectory-based acceleration distance, and Strength-to-force function remain unspecified.

## Acceptance tests

- A reference arm length is determined by **Size Category**. Medium has the adopted **0.7865 m** standard reference, while the seven other categories await calibration; two ordinary Beings of the same class do not need independent limb-length fields for this reference.
- Do not mistake Size Category effective-size factors for meters or linear limb-scaling ratios; **0.7865 m applies to Medium alone** and gives no ratio for the other seven classes.
- Do not equate the category-derived reference arm length with throwing acceleration path or personal melee Reach, and do not produce a numerical maximum force from that convention alone.
- An acquired Throw skill begins at level 1; the Throwing Table assumes its fixed `+1` velocity modifier. At Strength 10, level 0 gives `20 yd/s`, while any acquired Throw level gives `22.5 yd/s` via the specified formula.
- Preserve `100 lb → ~445 N` and `400 lb → ~1,779 N` as derived lifting reference forces, not Pull force magnitudes.
- Verify conditional throwing example's kinetic energy and force dependence on launch path; force cannot be inferred uniquely from mass and launch speed alone.
- Confirm 50 lb can be thrown at all at Strength 10 even though its `0.9 yd/s` theoretical speed is below the `5 yd/s` effective adjacent-hex threshold. The `20` versus `22.5 yd/s` level-zero versus acquired-Throw baseline is resolved in revision 56; no source values are altered.
- Two identical Beings and circumstances give the same maximum-capacity values regardless of the winning roll margin; independently successful simultaneous Pull forces remain vector-combined.
- Any proposed curve must account for the relevant source tables and body-dependent context; an unresolved contradiction blocks claiming objective unique calibration.


## Revision 59 — Ratified throwing resolution

Medium reference arm length: **0.8 m**. Progression Diminutive 0.1, Tiny 0.2, Small 0.4, Medium 0.8, Large 1.6, Huge 3.2, Gargantuan 6.4, Colossal 12.8 m. Acceleration distance equals arm length. At equal absolute Strength, effective accelerating force is size-independent, not multiplied by muscle cross section; velocity scales with `sqrt(L/0.8)`. Muscle area is relevant to attainable Strength. Lifting/carrying remain governed by the same Strength at every size and are an independent modeling theme.

Smooth empirical velocity fraction `exp(-[(m/H(S))/0.08081]^0.6010)` replaces the original Velocity versus Weight Table lookup, whose 25 entries provided surrogate values, not the missing original per-throw observations. Multiply by existing `Vmax(S, Throw skill)` and by `sqrt(L/0.8)`. The alternative proportional to linear length is rejected. No separate upper hand-motion speed constraint or arm inertial model adopted. Historical absolute throwable mass and 5 yd/s effectiveness threshold still apply. Unresolved audit: trajectory and wind consistency, extreme aerodynamic cases, tabular references, code migration/rounding. General resultant-force mechanics and multiple-grip Grapple issues are separate unfinished ES-041 work.


## Revision 60 — Trajectory calibration settled

Reference Medium arm length 0.8 m and the size-scaled throwing velocity remain adopted. Standard gravity is 10 m/s². The release height defaults to body height (6 ft for the reference Medium humanoid) and is substitutable for an individual throw. With velocity in m/s, h in meters and g=10 m/s², optimized maximum ground range is `(v/g) sqrt(v²+2gh)` and flight time is `sqrt(2(v²+gh))/g`. Horizontal-release range increment is `v sqrt(2h/g)`. The revised Throwing Table uses those relations, converting distances back to yards. Aerodynamic drag/wind investigations are deferred to the later launched-projectile study. Implementation regression tests remain, separate from the adopted rule decision.
