# U-ARENA-012 — First native opponent counterattack in the generated Arena

**Repository:** Universe (Codex-owned)<br>
**Type:** Bounded, playable vertical slice<br>
**Install at:** `docs/assignments/U-ARENA-012.md`<br>
**Report:** `docs/reports/U-ARENA-012-report.md`

## Outcome

From a newly generated, equipped two-Being Arena Encounter using the **empty-ground** profile, the opponent using the agreed **attack-only** strategy autonomously chooses and schedules a legal, native Dagger attack against the player. The player can move, choose an Action, advance through native one-second boundaries, observe the opponent's perceptible Action and its lawful consequences, and save/reload while the opponent attack is pending and after it resolves. The opponent must use its own *actual* `npcgen.api.arena_ready_being(...)`-created Dagger Object and the native Encounter Action, Choice, reach, facing, hit/defense, and damage systems. No parallel combat or AI-specific rules.

This is the **first two-sided combat slice**, not a general-purpose tactical AI. Keep scope narrow enough for one coherent implemented and tested milestone.

## Starting authority

- Read `docs/handoffs/universe-8-to-9.md`, `docs/reports/U-ARENA-009-report.md`, `docs/reports/U-ARENA-010-report.md`, `docs/reports/U-ARENA-011-report.md`, and the active Encounter rules and tests. Inspect implementation rather than relying on summary descriptions.
- U-ARENA-011 introduced native impact-time targetability for a Being occupying a one-yard regular hex when a weapon's reach penetrates that hex. **It did not** grant automatic hits or replace geometry for line-of-sight, cover, projectiles, or collision.
- The initial Arena strategy vocabulary already includes `random`, `attack only`, `defense only`, and `mixed attack and defense only` as intended options. Inspect which strategies, selections, session fields, and UI controls actually exist. This milestone only needs a working *attack-only* vertical slice; do not claim the others work unless tested.
- Default mixed/starter ground Objects may currently lead to `uncertain_path`. Use the explicit **empty-ground** fixture for acceptance. Do not change the world-obstruction rule or declare geometryless Objects transparent just to make the demo pass.
- Preserve native continuous Cartesian positions and 12-facing state, native one-second movement-before-Action evaluation and atomic publication, deterministic RNG, independent observer evidence, and exact cross-process Save/Load. Initial source NPC records and equipment provenance remain immutable initial specifications; native state evolves.

## Implementation

1. **Inspect and reuse.** Trace the existing opponent role/strategy selection and persistence, `GeneratedArenaSession`, player-only projection, `/api/generated/melee-strike`, native `MeleeStrike`, ChoiceBook/proposal→validation→publication workflow, action completion, and one-second advance. Identify the smallest server-side seam for autonomous choice. Do not build a second attack resolver or a broad strategy framework.
2. **Native opponent action.** At a legitimate choice point, an attack-only opponent with valid awareness/evidence of the player, a truly held/readied Dagger, and native capacity to act should issue a normal `MeleeStrike` proposal through the same authoritative scheduler as a player strike. Use the opponent's own Object ID. Choose a reproducible, supported attack motion (a fixed native Thrust is acceptable for this first strategy) and use native duration, range-at-impact, facing, and legality. Lack of a legal candidate must not fabricate a Choice, change RNG, or mutate the Encounter; keep the reason distinguishable for diagnostics. Do not auto-teleport, invent pursuit/pathfinding, rotate facing, or quietly modify equipment or target awareness.
3. **Avoid scheduling advantages.** The opponent must not inspect the player's uncommitted proposed Action or make retrospective choices based on the future. Schedule only at native, permitted decision points using the opponent's own currently authorized knowledge; ensure existing pending Actions are not reissued each second. Respect the native full-set validation/atomic-commit contract and common post-movement/pre-Action snapshots. If the present scheduler cannot admit simultaneous independent choices with those guarantees, implement the smallest compliant integration or document the exact contract blocker; do not bypass it.
4. **Browser play.** Reuse the existing strategy selector if present. If its attack-only choice is not wired, expose only the minimum needed to select it when generating a new Encounter, without presenting unimplemented strategies as effective. Show to the player the *perceptible* opposing Action and its timing/result to the extent allowed by current observer evidence. Do not reveal opponent NPC source fields, private HP, native IDs, inventory, or unseen Actions. Preserve UI terminal trace of player actions; do not leak private state in traces.
5. **Determinism and persistence.** Persist the selected strategy and all native pending/completed opponent Actions through versioned Arena Save/Load. Loading must not regenerate an NPC, kit, AI choice, or pending Action. Replaying from an identical saved boundary should yield the same resulting native events, HP, equipment/Action identities, Choice state, RNG cursor, and observer-authorized presentation. Failed or ineligible autonomous requests must leave no partially published action.
6. **Limits.** Do not broaden starting weapon catalogs, change `npcgen`, infer Being geometry or Object transparency, add sophisticated chase/pathfinding, add tactical bonuses, alter existing attack/defense mechanics, add victory conditions, or enable new strategies as unsupported placeholders. Retain the ordinary ground-loadout uncertainty as a clearly named outstanding issue for later adjudication.

## Acceptance proof

- Reproducible generated Arena (seed and parameters stated), two actual API-equipped Beings, empty-ground profile. Move/face through ordinary available controls to an encounter where the opponent can legitimately initiate a native strike; no manual post-generation mutation of native equipment, Awareness, positions, HP, or attack results. If movement/facing UI cannot produce the chosen scenario without a missing rule, isolate a test fixture for the additional condition and report the browser limit precisely.
- Show an **opponent-originated** native accepted `MeleeStrike` with the correct opponent actor, player target, opponent-held/readied Dagger Object, legal schedule, and impact-time resolution. Demonstrate the player's own independent attack path still works and there are no duplicate NPC submissions during a pending Action. Report genuine results (including misses/refusals if they occur); do not force hit/defense rolls.
- Validate reaction to no-awareness/no-evidence, unready or absent weapon, already-pending Action, unable-to-act actor, and out-of-reach at impact. These must follow the same native contracts as the player, with no information leaks or RNG/state corruption on refusal.
- Save while the opponent's Action is pending, restore into a fresh session with generation APIs replaced by failure stubs, continue both original and restored through resolution, and compare native identity/state/time/event/RNG equality; save and reload after completion too. Cover simultaneous player/opponent actions when supported by the native choice workflow.
- Run a real-browser smoke of strategy selection, opponent Action visibility, and native advance/result if loopback access permits. Distinguish real Chrome verification from HTTP integration tests and JavaScript harness tests; never claim an unrun check.
- Run focused new/affected tests, small nearby regression checks, syntax and `git diff --check`; avoid the full multi-hour suite on this increment. State exact commands, counts, durations, and limitations.

## Repository and report protocol

- Preserve unrelated pre-existing tracked deletions and untracked files; do not clean, restore, or stage them. Commit only intended changes in one or a few small coherent green commits. **Do not push** or rewrite Git history; the prior absolute-path publication issue remains separate.
- Do not modify the sibling `npc-generator` repository.
- Report: outcome and practical browser walkthrough; existing functionality reused; native chronological/observer/Save/Load proof; test commands/timings; changed files; commit hashes; precise unsolved blockers, especially ordinary starter ground-Object `uncertain_path` behavior.
