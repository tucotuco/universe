# U-ARENA-003B1 — Explicit trusted-local Arena-history admission

## Outcome

Implemented a host-authorized, read-only detached post-Spot history view for the one validated U-ARENA-003A six-boundary Arena prefix. The explicit execution request authorizes the assignment's narrowly stated application-host trust policy. Admission does **not** establish original publisher authenticity, create a live/native Encounter, or enable continuation. U-ARENA-003 remains open; checkpoint readiness flags and the existing Run-only restore path are unchanged.

## Implementation

Implementation commit: `16a692696aae081759d115bca9389228e01aa9a4` (`Add trusted-local Arena history inspection`), parent `1ba1ee58de8278d310fbcb7efa9b699c7aaf4215`, tree `2a6008f6a59d5b666eb401727f7070040ff3d1ee`. It changed exactly:

- `src/arena_history_admission.py`
- `examples/arena_history_admission.py`
- `tests/test_arena_history_admission.py`
- `TASKS.md`
- `docs/tasks/encounter-engine.md`

The private host admission function at `src/arena_history_admission.py:278-316` requires an already validated exact prefix object, the exact canonical SHA-256, an explicit expected scenario, and both host-authored source/native/position bindings. It revalidates the canonical bytes and source records. The capability is opaque, process-local, bound to that exact object/bytes/context, non-pickleable/non-JSON-serializable, and single-use. Attempted use consumes it even when revalidation refuses. A digest or decoded JSON alone cannot prepare a view.

The prepared frozen view (`:105-169`, built at `:318-341`) contains six boundaries, the resolved Spot at boundary 6, typed causal effects, Target-owned position/Awareness, original NPC source bytes and hashes, and the explicit source-to-native bindings. Geometry is absent from the validated 003A prefix, so this view does not invent or infer geometry. The host summary is detached. `observer_view()` (`:120-128`) returns only a participant's own Awareness and no coordinates; this is a filtering API, not an authenticated user/session boundary.

The new admission module does not import or use `Encounter`, the publisher/receipt registry, native checkpoint reconstruction, RNG, or the existing Run restore approval. The old authorization remains Run-specific: `src/checkpoint_restore_preparation.py:70-82,236-249` accepts a current `QuarantinedRunIdentityBinding` and its exact process-local graph; `src/checkpoint_binding.py:264-296,364-366` accepts only its single 0→1 Run case. The ordinary advanced-time constructor still refuses other cases (`src/encounter.py:128-137`). Native successful issuance remains process-local (`src/atomic_publication.py:41`); no historical receipt is forged, registered, or authenticated here.

The new runnable example `examples/arena_history_admission.py` has process A capture the actual native Arena prefix and process B decode, explicitly authorize the exact fixture, and consume the capability. It prints: **“NOT a live restored Encounter; no authoritative continuation.”** The child asserts that `atomic_publication`, `encounter`, `checkpoint_restore_preparation`, and `checkpoint_inventory` are not imported.

## Verification

- Focused isolated regressions: **52 passed** across Arena prefix/admission, checkpoint restore preparation/continuation, identity binding, receipt descriptors, native Arena, and Spot evidence tests.
- Active-worktree focused Arena/Spot regressions: **20 passed**.
- Full HTTP-inclusive regression on a disposable `git archive` export with loopback enabled: **1,727 passed**, 396.695 seconds.
- Fresh-process prefix and admission examples passed; the admitted view showed boundaries 1–6, successful Ari→Bex Spot at boundary 6, Ari-only Awareness, and both original source digests. Source bytes remain available on immutable binding records but are omitted from the human-readable summary.
- Both revision-60 generated-document checks passed: `generate_outstanding_todo.py --check` and `update_encounters_toc.py --check`.
- Changed Python files compiled. `git diff --check` and the staged whitespace check passed.
- All **72** documentation files in the isolated candidate retained their pre-suite SHA-256 values. The full suite used a clean committed export plus the exact increment files and read-only legacy CSV fixtures; it did not run against or repair the active user-managed documentation tree.

## Limits and next boundary

Trust here means that the local application host deliberately accepts this exact validated claim for read-only inspection. It is not cryptographic attestation, receipt authentication, a Python security boundary, or portable authorization. No native entities or histories are installed. No stepping, Choice acceptance, publisher calls, RNG advancement, Belief, or checkpoint readiness is exposed. The observer view only filters already-recorded Awareness; the host view remains omniscient. A later, separately authorized increment is required to design and test any live restoration/continuation contract, including how imported historical records remain separate from native-issued receipts.

## Repository preservation

Starting checkout was `main` at `1ba1ee58de8278d310fbcb7efa9b699c7aaf4215` with an empty index. It already contained 44 tracked documentation deletions and 868 untracked user-managed files, including the supplied assignment. The implementation commit staged only the five paths listed above; the index was empty afterward. No protected files, saved JSON, legacy source, or independent projects were modified, and nothing was pushed. The report is being added in a separate documentation-only commit; the final HEAD and remaining status are in the execution closeout.
