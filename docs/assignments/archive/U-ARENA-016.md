# U-ARENA-016 — Implement the adopted offensive Combat Actions

**Repository:** Universe (Codex-owned)<br>
**Type:** Consolidated, outcome-oriented native Encounter and Arena implementation<br>
**Install at:** `docs/assignments/U-ARENA-016.md`<br>
**Report:** `docs/reports/U-ARENA-016-report.md`

## Desired outcome

Implement **every offensive Combat Action in Appendix III of the authoritative adopted Encounter rules that can be implemented faithfully**, including the native prerequisites and shared mechanisms needed to make those Actions work. Deliver a playable browser path wherever the generated two-Being Arena can lawfully exercise an Action, native testable paths for Actions requiring other configurations, deterministic Save/Load of their active and completed states, and an exact implementation/disposition matrix for all 27 entries.

**This is one integrated assignment, not 27 micro-assignments.** Investigate code and dependencies, build the missing machinery, make a small number of coherent green commits at natural functional boundaries, and return one consolidated report. Do not stop simply because the current engine does not yet have a class, route, data structure, or test fixture. Those are engineering tasks. Stop an individual Action only where a genuine adopted-rules decision, required unmodeled physical quantity, or mutually incompatible adopted contracts prevent a faithful implementation; continue implementing other Actions.

Keep the focus on producing working simulation behavior, not drafting an architecture review or adding inert browser buttons. No invented rules or second combat simulator.

## Authoritative baseline

- Read `docs/handoffs/universe-8-to-9.md`, `docs/reports/U-ARENA-009-report.md` through `U-ARENA-015-report.md`, the **currently authoritative** Encounter rule-package README and adopted rule text (including revision 61 and applicable later spatial supplements), and the source/tests themselves. Follow actual rule precedence; older tactical-duel prototypes are not normative.
- U-ARENA-009 to -013 provide Generator-native equipment, observer-grounded targeting, one-yard regular-hex melee reach against Beings, native strikes/damage, independent player/opponent Actions, pursuit, and transactional simultaneous movement. U-ARENA-014/-015 add attack-specific, prepared and retained defenses. Reuse these paths and test their regressions.
- U-ARENA-015 found Block, Dodge, Parry, and Yield implemented; **Deflect** requires authoritative projectile target/impact/Missing and continuous trajectory observation; **Disengage** requires open/unoccupied traversed-hex and simultaneous route occupancy contracts. Those dependencies may affect offensive Actions too. Do not silently declare unknown geometry or ground Objects transparent.
- Generated source NPC records, Generator API equipment specifications, and initial provenance remain immutable. Live native Being/Object, Action/Choice, observer evidence, and committed Encounter state are authoritative. Load never regenerates a Being, Object, kit or Action.
- Preserve one-second chronological boundaries: movement phase first; every non-movement Action due in a second resolves against the **same post-movement/pre-Action snapshot**; consequences commit together. Defender decisions/limited resource allocations must precede knowledge of attack results. Admission failures must be atomic and consume no RNG.
- Preserve continuous metric Cartesian movement, player-facing yards, exact one-yard regular-hex conventions, twelve facings, impact-time reach, and explicit observation/awareness. No generic 3-D Being model is required for current hex-melee targetability, but physical geometry remains important for line-of-sight, cover, collision, thrown Objects and missiles.

## Coverage: all 27 Appendix III entries

Audit and disposition **each** of the following, using actual native source and authoritative rule wording; do not assume the preliminary categories below are implementation verdicts.

1. Break hold
2. Break weapon
3. Bull rush
4. Pull
5. Charge
6. Coup de grace
7. Delay
8. Disarm
9. End run
10. Feint
11. Grab (and continuing physical Hold)
12. Grapple (and its specified control/escape operations)
13. Multiple actions
14. Overrun
15. Ready
16. Shield bash
17. Shoot
18. Strike (Swing and Thrust)
19. Strike an object
20. Stun
21. Subdue
22. Throw
23. Touch
24. Trip
25. Two-handed strike
26. Undefended attack
27. Wrest

Potential shared work areas (**implementation grouping, not externally imposed stages**):

- **Core Action semantics:** Touch, Feint, Delay, conditional Ready, Coup de grace, the undefended condition, and completed Swing/Thrust variants. Respect the full existing attack/defense, timing, prerequisite and strategy-allocation rules.
- **Equipment and consequences:** Strike an object, Break weapon, Disarm, Shield bash, Two-handed strike, Stun and Subdue; represent actual objects, held/readied hands, hardness/HP, incapacity, equipment release, separate damage/conditions and native event receipts. Do not infer an unsupported weapon hand count or equipment effect.
- **Physical contact and control:** Touch prerequisites, individual Grab/Hold identity and maintenance, Break hold, Grapple/Escape/control positions, Wrest, and their concurrency. A Grab/Hold is **not** a Grapple; never merge distinct checks or let breaking a grip automatically terminate an already established Grapple. Respect damage-induced release under revision 61, multiple holders, and prior/same-second outcomes.
- **Position and concurrency:** Bull rush, Overrun, End run, Trip, Charge, Multiple actions, and their scheduling/forced movement/occupancy/simultaneity. Implement genuine movement-phase state transitions, contested occupancy and resource restrictions; never teleport, convert rolls into unauthorized force magnitudes, or introduce ad hoc sequential same-boundary effects.
- **Projectile and force dependencies:** Inspect actual native `ThrowAction`, trajectory and target contracts, existing archery/catapult and interception primitives. Implement Shoots/Throws **only to the extent their full adopted target, path, hit/miss, interception and outcome semantics are supported or can be built from authoritative rules**. In particular, the adopted **Pull** rules explicitly leave numerical Strength/physical-characteristics → newtons → displacement unresolved. Do not derive force from the winning roll or invent a physical model. Record an exact blocker and a bounded native partial proof if this is unavoidable.

These groupings are guidance for efficient engineering. Refactor shared primitives where necessary; do not implement twenty isolated versions of reach checks, custody transfers, or timing. No broad framework rewrite for its own sake.

## What counts as implemented

For each Action classified **implemented**:

1. Native declaration and validation through the ordinary scheduling/Choice mechanism, with a source-grounded Actor, required target/Object, equipment, resources, timing and prerequisites. Reject invalid choices without any mutation, orphaned identities or RNG movement.
2. Native execution through the common movement/action transaction and existing attack/defense/damage and observer model. State consequences are authoritative Being/Object/Action/Choice/effect/history changes, not presentation metadata or a parallel Arena result.
3. Correct lifecycle for in-progress, waiting, completed, aborted and other action-specific states; legal interactions with simultaneous attacks, defenses, movement, cancellation and multiple actions.
4. Deterministic focused positive and negative tests, including the relevant rule edge cases, cross-process Save/Load at meaningful pending and completed checkpoints, and observer-specific non-disclosure of private facts. Loaded state never invokes `npcgen`.
5. Player-facing invocation and observer-authorized feedback **where the current generated Arena can represent the necessary participants and prerequisites**. Otherwise a reproducible native/HTTP demo and an explicit honest UI availability reason; do not add controls whose native contract is not ready.

A partial mechanic, a test-only injection of impossible state, or a browser control without full native effects **is not** a completed Action. For an Action already implemented, audit its fidelity and strengthen tests; do not duplicate it.

## Engineering workflow and decisions

- First establish a concise source-grounded inventory of current native implementations, expected cross-dependencies and likely true rules blockers. **Do not stop at the inventory. Proceed directly with engineering.** Prioritize shared foundations that unlock several Actions; freely adjust sequencing based on actual code dependencies.
- Implement as much of the sufficiently specified rules as possible in this assignment. Make coherent, independently verified commits rather than a giant dirty checkout; do not request routine approval between related actions. Do not set an arbitrary low action count merely to avoid broader integration work.
- If a particular rule is genuinely underspecified, isolate and skip only the blocked portion, retain what works, name the exact missing quantity/semantic decision and cite the rule; move on to other Actions. A missing native implementation, absence of a browser control, or nontrivial tests are **not** rule blockers.
- Never silently simplify an adopted Action to a misleading one-on-one or no-movement proxy. A faithfully bounded subset may be implemented and labeled **partial**, with coverage and limitations explicit.
- Preserve current opposition strategies, source-equipment behavior, browser controls, native Pick up/Draw, blocker uncertainty for unmodeled ground Objects, the four working defenses, and strict existing checkpoint/admission validation. If a new native event/effect type is necessary, add **explicit** allowlisted versioned checkpoint handling; do not loosen global restore rules.
- Avoid new rules regarding physical collisions, geometry, force, projectile interception, class bonuses, shield effects, hand counts or conditional action effects that are not established by the adopted documents. Ask only when an essential **rules** choice truly cannot be avoided for that Action; otherwise record the blocker and continue the other work.
- Preserve unrelated tracked deletions/untracked user files; stage only intended paths. Do not modify the sibling `npc-generator`. No `git push`, history rewrite, force push or clean; the historical-publication concern remains separate.

## Required demonstrations and checks

Deliver at least one **newly implemented offensive Action** through the ordinary generated-Arena browser controls and native completion, using legitimate generated Beings and an appropriate supported empty-ground configuration. Demonstrate representative different families (e.g. contact/control, equipment damage/custody, and forced movement or special attack) as their native prerequisites become available; for multi-Being cases use a real native Encounter fixture rather than fabricating post-creation state. Demonstrate refusal/rollback and representative simultaneous outcomes. Do not force favorable attack rolls to disguise outcomes.

Use focused new/affected tests and minimal adjacent regressions per coherent commit; preserve the already verified native attack/defense/persistence coverage. For shared transaction, scheduling, or checkpoint primitives, run appropriately broader regression batches. Run the full expensive suite **once at a meaningful final integration checkpoint if warranted and feasible**, not on every incremental commit; state plainly what was and was not run. Run `py_compile`, `git diff --check`, and a real-browser smoke when the local loopback environment permits it. Give exact commands, counts, timings and failures/fixes.

## Report: one consolidated deliverable

Write `docs/reports/U-ARENA-016-report.md` with:

1. A brief **Where we stand** summary and a run-through of actually executable new Action(s).
2. A compact **27-row matrix**: Action; native status (**existing/implemented this assignment/partial/blocked**); Arena availability; evidence/test; and **specific** remaining dependency when not fully implemented. Distinguish a rule gap from an engineering backlog.
3. The important shared native architecture/transaction changes, rule-faithfulness decisions, edge cases, and representative browser/native test scenarios.
4. Save/Load and observation-isolation evidence; exact tested commands/pass counts/timings; individual commit hashes; unchanged repositories and Git status.
5. A **prioritized residual backlog** grouped by truly shared prerequisites, not a separate assignment suggestion for every Action. Keep it brief enough that our next decision can focus on material gaps.

**Success:** a substantial and correctly integrated expansion of the native offensive combat system, plus a trustworthy inventory of the remaining Actions and precisely why they are not yet complete—not an audit-only report, an overpromising UI, or invented rules to make boxes appear green.
