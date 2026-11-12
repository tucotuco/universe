# U-DOC-001 — Canonical state register and process adoption

## Result

Installed the reconciled root [`TASKS.md`](../../TASKS.md) and historical [`docs/DEVELOPMENT-PROCESS.md`](../process/DEVELOPMENT-PROCESS.md). The register now has 181 unique list entries covering bounded completed work, open/partial/deferred items, candidate next work, all 39 adopted Combat Action inventory entries, and retained ideas. It preserves every stable ID found in the previously committed register.

There is **no active implementation assignment** after this documentation task. U-ARENA-018 is recorded once as PARTIAL / OPEN and a NEXT candidate: its report verifies native Takedown, Reverse, Pin and Trip plus an in-app-browser Touch→Grab→Grapple→Takedown flow with pending-Grapple Save/Load, but it explicitly says the assignment is incomplete. The separate Chrome run reached Touch and Grab only. The remaining close-contact requirements stay visible; no feature work was performed here.

## Reconciliation evidence and decisions

- Starting checkout: branch `main`, HEAD `1237897b8749b27f360856b182c85ba1f45b191e`, tracking `origin/main` and 154 commits ahead. The working tree already contained the supplied modified `TASKS.md`, an untracked root `DEVELOPMENT-PROCESS.md` candidate, many tracked documentation deletions, and unrelated untracked content. These were preserved. The supplied root process candidate remains untouched and unstaged.
- Compared committed `TASKS.md` (56 unique referenced IDs) with the working candidate (162 unique referenced IDs), five `docs/tasks/` topic files, the historical backlog at `docs/design/deferred-ideas.md`, the inbox idea, Encounter package README and generated outstanding issue list, handoffs through Universe 9, and the current U-ARENA-011 through U-ARENA-018 reports and assignments. Also reviewed the U-ARENA-016B and U-ARENA-017 reports, the Generation/Attention topic and U-REL-001 D1–D3 design contracts/examples.
- There is no standalone current `U-REL-001` engineering report. The task file and implementation examples provide the V1–V12 scope and limitations; they say the profiles are not adopted biology and the bounded reproduction checkpoints are not general Encounter persistence.
- The adopted Encounter README identifies revision 61 plus the applicable revision 62–65 supplements as the controlling package. The outstanding issue list is generated from the historical revision-60 issue register and still contains an older baseline description. This documentation task did not rewrite either adopted rules or issue statuses; `U-DOC-003` remains open to reconcile that register carefully.
- The candidate incorrectly said U-ARENA-018 was assigned with no report and omitted 18 IDs from the committed register. The final list restores the historical U-ARENA-002/003 chain and its bounded 003A–003C3 checkpoints, U-LOC-002B, U-NPC-BEING, U-OPS-001A, and U-THROW-001–006; it also adds U-ARENA-011–013 as explicit bounded milestones. The U-ARENA-003 umbrella remains PARTIAL / OPEN because the fixed local claims did not establish general persistence. U-PER-002 remains the current general persistence gap.
- The user idea intake `IDEA-SUB-20261111-001` is distinct in scope from broad U-IDEA-016 ecology/evolution. It is registered as **U-IDEA-051**, remains an unauthorized IDEA (not a rule or task), and links to its preserved detail at `docs/ideas/processed/IDEA-20261111-biota-molecular-phylogeny.md`. The source note was moved from `ideas/inbox/` only after staging and validating its `TASKS.md` entry, as it directed. Other inbox/untracked items were not moved.

The new process document establishes source-of-truth precedence, the no-shadow-register rule, status meanings, collaboration ownership, future assignment/report requirements, test evidence levels, worktree/Git safety, and handoff procedure. Its copyable assignment clause requires exact affected IDs, evidence-based before→after statuses, preservation of unrelated state, and confirmation that the register was actually committed.

## Task-state transitions

| IDs | Before | After |
|---|---|---|
| U-DOC-001 | NEXT candidate | DONE: reconciled register and process installed |
| U-ARENA-018 | Candidate snapshot said ASSIGNED, no report | PARTIAL / OPEN, with verified implementation and remaining gaps; NEXT candidate, not ACTIVE |
| U-ARENA-011, U-ARENA-012, U-ARENA-013 | Omitted by candidate | DONE, bounded according to their reports |
| U-ARENA-002, U-ARENA-003 and U-ARENA-003A/B1/B2/B3/C1/C2/C3 | Omitted by candidate | Restored as bounded historical milestones; 003 remains PARTIAL / OPEN |
| U-LOC-002B, U-NPC-BEING, U-OPS-001A, U-THROW-001–006 | Omitted by candidate | Preserved with their historical/deferred bounded status |
| U-IDEA-051 | Intake had no register ID | Added as speculative IDEA linked to preserved source |
| U-DOC-002, U-DOC-003 | Existing candidate OPEN | Remain OPEN for historical idea completeness and Encounter issue-register reconciliation |
| Active implementation | U-ARENA-018 stale candidate said ACTIVE / ASSIGNED | None after U-DOC-001; no old assignment is treated as current authorization |

## Validation

- Stable-ID comparison against committed `TASKS.md`: **no prior IDs absent**.
- Register entry check: **181 rows / 181 unique IDs; no duplicate entry IDs**. All 39 `U-ACT-*` inventory rows remain individually represented.
- Local Markdown link checks for `TASKS.md` and `docs/DEVELOPMENT-PROCESS.md`: **no missing targets**.
- Process-contract structural checks: copyable mandatory `TASKS.md` assignment clause, exact ID listing, before→after reporting, preservation safeguards, no-push rule, and explicit no-active-task state are present.
- `git diff --check`: passed.
- No application/source/test files were changed. No full test suite was run for this documentation-only task.

## Files, Git, and remaining verification

The state/process/idea migration is committed as `134a93a` (`Adopt canonical task register and process`), with only `TASKS.md`, `docs/DEVELOPMENT-PROCESS.md`, and the processed IDEA note staged. This report is recorded in an adjacent report-only commit. The many pre-existing tracked deletions and unrelated untracked files remain outside the staged set. The local branch remains ahead of its upstream; no push, reset, cleanup, history rewrite, or NPC Generator modification was performed.

`U-DOC-002` keeps the limit of historical idea completeness explicit: inaccessible conversation exports cannot be audited from this checkout. Continue capturing ideas in `TASKS.md`, and use U-DOC-003 before relying on the stale generated issue list as a current status authority.
