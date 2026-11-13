# U-ARENA-018 bounded closeout

**Status: DONE (bounded) on 13 November 2026.** This reconciles the original `docs/assignments/U-ARENA-018.md` against the live source, focused tests, actual Chrome evidence, and the closed U-ARENA-018D report. It preserves the original engineering report and the D closeout as historical evidence.

## Original minimum completion standard

The minimum calls for a normal generated-Arena contact/grappling walkthrough in the shipped browser; native Takedown, Reverse and Pin transitions; and at least one adjacent offense, Trip or Wrest. Evidence is present:

- Actual Chrome generated a normal Encounter and demonstrated map movement, perceived-target Touch, free-hand Grab, Grapple, Takedown, visible positional status and portable Save. It used ordinary Generate controls and no fixture state injection.
- The in-app browser completed the same route with pending-Grapple Save/Load and continuation through Takedown. The generated HTTP/session tests repeat the pending and committed-state Save/Load in fresh OS processes.
- Native transactional actions and tests cover Takedown, Reverse, Pin, Trip and held-Object Grab/Wrest. Three-Being custody and incompatible-position cases are included.

This is enough to close the stated minimum while retaining wider Action/UI limits as separate work. Chrome file-based Load is not claimed: the extension blocked local-file selection; fresh-process and in-app Save/Load are verified. The manual Chrome walkthrough did not operate Escape or Break hold as a defending player; the catalog/API exposes these eligible Actions, and native/session Escape plus Break-hold behavior is tested. This limitation remains visible under U-UI-001 evidence, not as a claim that every interaction was manually demonstrated in Chrome.

## Full Sections A–D review

| Original requirement | Reconciliation | Evidence / remaining scope |
| --- | --- | --- |
| A. Usable generated Arena; lawful movement and contact, status, positional transition, Save/Load. | **Met for the bounded loop.** | Chrome demonstrated Generate → move → Touch → Grab → Grapple → Takedown → Save. In-app browser and fresh-process tests demonstrate pending/resolved Save/Load. Observer handles and status are tested. Defensive Escape/Break is native/session-tested but not manually exercised in the Chrome run; Chrome file Load remains an extension permission limit. Broader observer presentation remains U-UI-001. |
| B. Takedown, Reverse, Pin, prerequisites, one-check transitions, failure/tie, conflicts, posture/movement, independent Grip lifecycle. | **Met for represented cases.** | Native snapshot/effect implementation and tests validate positions, size limits, failure preservation, compatible/incompatible control, pinned movement/attack restrictions, outside attack modifier/redirection, Grip release and six-second automatic maintenance. Unrepresented geometry/force and subsequent joint-holder contests remain explicitly unsupported. |
| C. Trip and/or held-Object Wrest; audit other supported close-combat actions. | **Met at bounded action scope.** | Trip and same-ID held-Object Grab/Wrest are transactional, with custody contention, rollback and persistence. Core armed/unarmed Disarm is implemented. Stun/Subdue and optional Disarm consequences remain separate U-ACT-020/021 and U-ACT-008 items because they require additional timed-condition, subdual/recovery, custody-selection or gauntlet-attachment state. They are not required by the original minimum completion standard. |
| D. Focused regressions, persistence, checkpoint integrity, Action delta register, report. | **Met at bounded program scope.** | Focused native, generated HTTP/JavaScript and fresh-process tests cover the accepted loop and rollback. Checkpoint/private-RNG validation was retained. U-ARENA-018D's report gives the complete detailed criterion matrix and exact test history; TASKS keeps every broader Action gap under its stable ID. No full repository suite or Chrome file-picker Load is claimed. |

## Task-register transition

- `U-ARENA-018`: PARTIAL / ACTIVE → **DONE (bounded)** for its original minimum close-contact program and represented Sections A–D outcomes.
- The sole ACTIVE program moves to `U-CAP-001` as authorized by that assignment.
- Remaining work stays under existing IDs: U-ACT-007 Delay, U-ACT-008 Disarm variants, U-ACT-012 broader Grapple, U-ACT-013 general Multiple actions, U-ACT-015 conditional Ready, U-ACT-020 Stun, U-ACT-021 Subdue, U-UI-001, and U-PER-002. No remaining item is silently absorbed into this bounded DONE claim.

Detailed source/test/commit evidence is in [U-ARENA-018D](U-ARENA-018D-report.md), [the original U-ARENA-018 report](U-ARENA-018-report.md), and the current [TASKS register](../../../TASKS.md).
