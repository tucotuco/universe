# U-ARENA-012 — Native attack-only Arena opponent

## Outcome

Implemented the first opponent counterattack as a native Arena `MeleeStrike`. The Generate Encounter form offers the bounded `Attack only (native Dagger)` strategy and `No autonomous strategy`; other strategy vocabulary remains unavailable. Attack-only requires the equipped Arena kit. The default equipped-kit browser flow and explicit empty-ground profile produce two API-generated, equipped Beings.

The opponent selects a fixed native Thrust at the next player-requested one-second decision point, after Arena activation. Eligibility reads the opponent's current observer-owned evidence of the player, native awareness, current capacity to act, and the opponent's actual API-created Dagger in a functioning readied hand. It does not read the player's destination or proposed Action. It neither moves nor turns the opponent. A pending opponent Action is not reissued.

The accepted strike uses `Encounter.prepare_action` and `Encounter.schedule_action`; movement, impact-time reach and facing, hit/defense checks, damage, native RNG, history, and publication remain in the existing Encounter pipeline. Independent player and opponent strikes scheduled at the same native time settle in the same committed boundary. Opponent declarations are hidden during their declaration second and are projected to the player after the next second only while the player's current evidence and awareness still permit observation. The browser shows Action name, remaining time, and completed outcome without opponent HP, source specification, equipment inventory, or native IDs.

## Browser walkthrough and observed result

In Chrome, the local Arena was generated with seed `20261107`, 10×5 hexes, 10,000 starting XP, equipped Beings, and the `Empty ground` profile. I selected `Attack only (native Dagger)`, clicked the Sprint/turn destination hex `(5,4)` using the normal map control, and advanced one second. At Encounter time 1, the browser showed `Opponent Thrust is underway; 3 seconds remaining.` Advancing through time 4 showed `Opponent Thrust resolved: normal after 4 seconds.` No Being position, facing, equipment, HP, awareness, or result was changed outside ordinary browser controls and native resolution.

The reproducible test setup confirms initial cells `(3,4)` and `(5,3)`, opponent facing `3/12`, and the player's ordinary movement to `(5,4)`. The opponent's native Thrust uses its own API-created Dagger and four-second native timing. A separate route away from the opponent resolves natively as `out_of_reach`; the implementation does not force a successful hit.

## Persistence and refusal coverage

Arena Save schema `/5` strictly records the selected strategy. Existing `/4` Arena files load with autonomous strategy disabled. Pending and completed opponent strikes remain solely in the native graph and are reconstructed without NPC or equipment generation. The deterministic regression saves after boundary 1 with the opponent strike pending, restores into a fresh session while `npcgen.api.arena_ready_being` is stubbed to fail, advances original and restored sessions to boundary 4, and compares Action identity/outcome, Encounter time, finished Action list, event identities, Choice state, both observer evidence histories, native HP, and RNG cursor. A post-completion save is restored and advanced again; the next opponent Action identity agrees across the two sessions.

Read-only and integration checks cover missing Awareness/evidence, unready Dagger, missing Dagger, an unable opponent, a pending opponent Action, and impact-time out-of-reach. Ineligible scheduling creates no Action or Choice, does not change Choice revision or event history, and consumes no Arena RNG. Simultaneous player/opponent Thrusts are verified in one committed boundary. Existing player melee Save/Load behavior remains green.

## Validation

- `PYTHONPATH=src:tests:../npc-generator python -m unittest test_arena_opponent_attack test_arena_melee_attack test_arena_ready_weapon test_arena_persistence test_arena_state_activation test_arena_checkpoint_activation test_arena_destination_movement_blocker test_checkpoint_arena_perception test_action_choices test_transactional_progression` — **164 tests passed**, 97.810 s. The opponent module contributes five focused tests, including strict `/4` load compatibility and deterministic pending/completed cross-session continuation.
- `python -m py_compile src/arena_browser_session.py src/arena_persistence.py examples/arena_web.py` — passed.
- `git diff --check` — passed.
- Real Chrome smoke — passed as described above. The initial sandbox loopback bind failed with `PermissionError`; after user approval, only the Arena server smoke was run outside the network-restricted sandbox. The server bound `127.0.0.1:64175` on an OS-assigned port. It was stopped after the smoke.

An initial broad test invocation used two incorrect module names and omitted `tests/` from `PYTHONPATH`, so its two collection errors were test-runner setup issues; the corrected command above passed all 163 tests. The sibling Generator source is referenced relatively and was not modified.

## Changed files

- `src/arena_browser_session.py` — strategy selection, eligibility, stable opponent Action identity, native scheduling, player-authorized delayed projection, and movement coexistence.
- `src/arena_persistence.py` — versioned strategy sidecar and strict prior-schema default.
- `examples/arena_web.py` — Generate selector and opponent Action countdown/result display.
- `tests/test_arena_opponent_attack.py` — attack, refusal, simultaneous settlement, browser scenario state, and persistence coverage.

## Limits

Only attack-only is implemented. The opponent does not pursue, change facing, or adjust tactics; it may make a legal native attack that resolves as `not_facing`, `out_of_reach`, a miss, or another ordinary native result. The known ordinary starter-ground-Object `uncertain_path` behavior remains unchanged; the acceptance scenario uses the existing empty-ground profile. No changes were made to `npc-generator`, no general AI framework or victory condition was added, and nothing was pushed.

## Commit

Implementation commit: `3bd2359` (`Implement native Arena opponent attack-only strategy`).
