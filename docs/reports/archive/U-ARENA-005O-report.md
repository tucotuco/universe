# U-ARENA-005O — Cross-process individualized Being originals

## Where we stand

The native Run checkpoint binding path now reconstructs individualized `BeingInstance.original` definitions in a fresh Python process while preserving the registered Library template and a distinct current definition. A real `npcgen`-generated pair of Human Beings was encoded from the source process, decoded and bound in a subprocess, then compared field-for-field. The binding remains quarantined and is not an authorized live Encounter restore. The exact movement-activated Arena boundary-1 candidate still has `inventory_validated=True`, `closure_validated=False`, `portable_schema_defined=False`, and `restore_verified=False`.

## Root cause and representation

The typed native checkpoint graph already encodes a Being's `original` field as a reference to a closed `being.BeingDefinition` node. That node's native `obj_type` identifies the registered type template; its owning Being node is reached from the ObjectRegistry entry and checked against the logical Being ID. No new wire schema, pointer, provenance token, or authentication mechanism was needed.

The blocker was in reconstruction. `checkpoint_binding.py` derived the Library definition key from `BeingInstance.name` (the display name) and then required every original reference to equal one of those Library dictionary nodes. `checkpoint_reconstruction.py` likewise rejected any original outside the Library. Both assumptions contradict the native Arena model: generated originals are individualized copies, while the shared Library entry is the type template.

The shared reconstruction validator now uses `NativeInventory`'s existing strict definition checks. It requires the Being owner ID to match its ObjectRegistry key; every `obj_type` to resolve to exactly one registered type template; canonical originals to use that exact template node; and each individualized original to be unique to its Being, native and closed, template-equal outside the seven mapped fields (`race`, `length`, `weight`, `hit_points`, `experience`, `abilities`, `skills`), with no shared mutable definition subgraphs. Current definitions must be distinct and have the same native type.

For a canonical original, reconstruction still uses the registered template. For an individualized original, it copies the template, deep-copies only the seven validated values from the closed native original node, and confirms the resulting complete definition matches the source node. The shared template is only read. The native `BeingInstance` constructor and ObjectRegistry path retain the Being identity; the graph's separate current node remains its independent current state. This reuses the existing pointer-free graph reference bound to owner and template instead of adding a second serialized materialization format. No Generator character is rerun during binding.

Both the initial native reconstruction path and committed Run identity binding use this treatment. Existing canonical-original cases remain supported. Display names no longer have to equal definition keys.

## Demonstration and refusal probes

The subprocess regression generates two Human Beings with npcgen seeds 5 and 10 at 10,000 XP, commits one native Run second under the existing Run transaction, captures the closed Run/Spot envelope, and sends its actual wire bytes to a fresh Python process. The subprocess decodes the wire and calls `bind_quarantined_run_boundary`; it does not call npcgen. The test compares complete `original` and `current` native definition values, HP, XP, length, weight, abilities and skills to the source; verifies original/current, template/original, and cross-Being mutable identity separation; and checks module RNG purity. The source's registered template snapshot remains unchanged after generation and checkpoint capture.

Additional controls bind a Human/Half-elf pair and bind two same-seed Human candidates whose individualized values are identical. Those identical values still reconstruct as separate originals, Abilities, and Skills objects. A self-consistent wire with an altered inherited `alignment` is refused; a self-consistent wire that aliases both Beings to one original is also refused. Existing tests cover wire-digest tampering and canonical template binding. The initial reconstruction test independently exercises individualized materialization from the existing initial graph path.

## Exact Arena boundary-1 result and next dependency

The exact seed-`20261120`, XP-`10000`, 5×5, boundary-1 Arena capture was rerun. It emits `bounded_run_spot_closure_verified` and passes inventory validation; both generated Being originals remain distinct from the registered Human template and from each other. Its two remaining diagnostics are:

- `receipt_rebinding_required` for `CommittedBoundaryRecord.action_anchors` and `target_anchors`: native identity/digest anchors need authenticated identity-preserving issuance during restoration.
- `semantic_closure_adapter_incomplete`: the bounded certificate does not close unrelated Library dictionaries/entities, every Universe alias role, fresh Choice declaration signatures, receipt reissuance/anchors, or restoration.

No candidate readiness flag was promoted. The Arena's initial target-free movement boundary also has no Action/Choice, while the existing quarantined Run binder accepts an Action-bearing Run/Spot projection only. Exact Arena continuation still needs a boundary-specific authorized receipt/identity path, the accepted session `_movement_plan` (destination, rate, facing policy, decision ID), deterministic private RNG/Choice/Entity reconstruction, and complete semantic closure. The regular Run subprocess test proves the individualized-definition binding step only; no activated Arena cross-process boundary-2 equivalence or live resume was attempted.

## Validation

Python 3.14.3, from the repository root, with `PYTHONPATH=src:tests:examples:../npc-generator` unless otherwise noted.

| Command | Result |
| --- | --- |
| `PYTHONPATH=src:tests:examples:../npc-generator python -m unittest test_checkpoint_identity_binding test_checkpoint_reconstruction test_checkpoint_arena_perception test_checkpoint_adapters test_npcgen_arena_adapter -q` | 79 tests passed in 38.684 s. Includes fresh-process native binding, identical-value and mixed-type controls, negative template/alias wires, initial reconstruction, exact Arena boundary-1 capture, and NPC adapter coverage. |
| `PYTHONPATH=src:tests:examples:../npc-generator python -m unittest test_checkpoint_envelope test_checkpoint_wire test_checkpoint_restore_preparation test_checkpoint_restore_continuation test_checkpoint_inventory test_checkpoint_bounded_closure test_checkpoint_receipt_descriptors -q` | 67 tests passed in 39.976 s. |
| `PYTHONPATH=src:tests:examples:../npc-generator python -m unittest test_checkpoint_arena_perception.ArenaPerceptionCheckpointTests.test_activated_capture_closes_action_free_receipt_and_definition_identity -q` | Exact movement-activated boundary-1 capture regression passed in 0.851 s. |
| `PYTHONPATH=src:tests:examples:../npc-generator python -m unittest test_checkpoint_reconstruction.TestInitialNativeReconstruction.test_template_derived_originals_rebuild_without_library_aliases -v` | 1 test passed in 0.211 s. |
| `python -m py_compile src/checkpoint_binding.py src/checkpoint_reconstruction.py tests/test_checkpoint_identity_binding.py tests/test_checkpoint_reconstruction.py` | Passed. |
| `git diff --check` | Passed. |

No loopback-dependent HTTP test or full repository suite was needed. No live Arena restore was claimed.

## Commits and repository state

- `beb5be7` — `Materialize individualized Being originals on bind`.
- A separate report commit records this document.
- Unrelated pre-existing worktree changes were left unstaged.
- No `npc-generator` files were changed and nothing was pushed.
