# U-ARENA-003B — Trusted-local post-Spot restore preparation

## Verdict: blocked before admission

No production preparation API was added. The existing host authorization capability cannot authorize the U-ARENA-003A six-boundary detached Arena history. Its input is a private, process-local native Run binding; accepting the Arena JSON through that API would require inventing a new authorization contract. Per the assignment, work stops at that boundary. U-ARENA-003B is not complete, U-ARENA-003 remains open/blocked, and all checkpoint readiness refusals remain unchanged.

## Source evidence

- `src/checkpoint_restore_preparation.py:52-59` defines an opaque process-local `_HostLocalApproval` registry whose values are exact native binding identities. `:70-82` only mints approval when the input is the exact `QuarantinedRunIdentityBinding` already present in `_NATIVE_BINDINGS`; other objects are rejected. `:236-249` consumes that approval only with the same binding and its existing private native graph. This is not an API for authorizing a detached Arena prefix or arbitrary bytes.
- `src/checkpoint_binding.py:261-287` keeps native bindings in a process-local `WeakKeyDictionary`, accepts only a strictly decoded `DecodedRunSpotWire`, and revalidates the Run projection. `:293-296` requires one committed boundary and no future choices; `:364-366` explicitly limits this identity binding to the start-0, boundary-1 Run case. Its reconstruction builds a closed native Run graph, not the Arena Spot identities/history.
- `src/encounter.py:127-137` preserves the ordinary constructor refusal for advanced time; the only special constructor token permits exactly start 0/time 1. It cannot create the required post-boundary-6 Encounter.
- `src/atomic_publication.py:41` documents `_COMMITTED_RECEIPTS` as process-local successful issuance, not a replay format. The detached Arena prefix must not be used to synthesize those entries.
- `src/arena_history_prefix.py:334-366` decodes only a validated detached claim. The prefix carries the trust label “detached historical claim; original publisher authenticity is not portable”; it provides no external authorization proof. Its existing capture obtains historical data from native inspection but does not mint an admission capability.
- Adopted revision-60 Spot rules remain unchanged: `docs/encounters_adopted_r60/encounters-working-draft-adopted-r60.md:385-397` defines deliberate Spot as a six-second discovery Action and its outcome/awareness rules. U-ARENA-003B did not alter those mechanics.

The existing host capability is safe for the Run case precisely because the host explicitly approves an already-created native binding and the token is process-local and single-use. There is no source-supported way to turn a detached six-boundary Arena prefix into that binding. Treating its checksum, canonical encoding, or schema validation as authorization would collapse integrity into trust and would not satisfy the assignment.

## Smallest prerequisite requiring approval

Approve a separate, explicit host policy contract for trusted-local admission of this exact Arena prefix: the host must deliberately authorize the validated schema and content digest out-of-band, with a process-local, single-use capability bound to that exact prefix and an explicit provenance label that remains distinct from native receipt authenticity. Only after that policy/API boundary is approved should a bounded Arena-specific read-only prepared view be designed. This is the one blocker; no new cryptographic receipt scheme is implied.

## Verification

- Direct refusal probe built the actual native six-boundary Arena, captured its detached prefix, and passed that prefix to `_host_authorize_trusted_local_restore`. It rejected with `host approval requires the exact private Run binding`; `_COMMITTED_RECEIPTS` remained byte-for-byte equivalent by mapping comparison.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests python -m unittest test_arena_history_prefix` on the active worktree: **5 passed**.
- The active-worktree combined command `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests python -m unittest test_arena_history_prefix test_checkpoint_restore_preparation` passed the five Arena-prefix tests, but the five Run-preparation tests errored before reaching their assertions because the tracked `docs/universe4-authoritative-decisions-2026-10-27.md` is absent from the current user-managed worktree. No restoration or repair was attempted.
- Repeated those same focused suites in a disposable `git archive HEAD` export, adding the existing read-only legacy offspring CSV test fixtures: **10 passed**. This confirms the committed host-approval and refusal tests without changing the active tree.
- No full regression was run because implementation was blocked and no production code changed. `git diff --check` passed after the documentation updates.

## Changes and preservation

Only these documentation paths changed for this increment:

- `TASKS.md` — records the 003B blocker and retains U-ARENA-003 as open/blocked.
- `docs/tasks/encounter-engine.md` — documents the exact Run-only host-approval boundary and the approved next decision.
- `docs/reports/U-ARENA-003B-report.md` — this investigation report.

Starting state was branch `main`, HEAD `49bce3898f047dd57591a5240bd16b5305d9580c`, with an empty index. The user-managed state already contained 44 tracked documentation deletions and 867 untracked files, including the supplied assignment. No code, tests, NPC data, saved JSON, receipt registries, encounter state, or unrelated files were modified. A documentation-only commit, `b3b8e5bd611abdb912cb3be9f33135900045d55d` (parent `49bce3898f047dd57591a5240bd16b5305d9580c`), records exactly the two task-status files and this report. At that commit, the index was empty; the 44 tracked deletions and 867 user-managed untracked files remained. Nothing was pushed.

The missing working-tree copy of the handoff was read from the committed `HEAD:docs/handoffs/universe-6-to-7.md`; it was not restored. The read-only r60 source remains present in the worktree.
