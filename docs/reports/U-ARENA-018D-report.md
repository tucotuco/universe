# U-ARENA-018D — close-contact lifecycle continuation report

**Status: PARTIAL; U-ARENA-018 remains ACTIVE.** This increment implements the user-adopted automatic Hold-maintenance rule, fixes its Arena presentation, adds a reproducible generated-Arena HTTP/session walkthrough without fixture mutations, and preserves the earlier native close-contact/custody work. It does not meet all of U-ARENA-018's completion criteria; remaining scope is recorded below and in `TASKS.md`.

The installed authorized assignment was supplied as `docs/assignments/U-ARENA-018D-workflow-amended.md`. The canonical `docs/assignments/U-ARENA-018D.md` has now been established from that complete amended assignment and committed as `f0264cc` (`Install canonical U-ARENA-018D assignment`). The amended source remains preserved and unstaged. The standing workflow correction was already committed as `32a698f31ff015ad5885f376044867756f742b0c` (`Clarify persistent assignment workflow`): outcome completion is the stop condition, ACTIVE survives bounded work and handoffs, handoff paths are canonical, and in-scope local commits/report corrections are authorized without repeat approval. Maintained process links checked: 2, 0 broken.

## Adopted Hold rule and implementation

The user selected: **automatic six-second Hold maintenance check; no Action cost**. This is recorded as adopted revision 67 in `docs/encounters/encounters-consistency-decisions-r67.md` and linked from the controlling Encounter package. The adopted rule retains the existing initial-Grapple substitution and independent Grip schedules.

- Transactional progression inserts each due check at its exact six-second boundary as a receipt-bearing native system event. Long steps resolve through their constituent committed seconds so the event joins the ordinary frozen snapshot, deterministic RNG, settlement, publication, replay, and Save/Load path.
- Check-and-schedule is serialized on the scheduler/ChoiceBook lock. Duplicate maintenance events are suppressed. An initial Grapple for the same Grip at its coincident first check continues to substitute for maintenance.
- A strict holder win maintains that Grip; a tie or loss releases only that Grip. A test also proves an ordinary Touch by the holder resolves at the same boundary, showing that automatic maintenance consumes no actor Action capacity.
- Manually declaring Hold is refused; the Arena catalog describes automatic maintenance and does not offer it as a paid Action. The Arena no longer reports a simultaneous system Hold as the player's last chosen Action.

## Reproducible generated-Arena route

Added `test_generated_http_contact_grapple_takedown_save_load_without_fixture_mutations`. It uses the shipped generated Arena HTTP/session routes with root seed `20261100`, 10,000 starting XP, a 5×5 map, unequipped start, no opponent strategy, and explicit Medium size choices for both participants. The choices are supplied at Generate time; no Being skill, position, RNG, equipment, Grip, or Grapple state is altered by the test.

1. Generate, select Walk to cell (0,1), and advance one second.
2. Inspect the perceived opponent, submit Touch, and observe `touched` at second 2.
3. Select the left hand, submit Grab, and observe `success` at second 3 with the next maintenance boundary shown as six seconds away.
4. Submit Grapple, save while its six-second preparation is pending, and load that save in a fresh OS process.
5. Advance the restored process through a successful Grapple at second 9. Through the same session route, declare Takedown to prone and advance to second 15; observe a successful Takedown, `advantaged_takedown_top`, and lying posture. The system Hold check also succeeds at second 15.
6. Save again and verify in another fresh OS process that time, the Grip, Grapple position, and posture persist.

This is real generated initialization plus the shipped HTTP/session handlers and fresh Python processes. An actual Chrome run is separately recorded below; it executes Touch → Grab → Grapple → Takedown and Save. Its file-based Load step was limited by the browser extension’s local-file access setting.

### Actual Chrome walkthrough (12 November 2026)

Chrome opened the local generated Arena. With root seed `20261100`, 10,000 XP, a 5×5 map, unequipped player/opponent, no opponent strategy, and Medium size categories selected in the Generate form, the visible sequence was:

1. Generated the Encounter; chose Walk to cell `(0,1)` and advanced one native second. The player sheet showed the committed position in that cell.
2. Opened the player popup from the blue map marker. Inspected the perceived opposing Being through its visible-entity button, then selected Touch against the opponent. At native second 2 the page showed `Touch resolved: touched.`
3. Selected Grab with the left hand. At second 3 the page showed `Grab resolved: success.` and the player sheet exposed Grapple at the grip’s scheduled check.
4. Selected Grapple; after six committed seconds the page showed `Grapple resolved: success.` at second 9 and displayed the individual left-hand Hold plus Grapple control and next six-second checks.
5. Selected **Takedown → prone**; after six more committed seconds the page showed `Takedown resolved: success.` at second 15 and the player status exposed `advantaged_takedown_top`, confirming the new positional transition.
6. Clicked **Save Encounter**; Chrome showed `Encounter downloaded as a portable native save file.`

The Chrome Load control opened a local file chooser, but `setFiles` was rejected by the Codex Chrome extension because **Allow access to file URLs** is disabled. No Chrome permission was changed. Therefore this confirms the native browser action sequence and Save, not file-based Load in Chrome. The exact generated HTTP/session scenario above verifies Save/Load across fresh OS processes, including pending and resolved contact state.

### Player cancellation control

Added a character-popup **Cancel pending contact Action** control backed by `/api/generated/cancel-contact`. The request contains no Action ID: the server locates only the player’s own latest supported contact Action, permits a sole-member accepted Choice to be undone before it starts or a currently pending Action to be cancelled, and refuses to withdraw a shared multi-member Choice or an already-resolving Action. The API route regression withdraws a future accepted Wrest before its start fence and cancels a later pending Wrest. It verifies no identity disclosure, no RNG draw, unchanged Object custody, and retained Object Grip receipt.

## Earlier 018B/018C work retained in this increment

- Being Grips and Grapple control remain separate receipt-backed identities. Native work includes voluntary one-Grip Release, qualifying Trip, initial Grapple and Escape, bounded Takedown/Reverse/Pin transitions, compatible simultaneous control rerolls, attacker effective-size capacity/bonus, pinned-target restrictions, and earlier-versus-same-second prerequisite-loss behavior. A new progression regression establishes two Grips on separate hands at different times, scripts a loss at the first six-second boundary and a win at the second, and verifies that only the checked Grip changes each time.
- Held-Object Grab creates a receipt-backed Object Grip; Wrest contests the exact same Object and atomically transfers its identity/custody/hand references. Failure/tie preserves custody. Tests cover holder weapon use, same-boundary Disarm/Wrest custody conflict, a second Object Grab refusal, pending Wrest cancellation, and late-publication fault injection restoring raw graph, custody references, receipts, RNG, and refusing Save after the fault.
- Arena status exposes observer-authorized Grip/Object-Grip state with opaque handles. Catalog and view expectations were corrected to current server behavior.

### Compact Action delta matrix from U-ARENA-017

| Action / area | Change in 018B–018D | Current result and noteworthy gap |
| --- | --- | --- |
| Break hold | Added to browser choice flow with exact Grip identity; player can cancel a pending contact Action without disclosing an Action ID. | Native and HTTP cancellation are covered. Full Multi-action continuation with Break hold remains unavailable. |
| Grab | Added held-Object Grab as a separate receipt-backed Object Grip; expanded hand reservation and custody validation. | Same Object ID is carried into Wrest; broader three-Being / simultaneous custody-loss cases remain. |
| Grapple | Added Takedown, Reverse and Pin control-position transitions; multi-attacker effective-size capacity/bonus, incompatible-position rerolls and pinned-target restrictions; automatic no-cost Hold maintenance. | Touch→Grab→Grapple→Takedown is covered in native, HTTP/fresh-process and Chrome runs. Multi-action defense/resource allocation and broader posture/size/interruption combinations remain. |
| Multiple actions | No general declaration/strategy-allocation implementation. | Open: ordered action program, shared defense/skill/ability resources, overlap priorities and penalties. |
| Stun | No new implementation. | Open: specialized unarmed attack/threat, Fortitude save, duration and later-action interruption integration. |
| Subdue | No new implementation. | Open: bludgeon-only subdual damage ledger and recovery/fatigue lifecycle. |
| Touch | Completed a real generated Chrome opposed Touch as the opening step of the accepted sequence. | Bounded unwilling-Being path works; willing-recipient consent and concurrent-action variants remain. |
| Trip | Added receipt-identity eligibility, defender Strength/Dexterity selection, adopted size/stability terms and later-second attack cancellation. | Bounded success/failure/tie and same-second nonretroactivity are covered; broader body stability evidence remains unsupported where absent. |
| Wrest | Added same-Object custody transfer, failure/tie and reservation conflicts; injected late-publication rollback and player cancellation coverage. | Same-ID custody and fresh-process restoration are covered; broader simultaneous three-Being outcomes remain fail-closed where the adopted winner policy is unspecified. |
| Arena / persistence | Added observer-authorized opaque target handles and contact status; pending and resolved save continuation. | Chrome Save and generated fresh-process Save/Load pass. Chrome file picker Load remains blocked by extension local-file permission. |

## Verification

All commands use the preserved `.venv`, `-B`, and no custom pre-import shim.

| Command | Result |
| --- | --- |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_action_evaluation` | 75 passed, 79.098 s |
| `.venv/bin/python -B -m unittest tests.test_action_evaluation.TestActionEvaluation.test_staggered_automatic_maintenance_keeps_each_grip_independent -v` | 1 passed, 8.182 s |
| `.venv/bin/python -B -m unittest tests.test_action_evaluation` | 76 passed, 79.371 s (includes the staggered two-Grip regression) |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_generated_arena_browser` | 48 passed, 67.330 s |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_native_object_wrest` | 9 passed, 11.691 s (includes accepted-future and pending Wrest cancellation through the new player-facing HTTP route) |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_native_object_wrest` | 10 passed, 30.096 s (adds three-Being earlier-Disarm custody-loss invalidation of an accepted future Wrest; see fixture finding below) |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_atomic_publication` | 70 passed, 49.361 s |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_transactional_progression tests.test_encounter_inspection` | 104 passed, 63.338 s |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_generated_http_contact_grapple_takedown_save_load_without_fixture_mutations` | 1 passed, 9.200 s (also in the 48-test browser module) |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_grab_selector_http_receipt_and_fresh_process_hold_continuation` | 1 passed, 24.216 s (also in the 48-test browser module) |
| Automatic Hold tie releases only its Grip | 1 passed, 2.027 s |
| Checkpoint inventory/receipt/restore cohort | 42 tests: 5 semantic-closure failures and 1 private-RNG-owner error; 19.521 s. The five closure refusals were reproduced at the verified published baseline in 018B; the private-RNG test is unchanged baseline behavior. No closure or private-RNG validation was weakened. |
| `git diff --check` | Passed at the last check; rerun before commit. |

The checkpoint cohort failure details remain in the earlier 018B/018C reports. They are independent of the Hold work; the passing Arena fresh-process scenario above exercises the supported generated-Arena persistence path.

The bare `.venv/bin/python -B -m unittest tests.test_native_object_wrest` invocation previously failed one import because the repository's test helper `test_interval_staging` is a top-level module; the standard configured `PYTHONPATH=tests:src:examples` resolves it without a pre-import shim. The earlier three-Being Disarm probe's `uncertain_path` was caused by fixture context, not an adopted-rule gap: it used a mapless Encounter, whose physical-path classifier intentionally retains non-Arena behavior and therefore treated held, positionless Weapons as unknown path entities. The corrected regression uses the adopted Arena hex descriptor, explicit Being geometry and valid facings. It now accepts a future Wrest after a successful Object Grab, resolves a third Being's earlier Disarm, and proves the stale Wrest ends `not_held` before any RNG draw; the same Object is dropped at the holder's position and all hands/receipts are cleared. No production path semantics or geometryless generated Being defaults were changed.

## Remaining scope and task state

`TASKS.md` remains canonical and retains U-ARENA-018D as ACTIVE. U-ARENA-018 and U-ACT-012 remain PARTIAL; U-ACT-013 (declared Multiple actions) remains OPEN. The new progression case verifies staggered no-cost maintenance remains independent per hand/Grip, and the new three-Being regression verifies earlier custody loss invalidates an accepted future Wrest. Remaining independent work includes broader control/posture/size cases, competing custody combinations, defender-side browser action outcomes, and Chrome file-based Load verification (the extension denied local-file access). Multiple actions remain unimplemented: the adopted rules specify prerequisite, ordered design, timing, shared defense allocation, per-action priority and the `3(n-1)` penalty table, so this is an implementation gap rather than an unresolved semantic rule. The distinct rule phrase that still needs a capacity interpretation is willing Touch while the actor is performing another Action: the adopted Touch rule allows it without Multi-action only “if” the actor has the capacity, but does not define which concurrent action combinations qualify. That narrow question is deferred until independent implementation work is exhausted. U-ACT-020 Stun and U-ACT-021 Subdue remain OPEN; no new unarmed damage, timed condition, subdual track, or recovery framework was added. Force-based Pull remains outside this close-contact increment because its adopted force-to-motion mapping is explicitly unspecified.

No ideas-inbox entry was present for this scope. The generated outstanding-only Encounter to-do was refreshed using the documented tool; the working-draft TOC tool reports its older revision-60 target already current and did not modify the adopted revision-61 source. No `.venv`, ignored `legacy/`, local saves, independent `npc-generator`, backups, or unrelated user files were changed. The supplied assignments and unrelated report remain untracked. No push, reset, clean, or history rewrite was performed.

**Local functional commits:** `719c8ca` (`Add automatic Hold maintenance and Arena walkthrough`); `a376aa7` (`Expose player cancellation for contact actions`); `2d635ed` (`Verify staggered independent Hold maintenance`). **Publication:** not authorized; no push.
