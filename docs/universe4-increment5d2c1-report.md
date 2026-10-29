# Universe 4 — Increment 5D2C1 report

## Result

Implemented an inactive, versioned portable descriptor for accepted choices containing exact native `RunAction` and `SpotAction` declarations. It replaces process-local accepted-signature data in the native inventory projection for those supported choices. It does not alter live scheduling signatures or enable serialization, restoration, replay, or continuation.

## Changes

- Added [checkpoint_choices.py](../src/checkpoint_choices.py): `universe.accepted-action-choice/1`, frozen detached descriptor records, exact Run/Spot adapters, exact integer/binary64 timing encoding, verified logical references, ordered member and prepared schedule capture, reservation validation, explicit unsupported-case refusal. Descriptor reads hold the native ChoiceBook lock.
- Updated [checkpoint_adapters.py](../src/checkpoint_adapters.py) to embed this descriptor in place of `_Accepted.signatures`; unsupported choice families produce `portable_choice_descriptor_unsupported`.
- Updated [checkpoint_inventory.py](../src/checkpoint_inventory.py) so the descriptor adapter participates in the rule-kernel compatibility fingerprint. Full checkpoint readiness remains false.
- Added [test_checkpoint_choice_descriptors.py](../tests/test_checkpoint_choice_descriptors.py) and updated the 5D2B blocker test to expect the newly represented supported choice.
- Extended the existing [checkpoint compatibility contract](universe4-checkpoint-compatibility-contract-draft.md) with schema, identity, numeric, rehydration, and refusal requirements.

## Descriptor behavior and limits

The descriptor preserves exact fractional values with float-hex tags, ordered members, native adapter tags, stable logical IDs, prepared schedule data, and resource reservations. It does not contain `id(type(action))`, object addresses, callables, native handles, or old live signatures. It verifies those live signatures during capture, then omits them. Future reconstruction must rebuild and validate native objects and compute fresh process-local signatures before acceptance/publication.

Only pending exact native Run and Spot Actions are supported. Custom subclasses, callback-bearing inquiries, group observation, combat/defense Actions, unresolved/ambiguous references, unknown Action fields, stale declarations, non-pending outcomes, altered member order/timing, and reservation mismatches refuse. The supported Action families currently require no active Objects; reservation tampering is still detected against the prepared schedule. No live scheduling or transactional resolver behavior changed.

The portable choice descriptor is complete only for this declared subset. Receipt reissuance/anchors, global definition/dictionary/alias closure, unsupported Action adapters, and a durable authenticated checkpoint schema remain blockers. `closure_validated`, `portable_schema_defined`, and `restore_verified` remain false, and existing export/import refusals remain intact.

## Tests and preservation

- Existing checkpoint-focused suite before edits: **73 passed**.
- Final focused checkpoint suite: **78 passed**.
- Final complete regression suite, including HTTP: **1,481 passed** (`133.899s`, `OK`).
- The repository was already dirty. Existing changes were preserved; this increment added one source module, one focused test module, narrowly updated the existing 5D2B test, changed the two checkpoint adapter/fingerprint modules, and appended to the compatibility draft. No commit was created.

Stopped after 5D2C1.
