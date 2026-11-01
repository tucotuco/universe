# Universe fatigue R4 workbench — status

- Baseline: `e169660c2b39e028b2bba337a35fde1bc22acd13` (tree `31a08dc6036a6a127d7506ea9cc3603c3338fcea`).
- Original paths: `universe-fatigue-workbench/`; the coherent workbench source, rules, UI and tests are copied under this topic's snapshot. Four ignored `.pyc` cache files were left in place and excluded from the tracked snapshot as regenerable output; they were not status paths.
- State: independent experimental workbench, not active live R4 fatigue settlement and not part of the committed Encounter engine.
- Constraints: do not import these modules into runtime, activate fatigue settlement, or treat workbench tests as the repository regression suite.
- Tests: not run during cleanup.
- Next: review the workbench on its own terms before proposing any separate integration increment.
- Restore: verify manifest hashes, then copy selected snapshot files to their original paths.
