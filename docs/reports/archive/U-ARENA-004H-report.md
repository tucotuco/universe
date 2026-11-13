# U-ARENA-004H — Generated Arena Spot readiness

## Outcome

The generated browser remains **Generate-only**. No production geometry constructor or lawful target-free Encounter activation path is currently supported by the adopted rules and native APIs, so the Spot and Advance controls remain disabled. No application source, Generator source, production Being geometry, Awareness, or Encounter initiation behavior was changed.

Added a reproducible native success/failure Spot demonstration using explicitly authored **test-only** geometry and an explicitly already-initiated test Encounter. It proves the native six-second Spot, transactional boundary progression, result timing, owner-scoped Awareness, and location evidence behavior. The fixture is not evidence that generated Beings have that shape or that a generated user Encounter can legally start the Action.

## Baseline and inspected authority

- Universe began at `734f5e5` on `main`. Pre-existing tracked deletions and untracked user files were present and preserved. Only the test/example files and this report were staged. No push was made.
- Installed `npcgen` remains 2.1.0 with rules hash `sha256:78e8a2bc8e7dc7ba635f8ab6d8bdf8174c35608c9af04b6533cc3d84c46865ff`, imported through the existing local `.venv` site-packages entry linked to the adjacent Generator source. The Generator checkout remained at `9c36a2a` with pre-existing work; it was not modified.
- Read the 004F initializer and native adapter, 004G generated session/routes, `Encounter`, `EncounterInitiation`, `ChoiceBook`, `accept_spot_attention`, `SpotAction` resolution, transactional preflight, observer/location evidence projection, spatial geometry/visibility, and the adopted Encounter package README with r61, r62, and r63 documents.

### Geometry gate

The five exact native Being types the 004E/004F adapter supports are Human, Grey elf, High elf, Wood elf, and Half-elf. Their native definitions currently have `width=0`, `height=0`, and empty `body_parts`; the definitions have no Geometry3D field. The 004F adapter creates each Being with `geometry=None`. Generator records provide stature and mass, not a shape, horizontal extents, reference offset, opacity, or facing.

`BeingDefinition.length` is documented in the native source as stature in inches, while weight is pounds. Revision 62 uses stature in a reference-arm/Reach formula; it does not define body volume. Revision 63 preserves precise metric positions and explicitly adds no geometry inference. `ObjectInstance.set_geometry` requires a separately authored `Geometry3D`; it deliberately does not interpret definition dimensions as world geometry.

The existing `Sphere` and axis-aligned-box classes are geometry primitives, not body rules. A Sphere needs an authored radius and is centered on the Entity's position. An `AxisAlignedBox` needs three authored full dimensions, is aligned to global axes, and has no rotation model. Neither primitive specifies where a ground-positioned Being's volume begins, a visual/eye point, body opacity, or race-specific measurements. `visual_occlusion` is a separate property. `Encounter.line_of_sight` defaults to reference-position endpoints, excludes source and target volumes, and describes only modeled geometry; its `clear` result is not a complete vision determination. Adopted r61 Spot requires a physically possible unobstructed line of sight, so the native `SpotAction` refuses the generated target as `unmodeled_target` before rolling when its geometry is absent.

No complete, rule-supported deterministic geometry mapping exists for all five supported generated races. Production geometry remains absent.

### Initiation gate

An ordinary generated Encounter begins at `initiated=False`, `initiation=None`, and empty Awareness. `Encounter.decide_to_act` is specifically target-directed: it accepts only a participating Being actor, an existing participating target, and prior Awareness of that target, then records `(actor_id, target_id, intent, time)` as the first `EncounterInitiation`. Native action scheduling and `Encounter.step` both require `initiated=True`; selecting transactional progression also preflights an initiated Encounter. `accept_spot_attention` is target-free at its caller boundary and privately binds one unfamiliar Being, but only after transactional mode is selected. It does not provide an initiation path.

On a fresh generated candidate, the proof calls `decide_to_act(player, hidden_target, "Spot")` without Awareness: it returns `None` and leaves initiation false. Enabling transactional progression raises `IntervalIntegrityError` stating an initiated Encounter is required. `Encounter.schedule_action(SpotAction(...))` raises `RuntimeError: Encounter must be initiated before scheduling actions`. The refusal leaves time, boundary cursor, Awareness, events, pending Actions, ChoiceBook choices/drafts, progression mode, and module RNG unchanged. The player projection contains neither the hidden target ID nor its test-only sentinel name.

There is no existing native target-free activation API. Setting `initiated=True` directly or constructing `Encounter(initiated=True)` in production would bypass the adopted target-directed initiation contract. The product direction that choosing an Arena Action starts resolution without prior discovery is not yet represented by an explicit native initiation event or atomic API; it must be distinguished from `decide_to_act` before production integration.

## Reproducible test-only Spot demonstration

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python examples/generated_arena_spot_geometry.py
```

The demonstration generates a 0-XP, 5×5 candidate at root seed `20261107`, then copies the generated native definitions and starting positions into a fresh test Universe. This isolates each test from the original inactive Encounter's ChoiceBook ownership. It explicitly authors a 0.25 m Sphere centered at each test Being's supplied Cartesian position; this is a test premise, not a conversion from stature, mass, race, or grid cells. It sets the target DC to 1 for a guaranteed success and 100 for a guaranteed failure and uses a caller-owned `RNGCursor` initialized from `random.Random(5302)`; no `die_roll` is forced.

Each case constructs a native test Encounter at t=0 with `initiated=True` and empty Awareness, explicitly labeling the precondition as test-only. The existing `accept_spot_attention` adapter privately binds the target and accepts a native six-second `SpotAction`. Six native one-second `Encounter.step(1)` calls reach boundary 6. The executable prints:

```text
test-only DC 1: success; native t=6; resolved_boundary=6; player_awareness=1; location_evidence=1
test-only DC 100: failure; native t=6; resolved_boundary=6; player_awareness=0; location_evidence=0
Limit: explicit test geometry and an already-initiated test Encounter only; no production geometry or Arena initiation rule is implied.
```

The test verifies no Awareness or location evidence appears during boundaries 1–5; successful Spot publishes one observer-owned Awareness and a location record at boundary/time 6 with the exact native position; failed Spot publishes neither. The target does not become aware of the Spotter. The intent response contains no target or Action ID, and the Spotter's skill-practice state is unchanged (Spot awards no XP). The test-only Encounter uses the standard native resolver and transactional publisher; it does not simulate an outcome in browser code.

## Browser status and decisions needed

The U-ARENA-004G generated page remains empty until Generate succeeds, keeps the one-yard map and name fields, and still omits the hidden Being from player JSON. Spot remains disabled with the geometry-specific reason; there is no Advance button. We did not add a hidden Reality endpoint or make the success fixture visible through the production player projection.

Two decisions are needed before a Generate + native Spot slice can be enabled:

1. **Geometry:** Either adopt a deterministic per-supported-race Geometry3D contract with the primitive, all dimensions in meters, reference/ground-point offset, opacity semantics, and explicit facing/eye-point limitations, or keep generated Being geometry unmodeled and Spot unavailable until a separately supported perception rule removes that prerequisite. Stature alone is insufficient to choose horizontal dimensions or an origin.
2. **Activation:** Recommended: keep target-directed `EncounterInitiation` and `decide_to_act` Awareness-gated, and separately adopt a target-free Arena Action activation record/API that atomically starts the native timeline as the player's first Choice is accepted. Specify its fields, authority, timing, and publication/rollback behavior without recording or revealing the privately bound Spot target. Alternatively, retain existing initiation semantics and require an adopted incidental-awareness path before the player can choose a target-directed Action. No activation option was implemented here.

After both decisions, the smallest next implementation is an atomic native path that binds the adopted geometry, activates the Arena timeline according to the selected contract, accepts the target-free native Spot, and exposes only committed observer evidence. Until then the 004G UI must remain Generate-only.

## Verification

- Focused plus nearby regression command, run from `tests/`:

  ```sh
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=../src:../examples:.. ../.venv/bin/python -m unittest test_generated_arena_spot_readiness test_generated_arena_browser test_arena_initialization test_npcgen_arena_adapter test_attention_intent test_encounter_initiation
  ```

  **37 passed, 0 failures, 0 skips** in 10.935 seconds. This covers geometry absence across the five supported native race templates, uninitiated schedule/transaction refusals and atomicity, generated browser nonleakage/disabled controls, native test-only success/failure, existing 004F/browser behavior, attention-intent behavior, and native initiation regression.
- Runnable demonstration above: both native cases passed as reported.
- `git diff --check` was clean before commit. Python emitted the existing pyenv shim and tests-directory venv-prefix warnings.
- A localhost bind attempt using `ThreadingHTTPServer(('127.0.0.1', 0), ...)` failed with `PermissionError: [Errno 1] Operation not permitted`. Handler tests were run directly; no browser rendering or accessibility smoke test is claimed.
- An initial demonstration draft reused the same Being instances under the inactive 004F Encounter and a second test Encounter. Native transactional preflight correctly rejected cross-Encounter ownership. The final proof copies generated native definitions/positions into an isolated test Universe and passed without sharing those instances.

## Commits and final state

- `679c363` — `Add test-only generated Arena Spot readiness proof`
- The report is committed separately. No push or Generator change was made. Existing unrelated work remains preserved.
