# U-OBS-001 — Playable perception and observer-owned evidence

## Current result

**ACTIVE; implementation is underway.** This initial checkpoint resumes the installed U-OBS-001 scope after acceptance and archival of U-PLAYTEST-001. No new perception rules are adopted. The accepted playtest release remains outside and unchanged from this repository.

### Execution interval

- Start: **2026-11-14T22:34:58-08:00** (local execution start captured at the first repository inspection; timezone is America/Los_Angeles)
- End: pending this execution closeout
- Elapsed: pending this execution closeout

## Starting repository state

- Branch `main`, HEAD `4540b949345fdf01bc42641c63e5f220950c66a9`.
- Five unrelated pre-existing staged archive changes were present (four historical active-path deletions and one U-THROW-001 archive rename); `docs/assignments/universe-arena.json` was untracked. Both states are preserved.
- `docs/assignments/U-OBS-001.md` was installed but untracked; it is the authorized current assignment and is being versioned with this execution.
- `TASKS.md` had U-OBS-001 as the sole ACTIVE program. U-PLAYTEST-001 was accepted as DONE by the user, its report consumed, but its assignment/report were still in active directories; this execution archives them and repairs current links.
- Adopted Encounter authority is revision 70. The frozen external U-CAP-008A playtest distribution is unchanged.

## Initial trace

The code already has a native `ArenaPerceptionLedger` and revision-65 unobstructed generated-Arena initialization/refresh in `src/arena_perception.py`. `SpotAction` exists and generated-browser UI has only a disabled Spot control because generated npcgen Beings lack the geometry required by the native resolver. `TASKS.md` records U-ACT-037 as bounded DONE, U-ACT-038 Listen as VERIFY, U-ACT-039 as catalog VERIFY, U-SPOT-002 and U-LOC-002 as open/partial. The assignment requires tracing native observation, Search/Spot/Listen, motion, Action/Event evidence, controllers, persistence and shipped UI; detailed implementation and verification findings will be added below as work progresses.

## U-PLAYTEST-001 archival

The user accepted the assignment and consumed the report. Both were moved with Git-aware renames to `docs/assignments/archive/U-PLAYTEST-001.md` and `docs/reports/archive/U-PLAYTEST-001-report.md`; TASKS and the maintained handoff point to the archive. The independently installed release folder and ZIP were not modified.

## Verification and remaining acceptance matrix

This initial report does not claim U-OBS-001 acceptance. The assignment’s current-versus-historical evidence, deliberate discovery Actions, meaningful incidental discovery, Entity/Event/motion/Action records, privacy, Arena UI, two-sided observer divergence, fresh-process persistence, and both combat-mode regression criteria remain to be implemented or verified against the live checkout. Exact focused commands, outcomes, final task transitions, commit hashes, staged audit results and the final execution time will be recorded at closeout.
