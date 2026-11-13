# U-NPC-BEING-004 — Generated initial HP mapping

## Status

**Complete for the exact hash-pinned `npcgen-npc` v2 fixture.** Source evidence supports mapping the generated HP value into the native Being's initial current HP. This does not establish a general maximum-HP or Hit Dice contract.

## Source evidence and semantic boundary

The fixture remains byte-exact at SHA-256 `e59b55a6c22f822d65716215b64bccf0c1f2c7a42d49036092580d7c470241ae`. Its canonical `state.hps` and derived `sheet.hit_points` are both integer `23`.

Read-only inspection of `../npc-generator-web` established:

- `npcgen/engine.py` calls `hit_points()` as part of new-NPC generation (`figure_it`, lines 134–155). `hit_points()` (lines 466–487) computes one total from class-level Hit Dice rolls and configured Constitution adjustments and assigns it to the single `NPC.hps` field. The NPC model has one `hps` value (`npcgen/models.py:64`); it has no separate maximum HP, current HP, injury, or damage-history field.
- `npcgen/persist.py:90` renders `sheet.hit_points` directly from `n.hps`; `record()` persists the full NPC state as authoritative and the sheet as a projection (`persist.py:102–118`). Thus the fixture value is the generated character's starting HP value, not a damage-adjusted current value.
- Native `BeingDefinition.hit_points` is stored as the definition's HP value (`src/being.py:33–44`). `BeingInstance` copies the definition into `current` (`src/being.py:350–356`, with `ObjectInstance` also initially copying it at `src/object.py:111–117`). Consequently, using the value creates a native Being whose initial current HP equals the source-generated HP.

The producer's integration handoff still labels HP mapping as needing verification and cautions against assuming equivalence. This increment closes only the fixture-specific initial-value mapping from producer implementation evidence; it does not revise that external handoff or claim a universal NPC-to-Universe rule.

## Implemented mapping

`src/npcgen_being_adapter.py` now requires `state.hps` to be a nonnegative integer and requires `sheet.hit_points` to be an integer exactly equal to it. Missing, null/unresolved, boolean, fractional, negative, or inconsistent values refuse before registering a Being. The verified value initializes `BeingDefinition.hit_points`, so both the new Being's original definition and initial current HP equal `23`.

The terminal and browser developer views distinguish:

- Tobe's source-derived initial HP (`state.hps`) and live native current HP;
- the opponent's Arena-authored initial/current HP (10).

The committed Action display remains sourced from native inspection. In the fixed seeded scenario the boundary-4 Dagger Thrust remains `normal`, causes 4 body damage to the opponent, and leaves opponent HP at 6. Tobe remains at 23 HP. No NPC equipment, Hit Dice, class/level/XP, race, age, possessions, or damage history is imported.

## Changed files and verification

- `src/npcgen_being_adapter.py`
- `examples/npc_being_arena.py`
- `examples/npc_being_arena_web.py`
- `tests/test_npcgen_being_integration.py`
- `tests/test_npc_being_arena.py`
- `tests/test_npc_being_arena_web.py`
- `TASKS.md`
- `docs/tasks/encounter-engine.md`

Focused command, run from `tests/` with loopback permission for the two HTTP tests:

```sh
PYTHONPATH=..:../src:../examples python -m unittest \
  test_npcgen_being_integration test_npc_being_arena \
  test_npc_being_arena_web test_melee_combat
```

Result: **17 tests passed in 3.038 seconds**. Compilation passed for the changed Python modules/tests, and `git diff --check` passed. The runnable terminal example was also exercised; it printed source-derived initial HP 23, native current HP 23, the Arena-authored opponent HP 10, and the committed boundary-4 outcome/damage above. The full regression suite and unchanged long Ari/Bex persistence HTTP suite were not run, as the assignment directs.

## Remaining limits and next data needs

This is a narrow mapping of the producer's generated HP scalar to native initial current HP. It does not map native maximum HP (the native model does not establish that interpretation here), source Hit Dice, ongoing damage/injury, class or level semantics, XP, or class/race-derived combat rules. A broader importer should require explicit producer fields and documented semantics for maximum versus current HP, damage state, Hit Dice, and the ruleset mapping rather than infer them from `hps`.

## Commits and preservation

- Implementation commit: `7e01d2fb9d0dec4d5fc38118f77ff11ae02796ed`, parent `d2c87738a1293ceed4096ef22dcfd543d09dab19` (`Map generated NPC initial hit points`).
- The report is committed separately; its commit ID is returned in the execution summary.
- No push was performed. The index was empty after the implementation commit.
- At task entry, the checkout was `main` at `d2c87738a1293ceed4096ef22dcfd543d09dab19` with an empty index, 44 tracked documentation deletions, 18 untracked path entries, and the pre-existing Arena example modification that this task necessarily extended. No unrelated path was staged.
- Additional unrelated documentation changes appeared during the work. After the implementation commit, status showed 46 tracked deletions and 19 untracked entries, including two more `docs/encounters_adopted_r60/` deletions and an untracked r61 draft. At final verification, status showed 59 tracked deletions and 19 untracked entries: 13 more adopted-r60 documentation deletions and an untracked `docs/encounters/` directory had appeared. All such files were left untouched. There are no remaining modified tracked files, the staged index is empty, and `git diff --check` passes.
