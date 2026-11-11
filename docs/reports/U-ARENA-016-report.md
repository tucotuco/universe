# U-ARENA-016 — Adopted offensive Combat Actions

## Where we stand

This assignment is **partially delivered and remains incomplete**. The native Arena now accepts, resolves, records, displays, and saves one bounded offensive Action: the one-second opposed-Being branch of **Touch**. It uses the normal Choice scheduler, frozen evaluation, Target-owned receipt, atomic Encounter publication, browser Action selector, and portable Arena file. The native test demonstrates successful contact; the generated browser test exercises an out-of-reach result and pending/completed cross-process persistence. This does not meet the assignment's substantial-coverage success threshold.

The browser path is: generate two Beings with an empty ground profile; activate the Encounter through Run; select the perceived opponent; choose Touch; advance one second; inspect the native committed outcome. At contact range the native evaluator rolls both d20s and compares the Actor's attack total to the target's defense total. A tie or lower Actor total is a miss. Touch has no damage effect. A position outside personal reach resolves as `out_of_reach` before drawing randomness. Arena UI feedback describes that limitation. The implemented path is only for an opposing Being; willingness, dexterity-check branches, and Touch combined with another Action are not implemented.

## Appendix III disposition matrix

“Blocked” below means blocked by missing native engineering contracts unless explicitly marked as a rules gap. Those Actions remain in the normal catalog as unsupported; no placeholder buttons were added.

| # | Action | Native status | Arena availability | Evidence and specific remaining dependency |
|---:|---|---|---|---|
| 1 | Break hold | Blocked | Not offered | No identity-specific Grab/Hold records or grip-continuity schedule exists. `Being.currently_possible_actions` still has a TODO. |
| 2 | Break weapon | Blocked | Not offered | No transactional Object-damage consequence for a held weapon, weapon hardness/HP settlement, or simultaneous nullification of its attack. |
| 3 | Bull rush | Blocked | Not offered | Strength contest inputs exist, but the native movement phase has no contested forced-displacement/occupancy transaction or continuation record. |
| 4 | Pull | Blocked — rules gap | Not offered | Revision 61, Appendix III “Pull,” §§ success/applied force and competing Pulls: the Strength/physical-characteristics-to-newtons and force-to-displacement mappings are explicitly unresolved. A contest result cannot supply force magnitude. |
| 5 | Charge | Blocked | Not offered | No Charge preparation/continuation, engagement state, momentum, or movement-phase attack/interception contract. |
| 6 | Coup de grace | Blocked | Not offered | Native Being helplessness checks exist, but there is no transactional automatic-critical branch with the separate post-damage Fortitude save and death consequence. |
| 7 | Delay | Blocked | Not offered | The scheduler has timed Choices but no adopted trigger/wait record for pausing/resuming an arbitrary Action or changing its resolution boundary. |
| 8 | Disarm | Blocked | Not offered | Custody and hand slots are modeled; no opposed disarm proposal, margin-based landing range, legal ground placement, or atomic release from the defender's hand exists. |
| 9 | End run | Blocked | Not offered | Requires traversed-hex passage, occupied-route contest, and same-boundary route occupancy; the Arena movement contract is destination-based. |
| 10 | Feint | Blocked | Not offered | The attack roll can be reused, but no native receipt carries the success-bound +2 to the next selected attack against the same victim and expires it atomically. |
| 11 | Grab / Hold | Blocked | Not offered | Touch is only the prerequisite branch. Individual grip identity, continuing Hold checks, hand/target custody, and damage-induced release are absent. |
| 12 | Grapple | Blocked | Not offered | No distinct Grapple state/control position, six-second preparation, Grapple contests, Escape checks, or concurrency policy exists. Must remain separate from physical Grab/Hold. |
| 13 | Multiple actions | Blocked | Not offered | Choice supports native Actions, but no declared Multi-action package, timing allocation, shared penalty, or simultaneous action-capacity record exists. |
| 14 | Overrun | Blocked | Not offered | Needs contested movement through an occupied hex, simultaneous occupancy, prone/trample consequences, and legal route state. |
| 15 | Ready | Partial | Native weapon Draw is available where its actual hand/location prerequisites exist. | The browser and native engine support two-second Draw and persist it. Appendix III Ready also covers variable object retrieval/preparation, for which revision 61 leaves timing to referee adjudication and no generalized location model exists. |
| 16 | Shield bash | Partial | No separate Arena choice; current player weapon control selects the committed Dagger. | `MeleeStrike` can consume native shield weapon-table attacks, but the Arena does not select an equipped shield for offense, and the adopted off-hand/Ambidexterity penalty is not represented in native strike resolution. |
| 17 | Shoot | Blocked | Not offered | No native targeted Bow/Crossbow/Catapult release-to-impact Action with hit/miss, target movement, interception, and continuous observer evidence. Existing Throw is not a Shoot substitute. |
| 18 | Strike (Swing/Thrust) | Existing | Available for the initial ready Dagger when target/reach/path rules permit. | Existing `MeleeStrike` performs native Swing/Thrust timing, reach, attack/defense, damage, equipment protection, and receipt settlement. Preserved; no duplicate strike engine added. |
| 19 | Strike an object | Blocked | Not offered | No native object-target strike proposal or hardness/HP settlement; combat evaluation intentionally requires a Being target. |
| 20 | Stun | Blocked | Not offered | No Stun skill attack mode, threat/critical split, Fortitude save, timed stunned-state effect, or reduced-damage settlement. |
| 21 | Subdue | Blocked | Not offered | No separate native subdual-damage balance, hourly fatigue recovery, or simultaneous normal/subdual damage receipt. |
| 22 | Throw | Partial | No player attack control. | Native `ThrowAction` has bounded point-mass release/trajectory support; it does not deliver the Appendix III target hit/miss/interception outcomes at impact. |
| 23 | Touch | Partial (implemented this assignment) | Offered for a currently perceived opposing Being after Encounter activation. | Positive native case: `test_native_one_second_touch_uses_opposed_attack_totals_without_damage`. Browser/HTTP and cross-process pending/completed save/load: `test_touch_uses_native_choice_http_route_and_survives_pending_save_load`. Still missing willing/stationary automatic contact, required Dexterity checks for the other willing cases, and a native declaration for simultaneous Action capacity. |
| 24 | Trip | Blocked | Not offered | No typed prerequisite link to successful Touch/Grab/Bull rush/Strike, Strength-vs-Strength-or-Dexterity contest, prone commit, or cancellation of later pending attacks. |
| 25 | Two-handed strike | Blocked | Not offered | No authoritative per-weapon hand-count/two-hand damage policy or native two-hand custody declaration; hand slots alone do not establish wielding mode. |
| 26 | Undefended attack | Blocked | Not offered | No native fact identifying an aware target as too occupied to defend at the attack boundary. Setting defense to zero from caller preference would invent the condition. |
| 27 | Wrest | Blocked | Not offered | No successful physical Grab prerequisite linked to a Strength contest and atomic transfer of the named Object from one hand/custody to another. |

## Shared implementation and adopted-rule handling

- Exact base `Action` event type `touch` is admitted only through a transactional Encounter. Scheduling requires two distinct participating, aware Beings, no instrument, and exactly one second. It uses the existing Choice/preparation protocol and consumes no random values on admission refusal.
- The evaluator uses the frozen Being dimensions and continuous native positions. It derives personal reach from the existing reference-arm function, then rolls the specified opposed d20 totals only when both Beings are placed and in reach. It records distance and one of the bounded Touch outcomes; it creates no damage/equipment effects. No optical path, body geometry, collision, or movement rule was added for Touch.
- Settlement rejects Touch attack/damage/defense effects and checks its limited outcome/metadata contract. The result is a native Action receipt in the ordinary committed Target history, not an Arena-side result.
- The Arena action catalog and shipped selector present the opposing-Being branch. The `/api/generated/touch` route accepts only a player-authorized handle; it does not expose native target or Action IDs. The view reports accepted/executing/completed state and outcome, and terminal tracing records the accepted Touch and committed result.
- The strict Arena snapshot tag closure now includes the already-adapted native `action.Action` type, so pending and completed Touch Actions reconstruct by native identity. No general checkpoint allowlist was broadened, no Action was regenerated/replayed, and no npcgen state was modified.
- No Save/Load guarantee is claimed for a Touch plus a still-pending movement plan: existing Arena movement-plan checkpoint admission only covers its established initial activation boundary. The new cross-process demonstration saves the pending Touch after activation with no additional movement plan.

## Verification

- `.venv/bin/python -m unittest tests.test_action_evaluation tests.test_action_settlement tests.test_schedule_preparation tests.test_generated_arena_browser` — **161 tests passed in 18.501 seconds**. Includes native Touch success, browser HTTP route, invalid-handle atomic refusal, no target/Action-ID disclosure, pending and completed fresh-process save/restore, and equality with uninterrupted boundary-2 position, Touch result, and RNG state.
- `.venv/bin/python -m unittest tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_touch_uses_native_choice_http_route_and_survives_pending_save_load -v` — **1 passed in 2.460 seconds**, including fresh-process restoration of the pending and completed native Touch boundaries.
- `PYTHONPATH=tests .venv/bin/python -m unittest test_transactional_progression test_checkpoint_inventory` — **91 tests run; 90 passed and one failed** in 42.571 seconds. The failure is existing `TestCheckpointInventory.test_module_rng_is_not_silently_assumed_private`: it calls `capture(self.world, self.enc, quiescent=True)` without an explicitly supplied private RNG cursor, and strict checkpoint capture raises `CheckpointRejected: unbound Encounter checkpoint requires an explicitly supplied private RNG cursor`. Neither checkpoint module nor that test was changed here. The first invocation without `PYTHONPATH=tests` also had two test-loader import errors for sibling fixture modules; the corrected command above ran them.
- `.venv/bin/python -m py_compile src/action.py src/action_evaluation.py src/action_settlement.py src/arena_browser_session.py src/arena_native_snapshot.py src/transactional_progression.py examples/arena_web.py tests/test_action_evaluation.py tests/test_generated_arena_browser.py` — passed.
- `git diff --check` and staged `git diff --cached --check` — passed.
- Loopback browser smoke: the ordinary ephemeral `127.0.0.1` bind failed with sandbox `PermissionError`. After user approval, only the local Arena smoke server was retried outside the restricted sandbox and bound to `127.0.0.1:51987`. The browser security policy then refused opening that local URL. No alternate browser surface, raw CDP, or workaround was attempted; **real browser interaction remains unverified**. Shipped JavaScript string/control wiring and HTTP/session routes are covered by the 161-test suite.
- No full repository suite was run. No push or `npc-generator` modification occurred.

## Commits and repository state

- `11273d2` — Add native Arena Touch Action.
- `c94f5d4` — Verify Touch restart continuation across processes.
- Branch: `main`; these commits follow `18ef9bc`.
- The Touch implementation and tests are committed. The report is committed separately. The supplied U-ARENA-016 assignment and pre-existing tracked deletions/unrelated untracked files remain untouched and unstaged; see the working tree for the complete list.

## Prioritized residual work

1. **Native physical-contact state and movement concurrency:** model individual Grab/Hold identities separately from Grapple, then build their break/escape/wrest/Trip dependencies and simultaneous release behavior. Keep Pull blocked until revision 61's force-to-newtons and force-to-displacement model is adopted.
2. **Native attack consequences and equipment state:** add a reviewed Object-target/hardness/HP transaction, then use it for Strike an object, Break weapon, Disarm, Shield bash, Two-handed strike, Stun, and Subdue only with their distinct adopted consequences and equipment prerequisites.
3. **Action lifecycle and multiple-action semantics:** model Delay/Feint/Coup-de-grace/undefended conditions and multi-action declarations/penalties in native Choice and receipt state before exposing browser controls.
4. **Route/trajectory contracts:** add occupied-route movement for Charge/Bull rush/Overrun/End run and target-bearing impact/interception plus continuous observation for Shoot/Deflect-related projectile cases. This must include simultaneous occupancy and observer evidence rather than browser-only outcomes.
