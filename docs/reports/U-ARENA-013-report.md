# U-ARENA-013 engineering report

## Result

The `attack_only` Arena opponent now approaches an observed player with the existing native movement engine, then schedules an ordinary native Dagger Thrust when the committed snapshot makes that Action tactically plausible. The opponent never reads the player's uncommitted destination or proposed Action. Player and opponent movement can be proposed for the same one-second boundary and settle together through the existing atomic Encounter publication path.

The decision policy is intentionally bounded to deterministic approach on an unobstructed map. It does not implement pathfinding, collision, body geometry, cover, or prediction. A ground profile containing unmodeled Objects remains conservatively uncertain and does not get treated as transparent; the positive scenario uses the adopted `Empty ground` profile.

## Native decision and movement behavior

At each available native decision opportunity, the session first checks the opponent's current observer-owned evidence for the player's committed position, current ability/capacity, pending Actions, and actual API-created ready Dagger. An ephemeral native `MeleeStrike` uses the adopted strike status evaluator. If the current state is `in_reach`, the opponent submits a real Thrust through the native scheduler. If the strike is out of reach or misfaced, it derives a valid map destination and facing policy from the observed committed target position and asks `prepare_movement_intent` to resolve the move using native Run movement-rate, turn-and-move, and posture rules. It waits rather than proposing movement when evidence, actor state, geometry/map bounds, or the empty-path premise is not supported.

Movement decisions contain no caller-supplied velocity. The opponent does not change facing directly. The session supplies distinct player/opponent `MovementIntent`s to one Encounter step; the transactional progression layer validates the actor/condition mapping, evaluates both from a common declaration snapshot in stable actor order, and publishes movement plus scheduled Action resolution atomically. Existing single-actor movement callers retain their previous API. An injected post-movement publication failure verified rollback of both actors, both facings, Choice/RNG state, and Encounter time.

The policy is derived from the opponent's current native evidence, committed positions/facings, map bounds, and a short native committed-position history used only as a deterministic anti-reversal tie-break. It adds no serialized AI world model or controller state. The existing Arena save schema remains unchanged. Load therefore does not regenerate Beings, equipment, movement plans, or Actions; later decisions are recomputed from restored state.

## Reproducible native and browser demonstration

The positive scenario uses root seed `20261123`, a 10 by 5 Arena, 10,000 starting experience, equipped Beings, the checked-in `Empty ground` profile, and `Attack only (native Dagger)`. The player stays stationary for the core approach. Generation itself supplies the initial positions, facings, equipment, and observer evidence; no native position, facing, hit point, equipment, or awareness fields are edited after generation.

Through the real Chrome page, Generate Encounter and the normal Run activation / Advance 1 second controls produced this native sequence:

| Boundary | Result |
| --- | --- |
| 0 | The generated player and opponent are separated. Opponent has its own ready native Dagger. |
| 1 | The opponent's native position changes from hex `(0,3)` to `(5,1)` by ordinary turn-and-move. The page says “Opponent is approaching.” |
| 2 | The opponent moves again to hex `(8,1)`. The page reports a Thrust opportunity; no doomed distant Thrust was scheduled. |
| 3 | The native Thrust is executing with 3 seconds remaining. The opponent does not move during its pending Action. |
| 6 | Native impact commits `normal` after 4 seconds. A hit was not required by the rules or acceptance test. |

The real browser was Chrome at `127.0.0.1` on an OS-assigned port. The normal sandbox loopback bind failed with `PermissionError`; the previously approved narrowly scoped Arena smoke was run outside the network-restricted sandbox, bound only to `127.0.0.1`, and the server was stopped after the smoke. Browser-generated requests exercised the shipped JavaScript and native session handler. The browser message exposes the opponent's activity without exposing its private destination or native identifiers.

Additional seeded checks show that the player can submit a native destination while the opponent approaches, and can continue moving while the accepted opponent Thrust resolves. The impact outcome remains native and is evaluated against the then-current target state. Existing same-boundary player and opponent strike tests verify both Actions share the ordinary native scheduler/settlement. Out-of-reach impact remains an ordinary `out_of_reach` result if the player moves away after the Thrust is accepted.

## Persistence and observer checks

The focused Arena tests save and restore once while the opponent is approaching, compare the restored continuation against uninterrupted execution, save again with the actual native Thrust pending, then restore and compare through its completed boundary. The comparison covers Encounter time and committed boundary, both native Being identities/positions/facings/hit points, pending and finished Actions, event identities, Choice state, each Being's observer-owned evidence/history, and RNG cursor state. `npcgen.api.arena_ready_being` is patched to fail during every restore, proving Load does not regenerate either Being. Pending Thrust and instrument identities match the originals.

The test also starts a fresh operating-system Python process twice: once from the approaching save and once from the pending-Thrust save. Each process disables the NPC generation API, loads the file, advances the ordinary native Encounter, and returns a canonical digest of the complete tested continuation projection. Both digests match uninterrupted continuation. Raw checkpoint bytes are not compared because serialization contains process-dependent ordering; the digest comparison uses sorted canonical JSON over native simulation state, actions, observer evidence/history, Choice state, event identities, and RNG cursor. The real Chrome smoke separately verified the shipped browser event path but did not restart its server from a saved file.

## Validation

- `PYTHONPATH=src:examples:../npc-generator python -m unittest tests.test_movement_intent tests.test_arena_opponent_attack tests.test_generated_arena_browser -v` — 67 tests passed in 30.650 seconds.
- `PYTHONPATH=src:examples:tests:../npc-generator python -m unittest test_arena_opponent_attack.TestArenaOpponentAttack.test_approach_and_pending_thrust_restore_continue_deterministically -v` — passed in 5.680 seconds, including two fresh OS-process restores; this test is also included in the focused suite above.
- `PYTHONPATH=src:examples:tests:../npc-generator python -m unittest test_arena_persistence test_arena_melee_attack test_transactional_progression test_encounter_inspection test_arena_checkpoint_activation -v` — 119 tests passed in 70.007 seconds.
- `python -m py_compile src/arena_browser_session.py src/transactional_progression.py src/encounter.py examples/arena_web.py` — passed.
- `git diff --check` — passed.

## Changed files and commit

Implementation and regression coverage changed:

- `src/arena_browser_session.py`
- `src/transactional_progression.py`
- `src/encounter.py`
- `examples/arena_web.py`
- `tests/test_arena_opponent_attack.py`
- `tests/test_generated_arena_browser.py`
- `tests/test_movement_intent.py`

Implementation commit: `3e5ca66` (`Implement attack-only Arena approach decisions`). The report is committed separately.

## Limits

This is the attack-only strategy, not a general tactical AI. It does not use pathfinding or infer whether unmodeled ground Objects are passable; starter profiles that trigger native `uncertain_path` remain a stop condition. It will not attack without current observer evidence, a usable actor and actual ready Dagger, or an authoritative in-reach status. There is no unresolved native movement or facing rule decision for the demonstrated empty-ground case.
