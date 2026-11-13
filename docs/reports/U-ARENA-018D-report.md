# U-ARENA-018D — close-contact lifecycle closeout

**Status: U-ARENA-018D CLOSED on 12 November 2026. The broader U-ARENA-018 program remains PARTIAL / ACTIVE.** This report records the final criterion review and current evidence. Historical milestone detail is summarized at the end; the current matrix and state above it supersede older progress notes.

## Acceptance matrix

| U-ARENA-018D criterion | Result | Evidence |
| --- | --- | --- |
| 1. Generated Arena runs the adopted contact lifecycle through relevant success, failure, release, maintenance and positional cases; UI offers only observed/authorized choices. | **Met.** | Generated Arena HTTP/session route: Touch → Grab → pending Grapple Save/Load in a fresh process → successful Grapple → Takedown → second Save/Load. Actual Chrome walkthrough separately demonstrated Touch, Grab, Grapple, Takedown and Save. Native regressions cover failed/tied Touch, Grab, Hold maintenance, Trip, and release; one-Grip release, staggered no-cost maintenance, Escape, Takedown/Reverse/Pin, size/capacity limits, and pinned movement/attack restrictions. Pin low-roll redirection is now implemented and tested. |
| 2. Held-Object Grab/Wrest preserves the same Object ID, hand/equipment/ownership state, and deterministic failure/tie behavior; contention and custody loss follow adopted rules or are clearly bounded by an unresolved rule. | **Met.** | Native `tests.test_native_object_wrest` covers same-ID held-Object Grab/Wrest, hands and equipment, failure/tie, holder weapon use, same-boundary Disarm, earlier Disarm invalidation, cancellation, and three-Being same-snapshot success where both Wrest challengers co-hold the single Object. Revision 68's independent claims commit atomically and preserve identity. No rule is invented for a later contest among joint holders; that exact later case remains unsupported and is documented as an explicit adopted-rule boundary. |
| 3. Injected Object-Grip/Wrest faults restore custody, receipts, RNG and replay; pending and successful state survives fresh-process persistence. | **Met.** | Fault-injection regressions restore all custody references and receipt/RNG/replay state after late publication failure. Native and generated Arena tests reload pending and completed contact/custody state in fresh OS processes. |
| 4. Related native and ordinary HTTP/browser-JS tests pass without pre-import shims; actual browser evidence is distinguished. | **Met for the focused close-contact gate.** | `tests.test_action_evaluation`: 85 passed, 87.674 s. `tests.test_native_object_wrest` plus generated contact and Disarm fresh-process routes: 15 passed, 39.281 s. These run through normal test imports and shipped HTTP/session code. Earlier focused suites also cover Multiple-action rules, Arena JavaScript harness, checkpoint reconstruction/wire, and persistence; see test log below. Actual Chrome evidence is distinct and does not claim Chrome file-based Load, which the extension's local-file permission prevented. The full repository suite was not run. |
| 5. Authority, `TASKS.md`, inbox and completion state are accurate. | **Met.** | Revision 61 and adopted supplements 62–68 remain authoritative. `TASKS.md` now closes subordinate assignment D, preserves U-ARENA-018 as ACTIVE / PARTIAL, and keeps OPEN Actions and other gaps separate. `docs/ideas/inbox/` is absent. No source authority or protected repository/data was changed. |

## Final implementation and verified behavior

- Receipt-backed Touch, Being/Object Grab, individual Grip/Hold, voluntary Grip release, automatic six-second no-cost Hold checks, initial Grapple, Escape, Trip and positional Takedown/Reverse/Pin use the transactional native scheduler and common snapshots. Grip loss does not end established Grapple; earlier versus same-second prerequisite loss is covered. Multiple Grips retain independent hands and check schedules.
- Positional prerequisites and restrictions are enforced: Takedown requires standing control and standing participants and respects the adopted size limit; Reverse requires the supported disadvantageous positions and size limit; Pin requires advantaged top control and an explicit top/bottom destination. Pin immobilizes movement, bars the holder from striking the pinned Being and the pinned Being from melee, gives outside strikes +4, and redirects a missed outside attack with the adopted low roll to the pinning holder. The new regression for redirection is in commit `dbc9587`.
- Same-ID held-Object Grab/Wrest is integrated with native custody and equipment state. Competing successful same-boundary Wrest rolls use one shared snapshot, co-hold the same Object under revision 68, and clear the former holder. Disarm/Wrest same-boundary conflicts and earlier custody loss retain deterministic behavior. Three-Being fixtures use explicit Arena hex geometry; the former `uncertain_path` observation was fixture construction, not a missing path rule.
- Multiple-action native execution implements declaration, ordering, timing, capacity and resource allocation, priority penalties, common-snapshot resolution, interruption/abort, repeat cycles, and checkpoint restoration. Generated Arena exposes ordered two-Touch and Grapple + Break-hold declarations with priority and abort controls.
- Native and generated Arena implement the adopted unarmed Disarm attack path with Unarmed skill, free arm, arm reach/timing, opposed roll, Grapple defense modifier and atomic drop of the same weapon. Broader U-ACT-008 optional weapon-taking/landing controls and locked-gauntlet attachment state remain tracked as Action work; they do not negate the accepted physical-contact and core unarmed-Disarm route delivered here.

## Test log and verification

All commands used `.venv/bin/python -B -m unittest` with `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples`.

| Focused command | Result |
| --- | --- |
| `tests.test_action_evaluation` | 85 passed, 87.674 s; includes the new pinned-target redirection regression. |
| `tests.test_native_object_wrest tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_generated_http_contact_grapple_takedown_save_load_without_fixture_mutations tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_disarm_http_pending_save_load_commits_exact_weapon_to_ground` (the Disarm method was invoked twice in the recorded command) | 15 passed, 39.281 s; 12 native custody regressions plus generated contact and Disarm fresh-process routes. |
| `tests.test_native_object_wrest` (prior focused run) | 12 passed; included three-Being co-holding, rollback, custody loss and persistence. |
| `tests.test_generated_arena_browser` (prior focused run) | 55 passed; generated HTTP/session routes and shipped-JavaScript harness. |
| `tests.test_multiple_action_rules tests.test_action_choices tests.test_interval_staging` (prior focused run) | 120 passed, 19.344 s. |
| `tests.test_checkpoint_reconstruction tests.test_checkpoint_wire tests.test_encounter_inspection` (prior focused run) | 59 passed, 40.162 s; private-RNG and semantic-closure validation retained. |
| `tests.test_arena_persistence` (prior focused run) | 7 passed, 13.117 s. |

`git diff --cached --check` and `.venv/bin/python -B tools/check_publication_safety.py --staged` passed for each implementation/evidence commit. The positional correction audit reviewed exactly two staged files and found zero findings. No push was performed.

## Generated Arena browser coverage

**Actual Chrome (12 November 2026):** Generated with root seed `20261100`, 10,000 XP, 5×5 map, unequipped starts, no opponent strategy and Medium size categories. The player moved to `(0,1)`, selected the perceived opponent and completed Touch at second 2, Grab with the left hand at second 3, Grapple at second 9, and prone Takedown at second 15. The visible status showed `advantaged_takedown_top`; **Save Encounter** downloaded a native save. Chrome's local-file chooser could not be automated because the Codex extension has **Allow access to file URLs** disabled. No Chrome permission was changed.

**Fresh-process Save/Load:** The generated HTTP/session regression performs the same real Generate and movement setup, saves while Grapple is pending, reloads in a new OS process, resolves Grapple and Takedown through the shipped session, then saves and reloads the committed Grip/control/posture state again. This is Save/Load evidence from native fresh processes, not a claim that Chrome's file chooser was exercised.

## Remaining work outside this closed assignment

These items keep the broader program and Action inventory PARTIAL / OPEN; they are not hidden blockers to U-ARENA-018D:

- **U-ACT-008 Disarm — PARTIAL:** optional take-on-margin and selectable landing distance/direction are not exposed; the native model lacks a locked-gauntlet attachment relation. Core armed/unarmed Disarm and exact-object drop are implemented.
- **U-ACT-020 Stun — OPEN; U-ACT-021 Subdue — OPEN:** these separate Action entries need typed timed-condition/interruption and subdual-damage/recovery state respectively. They are not the close-contact positional/custody acceptance criteria closed here.
- **U-ACT-013 Multiple actions — PARTIAL:** native execution and representative generated compositions are integrated; generic browser composition and other Action families remain open.
- **Joint-holder subsequent Wrest:** revision 68 intentionally does not define subsequent contests among new co-holders. The engine rejects that unsupported case rather than adding a winner rule.
- Chrome file-based Load and the full repository suite were not verified in this closeout.

## Commit and scope evidence

- `35ecd957cab792ef5f056b0c3d423b7097529a5f` — simultaneous Wrest co-holding and willing Touch (revision 68).
- `98bed44bc00a6adfcbbe27fc9d29ca85a660ddab` — native/generated unarmed Disarm.
- `a908169562667049cb78657a63caaa5b33eafaa5` — grappled-defender Disarm modifier regression.
- `ead115d92621081fe4204f1f228156aed3248409` — contact Multiple-action Arena integration.
- `dbc95877afe888c90f71c5d2b2fb0258a7a78ab3` — pinned-target attack redirection and regression; focused 85-test action-evaluation module passed after this commit.
- Earlier required workflow correction and canonical assignment commits are `32a698f31ff015ad5885f376044867756f742b0c` and `f0264cc`.
- TASKS/report closeout commit: `07d93a644f80fe9e67fee754e91c536a8e459c52`. At closeout verification, tracked changes were committed and only the pre-existing unrelated user-provided untracked files remained; they were not staged. The checkout remains unpublished.

## Historical milestone notes (superseded by the current matrix)

The prior report sections documented revision-67 automatic Hold maintenance, the first generated-Arena Chrome walkthrough, early `uncertain_path` fixture failures, the two revision-68 rule questions, and incremental Multiple-action/Disarm implementations. Revision 68 resolved the two former rule questions. The path fixture was corrected by constructing a native three-Being Arena with explicit geometry. Older claims that U-ARENA-018D remained ACTIVE, that simultaneous Wrest outcomes needed a rule decision, or that willing Touch required an unspecified capacity decision are superseded. Commit hashes above and `TASKS.md` are the canonical current-state evidence.
