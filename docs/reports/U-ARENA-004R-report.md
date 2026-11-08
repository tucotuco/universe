# U-ARENA-004R Engineering Report

**Outcome:** the generated Arena now has a playable native destination-movement loop. The player can select an in-footprint hex center, choose Walk/Hustle/Jog/Run/Sprint and turn-or-maintain facing, then advance native Encounter time one second at a time. Position, facing, occupancy, plan, and remaining distance are projected from committed server state. A destination remains active across seconds and can be changed or stopped at a boundary.

## Native posture and rate inputs

`BeingInstance` now carries a validated posture value: `standing`, `crouching`, `lying`, or unknown (`None`). New Beings are unknown unless a world author establishes posture. An absent or false legacy `prone` state remains unknown; legacy `prone=True` establishes effective `lying`. Contradictory prone and posture facts fail closed. There are no new posture-changing Actions.

The generated Arena explicitly authors both Beings as standing at time zero and retains `arena.initial-posture.v1/scenario` provenance on each participant. The player's own projection includes that source. Posture is frozen into the common `EvaluationSnapshot`; rate evaluation requires this snapshot, rejects caller-supplied posture, and applies the adopted posture limits from the frozen value alongside Fitness, Run, fatigue, and carried weight.

Closed checkpoint field inventories, binding, reconstruction, and closure semantics include posture. The bounded Run/Spot closure certificate is now `/3`. Its refusal of activated Arena checkpoints remains in force, including the separately typed movement activation. The separate reproduction/Being checkpoint still supports only an unknown-posture pristine Being; known posture is rejected. Existing v1–v3 wire compatibility is retained because those historical payloads represent the constructor's formerly absent posture as unknown.

## Arena movement interaction

- Selecting the first destination creates an `ArenaMovementActivation` record with Encounter, actor, start time, and movement-decision identity. It selects native transactional progression without an Action, Choice, target, Encounter initiation target, Awareness, or RNG draw.
- The session keeps the destination/rate/facing policy as a server-owned plan. At each untouched boundary it builds a fresh `MovementIntent` from the current native position and passes it through the existing one-second Encounter pipeline. Facing-relative direction and turn selection are resolved by the native movement engine; no browser velocity or position arithmetic is authoritative.
- The native engine publishes movement and facing together, before same-boundary Action resolution. It provides exact partial-second arrival without overshoot. The session clears the plan on arrival; stop and destination changes take effect at the current committed boundary.
- RunAction is not classified as another demanding Action. Unknown co-resolving Action types fail closed. Terrain and hampering come from the explicit Plains/Road unhampered Arena premise. Maintain-facing non-forward restrictions and standing/crouching/lying rate caps are native r61 rules.
- The HTTP projection contains only the player, the generated map/environment scope, native time, and the player's own movement plan/outcome. Handler tests verify that the opponent's identity, name, position, facing, and provenance remain absent. Generate still has exactly the three XP/width/height inputs; Spot and Load remain disabled.

The end-to-end handler test uses the generated Being's actual initial position and reproducible facing, selects the farthest generated map cell, and repeatedly commits native seconds through exact arrival. It confirms no new events, Choices, Awareness, or RNG changes. Separate tests cover stop/change, unknown-posture refusal without activation or mutation, and activation rollback after injected failure. Existing native tests cover movement-plus-turn rollback, same-second snapshot ordering, exact arrival, and RunAction's non-demanding observation role.

## Limits and browser smoke

No Being body geometry, collision adjudication, obstacle clearance, pathfinding, perception, terrain traversal, or additional movement physics was added. The generated map's unobstructed/unhampered premise does not establish physical clearance between Being bodies or vacant-hex safety. Destination selection means a hex center target for the native reference point.

The HTML/handler was tested directly, but browser rendering was not verified: a loopback bind to `127.0.0.1:0` failed with `PermissionError: [Errno 1] Operation not permitted`. On a machine that permits loopback, run `PYTHONPATH=../npc-generator .venv/bin/python examples/generated_arena_browser.py`, open `http://127.0.0.1:8000/`, Generate an Encounter, click a distant hex, choose a rate and facing policy, then advance until the native plan reports arrival. Repeat with Stop and a changed destination.

## Verification

The adjacent NPC Generator source is available at `../npc-generator` and was used read-only through `PYTHONPATH`; it was not modified. This environment has no `pytest` installation, so tests used the repository's `unittest` runner.

| Command | Result | Test runtime |
|---|---:|---:|
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_generated_arena_browser.py'` | 13 passed | 3.697 s |
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_movement_intent.py'` | 20 passed | 3.766 s |
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_action_evaluation.py'` | 47 passed | 0.398 s |
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_arena_initialization.py'` | 7 passed | 0.467 s |
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_arena_hex_map.py'` | 4 passed | 0.001 s |
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_checkpoint_reconstruction.py'` | 8 passed | 2.997 s |
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_checkpoint_bounded_closure.py'` | 7 passed | 3.900 s |
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_checkpoint_identity_binding.py'` | 11 passed | 10.807 s |
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_atomic_publication.py'` | 70 passed | 40.598 s |
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_reproduction_being_checkpoint.py'` | 14 passed | 1.671 s |
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_checkpoint_adapters.py'` | 47 passed, 1 known failure | 20.348 s |
| `PYTHONPATH=tests:../npc-generator python -m unittest test_checkpoint_adapters.TestNativeCheckpointAdapters.test_movement_activated_arena_remains_outside_bounded_checkpoint -v` | 1 passed | 0.073 s |

The one adapter failure is the pre-existing `test_dangling_equipment_and_possessions_refuse` expectation: it expects `ValueError: dangling equipment`; native preflight raises `EvaluationIntegrityError: unknown transitive Object identity`. It is unchanged and was not broadened into this work.

`python -m py_compile` passed for all changed Python modules, and `git diff --check` passed. The full suite was not run.

## Commits and where we stand

- `6392da7 Add authoritative Being posture for movement`
- `4b20247 Connect generated Arena to native destination movement`

The requested playable destination-movement slice is implemented and native handler tests prove committed progress through arrival. Remaining limits are the adopted absence of Being geometry/collision rules and the environment's loopback restriction, which prevented visual browser verification. No Generator files were changed and nothing was pushed. Pre-existing unrelated working-tree deletions and untracked files were preserved and left outside these commits.
