# U-ARENA-003B2 — Detached post-Spot Arena state candidate

## Result

Implemented a closed, versioned, immutable data candidate for the one supported Arena state: the native Ari→Bex six-second Spot succeeded and committed boundary 6. A separate Python process decodes the candidate and validates it against the exact U-ARENA-003A history-prefix digest and a separately host-accepted U-ARENA-003B1 read-only history view.

This is **not a checkpoint, trusted state, receipt authority, or live restored Encounter**. The B1 capability authorizes only the exact history prefix; it does not authorize the B2 state candidate. The candidate digest detects byte changes, not authenticity. No native entities are reconstructed, no receipt is issued or authenticated, and no Action can be scheduled or continued from this data.

## Changes

Implementation commit: `55f72eb942cdab35069b52ecd9d8d8570e28fe74` (`Add detached Arena state candidate`), parent `399a166caba84122b66d63149935197f09b3c177`.

- `src/arena_state_candidate.py` adds schema `universe.arena.detached-post-spot-state-candidate/1`, strict canonical JSON bytes, frozen public views, closed native-field/definition graph validation, exact two-NPC source-byte and native-identity bindings, six Target-owned boundary histories, the fixed Encounter/Universe/ChoiceBook state, six Q/B frames, and the captured RNG cursor state with its process-local limitation. Capture runs under coordinated read access and refuses unsupported fields, registries, participants, Actions, choices, geometry, history, or bindings.
- `examples/arena_state_candidate.py` commits the actual native Spot in process A. Process B decodes the history and state candidates, applies the existing B1 host policy to the history only, checks the state against both detached inputs, and prints identities, positions, `Sphere(0.5)`, HP, time/boundary, and Ari-only Awareness. It confirms that no Encounter, publisher, receipt, restoration or checkpoint-inventory capability is imported.
- `tests/test_arena_state_candidate.py` adds round-trip, immutability, native-state/RNG/receipt non-mutation, prefix and source binding, target chronology, tampering, schema, geometry, graph, open scheduling state, unknown native fields, populated ReproductionGroup registry, and fresh-process example coverage.
- `TASKS.md` and [the Encounter task document](../tasks/encounter-engine.md) mark only B2's detached candidate as complete. U-ARENA-003 remains OPEN/BLOCKED; live restoration and continuation remain unavailable.

The candidate includes current native Being fields and closed Human definition graphs, but it deliberately does not carry process-local publisher receipts, live native objects, ChoiceBook registration signatures, or restoration handles. The completed Choice/Action and Target consequences are described by the candidate and bound history claim. Receipt count is diagnostic only, not proof of issuance.

## Verification

Focused tests were run in an isolated `git archive` export of the starting HEAD with only the B2 candidate files and status updates overlaid. This kept the active moved/deleted documentation and all untracked work untouched.

- Focused Arena/checkpoint/Encounter/Spot command (10 test modules): **123 passed**.
- B2-only test module against the final committed implementation: **10 passed**.
- `PYTHONDONTWRITEBYTECODE=1 python examples/arena_state_candidate.py`: passed; process A committed the native boundary-6 Spot and process B decoded and validated the detached candidate.
- `python -m py_compile src/arena_state_candidate.py examples/arena_state_candidate.py tests/test_arena_state_candidate.py`: passed.
- Revision-60 generated-document checks: `generate_outstanding_todo.py --check` and `update_encounters_toc.py --check` both passed.
- `git diff --check` and the exact staged diff check passed.
- Full loopback-enabled `PYTHONDONTWRITEBYTECODE=1 sh run_tests.sh` in the isolated export: **1,737 tests ran; 2 failures and 10 errors**. The failures/errors are confined to the legacy reproduction explorer/what-if tests whose fixtures are under the explicitly excluded, untracked `legacy/src/data/` tree. Missing files prevent profile loading; one test consequently cannot reach its intended changed-digest assertion. The HTTP tests completed with loopback enabled. These unrelated legacy-fixture failures were not skipped, edited, or worked around.

The first sandbox-limited full-suite attempt could not bind loopback sockets and therefore was not used as the final HTTP result. The final full run used the assignment-authorized loopback permission. The independent legacy fixtures were not inspected or copied.

## Closure and limits

This closes only the detached state representation and cross-process semantic checks for the fixed post-Spot Arena fixture. It is not a complete persistence contract or claim that every possible Encounter field is portable. The captured RNG cursor belongs to its original process and has no portable ownership claim. Native receipt authentication and live history composition remain process-local. A future restoration increment needs a separately approved trust policy for the *state candidate*, reviewed identity-preserving native constructors/rebinding, and an explicit imported-history versus newly issued receipt design. It must preserve the existing B1 refusal boundary and must not reconstruct or register historical receipts from this candidate.

## Preservation and Git state

- Start: branch `main`, HEAD `399a166caba84122b66d63149935197f09b3c177`, empty index, 44 pre-existing tracked documentation deletions and 869 pre-existing untracked paths (913 status paths total).
- Implementation commit contains exactly the five paths listed above; its staged whitespace check passed. No push was made.
- After the implementation commit, HEAD was `55f72eb942cdab35069b52ecd9d8d8570e28fe74`, index empty, and the same 44 deletions/869 unrelated untracked paths remained. This report is committed separately; its commit hash and final HEAD are recorded in the completion message because a commit cannot include its own hash in its contents.
- The missing/moved documentation, legacy data, saved JSON, independent projects, and other untracked material were not restored, read, staged, or altered.
