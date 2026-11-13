# U-ARENA-004V — Native acquisition of a generated-Arena ground Object

## Outcome

No native ground-item acquisition Action can be implemented without inventing an adopted rule. The largest safe integration slice is now an executable end-to-end fail-closed test: it builds an Arena through the U-ARENA-004S typed ground-Dagger path, uses the real Arena destination/Walk→Sprint movement interface to activate native transactional progression, submits `grab object`, `ready weapon`, and `ready object` through `Encounter.schedule_action`, and verifies native action admission rejects each label before Choice publication. It then advances the same accepted movement plan to exact arrival.

The Object remains the same registered native `WeaponInstance` at the same ground position throughout. The Being retains empty possessions/weapons/armor slots; no load, hand, attack, or protection effect is introduced. The test harness has access to the private fixture ID, but ordinary player projections and subsequent responses never reveal it or the source-local ID. No item button or marker was added.

This is not an acquisition implementation: the accepted native Action pipeline has no reviewed ground-pickup family/effect. The report records the exact narrow rule and engine decisions required before acquisition and readying can be safely scheduled, resolved, and published.

## U-ARENA-004D and adopted authority

- `docs/assignments/U-ARENA-004D.md` is present. Its goal and safety restrictions match this task. I found no U-ARENA-004D report in the checkout and no corresponding completion commit in the reachable Git log; it remains uncompleted here rather than presumed implemented.
- `docs/encounters/README.md` identifies the controlling package as adopted Encounter revision 61, limited revision-62 physical-dimension/reach/throwing supplements, and the revision-63 spatial-precision clarification.
- Revision 61's Throwing section says “anyone can throw just about anything they can pick up” and sets a Strength-based maximum pickup weight through the Carrying Capacity Table. That establishes a lifting/weight limit, but not a ground-object Action, duration, contact/reach test, hand occupancy procedure, transfer/possession effect, or readiness sequence.
- Revision 61's `Grab` section defines a successful touch followed by a one-second Grab against a Being. Its “Grabbing objects” paragraph is specifically for an Object **held by someone else**: an attack roll against the holder's defense and object size plus +5 DC, followed by `Wrest`. `Wrest` is a separate one-second Strength contest to take the Object from that holder. These rules do not specify acquiring an unheld ground Object, and the U-ARENA-004S ground Dagger is unheld.
- The `ready weapon` timing in the weapon section concerns re-readying a weapon after an attack (one-third of weapon timing, rounded down). The distinct “ready and throw” timing applies to preparing a Throw. The rules do not establish the duration/prerequisites for initially readying a weapon acquired from the ground. The special four-second pole-set preparation is not a general weapon-readiness rule.
- Revision 62 and 63 supplements do not add a ground pickup or initial weapon-readiness procedure.

## Native Action status and failure boundary

`src/config/actions.tsv` contains labels `grab object`, `hold object`, `wrest`, `ready object`, and `ready weapon`. The catalog is not the native Action implementation:

- `transactional_progression.validate_action_contract` permits the exact base `Action` only for `swing` and `thrust`; the exact reviewed families are Run, Spot, Throw, melee strike/defense, and limited observer/history actions. A ground-item label is rejected with `UnsupportedEvaluation: unsupported transactional base Action activity` before a Choice draft is accepted or published.
- `action_evaluation.capture_snapshot` and its closed Action-family registry have no ground acquisition or readying family. `action_settlement` supports a closed list of Damage, Fatal, Protection, Practice, Awareness, Defense, and ProjectileRelease effects; there is no possession, held-slot, containment-transfer, or readied-weapon effect.
- Choice reservations derive from the reviewed schedule packet's `active_object_ids` (normally an Action instrument). There is no reviewed ground-target acquisition declaration that reserves a targeted Object through a shared boundary. Adding a resolver without extending those closed contracts would bypass accepted-Choice resource and atomic-publication guarantees.
- Existing `BeingInstance` helpers and body-part/possession fields provide direct setup state, not an Encounter Action lifecycle. They were not called after activation. No Object state was directly mutated by the test.

## Changed files

- `tests/test_arena_acquisition_boundary.py` adds the generated-Arena native-scheduler refusal test and checks unchanged movement, Object identity/position, inventory, Choice state, RNG, clock, and observer projection.
- `docs/reports/U-ARENA-004V-report.md` records this assignment's rules, source/engine evidence, safe result, exact remaining decisions, and verification.

No production Python, browser, catalog, checkpoint, snapshot, settlement, or NPC Generator source was changed because no action rule/effect contract currently supports the requested state transition.

## Integration proof

`tests/test_arena_acquisition_boundary.py` constructs a generated Arena with one caller-authored ordinary Dagger via the 004S typed ground-object input. It checks the Object is registered, uncontained, at its ground position, and unpossessed; the Being has no weapons, possessions, or armor. It confirms player view has no Object key, provenance ID, or name.

The test selects a native destination, changes Walk to Sprint after selection, and confirms the accepted plan uses Sprint and the Encounter is in transactional mode. It then submits each of the three catalog labels (`grab object`, `ready weapon`, `ready object`) as a target-directed base Action through `Encounter.schedule_action`. Each is rejected by the real transactional admission check before Choice publication. For every refusal, the test verifies event history, pending actions, Choice state, RNG cursor, clock, Being/Object positions and equipment state, and public projection are unchanged. Finally, without changing the movement plan, it advances one second at a time to exact destination arrival and verifies the native Dagger identity/state remains on the ground and hidden.

The fixture is explicitly privileged test code: naming the ground ID in the rejected schedule attempt does not mean the player has perceived or learned that ID. No ordinary projection endpoint, UI control, or trace is given the ID. The test does not assert an acquisition outcome or simulate two contenders; with no supported acquisition declaration there is no legitimate same-second action to resolve or reserve.

## Exact remaining decisions

Before implementing the next acquisition slice, the rules owner must establish:

1. Whether a free ground Object is acquired by an ordinary `Pick up` Action or by the existing `Grab object` Action. If `Grab object`, define how the held-by-someone procedure differs for an unheld target.
2. The action duration and any interruption/replacement consequences for a ground pickup.
3. The access relation: touching/contact versus a Reach check, and what constitutes legal reach to a ground item. Arena display-cell membership and the Object's reference point are not body geometry or clearance.
4. The exact successful state transition: possession only, one hand/body-part hold, a native containment relation, or another defined representation; specify how exclusivity and free hand capacity are evaluated. The chosen representation must preserve the same Object ID and weight and must not grant readied-weapon or shield/armor effects before their own prerequisites.
5. Whether initial weapon readying is a distinct Action; its prerequisites, duration, and representation. The existing one-third timing is post-attack re-ready timing and cannot supply a general initial-readying rule.
6. How same-second attempts by two Beings to acquire one Object interact under the common frozen snapshot: whether both may validly succeed, conflict, or use another adopted contest. The existing scheduler's Object-instrument reservations do not decide contested ground pickup.

Once these are adopted, implement the acquisition as a reviewed native Action family with Choice declaration, validation, schedule/reservation identity, pure proposal/effect types, shared-snapshot eligibility, and atomic Object/Being publication. If readying is independently specified, implement it as its own Action. Only then can the browser offer an item action, and only after observer-owned evidence lawfully identifies the item. The existing NPC profile remains caller-supplied; no default loadout was added.

## Verification

All successful commands below passed with no failures or skips. Times are unittest-reported.

| Command | Result |
|---|---|
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_arena_acquisition_boundary.py' -v` | 1 passed; 0 failed/errors/skips; 0.465 s. |
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_arena_ground_objects.py' -v` | 4 passed; 0 failed/errors/skips; 1.915 s. |
| `PYTHONPATH=../npc-generator python -m unittest discover -s tests -p 'test_generated_arena_browser.py' -v` | 23 passed; 0 failed/errors/skips; 7.162 s. Includes shipped JavaScript option-update ordering and server acceptance regressions for U-ARENA-004U. |
| `PYTHONPATH=src:examples:../npc-generator python -m unittest discover -s tests -p 'test_movement_intent.py' -v` | 20 passed; 0 failed/errors/skips; 4.131 s. |
| `python -m py_compile tests/test_arena_acquisition_boundary.py` | Passed. |
| `git diff --check` | Passed. |

The first attempts at this new test used a zero-XP Being and then an unsupported NPC seed; native movement correctly refused those generated conditions. The committed regression uses the same reproducible supported test-world seed and XP premise as the 004S movement proof. Those setup attempts were not passing test runs and are not included in the results table. No common Encounter snapshot, settlement, Choice, publication, or checkpoint primitive was modified, so broad transaction/atomic/checkpoint suites were not run. The pre-existing checkpoint diagnostic mismatch `test_dangling_equipment_and_possessions_refuse` was not exercised or changed.

## Browser, commits, and disposition

No GUI or local browser server was launched. The ordinary browser remains unaware of ground Objects, so this increment adds no acquisition button. The shipped JavaScript handler suite passed. To smoke the movement controls on a real machine, run `examples/generated_arena_browser.py`, generate the Arena, choose a destination, change Walk/Sprint after selection, and advance by one second until arrival; do not expect an item marker or pickup control until an adopted pickup Action and observer-owned evidence path exist.

Implementation/test commit: `0cc2655` (`Verify Arena acquisition actions fail closed`). The report is committed separately immediately afterward. No push, remote changes, Generator changes, or history rewrite. Pre-existing unrelated work remains untouched and unstaged.

Where we stand: the Arena can create ordinary native ground combat Objects and preserve them through player movement, but the native Encounter does not yet define or resolve a ground pickup Action or initial readying Action. The scheduler rejects those catalog labels atomically. The next implementation depends on explicit rule decisions for Action identity/timing, access, custody/hand state, readying, and contested simultaneous acquisition; item information must remain outside the player projection until supported observer evidence exists.
