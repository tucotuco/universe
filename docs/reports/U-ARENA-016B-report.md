# U-ARENA-016B — Native offensive Actions and Object interactions

## Result

This increment adds a connected native combat-Object transaction slice to the existing Touch, Feint, and Coup de grace work. It implements Object-targeted melee damage, armed Disarm, and the supported earlier-second Break weapon case, then exposes those supported Actions through the generated Arena's native Action selector and session routes. Object damage and custody changes use the Encounter's frozen evaluation, settlement, receipt, and atomic publication path. The browser submits accepted native Choices; it does not simulate effects.

The shipped Arena's Coup de grace selector and HTTP/session route are also connected to the existing native Coup de grace evaluator. It is offered only when the player-authorized target and held weapon satisfy native eligibility. It does not add an Arena-specific damage or death path.

## Native implementation

### Strike an object

`strike object` and `strike an object` are admitted through native Action scheduling with supported Swing/Thrust weapon timing. The resolver only accepts a currently known, immobile, unattended, nonmagical ground Object with explicit supported hardness and HP. It reuses the native melee hit, critical, weapon damage, and randomness calculations; hardness is applied to each blow. Successful damage is recorded as a native Object HP effect and published atomically with the Action receipt. Destroyed Objects remain the same native Objects with zero HP rather than being deleted or replaced.

Actions aimed at the same Object evaluate against the same frozen pre-Action state; simultaneous Object damage is accumulated and applied together, with hardness retained per blow. Missing material/HP data and unsupported target states are rejected without inventing material properties. Settlement validates the effect and history transition.

### Disarm

The supported armed Disarm branch performs the adopted opposed native attack checks and records the contest margin. On success, native atomic publication releases the exact weapon Object from the defender's hand and custody, preserves its identity, and places it on the ground in the defender's hex. The receipt records the rule-derived maximum landing distance (`floor(margin / 3)`); the present implementation chooses the defender's hex, a legal zero-distance landing. Inspection validates the receipt-backed custody, hand-slot, and spatial-history transition. No Object is deleted or cloned.

### Break weapon

The supported Break weapon case is a native one-second Action against the actual weapon used by an opponent's pending MeleeStrike aimed at the breaker. Scheduling derives the time relationship from the opponent's native weapon Swing timing and the selected native strike. Resolution uses the weapon's native damage and hardness/HP support. A successful Break resolved in an earlier second leaves the weapon unusable; the later attack resolves normally and records `weapon_unavailable`. Same-boundary Actions still use the common frozen snapshot: a Break in that batch does not retroactively cancel a simultaneous attack.

Only the adopted, representable pending-attack case is offered. This does not fabricate an opponent Action or infer a weapon from UI intent.

### Shared custody, history, and persistence

The new drop effect participates in strict settlement validation, atomic publication, inspection, observer proposal validation, and checkpoint reconstruction. It removes the Object from the proper custody/slot, retains the Object's native identity, and appends its native spatial state. Checkpoint closure is extended only for the new typed Action fields/effect. Existing strict identity, receipt, Action-bearing history, RNG ownership, and observer-evidence validation remain active.

## Touch and Coup de grace

Touch retains the existing one-second unwilling-Being opposed branch. Its map eligibility now uses the adopted hex-occupancy personal-reach/path calculation without imposing a facing requirement that Touch rules do not state. A focused native test proves that a Touch in an adjacent one-yard cell can be evaluated while the actor is not facing the target. It still uses the existing transactional Action and no-damage result.

The current native Being/Encounter state does not represent the target's willingness or consent at the Action boundary. Therefore the willing stationary and willing in-motion automatic-contact/Dexterity-check branches cannot be implemented faithfully from authoritative state; the resolver does not infer willingness. Touch alongside another demanding Action remains unavailable until native Multiple Actions/capacity rules are represented.

Coup de grace remains a native helpless-target Action: it uses native weapon timing, reach and damage/protection, automatic critical resolution, then the distinct Fortitude save against `10 + damage dealt` and the established fatal consequence. The Arena selector and route now submit that native Action and report its pending/completed status using player-authorized evidence. Native simultaneous-resolution behavior is retained; Coup does not mutate target HP in a browser handler.

## Browser and persistence integration

The Action catalog includes observer-authorized entries for Swing/Thrust at a supported perceived Object, armed Disarm, Break weapon, Touch, and eligible Coup de grace. Current native prerequisites drive availability and reasons. The shipped selector submits through the Arena session's native Choice scheduling routes. Disarm result presentation reports the public result, margin, and maximum legal landing distance without exposing private simulation identifiers.

The HTTP/session regression saves a pending Disarm, restores it in a separate Python process, continues native resolution, and confirms that the same weapon Object is released to the ground. Existing completed/pending Action Save/Load mechanisms are used; there is no regeneration or effect replay into live state. The Coup path is wired to the native browser/session pathway, and the browser smoke below exercised the shipped Action selector in a launched Arena.

## Verification

- `py_compile` over the changed native Action, evaluation, settlement, checkpoint, inspection, browser-session, server, and test modules: **passed**.
- `.venv/bin/python -m unittest tests.test_action_evaluation tests.test_action_settlement tests.test_generated_arena_browser -q`: **152 passed** in **37.154 s**. Includes native Object hardness/HP effects, simultaneous Object strikes, atomic identity-preserving Disarm, Break timing and next-boundary weapon unavailability, Touch occupancy/facing, Coup simultaneous behavior, Arena routes/catalog, and pending Disarm fresh-process continuation.
- `PYTHONPATH=tests .venv/bin/python -m unittest test_transactional_progression -q`: **61 passed** in **28.550 s**.
- `PYTHONPATH=tests .venv/bin/python -m unittest test_checkpoint_inventory -q`: **30 run, 29 passed, 1 failed**. The failure is `TestCheckpointInventory.test_module_rng_is_not_silently_assumed_private`, which correctly rejects an unbound checkpoint without an explicitly supplied private RNG cursor.
- Baseline proof: checked out pristine archive `c67ec2e` to `<PRIVATE_TEMP_DIR>` and ran the same failing checkpoint test with the project virtualenv. It produced the same `CheckpointRejected: unbound Encounter checkpoint requires an explicitly supplied private RNG cursor` at `checkpoint_inventory.py:318`. The failure predates this change; strict private-RNG checkpoint validation was preserved.
- `git diff --check`: **passed** before the implementation commits. Python compilation and all focused suites above passed after the implementation changes.
- Real-browser smoke: the initial sandbox loopback bind was denied with `PermissionError`. Under the user's scoped approval, only the Arena smoke server was run outside the network-restricted sandbox and bound to ephemeral `127.0.0.1:54541`. Chrome opened the generated Arena, inspected the player's Being, displayed the contextual Action selector, and activated native Run. Break weapon was correctly unavailable with the player-facing reason that no currently perceived pending opponent attack targeted the player. The server was stopped after the smoke. This verifies the shipped browser wiring and native session integration; it does not claim a full real-browser Disarm/Coup combat walkthrough.
- No full repository suite was run. No push or NPC Generator change was made.

## Remaining limits

- **Touch:** willingness is absent from authoritative state, so willing stationary/in-motion and associated Dexterity-check branches remain unsupported. Concurrent demanding Actions remain unsupported pending the Multiple Actions/capacity contract.
- **Disarm:** the armed opposed branch is implemented. Unarmed Disarm and locked-gauntlet behavior have no supported state/rule path. The current legal landing is the defender's hex; choosing among other margin-permitted hexes is not implemented because no direction/cell selection contract exists.
- **Break weapon:** the implemented case requires the opponent's actual pending melee attack against the breaker. Defending against a weapon actively used on somebody else and other source-described variants remain unavailable because the necessary native Action relationships are not represented.
- **Object strike:** only known-hardness, known-HP, immobile, unattended, nonmagical ground Objects are supported. Attended/saving-throw, attached, animated, moving, and unsupported Object categories fail closed.
- **Coup de grace:** the implemented and browser-offered branch is melee. Bow/thrown Coup variants remain unsupported where their native range/impact contracts do not apply.

These are scoped rule/state limitations; no fallback formula, body geometry, willingness, landing direction, or equipment property was fabricated.

## Commits and repository safety

- `5e4c9fb` — `Implement native Object strike and disarm Actions`
- `f3463d8` — `Integrate combat Objects in Arena Actions`
- Prior U-ARENA-016 Touch, Feint, and Coup de grace commits remain in history unchanged.
- Work is on `main`; no push was performed. The pre-existing tracked deletions and unrelated untracked content shown by `git status --short` were preserved and not staged. Only this report is intended for the report commit.
