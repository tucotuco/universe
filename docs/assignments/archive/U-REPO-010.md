# U-REPO-010 — Restore the Universe development environment after repository replacement

**Repository:** the sanitized, published `universe` checkout occupying the user's original authorized Universe path.
**Install:** `docs/assignments/U-REPO-010.md`
**Report:** `docs/reports/U-REPO-010-report.md`
**Invocation:** `Execute docs/assignments/U-REPO-010.md.`
**Purpose:** make ordinary Universe/Arena development and tests usable in the new clone without changing Codex permissions or altering the independent `npc-generator` repository.

## Outcome

Resolve the two practical setup limitations from the U-REPO-009 diagnostic:
1. Establish an **ignored, local Universe Python environment** with the versions and dependencies required by the repository, so that imports and focused tests work.
2. Make that environment import the **existing sibling `npcgen` package** and call/inspect its documented `npcgen.api.arena_ready_being` entry point without modifying the Generator checkout or duplicating its source.

Also verify readiness to execute U-ARENA-018B, distinguishing mandatory native/HTTP testing from optional actual-browser automation. Produce an engineering report. **Do not begin U-ARENA-018B's combat implementation** in this assignment.

## Known state (verify against actual checkout)

- U-REPO-008C published a sanitized range by ordinary fast-forward, established a clean continuation clone, and retained the old unsanitized checkout separately as `universe-old`. That original is a recovery archive, not the development lineage.
- U-REPO-009 reported `main == origin/main` at `d59bc7d` and divergence `0 0`; the working tree had one untracked assignment. Do not assume those facts remain unchanged.
- Readability, scoped temporary write access, Git commit configuration, offline publication-safety scanner, and remote read were all successful.
- The currently selected Python was `3.14.3`; there was **no `.venv`**, and `import npcgen` failed with `ModuleNotFoundError`. Eight `tests.test_publication_safety` tests passed.
- Arena entry points exist; local `127.0.0.1` bind worked. Chrome/Chromium was not discovered, and available browser control was not established; **that does not block native/HTTP Arena work**.
- `docs/assignments/U-ARENA-018B.md` was not yet installed. It is the separate next combat assignment to run after this environment preflight.

## A. Verify source, authority, and setup

1. Verify this checkout is the **sanitized continuation** at the user's established `universe` directory, not `universe-old`: current branch/HEAD, `git status --porcelain`, upstream, `git remote -v`, and current `origin/main` ancestry. Do not fetch, push, reset, clean, switch branches, or rewrite history for setup.
2. Read root `TASKS.md`, `docs/process/DEVELOPMENT-PROCESS.md`, `docs/encounters/README.md`, relevant setup/requirements/packaging files, `docs/reports/U-REPO-008C-report.md`, and any repository instructions for the NPC Generator dependency. Inspect `docs/ideas/inbox/` at the start and again before task-state closeout. Do not duplicate pending ideas or expand this setup task into implementation.
3. Inventory available Python interpreters and supported project requirements. **Do not assume Python 3.14 is a supported runtime** simply because a few standalone tests passed. Prefer a supported existing interpreter (for example 3.11–3.13 only if actual project and dependency requirements allow). If no suitable supported interpreter is available without system-level changes, report the precise requirement instead of installing host-level software without user permission.
4. Inspect the sibling `npc-generator` checkout **read-only**, only as necessary to confirm its package location, version, dependency metadata, and importable `npcgen.api.arena_ready_being` contract. **Do not modify, stage, install generated metadata into, create caches in, or otherwise write to the sibling checkout.** Do not grant Codex additional permissions solely for this investigation; if access is unavailable, report the exact non-invasive alternative or permission requirement. Do not copy or fork generator logic into Universe.

## B. Restore a local, untracked environment

1. Create/recreate the **Universe-local** `.venv` (or the documented standard environment), ensuring the path is ignored by Git. Install only the project's declared dependencies required for focused development tests and the generator integration. Use pinned/declared versions where available. Record actual interpreter version and commands, sanitized of personal absolute paths. Do not silently upgrade major dependency versions or alter tracked lock/config files.
2. Supply a **local-only**, reproducible connection to the sibling `npcgen` source without mutating the sibling. Prefer an existing documented installation method that demonstrably has no write effects on the Generator worktree; otherwise, where appropriate, use a `.venv`-local Python path registration or another non-tracked mechanism. Inspect for accidental `*.egg-info`, cache, build or tracked changes in `npc-generator`; reject any approach that needs writes there unless the user separately authorizes them.
3. Avoid embedding absolute machine-specific paths in tracked repository files, assignment reports or committed configuration. It is fine for **ignored local environment state** to refer to the local sibling checkout. Use relative repository references in documentation.
4. Confirm the environment behaves consistently across a **fresh shell/process**. Show `sys.executable` in a sanitized form, `npcgen.__version__` if available, the module's origin in sanitized relative terms, and that `from npcgen.api import arena_ready_being` succeeds. Validate an actual lightweight documented function call or the nearest existing integration test; merely importing a symbol is not enough to declare Arena generation ready.
5. Confirm the Universe source and test imports work in the restored environment and that the browser server entry point can start/bind loopback as already supported; do not overwrite existing saves or touch live user data.

## C. Verify focused development readiness

Run the smallest meaningful selection of:
- `python -m unittest tests.test_publication_safety` with the restored interpreter (previously eight passing);
- the existing NPC Generator adapter / Arena character generation integration tests, using their actual names as discovered from the repository;
- a minimal current native Encounter/Arena HTTP-session test touching generated Beings and beginning a generated Encounter; no need to run all tests;
- `python -m py_compile` on affected setup-related Python (if any) and `git diff --check`;
- `python tools/check_publication_safety.py --staged` (there may be zero staged files until the report is staged).

Record exact commands and counts, durations, unexpected skips, and any baseline known failures. Do not claim an unrun suite is passing. Actual Chrome/Chromium or browser-controller support is **optional for ordinary code development**, but label it explicitly **LIMITED/UNVERIFIED** if not tested; recommend what is needed for UI acceptance later without installing a browser or requesting additional permissions prematurely.

## D. Assignments, tasks, and report

- Check `docs/assignments/U-ARENA-018B.md` and report whether it exists; if absent, say **"Download/install the existing U-ARENA-018B assignment before running it"**. Do not invent its full contents or begin its work.
- Keep `TASKS.md` authoritative as a **state document**: verify whether a task entry already represents environment restoration or development readiness. Add/update `U-REPO-010` only if needed to preserve a genuinely distinct current state; avoid a redundant permanent task if the project process treats successful local preflight as operational evidence. Mark DONE only after the environment and actual `npcgen`-dependent tests work. If a tracked state change is warranted, preserve all existing IDs and unrelated state, and follow the required `docs/ideas/inbox/` intake protocol.
- **Produce the normal persistent report** at `docs/reports/U-REPO-010-report.md`, including: READY/READY WITH LIMITATIONS/NOT READY; exact recovered runtime and generator API checks; test results/timing; read-only sibling-worktree confirmation; browser acceptance limit; actual Git/staged safety results; installed vs missing next assignment; any task/idea updates and before→after mapping.
- Scoped commits are permitted for **new report, new assignment if intended to track it, and a necessary focused TASKS/process correction only**. Run the staged-content safety scanner before committing; stage explicitly selected files; never commit `.venv`, personal paths, private local configs, generated data, or unrelated untracked files. A no-source-change environment restoration need not create a code commit. **Do not push**. Do not alter the original `universe-old`, private bundles, or the independent Generator.
- If a permission/system dependency is genuinely missing, leave the checkout intact and report the narrowest user action required. No broad chmod, administrative installation, permanent environment-variable editing, or workspace authorization changes without approval.

## Completion standard

**READY** means: correct sanitized checkout, supported local runtime, all required declared dependencies, working real `npcgen` API, successful focused Universe/Generator integration test and native/HTTP smoke, clean Git/status aside from explicitly intended report/assignment changes, safety checker success. **READY WITH LIMITATIONS** is acceptable if only actual-browser automation remains unavailable; report that as a testing limitation rather than blocking native engineering. **NOT READY** if the environment cannot generate Beings or run essential focused tests.

**Exact prompt:** `Execute docs/assignments/U-REPO-010.md.`
