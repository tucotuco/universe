# Universe 4 assignment 03: timeline, choice, and damage characterization

Date: October 27, 2026. Status: characterization and implementation proposal only. **No production code changed.**

## Outcome and authority

The current native engine passes its existing full suite, but does not implement the adopted one-second transaction or exclusive-use choice lifecycle. Added 42 passing, explicitly labeled **legacy-current-behavior** tests. The full suite with those tests passes: **822 passed, 0 failed, 0 errors, 0 skipped**. No alternative combat simulator, production refactor, target-behavior implementation, or failing future test was introduced.

Authority, in order: [revised assignment](universe4-codex-task-03-updated-2026-10-27.md), [Class A addendum v2](universe4-class-a-addendum-t5-f2-h2-v2-2026-10-27.md), then the nonconflicting parts of the [decision record](universe4-class-a-decisions-2026-10-27.md). All three are present. The earlier architectural reports were used as leads and checked against current source, not assumed accurate.

The decision record's deferred T5 language, initial-time questions, unspecified F2 refusal timing/passive protection, and pending low-HP H2 reducer are **superseded**. They are not remaining approval questions. Adopted rules now include start at zero, duration ≥1, completion bucket `ceil(nominal_end)`, exactly-once chronological integer boundaries, scheduling-time active-use refusal, positive whole-choice acceptance/editing/undo, and the exact no-healing fatal reducer.

## 1. Verified baseline and preservation

Repository: repository root. Branch: `main`. HEAD: `8a00e884a62e37160a8eeb69f0e6e67e94ab16b4`. Python: 3.14.3.

The inspected revision is **HEAD plus the existing dirty/untracked working tree**, not HEAD alone. Existing tracked modifications: `examples/live_combat.py`, `src/being.py`, `src/encounter.py`, `src/library.py`, `src/universe.py`. There were also untracked native fatigue/work/profile modules and tests, planetary work, examples, saved workspaces, fatigue workbench, patch deliveries, and documents. The complete initial list is retained in [initial-status.txt](historical-evidence-archive-index.md#universe-4-assignment-03-evidence); none was removed, reset, committed, or overwritten.

Preservation verification hashes 128 existing files under `src/` and `examples/`, excluding bytecode, before additions and after verification. **All remained byte-identical**. The [preservation manifest](historical-evidence-archive-index.md#universe-4-assignment-03-evidence) also records delivery-time test hashes and confirms no tracked test changes; no pre-existing test file was edited. Only the new characterization test, this report, and its evidence were intentionally added.

### Native fatigue patch state

- Patch 1 behavior is present: immutable persistent Q/B plus physiology reference/migration, Being initialization/reset/serialization, common fatigue views/history, and existing tests. Patch 1's added `physical_fatigue.py`, `standard_fatigue_check.py`, `universe_physical_fatigue_r4.py`, and `test_native_physical_fatigue.py` match its delivered full-file additions exactly.
- `git apply --reverse --check universe4-native-fatigue-patch2.patch` exits **0**: Patch 2's delivered hunks are present in this tree. This was a read-only applicability check, not an application or reversal.
- Patch 1 reverse-check exits **1** on bridge/Universe/Encounter hunks extended by later work; that is not evidence Patch 1 is absent. Its bridge file is superseded by Patch 2's profile/work proposal extension. See [patch-state.txt](historical-evidence-archive-index.md#universe-4-assignment-03-evidence).
- Verified native `PhysicalFatigueState`, `FrozenFatigueFrame`, `WorkTimeline`, versioned `PhysiologyRegistry`, and pure `propose_work()`/`propose_physical_fatigue()` exist. There is **no general native Being/Object transaction**, no automatic work provider, and no native Q/B settlement in the dispatcher. Melee accuracy still uses legacy fatigue; TacticalDuel still applies legacy Exertion checks after combat. Nothing here activates new fatigue penalties or costs.

### Exact verification commands and results

Run from `src/` or adjust relative test paths from repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s ../tests -p 'test_*.py' > $TMPDIR/universe4-assignment03-baseline.log 2>&1
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s ../tests -p 'test_*.py' > $TMPDIR/universe4-assignment03-baseline-unrestricted.log 2>&1
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s ../tests -p 'test_encounter_legacy_characterization.py' -v > $TMPDIR/universe4-assignment03-characterization.log 2>&1
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s ../tests -p 'test_*.py' > $TMPDIR/universe4-assignment03-final-suite.log 2>&1
```

| Run | Result | Meaning |
|---|---|---|
| Initial sandboxed full discovery | 749 test executions; 12 reported errors; 0 assertion failures; no skips reported | Socket binds were prohibited. Some errors are class setup errors and suppress entire HTTP classes, so subtracting 12 from 749 is not a valid passing-test count. This was not accepted as the complete baseline. |
| Existing suite with local socket access | **780 passed; 0 failures/errors/skips**, 16.945 s | Complete baseline before new tests. |
| Final focused characterization run | **42 passed; 0 failures/errors/skips** | Controlled native probes and damage handlers; no network required. |
| Final full discovery with local socket access | **822 passed; 0 failures/errors/skips**, 17.282 s | Includes existing HTTP tests and all new characterization tests. |

The second and fourth commands used the tool's approved execution outside the restrictive socket sandbox. No tests were disabled or skipped to obtain the full result. Existing tests print several diagnostic messages and a temporary replay path; these are not test failures. Raw output is retained in the [evidence directory](historical-evidence-archive-index.md#universe-4-assignment-03-evidence).

## 2. Native interfaces and hooks inspected

| Built-in | Deadline construction and scheduling effects | Evaluation / consequences |
|---|---|---|
| [`Action`](../src/action.py) | Constructor overwrites supplied `end_time` with calculated weapon timing or fallback `start+1`; no hook | Rolls hit/save, then directly mutates shield/armor/body HP or invokes the current no-op drop handler. |
| [`MeleeStrike`](../src/melee_combat.py) | Weapon timing; hook checks actor/target viability, awareness, held weapon, motion and damage support | Eligibility snapshot is limited to HP readiness, possession, reach/path; live legacy fatigue and skills remain inputs. Produces mutable combat result and practice proposal. |
| [`MeleeDefense`](../src/melee_defense.py) | Constructor sets `end_time=encounter.time` as a placeholder. Hook sets readiness and **final end to the designated strike's end**, and records schedule-time threat | Priority `-1`; contests live skills/strategies, writes strike `defended_by` and its own result, returns practice. |
| [`RunAction`](../src/activities.py) | Positive duration, not minimum one second; hook stores start position and binds start to scheduling time | Measures displacement; no movement mutation inside resolver. Returns configured practice. |
| [`SpotAction`](../src/activities.py) | Positive duration; hook binds Encounter, checks start and skill definition | Reads live rank/positions/optics; stores check metadata, returns practice and directed awareness. |
| [`ObserveGroupAction`](../src/group_observation.py) | Positive duration; hook binds actor/group/skill context | Sampling can realize group aggregate composition/cache; interpretation reads live observer rank. Completion hook learns evidence into a supplied BeliefLedger. |
| [`AskAboutPastAction`](../src/history_conversation.py) | Positive duration; hook checks personal history/range-independent eligibility/awareness/start | Resolves speaker history and supporting facts immediately; completion delivers account and optionally appends a caller-owned list. |

[`Encounter.schedule_action()`](../src/encounter.py) accepts any `Event` with callable `resolve`, participating actor, and optional participating target. Non-Action Events can be scheduled and resolved but `cancel_action()` refuses them; non-Action structured results cannot award practice or observations. General instrument existence, resource declarations, hook purity, or final post-hook deadlines are not validated. It retains the same Event/Action object in Universe history.

`on_schedule()` runs **after initial checks but before parent assignment/event registration/pending append**. There is no staged preparation protocol. A failing hook can mutate Beings and register nested events; those effects survive. TacticalDuel directly calls strike/defense `on_schedule()` before interrupting an existing action and then calls `schedule_action()`, which invokes the hook again. Migrating hooks must eliminate double preparation without weakening validation-before-interruption.

Legacy combat AI in `choose_fight_actions()` directly appends/registers base Actions, bypassing `schedule_action()`. Any future scheduler invariant must close that path. `resolve_actions()` is callable directly and has no initiated, boundary, reentrancy, or finite-cutoff guard.

## 3. Time and scheduling: current versus adopted

Evidence is the current [`Encounter`](../src/encounter.py), constructors above, the new `TestLegacyTimeline` and `TestLegacyChoiceAndHooks`, and existing `test_encounter_cycle.py`, `test_attack_specific_defense.py`, and replay tests.

| Case | Current behavior | Adopted status and narrow candidate check |
|---|---|---|
| Start at `t=0`, duration exactly 1 | Scheduling valid; ordinary fallback Action finishes at 1 | Compatible. Never reject start zero as an attempted repair. |
| Supplied zero end to base constructor | Ignored/recalculated; fallback end is 1 | Not proof of zero-duration execution. Validate finalized schedule, not the argument alone. |
| Registered generic Action with `start=end=0` | Accepted if its deadline is explicitly set; direct dispatcher can execute at zero | T5 violation. Finalized duration ≥1 and resolution boundary ≥1. No unmodified duration-based constructor among Run/Spot/group/inquiry accepts duration zero. |
| Defense placeholder start=end | Initial check permits equality, then hook usually finalizes to a later designated impact | Do not reject the placeholder before preparing final timing. A real t=0 defense in the test finalizes readiness 2 and impact 4. |
| Durations `<0`, `0`, positive `<1`, `1`, `>1` | Scheduler rejects negative duration but accepts zero and positive subsecond values. Run/Spot/group/inquiry constructors reject ≤0 but accept positive subsecond duration | Enforce finite finalized `end-start >=1` for Actions. Preserve fractional durations ≥1. |
| Nonfinite times | Initial scheduler checks reject NaN/±infinity. Most duration constructors reject them too; scheduler numeric test also accepts booleans because bool subclasses int | Validate final typed numeric fields, with explicit boolean policy recommended as input hygiene. |
| Hook changes final end | Hook can change valid initial end to `0`, negative, `None`, NaN, infinity, or beyond Encounter end and still register | Pure preparation plus complete final validation before any authoritative effects/registration. |
| End inside `(n−1,n]` | Due when `end_time <= as_of`; direct/fractional progression may resolve before `n` | Use exact `ceil(nominal_end)` boundary, no epsilon rounding invented. |
| End exactly `n` / just above `n` | Exact is due at n; just-above is due on next cutoff, even n+0.5 | Exact belongs to n; just-above belongs to n+1, with physical fractions retained. Test uses `math.nextafter(1, inf)`. |
| Different fractional ends in one second | Separate exact-time eligibility groups; earlier effects visible to later group | One common integer-boundary snapshot for the entire bucket. Nominal end retained separately for provenance. |
| Long `step(2)` | Single movement to final endpoint; both end-1/end-2 evaluators see x=2 under unit velocity | T2/T3 violation. Segment existing constant-velocity movement chronologically to x=1 then x=2, with separate boundary settlements. No acceleration interpolation invented. |
| Two `step(1)` calls | Evaluators see x=1 then x=2 | Existing supported kinematic trajectory to preserve for equivalent inputs. Long and short steps currently differ in observations/effects. |
| Fractional stepping | Any finite positive duration accepted; every call dispatches due nominal deadlines, captures history and calls environment hook | Physical fragments may progress without resolution until an integer boundary. Review environment/history cadence; do not accidentally lose substep kinematics. |
| `run()` | Resolve at current time (including 0), then choose AI actions, increment by 1. Can return after increment without processing newly reached boundary | Refactor to the same boundary walker as `step()`, with AI choice explicitly placed. Existing movement hooks are placeholders. |
| Direct future dispatch | Can execute end-1 action with `as_of=20` while Encounter time stays 0 | No late/future shortcut. Internal boundary token must attest matching post-movement state; public compatibility call validates or errors. |
| Repeated dispatch | Usually empty because pending IDs were removed; no record of committed boundaries | Exactly-once ledger/cursor check; empty repeated boundary is still an invariant violation, not evidence it is safe. |
| Overdue/restored stale end | Resolves late at current cutoff; missing event ID skipped forever; null end ignored | Detect corruption/overdue before effects; report invariant error. No automatic catch-up or reconstruction policy. |
| NaN/infinite `as_of` | NaN dispatches nothing; infinity dispatches all finite deadlines | Validate cutoff/context before snapshot/evaluation. |
| Hooks schedule active/past boundary | During step the clock is still the starting time; nested zero-time declarations may register, and declarations during resolve/completed wait for another due-list collection | Validate prepared completion bucket against active and committed boundaries before **all** hooks/publication, including nested paths. |
| Recursion | Nested resolve can execute current pending Action twice; outer pending removal then fails | Guard progression/resolution reentrancy before snapshot or draws. |
| Target/instrument disappearance | Missing target causes AttributeError in melee capture; removed instrument filters out of `armed_with()` and yields completed `weapon_unavailable`, no practice | Preserve declared gameplay outcomes where modeled; distinguish absent/corrupt registry references from ordinary unavailable weapons. Do not invent replacement targets. |
| Interrupted step and retry | Movement and resolver effects/RNG draws survive, time stays at old value; retry moves again. Earlier completed actions stay finished | Stage batch state and review movement/clock/RNG rollback contract below. Do not silently re-execute stale actions. |

An Action can therefore actually complete at zero through the accepted generic Action extension path or mutable final deadlines; **a defense constructor placeholder alone does not demonstrate that defect**. Universe's origin Event at zero is not an Action and is not inherently a violation of the adopted minimum Action duration.

### Serialization and facades

`Encounter.to_json()` stores nominal start/end, current time, pending/finished/cancelled IDs, awareness, and fatigue history; no committed-boundary cursor, in-progress transaction, resource reservations, or accepted-choice state exists. Universe serialization omits active fatigue/runtime registry state. The legacy `Universe.load_from_file()` only recognizes Event/Encounter types, passes incompatible serialized fields to constructors, and loads registry entries as dictionaries. The new save/load probe fails on an unexpected serialized keyword before it can restore a functional pending ProbeAction. It is **not** a working stale-event recovery path.

`TacticalDuel.choose()` steps one second, applies legacy Exertion checks, refreshes observations, and records GUI/log state. `to_session()/from_session()` reconstruct from seed+commands and validate fingerprints/foe journals, rather than deserialize arbitrary Encounter state. Current replay tests pass. New boundary/resource/HP semantics can change old journal fingerprints; version/migration compatibility must be explicit. `examples/live_combat.py` and AI HTTP facades delegate to those interfaces; they must not gain a separate scheduler.

## 4. Group choice and active Object dependencies

There is no complete-set proposal/validation/acceptance API, no accepted-choice reservation table, and no group-level undo. Repeated `schedule_action()` calls register incrementally: if the second fails, the first remains. Same held weapon can schedule two real strikes or an attack and parry. Current tests pass because exclusivity is not enforced.

### Resource inventory

“Explicit IDs” are current fields, not a claim that every referenced Object is actively used. No built-in presently declares enforceable usage windows.

| Action | Explicit IDs / transitive state | Active-use candidate and interval evidence | Passive / target references |
|---|---|---|---|
| Base Action | `actor_id`, optional `target_id`, `instrument_id`; actor/target strategies; held shields and equipped armor via Being | Instrument actively attacks for swing/thrust. Nominal activity start→end known; exact active subwindows not represented | Target receives hit; shields intercept; armor protects. Those are not extra Actions/reservations. |
| MeleeStrike | Same plus owning Encounter and geometry blockers | Held `instrument_id` is active. Preparation starts at `start_time`; resolves at nominal impact. Full windup versus smaller use windows needs declared policy | Target, all blockers, passive actor/target armor/shields are dependencies, not active-use conflicts just for being referenced. |
| MeleeDefense: parry | Actor, attacking Being as target, parry weapon; designated strike ID (Event), that strike's weapon and timing | Parry weapon is active. Preparation starts at declaration, `ready_at` is computed, `end_time` remains designated impact. Whether reservation includes full readiness/holding interval must be approved | Incoming weapon/attacker are references, not active resources of the defense. Own passive protection is separate. |
| MeleeDefense: dodge | Actor, attacker, designated strike, schedule-time threat | No instrument Object. Movement occurs via facade velocities at designated impact, before snapshot | No invented body-part Object IDs or implicit weapon reservation. |
| RunAction | Actor and stored start/current positions | No explicit instrument; continuous measured activity over start→end | No target. Whether the actor Being itself is an exclusive resource requires the scope decision below. |
| SpotAction | Actor, target, line-of-sight geometry/blockers, spot rank | No explicit instrument; actor senses/attention modeled only as a check, not separate Object IDs | Observed target and blockers are not actively used by observation. |
| ObserveGroupAction | Actor, target StatisticalGroup, composition/position, interpreter and supplied ledger | No explicit instrument; observation duration known | Group truth, perceived candidates, and passive holdings are not active tools. Does not instantiate group members. |
| AskAboutPastAction | Listener actor, speaker target, speaker PersonalHistory, generator and optional account list | No explicit instrument. Whether speaking/being asked requires a second active participant reservation is not specified by current code | Speaker history is objective dependency; listener account/evidence destination is not a tool. |
| Custom resolvable Event | At minimum actor/optional target plus arbitrary extension fields/hooks | Cannot infer complete multi-Object usage; extension must declare active IDs and prepared intervals | A generic `instrument_id` alone cannot prove completeness or active use. |

Actor Beings are Objects in the type model, but treating every actor as an exclusive whole-body Object would prohibit established movement+strike and movement+parry concurrency. Do not make that inference automatically. The exact resource scope (whole Being, equipment, body part, multi-actor participation) needs approval. Passive shield interception can coexist with active use only insofar as the adopted passive/active distinction allows; two distinct active Actions using that shield still conflict.

### Window versus bucket cases

| Declarations using one active weapon | Window reading | Bucket reading / review |
|---|---|---|
| Both `[0,2]`, boundary 2 | Overlap | Same bucket: refuse as adopted. |
| `[0,2]` and `[1,3]`, boundaries 2 and 3 | Overlap despite different impact buckets | End-bucket-only checking misses a real active overlap. |
| `[0,1.1]` and `[1.1,2.1]`, boundaries 2 and 3 | Endpoint handoff depends on endpoint convention | Decide whether handoff at exact nominal end is allowed and whether use persists to settlement. |
| Distinct active subwindows of long Actions, both nominally ending in `(1,2]` | Could be disjoint if subwindows are permitted | Same-bucket exclusivity may still forbid reuse; do not infer a narrower subwindow rule. |
| Legacy `[0,1.1]` and `[1.2,1.9]` probe windows | Disjoint nominal windows, same bucket | Current scheduler accepts; **second duration .7 is invalid under T5**, so this probe is not a legal target-semantics counterexample. |
| Several impacts on one passive shield/armor | No second active use | Allowed H4; aggregate damage from common protection snapshot. |

With durations ≥1 and full start→end reservations, two legal Actions ending within the same unit interval necessarily overlap; the apparent bucket/window difference arises from different buckets with overlap, endpoints, narrower active subwindows, or extension to settlement. The exact rule must be recorded once and used by all schedulers. Do not create winners, silently drop a subset, or decide at impact.

### Proposed native choice API (design only)

```python
draft = encounter.propose_choice(owner_id, action_specs)  # immutable descriptions
draft = encounter.edit_choice(draft.id, complete_replacement_specs)
validation = encounter.validate_choice(draft.id, expected_revision)
# invalid: diagnostics -> edit/replace complete set -> validate again
choice = encounter.accept_valid_choice(validation.token)
encounter.undo_choice(choice.id)                         # whole, pre-execution only
replacement = encounter.replace_choice(choice.id, validated_replacement_token)
publication = encounter.publish_choice(choice.id, expected_revision)
```

Suggested phases: `DRAFT → VALIDATED → ACCEPTED → REGISTERED → EXECUTING → FINISHED/CANCELLED`. An invalid proposal remains DRAFT with diagnostics. VALIDATED is a versioned result, not authorization to mutate. Acceptance rechecks the complete set and all conflicting commitments/reservations; a stale token cannot bypass competition. Every edit invalidates the token. No action subset is accepted.

Diagnostics should include code, proposed action index/key, Object ID/role, conflicting existing/choice action, both active intervals/buckets, and a concrete edit reason. Examples: minimum duration violation, stale boundary, missing held weapon, designated-strike mismatch, or exclusive use conflict. Recommendations may suggest editing; they must not silently perform the edit.

**Recommended publication boundary for review:** accepted choices live in a reversible selection/reservation store, not Universe event history. Atomically publish the complete group immediately before its first execution/start fence, then begin execution. Preserve an explicit REGISTERED phase even if publication and start occur in one controlled operation. Undo/replacement is allowed until any group member starts; validation of a replacement occurs against the old group's released resources only inside the atomic swap. If future registrations must be visible before that fence, they remain wholly withdrawable and side-effect-free; specify that alternative explicitly. Acceptance at simulation time zero does not itself run `on_schedule()`.

Preparation must replace mutating `on_schedule()` with pure `prepare_schedule(read_context, complete_candidate_set)` producing final timing, binding intents, resource-use declarations, and staged initialization. A parry can designate a proposed strike in the **same set**, so draft-local keys must resolve before publishing Universe IDs. Current defense hook requires an already registered pending strike and cannot validate that case unchanged.

After all preparation succeeds: validate finalized durations, target/instrument ownership, active and committed buckets, ID collisions, Encounter end, resources, parents, full references, and schedule revision; then atomically publish all parents, event IDs, pending IDs, resource reservations, and staged start metadata. Preserve object identity. Nested hooks cannot authoritatively register during preparation. Unknown hooks/extensions must have a safe protocol or fail prepublication, not run in a pretend sandbox.

`schedule_action(action)` can become a backward-compatible **single-item prepare/validate/publish adapter** for approved built-ins; its old mutating hooks cannot remain an unrestricted escape hatch. Return type can remain action ID. Adapt callers that preinvoke hooks, and route legacy AI through the same scheduler. A user-facing accepted group API must not merely loop over that adapter.

Undoing an accepted selection releases its whole reservations and tentative references without adding cancellation evidence. `cancel_action()` remains an interruption of an authoritative started activity: retain intent/event/cancellation provenance and no earned completion practice. It is not selection undo or rollback of elapsed simulation time. Non-Action Event cancellation remains an explicit extension-contract issue.

GUI/replay/save/load must distinguish draft, accepted, published, and executed state, and replay atomic choice edits/publications where they matter. Either persist accepted reservations/versioned plans with validation on load or explicitly exclude unexecuted UI drafts from authoritative saves; this is an engineering contract to approve.

### Choice lifecycle pending tests

`CHOICE_VALID_COMPLETE_SET`, `CHOICE_CONFLICT_EDIT_REVALIDATE`, `CHOICE_NO_SUBSET_ACCEPTANCE`, `CHOICE_UNDO_WHOLE_ACCEPTED_SET`, `CHOICE_REPLACE_ATOMIC_SWAP`, `CHOICE_NESTED_PREPARATION_FAILURE_NO_LEAK`, `CHOICE_COMPETING_RESERVATIONS_STALE_TOKEN`, `CHOICE_SAME_SET_DEFENSE_REFERENCE`, `CHOICE_UNKNOWN_EXTENSION_REJECTS_BEFORE_EFFECTS`, and `CHOICE_PUBLICATION_FAILURE_PRESERVES_IDS_PARENTS_REFERENCES` are named pending specification tests, not active failing tests. Assert byte-equivalent authoritative state/queues/ledgers/RNG after rejected preparation; accepted selection state may change only through the approved reversible choice store.

## 5. Damage and result characterization

### Current calculation chain

[`ObjectInstance.damage()`](../src/object.py) is inherited by Being, ArmorInstance, and WeaponInstance. If `damage > current.hit_points`, it assigns zero; otherwise it subtracts. Thus `12−8−7` currently becomes 0, armor `6−4−4` becomes 0, and damage 6 applied at HP −12 **raises HP to 0**. These are legacy defects relative to H1/H3/H4, not normative expectations.

[`Action`](../src/action.py) dispatches exactly one hit handler:

- Normal: weapon damage die + action extra damage → shield interception → armor → target HP.
- Shield: choose a held shield, roll interception, apply **full incoming damage to shield HP**, and pass `max(0, incoming−shield_size)` onward. No new broken-shield rule.
- Armor: calculate armor damage `max(0, incoming−hardness)` and body damage through the weakest applicable protection, then apply armor HP damage. Protection uses `current.defenses` and does not degrade with HP.
- Critical: normal die + extra damage passes through protection; **extra critical die bypasses shield/armor** and adds to body damage.
- Critical failure/self-hit: ordinary chain against actor shield/armor/body, not the target.
- Fatal: after natural 20 and confirming natural 20, defender makes the existing CON save. Failed save selects `do_fatal_hit()`; **no ordinary damage die, shield/armor damage, or critical die is computed on that fatal path**. The handler conditionally assigns −10 only when starting HP >−10. A successful save falls back to critical and does roll ordinary/critical damage. Other confirmation outcomes retain current hit rules.
- Drop handler calls a stub `Being.drop_weapon()` and presently changes no holdings. Miss/spectacular miss change no HP.

The new controlled fatal tests verify save ownership, two attack rolls/no damage calculation on failed-save fatal, and four Action rolls when the fatal save succeeds and falls back to critical. They do not change saving throw rules or damage dice.

Current `MeleeResult` stores actor/target HP before and after its sequential resolver and per-action armor HP differences. Two controlled attacks on the same leather-armored target currently record `(10,7)` and `(7,4)`, each with 4 armor damage. Snapshot HP-before and shared batch-final HP-after under H5 require intentional changes. There is no explicit per-action body-damage field in this record.

**Consumer dependency:** TacticalDuel currently infers per-action `damage` as `max(0, hp_before−hp_after)` and includes it in UI/log/replay signatures. Under H5 that difference is the whole batch loss for each attack, so leaving the consumer unchanged would double-attribute damage. Add explicit own-action post-protection body/self/shield/armor contributions (and fatal provenance) before migrating result semantics. Do not use HP-before/after difference as an individual damage amount after H5.

### Adopted settlement specification (not implemented)

For each target, evaluate all attacks against one snapshot. Accumulate each uniquely identified, actual post-protection damage contribution exactly once as `D`; separately OR successful fatal flags. Then:

```text
without fatal: HP_final = H - D
with any fatal: HP_final = min(H, -10) - D
```

Apply additive actual damage to shield/armor HP without zero floor. Multiple fatal flags do not add extra −10 terms; fatal effects do not fabricate ordinary damage. If an extension explicitly produces both a fatal flag and a distinct actual-damage component, include the real component once. The existing fatal handler itself produces no such component. All qualifying individual results use snapshot HP-before and batch-final HP-after, with their own contribution/protection fields.

### Named pending target tests

These are **specification cases only**, deliberately not runnable failing tests or tests of a separate reducer implementation:

| Pending test | Required assertion |
|---|---|
| `H1_BEING_ADDITIVE_NEGATIVE` | H=12, real damage 8 and 7 → −3; own contributions remain 8/7. |
| `H4_ARMOR_ADDITIVE_NEGATIVE` | Armor H=6, damage 4 and 4 → −2; both impacts use original protection. |
| `H4_SHIELD_SHARED_SNAPSHOT` | Multiple intercepted impacts each calculate against original passive shield; shield damage adds below zero without active-use conflict. |
| `H3_DAMAGE_BELOW_ZERO` | H=−10, damage 6 → −16; H=−12, damage 6 → −18. Unit/settlement fixture must not require MeleeStrike to bypass its existing target-down gate. |
| `H2_MULTIPLE_FATAL_ONLY` | H=20, two fatal flags/no D → −10. |
| `H2_FATAL_PLUS_REAL_DAMAGE` | H=20, fatal + D=6 → −16; two fatal flags + D=6 also −16. |
| `H2_NO_HEALING_LOW_HP` | H=−10/−12, fatal alone → unchanged; fatal +6 at −12 → −18. |
| `H2_FATAL_WITH_OWN_DISTINCT_DAMAGE` | Approved proposal carrying fatal plus a separately calculated real component subtracts that component once, plus other actual damage once. No ordinary component is invented for the existing fatal path. |
| `H2_FATAL_SAVE_AND_CRITICAL_BYPASS` | Existing defender confirmation/save and successful-save critical fallthrough retain exact dice and protection behavior. |
| `H5_SHARED_FINAL_RECORDS` | All involved records show same snapshot starting HP and final HP; own armor/body/shield/self effects retain individual provenance. |
| `H5_FACADE_NO_DOUBLE_ATTRIBUTION` | Duel UI/log/fingerprints consume own-action contribution, never infer it from shared final HP. |
| `BATCH_NO_PARTIAL_DAMAGE_OR_RESULTS` | Any later evaluation/validation failure publishes no HP, item damage, action result, XP, evidence, objective fact, or completion for that second. |

## 6. Shared-snapshot and transaction dependencies

This work reconfirms the earlier mutation inventory, with adopted ambiguities now resolved where v2 governs. Snapshot closure includes HP, nested skill/strategy data, legacy fatigue and Exertion penalty inputs, Q/B/profile versions, positions/geometry/optics/blockers, holdings/instrument/armor/shield data, awareness, designated strike metadata, configuration, and objective history/group ledgers.

Keep defenses as an explicit proposal dependency: evaluate all valid designated defenses from the same snapshot, then supply a **set/list of successes and full provenance** to strike evaluation. One success suffices; benefits do not stack. The current single `defended_by` gets overwritten by later success and cannot fully represent F1. Keep qualifying practice for successes/failures and attack-specific binding, subject to F2 scheduling refusal.

Run/Spot return largely declarative practice/awareness today, but action-local metadata is still mutated. Group observation invokes read-looking `counts()` that commits household facts and aggregate cache. Conversation commits PersonalHistory through `RealityLedger.ask()`. Completion hooks write evidence, belief revisions, and caller-owned accounts. Stage **all** these, not just damage and XP.

R1–R5 require one shared candidate Reality for the batch: one group composition and one episode/supporting fact set, observer-specific sampling/interpretation from original ranks, and atomic contradiction refusal. Differences in evidence/belief are not objective contradictions. Existing `RealityLedger.commit()` is locally atomic; it is not a transaction spanning native world state. History validators inspect skill history, and `record_skill_use()` performs extra history checks not included in the earlier `validate_skill_use()` pass. Validate the complete combined candidate before any publication.

Arbitrary hooks/generators retain access to live state through Universe/Encounter references and closures. Running them live then restoring, or sequentially against one cloned world, does not establish the invariant. Introduce explicit immutable evaluation/read contexts and typed staged effects in the native classes; constrain extensions. Preserve existing Object/Being, ledger, and exposed list identities at commit. No Q/B depletion or new fatigue penalties join this increment automatically.

## 7. Candidate errors, rollback, and recovery boundaries

Proposed names below are engineering contracts for review, not implemented exception classes or late-execution rules:

| Category | Detect before | Diagnostic / action |
|---|---|---|
| `InvalidActionTiming` | Authoritative registration, after pure finalization | Bad final duration, nonfinite start/end, disallowed final Encounter range. Return to edit. |
| `ChoiceConflict` / `StaleChoiceValidation` | Acceptance and publication | Active Object/window conflict or changed commitments. Whole set stays/reverts to editable proposal; no partial registrations. |
| `BoundaryInvariantError` with reason codes | Any effects or draws | Zero/duplicate/skipped/overdue boundary, wrong cutoff/post-movement token, declaration into active/committed bucket. Stop, retain diagnostics; no late execution. |
| `CorruptScheduleReference` | Boundary preparation/load acceptance | Missing event, invalid final deadline/parent/ID, inconsistent restore cursor. No silent skipping or target replacement. |
| `ResolutionReentrancyError` | Nested scheduling/progression entry when forbidden | Reject recursive dispatch before the current event is re-executed. |
| `UnsupportedResolutionExtension` | Choice preparation / batch evaluation | Cannot declare resources or stage effects safely. Do not invoke opaque mutating fallback. |
| `BatchValidationError` / objective contradiction subtype | Publication | Proposed effects or Reality incompatible; discard entire second's candidates. |
| `PostCommitDeliveryError` | After authoritative commit only if notifications retained | Durable, separately retryable notification; must not imply authoritative batch rollback or rerun combat. |

Recommended interfaces: shared `advance_to(target_time, motion_inputs)` boundary walker; internal `resolve_boundary(boundary_context)` requiring a post-movement token; explicit `last_committed_boundary` and active phase/cursor; pure `prepare_schedule()` and `evaluate(snapshot, batch_context)`; typed effect proposals and prepared publication. These must replace bypass paths, not merely wrap them.

**Recommended failure contract for review:** each successfully committed earlier second remains committed. Stage current-boundary movement/clock and all non-movement effects together so an unsuccessful boundary can return to its immediately preceding accepted checkpoint, with its RNG cursor restored and no leaked proposal fields. Fractional movement fragments already published before reaching a boundary complicate that checkpoint; specify whether the retry checkpoint is the previous boundary or latest fragment, and journal inputs needed for replay. This report does not implement either answer. An alternative retaining post-movement state on failure requires an explicit prepared-frame retry token to prevent moving twice; it must still reject stale late execution.

Use a batch-local RNG cursor preserving established stable action/priority draw order where possible; publish its advanced state only on success. Abort should discard draws, not regenerate objective truth to conceal contradictions. Arbitrary injected generators must follow the staged/pure protocol; external irreversible side effects cannot be rolled back by restoring a Python RNG.

Move built-in completion data into prepared effects. Define optional post-commit notifications separately, with exactly-once logical delivery/idempotent keys and retry. Unsupported callbacks must fail safely before publication. No opaque hook should be the final operation needed to make a supposedly committed batch complete.

## 8. Ordered production increments for later authorization

This is a dependency-ordered plan, **not permission to execute any production patch**. Each increment requires separate review. Existing characterization assertions for behavior intentionally superseded by that increment must be migrated explicitly to adopted target assertions; do not keep defects just to preserve the legacy count or weaken unrelated tests.

Common regression commands from `src/`:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s ../tests -p 'test_encounter_legacy_characterization.py' -v
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s ../tests -p 'test_encounter_cycle.py'
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s ../tests -p 'test_*.py'
```

### Increment 1 — Pure schedule preparation and minimum-duration gate

Targets: `src/encounter.py`, `src/action.py`, `src/activities.py`, `src/melee_combat.py`, `src/melee_defense.py`, `src/group_observation.py`, `src/history_conversation.py`, `src/tactical_duel.py`; scheduling/timing tests.

Extract read-only preparation from built-in schedule hooks. Validate final duration ≥1, finite deadlines, parents, references and Encounter end **before publication**, allow t=0 starts, and preserve defense placeholder finalization. Eliminate TacticalDuel double hook calls and route legacy AI registration through the supported path. Add a publication guard/preflight contract for custom Events; do not claim arbitrary-hook rollback.

Acceptance: no finalized short/zero/negative/nonfinite Actions register; real defense finalizes correctly; nested preparation failure changes no authoritative state; legacy valid single-action schedules retain timings/results. Regression: common commands plus `test_running_action.py`, `test_spot_action.py`, `test_attack_specific_defense.py`, `test_combat_engagement.py`. Approval needed first: extension boundary and preparation contract, not the already-adopted one-second minimum.

### Increment 2 — Boundary cursor and chronological progression

Targets: `src/encounter.py`, `src/event.py` if separate nominal/effective timing fields require it, `src/tactical_duel.py` and save/replay interfaces, boundary tests.

Implement common boundary walker for `step()`/`run()`, integer bucket assignment, fractional kinematics with no premature dispatch, exactly-once cursor, active-boundary scheduling refusal, finite direct-dispatch validation, and stale/corrupt schedule errors. Provide explicit movement/prepared-frame failure state according to approved rollback contract. Do not add reconstruction or late execution. Adopt clock/environment/history cadence and persist/version cursor information or reject unsupported restore.

Acceptance: boundary 0 never resolves Actions; deadlines at/just above n bucket correctly; long constant-velocity step matches one-second sequence for equivalent inputs; empty boundaries processed exactly once; no nested or repeated dispatch; hook/publication cannot enter a closed bucket; stale data fails before effects. Common regressions plus new boundary specs and `test_encounter_frame.py`, `test_native_physical_fatigue.py`, `test_native_physical_work.py`. This increment fixes time grouping but must not yet claim simultaneous atomic consequences while legacy evaluators remain.

### Increment 3 — Whole-choice lifecycle and exclusive-use declarations

Targets: `src/encounter.py`, native Action subclasses, a small native choice/resource module if needed, `src/tactical_duel.py`, AI/GUI callers and versioned replay/session handling.

Introduce drafts, diagnostic validation tokens, whole valid acceptance, competing reservations, atomic replacement/undo before execution, and complete-set registration. Add multi-Object resource declarations and the approved active-window/bucket/endpoint/actor scope. Prepare same-set defense references. Preserve passive armor/shield multi-impact behavior. Single `schedule_action()` is a one-item adapter, not a bypass.

Acceptance: all named CHOICE cases above pass; invalid sets never partly register; shared active weapon conflicts refused during scheduling; distinct valid resources remain usable; accepted group undo leaves no parent/event/hook leak; published/started cancellation retains intent. Common regressions plus `test_attack_specific_defense.py`, `test_combat_reactions.py`, `test_ai_encounter.py`, `test_combat_next.py`. Requires the remaining F2 scope/window decision and selected publication/undo contract.

### Increment 4 — Native immutable evaluation and explicit effect proposals

Targets: `src/experience.py`, `src/action.py`, `src/melee_combat.py`, `src/melee_defense.py`, `src/activities.py`, `src/encounter.py`, small snapshot/effect types, `src/tactical_duel.py` result consumers.

Extract current combat calculations into snapshot reads and typed shield/armor/body/self/fatal effects; retain saves/critical bypass/dice ordering. Add explicit own-action contribution fields before switching HP-before/after meaning. Represent all F1 defense provenance. Adapt pure Run/Spot evaluation. Keep tested direct helper compatibility where possible, and explicitly mark any temporary single-action adapter as nontransactional. New coordinator stays gated from unsupported evaluator families until the next increment closes them.

Acceptance: single-action equivalence under fixed rolls for compatible mechanics; evaluator leaves live state unchanged; two valid simultaneous attacks use identical inputs; all defenses read original ranks; UI no longer infers own damage from final-HP delta. Common regressions plus `test_action.py`, `test_melee_combat.py`, `test_armor.py`, `test_weapon.py`, and F1/H5 consumer specs. No Q/B penalty/work activation.

### Increment 5 — Full batch candidate state, Reality, reducer, and atomic publication

Targets: `src/encounter.py`, effect/reducer types, `src/object.py`, `src/being.py`, `src/group_observation.py`, `src/history_conversation.py`, `src/personal_history.py`, `src/realization.py`, `src/statistical_group.py`, `src/field_observation.py`, `src/tactical_duel.py`, serialization/replay surfaces.

Stage shared group/history Reality, observer evidence, combined practice and personal-history validation, action records and queues. Implement H1–H4 negative additive damage and the adopted H2 fatal reducer **together with** own-action contribution/H5 result handling, rather than first flipping `Object.damage()` in isolation. Validate all candidate effects, publish identity-preserving state and RNG once, and discard the complete second on contradiction/failure. Convert built-in completion hooks to effects; integrate approved notification contracts. Add versioned replay/save transitions and refuse unsupported restore/extensions without mutating state.

Acceptance: every pending H/R/batch test passes, including negative equipment HP, fatal+real damage exactly once, shared truth with different beliefs, no partial practice/evidence/result publication, live reference identity, abort/retry RNG determinism, and prior-second persistence. Common full regression plus `test_personal_history.py`, `test_realization_contract.py`, `test_group_observation_action.py`, `test_belief_revision.py`, `test_native_physical_fatigue.py`, `test_native_physical_work.py`, `test_tactical_duel.py`, `test_combat_visual.py`.

The final increment is broader because atomicity spans these families. If too large for safe review, split its implementation into separately tested, inactive candidate adapters, then one reviewed activation patch; do not activate a partially transactional fallback. This ordering deliberately moves pure scheduling preparation before choice acceptance, and contributions before the damage reducer: otherwise hook leaks and H5 double attribution would survive apparently small fixes.

## 9. Approval checklist

### Remaining simulation semantics

- [ ] Exact F2 active-use scope and interval: full action versus narrower active subwindows; readiness/holding through boundary; endpoint handoff; overlap across distinct completion buckets; relationship to same-bucket prohibition. Determine whether/how actor Beings, conversational speakers, body parts, or multi-Object extensions reserve active resources without silently banning established concurrent movement.

### Engineering contracts to approve

- [ ] Accepted-choice reservation/publication/start fence and whole-group undo lifetime; replacement competition; persistence of unexecuted selections. Proposed default is reversible accepted choice storage followed by atomic publication/start.
- [ ] Failed-second movement/clock checkpoint, partial fractional progression, retry inputs, earlier committed-second preservation, and atomic RNG cursor handling. No late recovery implied.
- [ ] Stable random allocation/replay version strategy, pure shared-realization generator protocol, and conflict diagnostics. Existing ledgers must not be silently overwritten or resampled.
- [ ] Restriction/adaptation of custom Events and hooks, direct dispatcher compatibility, and post-commit notification delivery. Decide generic Event timing scope separately from adopted Action minimum duration.
- [ ] Result schema extension for individual contributions and multiple-defense provenance, journal versioning, and incomplete legacy Universe load behavior. H5 shared final HP itself is already adopted.
- [ ] Approve the scope of **increment 1 only** after reviewing this report and tests; later increments remain separately gated.

Not pending: T1–T5 integer grouping and chronological progression; Action start at zero/minimum one second; no late fallback; F2 scheduling-time refusal and passive protection exemption; positive whole-set validation/acceptance and reversible pre-execution choice; H1–H5 including `min(H,-10)-D`; F1 at-least-one-success; R1–R5 shared Reality and atomic contradiction rejection. No new combat/fatigue/breakage rules are proposed.

## 10. Exact characterization-test catalog

All tests below live in [`test_encounter_legacy_characterization.py`](../tests/test_encounter_legacy_characterization.py). Names deliberately say `legacy`; assertions describe the current migration baseline, not rules to preserve after authorized target implementation. ProbeAction is instrumentation around the native scheduler; all damage tests invoke native handlers. Pending target cases above are documentation only.

### `TestLegacyTimeline`

- `test_legacy_registered_zero_duration_action_can_resolve_at_zero`
- `test_legacy_schedule_duration_matrix`
- `test_legacy_builtin_duration_constructors_allow_positive_subsecond`
- `test_legacy_base_action_ignores_supplied_end_and_defaults_to_one_second`
- `test_legacy_defense_constructor_placeholder_finalizes_on_schedule`
- `test_legacy_final_deadline_is_not_revalidated_after_schedule_hook`
- `test_legacy_fractional_deadline_executes_before_integer_boundary`
- `test_legacy_fractional_deadlines_in_one_second_observe_sequential_effects`
- `test_legacy_exact_and_immediately_after_integer_deadline`
- `test_legacy_long_step_samples_endpoint_instead_of_earlier_boundary`
- `test_legacy_successive_steps_sample_each_endpoint`
- `test_legacy_direct_future_and_repeated_dispatch_does_not_advance_clock`
- `test_legacy_stale_missing_and_null_pending_events`
- `test_legacy_nonfinite_dispatch_cutoff_is_not_validated`
- `test_legacy_run_dispatches_at_zero_then_increments_without_dispatch_at_one`

### `TestLegacyChoiceAndHooks`

- `test_legacy_same_weapon_overlap_and_resolution_bucket_conflicts_are_accepted`
- `test_legacy_real_strikes_can_share_one_actively_held_weapon`
- `test_legacy_same_weapon_can_attack_and_parry_overlapping_actions`
- `test_legacy_sequential_group_registration_leaves_first_when_second_fails`
- `test_legacy_failed_schedule_hook_leaks_being_change_and_nested_registration`
- `test_legacy_on_schedule_can_register_nested_same_time_action`
- `test_legacy_resolve_and_completed_can_register_active_boundary_actions`
- `test_legacy_schedule_hook_can_register_into_an_already_resolving_boundary`
- `test_legacy_reentrant_dispatch_reexecutes_current_action_before_list_failure`
- `test_legacy_cancellation_retains_registration_and_schedule_effects`
- `test_legacy_completion_hook_failure_occurs_after_finished_publication`
- `test_legacy_step_failure_retains_movement_effects_and_consumed_randomness`
- `test_legacy_same_second_practice_is_visible_to_later_evaluator`
- `test_legacy_custom_resolvable_event_is_accepted_but_not_cancelable`
- `test_legacy_instrument_id_is_not_generally_validated_by_scheduler`
- `test_legacy_target_disappearance_raises_without_completing_strike`
- `test_legacy_instrument_disappearance_completes_as_weapon_unavailable`
- `test_legacy_hook_cancellation_does_not_remove_later_action_from_frozen_due_list`

### `TestLegacyDamage`

- `test_legacy_ordinary_damage_zero_clamp_and_negative_hp_reset`
- `test_legacy_armor_hp_zero_clamps_but_protection_does_not_degrade`
- `test_legacy_multiple_fatals_are_nonadditive_and_do_not_heal_by_themselves`
- `test_legacy_fatal_and_ordinary_damage_are_order_dependent`
- `test_legacy_fatal_path_rolls_defender_save_without_ordinary_damage`
- `test_legacy_successful_fatal_save_falls_back_to_critical_damage`
- `test_legacy_shared_target_records_sequential_hp_not_shared_final_hp`
- `test_legacy_drop_weapon_handler_does_not_remove_held_weapon`
- `test_legacy_universe_loader_cannot_reconstruct_saved_probe_actions`
