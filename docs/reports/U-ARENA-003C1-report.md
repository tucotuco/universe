# U-ARENA-003C1 — Trusted-local Arena continuation report

## Result

**Completed within the approved fixed scope.** A fresh process accepted the exact host-approved B1/B2 Arena state as local time-6 initial conditions, then published one new native Run Action at boundary 7. The original boundaries 1–6 remain imported claims; no historical native receipt was recreated or installed.

User approval: “Approve exact C1 policy.” The implementation does not generalize that authorization to other scenarios or checkpoint types.

## Implementation

Commit: `a4742321cd8acb509c98a62fe8aa7b9471e8b097` (`Add trusted-local Arena boundary-7 continuation`), parent `4f2eb9f3e3a298638917c6797d16c56a9b8dc3f5`.

Six committed paths:

- `src/arena_state_activation.py` — strict fixed-case revalidation, opaque process-local single-use activation authorization, and composed imported/native inspection.
- `src/arena_state_admission.py` — retains the exact B1/B2 admission inputs with the quarantined native graph and supports one private transfer to activation.
- `examples/arena_trusted_continuation.py` — reproducible uninterrupted Process A versus fresh Process B example.
- `tests/test_arena_state_activation.py` — activation refusal, single-use and mismatch handling, native boundary publication, rollback/retry, and unchanged ordinary-constructor refusal.
- `TASKS.md` and `docs/tasks/encounter-engine.md` — record C1 as complete within scope and keep U-ARENA-003 open.

Activation uses the ordinary `Encounter(start_time=6, time=6)` constructor, preserves Ari/Bex identities, their current physical state and geometry, and Ari-only Awareness, and creates a fresh Encounter/Universe with no imported Actions, Choices, Target histories, or receipts. The new ChoiceBook starts above the accepted historical draft-1 identity. The RNG cursor is newly selected by the host; B2 RNG authority is not transferred. The capability is consumed once and bound to the validated private graph and exact accepted inputs.

The example schedules a genuine `RunAction` through `Encounter.schedule_choice()` and commits it with `Encounter.step()`. Native `inspect_committed()` and receipt history contain boundary 7 only. A separate composed view labels 1–6 `imported/host-accepted claim; original receipt authenticity not established` and boundary 7 `native/publisher-issued in this process`.

## Demonstration

Command, run from the isolated export:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 examples/arena_trusted_continuation.py
```

Observed comparison: uninterrupted native execution and fresh-process continuation match for the supported boundary-7 Action and causal effects, Being identities and positions, HP, Awareness, Target-owned Run practice, NPC source bindings, and composed chronology 1–7. Ari moves from `(0, 0, 0)` to `(1, 0, 0)`; Bex remains at `(3, 0, 0)`. The Run succeeds and records 4 Run experience for Ari, caused by the boundary-7 Run Action. HP remains 10 for each Being. The new Choice ID is `npc-arena/encounter/1/draft/2`.

Process B's fresh RNG cursor is unchanged by this RNG-free Run. This demonstrates neither transfer of old RNG state nor stochastic replay equivalence. Receipt identities are process-local; only the new Process B boundary-7 receipt is authenticated by its native publisher.

## Verification

All final checks were performed against the isolated candidate export at `/private/tmp/u-arena-003c1-y6tnAF`; its required legacy CSV inputs were copied read-only for the tests. No legacy code was executed.

- Focused final activation tests: **6 passed** (`PYTHONPATH=../tests python3 -m unittest test_arena_state_activation`, from the export's `src/`).
- Broader Arena/history/state/checkpoint/Run focused set: **149 passed**.
- Full HTTP-inclusive suite: **1,752 tests passed**. HTTP loopback tests require permission to bind localhost; the sandbox-denied attempt produced environment-only bind errors, then the permitted run passed. One unrelated random exertion assertion failed once in an intermediate run, passed on focused rerun, and the final full rerun passed.
- `py_compile` passed for the four changed Python files.
- Revision-60 generated-document checks passed: `generate_outstanding_todo.py --check` and `update_encounters_toc.py --check`.
- `git diff --check` and an explicit trailing-whitespace scan passed for all six implementation paths. The new test's extra final blank line was removed before commit.
- Staged commit contained exactly the six paths listed above; the index is empty after commit.

The example prints a benign pyenv warning that its global shims directory is not writable; execution completed successfully.

## Preservation and limitations

The checkout was on `main` at `4f2eb9f3e3a298638917c6797d16c56a9b8dc3f5` before the implementation commit. The existing dirty work was preserved: the final status still shows 44 pre-existing tracked deletions and 871 untracked paths, including saved JSON and protected independent material. Only the six explicitly listed paths were committed. Final HEAD is `a4742321cd8acb509c98a62fe8aa7b9471e8b097`; local `main` is ahead of `origin/main` by 20 commits. Nothing was pushed.

This is a fixed trusted-local continuation demonstration, not portable receipt authentication, general checkpoint restore, imported RNG continuation, stochastic replay, or an Arena save/load workflow. Imported claims remain separate from native history. U-ARENA-003 remains **OPEN**.

## Next step

A separate assignment should define the next bounded Arena continuation case before implementation—especially whether another deterministic Action can safely follow this imported-prefix/new-native-boundary model. General persistence or historical receipt authentication would require separate design and authorization.
