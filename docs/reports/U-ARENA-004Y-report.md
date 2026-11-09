# U-ARENA-004Y Engineering Report

## Outcome

The generated Arena now lets the player edit the session display name of any Entity in the player's current observer projection, including the opposing Being and ground or carried Objects. The server keeps the override in `GeneratedArenaSession._display_names`, keyed internally by the native Entity ID. The browser sends only its observer-authorized opaque handle and the requested name. Each edit re-resolves that handle and checks the player's current `ArenaPerceptionLedger` evidence before applying the override.

The override is presentation-only. It does not update native names or IDs, Generator source records, perception evidence or history, Awareness, Choices, Encounter time, or RNG state. Successful regeneration clears overrides along with the prior candidate and handles; failed generation leaves all of them intact. The existing name validator limits names to 1–40 trimmed characters. Rendered list and inspector text use `textContent`; map labels use canvas text drawing. Existing player and Encounter name editing remain intact.

The server returns the selected projection after rename, so list labels, marker labels, and the inspector refresh from the same projected name. A carried Object remains selectable, has no ground position/marker, and retains its edited session display name. Rename tracing records operation/status and safe Entity category/type only; it omits the proposed name, native IDs, source item IDs, and request body.

## End-to-end evidence

`test_actual_shipped_javascript_handlers_order_sprint_update_before_immediate_advance` runs the shipped page's JavaScript in the JavaScriptCore mock-DOM/fetch harness with the explicit fixture profile. It exercises generation at 10,000 XP on a 10×5 map, map-marker inspection, rename, a background hex click kept distinct from marker inspection, rate changes after destination selection, serialized option updates before Advance, exact target cell arrival in the harness state, same-hex Pick up, and carried-state inspection with the renamed display name. The harness verifies that requests carry the opaque handle/name only. The harness supplies mock endpoint behavior for this UI wiring check; authoritative rename authorization and native movement/pickup are separately verified by the direct server/session tests.

`test_http_visible_object_selection_pickup_and_custody_use_native_action` drives the handler/session path with an explicitly authored Dagger, moves to the item's cell through native movement, verifies exact committed arrival, and resolves the native PickUpAction. It checks that the carried Object retains its native ID and possession relation, its ground position is removed, and its display name remains editable without changing its native name. `test_display_name_overlay_is_safe_observer_scoped_and_replacement_atomic` verifies time-zero opponent visibility, no default ground equipment, unchanged observer evidence/history, Awareness, Choices, time, and RNG across rename, invalid and stale request refusals, no identity/source disclosure, retained override and candidate after failed generation, and cleared override after successful replacement.

## Validation

- `PYTHONPATH=tests .venv/bin/python -m unittest test_generated_arena_browser test_arena_ground_pickup test_movement_intent` — **54 tests passed** in 12.210 seconds.
- Focused JavaScriptCore rerun: `PYTHONPATH=tests .venv/bin/python -m unittest test_generated_arena_browser.TestGeneratedArenaBrowser.test_actual_shipped_javascript_handlers_order_sprint_update_before_immediate_advance -v` — **1 test passed** in 1.096 seconds.
- `.venv/bin/python -m py_compile src/arena_browser_session.py src/arena_ui_trace.py examples/arena_web.py tests/test_generated_arena_browser.py` — passed.
- `git diff --check` — passed.

An additional adjacent exploratory run included `test_arena_destination_movement_blocker` and `test_generated_arena_spot_readiness`: **59 tests ran, with 3 failures**. Those failures are stale expectations that conflict with already adopted Arena contracts: two blocker tests expect the generated destination route to be absent and native passive Awareness to remain empty; one Spot-readiness test expects Encounter Awareness to remain empty. The current-contract browser, native pickup, and movement suites above pass. These failures are not caused by display-name overlays.

The activated-Arena checkpoint boundary remains strict and unchanged. The previous U-ARENA-004X checkpoint run recorded **39 tests: 31 passed, 6 errors, 2 failures**: six exact-closure refusals (`ArenaStateRejected: Encounter has an unrepresented native field`) and two HTTP continuation subprocesses that exited before readiness. That suite was not rerun for Y because these changes do not alter checkpoint state or serialization. No checkpoint vocabulary or reconstruction behavior was changed.

No live browser/listener session was claimed. U-ARENA-004X documented that the local HTTP subprocesses could not reach their readiness line in this environment; this increment verified the shipped JavaScriptCore handlers and the actual direct server/session pathways instead.

## Manual macOS playtest

From the Universe repository, launch the browser UI with the explicit equipment fixture:

```sh
ARENA_TRACE_UI=1 PYTHONPATH=../npc-generator .venv/bin/python examples/generated_arena_browser.py --ground-loadout-profile tests/fixtures/arena/test_ground_loadout_profile.json
```

Generate **10,000 XP**, **10 columns**, and **5 rows**. Confirm the opposing Being and ground Objects appear. Click a Dagger marker to inspect it, enter a display name and apply it, then click the background of its hex to select a destination. Change Walk to Sprint after selecting the destination and confirm the accepted plan updates before advancing. Advance until the exact destination is reached, choose **Pick up**, and advance one second to resolve the native Action. Confirm the ground marker disappears and the carried Object shows the edited display name. Stop or choose another destination to confirm the existing rate-update behavior remains available. Terminal tracing should show the named UI operations, accepted/refused status, native step, movement result, and pickup outcome without private identifiers or raw values.

## Scope and commits

No NPC Generator source, combat rules, geometry, collision, perception rules, pickup rules, readying rules, equipment defaults, or checkpoint code was changed. Existing movement, pickup, observer isolation, and transactional behavior remain authoritative. The manual live-browser playtest remains to be run in an environment with an available local browser listener.
