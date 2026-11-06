# U-THROW-005 — Independent native Run during projectile flight

## Outcome

The native Throw flight and an independent native `RunAction` now execute together in one committed interval without changes to the shared transaction machinery. The example keeps `examples/native_throw_arena.py` unchanged and adds an opt-in integration scene at `examples/native_throw_concurrent_run.py`.

The added Runner has a stable native identity and an explicitly authored initial position `(100, 0, 0) m`. A native one-second Run begins at t=4; the ordinary Encounter movement input supplies `1.25 m/s` over `[4, 5]`. The Runner and projectile have separate roles. The Run causes only its own movement/practice consequences; the projectile's committed flight state remains caused by the Throw release effect at t=4.

## Committed chronology

The runnable example reports developer inspection of authoritative committed state, not Agent perception. Its actual output is:

| Boundary | Projectile position (m) | Range (yd) | Projectile state | Runner position (m) | Action result | Receipt |
|---:|---|---:|---|---|---|---|
| 4 | `(0, 0, 1.7526)` | `0.000000` | in flight | `(100, 0, 0)` | Throw released | boundary 4; Throw Action and release effects |
| 5 | `(10.936693365293, 0, 7.689293365293)` | `11.960513` | in flight | `(101.25, 0, 0)` | Run success | boundary 5; Run Action, practice and lifecycle effects |
| 6 | `(21.873386730586, 0, 3.625986730586)` | `23.921027` | in flight | `(101.25, 0, 0)` | no due Action | boundary 6; no Action effects |
| 7 | `(25.562401076005166, 0, 0)` | `27.955382` | landed | `(101.25, 0, 0)` | no due Action | boundary 7; no Action effects |

The analytical reference uses the existing exact fixture (Strength 10, Throw 1, 69-inch stature, 1-lb Object, four-second preparation, 45° elevation, 0° azimuth, and `g=10 m/s²`). It predicts impact at `6.337306187730018 s`; the Object remains airborne at t=6 and lands at t=7 with that same fractional impact metadata. The t=5 position matches the existing pure trajectory projection. RNG is unchanged. Neither the thrower nor Runner moves except for the explicitly supplied Runner movement during `[4,5]`.

Boundary 5's single native receipt names the Run Action. Its effect identities belong to the Run; the projectile state carries the original t=4 Throw release-effect identity. There are no synthetic per-boundary Throw Actions or flight effects attributed to the Run. Target inspection shows the Run practice contribution belongs to the Runner and occurs once at boundary 5.

## Read-only, rollback and compatibility checks

- Repeated `inspect_committed(4)` calls left projectile flight state, prior Target history, RNG, Action result and receipt list unchanged. The detached t=4 inspection remained stable after t=5–7 committed.
- Injecting publication failure after the boundary-5 Target write phase rolled back both ordinary movement and projectile flight, Target histories, Run practice/Action completion, queues, RNG and the committed-receipt registry. Explicit recovery followed by retry committed the same t=5 result.
- A competing Throw using the same Object during the original preparation reservation was refused before registration.
- A separate ordinary Encounter without Throw still resolves a normal Run and awards its existing scenario-authored practice.
- No shared transaction defect was found; production transaction code was not changed.

## Changed files and commit

Implementation commit: `35a7331` (`Demonstrate Run during projectile flight`):

- `examples/native_throw_concurrent_run.py`
- `tests/test_native_throw_concurrent_run.py`
- `TASKS.md`
- `docs/tasks/encounter-engine.md`

This report is committed separately. No push was performed.

## Verification

- New integration tests: **4 passed** (`test_native_throw_concurrent_run`).
- Focused integration/regression selection: **352 passed** in 95.363 seconds. Command, run from `tests/`:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=../src:. python -m unittest -q test_native_throw_concurrent_run test_native_throw_arena test_throwing test_action_evaluation test_action_settlement test_action_choices test_interval_staging test_atomic_publication test_encounter_inspection test_melee_combat test_npc_being_arena`
- Runnable example: `PYTHONDONTWRITEBYTECODE=1 python examples/native_throw_concurrent_run.py` — completed and printed the chronology above.
- Python compilation passed for the new example and test module.
- `git diff --check` passed.
- One full discovery attempt, run from `tests/` with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=../src:. python -m unittest discover -q`, completed in 381.390 seconds: **1,759 tests, 1,591 passing, 43 failures, 125 errors**. The full suite is not green in this checkout. Diagnostics included HTTP test server setup denied from binding `127.0.0.1` (`PermissionError: Operation not permitted`) and checkpoint tests unable to read `docs/universe4-authoritative-decisions-2026-10-27.md`, which is a pre-existing tracked deletion in the current user-managed documentation migration; the replacement material is in the separate untracked `docs/encounters/` tree. Other suite failures were not exhaustively classified because the full output exceeded the execution display limit. The focused changed-path and cross-cutting regressions passed.

## Repository preservation and remaining limits

The branch is `main`; this task added two commits beyond the prior U-THROW-004 closeout. The pre-existing tracked deletions and untracked paths—including `.agents/`, `.claude/`, `docs/assignments/`, `docs/encounters/`, `legacy/`, saved examples, and workspace JSON—were not staged or altered. Only the four implementation/status paths above and this report were committed.

This remains the bounded drag-free point-mass Throw fixture. It adds no collision, interception, hit/damage, broader Throw brackets, perception claims, or checkpoint support. Projectile state is authoritative only after the native interval publisher commits it.
