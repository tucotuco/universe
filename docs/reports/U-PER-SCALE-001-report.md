# U-PER-SCALE-001 — Engineering report

**Status:** ACTIVE; segmented persistence and the t=300/65-Action demonstration are verified, but the binding addendum acceptance matrix remains partial and is not accepted. Do not archive or mark the assignment complete before acceptance.

**Program:** U-PER-SCALE-001 is the sole ACTIVE implementation program. U-ACT-GATE-001 remains FUTURE/unpassed, U-NET-001 remains DEFERRED, and U-ACT-FULL-003 remains DEFERRED. Shield completion is the next implementation priority; ranged Actions follow the shared 3-D geometry work.

**Repository:** active Universe checkout; no push performed.

**Execution intervals (America/Los_Angeles):**

| Interval | Start | End | Elapsed |
|---|---|---|---|
| Initial implementation | 2026-11-15T16:42:40-08:00 | 2026-11-15T17:52:06-08:00 | PT1H9M26S |
| Extended operational verification | 2026-11-15T18:19:20-08:00 | 2026-11-15T19:08:18-08:00 | PT48M58S |
| Sufficiency addendum continuation | 2026-11-15T20:39:02-08:00 | 2026-11-16T03:08:36-08:00 | PT6H29M34S |

**Current addendum disposition:** Current portable save schema `/12` (archive `/3`) stores the native resumable graph, compatibility-bound immutable definitions, and independently validated commit-boundary history. Completed native Action roots are now stored with their exact boundary segments and restored before strict native inventory validation. At t=300: snapshot 23,813 nodes / 331,315 bytes; definitions 51,921 / 560,106; history 1,139,080 / 12,815,153; compressed archive 2,968,730 bytes. Snapshot falls 39.3% (16,517 nodes / 214,795 bytes) versus `/11`, with no loss of Action identity or history. The 64+1 Feint run, 169 quiet boundaries, strict fresh-process Load→Save, and t=301 continuation pass. Supported `/10` and `/11` archives migrate through fresh processes. Chrome `/12` Save produced the served UI download confirmation; Open-file Load remains unverified because extension local-file access is disabled. HTTP/session Save/Load, transactional rejection, and interrupted-export preservation pass. The 2/20/200 curve concerns registry Beings, not active combatants. The assignment remains ACTIVE: state is still a recursive native graph, completed Choice settlement wrappers remain in current state, Load eagerly reassembles history, active Encounter participation is two Beings, and served Chrome Open is unverified.

**Active execution time across three sessions:** PT8H27M58S. **Total calendar span:** PT10H25M56S from first recorded Start to last End; the two inter-session gaps total PT1H57M58S and are excluded from active execution time.

The original interval established a fixed-size graph-reference encoding and corrected four checkpoint-adapter cases. The latest interval followed up because that first format still failed strict Save at t=91. Its results supersede the earlier report's t=67-only reliability conclusion.

## Sufficiency architecture and current verification

The addendum changes the target from “stay under one million nodes” to “persist only resumable facts, plus lossless history once.” This execution added a bounded portable archive, moved ten reviewed append-only history field families into ordered history segments, and made native committed inspection index Target records once instead of repeatedly rescanning each Target's full prefix. This continuation also reuses equal immutable projections across consecutive committed inspection and Target records. Receipt identity, boundary, fields, event references and history ordering remain present; only equal immutable subvalues share an in-memory graph node. The read fence recognizes only the closed frozen history fields by sequence identity; mutable fatigue frames remain content-checked. Strict inspection and checkpoint capture still validate row contents, receipt fingerprints, schema compatibility and cross-references. No native combat rule, Action eligibility, RNG algorithm or structural safety cap was relaxed.

The source audit separates four classes. Entity/Object/condition/custody/position state, RNG cursor, pending Actions and Choices, scheduler state, current observer awareness, unresolved facts and the current fatigue frame affect the next legal boundary and remain in the snapshot. Completed receipts, per-Target interval records, past fatigue frames and observer history remain durable in ordered segments. Shared immutable definitions are now in `definitions.json`, referenced by the same native identities from the snapshot/history; they are not regenerated from a current Library. Locks, pointer anchors, signature caches and display handles are rebuilt or stored only as stable IDs. The current-state representation remains a closed, compatibility-bound native graph table, not a field-minimal Arena domain-row model. The field audit omits 15 proved process-local/derived fields from the resumable document: Universe synchronization and the verified-empty reproduction registry; ChoiceBook lock and draft/validation caches; quiescent Encounter transaction flags; the absent Arena physiology registry; and coordinator clocks that must exactly equal `Encounter.time`. Restore recreates these fields. The source-linked inventory records the readers and checks. A fail-closed per-type field gate at capture, encoding, decoding and restore requires every native tag to have an explicit `FIELD_ADAPTERS` allowed/required contract; unknown fields, missing current-schema fields, duplicate field names, malformed pairs and unreviewed tags refuse. Restore requires every ordinary field and permits omission only for the explicit `ARENA_REBUILT_FIELDS` set. This closes accidental runtime-field expansion but does not itself transform the remaining graph into domain rows.

The `/12` archive carries reviewed immutable `*Definition` records in `definitions.json` and keeps exact references from the native graph. It stores completed Action roots in their commit-boundary segments. Generic Event rows and accepted ChoiceBook settlement structures remain in the compatibility-bound graph because current native consumers still resolve them.

The alternative explicit native field adapter does not currently certify the whole Arena closure: a direct read-only t=0 `capture_checkpoint_candidate(..., native_adapters=True)` probe returned `bounded_run_spot_closure_verified` together with `semantic_closure_adapter_incomplete`. `checkpoint_fields.RUN_SPOT_FIELD_CLOSURE` deliberately says it does not close unrelated Library dictionaries, all Universe aliases, receipt reissuance/anchors or general restoration. The general inventory diagnostic likewise says its semantic closure is incomplete. This explains why a compact hand-authored current-state restore could not be substituted safely in this continuation without implementing and validating new adapter/reconstruction coverage. The ordinary production path therefore remains the exact closed-type native schema; this gap is explicitly still open, not described as an accepted normalized model.

| Category | Before segmented archive | Current `/12` representation | Authority / exact fact kept |
|---|---|---|---|
| Current Being/Object state, custody, equipment, position, conditions, pending schedules/Choices, RNG and observer current knowledge | Native snapshot | Native snapshot | Authoritative input to future simulation; stable native IDs and current values retained. |
| Encounter boundary receipts and Target interval projections | Embedded prefixes in native snapshot | One ordered segment attachment per committed boundary | Durable committed record, including Action/effect identity and target-owned state. |
| Fatigue frames | Embedded Encounter list | One ordered segment record per boundary, with latest frame still available after reassembly | Prior frames remain historical; latest frame is future-relevant. |
| Observer perception history | Embedded ledger history list | Ordered per-boundary ledger attachments | Observer-specific evidence and provenance retained without omniscient reconstruction. |
| Equal immutable committed inspection projections | Detached separately in consecutive interval receipts | Reuse prior projection only when complete frozen value equality holds | Receipt identity, boundary and changed fields remain unique; no historical facts are omitted. |
| Equal immutable Target candidate state | Copied into every Target interval record | Reuse prior `TargetCandidate` only when its full value is equal | `TargetIntervalRecord` owner/boundary remains unique; changed outgoing effect identities are kept distinct. |
| Completed native Action roots | Native snapshot graph | Stable root in the exact committed-boundary history segment; absent from snapshot | Loader checks event identity, Action type, resolved state and boundary, then restores the same Action before strict inspection. |
| Generic Event rows and accepted Choice settlements | Native snapshot graph | Remain in native snapshot graph | ChoiceBook, history conversation, Action follow-up, restoration and inspection still resolve these identities. |
| Immutable `*Definition` records | Native snapshot graph | Separate compatibility-bound `definitions.json`; snapshot and history keep exact graph references | Definition type allowlist is explicit; content is included once, never regenerated from a newer Library. |
| Runtime locks, object addresses, cached signatures and browser handles | Reconstructed or session metadata | Reconstructed or stable-ID session metadata | Not authoritative facts; no raw address is persisted. |

### Current acceptance matrix

The first `/11` 5×5, 10,000-XP generated Arena measured a resume snapshot of 145,906 bytes / 11,645 wire nodes, a separate definition table of 548,728 bytes / 50,625 nodes, and 458 bytes of history in a 220,070-byte archive. The prior `/10` 2-Being measurement was 624,702 snapshot bytes / 49,179 nodes and a 213,151-byte archive. Thus the resume-only document is substantially smaller while definitions remain self-contained and exact; total archive size is slightly larger because the separate document carries its own schema and metadata. The fixture seed/profile differ from some earlier t=0 attribution values, so this is a format observation, not a controlled before/after percentage.

| Addendum requirement | Status | Evidence / remaining work |
|---|---|---|
| Field-by-field necessity/readers audit | Partial | [Inventory](../design/persistence-sufficiency-inventory.md) traces next-boundary vs historical role, ownership, source readers and shared definitions, and includes row attribution. The 2/20/200 registry curve measures unplaced Beings plus equipment, not active Encounter scaling. |
| Resumable snapshot separated from durable history | Partial | `/12` stores snapshot, immutable definitions, and digest-checked ordered history segments. Completed Action roots move to history; generic Events and accepted choice settlements remain in snapshot. History is eagerly reassembled at Load; this is not yet a compact domain-row/current-state reference model. |
| Resume-only growth plateau after action burst | Met for current 2-Being Arena case | After 65 Feints, t=131→300 advances 169 lawful quiet boundaries: snapshot stays 23,813 nodes / 331,315 bytes; definitions stay 51,921 / 560,106; history grows from 5,949,893 to 12,815,153 bytes. |
| At least 64 lawful combat resolutions | Met for the adopted Feint slice | 64 in-range Feints produced native `success`/`failure` Attack Roll receipts, followed by a 65th Action. Feint is nondamaging by rule; HP stays 81/97. This test does not establish a 64-hit damage workload or multi-opponent combat scale. |
| Exact multiple fresh-process continuation | Met for tested boundaries | Existing seed-14 branches verify t=67→72, t=91→92 and t=100→101. Generated-Arena regression saves after 64 Actions and at t=300; independent processes restore/resave exact bytes and continue t=131/t=301 identically. Stable Being/Object/Action IDs, receipts, observer history, RNG and HP are checked. |
| Proportionate lossless history and strict integrity | Met for the tested archive contract | t=300 has 300 contiguous segments, 1,139,080 history wire nodes and 12,815,153 history bytes. Missing, extra, altered/truncated segment, definitions, bad digest/CRC/path, unsupported schema/type and cursor mismatch refuse without replacing live state. Limits unchanged: 1,000,000 nodes per document, 10,000,000 aggregate nodes, 64 MiB aggregate decoded data/archive, bounded entries and compression ratio. |
| Crash/failure recovery | Met for preserving the caller's previous complete portable artifact; no autosave claim | Tests inject an export exception and kill a fresh OS process with `os._exit(73)` during history-entry writing. The previously complete `.uarena` held by the caller remains byte-identical and a second fresh OS process strictly loads/resaves it byte-identically. The source live candidate also remains unchanged on caught failure. This does not test an in-place local save-file replacement or autosave. Truncated/corrupt Load is transactional. There is no autosave/durable append journal: a crash before the user downloads a new complete artifact loses post-save progress, while the last complete file remains recoverable. |
| Legacy compatibility and prior regressions | Met for focused supported schemas | Native v3/pinned v4 and portable `/10`/`/11` migrations pass in fresh processes; 48 checkpoint-adapter tests and prior t=91/t=100 continuations pass. The current-format focused cohort also passes transactional segment rejection and 2/20/200 registry persistence. |
| Ordinary browser file Save/Load | Partial | Current served Chrome `/12` Save displayed “Encounter downloaded as a portable native save archive.” Open-file Load was blocked because the extension local-file permission is disabled. No current `/12` browser reload is claimed. The old 223,484-byte artifact is confirmed `/10` only; HTTP/session and native strict Save/Load pass. |
| World-size, memory and normal load-time scaling | Partial | Current `/12` strict fresh-process registry curve passes at 2/20/200 BeingInstances, with 0/18/198 WeaponInstances recorded in their inventories. All additional Beings are unplaced and non-participating. Resume snapshot bytes are 145,562 / 302,833 / 1,879,939; nodes are 11,621 / 24,294 / 151,014. Definitions are 551,452 / 709,564 / 2,290,684 bytes. Full portable archives are 220,106 / 311,891 / 1,202,866 bytes. At 200, create/save peak RSS is 131,104,768 bytes and Save is 0.949s; fresh Load is 0.618s, exact resave 0.931s, Load-worker peak RSS 112,787,456 bytes. Combat/perception still supports two participants. At t=300, fresh Load+exact-resave is 18.820s with 278,773,760 peak RSS.

### Extended scenario measurements

The run uses the published generated-Arena/native Encounter path, 5,000,000 XP, a fixed seed, empty ground-equipment profile, actual represented 0.2 m separation, and Difficulty Class 1 as prepublication scenario inputs. Each of the 64 Feints resolved to a native success or failure Attack Roll; no out-of-reach results were counted. A 65th Feint was chosen through the Arena session route after strict fresh-process restoration. Feint is nondamaging in the adopted rule, so preserving both Being HP at 81/97 is the expected consequence, not suppressed damage. The Action sequence and history remain persisted.

| Boundary | Feint Actions resolved | Action roots in history | Snapshot nodes | Snapshot bytes | History segments | History nodes | History bytes | Full archive bytes |
|---:|---:|---:|---:|---:|---:|---:|---:|
| t=129 (after 64 Feints) | 64 | 65 | 23,643 | 328,686 | 129 | 522,542 | 5,843,925 | not emitted in test log |
| t=131 (after 65th Feint) | 65 | 66 | 23,813 | 331,315 | 131 | 531,648 | 5,949,893 | not emitted in test log |
| t=300 (169 quiet boundaries later) | 65 | 66 | 23,813 | 331,315 | 300 | 1,139,080 | 12,815,153 | 2,968,730 |

At t=131→300 `/12` snapshot and definitions are byte- and node-stable. History increases 6,865,260 bytes over 169 commits (about 40,623 bytes/boundary). Decoded snapshot+definitions+history total 13,706,574 bytes; the ZIP is 2,968,730 bytes (4.62:1). Versus `/11`, snapshot falls 39.3% (16,517 nodes / 214,795 bytes), history increases 297,125 bytes because completed Actions now reside in boundary segments, and compressed archive falls 5,743 bytes. In the latest run Save took 4.938s; fresh-process strict Load plus exact resave took 18.820s; peak RSS was 278,773,760 bytes. These are measurements of the two-Being fixture, not projections.

History composition at t=300: 300 Encounter interval receipts, 300 fatigue frames, 600 Being Target records, 600 Armor Target records, 600 Weapon Target records, 11 observer-history records, zero skill-use records and 66 completed Action roots. History segment wire nodes total 1,139,080. Field rows remain exact and identity-linked; row category bytes are diagnostic and not additive to archive bytes. A fresh 10,000-XP, 10×5 empty-loadout t=0 Arena was measured through the live capture path: 637,923 native wire bytes and 2,369 graph rows. The ten largest canonical row groups are in the linked inventory; ordered-map rows account for 384,216 attributed bytes, followed by WeaponDefinition (112,614) and BeingDefinition (77,885).

The new t=300 snapshot diagnostic attributes the ten largest graph-row categories as follows. It counts canonical row bytes by owning node type; these numbers exclude surrounding list/manifest syntax and are not additive to `snapshot.json` bytes.

| Current snapshot row type | Rows | Canonical row bytes |
|---|---:|---:|
| Native list containers | 61 | 247,762 |
| Native ordered-map containers | 313 | 159,417 |
| Native tuple containers | 211 | 37,971 |
| Completed `action.Action` instances | 0 | 0 (roots are in history) |
| `EffectIdentity` instances | 132 | 48,800 |
| `ActionProposal` records | 66 | 48,747 |
| `PreparedSchedule` records | 66 | 47,427 |
| `LifecycleEffect` records | 66 | 43,182 |
| ChoiceBook `_Accepted` records | 66 | 36,765 |
| `ChoiceView` records | 66 | 25,213 |

Under `/11`, completed Action rows were 65 / 79,434 canonical bytes. Under `/12`, those rows are absent from snapshot and the tuple group falls from 474 / 88,508 to 211 / 37,971 bytes. The remaining 66-choice settlement records stay in current state because native ChoiceBook, history conversation, restoration and inspection still resolve them. Immutable definition records remain separately bounded.

| History closure category | Before sharing: rows / canonical bytes | After sharing: rows / canonical bytes | Byte reduction |
|---|---:|---:|---:|
| Encounter interval receipt closure | 49,133 / 25,290,613 | 4,844 / 10,433,789 | 58.7% |
| Being Target state closure | 7,266 / 2,912,394 | 2,129 / 814,630 | 72.0% |
| Armor Target state closure | 1,800 / 754,584 | 604 / 200,238 | 73.5% |
| Weapon Target state closure | 1,800 / 753,984 | 604 / 200,236 | 73.4% |
| Fatigue frames | 1,200 / 379,582 | 1,200 / 379,582 | 0% |
| Observer history | 13 / 9,047 | 13 / 9,047 | 0% |

The repeated receipt/Target projection categories fall because exact immutable state is shared. Fatigue changes with time and stays distinct; observer history count/bytes do not change in this quiet two-observer fixture. Canonical closure bytes are diagnostic row sums; ZIP member framing and encoder-shared syntax make them non-additive to archive bytes.

### World-size registry curve

The native Arena contract still admits exactly two Encounter participants and two observer ledgers. Separately, the existing `Universe.add_object`/`ObjectRegistry` accepts additional native `BeingInstance` records that are not assigned a location or encounter participation. A test now measures this supported persisted-object path at 2/20/200 Beings. For each added Being it creates one native `WeaponInstance` and appends its stable ID to `Being.weapons`, using the existing `BeingDefinition` and Dagger definition; it does not invent distinct provenance, position, perception, group membership or combat behavior. Every archive is loaded and re-saved in a fresh OS process and compared byte-for-byte.

| Realized Beings in Universe registry | Added Weapons | Snapshot bytes/nodes | Portable file bytes | Create/save peak RSS | Save time | Fresh-load peak RSS | Strict Load / exact resave |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 0 | 145,576 / 11,621 (+ 551,452 definition bytes) | 220,072 | 51,494,912 bytes | 0.216s | 47,185,920 bytes | 0.125s / 0.184s |
| 20 | 18 | 302,843 / 24,294 (+ 709,564 definition bytes) | 311,868 | 56,672,256 bytes | 0.285s | 49,250,304 bytes | 0.165s / 0.333s |
| 200 | 198 | 1,879,948 / 151,014 (+ 2,290,684 definition bytes) | 1,202,879 | 114,114,560 bytes | 1.184s | 111,165,440 bytes | 0.593s / 0.923s |

Memory is per-worker `ru_maxrss` and includes Arena generation/strict restoration, on this macOS host. The 20/200 cases are valid world-registry persistence growth, not 20/200 active Encounter participants; the current source contract does not support scaling simulation/perception participants beyond two. The portable file stays far below the unchanged 64 MiB byte and 1,000,000-node per-document limits at 200 objects. The one focused test command and exact per-process values appear below.

### Focused verification this execution

- `UNIVERSE_PER_SCALE_METRICS=1 ../.venv/bin/python -B -m unittest test_arena_persistence.TestArenaPersistence.test_64_lawful_native_feint_resolutions_segment_history_and_resume` (cwd `tests`) — 1 passed, 315.714s. At t=300: snapshot 23,813 nodes / 331,315 bytes; definitions 51,921 / 560,106; 300 history segments, 1,139,080 history wire nodes / 12,815,153 bytes; 2,968,730-byte archive. Save 4.938s; fresh-process Load+exact resave 18.820s; peak RSS 278,773,760 bytes. t=131→300 adds 169 history segments while snapshot/definitions remain fixed; byte-exact t=301 continuation passes.
- `../.venv/bin/python -B -m unittest test_arena_persistence.TestArenaPersistence.test_segmented_portable_archive_is_exact_and_rejects_partial_history_transactionally test_arena_persistence.TestArenaPersistence.test_supported_segmented_v10_archive_migrates_in_fresh_process test_arena_persistence.TestArenaPersistence.test_supported_segmented_v11_archive_migrates_in_fresh_process test_arena_persistence.TestArenaPersistence.test_native_world_registry_persistence_size_curve_2_20_200` (cwd `tests`) — 4 passed, 21.941s.
- `UNIVERSE_PER_SCALE_METRICS=1 ../.venv/bin/python -B -m unittest test_arena_persistence.TestArenaPersistence.test_native_world_registry_persistence_size_curve_2_20_200` (cwd `tests`) — 1 passed, 6.059s; exact `/12` size/time/RSS measurements above.
- `.venv/bin/python -B -m unittest discover -s tests -p 'test_checkpoint_adapters.py'` — 48 passed, 24.429s (prior focused cohort; current changes do not modify those adapters).
- `.venv/bin/python -B -m unittest test_generated_arena_browser.TestGeneratedArenaBrowser.test_http_save_and_load_use_binary_portable_file_and_atomic_replacement` — 1 passed, 0.711s. Four current `/12` browser regressions also passed (seeded two-sided combat continuation, pending shield Save/Load, shield allocation privacy, pristine Arena Save/Load) in 15.217s. These tests use the browser/server harness; they are not manual Chrome Open-file evidence.
- Current served Chrome `/12`: clicking Save displayed “Encounter downloaded as a portable native save archive.” The extension refused local-file selection for Open because local-file access is disabled. No browser permission changed and no Chrome `/12` Load is claimed.
- `UNIVERSE_PER_SCALE_METRICS=1 .venv/bin/python -m unittest tests.test_arena_persistence.TestArenaPersistence.test_native_world_registry_persistence_size_curve_2_20_200` — 1 passed, 6.808s; independent create and load OS processes at 2/20/200 native Beings, all archives exact-resave, with 0/18/198 WeaponInstances. Snapshot and definitions metrics are in the world-size table above.
- `.venv/bin/python -m unittest tests.test_arena_persistence.TestArenaPersistence.test_segmented_portable_archive_is_exact_and_rejects_partial_history_transactionally` — 1 passed, 5.615s with the per-type field-schema gate enabled; canonical round-trip, injected exception leaves native committed state unchanged, a worker killed mid-export leaves the prior full file byte-identical and a fresh worker loads/resaves it exactly, and missing/extra/altered/truncated history preserves candidate identity and save bytes.
- `.venv/bin/python -m unittest tests.test_arena_persistence.TestArenaPersistence.test_current_snapshot_requires_reviewed_per_type_field_schemas tests.test_arena_persistence.TestArenaPersistence.test_portable_snapshot_omits_rebuilt_quiescent_runtime_fields` — 2 passed, 2.381s; unknown/missing/duplicate/unreviewed data refuse, and all 15 reconstructed fields are omitted, restored, and byte-identically resaved. Their aggregate measured t=300 saving is 853 bytes / 59 wire nodes.
- Focused `test_generated_arena_browser` shield-allocation, Draw timing and Ready/Delay HTTP controls — 3 passed within a 4-test command (the fourth was the generated Throw pending/in-flight strict fresh-process save/load); total 4 passed, 8.001s with the per-type field-schema gate enabled.
- `.venv/bin/python -m unittest tests.test_arena_persistence.TestArenaPersistence.test_pinned_native_v4_schema_migrates_to_current_compact_wire` — 1 passed, 1.225s.
- `.venv/bin/python -m unittest discover -s tests -p 'test_arena_opponent_attack.py' -k old_arena_save_schema_loads_with_autonomous_strategy_disabled` — 1 passed, 0.805s.
- `.venv/bin/python -m unittest discover -s tests -p 'test_checkpoint_adapters.py'` — 48 passed, 20.070s with the per-type field-schema gate and adapters enabled.
- `.venv/bin/python -m unittest discover -s tests -p 'test_atomic_publication.py'` — 70 passed, 49.115s after this continuation's changes.
- `.venv/bin/python -m unittest discover -s tests -p 'test_interval_staging.py'` — 57 passed, 17.744s after this continuation's changes.
- `PYTHONPATH=tests .venv/bin/python -m unittest test_encounter_inspection.TestCommittedInspection` — 32 passed, 15.871s after this continuation's changes. The full `test_encounter_inspection.py` cohort had 42 passes and one failure in an earlier run: `test_shield_can_be_negative_and_has_separate_causal_damage` expected shield HP −7/8 damage, while the unchanged native resolver and committed Target receipt produce −3/4. No shield/combat resolver file was changed; the exact failure remains outside this persistence assignment.
- `.venv/bin/python -m unittest discover -s tests -p 'test_generated_arena_browser.py' -k http_save_and_load_use_binary_portable_file_and_atomic_replacement` — 1 passed, 0.667s before the one-pass grouping optimization; rerun follows below.
- `.venv/bin/python -m unittest discover -s tests -p 'test_arena_vs_arena.py' -k two_controllers_native_consequence_and_fresh_process_continuation` — 1 passed, 10.028s.
- Gate-enabled rerun of `test_arena_vs_arena.py -k two_controllers_native_consequence_and_fresh_process_continuation` — 1 passed, 10.769s.
- Gate-enabled rerun of `test_generated_arena_browser.py -k seeded_two_sided_browser_combat_hit_and_fresh_process_continuation` — 1 passed, 7.479s.
- `py_compile` passed for changed Python modules. Full repository suite was not run.

Continuation verification after the one-pass history row grouping:

- The full `tests.test_arena_persistence.TestArenaPersistence` class ran 21 tests in 439.707s; all 21 passed. The combined command also named `tests.test_checkpoint_adapters` as a package-style module, which failed to import because `tests/` is not a package on this invocation. This runner error did not affect the 21 persistence tests. The adapter file was then rerun through unittest discovery: 48/48 passed in 20.070s.
- Earlier `/11` 64-Action and `/11` 2/20/200 runs are historical evidence only; the current `/12` replacements and exact results are listed above and in the current-format metrics run.
- After one-pass history grouping, the Arena-vs-Arena consequence/fresh-process test passed (1, 10.057s), HTTP portable Save/Load replacement passed (1, 0.552s), and seeded two-sided browser combat with fresh-process continuation passed (1, 7.487s).

Those rows above are preserved as earlier `/11` evidence. The current `/12` results replace only the explicitly labeled current-format measurements. No full persistence-class rerun or repository-wide suite was run in this continuation.

### Remaining acceptance work

1. Replace the remaining recursive native graph snapshot with a compact Arena-specific authoritative state record and stable references to immutable definitions. Completed Actions now have history roots; accepted Choice settlement and generic Event structures need a consumer-by-consumer sufficiency audit before any further extraction.
2. Extend the measured 20/200 world-object curve to active Encounter participants only if the native/adopted participant and observer contract supports it. Current Arena source fixes exactly two participants and initializes exactly two observer ledgers; do not invent group or observation rules to bypass this.
3. Reduce strict t=300 Load time further and measure repeated Save/Load memory under normal browser operation.
4. Add an interrupted-export/process-kill recovery demonstration if a durable local publication path is introduced; the current portable in-memory archive has transactional rejection evidence but no persistent append journal.

The top-ten t=0 attribution is complete. Current served Chrome `/12` Save is confirmed by its UI message. Open-file Load is unverified because local-file access is disabled in the browser extension. Legacy `/10` Chrome restoration was separately verified; no current `/12` browser reload or long-history browser walkthrough is claimed.

No shield mechanics, ranged Actions, new Encounter rules or multiple-Encounter persistence were implemented. U-PER-SCALE-001 remains ACTIVE.

## Earlier graph-only outcome (superseded by the segmented archive)

The t=91 concern is resolved by a second lossless checkpoint-format improvement. Ordinary strict Save/Load now succeeds for the terminal seed-14 combat encounter at t=91 and for later t=100 state; fresh OS processes reproduce the exact checkpoint and deterministic next interval. A continuous control and fresh-process branches match full serialized state, including native time, Being/Object and Action identity, HP/equipment, receipts, observer evidence and RNG continuation. The strict structural cap remains 1,000,000 nodes.

The adopted 2026-11-15 multiple-shield passive-protection rule is authoritative in the effective Encounter supplement and linked from the Encounter README. No shield behavior was implemented in this persistence assignment.

## Earlier v5 compression acceptance matrix (superseded by the current addendum matrix above)

| Requirement | Result | Evidence |
|---|---|---|
| Reproduce ordinary strict refusal at t=91 | Met | The prior identity-only native v4 writer produced a 1,062,228-node outer checkpoint at t=91 (native payload 11,625,696 bytes; outer save 15,540,071 bytes). The unchanged ordinary loader refused it with `native Arena state exceeds structural limits`. The analysis input was preserved outside the repository as a temporary artifact, not in user save storage. |
| Correct structural amplification without dropping history or relaxing limits | Met | Native schema `/5` and outer save schema `/9` use a per-checkpoint sorted scalar-string symbol table, compact typed-string indices, and flattened ordered-map/field pairs. Decode first applies the unchanged strict tree/depth/byte admission to the compact wire form, validates indices and pair structure, expands losslessly, then runs the ordinary graph allowlist and restoration validators. Writer admission also counts its actual emitted wire before returning. |
| Strict fresh-process Save/Load beyond the prior failure | Met | At t=91 and t=100, fresh OS processes load through the ordinary production loader, immediately re-save byte-identically, advance one interval, and produce bytes identical to uninterrupted execution at t=92 and t=101. The regression also branches at t=67 and verifies exact t=72 continuation. |
| Extended workload and preserved consequences | Met (equivalent-history clause) | The controlled seed-14 scenario resolves 91 committed intervals and 22 actual melee attacks before a combatant reaches −2 HP. It cannot lawfully continue to 64 attacks after death. It preserves all combat consequences, observers and history and is larger than the prior 67-interval/16-attack threshold; continuation to t=100/101 checks sustained post-terminal checkpoint reliability without inventing new combatants or suppressing facts. |
| Exact uninterrupted/fresh-process equivalence | Met | The regression compares full canonical save bytes at checkpoints and after continuation, and asserts stable Being/Object/Action IDs, combat HP, equipment/custody, pending/completed Action records, event receipts, observer-ledger state and RNG ownership/cursor through the production restore path. |
| Compatibility and strict rejection | Met | Exact pinned v3 native compatibility migrates; a synthetic exact pinned v4 graph fixture migrates to compact v5. Unknown fingerprints fail closed. Existing corrupt graph ID/reference/type and compact symbol/table validation regressions pass. A preserved historical v3 Arena input loads and re-saves through outer `/9`, native `/5`. An intermediate, uncommitted schema-4 fingerprint is intentionally not accepted. |
| Adapter diagnostics | Met | All four previously reported adapter cases were reproduced against pre-change baseline `e83c8f31c6583b52fbe2bc3edd9759403458bfff` and corrected narrowly; the affected adapter suite now passes 48 tests. See diagnosis below. |
| Multi-shield adoption integrated, not implemented | Met | The effective [dated Encounter supplement](../encounters/encounters-adopted-supplement-2026-11-15.md) records the adopted shared-boundary allocation and durability rule after revision 70; [Encounter README](../encounters/README.md) links and identifies it as controlling. |

## Root cause and correction

The first correction replaced repeatedly embedded traversal-path identities with fixed-size owned-node digests. That removed the dominant quadratic path-prefix amplification, but exact t=91 testing exposed a second count issue: the v4 native inventory tree had 1,062,191 nodes even though its graph node table had only 27,844 unique nodes. Repeated `('string', value)` wrappers plus nested key/value and class-field pair containers expanded the serialized tree beyond the cap. This was a genuine write/read-boundary failure; it was not a byte-limit or restore failure.

The schema `/5` compact inventory encodes the repeated typed-string vocabulary once in a sorted symbol table; negative integer tokens reference table entries. Ordered maps and class fields encode pairs as flat sequences. The decoder counts and bounds the compact serialized representation before expansion, validates the table (sorted, unique strings, at most 250,000 entries), validates each negative reference and even pair count, then reconstructs the exact prior typed inventory for the unchanged semantic validators and adapters. The format preserves every historical receipt, snapshot, observer fact, identity and RNG field. It changes representation, not simulation state.

During extension past t=100, inventory capture also encountered a separate implementation guard: it counted every scalar traversal visit against the 250,000 unique-owned-node limit. Changed capture to enforce that limit on unique emitted graph nodes while retaining recursion/depth protection and the final 1,000,000-node wire admission. Neither node limit was increased or bypassed. Native opponent scheduling after the player died was adjusted to treat the native `combatants must be able to participate` refusal as ordinary controller unavailability; it does not create a failed Action or modify native combat eligibility.

## Growth and strict-load measurements

The original v4 t=91 measurement and the compact v5 measurements below come from the same seed-14 Arena scenario and native history. Counts are decoded JSON values/containers at the production strict boundary; bytes are UTF-8 checkpoint bytes. Depth is maximum JSON nesting.

| Native time | Receipts / committed intervals | Resolved Actions | v5 tree nodes | v5 native bytes | v5 outer-save bytes | Depth |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 50,459 | 641,331 | 894,217 | 10 |
| 10 | 10 | 2 | 119,824 | 1,457,325 | 1,982,243 | 13 |
| 20 | 20 | 5 | 192,544 | 2,318,829 | 3,130,915 | 13 |
| 35 | 35 | 10 | 306,421 | 3,669,555 | 4,931,883 | 13 |
| 50 | 50 | 13 | 424,468 | 5,067,485 | 6,795,791 | 13 |
| 67 | 67 | 18 | 568,655 | 6,785,608 | 9,086,623 | 13 |
| 91 | 91 | 24 | 783,335 | 9,343,874 | 12,497,643 | 13 |
| 92 | 92 | 24 | 792,017 | 9,446,046 | 12,633,871 | 13 |
| 100 | 100 | 24 | 861,473 | 10,263,460 | 13,723,759 | 13 |

At t=91, v5 is 278,893 nodes below the unchanged cap (27.9% headroom), compared with v4's 62,228-node overage. At t=100 the same history remains 138,527 nodes below cap. History is not pruned: receipts equal committed intervals at every measured boundary; the 22 melee attacks and all resulting state/evidence remain represented. The extended t=91 checkpoint is 49.25% more intervals and 37.5% more attacks than the prior t=67/16-attack failure report. Its strict save succeeds; exact future equivalence is verified at more than one post-threshold boundary.

## Adapter diagnosis against baseline

The four cases were run in an isolated checkout of pre-change `e83c8f3`; baseline outcomes were one error and three failures (`EFFF`), not new regressions.

| Case | Verified cause and narrow correction |
|---|---|
| `test_container_cycles_and_shared_entity_state_refuse` | A cyclic nested evaluation tag escaped as `RecursionError`; active container identities now cause controlled `EvaluationIntegrityError`. Shared live entity state remains refused. |
| `test_hex_facing_requires_unknown_or_canonical_integer` | Capture failed earlier because Run/Spot field closure omitted Arena-owned Disarm landing receipt. That receipt is explicitly outside the partial Run/Spot certificate; Arena persistence uses its own typed adapter, allowing the facing validator to be exercised. |
| `test_movement_activated_arena_remains_outside_bounded_checkpoint` | Expected obsolete diagnostic. The test now asserts current bounded-closure certificate, partial/non-resumable status and no mutation; completeness is not claimed. |
| `test_unstarted_arena_opt_in_is_outside_the_initiated_checkpoint_path` | Expected an interval-validation error from inventory-only capture. The test now asserts partial capture and unchanged source state; production interval eligibility is unchanged. |

## Focused verification

Focused tests only; the full repository suite was not run.

| Command | Result |
|---|---|
| `UNIVERSE_PER_SCALE_METRICS=1 .venv/bin/python -m unittest discover -s tests -p 'test_arena_persistence.py' -k extended_seed14_combat_checkpoint_stays_strict_and_continues_exactly` | 1 test passed, 293.111s. Printed all measurements above; covered t=67→72, strict t=91→92 and t=100→101 branches. |
| `.venv/bin/python -m unittest discover -s tests -p 'test_checkpoint_adapters.py'` | 48 tests passed, 21.511s. |
| `.venv/bin/python -m unittest discover -s tests -p 'test_arena_vs_arena.py' -k two_controllers_native_consequence_and_fresh_process_continuation` | 1 test passed, 11.857s. |
| `.venv/bin/python -m unittest discover -s tests -p 'test_generated_arena_browser.py' -k seeded_two_sided_browser_combat_hit_and_fresh_process_continuation` | 1 test passed, 7.490s. |
| `python3 -m py_compile src/arena_browser_session.py src/arena_native_snapshot.py src/arena_persistence.py src/checkpoint_inventory.py tests/test_arena_persistence.py` | Passed. |
| `git diff --check` and `git diff --cached --check` | Passed; the scoped staged safety audit returned zero findings for seven intended files and five pre-staged archive paths. |

Legacy native v3 migration, pinned native v4 migration, malformed compact symbols/references, duplicate/dangling graph IDs and unsupported types are exercised in `test_arena_persistence.py`. The earlier standalone runs of those specific tests passed; they are also part of the persistence regression cohort. No whole-suite green claim is made.

## Scope, task state and preservation

- `TASKS.md` retains U-PER-SCALE-001 as the sole ACTIVE program and advances U-PER-002 with the verified t=300/65-Action bounded snapshot evidence, pending report review. U-ACT-GATE-001 remains FUTURE/unpassed; U-NET-001 remains DEFERRED; U-ACT-FULL-003 remains DEFERRED. Shield completion is next; ranged Actions remain after shared geometry.
- The inbox check found no files under `docs/ideas/inbox/`.
- The five pre-staged user archive paths remain unchanged and excluded from these commits: deletions of U-CAP-002/U-CAP-003 assignment and report files, and the U-THROW-001 patch rename into archive. Untracked `docs/assignments/universe-arena.json` and `docs/assignments/universe-arena.uarena` remain untouched. `.venv`, ignored `legacy/`, saved worlds, independent `npc-generator`, repository backups and the frozen Playtest Edition were not modified.
- No shield implementation or geometry, ranged Action, combat-mechanics, observer privacy or NPC generation work was added. Save/Load preserves represented observer evidence and combat state.

## Commits

- `5076e497d3b92cf31a77fd4d59c112ffa4fe2387` — register U-PER-SCALE-001, archive accepted U-ACT-FULL-002 assignment/report, integrate the adopted shield supplement, and reconcile program priorities.
- `240668f867bbda3469b60a34a98effc5cba3819d` — introduce compact long-running checkpoint graph identities and initial regressions.
- `17c147ad4ddab102dce52acd4cd7e301dc00a132` — earlier report closeout for the initial t=67 milestone, now superseded by this follow-up evidence.
- `d345ed525217571acbd68861c016824af69c8e80` — compact repeated-string/pair inventory encoding, unique-node capture limit correction, terminal-continuation handling, extended fresh-process regressions, and TASKS reconciliation.
- `a561e78909b084ce758b1f8829e0c5951c08f858` — `/10` segmented portable snapshot/history archive, strict archive checks, incremental Target-history inspection, append-only read-fence identity checks, generated 64-Action/t=300 fresh-process regression, and source-linked sufficiency inventory.
- `8fe46b1bec68105306528123187795b0f2167979` — equal-value inspection/Target history sharing, 2/20/200 world-registry growth with exact fresh-process round trips, archive interruption/process-kill recovery, and their tests and measurements.
- `1a4199c` — fail-closed Arena snapshot field allowlists/required-field checks, per-type coverage additions, and focused negative-schema regressions.
- `ef01b913a129c17a58a2a17e831d84702eab5c9e` — portable save/archive `/12` and `/3`, completed Action roots in commit-boundary history, strict `/11` migration fixture, and extended exact continuation regressions.

**Current closeout:** latest implementation commit is `ef01b913a129c17a58a2a17e831d84702eab5c9e`. `/12` materially reduces and bounds resume-state growth while retaining commit-boundary history and strict exact restoration; the report is still not accepted. Ordinary Chrome Save is verified, but Chrome Open-file Load was blocked by disabled extension local-file access. The current graph-backed representation and eager history reconstruction remain bounded design limits. U-PER-SCALE-001 remains ACTIVE; no push was performed.
