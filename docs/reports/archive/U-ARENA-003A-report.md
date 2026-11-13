# U-ARENA-003A — Detached six-boundary Arena history

## Result

Implemented the bounded historical-prefix contract. This is portable, validated historical data only: it is not a restored Encounter, native receipt, publisher-authenticated record, checkpoint-readiness claim, or continuation mechanism. U-ARENA-003 remains open/blocked.

## Changes

The implementation commit is `a3bcaf6d926267bc95b079372abc61de3a0837b7` (`Add detached Arena Spot history projection`; tree `556daf9dd861bc548b46ff98b7ddf4e0890b4129`). It contains exactly:

- `src/arena_history_prefix.py` — closed schema `universe.arena.detached-spot-history-prefix/1`, detached immutable values, canonical JSON bytes and SHA-256 consistency, bounded decoding, and strict validation of the single supported six-boundary Ari→Bex Spot case. It preserves the two NPC source records byte-for-byte (base64 in the wire form), their hashes, and explicit native bindings. It captures through native `Encounter.inspect_committed()` under the existing publication coordination lock. Decode validates the claim without importing receipt/publisher authority or constructing an Encounter.
- `examples/arena_history_prefix.py` — completes the native Spot scenario, exports the prefix, starts a fresh Python process to decode it, and displays the historical-only summary.
- `tests/test_arena_history_prefix.py` — canonical detached capture, fresh-process decode, boundaries/references/provenance tampering, unsupported version/effect and failed Spot refusal, and no publisher-registry/RNG/Awareness mutation.
- `TASKS.md`, `docs/tasks/encounter-engine.md`, and `docs/design/Universe-Playground-Revised-Roadmap.md` — mark only U-ARENA-003A complete and keep U-ARENA-003 open/blocked.

The wire contract accepts only boundaries 1–6, with a successful fixed Arena Spot resolving at boundary 6, and the closed Awareness, ActionOutcome and Lifecycle effects produced by that case. Unsupported or inconsistent inputs fail closed. Original publisher receipt authenticity is deliberately not carried: a digest detects inconsistency but does not prove who issued the historical claim. The detached prefix is not added to `Encounter.inspect_committed()` and cannot be used to continue simulation.

## Demonstration

Command:

```sh
PYTHONDONTWRITEBYTECODE=1 python examples/arena_history_prefix.py
```

The fresh process validated boundaries 1–6; the native Ari→Bex Spot at boundary 6 succeeded with roll 20 against DC 15. Ari's Target history contains Awareness of Bex; Bex's does not. Both source records and explicit native Being bindings are shown, including source SHA-256 values `fbbee87dab9b7047b13ee11bb4ad37385779381f60d1dfc3c230afc5251befde` (Ari) and `9da574a288bd4f62832324e30c38426c9e666988628e2989c713db28c8007570` (Bex). The summary labels the data a detached historical claim, not authenticated publisher history.

## Verification

- Focused: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests python -m unittest test_arena_history_prefix test_npc_encounter_arena` — **14 passed**.
- Full suite on an isolated `git archive` export of the starting baseline plus the exact implementation files and required read-only legacy CSV fixtures: `PYTHONDONTWRITEBYTECODE=1 sh run_tests.sh` with loopback permission — **1,721 passed**, 310.440 seconds.
- An initial isolated full-suite attempt without loopback permission ran 1,690 tests and had 16 HTTP setup errors from sandbox `PermissionError` on `127.0.0.1` binds. Re-running with loopback permission passed the full suite. The earlier attempt is an environment limitation, not a product test failure.
- Both adopted revision-60 generated-document checks passed: `generate_outstanding_todo.py --check` and `update_encounters_toc.py --check`.
- Changed Python files compiled; runnable fresh-process example passed; `git diff --check` and the staged diff whitespace check passed.
- Compared SHA-256 values of all **70** tracked documentation files in the isolated export before and after the full suite; all remained unchanged. No test suite was run against or used to repair the active working tree.

## Preservation and final state

Starting state was `main` at `b949f64ffcac604d4249d90c7f85b92a6757058d` with an empty index. Before implementation, the worktree already contained **44 tracked documentation deletions** and extensive untracked user-managed material. Those paths were not staged, restored, removed, or otherwise changed. The previously reported extra deletion of `docs/planetary-two-moon-observations.md` is a user-managed move: its remaining copy at `docs/experiments/world-generation/planetary-two-moon-observations.md` has the identical SHA-256 `76220f9d1506bf2709f6acfbda3275245f1ffce8eef3c5138b865d53f81f6c91`. This increment did not read saved-session JSON or execute legacy code.

The implementation commit changed only the six paths listed above. At report preparation, `main` points to that commit, the index is empty, the 44 pre-existing tracked deletions remain, and 866 pre-existing untracked files remain (plus this report until its documentation-only closeout commit). Nothing was pushed.

## Remaining work for U-ARENA-003

Native Arena restore and continuation remain unsupported. The existing native receipt/reconstruction contracts are narrower and receipt issuance authentication is process-local; existing trusted restoration/continuation applies to a Run-only subset. Arena NPC bindings are also outside the native checkpoint graph. A separate reviewed trusted-local imported-history/inspection-composition contract is needed before any restoration or post-load Action publication. No general persistence or receipt-authentication guarantees are implied here.
