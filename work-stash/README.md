# Interrupted work stash

This directory organizes unfinished Universe work for review. Its contents are **interrupted work, not verified production**. It must not be treated as an implementation specification or as proof that the copied code passes tests.

Baseline: commit `e169660c2b39e028b2bba337a35fde1bc22acd13`, tree `31a08dc6036a6a127d7506ea9cc3603c3338fcea`. Original source paths remain in the working tree unless the status record says otherwise; copied snapshots are retained under each topic's `snapshot/` directory. `MANIFEST.tsv` records original path, status, topic, mode, byte count and SHA-256 for the 78 copied topic snapshots. `checkpoint-and-realization/` also has a tracked-diff patch against the baseline; its byte count and SHA-256 are recorded in that topic status.

Each topic `STATUS.md` records scope, known unfinished state, constraints and a cautious restoration recipe. For a copied file, verify its manifest digest, then restore from `topic/snapshot/<original_path>` to the repository root only after checking the target path and saving newer edits. To reapply the tracked residual patch, first confirm the repository is on the baseline commit and inspect the patch with `git apply --check`; no patch is to be applied automatically.

No content here has been staged or committed in this increment. The directory is not ignored, but Git does not consider new files tracked until a later authorized commit. Do not use `git add -A`; review and commit topic paths selectively. Do not push sensitive or oversized material.
