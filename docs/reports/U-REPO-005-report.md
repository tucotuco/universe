# U-REPO-005 — Bounded regression triage

## Checkout and scope

At triage start: branch `main`, HEAD `3d8b2f305e32a19aae489a99c1eb70aaff9eb907`, upstream `origin/main`, 54 commits ahead / 0 behind, empty index. Existing tracked deletions and untracked paths were left untouched. No production, test, or rule files were edited. This report is an untracked closeout artifact.

## Discovery and prerequisites

Discovery-only inventory used `PYTHONPATH=src:tests` with `unittest.TestLoader().discover('tests')`: **1,797 test IDs across 185 test modules; 0 discovery import errors**. The first exploratory discovery from `.` without project import paths produced five import errors; this was a discovery invocation issue (`src` and `tests` were absent from `sys.path`), not the configured inventory. The correctly configured discovery is the result reported above. It does not execute tests.

Repaired prerequisite: `PYTHONPATH=src:tests python -m unittest test_checkpoint_inventory` — **30 passed**, 12.771 s test time (13.206 s elapsed).

Encounter package checks both passed:

- `python docs/encounters/tools/generate_outstanding_todo.py --check` — `Outstanding to-do current`.
- `python docs/encounters/tools/update_encounters_toc.py --check docs/encounters/encounters-working-draft-adopted-r61.md` — `TOC current`.

## Bounded cohorts

| Cohort and purpose | Command | Outcome |
|---|---|---|
| Transactional Action, shared snapshots, atomic publication | `PYTHONPATH=src:tests python -m unittest test_atomic_publication test_interval_staging test_shared_objective_reality` (repository root) | **169 passed**, 56.589 s test time (57.02 s elapsed). |
| Physical work, fatigue and exertion | `python -m unittest test_native_physical_work test_native_physical_fatigue test_exertion` (run from `tests/`) | **43 passed**, 0.160 s test time (0.396 s elapsed). |
| Group-member and statistical reproduction realization | `PYTHONPATH=src:tests python -m unittest test_group_member_realization_candidate test_reproduction_generation test_reproduction_group_publication test_transactional_group_member_realization` (repository root) | **37 passed**, 7.409 s test time (7.75 s elapsed). |

### Classified invocation failure

The physical-work cohort was initially invoked from the repository root. That invocation produced **26 errors** because these tests construct `Library(config_dir='../src/config')`; from the root this resolves outside the repository, leaves the Being dictionary unset, and `Universe.make_being()` raises `AttributeError: 'NoneType' object has no attribute 'get_object_definition'`. The smallest reproducer was `PYTHONPATH=src:tests python -m unittest test_native_physical_work.TestNativeWorkContract.test_declared_overlap_cannot_be_summed_or_doubled`: it errors during fixture setup, before exercising the assertion. Running the same cohort with the test directory as current working directory resolves the relative config path and all 43 tests pass. Classification: **checkout/test-invocation-dependent fixture path**, not a demonstrated application defect. No files or fixtures were moved or copied.

Total successful focused tests (including the checkpoint module and three corrected cohorts): **279**. This is a sample, not a full-suite result. No clean export was needed because the path-dependent failure reproduced at a single test and its correct invocation passed.

## HTTP capability

One loopback bind probe was attempted: binding `127.0.0.1` to an ephemeral port failed with `OSError: [Errno 1] Operation not permitted`. HTTP listener tests are **environment-unverified**, not passed or classified as application failures. On an unrestricted host, a representative command is:

```sh
PYTHONPATH=src:tests python -m unittest tests.test_ai_encounter.AIEncounterHTTPTest
```

No retry was made. No HTTP tests were run.

## Gate and recommendation

No reproducible non-environmental defect in foundational Action, shared-snapshot, atomic-publication, or Reality behavior was found in the selected cohorts. The on-demand Encounter-instantiation slice is a **go**, with explicit residual regression uncertainty: the historical 1,759-test result (1,591 pass, 43 failures, 125 errors) is not a current baseline, its full failure log was not retained, and the current broad suite remains unverified. Do not claim that all historical errors were repaired or that unrun tests pass. HTTP remains unverified in this restricted environment.

The complete repository suite was not run, in accordance with the assignment. No source changes, staging, commit, or push occurred.
