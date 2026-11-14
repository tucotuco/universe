# U-CAP-005 — Stun and Subdue implementation report

**Status:** ACTIVE pending ChatGPT acceptance and report consumption. The functional implementation is complete; this continuation reconciles adjacent verification failures. Keep this report and its assignment in the active directories until acceptance and consumption.
**Assignment:** [U-CAP-005](../assignments/U-CAP-005.md)
**Repository:** `~/Projects/universe`
**Publication:** No push authorized or performed.

## Execution interval

- Start: `2026-11-13T21:07:54-08:00` (captured at execution start; UTC `2026-11-14T05:07:54Z`).
- End: `2026-11-13T22:24:39-08:00` (captured immediately before closeout; UTC `2026-11-14T06:24:39Z`).
- Elapsed: `PT1H16M45S`.

### Verification continuation

- Start: `2026-11-13T23:49:21-08:00` (captured when this continuation began; UTC `2026-11-14T07:49:21Z`).
- End: to be captured immediately before closeout.
- Elapsed: to be calculated from the captured continuation interval.

The independent accepted U-CAP-004 archival/reconciliation operation ran within the recorded interval and was completed in `fdb4798d6066d7f3fe8ea82b6641e76ae4a585ce`.

## Acceptance matrix

| Criterion | Result | Evidence and bounded scope |
|---|---|---|
| A. Native Stun | **Met** | Native Actions use the adopted unarmed Arm/Leg profiles, Stun rank, trained creature-category threat modifier, armor check penalty, attack DC/immunity limits, Fortitude DC 20 and per-rank duration. Tests cover hit without threat, save success/failure, confirmed/nonconfirmed critical, failed-Stun half damage, fatal double natural 20, armor penalty, later-only interruption, same-boundary target Action, expiry and rejection/rollback paths. |
| B. Native Subdue and recovery | **Met** | Held melee bludgeon only; known immunity and unsupported weapon motion refuse. Native typed effects retain separate subdual burden and ordinary HP damage, threshold unconsciousness independent of HP, simultaneous burden aggregation and cause-specific recovery. Tests prove positive-HP subdual unconsciousness, persistence after fresh-process reload, helplessness, and exact 3,599/3,600 hourly recovery boundary from the loaded committed anchor. |
| C. Atomic scheduling and persistence | **Met** | Effects are staged from the common postmovement/pre-action snapshot and published with typed receipts. The target's same-boundary Action remains eligible; successful Stun/Subdue interrupts a later still-running Action. Strict checkpoint field/native-snapshot adapters include the new receipt/state types without loosening fingerprints. Fresh-process tests preserve pending and committed Actions/effects, Encounter identity, RNG continuation, interruption and conditions. |
| D. Generated Arena | **Met** | Shipped JavaScript composer renders each represented Stun motion and Subdue weapon/motion option. Generated Arena HTTP/session tests explicitly author only the scenario facts needed, prove catalog eligibility, submit opaque handles, save pending state, load in a new process, resolve native effects, and save/reload committed results. Stun actually interrupts a later swing. Subdue causes unconsciousness at 1 HP with burden 1 and zero ordinary HP loss. The Chrome smoke generated an equipped Arena and opened the character Actions view; it displayed “unknown from player-authorized evidence,” so that manual session did not verify an eligible Stun/Subdue control. The generated HTTP scenarios are the verified end-to-end UI-route evidence. |

The complete supported criteria are met without modifying the separate Shoot, Deflect or broader Throw work. Generated NPCs do not receive invented Stun ranks, category training, immunities, weapons or health facts. These cases remain unavailable unless represented by authorized Arena scenario facts.

## Implementation summary

Native declaration and scheduling route Stun/Subdue through Action/Choice, timing, resource checks, melee range and target authorization. The common-snapshot evaluator produces typed `StunEffect`/`SubdualEffect` receipts and normal damage/protection effects. Atomic publication maintains Stun expiration and separate Subdual burden/recovery anchor, aggregates same-boundary Subdual attacks before unconsciousness/interruption, and reevaluates conditions alongside HP. A shared recovery calculation applies one Subdual point per elapsed hour at committed boundaries. Recovery at the exact boundary is validated from a fresh-loaded persisted anchor; this report does not claim a 3,600-step live UI progression demonstration.

Generated Arena action programs accept only current observer-owned target/equipment handles. Status projection reports condition and duration only within the existing authorized observer projection. Existing unknown geometry, reach and physiology continue to fail closed; no body geometry is inferred.

## Verification

All commands below used the repository `.venv` unless noted.

**Acceptance suites passed:**

- `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_action_evaluation` — **125 tests passed**, 111.573 s.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_generated_stun_program_survives_fresh_load_and_interrupts_later_action tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_generated_subdue_http_fresh_load_and_independent_condition` — **2 tests passed**, 5.666 s. The second test proves the fresh-loaded exact recovery calculation; the one-hour boundary is not simulated by 3,600 committed steps.

**Focused verification and baseline reconciliation:**

- Baseline: source and tests were extracted read-only from pre-U-CAP-005 commit `2148876` into a temporary baseline checkout. Four representative tests reproduced the same failures there: unbound module RNG checkpoint capture, missing `ReadyPreparationAction` import, overlap without Multi-action skill, and a malformed target-bearing generic Delay yielding `SettlementIntegrityError`. These were stale fixtures/expectations, not regressions in U-CAP-005.
- Baseline generated Arena: targeted tests reproduced the broad “destination” substring and allowlist substring false positives against `2148876`; the mixed-program status test passed there. The current positional assertion was stale because the current projection includes one-member Action programs. Assertions now inspect represented payload keys and select the program by component names.
- Current checkpoint inventory, checkpoint choice descriptors and Action Choices — `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_checkpoint_inventory tests.test_checkpoint_choice_descriptors tests.test_action_choices` — **99 tests passed** (15.604 s). The checkpoint test now expects refusal when no private module RNG cursor is supplied; the Action Choices fixture imports its native Ready preparation type.
- Current generated browser — `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_generated_arena_browser` — **67 tests passed** (111.556 s). The fixes are test-only: payload-key/coordinate checks avoid matching explanatory prose, and the mixed program is selected by represented components.
- Current atomic publication and interval staging — `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_atomic_publication tests.test_interval_staging` — **127 tests passed** (57.332 s). The former 31 errors comprised 30 choices missing the adopted Multi-action skill and priority allocations plus one malformed generic Delay fixture. Test-only helpers now declare acquired skill and the adopted fixed priority penalties; the separate run/spot fixtures are scheduled without illegal overlap. The unsupported-family test now exercises a supported native Delay receipt. No Multiple-action or atomic-resolution rule was weakened. A further targeted run of the three representative atomic/interval cases passed (3 tests, 0.797 s).
- `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 .venv/bin/python -B -m compileall -q src examples` reports `IndentationError` in untouched `src/location.py:57` (function beginning at line 55). Compiling the same file from baseline `2148876` reports the identical error at line 57: its function body is already empty. This verified pre-existing issue is outside U-CAP-005 and is recorded in `TASKS.md`.
- No runtime source was changed in this continuation. The U-CAP-005 native and generated acceptance tests remain covered by the earlier results above. Final `git diff --check`, cached diff check, publication-safety audit, exact staged paths, final HEAD and unrelated staged archive preservation are recorded below.

## Separate U-CAP-004 closeout and task state

The accepted U-CAP-004 assignment/report were moved with `git mv` to their archive directories; maintained references and `TASKS.md` were reconciled. U-CAP-005 is now DONE (bounded) and its report remains active awaiting review. U-ACT-020 and U-ACT-021 are marked DONE (bounded). U-ACT-017 Shoot and U-ACT-029 Deflect remain OPEN; U-ACT-022 Throw remains PARTIAL beyond U-CAP-004's bounded targeted Throw slice. A commit initially captured the earlier staged U-CAP-002/U-CAP-003 archive changes and U-THROW proposal move; a scoped corrective commit restored their original repository state and they remain staged, excluded from the Arena and documentation commits.

## Commits and audits

- `fdb4798d6066d7f3fe8ea82b6641e76ae4a585ce` — archive accepted U-CAP-004 and install U-CAP-005.
- `afb0113881ed76d2e7043761300277f6f092eb7d` — native Stun/Subdue. This commit accidentally swept the already staged U-CAP-002/U-CAP-003 archive deletions and U-THROW patch move. No history was rewritten: `b3950cfc926fd271d16d315744e8db6324e5ee71` restores those paths to their pre-commit repository state, and the original archive changes were reconstructed as staged work.
- `921cf8b8a925dcd285e6acf09d49188b09452630` — generated Arena Stun/Subdue composer and HTTP/session integration.
- Native and generated commits each passed `git diff --cached --check` and `.venv/bin/python -B tools/check_publication_safety.py --staged` (`findings=0`). The corrective staged inverse also passed the same safety check. The generated commit used `git commit --only` so the reconstructed archive changes remained staged and excluded.
- No push. Final closeout commit hash is included in the Codex closeout; it commits this report and `TASKS.md` only.

## Bounded limitations

- The one-hour recovery function is applied by native committed progression and its exact threshold is checked against a fresh-loaded persisted anchor; this execution did not run 3,600 committed one-second boundaries because the transaction pipeline makes that a slow UI test.
- The real Chrome smoke used a normal generated NPC without authored Stun training or a bludgeon Subdue loadout. Its character Actions panel correctly withheld unknown availability facts. End-to-end eligible control execution is proven by the generated Arena HTTP/session test fixtures with explicit scenario evidence.
- Shoot, Deflect and unsupported broader Throw/interception variants remain separate open Actions and are outside U-CAP-005.

## Final repository state

The following unrelated historical archive changes were already staged before this continuation and are preserved outside the U-CAP-005 commit: deletes of `docs/assignments/U-CAP-002.md`, `docs/assignments/U-CAP-003.md`, `docs/reports/U-CAP-002-report.md` and `docs/reports/U-CAP-003-report.md`, plus the Git-aware move of `docs/reports/U-THROW-001-rule-sync-proposal.patch` into `docs/reports/archive/`. Final HEAD, U-CAP-005 commit, staged audit and status are recorded before closeout.
