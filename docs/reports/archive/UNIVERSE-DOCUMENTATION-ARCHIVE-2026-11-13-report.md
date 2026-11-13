# One-time Universe assignment and engineering-report archive

**Result:** completed. The user explicitly authorized a one-time historical sweep of every assignment document and engineering report Markdown file directly under the active directories. This disposition applies only to this sweep; the permanent future archival gates remain unchanged.

## Codex execution interval

| Start (ISO 8601) | End (ISO 8601) | Elapsed (ISO 8601 duration) |
|---|---|---|
| `2026-11-13T08:45:52-08:00` | `2026-11-13T09:02:03-08:00` | `PT16M11S` |

## Inventory

- **14 assignment documents moved** to `docs/assignments/archive/`: U-ARENA-011, U-ARENA-015, U-ARENA-018, both U-ARENA-018B variants, U-ARENA-018C, both U-ARENA-018D variants, U-CAP-001 adopted clarifications, U-REPO-009, both U-REPO-010 variants, U-REPO-012, and corrected U-REPO-013.
- **95 engineering reports moved** to `docs/reports/archive/`: all report Markdown files present directly in the active directory, including the U-ARENA, U-NPC-BEING, U-REPO, U-THROW and U-SPATIAL series, U-ARENA-018 closeout, the engineering baseline, and the two Universe 4/5 incremental reports.
- **Already archived before this sweep:** 10 assignment Markdown documents and the U-CAP-001 engineering report. The assignment archive README is an index and is not counted as an assignment. U-CAP-001 remained in place.
- Of the 109 moved documents, 100 were tracked and relocated with `git mv`; 9 were previously untracked, inspected and moved to their archive paths, then added after pre-staging safety review. Existing filenames were retained. No archive filename collision was found. The two distinct U-ARENA-018B filenames have duplicate content after whitespace-only cleanup; both are retained at their original distinct names.
- The direct directories now contain no assignment/report Markdown documents. Their README files explain where new unfinished assignments and unreviewed reports belong. The unrelated assignment `.DS_Store` and `universe-arena.json`, and the report-directory `U-THROW-001-rule-sync-proposal.patch`, were left in place.

## Reference repair and preserved history

Updated `TASKS.md`, maintained handoffs and task/design documentation, archive indexes, and Markdown links inside relocated documents. Relative links in moved documents were rebased; links to moved documents now target their archive paths. The U-ARENA-018 continuation handoff has a dated archive/status note. Task state and project priorities were not changed.

The required staged safety audit found four local temporary-directory prefixes in three historical reports (`U-ARENA-003B3`, `U-ARENA-003C1`, and `U-ARENA-003C2`). The reports were retained; only those prefixes were changed to `<temporary-directory>`. No other unsafe or duplicate candidate was found. The nine formerly untracked Markdown documents passed a direct pre-staging publication-pattern scan. Final staged audit: 221 staged path/content entries, **0 findings**.

The link checker found 20 pre-existing broken or external-placeholder links before the moves. After relocation it found the same 20 and no new broken links; no Markdown link points at a direct active assignment/report path. The unchanged items are two links to absent U-REPO-006 reports, historical links in the Universe 6→7 handoff to files no longer in this checkout, and eight sanitized placeholder references in the U-ARENA-004A report. All newly introduced README and handoff links resolve.

## Verification, Git, and exceptions

This was documentation-only; no implementation tests were run. `git diff --check` and `git diff --cached --check` passed. `.venv/bin/python -B tools/check_publication_safety.py --staged` passed with zero findings. The main archive/reference commit is `c7aa7bd6de9f8e54167c54680fa5ae97fb7c2436`; its closeout includes 100 Git-detected renames, reference repairs, 9 previously untracked archival documents, and active-directory guidance. The persistent closeout report is committed separately; its commit hash is given in the Codex closeout.

The prior archive index identifies three older repository-cleanup assignment documents available only in preserved private pre-safe copies. They were not present under either active directory, were not accessed, and were not moved. No files were discarded or overwritten. No push, history rewrite, implementation change, task-priority change, or change to `.venv`, ignored `legacy/`, local saved-world data, independent repositories, or backups was made. The pre-existing unrelated `docs/assignments/universe-arena.json` remains untracked and untouched.

Future work remains governed by [`DEVELOPMENT-PROCESS.md`](../../process/DEVELOPMENT-PROCESS.md): archive an assignment only after its completion is confirmed and a report only after ChatGPT has reviewed and accepted it.
