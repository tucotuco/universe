# U-ARENA-004M — Restore the adopted Arena hex map

## Result

The generated Arena now uses a flat-top regular hex layout. Opposite horizontal
edges are one yard (0.9144 m) apart; the across-points width is about 1.1547
yards. The UI renders six-sided polygons and places the player marker at the
current native Cartesian x/y coordinate. The displayed `(column,row)` address
is recalculated from that full-precision committed position on every safe
public-view read. The map projection never snaps, rounds, or writes native
position.

The native movement implementation and Encounter resolution pipeline were not
changed. Existing movement still commits continuous metric positions in its
usual movement-before-Action transaction. A focused authored-world proof moves
one generated Being one native second across a hex boundary and verifies both
that its derived address changes from `(0,0)` to `(1,0)` and that the exact
committed position is returned unchanged. The invisible second Being's
identity and position remain absent from the player projection.

## Adopted convention and geometry

Adopted r61 describes interlocking hexagons with a conventional one-yard
side-to-side distance for Encounters (`docs/encounters/encounters-working-draft-adopted-r61.md:540`).
Revision 63 preserves full-precision metric Cartesian coordinates and permits
hexes as a mapping convention without requiring whole-hex movement
(`...adopted-r61.md:308`). Facing remains a separate hex-side/hex-point rule
(`...adopted-r61.md:726-740`).

`src/arena_hex_map.py` defines the display lattice:

- Flat-top hexagons have horizontal top and bottom edges, with one yard
  between those opposite sides. Side length is `1/sqrt(3)` yards and
  across-points width is `2/sqrt(3)` yards.
- Stable addresses use odd-column offset coordinates. For column `q` and row
  `r`, the axial row is `r - floor(q/2)`. The metric center is derived from
  `x = side + q*(sqrt(3)/2)` yards and
  `y = 0.5 + r + (q mod 2)*0.5` yards; z is unchanged (initially zero).
- Six axial neighbor offsets are fixed. All neighbor center distances are one
  yard and their regular hex polygons share exactly two vertices, the two
  endpoints of an edge.
- The initial `width × height` footprint has exactly `width*height` addresses.
  `ArenaHexLayout.irregular(...)` represents finite missing-cell outlines;
  six-neighbor enumeration is independent of footprint membership so a later
  expansion can select edge neighbors without changing the coordinate model.
  Irregular public outlines are serialized compactly as per-column row ranges.
- Cartesian projection uses closed polygon membership with a documented
  `1e-12` yard comparison tolerance. Exact edge/vertex ties select the
  lexicographically smallest `(column,row)` among containing cells in the
  finite footprint. If no in-footprint polygon contains the reference point,
  the public occupancy is `null` and the UI says “outside map footprint.” The
  horizontal map projection ignores z; it does not claim vertical occupancy.

These are display and initialization conventions. A displayed hex address is
only the membership of one Being reference point in the 2D map layer. It does
not describe body volume, prohibit overlap, establish perceptibility, prove
collision clearance, or show that a vacant hex makes a path safe.

## Square-assumption inventory and correction

The prior generated implementation had square assumptions in these active
paths:

| Area | Prior assumption | Correction |
| --- | --- | --- |
| `src/arena_initialization.py` | Centers at `(column+0.5,row+0.5)` yards; no stagger; cell size represented a square yard. | Centers now come from the flat-top odd-column hex layout, converted to meters. Two distinct indices are still sampled from the same independent deterministic placement stream. |
| `src/arena_browser_session.py` | The initial placement address was returned forever as the Being's cell. | `player.cell` is derived from the live native position in the server-owned view; native position is serialized exactly. |
| `examples/arena_web.py` | Canvas drew orthogonal vertical/horizontal grid lines and centered the marker in the original square cell; labels called dimensions cells. | Canvas draws the six-edge polygons from server-provided geometry and compact footprint data; it plots the marker using native x/y. Labels now say hex columns/rows and explain the one-yard side-to-side measure. |
| `tests/test_arena_initialization.py`, `tests/test_generated_arena_browser.py`, `tests/test_movement_intent.py` | Expected half-yard square centers, static occupancy, or only axis-aligned movement. | Assertions now check hex centers, browser layout metadata/markup, a native boundary-crossing displacement, exact position preservation, and hidden-opponent isolation. New `tests/test_arena_hex_map.py` tests metric dimensions, neighbor edges, deterministic mapping, edge ties, outside points, and irregular outlines. |
| `docs/design/U8-Arena-v1-requirements.md`, `docs/design/U8-Arena-destination-movement.md` | Described square-yard cells and facing over square cells. | Updated active design language to the adopted hex display and left only the unresolved mapping of a Being's native facing onto the rendered orientation. |
| Historical `docs/reports/U-ARENA-004A-report.md`, `U-ARENA-004G-report.md`, and `U-ARENA-004J-report.md` | Earlier reports record the square-cell proposal/implementation as it existed then. | Kept as historical engineering records; this report supersedes their generated-map description. The fixed-scenario Arena and unrelated global spatial maps were not changed. |

Width/height request names, integer validation, minimums, one-million-cell
bound, generated candidate schema/provenance, native IDs, role assignments,
and atomic publication are preserved. The same root seed and source identity
remain reproducible, though the selected sampled indices now map through the
documented hex column-major address order, so old square-era coordinates are
not a compatibility promise.

## Executable evidence

With fixed root seed `20261107`, the initializer still builds two distinct
native Beings through its independent placement RNG stream. Each exact native
initial position equals the computed center of its selected unique map hex.
Repeated identical inputs reproduce candidate source records, attempt history,
placement seed, and addresses; the module-global RNG state is unchanged.

The one-second movement proof is in `tests/test_movement_intent.py` and is
explicitly test-only:

1. Generate the two-Being Arena, activate the player through the approved
   target-free native Run Choice, and set authored test reference positions.
   Start at the center of hex `(0,0)` and put the hidden second Being far away.
2. Explicitly premise a clear test corridor aligned to the adjacent `(1,0)`
   center. Also explicitly supply Plains/Road, unhampered, standing, forward,
   and demanding-Action rate conditions from U-004L. None of those premises is
   inferred from the hex map.
3. Submit the existing one-second native `MovementIntent` toward a distant
   destination along the center-to-center direction. The native step commits
   one yard of continuous displacement. The display projection reports
   `(1,0)` and publishes the exact committed x/y/z values without writing
   them.
4. Assert hidden identity, position, and Reality are absent from both
   player-facing JSON views; no Awareness or RNG state is created by the
   projection.

This test does not add GUI movement or movement behavior. It only uses the
previously authorized native movement path with explicit test-world premises.

## Verification

Commands and results:

```sh
# Repository root
.venv/bin/python -m unittest tests.test_arena_hex_map tests.test_arena_initialization tests.test_generated_arena_browser tests.test_movement_intent tests.test_arena_target_free_activation -q
# 33 tests passed in 4.738 s

# Working directory: src/
../.venv/bin/python -m unittest discover -s ../tests -p 'test_transactional_progression.py' -q
# 61 tests passed in 27.734 s
../.venv/bin/python -m unittest discover -s ../tests -p 'test_encounter_spatial.py' -q
# 10 tests passed in 0.054 s

# Repository root
.venv/bin/python -m py_compile src/arena_hex_map.py src/arena_initialization.py src/arena_browser_session.py examples/arena_web.py examples/arena_initialization.py tests/test_arena_hex_map.py tests/test_arena_initialization.py tests/test_generated_arena_browser.py tests/test_movement_intent.py
git diff --check
```

All **104 targeted tests** passed. `py_compile` and `git diff --check` passed.
The Python environment printed pyenv rehash and `sys.prefix` warnings during
the tests, but each command exited successfully. Handler and canvas markup
were checked through the browser test suite; I did not run an interactive
browser smoke test or bind a loopback server. The full repository suite was
not run.

## Limits and next slice

The square-grid display assumption is corrected, but hex occupancy remains a
reference-point projection only. Generated Beings still have no adopted body
geometry. This change adds no collision, pathfinding, terrain, awareness,
perception, or physical-occupancy rules. It does not infer a clear path from
empty hexes or alter movement rate/velocity.

Still open before destination movement can become a player-facing browser
feature:

1. Adopt how native six-side/six-point facing maps to continuous destination
   vectors and facing-relative movement-rate limits; no facing value or
   automatic turn is introduced here.
2. Adopt destination arrival, stopping, and target-revision behavior for
   continuous movement.
3. Adopt generated Being geometry and clearance/collision/path interactions,
   plus authoritative terrain/posture/hampering and demanding-Action inputs.
4. Only then expose a browser movement Choice backed by the native one-second
   transactional movement pipeline. Keep the current canvas read-only.

## Git and preservation

Implementation commit: `15539c8` (`Render generated Arena on adopted hex map`).
This report and the active design-document corrections will be recorded in a
separate documentation commit. Existing user-owned tracked deletions and untracked
handoff, design/report, saved-example, legacy, and workspace materials were
preserved and not staged. No changes were made to `npc-generator`, adopted
rule files, the historical fixed-scenario page, or global spatial systems.
No push was performed.
