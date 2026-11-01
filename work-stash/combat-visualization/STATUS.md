# Combat visualization — status

- Baseline: `e169660c2b39e028b2bba337a35fde1bc22acd13` (tree `31a08dc6036a6a127d7506ea9cc3603c3338fcea`).
- Original paths: see `../MANIFEST.tsv` for visualization code, template, test and documentation.
- State: interrupted visualization work; source/test files remain at original paths and are copied here. The root HTML replay and preview outputs were archived externally as generated presentations; `examples/combat_visual.py` can regenerate `combat_replay.html`.
- Constraints: visualization is not simulation authority and must not mutate Encounter state.
- Tests: not run during cleanup.
- Next: review whether the visualization remains needed, then run its focused test before any commit.
- Restore: copy source snapshots back by recorded path; generated HTML can be recovered from the external preservation archive.
