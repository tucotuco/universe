# U-ARENA-003C2 — Fixed Arena save, reopen, and native continuation

## Result and commits

**Completed within the fixed C2 scope.** The loopback Arena now offers a local operator save after a successful native Ari→Bex Spot commits at boundary 6. A fresh process can reopen only after a separate affirmative host-approval flag and then accept one native Ari Run +X Choice for boundary 7.

- Initial checkout: `main` at `40d551fd031515dc7225728d915f45da4291d489` (C1 report-closeout commit); index empty.
- Implementation: `126c26bad00ef7edde546c505e004b2cd757a807`, parent `40d551fd031515dc7225728d915f45da4291d489`, subject `Add fixed Arena local save and reopen flow`.
- The report is committed separately as `Document Arena save/reopen increment` (its commit ID is the final HEAD; the report does not embed its own hash).

The implementation commit contains exactly six paths: `src/arena_local_checkpoint.py`, `examples/arena_web.py`, `examples/npc_encounter_arena_web.py`, `tests/test_arena_local_checkpoint.py`, `TASKS.md`, and `docs/tasks/encounter-engine.md`.

## Operator workflow

Choose an absolute destination in an existing directory **outside the repository**, and ensure the file does not already exist. Process A:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 examples/npc_encounter_arena_web.py \
  --port 8000 --save-path /absolute/local/path/arena.bundle
```

In the browser, submit Ari→Bex Spot, advance six one-second native boundaries, and use **Save supported Arena state**. Save is enabled only after a successful boundary-6 Spot and quiescent finished Choice. Stop the process with Ctrl-C.

Process B, after the stop:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 examples/npc_encounter_arena_web.py \
  --port 8000 --resume-from /absolute/local/path/arena.bundle \
  --approve-local-checkpoint --rng-seed 90210
```

The approval flag and new RNG seed are separate explicit host inputs. The resumed page shows imported boundaries 1–6 as host-accepted claims. Submit **Ari Run +X** once, then advance one second to publish boundary 7. The loopback interface has no upload, caller-selected file path, caller-selected Entity/Action ID, or general Action builder.

Reproduce the end-to-end stop/restart/browser flow with:

```sh
cd /private/tmp/u-arena-003c2.kKyhCE/src
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=../tests \
  python3 -m unittest test_arena_local_checkpoint.ArenaOperatorHTTPContinuationTests
```

## Implementation and authority boundaries

`src/arena_local_checkpoint.py` wraps the **unchanged** B1 history-prefix and B2 state-candidate wire formats in `universe.arena.operator-bundle/1`. The outer envelope is canonical, closed-field, digest-checked, and limited to 16 MiB. It stores the exact B1/B2 bytes and their association; their existing records retain NPC source bytes, hashes, and explicit bindings. It adds no second checkpoint schema for native fields.

The browser writes only to the host-configured destination, outside the repository. The file is created atomically through a same-directory temporary file and no-replace link, uses mode `0600`, and is never overwritten. Refused or injected failed writes leave no partial destination/temp file. The HTTP save request must be `{}`; paths are never accepted from the browser.

At startup, `--resume-from` without `--approve-local-checkpoint` is refused before serving. With approval, C2 revalidates the exact fixed Ari/Bex NPC fixture bytes and binding expectations, then reuses the existing B1 history approval, B3 quarantined Being admission, and C1 one-shot activation gates. No Arena session is returned on malformed/tampered/mismatched data. The process uses the host-selected seed to create a new RNG cursor; it does not restore the old cursor.

Before boundary 7, native receipt and inspection timelines in the resumed Encounter are empty. The separate browser GM chronology shows boundaries 1–6 as `imported/host-accepted claim; original receipt authenticity not established`. The existing native `Encounter.schedule_choice()`/`Encounter.step()` path publishes the Run. Afterward, only boundary 7 appears in native inspection and publisher receipt history, labeled `native/publisher-issued in this process`. Owner-filtered Ari/Bex views continue to use Awareness and disclose no coordinates. GM Reality remains visibly separate from those observer views.

## Demonstrated continuation

The two-process HTTP test verifies Process A’s browser Spot, six native advances, boundary-6 save, process termination, refusal to start Process B without approval, then successful approved startup. It inspects the imported chronology, submits one Run Choice, verifies no boundary-7 commit before advance, and commits boundary 7 through the browser.

The resumed result matches an uninterrupted native Arena for the supported case: Ari/Bex identities and source hashes, boundary-7 Run Action and Choice identities, causal effect identities, outcome/metadata, positions, HP, observer Awareness, and Ari’s Target-owned 4 Run practice XP. Ari moves to `(1,0,0)`; Bex remains at `(3,0,0)`. The new Choice is `npc-arena/encounter/1/draft/2` after the historical draft-1 identity fence.

This deterministic Run consumes no RNG. The result does **not** demonstrate old RNG transfer or stochastic replay. Imported boundaries remain local-host-accepted claims, not authenticated historical receipts. The native publisher authenticates only the new boundary-7 receipt in Process B.

## Verification

Tests and checks ran on a clean isolated Git export at `/private/tmp/u-arena-003c2.kKyhCE`, based on initial HEAD `40d551fd031515dc7225728d915f45da4291d489`, overlaid with the six scoped implementation/task paths. Sixteen `legacy/src/data/offspring_*_wlist.csv` files were copied read-only into the export as required test fixtures; no legacy program was executed. The current dirty working tree and real index were not used as the test source.

- Final focused C2 and existing Arena browser regressions: **8 passed** (`test_arena_local_checkpoint`, `test_npc_encounter_arena_web`; HTTP loopback enabled).
- Broader Arena/history/state/checkpoint/Spot/Run focused set: **80 passed** before the final extra comparison/refusal assertions; the final full suite below includes the final assertions.
- Final complete HTTP-inclusive regression: **1,756 tests passed**, `OK` (`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=../tests python3 -m unittest discover -s ../tests -p 'test_*.py'`, from the export’s `src/`).
- `py_compile` passed for all four changed Python files.
- Revision-60 generated checks passed: `generate_outstanding_todo.py --check` and `update_encounters_toc.py --check`.
- All six scoped paths passed trailing-whitespace/final-newline checks; the implementation staged diff passed `git diff --cached --check` and contained exactly six paths.
- No incidental `test_exertion` failure occurred in the final suite. Python emitted existing HTTP `ResourceWarning`s and expected “Ojo” diagnostic text after the suite; the test result was successful.

## Repository preservation and limits

No push was performed. Final `main` is at the report-closeout commit, 23 commits ahead of `origin/main`, with an empty index. The pre-existing 44 tracked documentation deletions and untracked user-managed material remain in place; this increment did not restore or stage them. `legacy/`, independent projects, `.agents/`, `.claude/`, `examples/saved/`, and `workspace/*.json` were not modified. Only the six implementation paths and this report were committed.

This workflow is intentionally fixed to the successful Ari/Bex boundary-6 Spot fixture and one deterministic Run. It is not general Universe persistence, portable checkpoint readiness, arbitrary scenario restore, historical receipt authentication, old-RNG continuation, stochastic replay, or a remote/login-secured UI. Local host approval expresses application trust; it is not cryptographic authentication or protection against a malicious process with local filesystem access. U-ARENA-003 remains **OPEN**.
