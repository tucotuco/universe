# U-ARENA-015 — Defensive Actions integration report

## Result

Implemented retained native Dodge and Parry preparation/assignment, completed their generated-Arena controls, and verified that the `defense_only` opponent uses observer-grounded defenses. Existing native Block and movement-backed Yield remain integrated and were re-audited. No adopted Guard Action was found in revision 61's Appendix IV.

The user clarified the two disputed inputs: Dodge's strategy-point pool is governed by Dexterity, with Tumble ranks also added to the pool; learned Tumble separately adds one Dodge point per four ranks. Parry preparation uses the defender's selected swing or thrust timing for the defender's own weapon.

## Six-Action disposition

| Action | Native disposition | Arena availability | Evidence / exact limitation |
|---|---|---|---|
| Block | Implemented. Uses the actual held shield, its native size-based preparation, -4 to the attack roll, effective shield size +1, +2 damage stopped, and occupied shield arm. | Offered only for a currently equipped eligible shield and an observed pending strike. Current standard Arena kit does not guarantee a shield. | Positive and refusal tests in `tests.test_action_evaluation`, `tests.test_arena_opponent_attack`, and `tests.test_generated_arena_browser`; earlier verified commits `1824076`, `1096792`, `5660747`, `6422687`. |
| Deflect | Not implemented; current projectile contract is insufficient for the adopted effect. | Not offered. | `ThrowAction` can publish a bounded drag-free point-mass trajectory, but has no intended target, target hit/miss result, or Missing-rule redirection. The current Arena has no Arrow/Bolt action. Native state also does not provide the continuous observer evidence needed to establish awareness throughout a missile's trajectory. Adding a defense outcome would invent target and impact semantics. |
| Disengage | Not implemented as a separate Action. Ordinary native movement can change position and existing melee reach checks naturally invalidate an out-of-reach strike. | No Disengage option. | The adopted Action requires a faster withdrawal than every pressing opponent along an open path of unoccupied hexes. The movement contract accepts a destination and continuous displacement; it does not validate an unoccupied traversed-hex route or reserve/resolve such a route against simultaneous movement. A Disengage success flag would bypass those missing occupancy facts. |
| Dodge | Implemented as target-free preparation, retained readiness, and one-use assignment before attack outcome. Pool: Dexterity modifier + Tumble ranks − applicable armor check penalty, floored at zero; allocate the whole pool between defense and timing. Tumble adds its separate `rank // 4` Dodge bonus. | Available when the player can allocate the native pool; assignment requires an observer-authorized handle for a currently perceived, pending, in-reach strike. | Native preparation/retention/assignment, attack resolution, refusal, one-use, observer isolation, pending/completed save-load and fresh-process continuation tests pass. `defense_only` NPC prepares only from its own state and assigns only to a perceived player strike. |
| Parry | Implemented as target-free preparation with a selected defender weapon motion, retained readiness, and one-use assignment. Uses the selected weapon's native swing or thrust time minus one second (minimum one), advanced skill, actual custody/held state, incoming-weight limit, and +2 defense against the assigned attack. | Available only with an actually held weapon and advanced skill; UI offers legal weapon/motion options. Assignment requires an observer-authorized handle for an observed pending strike. | Native HTTP/browser route, selected-motion timing, retained assignment, weight/skill checks, ordinary native attack resolution, and save/load continuation covered. `tests.test_arena_opponent_attack.test_retained_target_free_parry_uses_selected_defender_motion_and_native_resolution` exercises the integrated path. |
| Yield | Implemented as one-second committed movement away from an observed attacker, using the accepted native destination and movement-before-Action pipeline; modifies applicable melee attack rolls by −1. | Offered only when a valid accepted destination away from the attacker can be used with the observed pending strike. | Native positive/refusal, same-boundary resolution, persistence, and browser/session integration predate this change; the audit verified the route and preserved the restriction that Yield gives no bonus against archery, catapult, or thrown attacks. |

### Guard audit

Revision 61 Appendix IV names Block, Deflect, Disengage, Dodge, Parry, and Yield. It does not define a sustained Guard defense Action. Guard-like stances in the older tactical prototype are not an adopted production contract and were not added to native Actions or the Arena.

## Implementation

Dodge and Parry now share the native Choice, schedule, event-history, evaluation, and atomic-settlement path. Their preparation Actions contain no attacker or strike identity. Readiness persists in native history. Assignment references that completed native preparation and a currently pending strike; an explicit source identity prevents reuse. Invalid or late assignment is refused before publication. The assigned Action and attack resolve in the same native boundary, and the defense result derives from the ordinary attack result rather than a separate Arena-side roll.

Checkpoint adapters validate the new selected Parry motion, Dodge pool, and preparation reference. Browser requests use observer-owned Being handles and keep preparation Object/Action IDs private. The deterministic opponent policy first prefers a legal Block with a real shield; otherwise it prepares/retains Dodge and assigns only to a strike supported by its own observation. It does not attack under `defense_only`.

## Verification

- Focused and adjacent integration suite: `.venv/bin/python -m unittest tests.test_action_evaluation tests.test_action_choices tests.test_action_settlement tests.test_generated_arena_browser tests.test_arena_opponent_attack -q` — **206 tests passed in 58.577 seconds**.
- This suite includes target-free Dodge preparation using the clarified pool, explicit swing/thrust Parry preparation, positive/negative Block, Yield, player Dodge and Parry lifecycle, opponent Dodge, observer filtering, browser HTTP routes, and fresh-process save/restore continuation.
- Real Chrome smoke against the shipped local Arena: generated equipped Beings with `defense_only`, clicked a map destination, and used **Advance 1 second**. The browser displayed the server-accepted movement; native time advanced from 0 to 1, and the player moved from hex `(3, 4)` / `(2.9, 4.57, 0)` m to hex `(2, 3)` / `(2.41, 3.16, 0)` m with facing updated from 10 to 8. The smoke verified real browser event wiring and native progression; combat-defense outcomes are established by the native and HTTP/session integration tests above.
- `python -m py_compile` on changed Python modules and `git diff --check` passed.
- No unrelated checkpoint fields were admitted; no `npc-generator` changes or push were made.

## Commits

- `5709547` — Implement retained native Dodge and Parry.
- `1e16057` — Expose retained defenses in generated Arena.
- Existing audited defenses retained from `9e1baaa` (Yield) and `1824076`, `1096792`, `5660747`, `6422687` (Block and its Arena eligibility/opponent integration).

## Remaining adopted-rule/data boundaries

Deflect needs a target-bearing projectile hit/miss and Missing-resolution contract plus continuous observer evidence for the entire flight. Disengage needs native open/unoccupied route semantics and simultaneous route occupancy so the speed/path condition can be decided without approximating collisions. Neither limitation is an ambiguity in Dodge or Parry; no further design choice is needed for the implemented work.
