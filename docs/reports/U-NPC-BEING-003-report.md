# U-NPC-BEING-003 — Loopback browser Arena

## Result

Implemented a separate, opt-in local browser Arena for the fixed NPC-generator fixture. Its two explicit controls submit one native Dagger Thrust Choice and then advance the transactional Encounter to the Action's native resolution boundary. The page is labeled as omniscient developer/GM inspection and does not expose an observer endpoint.

## Scope and provenance

- Fixture: `tests/fixtures/external/npcgen-npc-native-skill-candidate.json`
- Verified SHA-256: `e59b55a6c22f822d65716215b64bccf0c1f2c7a42d49036092580d7c470241ae`
- The page keeps source-derived NPC values separate from Arena-authored mechanics. It does not expose the whole source record or unsupported race, class, age, XP, possessions, or HP fields. It states that the imported `armed combat` rank is not a complete revision-60 strategy-pool calculation.
- Only the fixed Action and operation names are accepted. Malformed or extra request fields, unsupported methods, non-JSON requests, repeats, and invalid advance requests are refused. The server binds to IPv4 loopback only.
- On commit, outcome, metadata, causal damage, Target HP, and receipt boundaries are taken from native committed inspection and interval history. Target HP is read from the immutable Target projection (`state.projected_hp`), not a subsequent live Being read. The numerical d20 is not exposed or reconstructed.

## Demonstrated chronology

1. Initial state is at time 0 with no accepted Choice, committed result, or receipt. Read-only page/state requests leave the scenario fingerprint, RNG, and world unchanged.
2. The allowlisted submit operation accepts the fixed native Choice without advancing time or RNG. It exposes the pre-commit state and no Action result.
3. Advancing to scheduled resolution commits at boundary 4. In this fixed scenario native inspection reports outcome `normal`, distance `1.5`, body damage `4`, and Target HP `10 → 6`; native receipts cover boundaries 1–4. The d20 value remains unavailable.
4. Repeated submission and advance are refused without further mutation.

The focused HTTP test exercised the same JSON endpoints used by the page controls, including initial display, pre-commit state, commit, and rejection paths. A manual browser click-through was not completed: the desktop CUA browser bridge returned `native pipe path unavailable`, and its Chrome app inspection timed out. The runnable page is available for direct verification using the command below.

## Files and verification

- `examples/npc_being_arena.py` — split submit from advance; retained `resolve_one_thrust()` as a convenience wrapper; read committed Target HP from inspection.
- `examples/npc_being_arena_web.py` — new loopback-only opt-in web entrypoint and allowlisted JSON API.
- `tests/test_npc_being_arena_web.py` — focused loopback HTTP, privacy/provenance, immutability, progression, outcome, and refusal coverage.

Command (from the repository root):

```sh
python examples/npc_being_arena_web.py --port 8001
```

Then open `http://127.0.0.1:8001/`, submit the fixed thrust, review the accepted pre-commit Choice, and advance to the commit boundary.

Focused verification:

```sh
cd tests
PYTHONPATH=..:../src:../examples python -m unittest \
  test_npc_being_arena_web test_npcgen_being_integration test_npc_being_arena \
  test_melee_combat test_integrated_encounter test_npc_encounter_arena
python -m py_compile ../examples/npc_being_arena.py ../examples/npc_being_arena_web.py \
  test_npc_being_arena.py test_npc_being_arena_web.py
cd ..
git diff --check
```

Result: **29 tests passed in 9.727 seconds** with loopback permission; compilation and `git diff --check` passed. The initial sandbox-restricted run could not bind loopback for the two HTTP cases, so the same command was rerun successfully with loopback permission. Per assignment, the full suite and unchanged Ari/Bex persistence HTTP suite were not run.

## Commit and repository state

- Implementation commit: `d015251c39c2cc39701c41aed81100b203203d8e` (`Add loopback NPC Being Arena`), parent `4514a3b7f859428c54d4b180655e79f119991ab6`.
- The commit contains exactly the three implementation paths listed above. The index is empty after commit.
- The pre-existing working-tree state was preserved: 44 tracked documentation deletions and 18 untracked path entries remain. No unrelated path was staged or committed; no push was performed.

## Remaining limits

This is a local developer-only tool, not a player or authentication boundary. The full revision-60 strategy pool for `armed combat` is not calculated, the d20 is not exposed by native committed inspection, and manual browser click-through remains unverified in this run because the desktop browser-control bridge was unavailable. No native combat or checkpoint code was changed.
