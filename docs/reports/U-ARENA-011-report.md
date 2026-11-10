# U-ARENA-011 — Hex-occupancy reach for native melee against Beings

## 1. Result / where we stand

Implemented native hex-occupancy melee targetability for Arena Beings. A generated Being with an `npcgen.api.arena_ready_being(...)` Dagger can submit and resolve a native Thrust against a generated opponent whose native `Geometry3D` is `None`. Hex overlap permits the ordinary strike roll; it does not award a hit. The native hit/miss, damage, armor, Action, Choice, RNG, and transaction paths remain in force.

The generated Arena now persists a strict map descriptor (`flat-top-hex-1-yard-v1`, width, height) on the Encounter so the native impact resolver and restored Arena can use the same finite one-yard hex convention. No browser-side reach result or Being geometry was added.

## 2. Native impact contract before and after

Before this change, `MeleeStrike` compared the two Being reference-point distance with reach, then required a physical path whose endpoint lay on the target. A geometryless Being or an unknown path member could therefore turn otherwise eligible Arena strikes into `uncertain_path`; center distance also rejected cases where the target reference point was outside reach even though reach crossed the occupied target hex.

In an Encounter carrying the recognized Arena map descriptor, the impact-time resolver now:

1. Uses the target's committed Cartesian point and `ArenaHexLayout.cell_at_position` to select its occupied cell. Existing closed-edge membership and lexicographically deterministic in-map tie handling are reused. An out-of-map target is `unplaced`.
2. Measures the shortest 3-D distance from the attacker's committed point to the target cell's regular hex cross-section at the target's height. Reach must be **strictly greater** than that separation. Exact edge/vertex tangency is `out_of_reach`; any positive interior overlap can pass even when the target reference point itself is farther away than reach.
3. Applies the existing twelve-way native facing convention at impact. An attacker not facing the target in the adopted front sector resolves as `not_facing`. A rear-facing target has its allocated defense level set to zero as adopted by Encounter revision 61; the same rule is applied in the pure proposal evaluator and the legacy native `MeleeStrike.roll_hits` path.
4. Preserves independent path checks. A known path intersection remains `blocked`; an unmodeled standalone ground Object remains `uncertain_path`. In Arena hex Encounters, carried/container-owned Objects without independent world positions are excluded from the environmental path candidate set; they are possessions, not additional obstacles in the space between Beings. Non-Arena Encounter path behavior is unchanged.
5. Proceeds through the unchanged native attack roll, defense, damage, equipment, skill practice, and atomic publication pipeline. Hex reach is only a targetability gate.

The test boundary uses the existing 1-yard-across-flats regular hex. It verifies a 0.2 m reach whose endpoint is 0.3 m from the cell center but penetrates the hex, exact tangency returning `out_of_reach`, and the immediately inward representable coordinate returning `in_reach`. A same-cell case and an exact shared-edge tie confirm occupancy and deterministic address selection.

## 3. Executable armed-exchange example and controls

The native HTTP/session regression uses root seed `20261107`, 10,000 starting XP, equipped generated Beings, and the empty-ground profile. It activates through the Arena route, moves the player to a target-neighbor hex, inspects the perceived opponent, and submits the generated/readied Dagger Thrust through `/api/generated/melee-strike`. The resolved native outcome is `normal`; the target's native HP fell from 13 to 10. Both Beings retain `geometry=None`. The hit and damage are produced by the existing native roll/effect transaction.

A second seeded regression schedules the strike while the player begins more than one cell plus reach away, then concurrently submits a native Sprint destination plan while the strike is pending. At impact, the updated positions and facing are read from the post-movement state. With the defender oriented away and an allocated defense level of 100, the attack resolves `normal` and reduces native target HP, demonstrating both movement-before-Action ordering and revision-61 zero defense from behind.

Controls verify strict tangency and out-of-reach at the impact boundary, `blocked` for a known path intersection, `uncertain_path` for an unmodeled ground path Object, and refusal of absent/unreadied Dagger and unobserved Being targets. The scheduled-distant test confirms distance is not rejected at Action acceptance. The target's damage is inspected only in native tests, not exposed by the player-facing Arena response.

## 4. Save/Load, observer evidence, and browser verification

The focused persistence test saves the accepted Thrust while pending, restores it into a new `GeneratedArenaSession` with `npcgen.api.arena_ready_being` patched to fail if called, and advances original and restored sessions through the four-second impact. It compares the completed action result, time, RNG cursor, HP, native Action and weapon identities, possession/equipment state, and saved completed result. Private native Being/Object identities remain absent from the public completion response.

The shipped JavaScript harness verifies that the UI submits only the visible opponent handle and the selected motion; it expects the actual native result to appear after four seconds. I also exercised the real local Arena in Chrome through the page's map click and player popup: the UI accepted a native `Dagger Thrust`, advanced one second at a time, and displayed `Thrust resolved: normal after 4 seconds.` The generated player was facing `5 / 12`; the visible opponent was at 0.92 m, within the displayed 1.01 m reach. The player-facing view did not expose the opponent's HP or private native ID.

With the ordinary starter ground-loadout profile, that browser session conservatively resolved `uncertain_path` because unmodeled ground Objects occupied the independent attack path. I then selected the supported empty-ground profile and repeated the browser click path; its valid native attack resolved `normal`. This preserves existing unknown-obstacle behavior rather than declaring unknown ground Objects transparent.

## 5. Known limits / any rule decision still needed

- This only defines Being targetability for Encounters using the recognized generated-Arena map descriptor. Encounters without that descriptor retain legacy center-distance behavior.
- Being body geometry remains deferred for line of sight, concealment/cover, thrown and missile-weapon trajectories, and physical collision. This work does not use hex reach for those systems.
- Any independently positioned or unmodeled ground Object on the required attack path remains conservative (`blocked` or `uncertain_path`); geometry or transparency rules for such Objects were not added.
- Exact rear-facing attacks use the adopted defense-level-zero rule. Flanking bonuses, collision, body geometry, and broader attack-motion clearance remain governed by their existing implementation or deferred rule work; this change does not infer them from hex overlap.
- `not_facing` is now an explicit native melee result for Arena attacks that do not satisfy the adopted front-facing requirement. The browser catalog still advertises a valid weapon/target Action where its existing admission checks pass; native impact remains authoritative for facing and range.

## 6. Tests, timings, commits, and working-tree preservation

Passing focused checks:

- `.venv/bin/python -m unittest tests.test_arena_melee_attack` — 7 tests, 11.025 s.
- `.venv/bin/python -m unittest tests.test_action_evaluation tests.test_arena_persistence tests.test_arena_hex_map` — 58 tests, 14.377 s.
- From `tests/`, `PYTHONPATH=..:../src:../examples ../.venv/bin/python -m unittest test_melee_combat` — 11 tests, 0.109 s. This legacy suite uses working-directory-relative config paths; its first attempt from the repository root errored during setup and passed when run from its required directory. The successful run emitted only local pyenv/`sys.prefix` warnings.
- `.venv/bin/python -m py_compile` for the changed Python modules and focused test — passed.
- `git diff --check` — passed.
- Real Chrome smoke — native map interaction, generated equipment, four-second Thrust pending/advance/result path — passed as described above.

The assignment file was installed at `docs/assignments/U-ARENA-011.md` from the supplied reissued assignment. Implementation commit: `cb91aca` (`Implement native Arena hex melee reach`). This report is committed separately. Pre-existing unrelated working-tree deletions and untracked files were preserved and not staged. No NPC Generator source, unrelated files, or remote branches were modified; nothing was pushed.
