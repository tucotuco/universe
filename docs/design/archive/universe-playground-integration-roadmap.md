# Universe Playground — integration and persistence roadmap

> **ARCHIVED PROPOSAL — superseded for current planning.** Retained as design history only. Use [`TASKS.md`](../../../TASKS.md), the [current Arena roadmap](../Universe-Playground-Revised-Roadmap.md), and adopted Encounter rules for present direction; this proposal does not authorize implementation or change simulation rules.

**Status:** Proposed architecture and staged plan, 2026-11-04. **Not an adopted implementation contract.** No project source code, repository, or authoritative rules were changed by preparation of this document.

**Original proposed repository location:** `docs/design/universe-playground-integration-roadmap.md`. The document is now retained only at this archived path; its earlier link-integration suggestions have been superseded by the current task register and revised roadmap.

## 1. Purpose and demonstration goal

Build a **playground in which Universe capabilities become visible and usable**: develop a Being, equip it, place it in a local scene, run native Encounter Actions, see the consequences through appropriate observer perspectives, and save/reopen the continuing world without losing identity or history.

The long-term experience should feel like one coherent system while preserving distinct tools and their repositories. Early releases may involve importing/exporting files rather than a seamless live connection. Prioritize an end-to-end runnable experience over a proliferation of design memos or duplicate engines.

### First meaningful user story (target, not a current capability)

1. Create or edit a detailed Being in the independent NPC generator; export a deterministic, provenance-bearing character record with abilities, skills, and owned/held Objects where supported.
2. Bring that Being into a BattleCode Web local battlefield editor, add another Being, position them, and inspect the scenario. The editor distinguishes GM/editor knowledge from observer knowledge.
3. Start a supported native Universe Encounter. Perform a deliberately small set of supported Actions (for example Move and Spot initially; combat only after verified coverage). Show elapsed seconds, apparent actions, observed effects, and causal history.
4. Save a committed state, close/restart the relevant runtime, reload, and advance another Action. Confirm the same native Being identity, supported equipment/abilities, spatial state, provenance, owner-specific knowledge, and deterministic continuation.
5. Where a rule or attribute has no validated Universe counterpart, show a diagnostic or preserve it as **non-authoritative source metadata**; never silently claim the simulation used it.

These steps will be delivered incrementally. In particular, **editable scene JSON is not an authoritative Universe checkpoint**.

## 2. Components and proposed roles

| Component | Role | Evidence / caution |
|---|---|---|
| **Universe** (Python, primary source) | Authoritative Reality, native Being/Object identity, genealogy/population commitments, Cartesian positions, one-second Encounter scheduler/resolver/transactions, observer evidence, consequences and eventual portable checkpoint codec | Native Encounter and bounded save/resume exist. General mutable Being/Encounter/world persistence, broad inventory/skills closure and full combat coverage are **not** established. |
| **NPC generator** (`npc-generator-web`, independent Claude project) | Authoring of richly specified *candidate* Beings: attributes, abilities, skills, equipment/accumulated Objects, generation parameters/provenance | Its reconstruction goals include JSON export; actual current feature set, schema and validation must be inspected. Do **not** infer native Universe semantics from a generated field name. Historical `legacy/NPC/` is not a runtime dependency. |
| **BattleCode Web** (`battlecode-web`, independent project) | Local-map editor, arrangement, positions, sides/groups and eventual action visualization/replay | Prior starter specification describes a Vite/TypeScript browser editor and versioned JSON. Its **current implementation must be verified**. Legacy BattleCode did not provide a finished combat resolver. Sides/visual groups are not automatically Universe Group, population, or kinship facts. |
| **Earlier interactive Encounter playground** | Reference for map controls, choosing Actions, perceived opponent behavior, reach, timing, status/history, save/load/replay UX | Earlier work had a runnable bounded browser/HTTP prototype but not general authoritative Universe persistence or full r60 compliance. Reuse UX concepts or components after audit; avoid incorporating an obsolete parallel resolver. |

**Recommended composition (provisional):** use BattleCode Web as the **playground/editor shell**, adapt NPC generator exports into validated Universe Being candidates, and use a **thin local Universe runner/service** as the sole authority when a scene is played. Keep each repository independent; do not merge the three codebases. If the existing Encounter UI offers a more usable play surface after inspection, it could instead be the player view, but not a second rules engine.

### Data and control flow

```text
NPC generator                         BattleCode Web editor
  creates candidate Being(s)  ------> edits positions / sides / scenery
  with provenance                        |
                                         v
                           Versioned scenario draft + source refs
                                         |
                                  validate / import
                                         v
                      Universe authoritative scene and Encounter
                      - stable Being / Object identities
                      - Reality, Observation, Belief kept separate
                      - native schedule, resolution, atomic commit
                           |                         |
                  observer-filtered views        authoritative checkpoint
                           |                         |
                     playground UI            restart / continue / replay
```

## 3. Separate four kinds of data

1. **Generated candidate/profile** (NPC generator): authored/generated input, rule/profile versions and random seed; not yet a native realized Being. Unsupported fields remain clearly labeled and cannot affect simulation invisibly.
2. **Scenario draft** (BattleCode editor): layout, placements, editorial groups, visual styling and references to candidate profiles; may be changed by the editor until materialization. This is not historical Reality.
3. **Authoritative committed state** (Universe): stable native identities, allocated Objects, population/genealogy authority if present, Cartesian positions, mutable skills/inventory/HP as supported, observer ledgers, schedules/choices, event and Action histories, provenance, atomic receipts and RNG state. Only Universe can issue a portable checkpoint of this state.
4. **Projections and replay**: observer-owned views and committed causal history shown by the UI. Projections must not be used as a source for reconstructing hidden Reality. A replay is not automatically a general checkpoint.

For portable transfer, use small **versioned, inspectable file-based JSON contracts** initially, with explicit schema and engine/rule/profile version information and content/source identity. Avoid a database until justified. Validate imports atomically; reject conflicts, duplicate identities, unresolved required references or unsupported authoritative state. Never silently drop active equipment, skills, effects, pending Actions or observer evidence from a save advertised as resumable.

### Identity and ownership

- Import must bind each candidate to **one** Universe Being ID, persist a stable source-to-native mapping, and keep that mapping through save/reload. Do not create duplicate Beings when the same generated record is reimported or referred to by different layers.
- An equipped or owned Object has its own stable identity and explicit relationship to the Being. Do not confuse an object description or template with a realized, individually owned Object.
- Existing Population/StatisticalGroup conservation, ReproductionGroup identity and merge/alias semantics must remain intact; importing a character does not automatically fabricate household membership, parentage or counted population slots.
- Cartesian coordinates are authoritative. Battlefield grid/tile coordinates and ISEA TriFold are projections; define explicit reversible transformations and round-trip tolerance before connecting the map to native space.
- GM/editor view may show Reality for authoring, but observer/player views must use authorized evidence and beliefs. A successful Spot does not imply complete target disclosure. Deferred generalized perception rules remain deferred.

## 4. Incremental delivery

### P0 — Three-repository interface audit (read-only)

**Output:** one short evidence-backed compatibility matrix and one recommended simplest runnable integration pathway. Inspect the actual current commits, source entry points, frameworks, exports, existing save formats, native Being/skill/inventory APIs, map coordinates, Encounter actions and checkpoint restrictions, and previously built UI. Record exact capability and provenance; no edits to any repository or protected legacy files.

**Acceptance:** each claimed existing feature links to code/tests or is marked unverified; high-risk mismatches and possible reuse paths identified; practical recommendation for the first runnable slice. This is the next suggested task.

### P1 — Character-to-scene interchange (visible, no native simulation yet)

**Demo:** export one or two NPC-generated candidate Beings, import them into BattleCode Web, inspect supported attributes/equipment, place them on the map, save/reopen the scene. Use documented versioned JSON and clear unsupported-field diagnostics. First preserve every source field faithfully at the file boundary; only a separately validated subset will later become active Universe state.

**Acceptance:** deterministic identity mapping on repeated imports, no hidden data loss, scene JSON versioning and migration/rejection rules, tests and a short screen-based demo. Avoid writing to the historical legacy archive.

### P2 — Native Encounter bridge (first actual shared simulation)

**Demo:** materialize supported scene elements into Universe and perform at least one native supported Action; visualize its **committed** result in BattleCode Web. Start with a narrow preapproved subset rather than full combat and full generated abilities. Prefer an offline `scenario -> native run -> event/view JSON -> UI replay` loop before adding live APIs unless existing infrastructure makes live integration cheaper.

**Acceptance:** native Encounter authority only, no second combat resolver, reproducible action outcomes, truthful unsupported-action errors, IDs and positions conserved, no unauthorized observer information in player view, and no changes to unrelated projects.

### P3 — Genuine portable persistence of the integrated slice

**Demo:** save a committed Encounter with its supported Beings, mutable fields/Objects and observer evidence; restart in a new process; resume; compare with uninterrupted execution. Extend only the checkpoint closure required by P2; explicitly refuse unsupported scenes rather than claiming a general solution.

**Acceptance:** versioned and self-consistent checkpoint plus deterministic continuation and replay; two-process tests; stable identities, ownership, inventories, skills where live, RNG, history, pending commitments, cross-layer references and observers preserved. Test mismatches, old versions and tampering detection; distinguish integrity checks from authenticity. Preserve transaction and rollback invariants. Note that current native Run-only and separate reproduction codecs are insufficient as-is.

### P4 — A cohesive interactive playground

**Demo:** author/import, start an Encounter, choose an allowed Action in the browser, watch time and consequences, inspect what each observer knows, save/resume, and replay. A minimal local Universe service can accept **validated proposals**, not direct state mutation, and return committed outcomes and observer-filtered read models.

**Acceptance:** visible valid/invalid choices, simple timing/feedback, persistent encounter history, one authoritative engine. Avoid premature cloud hosting, authentication or database dependencies.

### P5 — Richer Being and world evolution

Incrementally activate NPC-generated skills, attributes, experience, inventory/equipment mechanics, injury/fatigue and combat only as their native Universe semantics are verified or adopted. Add Agent decision-making, unknown-target and multi-target perception, generalized world-generated Beings, statistical refinement, and global geography in independent bounded slices. Maintain explicit separation of historical/provisional rules from adopted r60 rules.

## 5. Architectural decisions to defer until the audit

- **Playground shell:** BattleCode Web editor as the host is preferred, but compare against the prior Encounter UI's actual maintained code.
- **Interchange mechanics:** determine current NPC export capabilities and schema, then define a minimal adaptation contract instead of requiring the NPC project to change its internal model.
- **Integration transport:** start with JSON files and local commands if sufficient; add a Python local HTTP service only when action-by-action play requires it.
- **Position conversion:** decide scale, axes, 2D-to-3D height and grid semantics with testable transformations, not implicit conversion.
- **Authoritative Being support:** identify exactly which abilities, skills, possessions and mutable fields Universe can now execute/persist. Mark the rest as authored profile data, not active physics/combat mechanics.
- **Save closure:** select first bounded committed-state schema only after inspecting current checkpoint codecs; include location observation recipient (currently rejected by portable codec) if it participates in the demo.
- **Action/observation permissions:** an editor's full-Reality display must not be mistaken for a Being's perception.

## 6. Risks and safeguards

**Rule-model drift:** NPC legacy rules might not match the current r60 draft. Treat imports as data; require explicit mapping and semantic approval for active mechanics. Never silently translate abilities or skills.

**Competing authoritative states:** map editor, generator and Universe could each believe they own the same Being. Keep one directional materialization boundary and one authoritative runtime; only explicit versioned exports are exchanged.

**False persistence:** scene import/export and UI replay are useful but not proof of Universe state closure. Claim general save/resume only when cross-process deterministic continuation tests pass for the declared scope.

**Information leakage:** separate GM/editor and per-observer read models. No direct client access to hidden Reality when running as a Being.

**Scope creep:** each assignment should produce a visible runnable story and 1–3 independently green commits. No mass repository copy, broad staging, legacy execution, unapproved NPC/Claude/BattleCode edits, or push without separate authorization.

## 7. Where we stand and suggested immediate next step

The authoritative Universe engine now has transactional one-second Encounters, a bounded integrated Being across genealogy/population/space, identity-free unique-target Spot, and observer-owned time-stamped Being location evidence. The last known full reported suite was 1,703 passing tests for U-LOC-002A; subsequent local commits have not been independently verified here. Generalized Being/Encounter/world persistence remains open. The NPC-generator and BattleCode-Web *current* working features must be inspected, rather than assumed from the reconstruction briefs.

**Recommended first assignment:** P0 read-only cross-project contract audit. Then decide P1's smallest demonstrable transfer. No feature implementation is authorized by this document. Once the roadmap is accepted and installed, link it from `TASKS.md` and appropriate `docs/tasks/` files in a separate narrowly scoped documentation commit.
