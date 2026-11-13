# U-REPO-008 — Publication audit, prevention controls, and hold

## Result

**PARTIAL / PUBLICATION BLOCKED pending a user decision.** The intended public destination is the public GitHub repository [`tucotuco/universe`](https://github.com/tucotuco/universe), branch `main`. The freshly fetched remote tip `a97ba141fab8e86718e616a5f5a2234ea4624004` is an ancestor of local pre-task HEAD `4d9fcc14fb4df7c8ec4ade5cbae34966d4982279`; the exact unpublished range contains 156 commits. The destination did not move during verification.

The newly reachable unpublished range has 48 machine-local path matches across 14 object/version findings. The remote's already-published history also has 17 machine-temporary-path matches across 12 findings, plus two published saved-state filename review findings (one workspace JSON and one archived saved-scene JSON). These files were not opened or altered; filenames alone do not establish that their contents are safe. No secret-pattern match or blob over 2 MB was found in either scan. U-REPO-008 expressly says to stop for published-history exposure. The existing authorization covers rewriting unpublished commits, not rewriting the public ancestor. Therefore **no history was rewritten and nothing was pushed**.

I completed the independent prevention increment: a staged-content and history-range checker with synthetic tests, process-contract publication gates, and current task-state updates. The checker confirms the unpublished range currently fails. This is not a claim that it is safe to push.

## Destination, recovery, and scope

- `git remote -v` and upstream configuration designate `origin` → public `https://github.com/tucotuco/universe.git`, `main` → `origin/main`. GitHub independently identifies that repository as public. `git ls-remote --heads --tags origin` returned `main` at the hash above and one unrelated existing branch; no tags were returned. Only `main` is the authorized publication target.
- The remote was freshly fetched into a clean isolated clone. `git rev-list --left-right --count origin/main...main` returned `0 156`; `git merge-base --is-ancestor origin/main main` passed. The isolated clone's pre-task HEAD exactly matched the dirty primary's pre-task HEAD.
- Before any rewrite, an all-ref Git bundle was created outside the working tree and `git bundle verify` passed. The isolated clone was created from that bundle and then fetched the live remote. The dirty primary was not reset, cleaned, checked out, or rewritten; its original deletions, untracked content, ignored data, and sibling repository remain untouched. No dirty-file backup copy was required because that checkout was left in place and was not modified for the rewrite.
- The unpublished audit found 47 home-directory matches and one temporary-directory match. Findings are confined to historical engineering reports, including the prior handoff leads and later report versions. The published audit found 17 temporary-directory matches across eight historical documents. This report gives only categories, counts, and repository-relative document locations; it does not reproduce any matched value.
- Neither audit found a high-confidence credential/token/private-key match or a blob exceeding the 2 MB review threshold. The published saved-state filename findings remain unreviewed because the assignment's published-history stop condition has been reached.

## Checker and process controls

Added `tools/check_publication_safety.py`, an offline CLI with two gates:

- Before each commit: `python tools/check_publication_safety.py --staged` scans staged path names and staged content, including symlink target blobs. It does not enumerate arbitrary untracked files. It reports finding category/location without echoing matched values and fails closed.
- Before an approved push: `python tools/check_publication_safety.py --range <verified-upstream>..<proposed-tip>` scans every commit's raw metadata/message, changed path name, and each unique newly reachable blob version, including intermediate content later removed. It flags secrets, local file URLs and machine paths, sensitive filenames, and blobs over the review threshold. Explicit `<PLACEHOLDER>` examples and repository-relative paths pass; there is no blanket whitelist.
- For a baseline / already-published-history audit: `python tools/check_publication_safety.py --history <tip>` scans all reachable commit and object history without changing it.

`tests/test_publication_safety.py` uses only disposable local repositories and covers clean relative/placeholder paths, Unix home/temp/volume/run-user paths, Windows home paths, `file://` URLs, a secret assignment, a commit-message path, staged content, and a sensitive path committed then removed before HEAD. The tests make no network requests and verify that scanner output does not echo the matched values.

The current `docs/DEVELOPMENT-PROCESS.md` now requires the staged gate before every future commit, the history gate before every separately authorized push, explicit destination/ancestry checks, report evidence, and a stop on unresolved disclosures. It clarifies that ordinary assignments still do not authorize push or history rewrite. No hook is claimed; a local hook would not be a version-controlled control.

## Verification

- `git bundle create <PRIVATE_RECOVERY_BUNDLE> --all` and `git bundle verify <PRIVATE_RECOVERY_BUNDLE>` — passed; isolated clone created from that bundle.
- `git fetch --prune origin` in the isolated clone, `git rev-parse HEAD refs/remotes/origin/main`, `git rev-list --left-right --count origin/main...HEAD`, and `git merge-base --is-ancestor origin/main HEAD` — passed with the hashes/count recorded above.
- Initial object audit using an offline scanner over `origin/main..main`: 156 commits, 1,355 unique reachable objects, 48 path findings in unpublished history; zero large blobs and zero sensitive filenames.
- `tools/check_publication_safety.py --history refs/remotes/origin/main` — **FAIL: 152 commits, 1,128 blobs, 19 findings** (17 temporary-path matches and two saved-state filename reviews); zero large blobs. This is the mandatory stop condition; the existing public objects were not altered.
- `python -m unittest tests.test_publication_safety -v` — **6 passed**.
- `python -m py_compile tools/check_publication_safety.py tests/test_publication_safety.py` — passed.
- `tools/check_publication_safety.py --staged` — **PASS: 5 explicitly staged files, zero findings**. `git diff --cached --check` — passed.
- `tools/check_publication_safety.py --range refs/remotes/origin/main..refs/heads/main` — **FAIL as expected: 156 commits, 652 blobs, 48 findings**. This exact pre-task range is not clean and was not pushed.
- No application tests or full suite were run. The change adds documentation and an offline audit utility only.

## Task-state transitions and continuation

| ID | Before | After |
|---|---|---|
| U-OPS-006 | OPEN / publication hold | OPEN / publication hold; current published-history finding must be resolved by user direction before publication |
| U-REPO-008 | Not registered | ACTIVE / BLOCKED at the publication gate; prevention control complete locally, unpublished sanitization/publication incomplete |
| U-DOC-001, U-DOC-002, U-DOC-003, U-ARENA-018, U-IDEA-051 | Existing states | Preserved |

The checker and process amendment are being delivered as a scoped local commit only; it has not been pushed. The primary checkout remains on the original unsanitized lineage, with the prevention/report commit atop it, and retains user data; do not treat it as a safe continuation point. The private recovery bundle and isolated clone are analysis/recovery artifacts, not the designated future development checkout.

Once the published-history decision is resolved, the next safe procedure is to sanitize only the explicitly authorized history in the isolated clone, rerun the checker and equivalence validation, re-fetch `origin/main`, and push only if the clean rewritten branch remains an ordinary fast-forward from the verified published ancestor. Then create a fresh local clone tracking the independently verified sanitized remote tip; leave the dirty primary untouched and use the new clone for future Codex work. No commit mapping was generated because no rewrite occurred.

No force push, ordinary push, history rewrite, NPC Generator modification, primary-checkout cleanup, or unrelated file staging was performed.
