# Repository workflow and preservation

Back to [TASKS.md](../../TASKS.md).

## Verified commits and test provenance

- **5E3A:** commit `e169660c2b39e028b2bba337a35fde1bc22acd13`; exact 83-path candidate tree `31a08dc6036a6a127d7506ea9cc3603c3338fcea`. The isolated 5E2Z candidate reported 1,573 complete HTTP-inclusive and 400 focused tests.
- **5E3F:** commit `03c5e9a874c88ac21686b0c0da58d24a736a4cd4` preserves interrupted work under Git-tracked `work-stash/`, with 78 verified snapshots.
- **5E3H:** commit `379219223686d841fdff70702cd43a45423b8758`, parent `03c5e9a874c88ac21686b0c0da58d24a736a4cd4`, tree `1d12256a79aca7f9ca06b279e238ca462d836d54`; 25 documentation paths. The latest full clean-export regression reported 1,573 passing tests at 5E3G. The 5E2U dirty-tree integration reported 1,630; that later count is separate evidence and is not a replacement for the committed 5E3A candidate provenance.
- **5E3I:** installs the task register and topic files in one selective documentation commit. Its self-hash is not written into that same commit; identify it in Git by report path and commit subject.
- **5E3J–5E3K:** sanitized unpublished local history was pushed normally to `https://github.com/tucotuco/universe.git`; the 5E3K remote `main` was independently confirmed at `a22c284909d7f64c14cad919518f9da319bcf1ed`. On 2026-11-04, U-OPS-001A published 23 descendant commits; the live remote and local `main` are now both verified at `10ba6c85f329ccced15332b24f19faddf9303d85`. Private `ARCHIVE_ROOT/` files are still not GitHub-backed up.

No regression suite was run for this documentation-only adoption. Run `python docs/encounters_adopted_r60/tools/generate_outstanding_todo.py --check` and `python docs/encounters_adopted_r60/tools/update_encounters_toc.py --check` to verify the maintained issue output and ToC.

## Uncommitted local data and current handoff

The following four JSON files are intentionally untracked user data, not cleanup targets:

- `examples/saved/universe-inhabited-scene.json`
- `workspace/ai-encounter.json`
- `workspace/combat-session.json`
- `workspace/universe-planetary-world.json`

The 5E3I seed ZIP is also a local untracked handoff input. It is not part of the seven-file adoption commit. Do not stage or remove it in this task.

## Work-stash and private archives

Keep `work-stash/` tracked and topic-oriented. Verify `work-stash/MANIFEST.tsv` before restoring any snapshot; its contents are unfinished work, not an accepted implementation.

The historical archive is addressed through [`historical-evidence-archive-index.md`](../historical-evidence-archive-index.md). `ARCHIVE_ROOT/` is a portable placeholder for private local storage. Neither those files nor the local commits below imply an off-machine backup.

## Completed operational task: GitHub publication

**U-OPS-006 is complete** for the sanitized history through `a22c284909d7f64c14cad919518f9da319bcf1ed`, as independently verified by 5E3K. U-OPS-001A later published its 23-commit descendant range, and live `origin/main` was confirmed at `10ba6c85f329ccced15332b24f19faddf9303d85` on 2026-11-04. Future pushes still require normal repository/content review and explicit authorization. Private `ARCHIVE_ROOT/` contents remain outside GitHub.

**U-OPS-007 is complete:** the verified Universe 6 → 7 handoff was installed at [`handoffs/universe-6-to-7.md`](../handoffs/universe-6-to-7.md) on 2026-11-04. The original cleanup task U-OPS-002 remains historical and unchanged.

## Safe commits

Use exact explicit paths, review `git diff --cached --name-status`, inspect staged content and require clean whitespace for new documents. Do not use `git add -A` or `commit -a` on this accumulated repository. The task-system adoption commit is authorized for exactly `TASKS.md`, five files in `docs/tasks/`, and its adoption report.
