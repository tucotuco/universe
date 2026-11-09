# U-ARENA-005H Engineering Report

## Result

Added a strictly opt-in, checked-in authored Draw scenario to the generated
Arena launcher. It creates one actual native carried Dagger for the generated
player Being, authors one free `right hand`, and attaches the existing native
owner-linked `worn_sheath` draw-location evidence. A fresh browser can inspect
the Dagger and perform the existing two-second native Draw without fixture
mutation after session creation. Normal launches and generated Being templates
remain unchanged.

The scenario is selected explicitly with:

```sh
PYTHONPATH=../npc-generator .venv/bin/python examples/generated_arena_browser.py \
  --port 8001 --authored-draw-scenario
```

The launcher loads only
[`examples/arena_scenarios/ordinary-dagger-draw.json`](../../examples/arena_scenarios/ordinary-dagger-draw.json).
Its strict schema fixes the scenario ID, Dagger type/display name, one empty
right-hand slot, and `worn_sheath` source. The option is mutually exclusive with
the ground-loadout profile. There is no generic browser mutation API or client
input for native IDs, anatomy, location evidence, or arbitrary equipment.

## Native authoring and boundaries

Authoring runs against the private candidate after native Arena generation and
before publication. It resolves the actual player-controlled `BeingInstance`,
constructs the Dagger through the Encounter's native Weapon factory, and checks
the generated player is alive, able to act, has no preexisting possessions,
weapons, armor, or body-part state, and has its own native Arena perception
ledger. It then adds the one explicit hand slot, a single possession entry,
matching native parent custody, and the existing owner-linked draw-location
record. The resulting object is entered in the player's observer-owned current
and historical evidence; it is not added to the opponent's ledger or inventory.
The browser receives opaque entity handles and ordinary authorized character
data, not native object IDs or provenance.

Failed/invalid fixture construction fails before candidate publication, leaving
the prior active Arena and view intact. Regeneration creates a fresh native
Object identity and resets its state to carried/unreadied with the authored
source location. The fixture does not advance Encounter time, create fictional
Action/history events, or add Awareness as a side effect of activation.

The first player Draw uses the existing bounded generated-Arena first-Choice
activation transaction. Activation metadata remains targetless and does not
grant Awareness or bypass ordinary native checks. The Draw Choice still names
the exact possessed Weapon and goes through native custody, location, and free
hand validation before scheduling. Normal Draw timing remains two seconds under
the adopted Encounter r61 rules; the withdrawn r66 one-second proposal is not
used. Existing transactional settlement consumes the source-location evidence
only when readiness commits.

Ordinary ground Pick up remains a distinct custody transfer. It does not create
a hand slot or drawable source, and a free hand alone does not make a picked-up
weapon drawable. The existing native Pick up regression verifies carried but
unreadied state, no source-location evidence, and unavailable Draw. This
scenario does not add the optional second ground Dagger; that separation is
covered by the dedicated ground-Pick-up integration tests. No general anatomy,
stowing, Quick-draw, post-strike re-ready, or default equipment rule was added.

## Browser demonstration

An isolated real Chrome session used a fresh server started on OS-assigned
loopback port `59129`; port 8000 was not opened or modified. I set starting
experience to 10,000 in the Generate form so the generated player met the
scenario's native alive/able-to-act precondition, then completed:

1. Generate the authored scenario and inspect `Drawable Dagger — Dagger` in the
   Entity popup. The Character popup showed it carried and not readied, with
   weight counted once. Character → Actions exposed `Draw (2 s)` and the
   explicit `right hand` selector.
2. Select Draw into the right hand. The browser reported the native Choice was
   accepted and to advance two seconds. At time 1, the popup still showed
   `carried; not readied`; the hand remained empty.
3. Advance one more second. At time 2, native settlement reported success and
   the popup showed `readied in right hand`. The same native Object remained in
   the player's possession with unchanged individual and total carried weight.

This was a fresh local browser/server interaction, in addition to the shipped
JavaScriptCore harness and in-memory HTTP/session route tests. The browser test
also exercised forged and stale handles, failed replacement Generate atomicity,
player-only character projection, and absence of native IDs in requests and
responses. No live port-8000 session was used.

## Verification

All commands ran from the Universe repository root with the installed
`npc-generator` source on `PYTHONPATH`.

| Check | Result |
|---|---|
| `PYTHONPATH=src:examples:tests:<LOCAL_HOME_PATH> python -m unittest test_arena_ready_weapon test_generated_arena_browser test_arena_target_free_activation test_arena_ground_pickup test_action_settlement test_atomic_publication test_interval_staging test_transactional_progression -q` | **289 passed**, 104.332 s unittest time (104.88 s wall). Includes the actual shipped JavaScriptCore harness, native HTTP/session integration, Draw +1/+2 boundaries, ordinary Pick up, movement, scheduling, rollback, and publication regressions. |
| `PYTHONPATH=src:examples:tests:<LOCAL_HOME_PATH> python -m unittest test_checkpoint_inventory -q` | **30 passed**, 13.541 s unittest time (14.06 s wall). |
| `python -m py_compile src/arena_authored_draw_scenario.py src/arena_browser_session.py src/activities.py src/encounter.py examples/generated_arena_browser.py tests/test_arena_ready_weapon.py tests/test_generated_arena_browser.py tests/test_arena_target_free_activation.py` | Passed. |
| `git diff --check` | Passed before final report/commit review. |
| Isolated real Chrome smoke | Passed on `127.0.0.1:59129` with Generate → inspect → Draw → +1 still unready → +2 readied. |

The Arena-local and S7 checkpoint suites were not rerun for this assignment; no
checkpoint code or schemas were changed. Previously observed checkpoint
blockers remain outside this slice: local/S7 reconstruction reports missing
representation for Arena activation and movement-activation fields, and two
multi-process startup cases exit with code 1 without stdout. The passing inventory
suite above does not establish that those broader Arena checkpoint cases are
fixed.

## Commits

Implementation and regression changes were committed in two scoped commits:

- `b0a6ae6 feat(arena): add opt-in authored weapon draw scenario`
- `eb30024 test(arena): verify authored draw through browser routes`

The report is committed separately. Unrelated dirty files and deletions in the
checkout were intentionally excluded.

