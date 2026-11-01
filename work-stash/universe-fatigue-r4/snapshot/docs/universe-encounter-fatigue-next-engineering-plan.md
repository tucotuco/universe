# Universe — Next Engineering Milestone: Native Encounter–Fatigue Integration

**Reconstructed 26 October 2026 from the recovered Universe 3 integration specification.**

**Status:** execution plan, not a claim that the live Universe repository has been modified.

## Fixed design decisions

- Ordinary Universe play is software-managed; no manual fatigue bookkeeping requirement.
- Q and B are the **only persistent physical-fatigue quantities**, stored at full precision in `[0,1]`. Fresh state is `Q=B=1`. Do not invent an exertion-point or legacy fatigue-level meter.
- Reuse the unchanged R4 physiology model for depletion, recovery, sustainable output and available output. Fitness is a trainable ability. Run skill modifies running physiology only when actually running.
- One universal physical-check modifier: `-floor(5*(1-standard_output(Q,B))+0.5)`. Fixed PCFS=5; apply **once** per physically demanding check to the initiator and responder. No stacking legacy physical fatigue penalties.
- Infeasibility is **task-specific**, not automatic incapacitation; voluntary all-out effort is capped. Never modify a compulsory workload or mandatory pace to manufacture success.
- Existing Encounter engine owns action timing, perception, movement, combat, damage, incompatible-outcome rerolls, and world state commits. The fatigue bridge may **only propose** Q/B updates.
- Resolve movement, then freeze the *post-movement/pre-nonmovement* state for every non-movement action resolving in a given second. Evaluate all those actions against the **same** snapshot. Commit all compatible Being/Object effects (fatigue, damage, incapacitation, etc.) only after every resolution completes. Conflict rerolls do not consume extra time or fatigue.
- Actual realized work is recorded; unsuccessful attempts still incur their actual exertion. Workloads from overlapping actions must never be naively added or counted twice.
- Preserve ordered history for resolution on demand; do not average alternating effort and rest.

## Initial repository audit — the first executable step

1. Record branch, HEAD commit, working-tree status and the precise test command. Do not overwrite user changes.
2. Run existing complete test suite **before** modifications; retain baseline results and any existing failures.
3. Inspect current code, particularly:
   - `src/being.py` (state, initialization, serialization, histories)
   - `src/encounter.py` (per-second scheduling, movement, snapshots, transactions)
   - `src/melee_combat.py` (strikes and contest checks)
   - `src/melee_defense.py` (Parry/Dodge/ready state)
   - `src/tactical_duel.py` (UI-facing combat orchestration)
   - `src/exertion.py` (legacy physical-fatigue logic and mental-stress separation)
   - tests, configs, save-game compatibility, replay pathways
4. Locate and verify the previous independent `encounter_fatigue_bridge.py`, reference `universe_physical_fatigue_r4.py` and `standard_fatigue_check.py` before duplicating any of them.

## Patch 1 — Being state and stable per-second fatigue views

**Goal:** native Being objects persist Q and B, and the Encounter resolver can expose a frozen fatigue view at the existing post-movement snapshot without changing combat outcomes yet.

- Add explicit persistent fatigue (`q`, `b`) with validation and versioned `physiology_id` reference, using repository conventions.
- Add explicit migration for old saves: define fresh default for missing fatigue only where migration policy permits; **do not infer Q/B from obsolete fatigue scores**.
- Include Q/B in save/load, initial and committed state snapshots, history and replay fingerprints.
- Adapt to the existing bridge API rather than reimplementing fatigue equations.
- Provide an invariant that every action due at time `t` sees the same frozen Q/B and physical-check modifier; evaluating an action cannot mutate that frozen state.
- Keep old physical-fatigue penalties disabled at the interface as soon as the new modifier is applied, while retaining mental fatigue; avoid a period of double penalties.

### Patch 1 acceptance tests

1. Fresh Being state Q=B=1; load old-save fixture under an explicitly documented migration policy.
2. Save/load round trip preserves Q/B exactly within serialization fidelity and resolves `physiology_id` deterministically.
3. Two same-second physical checks see identical Q/B even if the first action would cause injury, incapacitation or resource depletion.
4. Applying a check modifier once is observable; no previous physical-fatigue modifier is added.
5. A pending Q/B proposal does not change native state until the world transaction commits.
6. Baseline Encounter tests continue passing; no timing, defense, attack or dice behavior changes when fatigue remains fully rested.

## Patch 2 — Work contributions and nonduplication

**Goal:** introduce a native physical-work provider that represents what each Being actually did in a second, with no duplicate movement, strike, defense, grapple or passive resistance work.

- Represent time-bounded movements, muscular force/work, stationary sustained effort and recovery with explicitly defined provenance.
- Convert those *actual* contributions to a physiologically normalized workload `u`, slow-wear factor, and mode profile (by inherited configuration).
- Do not sum independent normalized `u` values. For overlap, either derive one nonduplicated realized effort from compatible physical work or split into temporally ordered subintervals. Reject unsupported multi-mode combinations rather than guessing.
- Cover movement, strike, Parry, Dodge, Touch, Grab, Grapple, Hold maintenance, Escape, reactions, idle and rest. Start with strictly bounded and independently testable cases.
- Preserve the accepted `u=0.70` Grapple experimental reference without claiming it is a universal workload for grappling.

### Patch 2 acceptance tests

- Movement+strike and movement+Parry do not charge duplicate shared exertion.
- Passive resistance is accounted for, even if no action was initiated.
- A failed strike and unsuccessful Grab still charge exertion that was actually performed.
- One-second and fractional-second interval splits converge to unchanged R4 reference behavior.
- Required action incapability is distinct from an unsuccessful feasible action and a naturally capped all-out effort.

## Patch 3 — Transactional Encounter integration

1. Capture physical effort from movement while resolving movement spatially.
2. Construct the common post-movement frozen fatigue frame.
3. Resolve all non-movement actions due this second using the same frame, appropriate once-per-check penalty and ordinary R60 procedures.
4. Solve incompatible simultaneous outcomes with existing no-time conflict rerolls; do not double-charge workload.
5. Consolidate realized workload per Being; obtain pending Q/B updates from the unchanged fatigue bridge.
6. Commit all compatible Being/Object effects atomically in the existing native transaction.
7. Write a deterministic action/work/dice/config-version journal sufficient for replay and resolution-on-demand reconstruction.

## Validation and completion

- Repeat the established Combat A–D tests where source mechanics match, and use new baseline fixtures where they do not; the R4.9 Grapple subset is not an authoritative replacement for native Encounter.
- Explicitly test concurrent incapacitation, shield damage, object destruction, prepared Parry/Dodge, grappling grip-vs-control distinction, early exhaustion, nonhuman and Run profiles, recovery, overlap and nondeterminism under a recorded seed.
- UI: optional exact Q/B inspection, Fresh/Winded/Tired/Weary/Exhausted descriptive labels, workload history and replay. No required fatigue paperwork.
- Reconcile adopted R60 rules text and universal-table research appendix. Remove superseded old **physical** fatigue language only when live runtime and documents match; retain mental fatigue separately.

## Required input before altering Universe sources

The latest Universe checkout or a repository connection that includes `src/`, `tests/`, configuration/packaging files and the current test command, plus the original bridge implementation if available. Do not patch against guessed APIs or pretend a prior test count is a current baseline.

## Deliberately excluded

- Building another action or combat resolver inside the fatigue workbench.
- New persistent fatigue meters, automatic incapacitation on Q=0, or hand-computation as an ordinary-play requirement.
- Species-specific universal physical-check tables or configurable PCFS.
- Thermoregulation, heat and dehydration, and uncalibrated flying workloads.
- Retrofitting unverified hardcoded load coefficients into all combat actions.
