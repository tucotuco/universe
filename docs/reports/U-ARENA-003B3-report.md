# U-ARENA-003B3 — Host-approved quarantined Arena state inspection

## Result

Implemented the bounded B3 policy and native construction path. A trusted local host can separately admit the exact validated B2 state candidate after B1 has prepared its exact history view. In a fresh process, the admitted graph reconstructs Ari and Bex as native `BeingInstance` Objects with their original logical IDs, Human definitions, complete captured instance fields, positions and authored `Sphere(0.5)` geometry. The native Beings are retained privately and marked quarantined. Public access returns frozen, detached views only.

This is **not** a restored Universe or Encounter. The history and candidate remain host-accepted claims; native historical receipts are neither reissued nor authenticated. The candidate RNG state remains detached data and grants no RNG ownership. U-ARENA-003 remains OPEN/BLOCKED.

## Exact source changes

Implementation commit: `6fd5140487c69a7ec33391885d66ae048f071ef6` (`Add host-approved quarantined Arena state inspection`). It contains exactly:

- `src/arena_state_admission.py` — separate host-selected, opaque, nonserializable, process-local, single-use B3 capability; exact B2/prefix/view/context/source-byte binding; strict revalidation; closed native Being graph construction; native-to-candidate field/projection comparison; process-local quarantine; immutable public views with private native ownership.
- `src/arena_history_admission.py` — process-local identity tracking for views produced by the B1 one-shot preparation path, plus a check that the admitted view still matches its exact prefix. B1's history-only authority and receipt limitations are unchanged.
- `examples/arena_state_admission.py` — Process A commits the real native six-second Spot and exports the existing B1/B2 pair. Process B separately accepts the history and state, reconstructs native Beings, compares its detached projection with Process A's candidate, and prints provenance, time, positions, geometry, HP, and Ari-only Awareness.
- `tests/test_arena_state_admission.py` — exact positive construction, private/quarantined ownership, frozen-view checks, B1-alone refusal, source/candidate/context binding, nonserializable and consumed-on-attempt capability, tamper and geometry refusal, no source Encounter/RNG/receipt mutation, and a fresh-process demonstration that imports no Encounter or publisher.
- `TASKS.md` and `docs/tasks/encounter-engine.md` — record B3 as complete within this narrow scope while keeping U-ARENA-003 open and blocked.

No native Target history was installed: its six-boundary representation remains in the detached, provenance-labeled history/candidate sidecar. No Universe, Encounter, ChoiceBook, Action, scheduler, publisher, receipt registry, or native RNG cursor is reconstructed or exposed. No step/accept-choice path exists on the public result.

## Verification

Tests ran against `/private/tmp/u-arena-003b3-checkout`, a disposable export of starting commit `2c93865f01abea1f1289e06988ad7c8ee3e27d62` with only the six implementation paths above overlaid. The export included the committed authoritative rules and revision-60 files. No source tree outside the export was used.

- Focused Arena/history/state/checkpoint/Run restoration regressions: **81 passed**.
- Dedicated B3 tests: **9 passed**.
- Fresh-process demonstration: passed; Process B reconstructed both native Beings and matched IDs, source digests, state, geometry, boundary 6, and observer-specific Awareness to Process A's data.
- Final full HTTP-inclusive suite: **1,746 passed** (`python -m unittest discover ../tests`, run from the export's `src/`). The loopback Arena HTTP tests ran successfully.
- The full suite initially ran without local legacy CSV fixtures and reported missing-file failures plus one transient `TestExertion.test_check` failure. As explicitly permitted for tests, the 16 `legacy/src/data/offspring_*_wlist.csv` bytes were copied read-only into the disposable export only. The exertion test passed in a focused rerun, and the final complete suite then passed. No legacy script ran; no file under the live `legacy/` tree changed.
- `py_compile` passed for the two changed source modules, new test module and new example.
- Revision-60 generated checks passed: `generate_outstanding_todo.py --check` and `update_encounters_toc.py --check`.
- `git diff --check`, a changed-file trailing-whitespace scan, and `git diff --cached --check` passed.

## Preservation and Git state

Started on `main` at `2c93865f01abea1f1289e06988ad7c8ee3e27d62` with an empty index and a heavily dirty working tree containing moved-document deletions plus user-managed untracked content. The initial status inventory was reported as 913 entries with untracked directories collapsed. At closeout, `git status --porcelain --untracked-files=all` reports 44 tracked deletions and 870 untracked files (914 records); the collapsed initial listing does not support a reliable file-for-file count comparison. The existing moved documentation, assignments, saved JSON, `legacy/`, `.agents/`, `.claude/`, independent-project/archive material, and other untracked work were not staged, reset, restored, moved, deleted or pushed.

The implementation commit staged exactly the six listed paths. The report is a separate documentation-only closeout commit. The report commit is the final `main` HEAD; its object ID is not written into itself because doing so would change that ID. The final commit ID is supplied in the completion response. After the report commit, only the unrelated dirty content described above remains; the index is empty.

## Remaining boundary and next requirement

The smallest next requirement for live post-restart progression is a separately authorized, source-grounded contract for assembling a private Arena Encounter around imported historical provenance while preserving process-local receipt authentication, then atomically publishing a *new* native interval receipt. It must not register historical claims as natively issued receipts, silently activate continuation, or import the old process's RNG authority. This increment establishes only quarantined Being/Object inspection; it does not claim that requirement is implemented.
