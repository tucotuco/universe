# U-THROW-004 — Native Throw flight progression

## Result

Implemented and committed the bounded native Throw Action and committed projectile-flight progression. The Arena example now releases a held Object at the native t=4 boundary, advances it through committed integer-second boundaries t=5 and t=6, and lands it at t=7. The trajectory uses the adopted constant-gravity model (`g = 10 m/s²`) and body-height release; it is computed from the committed release and remains part of the transactional state path.

The Throw is a four-second native Action. It validates an eligible Being, a single possessed Object within the assignment's mass limit, and positioned participants. It has no attack roll, damage, or skill practice. Legacy resolution refuses this Action rather than applying a sequential fallback. A concurrent Action cannot reserve the same Object during the Throw interval.

The example's pure trajectory projection is labeled separately from the committed native chronology. Native release and each subsequent flight-state update are published through the existing interval transaction. The release receipt preserves Action/effect provenance; the committed flight state remains Target/Object-owned. Evaluation does not advance authoritative RNG.

## Changes

The implementation commit `f3454f70e1465c2f75c542ca81450f1cb99dc8bc` contains these 15 paths:

- `src/activities.py`, `src/scheduling.py`, `src/action_choice.py`, `src/transactional_progression.py`: Throw declaration, eligibility and exclusive Object reservation.
- `src/action_evaluation.py`, `src/observer_proposals.py`, `src/action_settlement.py`: frozen evaluation, typed release effect, and fail-closed settlement validation.
- `src/throwing.py`, `src/interval_staging.py`, `src/atomic_publication.py`: immutable flight state, integer-boundary candidate progression and atomic release/flight publication with rollback.
- `src/encounter_inspection.py`: detached inspection of committed flight states and causal release provenance.
- `examples/native_throw_arena.py`, `tests/test_native_throw_arena.py`: reproducible chronology and focused regression coverage.
- `TASKS.md`, `docs/tasks/encounter-engine.md`: bounded completion status.

## Verification

- Focused Throw suite: **6 tests passed**.
- Related scheduling, transactional, evaluation, settlement, inspection, melee and NPC Arena regressions: **284 tests passed**.
- The related test command was run from `tests/` because several existing test fixtures resolve repository configuration paths relative to that working directory.
- Python compilation passed for all changed source files, the example and the test module.
- `git diff --cached --check` passed before the implementation commit.
- Runnable example completed with native release at t=4, flight positions at t=5/t=6, and landing at t=7. The committed impact time was 6.337306188 seconds; the Object landed at approximately 25.5624 m. Seven native boundary receipts were present, and authoritative RNG was unchanged.

The complete repository suite was not run; this increment used the focused regression set specified by its bounded verification scope.

## Commit and repository state

Implementation commit: `f3454f70e1465c2f75c542ca81450f1cb99dc8bc` (`Add native transactional Throw flight`). No push was performed. The branch is `main`, ahead of `origin/main` by 44 commits after this commit.

Pre-existing unrelated working-tree deletions and untracked files remain untouched, including the local `legacy/`, `.agents/`, `.claude/`, `docs/encounters/`, assignments, saved examples and workspace JSON. No unrelated paths were staged or included in the commit.

## Limits

This is the assignment's exact, bounded Throw implementation. It does not generalize projectile physics, add collision or hit mechanics, change adopted combat rules, or activate Throw in the legacy resolver. Transactional Encounter mode remains opt-in.
