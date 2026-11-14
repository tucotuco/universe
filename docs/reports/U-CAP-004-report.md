# U-CAP-004 — Targeted ranged combat

**Status:** ACTIVE; acceptance criteria remain incomplete. This report is the live implementation record and has not been consumed or archived.

## Execution interval

- Start time: 2026-11-13T18:48:00-08:00 (America/Los_Angeles; captured at execution start)
- End time: pending closeout
- Elapsed time: pending closeout

## Current verified progress

- Preserved the previously committed projectile full-precision boundary fix. The staged-flight invariant checks identity and exact preceding position before advancing.
- Corrected generated npcgen Being release-height lookup to use the generated source's measured stature (`length`) when its static height field is zero; the settlement validator uses the same source facts.
- Extended strict native checkpoint inventory and Arena snapshot tags for pending `ThrowAction`, `ProjectileFlight`, `ProjectileBoundaryState`, and release effects. The snapshot schema is now `/3`; full-precision spatial state is admitted only for Objects carrying the exact reviewed `ProjectileFlight` type.
- Added a fresh-process regression using deterministic generated Arena seed 5051. It saves a scheduled Throw, loads in a `python -S` process, commits launch/flight boundaries, saves again, and verifies exact Object identity, pending event type, flight descriptor, boundary history and RNG continuation after another fresh load.
- Verified command:

  ```text
  PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_native_throw_arena tests.test_native_throw_concurrent_run tests.test_native_throw_spot tests.test_arena_persistence.TestArenaPersistence.test_generated_throw_pending_and_in_flight_survive_fresh_process
  ```

  Result: 17 tests passed in 31.927 seconds.

## Acceptance status

| Criterion | Current status |
|---|---|
| A. Targeted Throw, flight, hit/miss, custody and persistence | Partial: full-precision untargeted flight and fresh-process pending/airborne state pass; target selection and arrival resolution remain to implement. |
| B. Shoot and ranged Coup de grace | Not implemented; authoritative bow projectile speed/flight facts remain absent, so no surrogate physics will be introduced. |
| C. Deflect, missing, obstruction and simultaneous encounters | Not implemented. Adopted miss direction is known, but destination distance remains explicitly unresolved. Whole-flight awareness is not yet represented as evidence. |
| D. Generated Arena and vertical slice | Not implemented. Existing generated Arena still reports Throw unavailable; no targeted hit/miss UI or actual generated Arena demonstration yet. |

## Rules and implementation limits

- User adopted attack-roll-at-arrival for targeted Throw: on successful roll, apply damage when the projectile reaches the target's represented position without adding body geometry; on failure, record the adopted d8 direction and an explicit unresolved destination. This supports a bounded game-level hit decision, not a claim of modeled body collision.
- Existing explicit `uncertain_path` decisions remain fail-closed. Do not weaken checkpoint fingerprints, infer generated Being geometry, or invent a miss distance, body shape, bow projectile speed, or flight time.
- Current native Throw remains limited to its authored Strength-10, <=3.3 lb, four-second preparation bracket. No hit or miss has yet been demonstrated.

## Git evidence

- Base HEAD at assignment start: `103e29c37c06d893f3163bf9dbbbfe42938aba21`.
- Startup reconciliation/archive commit: `c62b05c` (archives accepted U-CAP-003 and installs U-CAP-004 state; exact full hash to be recorded at closeout).
- Projectile precision fix: `0c5f1efc8b953429c3e4e4f81a1b07280e4a6de4`.
- Foundation cohort currently described above is not committed yet; closeout will record its exact commit and final status.
- Preexisting staged archival moves for U-CAP-002 and U-THROW-001 are intentionally preserved and excluded from U-CAP-004 commits. No push performed.
