# Faithful native Encounter replay — bounded evidence

**Status:** completed bounded validation slice for U-PER-SCALE-001; not a production persistence design or closure of the broader ACTIVE program. Production `/12` is unchanged. This is a same-source/rules/current-version correctness check, not a promise to rerun historical outcomes under changed rules or RNG algorithms.

## Problems first

- This fixture demonstrates the declared two-Being state closure and Events that the current recorder knows how to capture. It does not restore general native `CommittedBoundaryRecord` query objects, every Encounter/Being/Object type, arbitrary observer evidence, pending external Choice workflows, or all Action families.
- A naturally failed or unproductive Action was not reached in the fixed-seed run. The fixture does not force a roll or change rules to make one occur; this optional branch remains unproven. The consequential strike is native and successful.
- Four quiet boundaries retain required Encounter clock/cursor changes. They do not repeat unchanged Being/Object properties. The experiment does not claim that every quiet interval can be omitted: a change in represented time-dependent state must still be recorded.
- The artifact is integrity-sealed against accidental/tampered edits but is not signed or an adversarial authenticity format. A party able to rewrite the data and recompute its digest can produce a self-consistent alternate recording; re-execution against the pinned current engine detects discrepancies for this fixture.
- No production `/12` state is read or rewritten. This bounded result does not establish generic sufficiency, scalability, long-lived compatibility or Arena Save/Load behavior.

## Scenario and execution

The fixture is authored in `examples/encounter_delta_headless.py` and resolved only by native `Encounter.step()` and transactional publication. Ada and Bram are Human BeingInstances, begin at x=0 and x=2, and have directed awareness of one another. Ada has a Dagger. The fixture uses fixed IDs, private RNG seed 0, pinned source/config/rules, and ordinary native Run, Delay, Choice and MeleeStrike Actions.

The time-indexed record has nine boundaries. It retains the full initial native projection, one atomic before/after change set per boundary, every committed Event (including an Event with no Being/Object change), receipt-level Effect identities, and a full native-state snapshot at each boundary as an independent verification oracle. Historical reconstruction itself uses only the initial projection and ordered changes/Events; the nine snapshots let the verifier compare reconstructed values/presence against the original native state rather than replaying its own output. `native_headless_resume.py --playback` reconstructs selected boundaries and cumulative Event histories without calling `Encounter.step()`. `--reexecute` starts a new Encounter, resubmits the recorded legal declarations and advances the real native engine in a separate Python OS process.

From the repository root:

```sh
record=$(mktemp)
.venv/bin/python examples/native_headless_resume.py --record-full "$record"
.venv/bin/python examples/native_headless_resume.py --playback "$record" \
  --boundary 2 --boundary 3 --boundary 4 --boundary 7 --boundary 8 --boundary 9
.venv/bin/python examples/native_headless_resume.py --reexecute "$record" \
  --id-prefix independent/
.venv/bin/python -B -m unittest tests.test_faithful_replay \
  tests.test_native_headless_resume tests.test_persistence_headless_delta
rm "$record"
```

The test launches separate OS processes for recording, historical playback, native re-execution, and strict checkpoint resume. Historical playback is also tested with `Encounter.step()` patched to fail if called. Playback and re-execution report no imports from Arena session/controller/server code, `arena_native_snapshot`, or `npcgen`.

## Boundary evidence

`entity changes` counts changed Being/Object property paths; clock/cursor and RNG paths are listed separately in the recording. `delta bytes` is the canonical JSON size of that one boundary record. SHA-256 is over the native state projection, not Python runtime graph identity.

| t | Native Event(s) | Being/Object changes | Changes (all paths) | Delta bytes | Native state SHA-256 prefix |
|---:|---|---:|---:|---:|---|
| 1 | Run success | 4 | 8 | 2,906 | `fd3310dc3449` |
| 2 | quiet | 0 | 4 | 546 | `89b9794978bb` |
| 3 | Delay success; no Being/Object change | 0 | 4 | 1,732 | `a6923775c211` |
| 4 | two Runs success, one shared native commit | 6 | 10 | 6,945 | `f556c85b13c8` |
| 5 | quiet; pending schedule bookkeeping | 0 | 5 | 685 | `703410b32ee6` |
| 6 | quiet | 0 | 4 | 546 | `b6c50fa5a6a3` |
| 7 | quiet | 0 | 4 | 546 | `41cd36857a8d` |
| 8 | MeleeStrike thrust, normal | 4 | 10 | 19,251 | `bf072da4ea3e` |
| 9 | quiet after the strike | 0 | 4 | 546 | `7b8c21204747` |

At t=4 both Run Events are in one receipt and one shared atomic delta. At t=8 the native `MeleeStrike` targets Bram: the receipt associates five ordered EffectIdentity entries with that Action (effect slots 0/1, lifecycle slots 0/1, and release slot 0). Native proposal effects are `DamageEffect(source_action_id=action-native-dagger-strike, target_id=being-bram, amount=4, component=body)` and Ada's Dagger `PracticeEffect`. Bram HP changes 10→6. The t=3 Delay is a completed zero-Being/Object-diff Event; its `DelayDefenseEffect` remains in the Event even though no Being/Object property changes. t=2, 6, 7 and 9 are quiet with respect to Being/Object facts.

The player-independent fixture preserves the actual observer-specific facts represented by its `awareness_by_observer` projection. It does not claim general evidence/belief-history or sensory fidelity.

## Declared projection and exclusions

The replay state root is `schema`, `encounter`, `beings`, `weapons`, and `rng_state`. The exact captured Encounter fields are `id`, `difficulty_class`, `participants`, `pending_action_ids`, `cancelled_action_ids`, `time`, `start_time`, `last_processed_boundary`, `coordinator_time`, `interval_start`, `initiated`, and `awareness_by_observer`. Each Being projects `id`, `type`, `name`, `definition_key`, `position`, `hit_points`, `armor_id`, `body_parts`, `states`, `posture`, `size_category`, `hex_facing`, `fatigue_level`, `physical_fatigue`, `physiology_id`, `geometry`, `abilities`, `skills`, `weapon_skills`, `skill_experience`, `skill_practice_baselines`, `skill_use_history`, `strategy`, `personal_history`, `possessions`, `weapons`, and `armed`. The Dagger projects `id`, `type`, `name`, `definition_key`, `position`, `parent_container_id`, `hit_points`, `weapon_size`, `attacks`, and `geometry`. Exact field closure is enforced; absent keys, explicit nulls, and present values remain distinguishable. See the source-linked [native resume findings](persistence-headless-resume-findings.md) and [serialized field catalog](persistence-node-field-catalog.md) for prior closure evidence.

Action Event records are a separate typed history projection containing Action/Event identity and class, event type, parent, actor, target/targets, start/end time, outcome, proposal Effects/metadata, Choice/member packet, Action-specific data, and ordered receipt EffectIdentity references. Definitions are referenced by pinned Library key; they are not copied into the recording. Excluded or fail-closed cases include any other Being/Object kind or registry shape, active/unsettled Choices, unsupported Action/Effect/Event classes, non-null personal history outside this fixture closure, generic Universe registries, arbitrary perception evidence/beliefs, and restored historical native receipt object APIs. These are scope boundaries, not evidence that the broader runtime has no such state.

## Semantic identity and reference audit

Event identity inside one logical Encounter is retained as `event_id`/`action_id`; duplicate, missing and ambiguous same-Encounter identities are refused. The Event's parent Encounter, actor, target, Action choice/member references, causal proposal-effect source/recipient, ordered EffectIdentity source, boundary, channel and slot are validated. An independent native Encounter may generate different Action/Event and Choice IDs: the test creates an injective mapping across nine such references and applies it recursively to Event, Choice, receipt, state and Effect source references before comparison. The stable Being, Object, Encounter, definition, and parent Encounter identities are not remapped. There are no external references to this experimental artifact that prevent generated Action/Choice IDs from being consistently remapped.

The five EffectIdentity records are composite receipt references rather than independent UUID strings; their causal Action source is mapped, while Encounter/boundary/channel/slot and multiplicity/order remain exact. The test rejects repeated identity within one logical history and fails if independent identities map non-bijectively. Save/Load of a continuing logical Encounter continues to preserve existing generated identifiers; this mapping is solely for comparing independently instantiated runs.

## Storage and execution measurements

One local sample (canonical UTF-8 JSON; timing varies by host):

| Measure | Result |
|---|---:|
| Initial state | 9,020 bytes |
| Full t=4 checkpoint state snapshot | 10,748 bytes |
| Full t=9 terminal state snapshot | 11,388 bytes |
| Nine change/Event delta records | 33,703 bytes |
| Event arrays within those records | 7,651 bytes |
| Property-change arrays | 24,918 bytes |
| Nine full snapshots retained as validation oracle | 94,649 bytes |
| Complete sealed recording including validation oracle | 266,521 bytes |
| Quiet t=2/6/7/9 delta records | 546 bytes each |
| Native Event-only t=3 delta | 1,732 bytes |
| Historical selected-boundary query (includes validation) | 24.2 ms |
| Nine-boundary re-execution/comparison (includes pinned compatibility check) | 2.37 s |
| Individual native `step(1)` calls | 219–290 ms in this sample |
| Strict fresh-process Load/rehydration from t=4 | 47.5 ms |
| Fresh child process plus continuation through t=9 | 1.76 s wall time |

These values are fixture measurements, not a controlled comparison with an Arena save or a claim about large histories. The initial+delta/Event read model does not require the nine redundant verification snapshots; they are retained here so every reconstructed boundary can be independently compared with the original native state. The history stores clock changes and actual schedule/skill/combat changes; it does not repeat unchanged Being/Object properties on quiet boundaries.

## Fidelity and refusal matrix

| Requirement | Evidence / result |
|---|---|
| Native authored two-Being Encounter; no Arena/npcgen dependency | Met; native steps are the only resolver. Fresh playback/reexecute report no forbidden imports. |
| Historical playback from initial state; query selected times and cumulative Event history | Met for the declared projection; separate CLI process, `Encounter.step()` patched to fail, state equals each recorded boundary. |
| Property presence/value reconstruction | Met for every field in the explicit projection; canonical state and explicit before/after presence checks are applied by the delta reader. |
| Successful moving Action | Met at t=1; Ada's position changes. |
| Quiet boundary and zero-Being/Object-diff Event | Met at t=2 and t=3. |
| Atomic simultaneous batch | Met at t=4; two Run Events share the same receipt/boundary. |
| Native consequential combat and causal Effects | Met at t=8; Bram HP 10→6, Dagger practice, five ordered receipt Effects. |
| Observer-specific state represented in fixture | Met for directed awareness projection at each boundary; general evidence/belief history excluded. |
| Fresh-process same-version native re-execution | Met across t=1–9; ordinary native Actions submitted from declaration manifest, all state/delta/Event/action/Effect/receipt fields and RNG compared per boundary. |
| ID semantics across independent Encounter instances | Met using a validated one-to-one generated ID map; stable world/Encounter identities remain fixed. |
| Fresh-process selected-checkpoint resume | Met at t=4→9; playback's t=4 state matches the persisted checkpoint projection and strict native resume matches the uninterrupted control. |
| Failure and corruption handling | Met for checksum corruption, wrong preimage, missing/reordered commits, duplicate property paths, malformed chronology/time, broken Event/Effect references, duplicate and ambiguous ID mapping. |
| Naturally failed/unproductive Action | Not demonstrated; optional branch remains unproven rather than forcing a roll. |
| General historical native receipt APIs / all native field families | Not claimed; bounded read model only. |
| Production `/12`, Arena Save/Load and cross-version re-simulation | Excluded and unchanged. |

Historical re-execution is only a current-version correctness check for persistence representation. Durable historical facts are not expected to be re-resolved using changed rules, definitions, source or RNG algorithms.

## Sufficiency assessment

For this fixed Encounter and its explicitly enumerated current-state closure, initial state plus every committed typed/presence-aware property change, all native Events (including zero-Being/Object-diff Events), causal Effect/receipt references, and selected complete snapshots is sufficient to reconstruct and query the demonstrated history. The independent t=1–9 snapshots strengthen the test oracle; they are not required for the delta playback algorithm. Quiet clock transitions remain represented while unchanged Being/Object properties are not repeated. The bounded result does not establish sufficiency for omitted native field families, general receipt APIs, arbitrary Actions or long-running production histories.

## Focused verification

The exact focused commands, pass counts, syntax result, whitespace/publication audits and commit hashes are recorded in the archived [U-PER-SCALE-001 report](../reports/archive/U-PER-SCALE-001-report.md). No full repository test suite was run. The previously known adjacent transactional progression failures were not reassessed here and are not described as pre-existing or introduced by this bounded read-model work.
