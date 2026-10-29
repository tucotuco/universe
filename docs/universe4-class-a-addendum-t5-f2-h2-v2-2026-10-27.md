# Universe 4 — Class A Addendum v2: T5, F2, H2

**Date:** 2026-10-27\
**Status:** Adopted simulation semantics; production implementation not authorized\
**Precedence:** Supersedes contradictory passages in `universe4-class-a-decisions-2026-10-27.md` and in `universe4-class-a-addendum-t5-f2-h2-2026-10-27.md`.

## T5 — One-second resolution boundary invariants

1. Simulation time begins at `t = 0`. An Action **may be scheduled and started at time zero**.
2. **Every Action must have a duration of at least one second.** No zero-duration, fractional-duration-shorter-than-one-second, or negative-duration Action is valid. An Action cannot complete or resolve at `t = 0`.
3. Kinematic and other physical calculations retain fractional-second precision. Nominal completions in interval `(n−1, n]` enter the **same** action-resolution batch at integer time `n`, after movement to that boundary; all non-movement outcomes evaluate a common pre-action snapshot and commit together.
4. Every integer-second boundary crossed by Encounter progression must be processed in chronological order. The engine must not skip a designated resolution boundary or silently process an overdue Action at a later boundary. Missed/duplicate boundaries are **invariant violations**, not an ordinary gameplay option.
5. No Action may be newly scheduled into a boundary that is already resolving or has already been committed. Scheduling validation must detect this before registering any Action or causing authoritative effects.
6. Duration and final deadline validation must account for `on_schedule()` hooks: an intermediate constructor value is not proof that a successfully scheduled Action has zero duration.

**Engineering investigation, not additional simulation policy:** How the native `step()`, `run()`, direct `resolve_actions()`, fractional stepping, load/restore, failures, custom Events, and hook-driven scheduling uphold these invariants; errors and recovery of already-corrupt states must be proposed for review, not invented as late-execution mechanics.

## F2 — Exclusive active Object use and accepted action choices

1. An **Action is a scheduled activity**. The same Object cannot be actively used by two simultaneous Actions. Such conflicts must be detected **during scheduling**, not selected or arbitrated at resolution.
2. Passive effects (armor protection, passive shield interception, possession, receiving attacks/damage) are **not Actions** and do not constitute a second active use. Multiple simultaneous impacts may affect the same shield/armor Object; they use the common pre-action snapshot and aggregate equipment damage under H4.
3. The group-choice workflow is:
   - **Propose action choices.** Construct or edit a complete candidate set; nothing is authoritatively scheduled yet.
   - **Validate the complete choice set.** Check every proposed Action against existing commitments and other Actions in the set, including timing and exclusive Object use.
   - **If invalid, return to proposing/editing and revalidate.** Report actionable conflicts. Never accept an invalid set, silently accept a valid subset, or leave registration/hook side effects.
   - **Accept a valid set as a choice.** Only the validated complete set can become an accepted selection. This is a positive acceptance state, not a choice between accepting and undoing an invalid set.
4. **Group-level undo/replacement** of an accepted selection must be possible before execution, without leaving partial scheduling state. The distinction between an accepted *choice*, authoritative scheduling/registration, and subsequent execution/cancellation must be made explicit in the engineering interface. Undo of a pre-execution selection is not a rollback of already-executed simulation time.
5. The exact active-use interval(s), multi-Object actions, readiness, and the interaction between use-window overlap and common one-second resolution batches must be characterized and any genuine ambiguous rule presented for approval rather than silently inferred.

## H2 — Fatal effects and actual damage

For common-snapshot starting HP `H` and total *actual*, separately calculated, post-protection HP damage `D` across simultaneous attacks:

- No successful fatal effect: `HP_final = H - D`.
- One or more successful fatal effects: `HP_final = min(H, -10) - D`.

Multiple fatal outcomes **do not stack**. A fatal effect alone does not change HP already at or below −10, but any actual damage separately calculated for that attack or other simultaneous attacks subtracts **exactly once**. Do not invent damage for fatal results where the current rule calculates none. HP for Beings and protective equipment can fall below zero. Preserve saving throws, critical-hit bypass, and individual attack provenance.

Examples: `H=20`, two fatal effects alone → `−10`; `H=20`, fatal plus 6 actual damage → `−16`; `H=−12`, fatal alone → `−12`; `H=−12`, fatal plus 6 damage → `−18`.

## Other governing Class A and integration rules

- **F1:** Multiple valid defenses may target one strike; at least one success protects against the designated strike, without stacking; qualifying attempts retain practice outcomes. F2 prevents active reuse of the same Object for distinct simultaneous Actions.
- **R1–R5:** Shared batch-local candidate Reality; consistent statistical group and historical realization; observer-specific evidence and belief; reject incompatible objective facts without partial publication.
- **Q/B:** Only the adopted persistent fatigue reserves; existing Q/B freeze and physical-work proposals must not become premature mutations or double-charged workloads.
- Preserve the existing native Encounter and action calculations except where the new semantics explicitly supersede implementation behavior. **No production code changes are authorized by this decision record.**
