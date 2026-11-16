# Native history bridge — problems-first findings

**Status:** U-PER-SCALE-001 remains ACTIVE. This revised assignment requires the complete native capability, not the previously bounded experiment. No production save schema was changed during the first audit.

## Problems first

- Ordinary Universe persistence is not a native resumable Encounter API. `src/universe.py` explicitly refuses restoration when the file includes Encounter or Action history and rejects saving transactional Encounters.
- Current portable `/12` is Arena-specific. `src/arena_persistence.py` requires `GeneratedArenaSession`; `src/arena_native_snapshot.py` validates against `_ARENA_TAGS`, requires the exclusive Arena RNG/Encounter form, and `restore()` binds Arena progression and reissues Arena receipt authority.
- The native graph inventory is a draft, not a completed adapter. `src/checkpoint_inventory.py` always adds `semantic_closure_adapter_incomplete`, emits all readiness flags as false, and `CheckpointCandidate.require_complete()` refuses it. `src/checkpoint_adapters.py` records data recipes and caller-supplied recipient bindings; it has no portable writer or executable native restore.
- Existing history remains a Python-object graph at the persistence boundary. `/12` segments selected append-only lists and completed Action roots, then reassembles them at Load. It does not provide a generic historical delta query API for existing inspection consumers.
- The current field registry contains 152 native types; only 104 domain types are admitted by the Arena schema. A source-linked, exact field and family inventory is in [`persistence-capability-matrix.md`](persistence-capability-matrix.md). Every row still requires its own behavioral/restore evidence; field registration alone is not proof.
- Committed recording needs a transaction-safe integration point. `publish_interval_candidate()` validates and atomically publishes the `WritePlan`, then returns the `PublishedInterval`; a recorder must only claim a commit after that publication succeeds and must not leave a journal fact on rollback. It also must preserve no-property-change Events and simultaneous grouping.
- External observer recipient ledgers, reality validators, conditional-attribute RNG providers, reproduction-group registries, and multi-Encounter identity/RNG ownership have no general self-contained save/rehydration implementation. Their precise live field contracts and readers are listed in the matrix; they have not been called impossible or excused from the scope.

## Verified source boundary

| Claim | Source evidence |
|---|---|
| `/12` production entry is generated Arena only | `src/arena_persistence.py`: `encode(session, native_inventory)` validates exact `GeneratedArenaSession`; `src/arena_browser_session.py` owns the current caller. |
| Arena tag and Encounter restriction | `src/arena_native_snapshot.py`: `_ARENA_TAGS`, `_validate_inventory()`, `capture()` and `restore()`. |
| Native inventory remains not ready | `src/checkpoint_inventory.py`: false readiness fields, `semantic_closure_adapter_incomplete`, and candidate seal refuses readiness claims. |
| Legacy Universe Encounter restore refusal | `src/universe.py`: `to_json()`, `save_to_file()` and `load_from_file()`. |
| History list segmentation and eager reassembly | `src/arena_history_segments.py`: `split()` / `reassemble()`; `src/arena_persistence.py`: encode/decode archive path. |
| Commit and rollback boundary | `src/atomic_publication.py`: `publish_interval_candidate()`, `_WritePlan`, and `PublishedInterval`. |
| Historical inspection expects committed receipt graph | `src/encounter_inspection.py`: `inspect_encounter()`, `prepare_record()`; `src/atomic_publication.py`: Target history and receipt registration. |

## Current verification

- `.venv/bin/python -B -m unittest discover -s tests -p 'test_checkpoint_inventory.py'` — 30 passed.
- `.venv/bin/python -B -m unittest discover -s tests -p 'test_checkpoint_adapters.py'` — 48 passed.
- The combined attempt to run these by package module name plus `test_arena_persistence.py` was interrupted after early test markers, so it is not counted.
- `PYTHONPATH=tests .venv/bin/python -B -m unittest test_arena_persistence.TestArenaPersistence.test_64_lawful_native_feint_resolutions_segment_history_and_resume` — 1 passed in 272.770s. This confirms the current `/12` path retains and resumes 64 lawful Actions, but the test spends over four minutes at export/fresh-process work and its graph-history storage remains the architecture being replaced. This is measured baseline, not acceptable completion of the new native history requirement.
- `/12` production Save/Load has not been modified by this continuation. The new `src/native_history.py` and `tests/test_native_history.py` provide an Arena-session-independent history-only record/read component; current snapshot, append-at-publication, native rehydration/continuation, old format integration, and historical consumer cutover are still missing. `/12`, old accepted saves, unrelated staged archive operations, and the untracked local Arena save remain intact.

## Engineering conclusion

There is no adopted-rules ambiguity preventing this work. The present implementation gaps are code and data-contract integration work, not user decisions. The acceptance target is the full matrix, native strict Save/Load/continue, native historical reader parity, portable integrity/legacy migration, and controlled breadth/scaling. The matrix and the current implementation provide the sequence and test boundaries; no partial adapter is presented as a finished bridge.
