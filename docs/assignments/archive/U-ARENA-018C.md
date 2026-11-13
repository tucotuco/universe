# U-ARENA-018C — Native held-Object Grab and Wrest

**Repository:** active `~/Projects/universe` only
**Install:** `docs/assignments/U-ARENA-018C.md`
**Report:** `docs/reports/U-ARENA-018C-report.md`
**Prompt:** `Execute docs/assignments/U-ARENA-018C.md.`
**Push:** NOT authorized. Local, scoped commits ARE authorized by the existing standing development process.

## Outcome

Deliver the **smallest genuinely native, receipt-backed** sequence in which one generated Arena Being successfully Grabs a specific Object **held by another Being**, then attempts the adopted one-second **Wrest** contest. On a lawful win, the *same native Object ID* changes hand/custody atomically; on a failed/tied contest, ownership does not change. Show the sequence through existing Arena HTTP/session controls and fresh-process Save/Load. The implementation must respect the controlling Encounter rules, not invent a parallel minigame. This is a focused continuation of PARTIAL `U-ARENA-018` and OPEN `U-ACT-027`, **not** a demand to close the entire grappling family.

**Very important — concise chat:** At completion, Codex's **chat response must be at most eight short lines**: (1) status, (2) demonstrated capability, (3) focused-test result, (4) local commit(s), (5) principal blocker if any, (6) next step. **Do not paste the engineering report, test log, inventories, or a lengthy narrative into chat.** Put full evidence in the Markdown report. Do not request separate conversational permission for routine, in-scope local commits.

## Authority, bounds, and preflight

1. Verify actual branch, HEAD, worktree/index status and local remote tracking; the last reported implementation commit was `23c462d`, followed by a report-only commit, **not pushed**. Do not assume HEAD is still that commit or that `origin/main` is current. Preserve all existing untracked user files and unrelated changes.
2. Read `TASKS.md`, `docs/process/DEVELOPMENT-PROCESS.md`, `docs/encounters/README.md`, the **controlling revision 61 and supplements 62–65**, `docs/reports/U-ARENA-018-report.md`, `docs/reports/U-ARENA-018B-report.md`, and directly relevant native code/tests. Read `docs/ideas/inbox/` if it exists and apply ordinary intake procedure without expanding scope. Use the actual live repository to resolve path/name drift.
3. The U-ARENA-018B report verifies native Release grip and Trip changes plus HTTP/session fresh-process release, and identifies the missing typed **Object Grip**, native Wrest and atomic same-ID custody transfer. Preserve those implementations and tests. It also independently reproduced **nine checkpoint reconstruction errors in both a pristine `ab4089f` export and current worktree**. Treat these as an established baseline diagnostic, not as a new failure or authorization to weaken checkpoint/semantic-closure validation. Investigate only if new work affects that machinery; separately track a fix if necessary.
4. Use the existing `universe/.venv` with `.venv/bin/python -B`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONNOUSERSITE=1`, and suitable `PYTHONPATH=tests:src:examples`. Do not reinstall packages, rebuild `.venv`, mutate `npc-generator`, access or alter the three independent repository backups, modify the ignored `legacy/` collection or local saves, or begin geology work. No broad Git cleanup or full suite by default.

## Implement one coherent vertical slice

**A. Physical Object Grip from a genuine held Object.** Determine the real native Object identity, holder and hand, equip/readiness/custody facts, actual observation/reach/eligibility, and existing physical-contact representation. Add a distinct typed result/effect/receipt and durable state for a successful **Grab of a held Object**, separate from Grab of a Being, ground Pick up and Disarm. Implement the adopted attack resolution including holder's Defense, Object-size modifier and **+5 DC**, against the correct shared post-movement/pre-Action snapshot. Never infer success from visual proximity or let the browser author physics or unseen identities. Fail without publishing unsupported effects or spending RNG when the declared action is invalid.

**B. Wrest.** Require a qualifying, current Object Grip and follow revision 61's **one-second `3d6 + Strength bonus` contest** and its actual win/tie/failure rules. A successful Wrest transfers **the existing Object**, not a duplicate, using the native hand/custody and reservation protocol. Remove or update stale grips/hand references only as prescribed by adopted rules. Ensure target hand release and actor's receiving-hand availability are evaluated against the common snapshot, and publish consequences atomically. A failure/tie cannot silently transfer or drop the Object. Preserve deterministic RNG, rollback on exceptional failure and legitimate independent simultaneous Actions.

**C. Contention and unsupported cases.** Add focused regression scenarios for two attempts against one held Object, a holder dropping or otherwise losing the Object at the same boundary, another Actor/holder action competing for its custody, and any current Object Grip invalidated before a later Wrest. Apply only **already adopted** ordering, reservation, simultaneous-action and custody rules. If a case requires a genuinely unadopted conflict policy, *fail that case closed without corrupting state*, document the exact policy choice required, and continue completing the uncontested vertical slice. Do not silently invent winner priority, random tie-breaking, force transfer, or retroactive same-second cancellation. Do not expand to general multi-Action capacity, automatic six-second Hold scheduling, all positioning restrictions, Stun, Subdue or unarmed Disarm.

**D. Actual Arena and persistence.** Supply observer-authorized Action options for grabbing a visible held Object and subsequently Wrestling it; do not expose hidden objects, other Being's private state, or invalid target IDs. Demonstrate a reproducible **generated two-Being** Arena sequence with native object selection; the held Object must actually be held by the opponent through legitimate native actions. Use the existing HTTP/session route, receipt/state assertions, and save/reload in a **fresh Python process** to demonstrate at least one pending/established Object Grip and a completed Wrest (or clearly report if a distinct save/restore contract blocks one branch). Differentiate HTTP/session tests from an actual Chrome walkthrough. Do not claim browser verification without a real browser run.

## Acceptance and tests

- Prove positive Grip and Wrest with real generated Beings and one real held Object; verify preservation of Object ID and consistent ownership/hand references before and after the atomic commit.
- Prove invalid target, unobserved Object, inadequate reach/access, occupied receiving hand, missing/expired Grip, failed/tied Wrest, simultaneous conflict, and rollback produce **no illicit custody changes**. Distinguish cases supported by current rules from fail-closed deferred cases.
- Verify source/Action receipts, common-snapshot simultaneity, deterministic replay and fresh-process Save/Load. Include a short end-to-end script or focused test command in the report.
- Run only directly affected/new native, Arena HTTP/session and persistence tests plus minimal nearby release/grapple/trip regressions; `py_compile`, `git diff --check`, and staged publication-safety checks. Run the full suite only if a shared high-risk primitive genuinely warrants it. Record exact test names/counts/timing; never label unrun tests green.
- Keep `TASKS.md` authoritative as current **state**, not chronology. At minimum reconcile `U-ARENA-018`, `U-ACT-011`, `U-ACT-027`, `U-ACT-008` (if custody relevant), `U-UI-001`, and `U-PER-002`, with before → after entries in the report. `U-ARENA-018` remains PARTIAL unless the broad remaining lifecycle and position/capacity/browser scope is truly closed; a bounded successful Wrest does not make all Grapple work DONE. Intake new ideas only as deferred records, not authorized feature work.

## Commits, report, and finish

Make **one to three small independently checked local commits** at coherent boundaries. Explicitly review the staged paths and diff, run `git diff --cached --check`, and `.venv/bin/python -B tools/check_publication_safety.py --staged` before every commit. Never blanket-stage, reset, delete user files, rewrite history, commit ignored private material, or push. Include ordinary scoped code/test/state and report commits without repeatedly asking for permission.

Write `docs/reports/U-ARENA-018C-report.md` with: **Where we stand** (3–5 sentences); demonstrated generated Arena scenario and receipts; implementation changes; rule-authority and deferred-policy distinctions; focused tests and exact timings; persistence/browser evidence; task-state before→after; staged safety checks; commits; and next engineering priority. Make sure the report matches actual final HEAD and does not promise functionality not implemented. **Chat response ≤8 short lines** with a link/path to the report, not its contents.

**Exact invocation:** `Execute docs/assignments/U-ARENA-018C.md.`
