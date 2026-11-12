# U-LOC-002A Engineering Report

## Result

Implemented observer-owned historical location evidence for the existing identity-free native Spot scene. Starting HEAD was `dc1fd231c7adbd4290769bd66b28aa777579a89f`; the implementation commit is `51aff36f03e393fa150c7dba3e1e101e4b7bde56`.

On a successful configured Being Spot, the native evaluator stages a frozen `BeingLocationObservation` from the common post-movement/pre-action boundary snapshot. The native publisher commits it as a causal `LocationObservationEffect` alongside Awareness and Action lifecycle. The owner-bound ledger's `last_seen_location()` returns only stored evidence and does not read live Reality. A later move leaves that historical sample unchanged. Failed Spot publishes no location evidence; exceptional observer-phase failure rolls back the record and Awareness, and seeded retry publishes one record.

The canonical example now shows the boundary-7 sample, observer isolation, and boundary-8 movement. It retains revision-60 Spot duration (six seconds), DC 15, zero Spot XP, population total 11, and the existing genealogy/Being identity. A mismatched location-ledger owner is refused before scheduling. Non-null location recipients are explicitly rejected by the current portable checkpoint inventory; checkpoint readiness flags remain false.

## Changed paths

- `src/location_observation.py` (new); `src/observer_proposals.py`, `src/activities.py`, `src/attention_intent.py`, `src/action_choice.py`, `src/atomic_publication.py`, `src/encounter_inspection.py`, `src/interval_staging.py`
- `src/checkpoint_adapters.py`, `src/checkpoint_choices.py`, `src/checkpoint_fields.py`, `src/checkpoint_inventory.py` (closed-field support and explicit checkpoint refusal)
- `examples/individual_across_genealogy_population_place.py`
- `tests/test_attention_intent.py`, `tests/test_checkpoint_choice_descriptors.py`, `tests/test_genealogy_population_place.py`
- `TASKS.md`, `docs/tasks/encounter-engine.md`, `docs/tasks/generation-and-attention.md`

## Verification

- `PYTHONPATH=tests python -m unittest tests.test_attention_intent tests.test_genealogy_population_place tests.test_checkpoint_choice_descriptors` — **23 passed**.
- `python examples/individual_across_genealogy_population_place.py` — passed; boundary 7 sampled the post-movement coordinate, the other observer had no location record, and boundary 8 movement did not change the stored sample.
- `python -m py_compile` over all changed Python source, tests, and example — passed.
- Revision-60 `generate_outstanding_todo.py --check` and `update_encounters_toc.py --check` — passed.
- `git diff --check` — passed.
- `bash run_tests.sh` with loopback socket permission — **1,703 tests passed**. The initial sandbox-only attempt could not bind local HTTP test servers; the permitted loopback run completed cleanly.

## Scope limits and repository state

This is one explicitly configured native Being Spot path. It does not add Group or general Object location evidence, location measurement uncertainty, maps, waypoints, movement prediction, or generalized Belief policy. The location recipient is not portable through checkpoint descriptors yet. Broader `U-LOC-002` and `U-SPOT-002` remain OPEN. No push was performed.

The implementation commit changed exactly 19 approved paths. Existing untracked `.agents/`, `.claude/`, assignment/archive files, `examples/saved/`, `legacy/`, `npc-generator-web/`, and the three `workspace/*.json` files were not staged or modified. A separate documentation-only commit records this report.
