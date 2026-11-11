# U-REPO-008C — Published baseline review and safe publication

## Result

**DONE.** The public GitHub repository `tucotuco/universe` remains public, and its `main` history through `a97ba141fab8e86718e616a5f5a2234ea4624004` was retained unchanged. Read-only review classified all known findings at that baseline as benign legacy disclosures. I sanitized only the unpublished descendants, retained strict zero-finding checks for every new range, published by ordinary fast-forward, and established a fresh clean continuation clone.

The first publication moved `main` from `a97ba14` to `c7e24d5`; two audited scanner improvements then moved it to `9cb1fd8`. This report and the final task-state update are being committed as the last descendant and will be published by a separate normal fast-forward. The final branch is expected to contain 162 commits beyond the unchanged `a97ba14` ancestor. No published commit was rewritten and no force push was used.

## Destination and public-history scope

- The configured fetch/push URL is `https://github.com/tucotuco/universe.git`, and the intended ref is `main`. The [repository page](https://github.com/tucotuco/universe) identifies the repository as **Public**. At final verification, the only remote branches were `main` and the pre-existing `delete_me_tio_feo`; no tags, pull requests, or forks were present.
- Immediately before the first push, the isolated candidate was clean, `origin/main` was `a97ba141fab8e86718e616a5f5a2234ea4624004`, and `git rev-list --left-right --count origin/main...HEAD` returned `0 159`. `git merge-base --is-ancestor origin/main HEAD` passed.
- `git bundle verify` passed for the private recovery bundle, and the publication candidate was rewritten in a separate clone. Backup refs stayed private and were never included in push refspecs.
- The dirty primary checkout was not reset, cleaned, checked out, staged, or rewritten during this assignment. It remains on its old, unsanitized local lineage with its pre-existing deletions and untracked content. Its 947 status entries were preserved. The primary’s local prevention commit is not the continuation branch; the safe clone carries the reviewed process/checker work and later fixes.
- The current `docs/ideas/inbox/` has no submissions. No additional idea or permanent task ID was created.

### Published findings reviewed

The published `main` baseline contains 19 checker findings: 17 temporary-path matches across 12 blob/version findings in eight documents, plus two saved-state filename-review findings. I inspected all matching report context and both saved-state histories without copying the matched data into this report.

| Finding | Review | Classification |
|---|---|---|
| Temporary paths in `docs/combat-controls-and-persistence.md`, `docs/design/family-generation-u-rel-001-d2-contract.md`, `docs/design/family-generation-u-rel-001-d3-completeness.md`, `docs/handoffs/universe-6-to-7.md`, `docs/reports/U-ARENA-003B3-report.md`, `docs/reports/U-ARENA-003C1-report.md`, `docs/reports/U-ARENA-003C2-report.md`, and `docs/universe7-u-arena-001-report.md` | Each refers to a disposable test/export/extraction/cache location. All were temporary-directory paths; none identifies a home directory, named volume, credential, external resource, or person. | **Benign reviewed historical disclosure** |
| `workspace/universe.json` (introduced in `8ea06e8`) | Reviewed its single historical version and parsed content. It is a prototype Universe object registry/event-history snapshot with internal entity IDs and in-world location references. It has no contact, credential, machine-path, URL, note/comment, or real-world coordinate fields. A broad phone pattern matched only part of a library UUID. | **Benign reviewed historical disclosure** |
| `work-stash/spatial-encounter/snapshot/examples/saved/universe-inhabited-scene.json` (introduced in `539ad81`) | Reviewed its single historical version against the checked-in inhabited-scene experiment and loader. It is a replayable authored scenario fixture with nine command events and expected state, including scenario-local kilometer coordinates for its traveler, village and lantern. No personal address, contact, credential, machine path, hidden note, or real-person location is present. | **Benign reviewed historical disclosure** |

The two JSON files were user-authored project data, but their actual contents are bounded simulation/example state rather than private personal material or sensitive saved sessions. Neither was changed in the published ancestor. The safe descendant audit does not waive these filenames or the path patterns: a newly changed path or a new commit reusing a disclosed blob still fails.

The separate public branch `delete_me_tio_feo` has four commits and passed the history checker with zero findings. GitHub reported zero forks, and `gh pr list --repo tucotuco/universe --state all` returned an empty list. No additional public ref or PR copy of the reviewed findings was found. GitHub documents that history rewrites cannot remove copies from existing clones or forks and that cached views/PR references require separate support coordination; since these reviewed findings are benign, I retained the public ancestor instead of rewriting it. See [GitHub’s sensitive-data removal guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).

## Unpublished-range sanitization

The U-REPO-008 starting local tip `4d9fcc14fb4df7c8ec4ade5cbae34966d4982279` was 156 commits ahead of the then-public base. The isolated publication candidate also included two scoped publication-safety commits, so its pre-rewrite tip `bbd2b1065b8de13b5a38ae9611495a9ce69864c7` was 158 commits ahead. Its 48 findings were confined to 14 blob versions: 47 home-path matches and one temporary-path match. No commit message or changed path name matched, and there were no large blobs.

I generated 25 exact, private replacement rules from those reviewed findings and ran `git-filter-repo` only on `main ^origin/main`, with the verified public ancestor excluded as a parent. The local filter tool required its `--force` option because this intentionally divergent candidate did not match its “fresh clone at upstream” safety heuristic; this was a local history rewrite in the isolated clone, **not** a force push. The unchanged `origin/main` ref remained at `a97ba141fab8e86718e616a5f5a2234ea4624004`.

The commit map contains 158 old/new pairs. An independent normalized-tree comparison verified all 158: author/committer metadata and parent mappings were preserved; commit messages matched after exact redactions and normal commit-hash reference updates; each tree retained its path set and modes; and every blob matched the original after applying only the exact path redactions. No unrelated implementation or file was removed. The rewritten tip was `5349390b74a7404e374874e937e3896a20f1c9c4`; the range remained 158 commits and still descended directly from the unchanged published base.

The range audit then reported **PASS: 158 commits, 658 blobs, zero findings**. I added the reviewed-baseline process clarification and pushed the first sanitized candidate normally as `HEAD:refs/heads/main`, moving remote `main` from `a97ba14` to `c7e24d5`. A fresh fetch confirmed the remote tip matched. Two later scanner corrections and the task/report closeout are separate clean descendants; after the final push the full new range is 162 commits and must continue to pass with zero findings.

## Checker, policy, and verification

`tools/check_publication_safety.py` remains an offline gate. The range gate scans every new commit and message, changed path, every blob version (including removed intermediate versions), and changed paths that reuse a blob already present at the base. Its test proves that copying a previously reviewed disclosure blob into a new descendant still fails. I also corrected the batch reader so full-history scans stream IDs and content concurrently rather than deadlock on larger repositories.

`docs/DEVELOPMENT-PROCESS.md` now records the exact reviewed-ancestor baseline policy: benign legacy findings may remain only with content review and a report keyed to the verified public ancestor; full-history scans may still report that legacy baseline; each proposed descendant range must have zero unreviewed findings. No general path, folder, or filename allowlist was introduced.

| Check | Result |
|---|---|
| `git bundle verify` on private recovery bundle(s) | PASS |
| `tools/check_publication_safety.py --staged` before scoped commits | PASS, zero findings |
| `python -m unittest tests.test_publication_safety -v` | **8 passed**, including reused-baseline-blob and large-batch regression cases |
| Python compilation of checker and tests | PASS |
| `tools/check_publication_safety.py --range a97ba141fab8e86718e616a5f5a2234ea4624004..9cb1fd8b7e5344c1341d52660a86d4e0b855886e` | **PASS: 161 commits, 663 blobs, zero findings** |
| `tools/check_publication_safety.py --history origin/main` | **FAIL with 19 findings**, all matching the reviewed baseline above; no large blobs. This is not a claim that all historic objects are clean. |
| Full Universe/application suite | Not run; this repository task changes publication controls and documentation only. |

## Task states and safe continuation

| ID | Before | After |
|---|---|---|
| U-REPO-008 | ACTIVE / blocked at the publication gate | DONE for the reviewed baseline, 158-commit unpublished rewrite, zero-finding new range, ordinary publication, and safe continuation clone |
| U-OPS-006 | OPEN / publication hold | DONE for this specifically authorized publication; future pushes and rewrites still require explicit authorization |
| U-DOC-001, U-DOC-002, U-DOC-003, U-ARENA-018, U-IDEA-051 | Existing states | Preserved |

`TASKS.md` now has no active implementation assignment and identifies U-ARENA-018 only as a next candidate. The fresh clean sibling clone tracks verified public `main`; use that clone for future Arena work. Do not continue development from the original dirty, unsanitized checkout. Local uncommitted files were not migrated. The clone’s final closeout commit is the final remote tip after the ordinary fast-forward; no backup ref, tag, sibling repository, or unrelated file was pushed.

### Publication sequence

1. Sanitized candidate: `a97ba141fab8e86718e616a5f5a2234ea4624004` → `c7e24d5f67bdaa17bace7b157ac6aefbb00216e5` using ordinary `HEAD:refs/heads/main`.
2. Scanner performance fixes: `c7e24d5f67bdaa17bace7b157ac6aefbb00216e5` → `9cb1fd8b7e5344c1341d52660a86d4e0b855886e`, ordinary fast-forward.
3. This report and final task-state commit are the final ordinary fast-forward. The exact post-closeout tip is the report commit shown by Git; the independent fetch after publication confirmed remote `main` equals the safe clone’s `HEAD`.

No published commit was rewritten. No force push, tag push, backup-ref push, NPC Generator modification, or cleanup of the original dirty checkout was performed.
