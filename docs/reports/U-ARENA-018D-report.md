# U-ARENA-018D — close-contact lifecycle continuation report

**Status: PARTIAL; U-ARENA-018 remains ACTIVE.** This increment implements the user-adopted automatic Hold-maintenance rule, fixes its Arena presentation, adds a reproducible generated-Arena HTTP/session walkthrough without fixture mutations, and preserves the earlier native close-contact/custody work. It does not meet all of U-ARENA-018's completion criteria; remaining scope is recorded below and in `TASKS.md`.

The installed assignment was the user-provided `docs/assignments/U-ARENA-018D-workflow-amended.md`; the referenced canonical `docs/assignments/U-ARENA-018D.md` is absent. The amended assignment was treated as the live scope and remains unstaged. The standing workflow correction was already committed as `32a698f31ff015ad5885f376044867756f742b0c` (`Clarify persistent assignment workflow`): outcome completion is the stop condition, ACTIVE survives bounded work and handoffs, handoff paths are canonical, and in-scope local commits/report corrections are authorized without repeat approval. Maintained process links checked: 2, 0 broken.

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

This is real generated initialization plus the shipped HTTP/session handlers and fresh Python processes. It is **not** a full interactive Chrome walkthrough. The earlier Chrome session opened and inspected a generated Arena, but canvas marker targeting through the available automation did not reliably open the player selector, so no Chrome action/Save/Load sequence is claimed.

## Earlier 018B/018C work retained in this increment

- Being Grips and Grapple control remain separate receipt-backed identities. Native work includes voluntary one-Grip Release, qualifying Trip, initial Grapple and Escape, bounded Takedown/Reverse/Pin transitions, compatible simultaneous control rerolls, attacker effective-size capacity/bonus, pinned-target restrictions, and earlier-versus-same-second prerequisite-loss behavior.
- Held-Object Grab creates a receipt-backed Object Grip; Wrest contests the exact same Object and atomically transfers its identity/custody/hand references. Failure/tie preserves custody. Tests cover holder weapon use, same-boundary Disarm/Wrest custody conflict, a second Object Grab refusal, pending Wrest cancellation, and late-publication fault injection restoring raw graph, custody references, receipts, RNG, and refusing Save after the fault.
- Arena status exposes observer-authorized Grip/Object-Grip state with opaque handles. Catalog and view expectations were corrected to current server behavior.

## Verification

All commands use the preserved `.venv`, `-B`, and no custom pre-import shim.

| Command | Result |
| --- | --- |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_action_evaluation` | 75 passed, 79.098 s |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_generated_arena_browser` | 48 passed, 62.235 s |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_native_object_wrest` | 9 passed, 12.618 s |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_atomic_publication` | 70 passed, 49.361 s |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_transactional_progression tests.test_encounter_inspection` | 104 passed, 63.338 s |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_generated_http_contact_grapple_takedown_save_load_without_fixture_mutations` | 1 passed, 9.200 s (also in the 48-test browser module) |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_grab_selector_http_receipt_and_fresh_process_hold_continuation` | 1 passed, 24.216 s (also in the 48-test browser module) |
| Automatic Hold tie releases only its Grip | 1 passed, 2.027 s |
| Checkpoint inventory/receipt/restore cohort | 42 tests: 5 semantic-closure failures and 1 private-RNG-owner error; 19.521 s. The five closure refusals were reproduced at the verified published baseline in 018B; the private-RNG test is unchanged baseline behavior. No closure or private-RNG validation was weakened. |
| `git diff --check` | Passed at the last check; rerun before commit. |

The checkpoint cohort failure details remain in the earlier 018B/018C reports. They are independent of the Hold work; the passing Arena fresh-process scenario above exercises the supported generated-Arena persistence path.

## Remaining scope and task state

`TASKS.md` remains canonical and retains U-ARENA-018D as ACTIVE. U-ARENA-018 and U-ACT-012 remain PARTIAL; U-ACT-013 (declared Multiple actions) remains OPEN. This ruling resolves Hold's Action cost but does not implement the wider Multiple-action program, shared strategy allocation/priority penalties, or all legally simultaneous Action combinations. Remaining review also includes broader control/posture/size cases, more competing custody combinations, player-accessible cancellation of future pending contact Actions, defender-side browser choices, and the complete interactive Chrome walkthrough. U-ACT-020 Stun and U-ACT-021 Subdue remain OPEN; no new unarmed damage, timed condition, subdual track, or recovery framework was added. Force-based Pull remains outside this close-contact increment because its adopted force-to-motion mapping is explicitly unspecified.

No ideas-inbox entry was present for this scope. The generated outstanding-only Encounter to-do was refreshed using the documented tool; the working-draft TOC tool reports its older revision-60 target already current and did not modify the adopted revision-61 source. No `.venv`, ignored `legacy/`, local saves, independent `npc-generator`, backups, or unrelated user files were changed. The supplied assignments and unrelated report remain untracked. No push, reset, clean, or history rewrite was performed.

**Local functional commit:** `719c8ca` (`Add automatic Hold maintenance and Arena walkthrough`). **Publication:** not authorized; no push.
