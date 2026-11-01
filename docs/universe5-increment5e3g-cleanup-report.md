# Universe 5 Increment 5E3G — Cleanup report

## Result

The bounded cleanup completed without changing committed source behavior. The repository remains on `main` at HEAD `03c5e9a874c88ac21686b0c0da58d24a736a4cd4` (tree `1d76b052b7a8dc6ec04e050db5bcd1981591f922`); the real index is empty. Nothing was staged, committed, pushed, or deleted outside the individually listed cleanup actions.

## Preservation and cleanup

- The 5E3B private recovery tarball SHA-256 matched its recorded value (`a68edde94e2db88b0bfa178fe2463c1b414f603c392356d0fb0fa7c510c68124`). Its 549 checksum-listed files verified. The previously archived-artifact manifest still contains 88 verified entries.
- The fresh 5E3G pre-cleanup archive matched SHA-256 `80dabb46082d7ff33e030bf136b1a58d173bb63ddebbef65416d3971ba6f24a5`. All 463 dirty paths, their bytes, and modes matched that snapshot before cleanup.
- All 78 interrupted-work originals matched `work-stash/MANIFEST.tsv` by content and mode; each committed snapshot blob and mode also matched the manifest. The 70,961-byte residual patch matched SHA-256 `f183cfb4d8ddaced35122872caee1b1d57cec46ffdc9181ef218842cc57a1f4c`.
- Eleven tracked modified paths were atomically restored to exact HEAD content and mode; the twelfth was already restored during the same verified operation. Their former contents remain in the committed work-stash and external 5E3G snapshot.
- Sixty-two redundant untracked interrupted-work originals were removed after hash, mode, snapshot, and dependency checks. Four saved-data paths remain in place: `examples/saved/universe-inhabited-scene.json` and the three `workspace/*.json` files.
- Of 92 still-present historical artifacts in the 5E3B inventory, 70 had no path or basename reference in other documentation. All 92 were copied byte-for-byte into the private external archive with original relative paths and modes. Seventy unreferenced repository copies were removed after verification; the other 22 referenced artifacts remain in the repository and also have external copies to keep the archived set coherent. Historic evidence paths classified `NEEDS_REVIEW` (266 inventory entries) and all active/required material were left untouched.

The updated external inventory is `ARCHIVE_ROOT/5e3g-before-cleanup/ARCHIVE_INVENTORY.tsv`. The new historical archive includes `ARCHIVE_ROOT/5e3g-before-cleanup/historical-artifacts/MANIFEST.tsv` and a restoration index. Its portable locator prefix is `ARCHIVE_ROOT/5e3g-before-cleanup/historical-artifacts/payload/`.

The complete before-path action log is [universe5-increment5e3g-cleanup-actions.tsv](universe5-increment5e3g-cleanup-actions.tsv). It has 463 rows, one per pre-cleanup dirty path, and records prior status, action, source hash, preservation locator, resulting hash, and reason.

## Verification

- Full regression ran from a fresh `git archive HEAD` export at a temporary `git archive HEAD` export, from its `tests/` directory with `PYTHONPATH=../src` and loopback enabled: **1,573 tests passed** (`Ran 1573 tests in 246.038s`, `OK`). The first sandboxed attempt could not bind loopback and produced HTTP setup errors; the authorized loopback-enabled rerun passed.
- `git diff --check` passed after tracked restorations. The working-tree tracked diff is empty.
- Branch, HEAD, tree, and empty index match the required baseline. The 5E3G before-snapshot remains intact and verified.
- After adding this report, the expected working-tree status is 321 untracked paths: the 319 retained pre-existing paths plus the two 5E3G deliverables. There are no modified tracked files.

## Remaining paths and next action

The retained paths fall into five bounded groups: 266 historical evidence entries marked `NEEDS_REVIEW`; 22 referenced historical artifacts; 17 active/required paths (including adopted revision-60 material and maintained source/tests/examples); 10 newer handoffs or reports absent from the 5E3B manifest; and four saved example/workspace data files. Their exact paths and disposition are in the action TSV. They were retained because they are linked, active, newer, or user data rather than redundant interrupted originals.

The shortest remaining cleanup is a single grouped review of the 266 evidence entries and 22 linked reports, retaining any referenced evidence and archiving only complete, unreferenced groups. The 17 active files, ten newer handoffs/reports, and four saved-data files should remain available for the planned `TASKS.md` adoption decision. No further cleanup was performed here.

No Git commit is proposed in this increment; the source tree is already clean relative to HEAD, while the remaining untracked material needs the review above. `TASKS.md` and family-relationship work were not started.


The archive locators above use the portable `ARCHIVE_ROOT/` convention. Increment 5E3H records the subsequent final disposition; the path/status rows above remain a point-in-time record of 5E3G.
