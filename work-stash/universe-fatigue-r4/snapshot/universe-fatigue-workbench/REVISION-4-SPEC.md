# Universe Encounters — Physical Fatigue, Candidate Revision 4

> **Adopted R4.9 check-table update (2026-10-26):** Section 7’s former absence of a physical-check fatigue conversion is superseded by the universal Q/B physical-check rule in [Appendix — Universal Table](APPENDIX-UNIVERSAL-FATIGUE-TABLE.md). Apply one standardized, fixed-sensitivity (5) penalty to physically demanding checks and contests, both sides, without changing base ability scores. This does not change the candidate R4 physiological engine.


**Date:** 2026-10-25  
**Status:** Complete mechanics candidate for assessment; not ratified into authoritative Encounters rules.  
**Scope:** **Physical** fatigue only. Mental stress/fatigue unchanged.  
**Architectural decision already adopted:** exactly two persistent continuous fatigue components; descriptive labels derived, not directly mechanical.  
**Implementation:** `universe_physical_fatigue_r4.py` (standard-library Python), including representative scenarios and consistency tests.

## 1. What Revision 4 changes and why

Revision 3 used fixed subjective exertion intensity, two exponential fatigue accumulators and one broad percentage modifier to all physical performance. This did not adequately model athletes who race to their limits: a 24-hour ultrarunner could finish with full immediate reserve, and there was no governing relation between chosen pace, changing capability and task failure. The percentages were not meaningful measures of capacity to *continue an activity*.

**R4 replaces the all-purpose performance multiplier with a capacity-versus-demand model:** the available sustainable output falls with prolonged work; fast reserve temporarily supports work above it; at any instant the Being has a maximum realizable output. If demanded output exceeds that bound, it must slow, reduce physical effort, change tactics or fail to sustain the task. All quantities are evaluated continuously and on the existing simulation timeline. No rule is tied to a race finish line or event duration.

R4 uses a critical-power-inspired finite high-intensity reserve, but is a playable abstraction, not a literal validated energy-metabolism model. Scientific critical power / W′ models apply especially well to relatively controlled exercise above the critical threshold; extrapolation to ultras, heterogeneous locomotion, combat and animals is a deliberate simulation design choice, not a claim of equal evidentiary strength.

## 2. Persistent state — exactly two values

Track, for each Being:

- **Q** = immediate physical reserve remaining, real number in `[0,1]` (displayed 0–100%).
- **B** = endurance reserve remaining, real number in `[0,1]` (displayed 0–100%).

Fully rested is `Q=B=1`. Neither number is the fraction of fresh running speed, lifting ability or overall performance remaining. `Q=0` means that physical output above the current sustainable threshold cannot be maintained; it does **not** mean paralysis. A Being can be exhausted for sprinting or racing and still walk or perform lower-demand actions. `B=0` indicates extreme accumulated fatigue; capacity may remain for some low-demand action.

All other quantities here are *derived* from these values and previously established character, activity and environment data. No exertion-point, muscle-wear, recovery-debt, race-clock or extra stamina counter is introduced.

**Attributes:** Fitness remains the trainable ability established in Encounters, with Constitution-limited improvement and ordinary 3d6 ability checks where otherwise required. Run remains a skill. Neither base Fitness nor Strength decreases when Q/B falls.

## 3. Actual demand and reference output

For any activity, define its **realized normalized physical demand** `u ∈ [0,1]` relative to this individual's *fresh reference maximum* in that action or locomotion mode. `u=0` is complete rest; `u=1` is the reference maximal achieved physical workload. It is not an arbitrarily assigned psychological effort label. The mode's demand profile derives `u` from **achieved** speed, acceleration, positive mechanical work, load, gradient, medium/terrain, leverage, posture and technique, normalized by capability. Mode-specific profiles are inherited and may be specialized by species, population, individual or circumstances.

**Default coarse descriptions** (illustrative; select based on the actual Being and conditions): resting `0`; light activity `0.05–0.15`; easy walking `0.15–0.25`; loaded marching `0.22–0.35`; steady endurance running/cycling/swimming `0.30–0.55`; demanding continuous work `0.50–0.75`; hard bursts `0.75–0.95`; maximal physical exertion `1.00`. These are estimation aids, not universal mappings from activity names.

A stable activity may have a specified *requested* demand `u_req` (holding a speed or a wrestling force). **Actual output** is the lower of that request and the dynamically computed maximum below. If the action's required work cannot be produced, it cannot proceed *as declared*. A Being can continue below the requested effort. In an all-out sprint, `u_req=1` means maximal attempted effort; falling below 1 is the normal realized response, not an automatic failed action.

For locomotion, fresh maximum sprint speed and acceleration are calculated by the separately adopted or candidate locomotion mechanics. This fatigue model does **not** replace those mechanics. To turn workload into velocity, each locomotion mode has a monotone `speed ↔ u` cost profile. A minimal default needs the fresh maximum speed, a reference critical-speed anchor and the physiological critical fraction. For example, with speed `v`, reference critical speed `v_c`, fresh maximum `v_max`, and physiological threshold `c0`:

- For `0 ≤ v ≤ v_c`: `u(v)=c0 × v/v_c`.
- For `v_c < v ≤ v_max`: `u(v)=c0+(1−c0)(v−v_c)/(v_max−v_c)`.

The inverse is defined by the same line segments. This is a **fallback cost map**, not a universal law of metabolic economy. Swimming, cycling, walking, running, mounted travel, and fantastical locomotion can have their own cost curves. Work against load, slope or other resistance changes the cost of an achieved speed, *not* the speed directly. Terrain and hampering can still limit reachable speeds independently; do not count the same penalty twice.

### Competing physical demands

When a Being moves and attacks, or acts in multiple ways simultaneously, combine the **actual total exertional work**, not the sum of arbitrary normalized intensities. Use the relevant action's governing work/effort profile and overlapping time intervals. Never count the same muscle work twice. A static restraint may cost effort without displacement, because sustained isometric force has a metabolic cost. Passive defense and short reactions should not consume an entire second of maximal output unless actually exerted for that long.

## 4. Derived sustainable and maximum output

Let `c0` be the Being's fully recovered sustainable fraction of reference peak output. For remaining long-term reserve `B`, the sustainable output ceiling is:

`C(B) = c0 × [f_c + (1−f_c) B]`

Here `f_c` is the nonzero residual proportion when long reserve is exhausted. A Being at low B may still walk, but cannot maintain an intense pace.

Long-term fatigue also reduces maximum brief output:

`H(B) = 1 − (1−f_p)(1−B)`

where `f_p` is the residual peak-output fraction at `B=0`.

Immediate reserve governs how far above sustainable output a Being can perform:

`M(Q,B) = C(B) + [H(B)−C(B)] × [1−(1−Q)^n]`

`M` is the **currently available maximum normalized physical output**; `M(1,1)=1`, and `M(0,B)=C(B)`. The exponent `n` delays significant instantaneous power loss during an initial sprint even while fast reserve is consumed, then reduces maximum performance increasingly steeply as Q empties. This is a game calibration, not a mechanistic muscle contractility equation.

An attempted workload `u_req` is feasible **at that instant** if `u_req ≤ M(Q,B)`. The realized workload is `u=min(u_req,M)`. Failure to sustain a specified pace is detected when the required normalized output first exceeds `M` (within numerical tolerance); this is a *task failure*, not unconsciousness. For all-out voluntary effort, fatigue simply forces `u` progressively below 1. Fatigue must never instantaneously teleport a Being to a lower speed: the established acceleration/deceleration/position update integrates toward the currently feasible speed.

## 5. Reserve evolution

All rates below use **realized** physical workload `u`, not an unachievable declared demand. Ordinary wear multiplier `w ≥ 0` is an *input* for nonduplicated eccentric/mechanical demands; default `1`, and do not add wear when its effect was already included in workload `u` or an injury rule.

**Immediate reserve:**

- If `u > C(B)`: `dQ/dt = −[u−C(B)]/W_fast`.
- If `u ≤ C(B)`: `dQ/dt = [1−Q][C(B)−u]/[C(B)T_Q,recovery]`.

`W_fast` is the finite budget in seconds of normalized above-threshold output (the dimensionless counterpart of an amount of tolerable work above critical power). Q is clipped to `[0,1]`. The second equation restores a fraction of what is missing, with slower recovery while approaching sustainable output. At zero Q the Being may continue **at or below C(B)** without being physically incapacitated.

**Endurance reserve:**

Define the nonnegative wear rate:

`g(u,w) = w × [max(0,(u−u_0)/(1−u_0))]^2`.

Then:

`dB/dt = −B × g(u,w)/T_B,depletion + (1−B) × max(0,C(B)−u)/[C(B) T_B,recovery]`.

Use the `sleep` recovery time for sleeping, otherwise the `awake` rate. Sleeping requires `u=0`. The B recovery term does not automatically trigger an instant reset when a Being slows below threshold. At low sustainable intensities, loss and recovery compete and may establish a steady state; at sustained heavy work, B diminishes. The workload response exponent and parameters are configurable physiological references.

**Integration:** Q and B are coupled through `C(B)` and `M(Q,B)`. Update from the same current state and realized effort using a consistent numerical integrator; constant-coefficient exponential updates may be used within sufficiently small substeps. For a long coarse interval, integrate over the activity block numerically to a specified accuracy rather than rounding each second to integer percentages. Split intervals when work, terrain, sleep, injury or physiological conditions change. A correct implementation must give consistent results (within declared tolerance) whether a long unchanged activity is processed in one call or several calls.

A deterministic numerical reference is provided in the accompanying Python file. The reference computes the two reserves with a held-work substep integrator and exercises convergence; a production implementation may use a higher-order adaptive solver.

## 6. Provisional human defaults, skill and physiology

These are **review values**, not measured universal human constants:

| Parameter | Fitness 12, Run 0 reference | Meaning |
|---|---:|---|
| `c0` | 0.60 | Fresh sustainable fraction of mode reference maximum output |
| `f_c` | 0.25 | Fraction of fresh sustainable ceiling retained at B=0 |
| `f_p` | 0.55 | Fraction of fresh peak output retained at B=0 |
| `n` | 2.0 | Fast reserve-to-peak response exponent |
| `W_fast` | 20 s | Above-threshold normalized-work budget |
| `T_Q,recovery` | 60 s | Q recovery constant at rest |
| `T_B,depletion` | 7,200 s | B depletion constant at normalized high workload |
| `T_B,recovery awake` | 86,400 s | B recovery at complete awake rest |
| `T_B,recovery asleep` | 43,200 s | B recovery during sleep |
| `u_0` | 0.10 | Lower bound for net slow wear term |

**Individual human example scaling**, where `F` is established *base* Fitness and `R` is the Run level **only during actual running** (otherwise R=0):

`S = 1 + .01 R`

`c0(F,R) = min(.80, .60[1+.006(F−12)+.0015R])`

`W_fast(F,R) = 20 sqrt(F/12) S` seconds

`T_B,depletion(F,R) = 7200 (F/12) S` seconds

`T_Q,recovery(F) = 60 sqrt(12/F)` seconds

`T_B,recovery awake(F) = 86400(12/F)` seconds

`T_B,recovery asleep(F) = 43200(12/F)` seconds

These are explicit proposed replacements for the old fatigue-check Run benefits, **not** new bonuses layered onto the old rules. They allow training and Fitness to improve sustainable output, effort tolerance and recovery without a separate fatigue or stamina attribute. Do not apply the running-specific Run endurance increment to swimming or cycling; their corresponding skills may eventually be calibrated analogously, but do not invent them automatically.

Fresh human sprint calibration remains separately proposed as `v_max=.4572F + .19652 R F/18` m/s, with acceleration time constant `τ=1.10+.005R` seconds. This ties peak human reference running to Fitness 18 and Run 20 as previously explored. It is not a newly established universal athletic limit. The fatigue system acts through feasible `u(v)` and **does not multiply sprint speed a second time**.

**Physiological inheritance:** references define distributions of these parameters by body plan or physiological mechanism, optionally specialized for clades, species, breed/population and individuals. No independent parameter set is mandatory for every species, but species-specific values are explicitly permitted. Resolution-on-demand refinement must respect committed performance and individual history. Actual physiological constants of horses, camels, cheetahs or flying beings cannot be determined by naming the species alone.

## 7. Derived states and physical ability checks

**Descriptive state**, determined from `min(Q,B)`; descriptions have no mechanical effects in addition to the actual reserve equations:

| Minimum reserve | Descriptor |
|---|---|
| 90–100% | Fresh |
| 65–<90% | Winded |
| 35–<65% | Tired |
| 10–<35% | Weary |
| 0–<10% | Exhausted |

This means a runner with Q=1%, B=45% is **exhausted for hard physical work** but can still move at a low demand. It avoids claiming that B=45% translates into 45% of race performance. `Incapacitated` is **not a fatigue stage**: only an independent injury/health condition or an explicit action requiring output above the currently available maximum prohibits the task.

Do **not** reduce base Fitness/Strength scores, roll another 3d6 fatigue threshold, apply the old PFL factor, or enforce categorical pace bans. For physically demanding checks and contests apply the **adopted standard Q/B check penalty once**, as specified in [the universal-table appendix](APPENDIX-UNIVERSAL-FATIGUE-TABLE.md); it replaces the previous missing check-conversion step. Action feasibility remains Being-specific. Do not add further fatigue penalties to ability scores, defending, or technique.

**Open combat-integration detail:** the precise effort requirement and permitted downgraded effects of each strike, defense, sprint, shove, sustained hold, charge or grapple are not yet empirically calibrated. This is the deliberately bounded next step; it does not change the two-reserve architecture.

## 8. Manual tracking — no third meter, no exponentials for players

Record **Q% and B%**, whole or nearest 5% for routine tabletop play. For typical intervals use printed **activity cards** specifying demand class, duration, Q spent/restored and B spent/restored for the reference physiology. The user may choose an exertion or pace, but does not track exertion itself; it is an activity input. A small chart converts current B into `C(B)` and current Q/B into `M(Q,B)` when an action is close to its limit. For typical low-intensity activity, Q remains near 100 and only B is updated at an appropriate interval.

**Hand methods for the reference human (Q/B expressed as fractions):**

- Approximate Q expenditure above C over `Δt`: `ΔQ ≈ (u−C) Δt / 20s` (multiply by 100 for percentage points). Re-evaluate current C when B changes meaningfully.
- At complete rest, Q replenishes approximately 63% of what is missing in one 60-second time constant, or about 28% of missing Q in 20 seconds.
- For B, use printed 10-min, 1-hour and sleep/rest cards rather than continuous arithmetic. Round **once per completed card interval** and carry fractional remainder when necessary; do not erase fractional effort each second.

For a reference Fitness 12, Run 0 human, starting Q=B=100%:

| Activity | Q after | B after | Interpretation |
|---|---:|---:|---|
| 10 seconds maximal effort | ~80% | ~100% | Very high effort is still possible initially; fresh peak output only falls slightly |
| Followed by 60 seconds rest | ~93% | ~100% | Most immediate capacity returns |
| 5 hours loaded march at illustrative u=.27 | ~100% | ~91% | Moderate accumulated burden, useful work still possible |

**Manual precision contract:** Five-point bands are a game approximation. A digital simulation should store real values and only round for display. If an outcome is sensitive to a 5% band boundary, temporarily use 1% precision or roll/estimate within the known range rather than pretend the coarse table is exact.

## 9. Stress tests and interpretation

All numerical results in this section are **results of these proposed equations under explicitly chosen example workload profiles**. They are not empirical fits to named historical people, animals or race records. Workload and physiology must eventually be calibrated against measured observations.

### Short and maximal human efforts

At Fitness 12/Run 0, asking for continuous all-out effort for 10 seconds leaves approximately **Q=80%, B≈100%** and an instantaneous maximum output of **98.4% of the fresh reference**. This preserves small late-sprint performance change despite meaningful fast-reserve expenditure. Maximal effort for 45 seconds leaves Q≈28% with output capacity near 79% of fresh. Output degrades continuously as demands remain high; no random abrupt fatigue checks occur.

### Endurance event as an actual feasibility problem

A long-distance competitor selects an effort policy; the simulation evaluates the **same** physics independently of where the finish line is. To diagnose limits, solve for the highest *constant demand* that can be maintained for an arbitrary observation period. This is a pacing calculation, not a rule that exhausts a Being when the requested period ends.

For an illustrative elite human Fitness 18 / Run 20 during running (skill scaling included):

| Diagnostic duration | Highest approximately feasible constant demand | Q at end | B at end |
|---|---:|---:|---:|
| 2.5 hours | 0.562 | 2.5% | 78.8% |
| 10.5 hours (single-mode mathematical reference; **not an Ironman calculation**) | 0.471 | 1.5% | 61.7% |
| 24 hours, running impact multiplier 1.3 | 0.388 | 1.1% | 45.1% |

At slightly higher continuous demand, physical output is insufficient earlier. At a more conservative demand, meaningful reserves remain. The same athlete could walk after finishing because walking demands less output than the depleted racing limit. This fixes the key R3 failing: the athlete does not retain full Q after an athlete-maximum endurance effort.

**Careful interpretation:** B need not reach zero for a Being to be *exhausted at racing intensity*. Racing task failure is governed by the available output, and Q reaches near zero because the declining sustainable ceiling cannot continue supporting the demanded pace. We do not equate overall physical reserve depletion with death, unconsciousness or loss of ability to walk.

### A full-distance triathlon with distance-based legs

For an illustrative elite human with Fitness 18, running Run level 20, separate fresh swim/bike/run cost profiles, adequate normal conditions and a common proportional pacing strategy, a maximal approximately feasible example produces:

| Discipline | Time | Relative work demand | Q after leg | B after leg |
|---|---:|---:|---:|---:|
| Swim 3.8 km | 55.1 min | 0.433 | 100% | 96.3% |
| Bike 180 km | 310.3 min | 0.462 | 100% | 78.7% |
| Run 42.195 km | 172.6 min | 0.492 | **1.9%** | **65.4%** |

With two five-minute transitions, total time is **9.13 hours**. A 5% more conservative effort strategy finishes in **9.60 hours**, leaving Q near 100% and B near 68%; a strategy 2% more aggressive exceeds available output during the run, and **the projected faster time cannot be completed at that pace**. The failure calculation knows only actual demand and reserves, never a finish-line rule. The swim and bike speeds are explicitly illustrative configuration anchors, not validated physiological values.

### Roman-style military marching

Reference Fitness 12, with five hours at `u=.27,w=1.1`, two hours of camp work `u=.40,w=1`, nine hours of light awake activity and eight hours of sleep. The identical schedule repeated four days yields:

| Stage | Day 1 B | Day 2 B | Day 3 B | Day 4 B |
|---|---:|---:|---:|---:|
| After march | 91.1% | 85.5% | 83.9% | 83.5% |
| After camp work | 81.8% | 76.8% | 75.5% | 75.1% |
| After rest/sleep | 93.1% | 91.2% | 90.7% | 90.5% |

Q remains around 100% at the stipulated sustainable workloads. This produces substantial **but not inevitable runaway** fatigue. A trained Fitness 15 soldier would fare better under the scaling equations. Historical march benchmarks are a constraint on practical speed and load, not a calibration of these percentages; the five “summer hours” described by Vegetius require care when converted to modern hours.

### Pony Express-style relays

Each animal and rider has independent Q/B. A rider changing mounts inherits no fatigue from the previous horse, but retains their own Q/B. An illustrative equine-specific profile riding for 72 minutes at `u=.37` leaves Q≈100%, B≈97%; a rider's illustrative nine hours at `u=.20` leaves Q≈100%, B≈95%. **These values are demonstrations only**, not estimates of real equine/rider physiology. A proper equine workload mapping must use its gait, mass, carrying load, terrain and appropriate physiological reference, not the rider's speed or a human Run skill. Historical relay distances provide useful plausibility constraints.

### Combat: preliminary stress tests (not a combat-rule ratification)

Combat demands involve bursts, lulls and overlapping actions. The implementation was exercised with three *illustrative* alternating effort patterns for Fitness 12 / default profile:

| Example pattern | End of 60 seconds | End of 5 minutes | Interpretation |
|---|---|---|---|
| Moderate: 1 s at `u=.85`, 2 s at `.20` repeatedly | Q≈80%, B≈99.8% | Q≈50%, B≈99% | Sustained intermittent action remains feasible; maximum burst output declines |
| Severe: 2 s at `.98`, 1 s at `.35` | Q≈38%, B≈99.5% | Q≈9%, B≈98.5% | Repeated full-intensity bursts become unsustainable well before the five-minute mark |
| Hard grapple: 3 s at `.86`, 1 s at `.20` | Q≈46%, B≈99.6% | Q≈9%, B≈98.4% | High sustained force depletes short-term reserve and forces reduced effort |

The severe and hard-grapple examples hit the output cap before five minutes; reported later percentages result from the implementation automatically limiting **achieved**, rather than continually applying impossible **requested**, work. These checks show that the model can distinguish pacing patterns. They do **not** determine real strike energy, defensive effectiveness, Grapple/Bull rush resolution or actual fighters' conditioning. That is the next action-specific calibration stage.

## 10. Encounters integration and non-fatigue conditions

1. Before movement, read the committed Being state Q/B and attributes. Integrate feasible actual movement and corresponding physical exertion together over the movement phase; retain the established motion and collision rules.
2. Evaluate all non-movement actions resolving in the same second against the shared post-movement snapshot. Do not let the fatigue caused by one simultaneous action preempt another action in that same resolution set. Combine actual energy/effort demands without double-counting and commit Q/B with the other consequences afterward.
3. Effort committed during an action remains locked according to the adopted action-timing rules; if current ability cannot deliver it at resolution, apply the appropriate physically feasible reduced effort/failure rule without moving decisions backward in time. Do not recalculate the actor's action choice merely because a later action is declared by another Being.
4. The old integer physical exertion points, rounding-discard procedure, failed-Fitness-check transitions, categorical movement-rate bans, `1−PFL/5` multiplier and automatic `−1/−2/−3` ability losses are removed **when and only when R4 is ratified**. No double penalties.
5. Food, sleep deprivation, illness, injury, environment, heat, dehydration and physiological failure may independently constrain feasible output or alter mode cost/physiology if **those existing world conditions** are simulated. They are not secretly additional physical-fatigue reserves. Without their data, results are explicitly conditional on benign support conditions. Long ultras cannot be fully predicted from these two reserves alone.
6. Competition variability should come from stochastic reaction time, movement execution, pacing/tactical choices, terrain and physiological individual variation, under a recorded RNG seed. No stochastic abrupt fatigue jumps are required; Q/B responds deterministically to the **realized** work history.
7. Powered flight, gliding, soaring and hovering—and deliberate fantastic violations of terrestrial aerodynamic limits—remain a **deferred workload/physics investigation**, not a reason to change the two-reserve architecture now.

## 11. Acceptance and known limitations

**Implementation checks:** bounded Q/B, recovery at rest, zero-fast-reserve threshold behavior, reduction of peak output with Q or B, reversible workload/speed reference mapping, no automatic finish-line exhaustion, repeatable relay state, independent Q/B per Being, and convergence under smaller numerical timesteps. Tests are in the Python reference file.

**Still to calibrate:** actual demand profiles and per-action effort for human locomotion and combat; individual or physiological reference parameters; localized/compound combat workloads; long-event fueling/heat/sleep if simulated; task-specific biomechanical effects; exact numerical integration tolerances for production; whether extreme physical fatigue should occasionally lead to distinct health events. These are bounded calibration and other-system interactions, not missing extra physical-fatigue state variables.

**Recommended decision:** accept Revision 4 as an internally coherent **complete mechanical candidate** for review. Keep coefficients provisional. First perform detailed combat tests using the actual Encounters timing, actions, effort commitment, and simultaneous-resolution rules; do not silently install it as authoritative until those tests and the user's review are complete.

### Scientific and historical context (for calibration, not exact numerical derivation)

- Critical power and the finite work reserve above it; recovery/reconstitution: https://pmc.ncbi.nlm.nih.gov/articles/PMC7552657/
- Review of task failure and multiple determinants of fatigability: https://pubmed.ncbi.nlm.nih.gov/41917650/
- Limitations of ultramarathon performance: https://pubmed.ncbi.nlm.nih.gov/37751076/
- Roman military marching (including the caution regarding “summer hours”): https://histos.org/index.php/histos/article/download/363/357/366
- Pony Express horse and rider relief history: https://www.nps.gov/poex/learn/historyculture/the-first-ride.htm

## Appendix — Starter paper reference card (Fitness 12, Run 0)

All entries are **rounded approximations**, not values to substitute into precise simulation. Use an individual or physiology-specific card for other Beings; repeated use should reflect the Being's **current**, not initially fresh, reserves.

**At one hour of constant achieved activity**, example Q/B endpoints for the reference human:

| Demand u | Q/B if starting 100/100 | Q/B if starting 100/75 |
|---|---|---|
| 0.10 (very light) | 100/100 | 100/76 |
| 0.20 (easy) | 100/99 | 100/75 |
| 0.27 (march reference) | 100/98 | 100/74 |
| 0.35 (brisk) | 100/96 | 100/72 |
| 0.45 (demanding endurance) | 100/93 | 100/70 |
| 0.55 (hard sustained) | 99/88 | **Unsustainable from B=75**: Q reaches 0 and output must decline |

**Immediate recovery at complete rest**, showing Q% after resting when initial B=80% (B hardly changes over such short intervals):

| Starting Q | After 20 s | After 60 s | After 5 min |
|---|---:|---:|---:|
| 20% | 43% | 71% | 99% |
| 50% | 64% | 82% | ~100% |
| 80% | 86% | 93% | ~100% |

**Eight hours of sleep**, starting at Q=100%; B recovery:

| Starting B | B after sleep |
|---|---:|
| 50% | 74% |
| 75% | 87% |
| 90% | 95% |

For encounter-length intervals, use the Q expenditure rule and display whole percentages. For sustained low-demand travel Q normally remains 100%, so B alone needs regular updates. This appendix is a deliberately small starter card, not an exhaustive library of all possible starting reserve values and activity demands.


---

## Workbench R4.3 operational-requirement audit (2026-10-25)

This appendix concerns the *workbench scenario orchestration*, not a change to the Revision 4 fatigue equations. Roman marching and camp work now enforce their prescribed pace, workload, and schedule; low-Fitness Beings are allowed to fail these duties. Strict assignment outcomes are binary although physiology remains continuous. The observed threshold is not evidence for a discontinuity in Fitness.

For other workbench scenarios, sustaining a scheduled relative exertion is **not** equivalent to accomplishing a prescribed distance, cargo delivery, tactical result, or race objective. The scenario metadata specifies exactly what was and was not tested. No empirical workload-to-distance mapping is implied.
