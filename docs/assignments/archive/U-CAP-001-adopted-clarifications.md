# U-CAP-001 — Adopted Delay, Draw, and Ready clarifications

**Date adopted:** 2026-11-13
**Project:** Universe Encounter / generated Arena
**Install as:** `docs/assignments/U-CAP-001-adopted-clarifications.md`
**Parent assignment:** `docs/assignments/archive/U-CAP-001.md` (completed and archived)
**Engineering report:** `docs/reports/archive/U-CAP-001-report.md`
**Status:** user-adopted rule clarifications and implementation instructions; **not a separate engineering assignment**. Integrate the governing rules into the next numbered adopted Encounter supplement and its controlling README. Retain this note as dated provenance, not as a competing rules authority.

## Adopted decisions (supersede the now-rejected interpretations)

1. **Delay:** A Being can wait, selecting the appropriate defense level and choosing a subsequent Action at a later one-second boundary. A Being may pause an *eligible* Action between committed seconds and subsequently resume **the remaining duration**, not restart it. Pausing cannot undo completed work or effects. Existing prohibitions on pausing spellcasting or momentum-dependent Actions such as a strike/charge are retained. Delay itself does not consume the preparation acquired by Ready.
2. **Ready is preparation, not a conditional-trigger declaration.** It does not commit to a later Action, a target, or a triggering condition. **Remove the conditional Ready/trigger-observation branch from U-CAP-001's required implementation.** No event/condition monitoring or hidden-Reality trigger engine is authorized by this adoption.
3. **Draw is a distinct Action preceding Ready when needed.** A weapon not yet drawn must be drawn before use; ordinary Draw adds its two-second time. Draw makes it available, but is not itself Ready and does not confer the Ready reduction. Quick-draw plus advanced weapon skill retains the existing essentially-no-time exception; do not silently invent a zero-duration Action to implement it.
4. **Ready provides an optional advance preparation benefit.** Once Ready is complete, it persists while the Being waits/Delays and until a subsequent Action uses that Object (except Delay). Strike consumes readiness. A drawn but unready weapon can be used to Strike with normal timing. Readiness is a committed fact subject to ordinary simultaneous-resolution and Save/Load rules.
5. These clarifications concern weapons and Objects now. Possible future readiness of **Events** is a retained direction, not authorization to invent Event-readying mechanics in this assignment.

## Adopted rule wording

The user approved the following distinct Draw and Ready sections. Preserve their substance and meanings when integrating into the adopted rule package; change only editorial formatting or cross-references needed for the current working draft.

### Draw

**Timing:** Normally 2 seconds.

Draw is an Action by which a Being takes a weapon from its stored or carried location and makes it available for use.

Drawing a weapon normally takes two seconds unless otherwise specified in the weapon description. A Being with Quick-draw skill and advanced skill in the weapon can draw it in essentially no time.

Draw does not itself provide the timing reduction associated with Ready. A weapon that has been drawn may subsequently be readied or used without additional preparation, in which case its normal attack timing applies.

Drawing and readying are distinct Actions.

### Ready

**Timing:** As specified for the Object or preparation involved.

Ready is an Action by which a Being prepares an Object for possible use in a subsequent Action. Readying completes whatever preparation can be undertaken without actually performing the intended subsequent Action.

A Being that has readied an Object is not committed to using it, to any particular Action, to a target, or to any condition under which the Object must be used.

Once completed, the preparation remains effective until the Being undertakes another Action using the readied Object, other than Delay. Merely waiting or delaying does not invalidate readiness.

#### Readying a weapon

The timing required to strike with a weapon is given in the Weapons Tables for each eligible attack motion.

One-third of the weapon's applicable attack timing, rounded down, is used to ready or re-ready it.

If the weapon has been readied and no intervening Action has used it, other than Delay, the time required for a subsequent strike is reduced by the applicable readying time. A strike can never take less than one second.

After a strike, the previous readiness no longer applies. The weapon may be readied again before another strike.

#### Readying another Object

To ready another Object is to prepare it for possible use in a later Action.

Preparation may involve retrieving the Object from a container, picking it up, positioning it, or otherwise making it ready for use.

The required preparation and its timing depend on the Object and circumstances and must be established by the applicable rules or adjudicated by the referee.

## Implementation outcome within the existing U-CAP-001

1. **Rules and documentation.** Examine current `docs/encounters/README.md`, revision 61 and adopted supplements through 68. Create the next *numbered adopted* clarification/supplement and update the effective rules index, task entries `U-ACT-007` (Delay), `U-ACT-015` (Ready), and relevant Draw/Strike entries. Supersede the earlier report's conditional-Ready interpretations and rejected A/B choices explicitly without falsifying its historical record. Do not amend unrelated worldbuilding rules.
2. **Native Actions.** Implement actual independently schedulable Draw and Ready semantics with an explicit authoritative weapon location/availability and hand relationship; do not conflate an existing `ReadyWeaponAction` *named* for ordinary Draw with the new preparation state. Use existing native Choice/transactional Action machinery, one-second boundaries, common frozen snapshot, atomic publication and deterministic RNG. Do not silently classify an Object in `possessions` as drawable or assign unrepresented hands/locations. Distinguish Draw (2s), preparation (floor of applicable weapon motion time/3), ordinary Strike, and Strike with the valid preparation reduction; apply the one-second minimum. Track actual preparation through delay, other Object uses, contact and release, interruption, repeated attacks and Save/Load. If motion-dependent preparation creates a genuine unspecified rule (e.g., readiness for different motions), use a conservative, declared eligible motion and record precisely what is and is not supported; do not silently grant a general discount.
3. **Delay.** Integrate voluntary indefinite waiting and eligible inter-second pause/resume (remaining duration) into the existing native Choice timeline and the general generated-Arena controls. Preserve earlier completed effects and legal defenses; no mid-second retroactive effects, no free cancellation of reservations/RNG, no unapproved momentum or spell pauses. Delay does not consume Ready preparation.
4. **User-facing exercise.** Generated Arena provides clear observer-authorized Draw / Ready / Delay / Resume / Strike choices, eligibility reasons, visible preparation/timing and cancellation; no raw native identifiers, invented trigger conditions or browser-side simulation. Do not claim unmodeled weapon source locations are available. Demonstrate reproducible legal user actions through shipped controls; if a native input fact is missing, solve it by an approved supported initial condition or report the exact external/rules constraint, not a privileged fixture mutation presented as gameplay.
5. **Focused acceptance.** Verify at least drawn-but-unready and already-ready weapon strike timelines; ordinary two-second Draw; a table-driven long-sword example (6s swing, 2s Ready, 4s prepared Strike); Ready→Delay→Strike; Ready→other use of same Object→normal Strike; repeated Strike without implicit renewed discount; interrupted/unestablished Ready; eligible pause/resume with remaining duration; prohibited momentum/spell pause; concurrent snapshot conflicts; and fresh-process Save/Load of drawn/readied and paused pending states. If a case is impossible due to genuinely missing adopted geometry/source/anatomy/skill semantics, identify the exact case and keep independently implementable paths moving. Verify observer privacy, rollback and unrelated equipment/Action regressions. Focus tests rather than rerunning the expensive full suite after every commit.
6. **Process and closeout.** Confirm the standing process document `docs/process/DEVELOPMENT-PROCESS.md` includes the earlier user-requested **ISO 8601 Start time and End time (with offsets), and elapsed duration** for each Codex execution interval, in both short chat and persistent reports; incorporate that process correction if still missing. Use actual measured times; do not invent missing timestamps. Keep `U-CAP-001` ACTIVE until its revised, adopted acceptance criteria are met, otherwise document a demonstrated genuine blocker. Record exact focused tests and timings, final HEAD and local audited commits in the existing `docs/reports/archive/U-CAP-001-report.md`; no GitHub push or history rewriting.

**Scope guard:** This is an adopted-rule supplement and continuation *within U-CAP-001*, not a new task program. When U-CAP-001 is honestly complete, close it and select the next outcome-oriented Action implementation program from live `TASKS.md` (do not invent a priority or begin unrelated programs without the user's authorization). Preserve `npc-generator`, `universe-geology`, saved data, ignored `legacy/`, `.venv`, backups and unrelated user files.

## Historical continuation prompt

`Continue docs/assignments/archive/U-CAP-001.md using the adopted rules in docs/assignments/U-CAP-001-adopted-clarifications.md. Integrate the next Encounter supplement, implement Draw/Ready/Delay through native and Arena with focused tests and fresh-process Save/Load, and continue to the existing assignment's acceptance criteria. Do not stop at intermediate milestones or push. Keep chat concise and record actual ISO 8601 execution times in the report.`
