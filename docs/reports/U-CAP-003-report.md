# U-CAP-003 engineering report

**Status: ACTIVE — this execution advanced the capability but did not satisfy every assignment criterion.** Keep the assignment and report in the active directories. Do not archive either before ChatGPT accepts them. U-CAP-002 remains accepted DONE (bounded); its assignment and consumed report are archived.

## Acceptance status

| Area | Status | Verified outcome and remaining boundary |
|---|---|---|
| A. Draw, Ready, hands and weapon use | Partial | Native Draw accepts supported carried Weapons with explicitly authored worn-sheath location and a represented free hand. Ready remains separate, motion-specific preparation. Generated controls select held non-Dagger Weapons. Tests cover generated Longsword Draw → Ready → two-handed Strike, a prepared Longsword used one-handed with a Medium shield while two-handed use is refused, hand/size constraints, the adopted floor damage multiplier, and fresh-process pending-action restoration. Quickdraw-plus-advanced-skill timing and some preparation/resource combinations remain outside the exercised data contract. |
| B. Shields and equipment resources | Partial | Native and generated Shield bash use a currently held shield's configured motion timing, damage, and penetration; explicit dominant-hand evidence controls the adopted off-hand penalty, and tower shields are refused. The generated Medium-shield bash now resolves after a fresh-process restore. A validated per-Object forearm-buckler attachment preserves protection while leaving the hand available; the attack snapshot applies the adopted -2 same-hand adjustment. General Don/Remove Shield transitions remain unsupported where native shield source/strap and applicable ST inputs are absent. |
| C. Strike Objects and durability | Partial | Native attacks on supported unattended, immobile, nonmagical Objects apply actual hardness and HP and settle atomically. A destroyed Object and native Action receipt restore in a fresh process with the same Object ID and zero HP. Generated Arena accepts opaque held-weapon/Object handles, then resolves the current geometryless-participant scenario as `uncertain_path`; regression verifies no HP loss or RNG advancement. No geometry or clear path was fabricated. |
| D. Generated Arena and persistence | Partial | Generated Arena tests demonstrate Longsword Draw/Ready/two-handed Strike, prepared Longsword with Medium-shield one-handed use and two-handed refusal, and a Shield bash that resolves after fresh-process restoration. Forearm-buckler availability/protection/bash Choice and pending preparation are also restored. Generated Object destruction remains bounded by absent geometry; general Don/Remove remains bounded by absent source/strap/time facts. Evidence is native and generated Arena session/HTTP/shipped-JavaScript automation; no interactive Chrome session is claimed. |

There is no unresolved adopted-rule question in this slice. Remaining blockers are specific missing facts/data: generated Beings lack body geometry, so the evaluator cannot establish that another participant does not obstruct a path to an Object; no shield source/strap transition and ST input are authored for general don/remove; and Quick-draw with advanced weapon skill is essentially no-time while the current scheduler represents only integer-second Actions. Revision 69 does not license inventing a zero-duration scheduled Action. These limits do not justify inventing source, strap, timing, or collision facts.

## Execution interval

| Session | Start (ISO 8601, explicit offset) | End (ISO 8601, explicit offset) | Elapsed (ISO 8601 duration) |
|---|---|---|---|
| Earlier partial execution | 2026-11-13T15:37:40-08:00 | Not recorded | Not calculable; not estimated |
| Current continuation | 2026-11-13T17:09:04-08:00 | 2026-11-13T17:22:47-08:00 | PT0H13M43S |

The earlier interval's start was captured but its end was not; elapsed time is unknown. Other earlier execution intervals were not recorded and are not estimated. The current interval's end was captured immediately before closeout; duration is calculated from the captured timestamps.

## Implementation and verification

- `MeleeStrike` now carries two-handed and shield-bash declarations through native Choice signatures, snapshots, checkpoints, and resolution. Two-handed eligibility requires represented hands and explicit size facts; a next-larger weapon requires both hands without the damage bonus, while same-size-or-smaller ordinary weapons receive `floor(1.5 × weapon damage)` unless explicitly tagged as designed for two-handed use. An occupied second hand and incompatible non-buckler shield use are refused. A generated Longsword-with-Medium-shield scenario confirms the weapon can be Drawn/Readied and used one-handed, while two-handed use is refused.
- Shield bash uses a currently equipped native shield's motion data, refuses tower shields, requires explicit dominant-hand evidence, and applies the adopted non-dominant-hand adjustment unless Ambidexterity is represented. Generated controls pass the selected opaque weapon/shield handle to the native validator.
- Multiple-action Choice validation derives active hand claims from native Action declarations: a two-handed strike claims both represented hands, a one-handed strike claims its weapon hand, Draw claims its selected hand, and Ready claims the held weapon's hand. Overlapping claims are refused with a hand-name-only diagnostic; no native Being/Object identifier is exposed. This supplements existing acquired-skill/priority validation and actual-Object reservations without changing checkpoint schema.
- Forearm-buckler attachment evidence is validated and stored in existing Weapon instance tags. Native Beings recognize an attached buckler as protective without occupying its hand; attack snapshots apply the adopted -2 same-hand penalty. Generated inventory labels the attached forearm and shows the hand empty; the Arena exposes the buckler's configured bash and restores its pending Action with the same Object ID in a fresh process.
- A generated Arena regression authors an equipped Medium shield, declares an explicit initial facing, moves through the native destination route, chooses Shield bash through the Arena control, saves, restores in a fresh OS process, and resolves the same native shield Action. The test accepts the ordinary hit/miss outcomes while requiring the persisted shield and target identities; this is a generated NPC encounter with a test-authored equipment/facing scenario, not a manual Chrome run.
- Draw is no longer Dagger-only. It still requires native custody, an explicitly authored drawable source, and an explicitly free hand. Generated being-target and Object-target controls project held native weapon options; the browser submits opaque handles, while native Action evaluation remains authoritative.
- The shipped-JavaScript melee fixture now waits for the refreshed state after the asynchronous request and verifies the selected weapon handle. Its prior target-only payload and Dagger-era refusal/reason assertions were stale; the adjacent generated Arena tests pass with the current contract.
- A fresh-process native persistence regression destroys a test-authored immobile Object, then restores its same native ID, zero HP, completed `strike object` Action, critical receipt, and Encounter time. This supplements generated Longsword pending/preparation and Shield-bash fresh-process regressions.
- The generated Object-strike HTTP regression follows the accepted Action to resolution. In this scenario the other participant lacks modeled body geometry, so path classification is `uncertain_path`; the test confirms Object HP and session RNG cursor do not change. This is a verified bounded refusal, not a fixture-only success.

Commands were run from the repository root except `test_melee_combat`, whose fixture configuration requires the `tests/` working directory. All commands used the repository `.venv`, with bytecode and user-site writes disabled:

| Command | Result |
|---|---|
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_action_evaluation` | **117 passed**. Includes two-handed damage/eligibility, Shield bash/off-hand/tower, forearm-buckler, and fresh-process destroyed-Object receipt cases. |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_arena_ready_weapon` | **23 passed**. Includes fresh-process Longsword Draw/Ready/two-handed pending Strike, prepared Longsword with shield restrictions, Medium-shield/forearm-buckler bash Choice restoration, and a resolved Medium-shield bash after fresh-process restoration. |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_generated_arena_browser` | **61 passed**. Includes HTTP and shipped-JavaScript controls plus generated Object `uncertain_path`/no-mutation regression. |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_arena_melee_attack` | **17 passed**. Includes target reach/path, native weapon choice, Save/Load, and shipped-JavaScript route. |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_action_choices tests.test_checkpoint_choice_descriptors` | **68 passed**. Includes simultaneous two-handed strike/Draw hand-conflict refusal and checkpoint descriptor regressions. |
| From `tests/`: `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=../tests:../src:../examples ../.venv/bin/python -B -m unittest test_melee_combat` | **11 passed**. |

No full repository suite was run. The generated-Arena `uncertain_path` result is the expected conservative path outcome for unmodeled Being geometry, not a fixture workaround or successful destruction. No actual Chrome/browser session was run.

## TASKS.md state

- U-CAP-003 remains the single ACTIVE program; criteria A–D are not marked complete.
- U-ACT-016 remains PARTIAL (generated Shield bash resolves after fresh-process restoration, including explicit forearm buckler; general Don/Remove transitions remain open).
- U-ACT-018 remains DONE (bounded) for supported held non-Dagger weapon attacks.
- U-ACT-019 remains PARTIAL (native hardness/HP destruction and fresh-process receipt restore; generated destruction is path-limited).
- U-ACT-025 remains PARTIAL (two-handed selection, size/hand restrictions, damage multiplier, and forearm-buckler hand use; other equipment/resource combinations remain open).
- U-CAP-002 remains DONE (bounded) with archived assignment/report references intact.

## Git, audits, and preservation

- Repository: Universe checkout; branch `main`.
- Starting HEAD: `93a997b5e508f9d68ac6be2d0823cb243acd7a79` (`Archive accepted U-CAP-002 and start U-CAP-003`).
- Implementation/test commit: `a209cb7be83cf8ab4a5d94f1d766116eb96c4cfc` (`Add native non-Dagger and shield attacks`).
- Generated Longsword-with-shield regression commit: `1b7be0bb238f3600a7456fe7094480bd5d9f5c6d` (`Cover prepared weapon use with shield equipped`).
- Multiple-action hand-resource validation commit: `2737eea72f2b026af0f9f493c9037330bd9d7cd8` (`Validate overlapping hand-resource claims`).
- Forearm-buckler integration commit: `bb81f798fffb1c0fc4bb22ff7761e5127cbc01dd` (`Model forearm-worn buckler use`).
- Forearm-buckler/two-handed regression commit: `fe88ed3a3a6cae77fed2323739cfbcdc89e8bfaf` (`Verify buckler leaves its hand available`).
- Fresh-process Object destruction, generated Shield-bash resolution, and generated Object-path refusal regression commit: `00451bd830bed3a2a80f0f75aafa3f34be368ca4` (`Verify weapon outcomes across fresh process`).
- Interim documentation commits `8765f7434adbe22321a8d73d20103bf3acb2ceee`, `6cdfe85d1a0c51ae1fef7e81d0f57881afa65d7b`, and `962eb7f61936e3c0d30fef4dae9a714b119b8bd8` updated earlier report snapshots; the current matrix supersedes those interim conclusions.
- Before the implementation commit, the staged path inventory was inspected, `git diff --cached --check` passed, and `.venv/bin/python -B tools/check_publication_safety.py --staged` returned `staged-audit files=16 findings=0 result=PASS`. Before the TASKS/report commit, the same checks returned `staged-audit files=6 findings=0 result=PASS`. The first documentation scan found the absolute local checkout path in this report; it was removed before the passing rerun. Both commits used explicit path lists and excluded unrelated staged U-CAP-002 archival deletions and the user's staged U-THROW-001 archival rename.
- Before commit `00451bd830bed3a2a80f0f75aafa3f34be368ca4`, the staged path inventory was inspected, `git diff --cached --check` passed, and the staged publication audit returned `staged-audit files=7 findings=0 result=PASS`; `git commit --only` included only the three reviewed U-CAP-003 test files.
- After the TASKS/report commit, `git diff --check` and `git diff --cached --check` passed. `git status --short` showed only the pre-existing staged U-CAP-002 archival deletions and U-THROW-001 archival rename; no U-CAP-003 files remained unstaged. No push was attempted.
- `.venv`, ignored `legacy/`, local saved-world data, the independent `npc-generator`, repository backups, and `universe-geology` were not modified. The removed historical `docs/assignments/universe-arena.json` was not recreated or inspected.
