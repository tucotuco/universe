# U-ARENA-005Q Engineering Report

## Outcome

This increment does **not** establish a native reconstructed Encounter. The first supported reconstruction boundary remains U-ARENA-005P's detached movement/Target identity binding. Attempting the existing native reconstruction API against the real fixed-seed movement checkpoint in a fresh process returns the precise refusal below. No fake `PublishedInterval`, Action, Choice, or restored history was installed to make that refusal disappear.

The fixed source was generated with seed `20261120`, shared starting XP `10000`, and a `5 × 5` Arena. A destination was accepted and one native second committed. The actual captured envelope/wire carries boundary sequence `(1,)` and receipt schema `universe.committed-movement-only-boundary/1`, with the two participant IDs and Target records, no Actions, Choices, or effects, both observer-owned ledgers, movement activation, and committed RNG.

The child process receives those real wire bytes and imports no `npcgen` module. It successfully runs `bind_quarantined_movement_boundary`, matching both individualized original/current definitions, stable participant and Target-history references, two independent observer ledgers, activation state, and RNG. It then exercises `reconstruct_initial_run_spot` and receives:

```text
committed boundaries are refused: no reviewed quarantine-only native Action/Target projection exists; native receipt authenticity depends on process-local issuance, which checkpoint reconstruction must not recreate
```

That is a fail-closed boundary, not a generation failure. The result remains a detached sidecar; there is no reconstructed native Encounter in this increment.

## Native invariant traced

The live publication and inspection path establishes committed history through a specific chain:

1. `publish_interval_candidate` accepts only a current issued `IntervalCandidate`, validates its frozen read and RNG state, builds an atomic write plan, appends Target-owned `TargetIntervalRecord`s, appends a `PublishedInterval`, and applies the publication phases. Only after successful publication does it register the receipt in `atomic_publication._COMMITTED_RECEIPTS`, keyed by that exact receipt object's process-local identity and paired with its owning Encounter weak reference and fingerprint.
2. The Target anchors record the identities of the registered Object, its current definition, spatial state, target-history list, and exact TargetIntervalRecord, plus the record fingerprint. `encounter_inspection.inspect_encounter` requires one matching Target-owned row per receipt boundary and verifies these identities and fingerprints. It does not accept portable IDs as substitutes for new process-local Object/storage/record anchors. The receipt inspection additionally checks the committed receipt's exact object, owner, and fingerprint.
3. The only in-engine issuance path is the real candidate publisher. Calling it to obtain a receipt would stage and publish a new interval; it cannot be used to recreate already committed movement without replaying an interval. The checkpoint reconstruction path explicitly refuses committed rows rather than directly inserting a `PublishedInterval` into the process-local authenticity registry.
4. Native inspection also requires the Encounter to be in transactional mode. Ordinary `enable_transactional_progression` only accepts the unadvanced start cursor with no committed history. The trusted-local prepared continuation gate accepts a boundary-1 Encounter only with empty `_atomic_interval_history`, empty Target history, and the existing Run continuation contract. Its preparation preflight requires one historical Run Action, so it is not a movement-only importer.

Thus the existing integrity boundary is concrete: the checkpoint describes the old successful event, but the new process has no authorized API to bind the newly reconstructed Objects and Target storage to a native committed receipt and transactional history context. Reusing the publisher would publish new simulation; direct writes to `_atomic_interval_history` or `_COMMITTED_RECEIPTS` would bypass the publisher's validation and atomicity. This increment does not add either bypass.

## Smallest next native dependency

The next required implementation is a **host-authorized imported-boundary rebind through the native receipt/restoration owner**. It must reconstruct the exact participant graph first, materialize the already-recorded TargetCandidate state without reevaluation, attach exactly one TargetIntervalRecord to each matching Being, rebuild anchors from those new Object/current/spatial/history/record identities, and admit the PublishedInterval/fingerprint to the existing process-local receipt validation only after validating the full 0→1 record. It also needs a transactional inspection/import context that accepts this authenticated committed boundary while leaving it quarantined. This uses existing receipt and anchor concepts; the current code has no such movement-only import operation. It must not invoke `publish_interval_candidate`, regenerate Target observations, or create Actions or Choices.

That import contract alone would not authorize live or general checkpoint continuation: the exact candidate flags on the captured Arena remain `inventory_validated=True`, `closure_validated=False`, `portable_schema_defined=False`, `restore_verified=False`. Whole-Universe closure and trusted restore admission remain unproved.

For a later deterministic time-2 comparison, the accepted `GeneratedArenaSession._movement_plan` must also cross the process boundary with its exact destination, rate, facing policy, and movement decision ID, bound to the restored Encounter/session identity. It currently lives outside the native inventory. The later one-second Arena step would also be a second Action-free movement interval; the adopted portable receipt rule only admits the *initial* Action-free interval, so the later interval needs its own explicit validated contract before that comparison can be claimed. No plan was synthesized and no time-2 step was attempted.

## Validation

- Focused movement-boundary suite: **2 tests passed in 4.891 seconds**. The actual fixed-seed wire is decoded and bound in a fresh Python process; the test compares identities, individualized definitions, Target records, observer ledger evidence, activation, and RNG against the source. The child confirms the native-reconstruction refusal above and does not invoke `npcgen`.
- Adjacent checkpoint controls: **35 tests passed in 30.812 seconds** across movement binding, Action-bearing identity binding, initial reconstruction, trusted-local restore preparation, and portable receipt descriptors. Existing Run/Spot paths remain green.
- Negative cases cover wrong boundary, omitted/duplicate portable Targets, omitted/duplicate native Target-history rows, mutated Target state, wrong activation phase, repeated Action-free boundary, invented Action/Choice, and source immutability after refusal.
- `py_compile` passed for the changed test and relevant checkpoint modules; `git diff --check` passed. No HTTP/loopback tests were needed.

## Commits and worktree

- `b8735e3` — Pin movement restore refusal at native boundary.
- `612dede` — Report movement-only boundary binding (prior U-ARENA-005P commit).

No application/runtime behavior was changed in this increment; the focused change makes the fresh-process native-restore refusal executable and regression-tested. Existing unrelated dirty files were preserved. No push was performed.
