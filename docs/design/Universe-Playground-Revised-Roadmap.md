# Universe Playground — Encounter Arena roadmap

**Status:** Revised proposed roadmap, 2026-11-04. Replaces the earlier BattleCode-Web-centered P1–P5 recommendation after review of `universe-playground-p0-assessment.md` and the user's decision to exclude BattleCode from near-term integration. This document is planning guidance, **not** an adoption of new Encounter or NPC-generation mechanics. No feature implementation is implied.

**Repository location:** `docs/design/Universe-Playground-Revised-Roadmap.md`. Keep this reachable from `TASKS.md` through the appropriate task entries. Preserve the earlier BattleCode-centered roadmap and P0 assessment as historical evidence; do not rewrite their findings.

## 1. Outcome: a limited, genuine Encounter Arena

The short-term playground lets a user generate or edit NPC candidates, import their complete source records into a small local Arena, create native Universe Beings and place them in Cartesian space, initiate **supported native Encounter Actions**, inspect committed consequences and observer-specific evidence, and ultimately save/restart/continue a bounded Encounter. It should become interactive quickly, but implementation remains incremental.

**Universe is the only simulation authority.** The NPC generator is an independent authoring source; the earlier Encounter UI supplies interaction patterns and possibly safe presentation components, **not** a second resolver. BattleCode Web and its grid/schema/conversion are **not** part of the near-term plan. The separate BattleCode repository remains untouched.

This Arena is a useful development/playback surface for the wider Universe project, **not** a replacement for its statistical-world, geographic, Agency, Reality/Observation/Belief, reproduction, or transactional goals.

## 2. Grounded P0 findings and immediate implications

P0 inspected local sources read-only. It reported Universe `main` at `fd9910d29b18eecd552772c0e36d927897b5de4d` at inspection time (not a claim about current HEAD); `npc-generator-web/` was an independent untracked nested project with no verified Git revision. Native Universe `make_being()` and Encounter APIs exist; `examples/live_combat.py` / `src/tactical_duel.py` offer UX references but their tactical facade is a legacy consumer, not an approved transactional engine. Universe's portable checkpoints are bounded and reject certain observer-location recipients. The NPC generator's `npcgen-npc` JSON carries schema/rule identifiers, seed, edits, state, and display data, but **not** a reviewed Universe-native skill list, native Object ownership, or native ReproductionGroup parentage. No field-by-field authoritative mapping has been adopted.

Therefore the first goal is **candidate -> explicit native Being binding -> native Encounter outcome**, not candidate -> editable BattleCode scene. Run a focused source-contract check as part of that slice; do not launch another stand-alone multi-project audit.

## 3. Ownership and truthful data boundaries

| Artifact | Owner / meaning | May be edited? | Persistence status |
|---|---|---|---|
| NPC candidate (`npcgen-npc`) | Source-generated authored profile and provenance, including unrecognized fields | In NPC generator or explicit new source revision | Versioned import/export; **not** a native Being or world checkpoint |
| Arena draft | Explicit participant binding, selected native creation defaults, initial Cartesian coordinates, and selected scenario parameters | Before simulation, by Arena author | May be a versioned scenario file; **not** a resumable simulation state |
| Native Universe state | Realized Being/Object identity, Actions, positions, histories, practice, observer evidence, RNG, transactions | Only by legal native simulation operations | Requires a validated, closed **authoritative checkpoint** to resume |
| Arena presentation | GM/developer view and observer-filtered read-only projections of committed state | UI controls propose Actions; presentations do not mutate truth | Not sufficient to reconstruct Reality or RNG |

**Identity:** A source record's digest identifies that exact content revision, not a person. Bind a source candidate to a separately assigned stable native Being identity, explicitly and only once within a session. Do not silently bind different source revisions, deduplicate separate people, or regenerate native IDs on resume. Imports do not imply population slot, residence, ReproductionGroup, Group, relationship, belief, or knowledge.

**Property activation:** Show and retain the entire source record, but only explicitly validated fields may become mechanics. Display names are safe for presentation; ability scores, HP, age/size, class/level/XP, possessions, family narrative, and skills require semantic review before activation. Text possessions are not realized native Objects. Unsupported source fields must remain visible as unimplemented metadata or produce clear diagnostics, **not** silent gameplay effects.

**Space:** Use Universe continuous 3D Cartesian coordinates directly for the first arena. A rendered local 2D map is a view with documented scale; it is not an independent authoritative integer-grid world. No BattleCode grid conversion needed.

**Information:** A designer/GM may inspect Reality; a Being sees only authorized Awareness/Observation/Belief. Do not convert native hidden state or old UI omniscience into observer evidence. Generalized Object/Event/action/velocity perception remains deferred under `docs/design/deferred-object-event-perception.md`.

**Encounter:** All Actions use the supported native scheduler, common snapshots, publication/rollback, and r60 semantics. The historical `tactical_duel` resolver cannot be used as the authoritative engine. Never claim an unsupported combat mechanism is integrated.

## 4. Development increments and demonstrations

### A1 — First executable native Arena (completed: U-ARENA-001)

**Demo:** Import two valid NPC generator JSON candidate records; retain exact source records and provenance; create two distinct native Universe Beings with explicit IDs/bindings and explicitly authored Cartesian starting positions. Render a minimal local map/readout plus Action timeline. Schedule/resolve one or more **verified supported native** Actions demonstrating two participants (for example native Spot involving the other Being and a simple Move), then show committed state and observer isolation. If native combat is verified safe within the bounded scenario, it may be used instead, but do **not** extend the rule engine to manufacture that demo. Report which candidate properties affected simulation and which were reference-only.

**Acceptance:** deterministic, repeatable CLI/local demo with inspectable output; source record round-trip/provenance intact; identity stable and separate from digest; no invented skill/inventory/parentage, no second resolver; meaningful native Action effects; explicit invalid-input refusals; focused tests, existing suite maintained. Interactive web UI and general save/resume are not required for A1.

**Bounded result:** [`examples/npc_encounter_arena.py`](../../examples/npc_encounter_arena.py) uses two exported v1 source records, preserves exact source bytes/provenance, and binds display names to two explicitly identified native Human Beings. It commits one revision-60 Spot through the transactional publisher and reports the result as developer inspection. Only names map from NPC source; positions, definitions, geometry, and roll are Arena-authored. See U-ARENA-001 in [`TASKS.md`](../../TASKS.md) and [`docs/tasks/encounter-engine.md`](../tasks/encounter-engine.md). This does not activate generator-derived mechanics or add browser controls.

### A2 — Minimal interactive Arena (next planned increment: U-ARENA-002)

Revisit the actual `examples/live_combat.py` / prior Encounter UI. Reuse safe UI components, controls, visual language or timeline concepts after verification; replace/avoid any facade that owns rules or serialization. Present positions, known/apparent Actions, time, selected participant and committed effects through read-only projections. An operator may propose and submit valid native Actions; each request must be validated by Universe's Action choice and transaction machinery. Keep a distinguishable GM view versus an individual Being's viewpoint. Start local; no cloud or cross-project merge.

**Demo:** two imported participants; choose a supported Action, step time, see correct committed result and history. Do not silently hand out observer omniscience. If existing UI is unusable, implement the smallest new presentation layer rather than repairing a parallel tactical resolver.

### A3 — Bounded portable Arena checkpoint

Save a **supported** committed Arena state, start a fresh process, restore and continue a native Action, compare against uninterrupted simulation. Explicitly include provenance/bindings, stable native identities, live supported attributes, positions, RNG, relevant Actions/choices, observer records, receipts and references. Investigate checkpoint refusals, including `BeingLocationObservation` recipients from U-LOC-002A, **only within** the chosen supported closure. Unsupported authoritative state must be refused, never dropped. Protect reproducibility across versions; a checksum is integrity detection, not authenticity.

A saved Arena draft and event replay are not substitutes for this checkpoint.

### A4 — Activate richer NPC properties incrementally

After reviewing NPC vs r60 meaning and native APIs, adopt/test specific mappings one at a time: ability scores, HP and injury, real inventory/equipment/ownership, trainable skills and practice, experience and other background data. Model Objects separately; do not infer kinship from narrative, or let class/level/XP import rewrite native rules. Each mapping has explicit acceptance examples and preservation tests.

### A5 — Broader Arena/world development

Expand verified combat and opposition, tactical controls and replay, observer evidence, Agent decisions, world-generated Beings, and eventually larger scenes as independent slices. Generalized statistical/spatial realization, ReproductionGroup and other world domains remain in Universe's main roadmap; Arena demonstrations should integrate them only through authoritative interfaces.

## 5. Cross-cutting safeguards

- No modifications to independent `npc-generator-web/`, `battlecode-web/`, historical `legacy/`, `.agents/`, `.claude/`, saved examples, or workspace JSON without separate authorization. Source-generator reads are allowed; do not import private saved candidates without approval.
- Preserve current native one-second transactional commitments, reproducible draws, observer isolation, population conservation and parentage identity.
- Use a small number of independently green commits (1–3 per assignment) with exact path staging; no automatic push.
- The Arena is allowed to display a candidate's non-operational details, but **must distinguish display from authoritative gameplay state**.
- No broad speculative persistence rewrite. Work toward one demonstrated cross-process resume at a time.
- Every adopted roadmap change or new design note must be findable through `TASKS.md` / linked topic tasks.

## 6. Current recommendation

The next Codex assignment is **A1 — NPC candidates in a native Universe Arena**, with `docs/assignments/U-ARENA-001.md` as the proposed implementation task. It is a bounded runnable demonstration, not another reconnaissance report. Before implementation Codex must confirm actual checkout/head, the latest r60 and native APIs. Architectural conflicts must be surfaced rather than resolved by silently adopting NPC-generator mechanics.
