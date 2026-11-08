# U-ARENA-004S — Ground combat Objects in the generated Arena

## Outcome

Implemented bounded native ground-Object construction and placement inside the private generated-Arena candidate. An explicitly authored test-only profile and typed fixtures create ordinary native weapons, armor, and shields. Objects receive distinct native identities and metric positions at distinct hex centers, while staying uncontained, unpossessed, unequipped, unheld, and outside the player projection. The existing Generate → destination → one-second advancement → exact-arrival path remains functional with these Objects present.

The requested assignment path `docs/assignments/U-ARENA-004S.md` was absent in this checkout; the assignment was present and completed as `docs/assignments/U-ARENA-004S-assignment.md`.

## Source contracts verified

- The installed sibling `npc-generator` source imports as `npcgen` version **2.1.0**, rules hash `sha256:78e8a2bc8e7dc7ba635f8ab6d8bdf8174c35608c9af04b6533cc3d84c46865ff`. Its importable signatures are `arena_loadout(candidate, profile, sampling_seed) -> dict`, `validate_loadout_profile(profile) -> dict`, `validate_loadout(payload, profile=None) -> list`, and `arena_items(npc, rules=None) -> dict`.
- `docs/arena-loadout.md` in that repository defines ordinary, nonmagical, typed weapon/armor/shield descriptions and a versioned caller-supplied profile. The profile validator rejects unknown/ambiguous fields and mismatched category keys. The API has **no built-in equipment distribution**. Repeated units are allowed, each gets a separate source-local `npcgen-loadout:...` ID, and records carry `ordinary=true`, `magical=false`, `mechanics=null`, `quantity=1`, and origin. Shields are descriptions that consumers map to native weapons in category `Shields`.
- The integration calls that API only when a caller supplies a profile, validates the profile before candidate creation, validates each generated response, then independently checks each returned native type against Universe dictionaries. The browser's three Generate inputs and default session still enable no loadout. No `npc-generator` files were changed.
- Generator historical possessions remain separate: the `arena_loadout` contract does not read or reinterpret them. The original NPC source record remains attached to the private `ArenaNativeBeing`; no magical, exchanged, or unresolved possession text was parsed, dropped, equipped, or projected. The separate `arena_items` projection is not used to manufacture ground Objects.
- Native definitions were verified in the installed Universe library: `Dagger` is an ordinary `WeaponDefinition` (weight 1), `Leather armor` is an ordinary `ArmorDefinition` (weight 15), and `Small shield` is an ordinary `WeaponDefinition` (weight 6) in the native `Shields` category. The adapter only accepts exact keys, positive finite physical weight, and native `is_magical is False`; it does not use substring or display-string matching. A source item quantity must be exactly one, so duplicate types become independent native instances.
- The action catalog includes `ready weapon`, and older source reports document direct setup/equipment helpers. I found no current transactional ground pickup or ready/equip Action implementation in the Arena/Encounter path. No substitute Action was added. Thus these Objects are native world Objects but cannot yet be picked up or readied through this Arena interaction.

## Implementation

- Added `src/arena_ground_objects.py`, a documented fail-closed adapter for exact typed item records. It validates all descriptions and placements before construction, constructs `ArmorInstance` or `WeaponInstance` from native definitions, checks unique Universe identity including duplicate types, places each uncontained Object at its selected hex center, and only then registers instances in the still-private candidate Universe. Constructor and validation failures receive classified refusals. It retains a separate source-local ID → native Object ID relation.
- Ground placement uses a seed from the independent `ground-placement-v1` namespace and a private `random.Random`. It samples distinct initially vacant cells without replacement while preserving both Being placements. Once vacant cells are exhausted, it selects from a deterministic sorted frontier of edge-sharing native hex neighbors and builds an irregular finite `ground_layout`. Bounds cap items at 3,000, added cells at 3,000, and layout bounding area at 1,000,000 cells. The public initial Arena map and movement lattice remain unchanged; the private ground layout is placement bookkeeping, not post-time-zero collision or movement geometry.
- Extended `ArenaInitializationCandidate` with private ground placements, provenance bindings, layout/seed, and optional Generator profile provenance. Candidate Objects are assembled before return in the same fresh unpublished Universe as both Beings. Session replacement still occurs only on successful generation; failed construction leaves the prior candidate, projection, and RNG cursor unchanged.
- Extended `GeneratedArenaSession` with optional host-side test/profile inputs. Those inputs are deep-copied and are not browser controls. There is no production equipment distribution or new object-view endpoint.
- Added `tests/fixtures/arena/test_ground_loadout_profile.json`, explicitly labeled by its profile/catalog IDs as a test profile. It samples two Daggers, one leather armor, and one small shield for each NPC. The typed-fixture helper additionally exercises arbitrary repeated items and capacity boundaries without requiring a Generator distribution.
- The tests verify native classes, exact definitions and positive weight, unique per-unit identities, source/native ID separation, distinct cells and positions, unowned/unequipped/neutral defense state, deterministic replay and namespace isolation, full 5×5 placement and eight-cell expansion, observer secrecy, failed-request stability, and real movement to exact arrival without implicit pickup/equip.

## Movement, observation, and rule boundaries

With the optional profile enabled, the test selects a destination, changes rate from Walk to Sprint without clicking the map again, then advances through the native one-second movement path until exact destination arrival. The updated accepted movement plan is used. Ground Object positions remain unchanged, no item enters Being possessions/weapons/armor/body-part slots, no skill practice is recorded, and both Beings' Awareness ledgers stay empty. Browser projections contain no item names, item locations, counts, native IDs, or Generator source IDs; calling the player projection does not advance the session RNG or consume Python's module RNG.

Objects have `geometry=None`, and the derived hex center is only a reference position. No body volume, collision, clearance, pickup, perception, Spot result, or item visibility is inferred. No observer-owned evidence path for ground Objects was found, so the player map intentionally continues to reveal no Objects. Native shields are built but grant no defense because they are not held/equipped. There is no generated gear default pending an approved profile/catalog choice and a native transactional pickup/readying path.

## Verification

All successful test commands below passed with no skips. Times are unittest-reported durations.

| Command | Result |
|---|---|
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_arena_ground_objects.py' -v` | 4 passed, 0 failed/errors/skips; 1.650 s |
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_generated_arena_browser.py' -v` | 23 passed, 0 failed/errors/skips; 7.248 s. Includes shipped JavaScript wiring and Walk→Sprint request ordering/acceptance coverage for the existing browser behavior. |
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_arena_initialization.py' -v` | 7 passed, 0 failed/errors/skips; 0.560 s |
| `python -m unittest discover -s tests -p 'test_arena_hex_map.py' -v` | 4 passed, 0 failed/errors/skips; 0.001 s |
| `PYTHONPATH=src:examples:../npc-generator python -m unittest discover -s tests -p 'test_movement_intent.py' -v` | 20 passed, 0 failed/errors/skips; 4.159 s |
| From `tests/`: `PYTHONPATH=../src:../examples:../../npc-generator python -m unittest discover -s . -p 'test_object.py' -v` | 25 passed, 0 failed/errors/skips; 0.009 s |
| From `tests/`: `PYTHONPATH=../src:../examples:../../npc-generator python -m unittest discover -s . -p 'test_weapon.py' -v` | 11 passed, 0 failed/errors/skips; 0.017 s |
| From `tests/`: `PYTHONPATH=../src:../examples:../../npc-generator python -m unittest discover -s . -p 'test_armor.py' -v` | 20 passed, 0 failed/errors/skips; 0.016 s |
| `python -m py_compile src/arena_browser_session.py src/arena_initialization.py src/arena_ground_objects.py tests/test_arena_ground_objects.py` | Passed. |
| `git diff --check` | Passed. |

Three early adjacent-suite invocations had environment setup errors and were rerun successfully: movement was first invoked without the NPC Generator path (20 setup errors); Object/Weapon/Armor suites were first invoked from the repository root, although their existing fixtures use paths relative to `tests/` (3, 4, and 5 fixture-file errors, respectively). The corrected commands and their clean results are listed above. No full suite or checkpoint suite was run; no checkpoint primitive was changed. The assignment's known dangling-equipment diagnostic mismatch was not exercised or altered.

## Browser smoke procedure and current constraints

On a machine where loopback binding is permitted, launch `examples/generated_arena_browser.py` with the repository's supported Python environment and `npcgen` on `PYTHONPATH`; open its local URL, generate the Arena, select a destination, change Walk/Sprint and facing policy after selection, and press **Advance 1 second** repeatedly until the player reaches the destination. The ordinary browser should show no ground item identity or position. For a terminal trace use `ARENA_TRACE_UI=1` before launch. This environment did not launch the local browser server or GUI, so no real-machine visual smoke is claimed. The shipped JavaScript handler test did run.

## Commits and disposition

Implementation commit: `9de5463` (`Add bounded Arena ground combat objects`). The report is committed separately immediately afterward. No push was made. Unrelated pre-existing deleted/untracked files were left untouched and excluded from staging.

Where we stand: generated Arena Beings can now share a private native world with independently realized, explicitly sourced ground combat Objects. The initial player map and its U-ARENA-004U option synchronization remain intact. The next supported slice requires adopted native pickup/readying Action semantics and a separately approved default ordinary-loadout profile; object perceptibility must be resolved before any item information can enter a player projection.
