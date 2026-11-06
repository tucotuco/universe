# Universe 4 — Authoritative Encounter Decision Record

**Date:** 2026-10-27\
**Status:** Adopted simulation and engineering contracts; implementation requires a separately scoped assignment\
**Purpose:** One noncontradictory reference for the existing native Universe Encounter engine.

## Authority and supersession

This record consolidates the user's adopted Universe 4 Class A decisions (T1–T5, H1–H5, F1–F2, R1–R5) and engineering decisions D1–D7. **Later user decisions supersede earlier proposals** wherever they conflict.

In particular, the original Class A record's statement that T5 was deferred has been superseded; the original H5 requirement that individual Action records carry target HP-before and HP-after has been **rejected and superseded by target-owned state**; the original permissive F2 same-weapon rule has been rejected; existing zero-clamped HP and sequential outcomes are not authoritative rules. Legacy result APIs need not be preserved, although versioned saves/replays require explicit compatibility handling.

The Codex characterization report `encounter-timeline-choice-damage-characterization.md` establishes an **822-test historical baseline**, including 42 added tests explicitly labeled as characterizing legacy behavior, **not** adopted target semantics. Its reported state is HEAD `8a00e884a62e37160a8eeb69f0e6e67e94ab16b4` plus the then-existing uncommitted work. Reconfirm the current working tree and tests before editing.

## A. Simulation time, movement and scheduling: T1–T5

1. Continuous physical calculations (kinematics, trajectories, fatigue work, etc.) may use fractional seconds. **Non-movement Action resolution occurs only at integer-second boundaries.** Nominal completion in `(n-1,n]` belongs to the batch at `n`, including exact `n`; preserve the original nominal time for relevant provenance.
2. All non-movement Actions in one batch evaluate the **same post-movement, pre-action world snapshot** and commit consequences together. No Action observes another simultaneous Action's uncommitted state changes.
3. Long steps process each one-second boundary in order, moving to that boundary with the existing supported physical model; earlier committed seconds are visible to later seconds. Do not calculate all due Actions from the long step's final position.
4. An Action **may be scheduled/started at time zero**, but must have a **finalized scheduled duration of at least one second**. Actions cannot resolve at time zero. A legitimate early interruption can terminate actual activity earlier; it does not retroactively invalidate the initial schedule.
5. A designated boundary must never be missed, duplicated or processed late. Scheduling an Action into an active or previously committed boundary is forbidden. Such conditions indicate an invariant violation, not a recoverable gameplay outcome. Finalize and validate all scheduling-dependent times, including melee-defense timing, before publication. Ordinary non-Action Events (e.g., the origin Event) do not acquire these Action-only requirements.

## B. Damage and affected-Object state: H1–H5, corrected D7.1

1. Actual HP damage is additive **without a zero floor**, including when the starting HP are negative. A Being at 12 HP taking 8 and 7 actual damage finishes at -3 HP; armor at 6 HP taking 4 and 4 finishes at -2 HP.
2. Each simultaneous attack computes its own post-protection effects from the **common equipment snapshot**. Aggregate the distinct actual damage contributions to each affected Being, shield, armor, or other Object, without new implicit breakage/degradation/drop rules.
3. Multiple successful fatal effects do **not** stack. Let `H` be starting HP and `D` the sum of separately calculated *actual* HP damage contributions, counted once. Without any successful fatal effect: `HP_final = H - D`. With one or more: `HP_final = min(H, -10) - D`. A fatal result that does not calculate ordinary damage invents no extra damage. Preserve established attack rolls, defender saves, critical bypass and other calculations unless explicitly changed.
4. **Action versus Target ownership:** An Action records what it did and to which Target(s), including action-specific resolution facts as needed; it does **not** own or duplicate any Target's authoritative HP-before/HP-after or other resulting state. A Target (Being/Object) owns its resulting state and any target-associated state-change/provenance information needed to interrogate the impact, with causal references to source Actions as appropriate. Design the necessary target-side query/history representation consistent with resolution on demand; do not silently infer individual damage by subtracting shared batch-final HP from its starting HP in the Action.
5. The prior H5 proposal requiring per-Action `HP-before`/`HP-after` fields is **superseded** by item 4. The tactical duel's previous own-damage derivation from Action HP differences must be replaced when integrating the new result model.

## C. Defenses and exclusive resources: F1–F2, D1

1. Multiple valid designated defenses can be evaluated against one strike using the common snapshot. One success suffices; successes do not stack; each qualifying attempt retains its legitimate practice/outcome. Preserve full association and provenance between the attacking and defensive Actions. **Old single-`defended_by` result interfaces may be replaced.**
2. The same Object cannot be **actively used** by overlapping scheduled Actions. The conflict is rejected during scheduling, not arbitrated at impact. Every Action declares the Objects it actively uses; reservations span from each Action's start until its designated resolution boundary, modeled as `[start,boundary)` with handoff at the boundary **after settlement**. Even Actions resolving in different seconds conflict if their active-use intervals overlap. Do not invent narrower implicit active subwindows.
3. Merely being the actor or target of an Action **does not automatically reserve an entire Being**. Preserve other established Action concurrency constraints (notably permitted movement while attacking). Body parts or the whole Being may be explicit resources only when their actual rules require that; do not infer them by inheritance from Object.
4. Passive protection or interception, receiving damage, being observed, and mere possession are not additional active Actions or exclusive resource use. Several simultaneous attacks may affect the same shield or armor Object.

## D. Shared Reality, Observation, and Belief: R1–R5

1. Simultaneous inquiries requiring an unresolved objective fact use **one shared batch-local candidate realization**, committed only with that batch.
2. Observers of a statistical group share one objective candidate composition, though observations/estimates can vary; do not realize individual Beings unless demanded by resolution.
3. Inquiries about the same unresolved historical episode share a candidate episode and supporting facts, respecting previously established constraints and validating the combined proposal.
4. Shared objective Reality does not imply identical observer-specific Observation or Belief; use each observer's pre-action capabilities.
5. Irreconcilably contradictory candidate **objective facts** prevent publication of the entire batch. Never overwrite established truth, choose an arbitrary winner or reroll to hide contradiction. Different perceptions/beliefs are not objective contradictions.

## E. Engineering and lifecycle decisions: D2–D7

### D2 — Safe scheduling preparation and extension contract

- Preparing a schedulable Action is pure/read-only: finalize timing, participants, active Objects, and prerequisites without authoritative mutation, RNG consumption or event registration.
- Validate the **fully prepared** candidate before any authoritative publication, including finalized defense timing.
- Custom Actions and Encounter-resolved Events must implement the approved safe scheduling/evaluation contracts. Unsupported opaque mutating extensions fail **before** unsafe callbacks are invoked. Ordinary non-Action Universe Events retain their separate semantics.

### D3 — Whole-choice lifecycle

- Proposal and validation form an editable loop. Invalid complete sets stay drafts with diagnostics; never accept a valid subset or leak partial registration.
- Acceptance of a complete valid choice establishes reversible resource reservations, with revalidation against competing accepted choices, but does not execute Actions, consume RNG, award practice, or create completion history.
- Before the earliest member Action starts, a choice can be wholly undone or atomically replaced; invalid replacement leaves the original intact. Undo leaves no cancellation or execution history.
- Immediately before the earliest Action starts, publish/register the **entire** choice atomically before any member begins. Once any member begins, planning undo is unavailable; later cancellation/interruption follows Action rules and preserves appropriate provenance.

### D4 — Legitimate Action outcomes versus exceptional integrity faults

- Every valid scheduled Action produces a legitimate simulation outcome: achieved, missed, partial, inaccessible target, unavailable instrument, interrupted or terminated early, etc. These are **not** transaction failures.
- The entire one-second interval, including provisional movement, physical progression, Action effects, reality/belief changes, practice and lifecycle state, is atomic; earlier committed seconds remain committed.
- Only exceptional engine faults, irreconcilable objective state, or invalid internals prevent commit. Roll the current second back to its preceding committed checkpoint, stop with diagnostics, and allow deterministic retry **after correction**, never an uncontrolled automatic loop.

### D5 — Stochastic reproducibility and RNG

- Same authoritative starting state, compatible version, accepted Action choices/timing and RNG state must reproduce the same results.
- Allocate simultaneous draws in a stable documented order, preserving existing priority/accepted scheduling order when possible. Draw order does not establish world-state commit precedence.
- RNG is provisional during a batch, advances at successful commitment, and is restored on exceptional abort. Ordinary unfavorable gameplay results commit their draws.
- Shared candidate objective realization is deterministic; observer-specific randomness may vary, but candidate truth is not resampled to hide contradictions. Retain existing appropriate keyed/local RNG approaches.
- Saves/replays must be version-aware and explicitly identify incompatibility rather than silently reinterpret old results.

### D6 — Authoritative effects and notifications

- Authoritative Action/lifecycle effects, including observation, belief, testimony, histories, skill practice, completion and cancellation, are staged and committed in their applicable atomic transactions.
- Completion hooks/extensions cannot bypass transaction staging with direct authoritative mutations.
- Non-authoritative UI/external notifications occur **after** commitment; optional reliable delivery uses stable intents and idempotent retries when supported. A notification failure never rolls back a valid simulation or reruns its Actions.

### D7 — Results, persistence and compatibility

- **D7.1:** Action describes what it did and to which Target(s). The Target owns resulting state and target-associated queries/history/provenance. No duplicated Target HP-before/HP-after on Actions.
- **D7.2:** Preserve multiple defense outcomes and their associations, but **legacy result interfaces may be replaced**; no structural backward-compatibility obligation for internal APIs.
- **D7.3:** Save/restore a coherent authoritative checkpoint sufficient to continue reproducibly, including pertinent Beings/Objects, Q/B and physiology references, objective/observer states, accepted choices/reservations, pending Actions, boundary cursor and RNG. Editable drafts need not be authoritative saves. Preserve stable identity/references and reject inconsistent restores.
- **D7.4:** Version saves and replays by rules/data/engine compatibility. Support migrations where meaning can be faithfully preserved; otherwise reject explicitly. Existing UI and replay consumers should migrate to the native engine's revised interfaces rather than creating a second engine.
- **D7.5:** Authoritative saves must reflect successfully committed checkpoints, never partial transaction state. During an in-progress second, save the previous committed checkpoint or complete that transaction first. Exceptional failure retains the previous checkpoint for diagnosis/recovery.

## Integration and implementation limits

- Preserve the existing native Encounter resolver and rule calculations wherever they do not contradict adopted semantics; use tested, bounded changes and do not create a parallel combat simulator.
- Persistent fatigue reserves are **Q and B only**; PCFS is fixed at **5**, with one universal physical-check table. Physiology governs depletion/recovery/output. Current R4 work/physiology proposals are present but **not yet live Q/B settlement**. Do not activate R4 fatigue in the transaction/scheduling refactor before a separately authorized increment, and do not double-count overlapping work.
- All already-held references to authoritative Beings/Objects/ledgers must remain meaningful after commit; target-side state and history must be designed accordingly.
- Existing legacy characterization tests may intentionally conflict with the adopted rules. Amend them deliberately with documented reasons when the corresponding implementation increment supersedes legacy behavior; never force the suite green by silently retaining defects.

## Remaining distinctions

No unresolved **simulation-rule** decision blocks **Increment 1 (pure scheduling preparation and finalized duration validation)**. Detailed data structures and API names, exception taxonomy, target-side state/provenance representation, historical save migrations, and the future transaction coordinator remain engineering design/implementation tasks; they do not authorize expanding Increment 1.

## Source and historical references

- `encounter-timeline-choice-damage-characterization.md` — Codex Assignment 03, full baseline 822 passing after 42 legacy characterization additions.
- `encounter-snapshot-transaction-dependency-analysis.md` and `encounter-resolve-actions-architectural-audit.md` — native mutation and call-path analyses.
- `universe4-class-a-decisions-2026-10-27.md` and `universe4-class-a-addendum-t5-f2-h2-v2-2026-10-27.md` — earlier decisions; **this record supersedes contradictory passages**.
