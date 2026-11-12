# U-DOC-001 — Adopt one canonical Universe state/ideas register and development process

**Repository:** `universe`, Codex owned.<br>
**Suggested run point:** after U-ARENA-018 completes, or at a nonconflicting documented commit boundary; **do not interrupt or overwrite concurrent source/TASKS changes**.<br>
**Source files supplied by ChatGPT for installation:** `TASKS.md` and `DEVELOPMENT-PROCESS.md` (both prepared 2026-11-11).<br>
**Intended destinations:** repository-root `TASKS.md`, `docs/DEVELOPMENT-PROCESS.md`.<br>
**Required report:** `docs/reports/U-DOC-001-report.md`.<br>
**Prompt:** `Execute docs/assignments/U-DOC-001.md.`

## Outcome

The repository should have one **comprehensive, evidence-reconciled, list-based root `TASKS.md`** for all DONE, ACTIVE, next, PARTIAL/OPEN/BLOCKED/DEFERRED tasks **and IDEA entries**, and one version-controlled development-process contract that requires every future Codex assignment to direct its own `TASKS.md` updates. Do **not** maintain a second current ideas list; retain `docs/deferred-ideas.md` as archival source. This is a **documentation/state migration**, not permission to change simulation rules, engine implementation, source test behavior, or Git history.

The provided files are candidates, not authority about an unseen live checkout. The current repository may contain newer statuses, ideas, or the finished U-ARENA-018 report. **Reconcile before committing; never replace a richer live version with an older snapshot.**

## 1. Source and repository preflight

1. Inspect `git status --short --branch`, actual HEAD/branch/upstream, `git log --oneline -15`, staged changes and explicit provenance of any in-progress task-file edits. Preserve user-managed tracked deletions, all untracked materials, `legacy/`, `.agents/`, `.claude/`, saved world JSON, and the sibling independent `npc-generator`. No blanket staging, reset, clean, stash, mass restoration, rebase or push.
2. Read live `TASKS.md`, `docs/tasks/*.md`, `docs/deferred-ideas.md`, `docs/encounters/README.md` and current issue register, handoffs through Universe 9, the latest actual Arena reports (especially U-ARENA-016B, -017 and any -018 report), and relevant U-REL-001/reproduction reports. Inspect the exact source/test evidence for disputed claims. Source paths and current rule precedence may have changed.
3. Read the two supplied candidates **as source material**. Inventory current/candidate stable task IDs and idea entries; compare by ID and concept. Identify missing current-local entries, duplicate IDs, conflicts, stale statuses, incorrect paths and statements unsupported by actual reports/tests. Do not assume chat-side file dates equal local Git status. Explicitly distinguish absence from true incompleteness.

## 2. Merge and adopt current state, not historical narrative

4. Reconcile root TASKS with all current tasks and previously retained ideas. Preserve every legitimate local task/idea and all existing permanent IDs. Add candidate entries absent from local only after checking that they are not duplicate concepts under another ID. If a candidate has a new `U-ACT-*` or `U-IDEA-*` ID that collides with an independently created local ID, allocate a noncolliding ID **and record the mapping**. No silent overwrite, deletion, regression or accidental promotion from IDEA to adopted rule.
5. Correct the snapshot to **actual current states**, especially whether U-ARENA-018 is still assigned or has a verified report; do not mark Takedown/Reverse/Pin/Trip/Wrest as done based on the assignment alone. Preserve fully accurate bounded qualifiers for U-ARENA-015–017, current dynamic NPC integration, actual reproducible persistence and unresolved checkpoint failures. Distinguish earlier R4.6 experimental Grapple logic from production native integration. Treat current adopted rules README as authority, not the obsolete r60 documentation references.
6. Maintain one ACTIVE program *when work is active*. If the last program is complete and none is authorized, explicitly show **no active implementation** instead of inventing one. Keep NEXT options as options, not an authorization to execute. Keep already completed tasks in a compact DONE section (not an incremental execution log); all future ideas live **in `TASKS.md`**.
7. Install `docs/DEVELOPMENT-PROCESS.md`, adjusting only genuine repository-specific conflicts. It must document the single state register, status/idea lifecycle, source-of-truth hierarchy, user/ChatGPT/Codex roles, formal assignment/report cycle, mandatory assignment TASKS clause, test/commit/persistence/privacy safeguards, and conversation-handoff protocol. Link it from root TASKS (and from existing README or handoff navigation only where that is an obvious localized documentation change).
8. Do not remove historical `docs/deferred-ideas.md`, experiment files, `docs/tasks/` details or old handoffs. They remain provenance, **not** second canonical status authorities. Do not rewrite adopted Encounter rules or issue statuses as part of this documentation-only job.

## 3. Validate and commit

9. Check no duplicate IDs and exactly one status interpretation per row; check that all current tasks/idea concepts from the old root and deferred-ideas list are represented, with no false closure. Resolve obvious Markdown links against actual file paths. `git diff --check` must pass. A lightweight Markdown parser/script is acceptable; do not require a full one-hour test suite for documentation-only changes.
10. Stage explicitly reviewed `TASKS.md`, `docs/DEVELOPMENT-PROCESS.md`, any directly needed navigation edit and `docs/reports/U-DOC-001-report.md`, with correct generation/commit timing. Commit one clean coherent documentation change (or a minimal doc-state commit plus one report commit). No unapproved push, no history rewrite, no private path or absolute machine path in newly committed reports.
11. Write the report: actual starting HEAD/status, source documents reviewed, preserved/migrated task/idea counts, added/renamed IDs, major discrepancies resolved, current ACTIVE status, affected files, checks actually run, commits and remaining unverified ideas. **If you cannot safely reconcile local files, leave them untouched and report a precise merge/conflict plan.** Do not claim installation succeeded otherwise.

## 4. New standard for every future Codex assignment

The two installed documents govern future coordination. Every new `docs/assignments/<ID>.md` must include a `TASKS.md` integration section following the copyable clause in `docs/DEVELOPMENT-PROCESS.md`. It must list exact IDs to inspect/update and require the final report to identify **before → after** states and whether the TASKS edit was committed. Ordinary implementation work should update only relevant rows and newly discovered ideas, not rewrite the register as a changelog. Future ChatGPT/Codex handoffs use current `TASKS.md` + process + adopted rule README + latest report/assignment as their minimum navigation set.

**Minimum success:** a single comprehensive current state/idea register and a functioning written process contract **in the actual Git repository**, safely reconciled to current local work, with verification and a concise report. An unchanged candidate copied over newer local edits is a failure.
