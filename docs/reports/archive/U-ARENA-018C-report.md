# U-ARENA-018C — native held-Object Grab and Wrest

## Where we stand

U-ARENA-018C adds a bounded native sequence in the generated Arena: a Being can Grab a specifically observed opponent-held weapon, establish a receipt-backed Object Grip, and later Wrest it in a one-second contest. A strict contest win atomically moves the original Object ID and its hand/custody references; a loss or tie preserves the holder's custody. The sequence was exercised through the existing Arena HTTP/session controls, and both an established Grip and completed Wrest were saved and restored in separate fresh Python processes. U-ARENA-018 remains PARTIAL: broad grappling lifecycle, general multi-Action capacity, additional simultaneous custody cases, and a real browser walkthrough remain open.

## Demonstrated generated Arena sequence

The reproducible fixture is root seed `20261107`, a generated 5×5 Arena with two generated Beings and native initial equipment. The opponent's actual generated Dagger Object is selected through observer-owned perception evidence; its opaque Arena handle is sent through `/api/generated/grappling`. No Object ID is supplied by the browser and no physical custody is authored by the test. The test verifies the Object's parent, weapon membership and holder hand before and after each boundary.

Sequence and evidence:

1. Generate the encounter, initiate it, advance to second 1, and inspect the holder's Dagger. The catalog exposes `grab object` only after current observation. The response does not disclose the native Object ID.
2. Submit `grab object` with the player's free left hand. The accepted Action resolves at second 2 against the shared post-movement/pre-Action snapshot. Its result is `success`, while the opponent remains the Object owner and retains it in the right hand. The typed Object Grip receipt identifies this Object, actor hand, holder hand, holder, source Action and boundary.
3. Save this established Grip. A fresh Python process loads it, observes the same Object, and sees Wrest available. It submits `wrest`; the successful boundary transfers the same Object ID to the actor's left hand. Holder weapon/possession/hand references are removed and actor weapon/possession/hand references are added atomically. The transfer receipt is attached to the Object. The fresh process saves again; a second fresh Python process reloads and verifies the successful Wrest Action and identical Object ID/custody.
4. Controlled deterministic tests seed the random stream to exercise the held-Object attack's holder-Defense and `+5 + size modifier` DC and the strict 3d6 tie/loss branches. A Dagger of size `T` has modifier `+2`. The one-second Wrest roll uses three independent 1d6 draws plus the Strength bonus for each contestant; equality is failure for the wrestler.
5. An existing accepted holder attack reserves the same weapon Object and prevents a competing Wrest from being scheduled. The rejection leaves the holder's hand, Object parent and established Grip unchanged. The complementary same-boundary action evaluator also returns `custody_conflict` for holder weapon use or a pending Disarm against the held Object if such Actions reach the shared snapshot.

The holder's weapon is generated native initial equipment. The demonstration does not stage a separate ground Pick up or Ready Weapon Action. This keeps the acceptance sequence to the smallest generated two-Being, receipt-backed path without fabricating custody.

## Implementation

- Added the frozen `ObjectGripEffect`, a distinct Object-target receipt history and a fold that exposes only a current grip whose Object is still held by the recorded opponent and whose receiver hand remains valid. A successful Wrest transfer closes that grip state.
- Added `grab object` attack resolution against the holder's Defense, with the adopted size modifier and +5 DC, and a strict one-second `3d6 + Strength bonus` Wrest contest. Invalid declarations, missing/expired grips, out-of-reach holders, unavailable hands and same-boundary custody conflicts fail before unsupported effects are published; invalid action preflights do not consume RNG.
- Added atomic same-ID custody transfer across Object parent, both Beings' hand slots, weapon lists and possession lists. Commit validation rejects duplicate or changed claims. Object-visible equipment status is refreshed from committed owner/hand state.
- Added observer-authorized Arena catalog entries and HTTP/session choices using opaque evidence handles. Persistence adapters preserve typed grip and transfer receipts, and the initial-equipment validator now accepts a changed owner only with a contiguous committed Wrest receipt chain.
- Added native/inspection validation for expected hand slots and live custody, plus reservation integration between Object Grip and Being Grip hands.

## Rule authority and contention limits

The adopted Encounter revision 61 and supplements 62–65 control the roll, one-second contest and result. The implementation does not add priority or simultaneous cancellation rules. Existing native Object reservations reject simultaneous accepted Actions that claim the same Object. When competing actions are represented together in the common snapshot, evaluation marks a same-Object Grab/Wrest claim `contested`, a pending Disarm `custody_conflict`, and the holder using the same weapon `custody_conflict`; it does not transfer on those outcomes.

The focused regression covers duplicate same-actor submissions, a competing holder weapon reservation, invalid/missing targets and no current Grip. It does not yet construct a three-Being simultaneous two-attacker contest, a live pending Disarm/drop against an established grip, or an injected exception between the Wrest target writes. Those combinations remain explicitly unverified; no new winner priority, drop ordering or cancellation policy is inferred. The shared atomic-publication transaction stages all Wrest custody writes together, and existing atomic-publication tests exercise rollback infrastructure, but this increment has no Object-Grip-specific injected-write rollback test. A current receipt ceases to qualify if the holder loses custody or the receiving hand becomes occupied, so later Wrest preflight fails closed.

## Focused verification

All commands used the preserved `.venv`, with `PYTHONDONTWRITEBYTECODE=1`, `PYTHONNOUSERSITE=1`, `PYTHONPATH=tests:src:examples`, and `.venv/bin/python -B`.

- `python -m unittest tests.test_native_object_wrest`: **5 passed, 7.388 s**. Covers HTTP/session success, invalid/unobserved target, occupied hand, duplicate submission, reach without RNG use, attack DC/Defense, successful Wrest and identity continuity over two fresh processes, failed/tied Wrest custody, and reservation conflict.
- `python -m unittest tests.test_action_evaluation tests.test_action_settlement`: **119 passed, 53.663 s**.
- `python -m unittest tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_grab_selector_http_receipt_and_fresh_process_hold_continuation`: **1 passed, 25.554 s**. This is HTTP/session evidence, not Chrome.
- Targeted checkpoint inventory/receipt/continuation probe: **42 tests, 36 passed, 6 failed/error, 20.710 s**. Five failures in checkpoint restore continuation and one inventory error arise in existing source fixtures before the new Arena Grip/Wrest persistence path: the established `bounded semantic-closure certificate is missing` source-envelope refusal and `unbound Encounter checkpoint requires an explicitly supplied private RNG cursor`. The nine reconstruction failures with the missing semantic-closure certificate were independently reproduced at published baseline `ab4089f` and current worktree in U-ARENA-018B; checkpoint validation was not weakened. Fresh-process Arena Grip/Wrest save/load passes in the focused test above.
- `py_compile` for every modified Python source, `examples/arena_web.py` and the new test: **passed**. `git diff --check`: **passed**.
- A shipped-JavaScript harness check for the Action catalog count and an older generated-view allowlist assertion also failed during exploration; they assert stale catalog/view expectations and do not exercise the native Arena HTTP/session sequence. No Chrome walkthrough was run. These failures are not presented as green browser verification.

No full suite was run. No bytecode, package, legacy, saved-world, generator or backup changes were made.

## Task state before → after

| ID | Before | After |
|---|---|---|
| U-ARENA-018 | PARTIAL / OPEN; Object Grab/Wrest gap | PARTIAL / OPEN; bounded receipt-backed held-Object Grab → Wrest delivered; broader lifecycle, capacity, conflict and browser gaps remain |
| U-ACT-011 | DONE bounded for Being Grab after Touch | DONE bounded; held-Object Grab added with holder Defense, size and +5 DC |
| U-ACT-027 | OPEN; no Wrest path | DONE bounded; strict one-second current-Grip contest transfers same ID atomically; broader conflict cases remain |
| U-ACT-008 | PARTIAL; armed Disarm/drop implemented, variants missing | PARTIAL; no Disarm variant added; interaction with simultaneous Object Grip custody remains fail closed and broader scenarios unverified |
| U-UI-001 | PARTIAL; no observer-facing held-Object choice | PARTIAL; observer-authorized Grab/Wrest choices added; full browser lifecycle remains open |
| U-PER-002 | PARTIAL; general persistence incomplete | PARTIAL; established Object Grip and completed Wrest verified across fresh Python processes; general checkpoint limitations remain |

`docs/ideas/inbox/` is absent in this checkout; no idea intake was needed. `TASKS.md` is updated to match this bounded current state.

## Git, staged safety and closeout

Repository branch is `main`, implementation started from local `b8fea8b`, ahead of the stale cached `origin/main`; the live remote `main` was verified at the published baseline `ab4089fa2b28ba615effe29211be0a73b8d60946`. The assignment is local-only and authorizes no push. The pre-existing untracked U-REPO inputs and `U-ARENA-018B-new-codex.md` remain unstaged. Before each scoped local commit, the staged file list and diff are reviewed, `git diff --cached --check` is run, and `.venv/bin/python -B tools/check_publication_safety.py --staged` is run; commit hashes and results are added here after commit.

## Next engineering priority

Keep U-ARENA-018 partial. The next Encounter work should resolve and test multi-actor same-Object contention and custody loss/drop ordering only from adopted rules, add Object-Grip-specific fault-injection rollback coverage, and separately decide the remaining physical-contact Action-capacity/lifecycle contract. Do not treat HTTP/session tests as a browser walkthrough.

### Final execution record

- The implementation commit is `417bbea` (`Add native held object wrest custody`), with 18 explicitly reviewed paths. Before committing, `git diff --cached --check` passed and `.venv/bin/python -B tools/check_publication_safety.py --staged` reported `18 files, 0 findings, PASS`.
- The report-only commit follows after the same explicit-path staging, staged-diff review, cached whitespace check and publication-safety audit. No push was attempted.
