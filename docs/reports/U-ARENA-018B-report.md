# U-ARENA-018B — bounded contact lifecycle continuation

## Where we stand

U-ARENA-018B adds a declared one-second Release grip Action, correct earlier-second cancellation of an unestablished initial Grapple after its last prerequisite Grip ends, adopted Trip contact sources and later-second attack interruption. The new Arena session regression exercises selected-hand Release through the shipped HTTP route and restores the committed result in a fresh Python process. **U-ARENA-018 remains PARTIAL. U-ACT-027 Wrest remains OPEN:** the native pipeline still has no receipt-backed Object Grip or atomic transfer path for this sequence.

No push was performed. The published baseline remains `ab4089fa2b28ba615effe29211be0a73b8d60946` on remote `main` (verified before implementation). The local cached `origin/main` ref was stale; it was not used as publication authority. Protected `.venv`, ignored `legacy/`, saved-world files, the independent `npc-generator`, and all three repository backups were preserved.

## Demonstrated behavior

Native tests provide reproducible end-to-end sequences from generated native Beings and committed receipts:

- Touch → Being Grab → voluntary Release grip. Release targets one selected Grip, consumes one declared second, makes no random draw, and leaves an independent Grip and established Grapple unaffected.
- Releasing the last qualifying Grip before an initial Grapple's first check cancels only that unestablished attempt at the release commit boundary. The same-second case still resolves both Actions from the shared frozen snapshot.
- Successful Touch, Being Grab, and qualifying Swing/Thrust Strike receipts are accepted as Trip contact sources. Only Grab contact adds the adopted +2. A successful Trip atomically sets prone posture and cancels that target's attack only when its deadline is in a later second; same-second attacks resolve normally.

The generated Arena HTTP/session regression now selects **Release grip → left hand**, advances its one-second boundary, saves the encounter, and restores it in a fresh Python process with no active physical Grip. The same test continues its existing separate-process Hold, initial Grapple, Escape, and checkpoint continuation. This is HTTP/session and fresh-process evidence, not a new Chrome walkthrough.

The preceding [U-ARENA-018 report](U-ARENA-018-report.md) records a Chrome Touch/Grab smoke and an isolated in-app-browser generated Arena trace through Touch → Grab → Grapple → pending-Grapple Save/Load → Takedown. Those browser traces predate this continuation's Release/Trip changes; they do not demonstrate the new commands in Chrome. No defender-side Break hold/Escape browser walkthrough was completed in this assignment.

## Source, API, and test changes

- Added `release grip` to the native Action contract, evaluation, typed Grapple state effect, settlement validation, atomic progression, Arena Action catalog, and browser selector. UI asks for a specific hand/Grip. It is a declared one-second no-contest Action, never a free mutation.
- Added committed-receipt classification for Trip contact from Touch, Being Grab, and Swing/Thrust Strike. Trip receipts retain `contact_kind`; the +2 modifier is based on that contact source rather than an unrelated active Grip.
- Added atomic lifecycle interruption for a later-second target Swing/Thrust after successful Trip and for an initial Grapple whose last prerequisite Grip is released in an earlier second. Other Grips preserve the initial attempt; established Grapple control is not canceled. Same-boundary Actions retain common-snapshot results.
- Corrected settlement's cancelled-melee outcome validation so an interrupted native melee Action can be published as `interrupted`.
- Added native regressions for selected Grip release without RNG, Grab-sourced Trip, same/later-second Trip attack scheduling, and earlier/same-second initial-Grapple prerequisite release. Extended the generated Arena HTTP/session test with Release and fresh-process restoration.

### Held-Object Grab → Wrest gap

Revision 61 distinguishes an attack roll to grab a held Object (including its holder's Defense level, the Object-size attack modifier, and +5 DC) from the later one-second `3d6 + Strength bonus` Wrest contest. The current physical-contact state is specifically folded from Target-owned Being histories and `GrappleStateEffect`; it cannot represent an Object Grip receipt. Existing custody effects cover ground Pick up, weapon readiness, drop, and disarm, but do not encode the intermediate Object Grip or a Wrest transfer from a holder's hand to another Being while preserving the same Object identity. There is also no reviewed same-boundary reservation/conflict contract for two actors attempting to Wrest that Object.

Accordingly no Object Grab/Wrest choice is exposed and no unsupported custody mutation is attempted. The precise engineering work remaining is a typed receipt-backed Object Grip, adopted attack/holder/size inputs with observer authorization, and an atomic same-identity custody/hand transfer with contention and rollback semantics. Until that path exists, this branch fails closed. This is the principal unmet acceptance item; this report does not claim the U-ARENA-018 family complete.

### Maintenance, position, and adjacent Actions

The existing six-second Grip check is still represented by a separately selected one-second Hold Action at its due boundary, with the established initial-Grapple substitution for that same Grip. This increment preserves that behavior and its settlement correction; it does not add automatic recurring scheduling or a retained-Action capacity contract. ChoiceBook has no represented recurring/retained demand semantics, so automatic maintenance would need a deliberate capacity model to avoid silently replacing the Being's demanding Action. The question remains open and must be resolved before claiming maintenance/capacity completion.

Existing Takedown/Reverse/Pin posture/control transitions remain bounded to represented two-participant positions and known size categories. This increment does not complete all posture-dependent attack/defense restrictions, incompatible simultaneous position rerolls, or multi-grappler occupancy facts. Stun and Subdue remain OPEN; armed Disarm remains PARTIAL and no new variants were added. The next shared implementation cluster is a typed, observer-safe held-Object interaction/custody contract; general Multi-action capacity remains a separate dependency.

## Verification

Executed with the preserved checkout `.venv`, no bytecode writes, no user-site packages, and `PYTHONPATH=tests:src:examples`:

- Five focused native lifecycle tests (Release, Trip later/same-second, initial Grapple earlier/same-second): **5 passed, 6.9 s**.
- Two focused Trip receipt tests (Touch and Grab contact): **2 passed, 4.1 s**. A separate tied-Trip test also passed, preserving standing posture and recording the Touch source.
- Generated Arena `test_grab_selector_http_receipt_and_fresh_process_hold_continuation` plus six focused native lifecycle cases: **7 passed, 34.1 s** before adding the HTTP Release/fresh-process branch.
- After adding the Release HTTP-route test, `test_grab_selector_http_receipt_and_fresh_process_hold_continuation`: **1 passed, 25.839 s**. Its first attempt found a test-only expected-boundary error (expected 5, restored actual 4); correcting the assertion yielded the passing final rerun. The final tie test passed separately.
- `py_compile` for modified Python source/tests and `git diff --check`: **passed**.
- The nine `tests.test_checkpoint_reconstruction` errors at `checkpoint_envelope.py:167` were reproduced in both the working tree and a pristine `git archive` of `ab4089f…`, using this same `.venv`: working tree **9 errors in 0.412 s**; pristine baseline **9 errors in 0.415 s**. Both fail while building the source envelope because the bounded semantic-closure certificate is missing. No checkpoint/RNG validation was weakened.

The full test suite and an actual browser walkthrough of the new Release/Trip controls were not run. HTTP/session evidence must not be described as Chrome. Existing fresh-process continuation evidence is limited to the states named above; no Object Grab/Wrest checkpoint exists because that native path is not implemented.

## Task IDs before → after

| ID | Before | After |
|---|---|---|
| U-ARENA-018 | PARTIAL / OPEN; no active continuation | PARTIAL / OPEN; U-ARENA-018B bounded increment delivered; Object Grab/Wrest, maintenance capacity, and broader position/browser gaps remain |
| U-ACT-011 | DONE bounded for Grab of a Being | Unchanged; held-Object Grab remains unsupported |
| U-ACT-012 | PARTIAL; no voluntary Release grip | PARTIAL; declared one-second Release and last-prerequisite interruption added; maintenance/capacity and positional gaps remain |
| U-ACT-024 | PARTIAL; Touch-only prerequisite and no later attack interruption | PARTIAL; Touch/Grab/Strike receipt sources and later-second interruption added; wider conflict coverage remains |
| U-ACT-027 | OPEN; no Wrest path | OPEN; typed Object Grip/custody path remains unimplemented |
| U-ACT-008 | PARTIAL armed Disarm | Unchanged |
| U-UI-001 | PARTIAL | PARTIAL; bounded Release/Trip selector options added, complete browser and observer-facing scope remains |
| U-PER-002 | PARTIAL | PARTIAL; Release state is covered by fresh-process Arena Save/Load regression; general persistence remains open |

`docs/ideas/inbox/` does not exist in this checkout, so no intake items were mapped or moved. `TASKS.md` reflects the bounded outcome and clears the ACTIVE marker; its update is intended to be committed with this report. No unrelated task or idea was rewritten.

## Git and publication safety

The staged paths will be limited to the reviewed source, tests, Action catalog, process clarification, `TASKS.md`, this report, and the installed canonical assignment. The pre-existing untracked `U-REPO-*` assignment/report inputs and `U-ARENA-018B-new-codex.md` remain unstaged. Before each local commit the staged path list, cached diff, staged publication-safety scan, and cached whitespace check will be recorded below. No push is authorized or planned.

### Final execution record

- The final HTTP Release/fresh-process test passed (1 test, 25.839 s); the Trip tie test passed (1 test, 1.017 s); modified Python files compiled; and `git diff --check` passed.
- Staged paths were the 15 files listed above. The first cached whitespace check found four Markdown hard-break trailing spaces in the newly installed assignment; those spaces were removed, then `git diff --cached --check` passed.
- `.venv/bin/python -B tools/check_publication_safety.py --staged`: **15 files, 0 findings, PASS**. Untracked `U-ARENA-018B-new-codex.md` and pre-existing U-REPO assignment/report inputs remain unstaged.
- Local commit and final worktree status are reported in the task closeout. No remote publication was attempted.
