# U-REPO-013 — reference-only geography files and handoff

## Result

The user-requested `docs/assignments/U-REPO-013.md` was not present. I executed the only installed version, `docs/assignments/U-REPO-013-corrected.md`, without copying or staging that untracked input. Four externally gathered references were copied byte-for-byte to ignored `legacy/geography-references/`; after exact hash/mode and ignore checks, their tracked `src/` paths were removed. `src/continent.py` was classified as uncertain and retained.

## Candidate classification and integrity

All source files were regular files, mode `0644`, and tracked before this task. The new destination paths were absent, and no same-basename copies were found under `legacy/`. The four legacy destinations are ignored by the existing `/legacy/` rule, absent from the Git index, and not staged. For every moved file, source and destination bytes, SHA-256, and mode matched before source removal.

| Candidate | Status | Bytes | Source SHA-256 | Destination SHA-256 | Git / rationale |
|---|---|---:|---|---|---|
| `src/AM_Kastrisios_Voronoi_Python.py` | Moved to `legacy/geography-references/AM_Kastrisios_Voronoi_Python.py` | 7,440 | `53b5adb27e99e8345484d59df323a8130569f72f9a09875060e24473f0dd6286` | `53b5adb27e99e8345484d59df323a8130569f72f9a09875060e24473f0dd6286` | Source deletion staged; destination ignored/untracked. Header identifies the maritime-boundary project and author. It uses ArcPy, Python 2 syntax, and an absent `Voronoi_Ellipsoid_lib`; no active Universe consumer was found. No license statement was present in the inspected header. |
| `src/world_builder_fp.py` | Moved to `legacy/geography-references/world_builder_fp.py` | 16,434 | `8384b57f912fdfd0a914d4b3e74450a456fe4ab7603e242dc0c3f01ed42e2062` | `8384b57f912fdfd0a914d4b3e74450a456fe4ab7603e242dc0c3f01ed42e2062` | Source deletion staged; destination ignored/untracked. Standalone NumPy/Matplotlib prototype, no active imports or tests. `world_map.png` appears only as this script's default generated output filename, not an input asset. No attribution or license statement was present. |
| `src/ModernApolloNavigator.py` | Moved to `legacy/geography-references/ModernApolloNavigator.py` | 1,223 | `9127d6d9980a9ec7d984faff5a3b9d7f305898d6e3618d91a2ee81adcb6a1499` | `9127d6d9980a9ec7d984faff5a3b9d7f305898d6e3618d91a2ee81adcb6a1499` | Source deletion staged; destination ignored/untracked. Standalone NumPy/SciPy class; its header cites an external article. No active imports or tests were found. No license statement was present. |
| `src/world_map.png` | Moved to `legacy/geography-references/world_map.png` | 621,694 | `c57bbadc3a28226df7d66f9f9fe3a12a37f7fc4f623ce1ec0b155feac11f8a81` | `c57bbadc3a28226df7d66f9f9fe3a12a37f7fc4f623ce1ec0b155feac11f8a81` | Source deletion staged; destination ignored/untracked. No active source, test, example, or documentation input reference was found. The only same-name use was the archived builder's output default. PNG text metadata has only a `Software` key, with no source, author, or license key. |
| `src/continent.py` | Retained in `src/` | 4,090 | `e2f1843bc5b1ddb53f97c56ad04229eab3bcbfb3f103bc0777b1a42ae291a8ca` | — | Still tracked; no destination. No active imports or tests were found, but it is self-contained Universe-relevant Voronoi/continent generation code, has no source attribution or license note, and entered history in the same undifferentiated development snapshot as the other candidates. Its provenance and intended status cannot be established, so removal would be speculative. |

The four moved files first appear in the same general development snapshot, which does not establish authorship or rights. Existing attribution comments were preserved locally. The new copies remain strictly local and are not included in the commit or push. Removing tracked source paths does not erase their already-published historical versions.

## Dependency and reference check

Searched active `src/`, `examples/`, `tests/`, `tools/`, current documentation, and task state for the four module/image names, the ArcGIS helper name, and `continent` imports. No active import, dynamic load, invocation, source-asset read, or maintained link depended on the moved files. The builder's output filename was not a consumer of the PNG. No maintained references needed updating. A post-removal `rg` import/reference check returned no hits in `src/`, `examples/`, `tests/`, or `tools/`.

## Verification

All commands used the existing `.venv` with `-B`, `PYTHONDONTWRITEBYTECODE=1`, and `PYTHONNOUSERSITE=1`; no environment installation or rebuild occurred.

| Command | Result |
|---|---:|
| `PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest test_npcgen_being_integration test_npcgen_arena_adapter` | 9 passed (0.956 s unittest time) |
| `PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest test_arena_initialization test_arena_complete_profiles_and_kits` | 15 passed (3.668 s) |
| `PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest test_npc_encounter_arena_web -v` | 4 passed (5.448 s); local listener bound normally; no import-order shim |
| `PYTHONPATH=src:examples .venv/bin/python -B -c 'import arena_web, npc_encounter_arena, arena_npc_import, encounter, being'` | All active Arena/native imports succeeded |
| `rg -n -i 'AM_Kastrisios_Voronoi_Python|world_builder_fp|ModernApolloNavigator|world_map\.png|Voronoi_Ellipsoid_lib' src examples tests tools` | No matches |
| `git diff --check` | Passed |

No full suite or real-browser smoke was run for this reference cleanup. U-REPO-012's report records its separate 59-test focused baseline. `docs/*.md` remains empty. `docs/ideas/inbox/` and `docs/assignments/U-ARENA-018B.md` are absent; no idea was processed and no replacement assignment was invented. `TASKS.md` was left unchanged because this local reference cleanup does not change an Arena milestone or task status.

## Git, local resources, and publication

Before the U-REPO-013 closeout commit, local HEAD was `48848bf835e6ef433582336aeea09fb5eba58cc6` on `main`, tracking `origin/main`; the live remote was the public `tucotuco/universe` repository, default branch `main`, at `d59bc7d495e5d4fbd3ccbe43f8e65296d63bf2af`. That live tip was an ancestor of local HEAD. The six preexisting untracked assignment/report inputs remained unstaged. Existing ignored `legacy/`, four saved JSON files, and `.venv` remain outside Git.

The six-file closeout set passed `git diff --cached --check` and `.venv/bin/python -B tools/check_publication_safety.py --staged` (`staged-audit files=6 findings=0 result=PASS`). The exact outgoing range `d59bc7d495e5d4fbd3ccbe43f8e65296d63bf2af..52cdfaba9bf99d1d52c116f5728a43b3b165f590` passed the history audit (`commits=4 blobs=36 large-blobs=0 findings=0 result=PASS`). `git push origin main` published `52cdfaba9bf99d1d52c116f5728a43b3b165f590` by ordinary fast-forward; a subsequent independent `git ls-remote origin refs/heads/main` returned the same SHA. Git could not update the local `refs/remotes/origin/main` because sandbox access to its lock file was denied; the remote publication itself succeeded, and the live remote was verified independently. No force push, history rewrite, or backup modification occurred.
