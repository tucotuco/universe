# Checkpoint and realization residuals — status

- Baseline: `e169660c2b39e028b2bba337a35fde1bc22acd13` (tree `31a08dc6036a6a127d7506ea9cc3603c3338fcea`).
- Original paths: checkpoint inspection/realization examples and tests are listed in `../MANIFEST.tsv`. The tracked post-5E3A residual diff is `tracked-residuals.patch`.
- State: residual edits and exploratory tools are preserved, not accepted as a subsequent increment. The 5E3A committed baseline remains unchanged.
- Patch: `tracked-residuals.patch` is 70,961 bytes, SHA-256 `f183cfb4d8ddaced35122872caee1b1d57cec46ffdc9181ef218842cc57a1f4c`.
- Constraints: do not issue historical receipts, relax quarantine, enable restore beyond the committed bounded contract, or change readiness flags without an authorized assignment.
- Tests: not run during cleanup.
- Next: review the patch and untracked tools against the current committed source, then define one narrow follow-up.
- Restore: inspect the patch with `git apply --check` at the exact baseline before applying; file snapshots are SHA-256 indexed.
