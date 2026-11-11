# U-ARENA-017 — recovery and transactional grappling report

## Where we stand

The current Universe tree does not contain a production transactional Grapple family. It retains older direct duel/combat modules, whose direct mutation and sequential resolution cannot safely enter the current frozen-snapshot transaction. The separate R4.6 workbench contains a bounded two-person algorithm and examples, but explicitly omits damage, movement, multi-attacker and positional variants. I adapted its opposed-check structure to the current Action/Choice/receipt pipeline and adopted revision 61, rather than invoking either older resolver.

The new transactional path implements separate successful Touch evidence → one-second Grab → independently identified Hold with six-second maintenance → one-second Break hold → separately prepared six-second initial Grapple → six-second Escape. Grip and Grapple control have different typed effects and identities. Grapple Escape releases control only; any physical Grip remains. Third-party positive HP damage stages independent per-Grip releases from the strike's committed damage and common pre-action HP. Grapple state is persisted through native checkpoint reconstruction and remains observer-sanitized in Arena.

A real Chrome smoke loaded the shipped generated Arena at `127.0.0.1:55355`, generated a session, opened the player Being popup, and expanded the Action selector. This browser session showed only the player marker; the popup reported native identity/character fields as unknown and the selector showed availability unknown, so it did not complete a physical-contact Action. A browser extension logged an asynchronous-listener error, but the page itself remained usable for Generate and popup interactions. The deterministic generated-Arena HTTP/session integration test did complete Touch/Grab, save/restart Hold, pending Grapple preparation, established control, simultaneous Hold maintenance and Escape, then another fresh-process continuation. The live-browser limit is stated rather than represented as a successful interaction.

## Recovery matrix (27 Appendix III + 6 Appendix IV entries)

“Transactional” means current frozen-snapshot native Action/Choice/atomic settlement; Arena availability is noted separately. Legacy modules remain unsuitable as a transactional resolver unless adapted. “Experimental” refers to `work-stash/universe-fatigue-r4/snapshot/universe-fatigue-workbench/`.

| Adopted Appendix entry | Current transactional state / Arena | Earlier source and disposition |
|---|---|---|
| Break hold | Implemented; Arena selector; one-second per identified Grip | R4.6 `grapple_encounter.py` / `test_resolved_grapple.py` check structure adapted; revision 61 Strength-only contest retained |
| Break weapon | Implemented; Arena selector | Native path in `src/action_evaluation.py`; prior 016B work retained |
| Bull rush | Missing | Legacy `TacticalDuel`/`AgentDuel` calculations are sequential; not safely reused |
| Pull | Missing | Legacy rush calculations are not a native forced-movement transaction; force model and grip-safe displacement still required |
| Charge | Missing | Present only in adopted rules/catalog scope; no current transactional resolver |
| Coup de grace | Implemented bounded weapon branch; Arena | `216a6e0` native transaction and its tests retained |
| Delay | Missing | No admitted timed delay transaction |
| Disarm | Implemented bounded held-weapon branch; Arena | `5e4c9fb` native resolver retained |
| End run | Missing | Movement can be native, but no End Run Action semantics are integrated |
| Feint | Implemented bounded armed branch; Arena | `ef7e811` plus `tests/test_action_evaluation.py` adapted to current transaction |
| Grab | Implemented as one-second post-Touch Action; Arena | R4.6 opposed-check formula/examples adapted; no automatic Grip on Touch |
| Grapple | Partial: initial control and Escape; Arena selector | R4.6 two-person control model adapted; Takedown/Reverse/Pin and conflicting position outcomes remain unsupported |
| Multiple actions | Missing | No native multi-Action declaration/resolution program is connected |
| Overrun | Missing | No current native Action implementation |
| Ready | Ordinary weapon Draw implemented separately; Arena | U-ARENA-005 series native readying path retained; not treated as generic Ready Action |
| Shield bash | Missing | Native shield Objects exist; no shield-bash transaction |
| Shoot | Missing | No supported projectile Action in this Arena path |
| Strike (swing or thrust) | Implemented; Arena | Native transactional melee evaluator and defense pipeline retained |
| Strike an object | Implemented bounded Object damage; Arena | `5e4c9fb` native Object strike work retained |
| Stun | Missing | No current native stun resolver |
| Subdue | Missing | No current native subdual resolver |
| Throw | Narrow native resolver; not available in Arena selector | `src/action_evaluation.py` admits a limited parameter bracket; no Arena control for its load/trajectory inputs |
| Touch | Implemented; Arena | `11273d2` native Touch path retained; successful Touch receipt gates separate Grab |
| Trip | Missing | Historical direct melee code is not used by transactional progression |
| Two-handed strike | No supported two-handed transactional branch | Existing single-weapon Swing/Thrust does not establish two-handed handling |
| Undefended attack | No distinct Action | Current melee uses defense/awareness rules; label is not an independent native resolver |
| Wrest | Missing | No current transactional resolver |
| Block | Implemented; Arena | `1824076` native shield Block retained |
| Deflect | Missing | Legacy/direct calculation only; not routed through atomic Encounter settlement |
| Disengage | Missing | No current native Action implementation |
| Dodge | Implemented; Arena | `5709547` native transactional defense retained |
| Parry | Implemented; Arena | `5709547` native transactional defense retained |
| Yield | Implemented; Arena | `9e1baaa` native Yield retained |

The legacy code searched was `src/tactical_duel.py`, `src/ai_duel.py`, `src/melee_combat.py`, and `src/melee_defense.py`; those sequential facades were not called by the new path. The relevant R4.6 references are `RESOLVED-GRAPPLE-VALIDATION.md`, `grapple_encounter.py`, and `test_resolved_grapple.py`. Their two-participant algorithm is experimental provenance, not current Encounter state.

## Native chain evidence

The focused native test `test_native_touch_grab_hold_break_grapple_and_escape_use_separate_receipt_state` resolves successful Touch at boundary 1, separate successful Grab at boundary 2, Hold maintenance at its six-second due boundary, winning Break hold on that single Grip, a second separately identified Grip, initial six-second Grapple control, then Escape. It asserts that Touch alone creates no Grip, successful Grab creates one Grip, Break hold affects only its selected Grip, Escape removes control while preserving the other Grip, and the effects appear in committed Target-owned history.

`test_third_party_positive_hp_damage_releases_each_physical_grip_transactionally` supplies one damaging third-party strike to an actor holding two distinct Beings. Each Grip receives a separately staged release effect from the same pre-action holder HP, with no direct handler mutation. Damage settlement and release share the frozen snapshot and one atomic commit.

The Arena integration `test_grab_selector_http_receipt_and_fresh_process_hold_continuation` uses generated Beings and the existing observer-owned target handle. The fixture authorizes contact range/empty hand and improved-grapple ranks as explicit test-world inputs; it does not manufacture production geometry. HTTP Grab is accepted through the selector, and opaque Action/Grip IDs are not returned as private view state. Separate child processes save/restore a maintained Hold, pending initial Grapple, established control and simultaneous Escape/Hold maintenance; the last restored process verifies the surviving physical Grip and ended Grapple control. This exercises the existing Arena versioned snapshot, native identity bindings, receipt/history reconstruction and RNG/Choice continuation.

## Rules, boundaries, and reuse

- Grab uses the adopted opposed `3d6 + Improved Grapple + better applicable STR/DEX bonus + applicable modifiers`; the initiating participant must win, ties establish no Grip. It requires a separate successful native Touch receipt and a represented free hand.
- Each Grip has a stable state ID, hand and next six-second check. Hold maintenance is its own one-second Action. Failed/tied maintenance releases only that Grip. Break hold is a one-second opposed `3d6 + Strength bonus`; Escape Artist is not used.
- Initial Grapple is a separate six-second check tied to a qualifying Grip maintenance boundary. It substitutes for that same Grip's Hold check. Failed/tied initiation keeps the Grip. Established control is a separate state and does not depend on later Grip retention.
- Escape is a six-second opposed Grapple check with the escaping participant's Escape Artist ranks added once. Success releases control only; failure maintains it. The native state remains checkpoint portable.
- Damage-induced release is considered only for positive body HP damage after protection, uses the strike's positive damage over the holder's common pre-action HP, is independent per Grip, and is staged with the same simultaneous batch. No release is inferred from equipment-only damage or nonpositive pre-action HP.
- Movement that demonstrably increases separation across a physical Grip is refused by the existing movement transaction. Joint movement, reduced separation and stationary movement remain possible where native movement prerequisites pass. The implementation does not freeze all held Being movement.
- No body shape, occupied-space collision, pull-force formula, effective species size, multi-grappler bonus, willing/immobilized automatic success, or unsupported capacity is inferred. Multi-attacker position modifiers cannot be derived because the current generated Being model does not supply adopted effective size categories.
- Advanced Takedown, Reverse, Pin, incompatible simultaneous position outcomes, and multiple-grappler conflicts remain partial. Voluntary release's exact Action/timing declaration and immediate cancellation of an unestablished Grapple when its last Grip releases before its initial check are also not implemented; no free release/cancellation is fabricated. The established Grapple remains independent of later Grip loss as revision 46 requires.
- The experimental formula was reused only where revisions 30–48 and revision 61 agree. Evaluation, typed effects, identities, rollback, Target-history issuance, observer projections and reconstruction were rewritten/adapted for the existing native Encounter transaction; the workbench resolver itself is never invoked.

## Verification and delivery

Focused commands:

- `PYTHONPATH=tests .venv/bin/python -m unittest test_action_evaluation.TestActionEvaluation.test_native_touch_grab_hold_break_grapple_and_escape_use_separate_receipt_state -v` — passed.
- `PYTHONPATH=tests .venv/bin/python -m unittest test_action_evaluation.TestActionEvaluation.test_third_party_positive_hp_damage_releases_each_physical_grip_transactionally -v` — passed.
- `PYTHONPATH=tests .venv/bin/python -m unittest test_generated_arena_browser.TestGeneratedArenaBrowser.test_grab_selector_http_receipt_and_fresh_process_hold_continuation -v` — passed (fresh-process Arena save/resume).
- `PYTHONPATH=tests .venv/bin/python -m unittest test_action_evaluation test_action_settlement test_generated_arena_browser test_movement_intent -q` — **178 tests passed**, 68.294 s.
- `PYTHONPATH=tests .venv/bin/python -m unittest test_checkpoint_inventory test_checkpoint_reconstruction test_arena_checkpoint_activation test_arena_local_checkpoint test_checkpoint_restore_continuation -q` — **49 tests, 6 errors and 2 failures**, 26.154 s. The six Run/Spot reconstruction errors and the subprocess reconstruction failure share the pre-existing unsupported Arena-perception-ledger adapter at `src/checkpoint_reconstruction.py:585`; a clean `git archive HEAD` at `fb7df35` reproduced the same blocker in three representative inventory/reconstruction tests (one RNG-privacy error and two ledger-adapter errors). The other failure is the loopback-bound operator HTTP test; rerunning only `test_arena_local_checkpoint.ArenaOperatorHTTPContinuationTests.test_two_process_browser_save_approved_reopen_run_and_native_commit` outside the network-restricted sandbox passed (1 test, 7.823 s). No checkpoint validator was loosened.
- `.venv/bin/python -m py_compile ...` over every changed Python module and `git diff --check` — passed.

No `npc-generator` files were touched; no push was performed. Implementation/tests are committed as `1a28aec` (`Integrate transactional physical contact and grappling`). The pre-existing tracked deletions and untracked files were preserved and excluded from staging. The report is a separate follow-up documentation commit.
