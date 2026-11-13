# U-ARENA-005N — Individualized Being-definition checkpoint closure

## Where we stand

The exact boundary-1 Arena capture now passes the strict Being-original definition gate. It remains an incomplete, nonportable checkpoint: `inventory_validated=True`, while `closure_validated=False`, `portable_schema_defined=False`, and `restore_verified=False`. The next capture diagnostics are authenticated receipt-anchor rebinding and the existing whole-checkpoint semantic-closure gap. No restore or continuation is claimed.

## Root cause and native representation

`prepare_npcgen_arena_being` in `src/npcgen_arena_adapter.py` begins with the one registered native type template selected for the Generator record, copies it, and writes the per-Being generated values into that copy: race fallback, stature, weight, HP, exact starting XP, mapped abilities, and age-derived skills. `BeingInstance` in `src/being.py` stores this individualized definition as `original` and makes a separate copy for `current`. `Universe.add_object` registers the instance in the ObjectRegistry; it does not register the individualized definition in the Library.

That is consistent with the current data model: same-type generated Beings need distinct individualized originals. Replacing either original with the shared Library template would discard authoritative generated values and make per-Being base/max HP and definition state inaccurate. Registering both under one type key or mutating the shared template would be incorrect. No NPC Generator source was changed.

The checkpoint adapter now admits the existing representation with strict checks. A canonical original is accepted only under its unique matching Library key. An unregistered individualized original must have a matching registered template, be exclusive to one Being, be a valid closed native definition, preserve every template field outside the adapter's explicitly mapped fields (`race`, `length`, `weight`, `hit_points`, `experience`, `abilities`, `skills`), and use the adapter's exact race fallback. Its mutable subgraphs must remain exclusive across templates, originals, and current definitions. The registered template is only read; it is not altered. The closure certificate is now version 4 and records whether each original was canonical or template-derived.

Cross-process reconstruction is a distinct unresolved contract. `src/checkpoint_binding.py` currently requires every `BeingInstance.original` reference to be owned by the captured `BeingDictionary`; that cannot represent these individualized originals as presently encoded. This increment did not relax that requirement or introduce an unreviewed materialization schema.

## Evidence and strict refusals

The exact seed `20261120`, 10,000-XP, 5×5 boundary-1 test produces two Human Beings with independent `original` objects, each distinct from the canonical Human template and from each other. It verifies original/current HP, XP, length, weight, and empty native hand slots, and snapshots the type template to prove capture leaves it unchanged. Their independent mapped values and native histories remain in their own instance graphs.

The capture now emits `bounded_run_spot_closure_verified` and no Being-definition refusal. The regression temporarily changes an unmapped original field (`alignment`) and then substitutes the other Being's original; strict capture rejects the respective mismatched-template and cross-Being-alias cases. The test restores the authentic references in `finally` blocks and compares native/session state before and after the reproduction and probes. The Half-elf adapter test additionally closes two independently generated Half-elf originals against the registered Half-elf template and their separate current definitions.

The next diagnostics from the exact candidate are:

- `receipt_rebinding_required` for `CommittedBoundaryRecord.action_anchors` and `target_anchors`: native identity/digest anchors need authenticated identity-preserving issuance during restoration.
- `semantic_closure_adapter_incomplete`: the current bounded field certificate does not close unrelated Library dictionaries/entities, all Universe alias roles, fresh Choice declaration signatures, receipt reissuance/anchors, or restoration.

The candidate flags remain partial as listed above. Current binding also assumes committed Action-bearing Choice identities; the initial movement-only boundary has no Action or Choice, so the restore binding path needs an explicit treatment for that already-validated receipt form. The accepted session `_movement_plan` (destination, rate, facing policy, decision ID) and exact private RNG/Choice/Entity reconstruction are still required for deterministic continuation. The individualized-original materialization dependency must be resolved as part of that same strict reconstruction work. No permissive definition allowlist, default substitution, or new provenance requirement was added.

## Validation

Python 3.14.3. Focused commands ran at the repository root with `PYTHONPATH=src:tests:examples:../npc-generator`, except where noted.

| Command | Result |
| --- | --- |
| `PYTHONPATH=src:tests:examples:../npc-generator python -m unittest test_checkpoint_arena_perception test_checkpoint_receipt_descriptors test_arena_checkpoint_activation test_checkpoint_adapters test_npcgen_arena_adapter test_checkpoint_bounded_closure -q` | 73 tests passed in 30.320 s. Includes the exact boundary-1 capture, action-free receipt and Action-bearing controls, strict tampering/alias refusals, checkpoint adapters, generated NPC mapping, and bounded closure. |
| `PYTHONPATH=src:tests:examples:../npc-generator python -m unittest test_checkpoint_envelope test_checkpoint_wire test_checkpoint_identity_binding test_checkpoint_reconstruction test_checkpoint_inventory test_checkpoint_restore_preparation test_checkpoint_restore_continuation test_being -q` (from repository root) | 81 tests ran; 6 setup errors and 1 failure because legacy `test_being` fixtures resolve `../src/config/*.tsv` relative to `tests/`. The missing relative files also made the `ki` dictionary assertion fail; this was an invocation-directory issue. |
| `PYTHONPATH=../src:.:../examples:../../npc-generator python -m unittest test_checkpoint_envelope test_checkpoint_wire test_checkpoint_identity_binding test_checkpoint_reconstruction test_checkpoint_inventory test_checkpoint_restore_preparation test_checkpoint_restore_continuation test_being -q` (from `tests/`) | 81 tests passed in 49.934 s. |
| `PYTHONPATH=src:tests:examples:../npc-generator python -m unittest test_checkpoint_arena_perception.ArenaPerceptionCheckpointTests.test_activated_capture_closes_action_free_receipt_and_definition_identity -q` | Exact boundary-1 test passed in 0.917 s. |
| `python -m py_compile src/checkpoint_adapters.py src/checkpoint_envelope.py src/checkpoint_wire.py tests/test_checkpoint_arena_perception.py tests/test_npcgen_arena_adapter.py tests/test_arena_checkpoint_activation.py tests/test_checkpoint_bounded_closure.py` | Passed. |
| `git diff --check` | Passed before commit. |

No loopback-dependent HTTP test or cross-process restoration was necessary or run. The full repository suite was not run.

## Commits

- `1993a6f` — `Close individualized Arena Being definitions`
- A separate report commit records this document.

Unrelated pre-existing worktree changes were left unstaged. No NPC Generator files were changed and nothing was pushed.
