# U-ARENA-004O — Native hex facing and transactional orientation

## Result

Implemented and committed the bounded twelve-way facing and orientation foundation in Universe. The change does not choose an initial facing for generated Beings, expose facing in the Arena browser, or add arrival, collision, body geometry, pathfinding, or perception rules.

The starting checkout was `<LOCAL_HOME_PATH>`, branch `main`, at `87d4203` (`main...origin/main [ahead 24]`). Existing unrelated tracked deletions and untracked files were preserved and not staged. The implementation commit is `8d6f607415e650d205d8f4a44ab45b635dc7ecad` (`Add transactional native hex facing`). No push was made.

## Adopted rules and native sources

- Adopted Encounter r61 Facing (`docs/encounters/encounters-working-draft-adopted-r61.md:724-738`) establishes six side and six point facings, a front sector bounded inclusively by the adjacent headings, one-second facing changes that may coincide with movement/actions, ordinary forward movement toward the front, and a one-hex-per-second ordinary limit in other directions. The movement-rate section at `:557` independently sets the ordinary one-yard-per-second limit while performing another demanding Action.
- Revision 62 adds no facing rule relevant to this slice. Revision 63 (`docs/encounters/encounters-consistency-decisions-r63.md`, reflected at r61 file `:5` and coordinate rule `:308`) preserves full-precision metric Cartesian Reality and says the hex mapping does not quantize movement.
- `src/arena_hex_map.py` documents the existing flat-top map, one yard between opposite horizontal edges, odd-column north offset, and vertex coordinates using angles `0, 60, ... 300` degrees. It provides presentation occupancy, not collision authority.
- `src/object.py:114-115` retains historical `top_facing=0` (“up”) and `front_facing=1` (legacy six-direction comment). Neither field is repurposed. There were no native consumers using them as a twelve-way orientation.
- `RunAction` in `src/activities.py:76-151` records and reports Encounter-supplied displacement; it does not generate movement. Its co-resolution is not treated as another demanding Action.

## Facing representation and classification

`BeingInstance.hex_facing` is the single new native facing value. It is `None` until explicitly authored and otherwise a validated integer 0 through 11 when set with `set_hex_facing`. Legacy `front_facing` and `top_facing` remain unchanged. No random or generated default is inferred.

`src/hex_facing.py` defines the implementation convention: counter-clockwise in 30-degree increments from world +x; even indices face a hex vertex and odd indices face a side normal. This matches the flat-top lattice axes. The zero axis and integer encoding are local conventions, not additions to the adopted rules. The module deliberately supplies no nearest-facing or destination-rounding function.

A movement vector is classified at full Cartesian precision by its horizontal dot product against the authored facing vector. Front includes the two adjacent headings at ±30 degrees; all remaining directions are `non_forward` for this movement cap. A small 16-ULP tolerance makes computed boundary vectors deterministic and inclusive. There is no finer flank/behind movement-rate mapping in this slice because r61 applies the same ordinary cap to directions outside the front.

`MovementIntent` now names `facing_policy="maintain"` or `"turn"`. Maintain requires known facing, derives the sector from the continuous displacement, and caps non-forward motion at 1 yd/s (0.9144 m/s), combined with any lower fatigue, load, posture, or explicitly supplied concurrent-demanding-action limit. A turn requires a caller-authored valid `target_facing`; movement must lie inside that target’s front sector. Unknown facing, malformed facing, absent target, and incompatible turn/vector pairs fail closed. No automatic facing is selected for arbitrary destinations.

## Transaction and observer behavior

The transactional movement coordinator passes a scoped facing-update map with the velocity into `prepare_interval_candidate`. The staging adapter validates that each orientation belongs to a participating Being with nonzero staged movement in the same interval. The endpoint fence uses the proposed orientation to build the common post-movement, pre-Action snapshot. Publication adds the Being facing write to the existing movement phase and inverse journal beside Cartesian position. Thus co-resolving Actions see the committed-boundary orientation, and a publication failure restores both facing and position.

A regression uses an explicitly authored northward target facing and movement with a pending Run observer. It captures the shared snapshot and verifies that it contains the new facing, verifies the native facing and displacement commit together, and verifies Run succeeds on the displacement. A fault injected after the movement publication phase verifies position, facing, pending lifecycle, unresolved Action, RNG cursor, Awareness, and Encounter time are restored before explicit recovery. The player projection remains on its existing allowlist and exposes no facing or opponent state.

## Persistence and scope limits

The general closed Being checkpoint inventory, binding adapter, and reconstruction adapter now include the facing value, including explicit `None`. This changes that checkpoint inventory: older payloads lacking the required field are not silently upgraded. General save/replay support remains separate. The narrower combined reproduction/Being checkpoint still only accepts pristine Beings with unknown facing; it now rejects a known orientation instead of dropping it. Its round-trip and fail-closed behavior are covered by a test.

Generated Arena initialization leaves `hex_facing` unknown, so generated destination movement remains refused until an initial facing is lawfully authored. The work does not infer that the visible map footprint is body clearance, or that a destination can be reached safely. Terrain and hampering along a path, posture provenance, broad demanding-Action classification, clearance/collision, destination arrival, and any initial-facing policy remain unresolved. No browser movement route or automatic turn selection was added.

## Verification

Commands below ran from the repository root. `.venv/bin/python` is required here: system `python` could not import the installed `npcgen`, so its first exploratory movement-suite invocation stopped during Arena fixture setup (16 setup errors). The project environment contains `npcgen` at `.venv/lib/python3.14/site-packages/npcgen`.

| Command | Result |
|---|---|
| `time .venv/bin/python -m unittest discover -s tests -p 'test_movement_intent.py' -q` | 16 tests passed; 2.978 s wall |
| `time .venv/bin/python -m unittest discover -s tests -p 'test_atomic_publication.py' -v` | 70 tests passed; 40.686 s wall |
| `time .venv/bin/python -m unittest discover -s tests -p 'test_transactional_progression.py' -v` | 61 tests passed; 30.822 s wall |
| `time .venv/bin/python -m unittest discover -s tests -p 'test_action_evaluation.py' -v` | 47 tests passed; 0.521 s wall |
| `time .venv/bin/python -m unittest discover -s tests -p 'test_arena_hex_map.py' -v` | 4 tests passed; 0.062 s wall |
| `time .venv/bin/python -m unittest discover -s tests -p 'test_reproduction_being_checkpoint.py' -q` | 13 tests passed; 1.692 s wall |
| `.venv/bin/python -m py_compile src/being.py src/hex_facing.py src/movement_intent.py src/action_evaluation.py src/interval_staging.py src/encounter.py src/transactional_progression.py src/atomic_publication.py src/checkpoint_binding.py src/checkpoint_fields.py src/checkpoint_reconstruction.py src/reproduction_being_checkpoint.py` | Passed |
| `git diff --check` | Passed before implementation commit |

The checkpoint suites are not green in this checkout and were investigated because this change extends the Being checkpoint inventory:

- `.venv/bin/python -m unittest discover -s tests -p 'test_checkpoint_adapters.py' -v`: 42 tests, 22 errors and 4 failures. Most errors stop at the current strict Encounter adapter rejecting `arena_activation` and `arena_activation_enabled`; some tests then fail their expected downstream error text, and the suite also reports unrelated dangling-reference expectation mismatches.
- `.venv/bin/python -m unittest discover -s tests -p 'test_checkpoint_identity_binding.py' -q`: 10 tests, 8 failures, with the same strict Encounter-field rejection during fixture capture.
- `.venv/bin/python -m unittest discover -s tests -p 'test_checkpoint_reconstruction.py' -q`: 6 tests, 6 errors, with the same strict Encounter-field rejection.

These failures occur in Encounter inventory validation before the Being checkpoint field is serialized or reconstructed. The targeted reproduction checkpoint round-trip passes for unknown orientation and specifically verifies known orientation refuses.

## Committed implementation paths

Commit `8d6f607415e650d205d8f4a44ab45b635dc7ecad` contains:

- `src/hex_facing.py`
- `src/being.py`, `src/movement_intent.py`
- `src/action_evaluation.py`, `src/interval_staging.py`, `src/encounter.py`, `src/transactional_progression.py`, `src/atomic_publication.py`
- `src/checkpoint_binding.py`, `src/checkpoint_fields.py`, `src/checkpoint_reconstruction.py`, `src/reproduction_being_checkpoint.py`
- `tests/test_movement_intent.py`, `tests/test_reproduction_being_checkpoint.py`
- `docs/design/U8-Arena-destination-movement.md`

This report is committed separately after the implementation.

## Recommended next slice

Before enabling any generated-Arena destination control, decide how Arena creation lawfully establishes each Being’s initial orientation and authoritative per-interval terrain/posture/hampering premises. Then make a bounded native consumer use the new facing snapshot for an already adopted front-relative rule. Keep destination arrival and clearance disabled until their rules and geometry inputs are adopted. The browser should continue to expose neither destination movement nor facing state.
