# U-NPC-BEING-001 — External NPC to native Being integration

## Result

**Accepted for the bounded fixture.** The byte-exact `npcgen-npc` v2 fixture was validated, used to create a real native `BeingInstance`, and its configured Dagger rank affected an actual native `MeleeStrike` resolved by `Encounter`. This is a narrowly scoped consumer-side adapter, not a general importer or a claim that all NPC-generator fields share Universe semantics.

## Source fixture and provenance

- Source path: `tests/fixtures/external/npcgen-npc-native-skill-candidate.json` (copied byte-for-byte from the independent `npc-generator-web` fixture).
- SHA-256: `e59b55a6c22f822d65716215b64bccf0c1f2c7a42d49036092580d7c470241ae`.
- The checksum pins the test input only. It is not producer authentication, a native Being identity, or proof that the producer's rules hash matches Universe rules.
- The integration test keeps and compares the complete original bytes and parsed source record. The adapter does not store generator history, class XP, family, possessions, or other source data as native mechanics.

## Field mapping

| Source field | Result | Boundary |
|---|---|---|
| `state.name` | Native display name `Tobe` | Must equal `sheet.identity.name`; not an ID or uniqueness guarantee. |
| `state.scores` | Native STR, INT, WIS, DEX, CON, CHA | Cross-checked against the six named `sheet.abilities.scores`, then passed to native `Abilities`. Native FIT follows the existing constructor convention of FIT = CON; no Fitness value is imported. |
| `state.skills.skills["armed combat"] = 1` | Native acquired ordinary rank 1 | Validated against the configured native `SkillDictionary`. |
| `state.skills.weapon_skills["Dagger"] = 2` | Native Dagger rank 2 | Validated against configured native weapon definitions and installed through `Skills.set_weapon_skill_level`; ordinary native weapon-category propagation remains derived. The adapter does not label propagated ranks as separately acquired. |
| Required Being mechanics absent from a verified source mapping | Test-only native definition defaults: generic fixture type, length 1.7, weight 70, HP 10, hit dice `1d8`, Neutral alignment, AC 11, challenge rating 1 | Explicit test setup only, not facts imported from the NPC. |
| Race, sex, age/category, class, levels, class XP, source HP, height/weight, possessions, family, psionics, seed, notes and producer metadata | Retained only in the original source record; not mapped to native state | No exact approved native mapping was demonstrated. In particular, “High Elf” is not converted to a native race and a Dagger skill does not grant a Dagger. |

The integration test explicitly creates and equips a native Dagger for the test. The source NPC's possessions are not used. Imported ranks are initial conditions; the import creates no Action, skill-use record, practice XP, or source-derived native ID. The native Being receives its own identity from `BeingInstance`.

## Native Action evidence

The test creates the imported Being in a Universe registry, adds it to an Encounter, provides an explicitly test-owned native Dagger, establishes the ordinary awareness/decision prerequisites, and schedules a native `MeleeStrike` thrust. With the same die roll of 8 against DC 10, the imported Dagger rank 2 produces a normal hit (`8 + 2` meets DC 10); a same-ability native control with Dagger rank 0 misses. The hit damages the target through the existing melee resolution path. This demonstrates the imported rank is read by native Action resolution.

The test uses the existing native Encounter/MeleeStrike fixture path. It does **not** claim revision-60 Armed Combat strategy-point allocation: the current native melee path adds the weapon rank and supplied Action strategy, and this test uses the default zero strategy. No combat or Encounter rules were changed.

## Changed files

- `src/npcgen_being_adapter.py` — narrow schema/rank validation and native construction helper.
- `tests/fixtures/external/npcgen-npc-native-skill-candidate.json` — exact external fixture copy.
- `tests/test_npcgen_being_integration.py` — source integrity, native field mapping, refusal, and real melee comparison tests.
- `docs/reports/U-NPC-BEING-001-report.md` — this report.

## Verification

Baseline focused tests, before implementation:

```sh
cd tests
PYTHONPATH=../src:../examples python -m unittest test_melee_combat test_integrated_encounter
```

Result: **14 tests passed**.

After implementation:

```sh
cd tests
PYTHONPATH=../src:../examples python -m unittest test_npcgen_being_integration test_melee_combat test_integrated_encounter
python -m py_compile ../src/npcgen_being_adapter.py test_npcgen_being_integration.py
cd ..
git diff --check
```

Result: **17 tests passed**; compilation and whitespace checks passed. Per the assignment's fast-verification policy, the full HTTP-inclusive suite was not rerun; the last broad baseline remains the 1,761-test U-ARENA-003C3 result and is not represented as a full-suite result for this change.

## Commits and repository preservation

- Implementation commit: `b22390017688d629ee8248737cc50e4506d43d5d` (`Import bounded NPC skills into native Being`).
- Report is committed separately as a documentation-only closeout; its hash is stated in the completion response.
- No push. The independent NPC-generator repository was read only; no BattleCode, legacy, saved-session, or other project files were touched.
- At task start and after the implementation commit, the pre-existing worktree consisted of 44 tracked documentation deletions and 18 untracked path entries, with no other modifications. Those deletions and untracked paths were preserved. No unrelated paths were staged.

## Remaining producer and consumer work

**NPC producer:** document/version mappings for race, age, source ability ordering/ranges, physical units, class/level/XP, HP, and possession semantics before consumers can import them. Its age-based skill-budget policy remains provisional and is not an adopted Universe progression rule.

**Universe consumer:** expand only after field-by-field semantic approval. This adapter currently refuses unknown acquired skill names/ranks and does not import race, age, class, XP, HP, equipment, family, or psionics. Native Being defaults are explicit fixture scaffolding, not an interchange contract. The existing melee path also does not calculate the complete revision-60 strategy-point pool.
