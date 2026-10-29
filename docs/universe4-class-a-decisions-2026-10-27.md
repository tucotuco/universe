# Universe 4 — Class A Encounter Semantics Decision Record

Date: 2026-10-27\
Status: Adopted decisions consolidated; explicitly open decisions remain open\
Scope: Native Universe Encounter action resolution, simultaneous effects, and resolution-on-demand\
Implementation authorization: **None. This is a design/decision record, not a code-change instruction.**

## Authority and scope

This record consolidates the user's Universe 4 Class A selections, including corrections to initially proposed decisions. An earlier *proposed* rule must not override a later user correction. In particular: no zero-HP damage clamp is authorized by these decisions; ordinary damage remains additive below zero; multiple fatal effects do not stack; and one Object cannot be used for two simultaneous actions.

These rules are authoritative *design intentions*, not claims about the behavior of the current repository. The October 27 Codex architectural analyses report that current `ObjectInstance.damage()` zero-clamps ordinary damage and that `Action.do_fatal_hit()` conditionally assigns −10 HP; the native resolver still applies most effects sequentially. Implementation must deliberately migrate these behaviors with tests, not assume compatibility.

## A. Time and movement — T1–T4 ADOPTED

- **T1: One-second simultaneous action intervals.** Physical computations (position, velocity, acceleration, distance, and related quantities) can use fractional seconds. Non-movement actions with nominal completion times in the same interval **(n−1, n]** are simultaneous and resolve at integer-time boundary **n**.
- **T2: Chronological settlement of long steps.** A multi-second Encounter step processes successive one-second intervals chronologically, committing each interval before the next snapshot. Subject to equivalent scheduled inputs, physical trajectories, and random streams, a long step should match the succession of one-second steps.
- **T3: Movement before action resolution.** Advance movement to each interval's end using the established movement/kinematics model; then freeze one post-movement, pre-action world snapshot and evaluate the interval's non-movement actions. Do not substitute the final position of a long step for positions at earlier boundaries or invent a new interpolation model.
- **T4: Exact boundaries.** An action nominally completing exactly at integer time **n** belongs to **(n−1, n]**, resolved at **n**. Fractional calculations retain their numerical precision; they do not create separate action-commit instants within the same second.
- **T5: Overdue actions — DEFERRED.** Behavior when an action's designated one-second boundary has already been processed is not adopted. The question is distinct from normal fractional completions, which are not overdue.

Additional implementation questions: handling of events scheduled at initial time zero and zero-duration actions; scheduling new same-boundary actions during resolution; treatment of genuinely overdue actions; and failure/clock behavior if a boundary cannot commit.

## B. Damage and per-action results — H1–H5 USER-CORRECTED DECISIONS

- **H1: Ordinary HP damage adds without a zero floor.** Compute each simultaneous attack independently from the common snapshot, including protection, and add the HP damage on each target. Example: 12 HP − 8 − 7 = **−3 HP**.
- **H2: Fatal effects are not additive with each other; ordinary damage is additive.** One or more successful simultaneous fatal effects establish a fatal result of **−10 HP** (fatal effects do not stack). Additional simultaneous ordinary damage is subtracted: fatal + 6 ordinary damage yields **−16 HP**; two fatal effects alone yield **−10 HP**. Retain established fatal confirmation/save mechanics. A fatal effect must not restore HP when the target is already below −10; the exact reducer for that edge case should be made explicit before implementation.
- **H3: Damage continues below zero.** Starting negative HP does not prevent additional ordinary damage: −10 − 6 = **−16 HP**.
- **H4: Shared-snapshot equipment protection and cumulative equipment damage.** For each simultaneous impact, shield/armor protection uses the same pre-action equipment state. Add damage to each relevant shield/armor item's HP at settlement; item HP can become negative. Example: armor 6 HP − 4 − 4 = **−2 HP**. Do not invent new degradation, breakage, drop, or removal mechanics.
- **H5: Individual result records show shared batch-final HP.** Preserve each action's own damage/protection details, with target HP-before drawn from the shared snapshot and HP-after reflecting the final batch-settled HP. Example: both attacks in H1 record HP-before 12, HP-after −3, with their own distinct damage contributions.

**Open edge case:** At least one fatal effect against a Being already below −10 HP must never cause healing. Recommended interpretation for explicit approval: use the lesser of starting HP and −10 as the fatal baseline, then subtract the batch's ordinary damage. This is a recommendation, not an additional adopted rule.

## C. Defenses and shared Objects — F1–F2 ADOPTED

- **F1: Multiple valid designated defenses.** Every valid defense designated against the same strike evaluates from the common snapshot; one successful defense is sufficient to stop the designated strike. Successful defenses do not stack protection benefits; qualifying attempts retain their established practice outcomes and attack-specific binding.
- **F2: Exclusive simultaneous Object use.** The **same Object cannot be used for two actions simultaneously**. This expressly rejects the earlier suggestion that the same weapon could be used both to attack and to Parry within the same resolution second. A batch coordinator must detect conflicts; it cannot quietly double-use an Object.

**Open subdecisions:** Precisely distinguish active *use* of an Object from passive protection, possession, or receiving simultaneous impacts (important for shield interceptions and H4); define whether incompatible actions are rejected at scheduling time, rejected as a conflicting resolution batch, or handled through another explicitly approved mechanism. Do not arbitrarily select a winner. Defenses employing distinct eligible Objects may coexist, subject to other existing rules.

## D. Reality, Observation, Belief — R1–R5 ADOPTED

- **R1: Shared batch-local objective realization.** Simultaneous actions requiring the same unresolved objective fact use one shared candidate realization. It becomes established Reality only when the entire batch commits.
- **R2: Statistical group consistency.** Simultaneous group observations share one underlying objective group composition. Observation samples and estimates can differ by observer; do not materialize individual Beings unless another requirement demands that resolution.
- **R3: Shared historical episode realization.** Simultaneous inquiries into the same unresolved historical episode use one candidate objective episode and supporting facts. Respect already-established history and validate the combined proposed history before commit.
- **R4: Observer-specific observations and beliefs.** One shared Reality can legitimately produce different observer-specific evidence, interpretations, and beliefs according to each observer's pre-action perceptual and cognitive state.
- **R5: Reject irreconcilable objective facts atomically.** If candidates contradict established Reality or one another and cannot be reconciled, reject the **entire action batch** without publishing partial consequences. Do not overwrite prior truth, choose arbitrary winners, or regenerate an alternative merely to conceal the contradiction.

R5 concerns **objective** contradictions. Differences between observations or beliefs do not themselves constitute contradictory Reality.

## Invariants that remain in force

- Each resolution second has one post-movement, pre-action snapshot for all its non-movement actions.
- All consequences of a successfully evaluated one-second batch commit together; earlier action effects must not leak into later evaluations within the batch.
- Frozen Q/B is available as an input. Physical-fatigue proposals and work accounting must not modify Q/B early or double-charge overlapping work.
- Preserve the native Encounter engine, established combat calculations except where these decisions explicitly revise semantics, resolution-on-demand, and Object/Being identities visible to consumers.
- Any transaction design must stage objective realization and observer-specific effects as well as ordinary combat consequences.

## Open questions before native resolver *implementation*

1. **T5 and boundary anomalies**: overdue events; zero-duration events; event deadlines at initial time 0; due actions scheduled during a boundary; direct `resolve_actions(as_of=...)` behavior.
2. **F2 operational conflict policy**: definition of active Object use versus passive interception/protection, and when/how incompatible simultaneous uses are refused.
3. **H2 low-HP fatal edge**: confirm no-healing fatal reducer for initial HP below −10 and ordinary damage in the same batch.
4. **Failed-batch scope**: reject all non-movement consequences for that second; determine whether movement for the failed second, clock advancement, and preceding committed seconds remain or are rolled back, and how retry is supported.
5. **RNG and determinism contract**: staged/random draw allocation, abort/retry state restoration, deterministic replay, and side-effect-free injected generators.
6. **Events, hooks, and extensibility**: prevalidation/acceptance of arbitrary Events and mutating completion callbacks, cancellation/scheduling effects, and post-commit notification delivery semantics.
7. **Action-result/provenance compatibility**: preserve current result schemas while distinguishing individual attack damage from shared batch-final state; represent multiple successful defenses without losing provenance.

The first three are residual **Class A simulation semantics**; the next four are largely **Class B engineering contracts** (to be reviewed, not silently invented).

## Recommended next Codex engineering increment

**Characterization and specification tests only, no production resolver refactoring yet.** Codex can inspect the current tree, establish and record a complete test baseline, and add narrowly scoped tests that characterize current outcomes, mutation timing, saving/serialization, random draws, and conflicting dependencies. Separate tests of intentional current behavior from tests asserting the new adopted semantics (which should be clearly marked as pending until implementation). Existing zero-clamping and sequential side effects must not become normative assertions merely because they are today's code behavior.

Before implementing an Encounter-owned snapshot/proposal/commit engine, settle the remaining Class A semantic edges above and approve its error/RNG/callback contracts. All implementation must target the existing native resolver; do not construct a parallel combat simulator.

## Source analyses

- `encounter-resolve-actions-architectural-audit.md` (Codex, 2026-10-27)
- `encounter-snapshot-transaction-dependency-analysis.md` (Codex, 2026-10-27)

The source analyses are evidence for current implementation behavior. Adopted decisions above supersede incompatible implementation details and superseded draft proposals.
