# U-ARENA-003C3 — Fixed S6→S7→boundary-8 continuation

## Result

**Implemented after approval of the exact S7 trusted-local admission policy.** The fixed Arena now supports two distinct, non-overwriting local files and three fresh processes:

1. Process A commits Ari's native Spot at boundary 6 and writes the existing S6 B1/B2 bundle.
2. Process B requires the existing S6 host-approval flag, commits one native Ari Run at boundary 7, and writes a new S7 claim to a second host-configured path.
3. Process C requires the separate `--approve-local-s7-checkpoint` flag, reconstructs the reviewed post-boundary-7 state as local initial conditions, accepts one native Ari Run, and publishes boundary 8.

The S7 object is a closed, versioned data claim, not a receipt or cryptographic attestation. Its trust label says so. Boundaries 1–7 appear as `imported/host-accepted claim; original receipt authenticity not established`; Process C's only native receipt and inspection boundary is 8. No previous publisher registry, native historical Action/Choice, Target receipt record, or RNG authority is imported.

## Implementation

- `src/arena_s7_checkpoint.py` defines `universe.arena.local-s7-claim/1`, canonical encoding, strict field/digest/base-S6 validation, native boundary-7 capture checks, and the exact fixed Run/effect/practice/Target claim. Capture refuses stale/unreceipted live state, unsupported Action or ChoiceBook state, and a non-quiescent boundary.
- `src/arena_local_checkpoint.py` validates S6 and S7 bundles at the local-file boundary and retains the existing atomic mode-0600/no-overwrite writer. The S6 schema and admission path remain intact.
- `src/arena_state_activation.py` binds a distinct one-use S7 authorization to the already validated S6/B1/B2 state and exact S7 view. While the B3 native Beings are still quarantined, it reconstructs Ari's verified boundary-7 position and one Target-owned `BatchSkillUse` (4 Run XP, caused by `run-ari-boundary-7`). It then constructs a normal fresh Encounter at `start_time=time=7`, initializes the ChoiceBook counter floor at 2, and uses a new host-selected RNG seed. It does not replay Run7 or install its historical receipt/Target records.
- `examples/arena_web.py` allows Process B to save S7 only after the native boundary-7 Run commits. `examples/npc_encounter_arena_web.py` keeps S6 and S7 approvals separate and host-selected; S7 uses `--approve-local-s7-checkpoint`. The browser displays the imported/native chronology in its developer view while observer endpoints remain Awareness-only.
- `tests/test_arena_s7_checkpoint.py` covers the closed S7 data contract, altered claims, stale/practice mismatch, open scheduling state, failed atomic write with retry, separate S7 approval, and the complete three-process browser flow.

The imported Run practice is initialized once as Being state and remains visible to frozen-practice evaluation. The next native Run awards a separate 4 XP transition with its own Action/effect provenance, producing 8 Run XP total without replaying or duplicating the first award. Imported Target histories remain detached claims; native inspection at boundary 8 contains only Process C's new interval.

## Reproduction commands

Choose two distinct absolute destinations in an existing directory outside the repository. Do not reuse a destination; writes refuse overwrite.

```sh
# Process A: run fixed Spot, advance six one-second boundaries, save S6 in the browser.
PYTHONDONTWRITEBYTECODE=1 python3 examples/npc_encounter_arena_web.py \
  --port 8000 --save-path /absolute/local/path/arena-s6.bundle

# Process B: after stopping A, approve S6, commit Run at boundary 7, then save S7.
PYTHONDONTWRITEBYTECODE=1 python3 examples/npc_encounter_arena_web.py \
  --port 8000 --resume-from /absolute/local/path/arena-s6.bundle \
  --approve-local-checkpoint --rng-seed 90210 \
  --save-path /absolute/local/path/arena-s7.bundle

# Process C: after stopping B, use the separate S7 approval, commit boundary 8.
PYTHONDONTWRITEBYTECODE=1 python3 examples/npc_encounter_arena_web.py \
  --port 8000 --resume-from /absolute/local/path/arena-s7.bundle \
  --approve-local-s7-checkpoint --rng-seed 123456
```

In Process A, submit the allowlisted Spot and advance six seconds before saving. In Process B, submit the allowlisted Run and advance once before saving. In Process C, submit one Run and advance once. The HTTP API does not accept caller-selected paths, Action IDs, or arbitrary Actions.

## Verification

Tests ran against an isolated export of the candidate from the checked-out baseline, with only the existing read-only `legacy/src/data/offspring_*_wlist.csv` test fixtures copied. No legacy program was executed. The working checkout was not used as the suite's import source.

- Focused C2/C3 checkpoint and loopback tests on the final source: **7 passed**. An earlier focused run included two tests before the final removal of an unused generic activation dispatcher; the complete final suite below ran after that removal.
- Final full HTTP-inclusive regression: **1761 tests passed** (`unittest discover`, `OK`).
- Earlier full attempt: **1760 tests, one failure** because an existing C2 refusal test matched the old S6 approval diagnostic exactly. The CLI diagnostic was restored for S6, preserving the new separate S7 error, and the focused tests plus final full run passed.
- `py_compile` passed for the six changed Python files.
- Adopted-r60 generated TODO and TOC checks passed.
- `git diff --check` passed.
- S7 integration verified an actual three-process HTTP stop/restart sequence; S6 bytes and digest stayed unchanged. Process C began at time 7 with empty native receipt/inspection histories, Ari at x=1 with 4 Run XP, and imported boundaries 1–7. It did not commit boundary 8 before the native Run Choice was advanced. After publication, Process C held only a native boundary-8 receipt; Ari was at x=2 with 8 total Run XP, and Target practice contained exactly one causal contribution at times 7 and 8. Bex remained at x=3 with unchanged HP and no Awareness. The result matched uninterrupted native Spot→Run7→Run8 for Action/Choice/effect identities, outcome/metadata, position, HP, Awareness, practice and source bindings.

The deterministic Run consumed no RNG. Process C used a new host-selected RNG cursor and that cursor remained unchanged; no cross-process RNG transfer or stochastic replay is claimed.

## Commits and preservation

- Starting branch/HEAD: `main` / `f712568483ad6ee454d3720544069bb41bd4fc9c`; index was empty.
- Implementation commit: `e4c7fde674ffdf538e060644e0bb67818576a69e` (`Add fixed Arena S7 continuation`).
- This report is committed in a separate documentation-only closeout commit after the implementation commit; the final HEAD is reported in the completion summary.
- No push was performed.
- The pre-existing 44 tracked documentation deletions and 18 untracked entries (including `.agents/`, `.claude/`, local JSON, `legacy/`, and the independent project/archive material) were preserved. Only the explicitly listed C3 implementation, tests, task-status files and this report were staged/committed.

## Limits and remaining scope

This remains an exact Ari/Bex fixture, two fixed Run declarations, local trusted-host policy, and deterministic continuation demonstration. S7 digest checking detects changed bytes but does not authenticate who issued an earlier receipt. The S7 host must independently approve the exact claim. Native receipt authenticity, general checkpoint readiness, arbitrary Encounter save/load, historical receipt installation, RNG restoration, stochastic replay, a generalized Action/state schema, and U-ARENA-003's broader acceptance criteria remain out of scope. U-ARENA-003 remains **OPEN**.
