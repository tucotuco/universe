# U-ARENA-004L — Ground movement inputs in native state

## Outcome

The U-ARENA-004K rate evaluator now reads the Being-derived inputs that native
Universe state can establish: race, Fitness, Strength, canonical Run skill
rank, physical fatigue level, and represented carried weight. It validates the
Run skill against the existing native dictionary before interpreting an
absent Being rank as zero. The installed config was already correct; no config
or Generator change was needed.

The generated-Arena integration test now uses `GeneratedArenaSession.generate`
and its approved target-free `choose_run()` path, then supplies a
test-premised one-second `MovementIntent` to the existing native transactional
Encounter. It commits 0.9144 m at the t=1 boundary, after which the co-resolving
native Run Action reports success. Movement still happens before Action
resolution. The test premises establish this one fixture only; generated
browser movement remains disabled.

## Source-grounded movement-input table

| Input | Classification | Native evidence and current handling |
| --- | --- | --- |
| Race | Native-derived | `BeingInstance.current.race` (`src/being.py`); r61 names the supported race groups in the sprint formula (`docs/encounters/encounters-working-draft-adopted-r61.md:546`). Unsupported race names refuse. |
| Fitness and Strength | Native-derived | `BeingInstance.FIT()` and `.STR()` read current abilities (`src/being.py:672-712`). r61 applies fatigue ability adjustments; `src/exertion.py` provides the adopted per-PFL adjustments. The evaluator adjusts these abilities before sprint and heavy-load calculations. |
| Run definition | Native-derived configuration | `src/config/skills.tsv:18` already defines lowercase `run` as `True/True` (ordinary/progressive), matching r61's Run heading (`...adopted-r61.md:2367-2373`). `src/skill.py:131-148` uses case-sensitive names. The prior 004K “missing Run” finding came from looking up uppercase `Run`; the configured skill is lowercase `run`. |
| Run rank | Native-derived | `BeingInstance.get_skill_level('run')` reads the Being's native skill state (`src/being.py:732-740`). A missing rank (`None`) is treated as rank zero only after the native dictionary definition is verified. A missing/malformed definition refuses. The Arena Generator's initial absent rank remains absent, with no fabricated XP or practice history. |
| Physical fatigue level (PFL) | Native-derived | `BeingInstance.get_fatigue_level()` (`src/being.py:545-555`) is the discrete PFL used by r61. `src/exertion.py` holds the matching ability adjustments and maximum categories. The separate Q/B `PhysicalFatigueState` is not substituted for PFL. |
| Encumbrance | Native-derived for represented native gear | The helper deduplicates IDs in native possessions, weapons, held body parts, and armor; resolves Object weights and represented container contents; then sums finite nonnegative pounds. Sources: `src/being.py:359-365,762-820`, `src/object.py:22-35,104-119,247-248`, and r61 customary units (`...adopted-r61.md:351`). Empty references produce known 0 lb. Missing IDs or weights refuse. |
| Posture | Not yet modeled | Native `States` is an open boolean map (`src/states.py:26-54`); `src/config/states.tsv` includes `prone`, but no adopted mapping from those flags to standing/crouching/lying is implemented. A missing state is not treated as standing. Supplied explicitly in the test fixture. |
| Direction/facing | Not yet modeled for movement vectors | `ObjectInstance` has integer `front_facing` and `top_facing` fields (`src/object.py:114-118`), while r61 defines facing on six hex sides/points and rate limits in hex directions (`...adopted-r61.md:724-740`). No native mapping connects those fields to the Arena's continuous Cartesian vectors. Test supplies forward alignment; runtime does not infer it. |
| Terrain and hampering | Not yet modeled | r61 defines the Terrain and Hampered Movement tables and MMR factors (`...adopted-r61.md:557-606`), but the generated Arena has no authoritative terrain/environment map. The current interval's environment adapter is explicitly a no-op (`src/interval_staging.py:720-724`). The test supplies Plains/Road multiplier 1.0 and unhampered multiplier 1.0. |
| Concurrent demanding Action | Not yet classified | The Encounter/ChoiceBook records accepted and pending Actions, but native Action contracts have no universal demanding/non-demanding field. r61 caps ordinary movement at 1 yd/s during another demanding Action (`...adopted-r61.md:557`). The test expressly premises that its co-resolving Run Action is demanding; no production classification is inferred. |
| Path clearance/body geometry | Not yet modeled | Native `SpatialState` has position only, and generated Being geometry is absent. The test explicitly declares a clear corridor; it does not infer clearance from empty cells or participant reference positions. No geometry, collision, occupancy, or path check was added. |
| Destination arrival | Not yet modeled | `prepare_movement_intent` continues to refuse a destination reachable within the requested second. No stop, clamp, pass-through, partial-second, or repeat-until-arrival behavior was added. |

### Common pre-action snapshot

`action_evaluation.capture_snapshot` freezes participant race, abilities,
skills, states, legacy fatigue level/adjustments, position, possessions,
weapons, armor, and body-part references. It now also includes represented
inventory objects and transitive contents, with their native weights and
`parent_container_id` references (`src/action_evaluation.py:293-380`). During
`step_transactionally`, `prepare_movement_intent` receives this exact common
pre-action `EvaluationSnapshot`; the rate evaluator reads Being values and
carried mass from that frozen frame before movement staging. A focused test
changes live gear weight after capture and verifies the computed load remains
the captured 1.5 lb. The snapshot still does not classify demanding Actions or
provide posture, direction, terrain, hampering, or corridor clearance. Those
remain required explicit conditions or test-world premises. Snapshot
preparation and movement evaluation do not alter clocks, positions, RNG,
Action Choices, or Awareness.

## Source changes

- `src/action_evaluation.py`: extends the common snapshot to include native
  possession, weapon, held-item, armor and container-content closure, including
  the fields required to resolve represented load consistently.
- `src/transactional_progression.py`: supplies the boundary's common
  pre-action snapshot to movement preflight; movement ordering remains before
  Action resolution.
- `src/movement_intent.py`: added `NativeMovementInputs` and
  `derive_native_movement_inputs`; use canonical lowercase `run`; check that
  the loaded dictionary defines it as ordinary/progressive; distinguish
  missing rank (0) from missing definition (refusal); derive encumbrance from
  native equipment references and weights; derive fatigue adjustments from
  the native PFL table. Caller conditions no longer accept an asserted load
  value.
- `tests/test_movement_intent.py`: now tests the loaded Run config, absent
  rank versus absent definition, unchanged generated rank/experience/practice
  state, native object-weight load, fatigue-adjusted rate, the generated
  session activation and one-second movement proof, allowlisted public
  projection, unchanged RNG, and atomic refusals.
- `docs/design/U8-Arena-destination-movement.md`: records the corrected Run
  config finding and native input derivation.
- No changes to `src/config/skills.tsv`, Arena UI routes, Encounter ordering,
  NPC Generator, or adopted rules.

## Executable integration evidence

The test-world setup is explicit in `tests/test_movement_intent.py`:

- Generate two Beings with seed `20261107`, starting XP 0, and a 5x5
  presentation map; use the generated player and its native Encounter.
- Set test-only reference positions to `(0,0,0)` and `(0,100,0)` meters. The
  fixture separately declares the segment from `(0,0,0)` to `(20,0,0)` clear.
  The remote reference point and empty grid cells are not treated as proof of
  clearance, and no body volume is defined.
- Supply explicit test-only Plains/Road and unhampered factors (1.0), standing
  posture, forward alignment, and demanding-Action status for the co-resolving
  Run Action. These are not production defaults or native inferences.
- Verify generated Being native inputs: Elf, Fitness 14, Strength 13, Run
  rank absent/zero, PFL 0, and empty represented possessions/weapons/armor/
  held-item inventory. Native mass therefore resolves to 0 lb.
- Select walk (1.75 yd/s); the fixture's demanding-Action premise caps the
  interval to 1 yd/s. The Encounter commits `(0.9144, 0, 0)` meters before the
  Run Action resolves success at t=1.
- Confirm the public browser projection still contains only its player
  allowlist (no opponent identity/state), and that both global RNG and the
  session's Arena RNG cursor are unchanged.

Rate tests also set rank 3 through the native skill API in a test-only fixture
and verify the one-foot-per-second-per-level increment. A native Brick
instance weighs 1.5 lb and is included in the derived load; at STR 13 that
reduces unencumbered MMR by the r61 `(2*HL-E)/(2*HL)` factor. A PFL 2 fixture
verifies the corresponding Fitness/Strength ability adjustments and jog
ceiling. No test changes Generator skill output or practice history.

The refusal test snapshots time, position, event history, pending Actions,
ChoiceBook state, public projection, Arena/global RNG, and Awareness. Unknown
terrain, possible within-second arrival, and a stale boundary all refuse with
those values unchanged.

## Verification

Focused and adjacent commands/results:

```sh
# Repository root
.venv/bin/python -m unittest tests.test_movement_intent tests.test_arena_destination_movement_blocker tests.test_arena_target_free_activation tests.test_generated_arena_browser -v

# Working directory: src/
../.venv/bin/python -m unittest discover -s ../tests -p 'test_transactional_progression.py' -v
../.venv/bin/python -m unittest discover -s ../tests -p 'test_action_evaluation.py' -v
../.venv/bin/python -m unittest discover -s ../tests -p 'test_running_action.py' -v
../.venv/bin/python -m unittest discover -s ../tests -p 'test_encounter_spatial.py' -v

# Repository root
.venv/bin/python -m py_compile src/movement_intent.py src/action_evaluation.py src/transactional_progression.py tests/test_movement_intent.py
git diff --check
```

The final focused Arena group passed **24 tests** in **4.469 s**. Adjacent
regressions passed: transactional progression **61** in **28.784 s**;
snapshot/action evaluation **47** in **0.389 s**; RunAction **8** in **0.065
s**; Encounter spatial **10** in **0.056 s**. The groups contain **150 unique
targeted tests** after accounting for overlap; the full suite was not run.
`py_compile` and `git diff --check` passed. The Python environment emits
pyenv rehash and sys.prefix warnings, but all listed commands exited 0.

An intermediate focused run failed because the snapshot test initially called
`capture_snapshot` before its required positive integer pre-action fence. The
fixture now establishes boundary 1, and the final focused groups above pass.

## Remaining movement decisions and next slice

Still required before a generated Arena destination UI can be enabled:

1. **Facing/direction:** define an adopted mapping from native orientation to
   continuous movement vectors and front/back/side rate limits.
2. **Arrival:** decide how interval movement ends at or crosses a selected
   destination and how a revised/stopped target takes effect.
3. **Clearance:** adopt body geometry, occupied-space, obstacle/path handling,
   and any Grab/Hold movement interactions.

Also provide an authoritative Arena terrain/hampering source, posture model,
and a native demanding-Action classification before removing those explicit
test premises. The smallest next GUI-capable slice should first bind these
facts into a read-only native movement-context snapshot and prove them on
authored geometry; only then can the browser submit the accepted one-second
intent. Do not add ETA, speed indicators, or client-side rate/path decisions.

## Git and preservation

The checkout started with unrelated tracked documentation deletions and
untracked handoff, design/report, saved-example, legacy, and workspace
materials. They were preserved and were not staged. Task changes are limited
to `src/movement_intent.py`, `src/action_evaluation.py`,
`src/transactional_progression.py`, `tests/test_movement_intent.py`,
`docs/design/U8-Arena-destination-movement.md`, and this report.
Implementation commit: `2c80116`.

No push was performed. No changes were made in `npc-generator`.
