# U-ARENA-007 engineering report

**Status:** Implemented and verified in the generated Arena browser. No changes were made to `npc-generator`, and nothing was pushed.

## Delivered

### Starter ground equipment and lifecycle

- A normal `examples/generated_arena_browser.py` launch reads the checked-in, deterministic starter demonstration profile at `examples/arena_profiles/starter-ground-equipment.json`. It creates eight ordinary native combat Objects: two daggers, two short swords, two leather armors, and two small shields. They receive independent native identities and distinct ground hexes, separated from the two Beings. They start on the ground, uncarried, unready, and unequipped. This is an explicitly authored sample profile, not an inferred NPC Generator possession rule or an Arena-wide random equipment distribution.
- Generate exposes **Starter ground equipment** by default and **No ground equipment**. The latter correctly creates no ground Objects. The `--authored-draw-scenario` workflow remains opt-in and is independent of the standard starter loadout.
- Before generation/load, the page shows Generate and Load, without an Encounter or Visible Entities section. On success the generation form hides; the map, entity list, Save, Load, and confirmed New Encounter controls are available. Advance 1 second is beside the Encounter heading. Entity clicks open a dialog while map clicks retain destination selection. The separate Character button is gone; the player marker opens the player sheet.
- The old **Choose Run instead** button sent the native target-free Run Choice to `/api/generated/run`; it was a separate invitation to use Run, not a fallback implementation of another Action. That separate control is removed. Run remains explicitly selectable in the native Action catalog alongside the other supported/unsupported entries, with native availability and reasons.

### Authoritative measurement truncation

`src/measured_values.py` supplies the common finite-number truncation primitive. It converts through `Decimal(str(value))` and `ROUND_DOWN`, which truncates toward zero without binary-float threshold artifacts (`70.999 → 70.99`, `150.678 → 150.67`, `-1.239 → -1.23`, and `-0.009 → 0.0`).

The rule is enforced where supported measured state is created or committed:

- Being stature and body weight, and Object/weapon/armor/shield length, width, height, and weight.
- Sphere radius and axis-aligned-box side lengths, the other persisted native physical extents.
- Every stored Cartesian position component, including initial Being/Object positions and positions published at each committed movement boundary. Intermediate movement integration and geometry calculations retain their required precision; only the committed position is truncated.
- Accepted Arena hex destinations, saved movement-plan checkpoints, carried-weight projection, and saved/restored native graph validation. Native restore rejects a noncanonical stored measurement instead of silently changing the file.

The Arena-native snapshot schema advanced from `/1` to `/2`, and the generated Arena save envelope from `/2` to `/3`, so files from the prior measurement contract fail closed. Checkpoint movement reconstruction now compares against the truncated canonical hex center, preserving exact destination identity under the new storage precision.

Exact yard-to-meter constants, hex geometry, time, skill ranks, probabilities, proportions, fatigue values, and dimensionless visibility opacity are rule values or non-length quantities; they remain unchanged. Derived distances such as the movement engine's integration intermediates are not persisted measured positions. The NPC Generator's exact source JSON is preserved as provenance; the Arena's authoritative initial Age projection is the two-decimal-truncated value.

### Generator skill provenance, Age, and Class

The 1,000-XP case is reproducible with installed Generator inputs `seed=8`, `starting_experience=1000`, `cost_modifiers="character"` (covered in `tests/test_npcgen_arena_adapter.py`). Its preserved NPC Generator record reports:

- age `101.26`, category `Middle-aged`;
- class allocation Ranger (ID 1), level 1, 1,000 class XP;
- explicitly acquired `armed combat: 3` and only `Dagger: 3` in `state.skills.weapon_skills`;
- no native earned skill-practice XP.

Universe's native `Skills.set_weapon_skill_level` (`src/skill.py`) expands a weapon rank to its weapon-category peers at `floor(rank / 2)`. Thus Dagger 3 produces 17 effective category-derived weapon ranks of 1. The source does not claim these 17 ranks were individually acquired. The player sheet now separates initially acquired ordinary skills, initially acquired weapon skills, effective category-derived weapon ranks, and earned practice XP. In the exact 1,000-XP case it reports Dagger 3 as acquired, the 17 rank-1 peers as effective/not individually acquired, and practice as zero.

The installed Generator API (`../npc-generator/npcgen/api.py`, `generate_arena_candidate`) explicitly says skills are not derived from XP or level and resolves them once through its age-class budget policy. `../npc-generator/npcgen/skills.py` holds the budget table and policy. The Arena did not replace that adopted age-primary policy or edit the sibling repository. The older erroneous display was caused by projecting the expanded native effective weapon map as if every key were a source-acquired rank, not by the seed-8 Generator record.

Every generated player Being retains a validated `_arena_initial_profile` with truncated initial Age, source category/birthday, all parallel class IDs/names/levels/class XP, exact initial total XP, and the source's explicit initial skills/resolution. This record is separate from evolving native total XP and skill practice. Class names come from the installed Generator's indexed class table; IDs remain visible so the saved allocation is unambiguous. Save/load and strict checkpoint closure now validate and restore the same record without regenerating the Being. Native snapshot/save schema changes above reject incompatible older files.

### Consistent Being popups

The player and Arena-controlled Being use the same `renderCharacterSheet` component and section order. The header is only the effective display name. Player fields come from current native state plus the validated initial profile. The opposing Being is projected from observer-owned evidence only; private age, class, ability, experience, skill, condition, hands, and inventory facts remain `Unknown`/unavailable in the matching fields. No GM state is used to fill the opponent sheet. Comprehensible Conditions, Hands, Position and movement, and carried/equipped/readied inventory replace the old raw `Native States` presentation.

## Browser acceptance evidence

I used the shipped page in an isolated Chromium browser session against the actual `GeneratedArenaSession` HTTP server. Both servers bound only to `127.0.0.1` on an OS-assigned ephemeral port. I also inspected the terminal trace from the ordinary interaction.

1. **Ordinary gameplay and pickup Save/Load:** generated through the ordinary starter-profile launch with 1,000 starting XP; the browser showed both Beings and the eight ground Objects. The player sheet showed native Age/Class/XP and distinct acquired/effective/practice skill sections. I selected an adjacent hex, committed native movement from `(2.11, 4.11, 0)` to `(2.11, 3.20, 0)`, moved to the Dagger's hex, inspected it, and submitted the native Pick up Choice. The one-second boundary resolved `success` at time 3. Save downloaded `universe-arena (4).json`. I stopped the server, restarted it as a new process, loaded that file, and observed time 3, the same native position, and the carried Dagger. I then selected another destination and committed the next second to time 4 at `(3.69, 3.20, 0)`. The terminal trace recorded the browser click, accepted destination, native position change, and HTTP response in order.
2. **Pending Draw across restart:** launched the checked-in opt-in authored Draw scenario, generated at 10,000 XP, inspected the carried/unready Dagger and empty hands, selected the Dagger, selected **right hand**, and submitted the native two-second Draw. Save downloaded `universe-arena (5).json` while Draw was pending. After stopping and restarting the authored server, I loaded it in the browser at time 0. One second committed with left and right hands still empty and Draw still pending. The second boundary advanced to time 2 and reported `Draw resolved: success`; the player sheet then showed `right hand: Drawable Dagger` and the same carried native Object as readied in that hand.
3. **Invalid file retention:** while that loaded/played Encounter was active at time 2, I loaded a prior-format save. The UI refused it (`saved native Arena implementation/rules differ from this runtime`) and retained time 2, position `(2.9, 4.57, 0)`, and the readied Dagger. No partial replacement was published.

One attempted zero-XP ordinary generation produced a native player Being at 0 HP. The browser reported the adopted voluntary-movement refusal and left time and position unchanged. This is the generated native hit-point value, not a precision or movement defect; it was not changed by overriding source state or native rules. The successful ordinary workflow used 1,000 XP. The authored Draw workflow used its explicit 10,000-XP premise.

## Verification

- `PYTHONPATH=src:examples .venv/bin/python -m unittest tests.test_measured_values tests.test_spatial_geometry tests.test_npcgen_arena_adapter tests.test_arena_persistence tests.test_generated_arena_browser tests.test_arena_ground_objects tests.test_movement_intent tests.test_spatial_state tests.test_arena_initialization tests.test_checkpoint_movement_binding tests.test_checkpoint_movement_continuation tests.test_arena_checkpoint_activation -q` — latest run: **113 tests passed in 58.681 seconds** (includes exact generator skill provenance, negative/threshold truncation, geometry, movement/hex state, native Save/Load, browser JavaScript/session, and strict checkpoint movement reconstruction).
- `PYTHONPATH=src:examples .venv/bin/python -m unittest tests.test_arena_local_checkpoint -q` — ordinary sandbox attempt: **3 passed, 1 environment failure**; the child loopback server exited before announcing its endpoint under the socket restriction.
- Reran only the blocked test with narrowly elevated execution: `PYTHONPATH=src:examples .venv/bin/python -m unittest tests.test_arena_local_checkpoint.ArenaOperatorHTTPContinuationTests.test_two_process_browser_save_approved_reopen_run_and_native_commit -q` — **1 passed**. All other development commands remained sandboxed.
- Browser acceptance above exercised real shipped JavaScript and native server/session Save, Load, Action, and movement requests. The browser-visible files were emitted by the Save controls and selected through the browser file chooser; no in-memory test handler substituted for that flow.
- Targeted `py_compile` of the changed Python modules and `git diff --check` passed. A repository-wide `compileall` attempt is not clean because of unrelated existing files (`src/AM_Kastrisios_Voronoi_Python.py` has Python 2 print syntax, `src/ModernApolloNavigator.py` is not Python, and `src/location.py` has an indentation error); none was changed. No broad full-repository test suite was run; unrelated changes and existing work were left untouched.

## Commits and repository boundaries

The verified implementation commits are `e1c55d3` (measurements), `2dabba9` (initial Generator profile and strict reconstruction), and `6d86fb9` (browser and starter profile). The initial Age/Class record is covered by strict native checkpoint closure and Arena portable-save restoration. No `npc-generator` file was edited, no unsupported Action/combat rule was introduced, unrelated dirty and untracked repository content was not staged, and nothing was pushed.
