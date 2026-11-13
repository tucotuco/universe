# U-REPO-010 — Copy and validate the preserved Python environment

## Result

**REUSABLE WITH LIMITATIONS.** At the user's direction, I copied the preserved venv as-is with `cp -a ../universe-old/.venv .venv`. The copy at `universe/.venv` now runs the new checkout's Universe source, imports the sibling `npcgen` 2.1.0 source and callable Arena-ready API, and passes focused Generator-backed Arena initialization, kit/profile, native movement, publication-safety, and loopback HTTP/session tests.

One existing NPC native-Being integration assertion fails because it expects a pre-truncation float value (`49.59000015258789`) while the current native value is `49.59`. No implementation or test was changed. HTTP test imports need a one-process ordering shim because example scripts shadow source modules with the same names. No real GUI/browser smoke was run.

## Checkout and environment

- New checkout: branch `main`, HEAD `d59bc7d495e5d4fbd3ccbe43f8e65296d63bf2af`; `origin/main` matched by read-only `git ls-remote`, local divergence `0 0`, and ancestry check passed.
- The copy source was `../universe-old/.venv`; the destination did not exist before the copy. The original venv and `../universe-old` checkout were not modified. No package was installed, no venv repair was made, and no separate environment was created with `venv` or `python -m venv`.
- The copied interpreter runs Python **3.14.3**; `sys.prefix` resolves to the new `universe/.venv`, `sys.base_prefix` is distinct, and the configured base interpreter exists. The copied `pyvenv.cfg`, activation script, and `pip` shebang all point to the new `universe/.venv` location as expected. Unlike direct invocation through the old relative path, the copied environment emits no `sys.prefix` warnings.
- Use the copied interpreter from the new repository root: `.venv/bin/python`. For repository tests, set `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=tests:src:examples` and pass `-B`; `python -m unittest` and `python -m pip` work.
- Native Universe imports (`being`, `encounter`, `arena_initialization`, `arena_browser_session`, and `arena_web`) resolve from the new checkout. `npcgen.__version__` is **2.1.0**, and `npcgen.api.arena_ready_being` is callable. `npcgen` comes from `../npc-generator/npcgen` through an absolute symlink in the copied environment, so reuse still depends on keeping the independent Generator checkout at its current location. `python -m pip list` lists pip 25.3; `pip show npcgen` finds no distribution metadata because this is a source symlink, not a registered package distribution.
- The new venv is ignored by Git. Git status remained limited to the three provided untracked assignments and this report; `.venv` is not visible to Git. The old checkout's post-test status still had its pre-existing 947 entries (93 deleted, 854 untracked, no modified entries); no cleanup or restoration was done.
- Required TASKS, development-process, and Encounter-rules files were readable. `docs/ideas/inbox/` is absent. `docs/assignments/U-ARENA-018B.md` is not installed; install it there before beginning that work.

## Focused verification

Commands ran from the new repository root using `.venv/bin/python -B`, `PYTHONDONTWRITEBYTECODE=1`, and `PYTHONNOUSERSITE=1`. Unless otherwise shown, tests also used `PYTHONPATH=tests:src:examples`.

| Test | Result |
|---|---|
| `-m unittest test_npcgen_arena_adapter -v` | **6 passed**, 0.31 s. Exercises the installed Generator-backed native Being adapter. |
| `-m unittest test_arena_initialization -v` | **7 passed**, 0.70 s. Exercises deterministic two-Being Arena initialization and Generator generation. |
| `-m unittest test_arena_complete_profiles_and_kits -v` | **8 passed**, 4.91 s. Exercises `arena_ready_being`, profile validation, equipment selection, and source preservation. |
| `-m unittest test_movement_intent -v` | **23 passed**, 8.59 s. Native Encounter movement regressions. |
| `-m unittest test_publication_safety -v` | **8 passed**, 3.30 s. |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 .venv/bin/python -B tools/check_publication_safety.py --staged` | **PASS**, 0 staged files, 0 findings. |
| `-m unittest test_npcgen_being_integration -v` | **2 passed, 1 failed**, 0.28 s. The single failure is the exact-float expectation described above; current native state is `49.59`. |

Loopback HTTP/session test command (four tests passed in 7.005 s, binding only `127.0.0.1` on an OS-assigned port):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=src:tests:examples .venv/bin/python -B - <<'PY'
import importlib
for name in ('arena_history_admission', 'arena_history_prefix', 'arena_initialization',
             'arena_state_admission', 'arena_state_candidate', 'inhabited_scene'):
    importlib.import_module(name)
import unittest
suite = unittest.defaultTestLoader.loadTestsFromName('test_npc_encounter_arena_web')
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
PY
```

The six pre-imports ensure the colliding module names resolve to native `src/` modules before the test inserts `examples/` at the front of `sys.path`. Without that in-process ordering, the example files shadow source modules and trigger self-import/circular-import errors. This is a current source/test import-path limitation, not a copied-venv failure.

## Conclusion and boundaries

The copied environment is usable for local Generator-backed Arena and native development. Keep the copied `universe/.venv` and the sibling `npc-generator` checkout in place; use the copied interpreter and `python -m` commands. The focused test evidence covers actual Generator API calls and Arena initialization, equipment profiles, native movement, and HTTP/session integration. The one precision assertion and module-path workaround are the known limits. U-ARENA-018B remains a setup dependency, and real-browser UI verification remains untested.

No `npc-generator` source, `TASKS.md`, or repository configuration was changed. Nothing was staged, committed, or pushed.
