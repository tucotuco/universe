# U-ARENA-005C Engineering Report

## Finding and root cause

The port-8000 Chrome tab was not running the current checked-out Arena page. Its loaded JavaScript still contained the earlier static popup bindings `$('renameEntity').onclick = ...` and `$('pickup').onclick = ...`. Those elements are created only when an Entity popup is rendered, so at page startup the handler assignment dereferenced a null element. Chrome recorded:

```text
TypeError: Cannot set properties of null (setting 'onclick')
    at http://127.0.0.1:8000/:42:26
```

That exception stopped the inline script before it registered the map listener. This matches the user's report: a map click had no destination request and no canvas event to print. The loaded page also lacked the current `renderActionSelector` function and the 005C page-generation marker, confirming it was an older page/server instance. The current checkout creates popup-only controls and their handlers together when rendering each popup; the current page initializes without a script exception and records `page_script_ready`.

There is a second, expected event boundary: the Entity/Character `<dialog>` is modal. In the isolated browser, a click on the map while the Character dialog was open left `dialog.open` and `dialog.matches(':modal')` true, left the accepted movement plan unchanged, and produced no canvas trace. A modal backdrop receives that pointer input before the canvas listener, so no canvas event can be printed for a click it blocks. The dialog and map instructions now say to close the dialog before returning to the map.

The port-8000 process and its live browser tab were left untouched. The old server must be stopped and restarted for the checkout's current page to replace its in-memory older page. The generated page now sends `Cache-Control: no-store` and `X-Arena-UI-Generation: 005C`, and includes a matching meta marker so a later browser reload can be checked against the served UI generation.

## Changes

- Added opt-in, fixed-schema browser traces for page readiness and script errors, canvas click arrival, modal guard, player/entity marker hits, marker misses, hex selection misses, destination-queue enqueue, and destination request acceptance/refusal. These events report no pixel coordinates, names, opaque handles, native IDs, raw exception text, or hidden state. The existing server HTTP and native-step trace remains correlated by client sequence.
- Kept marker clicks as inspection and blank-hex clicks as destination selection. The click handler reports the branch it takes, serializes the destination request through the existing mutation queue, and reports acceptance only after the response arrives. Server validation and native movement remain authoritative.
- Added concise Close-dialog guidance and no-store/version response headers for the generated Arena page.
- Strengthened the shipped JavaScriptCore harness so it models clicks behind an open native modal as blocked instead of directly invoking the canvas listener. It now verifies Character Actions inspection and Close, player/opponent/Object marker inspection, Object-popup dismissal, destination selection, Walk/Sprint and turn/maintain updates before Advance, pickup/inventory refresh, and a fresh no-Run movement-only activation with a one-second displacement.
- No Encounter rules, movement rates, facing rules, movement physics, Action definitions, perception, pickup, or Generator code changed.

## Reproduction and browser evidence

An isolated traced server was run on `127.0.0.1:8002` with deterministic root seed `20261107`. The actual shipped page loaded with generation `005C` and no page JavaScript exception. Generate created a fresh 5×5 Arena at time zero. A blank map click selected hex `(2,2)` and was accepted as a movement-only activation; no Run endpoint or Action was used. Changing Walk to Sprint, changing facing to maintain, and restoring Walk/turn each updated the accepted server plan before Advance.

The terminal trace showed this ordered path:

```text
[arena-ui] seq=1 event=page_script_ready
[arena-ui] seq=2 event=generate_clicked
[arena-http] req=1 client_seq=2 action=generate status=accepted http=200 xp=0 map=5x5
[arena-ui] seq=3 event=canvas_click_received
[arena-ui] seq=4 event=canvas_marker_missed
[arena-ui] seq=5 event=canvas_hex_selected cell=(2,2)
[arena-ui] seq=6 event=destination_request_queued cell=(2,2) rate=walk policy=turn
[arena-http] req=2 client_seq=6 action=destination status=accepted http=200 cell=(2,2) rate=walk policy=turn plan=accepted
[arena-ui] seq=7 event=destination_request_accepted cell=(2,2)
[arena-ui] seq=8 event=rate_selected rate=sprint
[arena-http] req=3 client_seq=8 action=destination status=accepted http=200 cell=(2,2) rate=sprint policy=turn plan=accepted
[arena-ui] seq=9 event=facing_policy_selected facing_policy=maintain
[arena-http] req=4 client_seq=9 action=destination status=accepted http=200 cell=(2,2) rate=sprint policy=maintain plan=accepted
[arena-ui] seq=10 event=rate_selected rate=walk
[arena-http] req=5 client_seq=10 action=destination status=accepted http=200 cell=(2,2) rate=walk policy=maintain plan=accepted
[arena-ui] seq=11 event=facing_policy_selected facing_policy=turn
[arena-http] req=6 client_seq=11 action=destination status=accepted http=200 cell=(2,2) rate=walk policy=turn plan=accepted
[arena-ui] seq=12 event=advance_clicked
[arena-native] req=7 client_seq=12 action=advance status=committed time=0->1 position=(1.31982,4.572,0)->(1.84361,3.05995,0) cell=(1,4)->(2,3) displacement_m=1.6002 movement=moving plan=cell=(2,2),rate=walk,policy=turn remaining_m=0.819075
[arena-http] req=7 client_seq=12 action=advance status=accepted http=200
```

The browser showed Encounter time `1`, native position changed from `(1.3198227153674846, 4.572, 0)` m to `(1.843611117300937, 3.0599531257265866, 0)` m, and the accepted plan remained visible with `0.819075` m remaining. This is the complete blank-hex-click → accepted plan → option synchronization → native one-second movement path.

A separate random-seed browser smoke generated a Being whose selected Sprint and then Walk movement intents both failed native prerequisites. Each request returned HTTP 409, and the terminal trace confirmed rollback at time `0` with no position change (`reason=MovementIntentRefusal`). A second random `10000`-XP scenario also refused Walk. I did not change native movement rules to force those cases to succeed; the deterministic supported case above and existing native boundary tests demonstrate the supported path. The UI reports the existing rollback message, and the bounded terminal trace exposes the exception class without raw exception content.

## Verification

- `PYTHONPATH=tests .venv/bin/python -m unittest test_generated_arena_browser` — **30 tests passed** in 6.584 seconds. Includes the JavaScriptCore execution of the shipped script, modal/event harness, cache/version contract, and HTTP/native movement tests.
- `PYTHONPATH=tests .venv/bin/python -m unittest test_arena_ground_pickup` — **9 tests passed** in 5.862 seconds.
- `PYTHONPATH=tests .venv/bin/python -m unittest test_movement_intent test_action_choices` — **77 tests passed** in 4.389 seconds.
- `PYTHONPATH=tests .venv/bin/python -m unittest test_arena_acquisition_boundary` — **1 test passed** in 0.418 seconds.
- From `tests/`: `PYTHONPATH=../src:.. ../.venv/bin/python -m unittest test_perception` — **7 tests passed** in 0.045 seconds. The command emitted environment warnings about pyenv shim permissions and the relative virtualenv prefix; tests passed.
- `.venv/bin/python -m py_compile src/arena_browser_session.py src/arena_ui_trace.py examples/arena_web.py tests/test_generated_arena_browser.py tests/test_arena_acquisition_boundary.py tests/test_movement_intent.py` — passed.
- `git diff --check` — passed.
- Isolated Chrome loopback smoke on port 8002 — passed, including modal close, actual canvas click, request/server trace, option updates, and native nonzero movement. The user's port-8000 tab was not modified. No full repository suite or checkpoint suite was run.

## Manual restart and verification

In the terminal that owns the old port-8000 Arena process, stop it with Ctrl-C and start the current checkout with tracing enabled:

```sh
ARENA_TRACE_UI=1 PYTHONPATH=../npc-generator .venv/bin/python examples/generated_arena_browser.py --port 8000
```

Reload the Arena tab and verify the served page has `X-Arena-UI-Generation: 005C` (or `<meta name="arena-ui-generation" content="005C">`) and that the terminal prints `event=page_script_ready`. Generate an Encounter, close Character/Entity dialogs, click an empty distant hex, verify `destination_request_queued` then an accepted destination plan, select rate/facing, and press **Advance 1 second**. An open modal intentionally blocks map clicks; its Close button and the visible dialog hint restore map interaction.

## Commit and workspace disposition

- `f6a4532` — `Trace and restore Arena map destination interactions`.
- This report is committed separately. Existing unrelated deletions and untracked files were preserved; no push was performed.
