# U-ARENA-015 — Implement all currently rule-supported defensive Actions

**Repository:** Universe (Codex-owned)
**Install at:** `docs/assignments/U-ARENA-015.md`
**Report:** `docs/reports/U-ARENA-015-report.md`
**Replaces:** the earlier U-ARENA-015 assignment limited to prepared Dodge
**Approach:** One outcome-oriented integration milestone; work independently through engineering subproblems, make coherent commits, and return one final report.

## Outcome

Implement **all defensive Actions whose adopted Encounter rules provide sufficient semantics** to implement faithfully, not one action per assignment. Make every implemented defense available to native Encounter participants, and expose it in the generated Arena when its real prerequisites, equipment, and observer-authorized inputs are present. Include both the player and the existing `defense_only` opponent where appropriate. Keep unavailable choices accurately disabled with specific eligibility reasons rather than inventing prerequisites or effects.

**Do not stop after prepared Dodge.** Inspect the entire active defense catalog, implement the viable native capabilities in one development pass, and distinguish true rule gaps from merely missing code, tests, UI, or equipment. Investigate and resolve ordinary engineering dependencies autonomously. Do not ask for another micro-assignment between individual defenses.

## Authority and baseline

- Use the active Encounter rule package, its documented revision precedence, and source/tests as authority. Begin with the revision-61 **Appendix IV. Defense actions**: **Block, Deflect, Disengage, Dodge, Parry, Yield**. Inspect other adopted defensive mechanisms or strategy allocations (including sustained Guard if still authoritative), but distinguish them from the six named Appendix IV Actions. Consult revisions 62/63 and later adopted supplements for overrides.
- Review `docs/handoffs/universe-8-to-9.md`, U-ARENA-009 through U-ARENA-014 reports, and the present `MeleeDefense`, `MeleeStrike`, native movement, shield/weapon definitions, strategy points, Choice/action scheduling, simultaneous resolution, perception, transactional rollback, checkpointing, and browser session code. The old tactical duel/prototype is **not** authoritative.
- Preserve ES-011 declaration/observation ordering, ES-012 common post-movement/pre-Action snapshot and atomic simultaneous publication, and ES-013 preparation/retention/one-attack commitment of Dodge and Parry. Do not reintroduce the old provisional opposed-roll mechanics if they contradict the adopted defense-level/strategy rules. Inspect documented issues ES-024/025/026/027 and relevant adopted resolutions; verify current code rather than assuming historical audit findings remain current.
- U-ARENA-014 already has bounded attack-specific native Dodge against an observed pending `MeleeStrike` (two-second preparation), a player browser control, a `defense_only` opponent policy, and persistent pending/completed Actions. Extend/repair these rather than creating parallel versions. Attack-only movement and Thrust, NPC Generator 2.1.0 equipment, hex melee reach, ground pickup/Draw, and Save/Load all remain in force.

## Implementation requirements

### A. Audit and complete the defensive Action catalog

At the beginning of the work, determine for **each** named defense whether its current adopted rule and native data contracts are sufficient, which subcomponents exist, and which must be implemented. Use this working inventory, updating it from the actual rules:

| Defense | Adopted core contract to inspect | Integration considerations |
| --- | --- | --- |
| **Dodge** | Two-second preparation; strategy points allocated between defense and timing; prepared without an attack; retain readiness; commit to one observed eligible strike before outcome | Correct any old attack-specific/roll divergence; multiple attacks need Multiple Actions legality |
| **Parry** | Preparation one second less than defender's weapon timing; eligible skill/weapon, weight exception, +2 defense-level effect, prepared/retained and committed to eligible observed strike | Use actual native held weapon, skill, weight, and timing; document any unresolved weapon-motion timing choice, don't silently select an unsupported one |
| **Block** | Shield-based Action; preparation in seconds equal to shield size; -4 to attacker hit roll, effective shield size +1, damage stopped +2, shield arm occupied | Implement native shield effect and actual shield state; Arena lacks a generally supported starting shield, so use legitimate authored fixture for core proof and expose browser choice only for real equipped shield |
| **Yield** | One second, movement/space permitting; -1 to applicable incoming attack rolls; no bonus against archery, catapult, or thrown attacks | Use authoritative movement/facing and no teleporting; honor one-yard hex and continuous positions, movement-before-Action ordering |
| **Disengage** | Move away faster than all pressing opponents along open unoccupied hexes; engagement ends from actual movement/reach; no special parting attack or automatic zero defense | Integrate into native movement/engagement, not a magical disengaged flag; avoid collision/pathfinding inventions |
| **Deflect** | One second; requires Unarmed combat skill, freedom, awareness throughout trajectory; Dexterity check with projectile velocity modifier, weight/load and armor penalty; changes missed projectile destination | Implement native core **only if** sufficient real projectile trajectory, speed, skill, and targetability state exists. Do not invent a projectile simulation or assert deflect works in a melee-only Arena |

Audit **all** source-supported defensive mechanics and any applicable strategy-based Guard separately. If a defense's rules are sufficient but the production implementation is absent, **implement it**. If a listed defense cannot yet be exercised in the generated Arena because its *legitimate equipment or threat type* is missing, implement and test the native core against a valid authored fixture when possible; report that Arena availability is prerequisite-gated, not that the rule is intrinsically unimplementable. If an actual **rules ambiguity** prevents faithful mechanics, state the exact conflicting/missing rule, the minimum user decision, and the independently implementable parts completed. Never fabricate values to obtain a green demonstration.

### B. Shared native defense lifecycle

Use a consistent native Action lifecycle for every defense to which it applies: proposal → strict validation → acceptance → preparation → readiness/effect window → assignment/commitment to an eligible threat (where specified) → resolution/consumption or abortion/forfeiture. Not all defenses have identical readiness semantics: follow each adopted Action's rules, not a universal invented state machine.

For **Dodge and Parry**, make preparation **target-independent**, maintain ready state after their preparation time, allow use on an observed eligible strike in the same or a later second, and spend each prepared defense once. Multiple simultaneous strikes may not consume the same single ready defense twice; any permitted multiple defense must honor Multiple Actions and reservations. No defender may wait for an attack roll/outcome before deciding which strike to defend. A too-late or illegal defense must refuse without time, Choice, Action, evidence, or RNG changes. Honor capacity, weapon custody/ready state, skill, weight, armor, shield-arm occupation, strategy allocation and native actual time/reach constraints.

Use existing native combat rolls and effect records; **do not** introduce an Arena-side defensive probability, hit adjustment, shield absorption, or movement shortcut. Ensure defensive modifiers/effects are included correctly in the same shared simultaneous settlement as attacks. Defense may be effective without implying an attack necessarily hits or misses; keep the published outcomes and skill practice rule-conformant.

### C. Playable Arena and autonomous opponent

Expose all **currently eligible native** defensive options in the player Action catalog with accurate state, preparation timing, readiness, target/evidence restrictions, and refusal messages. For prepared defenses, distinguish `prepare`, `ready`, `use`, `spent` and `cancel` where those states exist. Browser requests use only observer-authorized handles; never expose private Action/Object IDs, hidden opponent state, source NPC profiles or uncommitted decisions.

Extend the existing `defense_only` opponent to choose lawfully among the available defenses, using **only its own observer-authorized evidence and committed native state**. Keep this a small deterministic policy, not a second combat engine or sophisticated AI. It must not launch attacks, make duplicate preparations, consume private player plans, or select a defense using an outcome that has not occurred. Do not equip the opponent with nonexistent items to make Block/Parry available; native equipment/skill eligibility decides. Preserve existing attack-only behavior.

Keep the existing **empty-ground** profile for positive melee acceptance, and preserve `uncertain_path` for unmodeled ground Objects. This task does **not** introduce Being 3-D geometry, line of sight, cover, missiles, thrown-object trajectories, general collision, or new starting-equipment policy.

### D. Save/Load, determinism and backward compatibility

Strictly serialize any new native Action state, ready/retained defenses, assignments, reservations, result/effect types, and observer-specific evidence. Test save/restore at preparation, retained readiness, after assignment but before impact, and after consumption/abortion. Compare continuous run with a loaded fresh-process continuation for native identities, Being state, Actions, Choice/event graph, observer histories, RNG cursors, and combat effects. **Load never calls `npcgen` or reselects equipment.** Validate/migrate old saves including U-ARENA-014 pending attack-specific Dodge, without silently losing an active defense or widening checkpoint admission.

## Acceptance and reporting

Deliver a **single meaningful end-to-end defensive combat milestone** with focused native and shipped-browser/HTTP tests, plus a real Chrome smoke when available. Demonstrate, as rules and equipment permit:

1. A defender prepares **Dodge before any attack is declared**, becomes ready at two seconds, retains it for additional seconds, and assigns it to a later observed strike before its outcome; only that one strike consumes it.
2. A legitimate skilled, armed defender performs the same target-independent preparation/retention/commitment for **Parry**, including preparation duration, incoming weapon-weight condition and defense-level effect.
3. **Block, Yield, Disengage** each produce their adopted native effect where prerequisites are represented, with focused positive and negative fixtures; do not simulate a shield by assigning unavailable kit equipment.
4. **Deflect** works if native projectile state is genuinely adequate; otherwise supply a reproducible, exact missing-dependency assessment and keep it disabled, without fabricating missiles.
5. Two same-boundary strikes with only one available prepared defense do not both benefit. Invalid/unobserved/late proposals are rejected without mutation. Existing attack-specific Dodge remains compatible.
6. The player and `defense_only` opponent use valid defensive choices in normal Arena progression; observer isolation and pending/ready/completed Save/Load survive fresh process boundaries.

Final report: a compact **six-action disposition matrix** (`implemented native`, `Arena usable`, `tested`, or `blocked with exact rule/data prerequisite`), adopted rule interpretations, meaningful positive demonstration, specific tests and their durations, code paths and commit hashes, and any *genuinely unavoidable* user decisions. Implement as many independently lawful defenses as possible **before** returning. A missing existing UI, adapter, test, or native class is an engineering task, not by itself a reason to stop. Do not exaggerate scope by calling a conditional or untested Action complete.

Use focused/nearby regression sets per coherent commit; avoid repeated hour-long full-suite runs. Run syntax and Git diff checks, then one appropriately broad integration verification for this milestone. Commit in small independently green groups (normally 1–3 implementation commits plus report). Preserve pre-existing unrelated tracked deletions/untracked files; stage only intended paths. Do not change sibling `npc-generator`, push, clean the checkout, or rewrite Git history.
