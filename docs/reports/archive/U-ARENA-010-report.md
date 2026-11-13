# U-ARENA-010 — Playable first armed exchange

## Result

The generated Arena now exposes the existing native Dagger Swing and Thrust through the player's contextual Action selector. The submitted request contains only the observer-issued target handle and chosen native motion; the server resolves that handle through the player's current perception evidence and binds the strike to the exact Dagger Object recorded by the initial `arena_ready_being` equipment commitment. The server constructs and schedules `MeleeStrike` through `Encounter.schedule_action`; it does not calculate a parallel combat result.

The Action catalog presents a strike only when its native scheduler/resolver contract is present, the selected target is a currently perceived, aware opposing participant, the Encounter is transactionally initiated, both combatants can participate, and the player's original API-created Dagger remains held and readied. Duration comes from the native Dagger weapon table. The catalog explains that reach and path are checked at impact, matching `MeleeStrike.prepare_schedule`; it does not turn an impact-time rule into a scheduling refusal. The UI returns native completion or refusal feedback without exposing source NPC facts, opponent condition, native IDs, or private inventory.

## Reproducible native acceptance

Using `GeneratedArenaSession(root_seed_factory=lambda: 20261107)`, a 10×5 generated equipped Encounter, and the installed npcgen Arena-ready API:

1. The player Beings were `05cd8701-7da1-401f-a751-1f9d38668c9e` and `669233c5-eb49-4b98-a7e9-588318ff3dd1` (the latter was the selected target). The player moved through the existing Sprint destination plan to an adjacent hex; no attack auto-movement or teleport was used.
2. The accepted native action was `MeleeStrike` `4fe5c26e-5723-4036-b866-e878e406882a`, actor `05cd8701-7da1-401f-a751-1f9d38668c9e`, target `669233c5-eb49-4b98-a7e9-588318ff3dd1`, instrument Dagger Object `5656ea88-445f-402d-accc-a0bc2c3021b0`. It was a Thrust starting at Encounter second 1 and resolving at second 5. The instrument remained the same player-owned, held, readied native Object.
3. The initial center distance was 0.9141662868428266 m, below the native calculated reach of 0.9854513513513513 m. Native impact resolution returned `uncertain_path` because generated Beings have no authoritative physical geometry. No damage was committed. This is the actual adopted resolver result; no hit, body geometry, or combat effect was fabricated.

The separate out-of-reach regression confirms the native timing distinction: a well-formed strike can be scheduled while distant and receives the native `out_of_reach` outcome at impact. Unavailable attacks with no equipped Dagger, a test-authored un-readied Dagger, or an invalid handle are refused before native Choice publication. Rejection leaves Encounter time, event history, Choice state, and the session RNG cursor unchanged.

## Browser and terminal trace

The shipped Action selector now binds its native `swing at being` and `thrust at being` catalog rows to `/api/generated/melee-strike`; clicking submits only `{handle, motion}`. A terminal trace event records the UI click, and the server trace records acceptance without printing the target or native Object ID. The page shows the pending duration and then the native outcome.

In an isolated real Chrome session against the loopback server, I generated an equipped Encounter, selected a destination by clicking the map, advanced two native seconds, reached cell `(5, 2)` adjacent to the opponent in `(5, 3)`, and opened the opponent's observer-authorized inspection popup. The terminal trace confirmed the accepted destination and committed native displacement of 1.60312 m followed by 0.814678 m, with arrival at second 2. The browser control surface exposed element-center clicks but no coordinate-targeting for the canvas; its attempted player-marker click landed on the current hex and was traced as `canvas_marker_missed`, so I could not complete the final player-popup button click in that real-browser session. The actual shipped JavaScript button handler was exercised with the JavaScriptCore harness, while the native HTTP/session route and full attack/advance path were exercised end to end in focused integration tests.

## Save/Load

Saving immediately after acceptance and loading into a fresh session preserved the accepted native `MeleeStrike`, exact action/instrument identities, target and observer evidence, pending Choice, schedule, RNG cursor, and the four-second remaining boundary. Advancing the original and restored sessions through second 5 produced the same `uncertain_path` outcome, impact distance, player condition, and RNG state. A second save/load after resolution preserved the same completed action and native result. Tests replace `npcgen.api.arena_ready_being` with a failure during load to prove reconstruction does not regenerate the Being or equipment.

To make this strict native snapshot close over the attack path, the reviewed Arena snapshot allowlist now includes `MeleeStrike`, its completed `MeleeResult`, and the `ReservationReleaseEffect` emitted in the completed boundary; the checkpoint inventory type catalog includes `MeleeResult`. No general checkpoint admission was loosened. The Action is rediscovered from native Event/accepted ChoiceBook state, so browser session metadata does not become an alternate source of truth.

## Verification

- `./.venv/bin/python -m unittest tests.test_arena_melee_attack tests.test_generated_arena_browser tests.test_arena_persistence tests.test_arena_ready_weapon tests.test_arena_ground_pickup tests.test_arena_complete_profiles_and_kits` — **77 tests passed**, 46.123 seconds.
- The focused new tests cover in-range scheduling and impact resolution, out-of-range impact outcome, absent/unready weapon rejection without state changes, shipped JavaScript Action-selector submission, pending Save/Load, continuation to completion, and completed Save/Load.
- `./.venv/bin/python -m py_compile src/arena_browser_session.py src/arena_native_snapshot.py src/checkpoint_inventory.py src/arena_ui_trace.py examples/arena_web.py tests/test_arena_melee_attack.py` — passed.
- `git diff --check` — passed.
- The first normal loopback bind was denied by the sandbox with `PermissionError`; the narrowly scoped loopback Arena server was then started on `127.0.0.1:62197` with an OS-assigned port for the Chrome smoke. The server was stopped after the smoke.

## Changed paths and limits

The implementation changes are in `src/arena_browser_session.py`, `src/arena_native_snapshot.py`, `src/checkpoint_inventory.py`, `src/arena_ui_trace.py`, `examples/arena_web.py`, `tests/test_arena_melee_attack.py`, `tests/arena_browser_js_harness.swift`, and `tests/test_generated_arena_browser.py`.

Implementation and acceptance coverage were committed on `main` as `3e5df25` (`Add native Dagger attacks to generated Arena`). The report closeout is committed separately; nothing was pushed.

Generated Arena Being geometry is still absent, so native strikes may resolve `uncertain_path` even when center distance is within the native reach bound. The real-browser smoke verified generation, movement to adjacent reach, and authorized target inspection, but not the final player-popup strike click because the available CUA canvas interaction could not target the player marker. The shipped JavaScript interaction and HTTP/native progression were verified independently as described above. No Generator code, attack physics, default equipment policy, or push was changed.
