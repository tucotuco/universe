# Universe 8 → Universe 9 handoff

**Prepared:** 2026-11-10

**Universe 8 Arena feature commit:** `21f1dc9a83afb8f84d854a5f53c24822bbdf9862` — `Complete Arena NPC profiles and starting kits`

**Local branch at audit:** `main`, tracking `origin/main`; 113 commits ahead at the time of review

**Publication:** Not pushed. The review found machine-specific absolute local paths in older committed Arena reports. Publishing the current branch would expose those paths. History was not rewritten or force-pushed.

## Universe 8 / Arena 008 capabilities

- Directly generate Beings through the installed `npcgen` Python library. Preserve the complete canonical, validated NPC Generator v2 record per Being, including fields Arena does not yet simulate. Keep that initial specification distinct from evolving native Encounter state; reload never regenerates a saved Being.
- Show the full source specification in the owning player's character details. Opponent source facts remain hidden; the player receives only observer-authorized evidence.
- Select bundled ground-loadout profiles and upload local JSON in Generate Encounter. The checked-in fixtures cover an empty profile, the mixed starter profile, every supported sword type, and deterministic selection of one supported type from each of the 19 native weapon dictionary groups. Profile selection, chosen types, ground Object IDs, placement, and observer evidence survive versioned Save/Load.
- Default browser generation starts both Beings with separate, real native equipment Objects. Initial Dagger hand state and armor custody use native `possessions`, `weapons`, `body_parts`, and `armor_id`; the explicit unequipped mode remains available. Ground Objects stay ground Objects.
- Retain Arena movement, native one-second progression, exact adopted position truncation, observer-specific perception, Pick up, two-second Draw where its prerequisites are represented, and deterministic transactional Save/Load for pending and completed Actions.

## Architecture and adopted boundaries

- `npcgen_arena_adapter.py` owns the boundary from Generator output to a native Being. It validates the installed engine identity and full source schema, maps only supported native fields, records the original profile, and retains unknown-to-Arena source fields without claiming they drive simulation.
- `arena_loadout_profiles.py` handles a closed, bounded profile vocabulary and seeded per-group selection. `arena_initial_equipment.py` contains the explicit Universe-owned initial kit preference policy. The NPC Generator has an `arena_ready_being` API, but that API accepts caller-provided catalog, anatomy, and kit policy snapshots; it does not define the Universe's equipment policy or claim effects. Integration of that API is the immediate next milestone.
- Native Encounter state and native Object identities remain authoritative after generation. Session display names and observer-owned evidence are presentation/knowledge state, not replacement identities or omniscient browser inventory.
- Ordinary ground Pick up does not assign a weapon location or imply readiness. Normal weapon Draw takes two seconds where the native hand and drawable location prerequisites are explicitly present. Initial Arena Dagger readiness is represented as starting native state, without fabricating an Action receipt.
- No collision, body geometry, pathfinding, undocumented hand-count inference, class combat bonuses, or new defensive values were introduced. Only Dagger is used for the initial one-handed ready state because other weapon types lack a native hand-count contract. Armor preference tiers are Arena policy inputs, not adopted combat rules.
- The sibling `npc-generator` repository was not changed.

## Verification at handoff

- Focused integration/regression batch: **108 tests passed in 69.891 seconds**. It covered Arena initialization, native ground Objects, persistence, shipped browser JavaScript and HTTP/session integration, the NPC Generator adapter, Draw, Pick up, checkpoint activation/admission, observer-perception checkpointing, all profile/kit tests, and hex-map behavior.
- `py_compile` on changed Python sources/tests and `git diff --check` passed for U-ARENA-008.
- A real-browser smoke generated the bundled sword profile, selected and uploaded a local all-swords profile, generated the seeded 19-group profile, moved through the native browser pathway, downloaded a Save, stopped/restarted the server, loaded the downloaded file, and continued the same movement plan to boundary 2.
- `git fsck --full --no-reflogs` exited 0. It reported dangling objects; no repository objects were rewritten or pruned.
- The U-ARENA-008 feature changes are committed in the feature commit above. The working tree also contains unrelated tracked deletions and untracked content. Preserve those; they were not included in the feature commit.

## Git publication finding

The local branch was `main`, upstream `origin/main`, remote `origin` was the Universe GitHub repository, and the local branch was 113 commits ahead of its tracking ref. The reviewed commit range contains the Arena v1-to-008 development chain. The working tree has unrelated deleted historical documents and untracked files; they were not staged.

Before publication, scan results found machine-specific absolute paths in committed historical reports, including `docs/reports/U-ARENA-004A-report.md`, `docs/reports/U-ARENA-004O-report.md`, `docs/reports/U-ARENA-005E-report.md`, `docs/reports/U-ARENA-005F-report.md`, `docs/reports/U-ARENA-005H-report.md`, `docs/reports/U-ARENA-005I-report.md`, and `docs/reports/U-ARENA-005J-report.md`. Other earlier Arena reports contain temporary absolute checkout paths. No credential/key-pattern match or generated binary artifact was found in the reviewed range. Because normal push would publish all 113 commits and those local paths are already embedded in their history, the milestone was not pushed. Cleaning the existing history requires a separate explicit history-redaction plan; this handoff does not rewrite it.

## Immediate next milestone: integrate `npcgen.api.arena_ready_being`

Use the completed Generator API to produce a versioned initial equipment specification for each generated NPC. Define and review Universe-owned catalog/anatomy/policy snapshots, validate the returned placement and ownership semantics against current native definitions, then translate accepted units into native Object IDs and `BeingInstance` state. Preserve exact source records, actual class XP/skills/Strength inputs, determinism, legal hand occupancy, native armor references, and all Save/Load bindings. Keep the Generator API's `mechanics: null` guarantee intact: do not infer combat effects, hand counts for uncatalogued weapons, protection, or past Actions. Compare the API-backed kit with the current documented Arena preference policy before removing or retaining that policy.

Do not resume broad equipment-policy guessing. First deliver this bounded adapter and deterministic compatibility tests, then review the policy inputs with the NPC Generator owner if their existing API contract is insufficient.
