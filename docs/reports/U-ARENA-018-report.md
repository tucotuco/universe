# U-ARENA-018 engineering report

## Outcome

This is a substantial native implementation increment, but **U-ARENA-018 is not complete**. Native positional Grapple transitions and Trip now resolve through the transactional Encounter engine, and the shipped Arena browser completed an authentic Touch and Grab against a naturally generated opponent. The required full Chrome sequence through Grapple and a new position transition, plus browser save/reload during that sequence, was not completed. Several explicit requirements below remain open.

No `npc-generator` files were changed and nothing was pushed. Changes were made only to Arena/native combat source and its focused tests. The worktree also contained unrelated tracked deletions, a `TASKS.md` edit, and untracked material; those were left unstaged.

## Implemented

- Added explicit optional Being size-category state and strict checkpoint-field support. Arena generation accepts optional authored size facts; actions requiring size refuse when facts are absent. No general Medium default or body geometry was added.
- Added native Takedown, Reverse, and Pin evaluation and staged position/posture effects. They use the existing Grapple check at the next six-second boundary, preserve the current position on failure/tie, validate the represented position and size prerequisites, and publish control plus posture changes atomically.
- Added native Trip using a recorded successful Touch identity, its two-second timing, the Strength versus defender-selected Strength/Dexterity contest, size and Grip modifiers when known, and an atomic prone posture result.
- Added kneeling posture handling and native movement refusal while kneeling.
- Added Arena controls and explanations for Trip, size-dependent availability, and current contact-state status. Result display selects the latest relevant Touch/Grapple result by time.
- Reproduced and fixed a settlement integrity defect: a failed initial Grapple can coincide with the prerequisite Grip's scheduled maintenance boundary. The settlement validator now permits only the matching failed-Grapple, same-Grip maintenance effect at that boundary. A deterministic test covers this case.
- Retained existing Touch, Grab/Hold, Break hold, initial Grapple, Escape, damage-induced Grip release, and checkpoint pathway. An earlier focused fresh-process Arena test confirmed pending Grapple continuation; see verification below.

## Actual Chrome evidence

On the shipped Arena at `http://127.0.0.1:58011/`, I generated a normal Encounter with root seed `20261197`, 10,000 starting XP, explicit Medium size categories, unequipped start, and no autonomous opponent strategy. These were ordinary generation controls; no character statistics, roll results, Grip, or Grapple state were injected.

| Native Encounter boundary | Browser interaction | Verified result |
|---:|---|---|
| 1 | Select destination `(4,1)` and Advance | Player Being moved from native position `(2.9, 1.82, 0)` to `(3.69, 1.37, 0)` metres. |
| 2 | Select destination `(3,0)` and Advance | Native position reached `(2.9, 0.91, 0)` metres. |
| 3 | Open the player popup, choose **Touch (1 s)**, Advance | Browser showed accepted pending Touch, then `Touch resolved: touched.` |
| 4 | Choose **Grab (1 s)** with the free left hand, Advance | Browser showed accepted pending Grab, then `Grab resolved: success.` The movement status showed the native left-hand Grip and its next six-second check. |

The opponent popup correctly showed unknown private characteristics because the player's observer evidence did not authorize those details. The browser remained observer-safe.

I attempted to restart the Encounter and repeat the run with Grapple scheduled immediately after Grab. Chrome presented the app's normal discard confirmation; after accepting it, Chrome's control channel began timing out while reconnecting to the local page. I stopped the live-browser attempt there. Thus this is authentic browser evidence for Touch and Grab only; the browser did **not** demonstrate Grapple, Takedown/Reverse/Pin, or browser save/reload in this pass. The missing browser steps are not represented as passed by the HTTP or fixture results.

## Focused verification

Passed:

- `PYTHONPATH=tests:src:examples .venv/bin/python -m unittest tests.test_action_evaluation.TestActionEvaluation.test_native_touch_grab_hold_break_grapple_and_escape_use_separate_receipt_state tests.test_action_evaluation.TestActionEvaluation.test_native_trip_uses_touch_identity_contest_and_commits_prone_posture tests.test_action_evaluation.TestActionEvaluation.test_failed_initial_grapple_still_atomically_maintains_its_prerequisite_grip` — 3 tests, 36.799 seconds, OK. The existing state-machine test includes successful Takedown, Pin, Reverse, and Escape position transitions.
- `test_grab_selector_http_receipt_and_fresh_process_hold_continuation` and the generated-Arena seed/optional-size browser-handler test passed in the earlier focused run (4 total tests including the native Touch/Grab state-machine and Trip tests, 57 seconds, OK). This is HTTP/session and fresh-process evidence, not actual Chrome evidence.
- `.venv/bin/python -m py_compile` on the modified Arena/native Python modules and `examples/arena_web.py` — passed.
- `git diff --check` — passed.

One attempted test command included the nonexistent test name `test_native_takedown_reverse_pin_position_transitions_are_transactional`; unittest reported one loader error because the transitions are covered inside `test_native_touch_grab_hold_break_grapple_and_escape_use_separate_receipt_state`. The corrected focused command above passed.

Checkpoint baseline investigation:

- `PYTHONPATH=tests:src:examples .venv/bin/python -m unittest tests.test_checkpoint_reconstruction` — **9 errors**. All nine stop in `checkpoint_envelope.py:167` with `EnvelopeRejected: bounded semantic-closure certificate is missing` while `build_source` creates the envelope. This is the known existing strict-checkpoint baseline, not a failure caused by Trip or positional Grapple. I did not weaken semantic-closure or private-RNG validation.

## Action status changes since U-ARENA-017

| Action/area | U-ARENA-018 change | Remaining gap |
|---|---|---|
| Takedown | Native timed, opposed transition with required size/position validation and atomic posture/control publication. | Multi-grappler compatibility and simultaneous incompatible success rerolls are not implemented. |
| Reverse | Native timed transition from represented disadvantaged positions. | Same multi-grappler gap. |
| Pin | Native timed transition with selected pin position and posture. | Immobilization and all attack modifiers/consequences still need complete integration; no broad claim of full Pin rules. |
| Trip | Native Touch-dependent contest, size/Grip modifiers and prone posture; browser Action is connected. | Successful Trip does not yet nullify an already-pending later-second attack. Only the Touch prerequisite is wired; Grab/Bull rush/Strike sources are not all connected. |
| Grapple status | Browser movement status now reports the player's native Grip and the next check; unknown opposing details remain private. | No complete usable Grip/Grapple/position-state panel, and no browser proof past Grab. |
| Kneeling/movement | Kneeling is represented; destination movement refuses while kneeling. | Broader Action restrictions for each Grapple position need review and implementation. |
| Hold maintenance | Existing timed maintenance and Break hold remain; matching maintenance at a failed initial Grapple boundary is now accepted. | The current one-second Hold-maintenance declaration model still needs a rules/action-capacity audit. |
| Voluntary Grip release | — | No separate timed/declarative voluntary-release path was added. |
| Wrest | — | Correctly not implemented: it requires a distinct successful Grab of an Object held by a Being; existing Being Grab and ground Pick up do not satisfy that prerequisite. |
| Stun/Subdue/unarmed Disarm | — | No new variants were added. Existing native weapon Disarm and Coup de grace work remain as before; Stun/Subdue need their required attack/condition/damage contract work. |

Trip cancellation, voluntary Grip release, full browser Grapple flow and save/load, complete position consequences, multi-grappler conflict resolution, and supported Stun/Subdue integration are substantial outstanding requirements. The feature is not accepted as complete.

## Commits

- `e219bfe` — Add native positional grappling and Trip.
- `2bc7776` — Expose close-contact state in Arena UI.
- The report is the remaining uncommitted task artifact. The unrelated `TASKS.md` edit, tracked documentation deletions, and other untracked content were not staged. No unrelated content was included in either commit.
