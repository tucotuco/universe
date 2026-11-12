# Encounter snapshot and transaction dependency analysis

Date: October 27, 2026. Inspected HEAD: `8a00e884a62e37160a8eeb69f0e6e67e94ab16b4`, plus existing working-tree changes. This describes the working tree, not HEAD alone. Engine code was not modified; only this requested report was added.

## Conclusion

The intended invariant is not currently enforced: **all non-movement actions resolving in the same second must evaluate one common post-movement snapshot, with consequences committed together**.

The smallest safe architectural change is an Encounter-owned batch coordinator with immutable read views, explicit action proposals, batch validation, and a single publication boundary. Extend the existing `ActionResolution` acceptance path rather than build a second combat engine. Extract existing calculations without changing their formulas, gates, dice order, or success/practice rules. A queue-only change, deferred damage alone, or a larger fatigue snapshot would leave other state leaks intact.

Some simultaneous-effect rules remain undecided. In particular, “same second” is not currently an engine grouping rule, and fatal-hit merging cannot always preserve today's sequential result. These decisions must be explicit before implementation. They are listed below rather than silently resolved here.

## Scope and completeness

Inspected all production `Action` subclasses in `src`: base `Action`, `MeleeStrike`, `MeleeDefense`, `RunAction`, `SpotAction`, `ObserveGroupAction`, and `AskAboutPastAction`; their invoked mutators; Encounter scheduling/completion; fatigue bridge; relevant orchestration, realization, and evidence ledgers.

The inventory below covers the concrete built-in resolution paths. `schedule_action()` also accepts arbitrary resolvable `Event` implementations. Resolver overrides, completion hooks, injected history generators, and custom observation/interpreter objects can execute arbitrary Python and reach mutable objects. No static inventory can bound those extension writes under the current contract. A safe transaction API must constrain extensions; it cannot assume they are pure.

## Present execution boundary

[`Encounter.step()`](../../src/encounter.py#L611) validates movement, applies all destinations, captures a common Q/B frame, and calls `resolve_actions(as_of=end)`. Environment update and clock advancement follow successful action resolution. Movement is already committed if an action fails.

[`resolve_actions()`](../../src/encounter.py#L787) collects due events once and orders them by `(end_time, resolution_priority, pending-list index)`. It groups eligibility snapshots by exact `end_time` equality. Each group is captured after earlier timestamps have resolved. It then runs each action, accepts structured practice/observations, moves its ID from pending to finished, and invokes its completion hook before proceeding.

The Q/B frame spans the entire call, even when several timestamps are due. The melee snapshot freezes only readiness, held-weapon status, and reach/path status. Live HP, skills, strategies, legacy fatigue, equipment data, realization ledgers, and other state are not universally frozen. `resolve_actions()` does not advance time. During `step()`, callbacks see the step's starting `Encounter.time`.

`run()` calls the same dispatcher after its movement hooks, then chooses future combat actions and increments time. Legacy AI construction registers base `Action` events directly. Any new batch boundary must cover both `run()` and `step()`, not just the interactive duel.

## State-mutation inventory

### Being and ordinary Object state

| Resolution path | Actual writes | Important existing behavior |
|---|---|---|
| [`Action._resolve_damage_to_shield()`](../../src/action.py#L258), reached through target/actor shield helpers | Shield WeaponInstance `current.hit_points`, through inherited `ObjectInstance.damage()` | Shield selection and interception use random draws. On interception the shield receives the full incoming damage; size determines what passes onward. No new shield breakage rule should be inferred. |
| [`Action._resolve_damage_to_target_armor()`](../../src/action.py#L292) | Target ArmorInstance `current.hit_points` | Computes armor damage and damage through from penetration/defense data before applying armor HP damage. |
| [`Action._resolve_damage_to_actor_armor()`](../../src/action.py#L310) | Actor ArmorInstance `current.hit_points` | Same pipeline for self-injury. |
| [`Action.do_normal_hit()`](../../src/action.py#L400) | Target `current.hit_points`, after shield and armor writes | Uses weapon damage, action strategy extra damage, and the existing shield→armor→target chain. |
| [`Action.do_critical_hit()`](../../src/action.py#L417) | Target `current.hit_points`, plus shield/armor HP | The extra critical die bypasses shield and armor. Preserve that separation. |
| [`Action.do_critical_failure()`](../../src/action.py#L438) | Actor `current.hit_points`, plus actor shield/armor HP | Existing self-hit path, not damage to the intended target. |
| [`Action.do_fatal_hit()`](../../src/action.py#L474) | Target HP assigned to `-10` when currently greater than `-10` | Distinct from ordinary damage and its zero clamp. The confirming save belongs to the defender. |
| [`Encounter.resolve_actions()` practice acceptance](../../src/encounter.py#L846) → [`BeingInstance.record_skill_use()`](../../src/being.py#L422) | `current.skills.skills` or `current.skills.weapon_skills`; `_skill_practice_baselines`; `skill_experience`; `skill_use_history` | Progressive ranks can rise immediately. Zero-XP exercises still record history. Does not award general `current.experience`; does not invoke category propagation via `set_weapon_skill_level()`. |

All ordinary HP damage above reaches [`ObjectInstance.damage()`](../../src/object.py#L326), inherited by Beings, armor, and weapons. It clamps to zero if incoming damage exceeds current HP; otherwise it subtracts. Do not replace this with unrestricted subtraction. Its interaction with already-negative HP deserves characterization before choosing a reducer.

[`Action.do_drop_weapon()`](../../src/action.py#L463) calls [`BeingInstance.drop_weapon()`](../../src/being.py#L765), but that method is currently `pass`: **no possession, body-part, weapon-list, container, or position write occurs**. Miss and spectacular-miss handlers also make no Being/Object writes. Saving throws and attack checks consume randomness but do not themselves change Being state.

Current armor HP loss does **not** change `current.defenses`. [`ArmorInstance.damage_through()`](../../src/armor.py#L253) reads defense values independently of HP; the shield code likewise has no HP-based destruction gate. A snapshot refactor must not introduce degraded protection, broken-item removal, natural-weapon drop behavior, or destruction effects.

### Lazy objective state and observer evidence

| Resolution path | Actual writes | Why it belongs in the boundary |
|---|---|---|
| [`ObserveGroupAction.resolve()`](../../src/group_observation.py#L166) → `SampledGroupObservation.sample()` → [`StatisticalGroup.counts()`](../../src/statistical_group.py#L281) | `_composition_reality` fact records/revisions for household count and household compositions; `_counts` aggregate cache | A read-looking sampling path commits objective group composition. No individual Being is materialized. StatisticalGroup is additional encounter entity state, not merely ordinary Object HP. |
| [`AskAboutPastAction.resolve()`](../../src/history_conversation.py#L97) → [`PersonalHistory.realize_episode()`](../../src/personal_history.py#L65) → `RealityLedger.ask()/commit()` | The speaker's personal-history ledger `_records` and `_revision`, including proposed supporting facts such as historical skill ranks | This commits Being-associated objective history before Encounter accepts completion. It does not automatically change the speaker's current skill rank or create listener belief. |
| [`ObserveGroupAction.on_completed()`](../../src/group_observation.py#L199) → [`BeliefLedger.learn()`](../../src/field_observation.py#L230) | Supplied ledger `_evidence`, `_interpretations`, and `_belief_history` | Agent evidence is external to the observed entity and may be external to the Being object. Still a visible consequence of the action. This call supplies no `communicated_by`, so it does not append the communication log. |
| [`AskAboutPastAction.on_completed()`](../../src/history_conversation.py#L122) | Action `heard_account`; optional caller-owned `received_accounts` list | Testimony delivery is currently a completion consequence. The list is not necessarily a Being field; it must still be staged for complete action atomicity. |

Each `RealityLedger.commit()` is locally atomic, but there is no transaction spanning it, HP, practice, evidence, and Encounter queues. `counts()` can perform multiple ledger commits before completion. History validators also depend on current/prior skill-use records, making historical realization and practice a joint validation problem.

### Encounter and action state that controls later evaluation

- [`mark_aware()`](../../src/encounter.py#L393) updates Encounter `awareness`, not a Being field. Structured observations invoke it immediately; later actions can read it through `is_aware()`.
- [`MeleeDefense.resolve()`](../../src/melee_defense.py#L73) writes the designated strike's `defended_by`, its own `defended_action_ids`, `success`, and `result`. Strikes read the marker. This is an established equal-time defense dependency, despite not being a direct Being/Object mutation.
- [`MeleeStrike.resolve()`](../../src/melee_combat.py#L134) writes `hit_type` and `combat_result`; Encounter later writes `action.resolution`. Result HP-before/after and armor-damage values currently describe the sequential execution point, not the whole second.
- Run writes measured `displacement`; Spot writes `skill_level_used`, `path_status`, and `roll`; group observation writes check/evidence/interpretation fields; conversation writes pending account and realization metadata. These fields must not publish successful-looking results for an aborted batch.
- Encounter changes pending/finished lists, and captures/clears temporary eligibility and fatigue fields. `last_fatigue_frame` changes even on an otherwise empty resolution pass. Successful `step()` also appends fatigue frame history.
- Completion hooks are arbitrary executable callbacks. A hook can cancel a later event after the due list is frozen; the later resolver still runs and then fails pending removal. A hook exception occurs after its action is already finished. Snapshot capture for later candidates can survive an earlier failure.
- Global random state is advanced by combat, saves, and undeclared Spot rolls. Group observation uses keyed local RNGs. TacticalDuel scopes global RNG use to a saved encounter RNG state. Random consumption and replay are transaction dependencies even though RNG state is not a Being/Object property.

### Adjacent writes outside action resolution

These are relevant boundaries, not additional built-in `resolve()` writes:

- Movement uses `entity.set_position()` before the snapshot. RunAction measures displacement; it does not move the Being itself.
- TacticalDuel adds dodge displacement to movement on the designated impact step. Preserve that pre-snapshot placement; `MeleeDefense.resolve()` itself does not move the defender.
- [`TacticalDuel._fatigue_tick()`](../../src/tactical_duel.py#L175) runs after `Encounter.step()`: it may increment legacy `fatigue_level` and updates Being-associated Exertion tracker level/start/end times. It currently skips incapacitated/exhausted participants. Do not move this earlier or replace it with Q/B depletion incidentally.
- Scheduling hooks establish run start position, defense timing/threat metadata, and encounter bindings. Decision/stance setup and awareness refresh also occur outside the resolver. They are inputs to the snapshot, not new action consequences by default.
- `FrozenFatigueFrame.propose_work()` is write-free. Native Q/B depletion, physical-check replacement, and integrated workload settlement are not currently implemented in this dispatcher. Custom test resolvers can mutate Q/B; the frozen view protects only reads through `fatigue_view()`.

## Dependency analysis

| Evaluator | Required snapshot inputs | Proposed consequences / dependencies |
|---|---|---|
| Base Action | Actor weapon skill and strategy; target strategy; save inputs/general experience; instrument damage/penetration/size; shield holdings; armor defenses; HP | Ordered dice trace; shield/armor/body damage or fatal assignment. Base Action has fewer feasibility gates than MeleeStrike; do not add those gates implicitly. |
| MeleeStrike | Base inputs plus HP eligibility, held weapon, positions/geometry/path, legacy fatigue level and Exertion penalty data | Combat record, attempt outcome, weapon practice; consumes explicit designated-defense outcome. |
| MeleeDefense | Actor helplessness, held parry weapon, skills/strategies; designated pending strike identity/time/status; schedule-time threat metadata; post-movement geometry | Defense proposal and practice. Does not protect unrelated or replacement strikes. |
| RunAction | Schedule-time start position, post-movement current position, distance threshold | Displacement, success/partial/no-movement, configured run practice. |
| SpotAction | Spot rank, post-movement positions and optical geometry, distance, difficulty, declared/random roll | Check metadata, practice, directed awareness on success. Earlier same-batch XP must not raise the rank used. |
| ObserveGroupAction | Spot and interpreter skill ranks; group position/composition/configuration; seeded sampling policy | Objective composition realization, noisy evidence and interpretation, practice, awareness, belief-ledger acquisition. |
| AskAboutPastAction | Awareness/range, speaker history and constraints, injected generator | Objective historical facts/supporting ranks, perceived testimony, awareness, delivered account. Shared episode requests need coordinated realization. |

Snapshot reachability is broader than actors and targets: include equipped shields/armor/weapons, geometric blockers, nested strategies and skill maps, Exertion data, object registries/participation, pending designated strikes, history/composition ledgers, and relevant configuration. Copying only `Being.current` leaves aliases and live lookups through `action.universe` or `action.encounter`.

Defense→strike is the principal established same-batch dependency. Preserve it by evaluating defenses from the common snapshot, then supplying their proposals explicitly to strike evaluation. This is a derived batch input, not a live mutation. All competing defenses still read original snapshot skills and equipment. Keep current priority and queue order for calculation/dice assignment until a replacement policy is approved.

Practice/history and realization collisions require validation of the combined candidate state. Summing XP is not enough: record every original action's exercise and outcome, derive progression in deterministic history order, and validate historical constraints against that complete candidate. Skill gains become visible to evaluators in a later batch only.

## Smallest safe refactoring proposal

### 1. Characterize current behavior before extraction

Add tests for the missing cases below. Keep single-action outcomes, timing, random draw order, and save/replay format stable. Treat sequential same-time leakage as behavior intentionally changed by the new invariant, not something all old behavior can preserve simultaneously.

### 2. Introduce one explicit batch context

Add an immutable `ResolutionSnapshot` and a `ResolutionContext` holding batch identity/time, stable event order, and a staged RNG cursor. Reuse `FrozenFatigueFrame` for Q/B rather than duplicate its equations. Read views must contain detached immutable nested values and stable ID lookups. Include the complete reachable dependency set above; snapshot capture must not realize unresolved history/composition on live objects.

Do not silently round floating-point deadlines into integer buckets. Initially retain exact-time grouping as the existing supported behavior, while documenting that the broader same-second invariant requires the time policy decision below. This initial compatibility step alone must not be claimed as full invariant compliance.

### 3. Separate evaluation from effects in existing action classes

Extend `ActionResolution`, or pair it with an immutable proposal containing typed HP/equipment effects, practice, awareness, realization facts, evidence/accounts, and action-result metadata. Extract the current Action combat calculations into snapshot-based evaluation; preserve their formulas and random call sequence. Keep shield, armor, self-hit, critical bypass, and fatal effects distinct until validated reduction.

Adapt Run/Spot and group/history actions to the same protocol. Preserve direct `Action.resolve()` and damage-helper compatibility through a deliberately scoped single-action adapter if required by callers/tests; Encounter must never use an immediate-write fallback. Unsupported custom Events need an explicit migration error before evaluation, rather than a promise of atomicity they cannot satisfy.

### 4. Evaluate, reconcile, then validate the complete candidate

Evaluate defenses then dependent strikes with the same snapshot and explicit defense proposals. Evaluate other actions without seeing staged XP, awareness, injury, or evidence. Use batch-local lazy-realization stores for unresolved objective facts; validate combined supporting facts without committing live ledgers. Stage action records too.

Reduce compatible consequences into detached candidate Being/Object, ledger, and queue states. Preserve current ordinary damage clamping and progressive XP/history semantics. Conflicting noncommutative effects must be surfaced until their rule is agreed; do not invent a universal sum, last-writer-wins rule, reroll, or extra resource meter.

### 5. Publish once

Prevalidate every operation that can fail, including personal-history validation, evidence ID conflicts, and completion delivery. Publish the complete batch in a non-reentrant Encounter-owned critical section, with prepared rollback for unexpected publication errors. Preserve live Being/Object identity and caller-owned ledger/list identity where the existing API exposes them. Merely replacing the Universe with a deepcopy would strand references held by actions, callers, histories, and UI code.

Migrate built-in hooks into staged consequences. Arbitrary callbacks cannot execute inside an allegedly infallible commit. If post-commit notification hooks remain, define their failure and exactly-once/retry contract separately; notifications must not be necessary to complete authoritative state. Queue mutations during evaluation must be deferred or rejected before any publication, and recursion/concurrent stepping must be guarded.

On failure, discard proposals and the staged RNG cursor. No batch effects, completion records, partial snapshots, practice, realization facts, evidence, or accounts should escape. Whether already-completed movement and earlier batches also roll back is a separate decision below.

### Why smaller-looking alternatives are unsafe

- Deferring only HP leaves XP, awareness, defense, history, and composition leaks.
- Running legacy resolvers against one shared deepcopy prevents live writes but retains sequential evaluation leaks inside the copy.
- One independent clone per action cannot by itself reconcile shared defenses, objective facts, XP, external references, or fatal/ordinary damage conflicts.
- Executing live and restoring afterward exposes intermediate state to callbacks and can leave RNG/external-list/ledger writes behind.
- `RealityLedger` provides local fact transactions, not a native Being/Object transaction. The engineering plan's reference to an existing native transaction is not implemented by the inspected dispatcher.

## Ambiguities requiring explicit decisions

1. **Time buckets:** does “same second” mean identical deadlines, integer time intervals, or all actions processed by one `step()`? Times and durations may be fractional. Define boundary inclusion and events exactly at a boundary. Different timestamps currently see earlier effects; do not collapse them accidentally.
2. **Long steps:** current `step(duration>1)` moves to the final endpoint before all due actions. Must it be split at second/action boundaries, or is endpoint evaluation intentionally retained? Define treatment of overdue events and direct `resolve_actions(as_of=...)` calls too.
3. **Fatal and ordinary damage:** a fatal assignment to `-10` and ordinary clamped damage are noncommutative today. Define compatible simultaneous settlement; no reducer can preserve every queue-order result while making results order-independent.
4. **Shared defenses/equipment:** preserve designated defense precedence, but clarify multiple defenses for one strike, overlapping use of a weapon/shield, and any future actual drop/breakage. Existing code does not supply a general resource/conflict rule. The engineering plan mentions no-time conflict rerolls; the inspected native resolver does not implement a general reroll protocol.
5. **Lazy realization:** two simultaneous inquiries for the same unresolved episode currently let the first generator commit and the second reuse it. Decide whether a stable shared realization authority preserves that behavior or whether conflicting proposals must be rejected. Define `newly_realized` and ledger revision reporting. Group composition must remain shared and deterministic, without creating individuals.
6. **Failure scope:** atomic consequences for one second do not automatically imply rollback of movement or previous seconds. Current failures leave movement committed and time unadvanced. Specify clock/history behavior and retry inputs for an aborted batch.
7. **Result records:** should each strike's HP-after mean its isolated proposed damage, batch-final HP, or a deterministic settlement trace? Existing records are sequential and replay/UI code exposes them. Preserve schema until meaning is decided.
8. **Randomness:** preserve stable priority/queue allocation of existing draws or approve another documented mapping. Common snapshot evaluation does not itself imply queue-order-independent RNG outcomes. Define abort/retry RNG behavior and generator side-effect restrictions.
9. **Fatigue scope:** retain current legacy Exertion mechanics and post-combat checks unless separately authorized. Do not wire Q/B penalties, workload costs, or R4 settlement into this refactor merely because proposal APIs exist.
10. **Open extension contract:** arbitrary Events and injected callbacks cannot retain unrestricted live mutation and also satisfy the invariant. Specify supported adapters, purity requirements, and behavior for unsupported extensions.

## Existing behavioral protection

| Tests | Mechanics they protect |
|---|---|
| [`test_action.py`](../../tests/test_action.py), [`test_armor.py`](../../tests/test_armor.py), [`test_weapon.py`](../../tests/test_weapon.py) | Damage potential, shield/armor paths, normal/critical/self/fatal handlers, attack/save-related behavior, timing, penetration and defenses. Some legacy tests rely on randomness; add controlled characterization rather than treating all as exact equivalence proofs. |
| [`test_melee_combat.py`](../../tests/test_melee_combat.py) | Persistent results, armor damage, weapon-type skill, misses, range/path gates, weapon removal, fallen targets, awareness at scheduling, defender fatal save. |
| [`TestTacticalDuel`](../../tests/test_tactical_duel.py) | `test_simultaneous_strikes_still_attempt_after_earlier_impact`; timing, earned practice, guard/strategy and movement behavior. |
| [`test_combat_reactions.py`](../../tests/test_combat_reactions.py) and [`test_attack_specific_defense.py`](../../tests/test_attack_specific_defense.py) | Equal-time parry precedence, failed-defense practice, dodge movement, designated-strike binding, no retargeting, preparation deadlines, validation atomicity, save/resume randomness. |
| [`test_encounter_cycle.py`](../../tests/test_encounter_cycle.py) | Due-time/queue ordering, movement before actions/environment, movement validation, duplicate/foreign events, failed action not marked completed. Its failing resolver raises before effects; it does not prove rollback. |
| [`test_action_resolution_experience.py`](../../tests/test_action_resolution_experience.py) | Multi-skill awards, zero-XP history, legacy `None`, no duplicate exercise, ordinary preflight rejection and duplicate practice protection. Does not cover later personal-history validation failing after an earlier award. |
| [`test_spot_action.py`](../../tests/test_spot_action.py) | Progression affecting a later step, observation only at completion, optical gates, natural 1/20, invalid observation rejection before XP. Does not require XP leakage within a second. |
| [`test_running_action.py`](../../tests/test_running_action.py) | Measured displacement, partial/no-movement practice, scheduling origin, progression without changing definitions. |
| [`test_group_observation_action.py`](../../tests/test_group_observation_action.py), [`test_field_interpretation.py`](../../tests/test_field_interpretation.py), [`test_belief_revision.py`](../../tests/test_belief_revision.py) | No individual materialization, keyed reproducibility, feasible failure practice, out-of-range no realization, fallible skill-dependent interpretation, evidence provenance and belief history. |
| [`test_personal_history.py`](../../tests/test_personal_history.py), [`test_realization_contract.py`](../../tests/test_realization_contract.py) | Inquiry idempotence, objective-fact consistency, supporting training ranks, skill/history compatibility, local ledger atomicity, restore constraints. |
| [`test_native_physical_fatigue.py`](../../tests/test_native_physical_fatigue.py), [`test_native_physical_work.py`](../../tests/test_native_physical_work.py) | Common immutable Q/B view, no write-through, post-movement capture, profiles frozen by version, pure proposals, explicit interval/work coverage and no double charging. These do not prove general Being/Object atomicity. |

Current verification: **193 tests passed** across the 18 entries/modules/classes above, using `PYTHONDONTWRITEBYTECODE=1` and unittest from `src/`. `TestTacticalDuel` was selected without its HTTP server class. This was a targeted audit run, not the full repository suite. No tests were added or changed. Existing socket-binding restrictions from the earlier audit were not escalated.

The native-fatigue test `test_common_snapshot_even_after_earlier_actor_changes_fatigue_and_hp` deliberately monkeypatches mutating resolvers and checks only frozen Q/B reads. Retain its freeze-only characterization for the legacy API or adapt its fixture to proposals; do not mistake its intentional live test writes for required production batch behavior.

## Recommended new regression tests

### Required invariant and failure tests

1. **Full common snapshot:** two same-batch evaluators read identical HP, skills, strategies, legacy fatigue, Q/B, equipment/defenses, geometry, and awareness despite the first proposing changes. Assert live state stays unchanged until commit; mutate nested returned structures to verify immutability.
2. **Practice isolation:** first Spot action earns enough XP to rank up; a second same-batch action uses the original rank and original interpreter skill. A next-batch action sees the new rank. Both practice records and total XP are retained.
3. **Mutual and many-to-one impacts:** both viable simultaneous opponents attempt and earn practice even if either proposal incapacitates the other. Several attackers on one initially viable target all use snapshot eligibility. Repeat with earlier-timestamp incapacitation to protect the distinct-batch gate.
4. **Damage fidelity:** controlled rolls for normal, critical bypass, self-hit, shield interception, armor HP loss, ordinary zero clamping, and fatal defender saves. Check single-action equivalence and compatible multi-hit totals. Add mixed fatal/ordinary and already-negative HP expected results only after the settlement rule is approved.
5. **Defense dependency:** designated equal-time defense can deflect its strike even when scheduled after it; another strike remains unaffected. Defense and attack practice use snapshot ranks. Preserve failed-defense XP and dodge's pre-snapshot displacement. Multiple-defense expected outcomes require the explicit rule above.
6. **Whole-batch rejection:** inject failure in a later evaluator, award, history validator, evidence acceptance, and prepared completion delivery. Assert no batch HP, equipment HP, skills, ledgers, awareness, action fields, queue completion, external account list, or RNG cursor changes. Explicitly test an earlier valid skill award followed by a history-incompatible award.
7. **Lazy realization staging:** successful group observation stages composition and cache without individual materialization; later batch failure leaves neither committed. Two observations share identical underlying truth. For inquiries, test repeated/shared episode access, supporting facts, failed-batch rollback, and conflicts under the approved realization policy.
8. **Callback safety:** cancellation, scheduling, direct mutation, and recursive resolution during evaluation follow the declared contract. No canceled event is resolved from a stale due list; no hook delivers evidence twice; unsupported custom Events fail before writes or random consumption.
9. **Snapshot/result cleanup:** evaluation and snapshot-capture exceptions leave no `_simultaneous_eligibility` or temporary context attached, no resolved-marker preventing retry, and no partial successful result published.
10. **Replay and identity:** fixed seed produces the same supported single-action dice trace and replay fingerprint; abort/retry follows the approved cursor rule. Commit preserves references to existing Being/Object, history, ledger, and account-list objects. Definitions remain unchanged.

### Boundary and integration tests after decisions

11. Parameterize fractional and integer deadlines, exact boundary events, overdue events, multi-second steps, and direct dispatcher calls. Verify the approved bucket policy and movement snapshot for each batch. Compare one long step with smaller steps only if equivalence is an approved requirement.
12. Drive identical batches through `run()`, `step()`, and the duel facade. Assert current prepared-defense timing, movement concurrency, post-combat legacy fatigue checks, serialization, save/resume, and per-action result semantics are preserved.
13. Verify empty batches, missing event IDs, `end_time=None`, generic resolvable Events, legacy `None` results, and duplicate scheduling against the agreed compatibility contract. Include zero-duration actions newly scheduled at a batch boundary.
14. Add an order-permutation test with explicitly fixed per-action rolls for compatible effects. Assert snapshot-derived outcomes do not change with queue permutation; separately assert stable queue-based RNG allocation where that remains the chosen compatibility policy.

No new combat rules, item destruction behavior, fatigue costs, conflict rerolls, or time quantization are recommended without resolving the listed ambiguities.
