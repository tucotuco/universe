# U-SHIELD-001 — Complete adopted shield protection and physical coverage

**Repository:** `~/Projects/universe` only
**Install:** `docs/assignments/U-SHIELD-001.md`
**Report:** `docs/reports/U-SHIELD-001-report.md`
**Invocation:** `Execute docs/assignments/U-SHIELD-001.md.`
**Status:** Assigned, not yet implemented or accepted. Begin only after confirming the preceding persistence program's accepted disposition and the repository state.
**Authorization:** Independently complete the coherent implementation with focused verification and small, audited **local** Git commits. No push, history rewrite, destructive cleanup or modifications to other projects.

## Outcome — one finished capability, not another bounded experiment

Implement **all adopted, currently executable shield protection and shield equipment/defense interactions** in the native Encounter and supported Arena application, including the adopted 2026-11-15 multiple-shield rule, and establish the reusable physical extent/orientation/cover foundation **to the extent required by the adopted tower-shield and related shield rules**. Demonstrate lawful interactions through real native one-second common-snapshot resolution, correct observer privacy, native Save/Load and the shipped application route.

Do not declare this assignment finished because one two-shield example passes. Finish the relevant adopted variants and observable outcomes; retain explicit `PARTIAL`, `BLOCKED` or `VERIFY` only where an actual authoritative rule/data/geometry prerequisite is missing, with specific evidence and the smallest necessary decision request. Do not invent new combat mechanics to make a test pass. This program is about shield completion, not all Encounter Actions, ranged combat or a universal physics engine.

## A. Begin with accepted persistence closeout and repository safeguards

1. Read `TASKS.md`, `docs/encounters/README.md`, its currently adopted supplements, `docs/encounters/action-implementation-coverage.md`, `docs/process/DEVELOPMENT-PROCESS.md`, `docs/process/ENCOUNTER-ACTION-COMPLETENESS-GATE.md`, `docs/reports/archive/U-PER-SCALE-001-report.md`, and the live code. Verify this proposed ID is unused. The preceding U-PER-SCALE-001 final report is **accepted by ChatGPT for the revised persistence criteria**; its reported current native Save/Load and HTTP regression results are sufficient for milestone closeout, while manual Chrome Save/Open remains an explicitly unverified UI smoke. Update the sole authoritative `TASKS.md` accordingly and archive the consumed assignment/report at the beginning of this assignment using the established process. Preserve the detailed persistence design/findings and compatibility tests.
2. Keep the older Arena `/10`–`/12` readers and the delivered native format supported. Do not expand transient native-schema migrations, build an autosave/journal, or redesign the newly accepted persistence architecture. Reuse it for shield continuation and rollback tests.
3. Before any edits inspect Git status, the user's pre-staged archive operations and untracked data; preserve those exact operations and unrelated files. Small independently green scoped commits are allowed. No push, destructive reset or automatic cleanup.
4. Maintain `docs/reports/ACTIVE-PROGRESS.md` as a short **derived view** of this assignment's verified gates, remaining gates, current work and blockers. It does not supersede `TASKS.md` or become another task register. Update after meaningful milestones without interrupting work or requesting approval; avoid a chronological novel.

## B. Adopted rule and provenance audit

The live adopted Encounter rules are authoritative, including the post-r70 dated multi-shield supplement (commonly `docs/encounters/encounters-adopted-supplement-2026-11-15.md`) and their links from the Encounter README. Verify the exact operative text in the checkout rather than assuming a historical revision incorporated later decisions. Source-link each shield variant, restriction, expected consequence and necessary native/UI test in the existing Action coverage matrix.

Mandatory adopted multiple-shield semantics:

- A legally borne shield has its **own incoming-attack capacity equal to shield size**. One attack can be assigned to **at most one** shield; interception chances and stopped damage never stack on the same attack.
- Defender allocation occurs **before outcomes**, requires that selected incoming Actions were perceptible in the **preceding round**, and is **not a timed Action** and consumes **no Action-capacity resource**. An Action first revealed during the resolving round cannot be retrospectively assigned.
- Each shield takes its **own** durability loss under its persistent Object ID; all attacks completing in one boundary use the common post-movement/pre-Action snapshot; consequences commit simultaneously. Shield destruction within that batch does not retroactively revoke already eligible protection; future boundaries use the damaged state.
- Preserve every existing hand, buckler, tower-shield, equipment, posture, Active Block, awareness, physical legality and tower-maneuver prohibition. This rule does **not** make wearing two shields automatically legal.
- No invented priority between equally eligible shields, no unrequested automatic allocation, no fabricated observation or cover geometry. If an eligible case is underdetermined by rules, fail closed without partial state/RNG mutation and record the exact missing decision.

Include the already implemented **single-shield** passive protection as a regression baseline, not a separate new invention.

## C. Complete the native resolution and spatial contracts

1. Implement and validate legal shield equipment changes, passive interception/allocation, Active Block and their interaction, buckler differences, tower-shield coverage/limitations, and lawful multiple-shield cases using current native Actions and rules. Distinguish eligibility from actual physical availability. Preserve shield ownership, identity, readiness, held/donned state, reach and hands.
2. Support the current continuous 3-D authoritative spatial model for shield-related extent, orientation, obstruction/cover and protection decisions where adopted rules require it. Reuse existing geometry/spatial representation. Do not replace authoritative continuous coordinates with hex-cell guesses or implement unrelated general ballistics. Where precise cover/occlusion cannot be determined from represented geometry, refuse or record uncertainty as the adopted rules require; never fabricate a hit or cover decision.
3. Resolve simultaneous and conflicting cases correctly: multiple incoming attacks, multiple shields, one shield's capacity exhaustion, passive vs Active Block, destroyed/damaged shields, overlapping Actions, movement-first and defensive declarations. Check known-vs-unknown attacks under independent observer views. Atomic effects and RNG must roll back on publication failure.
4. Reconcile any existing old shield tests that contradict the adopted rules by reproducing against current baseline, correcting stale expectations only with explicit evidence. Never relax the rule to satisfy a test.

## D. Player-facing use and persistence

1. A player must be able to declare all legitimately available shield allocations and active shield Actions through the supported Arena controls, with accurate reasons when unavailable. Autonomous Arena choices may stay limited to their supported strategies, without reading omniscient state to make allocations.
2. Private observational state must remain private. A defender may not allocate against an Action it could not have known in the preceding round; spectator/referee facts must not leak to the controller. Include a negative privacy case and correct prior-round positive case.
3. Save before and after shield changes, during pending allocations/Active Block as supported, and after one simultaneous multi-attack boundary. Strict native fresh-process Load must preserve shield IDs, allocations, durability, pending Choices, observers, history and RNG and then continue with the same native outcome. Test legacy production reader compatibility in an affected focused cohort; do not reopen the persistence architecture.
4. Demonstrate the real application's ordinary HTTP/session Save/Load path. Attempt a shipped browser UI walkthrough where tooling permits; report precisely if local browser extension/file-picker limits prevent a genuine click/Open verification, without claiming success or inventing a persistence failure. Offer simple manual steps for independent confirmation in the report.

## E. Acceptance evidence and conclusion

- Produce a concise **variant-level shield acceptance matrix**, citing operative rule sections, native implementation, tested result, UI visibility, privacy, persistence, and any genuine remaining blockers. Distinguish single shield, multiple shield, buckler, tower cover, Active Block and competing/simultaneous cases.
- Run focused rule, integration, observer/privacy, geometry and native persistence tests, plus selected shared-primitive regressions. Run a broader suite when a genuinely high-risk shared change warrants it and report what actually ran; do not repeatedly invoke the expensive full persistence suite for routine variants. Include all relevant refusal/rollback and identity checks.
- Provide reproducible headless and application demonstrations with exact steps and observed outcomes, plus source-linked evidence. Mark a test unverified if tooling prevented it.
- Reconcile `TASKS.md` without converting it into a progress diary, update shield coverage, the derived `ACTIVE-PROGRESS.md`, and write `docs/reports/U-SHIELD-001-report.md` using **Problems first; accomplishments second**, acceptance matrix and verification facts. Retain the broader U-ACT-GATE-001 as FUTURE until separately achieved and ranged U-ACT-FULL-003 as DEFERRED pending shield/geometry readiness.
- Treat success as **the finished adopted shield capability**, not a finite number of exploratory experiments. Work autonomously through meaningful internally verified commits until accepted criteria are achieved. Report early only for a genuine missing authoritative decision, external blocker or irreconcilable dependency. No pushes.

## Report closeout template

1. Problems first: verified defects, incomplete/blocked adopted variants, actual browser limitations, uncertainties.
2. Accomplished: implemented rule variants, consequences, geometry behavior, UI, privacy and persistence.
3. Acceptance matrix: exact criteria and pass/partial/refusal with source and tests.
4. Tests: exact command, count, duration, baseline comparison and any failures.
5. Git: scoped commits, preserved staged/untracked paths, no push.
6. Where we stand: full shield capability versus remaining Universe Action completeness and ranged/geometry work.
