# U-ARENA-005K — Reviewed Arena observer-ledger checkpoint closure

## Where we stand

The revision-65 observer ledger and evidence now have a strict, versioned,
bounded, pointer-free data representation integrated with native checkpoint
field admission. Its values validate and round-trip in a fresh Python process;
normal generated Arena state and a ground-Dagger `ground` → `carried` evidence
history are covered. The exact U-ARENA-005J t=1 native capture now passes both
observer-ledger validations and reaches the next refusal:

```text
CheckpointRejected: movement-activated Arena Encounter cannot be resumed by the bounded Run/Spot checkpoint
```

This increment does **not** produce a checkpoint candidate for that activated
Encounter, restore a live Encounter, advance a fresh process, or establish
Arena save/resume. The inventory/capture API and the detached ledger decoder
remain non-authorizing. No evidence is regenerated during capture or decode.

## Representation and guarantees

`checkpoint_arena_perception.py` defines three exact schemas:

- `universe.arena-perception-ledger/1`
- `universe.arena-perception-evidence/1`
- `universe.cartesian-position-binary64/1`

The ledger representation is an immutable tuple. Current evidence is sorted by
its durable Entity ID; history retains its native ordered sequence. Evidence
contains observer and Entity IDs, category, observer-visible name and type key,
position (three canonical binary64 hexadecimal values, or null), present/custody
state, boundary, time with its original integer/float type, and the adopted
revision-65 basis. No Being, Object, ledger, or position object handle is placed
in the wire representation. The serializer enforces 3,002 maximum Entity IDs,
16,384 history rows, and 4,096 characters per identity/label string.

The native encoder requires an exact `ArenaPerceptionLedger` owned by the
Encounter Being. It checks exact ledger/evidence fields, stable registered
Entity bindings, distinct observer ownership, evidence against native Entity
type, and current evidence against committed name, position, custody, boundary,
time, and that observer's native Awareness set. This uses Awareness as the
explicit host binding for the observer's current evidence set; it does not
synthesize omitted observations or expose another observer's ledger. A
post-generation authored Object can therefore be present in one observer's
ledger without being inserted into the other observer's evidence.

Historical entries are checked for valid observer and Entity bindings,
supported category/type and basis, canonical position/time, non-future
boundary/time, and global and per-Entity chronology. Historical properties
are not compared with present native state: earlier positions, names, and
custody states remain historical evidence. Decoder input must be supplied with
host-provided stable Entity and visible-Entity ID bindings. Decoding constructs
a detached `ArenaPerceptionLedger`; re-encoding against native state checks the
rebind. The representation is not authenticated authorization to restore a
world or Encounter.

`NativeInventory` admits `_arena_perception_ledger` only through this adapter.
The exact optional native field vocabulary is recorded in
`checkpoint_fields.py`; unexpected Being, ledger, or evidence fields remain
refused. Enabled Arena Beings with any ledger state must provide valid ledgers
for all Encounter observers. Old hand-authored activation fixtures without
revision-65 ledgers still reach their prior activation refusal. This preserves
their fail-closed behavior without admitting placeholder ledgers.

## Reproduction and next blocker

From the repository root, with the NPC Generator checkout at `../npc-generator`:

```sh
PYTHONPATH=src:tests:examples:../npc-generator python -m unittest test_checkpoint_arena_perception.ArenaPerceptionCheckpointTests.test_activated_capture_advances_to_movement_activation_blocker_without_mutation -v
```

The test regenerates the U-ARENA-005J seed-20261120 10,000-XP Human/opponent
Arena on the 5×5 map, selects a destination, and commits native boundary 1.
It asserts that the strict capture preflight validates both observer ledgers,
then capture refuses on the movement activation. Before and after refusal it
compares Encounter time and boundary, both native positions, the selected
session movement plan, RNG cursor state, Choice counter/records/states and
pending queue, and both observers' current and historical evidence. No value
changes on refusal.

The next unclosed dependencies are:

1. `arena_activation_enabled` and the non-null `arena_movement_activation`
   record, including authenticated actor/decision identity and lifecycle phase.
   The existing bounded Run/Spot adapter and reconstruction path explicitly
   refuse these activated fields.
2. Movement-only interval receipt provenance and safe cross-process rebinding.
   The current Action/Target receipt descriptors do not establish continuation
   authority for the target-free movement boundary.
3. `GeneratedArenaSession._movement_plan`, which owns the accepted destination,
   rate, facing policy, and decision ID outside the native Universe/Encounter
   graph. It needs an authenticated durable owner contract before continuation.
4. Full Choice, RNG-owner, registered-Entity identity, and reconstruction
   closure for the activated movement timeline. D7 inventory flags remain
   false; a ledger round-trip is only a data-adapter proof.

### U-ARENA-005J unit erratum

The movement coordinates in U-ARENA-005J differ by `3.6576` metres, equivalent
to approximately `4` yards. Its report labeled that numeric displacement as
`3.6576 yards`; that unit label was incorrect. The historical report was left
unchanged; this paragraph is the clearly labeled correction.

## Validation

All test commands below ran from the repository root on Python 3.14.3. The
relative `../npc-generator` path avoids embedding a user-home path in the report
or source.

| Command/suite | Result |
| --- | --- |
| `PYTHONPATH=src:tests:examples:../npc-generator python -m unittest test_checkpoint_arena_perception test_arena_checkpoint_activation -q` | 5 passed in 1.450 s. Covers fresh-process data round-trip, malformed/foreign/dangling/stale evidence refusals, Object pickup history, and the next activated-capture refusal. |
| Exact U-ARENA-005J capture reproduction test | 1 passed in 0.384 s. It confirms both ledger validations pass, then asserts the precise next blocker and source-state immutability. |
| `PYTHONPATH=src:tests:examples:../npc-generator python -m unittest test_checkpoint_arena_perception test_arena_checkpoint_activation test_checkpoint_adapters test_arena_initialization test_generated_arena_browser test_arena_ground_pickup test_atomic_publication test_checkpoint_inventory test_checkpoint_envelope test_checkpoint_reconstruction test_checkpoint_restore_preparation test_checkpoint_restore_continuation test_checkpoint_receipt_descriptors -q` | 235 passed in 117.573 s. |
| `python -m py_compile src/checkpoint_arena_perception.py src/checkpoint_adapters.py src/checkpoint_inventory.py src/checkpoint_fields.py tests/test_checkpoint_arena_perception.py` | Passed. |
| `git diff --check` | Passed. |

An earlier integration iteration failed two existing adapter assertions because
ledger preflight ran before hand-authored activation fixtures could reach their
established refusal. Preflight is now applied when revision-65 ledger state is
present; the final 235-test sweep passed. No loopback-dependent HTTP tests were
run in this increment, so no elevation request was needed. No full repository
suite was run.

## Commit and scope

- `f673163` — `Add strict Arena perception ledger checkpoint adapter`

Unrelated worktree changes were left untouched. No NPC Generator files were
changed. No push was made.
