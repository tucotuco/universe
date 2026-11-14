# U-CAP-003 engineering report

**Status: ACTIVE — this execution advanced the capability but did not satisfy every assignment criterion.** Keep the assignment and report in the active directories. Do not archive either before ChatGPT accepts them. U-CAP-002 remains accepted DONE (bounded); its assignment and consumed report are archived.

## Acceptance status

| Area | Status | Verified outcome and remaining boundary |
|---|---|---|
| A. Draw, Ready, hands and weapon use | Partial | Native Draw accepts supported carried Weapons with explicitly authored worn-sheath location and a represented free hand. Ready remains separate, motion-specific preparation. Generated controls select held non-Dagger Weapons. Tests cover generated Longsword Draw → Ready → two-handed Strike, hand/size constraints, the adopted floor damage multiplier, and fresh-process pending-action restoration. Quickdraw-plus-advanced-skill timing and some preparation/resource combinations remain outside the exercised data contract. |
| B. Shields and equipment resources | Partial | Generated and native Shield bash use a currently held shield's configured motion timing, damage, and penetration; explicit dominant-hand evidence controls the adopted off-hand penalty, and tower shields are refused. Pending bash Choice restores in a fresh process. The native Being model has no forearm/strap attachment slot, so buckler same-hand use and timed Don/Remove Shield transitions cannot be represented without extending native equipment state and its authored source/attachment contract. No equipment state is inferred. |
| C. Strike Objects and durability | Partial | Native attacks on supported unattended, immobile, nonmagical Objects apply actual hardness and hit points and settle atomically. Generated Arena exposes held-weapon and Object selectors and accepts the opaque handles, but a generated destruction outcome is not demonstrated: the other generated Being has no modeled geometry, and the conservative physical-path evaluator returns `uncertain_path`. No geometry or clear path was fabricated. |
| D. Generated Arena and persistence | Partial | Generated Arena tests demonstrate Longsword Draw/Ready/two-handed Strike and Medium-shield bash controls, pending native Choice persistence in fresh OS processes, and the selected-weapon browser route. The generated Object-destruction and complete shield-wearing lifecycle cases remain unverified for the native-data boundaries above. Evidence is native and generated Arena session/HTTP/shipped-JavaScript automation; no interactive Chrome session is claimed. |

There is no unresolved adopted-rule question in this slice. The remaining limits are implementation/data-model boundaries: native Beings expose hand slots but no forearm attachment state for bucklers; native weapon draw locations are explicit, but shield attachment/source transitions and their ST timing conversion are not represented; generated Beings lack body geometry, which keeps Object paths uncertain. These limits do not justify inventing hand, strap, timing, or collision facts.

## Execution interval

| Session | Start (ISO 8601, explicit offset) | End (ISO 8601, explicit offset) | Elapsed (ISO 8601 duration) |
|---|---|---|---|
| Current execution | 2026-11-13T15:37:40-08:00 | Pending final closeout capture | Pending |

Earlier U-CAP-003 execution intervals were not recorded in this report, so no estimate is provided for them. The interval above is the captured active execution interval for this report update.

## Implementation and verification

- `MeleeStrike` now carries two-handed and shield-bash declarations through native Choice signatures, snapshots, checkpoints, and resolution. Two-handed eligibility requires represented hands and explicit size facts; a next-larger weapon requires both hands without the damage bonus, while same-size-or-smaller ordinary weapons receive `floor(1.5 × weapon damage)` unless explicitly tagged as designed for two-handed use. An occupied second hand and incompatible non-buckler shield use are refused.
- Shield bash uses a currently equipped native shield's motion data, refuses tower shields, requires explicit dominant-hand evidence, and applies the adopted non-dominant-hand adjustment unless Ambidexterity is represented. Generated controls pass the selected opaque weapon/shield handle to the native validator.
- Draw is no longer Dagger-only. It still requires native custody, an explicitly authored drawable source, and an explicitly free hand. Generated being-target and Object-target controls project held native weapon options; the browser submits opaque handles, while native Action evaluation remains authoritative.
- The shipped-JavaScript melee fixture now waits for the refreshed state after the asynchronous request and verifies the selected weapon handle. Its prior target-only payload and Dagger-era refusal/reason assertions were stale; the adjacent generated Arena tests pass with the current contract.

Commands were run from the repository root except `test_melee_combat`, whose fixture configuration requires the `tests/` working directory. All commands used the repository `.venv`, with bytecode and user-site writes disabled:

| Command | Result |
|---|---|
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_action_evaluation` | **113 passed**. Includes two-handed damage/eligibility and Shield bash/off-hand/tower cases. |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_arena_ready_weapon` | **20 passed**. Includes fresh-process Longsword Draw/Ready/two-handed pending Strike and Shield bash Choice restoration. |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_generated_arena_browser` | **61 passed**. Includes HTTP and shipped-JavaScript controls; generated Object-destruction is not claimed. |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_arena_melee_attack` | **17 passed**. Includes target reach/path, native weapon choice, Save/Load, and shipped-JavaScript route. |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest tests.test_action_choices tests.test_checkpoint_choice_descriptors` | **67 passed**. |
| From `tests/`: `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=../tests:../src:../examples ../.venv/bin/python -B -m unittest test_melee_combat` | **11 passed**. |

No full repository suite was run. The generated-Arena `uncertain_path` result is the expected conservative path outcome for unmodeled Being geometry, not a fixture workaround or successful destruction. No actual Chrome/browser session was run.

## TASKS.md state

- U-CAP-003 remains the single ACTIVE program; criteria A–D are not marked complete.
- U-ACT-016 remains PARTIAL (Shield bash; Don/Remove and buckler attachment/use remain open).
- U-ACT-018 remains DONE (bounded) for supported held non-Dagger weapon attacks.
- U-ACT-019 remains PARTIAL (native hardness/HP settlement; generated destruction is path-limited).
- U-ACT-025 remains PARTIAL (two-handed selection, size/hand restrictions, and damage multiplier; remaining equipment/resource combinations are open).
- U-CAP-002 remains DONE (bounded) with archived assignment/report references intact.

## Git, audits, and preservation

- Repository: Universe checkout; branch `main`.
- Starting HEAD: `93a997b5e508f9d68ac6be2d0823cb243acd7a79` (`Archive accepted U-CAP-002 and start U-CAP-003`).
- Implementation commit: `a209cb7be83cf8ab4a5d94f1d766116eb96c4cfc` (`Add native non-Dagger and shield attacks`).
- Before the implementation commit, the staged path inventory was inspected, `git diff --cached --check` passed, and `.venv/bin/python -B tools/check_publication_safety.py --staged` returned `staged-audit files=16 findings=0 result=PASS`. The commit used an explicit path list; it did not include unrelated staged U-CAP-002 archival deletions or the user's staged U-THROW-001 archival rename.
- Documentation closeout commit and final working-tree audit are recorded after the final report/TASKS edits. No push was attempted.
- `.venv`, ignored `legacy/`, local saved-world data, the independent `npc-generator`, repository backups, and `universe-geology` were not modified. The removed historical `docs/assignments/universe-arena.json` was not recreated or inspected.
