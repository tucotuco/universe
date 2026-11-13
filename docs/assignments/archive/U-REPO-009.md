# U-REPO-009 — Post-rename Codex access and co-development preflight

**Repository:** the newly renamed, sanitized `universe` checkout at the **existing authorized Universe path**.
**Install as:** `docs/assignments/U-REPO-009.md` in that checkout.
**Invoke:** `Execute docs/assignments/U-REPO-009.md.`
**Type:** Diagnostic only; not an Arena implementation or publication assignment.
**Report:** Concise results **in Codex chat**; no committed report or `TASKS.md` change required for this read-only/preflight task.

## Goal

The user renamed the original Universe folder to `universe-old` and renamed the verified, sanitized fresh clone to `universe`, keeping the same absolute authorized workspace path. Determine whether this Codex session has **all access actually necessary to resume the established ChatGPT ↔ Codex collaboration and U-ARENA-018B implementation**, and identify specific blockers without increasing permissions unnecessarily.

**No permission escalation, broad recursive scanning, push, fetch that mutates refs, commit, branch switching, reset, clean, stash, deletion of user files, history rewrite, copying from the old checkout, or modifications to the independent `npc-generator`.** The only permitted write is a uniquely named, harmless temporary access-probe file created under the new repository's `docs/reports/` and removed by the same invocation (see below). If even this cannot be performed, report the failure and leave the repository untouched.

## Verification sequence

1. **Fresh session and correct directory.** Use a fresh Codex session associated with the *existing* authorized `universe` directory, not an old process whose current directory may reference the pre-rename filesystem inode. Run read-only checks of resolved working directory, `git rev-parse --show-toplevel`, current branch/HEAD, upstream, `git status --porcelain=v1` (report counts/categories rather than private filenames), `git remote -v`, `git merge-base --is-ancestor origin/main HEAD`, and `git rev-list --left-right --count origin/main...HEAD`. The checkout should be the fresh safe continuation, not the old unsanitized checkout. The last verified remote was GitHub `tucotuco/universe` public `main`; the latest U-REPO-008C report says clean clone and remote `main` matched at the closeout commit. **Do not rely on an earlier abbreviated hash.** If network reads are allowed, use `git ls-remote origin refs/heads/main` for independent non-mutating verification; compare to local HEAD and report a network-only limitation separately if inaccessible. Do not fetch or push in this diagnostic.
2. **Read the governing files.** Confirm readable and coherent: root `TASKS.md`, `docs/process/DEVELOPMENT-PROCESS.md`, `docs/encounters/README.md`, recent `docs/reports/U-REPO-008C-report.md` (if committed under that exact name), `docs/reports/U-DOC-001-report.md`, and `docs/assignments/U-ARENA-018B.md` if it has already been installed. Confirm a writable-looking `docs/assignments/` and `docs/reports/` directory without editing any existing file. Check `docs/ideas/inbox/` for pending submissions **by filename only**; do not process or relocate submissions. Missing future assignment files are a **setup item**, not automatic proof of permission failure.
3. **Practical write access.** Create one unique temporary file such as `docs/reports/.codex-access-check-<unique-token>.tmp` using safe exclusive creation, write a fixed harmless string, read it back, and remove **only that exact file**. Use a finally/trap cleanup and report if cleanup fails. No persistent file changes and no staging. Do not test writability by editing or replacing `TASKS.md`, the process document, or any historical report. Confirm `git status` after the probe is unchanged from before.
4. **Runtime/toolchain.** Verify Python and the project venv/interpreter (`.venv` if that is the actual configured environment), source/test imports, `git`, and the offline `tools/check_publication_safety.py` checker. Run `python tools/check_publication_safety.py --staged` from the appropriate interpreter (if present) and a small, relevant focused test group such as `tests.test_publication_safety` (expected 8 at the prior report) or an equivalent safe smoke. Report exact commands, pass/fail, timing, environmental errors and skipped checks. **Do not run the full ~1-hour test suite.** Do not create persistent test snapshots or overwrite saves. Set `PYTHONDONTWRITEBYTECODE=1` where practical.
5. **NPC Generator boundary.** Verify that Universe can **import the installed `npcgen` Python library via the intended Universe environment** and identify its version/API availability (`npcgen.api.arena_ready_being` if present), without modifying or opening a write session in the sibling `npc-generator`. The separate Claude/NPC repository does **not** have to be writable or granted to Codex. If its import is missing, report exactly the required installation/path correction without silently copying generator files.
6. **Arena/browser capabilities.** Check that the existing local Arena app entry point and required browser or HTTP test environment are available for subsequent GUI acceptance (e.g., available Chrome/Chromium or the approved browser interface, and whether local loopback binding is allowed). A real UI smoke is optional **only if safe and quick**; it must not affect saved world data. If Codex lacks browser control, report **browser-verification limited** rather than asserting Arena coding cannot proceed. Do not request unnecessary broad filesystem or remote-account access.
7. **Prior checkout and backup.** The original `universe-old` and private recovery bundles are intentional archives. At most verify that the expected old sibling name exists **if permitted without additional authorization**. No reading its private contents, changing it, or requesting permission to it is required to resume work in the new Universe checkout. If it lies outside allowed scope, record this as **expected and nonblocking**.
8. **Git publication capabilities.** Confirm that remotes/branch tracking and commit author configuration appear usable, without echoing private credentials or running a trial commit/push. Whether credentials are available for a *future separately authorized push* is a distinct, conditional gate, not a requirement to begin local development. Publication still requires the process's staged and unpublished-history safety audits and explicit approval.

## Required output

Give a compact matrix with rows:

- Correct sanitized checkout and clean lineage
- Read access to task/process/rules/assignment/report files
- Scoped write access and unchanged working tree after probe
- Git local commit capability (configuration only; **not** tested with a commit)
- Python/venv and focused tests
- Publication-safety scanner
- `npcgen` import/API
- Arena GUI/loopback verification capability
- Live remote read reachability (optional for local coding)
- Old repository access (not needed)

For each use **PASS**, **LIMITED**, **BLOCKED**, or **NOT CHECKED**, with the specific evidence and remedy. Distinguish **required to resume U-ARENA-018B** from **optional or required only for future push/UI tests**. End with a clear **READY / READY WITH LIMITATIONS / NOT READY** determination for ordinary Universe + ChatGPT + Codex co-development, and the smallest needed user action, if any.

The final `git status` must match the initial status. Report only in chat; **do not commit, update `TASKS.md`, move idea submissions, or push**. If the U-ARENA-018B assignment is not installed, identify its expected location so the user can install it after this preflight.
