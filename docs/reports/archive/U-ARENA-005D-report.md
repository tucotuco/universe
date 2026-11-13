# U-ARENA-005D Engineering Report

## Outcome

The reproduced failures had two independent causes. A generated Human with 0 HP was correctly refused voluntary movement. A positive-HP generated Human was also refused because its native Being race field was blank even though npcgen selected the Human race and the adapter matched the native Human template. The latter was an Arena import defect, not a movement-rule restriction.

The Arena importer now fills an empty native race field from the exact matched template type only when that type is one of the seven adopted movement race categories. Existing explicit native race classifications are preserved, including High elf → Elf. The native movement formula, generated HP, XP, abilities, facing, inventory, and random decisions are unchanged.

Movement preflight refusals now reach the browser as an allowlisted structured object. The UI displays the safe message and category while the server plan remains intact. Terminal tracing records the safe category rather than a raw native code or message. Native IDs, opponent characteristics, source records, and seeds do not enter the response or trace.

## Adopted rules checked

The controlling package is revision 61 with the applicable revisions 62–65 supplements (`docs/encounters/README.md`). Revision 61 specifies the race/Fitness/Run movement basis, fatigue and load multipliers, posture and direction restrictions, and that a Being at 0 HP or below is unconscious and cannot perform voluntary actions. No adopted rule permits a 0-HP Being to move. No movement-rule change was justified.

`src/movement_intent.py` checks voluntary-movement eligibility from the common pre-action snapshot before deriving race-based movement. Therefore the XP-zero Human at 0 HP correctly returned `ineligible_actor`; its later rate factors were never evaluated. For a positive-HP Human, movement input derivation read `BeingDefinition.race`. `src/config/beings.tsv` leaves the Human race column blank, while the npcgen source race and the exact native template type are both Human. Before the repair this produced `unsupported_race: native Being race is unavailable` before any rate calculation. This was a native import/configuration gap.

The checked-in High elf template already defines native race `Elf`; the repair leaves that authoritative category unchanged. The importer only supplies a missing field for the adopted supported categories and does not create a movement formula for other races.

## Deterministic reproduction

All candidates were 5×5, had no generated equipment, and used the installed engine identity:

```text
name: npcgen
version: 2.1.0
rules_hash: sha256:78e8a2bc8e7dc7ba635f8ab6d8bdf8174c35608c9af04b6533cc3d84c46865ff
```

The fixed root seeds were `20261107`–`20261110`; requested starting XP was 0 or 10,000. The player candidate seed is deterministically derived from the root seed and engine identity. For replay, the player seeds were:

| Root seed | Player candidate seed | Generator/native type |
|---:|---:|---|
| `20261107` | `105054029409069709294320349730872231487999665102577054146878790446041676956591` | High Elf / High elf |
| `20261108` | `96563643809641152993789150409896737784712287205528547586694393663766769129985` | Human / Human |
| `20261109` | `38113874106370331454713191339332601102114388186275629686415012166529147386289` | Human / Human |
| `20261110` | `90907265535117973914803161795108978592539915235354885829187843635901601343333` | Human / Human |

The initial-facing seed is independently derived by the existing Arena namespace. A distant destination was selected for each case by taking the most distant center among the non-current cells in the generated map; all plans used `facing_policy=turn`. Terrain and hampering were 1.0, posture was standing, no demanding Action was pending, fatigue was 0 with ability adjustment 0, Run had no explicit native rank (the movement adapter correctly derives rank 0), and represented carried weight was 0 lb.

| Root / XP | Race field before repair | HP | FIT / STR | Initial facing | Target hex / distance | Walk and Sprint before repair |
|---|---|---:|---:|---:|---|---|
| `20261107` / 0 | Elf | 7 | 14 / 13 | 4 | `(4,0)` / 4.751362 m | Both committed; Walk moved 1.6002 m; Sprint reached the exact target at 4.751362 m. |
| `20261108` / 0 | unset | 0 | 8 / 8 | 3 | `(0,0)` / 3.296916 m | Both refused with `ineligible_actor`. |
| `20261109` / 0 | unset | 0 | 8 / 8 | 6 | `(0,4)` / 4.838550 m | Both refused with `ineligible_actor`. |
| `20261110` / 0 | unset | 0 | 8 / 14 | 1 | `(4,4)` / 4.838550 m | Both refused with `ineligible_actor`. |
| `20261108` / 10,000 | unset | 14 | 8 / 8 | 3 | `(0,0)` / 3.296916 m | Both refused with `unsupported_race`. |
| `20261109` / 10,000 | unset | 12 | 8 / 8 | 6 | `(0,4)` / 4.838550 m | Both refused with `unsupported_race`. |
| `20261110` / 10,000 | unset | 5 | 8 / 13 | 1 | `(4,4)` / 4.838550 m | Both refused with `unsupported_race`. |

The two actual native refusal messages were:

```text
ineligible_actor: a Being at 0 HP or below cannot choose voluntary movement
unsupported_race: native Being race is unavailable
```

The first is the adopted rules result. The latter was caused by the empty native race field, despite the source record's verified Human race. After the import correction, the positive-HP Human cases committed both rates. For root `20261108`, XP 10,000, the native rate results were:

| Rate | Native sprint basis | Requested/allowed | Committed displacement |
|---|---:|---:|---:|
| Walk | 4 yd/s | 1 yd/s = 0.9144 m/s | 0.9144 m |
| Sprint | 4 yd/s | 4 yd/s = 3.6576 m/s | 3.296916 m, exact destination arrival |

For the High Elf candidate (native race Elf, FIT 14, STR 13), the derived sprint basis was 7 yd/s, Walk was 1.75 yd/s (1.6002 m/s), and Sprint was 7 yd/s (6.4008 m/s). The target distance limited its committed Sprint displacement to 4.751362 m and arrived exactly. Heavy-load upper bounds were 80 lb for STR 8 and 150 lb for STR 13; all diagnostic cases carried 0 lb. The 0-HP refusal happens before these movement rates can authorize activity.

## Correction and browser refusal behavior

`src/npcgen_arena_adapter.py` now fills the race field only if it is missing and the matched template type names an adopted movement category. Existing explicit classifications such as High elf → Elf remain authoritative. Positive-HP Human Walk and Sprint then derive the expected race/Fitness rate and commit a native one-second displacement. The 0-HP cases still refuse both rates without substituting one rate for another or changing generated statistics.

`src/arena_browser_session.py` maps native refusal codes to a short allowlist of player-facing categories: actor unable to move, rate unavailable, unsupported movement profile/rate, authoritative prerequisite unavailable, or movement prerequisite not met. The response contains only the safe category and explanation. For example:

```json
{
  "error": "Your Being is at 0 HP or below and cannot take voluntary movement under the adopted rules. No Encounter time or position changed; your destination plan remains selected.",
  "movement_refusal": {
    "category": "actor_unable_to_move",
    "message": "Your Being is at 0 HP or below and cannot take voluntary movement under the adopted rules. No Encounter time or position changed; your destination plan remains selected."
  }
}
```

The browser displays the message and stores the safe category on the alert element. Failed native preflight preserves Encounter time, position, facing, accepted movement plan, ChoiceBook, pending actions, event history, Arena RNG, Python global RNG, Awareness, and player-owned perception evidence. Trace output reports `reason=actor_unable_to_move`, not the internal code/message. The served page generation/header is now `005D`.

The shipped JavaScriptCore harness executes the actual inline page script through destination selection, plan acceptance, a native movement step, and a simulated structured refusal. It verifies that the message/category appear, time does not advance, and the plan remains. The same browser test continues to exercise destination-option ordering, popups, Entity inspection, movement, Pick up, and carried inventory.

An isolated Chrome smoke was not possible in this execution environment: binding the local server to `127.0.0.1` on an ephemeral port failed with `PermissionError: [Errno 1] Operation not permitted`. The user's port-8000 server was not contacted or modified. JavaScriptCore and HTTP/session integration coverage passed.

## Validation

| Command | Result | Duration |
|---|---|---:|
| Two focused tests: deterministic candidates and `test_actual_shipped_javascript_handlers_order_sprint_update_before_immediate_advance` | 2 passed; exact native cause, rollback checks, Walk/Sprint displacement, actual inline JavaScript/JavaScriptCore refusal display | 2.783 s |
| `time env PYTHONPATH=../npc-generator:tests .venv/bin/python -m unittest test_generated_arena_browser -q` | 31 passed | 7.852 s test time; 8.152 s elapsed |
| `time env PYTHONPATH=../npc-generator:tests .venv/bin/python -m unittest test_movement_intent test_action_choices test_arena_acquisition_boundary -q` | 78 passed | 4.454 s test time; 4.740 s elapsed |
| `time env PYTHONPATH=../npc-generator:tests .venv/bin/python -m unittest test_npcgen_arena_adapter -q` | 5 passed | 0.204 s test time; 0.379 s elapsed |
| `time env PYTHONPATH=../npc-generator:tests .venv/bin/python -m unittest test_arena_initialization -q` | 5 passed, 2 failed | 0.569 s test time; 0.770 s elapsed |
| `.venv/bin/python -m py_compile src/npcgen_arena_adapter.py src/arena_browser_session.py examples/arena_web.py tests/test_generated_arena_browser.py` | Passed | — |
| `git diff --check` | Passed | — |

The two initialization failures are both the existing assertion at `tests/test_arena_initialization.py:40` expecting `candidate.encounter.awareness == {}` for XP 0 and XP 12,000. Adopted revision 65 requires immediate observer-owned awareness of unobstructed Beings. This stale expectation was not changed as part of this movement assignment. The separate npcgen adapter suite passed.

## Commits and local smoke

- `4d96e54` — `Fix and explain generated Arena movement refusals`
- The engineering report is committed separately after the code commit.
- No changes were made in `npc-generator`; nothing was pushed.

When loopback binding is available, launch an isolated instance with:

```sh
ARENA_TRACE_UI=1 PYTHONPATH=../npc-generator .venv/bin/python examples/generated_arena_browser.py --port 8002
```

Open that port in a fresh Chrome tab, verify the page has generation `005D`, generate at XP 10,000 and select a distant hex. Try Walk and Sprint and advance one second; the native Being should move. Then generate XP 0 with root seed `20261108` using a test-controlled deterministic session and verify the safe 0-HP explanation while time and position remain unchanged. An open Entity/Character modal still blocks map clicks; close it before selecting a destination.
