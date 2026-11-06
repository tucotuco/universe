# U-ARENA-004A — Universe 8 Arena v1 contract and integration audit

**Status:** Complete; documentation only. No application feature, generator migration, or save schema was implemented. **Date:** 2026-11-06.

## Executive assessment

Arena v1 has a clear product baseline, but it is not ready for an end-to-end GUI implementation. The two live repositories have no complete, versioned boundary that turns the Generator's source record into every required native Being and generated Object. Universe can preserve full source bytes, create native Beings, accept validated native Choices, and advance transactional Encounter boundaries; none of that supplies the missing data semantics or generalized save closure.

**Ownership recommendation:** keep NPC generation separately owned by `npc-generator-web` (Claude-owned workflow) and keep Universe simulation/identity/history/persistence in Universe (Codex-owned workflow). Co-develop a versioned, byte-preserving interchange contract and fixtures; do not add a runtime dependency or copy generator code into Universe. This best preserves meaningful parallel work, but the contract must explicitly distinguish generator inputs/results from Universe simulation facts. The existing schema v2 is not sufficient for Arena v1's requested exact starting XP and typed generated Objects.

**Shortest proposed first implementation slice after review:** agree on the interop contract and XP/Object semantics, then add a small Generate form that invokes/consumes two seeded Generator results, validates the complete source records, constructs two legitimate native Beings plus typed generated Objects, places them in reproducible initially empty one-yard cells, and exposes the initial native Encounter at `t=0`. Test that exact candidate bytes, source provenance, native IDs, experience, item identities/ownership, placements, and RNG streams survive the boundary. Do not start with the all-Actions catalog, opponent AI, or general save/load. Those remain required Arena v1 follow-on slices, not optional feature removals.

**Decisions before that slice:** confirm separate-generator ownership and the contract; define how the common integer XP value corresponds to Generator per-class XP and Universe experience; require typed Object semantics or define a strict refusal for unrepresentable generated items; and choose the initial observer/player presentation policy that does not disclose hidden entities. Facing display, opponent fallback, and file support are blockers before their respective UI/persistence slices, but need not block the first backend generation proof.

## Checkout, scope, and preservation

### Universe checkout at start

- Repository: `<LOCAL_HOME_PATH>`; branch `main`; `HEAD` `a97ba141fab8e86718e616a5f5a2234ea4624004` (`Update Universe 8 handoff publication status`). `origin/main` resolved to the same commit; no divergence.
- `git status -sb` showed an empty index, 20 pre-existing tracked documentation deletions, and pre-existing untracked user material including `.agents/`, `.claude/`, `docs/assignments/`, many reports, `examples/saved/`, `legacy/`, and `workspace/*.json`. The assignment itself was in the untracked `docs/assignments/` tree. None of those paths was restored, removed, staged, or otherwise changed.
- This task added only `docs/design/U8-Arena-v1-requirements.md` and this report. They were staged by exact path and committed together; the unrelated working-tree state remains uncommitted.
- Remote: `https://github.com/tucotuco/universe.git`. No push was attempted.

### NPC Generator checkout at start

- Separate repository found at `<LOCAL_HOME_PATH>-web`; branch `main`; `HEAD` `e5ae0a7e25acd36b795e964c3b7796f0a0470540` (`Add NPC-INTEROP-001 report`). No remote was configured in the inspected checkout.
- Its worktree was not clean: tracked deletion `docs/assignments/claude-npc-generator-standalone-git-repo-assignment.md`; untracked `Claude.dmg` and four NPC skill/interop assignment documents. I did not open the disk image, alter either repository, or stage any NPC Generator path.
- Its root [`CLAUDE.md`](<LOCAL_HOME_PATH>-web/CLAUDE.md) says the project is independently maintained and must not depend on Universe; its generation/runtime instructions require seeded reproducibility and keep generator values distinct from authoritative Universe simulation results. This is relevant source-owner guidance, not permission to modify that repository.

### Adopted rules checked

The controlling Encounter package is [revision 61 with limited revisions 62/63 supplements](../encounters/README.md). Revision 62 controls physical units/reference-arm/Reach/Throwing matters; revision 63 controls authoritative spatial-coordinate precision. Nothing in Arena v1 changes those decisions. Current working positions remain full-precision metric Cartesian values; user-facing spatial distances are yards. The requirements baseline is captured separately in [U8-Arena-v1-requirements.md](../design/U8-Arena-v1-requirements.md).

## Source and tests inspected

The source audit below used current files, not historical reports as proof. Relevant evidence includes:

### Universe

- [`src/arena_npc_import.py`](../../src/arena_npc_import.py): `NPCandidate.from_json/from_file`, strict `npcgen-npc` **schema v1** validation, exact source-byte retention and SHA-256, display name/seed/engine/rule metadata extraction, plus `ArenaBindingBook.bind` for explicit native definition, Being ID, geometry, and Cartesian position. It does not translate generator rules or source mechanics.
- [`src/npcgen_being_adapter.py`](../../src/npcgen_being_adapter.py): `create_npcgen_v2_native_being` validates one bounded v2 profile and creates a `BeingInstance`. It maps name, six named/cross-checked abilities, stature in inches, weight in pounds, initial current HP, and the exact `armed combat: 1` / `Dagger: 2` fixture skills. It refuses unresolved/unknown skill profiles and imports no source class/level/XP, race, possessions, family, psionics, Action history, or practice history. It does not create Objects or claim source Dagger ownership.
- [`examples/npc_encounter_arena.py`](../../examples/npc_encounter_arena.py): `build_arena` loads two v1 source fixtures, binds both to explicitly authored native Human definitions/IDs/positions/geometries, creates a native Encounter with no initial Awareness, enables transactional progression, optionally schedules one six-second native Spot Choice, and prints developer inspection. `build_unstarted_arena` leaves the fixed Choice unscheduled. Almost all source mechanics are metadata only.
- [`examples/arena_web.py`](../../examples/arena_web.py): `ArenaSession` and `serve_local` back the loopback page. Session methods include `gm_view`, `observer_view`, `submit_spot`, `advance_one_second`, `save_supported_state`, `submit_run`, and `save_s7_state`. Routes are allowlisted for this fixed scenario; the UI supports Spot then one-second advance, and approved checkpoint continuation for one Run. The page separates GM/Reality inspection from Ari and Bex Awareness projections, but is not a login or player-authentication boundary.
- [`examples/npc_encounter_arena_web.py`](../../examples/npc_encounter_arena_web.py): launches that loopback server. Save/resume destination and source are host-configured command-line paths; resume requires a separate affirmative local host-approval flag. It does not show a browser-native file picker.
- [`src/encounter.py`](../../src/encounter.py): native entity registration; geometry/line-of-sight helpers; directed Awareness; `propose_choice`, `edit_choice`, `validate_choice`, `accept_valid_choice`, `replace_choice`, and `cancel_action`; native `step` and transactional progression entry points. `step` alone is not the Arena's proposed Action catalog or Choice UX.
- [`src/action_choice.py`](../../src/action_choice.py): `ChoiceBook` proposal/edit, preparation/validation, acceptance, replacement/interrupt, reservation, and cancellation state. It validates whole native choice schedules and constraints; it is not a complete user-facing enumeration of every Action in the adopted rules.
- [`src/transactional_progression.py`](../../src/transactional_progression.py) and [`src/encounter.py`](../../src/encounter.py): native interval preparation, movement-before-Action snapshots, supported Action validation, atomic publication/recovery, and one-boundary progression. Supported Action families are explicit/limited; an Action catalog entry does not itself imply a native transactional resolver.
- [`src/observer_proposals.py`](../../src/observer_proposals.py), [`src/perception.py`](../../src/perception.py), [`src/attention_intent.py`](../../src/attention_intent.py), and `Encounter` Awareness APIs: observer evidence candidates can be staged transactionally; `RangePerception`/`GeometricPathPerception` are explicitly incomplete scaffolds; the identity-free Spot adapter binds exactly one unfamiliar participant or refuses. Existing `LocationEvidenceLedger`/`ObjectObservationLedger` are opted-in and bounded.
- [`src/arena_local_checkpoint.py`](../../src/arena_local_checkpoint.py), [`src/arena_s7_checkpoint.py`](../../src/arena_s7_checkpoint.py), [`src/arena_state_candidate.py`](../../src/arena_state_candidate.py), and [`src/arena_state_activation.py`](../../src/arena_state_activation.py): closed fixed S6/B1-B2 and S7 claim formats, exact fixture/source binding, digest/canonical validation, trusted-local admission, and one continuation path. These are not generalized Encounter save/load or proof of historical receipt authentication across processes.
- [`src/ai_duel.py`](../../src/ai_duel.py): `TacticalPolicy`, optional `OpenAIPolicy`, and `AgentDuel` choose among a fixed legacy command set from a tactical observation; `to_session/from_session` reconstruct by replaying that legacy session. This is not Arena-v1 native opponent strategy or a permissible simulation resolver.
- [`src/object.py`](../../src/object.py), [`src/universe.py`](../../src/universe.py), [`src/being.py`](../../src/being.py), [`src/actiondictionary.py`](../../src/actiondictionary.py): native Object/Being identity, position, geometry, facing defaults, object/weapon constructors, containment/equipment helpers, and Being experience properties exist. The Object action dictionary/config is not a complete proof that each displayed Action has a supported native transactional implementation.

### NPC Generator

The audit inspected current source at the pinned working revision above: [`npcgen/engine.py`](<LOCAL_HOME_PATH>-web/npcgen/engine.py) (`Generator._start`, `roll_random`, `roll_class`, `regenerate`, `replay`, `experience`, `set_level`, `resolve_skills_by_age`, `group`); [`npcgen/dice.py`](<LOCAL_HOME_PATH>-web/npcgen/dice.py) (`PyRand`, `Dice`, `roll`); [`npcgen/models.py`](<LOCAL_HOME_PATH>-web/npcgen/models.py) (`NPC`, `Possessions`, `Family`); [`npcgen/possessions.py`](<LOCAL_HOME_PATH>-web/npcgen/possessions.py) (`Equipper`, `equip`); [`npcgen/output.py`](<LOCAL_HOME_PATH>-web/npcgen/output.py) (`to_json`, `from_json`, legacy binary path); [`npcgen/persist.py`](<LOCAL_HOME_PATH>-web/npcgen/persist.py) (schema v2, validation, replay); `config/rules/experience.json`; [`app.py`](<LOCAL_HOME_PATH>-web/app.py); the `npcgen-npc-native-skill-candidate.json` fixture; and current Generator tests.

## Generator interoperability and field coverage

The standard interchange export is `npcgen-npc` schema v2 (`npcgen/persist.py`), with engine version/rules hash, seed, generation mode, edits, full `state`, sheet projection, and notes. `state.skills` is either unresolved `null` or an explicitly resolved profile. `Generator.roll_random(seed)` deterministically regenerates one random-mode NPC from its per-character seed and current rules; with no seed it gets a seed from the session RNG. The serialized `rules_hash` identifies config content. Replay uses seed + generation parameters + edits. Generator dice are isolated `random.Random`-based Python RNG per candidate/session; these are not Universe Encounter RNG state.

| Generator field/output | Live meaning/source | Existing Universe coverage | Arena v1 status / gap |
|---|---|---|---|
| `engine.name/version/rules_hash`, `generation.seed/mode/class`, `edits` | Engine/config identity and candidate-generation provenance; replay input | v1 `NPCandidate` retains exact source bytes/digest but accepts only schema v1; bounded v2 adapter's caller can retain original bytes | Preserve whole record and provenance; current v1 importer rejects v2; schema migration/compatibility policy needed. Digest identifies a record, never a Being. |
| `state.name`, `sheet.identity` | Character label | Both import paths can use a name; native `BeingInstance` has a distinct caller-selected stable ID | Names may be UI labels but must not become identity or leak undiscovered identity. |
| `state.scores`, `sheet.abilities.scores` | Six ordered and named Generator ability scores | v2 adapter validates exact agreement and initializes six native abilities for one narrow fixture contract | Field-level mapping exists only for this narrow profile; other states need validated coverage. Fitness is not in NPC output and may not be inferred. |
| `state.height/weight`, `sheet.age.height_inches/weight_pounds` | Inches/pounds in v2 | v2 adapter maps after positive/finite/cross-check validation | Reusable bounded mapping; geometry must still be explicitly specified. |
| `state.hps`, `sheet.hit_points` | Generator initial HP value, cross-projected | v2 adapter validates agreement and initializes native current HP | Does not map maximum HP, Hit Dice, or damaged history; broader profile semantics require contract. |
| `state.classes/levels/xps` and `sheet.classes[]` | One or more classes and per-class float XP, levels and source tables | No complete importer mapping. Native `BeingDefinition` has numeric `experience`, and `BeingInstance` getters/setters exist; no adopted equivalence policy. | **Blocking:** requested common integer XP is not an input to `roll_random`; random XP is generated from `experience()` and is a per-class vector. `set_level` chooses a threshold-band float. Mapping to native experience must not invent class/level rules. |
| `state.race/subrace/sex/age/month/day`, sheet identity/age | Generator-specific indexed race and demographic values | No complete race/demographic translation | Preserve source, but no native race/category equivalence may be assumed. |
| `state.skills`, `sheet.skills` | `null` means unresolved; dict means resolved skill profile | v2 adapter maps only exact `armed combat:1` and `Dagger:2`, cross-checks sheet and configured native dictionaries | Not a general skills importer; current sample age-budget rule labels its class mapping provisional. Skill does not imply owning a weapon. |
| `state.possessions.items` | Human-readable rolled items, e.g. `Armor: Leather +2` | No object construction in either NPC importer; Universe constructors can create explicitly selected Objects, weapons, armor and containment | **Blocking:** text labels are not typed native Object definitions, owner, equipment slot, modifiers, IDs, or containment. No-loss conversion requires typed export/contract or an explicit supported-object whitelist with refusal. |
| `state.possessions.exchanged`, `.gold` | Items exchanged for gold and remaining currency | No general native representation mapping in NPC importer | Distinguish generated Object vs exchanged/absent Object vs currency; do not materialize an exchanged item as still possessed. |
| `state.psionics`, `family`, `notes` | Generator data and narrative/projection | Not imported as native simulation state by the bounded adapters | Preserve with source bytes/metadata; do not invent spells, relationships, history, or awareness. Decide visible metadata policy. |
| distinct generated item instances/identity | Current export mostly lists type/name strings and text, not globally stable Object IDs | Universe Objects need actual identity and native definition; containment can represent ownership | **Blocking:** repeated same-type items, item expansion, modifiers, and nested containment require explicit identities and typed payloads before initial ground placement. |

### Requested experience mismatch

`config/rules/experience.json` defines a random experience roll; `Generator.experience()` generates a float using that rule, and `roll_random` supplies it to `NPC.xps` per class. The Generate form's common integer XP input is therefore not currently consumed by random generation. `set_level(slot, level)` picks an XP value within a class table band and reruns derived values; it does not set an arbitrary common XP amount. `BeingDefinition`/`BeingInstance` do carry numeric `experience`, but the NPC project's instructions explicitly caution that NPC class/level/XP semantics are not automatically Universe semantics. **Do not directly copy `xps[0]` into Universe experience without an adopted mapping.** Generator needs an approved API/record field for the requested generation input/result or the user must revise the requested semantics.

## Ownership options

| Model | Benefits | Costs and risks | Assessment |
|---|---|---|---|
| (i) Claude keeps Generator; Universe consumes a stable contract | Respects current repo ownership and `CLAUDE.md`; no runtime coupling; Generator can retain its rules/data and own deterministic output; Codex can independently build the native consumer | Contract release/version compatibility and duplicate cross-repository fixture tests; consumer must fail closed on unsupported fields; schema evolution coordinated | **Recommended.** Define a versioned Arena export contract, not a new runtime dependency. Contract should include complete current-state values, typed Object instances, exact requested XP input/output provenance, seed/config identity, and unknown-field preservation. |
| (ii) Universe absorbs generation core; NPC Generator consumes it | One code authority for generation/native mapping and easier in-process calls | Conflicts with Generator repo's independent-owner instruction; migration of config/rules/tests/UI; risks collapsing generator meanings into simulation meanings; broad and unnecessary scope | Reject for this increment. Reconsider only if independent project ownership ceases to be a requirement. |
| (iii) Shared, independently versioned core | Centralized deterministic generation code and one generator implementation; both apps could pin same release | New shared repository/package/release/test matrix and version coupling; Python runtime overlap helps but packaging/deployment and API stability still become shared work; weakens independent parallelism until contract matures | Not recommended initially. A data contract has fewer operational dependencies and permits parallel development. |

### Parallel Claude/Codex workflow

1. Agree a written, versioned export contract in a review step; do not co-edit either runtime blindly. Clarify exact XP semantics and typed inventory/object coverage before freezing fields.
2. Claude owns Generator output and its tests/fixture-generation command in `npc-generator-web`; Codex owns the Universe consumer and simulation tests in Universe. Neither repository imports the other's source tree at runtime.
3. Both repositories test against the same checked-in canonical fixture bytes: Generator validates deterministic emission against the contract; Universe validates complete-field acceptance/refusal, provenance, native projection, and that no generated field disappears. Pin the fixture digest/rules identity and update it only with reviewed contract version changes.
4. Parallel implementation can continue after contract approval: the consumer can use an approved fixture while Generator builds matching output. A mismatch blocks integration rather than being papered over by hidden defaults. This is meaningful parallel work without generator migration.

## Reuse and gap matrix — Arena surface and native workflow

| Need | Reusable live implementation | Gap/constraint |
|---|---|---|
| Empty UI -> Generate/Load | `ArenaSession` wraps a session and fixed scenario; `npc_encounter_arena_web.py` starts a loopback server | Current server starts fixed Ari/Bex scenario by default, not an empty generation/load hub. No generation form, map dimensions, file chooser, or atomic replacement UI. |
| Two Beings/native Encounter | `build_arena`; native `Universe`, `Encounter`, source bindings, explicit geometry/position | Fixed source candidates and Arena-authored native Human definitions; does not construct full generator-derived profiles or item Objects. |
| Native Action choices | `Encounter.propose_choice/edit_choice/validate_choice/accept_valid_choice/replace_choice`, `ChoiceBook`, native scheduler | Choice flow exists, but Arena endpoint allowlists Spot/Run only. Action config/catalog does not enumerate executable constructors and all currently legal targets. Full disabled/invalid/valid catalog presentation is new work. |
| One-second chronology | `Encounter.step(1)`, native `transactional_progression` | Reusable for supported Actions; cannot claim every adopted action has a transactional resolver. Legacy `TacticalDuel` stepping must not replace it. |
| Change/cancel | ChoiceBook replacement/interrupt and `Encounter.cancel_action`; schedule preparation tests cover stale/conflicting choices | The web demo does not expose general change/cancel. UI needs a decision-boundary lifecycle projection so a submitted Choice can be changed/canceled only under native semantics; no whole-choice rollback after executed boundaries. |
| Movement destination/arrow/ETA | Native continuous Cartesian positions; `RunAction`; current GM web SVG draws current position | No general destination UI or user-selected path planner. Speed/arrival can only be estimated when accepted native Action and movement state make them defined; map cell is presentation only. |
| Facing | `ObjectInstance` has `top_facing`/`front_facing` integer orientation state; r61 describes facing relative to hex geometry | Square-yard map is not native hex space. Direction rendering is unresolved; do not quantize or rewrite native orientation to four square-grid directions. |
| Observer projection | `ArenaSession.observer_view`; directed `Encounter.aware_*`; observer evidence ledgers and transactional proposals | Existing view is Awareness-limited for fixed identities; generalized accurate-perceptible properties and initial-contact rule are absent. Range/geometry perception classes are scaffolding, not a complete visual/sensory model. |
| Action perception | Native Spot and several evidence effects; supported Spot can make one unknown participant discoverable | No general visible Action recognition/intent disclosure. Do not show an opponent's private scheduler/target through the player Action panel. |
| Opponent styles | Legacy `TacticalPolicy`/`AgentDuel` and optional OpenAI policy offer examples of policy interfaces | Legacy legal commands/resolver/history are not the four required native strategies. No Arena native strategy selector, legal-candidate policy, fallback, observer-knowledge constraint, or strategy persistence exists. |
| Full Action catalog | `ActionDictionary`/configured data and supported native action preparers | Known text/config entries, constructible classes, accepted schedules, transactional resolvers, and situation-valid choices are different sets. Need an explicit registry with implementation status + reason and engine validation for the current situation. |

## Spatial/display findings

- Universe is continuous metric Cartesian space with full precision; user-facing distances are yards. Grid cells must map to the native metric presentation frame, not hold a second authoritative position.
- Existing sample Beings are explicitly assigned Cartesian positions and `Sphere` geometry. No general generator-derived geometry exists; physical size must not be treated as collision geometry.
- The square-cell map can provide one-yard initial placement, but cell-to-position origin/axis, vertical plane, and footprint need explicit presentation conventions. Native movement remains free of cell quantization.
- Initial uniqueness is implementable as a generation-time allocator over selected empty cells. Later overlap/movement/collision are still governed by native spatial rules. Appending one edge-neighbor cell can maintain a connected irregular set, but random candidate choice and expansion RNG must be explicit/reproducible.
- Generated possessions currently mix item labels, exchanged items and currency; some item strings embed category/modifier text. Before placement, the contract must distinguish unique generated Object instances from equipment/contained objects, currency, exchanged objects and descriptive text. Ground placement requires a reversible explicit extraction from inventory; it cannot be inferred safely from one flat list.
- Native facing has `top_facing`/`front_facing` defaults and r61 defines six hex sides or points. The square display can render a separate arrow/overlay for that orientation without changing it, but the visual mapping needs user review.
- Current native movement Actions can yield authoritative displacement/destination and speed. ETA is a UI estimate only when the accepted movement model provides enough information; terrain, pathfinding and collision-aware route times are out of scope.

## Persistence and browser file access

### Current native persistence is narrower than the baseline

- `Universe.save_to_file`/object serialization does not close a general active Encounter's receipt-authenticated chronology, pending choices, active Actions, RNG and observer ledgers as one resumable Arena.
- U-ARENA-003's fixed B1/B2/S6 and S7 formats validate exact historical claims/source bindings and require affirmative local-host approval; U-ARENA-003C successors demonstrate fixed-local continuation only. They retain one scenario and bounded next actions. They are not user-selected generalized saves.
- Native publisher receipts are process-local; portable data cannot invent those receipts. Imported history remains a labeled host-accepted claim. A general format needs a provenance model that distinguishes validated/imported history from receipts newly issued in the current process.
- Arena source candidates/binding records are session-side objects today, outside some checkpoint graphs. General closure must include exact source bytes/digests plus stable mappings to native IDs, generator/rules versions, and any typed generated Objects.
- A save at stable decision points must include ChoiceBook drafts/accepted choices/reservations, Action declarations and mutable progress/cancellation state, pending movement, all Target state/history, observer evidence and ledgers, native geometry/positions, clock/next boundary, source records, policy selection, and each owned deterministic RNG stream. It must reject an in-progress publication/transaction.
- Safe load should parse and validate a detached full candidate graph and cross-reference every identity, schema, source and RNG before publication. Build a fresh quarantined Universe/Arena candidate, activate only after all validation succeeds, then atomically swap the session's active-state reference. On any error preserve the current Arena and return the baseline text `not a valid Encounter file`; no repair, regeneration, or defaults.

### Browser file picker path and limitations

The existing local browser page obtains paths from server startup flags, not from browser UI. The local process cannot directly choose a client file path merely because its server binds loopback. A feasible browser flow is: invoke the picker from a user click; read selected bytes in the browser; POST bytes to the loopback server for detached validation; after a successful save snapshot, return exact bytes to browser code and write through a selected save handle. MDN documents `showOpenFilePicker()` and `showSaveFilePicker()` as secure-context APIs and marks compatibility as browser-dependent: [open picker](https://developer.mozilla.org/en-US/docs/Web/API/Window/showOpenFilePicker), [save picker](https://developer.mozilla.org/en-US/docs/Web/API/Window/showSaveFilePicker). Treat browser support as a declared target and test it. A fallback `<input type="file">` can open a user-selected file; a Blob download can save, but its location is browser-controlled and it does not provide the same arbitrary-path save picker. Decide whether such a fallback meets the user's OS-mediated location requirement.

The existing `write_local_bundle` uses host-side POSIX temp-file/fsync/link semantics, validates a fixed bundle, stores outside the repository, and refuses overwrite; that is useful evidence for atomic file writing but is not a substitute for browser-selected handles or generalized load.

## Genuine semantic decisions / blockers

### Before the first generated Encounter slice

1. **Confirm ownership recommendation.** Keep NPC generation in the separate repo with a stable contract, unless the user intentionally changes its ownership model.
2. **Define common integer starting XP.** Is it a Generator input that drives class/race/level and per-class `xps`, an exact native Universe `experience` value independent of Generator XP, or a different convention? No current method implements this input.
3. **Require complete typed generated Objects.** Confirm that Generator will export exact instances with a supported native type/definition and stable source-local identity, or choose fail-closed generation when an item cannot be represented. Do not silently omit possessions or turn descriptive strings into Objects/mechanics.
4. **Initial player knowledge/view.** What may the controlled Being initially perceive, and is initial contact explicit Awareness/evidence, or does the initial map begin empty until native perception Actions resolve? No automatic Awareness from generation.

### Before the corresponding later slices

5. **Operator versus player naming/details.** Can an operator rename and inspect hidden entities in a distinct GM panel while player labels stay unknown, or must names/details only be editable after perception? This is needed to reconcile global editability with no leakage.
6. **Square cell/facing rendering.** Approve a faithful visual orientation overlay for native hex-side/point facing.
7. **Strategy semantics.** Select when/persist the four strategies and decide what each does if it has no legal candidate Action, without introducing hidden information or new combat eligibility.
8. **Browser target/fallback.** Approve supported browser(s) and whether `<input>`/download fallback is acceptable when File System Access picker APIs are absent.
9. **General save trust and process boundary.** Decide the authority/provenance representation for old accepted history versus future native receipts, and the level of portability expected. Digest-only files cannot authenticate simulation history.

The first four are the actual blockers for the proposed generation vertical slice. The remaining decisions should be staged with their respective UI/persistence increments rather than guessed in advance.

## Proposed shortest implementation sequence

These are proposed follow-on slices, **not assignments or authorization**. Each is limited to 1–3 small green commits and should receive its own reviewed scope/acceptance before code changes.

### Slice 1 — Contract and generated native start (first implementation assignment)

1. Add/approve a versioned interop export carrying complete generator provenance, exact XP request/result semantics, resolved current state, typed Object instances/containment, and unknown/source metadata; add a deterministic paired fixture/contract tests in the Generator repo and Universe consumer test.
2. Add a fail-closed Universe adapter that verifies the whole contract and creates two distinct native Being IDs plus Object IDs/instances, preserves exact source bytes, applies only adopted field mappings, and refuses unsupported fields rather than filling defaults.
3. Add Generate inputs and reproducible random placement to a local unstarted Arena; create the `t=0` Encounter, keep Encounter RNG separate from generation/placement RNG, and expose only the approved initial player projection. Test object/cell uniqueness, edge-connected expansion, source and generated counts, exact XP, replay, and refusal/rollback.

This completes one executable vertical slice from user input to native generated Encounter state. It does not satisfy all Arena v1 Actions, AI, or generalized persistence yet; later assignments must implement those baseline requirements.

### Slice 2 — Native decision/advance and information-safe interaction

1. Build an explicit Action registry distinguishing known-but-unimplemented, implemented-but-currently-invalid, and selectable native Actions; delegate actual validation to ChoiceBook/engine.
2. Add player destination/Action proposal, target parameter forms, native movement/choice display, replacement/cancellation, one-second native progression, and committed-action timelines.
3. Implement the four constrained opponent policies over legal choices available from its permitted view; test empty legal-action fallback, choice cancellation, simultaneous commits and observer non-leakage. Do not use `AgentDuel` to resolve simulation.

### Slice 3 — Complete atomic save/load and browser chooser

1. Specify and test a closed Arena snapshot for stable decision points including accepted/active/cancellable choices, Entities/Objects, histories/evidence, provenance and RNG; distinguish imported claims from newly issued receipts.
2. Implement detached validation + fresh candidate reconstruction + atomic active-session swap, with invalid input preserving the prior state and exact error message.
3. Add browser-native open/save chooser for the declared browser targets and fallback behavior; test save at each legal decision point, during-action continuation/cancel, corruption, unsupported schema, RNG equivalence, and rollback/no replacement on failed load.

## Verification and environmental notes

No full Universe or Generator suite was run; this was a bounded documentation/audit assignment. No loopback browser server was launched.

| Command and working directory | Result |
|---|---|
| In Universe root: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests python -m unittest test_npc_encounter_arena test_npcgen_being_integration test_action_choices test_schedule_preparation` | **91 tests passed** in 8.211 s. Covers current narrow import/Encounter, NPC v2 adapter, Choice and schedule contracts. |
| In Universe `tests/`: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=../src:. python -m unittest test_perception` | **7 tests passed** in 0.047 s. Uses the relative config path expected by those fixtures. |
| In NPC Generator root: `.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_engine.py tests/test_output.py tests/test_persist.py tests/test_native_fixture.py` | **42 tests passed** in 1.39 s. Covers deterministic engine/replay, output/persistence, schema and bounded native skill fixture. |

Exploratory attempts were corrected and are recorded for reproducibility: an initial Universe command named three nonexistent modules (`test_choice_proposal`, `test_choice_validation`, `test_choice_acceptance`); it nevertheless ran 25 schedule tests but exited with 3 import errors. The corrected command above used the actual `test_action_choices` module and passed. An initial root invocation including `test_perception` ran 98 tests with 7 errors because those fixtures resolve `../src/config` relative to the current working directory; rerunning the perception module from `tests/` passed all 7. The system Python in the NPC Generator repo lacked `pytest`/`jsonschema`; rerunning through the repo's `.venv` passed. Pyenv emitted a non-blocking “cannot rehash … isn’t writable” warning; disabling pytest cache avoided changing the NPC worktree.

Documentation checks after writing: `git diff --cached --check` passed; report/requirements diff reviewed for exact paths before commit. No source/application tests, network listeners, broad suite, or writes to the NPC Generator repository were performed.

## Final Git state

- Universe HEAD after the documentation-only commit: the exact self-hash is provided in the delivery response (omitted here to avoid a self-referential report hash).
- Exact commit paths: `docs/design/U8-Arena-v1-requirements.md`, `docs/reports/U-ARENA-004A-report.md` only.
- No push. The initial tracked deletions and all other pre-existing untracked material remain untouched and unstaged. The NPC Generator repository remains at its initial state, including its pre-existing deletion and untracked items.
- No application implementation, NPC Generator migration, schema implementation, broad refactor, dependency change, Encounter-rule edit, or persistence authority change.
