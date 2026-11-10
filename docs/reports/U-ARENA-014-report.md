# U-ARENA-014 — Native Dodge in the generated Arena

## Result

The generated Arena now supports one bounded defensive Action: **Dodge against one currently observed, pending native MeleeStrike**. The player can choose it from the contextual Action selector. A separately selectable **Defense only** opponent schedules the same native Dodge against an eligible player strike that it has observed. It never schedules a strike.

The implementation delegates timing, threat checks, rolls, defense outcomes, practice, Choice admission, same-boundary settlement, and publication to the existing `MeleeDefense` and transactional Encounter pipeline. The Arena does not calculate a defense result or write combat state itself.

## Rule and code basis

The adopted Encounter revision 61 establishes Dodge's two-second preparation, its use against an eligible observed attack, and expenditure at the attack's resolution. The production `src/melee_defense.py` contract is more specific: a `MeleeDefense(kind="dodge")` must designate one pending incoming `MeleeStrike`; `prepare_schedule` sets `ready_at = start_time + 2` and keeps the defense active through that strike's impact. It refuses if the preparation cannot finish by impact. The native resolver then decides `evaded`, `failed`, `no_threat`, or `unable_to_defend`, using its own rolls and eligibility checks.

The Arena submits that exact native Action through `Encounter.prepare_action` and `schedule_action`. The target strike is selected from the defender's current observer-owned perception and pending native history. Browser payloads contain only the selected perceived Entity handle; neither attack nor defense Action IDs are sent to or returned by the browser. The Defense-only policy checks only the opponent's current evidence and committed state. It does not read an uncommitted player Action or movement plan. Without a visible eligible strike, it waits without creating a Choice or consuming RNG.

Dodge needs no weapon or hand. **Parry is left unavailable** because the generated Arena does not implement its target-independent retained readiness or the required weapon-skill eligibility path. This avoids presenting the current native attack-specific `MeleeDefense` as a general held defense.

## Browser walkthroughs

Both interactions were exercised in isolated Chrome tabs against the shipped page and a local `127.0.0.1` server using the Empty ground profile and deterministic root seed `20261107`.

### Player Dodge

1. Generated a 10-by-5 Arena with 10,000 starting XP, equipped generated Beings, and Attack only.
2. Clicked the player Being, selected native Run, and advanced one second twice. The opponent's native Thrust was pending with impact at Encounter second 5.
3. Selected the perceived opponent in the Visible entities list, returned to the player popup, and selected **Dodge (2 s)** from Attack responses.
4. Advanced through seconds 3 and 4, when the Dodge was ready, then through second 5 for impact.

Chrome displayed `Dodge resolved: evaded` and `Opponent Thrust resolved: dodged after 4 seconds`. A focused trace assertion verifies that the player Dodge is reported as a native Action with two seconds of preparation; no hidden Action ID appears in the UI or trace.

### Defense-only opponent

1. Generated the same Empty-ground Arena with **Defense only** selected.
2. Activated through native Run, moved the player by the native Sprint plan to the adjacent hex, and selected the opponent from visible evidence.
3. Submitted the available native Dagger Thrust through the player Action selector. The opponent did not respond on the same declaration boundary; it scheduled Dodge after the next boundary exposed the player strike to its current evidence.
4. Advanced through second 6, the Thrust's impact.

Chrome displayed `Opponent Dodge resolved: evaded` and `Thrust resolved: dodged after 4 seconds`. No opponent strike was created. The action/status projection withheld the opponent Dodge until it was observable.

## Persistence, refusal, and determinism

The strategy enum now accepts `defense_only` in the existing strict Arena save format; no schema bump was needed. Older saves with no opponent strategy still load as `none`. The strict native snapshot tags now include the `MeleeDefense`, defense effect, skill exercise, and action resolution types needed to retain pending and completed native Dodge history.

The new session tests save and restore the player's preparing Dodge, a ready-but-waiting Dodge, and the completed result. They compare committed Action and Choice identities, pending/completed membership, native Being and skill state, observer evidence, and RNG against uninterrupted execution. They also load and advance preparing Dodge checkpoints in fresh OS processes with NPC generation patched to fail. Defense-only checkpoints are similarly restored and compared across impact. No Dodge is regenerated or replayed.

The tests cover no observed threat, an already planned player Action, duplicate/ongoing defenses, and a too-late Dodge. A live trace initially exposed that the Defense-only policy could propose a second Dodge while the first was waiting for impact; the policy now refuses another proposal while its native defense is pending. A repeated Chrome smoke and a regression assertion confirm one Dodge is scheduled. Refused choices leave Encounter time, pending Actions, event history, Choice state, and RNG unchanged. Native practice is preserved: the resolver's `SkillExercise` applies only for `evaded` or `failed`, not `no_threat` or `unable_to_defend`. A ready Dodge waits for its designated strike's impact; time advancing to `ready_at` does not resolve it early.

## Validation

Passed:

- `python -m py_compile examples/arena_web.py src/arena_browser_session.py src/arena_native_snapshot.py src/arena_persistence.py tests/test_arena_opponent_attack.py tests/test_generated_arena_browser.py`
- Focused Dodge, HTTP route, and shipped JavaScript tests: 5 tests passed in 13.390 s.
- After the duplicate-defense guard: player and Defense-only save/resume tests passed, 2 tests in 11.726 s; the Defense-only assertion confirms exactly one native Dodge remains scheduled through continuation.
- `python -m unittest test_attack_specific_defense test_arena_opponent_attack test_arena_persistence test_generated_arena_browser test_transactional_progression -v`: 125 tests passed in 87.424 s.
- From `tests/`: `PYTHONPATH=../src:../examples:.:../../npc-generator python -m unittest test_melee_combat -v`: 11 tests passed in 0.121 s.
- Real Chrome browser walkthroughs for player Dodge and the Defense-only opponent described above.
- `git diff --check`.

The first combined regression invocation included `test_melee_combat` from the repository root. Its 11 cases errored during fixture setup because that legacy module resolves `../src/config` relative to the working directory. The other 125 tests in that invocation passed. Rerunning the affected module from `tests/` passed all 11; this was a test working-directory issue, not an Arena or melee regression.

## Scope and remaining work

The browser exposes an attack-specific Dodge, not a general defense stance. Each Dodge is tied to one currently pending observed strike. The Arena does not expose retained target-independent readiness, multiple-strike defense selection, or Parry. Those behaviors require additional native/Arena contracts and were not inferred here. `Mixed` and `Random` opponent policies remain unavailable. Existing Attack-only approach, native Thrust, movement, and old-save defaults remain covered by regression tests.

## Changed paths

- `examples/arena_web.py`
- `src/arena_browser_session.py`
- `src/arena_native_snapshot.py`
- `src/arena_persistence.py`
- `tests/arena_browser_js_harness.swift`
- `tests/test_arena_opponent_attack.py`
- `tests/test_generated_arena_browser.py`
- `docs/reports/U-ARENA-014-report.md`

Implementation commits: `c13b836` (`Add native Dodge to generated Arena`) and `ad8a092` (`Prevent duplicate Arena opponent Dodges`).

No changes were made to the sibling NPC Generator repository. No push was performed.
