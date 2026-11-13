# U-ARENA-018 — Complete playable close-contact combat and recover remaining native rules

**Repository:** `universe` (Codex-owned)<br>
**Install as:** `docs/assignments/U-ARENA-018.md`<br>
**Report:** `docs/reports/U-ARENA-018-report.md`<br>
**Type:** Outcome-oriented implementation, including a real generated-Arena walkthrough<br>
**Invocation:** `Execute docs/assignments/U-ARENA-018.md.`

## Purpose and acceptance boundary

U-ARENA-017 successfully adapted R4.6's bounded Touch → Grab/Hold → initial Grapple → Escape/Break hold logic to the **current** transactional Encounter, including independent grips, after-protection HP-triggered releases, and fresh-process Save/Load. Do not repeat the catalog inventory or rebuild this path. **Now make it a usable, complete close-contact gameplay loop and integrate the adjacent adopted Actions that depend on it.**

Deliver **multiple substantive capabilities** in one engineering pass, committing coherent, independently verified steps; no permission-seeking or separate assignment for each Action. The minimum success criterion is (a) an ordinary, reproducible player-driven generated-Arena contact/grappling walkthrough through the shipped browser, **without privileged fixture mutations**, and (b) native implementation of Takedown, Reverse, and Pin with their adopted position transitions, plus at least one neighboring close-contact offensive Action (prefer **Trip** and/or **Wrest**) as allowed by adopted rules. If an actual adopted-rules ambiguity precludes one transition, finish other independently determined ones and provide a precise runnable obstruction proof. Missing code/state/tests/GUI are engineering work, not rule blockers.

Implement other clearly supported close-combat consequences (notably supported Stun, Subdue, unarmed Disarm) where common native prerequisites make them feasible within the same program; report each as tested/partial/absent. Do not trade away transactional correctness merely to broaden the count.

## Starting evidence and authority

1. Inspect the current branch and worktree; adopted `docs/encounters/README.md`, revision 61 plus later authoritative supplements; U-ARENA-015, -016B and -017 reports; source/tests for `src/action_evaluation.py`, `src/action_settlement.py`, `src/atomic_publication.py`, `src/transactional_progression.py`, `src/action_choice.py`, `src/arena_browser_session.py`, `examples/arena_web.py`, movement, observer evidence, Being/hand/custody, checkpoint reconstruction, and grappling state. Review the earlier R4.6 `grapple_encounter.py`/`test_resolved_grapple.py` and legacy combat code only to **reuse** still-valid calculation/test ideas; never dispatch their direct resolver from transactional progression.
2. U-ARENA-017 commit `1a28aec` established identity-specific physical Grips, six-second maintenance, Break hold, initial Grapple, Escape, and per-grip damage release. It is not proof of advanced control positions or a successful manual Chrome grapple session.
3. Preserve the adopted strict distinctions: Touch is not Grab; Grab/Hold is not Grapple; an established Grapple is independent of physical-grip survival; Escape is Grapple-only and does not release independent Grips; Break hold is Strength-only against one physical Grip. First Grapple preparation is a separately timed Action, with the specified coincident Hold-maintenance substitution. Targeted positive-HP damage can involuntarily release each Grip, including third-party strikes, based on common pre-action HP and after-protection damage.
4. Preserve movement-first, common post-movement/pre-Action evaluation, atomic settlement, deterministic RNG/Choice, observer-authorized identity handles, equipment state, hex-occupancy reach, and strict save/replay. No fabricated size, body geometry, force Newtons, collision transparency, or private player/opponent knowledge.

## A. Make the shipped generated Arena genuinely usable

The U-ARENA-017 Chrome smoke generated an Arena and opened the Action selector, but saw only the player's marker and `unknown` availability; it did not demonstrate a physical-contact Action. **Reproduce and diagnose the browser behavior first.** Determine whether it is legitimate observer filtering, an inactive/unsupported player state, a JS race, or a genuine bug—do not assume which.

Implement necessary UI/API integration and legal in-world setup so an ordinary **Generate** session can, using only user-accessible controls:

- See and select an opponent only if observer-authorized; move to contact range and obtain a free hand by lawful native state/Actions (or choose the existing supported unequipped start).
- Choose Touch, complete it, choose Grab with the valid Touch receipt, observe the resulting physical Hold, prepare/resolve Grapple, and choose Escape or Break hold when eligible.
- Show enough observer-authorized status to understand the current grip(s), their holder/subject, ready/ongoing Grapple, next maintenance check, and reason a proposed Action is unavailable. No raw private Action, Grip, Choice, or Generator IDs; use opaque handles.
- Perform and show at least one new position transition from section B in that same UI.
- Save and reload a **real** generated Encounter in at least one pending/retained state, then continue its ordinary native chronology.

Use a reproducible generated seed, XP, map size, starting-kit selection, initial positioning/movement, and Action sequence. Do not inject skill ranks, contact positions, successful rolls, grips, or Grapple control into a live browser session to make it pass; changing the RNG seed to find a naturally legal outcome is fine. Do not force results. Include exact click/action/boundary evidence or an equally reproducible authentic browser automation. Separately label actual Chrome proof, HTTP harness proof, and native fixture proof.

## B. Finish positional Grapple control

Implement adopted **Takedown, Reverse, and Pin**, with the authoritative control-position state and prerequisites (e.g. standing/advantaged/disadvantaged, size and participant restrictions where supported), using **one opposed Grapple check** at the next legal check boundary—not a gratuitous extra check. Failed/tied attempts preserve the position. Derive eligible combatants, modifiers, posture and resulting movement/action restrictions from the frozen snapshot; stage mutually compatible effects for one commit.

Support the adopted simultaneous incompatible-control reroll procedure where the represented participant/position prerequisites permit it. When a required size category or occupied-position fact is missing, use explicit supported native templates or reject the exact case rather than silently assigning a universal Medium/default geometry. Distinguish a real multi-grappler case from a narrow two-Being case and state what is still unsupported.

Correct remaining basic-state lifecycle gaps from U-ARENA-017:
- A Grip may end through lawful voluntary release; implement the rule-supported declaration/timing without turning release into a free off-books mutation.
- If the last prerequisite Grip ends in an **earlier second**, terminate only an **unestablished** first-Grapple attempt, preserving completed/established control and independent opposing Actions. Same-second release cannot retroactively cancel a concurrently resolving Grapple check.
- Periodic Hold maintenance must be correctly scheduled and must not require the player to remember arbitrary hidden bookkeeping. Verify whether U-ARENA-017's *one-second Hold-maintenance Action* representation matches the adopted six-second maintenance interval and existing Action-capacity rules; repair it if it introduces an extra player-declaration or unwanted competing Action.
- Validate movement limitations against physical Grips without inventing collision shapes; test joint approach, separation, release, obstruction/uncertainty refusal and rollback.
- Test multiple Grips, simultaneous damaging strikes, per-grip release and concurrent Grapple control changes against one frozen state; check deterministic evaluation order and replay.

## C. Integrate adjacent close-contact offense

**Trip:** Implement the adopted two-second follow-up after a *recorded qualifying* successful Touch/Grab/Bull rush/Strike. Validate the exact prerequisite identity and eligibility; use the attacker-Strength vs defender-chosen Strength/Dexterity contest, size/stability modifiers where known, native prone/posture effect, and cancellation of an attack scheduled for a **later** second without retroactively voiding same-second attacks. The initial minimal positive case may use Touch or Strike without first implementing Bull rush.

**Wrest:** Implement the one-second Strength contest following a successful Grab **of an Object held by another Being**, with exact Object identity and native atomic custody transfer. A Grip on a Being is not the same as grabbing a held Object; create the required separate supported object-Grab prerequisite and constraints before Wrest, rather than pretending the already-existing ground-object Pick up or Being Grab suffices. Preserve hand limits, observed evidence, and no cloning or loss of Objects.

**Other feasible close-combat actions:** Audit and implement supported variants of unarmed Disarm, Stun and Subdue using existing native contest, armor, critical, saving throw, condition/damage and interruption primitives **where the rulebook's prerequisites are satisfied**. Do not silently invent willing-target consent, underdefined body shapes, force-to-displacement, recovery physics, or a generic all-weapons unarmed mode; give exact blockers for any variant not completed. This section should produce working code where possible, not only a TODO list.

## D. Regression, persistence, and report

1. Focused tests for each new Action: eligible and ineligible declaration, failure/tie/success, target/hand/prior-receipt identities, posture/size validation, same-second compatibility/conflicts, damage/consequences, deterministic roll order, observer privacy, atomic rejected Choice and rollback. Cover held-grip loss before vs during first Grapple resolution, and the distinction between Escaping Grapple and breaking a physical Grip.
2. Save/load in a **fresh OS process** during pending Grapple/Trip/Wrest where supported, after posture/control transitions, and following voluntary/damage-induced grip releases. Compare native identities, timeline, positions/postures, custody, observer evidence, Choice and RNG, and eventual outcomes. Load must not regenerate NPCs.
3. Investigate the known checkpoint failures from U-ARENA-017. Existing baseline `test_module_rng_is_not_silently_assumed_private` must **not** be made green by weakening private-RNG validation. For `checkpoint_reconstruction.py:585` Arena-perception-ledger errors, establish the scope and actual baseline behavior and repair any current production Save/Load incompatibility if implicated. Distinguish sandbox loopback permission errors from native failures. Never claim all 49 tests passed; report the exact surviving failures.
4. Run focused new/adjacent regressions, syntax checks, `git diff --check` and real Chrome demonstration where network/browser permissions permit. Avoid the hour-long full suite unless a shared primitive requires it; report exact commands/timings, failures, and which tests were **not** run.
5. Deliver a compact updated **33-Action status matrix** listing only **changes from U-ARENA-017** plus remaining noteworthy gaps (do not recreate the full historical audit), a worked chronological browser scenario, tested core engine outcomes, new/reused logic, blocked variants and exact causes, and commit hashes. Preserve unrelated tracked deletions/untracked files. Do **not** push, rewrite Git history, or modify `npc-generator`.

**Completion:** Working end-to-end native positional Grapple Actions *and* a real player-operated generated-Arena close-contact sequence, plus at least one newly enabled adjacent Action (Trip or Wrest). A dependency inventory, fixture-only result, or a single tiny Action does not satisfy the assignment.
