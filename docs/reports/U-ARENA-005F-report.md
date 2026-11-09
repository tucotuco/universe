# U-ARENA-005F — weapon draw and re-ready timing correction

## Finding and authority

Adopted Encounter revision 61 is controlling. Its Weapons section says ordinary weapon drawing takes **2 seconds**, unless the weapon description specifies otherwise; its Quick-draw exception applies when the Being has Quick-draw and advanced skill in the weapon. The same section separately sets post-attack re-readying to one-third of the weapon's applicable timing, rounded down. The Ready section repeats these distinctions and says preparation/retrieval of an object can vary considerably and must be adjudicated. See [revision 61, Weapons and Ready](../encounters/encounters-working-draft-adopted-r61.md), especially Appendix I, Weapons (lines 1581–1589), and Ready (lines 2632–2644).

The adopted weapon tables are motion-specific. The Hand Weapons Table lists Dagger range, swing, and thrust timings as 4 seconds each (line 1706), producing a post-strike re-ready value of floor(4/3) = **1 second**. The Swords Table lists Longsword swing timing as 6 seconds (line 1818), producing **2 seconds**. I found no eligible 1- or 2-second weapon motion in the adopted revision-61 weapon tables inspected. The implementation's separate `src/config/weapons.tsv` does contain a Repeating crossbow range timing of 2 seconds, whose formula result is **0 seconds**, but Repeating crossbow has no corresponding weapon row in the adopted revision-61 weapon appendix. That data mismatch is unresolved; the config-only value is not asserted as an adopted rule. The pure helper returns zero for that input, but it creates no Action. None of these post-strike values set initial draw time.

The earlier revision-66 supplement incorrectly claimed a one-second initial Ready weapon rule. That claim is withdrawn. The proposed free-hand, Dagger-only, and same-boundary contention provisions were implementation assumptions and were not independently adopted. [Revision 66 is now marked as a non-adopted historical proposal](../encounters/encounters-consistency-decisions-r66.md), and the adopted-package index again identifies revision 65 as the latest adopted supplement. The historical [005E report](U-ARENA-005E-report.md) now carries a correction notice instead of asserting the false approval.

## Native state blocker and corrected behavior

The native Object model records possession, `parent_container_id`, and spatial placement. It does not encode whether an Object within a Being's custody is in a drawable location or buried in another carried Object. The Arena's generated Beings also have empty native `body_parts`; no hands are inferred or added.

Therefore an Arena `possessions` entry cannot be classified as an ordinary draw or as variable retrieval/preparation. The browser Action selector now keeps Ready weapon disabled after pickup and explains that the drawable location and applicable timing are unknown; it also states the ordinary two-second draw rule and distinguishes post-strike re-readying. The server rejects a direct Ready request without changing Encounter time, custody, weight, or hand state. It does not assume that a picked-up Object is sheathed or otherwise drawable.

The native `ReadyWeaponAction` candidate uses a two-second end boundary for an ordinary draw. At the first second the Action remains unresolved; it reaches its second boundary at +2. The transactional evaluator then refuses the unsupported source-location transition. This preserves the existing identity, Choice, contention, atomic publication, rollback, inventory, and observer safeguards without presenting their previous one-second success path as an adopted mechanic. A Quick-draw plus advanced-weapon-skilled Being is rejected from the fixed two-second declaration because revision 61 describes that draw as essentially no-time and the current Encounter Action path does not represent it. The current Dagger definition has no table-specific draw-time override. Other exceptions cannot be encoded because the weapon definition model has no draw-time field.

No initial weapon draw completed end to end: the assignment's own fail-closed boundary prevents that until native state can distinguish drawable location from variable retrieval. The verified browser path is map movement, ground Pick up, and then the character popup showing the same Dagger as `carried; not readied`, with Ready disabled and a specific reason. The shipped JavaScriptCore harness verifies the disabled control submits no Ready request; the native HTTP/session test verifies a direct request is refused with no state change.

## Table-derived post-strike utility

`weapon.re_ready_time_after_strike(weapon, motion)` reads the native weapon definition or instance's unmodified `R`, `S`, or `T` table timing and returns integer floor(timing/3). It does not calculate draw time, create an Action, change readiness, or infer a prior strike. Tests use loaded native definitions and verify:

| Weapon and motion | Native table timing | Re-ready formula | Result |
|---|---:|---:|---:|
| Dagger range/swing/thrust | 4 s | floor(4/3) | 1 s |
| Longsword swing | 6 s | floor(6/3) | 2 s |
| Repeating crossbow range (native config only; no revision-61 weapon row) | 2 s | floor(2/3) | 0 s; not treated as adopted |

The helper preserves the zero arithmetic result for the native-config-only input, but the corresponding weapon timing is not adopted Encounter data. No zero-duration Action is created. The existing combat lifecycle does not yet model a post-strike re-ready state transition, so the helper remains a tested primitive for a later integration.

## Safeguards and scope

- No NPC Generator data, generated Being templates, default equipment, sheath/pack locations, body geometry, or weapon statistics were added.
- The previous successful Ready publication path is no longer reachable through normal evaluation because initial drawable location is unknown. Atomic same-identity publication code remains. Test-only eligibility injection exercises its rollback and same-snapshot contention behavior without asserting that this is a currently legal Arena transition.
- Readiness never leaks opponent equipment. Carried Object identity, native weight, movement inventory projection, and observer-owned evidence remain unchanged on refusal.
- No checkpoint fields or reconstruction behavior changed. Checkpoint suites were not rerun because this change does not modify checkpoint state or shared checkpoint contracts; the existing activation-field gap documented by 005E remains outside scope.

## Validation

The commands use the sibling NPC Generator checkout in `PYTHONPATH` because `npcgen` is not installed in the default interpreter.

- `PYTHONPATH=<LOCAL_HOME_PATH>:$PYTHONPATH python -m py_compile src/activities.py src/transactional_progression.py src/action_evaluation.py src/weapon.py src/arena_browser_session.py examples/arena_web.py tests/test_arena_ready_weapon.py tests/test_generated_arena_browser.py` — passed.
- `PYTHONPATH=<LOCAL_HOME_PATH>:$PYTHONPATH python -m unittest tests.test_arena_ready_weapon tests.test_arena_ground_pickup tests.test_generated_arena_browser tests.test_arena_initialization -q` — **54 tests passed in 19.328 s**. Covers native table values, Quick-draw guard, +1/+2-second boundaries, browser disabled-state presentation, no-request behavior, HTTP refusal, movement, Pick up, observer isolation, and transaction rollback under the explicit test-only eligibility seam.
- `PYTHONPATH=<LOCAL_HOME_PATH>/src:<LOCAL_HOME_PATH>/examples:<LOCAL_HOME_PATH>/tests:<LOCAL_HOME_PATH> python -m unittest test_action_settlement test_atomic_publication test_interval_staging test_transactional_progression test_arena_ground_pickup test_arena_initialization -q` — **248 adjacent tests passed in 91.469 s**, rerun against the committed code.
- `git diff --check` — passed before commits.

## Commits

- `680a1d9 docs(encounters): correct initial weapon-readying authority`
- `bd3c567 fix(arena): fail closed on unknown weapon draw location`
- The final report is committed separately after the adjacent regression rerun.

## Remaining decision/data need

To enable a real initial Draw in the Arena, native state needs an authoritative distinction between a weapon in a drawable location and one stored for variable retrieval. Rules/data must also identify which hand is available; current generated templates do not provide it. If Quick-draw is supported in this path, an integer-boundary policy for its essentially no-time draw must be supplied. Until those prerequisites are established, the browser correctly leaves Ready unavailable.
