# Encounter Action Completeness — release gate

**Status:** Registered future milestone; **not** a new active Codex implementation assignment.
**Register ID:** `U-ACT-GATE-001` (verified unused in the live register and assigned on 2026-11-15).
**Priority:** After the active `U-OBS-001` program, ahead of `U-NET-001` (untimed two-human network Encounter).
**Authority:** The currently adopted Encounter rules, including revision 70 and genuinely adopted subsequent supplements. `TASKS.md` is the *single authoritative task-state register*. This document defines acceptance; it is not a second status ledger.

## Outcome

**All adopted Encounter Actions are complete**, not merely demonstrated in a bounded representative implementation. A fully complete Action has every applicable, adopted variant and outcome implemented in native Encounter resolution; can be selected by a player in the generated Arena wherever legitimately eligible; preserves observation/permission boundaries; composes correctly with other Actions and movement; and survives exact persistence/replay. The release gate is not achieved while any adopted executable Action variant is OPEN, PARTIAL, BLOCKED, or VERIFY.

`DONE (bounded)` on a prior assignment is evidence for the stated subset **only**, never a substitution for full Action completeness. The milestone is fulfilled against the *adopted rules as of the final audit*, not speculative later rules or unrealized general Universe features unrelated to an Action's legality and effects.

## Inventory and classification

1. Audit Appendix III (offense) and Appendix IV (defense) of the adopted Encounter rules, every additional named Action throughout the rulebook, and the authoritative Action catalog/configuration. Reconcile them against the current `U-ACT-*` inventory and actual native schedulers, validators, resolvers, and browser routes. Do not assume that a catalog label represents an executable Action or that a catalog count represents implementation coverage.
2. Preserve existing stable task IDs; allocate a new ID only for a genuinely distinct previously untracked Action or requirement, after checking collisions. Treat `Search`, `Spot`, and `Listen` individually. Distinguish `RunAction` from movement speed and `Draw` from `Ready`.
3. For *each* Action, enumerate **all adopted variants**, explicit prerequisites, timing, cost, range/reach/geometry, contest/defense, success, failure, interruption, duration/recovery, interactions, and special cases. Record source section/revision, implementation code and focused test evidence. Record any rules that remain ambiguous or mathematically unspecified; do not infer physics or adopt a new rule inside implementation.
4. Classify at **variant level**: `FULL` (all acceptance checks), `PARTIAL`, `OPEN`, `BLOCKED` (precise adopted-rule/data prerequisite), `VERIFY` (insufficient evidence), or `NOT AN INDEPENDENT ACTION` (e.g. an attack condition). If a named entry is not independently schedulable, document and test its actual rule integration rather than manufacturing a button. Aggregate an Action as `FULL` only when **every adopted variant is FULL or formally classified as non-executable with its rule integrated**.
5. Maintain one live, testable inventory in `TASKS.md`, or a separate machine-readable matrix linked from `TASKS.md` with `TASKS.md` remaining the only authority for state. Historical reports and archived assignments provide evidence, not competing registers.

## Per-Action completion tests (all required where applicable)

- **Authority and eligibility:** native prerequisites and forbiddances (knowledge, skills, equipment, hands, posture, geometry, orientation, environment, conditions, magic/force data) agree with adopted rules. Unknown necessary facts **refuse** without time, Action, Object, RNG, or knowledge mutation; do not silently convert unknown to eligible.
- **Time and concurrency:** movement-first; nominal due Actions resolve against the same post-movement/pre-action snapshot; deterministic shared effect publication; reservation and hand/resource conflicts, interruptions, simultaneous contests, Multi-action priority and repeated Actions obey adopted contracts.
- **Consequences:** success, failure, ties, critical/fatal cases, positional and custody effects, damage/protection, durability, fatigue/conditions and natural recovery where relevant update the real native state. Same native Being/Object identities remain stable; no visual-only or catalog-only implementation.
- **Perception and privacy:** each participant can select only through authorized current/remembered evidence as rules permit. Actions, target handles, apparent motion and consequences displayed in the Arena do not reveal another Being's hidden Reality; autonomous controllers use their own observation ledgers, never spectator/referee data.
- **Gameplay/UI:** every eligible human-declarable Action and variant is offered and executable from the shipped Arena interface (Player vs Arena); unavailable choices carry accurate reasons. Arena vs Arena continues working with its supported strategies; there is **no requirement** for AI strategies to select every possible Action.
- **Reproducibility/persistence:** success, refusal, interrupted/pending and completed states, receipts, RNG and observer knowledge survive strict fresh-process Save/Load, with deterministic continuation and failed-transaction rollback. Include cross-Action sequences and both Arena modes as relevant.
- **Evidence:** automated native + generated HTTP/session + shipped-JavaScript/UI test(s) for each variant, with real served-browser walkthroughs across representative combined scenarios. Record exact tests and limits; do not claim the full suite passed unless executed.

## Cross-cutting gate demonstrations

Before marking the *milestone* DONE, provide evidence for:

1. A source-linked Action/variant coverage matrix with zero unaccounted adopted executable variants, unresolved blockers, or unverified implementations. Every earlier `DONE (bounded)` label is reconciled to actual full coverage, not merely relabeled.
2. At least one reproducible playable **Player vs Arena** encounter and one **Arena vs Arena** encounter exercising multiple interacting Actions, actual native consequences, independent observer evidence, and legal control/strategy transitions.
3. Simultaneous incompatible and compatible Actions, concurrent holds/contested Objects, projectile interactions, and forced movement where adopted; rejection without mutation; later interruption; and actual outcomes after fresh-process checkpoint restoration.
4. A meaningful final integration validation, including the complete relevant Encounter/Arena regression suite, tests for persisted legacy saves where supported, documented failures, and an actual served-browser smoke. Run the broader repository suite when justified by the final milestone; if any mandated tests cannot run, the gate remains unverified, not DONE.
5. Updated `TASKS.md`, development docs, and an auditable engineering report listing every remaining **non-Action** general Universe limitation separately, so Action completeness does not falsely imply entire Universe completeness.

## Known gaps to reconcile, not a frozen authoritative status list

Based on earlier milestone reports (which may be superseded by code and current `TASKS.md`): Shoot arrow velocity/ammunition identity; Deflect whole-trajectory awareness and destination; general Throw weight/Strength brackets and miss interception; Pull quantitative force and displacement; remaining Bull Rush and occupied-space cases; special Break weapon and magical protection; Strike Object broader geometry/material cases; shield don/remove and exceptional Quick-draw; multi-grappler and post-co-holding custody cases; deliberate Search/Listen; and other config-defined Action variants. The audit must verify these claims rather than copying them as current facts.

## Scheduling and deferred multiplayer

- Keep `U-OBS-001` as the sole ACTIVE development program until accepted. Register `U-ACT-GATE-001` as a **future milestone**, not a parallel active implementation effort. Component assignments can progressively close gaps without claiming full gate completion.
- `U-CAP-009` is already assigned to global simulation time/events; do not reuse it for this gate or for observation.
- **`U-NET-001` remains DEFERRED until this gate passes.** Its proposed third Arena mode is Player vs Player, with *no real-world deadline*: each person explicitly indicates readiness, and the server advances the shared Encounter only when both are ready. Existing simultaneous chronology and participant-specific perception remain authoritative.
- Any rule ambiguity needing the user's decision should be surfaced as a specific question while independently implementable Action work continues. A deliberately unresolved adopted Action variant blocks the full gate rather than being treated as `FULL`.

## Register integration

The canonical gate is maintained at `docs/process/ENCOUNTER-ACTION-COMPLETENESS-GATE.md` and linked from `TASKS.md` as the future `U-ACT-GATE-001` milestone. `U-NET-001` is deferred until that milestone is accepted. `U-OBS-001` remains the sole ACTIVE implementation program. The gate identifier was checked against the live repository register before assignment; preserve stable IDs and all implementation evidence. Do not stage unrelated changes or push without authorization.
