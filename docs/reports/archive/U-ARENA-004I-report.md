# U-ARENA-004I engineering report

## Result

Implemented the target-free Arena activation rule explicitly adopted by the
request. A generated Arena can now activate its native Action timeline through
the first valid player Choice. The first supported Choice is deliberately
limited to a positioned participating actor's native, target-free `RunAction`.
The generated browser exposes **Choose Run** and **Advance 1 second** through
the U-ARENA-004F initialization path.

The activation record is `ArenaActionActivation` and contains Encounter ID,
actor ID, native Choice ID, activation time, and kind `first_player_choice`.
It has no target field. Activation does not call target-directed
`decide_to_act`, create Awareness, or record interpersonal intent. The existing
target-directed initiation and native Choice validation/start-fence protocols
remain in place.

## Native implementation and atomicity

Only generated initialization opts the Encounter into
`arena_activation_enabled`. `Encounter.activate_arena_for_player_action` checks
the opt-in, the unstarted state, participating actor, current start time, and
exact native `RunAction` type with `target_id=None`. The ordinary Action
contract and positioned-actor prerequisite remain active.

With an explicit native publication lease held before the schedule lock, the
method runs the ChoiceBook's normal proposal, validation, acceptance, and
publication operations. A narrow preparation flag permits the unstarted Arena
to validate the first target-free Action without publishing it or changing the
Encounter clock. Only after successful validation does it record activation,
accept the Choice, publish the Action at time zero, and select transactional
progression. The selection helper requires the same already-owned publication
lease, preserving the native lock order and avoiding nested/reentrant leases.

Invalid Choice preparation restores ChoiceBook counter, drafts, validation
tokens, choices, reservations, registrations, states and revision; it also
leaves activation, initiation, Event history, pending Actions, clock, Action
metadata and RNG unchanged. A test-injected failure after Action publication
exercises the rollback path and confirms the same externally visible state.
The guarantee follows the existing quiescent/coordinated-access ownership
contract; uncoordinated raw Python access is outside that native isolation
boundary. The browser additionally serializes all session reads/writes with its
session lock.

## Reproducible native result

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python examples/generated_arena_activation.py
```

The proof initializes a 0-XP, 5×5 candidate with seed `20261107`, accepts the
player's first target-free Run at time 0, and commits exactly one native second.
The committed result is `no_movement`; the player's native position remains
`(4.1148, 1.3716, 0.0)` meters. The Action itself observes displacement and does
not move its actor. No velocity, movement, path, geometry, perception, or
opponent decision is authored for this proof. Before and after the Choice, the
player has no Awareness; the ordinary `EncounterInitiation` remains `None`.

The generated browser session supplies its own candidate-seeded `RNGCursor`,
not a front-end timer or outcome. Its one allowed Advance calls native
`Encounter.step(1)` and displays the committed clock, native player position,
and Run outcome. It refuses further advancement in this bounded slice. The
player projection is allowlisted and omits opponent identity, opponent state,
Choice/activation records, target IDs, and Generator source data. Handler tests
exercise both routes in memory. No browser-rendering smoke test or loopback
server was run in this task, so no live-browser claim is made.

Generated Being geometry remains unsupported. Spot remains disabled, and this
activation contract does not change the U-ARENA-004H native Spot finding.

## Validation

Focused Arena/browser, geometry readiness, target-directed initiation, and Run
tests:

```sh
cd tests
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=../src:../examples ../.venv/bin/python -m unittest test_generated_arena_browser test_generated_arena_spot_readiness test_encounter_initiation test_running_action -v
```

Result: **28 tests passed in 5.242 seconds**. Coverage includes invalid Choice
preparation, an injected post-publication abort, generated player projection,
one committed native second, unchanged native position, no Awareness, hidden
opponent isolation, refusal of an extra second, explicit-geometry Spot
regressions, target-directed initiation, and existing native Run behavior.

Native transactional progression, ChoiceBook, and atomic-publication regression
command:

```sh
cd tests
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=../src:../examples ../.venv/bin/python -m unittest test_transactional_progression test_action_choices test_atomic_publication
```

Result from the same implementation: **188 tests passed in 67.342 seconds**.
The native activation contract's standalone suite also passed **3 tests in
0.571 seconds**. The full repository suite was not run. The environment emitted
pyenv rehash and `.venv` prefix warnings when invoked from `tests`; they did not
affect test results.

`git diff --check` passed after implementation. The executable proof above
completed successfully and printed `choice=executing`, `time_seconds=1`,
`run_outcome=no_movement`, unchanged player position, and the target-free
activation record.

## Recommendation for the next slice

Before claiming meaningful Arena movement, define or adopt an authoritative
player movement Choice/velocity rule and its native boundary semantics. Then
extend the generated session only through that rule. Keep the activation record
target-free and leave Spot blocked until generated Being geometry is supplied
by an adopted native mapping.

## Repository and commit evidence

The checkout had pre-existing unrelated tracked deletions and untracked work
before this assignment. Those paths were preserved and not staged. No
`npc-generator` files were modified and nothing was pushed. Only scoped
Universe implementation, tests, executable proof, design contract, and this
report were committed. Implementation commits are `ebf2e76` (native target-free
Choice activation and publication rollback) and `67995cb` (generated browser
Run/Advance loop and safe projection). This report is committed separately
after those verified implementation commits. The final checkout has no
task-owned uncommitted changes; the pre-existing unrelated deletions and
untracked files remain.
