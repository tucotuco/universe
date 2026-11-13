# U-NPC-BEING-005 — NPC physical attributes to native Being

## Status: BLOCKED before implementation

The producer side establishes the fixture's stature and body-weight meanings, but the native consumer does not specify units or enough field semantics for a safe conversion. Neither source value is imported. The Arena remains unchanged: its generic Being length 1.7, weight 70, and `Sphere(0.5)` geometry are still explicitly Arena-authored.

## Fixture and producer evidence

The exact fixture was rechecked: `tests/fixtures/external/npcgen-npc-native-skill-candidate.json`, SHA-256 `e59b55a6c22f822d65716215b64bccf0c1f2c7a42d49036092580d7c470241ae`.

| Source field | Fixture value and type | Producer meaning/evidence |
|---|---:|---|
| `state.height` | `49.59000015258789` (`float`) | Generated individual stature. `npcgen/engine.py:279–285` derives it from race/sex average height values whose `config/rules/races.json:191–209` comment explicitly says inches, then applies the generated strength/random percent adjustment. The schema's state is authoritative; `persist.py:84–86` projects a rounded `sheet.age.height_inches` value. |
| `state.weight` | `46.8067626953125` (`float`) | Generated individual body weight. `npcgen/engine.py:287–295` computes it from race coefficient, generated height, sex, and a strength/random adjustment. `persist.py:84–86` explicitly presents the projection as `sheet.age.weight_pounds` (rounded to 46.81). |

These are properties of the generated NPC rather than abstract size-category labels. The external handoff at `../npc-generator-web/docs/integration/npc-to-native-being-handoff.md:17` correctly leaves their mapping to native `length` and `weight` unresolved. The NPC project was inspected read-only and was not changed.

## Native evidence and blocker

- `BeingDefinition` passes `length` and `weight` to `ObjectDefinition` (`src/being.py:33–44`). `ObjectDefinition` only calls `convert_to_numeric` and stores the values (`src/object.py:22–30`); it declares neither units nor whether Being `length` means stature, a particular body axis, or another historical measure.
- `ObjectInstance.set_geometry()` explicitly says definition dimensions are not interpreted as world-space dimensions because historical configuration units and body orientation are unspecified (`src/object.py:153–159`). Therefore mapping height to `length` would make an unsupported anatomical/orientation choice, and would not establish any collision shape.
- Native `src/config/beings.tsv` contains bare `length`/`weight` columns (for example, Human `5.75` / `170`) with no unit metadata. Such values look compatible with familiar historical conventions but are not a documented conversion contract. Native `weight` likewise has no declared unit in the constructor or accessor. Other Encounter rules that specify pounds for particular weapons or throwing limits do not establish the unit of every Being/Object weight field.
- The fixture's apparent numeric plausibility cannot resolve these missing contracts. Applying inches-to-feet, inches-to-meters, pounds-to-kilograms, or pounds-as-native-weight would each choose semantics not established by the native field definitions.

## Mapping disposition

| Attribute | Producer source | Native target | Disposition |
|---|---|---|---|
| Stature | `state.height` / `sheet.age.height_inches` | `BeingDefinition.length` | Not mapped: native length units and its anatomical meaning are unspecified; no geometry follows from it. |
| Body weight | `state.weight` / `sheet.age.weight_pounds` | `BeingDefinition.weight` | Not mapped: native weight units/interpretation are unspecified. |
| Geometry | No exact shape field | `BeingInstance.geometry` | Remains explicitly Arena-authored `Sphere(0.5)`; no body-shape inference is made. |

## Smallest decision needed

Before a consumer mapping can be implemented, establish for native Being definitions:

1. Whether `length` means an individual's stature and, if so, its canonical unit and anatomical convention; or whether it remains a generic historical dimension that cannot receive NPC stature.
2. The canonical unit and meaning of `weight` for a Being (body mass/weight and its unit), including any conversion rule from producer pounds.

The producer-side values already have documented inches/pounds presentation and generating source paths; no additional generator rule or new fixture is needed for this bounded case. A broader importer should update the external handoff/schema with stable units only after the native contract is established. Geometry remains a separate authored/modelled property.

## Verification and repository state

- At entry: branch `main`, HEAD `29df6b37c34ed4d6a7362035e9f2f489741c8753`, empty index; the unrelated working tree contained 59 tracked documentation deletions and 19 untracked path entries. These were preserved.
- Baseline command: `cd tests && PYTHONPATH=..:../src:../examples python -m unittest test_npcgen_being_integration test_npc_being_arena` — **4 tests passed in 1.338 seconds**.
- Fixture checksum and JSON runtime types/values were verified as listed above. `git diff --check` passed. No production code, test, fixture, producer file, task register, or Arena path was changed; this report is the only authored file.
- No post-change test run was needed because this was a blocked, documentation-only result. The full suite was not run.
- No task-status change was made: the mapping remains unimplemented pending native semantic decisions. The unrelated concurrent documentation work remains untouched.
