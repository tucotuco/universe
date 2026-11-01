# Architectural audit: `Encounter.resolve_actions()`

Audit date: October 27, 2026.

Scope: read-only inspection of the current working tree, including callers, action implementations, and relevant tests. No implementation files were changed. This Markdown report was added afterward at the user's request.

`Encounter.resolve_actions()` is a **sequential, partially snapshot-based dispatcher**, with no transaction or rollback boundary. Equal-time melee eligibility is frozen; most effects remain immediately visible to later actions.

## Existing ordering and mutation contract

In [`resolve_actions()`](../src/encounter.py#L787):

1. Capture a fatigue frame unless the caller already supplied one—even if nothing is due.
2. Collect pending events whose non-null `end_time <= as_of`. Missing event IDs are silently skipped.
3. Sort by **end time → resolution priority → pending-list position**. Equal-time defenses have priority `-1`.
4. Before processing each distinct timestamp, capture every applicable action's simultaneous eligibility.
5. Resolve each action, immediately applying whatever mutations its resolver performs.
6. For an `ActionResolution`, validate observations and skill exercises, record practice, apply awareness, and store the resolution.
7. Remove the action from pending, append it to finished, invoke `on_completed()`, then append its ID to the return value.

The method itself never advances encounter time.

## Architectural findings

### High: failures can leave effects committed while an action remains pending

Resolution runs before result validation and completion bookkeeping. Damage, equipment changes, realized history, or action-local result fields may already have changed when validation raises. Retrying can repeat effects; `MeleeStrike` instead rejects a retry once `combat_result` exists.

Evidence: [resolution acceptance](../src/encounter.py#L825) and [melee resolution](../src/melee_combat.py#L134).

### High: the award-set preflight does not cover all recording failures

The encounter calls `validate_skill_use()` for every exercise first, but `record_skill_use()` additionally validates prospective practice against personal history. A later exercise can therefore fail after an earlier exercise has committed. Retrying then encounters the earlier award's duplicate-use rejection. The “preflight the entire award set” comment overstates the guarantee.

Evidence: [skill recording](../src/being.py#L422). This failure path was identified by inspection; it was not exercised by the two probes described below.

### Medium: callbacks can invalidate the fixed work list

The due list is collected once and pending membership is never rechecked. If an earlier completion hook cancels a later due action, that action still resolves, then fails when removed from pending. An in-memory probe reproduced this sequence. Newly scheduled due actions, conversely, wait for another invocation.

Evidence: [due-list capture](../src/encounter.py#L802) and [completion bookkeeping](../src/encounter.py#L862).

### Medium: completion hooks run after the action becomes finished

A hook exception leaves the action finished and its accepted effects committed, but prevents a successful return. A subsequent pass will not retry the hook. Existing hooks deliver testimony and record observation evidence, so completion bookkeeping and evidence delivery can diverge.

Evidence: [completion hook](../src/encounter.py#L864), [testimony delivery](../src/history_conversation.py#L122), and [observation evidence recording](../src/group_observation.py#L199).

### Medium: failed batches retain unprocessed eligibility snapshots

Only the currently resolving action's snapshot is cleared. If it fails, later actions at that timestamp retain theirs; snapshot-capture failures can also leave partial assignments. An in-memory probe confirmed retention. A later normal encounter pass overwrites these snapshots, but direct action resolution can consume stale eligibility.

Evidence: [batch snapshot lifecycle](../src/encounter.py#L817).

## What “simultaneous” currently guarantees

[MeleeStrike's snapshot](../src/melee_combat.py#L112) freezes actor/target viability, weapon possession, and reach/path status. It allows a strike to proceed after an earlier equal-time impact incapacitates its actor.

Damage, armor depletion, defense markers, skill progression, awareness, hooks, and random draws remain sequential. A later equal-time action can observe earlier skill gains or other mutations. Eligibility snapshots occur before equal-time defenses resolve, while strikes subsequently read the defense markers those defenses set.

The fatigue frame has a wider scope: one frame covers the whole resolution pass, including multiple due timestamps. The frozen fatigue view is an explicit API; it does not freeze every live fatigue-related read performed by action implementations.

## Caller implications

[`step()`](../src/encounter.py#L677) commits all movement before resolving due events. Events finishing earlier within a long step therefore see endpoint positions. During resolution and hooks, `encounter.time` still holds the step's start time. If resolution fails, movement and earlier action effects remain committed while the clock and step history remain unadvanced.

## Validation and limits

**69 relevant tests passed**, covering encounter cycles, simultaneous strikes, defenses, experience, perception, history, and fatigue:

- `test_action_resolution_experience`: 6 tests.
- `test_encounter_cycle`: 9 tests.
- `test_combat_reactions`: 12 tests.
- A combined run of `test_native_physical_fatigue`, `test_spot_action`, `test_group_observation_action`, `test_personal_history`, and `TestTacticalDuel`: 42 tests.

An initial run of the entire tactical-duel test module also passed its 10 non-HTTP tests, which were repeated in the combined run and are counted only once above. Its HTTP-backed test class could not initialize because the sandbox blocks socket binding.

Two temporary, in-memory probes confirmed:

1. Removing a later due action from pending in an earlier action's completion hook still allows the later action's resolver to run, followed by `ValueError` during pending-list removal.
2. A failure in the first action of an equal-time batch leaves a later action's captured eligibility attached.

No test files or implementation files were added or modified. Findings apply to the inspected working tree, which already contained local changes; source line references may shift as that tree changes.
