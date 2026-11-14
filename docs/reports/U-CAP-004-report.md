# U-CAP-004 — Targeted ranged combat

**Status: DONE (bounded), awaiting ChatGPT report review.** The original U-CAP-004 acceptance criteria A–D are met for the adopted and represented domains. The report remains active until reviewed and accepted; the assignment remains in the active directory until its completion is confirmed.

## Execution interval

- Start time: 2026-11-13T18:48:00-08:00 (captured when execution began)
- End time: 2026-11-13T20:56:36-08:00 (captured immediately before final closeout)
- Elapsed time: PT2H8M36S

## Acceptance matrix

| Criterion | Result | Evidence and boundary |
|---|---|---|
| A. Targeted Throw, flight, impact, custody | **Implemented for the supported Strength-10 bracket.** | Generic explicit-weight Objects and held weapons with an authored four-second ranged profile release as the same native Object, retain full-precision one-second flight state, and resolve at the first committed boundary at/after impact. Arrival attacks use target defense, moving/size/posture/range modifiers, standard critical/fatal/save handling, damage, shield/armor, and atomic effect settlement. Misses record d8 direction and `miss_unresolved` without fabricating a landing point. A target no longer at the selected aim point gets no retroactive roll or damage. Tests cover Dagger custody/profile, deterministic hit/miss, movement-away, simultaneous same-target impacts, rollback, and continuation.
| B. Shoot | **Bounded by missing adopted launch facts.** | The adopted bows table supplies timing, range, and damage/penetration but not arrow velocity or flight-time data. There is no supported native arrow/ammunition identity and release contract. Generated-Arena Shoot requests are explicitly refused before time, pending Actions, or RNG change. Throw velocity is not substituted for bow physics.
| B. Ranged Coup de grace | **Implemented for held four-second thrown weapons, bounded.** | Requires an aware helpless target within one horizontal yard, a held thrown weapon with an authored range profile, and an able actor. Arrival auto-hits and critically damages, then makes the adopted Fortitude save against DC 10 plus damage. Native and generated Action-program tests pass. Bow delivery remains bounded with Shoot.
| C. Missing and target movement | **Bounded behavior implemented.** | Failed arrival rolls store d8 direction and explicit unresolved destination. If the target leaves the aim point before arrival, the projectile is recorded at its known trajectory point with `target_moved`; no roll or damage is made. Incidental interception, scatter distance, and recovery are not inferred.
| C. Deflect | **Bounded refusal; continuous-awareness evidence is absent.** | Current observer-owned Spot records can show a committed projectile observation, but do not establish that a defender was aware of that missile throughout its entire trajectory before a timed Deflect. A successful redirection also depends on Missing destination data. Generated-Arena Deflect requests are explicitly refused before time, pending Actions, or RNG change. No Reality-only awareness or invented destination is used.
| C. Simultaneous attacks / protection | **Supported Throw subset implemented.** | Multiple same-boundary projectile arrivals use stable release-identity order for deterministic RNG while all attack/defense facts are read from the common post-movement/pre-action snapshot. Damage stacks and settlement order is independent of declaration order. Active Deflect interactions and unsupported collision geometry remain outside this bounded result.
| D. Generated Arena | **Implemented through the generated-Arena HTTP/session Action-program route.** | Reproducible `npcgen` generated-Arena tests declare targeted Throw using an opaque perceived-Being handle and player-owned projectile handle, then demonstrate actual hit/damage and, in another generated scenario, a d8 miss with unresolved destination. Held Dagger and eligible thrown Coup de grace controls are tested. HTTP responses contain no native identity.
| D. Save/Load and privacy | **Implemented for pending Throw, flight, and resolved Throw.** | A `python -S` fresh-process test saves pending Throw state, resumes through release and flight, saves again, and independently reloads after impact. It checks exact Object identity, boundary history, actual hit/miss, HP, direction/damage, and RNG continuation. Public status uses opaque handles and exposes only player-owned projectiles or player-authorized observations.
| D. Actual Chrome | **Live application inspected; manual impact scenario not completed.** | The existing Chrome tab showed the running Universe Arena player interface. Its selected session had no known authorized projectile/equipment evidence; this execution did not mutate that preexisting session to manufacture a result. Native and HTTP/session claims above come from reproducible generated-Arena automated scenarios, not a claimed manual Chrome win.

## Rules, fixture assessment, and boundaries

- Applied the adopted **attack roll at arrival** rule: success applies damage when the projectile reaches the target's represented position, without adding body geometry; failure records the adopted d8 direction and leaves destination unresolved.
- Full-precision world-space trajectory uses adopted drag-free throwing equations and `g=10 m/s²`; generated Being release height comes from measured stature. Action completion is distinct from impact; impact is processed at the next integer Encounter boundary after its calculated time.
- Throw eligibility remains the authored Strength 10, positive weight no greater than 3.3 lb, four-second preparation bracket. Held thrown weapons additionally require a native weapon R profile with four-second timing, damage, and penetration. No generic profile is inferred from catalog labels.
- Damage and armor/shield durability use ordinary native effects and atomic publication. Simultaneous impacts are stable by release-effect identity. Failed or rolled-back boundaries preserve time, projectile, effects, and RNG.
- A target that moved off the selected point is `target_moved` with no attack roll. Intervening entity collision, physical body geometry, cover volume, deflection path, incidental interception, and miss distance are not modeled.
- Shoot is bounded because adopted bow rules do not supply arrow velocity/flight time or a native ammunition release lifecycle. Deflect is bounded because observer-owned whole-trajectory awareness and redirected destination evidence are absent.
- The two older U-CAP-003-adjacent persistence fixtures were investigated without weakening `uncertain_path`. The three-process ground-object continuation now chooses a generated, represented clear route long enough to remain pending across the first boundary. The pending-pickup fixture uses a generated seed whose Dagger has an adjacent clear route. Both now pass. The original failures were test-authored paths through geometryless Objects, not a missing clearance rule or Arena persistence implementation.
- A broader melee/attack regression command was interrupted during its long fresh-process Charge test; it is **not counted as passing**. No full repository suite or manual browser impact scenario is claimed.

## Focused verification

Final combined focused command:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_native_throw_arena tests.test_native_throw_concurrent_run tests.test_native_throw_spot tests.test_arena_persistence.TestArenaPersistence.test_generated_throw_pending_and_in_flight_survive_fresh_process tests.test_arena_persistence.TestArenaPersistence.test_repeatable_three_process_continuation_with_ground_objects tests.test_arena_persistence.TestArenaPersistence.test_pending_pickup_save_load_keeps_exact_one_second_boundary tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_generated_arena_action_program_declares_targeted_throw_by_opaque_handles tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_generated_arena_targeted_throw_miss_records_direction_without_destination tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_generated_arena_declares_a_held_dagger_throw_by_opaque_handles tests.test_generated_arena_browser.TestGeneratedArenaBrowser.test_generated_arena_offers_thrown_coup_de_grace_for_eligible_aware_target tests.test_arena_ground_objects tests.test_arena_complete_profiles_and_kits -v
```

Result: **42 tests passed in 54.921 seconds.** This includes exact fresh-process hit/miss outcomes, the new shield/armor impact regression, both repaired geometryless-Object movement fixtures, and generated-Arena Shoot/Deflect no-mutation refusals.

Other separately completed focused checks: target movement-away/generated hit/generated miss/fresh-process persistence (4 passed); simultaneous arrival order and movement-away (2 passed); native/generated ranged Coup de grace plus held-Dagger declaration (3 passed); and native/generated Coup de grace after the fresh-process experiment was removed (2 passed).

## Git and closeout evidence

- Assignment-start HEAD: `103e29c37c06d893f3163bf9dbbbfe42938aba21`.
- Startup state/archive reconciliation: `c62b05c51ce298886af7168f7aac16b52f421d17`.
- Projectile precision: `0c5f1efc8b953429c3e4f81a1b07280e4a6de4`.
- Fresh-process flight state: `fc09da35ac5861d00ccf6abd5ee707b5175875da`.
- Generic generated-Arena Throw Objects: `7e672d26daa0c421112c6190352763db61d3a976`.
- Arrival attack/damage, miss, simultaneous impacts, movement-away, thrown Coup de grace and related UI/tests: `f52e7a8da29275d9a20c5c1cd50b454fae62dce9` (`Complete targeted Throw impact and ranged coup`).
- Bounded Shoot/Deflect request refusals and stronger resolved-impact persistence assertion: `736ef028780d9eea98bb669263cb7667e60835cb` (`Fail closed for unsupported ranged actions`).
- Fixture and native shield/armor regression plus task-state reconciliation: `3226db030dba4dd1b3fe714c22126cd7d5cdb89a` (`Verify ranged combat fixtures and status`).
- The report closeout is included in an audited documentation commit. The unrelated staged U-CAP-002 archival deletions and U-THROW-001 patch archive rename remain outside all U-CAP-004 commits. No push has been performed.
