# U-ARENA-017 — Recover and integrate earlier combat implementations

**Repository:** `universe` (Codex-owned)<br>
**Install as:** `docs/assignments/U-ARENA-017.md`<br>
**Report:** `docs/reports/U-ARENA-017-report.md`<br>
**Type:** Outcome-oriented implementation and legacy-code reconciliation; multiple coherent commits permitted<br>
**Do not push, rewrite history, change `npc-generator`, or touch unrelated worktree changes.**

## Why this assignment exists

Prior Universe work implemented more combat behavior than today's generated Arena exposes. In particular, the R4.6 *resolved grapple* experiment demonstrated a genuine, bounded `Touch → Grab → Hold → Grapple → Escape / Break hold` sequence with opposed checks, per-grip maintenance, and a distinction between grips and Grapple control. The older native/legacy `TacticalDuel` and `AgentDuel` code also contains combat calculations and tests. When explicitly selected transactional Encounter progression was introduced, older direct resolvers and facades were intentionally **guarded from use** because they could mutate state outside the frozen, simultaneous, atomic settlement path.

The present objective is **not to rebuild from scratch, restore the old resolver, or produce another catalog-only audit**. Recover correct earlier algorithms/tests where feasible and integrate a meaningful cluster of Actions into the **current authoritative transactional Encounter**, using today's adopted rule revisions. A historical implementation may be reusable, partially reusable, superseded by rules, or unavailable; establish which from source evidence rather than presuming loss.

## Current verified baseline

- U-ARENA-015: native Block, Dodge, Parry and Yield; Dodge/Parry have prepared/retained/one-use semantics.
- U-ARENA-016 and U-ARENA-016B: native Swing/Thrust; bounded Touch, armed Feint and melee Coup de grace; bounded Object-target Strike, armed Disarm, earlier-second Break weapon; generated Arena controls, native Action/Choice scheduling, frozen evaluation, atomic effects/receipts and persistence for the demonstrated paths.
- U-ARENA-016B reports **152** focused Action/browser tests and **61** transactional tests passing. One checkpoint-inventory regression (`test_module_rng_is_not_silently_assumed_private`) fails in a pristine baseline commit as well; preserve strict RNG-cursor validation and report, do not silently weaken it. Chrome verified basic selector wiring but not a real Disarm/Coup combat outcome.
- Current Encounter authority: `docs/encounters/README.md`, adopted revision 61 plus applicable later supplements/decisions, rather than historic prototype rules. Re-check the actual checked-out authority and source.

## Required outcomes

### A. Reconcile existing implementations before reimplementing

Inspect present and historically tracked code, tests, and available workbench source. At minimum search the relevant current/older source paths (`src/tactical_duel.py`, `src/ai_duel.py`, `src/melee_combat.py`, `src/melee_defense.py`, `src/action.py`, `src/action_evaluation.py`, `src/action_settlement.py`, `src/encounter.py`, `src/action_choice.py`, `src/transactional_progression.py`) and existing tests, `git log`/historical versions, `docs/encounters/`, and any available R4.6 grappling workbench (including `RESOLVED-GRAPPLE-VALIDATION.md` and local work-stash if present). Treat unknown locations as unknown: do not invent source paths or restore deleted user files.

Make a concise, source-backed **combat recovery matrix** for all 27 Appendix III and six Appendix IV entries, distinguishing:

1. current transactional implementation (and whether Arena-accessible),
2. still-present legacy/facade code requiring adaptation,
3. separate experimental code/tests worth reusing,
4. previously implemented behavior no longer present in the current tree (with Git evidence where possible),
5. never implemented or only a catalog/rule entry.

For every materially reusable earlier behavior, identify the precise module/function/test or commit and say **reused, adapted, superseded, or not yet integrated**. Do not mistake an Action label, a demonstration script, or an old checklist item for a functioning production Action. This investigation is **a prerequisite to implementation, not an alternative deliverable**.

### B. Integrate the physical-contact and Grapple vertical slice

Implement **native, transactional, independently identifiable** physical `Grab` and continuing `Hold`, distinct from the separately established `Grapple` Action/control state, with `Break hold` and `Grapple Escape`. Use existing current Touch as a prerequisite; reuse proven R4.6 check formulas and test examples where they match the adopted rules. No independent workbench simulator or second combat resolver may be called by Arena.

**Minimum playable chain:**

1. A player, using the ordinary generated Arena's observer-authorized Being target, successfully completes native `Touch` in legal contact range. Subsequent `Grab` is a **separate one-second declared Action** referencing the legitimate contact evidence/history and an appropriate available physical grip; do not award an automatic grip on Touch.
2. For an unwilling target, perform the **adopted separate opposed Grab check**: each participant rolls `3d6 + Improved Grapple ranks + better applicable Strength/Dexterity ability bonus + applicable Grab-specific modifiers`; the initiating participant must win. This is **not** an opposed d20 attack roll or a Grapple check. Commit one identifiable grip only on success; a tie does not establish it. Use native Being/body-part/hand capacity where actually represented, or refuse an unsupported attachment without inventing anatomy.
3. Establish **Hold** as the continuing state of that particular physical Grab, with individual six-second maintenance checks and lawful explicit release. Multiple individual grips must retain distinct identities; never use one shared boolean `grappled` flag as a substitute.
4. **Break hold** is a separate one-second Action against one identifiable physical grip with an opposed `3d6 + Strength bonus` contest; the breaker must win. No Escape Artist modifier and no automatic termination of someone else's already established Grapple. Changing one's own Grapple to Break hold follows the adopted Action/Multi-action rules, not a free added Action.
5. An initial **Grapple** requires a previously established qualifying Grab and separate six-second preparation unless legally accelerated by adopted strategy timing; its initial opposed **Grapple check** uses Improved Grapple, the better applicable Strength/Dexterity bonus, armor and other Grapple modifiers. Do not collapse the Grab check into the first Grapple check. If the first Grapple check coincides with maintenance of that prerequisite grip, resolve the **one specified Grapple check**, not two. Failure or tie does not erase the already established grip.
6. After a Grapple is actually established, implement the bounded native control continuation and **Grapple Escape** with its opposed Grapple check and the escaping participant's additive Escape Artist ranks. Escape is **not** available against a mere Grab/Hold; it does **not** automatically release independent grips. A loss of the last grip before the *first* Grapple check can invalidate the unestablished attempt, but release of grips later does not automatically end someone else's **established** Grapple.
7. Implement revision-61 **damage-induced release of physical grips** for positive HP damage from successful Swing/Thrust, including third-party hits: independent probability per grip `min(1, D / H)` using the holder's positive **common pre-Action HP** and the specific strike's after-protection HP damage. Independent tests for simultaneous strikes/grips, stage all releases, commit together, and never retroactively invalidate an Action resolving that same second. No such roll for equipment-only damage or nonpositive pre-Action HP.

Preserve exact one-second movement-before-Action ordering, target evidence and identity, actor/target and Object state, strategy/Multi-action capacity constraints, atomic refusal without RNG consumption, deterministic roll ordering, action history, and native checkpoints. The ordinary movement system must **not** silently permit an effective grip to be bypassed; where current geometry/force or movement constraints cannot make a specific displacement legal, refuse that specific move with a documented reason rather than fabricating body shapes, freezing every held Being in place, or silently dropping the grip.

If full advanced Grapple **Takedown, Reverse, Pin**, multi-grappler position conflicts, or special positional movement cannot yet be implemented faithfully, mark those distinct variants partial and give exact dependencies; do not label the whole Grapple Action complete. However, do not stop after only Touch or Grab: **the acceptance target is a genuinely exercised Grab–Hold–Break hold–Grapple–Escape chain**, with actual transaction and persistence evidence.

### C. Surface the integrated Actions in the generated Arena

Where native preconditions can be exercised with generated Beings, add legal contextual choices for `Grab`, `Break hold`, `Grapple`, and `Escape` (including current Hold/control status) through the established Action selector and strictly observer-authorized opaque handles. No privileged opponent Action IDs, hidden skills, generated NPC source record, raw RNG, or unpublished intention leakage. Explain ineligibility (missing successful Touch, missing grip, missing established Grapple, occupied hand/capacity, range, etc.). Opponent AI need not autonomously grapple in this assignment; do not change `attack_only`/`defense_only` behavior except for genuine compatibility.

Use native accepted Action results and published evidence for feedback; never mutate Being or grip state in HTTP handlers. An Arena browser smoke should, if environmental access permits, exercise actual Touch/Grab/Break hold or Grapple/Escape rather than only opening the selector. If real Chrome access remains blocked, document that limitation and provide executable HTTP/native integration proof.

### D. Persistence, simultaneity and regressions

Use a deterministic fixture and native Arena cases to verify, at minimum:

- A successful Touch does not itself create a grip; a failed Grab does not establish one; a successful separate Grab establishes exactly one identifiable Hold.
- Hold maintenance six seconds later, tie releases the specific grip, and independent grips do not collapse into one.
- A winning Break hold releases only its selected grip; failed/tied contests do not. No Escape from a mere grip.
- Established Grapple survives release of an individual or last physical grip as prescribed; first *unestablished* Grapple attempt responds correctly to prior loss of its prerequisite. Grapple Escape resolves control only, with continuing independent Hold restrictions.
- Same-boundary Break hold, Grapple checks and strikes evaluate against one frozen snapshot; outcomes become effective together, with deterministic RNG/rollback and no retroactive cancellation.
- Damage from a third-party strike may release a holder's grip; simultaneous hits use common pre-Action HP; no incorrect independent per-second roll or early exposure. Use a native multi-Being test fixture even though standard Arena generates two Beings.
- Fresh-process Save/Load in **preparation**, **established Hold**, **established Grapple**, and **post-Escape/Break hold** states continues identically (IDs, scheduled Action identities, receipts, Being/Objective state, observation evidence, RNG). Do not regenerate NPCs or reconstruct grips from descriptions.
- Existing native Object Strike, armed Disarm, Break weapon, Feint, Coup, Touch, defenses, movement, equipment, and attack-only opponent regressions stay green in focused relevant suites.

Use focused tests at each coherent commit; avoid the hour-long full suite for routine increments. Report exact commands, counts, durations, failures, `py_compile`, and `git diff --check`. Do not modify baseline checkpoint RNG privacy merely to turn its known legacy test green.

## Reporting and delivery

Deliver **one consolidated report** with:

1. A concise "Where we stand" and source-backed 33-entry recovery matrix (current/legacy/experimental/missing, exact provenance, migration/disposition).
2. A working native/API/browser Grapple-chain demonstration with before/after state, boundaries, Action/Grip IDs and actual outcomes. Separate live browser, HTTP, and native test evidence.
3. Tests, replay/checkpoint guarantees, rules fidelity, list of reused vs rewritten algorithms and why, and exact unresolved advanced variants.
4. A small number of coherent commits; unrelated tracked deletions/untracked files intact, no push/no `npc-generator` changes.

**Do not finish with only a survey, stub Action classes, an isolated alternate grappling simulator, or UI buttons that fabricate an outcome.** If an actual required rule is missing, implement the maximum independently supportable chain, provide a reproducible failing proof for the precise blocked transition, and explain why the unavailable step cannot be decided without inventing rules. Report partial completion plainly; never classify missing native code alone as a rule blocker.
