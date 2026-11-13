# U-REPO-010 — Assess and reuse the known-working `universe-old/.venv`

**Repository:** the sanitized active `universe` checkout, at its existing authorized path.
**Install:** `docs/assignments/U-REPO-010.md` (replaces the earlier U-REPO-010 draft).
**Report:** `docs/reports/U-REPO-010-report.md`.
**Prompt:** `Execute docs/assignments/U-REPO-010.md.`
**Scope:** environment assessment and non-mutating use only; no new environment, installation, combat implementation, commit, or push.

## User decision

The user prefers **reusing `../universe-old/.venv`**, the environment used successfully throughout earlier Universe/Codex co-development, **if it remains viable after the folder rename**. Do **not** create/recreate `universe/.venv`, invoke `pip install`, reinstall Python, copy or relocate an environment, change virtual-environment configuration, or alter an existing Python environment under this assignment. Inspect and test the old environment first; if it is viable, use its interpreter directly to run the supported focused tests against the **new sanitized `universe` source**. If it is not viable, report precisely why and propose the least-disruptive alternatives for a separate approval. No fallback installation is authorized.

**Important distinction:** a venv moved with its containing repository folder can be **non-relocatable**. Its interpreter may still run, while its console scripts and activation file refer to the former absolute `.../universe/.venv` path. A working `python` alone does not establish full compatibility. Conversely, a broken console script does not imply the Python environment is unusable through `python -m`. Do not infer the result; verify it.

## A. Confirm scope and inspect without modification

1. Confirm the working directory is the **new** sanitized `universe` repository, with its expected `main` and remote alignment, and not `universe-old`. Inspect the current Git status and any pre-existing user modifications; do not modify them. Do not fetch or push.
2. Locate `../universe-old/.venv` using repository-relative paths, not a hardcoded machine-specific absolute directory. Check whether Codex has **existing read-only access**. Do not change sandbox settings or permissions, use sudo, broaden authorizations, or bypass access restrictions. If access is denied, stop and report the narrow permission issue.
3. Read, without editing, `pyvenv.cfg`; the interpreter file/symlink targets; `bin/activate` (or platform equivalent); the shebangs of relevant installed commands; and installed distribution metadata. Record whether interpreter paths and scripts still target the original `universe/.venv` location and whether their referenced Python base exists. No activation is required for these checks.
4. Inventory only relevant packages and versions (especially `npcgen` and its dependencies) with **the old venv's Python**, not system `pip`: `../universe-old/.venv/bin/python -m pip --version`, `... -m pip list` or package metadata. Do **not** run installs, upgrades, dependency resolution that writes files, or automatic environment repair. Inspect relevant `*.pth`/editable import paths and package origins for references to the old or new Universe checkout. Read sibling `npc-generator` files only if permitted, without writing there.
5. Read the current `TASKS.md`, `docs/process/DEVELOPMENT-PROCESS.md`, `docs/encounters/README.md`, and current setup/test instructions. Check `docs/ideas/inbox/` for pending submissions; do not process them or change `TASKS.md` during this diagnostic unless separately authorized.

## B. Prove actual reuse against the correct source (non-mutating)

Run commands with **the old environment's interpreter explicitly**, *without activating it or running its possibly stale console-script shebangs*. Use the new `universe` directory as the current working directory. Apply `PYTHONDONTWRITEBYTECODE=1` / `python -B` and `PYTHONNOUSERSITE=1` for diagnostic runs where appropriate, and use temporary directories outside both repositories for test scratch output. Do not set persistent shell variables or change either checkout. Avoid new cache/build files in `universe-old`, `npc-generator`, or other unrelated directories.

1. Verify `sys.version`, `sys.prefix`, `sys.base_prefix`, the executable, import paths, and the interpreter's ability to load its standard library. Report paths **only as sanitized repository-relative descriptions**, not personal machine paths.
2. From the **new** checkout, test imports of native Universe modules and `npcgen`; inspect actual module origins. **Fail the preflight if Universe code is imported from `universe-old`** or Generator logic from an unexpected duplicate, even if tests appear to pass. If a supported project invocation needs `PYTHONPATH=tests:src:examples`, use that for this one process and document it, without modifying persistent configuration.
3. Verify `npcgen` version/identity and import `npcgen.api.arena_ready_being`; run an existing narrowly scoped actual Arena/NPC integration test that exercises real generation, if safe. Merely importing the API is not sufficient. Check whether a renamed-venv path or editable installation gives stale/incorrect modules.
4. Run a small selection of focused native Encounter/Arena tests and the eight publication-checker tests with the old environment's Python. Run an HTTP/session smoke if practical and safe. Do not run the full suite. Distinguish **test result** from whether the command might have written temporary data, and clean only uniquely created temporary scratch material outside either checkout.
5. Check the old interpreter's ability to run essential tools via `python -m` (test runner, pip **version/query only**, and server module import). Examine whether activation scripts/console entry points are now broken. **Do not create `universe/.venv` symlinks or wrappers, even temporarily**, and do not rewrite shebangs in `universe-old`. If a symlink to the old venv would restore compatibility, propose it as a separate optional choice, explaining that future installs through it would modify the original environment.
6. Inspect `git status --short` in the new and old repositories after testing, provided read access permits. Verify no tracked change was caused; do not clean or restore any unrelated content. If a test writes something unexpected, disclose the exact file category and stop rather than removing pre-existing user data.

## C. Decision criteria and report

Deliver a **persistent report** `docs/reports/U-REPO-010-report.md` in the active new repo. The report is the only intended new file (the downloaded assignment is user-provided). Do not stage or commit, push, change `TASKS.md`, change development-process policy, or install anything. Include exact commands (using repository-relative notation), test counts/results/durations, interpreter/`npcgen` identities, source-origin verification, and the state of the old venv's path references. Keep personal/machine-local absolute paths out of the report.

Conclude with exactly one status:

- **REUSABLE NOW:** direct invocation of `../universe-old/.venv/bin/python` runs current Universe source, the genuine sibling `npcgen`, representative generation and native tests correctly; no environment or sibling modification was needed. Explain the exact invocation convention Codex should use for future assignments and note any broken *optional* activation/console scripts.
- **REUSABLE WITH LIMITATIONS:** core imports/tests work, but named entry points, browser tests, or minor tooling limitations remain. Distinguish blockers to actual Arena development from optional tests.
- **NOT SAFELY REUSABLE:** interpreter, dependencies, source binding, permissions, or tests fail materially. Identify the smallest cause and propose **alternatives only**, such as an explicitly reviewed local symlink, a copy-and-repair, or constructing a new venv from the known-working package versions. None is authorized yet.

Also report whether `docs/assignments/U-ARENA-018B.md` is installed. Do not begin it in this assignment. Explain clearly that `universe-old` is preserved as an archive, and using its `.venv` would create an ongoing dependency on keeping that directory intact. Confirm **no changes to any existing Python environments** and no new Python environments.

**Stop condition:** If inspection or testing requires writes to an existing environment, a permission expansion, dependency installation, a repair of hardcoded paths, or a symlink under active `universe`, stop and return the finding rather than taking that action.
