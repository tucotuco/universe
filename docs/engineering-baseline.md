# Universe engineering baseline — 2026-10-19

This checkpoint was prepared against the user's uploaded working-tree snapshot
`universe-baseline-20261019T030520Z.tar.gz`, captured from branch `main` at
commit `a6617e32883c446e23f63ec464044984530413ce`.

At capture time, the tracked working tree was clean; an untracked
`docs/Encounters Working Draft.pdf` was reported and is intentionally not changed
by this patch. The captured environment was macOS/arm64, Python 3.11.1.

## Before

`python -m unittest discover ../tests`, run from `src/`, reported 448 tests:
five failures and three errors.

- **Exertion (3 failures):** tests use full activity names (`jogging`,
  `swimming`, `running`, `sprinting`), while the implementation recognized
  their abbreviated equivalents only. Both spellings are now accepted;
  previously supported abbreviations are unchanged.
- **Skill definitions (2 failures):** `src/config/skills.tsv` has 24 skills,
  including `spot`; the tests expected 23. The catalog is unchanged.
- **Weapon skills (2 errors):** a test fixture called the nonexistent
  `WeaponDictionary.load_objects()` method. Its supported file loader is
  `load()`. The test now uses that method and validates invalid skill
  updates with the correct setter signatures.
- **Universe persistence (1 error):** a test required an existing
  `results/` directory. It now writes to a temporary directory with
  automatic cleanup, rather than depending on the caller's filesystem.

The test runner (`run_tests.sh`) now sets its own working directory so that it
can be invoked from any location. The underlying older tests still depend on
their historical paths relative to `src/`; the script handles that expectation.

## After

Run from any directory with the project's Python environment active:

```sh
bash /path/to/universe/run_tests.sh
```

Or from `src/`:

```sh
python -m unittest discover ../tests
```

On the baseline snapshot with these corrections: **449 tests; OK (zero
failures or errors)**. Some intentionally invalid-action tests still print
`Ojo, eh!` warnings; these are not failures.

## Scope and remaining work

This checkpoint repairs test drift and test-runner reliability. It does **not**
validate complete Universe save/restore, historical Being state, or integrated
resolution-on-demand. Those remain separate architecture/integration milestones.

Always verify the full test suite on the authoritative local checkout after
applying the patch. The uploaded snapshot contains no `.git` history: its commit
identity is taken from the captured diagnostics, and the patch is tested against
its actual source contents.
