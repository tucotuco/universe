# Spatial Encounter work — status

- Baseline: `e169660c2b39e028b2bba337a35fde1bc22acd13` (tree `31a08dc6036a6a127d7506ea9cc3603c3338fcea`).
- Original paths: see `../MANIFEST.tsv` rows for this topic; includes the existing `examples/first_spotting_encounter.py` edit, spatial examples, tests and relevant observer/group source edits.
- State: exploratory and unfinished; the files are preserved at their original locations and copied under this topic's `snapshot/`. No new rules or validation claims are made here.
- Constraints: preserve revision-60 Spot, observer ownership, transaction publication and current group-observation boundaries. Do not treat example behavior as adopted policy.
- Tests: no tests run for this cleanup. Previous complete regression evidence is the clean 5E2Z candidate (1,573 tests), not this dirty worktree.
- Next: review the existing spatial series as one coherent candidate; select explicit runnable examples/tests before any source increment.
- Restore: verify each `MANIFEST.tsv` SHA-256 and copy selected files back to their recorded original paths.
