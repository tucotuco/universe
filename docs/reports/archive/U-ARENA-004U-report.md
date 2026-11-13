# U-ARENA-004U engineering report

## Root cause

The user's trace establishes the UI/server mismatch. The first click accepted a movement plan with `rate=walk`; the later Sprint selector event was traced, but the page sent no plan update. Advance therefore used the still valid server plan and native Encounter correctly stepped at Walk. This was a browser workflow defect, not evidence of a Sprint calculation error in the native movement evaluator.

## Fix

The existing `/api/generated/destination` operation already provides validated, atomic plan replacement. On either rate or facing-policy change, the page now submits the current accepted destination together with both selected settings. If there is no accepted destination plan, the selector only changes the pending UI choice; the next map click submits those choices with its destination.

The page serializes destination clicks, selector-driven plan replacements, Stop, Generate, Run, rename, and Advance through one mutation queue. Thus an immediate Advance waits for the preceding option request and uses its accepted server plan. Responses update the displayed accepted settings only when returned; the status separates `server accepted` settings from currently `selected` settings and shows when an update is pending. Failed updates refresh the effective server plan, state the retained rate/policy, and hold Advance until the settings are successfully applied or a different destination is accepted. Stop and regeneration are ordered behind earlier edits and clear the pending failure state.

No movement rate, facing rule, geometry, speed cap, or native transaction behavior changed. A rejected destination update leaves the last accepted plan intact because validation precedes plan replacement in the existing session operation.

## Request-order and native-step evidence

The shipped page's JavaScript was executed in a JavaScriptCore harness with a mocked DOM/canvas and fetch boundary. It exercised the actual Generate button handler, hex canvas hit-testing/click handler, rate selector change handler, and Advance button handler. The harness changed to Sprint before choosing a destination (pending choice only), accepted the destination at Sprint, changed the active plan to Walk, changed it back to Sprint, and invoked Advance immediately without awaiting the final selector handler. The observed state-changing request order was:

```text
POST /api/generated/destination  rate=sprint  # selected before destination
POST /api/generated/destination  rate=walk    # change to active plan
POST /api/generated/destination  rate=sprint  # final change to active plan
POST /api/generated/advance     seconds=1
```

The first change while there was no plan sent no destination request. Each active-plan change retained the same destination. The mock page response reported `server accepted sprint/turn`, and the mocked Advance response followed the accepted plan update. Separate native server tests exercised both destination-then-Sprint and Sprint-then-destination. For destination-then-Sprint, terminal tracing recorded the accepted replacement before the native step:

```text
[arena-ui] seq=2 event=rate_selected rate=sprint
[arena-http] req=3 client_seq=2 action=destination status=accepted http=200 cell=(9,0) rate=sprint policy=turn plan=accepted
[arena-ui] seq=3 event=advance_clicked
[arena-native] req=4 client_seq=3 action=advance status=committed time=0->1 position=(2.90361,4.572,0)->(7.65497,0.9144,0) cell=(3,4)->(9,0) displacement_m=5.99612 movement=arrival plan=cell=(9,0),rate=sprint,policy=turn remaining_m=0
[arena-http] req=4 client_seq=3 action=advance status=accepted http=200
```

These native results come from a deterministic generated test candidate at 10,000 starting XP. The plan-only changes left Encounter time, position, event history, ChoiceBook, Awareness, and the Arena RNG cursor unchanged. Tests also verify that an invalid update preserves the previous server plan and that the player projection and logs omit the hidden participant.

## The one-yard displacement

The reported `0.9144 m` is exactly one yard, but that step was explicitly accepted and logged as `rate=walk`; Sprint was never the native plan for that boundary. The trace therefore cannot show that Sprint was capped. The native speed depends on the generated Being's current attributes, Run rank, fatigue, encumbrance, posture, facing-relative direction, and applicable action/environment limits. Those evaluated inputs and the native requested-versus-allowed rate are not present in the supplied trace.

The adopted evaluator can produce a one-yard-per-second limit in supported cases: crouching, non-forward movement, and movement during another demanding Action. The focused native movement tests verify those one-yard caps. They also verify that, for their generated standing Being under explicit unhampered forward/no-demand premises, Walk is 1.75 yards/second and Sprint is 7 yards/second. A Walk result of one yard can also arise from that Being's uncapped category formula; the single displacement does not distinguish that from a cap. In the supplied case, the plan was turn-and-move and the Arena's generated posture/environment premises are standing and unobstructed, so the trace does not establish any of those caps as the cause. No legitimate native restriction was removed. The corrected trace will show Sprint as the accepted rate on the next step; actual distance may still be lower when an adopted native limit applies.

## Browser verification boundary

The actual shipped inline JavaScript ran in JavaScriptCore with simulated DOM, canvas, and network responses. The server route and native stepping were separately tested through the repository's handler/session boundary. A live Safari/Chrome interaction and live loopback request could not run in this environment: binding `127.0.0.1` fails with `PermissionError: [Errno 1] Operation not permitted`. The JavaScript harness does not claim a visual browser test or real network integration.

On the user's Mac, launch from the Universe repository root:

```sh
ARENA_TRACE_UI=1 PYTHONPATH=../npc-generator .venv/bin/python examples/generated_arena_browser.py
```

Generate XP 10000 with a 10×5 map, click a destination, change Walk to Sprint without clicking another hex, and immediately click **Advance 1 second**. Expect the rate-selection line, an accepted destination update retaining the clicked hex with `rate=sprint`, then an Advance line whose native plan says `rate=sprint`. The page should show the server-accepted Sprint/turn settings before the step. Repeat with a facing-policy change. A one-yard step should be evaluated against the Being's current native limits rather than assumed to indicate a stale plan.

## Verification

| Command | Result |
|---|---|
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_generated_arena_browser.py'` | 23 passed (6.758 s) |
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_movement_intent.py'` | 20 passed (4.396 s) |
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_arena_initialization.py'` | 7 passed (1.253 s) |
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_arena_hex_map.py'` | 4 passed (0.001 s) |
| `python -m py_compile examples/arena_web.py src/arena_browser_session.py tests/test_generated_arena_browser.py` | passed |
| `git diff --check` | passed |
| Live loopback/browser smoke | not run; loopback bind was blocked by the environment; see limitation above |

The browser-page suite includes the JavaScriptCore handler exercise and direct HTTP/native regressions for accepted option updates, both selection orders, rapid mixed changes followed by Advance, no-plan behavior, invalid-update preservation, stop, arrival, failed regeneration, rejected advancement, privacy, and transactional rollback. No full suite was run. No NPC Generator files were changed.

## Commits

Implementation and tests: `ec0a695 Synchronize active Arena movement options`. This report is in the following documentation commit. No push was performed.
