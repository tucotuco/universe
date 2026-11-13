# U-NPC-BEING-002 — Externally generated Being in a native Arena

## Result

**Complete for the bounded local developer scenario.** A single Enter in the new opt-in terminal Arena accepts one fixed native Dagger thrust by the fixture-derived Being. It uses the native Encounter ChoiceBook, transactional progression, committed inspection, and interval publisher. The default Ari/Bex Arena and S6/S7 persistence path were not modified.

## Fixture and source/native boundary

- Universe fixture: `tests/fixtures/external/npcgen-npc-native-skill-candidate.json`.
- SHA-256: `e59b55a6c22f822d65716215b64bccf0c1f2c7a42d49036092580d7c470241ae`; verified against the external NPC-generator fixture and the prior U-NPC-BEING-001 report.
- The digest pins the test input only. It is not producer authentication, an identity, or proof of rules compatibility. The fixture's complete original record remains available to the integration test; the developer display is a selected projection and does not print the full source record.

| Property | Provenance and handling |
|---|---|
| Name `Tobe` | Source `state.name`, cross-checked with `sheet.identity.name`; used as the native display name only. |
| STR 12, INT 11, WIS 16, DEX 12, CON 9, CHA 14 | Source `state.scores`, cross-checked against all six named `sheet.abilities.scores`, then mapped to native `Abilities`. Native FIT is 9 by the existing constructor's FIT=CON convention; it is not an imported source value. |
| `armed combat` 1 | Source acquired ordinary rank, checked against the configured native SkillDictionary. |
| Dagger 2 | Source acquired weapon rank, checked against configured native weapon data and passed through native `Skills.set_weapon_skill_level`. Native category propagation is derived, not claimed as separately acquired source ranks. |
| NPC definition's remaining required mechanics | Explicit generic test baseline: type `npcgen fixture baseline`, length 1.7, weight 70, HP 10, `1d8`, Neutral, AC 11, challenge rating 1. These values are Arena scaffolding, not NPC facts. |
| Arena scene and opponent | Arena-authored positions `(0,0,0)` and `(1.5,0,0)`, `Sphere(0.5)` geometry, DC 10, opponent HP 10/AC 11, and zero supplied Action strategy. |
| Weapon Object | A native Dagger is explicitly created, owned and equipped for this scenario. The fixture's possession list is not imported and does not supply a weapon. |
| Race, sex, age/category, class, level, XP, source HP, dimensions, possessions, family, psionics, seed and notes | Preserved in the source record only. No mapping was inferred. In particular, the source label High Elf does not become a native race, and source HP 23 does not replace the test baseline. |

The Arena uses the existing narrow `create_npcgen_v2_native_being` adapter. It does not accept a user-selected source path, expose the whole record to observer endpoints, create source-derived practice/Action history, or claim a source-authored native Being identity.

## Operator flow and demonstrated result

From the repository root:

```sh
python examples/npc_being_arena.py
```

The terminal first shows a local omniscient developer view with source-derived values separated from Arena-authored setup. Press **Enter once** to submit the fixed Action. A second submission in the same scenario instance is refused before any time, receipt, or Target change. There is no arbitrary Action, target, file-path, or source selector.

The verified run used the scenario's fixed private RNG seed `72002` and produced:

```text
Fixture SHA-256: e59b55a6c22f822d65716215b64bccf0c1f2c7a42d49036092580d7c470241ae
Source-derived name: Tobe
Source-derived abilities: {'Str': 12, 'Int': 11, 'Wis': 16, 'Dex': 12, 'Con': 9, 'Cha': 14}
Source-derived acquired ranks: {'skills': {'armed combat': 1}, 'weapon_skills': {'Dagger': 2}}
Action=npc-being-arena/action/one-dagger-thrust Choice=npc-being-arena/encounter/one-thrust/draft/1 boundary=4
outcome=normal metadata={'distance': 1.5}
Target=npc-being-arena/being/opponent HP after=6 causal damage={'body': 4}
progression=transactional native receipt boundaries=(1, 2, 3, 4)
```

The operator sees the native committed outcome, Target HP and causal damage. Current committed Action inspection exposes the outcome and distance, but not the d20 result; the Arena does not reconstruct or display a guessed roll equation. The unchanged U-NPC-BEING-001 comparative test supplies the same deterministic roll 8 to native scenarios and verifies that Dagger rank 2 hits where rank 0 misses. The current melee path adds configured weapon rank and supplied Action strategy; this work does not implement the full revision-60 Armed Combat strategy-point pool.

## Changed files

- `examples/npc_being_arena.py` — separate terminal developer scenario, explicit scene setup, one-shot native transactional Choice, committed result display.
- `tests/test_npc_being_arena.py` — source/native display separation, fixed one-shot request, result, damage and native receipt assertions.
- `TASKS.md` and `docs/tasks/encounter-engine.md` — bounded U-NPC-BEING-001/002 completion records; U-ARENA-003 remains open.
- `docs/reports/U-NPC-BEING-002-report.md` — this report.

No source adapter, shared combat/Encounter primitive, browser endpoint, checkpoint module, fixed Ari/Bex flow, or external project was modified.

## Verification

Baseline evidence from U-NPC-BEING-001 at starting HEAD `8405d0b4fcac336dbd5c587f969ce482e09b5c41`: the existing adapter/melee/Encounter focused selection had **14 passing tests**.

Post-change focused command from `tests/`:

```sh
PYTHONPATH=..:../src:../examples python -m unittest \
  test_npcgen_being_integration test_npc_being_arena test_melee_combat \
  test_integrated_encounter test_npc_encounter_arena
```

Result: **27 tests passed** in 7.679 seconds. Python compilation passed for the new example and test.

Unchanged Ari/Bex local checkpoint/persistence regressions:

```sh
PYTHONPATH=..:../src:../examples python -m unittest \
  test_arena_local_checkpoint test_arena_s7_checkpoint test_arena_state_activation
```

Result: **15 tests passed** in 84.194 seconds, including the existing loopback HTTP flows. The example was also run directly with one newline piped to its single Enter prompt; it produced the boundary-4 native published result above. `git diff --check` passed.

The full ~1,761-test HTTP-inclusive suite was **not run**, per the assignment's fast-verification policy. U-ARENA-003C3 remains the last full-suite baseline; it is not a full-regression claim for this increment.

## Commits, preservation, and remaining work

- Implementation commit: `2baaf602698bf0b57615d856e87f7e1aa77c4dd5` (`Add opt-in NPC Being melee Arena`).
- Report closeout commit is separate and its hash is given in the completion response.
- No push. The external `npc-generator-web` repository was read-only; its fixture and handoff were not modified. BattleCode, `legacy/`, saved sessions and fixed Ari/Bex persistence files were untouched.
- Existing pre-task work was preserved: 44 tracked documentation deletions and 18 untracked path entries. Only the four implementation/task-document paths above and this report were committed; no user-managed deletions or unrelated untracked paths were staged.

The last bounded display limitation is that committed inspection does not retain the attack roll, so the Arena reports the actual native outcome/effect, not a reconstructed arithmetic trace. Unsupported NPC source fields and full r60 strategy allocation remain separate decisions. A later, separately scoped increment could add this source/native panel to the loopback Arena without widening the fixed S6/S7 checkpoint contract.
