# U-ARENA-004T engineering report

## Findings and diagnosis

The generated Arena page wires its map `click` listener to a nearest-cell hit test and posts the chosen cell, rate, and facing policy to `/api/generated/destination`. A successful non-current destination creates the server-owned movement plan; `/api/generated/advance` then invokes the existing one-second native Encounter step. The browser page derives the marker and occupancy from the returned player projection.

I reproduced a misleading no-op branch in the actual server flow. Clicking the center of the player's current hex returns `already_at_destination`, clears the plan, and correctly leaves Advance disabled because there is no displacement to perform. Before this change, the UI described that result as “Destination accepted,” while the no-plan status did not explain that the user needed to choose another hex. The click handler now names the current-hex case explicitly, and page instructions explain that the selected destination must differ from the current position. This is a demonstrated interaction defect that could account for the report; the user's exact browser sequence was not captured, so it is not evidence that this was their specific click.

For a different in-footprint destination, the existing native path is supported: accepted plan, one-second `Encounter.step(1)`, committed nonzero displacement, and exact arrival. No movement rules or transaction semantics were changed. If the user's marker still does not move after selecting a different destination and seeing “Destination plan accepted,” the added terminal trace will identify whether the advance click arrived, the server had a plan, native time advanced, and the authoritative player position changed.

## Changes

- Added opt-in `ARENA_TRACE_UI=1` tracing. Default mode remains quiet and omits the diagnostic endpoint from the page.
- Traces finite, schema-checked UI events (Generate, hex, rate, facing policy, Advance, Stop, Run, and name-apply clicks), request/response outcome and bounded correlation IDs, validated Generate XP/map dimensions, destination choices, and validation/refusal classifications.
- For Advance, traces pre/post Encounter time, the controlled player's native Cartesian position and derived hex, committed displacement, movement outcome, plan parameters, and remaining distance where available. Missing-plan refusal, zero displacement, arrival, rollback, and unexpected exceptions have separate outcomes. A failed step is never reported as committed.
- Client events are best-effort and fire-and-forget; they do not gate or reorder the movement request. The trace endpoint is opt-in, loopback-origin constrained, allowlisted, schema checked, rate/event bounded, and does not mutate Arena state. Logs exclude NPC source, opponent state/identity, personal names, secrets, seeds, and request bodies. Trace stream failures are swallowed so diagnostics cannot affect simulation behavior.
- Corrected current-hex feedback and documented the select-destination/accepted-plan/Advance sequence in the page.

Example terminal trace from a server-session exercise (the position and values are illustrative of that run):

```text
[arena-ui] seq=1 event=generate_clicked
[arena-http] req=1 client_seq=1 action=generate status=accepted http=200 xp=0 map=5x5
[arena-ui] seq=2 event=rate_selected rate=walk
[arena-ui] seq=3 event=facing_policy_selected facing_policy=turn
[arena-ui] seq=4 event=canvas_hex_selected cell=(4,0)
[arena-http] req=2 client_seq=4 action=destination status=accepted http=200 cell=(4,0) rate=walk policy=turn plan=accepted
[arena-ui] seq=5 event=advance_clicked
[arena-native] req=3 client_seq=5 action=advance status=committed time=0->1 position=(1.31982,4.572,0)->(2.11992,3.18619,0) cell=(1,4)->(2,3) displacement_m=1.6002 movement=moving plan=cell=(4,0),rate=walk,policy=turn remaining_m=3.15116
[arena-http] req=3 client_seq=5 action=advance status=accepted http=200
```

## Browser verification boundary and local smoke procedure

The shipped JavaScript event wiring was inspected and checked by source-level regression assertions, but was not executed in a real browser in this environment. No JavaScript runtime or headless browser automation package was available; the browser-control provider reported its native pipe unavailable, and binding `127.0.0.1` failed with `PermissionError: [Errno 1] Operation not permitted`. Accordingly, this report does not claim a real-browser smoke test or resolution of the specific user session. The in-memory HTTP handler tests remain useful server integration evidence, not a substitute for browser execution.

On the user's Mac, from the Universe repository root, launch:

```sh
ARENA_TRACE_UI=1 PYTHONPATH=../npc-generator .venv/bin/python examples/generated_arena_browser.py
```

Open the loopback URL printed by the server. Generate an Encounter, set the rate and facing policy, click a hex other than the player's current hex, and confirm “Destination plan accepted by the server” and that Advance is enabled. Click **Advance 1 second**. A working movement step should print a `[arena-ui] ... event=advance_clicked` line, an `[arena-native] ... status=committed time=N->N+1 ... displacement_m=... movement=moving` line with a changed position, and an accepted `[arena-http]` line. Continue to verify exact arrival. Clicking the current hex instead should explicitly say it is the current position and leave Advance disabled. If movement still fails, share the terminal lines for the hex selection, destination response, Advance click, native outcome, and HTTP response.

## Verification

All commands were run from the repository root:

| Check | Result |
|---|---|
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_generated_arena_browser.py'` | 18 passed (5.165 s) |
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_movement_intent.py'` | 20 passed (4.213 s) |
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_arena_initialization.py'` | 7 passed (0.750 s) |
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_arena_hex_map.py'` | 4 passed (0.001 s) |
| `python -m py_compile src/arena_ui_trace.py src/arena_browser_session.py examples/arena_web.py examples/generated_arena_browser.py` | passed |
| `git diff --check` | passed |
| Local browser/loopback execution | not available: loopback bind returned `PermissionError: [Errno 1] Operation not permitted`; no actual browser event was executed |

Trace-on regressions exercise current-hex no-op feedback, source-level shipped-page wiring, plan acceptance, missing-plan and malformed/out-of-footprint refusals, concurrent destination requests, injected native-step rollback, committed movement and exact arrival, trace privacy, rate limiting, cross-origin refusal, and trace-off behavior. No full suite was run. No NPC Generator files were changed, and nothing was pushed.

## Commits

Implementation and tests: `9390255 Trace generated Arena movement interactions`. The report is committed separately.
