# U-ARENA-004E — Direct `npcgen` Arena Being bridge

## Result

Implemented a bounded direct-library path in `src/npcgen_arena_adapter.py`. It calls the installed `npcgen.api.generate_arena_candidate` with an explicit seed, exact starting-experience integer, and mandatory explicit `cost_modifiers` choice. It validates the generated record and age-resolution status, maps only source fields supported by the current Universe dictionaries and existing adapter semantics, creates a native Being from an exact native race-template match, and registers it only after validation and detached construction succeed.

This proves an actual native initialization path for the supported Generator races `Human`, `Grey Elf`, `High Elf`, `Wood Elf`, and `Half-elf` (case-insensitive exact matches to a unique native `BeingDefinition.obj_type`). It does not create a generic/fabricated Being fallback. All other Generator race names currently refuse. A returned `ArenaNativeBeing` carries the full canonical Generator JSON bytes, SHA-256, engine identity, and skill-resolution status alongside the independently generated native Being ID.

The bridge does not map Generator class IDs, class XP slots, or levels into Universe class mechanics. It verifies that the integer XP slots sum exactly to the requested total, leaves class/level facts in the retained source record, and writes the request directly into native `BeingDefinition.experience` without using rounded sheet data. It imports ranks only from a `resolved` age-derived profile. Initial `skill_experience`, practice baselines, and skill-use history remain empty. Unsupported race, unresolved skill, inconsistent record, unrecognized skill, or package identity failures raise `ArenaNPCRefusal` with a stable code/details object before `Universe.add_object`.

## Repository and package state

- Universe started on `main` at `2e780a3`; the tracked deletions and untracked material shown at task start were pre-existing. The implementation commit is `eff7ed9` (`Add direct npcgen Arena Being bridge`). A second documentation-only commit adds this report. No push was performed.
- The read-only Generator checkout is `npc-generator`, branch `main`, commit `bc77c8f48bd4cdab082e3d85e3676c906224710a`. It remained unchanged, including its pre-existing dirty/untracked assignment material.
- Live Generator package identity: `npcgen` `2.1.0`, rules hash `sha256:78e8a2bc8e7dc7ba635f8ab6d8bdf8174c35608c9af04b6533cc3d84c46865ff`.
- The confirmed API is `npcgen.api.generate_arena_candidate(seed, starting_experience, class_index=None, cost_modifiers="neutral", rules=None)`. It returns `ArenaCandidate(npc, skills_status, record)`. `npcgen.api.export_json(npc)` supplies the canonical persisted source record.

### Local installation used for direct import

The system Python and Generator `.venv` initially could not import `npcgen`. A normal editable install was attempted in the ignored Universe `.venv`, but pip could not fetch the required `setuptools>=68` build dependency because network access was unavailable. A `--no-build-isolation` attempt using the only local setuptools (from Python 3.11) failed under Python 3.14 because that older backend imports the removed `pkgutil.ImpImporter`; its wheel build command was also unavailable. No Generator file was changed.

For this local, non-network test environment, the Universe `.venv` has a source-linked package entry in its `site-packages` directory. `npcgen.__file__` resolves through `.venv/lib/python3.14/site-packages/npcgen/__init__.py`, with that package entry symlinked to the adjacent `npc-generator/npcgen` directory. The adapter uses an ordinary `from npcgen import api`; it does not modify `sys.path`, launch a CLI, or copy Generator code into tracked Universe files. The ignored environment can be recreated from the repository root with:

```sh
python -m venv .venv
npc_site=$(.venv/bin/python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
ln -s "$(cd ../npc-generator && pwd)/npcgen" "$npc_site/npcgen"
```

This is a local development link, not a committed runtime dependency manifest or release install. A deployed environment still needs a normal install of a pinned Generator commit/wheel with an available build backend. The generated record records the package version/rules hash, and the bridge requires it to match the active installed package identity.

## Implemented mapping and refusal boundary

| Generator source | Universe mapping | Result |
|---|---|---|
| `generation.starting_experience` with `starting_experience_meaning="arena-starting-total"` | `BeingDefinition.experience`, then the instance's copied current scalar | Exact nonnegative Python integer; float/bool coercions are rejected. The API's upper bound remains in force; there is no clamp. |
| `state.xps` | No native per-class field | Every slot must be an integer >= 0 and the slots must sum exactly to the request. `classes`, `xps`, and `levels` must be parallel; class IDs/levels are checked against Generator shape but remain only in source provenance. |
| `state.skills` plus `generation.skill_resolution` | Native `Skills.skills` and `Skills.weapon_skills` | Only explicit `resolved` profiles are imported. Rank names must resolve in configured native dictionaries and ranks must be positive integers. `None`/`unresolved` raises `skill_profile_unresolved`; resolved empty maps stay empty. |
| `state.scores` | Native `Abilities` | Six positive integer scores must match the named sheet scores; source ordering is checked. |
| `state.height`, `state.weight` | Native race definition copy's `length` (stature, inches) and `weight` (pounds) | Positive finite measurements must agree with rounded sheet projections. No geometry is created. |
| `state.hps` | Native template copy's current hit-point value | Nonnegative integer must match `sheet.hit_points`. This does not infer a maximum HP, native hit dice, or class mapping. |
| `state.name` | Native Being instance display name | Preserved as supplied. Native ID is independently generated. |
| `state.race` and `sheet.identity.race` | Exact unique casefold match to a native `BeingDefinition.obj_type` | The source index/name must agree with the installed Generator race table. No racial alias is inferred. Unsupported or ambiguous matches refuse. The native definition's race, alignment, hit dice, armor class, challenge rating, and other unmapped fields remain unchanged. |
| Full `npcgen-npc` record | Returned `source_record_bytes`, `source_sha256`, and `engine_identity` | Canonical bytes are retained for the caller; no Generator class/level/race mechanics are rewritten as Universe data. |
| Generator skill practice/history | None | No source mapping exists. Universe practice, baselines, and history are left empty on creation. |

Construction uses `template.copy()`, overlays only the fields above, creates `BeingInstance` while detached, and then calls `Universe.add_object` once. Tests verify source/native identities differ, repeated candidates retain byte-identical Generator records but receive distinct native UUIDs, native template fields are preserved, and no geometry or possessions are fabricated. The caller must retain `ArenaNativeBeing.source_record_bytes` if provenance is to survive beyond the current in-memory integration; save/load wiring was outside this assignment.

## Reproducible examples and limits

Direct API probes used the installed package from the Universe `.venv`:

| Seed / XP / cost policy | Generator result | Native result |
|---|---|---|
| `1 / 0 / character` | Half-elf; `xps=[0]`, `levels=[0]`; age 26 (`Adolescent`), resolved juvenile profile: `armed combat:1`, `Dagger:1` | Supported native `Half-elf`; exact experience 0 and exact ranks imported. |
| `1 / 12000 / character` | Half-elf; `xps=[12000]`, `levels=[3]`; age 32.174091339, resolved juvenile profile: `armed combat:1`, `Dagger:1` | Supported native `Half-elf`; native scalar exactly 12000 and initial ranks exactly imported. |
| `76 / 0 / neutral` | Human; `xps=[0]`, `levels=[0]`; `skills={skills:{}, weapon_skills:{}}`, status resolved | Supported native Human with a genuinely resolved empty rank profile. |
| `1 / 12000 / neutral` | Half-elf; status unresolved because neutral costs are not corroborated for Intelligence modifier 1 | Refuses `skill_profile_unresolved`; no native registry change. No retry or switch to `character`. |
| `4 / 12000 / character` | Gnome; resolved rank profile | Refuses `unsupported_native_race`; Universe has no exact native Gnome definition. |
| `1 / 9999999 / character` | Age 375.19189453125, category `Dead`; unresolved because Generator defines no starting-skill age class for `Dead` | Refuses with the Generator reason. XP is not capped and age is not altered. |

The current race-name intersection is only five of Generator's sixteen race names. In particular, `Dark Elf` is not mapped to native `Drow`; neither name equivalence nor mechanics equivalence is adopted. Multi-class records can be generated by the library and are validated as parallel class slots, but Universe has no native class/level model in this adapter. Age-based skill costs and age-class mapping carry Generator's own provisional provenance; Universe neither recalculates nor certifies those rules.

`cost_modifiers` is mandatory at the Universe bridge call site and accepts the existing Generator policies `neutral` or `character`. The bridge never changes policy, retries a seed, chooses a class, or selects among candidates. The Generator itself accepts exact starting XP only up to `2**53-1`; larger values are refused by the API and surfaced as `generator_refusal`. A product-level selection/retry policy for unresolved profiles, unsupported races, and Dead ages remains undefined and must be decided before a two-Being Generate flow can promise success.

## Tests and verification

### Final focused test runs

- Universe, run from `tests/`: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=../src:. ../.venv/bin/python -m unittest test_npcgen_arena_adapter test_npcgen_being_integration test_skill_experience test_action_resolution_experience` — **21 passed**, 0 failures, 0 skips, 3.232 s. A non-fatal Python venv-prefix warning appears because the executable is invoked as `tests/../.venv/bin/python`; `pyenv` also prints its pre-existing “cannot rehash” warning.
- Generator source regression: `.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_arena_xp.py tests/test_persist.py` from `npc-generator` — **30 passed, 1 skipped**, 3.57 s. This confirms the installed API's upstream exact-XP/provenance behavior; the skipped test is its environment-dependent packaging check.
- `git diff --cached --check` was clean for the implementation commit. No full Universe suite was run.

### Intermediate test corrections / invocation issue

- The first isolated run of the new 5-test module had **1 failure** because the initially selected seed 0 produced a nonempty profile, contrary to the test's resolved-empty fixture assumption. A fixed, probed seed (76) replaced it; the corrected 5-test module passed, and all five are included in the final 21-test passing run.
- A combined test invocation from the repository root failed with **13 existing test errors** because those older tests resolve `../src/config` relative to their expected `tests/` working directory. Running the exact same test modules from `tests/` passed all 21. This was a test-command working-directory issue, not an adapter failure.
- A first local `pip install -e ../npc-generator` did not install because network access to setuptools was unavailable; the alternate no-build-isolation attempt failed on the old local Python 3.11 packaging backend under Python 3.14. Those setup failures motivated the ignored local site-packages symlink described above; no source change or network installation was attempted after that.

## Claude-owned Generator changes

No Generator source change is needed for this bridge: the live `generate_arena_candidate` API already provides exact integer total XP, integer class-slot conservation, age-derived skills, explicit `resolved`/`unresolved` status, and complete replayable provenance. Keep its current refusal behavior. Future changes would be needed only if the product adopts one of these currently unsupported needs: wider native race compatibility, a changed Dead-age policy, a different approved age-class/skill policy, or a user-approved candidate filtering/retry API. Those choices must be made before changing Generator behavior.

For deployment, the Generator owner should continue publishing/pinning an installable commit or wheel and retain the version/rules hash. Universe does not rely on a CLI, HTTP service, or copied Generator implementation.

## Next smallest implementation slice

Build a two-candidate preflight coordinator that accepts two explicit `(seed, starting_experience, cost_modifiers)` requests, calls this bridge for both in detached/preflight mode, and publishes neither Being unless both candidates validate. Do not choose seeds or switch policies automatically. Before a user-facing two-Being Generate operation, settle the candidate retry/selection policy, accepted race subset, maximum experience product constraint, and whether Generator's provisional age-class mapping is acceptable. Map or reject future nonmatching Generator races only after an explicit native race mapping is adopted. Map Encounter placement and source-record persistence in later slices; this bridge does not create Objects, map cells, Awareness, GUI, or Actions.
