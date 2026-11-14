# U-CAP-006 — Playable tactical weapon control and deception

**Repository:** active `~/Projects/universe` only
**Install at:** `docs/assignments/U-CAP-006.md`
**Report at:** `docs/reports/U-CAP-006-report.md`
**Invocation:** `Execute docs/assignments/U-CAP-006.md.`
**Authorization:** routine in-scope implementation, focused tests, scenario fixtures, documentation and small audited local Git commits. No push, force push, history rewrite, destructive cleanup, change to sibling repositories/backups, ignored `legacy/`, `.venv`, or user local saved-world data.

## Outcome: a genuine playable tactical contest over equipment

Complete the independently supported **Disarm, Break weapon, Feint, Grab-held-Object and Wrest** variants as one coherent native Encounter / generated Arena capability. A player must be able to exploit a successful Feint, contest an opponent's actual held weapon, change its custody or durability through the rules, and act on the resulting world state. Use existing native Being/Object IDs, Choice transactions, observed target handles, movement/hex clearance, hand claims, Draw/Ready, damage/durability, one-second common-snapshot publication, RNG and strict Save/Load. Do not simulate a Disarm merely by editing an inventory or a Feint merely by presenting a button.

**Minimum end-to-end demonstrations** (real native Action resolution through generated Arena HTTP/session and shipped JS controls, with test-authored legitimate scenario state as needed):

1. A valid Feint resolves, confers its single +2 against the same target on the next chosen follow-up attack, is consumed at resolution, and is forfeited when a different Action/target is chosen. Include an unarmed variant where prerequisite facts exist.
2. A legal armed Disarm or unarmed Disarm changes custody of the *same native weapon Object* (ground location or unarmed taker as the adopted margin permits). The disarmed defender cannot continue to use a no-longer-held weapon; the victor must still use normal access/pickup/Draw/Ready rules rather than obtaining free readiness.
3. A legal Break weapon resolves against a represented weapon actually being used and produces its genuine hardness/HP outcome, with earlier-second interruption and same-second nonretroactivity; no synthetic weapon or timing precedence.
4. A legitimate Grab of an opponent-held Object followed by one-second Wrest transfers custody following the opposed Strength contest and preserves the Object identity; no automatic attack/readying benefit. Cover the established same-second multiple-success rule without inventing later shared-holder contest physics.
5. Demonstrate pending, contested, resolved and failed/aborted states across fresh-process Save/Load, including the affected Object identity, ownership/hand claims, weapon usability, Feint benefit, receipts, awareness and RNG continuation.

Do **not** stop after implementing one Action or after a small passing fixture: complete the viable combined scenario and acceptance criteria below. If a specific branch needs facts not present in authored sources, fail closed only for that branch and explicitly demonstrate independently feasible alternatives. No new rule decision is assumed necessary; ask only for a genuinely irreducible choice after checking all controlling sources.

## Initial checkout and closeout reconciliation

- Read the **current** `TASKS.md`, `docs/process/DEVELOPMENT-PROCESS.md`, adopted Encounter README + newest effective supplement (revision 69 and later, if any), and archived U-CAP-002 through U-CAP-004 reports with `docs/reports/U-CAP-005-report.md`. Confirm the actual repository branch/HEAD/index and compare against the report before modifying anything.
- **ChatGPT has accepted U-CAP-005 as DONE (bounded) and consumed its report.** Update `TASKS.md` accordingly, preserving U-ACT-020/021 as bounded DONE, and `git mv` the U-CAP-005 assignment and report to their respective `archive/` directories. Repair links and maintained references. Make the U-CAP-006 program ACTIVE and create this report in the active directory. Do not archive U-CAP-006 until ChatGPT explicitly accepts it.
- **Special index caution:** prior U-CAP-005 closeout reported user-staged historical U-CAP-002/U-CAP-003 *deletions* and a U-THROW-001 patch archival rename. Inspect `git status --short`, `git diff --cached --name-status`, both current and archived destinations, and `git ls-files` before staging. Do not reinterpret, remove, accidentally include, or overwrite those changes. Use exact-path staging and scoped `git commit --only` where appropriate. If archival paths conflict, record the exact conflict and preserve data rather than improvising `git reset`, `git clean`, or broad staging.
- The previously confirmed **pre-existing** `src/location.py:57` indentation error and the remaining Shoot/Deflect/broad Throw and force-calibration gaps are not silently closed by this assignment. They remain tracked; do not redesign unrelated modules merely to make a broad compilation command pass.

## A. Disarm and custody

- Implement the adopted armed route (advanced skill with attacking weapon) and unarmed route (Unarmed combat skill) through native Action eligibility, actual held defender weapon, opposed attack rolls, defender's defense-level-plus-5 counterattack (except the adopted Grapple case), tie/failure, timing, reach/facing, hand/weapon constraints, and special weapons with explicitly modeled modifiers.
- Respect locked-gauntlet and gauntlet immunity where authentically represented. For a successful disarm, model legal landing distances at one hex per full three points of margin with the specified destination and spatial clearance. Do not make an occupied/unknown landing location legal or teleport the weapon, except for the adopted revision-70 case: at a zero-hex limit only, the weapon may share the defender's represented hex when the defender is its sole occupant. In unarmed cases, transfer to the attacker's actual hand only when the win margin is at least five and custody/hand capacity is available; otherwise use the supported drop outcome.
- Update actual Object custody, possession, grip/hand/source, active readiness and dependent pending Actions consistently; resolve same-boundary competing events against a common state, with atomic commit and deterministic conflict/refusal, not iteration-order winner selection.

## B. Break weapon and Feint

- Break weapon: use the adopted **attacking weapon swing timing**, weapon being used by the opponent, the correct opponent-attacking-you / attacking-another / defending branches, damage/hardness/HP and potential both-weapons-break case. Preserve adopted *prior-second interruption* versus *same-second nonretroactivity*. Refuse unknown magic-saving, protection or hand/geometry facts instead of inventing them. Demonstrate at least one legitimate break and one failed attempt.
- Feint: require advanced skill in the wielded weapon or Unarmed combat skill, respect half weapon-motion timing rounded up and ordinary Attack Roll, use no damage on the Feint itself, and implement the one-use same-victim +2 on the actor's **next chosen Action** only if it is a follow-up attack against that victim. Expire it after that attack resolves even on a miss; forfeit immediately on another selected Action/target. Cover overlap, same-second ordering and checkpoint restore without leaking unobserved intentions.
- Undefended attack is an attack-resolution *condition*, not automatically a new playable command. Reuse existing target-defense rules when appropriate, and record any genuinely unsupported distinction under its own task ID.

## C. Grabbing and wrestling Objects

- A Grab on another Being's held Object must follow its **distinct Object-Grab attack rule**: holder's defense, Object-size modifier and +5 DC; do not substitute the unwilling-Being's opposed Improved-Grapple check. Keep the resulting Object grip distinct from ownership/possession and from a Grapple.
- Wrest after a successful Object Grab uses one second, opposed **3d6 + Strength bonus**, higher total wins, ties preserve the current situation. Ensure custody and hand occupancy genuinely transfer when legal. Apply the adopted multiple-success resolution: all independently successful new grabbers can acquire the Object, prior holder loses it; preserve shared custody/grip facts instead of arbitrarily choosing one winning grabber. Later contests among joint holders remain separate open scope where mechanics are not adopted.
- Include broken/released prerequisites, stolen or destroyed items, competing graspers, interrupted Actions, and simultaneous strikes where relevant. Do not create duplicate native Objects or grant free Draw/Ready or shield protection.

## D. Arena / persistence / acceptance evidence

- Present legal Action variants and appropriately scoped explanations in generated Arena Action composer; server validates opaque observer-owned handles, candidate equipment, targets, reachable paths and timing. Show weapon held/dropped/destroyed, existing Hand/Ready state, and Feint preparation/status only as authorized by observer evidence. Browser must never send or reveal native IDs.
- Run full supported end-to-end generated-NPC scenarios (explicit authored equipment/skills and path geometry allowed **only** through established scenario/native initialization, never by browser-side state mutation). Include tests executing the shipped JS/HTTP route; attempt real Chrome if available, and **separate** automated route evidence from a claimed manual demonstration.
- Fresh-process persistence must preserve Object IDs, custody, Grip/Hold, hand use, current Action identity and duration, unfinished/consumed Feint, damage state, observer-owned evidence and RNG. Verify nonmutation for rejected actions, stable deterministic rolls, same-second independent effects and rollback on faults.
- Run new/affected tests, nearby Choice/atomic/interval/geometry and Arena browser/persistence regressions, including a meaningful fresh-process sample. Do not claim an unrun full suite passes. Prefer focused cohorts over the costly full repo suite, unless shared primitives demonstrably warrant it.

## Report and completion discipline

Record an A–D acceptance matrix with **implemented vs bounded vs open** distinctions; test commands/counts/times and encountered failures; runnable generated-Arena reproduction including setup and expected receipts; actual-Chrome limitations; before→after `TASKS.md` task-ID changes; evidence for any source-data refusal; git status and scoped audited commit hashes. Report actual timezone-qualified ISO 8601 Start, End and Elapsed times (`PT...`) for each execution interval; do not estimate unrecorded intervals. Short chat closeout, durable details in `docs/reports/U-CAP-006-report.md`. Each commit: inspect exact staged paths, `git diff --cached --check`, `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 .venv/bin/python -B tools/check_publication_safety.py --staged`, and only commit reviewed scope. **No push**. Keep assignment and report active until accepted by ChatGPT.
