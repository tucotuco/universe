# U-ARENA-001 — Native Encounter Arena report

## Result

Implemented a runnable two-candidate Arena in which NPC Generator exports are preserved as source provenance and bound to distinct native Universe Beings. A revision-60 six-second Spot resolves through native transactional scheduling/publication and is inspectable through committed developer inspection.

## Commits and changed paths

Starting checkout: `main` at `fd9910d29b18eecd552772c0e36d927897b5de4d`; the index was empty. Implementation commit: `139d0d8da15786018e2c6dda081776499aff0ecc` (`Add native NPC candidate Encounter Arena demo`). It contains exactly these 10 paths:

- `src/arena_npc_import.py`
- `examples/npc_encounter_arena.py`
- `examples/npc_candidates/ari.npcgen.json`
- `examples/npc_candidates/bex.npcgen.json`
- `tests/test_npc_encounter_arena.py`
- `TASKS.md`
- `docs/tasks/encounter-engine.md`
- `docs/tasks/generation-and-attention.md`
- `docs/tasks/broader-universe.md`
- `docs/design/Universe-Playground-Revised-Roadmap.md`

This report is committed separately as a documentation-only closeout. No source, tests, or rules changed in that second commit.

## Demonstrated Arena and data boundary

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python examples/npc_encounter_arena.py
```

The example reports Ari and Bex at Arena-authored Cartesian positions `(0,0,0)` and `(3,0,0)`, with distinct native IDs `arena/being/ari` and `arena/being/bex`. Their explicit native definition is Universe `Human`; the authored geometry is `Sphere(0.5)`. These are scenario inputs, not translations of NPC dimensions.

Both fixtures are exact JSON output from the current local NPC generator's `Generator.roll_random(seed)`, a recorded name edit, and `persist.to_json`: seeds 71401/Ari and 71402/Bex. Re-running the exporter and byte-comparing its output to each fixture returned `exact_export_match=True`. Both record engine version `2.1.0` and rules hash `sha256:78e8a2bc8e7dc7ba635f8ab6d8bdf8174c35608c9af04b6533cc3d84c46865ff`.

The import boundary retains the full original UTF-8 source bytes and their SHA-256 digest; the digest is not used as a person ID. A separate explicit binding key and native ID identify each participant. Exact binding retry is idempotent; identity collisions and conflicting binding reuse refuse. NPC name maps to the native display name only. Race, scores, class/level/XP, source HP, psionics, dimensions, possessions, and family remain source-only. The generator model has no discrete Universe skill list. No population, genealogy, inventory, ability, skill, HP, or Belief effect is inferred.

The developer-labeled timeline shows Spot accepted at t=0 and committed at boundary 6, roll 20 against DC 15, with one-second committed boundaries 1 through 6. Ari receives Awareness of Bex; Bex receives none. The check is scenario-authored and consumes no authoritative RNG. The target ID is scenario-known for this deliberate targeted Spot; the example does not solve initial unknown-target selection. A roll-1 case commits without Awareness. An injected observer-phase publisher failure preserves the first five committed boundaries, rolls back boundary 6, and succeeds on deterministic retry.

## Verification

- Focused Arena, Spot, and attention tests: **22 passed**.
- Demo command above: passed; output showed the expected committed success and observer-specific Awareness.
- Candidate fixture regeneration and byte comparison: both exact exports matched.
- Python compilation: `PYTHONPYCACHEPREFIX=<temp-cache-dir> python -m py_compile src/arena_npc_import.py examples/npc_encounter_arena.py tests/test_npc_encounter_arena.py` passed.
- Relative Markdown links in the five updated task/roadmap files: no broken links. `git diff --check` passed; one extra blank line at EOF in the new importer was removed before commit.
- Full HTTP-inclusive suite: `PYTHONDONTWRITEBYTECODE=1 sh run_tests.sh` with loopback permission ran **1,712 tests**. HTTP tests completed; **one unrelated failure remains**: `test_exertion.TestExertion.test_check` expects `Exertion.check(20)` always to succeed. The existing `src/utils.py::ability_check` returns `ability_value > roll_dice("1d20")`; a natural 20 therefore fails the strict comparison. No exertion or utility files were changed. A preceding sandbox-only attempt could not bind local HTTP test servers; the permitted rerun resolved those setup errors.

## Limitations and preservation

This is a CLI/developer inspection slice, not an interactive browser Arena, player view, general source-to-Being mapping, or portable save/resume. Active NPC-generator abilities, race/species, HP, XP, skills, equipment, dimensions, and family semantics remain unsupported. Binding state is in-memory and scoped to this Arena session. The nested NPC-generator source is locally readable but has no independent Git metadata; its repository revision cannot be established. Its source/configuration files were not modified. BattleCode Web remains untouched and clean; `legacy/`, saved examples, workspace JSON, `.agents/`, `.claude/`, and other unrelated untracked files were not staged or committed.

## Next bounded increment

U-ARENA-002 is recorded as planned: a minimal interactive surface that submits only supported native Choices and reads committed and observer-filtered views. Keep Universe as the sole resolver; do not route transactional progression through the legacy `TacticalDuel` facade. General checkpoint closure and NPC mechanical mappings remain separate work.
