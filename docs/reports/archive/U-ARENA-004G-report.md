# U-ARENA-004G — Generated Arena browser shell and first observer-safe Action

## Result

Added a generated Arena browser shell to the existing loopback presentation adapter, launched with:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python examples/generated_arena_browser.py
```

The shell starts empty. It offers exactly three generation inputs: starting XP, width, and height. Client-side enablement checks decimal digit strings and the minimums (XP ≥ 0, dimensions ≥ 5) without converting through JavaScript floating-point numbers; the server repeats exact-string validation and delegates Generator XP and map-area limits to the U-ARENA-004F initializer. A Generate request gets a fresh host root seed from `secrets.randbits(256)`, builds through `initialize_two_being_arena`, and swaps the active candidate only after complete construction succeeds. A failed request leaves the previous candidate object, names, time, and public projection unchanged.

The generated page displays the native time-zero Encounter, southwest-origin one-yard grid, controlled Being marker, editable Encounter display name, and editable player Being name. It visibly disables Load and Spot. It does not expose an Advance button, because the available Spot cannot resolve against the geometry-free generated Being. The result is **Generate-only**, not Generate + native Spot progression.

## Baseline and package

- Universe began at `815147d` on `main`. The starting worktree already contained unrelated tracked deletions and untracked user material; those paths remain untouched. Only the implementation files and this report were staged. No push was made.
- Installed package identity remains `npcgen` 2.1.0, rules hash `sha256:78e8a2bc8e7dc7ba635f8ab6d8bdf8174c35608c9af04b6533cc3d84c46865ff`. Universe imports it through the existing local `.venv` site-packages entry linked to the adjacent Generator source checkout. The Generator checkout was at `9c36a2a` with pre-existing unrelated changes; no Generator files were modified.
- Implementation reuses `examples/arena_web.py`'s loopback-only server and handler factory while keeping the previous fixed/checkpoint `ArenaSession` routes and page intact. A separate `GeneratedArenaSession` owns the candidate and its private provenance. The new launcher selects that session; the existing launcher continues selecting the old session.

## UI, projection and replacement behavior

The browser sends the three values as strings. The server accepts only ASCII decimal digit strings, rejects non-string numbers, decimals, missing/extra fields, under-minimum values and the initializer's map-area limit, and does not clamp. Generator numeric-limit errors are surfaced as Generator refusals, not relabeled as high-XP age errors. Correctly classified age-exhaustion advice from 004F retains its exact message.

The player endpoint returns only an empty/active state, Encounter display name and time, map dimensions/scale/origin, and the player's own display name and cell. It omits the second Being, all native IDs, source records and hashes, XP/class/skill data, Awareness internals, and private Action/scheduler data. The generated handler does not expose the old omniscient `/api/gm` route or old fixed-scenario Spot/Advance routes. The map is drawn on one canvas rather than allocating one DOM node per cell; grid lines are sampled to at most roughly 300 intervals per axis on large maps, while cell dimensions and native coordinates retain the U-ARENA-004F one-yard-cell semantics. The current initializer also caps the footprint at 1,000,000 cells.

Encounter and player rename requests update only the corresponding display-name fields. Tests confirm the native Being ID and retained Generator source bytes do not change. No undiscovered opponent name control is shown. The display name of a hidden second Being remains a product decision for a later operator/observer UI.

## Native Spot and progression finding

The existing native target-free `accept_spot_attention` adapter can privately select the unique unfamiliar participating Being and accept a native six-second `SpotAction` through the `ChoiceBook`. To check whether it was usable with an unmodified 004F candidate, a focused proof enabled the existing transactional Encounter path with its required native `initiated=True` precondition and caller-owned `RNGCursor`, accepted that native attention intent, and advanced six native `Encounter.step(1)` calls.

The 004F generated Beings have `geometry is None`. At boundary 6, the existing Spot resolver produced `unmodeled_target`, emitted no Awareness effect, and left the Spotter's Awareness empty. The Action therefore does not establish target identity or evidence for this generated candidate. The UI leaves Spot disabled with that reason and offers no empty-time advancement. No Sphere, arbitrary footprint, forced Awareness, client-selected target, fixed roll, or browser-side result was added. Native one-second progression itself worked in the proof, but that does not make the Spot interaction usable or justify exposing progression without a supported Action.

Initial passive perception remains unresolved: 004F starts with no Awareness, and this shell preserves that state. A successful future native Spot for generated Beings needs an adopted native geometry/visibility contract (or another existing supported evidence route) before the target can be revealed. General perception, uncertainty, Action recognition, and hidden-target renaming remain outside this increment.

## Verification

Final focused and neighboring command, run from `tests/`:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=../src:../examples:.. ../.venv/bin/python -m unittest test_generated_arena_browser test_arena_initialization test_npcgen_arena_adapter test_attention_intent
```

**26 passed, 0 failures, 0 skips** in 5.959 seconds. The tests cover empty startup, disabled Load/Spot controls, generated zero-XP native pair at time zero, map state, player-only projection and forbidden-field checks, strict inputs, under-limit and Generator-limit failures, atomic failed regeneration, name editing without identity/source changes, rejection of unsupported routes, legacy page selection, and the exact native `unmodeled_target`/no-Awareness proof. `git diff --check` was clean. The test executable emitted the existing pyenv shim and tests-directory venv-prefix warnings.

The first HTTP integration-test attempt could not bind `127.0.0.1`: `ThreadingHTTPServer` raised `PermissionError: [Errno 1] Operation not permitted`. Per the assignment fallback, the final route tests invoke the generated handler directly with in-memory request/response objects. No localhost server or browser session was successfully run, so this report makes no browser-rendering claim. An earlier combined invocation also omitted the `examples` entry from `PYTHONPATH` and produced two import errors; the final command above uses the corrected paths.

## Commits and next slice

- `03150c1` — `Add generated Arena browser shell`
- The report is committed separately.

The next useful bounded increment is to adopt and test the native geometry/perceptibility contract for generated Being definitions, without weakening the existing Spot visibility gate. Then repeat native success and failure cases with observer-owned evidence and only afterward enable the Spot/one-second controls. Keep passive initial awareness and any operator-only hidden-name editing as explicit decisions; do not infer them from the generated Encounter's existence.
