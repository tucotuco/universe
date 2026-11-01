# Encounters — cumulative adopted decisions (Revision 59)

**24 October 2026.** Revision 59 supersedes the former 0.7865 m reference with **0.800 m** and settles the throwing curve and size scaling as described under the final Revision 59 decision below. The revision 58 entry immediately following is retained as historical decision provenance, **not current mechanical authority**.

## Historical revision 58 decision record

**23 October 2026.** Revision 58 adopts the **Medium** reference arm length as the observed adult-male anthropometric sample mean, **0.7865 m** from shoulder tip to middle fingertip. The other size-class arm lengths, throwing acceleration path, and quantitative force model remain open. No Universe engine changes.

## ES-041 — Adult human male arm length as Medium reference

**Author’s decision:** “The reference arm length for a medium being should be the average arm length of an adult male human in real life.”

- **Adopted value:** **0.7865 m (78.65 cm)** is the default reference arm length for **Medium (Size Category 3)**. It is the adult-male mean reported from the ANSUR II U.S. Army anthropometric data. **0.79 m** is a rounded presentation, not a separately adopted exact value.
- **Measurement endpoints:** Shoulder tip (**acromion**) to the tip of the middle finger (**dactylion**) with the arm straight, including the hand. Do not use shoulder-to-wrist or upper-arm-only measurements.
- **Empirical scope:** ANSUR II measured 4,082 U.S. Army men. This supplies a reproducible real-world reference but does not establish an exact global adult-male mean; the model assigns it uniformly to Medium Beings as a default, not as a claim about individual anatomy.
- **Seven uncalibrated classes:** Diminutive, Tiny, Small, Large, Huge, Gargantuan, and Colossal still require reference arm lengths and a justified scaling relationship; *effective size* is not linear anatomy.
- **Unchanged constraints:** Neither actual throwing acceleration path, Reach, Strength-to-newtons calibration, nor the Pull/force-vector model is defined by this measurement.
- **Provenance:** [U.S. Army ANSUR II source](https://ph.health.mil/topics/workplacehealth/ergo/Pages/Anthropometric-Database.aspx); [ANSUR II male percentiles](https://ergoassessment.cam/ansur-2-data-explorer/) (median 78.6 cm); [published use of 78.65 cm mean](https://www.ibew.org.uk/dvarch/DV04307.pdf).

### Acceptance tests (Revision 58)

1. Medium category 3 supplies **0.7865 m** without requiring a separate personal arm-length measurement.
2. A rounded report may say **0.79 m**, but the numerical modeling anchor remains **0.7865 m**.
3. The length is measured acromion-to-middle-fingertip, not acromion-to-wrist.
4. No body-type scaling or seven other category lengths follow automatically from effective size or this anchor alone.
5. Reference arm length remains distinct from acceleration trajectory and combat Reach; do not compute N from it alone.

---

## Historical cumulative decisions through Revision 57

# Encounters — cumulative adopted decisions (Revision 57)

**23 October 2026.** Revision 57 adopts a **Size Category-derived reference arm length** for throwing-force calibration. The geometric convention is adopted, but numeric reference lengths and acceleration path conversion remain open. No Strength-to-newtons equation or Universe code change is adopted.

## ES-041 — Reference arm length derived from size category

**Author's decision:** “Fair enough. I think we should simplify arm length to be based on the size class.”

- **Standardized geometry:** Use the Being's Size Category as the key to a standard reference arm length. Do not require separately entered individual arm lengths for ordinary throwing-force calibration.
- **Existing classes:** Use the eight categories in the existing Size Categories Table: Diminutive (0), Tiny (1), Small (2), Medium (3), Large (4), Huge (5), Gargantuan (6), and Colossal (7). This is an index to reference geometry; no lengths in meters have yet been selected.
- **Do not use effective size as length:** The table's `effective size` values concern aggregate Grab/Grapple attacker capacity; they do not specify arm length and cannot be treated as linear scale factors.
- **Arm length versus acceleration distance:** The standard arm length is an input to an eventual throwing-motion geometry model. It is not automatically equal to the distance over which the projectile is accelerated. The conversion to acceleration path, throwing efficiency, or applied force is not decided.
- **Unchanged distinct rules:** This does not replace the Reach section's personal combat reach or its center-to-center measurement convention, and does not modify Throw velocity, absolute throwability, carrying capacity, Bull rush, Pull, physical force units, or simultaneous vector combination.

### Acceptance tests (Revision 57)

1. Two ordinary Beings of the same Size Category use the **same standard reference arm length**, regardless of different Strength or acquired Throw skill levels; no numeric length is assumed yet.
2. Beings of different Size Categories select their reference arm lengths by category, but this decision alone assigns no relative numeric ratios or exact meter values.
3. A Medium Being (category 3, effective size 4) must **not** automatically receive a 4 m arm, four times Tiny's arm length, or any other interpretation of `effective size` as a length.
4. Reference arm length does not automatically equal throwing acceleration path. Dynamic-force calculation requires that separately specified relationship, and cannot currently yield uniquely calibrated N.
5. Keep reference arm length separate from established weapon/personal combat Reach mechanics and center-to-center reach eligibility.
6. Preserve revisions 51–56 on simultaneous force vectors, contest success versus force magnitude, Newtons, calibration evidence, throwability, and the acquired Throw skill baseline.

---

## Historical cumulative decisions through Revision 56

# Encounters — cumulative adopted decisions (Revision 56)

**23 October 2026.** Revision 56 confirms that **all acquired progressive skills start at level 1**. Unacquired ordinary progressive skills can still be attempted at level 0 where their individual rules permit; extraordinary skills continue to require any specified prerequisite level. The Throwing Table's velocity figures assume acquired Throw skill (level 1 or higher), resolving its apparent discrepancy with the maximum-velocity equation. No Strength-to-newtons equation or Universe engine change is adopted.

## ES-041 — Throw skill modifier and tabulated maximum velocity

**Author's decision:** “Yes. Having the Throw skill starts with level 1. This is true of all progressive skills.”

- **General progression:** The first acquired level of any progressive skill is **level 1**. Level 0 represents no acquired level; ordinary skills may be attempted at level 0 as independently allowed, but extraordinary-skill access rules are unaffected.
- **Specific Throw modifier:** The written maximum-velocity formula uses **Throw skill modifier = +1 for at least one acquired Throw skill level**, as indicated by the existing Throwing and Velocity-versus-Weight passages. At level 0, its modifier is 0. This fixed Throw velocity benefit is not the Throw level itself and does not increment with additional levels.
- **Table baseline:** With Strength 10 and modifier +1, `5 × (10 + 1 − 2) / 2 = 22.5 yd/s`; this matches the table. Strength 10 with no Throw skill (modifier 0) gives `20 yd/s`. The table therefore describes a Throw-skilled baseline. The other listed maximum velocities follow the same +1 treatment.
- **Prior question resolved:** Revision 55's 20 versus 22.5 yd/s baseline discrepancy is resolved by the level-1 skill assumption. Do not change the Throwing Table or formula, and do not infer that every additional skill level increases speed.
- **Force calibration still open:** The difference is one of throwing proficiency, not proof of higher intrinsic Strength-based force capacity. The Being-level calibration in N still requires a validated physical model, body/action parameters, and force-to-motion treatment.

### Acceptance tests (Revision 56)

1. Strength 10 and Throw level 0: `5 × (10 + 0 − 2) / 2 = 20 yd/s`, independently of the tabulated value for a Throw-skilled Being.
2. Strength 10 and Throw level 1: `5 × (10 + 1 − 2) / 2 = 22.5 yd/s`, matching the Throwing Table.
3. Strength 10 and Throw level 3: the **same** Throw-specific +1 velocity modifier; no automatic `+3` or three cumulative +1 increases are authorized.
4. A newly acquired progressive skill cannot be recorded at learned level 0; level 0 remains the unacquired state. Ordinary untrained use, where allowed, does not grant the acquired-skill benefit.
5. No modification to the 50-lb absolute max-weight interpretation, the 5 yd/s effective threshold, force capacity in N, or the success-vs-force separation.

---

## Historical cumulative decisions through Revision 55

# Encounters — cumulative adopted decisions (Revision 55)

**23 October 2026.** Revision 55 confirms that the Throwing Table's maximum weight is the heaviest object that can be **thrown at all**, not necessarily far or fast enough to meet the `5 yd/s` threshold for an effective adjacent-hex throw. No force equation is adopted; no Universe engine changes.

## ES-041 — Absolute throwability limit versus effective throw

**Author's decision:** “That's the maximum that can be thrown at all.” In context, this is the `Max Weight` field of the Throwing Table.

- **Absolute maximum throwable weight:** The Throwing Table gives the largest object mass that can be thrown at all at a given Strength. It does **not** promise that an object of that mass can travel into an adjacent hex, and it is **not** the upper heavy-load carrying capacity.
- **Effectiveness threshold separate:** The source's `5 yd/s` minimum determines whether a thrown object can effectively travel into an adjacent hex. Its maximum *effective* throwable mass may be lower than the absolute throwability limit. For Strength 10, a 50-lb object thrown at approximately `0.9 yd/s` is permitted by the absolute-weight constraint but does not meet the adjacent-hex threshold.
- **Maximum speed and distance are independent extrema:** They must not be attributed to a maximum-weight object at the same time. Weight-dependent speed remains governed by the Velocity versus Weight Table.
- **Remaining open question:** The maximum-velocity equation yields `20 yd/s` at Strength 10 for zero Throw modifier, while the Throwing Table lists `22.5 yd/s`. Confirm whether the table assumes `+1` Throw modifier before deriving a numerical force profile; preserve source values pending decision.
- **No new physical law:** Being-level Strength/body calibration in N, required acceleration geometry, net-force-to-movement conversion, and action-specific force application are still open.

### Acceptance tests (Revision 55)

1. Strength 10, maximum table throw weight 50 lb: **throwable at all**, even where projected speed is too low for adjacent-hex effectiveness.
2. Strength 10, 100-lb heavy-load limit: liftable/supportable under source rules, **not** automatically throwable.
3. Strength 10, 50 lb at 4% of 22.5 yd/s = 0.9 yd/s: no contradiction with the 50-lb *absolute* maximum, but the `5 yd/s` threshold for effective adjacent-hex throwing fails.
4. Strength 10, 15 lb at 24% of 22.5 yd/s = 5.4 yd/s: exceeds the effective threshold under the table's stated maximum speed, while not altering the 50-lb absolute limit.
5. An object's max-weight row and the table's max-velocity or max-distance cannot be treated as one simultaneous max-weight launch.
6. Keep the formula/table `20` versus `22.5 yd/s` Throw-skill baseline unresolved, and do not invent a Strength-to-newtons formula.

---

## Historical cumulative decisions through Revision 54

**23 October 2026.** Revision 54 adopts evidence-based, Being-level physical force calibration using Strength-dependent carrying and throwing rules. No universal numerical Strength-to-N equation is adopted, pending reconciliation of evidence and action-specific physical constraints. No Universe engine changes.

## ES-041 — Evidence-based intrinsic force capacity

**Author:** “Yes, it should be based on the being. We have several lines of evidence for how strength might translate into force. For example we have tables for throwing distinct weights of objects, capacity to carry weight, etc. We need to use those to estimate force objectively based on the Strength ability.”

- **Being-level attribute:** The intrinsic maximum force-production capability is based on the Being's Strength and physically relevant characteristics, not a separate arbitrary property for each action. Distinguish this capacity from actual force delivered under action-specific geometry, exertion and contact constraints.
- **Calibration data:** Use the Carrying Capacity Table, Throwing Table, and Velocity versus Weight Table. Reference upward support forces from the existing heavy-load limits are 222 N (Strength 5), 445 N (10), 890 N (15), 1,779 N (20), and 2,669 N (23), at Earth-like standard gravity. These are derived mechanics-implied support forces, not automatically the maximum force of Pull, Bull rush, or any other action.
- **Throwing:** A launch mass and velocity do not uniquely specify applied force; stroke length or acceleration time must be known. The formula `m*v²/(2*d)` is physically conditional and must not be assumed as an adopted throwing action algorithm.
- **Evidence quality:** The Strength 10 maximum thrown-weight figure of 50 lb is inconsistent with the given weight-velocity fraction and the rule's effective throwing threshold, unless additional context is supplied. Verify the interpretation and Throw skill modifier baseline before fitting a single force curve.
- **Open choices:** The numerical force-capacity profile, action-conditioned effective-force model, physical traction/inertia, force-time history, and forced displacement remain unadopted. The existing r53 newton unit, r52 success/magnitude separation, and r51 simultaneous force-vector addition remain controlling.

### Acceptance tests (Revision 54)

1. Convert 100 lb of weight under standard gravity to approximately 444.822 N without equating this to a Being's horizontal Pull force.
2. Strength 20 gives a 400-lb heavy-load upper bound and approximately 1,779.289 N reference support force.
3. For a 5-lb object launched at 47% of 22.5 yd/s (Strength 10, 5% of heavy load), speed is approximately 9.67 m/s; a conditional *one-meter* acceleration path yields about 106 N average accelerating force, while a half-meter path doubles the estimate. Do not infer stroke length from the source table.
4. A 50-lb object at Strength 10 is 50% of 100-lb heavy load; 4% of 22.5 yd/s is only 0.9 yd/s, below the rule's 5 yd/s threshold. Flag the incompatible interpretation; do not silently rewrite either table.
5. Do not compute maximum force from the bare 3d6 Strength-contest total, and do not assign identical effective force to lifting and Pull merely because the Strength is the same.
6. If two successful Pulls have supplied equal and opposite forces in N, their resultant is zero regardless of Strength contest margins; preserve the previous physical rule.

---

## Historical cumulative decisions through Revision 53

# Encounters — cumulative adopted decisions (Revision 53)

**23 October 2026.** Revision 53 adopts the **newton (N)** as the physical force unit for Encounters, without adopting a numeric force production or acceleration/displacement equation. No Universe engine changes.

## ES-041 — Force represented in newtons

**Author's decision:** “Newtons.” This chooses the physical SI unit of force rather than a relative game-force scale.

- **Canonical unit:** Applied physical force magnitudes and vector components are expressed in **newtons (N)**; `1 N = 1 kg·m/s²`. Net force is obtained by vector addition of like-unit contributions from independently successful Pulls. A Concerted Pull retains its existing check procedure; successful participants' *physical forces* are represented in newtons rather than derived from sums of rolled scores.
- **Success distinct from magnitude:** The contested Strength check decides only success. The Being's Strength and physical characteristics provide the basis of physical force once a quantitative model is later defined. Roll totals, bonuses, and winning margins must not be interpreted as N or multiplied into force.
- **Open calibration:** The exact force-capacity function, including relevant body and situational characteristics, has **not** been selected. Neither target mass-to-acceleration treatment, friction/contact constraints, force duration, nor net-force-to-displacement mapping over a one-second action has been specified by this unit choice. Keep those decisions explicitly pending.
- **No change in spatial conventions:** Distances and game thresholds follow the existing yard-to-meter rules; committed position uses 0.1-meter precision. Choosing force in N does not modify movement legality, grip continuity, combat timing, or simultaneity.

### Acceptance tests (Revision 53)

1. For stipulated simultaneous successful forces of `+100 N` and `−100 N` along the same axis, vector sum is `0 N`; there is no forced displacement attributable to those pulls and no Grapple-style reroll.
2. For stipulated perpendicular forces `(100 N, 0 N)` and `(0 N, 100 N)`, their resultant is `(100 N, 100 N)`. Do not infer a displacement distance without the separately adopted movement model.
3. If the same Being succeeds in otherwise identical circumstances with different Strength-contest rolls, the applied force in newtons must not change solely because of the roll.
4. Concerted Pull may win with summed modified contest results; do not label the sum “N”. Forces in N must come from the physical force model independently of the check totals.
5. Without a Strength/body-to-newton mapping, do not assign numerical force to a Being given only a Strength score, and do not assign movement from an unstipulated force.
6. A force measurement provided in a non-SI unit must be converted to newtons before adding it to an N-valued force vector; no physically incompatible components are summed.

---

## Historical cumulative decisions through Revision 52

# Encounters — cumulative adopted decisions (Revision 52) [historical]

**23 October 2026.** Revision 52 adopts the distinction between a Pull's **chance of success** and the **magnitude of force** exerted by a Being. No Universe engine changes.

## ES-041 — Contest success is not force magnitude

**Author confirmation:** Yes — applied force should be determined primarily by the Being's **Strength and physical characteristics**, with dice determining **only whether the declared action succeeds**.

- **Contest and chance:** A successful opposed Strength contest (including the adopted cooperative Concerted Pull procedure) determines eligibility for the declared Pull's forced-movement effect. The number shown on the dice, the total after skill or situational modifiers, and the victory margin are not physical force measurements.
- **Physical source:** Once an action succeeds, derive its effective applied force from the Being's **Strength and physical characteristics**, to be specified by a separate calibrated or game-consistent force model. This remains so for independently successful simultaneous Pulls and cooperating participants. No extra force is gained merely by rolling high.
- **Vector composition unchanged:** Add force vectors from successful Pulls and resolve the physical resultant and legal movement. Equal-and-opposite physically equal forces cancel **regardless of the contest values**. The contest results do not dictate relative vector magnitudes.
- **Still open:** Which characteristics and contextual physical factors determine a Being's actual applied-force magnitude, how they are mapped to common units, and how a net force affects a target's acceleration and displacement during one second, including discrete hex constraints. Strength and other physically relevant attributes are selected as the **source** of force, not yet a numerical function. Do not infer Newtons from a d6.

### Acceptance tests (Revision 52)

1. A wins the Pull contest with a modified result of 12 in one otherwise identical trial and 18 in another. **Applied force is unchanged** between the trials; only the yes/no outcome was determined by dice.
2. A and C independently succeed with unlike winning contest margins, yet have physically equal opposite applied forces: net force zero and no forced movement, without rerolls.
3. Two successful participants have physically unequal Strength/body characteristics: a future adopted model may give unequal forces even when their winning contest totals happen to match. Until the physical model is adopted, **do not assign a numerical difference**.
4. Concerted Pull participants add modified contest results to determine collective success; the numerical sum is **not** automatically the magnitude of their combined physical force.
5. Unsuccessful Pulls do not contribute a successful forced-movement effect under existing contest rules.
6. Given a stipulated set of physical force vectors, keep the r51 physical vector-composition principle; if those magnitudes are **not** supplied, quantitative displacement remains unresolved.

---

## Historical cumulative decisions through Revision 51

# Encounters — cumulative adopted decisions (Revision 51)

**23 October 2026.** Revision 51 adopts physical vector composition for simultaneously successful, independently declared Pulls on one Being. No Universe engine changes.

## ES-041 — Simultaneous competing Pulls

**Author-confirmed ruling:** “It’s not the same as simultaneous Grapple actions ... If both Pulls are successful, resolve them as a net combined effect based on the physics. For example, if the Pulls are in the opposite directions with the same force, there is no net movement effect. Fundamentally, the movement is the result of the vector combination of the forces applied.”

- **Physical composition, not Grapple conflict:** The already established no-time reroll of incompatible Grapple **control positions** does not apply to physical Pulls. Resolve Pull success per declaration; where multiple Pulls succeed simultaneously on one target, their applied force vectors combine and net movement follows the resultant, within physical and spatial limits.
- **Cancellation:** Equal opposite forces give zero resultant and no net displacement. Independently successful Pulls need not cause movement individually when opposed by other forces. Oblique forces can create resultant movement differing from every individual pull direction.
- **Concurrency:** Evaluate eligible same-second Pull declarations without order-specific sequential movement; resolve the net effect before committing position. Keep current checks, Concerted Pull collaboration requirements, grip continuity, occupancy, legal paths and speed limits. Do not import a Grapple-position reroll.
- **Open modeling question:** The source provides 3d6 + Strength contests to determine success and the rules for pooling cooperative contests. It does **not** define applied force in Newtons or game-unit magnitudes, target inertia, or a conversion from resultant force to hex movement. No rule maps dice totals, skill bonuses, or contest margins directly to vector magnitude. These remain explicitly unresolved for quantitative simulation; do not infer a formula from the author’s example.

### Acceptance tests (Revision 51)

1. A and C have independent Holds on B and independently succeed in simultaneous Pulls in exactly opposite directions with **equal physical force**: resulting displacement is zero; no check is rerolled.
2. The same Pulls have **unequal physical force**: use the net vector for the displacement direction; actual magnitude depends on the outstanding quantitative model and existing legal movement/space limits.
3. Two successes at right angles: resultant direction is diagonal at the physical level; do not select one successful action based on declaration order. Quantizing that result to positions is an open modeling step.
4. One successful and one unsuccessful Pull: only the successful forced-movement effect is eligible under the existing contest rule; keep any other physical restrictions.
5. Two successful incompatible Grapple control-position transitions: preserve the separate reroll-without-time rule; it is not replaced by force composition.
6. Concerted Pull: preserve prior coordination requirement and sum-of-modified-contest-results cooperative procedure. Do not merge competing declarations into a concerted action.
7. Even when contests have unequal totals, do not equate those totals to physical force until an explicit mapping is adopted.

---

## Historical cumulative decisions through Revision 50

# Encounters — cumulative adopted decisions (Revision 50)

**23 October 2026.** Revision 50 expands Pull to all non-forward directions, authorizes Concerted Pull using the established Concerted Rush procedure, and excludes all other Bull rush special provisions. No Universe engine changes.

## ES-041 — Non-forward Pull and Concerted Pull

**Author-confirmed instructions:** “To take care of lateral held motion, let's change backward to non-forward. That covers all directions. None of the rest of the Bull rush's special provisions apply. Multiple Being should indeed be able to cooperate in a Concerted Pull as proposed.”

- **Direction:** Bull rush handles forward forced movement through a physical grip; Pull handles any **non-forward** direction, including lateral and backward. Apply the existing directional movement limits; do not invent a faster sideways or backward rate.
- **Ordinary Pull:** Retain the existing Bull rush base Strength contest, one-second interval, size and stability modifiers, continuing-success rule, and legal displacement restrictions. Every puller must have a Grab/Hold on the target for the whole action.
- **Concerted Pull:** Like Concerted Rush, allies must communicate intent beforehand. Each must hold their own effective Grab/Hold on the common target. Each rolls 3d6 + Strength bonus and ordinary size/stability modifiers, then sum the modified results for the participants on each side. A higher pulling-side sum wins. Legal movement must accommodate every participating puller and the target. The coordination method adds no independent bonus.
- **Grip broken:** Release of any required participating grip ends the relevant ongoing Pull, with the usual earlier/same-second state-commitment rule. No automatic termination of a separately established Grapple.
- **Excluded special provisions:** No shield bonus, Charge continuation/bonus, Mounted Rush special rule, or Bull rush follow-up Trip/Overrun benefits for Pull. Concerted Pull is the **only explicitly authorized** special counterpart.
- **Supersession:** Revision 49's restriction of Pull to backward movement and its open question about Bull rush exceptions are superseded. Its basic physical Hold, timing and spatial constraints remain.

### Acceptance tests (Revision 50)

1. Force another Being forward using the applicable Bull rush; declare Pull for forced sideways, backward or other non-forward displacement through an intact Grab/Hold.
2. Perform a lateral Pull with legal unoccupied path: apply ordinary contest and movement rules. A non-forward direction does not create a special movement speed.
3. Reject a Pull attempt without an effective Grab/Hold; reject participation by a helper who lacks their own effective grip.
4. Two coordinated Beings with existing Grabs, prior communication and compatible intended directions: separately roll 3d6 + Strength bonus and ordinary applicable adjustments, sum modified totals for their side, and compare to target/resisting side. Do not pool into one dice roll or add a separate Concerted Pull bonus.
5. Target is too large for one puller, but lawful helpers cooperate: use the ordinary Concerted Rush help/size provisions with each helper required to maintain a grip. No automatic success; use the aggregate contest.
6. A would-be participant's facing or grip constrains the intended common displacement incompatibly: the illegal spatial outcome cannot be executed; no moving through occupied hexes.
7. Break one required grip before a new continuation second: end the ongoing concerted maneuver. Same-second Break hold cannot retroactively undo movement already resolved in that second.
8. Do not apply Bull rush shield, Charge, Mounted Rush or Trip/Overrun privileges to Pull, including Concerted Pull.
9. Independently established Grapple control persists notwithstanding ending Pull or releasing a physical grip, except under separate established Grapple termination rules.

---

## Historical cumulative decisions through Revision 49 (earlier superseded provisions identified above)

# Encounters — cumulative adopted decisions (Revision 49)

**23 October 2026.** Revision 49 adopts ordinary movement limits for Grab/Hold and a new Pull counterpart to Bull rush. No Universe engine changes.

## ES-041 — Hold-constrained movement and backward Pull

**Author's wording:** “A Grab or Hold does not prohibit ordinary movement, but movement cannot automatically break an effective Hold. A Being wishing to move beyond the limits imposed by a Hold must first break it. A Being wishing to force movement of another Being through an existing Grab or Hold must use Bull rush in a forward direction or Pull in a backward direction.”

- **Ordinary movement:** Neither physical Grab nor continued Hold automatically immobilizes a Being. Moves within grip constraints are permissible; moves beyond require Break hold. No automatic release through walking away. The independent Grapple action remains unaffected.
- **Pull:** The backward counterpart to Bull rush, with its base one-second timing, zero attack and defense levels for the puller, ordinary resisted 3d6+Strength contest and size/stability/continued-success modifiers, and existing movement caps. A Grab/Hold must remain effective for the full maneuver.
- **Spatial outcomes:** With puller stationary, a successful Pull may draw the target closer into legal unoccupied space. With puller moving backward, both Beings can move backward as long as their paths, speed limits, the physical connection and destinations remain valid. No movement into or through occupied hexes; no forced displacement if no legal configuration exists.
- **Grip release:** Author's exact instruction: “If a Grab or Hold is broken, the Pull ends. The universal simultaneous-action rules determine when that release becomes effective.” Earlier effective release prevents later Pull; a same-second Break hold cannot undo movement that already resolved in the movement phase, but prevents later continued Pull.
- **Special-case limits:** The author agreed that the shield, Charge, Concerted Rush, Mounted Rush and Trip/Overrun follow-up privileges from Bull rush should be reviewed for applicability rather than all copied silently. Those are **not adopted as Pull-specific privileges** yet.

### Acceptance tests (Revision 49)

1. A Holds B. B moves while keeping the effective grip within its spatial constraints: use ordinary movement rules. B attempts to leave those constraints without Break hold: prohibit the escape-by-movement.
2. A uses the existing grip to push B forward: resolve Bull rush. A uses it to force movement backward: resolve Pull. Pull without a current Grab/Hold is invalid.
3. Resisted Pull: each side makes 3d6 + Strength bonus with existing Bull rush size and stability adjustments; the puller must win to move the target. A tie leaves forced movement unsuccessful. Unresisted Pull follows Bull rush's existing procedure.
4. A stationary A pulls B toward A: B may enter only a legal, unoccupied closer position; A does not move. B cannot occupy A's hex.
5. A backs away while pulling B: both can move only within their own legal movement limits and occupied-space constraints, including the backward limit for A; an obstacle prevents movement through it.
6. A Grab/Hold is broken in an earlier second: continuing Pull cannot proceed. Break hold resolves in the same second as Pull: movement already resolved that second is not retroactively undone; further Pull ends when release commits.
7. Grapple established independently of the physical Hold remains established despite the latter ending. A successful Pull does not create or terminate Grapple.
8. Do not award Pull shield, Charge, mounted/coordinated, Trip or Overrun benefits solely by analogy to Bull rush; await a separate ruling.

---

## Historical cumulative decisions through Revision 48 (retained for provenance; current rule overrides older contradictory assumptions)

# Encounters — cumulative adopted decisions (Revision 48)

**23 October 2026.** Revision 48 preserves a separate physical Hold and its movement restrictions when a combatant successfully Escapes an established Grapple. No Universe engine code changes.

## ES-041 — Grapple Escape does not bypass an independent physical Hold

**Author-confirmed ruling:** “Yes, the Hold is in place, therefore its effects still hold.”

- Escape resolves **only** the established Grapple action/control position. It neither breaks nor releases a separate, continuing Grab/Hold.
- When the position-based Escape result ordinarily permits movement to an adjacent unoccupied hex, any continuing physical Hold still imposes its ordinary movement restrictions. The Escape action supplies neither a free physical-grip release nor permission to bypass the Hold.
- A successful Grapple Escape remains successful as to Grapple control. Where a separate Hold prevents movement, the listed movement is restricted; do not invent a second check or reinterpret the success as a failure of Escape.
- Physical Holds still end through their separately defined mechanisms, including successful Break hold, failed maintenance, or voluntary release.
- Do not equate the source phrase “still being held” in Grapple position outcomes with an independently established physical Hold; it describes remaining Grapple control unless a distinct Grab/Hold is recorded.

### Acceptance tests

1. A has an established Grapple and a separately maintained physical Hold on B. B succeeds at Grapple Escape. Apply the position-specific Grapple result; A’s separate Hold remains.
2. B’s Grapple Escape ordinarily permits an adjacent unoccupied hex but A’s distinct Hold prohibits that move under existing Hold effects. B cannot make the move solely due to Escape; the success of the Grapple Escape is not overturned.
3. If A has no surviving physical Hold, the ordinary position-specific Escape movement result still applies (subject to any other existing rules).
4. B later breaks A’s physical Hold through a separately declared one-second Break hold Strength contest. Only the targeted physical grip ends; no additional Grapple Escape check is implied.
5. A Grapple Escape fails or ties. The original Grapple-control position is preserved under the existing rule; any independent Hold is likewise unaffected.

---

## Historical cumulative decisions through Revision 47 (superseded decisions identified in prior sections)

**23 October 2026.** Revision 47 separates actions for breaking a physical Grab/Hold from escaping an established Grapple. No Universe engine changes.

## ES-041 — Grab/Hold: Break hold; Grapple: Escape

**Author-confirmed ruling:** “Let's separate the two things. Grab and Hold are broken by Break hold. Escape should be left to Grapple only.”

- **Grab and Hold:** To deliberately **break an opponent’s** physical Grab, including its continued Hold, declare the **one-second Break hold action** against one specific grip. Voluntary release and failed Grab maintenance remain existing independent ways for a grip to end. Apply the existing **opposed Strength ability contest**: each contestant rolls `3d6 + Strength bonus`, and the breaker must get the higher total. A tie keeps the grip.
- **Grapple:** **Escape** is an action applicable only to a **separately established Grapple**. Resolve Escape with the ordinary timed opposed **Grapple check**, including the escaping participant's **Escape Artist skill level as an additional modifier** to Improved Grapple. No separate Grab-escaping check exists.
- **Escape Artist:** Does **not** modify the Break hold Strength contest and does not provide a parallel way to release a physical Grab/Hold. Its pre-existing fixed-DC applications to ropes, entanglements, and confined spaces remain unaffected.
- **Independent state:** Releasing an individual physical Grab/Hold by Break hold does not itself terminate a previously established opponent's Grapple. Changing a combatant's own action can terminate their own Grapple, subject to the Multi-action exception already established.
- **Supersession:** The r32 language allowing an Escape declaration against a Grab as well as a Grapple is withdrawn for physical Grab/Hold. The grab-only Escape Artist declaration/timing uncertainty noted in r46 is resolved by eliminating that declaration, not by inventing another roll.

### Acceptance tests (Revision 47)

1. A successfully Grabs B and maintains it as a Hold, with no Grapple yet established. B attempts Escape: **invalid action** in this state. B may change actions to Break hold, using one second and the opposed Strength contest.
2. B wins Break hold with a higher `3d6 + Strength bonus` total: only the targeted physical grip is released. A tie or B's loss leaves that grip in place. Escape Artist level does not enter either total.
3. A has an established Grapple against B. B declares Escape: check at the normal six-second Grapple timing or legally accelerated time, using the opposed Grapple formula and B's additive Escape Artist contribution. No Break hold check is required first.
4. A physical Hold is broken but A's established Grapple remains: the existing Grapple action/position is **not** automatically terminated by physical grip loss.
5. An Escape Artist check to slip bonds or entanglement still uses its published fixed-DC and timing rules. It is **not** a Grapple Escape action or a one-second Break hold contest.
6. An unfinished **initial** Grapple attempt still requires its successful Grab prerequisite; losing that prerequisite before establishing Grapple remains governed by r46 and ordinary simultaneity.

---

## Historical cumulative decisions through Revision 46 (older contradictory rulings are superseded as identified above)

# Encounters — cumulative adopted decisions (Revision 46)

**23 October 2026.** Revision 46 applies the author's correction separating physical Grab/Hold from Grapple and explicitly supersedes incompatible earlier language. No Universe engine changes.

## ES-041 — Physical Grab/Hold and independently established Grapple

**Author clarification:** “Hold is the continuation of a Grab. Neither Grab nor Hold constitutes a Grapple, though the Grab is a prerequisite to a Grapple. ... Breaking a Hold does not terminate a Grapple. The only ways to terminate an opponent's Grapple is to Escape or have them go unconscious.”

- **Separate entities and actions:** Grab establishes one physical grip; Hold is that Grab continuing. Neither constitutes Grapple. Grapple initiation requires a successful Grab; it is a separately prepared action and check.
- **Existing Grapple persists:** An opponent's *already-established* Grapple is not canceled by breaking any physical Hold, including its last grip. The opponent's established Grapple ends through Escape or unconsciousness. A combatant may end *their own* Grapple by action change under the previously adopted action/Multi-action rules.
- **Supersession of r45:** The earlier automatic termination of B's unfinished Grapple on loss of B's last grip was incorrect **for an already-established Grapple**. Preserve loss of physical prerequisite for an **unestablished first Grapple attempt**, and preserve same-second simultaneous action resolution.
- **Separate named checks:** A **Grab check** establishes/maintains an unwilling target's individual Grab/Hold. It uses the same opposed 3d6 + Improved Grapple + best applicable Strength/Dexterity bonus + relevant modifiers procedure as the **Grapple check**, but a separate name, declaration, and result. This replaces the previously adopted d20-vs-d20 attack/defense Grab check for an unwilling Being (r40). Initial touch attacks, willing/object Grab exceptions, and the one-second Break hold Strength contest remain separate.
- **Grapple control terminology:** Physical Hold/Grab maintenance is not synonymous with Grapple-control positions. Takedown, Reverse, Pin, and Escape use the Grapple check. The r41 first-check-vs-coincident-Grab-maintenance substitution remains a timing exception, not proof that the two states are identical.
- **Not decided by this clarification:** Other Grab-versus-Escape Artist eligibility outside an established Grapple, and nuanced changes to grapple-position outcomes when grips are broken, should not be guessed. Review under ES-041 if needed.

### Acceptance tests

1. Successful physical Grab establishes a grip, not a Grapple; a successful maintenance Grab check continues only that Hold.
2. Failed/tied maintenance Grab check ends that grip; an already-established Grapple by the same opponent remains scheduled and is not forcibly canceled.
3. Releasing the **last** physical Hold during an established Grapple does not terminate the opponent's Grapple.
4. Releasing the sole Grab prerequisite **before the first successful Grapple check** makes an unfinished *initiation* ineligible, permitting an ordinary new action choice.
5. Escape or unconsciousness terminates the opponent's established Grapple; a combatant's own action change can terminate only that combatant's Grapple.
6. Grab and Grapple check formulas are structurally identical but their effects and labels are separate; touch attacks, grabbed objects and Break hold Strength contests are unaffected.
7. An initial Grapple check coincident with Grab maintenance still replaces the latter; an unsuccessful initial Grapple check leaves the original Grab in effect as previously adopted.

---

## Historical cumulative decisions through Revision 45 (retained for provenance; r40 and r45 portions superseded as stated above)

# Encounters — cumulative adopted decisions (Revision 45)

**23 October 2026.** Revision 45 applies the author's ruling on loss of Grapple's last physical prerequisite. No Universe engine code changed.

## ES-041 — Last required grip releases pending Grapple and permits new action choice

**Author's ruling:** “Yes, the pending action should be immediately terminated and provide B with a new action choice.” The scenario is that A's Break hold actually releases B's **only remaining necessary grip**, before B's already-scheduled Grapple action resolves.

- **Release is the trigger, not declaration:** A deciding to Break hold ends A's own Grapple (absent legal Multi-action), but leaves B's independent action pending. Only successful release of the last qualifying grip can remove B's physical prerequisite.
- **Immediate termination at the effective boundary:** When the successful release is committed, cancel B's still-unfinished Grapple preparation and remove its pending check from the timeline. Give B the normal new action choice at that decision point. B's new action is scheduled under its own timing and cannot resolve retroactively in the release second.
- **An alternative qualifying grip matters:** Losing a particular grip does not terminate an unfinished Grapple that remains supported by another qualifying grip. Do not presume that multiple grips are all one grip.
- **Preserve simultaneity:** A Break hold and an otherwise eligible Grapple check resolving in the same second both resolve against the common pre-action snapshot. No same-second cancellation. After simultaneous effects commit, any further unfinished Grapple work that depended on the now-lost last grip terminates.
- **No new dice or priority rule:** The one-second Break hold Strength contest, opposed Grapple skill formula and timing, independent Grab maintenance, and Multi-action restrictions remain unchanged.

### Acceptance tests (Revision 45)

| Scenario | Expected result |
| --- | --- |
| A declares Break hold while B has a pending Grapple | B continues; no physical grip has yet been removed |
| A breaks B's last required grip in second 6; B's Grapple scheduled for second 8 | B's pending action terminates when the second-6 release commits; B may choose and prepare a new action |
| A loses or ties the Break hold check | Target grip remains; B's pending Grapple continues |
| A successfully breaks one of B's two independently qualifying grips | Only target grip ends; B still has a qualifying prerequisite |
| A's Break hold and B's eligible Grapple check are both due in second 6 | Both checks resolve from the same frozen state; release does not nullify B's same-second check |
| B already resolved the Grapple in second 5; grip released second 6 | No retroactive cancellation of the completed action |
| B chooses a new action when the last grip releases | Normal action declaration and duration apply; no additional instantaneous check |

---

## Earlier cumulative decision record (through Revision 44)

**23 October 2026.** Builds on Revision 43. No Universe implementation changes.

## ES-041 — Break hold terminates only the initiating combatant's Grapple action

**Author clarification:** “If A initiates a Break hold, it terminates A's Grapple action. It does not affect B's Grapple action.”

- Each combatant's **Grapple action is independently declared and maintained**. There is no shared action that automatically ends for both participants when only one changes actions.
- Without a valid concurrent Multi-action design, A declaring Break hold terminates **A's** Grapple action and cancels **A's** unfinished Grapple preparation. **B's Grapple action continues unaffected** by this action change.
- Ending A's Grapple action **does not itself release existing physical grips** belonging to either participant. A subsequent successfully resolved Break hold can release **one targeted grip**. Other Grabs remain subject to their own maintenance, release, and other existing rules.
- The six-second opposed Grapple timing and formula, one-second Break hold Strength contest, simultaneous-action rule, and Multi-action eligibility/penalties are unchanged.
- Still unresolved: the exact eligibility and outcome of B's future Grapple check if A ceases grappling, especially if Break hold later removes a grip essential to a declared control state. Do not silently cancel B's action or invent a new check.

### Acceptance tests (Revision 44)

| Situation | Expected outcome |
| --- | --- |
| A and B independently declared Grapple; A switches to Break hold without Multi-action | A's Grapple action terminates and unfinished A Grapple is canceled; B's action remains scheduled |
| A switches actions before the Break hold resolves | No previously established grip is released by the declaration alone |
| Break hold fails or ties | Target grip remains; B's Grapple action unaffected; A's former Grapple action does not resume |
| Break hold succeeds against one of two distinct grips | Exactly the targeted grip is released; second grip persists subject to usual maintenance |
| A has a legal Multi-action program including Grapple and Break hold | A may continue both within existing skill, timing, compatibility, and penalty constraints; B's action remains independent |
| B's Grapple check becomes due after A changed action | Do not cancel B's declared action automatically; further eligibility/consequence rule remains open rather than being invented |

---

## Archived cumulative decision record through Revision 43

**23 October 2026.** Builds on Revision 42. No Universe engine implementation changes.

## ES-041 — Breaking a Grab during an existing Grapple; Multi-action requirement

**Author-confirmed ruling:** “Only if the combatant who is already Grappling has the Multi-action skill. Without it, changing an action to Break hold interrupts the Grapple.”

- **Without Multi-action:** To declare the one-second Break hold action, interrupt the combatant's existing Grapple. Cancel any associated not-yet-resolved Grapple action. A failed Break hold does not resurrect the canceled action.
- **With Multi-action:** A combatant may continue Grapple and separately attempt Break hold only when both are components of a legally **declared Multiple actions** program. Apply the original priority penalty `3(n-1)` for `n` parallel actions, normal timing, common defense-point distribution, and restrictions on physically incompatible component actions. Multi-action skill alone does not give a free check or retroactively extend a single-action declaration.
- **Check unchanged:** Break hold is the existing one-second opposed **3d6 + Strength bonus** contest to release one targeted hold. Grapple retains its separate opposed skill-check formula and usual timed intervals. Neither check substitutes for the other.
- **Scope:** Do not silently infer that interrupting one participant's action frees other independent grabs or automatically ends another participant's control. Those state-interaction cases remain under ES-041.

### Acceptance tests (Revision 43)

| Situation | Expected outcome |
| --- | --- |
| Grappler without Multi-action declares Break hold while preparing Grapple check | The Grapple is interrupted; pending Grapple check canceled; schedule one-second Break hold |
| Break hold subsequently fails or ties | Targeted grip remains; canceled prior Grapple action does not resume |
| Grappler with Multi-action designs and declares valid concurrent Grapple + Break hold | Both allowed subject to Multiple actions timing/priority, same-limb compatibility and shared-defense requirements |
| Grappler has Multi-action but no valid multiple-action declaration | Cannot add a free Break hold while preserving the ongoing Grapple |
| Break hold wins Strength contest against one of several grips | Only targeted grip ends; independent grips do not automatically break |
| No Multi-action; Grapple action already resolved earlier | Past result remains; any not-yet-resolved ongoing Grapple preparation is interrupted by the new declaration |

## Further ES-041 questions

Whether the loss of one grip changes an already-established overall Grapple state when other grips remain, and how to restart Grapple after it has been interrupted, have not been newly decided in this revision.

## ES-041 — Failure to transition to Grapple leaves Grab intact

**Author-confirmed ruling:** “Yes, A's original Grab remains established until there is something to terminate it.” A failed or tied **first opposed Grapple check** does not terminate the prerequisite Grab. The attempt to improve a successful Grab into a Grapple has failed, but the independently established Grab persists until an applicable terminating action or rule affects that particular grip.

This explicitly resolves the consequence left undecided in Revision 41: if the first opposed Grapple check **replaces** coincident six-second Grab maintenance, an unsuccessful Grapple attempt does **not** imply that a maintenance check was lost. There is no second check at that moment. A later independently applicable maintenance failure, a successful declared Break hold, or voluntary release can still end the Grab. Other grips are independent. This ruling does not choose a new date for the next maintenance check.

### Acceptance tests (Revision 42)

| Case | Expected result |
| --- | --- |
| A successfully Grabs B and loses the first opposed Grapple check | Grapple not established; original Grab remains |
| The first opposed Grapple check ties | Grapple not established; original Grab remains |
| Same-grip Grab maintenance would be due in the same second and is replaced by first Grapple check, which fails | Single Grapple check only; no presumed failed Grab maintenance; Grab remains |
| At a later separately applicable maintenance check the holder fails or ties | The particular Grab terminates under existing Grab maintenance rules |
| B subsequently wins a separately declared one-second Break hold contest | The targeted Grab terminates |
| A's independent second grip exists when first transition fails | Second grip unaffected |

## ES-041 — The first Grapple check supersedes coincident Grab maintenance

**Author-confirmed ruling: “Replace.”** When the first opposed Grapple check following a successfully established Grab is scheduled to resolve in the **same second** as six-second Grab maintenance **for the same prerequisite grip**, the opposed Grapple check **replaces** that Grab maintenance check. **Do not roll both checks.**

This is a check *replacement* at the transition, not a replacement of the initial successful Grab required before Grapple:

1. Establish the prerequisite Grab under its own one-second timing and opposed attack/defense procedure.
2. Prepare the initial opposed Grapple check for the usual six seconds after the successful Grab, with valid Combat Strategy timing adjustments.
3. If that initial check and maintenance of the same Grab coincide, resolve **one opposed Grapple skill check** (3d6 + Improved Grapple skill level + the greater applicable Strength/Dexterity ability bonus + situational modifiers; use the additional Escape Artist level only when Escape is declared), not an additional opposed d20 Grab check.
4. Preserve existing consequences of success, failure or tie. Do not impose an unapproved extra failure consequence on the prerequisite Grab.
5. Independently held grips by other hands or participants remain separate; this ruling does not cancel their own maintenance schedules.

This ruling is consistent with the previous decisions that Escape and Grapple position transitions use a single opposed Grapple check. The normal one-second **Break hold** action and its Strength contest remain distinct.

### Acceptance tests

| Case | Expected result |
| --- | --- |
| Grab established at second 0; initial Grapple preparation completes at second 6 simultaneously with maintenance of same grip | Only one opposed Grapple check; zero additional Grab-maintenance rolls |
| First Grapple check legally accelerated to second 4 | Opposed Grapple check in second 4, not on initial Grab success; its timing is unchanged by the replacement ruling |
| Same-second Grab maintenance due on another independent hand | That hand's applicable separate maintenance is not automatically replaced |
| Opposed Grapple check ends in a tie | Apply previously adopted Grapple tie rule; do not invent a separate Grab roll or automatic release |
| Opponent declares an individual one-second Break hold | Separate 3d6 + Strength bonus contest; not automatically incorporated into this transition |
| Grapple becomes established | Subsequent check timing follows the existing six-second/strategy-adjustable Grapple procedure |

## Still outstanding under ES-041

- Independently held grips and interactions among multiple hands.
- The failure consequence is resolved in Revision 42: the existing prerequisite Grab persists until separately terminated.
- Exact eligibility boundaries for the one-second **Break hold** action versus scheduled **Grapple Escape**.

Earlier audit snapshots are carried forward but have **not** been revalidated for Revision 41.


## Revision 59 — Ratified throwing calibration and size scaling

- Adopt Medium reference arm length **0.800 m**, not prior 0.7865 m; linear length doubles per size category (0.100, 0.200, 0.400, 0.800, 1.600, 3.200, 6.400, 12.800 m). Throw acceleration distance equals reference arm length; no separate hand, arm-mass, or throwing-speed-ceiling model.
- Absolute Strength is independent of size: equal Strength means exactly equal maximum lifting and carrying capacities. Muscle area influences attainable Strength, but does not add an extra force multiplier at equal Strength. Lifting-capacity modeling is independent from throwing calibration.
- Adopt smooth empirical throwing response as best available approximation, fitted to 25 historical derived table entries because individual human distance observations cannot be recovered: `Vrelease = [5 × (S+ThrowModifier−2)/2] × exp(−[(m/H(S))/0.08081]^0.6010) × sqrt(L/0.8 m)` in yd/s; one-time acquired Throw modifier is +1. Use the existing heavy-load table as the historical numerical normalizer **only**, not as a physical causal link.
- Ratify work-energy, square-root-of-arm-length scaling at equal Strength and projectile mass. Reject linear-in-arm-length velocity scaling (Alternative B). No independent hand-speed ceiling is needed.
- Preserve the existing hard maximum throwable mass and effective adjacent-hex speed threshold. Historical velocity-percent lookup is superseded for calculation but retained for provenance. Trajectory/wind arithmetic, edge-case projectile drag, engine migration and reference summary table reconciliation remain open for verification; no new simulation of feather drag is adopted.
- This resolution covers the main throwing calibration and size-scaling decisions **but not** the general ES-041 non-throwing force and Grapple work.


## Revision 60 — Throwing trajectories and release height adopted

- Standard throwing gravity is exactly **10 m/s²** (not 10 yd/s²).
- Release height defaults to **Being body height above landing level**; 6 ft (1.8288 m) for reference Medium humanoid. Explicitly substitute other release heights or target elevations.
- Reference Throwing Table maximum range uses the optimized projectile path from 6 ft, not same-elevation `v²/g` unless release and landing heights coincide. Time aloft is the physically consistent flight duration for that optimized trajectory. Range increment is horizontal launch distance from 6 ft.
- Compute actual-projectile trajectories from actual smooth-model release speed; calculate unrounded and round tabulations only for display.
- Aerodynamic drag and wind mechanics are deferred to the general launched-projectile review (archery, catapults, etc.). No speed ceiling, additional arm mechanics, or size-dependent Strength multiplier is introduced.
