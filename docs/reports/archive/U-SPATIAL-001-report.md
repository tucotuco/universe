# U-SPATIAL-001 — Blocked: position commitment conflicts with the unchanged Reach gate

**Verdict: BLOCKED before implementation.** No production, example, or test changes remain. The candidate 0.1 m position-commit change was removed after it reproduced a conflict with the assignment's explicit requirement that existing Melee Reach/NPC Arena outcomes remain unchanged. The report is the only U-SPATIAL-001 artifact.

## Checkout and preservation

- Starting checkout: branch `main`, HEAD `137e615e0c1a72e0b2bcbb4ad2ff4395cd5e946c`.
- The Git index was empty at inspection and remains empty before report staging.
- Existing user-managed tracked documentation deletions and untracked work were not staged, restored, moved, or otherwise changed. The nine code/example/test paths explored for this assignment were clean at start and have been returned to their exact HEAD contents.
- No push.

## Source and rule findings

- `src/transactional_progression.py::step_transactionally` publishes each crossed integer boundary separately.
- `src/interval_staging.py::prepare_interval_candidate` integrates the supplied constant velocity into staged positions, captures the post-movement/pre-Action snapshot, and derives projectile updates. Projectile positions already come from `ProjectileFlight.position_at(boundary)` and immutable launch facts, not from adding displacement to the prior boundary position.
- `src/action_evaluation.py` evaluates Run displacement and Spot/reach/path calculations from the frozen boundary entities. `src/atomic_publication.py::_make_plan` applies positions and projectile updates; `_committed_consistency` verifies them. `src/encounter_inspection.py::prepare_record` records committed Target positions and projectile history. U-THROW-006 builds Object observation from the same boundary snapshot and publishes it with the successful Spot.
- Adopted revision-61 `Numerical precision and units` and `Movement` specify nearest 0.1 m at movement-state commitment while retaining full precision in intermediate calculations. Revision 62 explicitly leaves the adopted metric precision unchanged. No adopted exact-half-tenth convention was found. The assignment proposes half-away-from-zero if implementation proceeds; this report does not install that tie policy.

## Reproducible acceptance conflict

The existing `tests/test_npc_being_arena.py::TestNpcBeingArena::test_transactional_reach_uses_post_movement_position_at_impact` moves a target from x=1.5 m toward the attacker at -0.25 m/s over boundaries 1–3, then resolves a Thrust. Current full-precision behavior ends at x=0.75 m; the native measured Reach is `0.8916429745442158 m`, so the existing attack resolves `normal` and deals 4 damage (target HP 10→6).

Applying the assignment's nearest-tenth commitment at each of those three published movement boundaries, with the requested half-away tie policy, yields:

| Boundary | Full-precision endpoint before commitment | Committed x |
|---:|---:|---:|
| 1 | 1.25 m | 1.3 m |
| 2 | 1.05 m | 1.1 m |
| 3 | 0.85 m | 0.9 m |

At boundary 4, with no further movement, the Thrust sees committed x=0.9 m. That exceeds the fixture's 0.8916429745 m Reach; the actual candidate run changed the outcome to `out_of_reach` rather than the required unchanged `normal` result. This was reproduced with the candidate implementation by running the focused NPC Arena test from `src/`; the failing assertion was `entered["outcome"] == "normal"` at line 140. The same test's outward-motion position similarly changes from 1.5 m to 1.6 m, although it remains out of reach.

This is not a defect in the Reach comparison or in ballistic projection. It follows from committing each intermediate authoritative position at 0.1 m and then using that committed value as the next interval's movement origin and later Action snapshot. Preserving the earlier Reach result requires retaining a separate exact movement position across commits and specifying whether reach/path calculations use that value while observation, target history, and inspection use the quantized position. Such a shadow position would be additional authoritative state with read-set, atomic-write, rollback, and eventual checkpoint-closure obligations; no such contract currently exists.

## Candidate projectile values if the position rule is applied

The exact Throw calculation remains unchanged: release z=`69 × 0.0254 = 1.7526 m`; exact analytical impact remains `6.337306187730018 s`; the full-precision flight descriptor remains the source for every boundary. Under half-away-from-zero, positions recorded at commitment would be:

| Boundary | Analytical position (m) | Candidate committed position (m) | State |
|---:|---|---|---|
| 4 release | `(0, 0, 1.7526)` | `(0, 0, 1.8)` | in flight |
| 5 | `(10.936693365293, 0, 7.689293365292997)` | `(10.9, 0, 7.7)` | in flight |
| 6 | `(21.873386730586, 0, 3.6259867305859963)` | `(21.9, 0, 3.6)` | in flight |
| 7 | `(25.562401076005166, 0, 0)` | `(25.6, 0, 0)` | landed |

The existing Runner endpoint `101.25 m` would commit as `101.3 m`. The immutable release/landing/velocity descriptor and impact time would remain unrounded. A successful t=6 Spot must record exactly the t=6 committed position, not the analytical value.

## Verification

- Restored baseline focused suite: **88 tests passed** in 31.626 s, from `src/` with `PYTHONPATH=../tests:..`: `test_native_throw_arena`, `test_native_throw_concurrent_run`, `test_native_throw_spot`, `test_melee_combat`, `test_npc_encounter_arena`, `test_npc_being_arena`, `test_action_evaluation`.
- `git diff --check`: passed before report creation.
- No full discovery run, in accordance with the assignment. The prior known full-suite result remains 1,759 discovered, 43 failures and 125 errors, with causes partly identified and partly unclassified.
- During candidate implementation, the focused existing NPC Reach test failed exactly as described. The implementation was then removed rather than changing the expected combat outcome or Reach rules.

## Decision required before the smallest safe implementation

Choose one contract:

1. **Committed-position geometry:** future Reach/path outcomes use the 0.1 m committed positions. Approve that the NPC example's t=4 Thrust may become `out_of_reach` under the adopted rounding rule, superseding the assignment's unchanged-outcome gate; or
2. **Dual precision:** preserve a separately represented exact movement position for later physical threshold checks while publishing the rounded coordinate for authoritative position/evidence history. This requires a reviewed data contract and explicit semantics for which queries use each position, plus transactional rollback/read-set tests and a checkpoint-closure plan.

No tie convention was added. If the chosen contract reaches quantization implementation, the assignment's deterministic half-away-from-zero policy remains the proposed interim tie behavior and should be confirmed in the report.

## Next step

Obtain approval for one of the two position-versus-Reach contracts, then implement that contract with a focused acceptance test before changing the flight/Spot publisher. Do not silently alter Reach or weaken the existing NPC Arena assertion.
