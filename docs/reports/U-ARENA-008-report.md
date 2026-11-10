# U-ARENA-008 engineering report

**Status: Complete.** The generated Arena now retains the complete `npcgen-npc` v2 record for each Being, offers bundled and local-file ground-profile selection in Generate Encounter, and creates real native starting equipment for both Beings by default. Existing Pick up, Draw, movement, observer evidence, measurement truncation, and versioned Save/Load remain in place. The sibling `npc-generator` repository was not modified, and nothing was pushed.

## Outcome scorecard

| Assignment section | Result | Evidence |
|---|---|---|
| A. Complete NPC record and native integration | Complete | Exact validated source JSON and digest retained per Being, shown only in the owning player's expanded character details, persisted through Save/Load, and kept separate from evolving native state. |
| B. Ground profiles | Complete | Bundled empty, starter, all-swords, and seeded weapon-group profiles; browser selector, preview, upload, validation, and capacity refusal; ground Object identity and history preserved. |
| C. Armed and armored Beings | Complete | Browser defaults to equipped mode, with an explicit unequipped option. Both selected candidates receive real owned native Objects in native hand/armor state; visible status comes from observer-owned evidence. |
| D. Integration and browser acceptance | Complete | Actual browser profile upload and generation, native movement, browser Save download, server stop/restart, Load of that file, and continuation to the next native boundary. Focused native suites cover pickup/draw and pending/completed Action persistence. |

No unresolved adopted-rules decision was required. NPC Generator does not supply a default equipment distribution: its `arena_ready_being` API expects caller-owned catalog, anatomy, and policy inputs, and its output expressly does not claim equipment effects. Universe therefore uses a small versioned Arena preference policy and native definitions; it does not attribute that policy to Generator rules.

## Source record and native mapping

For each candidate, the adapter retains the Generator's complete canonical JSON bytes, SHA-256, engine version/rules hash, and schema version. Save files preserve those bytes and reload validates them without calling `npcgen` or regenerating a Being. The mutable native Being/Objects, committed Actions, and native histories remain authoritative after generation. Current source schema changes fail closed.

| NPC Generator field | Arena/native treatment |
|---|---|
| `format`, `schema_version`, `engine` | Retained exactly in the source record. Engine identity and schema are validated on generation and restore. |
| `generation` (seed, mode, starting XP, skill resolution) | Retained exactly; the accepted starting total and skill-resolution status also enter the closed Arena initial profile. The live native Being's XP is the exact generated total. |
| `edits` | Retained as source history; not replayed during Save/Load. The generated record already contains the resulting state. |
| `state.name`, `race` | Native Being name and a uniquely matched native race/type template. Session display-name changes remain separate. |
| `classes`, `levels`, `xps` | Exact per-slot class ID/name, level, and class XP stored in the initial profile; total XP maps to native experience. No class combat feature is inferred. |
| Six `scores` | Native STR, INT, WIS, DEX, CON, and CHA. Arena FIT follows the existing native mapping from CON; no extra Generator attribute is invented. |
| `hps` | Native current hit points. |
| `skills.skills`, `skills.weapon_skills` | Explicit acquired ranks map to native skill state. Native effective category ranks remain derived by native rules. No skill practice is synthesized. |
| `age`, `month`, `day`, sheet age/birthday | Exact source values retained. A validated age/category/birthday summary is available as initial profile data; no age-based policy was changed. |
| `height`, `weight` | Native length/weight use the adopted truncation toward zero to hundredths; the complete original floating-point values remain in source bytes. |
| `possessions` | Entire original structure retained. The installed `npcgen.api.arena_items` projection is consulted for exact supported typed items; only compatible typed armor/shields are eligible for the relevant initial placement. Unsupported, exchanged, magical, and noncombat source possessions are not silently converted. |
| `sex`, `subrace`, `exc_str`, `psionics`, `family`, Generator-derived strength/reaction/learning data, sheet sections, and `notes` | Preserved exactly in the full source specification. Fields without a valid current native representation are shown as source data only, not claimed as live Arena mechanics. |

The player's character details contain a disclosure of the entire retained source specification using text-only rendering. Opponent source records, skills, class/XP, abilities, and other hidden Being data are not projected to the player. The Arena initial profile is checked against the source record, and the source record is checked against its digest and supported schema on Save/Load.

## Profiles and ground Objects

The Generate Encounter controls include the profile chooser, local JSON upload, preview, and the separate starting-equipment mode. Upload accepts bounded UTF-8 JSON only, rejects duplicate keys and unknown schemas/types, and never accepts paths or executable content. Both the existing NPC Generator profile format and the closed `universe-arena-ground-loadout-profile` v1 are supported. A too-large selected profile is refused before candidate generation with the exact required distinct-cell and total-cell capacity.

Checked-in profile fixtures:

| Fixture | Contents |
|---|---|
| `tests/fixtures/arena/empty.json` | Explicit zero ground Objects. |
| `tests/fixtures/arena/starter.json` | Existing NPC Generator mixed starter profile, retained unchanged. |
| `tests/fixtures/arena/all-swords.json` | One each of the 11 distinct ordinary sword types discovered dynamically from the native `Swords` category. |
| `tests/fixtures/arena/one-random-per-weapon-group.json` | One reproducibly selected supported type for every one of the native weapon dictionary's 19 object groups, using profile seed `2026008`. |

The random profile samples actual `object_categories` groups, not effective skill/category aliases. Its selected type and group rows, seed, and profile digest are stored in scenario provenance. Profile Objects are distinct native instances placed on unique ground cells. They are not added to a Being's inventory or equipment slots. Ground Object identity, custody, position, and observer evidence round-trip through Save/Load.

## Initial native equipment policy

Normal browser Generate defaults to **Class-appropriate equipped protagonists**. The user may choose **Unequipped protagonists** for tests. The authored two-second Draw scenario remains unready by design.

The Arena policy `universe-arena-class-xp-equipment/1` is intentionally a preference policy, not combat law:

1. Use the ordinary native Dagger: its one-handed status is the supported Draw premise already adopted for Arena. Record an acquired Dagger skill rank when present; otherwise use it as a low-weight fallback without granting proficiency. Other weapon types do not currently encode a native hand-count contract, so the initial kit does not infer that from their names or skills.
2. Prefer a supported armor type explicitly present in Generator's typed possessions. Otherwise use the highest actual Generator class level and native Strength as documented tier inputs: tier 0 selects Leather armor; tier 1 selects Studded leather armor; tier 2 selects Ring mail. Tier increases once for class level 2 or higher and once for STR 16 or higher, capped at tier 2.
3. Place the weapon only in a represented free native hand. Use a supported exact Generator shield only if a second represented hand is free. Refuse bounded candidate generation if a supported free hand is absent; do not assume anatomy.
4. Create ordinary native `WeaponInstance`/`ArmorInstance` objects with unique IDs, exact type keys, native weight, Being custody, `possessions`/`weapons` references, `body_parts` holding state, and native `armor_id`. No past Draw/Equip Action or history receipt is fabricated.

This policy uses the acquired Dagger rank where present, class allocation/level, XP-derived level, Strength, anatomy, and supported definitions. In a deterministic 1,000-XP example, a Ranger with STR 16 receives a Dagger and Studded leather armor, while a Mage with STR 15 receives a Dagger and Leather armor. Their kits are separate native Objects with different identities and actual holder/worn references. Armor definitions retain their native definitions; no defensive number or combat rule is fabricated. There is no standalone native encumbrance category to claim, so the sheet reports the actual represented carried weight and explicitly says when no category is stored. The native inventory view in the fixture example reported 21 lb for a 1 lb Dagger and 20 lb Studded leather.

The conservative boundaries remain deliberate: no unsupported race gets invented hands; no handedness, body fit, or strength threshold is claimed unless represented by the selected existing policy/definition; no Generator possession is silently substituted; and a ground Object never becomes owned or ready. Initial weapon readiness means the native hand/weapon references show that state; it does not create a Draw Action or grant a skill.

## Browser and persistence evidence

An actual Chrome session generated the bundled all-swords profile and showed all 11 ground sword types independently of the carried/worn starting kit. The opponent popup showed authorized presentation data and visible equipment status while class, age, abilities, skills, condition, and anatomy stayed unknown to the player.

In the actual in-app browser, the seeded 19-group profile preview matched the fixture selection and generated all 19 ground Objects. A checked-in all-swords JSON was then selected through the local file chooser; the browser reported successful validation, previewed 11 Objects, and generated that uploaded profile. A real map click submitted a native destination, and one-second advancement changed position from `(0.52, 2.28, 0)` m to `(1.43, 2.28, 0)` m.

The browser downloaded the Arena Save at committed boundary 1. I stopped the server, restarted it on a fresh ephemeral loopback port, loaded that downloaded file through Load Encounter, and continued the preserved movement plan through boundary 2 to the exact accepted destination `(2.11, 2.28, 0)` m. The restored page showed the same 19 ground Objects, carried equipment, observer-visible opponent, and pending destination before continuation; afterward it showed arrival and native time 2 seconds.

The existing versioned Arena Save/Load includes exact source NPC bytes, current native objects/equipment/inventory, profile selection and chosen random types, observer-owned evidence/history, pending/completed Actions, RNG/Choice state, and accepted movement plan. Existing strict field/schema validation rejects incompatible saves instead of regenerating NPCs or silently coercing records. Persistence tests cover repeated process-boundary continuation, movement, pending/completed Pick up, pending/completed two-second Draw, identity, custody, and Action history.

## Verification

| Command/check | Result |
|---|---|
| Final integrated Arena regression batch: initialization, ground objects, persistence, browser handler, npcgen adapter, readiness, pickup, activation, state admission, perception checkpoint, U-ARENA-008 profiles/kits, and hex map | **108 tests passed**, 69.555 s. |
| Browser/profile focused rerun after HTTP upload/catalog and generation marker coverage | **41 tests passed**, 12.618 s. |
| `tests.test_arena_complete_profiles_and_kits` after empty/starter profile-generation coverage | **5 tests passed**, 1.187 s. |
| `tests.test_arena_hex_map` | **4 tests passed**. |
| `python -m py_compile` for changed Python sources/tests | Passed. |
| `git diff --check` | Passed. |
| NPC Generator repository | Unmodified. |
| Push | None. |

Loopback binding was denied in the restricted sandbox with `PermissionError`. Following the narrowly scoped approved procedure, only the Arena server command was run outside that sandbox, bound to `127.0.0.1` on OS-assigned ephemeral ports, and the real-browser smoke succeeded. Ordinary development and test commands remained sandboxed.
