# U-ARENA-009 engineering report

## Result

Arena generation now calls the installed `npcgen.api.arena_ready_being(...)` for each equipped participant and materializes only its validated versioned equipment units into native Object custody and Being state. The API output and the exact catalog, anatomy, and policy snapshots are saved with the Arena's initial-equipment provenance. Load validates and restores those records and native identities without regenerating a Being or equipment choice. Unequipped mode and the browser's independent ground-loadout pathway remain unchanged.

## Installed API contract

The installed package is `npcgen` version **2.1.0** (the Universe virtual environment resolves the `npcgen` package from the sibling checkout). The inspected call signature is:

```python
arena_ready_being(candidate, catalog, anatomy, policy, equipment_seed, rules=None) -> dict
```

It returns `npcgen-arena-ready-being` schema version 1. The payload embeds the complete `npcgen-npc` v2 source record; its equipment units include a source-local equipment identity, exact native type key, ownership, category, placement, readiness, rationale, and `mechanics: null`. It does not claim protection, combat benefits, skill grants, or past Actions. The API uses a local deterministic RNG from the supplied seed and snapshots; it does not reroll NPC generation or mutate global RNG. Invalid inputs raise its Arena-ready refusal. Universe validates the returned record and refuses unsupported output; it has no independent kit-selection fallback.

The API has no installed distribution metadata in this environment because it is resolved from the checked-out source package. `npcgen.__version__` and the candidate's engine identity report `2.1.0`. The sibling Generator worktree was not modified; its pre-existing deletion and untracked files were left untouched.

## Universe-owned snapshots and policy

The caller snapshots are built from Universe native dictionaries and the generated Being's validated state:

- **Catalog `universe-native-arena-equipment/1`:** the verified ordinary native Dagger with one represented hand, and the exact supported armor type selected by the existing Arena preference. Armor's API `worn_slot` is `armor_id`, the one existing native armor reference; no body geometry is inferred.
- **Anatomy `universe-native-arena-anatomy/1`:** the names of actually represented free hand slots, the available native `armor_id` slot, and no carry locations. Unsupported hand anatomy or an occupied armor reference fails closed.
- **Policy `universe-arena-class-xp-equipment/2`:** the existing preference for the supported Dagger and no inferred proficiency; one armor preference; no shields or sidearms; a required primary weapon; no fallback. Its class kit keys use the installed Generator class vocabulary. Class XP, class levels, Strength, and skills remain in the actual candidate supplied to the API, and the API's per-unit rationale records those candidate facts.

The pre-integration Universe policy chose Dagger regardless of proficiency, preferred an exact supported typed NPC armor possession when present, and otherwise used the highest actual class level and native Strength to select Leather, Studded leather, or Ring mail. That preference calculation now supplies the single eligible armor key in the caller policy snapshot. The API produces the versioned initial-equipment commitment; Universe no longer selects a second kit after receiving it. The existing source possession projection currently provides no supported native shield mapping, so this bounded catalog does not offer a shield. No shield selection is discarded or approximated.

The materializer validates every returned unit against the snapshot and exact native definition, creates one native Object per unit with a unique native ID, and applies only the output's represented held/readied hand state or `armor_id` reference. It refuses carried placements because Arena currently has no adopted native carry-location representation. No Actions, receipts, bonuses, or additional equipment effects are created. Ground profile selection and ground Object placement remain in their original separate path.

## Persistence and browser integration

The versioned Arena save now preserves, for each equipped Being, the exact API specification, all three input snapshots, equipment seed, and the mapping from source equipment IDs to native Object IDs. Existing native object/Being state remains authoritative. Save/Load validation checks API schema and snapshot digests, source-record equality, native object category and identity, custody, inventory membership, hand occupancy, and armor links. Loading does not call `arena_ready_being` or re-evaluate the Arena preference policy. A strict validator also continues to accept pre-U-ARENA-009 equipped save records in their original format, checking their native custody/hand/armor references rather than regenerating them. Unequipped saves contain no initial kit claim. Ground profiles, their seeded selection, and ground Objects remain separate and unchanged.

The existing browser Generate and HTTP/session path now reaches the API through native Arena initialization; no JavaScript or browser control changes were needed. The browser handler, Save/Load session integration, ground profiles, ground Pick up, and two-second Draw regressions passed.

## Verification

Focused command:

```text
PYTHONPATH=src:examples:../npc-generator .venv/bin/python -m unittest \
  tests.test_arena_initialization tests.test_arena_ground_objects \
  tests.test_arena_persistence tests.test_generated_arena_browser \
  tests.test_npcgen_arena_adapter tests.test_arena_ready_weapon \
  tests.test_arena_ground_pickup tests.test_arena_complete_profiles_and_kits \
  tests.test_arena_hex_map -q
```

Result: **95 tests passed in 43.412 seconds**. Coverage added or extended verifies two per-Being API calls with Universe snapshots, complete source-record preservation, deterministic API inputs and output for equivalent seeds, native unit identities/custody/hands/armor, explicit refusal for invalid API output, no API call for unequipped generation, and Save/Load preservation without calling the generation API. A migration-compatibility test loads and resaves a pre-U-ARENA-009 equipped record with generation disabled.

`py_compile` passed for the four changed Python modules and the changed test module. `git diff --check` passed. No full test suite or real-browser smoke was run; the shipped JavaScript and wiring were unchanged.

## Changed files and commit

Intended files:

- `src/arena_initial_equipment.py`
- `src/npcgen_arena_adapter.py`
- `src/arena_initialization.py`
- `src/arena_browser_session.py`
- `tests/test_arena_complete_profiles_and_kits.py`
- `docs/reports/U-ARENA-009-report.md`

No NPC Generator file was changed, and no push was performed. Existing unrelated dirty deletions and untracked content in the Universe checkout were preserved and not staged.

The integration and legacy-save compatibility are committed locally as **Integrate npcgen Arena-ready equipment**.

## Limitations

The installed API can represent held, worn, or carried units, but Arena has native mapping only for held weapons/shields and its single armor reference. This integration advertises only the currently supported Dagger and armor preferences and rejects any API output requesting an unsupported carry placement. Shields remain absent because the current NPC Generator typed-possession mapping does not produce a supported native shield unit. The API's equipment effects remain explicitly null; native armor definitions are retained without adding claims about new defensive effects.
