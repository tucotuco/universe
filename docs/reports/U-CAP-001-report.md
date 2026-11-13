# U-CAP-001 — General Action composition report

**Status:** ACTIVE, with the independently implementable general composition/UI work implemented. Conditional Delay/Ready and the weapon re-ready lifecycle remain bounded by missing adopted timing/state semantics listed below. This report is the current status narrative; prior dated U-ARENA-018 reports remain historical evidence.

## U-ARENA-018 parent reconciliation

The original U-ARENA-018 acceptance minimum is reconciled and closed as DONE (bounded) in [the parent closeout](U-ARENA-018-closeout.md), commit `51249f5`. The original minimum's authentic generated-Arena Chrome contact/grappling walkthrough and required native Takedown/Reverse/Pin plus Trip-or-Wrest are evidenced in the closed U-ARENA-018D report; this does not close optional Stun, Subdue or complete Disarm variants. U-ACT stable IDs remain open where their broader scopes remain unfinished. The task register preserves one ACTIVE program, U-CAP-001.

## Implemented outcome

- Generated Arena provides an observer-authorized general composer for one-to-four ordered components from currently eligible, native-supported catalog entries. Current mappings cover Touch; armed melee/Feint/Disarm/Coup de grace/object strike/Break weapon; pickup and ordinary weapon Draw; Dodge preparation/use, Block, Parry, Yield; supported Being contact and Object contact/Wrest Actions.
- Target selection uses current observer handles, and the endpoint rejects unknown selectors, malformed resources, invalid timing order, unsupported catalog families and native-invalid combinations before whole-set Choice publication. Native `schedule_choice` remains the single validator and publication path.
- Component start offsets, per-component resource allocations and overlap priority penalties are explicit. The UI presents skill/STR/DEX and weapon-rank context. Native validation retains the adopted Multiple-action eligibility, resource and priority rules.
- Current program state projects order, event label, authorized target name, interval, remaining time, priority and resource allocation without Action or Choice IDs. One cancellation control undoes an accepted set or cancels all unfinished members of an executing set.
- Save/Load persists the accepted and running native Choice program; repeat cycles use fresh Action identities. The user's supplied UI composer was exercised in an actual seeded generated Arena browser session: Touch plus Dagger Swing with the second component offset one second was accepted by the shipped control and displayed both component timings/resources.
- No-cost automatic Hold maintenance and the revision-68 willing-Touch exception continue to use their distinct native contracts. Stun/Subdue, unmodeled action families and optional Disarm variants are not misrepresented as eligible.

## Acceptance verification matrix

| Requirement | Result | Evidence / boundary |
|---|---|---|
| Reconcile U-ARENA-018 original criteria first | Met | `docs/reports/U-ARENA-018-closeout.md`, committed as `51249f5`; U-CAP-001 is the sole ACTIVE program. |
| General eligible generated-Arena composer | Met for the native-supported catalog | Browser/session endpoint, opaque handles, resource/order/timing/priority controls and native all-or-none Choice validation; actual browser acceptance observed. |
| Sequential and mixed-duration overlap; execution and repeat | Met | Focused HTTP tests cover sequential Touch Save/Load, mixed Touch + Thrust, common start, completion, repeat with fresh IDs and cancellation. |
| Invalid overlap and no unintended RNG | Met | Generated browser test rejects two overlapping Touches without Multi-action skill and verifies RNG cursor unchanged. Native Choice suite covers transactional validation/publication and concurrency. |
| Program status, cancellation and persistence | Met for accepted/running general programs | New HTTP tests cover accepted cancellation, running sequential cancellation and fresh-process restoration; existing native tests cover repeat/abort and `/2` state. |
| Native simultaneous resolution, capacity, resource reservations, interruption, rollback | Met by shared native Choice infrastructure, with regression cohort | Existing native Choice tests cover priority/resource/endpoint behavior, competition, atomic rollback and interruption. See exact cohort result below. |
| Adopted Delay | Remaining rule/state boundary | Adopted text (r61) permits deferring a chosen Action, deciding in any later round, or pausing mid-action, with no specified native retained-action/resume boundary; defenses apply when Delay is independent. Native transactional state has no resumable paused Action. Do not invent when pause is sampled, how it resumes, or which completion boundary releases capacity. |
| Conditional Ready | Remaining rule boundary | Adopted text says a prepared Action triggers when a condition occurs and usually permits movement. It gives an example trigger but no trigger-observation authority, sampling boundary, or declaration/resolution ordering against concurrent Actions. A trigger resolver cannot safely infer hidden Reality or invent a same-boundary priority. |
| Ordinary Draw and weapon re-ready | Draw met; re-ready lifecycle remains | Revision 61 distinguishes two-second ordinary Draw from post-attack re-ready time and timing reduction. Native equipment exposes held/readied ownership but no consumed/unready state after a strike. Applying the reduction alone would silently grant repeat attacks without modeling the required re-ready interval/state. Revision 66 rejects assumptions about initial hand/readiness scope. |
| Adjacent Stun/Subdue and other open Actions | Out of scope and still open | Preserved under U-ACT-020/U-ACT-021 and other stable IDs; composer offers only complete currently supported native contracts. |

## Exact rule decisions needed to complete temporal branches

1. **Delay retention:** should an independent Delay be (A) a retained wait that completes only when the player explicitly chooses a new Action at a later one-second boundary, or (B) a condition-triggered wait that starts a selected Action on a trigger? A keeps the actor waiting for a player decision; B needs the trigger policy in item 2. Separately, the adopted text does not identify the legal mid-action pause boundary or whether resume continues remaining duration or restarts timing, so that branch remains out until specified.
2. **Ready/condition trigger:** should triggers be sampled (A) from this Being's observer-authorized evidence at each committed one-second boundary, or (B) from Reality events, including unobserved events? A preserves observation limits and starts the prepared Action at the next sampled boundary; B permits unseen triggers and needs a privacy/order contract. The adopted text does not say which controls, or how two prepared Actions triggered at one boundary contend.
3. **Weapon re-ready:** should a strike (A) consume the weapon's ready state and impose the one-third-timing re-ready interval before another strike, or (B) treat the one-third value only as a timing allocation discount without a consumed readiness state? These produce different strike cadence and save-state requirements. Revision 61 states the one-third rule but the current Encounter has neither a consumed-ready state nor a native re-ready interval; revision 66 rules out assumed initial-hand/readiness behavior.

No user decision is needed for the general composer or its native Choice integration. The independently implementable general composition scope is complete for the currently supported native catalog; leave this program ACTIVE pending temporal rule decisions.

## Verification and Git

- Actual browser interaction: shipped generated Arena UI accepted an ordered Touch + Dagger Swing program with the second start offset at one second. It showed component timing and resource allocations without native identities.
- `py_compile`: `PYTHONPATH=src:examples .venv/bin/python -B -m py_compile src/arena_browser_session.py examples/arena_web.py tests/test_generated_arena_browser.py` passed with the corrected assertion.
- Focused composer + label regression: four HTTP tests (the three `test_general_action_program_*` cases and the existing repeat/save control test) passed in 4.527 s.
- Native evaluator regressions: five focused tests for willing Touch, paralysis refusal without RNG, Grapple + Break-hold continuation, frozen priority and fresh-ID repeat/abort passed in 3.304 s.
- Combined command `PYTHONPATH=src:examples .venv/bin/python -B -m unittest tests.test_action_choices tests.test_generated_arena_browser` passed **118 tests in 87.246 s**. A preceding run had one stale assertion expecting the former `Abort Multiple actions` catalog label; updated the assertion to `Cancel Action program` and reran the full cohort successfully. `git diff --check` also passed. The full repository suite was not run.
- Idea inbox: `docs/ideas/inbox/` does not exist; no intake mapping or pending note.
- Starting HEAD for this work: `51249f5` (parent closeout). Implementation commit: `cea1708` (`Add generated Arena Action program composer`). Task/report state commit: `05d4395` (`Record U-CAP-001 composition status`). The report closeout correction is a documentation-only follow-up; its resulting HEAD and clean status are verified in the final repository check and final response. Implementation staged audit passed `git diff --cached --check` and `.venv/bin/python -B tools/check_publication_safety.py --staged` (`3 files; 0 findings`); task/report staged audit passed both checks (`2 files; 0 findings`). No push is authorized or performed.
