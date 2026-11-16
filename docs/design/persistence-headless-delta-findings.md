# Headless Encounter initial-state and delta proof

**Disposition:** bounded representation experiment for the still-ACTIVE U-PER-SCALE-001 program. No production persistence code or Save/Load behavior changed. The runnable proof is [`examples/encounter_delta_headless.py`](../../examples/encounter_delta_headless.py), with independent focused coverage in [`tests/test_persistence_headless_delta.py`](../../tests/test_persistence_headless_delta.py).

## Problems first

- This does **not** prove a replacement for `/12`, a general Encounter history format, or live resumability. The projected state is an explicitly bounded domain closure. It does not contain the full native Being/World/Action/Choice graph, all immutable definitions, physiology, fatigue evolution, equipment and condition fields, pending Choice settlement details, all Event types, or the observer evidence ledger. The report's [sufficiency inventory](persistence-sufficiency-inventory.md) and [109-node-type field catalog](persistence-node-field-catalog.md) show why a migration must not infer these omissions to be disposable.
- Native resumability is **NOT DEMONSTRATED**. `checkpoint_inventory.py` declares its candidate incomplete, leaves `restore_verified=False`, and its `require_complete()` explicitly refuses because there is no restore support. `arena_native_snapshot.py` does provide strict restore, but it is the Arena-specific adapter. A same-process probe captured/encoded/restored this hand-authored native fixture through that adapter (920,938 bytes); this uses the Arena persistence schema and did not prove fresh-process, Arena-independent continuation. The experiment therefore does not claim a resumable Save snapshot.
- The sample uses a Run, Delay and independent simultaneous Runs. It does not test damage, failed combat, resource consumption, observer evidence acquisition, additions/removals, or pending Actions/Choices across a saved snapshot. Those are not inferred from this proof.
- Quiet boundaries still require their own ordered time/boundary metadata and empty Event/change slots. This sample measured 130 bytes per canonical quiet delta; “unchanged state” does not mean “no committed timeline fact.”
- The earlier 26,003-byte quiet history-segment result was a different generated-Arena fixture and encoding. It is not a controlled comparison to this headless representation.

## Demonstrated closure and representation

The CLI authors two Human BeingInstances with fixed IDs, positions, represented sphere geometry, mutual directed awareness, difficulty, and a fixed private RNG seed. It constructs a native `Universe` and initiated `Encounter`, enables the existing transactional progression contract, and advances only by [`Encounter.step()`](../../src/encounter.py#L1382), which routes to the existing [`step_transactionally`](../../src/transactional_progression.py) / interval staging and [`publish_interval_candidate`](../../src/atomic_publication.py#L1493) path. No `GeneratedArenaSession`, Arena controller/browser/server, Chrome, `npcgen`, or GUI is imported or called. Actions are scheduled through native Encounter APIs; the adapter reads state after native commits and never resolves or writes an Action.

| Captured field or record | Classification | Evidence / bounds |
|---|---|---|
| Encounter ID, DC, ordered participant IDs | Identity / authored immutable | Initial state and every complete projection; IDs are stable, authored strings. |
| `pending_action_ids` | Mutable scheduler projection | Empty at all captured boundaries. It does not model accepted ChoiceBook packets or nonempty future schedules. |
| `awareness_by_observer` | Mutable, observer-owned current knowledge | Two directed observer keys are kept separate and compared at each boundary. No belief/evidence ledger is modeled. |
| Being ID/type/name and definition key | Identity / definition reference | `BeingInstance` IDs and `Human` key are stable. Definition content/version compatibility is referenced from the installed Library, not included. |
| Position (including explicit `null`), current HP, ordered possessions and weapons | Mutable current property / ordered references | Exact property presence and value are compared. Position changed at boundaries 1 and 4; the other listed values stayed fixed. |
| RNG cursor state | Future-relevant mutable state | Included in the full projection; unchanged in this non-random scenario. Its unchanged value is checked, not regenerated. |
| Boundary time and number | Per-commit timeline metadata | Recorded on every delta including quiet boundaries, separate from domain property changes. |
| Native completed Action Events | Historical facts, independent of property diffs | Stable Event/Action ID, type, parent, actor/target, start/end, native outcome and native receipt effect identities. Quiet commits explicitly carry an empty Event list. |
| Property change set | Atomic mutable fact set | One sorted path set per native boundary, with before/after values and explicit presence. The two simultaneous movements are one set attached to the shared native receipt. |

These rows are the **complete set claimed by this test**, not coverage of all 109 Arena graph tags in the [field catalog](persistence-node-field-catalog.md). Ordered lists are replaced as a whole when changed; dictionary additions/removals preserve explicit presence. Domain IDs, not Python object addresses or graph-traversal rows, key the experiment.

## Boundary-by-boundary results

Hashes below are SHA-256 of canonical typed JSON state. The recorder applies each boundary's one atomic change set to the preceding replay state and requires exact canonical equality with a fresh projection of the actual native Encounter before it proceeds. The per-boundary delta's digest is verified against that reconstructed result. Boundary/time are separately checked against the actual native cursor.

| Boundary/time | Native Actions / Events | Property changes | Actual = replay state hash (prefix shown) | Delta bytes | Native step / capture+diff+hash |
|---:|---|---|---|---:|---:|
| 1 | `action-run-ada`, Run / success | `being-ada.position`: `[0,0,0]` → `[1,0,0]` | `b7f521a5b02f` | 563 | 216.862 / 0.185 ms |
| 2 | Quiet / none | none | `b7f521a5b02f` | 130 | 198.684 / 0.166 ms |
| 3 | `action-delay-bram`, Delay / success | none | `b7f521a5b02f` | 451 | 209.184 / 0.165 ms |
| 4 | Two Runs / success, one native receipt | `being-ada.position`: `[1,0,0]` → `[2,0,0]`; `being-bram.position`: `[2,0,0]` → `[1,0,0]` | `931378bdfeee` | 1,015 | 230.516 / 0.169 ms |
| 5 | Quiet / none | none | `931378bdfeee` | 130 | 227.788 / 0.161 ms |
| 6 | Quiet / none | none | `931378bdfeee` | 130 | 228.064 / 0.163 ms |
| 7 | Quiet / none | none | `931378bdfeee` | 130 | 228.742 / 0.162 ms |

Full hashes: boundary 1–3 `b7f521a5b02f3d5492d56803acd5ccf4834e6a76c060716b091401946c1bb6b3`; boundary 4–7 `931378bdfeee8c8fce684301abac2ba1ef4fe78ec2499ac4b653d7ee2a607018`. `Delay` is an actual successful native Event with an empty property-diff set. Boundary 2 is an actual committed quiet interval with neither property changes nor Events. Boundary 4's two Event/Action IDs match the native receipt's two Action IDs; both changed positions appear in one atomic delta. This demonstrates same-boundary grouping, not a general contested-action proof. RNG and observer views remain exactly present and observer-separated at all seven snapshots.

The selected complete state snapshot at boundary 7 includes the boundary/time and every projected current-state field above. Replaying initial state plus all seven deltas produces byte-identical canonical JSON to this snapshot. The CLI was run in independent OS processes twice; canonical artifact output was byte-identical. Replayer tests reject changed preimages, duplicate paths/commits, missing boundary 1, and reordered commits.

## Storage and execution measurements

Canonical compact UTF-8 JSON bytes, uncompressed; the CLI's `--json` stdout adds one terminal newline not counted in the artifact measurement.

| Item | Bytes |
|---|---:|
| Initial state (including full Python RNG cursor) | 7,320 |
| All seven serialized boundary deltas | 2,557 |
| Of which Event arrays, including empty arrays | 1,261 |
| Of which property-diff arrays, including empty arrays | 406 (396 bytes of nonempty changes) |
| Selected complete boundary-7 snapshot | 7,352 |
| Full experimental artifact: initial + deltas + snapshot + envelope | 17,320 |

At boundaries 5–7 the native state is unchanged and each quiet delta is 130 bytes, carrying time, boundary, empty changes/Events and the state digest. Event-only data is not forced into a fake property mutation. The action and quiet commits took approximately 199–231 ms each in this run; capture/diff/hash took approximately 0.16–0.19 ms each (1.17 ms total). Seven native steps consumed 1,582.096 ms; the discrepancy from summed per-step timing is setup and loop/record overhead. A separate focused unittest run took 7.017 s for four tests, including two fresh CLI subprocess executions. These are small-fixture observations, not performance guarantees.

No same-scenario native historical-projection measurement exists for this hand-authored fixture. The prior 26,003-byte quiet-segment finding belongs to another fixture and cannot support a direct storage-win claim. The experiment's full artifact includes both a 7,320-byte initial state and a 7,352-byte selected snapshot; it does not claim that delta history alone replaces the production archive.

## Verdict and next step

For this tested two-Being closure, the measured representation is sufficient to reconstruct exact current positions, HP, identity/reference fields, ordered inventories, directed awareness, pending-action IDs, RNG cursor, boundary time, and the associated successful Action Events—including an Event with no property diff—and an atomic two-Action boundary. The invariants are executable and the strict replayer fails closed on malformed chronology/preimages.

**Do not integrate this representation into production persistence yet.** First derive an accepted per-domain field closure from native readers and historical consumers, then add and verify generic rehydration for future-relevant Action/Choice/scheduler, definitions, observer evidence, conditions, fatigue, object/custody, and history contracts. The existing Arena-native restore could be an implementation reference, but it is not proof that the smaller representation can safely resume a general Encounter. Existing `/12` Save/Load remains unchanged.
