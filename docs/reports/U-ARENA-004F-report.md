# U-ARENA-004F — Atomic two-Being Arena initialization

## Result

Implemented a bounded backend initialization path in `src/arena_initialization.py`. It accepts an exact nonnegative integer starting-XP value, integer map width and height of at least five cells, and a deterministic integer root seed. It creates a fresh, unpublished `Universe`, obtains two independently generated and validated native Beings from the installed `npcgen` library, assigns each to a distinct initial one-yard cell, constructs a native `Encounter` at time zero, and returns the candidate only after both Beings and the Encounter are registered in that private Universe.

The first role is recorded as `player_controlled`; the second as `arena_controlled`. These are candidate metadata only. The Encounter has no scheduled Action and no Awareness entries. The result retains each full canonical Generator source record as bytes, its SHA-256 digest, installed engine identity and skill-resolution status, selected candidate seed, all attempted/rejected seeds, role, native ID and cell/metric-position binding. Native UUIDs remain independently generated and are not promised to reproduce.

The U-ARENA-004F assignment content was supplied in the repository root as the untracked `U-ARENA-004F.md`; its header requests `docs/assignments/U-ARENA-004F.md`, which was not present at task start. I used the supplied file as the assignment and left it untouched. This report is at its requested path.

## Repository and package state

- Universe began at `57bb396` on `main`. The worktree already contained tracked deletions and numerous untracked user files, including the root assignment and other assignments/reports. These were preserved; only the paths named in the implementation commits and this report were staged.
- Implementation commits: `5e31b1a` (`Prepare npcgen Arena Beings without registration`) and `ce961e2` (`Add atomic two-Being Arena initialization`). The report is committed separately. Nothing was pushed.
- The adjacent read-only Generator checkout was at `9c36a2a` when inspected and already had unrelated dirty/untracked material. No Generator files were edited.
- The imported `npcgen` identity was `2.1.0`, rules hash `sha256:78e8a2bc8e7dc7ba635f8ab6d8bdf8174c35608c9af04b6533cc3d84c46865ff`. Import was through the existing local Universe `.venv` site-packages package entry, which resolves to the adjacent Generator source checkout. The implementation uses `from npcgen import api`; it does not copy Generator code, invoke a CLI, or edit the Generator checkout. A deployable pinned package installation remains an environment/release requirement.
- U-ARENA-004D remains separate: it concerns equipment Actions. This increment creates no Objects, equipment, protection, or loadout state.

## Construction and validation

`prepare_npcgen_arena_being` is the minimal U-ARENA-004E adapter refactor. It still performs the prior record, identity, exact-XP, class-slot conservation, age-skill status, native dictionary, race-template and rank checks, but leaves the constructed Being detached. The existing `generate_npcgen_arena_being` API now calls that preparer and retains its prior registered behavior. Unresolved skill refusals additionally carry source age metadata and a structured `age_unavailable` flag derived from the Generator's explicit “no starting-skill age class” reason.

For both roles, the coordinator always requests `cost_modifiers="character"`. Exact requested XP is passed unchanged. Each selected source record must satisfy the existing adapter's exact XP and class-XP-sum checks and have a resolved age-derived profile. It imports only those resolved ranks. It neither turns unresolved profiles into empty skills nor reinterprets Generator classes, levels, age rules, or skills. Starting `skill_experience`, practice baselines and skill-use history remain empty.

Only `unsupported_native_race` and `skill_profile_unresolved` are retryable. Each role receives at most 32 attempts. Malformed/corrupt records, identity mismatch, missing package/dictionaries, API numeric-domain refusals, and other integrity failures stop immediately as terminal failures. Exhaustion uses the exact high-XP diagnostic, `The starting experience is probably unreasonably high. Try reducing the XP value.`, only when every failed attempt for that role explicitly reports the Generator age category has no starting-skill age class. Other exhaustion has a distinct `candidate_retries_exhausted` refusal and does not claim XP is too high. Failure details retain attempt seeds and refusal classifications.

The seed algorithm hashes a versioned namespace, canonical installed engine identity, root seed, purpose, role index and attempt index with SHA-256 to produce each candidate seed. Placement has a separate `placement` namespace and seed; a private `random.Random(placement_seed)` samples two different indices from the implicit rectangular cell range. The map footprint is sparse metadata, not an allocated cell array, and is capped at 1,000,000 cells. Neither the module-global Python RNG nor the Encounter RNG is used or advanced.

Cell `(0, 0)` is the southwest/lower-left cell. X increases east, Y north, and Z is up. A cell center `(column, row)` becomes the continuous native Cartesian point `((column + 0.5) * 0.9144, (row + 0.5) * 0.9144, 0.0)` meters. The native position retains full floating precision; the map is initialization/presentation metadata and does not quantize later movement. No geometry or facing is assigned. Native Encounter construction succeeds at `t=0` without a map or geometry, so no staged proof or unsupported Sphere rule was needed.

Both Beings are prepared before registry mutation. The candidate is assembled in a fresh Universe that is not returned until both Beings and the Encounter are present. If the second candidate fails, the partially prepared first Being remains detached and the local candidate Universe is discarded; no existing caller Universe/session is accepted or mutated. This is an atomic return boundary, not persistent publication or save support.

## Race subset and operating limits

The adapter currently maps only the five exact Generator race names `Human`, `Grey Elf`, `High Elf`, `Wood Elf`, and `Half-elf` to unique case-insensitive native `BeingDefinition.obj_type` matches. No aliases or invented templates are added; the other Generator races may be rejected and retried. This is a provisional subset and does not represent the full Generator race distribution. The installed Generator's supported starting-XP numeric range remains authoritative (currently through `2**53 - 1`); a larger value is refused by Generator and is not clamped.

The returned candidate contains two native Beings and one native Encounter, with exact XP, age-derived initial skills, provenance, role metadata and initial cell placement. It does not include non-Being Objects, equipment, AI, automatic Awareness, a player-visible observation layer, GUI, generalized save/load, or a claim that the Encounter is playable. Rules identity and Generator source records are in-memory candidate provenance; persistence and observation policy remain later work.

## Reproducible proof

Run from `tests/`:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=../src:. ../.venv/bin/python ../examples/arena_initialization.py
```

With root seed `20261107`, the executable proof completed at both 0 and 12,000 XP on a 5×5 map. Each case selected two supported Beings within seven total role-attempt records, retained two distinct source hashes, put the native Encounter at time zero, and placed the Beings in distinct cells `(4,1)` and `(4,2)`. Their positions were respectively `(4.1148, 1.3716, 0.0)` m and `(4.1148, 2.286, 0.0)` m. Re-running the same root seed, inputs and engine identity reproduces the records, attempt history and cells; the executable prints newly assigned native IDs, which are expected to differ.

The focused tests also verify exact native XP at zero and positive XP, resolved rank import, empty practice history, distinct IDs/source records, deterministic retries and placement, retry bounds, retryable versus terminal errors, the age-related exhaustion diagnostic, no partial registration when the second candidate fails, map/input limits, and unchanged module-global RNG state.

## Verification

- Adapter-only regression before the coordinator commit: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=../src:. ../.venv/bin/python -m unittest test_npcgen_arena_adapter` from `tests/` — **5 passed**, 0 failures, 0 skips (0.196 s).
- Final focused plus adjacent regression run from `tests/`: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=../src:. ../.venv/bin/python -m unittest test_npcgen_arena_adapter test_arena_initialization test_npcgen_being_integration test_skill_experience test_action_resolution_experience` — **28 passed**, 0 failures, 0 skips (0.856 s).
- Executable proof: the command above completed both 5×5 examples successfully.
- `git diff --check` and staged-diff checks were clean before commits. A full Universe suite was not run. Python printed existing pyenv shim and venv-prefix warnings for the tests-directory invocation; they did not affect the results.

## Next smallest playable integration slice

Implement one bounded player-controlled interaction against a supported native target: first define and validate the candidate's player-visible observation boundary, then expose only authorized Being state and one already-supported native Action choice through that boundary. Keep equipment, generated loadouts and AI out of that slice. Before calling it playable, verify its Action prerequisites and resulting native state against the authoritative Encounter rules, and keep the Arena candidate unpublished until the interaction setup is complete.
