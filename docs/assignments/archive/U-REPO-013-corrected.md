# U-REPO-013 — Move reference-only material out of `src/`, publish safely, and prepare a fresh Codex handoff

**Run only in:** active `~/Projects/universe` checkout. **Do not work in or mutate** `~/Projects/universe-pre-safe/`, `~/Projects/universe-safe-backup/`, or `~/Projects/universe-pre-safe-backup/`. The independent sibling `npc-generator` checkout is also out of scope.

**Install at:** `docs/assignments/U-REPO-013.md`
**Completion report:** `docs/reports/U-REPO-013-report.md`
**Handoff:** `docs/handoffs/codex-continuation-2026-11-11.md`
**Invocation:** `Execute docs/assignments/U-REPO-013.md.`

## Purpose and authority

The user has explicitly authorized **(a)** relocating reference-only files out of active Universe source into the **local-only, Git-ignored** `legacy/` collection, **(b)** one ordinary **non-force** GitHub push after strict publication-safety checks, and **(c)** a durable handoff for a new Codex conversation. The user has **not** authorized history rewriting, force pushing, publication of private `legacy/` material, refactoring unrelated gameplay, or destructive cleanup of backups.

The user identifies these four distinct `src/` files as externally gathered references and wishes to remove them from active source:

1. `src/AM_Kastrisios_Voronoi_Python.py`
2. `src/world_builder_fp.py`
3. `src/ModernApolloNavigator.py`
4. `src/world_map.png`

The user asks Codex to **determine** whether `src/continent.py` likewise belongs in `legacy/`; **do not pre-judge it**. Classify it from its content, provenance, current use, and dependencies, then relocate it **only if convincingly reference-only and not needed by active Universe**. If ambiguous, keep it in `src/`, explain the evidence, and still complete the safe parts of this assignment.

U-REPO-012 previously completed recovery of 850 curated `legacy/` files (local-only), four saved JSON files (local-only), the previous documentation cleanup, and fixes for two test defects. The most recently reported implementation commit was `95408bb` plus a report-only successor; **verify actual HEAD and working state**, not this historical hash. The repository's process document is now at `docs/process/DEVELOPMENT-PROCESS.md`; Markdown files should not sit immediately under `docs/`. The existing `universe/.venv` is the verified working environment and must not be rebuilt, upgraded or otherwise modified.

## A. Safe inspection and classification (before writes)

1. Read `TASKS.md`, `docs/process/DEVELOPMENT-PROCESS.md`, adopted Encounter rules and the U-REPO-012 report. Check `docs/ideas/inbox/` if present, on entry and before task/report closeout. Do not create unrelated tasks. Check the current checked-out branch, HEAD, `git status --porcelain=v1 -uall`, staged changes, current `origin` URL, and `git ls-remote origin refs/heads/main`. Require `main` and confirm the live remote tip is an ancestor of local HEAD before contemplating any push; do **not** reset/rebase/clean/stash/switch branches or rewrite history.
2. Confirm each named source file exists, its actual type (script/image), whether Git tracks it, file size and SHA-256. Identify any existing destination or duplicate under `legacy/`. Detect/avoid symlinks or paths escaping the working tree. **Do not read private contents of unrelated `legacy/` files** or traverse symlink destinations.
3. For each proposed source removal, search for static/dynamic imports, invocations, path constants, tests, examples, scripts, documentation references, generated outputs, and asset loading in active code. Check file headers, imports, repository history and any available attribution/license evidence to distinguish third-party examples from original Universe modules. Do not run untrusted reference scripts or assume filename alone proves purpose. Document the basis for classification.
4. Decide specifically for `src/continent.py` whether it is (i) reference-only, (ii) active/required Universe code or (iii) uncertain. If (ii) or (iii), **leave it in `src/`** and report why. Do not remove an active dependency merely to make the tree visually tidy. If reference-only but some active documentation links to it, update maintained references as necessary, without silently changing adopted rules.
5. **Stop without moving any file** if a requested move would break required runtime functionality, violate a license/attribution obligation in a way the scope cannot responsibly address, overwrite a different existing legacy file, or cause a protected/private file to be staged. Report a narrow blocker; non-blocked file moves may proceed independently only if their safety is established.

## B. Local-only archival and tracked source removals

1. Use a clearly organized new subdirectory such as `legacy/geography-references/`, unless a more fitting existing legacy category is evident. Keep the four named reference files together where practical. Do **not** overwrite existing `legacy/` paths; if a matching identical file exists, verify its bytes and identify which copy is authoritative. Preserve file bytes, meaningful modes, and useful attribution as found. Avoid modifying or reorganizing the existing curated 850-file collection.
2. For each file: **copy** it from `src/` into the ignored legacy destination first; verify destination SHA-256 and file mode against source; ensure `git check-ignore -v` reports it ignored and `git ls-files --error-unmatch` does not identify the destination as tracked; only then remove the `src/` source. For tracked source files, explicitly stage the removal with `git rm -- src/<name>` or equivalent reviewed index operation. For untracked source files, do not stage them. Never use `git mv` to inadvertently force-add ignored legacy assets, `git add -A`, or an unconditional `rm -rf`.
3. Confirm the transferred assets are **not** staged for GitHub and that no active code/test/doc path became broken. If `world_map.png` is actively used as a source asset, first resolve the reference or keep the source file until a safe alternate is demonstrated. Do not publish copies of third-party assets under a new tracked location.
4. Add no broad ignore rule that could hide legitimate future work. `legacy/` is already intentionally Git-ignored; verify it remains so. Preserve and verify the four specifically ignored saved JSON files. Preserve the copied `.venv` and every backup unchanged. No installation, update, or environment repair.

## C. Focused verification

1. Use `.venv/bin/python -B` from the active repository with `PYTHONDONTWRITEBYTECODE=1` and `PYTHONNOUSERSITE=1`. Use the documented `PYTHONPATH=tests:src:examples` for applicable tests. Run targeted imports and tests for any module/asset consumers identified in A, and at minimum a small native/Generator-backed Arena smoke, `test_npcgen_being_integration`, `test_npcgen_arena_adapter`, and the ordinary `test_npc_encounter_arena_web` HTTP/session test **without a shim**. Include a small tests/source import-discovery check demonstrating that reference removal has not introduced an import error. Prefer a small focused set, not the ~1-hour full suite.
2. Record exact commands, pass/fail counts and timings. Do not claim unrun tests are green. Confirm `docs/*.md` count remains **zero**, maintained links referring to moved assets still resolve or are accurately updated, and `git diff --check` passes.
3. Reconfirm byte hashes in the new legacy destinations, presence and ignore rules for private saved resources, and status/diff of the three protected directory copies if read-only verification is practical. Ensure **no private legacy file or save is in the index**.

## D. Commit, safe publication and stopping gates

1. Create `docs/reports/U-REPO-013-report.md` covering a table of all five candidate files with status (`moved`, `retained`, `blocked`), rationale for `continent.py`, source/destination hash and track/ignore state, dependency check, tests, maintained reference updates, task/idea integration, and Git safety. Create the concise handoff `docs/handoffs/codex-continuation-2026-11-11.md` described in section E. These files may be **committed** after publication review; avoid absolute home paths in their contents. A historical pre-push report must not claim push was already successful.
2. Update `TASKS.md` only to record a real change in project state under `docs/process/DEVELOPMENT-PROCESS.md`, preserving existing unique IDs and all unrelated status. Process any genuinely pending idea inbox items according to the existing process, without inventing new requirements. This file's new `U-REPO-013` task entry is optional if the register is intended to remain at milestone granularity.
3. Explicitly stage **only** approved tracked source deletions, necessary affected references, report/handoff, and a warranted task change. Review `git diff --cached --name-status`, `git diff --cached --check`, license/privacy implications, large/binary files and ignore status. Run `.venv/bin/python -B tools/check_publication_safety.py --staged` **before every commit**. If the scanner fails, stop; never bypass it. Make one or a small number of coherent commits (prefer one closeout commit), record hash(es), and ensure the index is clear after committing. Do not stage pre-existing unrelated assignment/report inputs.
4. **Before any push**, compare live remote `refs/heads/main` to local known remote ref, verify that live tip is an ancestor of candidate HEAD and that the push is a true fast-forward. Run the repository's required **all-new-objects publication scan** for the **exact outgoing range**, e.g. `.venv/bin/python -B tools/check_publication_safety.py --range <verified-live-remote-sha>..<candidate-HEAD>` (confirm actual supported syntax). A staged-only check is **not enough**. The previously reviewed historic published-base findings must not be presented as new issues, but **zero unreviewed findings in the outgoing range is mandatory**. Check that `legacy/`, saved JSON, `.venv` and any other sensitive local files are absent from candidate tracked tree and outgoing additions. Be careful that removing a tracked file **does not erase its earlier published history**; do not claim it does.
5. If any gate fails, **do not push**. Report exact remaining blocker and safe next action; do not attempt a force push, history rewrite, branch reset or guessed workaround. If all gates pass, the user's request authorizes **one ordinary `git push origin main` (no `--force`, no tags)**. Independently verify the live remote SHA via `git ls-remote origin refs/heads/main` matches local HEAD; report the result in the **Codex chat response**. If verification fails, report uncertainty accurately. Do not create another post-push commit unless separately needed and expressly authorized.
6. Do not discard, delete or overwrite the three backup repositories; do not prune dangling Git objects; no global Python changes; no unrelated cleanup or new gameplay features.

## E. Fresh Codex-conversation handoff

Produce a self-contained and **portable** handoff at `docs/handoffs/codex-continuation-2026-11-11.md`, suitable for a brand-new Codex conversation authorized to the active Universe checkout. Keep it concise and factual, without personal absolute paths or secrets:

- Purpose/principles of Universe: resolution on demand, statistical-to-realized coherence, Reality/Observation/Belief, deterministic atomic 1-second Encounter resolution and rollback.
- Correct current working tree, sanitized published-history basis and exact local HEAD **at handoff authoring time**, plus a separate instruction for the next session to **verify** live remote HEAD rather than trusting a possibly pre-push description. Note whether push was pending when written; the final Codex chat must record the actual post-push confirmation.
- Exact locations and authority of `TASKS.md`, `docs/process/DEVELOPMENT-PROCESS.md`, adopted Encounter package, `docs/assignments/`, `docs/reports/`, and `docs/ideas/inbox/` when present. Correct role of historical reports vs live task status.
- Locally preserved material: Git-ignored `legacy/` (including newly moved references), four ignored saved JSON files, existing `.venv` connected to independently maintained `npc-generator`; no duplication/commit of Generator source. Protected backups stay out of scope.
- Verified test baseline and any limitations: exact newly run focused counts; previous 59 passing U-REPO-012 tests, no full regression claim; actual-browser automation not yet verified if still so.
- Completed work from U-REPO-012 and U-REPO-013; pending/incomplete Arena combat work (U-ARENA-018 and intended continuation U-ARENA-018B, if present) versus deferred world/system tasks. Read `TASKS.md` for precise up-to-date priorities; do not invent completion.
- Next entry task, ideally the existing `docs/assignments/U-ARENA-018B.md` **only if it actually exists**. If absent, explicitly say it must be installed; do not manufacture its contents. A new Codex conversation starts with a **read-only orientation**, not automatic implementation.

In the final chat response provide:

1. **Result** and `continent.py` classification with rationale;
2. exact moved paths and SHA-256 verification outcome, tests and Git commit(s);
3. live remote HEAD confirmed after the **one approved push**, or explicit reason for **not pushing**;
4. handoff file location;
5. an exact short prompt for the **new Codex conversation**, such as:

> Work in the active `universe` checkout. Read `TASKS.md`, `docs/process/DEVELOPMENT-PROCESS.md`, and `docs/handoffs/codex-continuation-2026-11-11.md`. Verify `main` against the live GitHub remote, local-only `legacy/` and `.venv` availability, and the next outstanding task. Give a concise "Where we stand" and identify the next installed assignment; do not implement anything yet.

## Definition of done

- Four specifically named reference-only files are safely preserved in ignored `legacy/` and absent from active `src/`; or an independently justified dependency/rights blocker is precisely reported.
- `continent.py` is **actually classified**, with action if demonstrably reference-only, or an evidence-based explanation for retention.
- Relevant native/NPC/HTTP tests and dependency checks pass; no unintended environment or backup modification.
- No `docs/*.md`, no private files tracked, publication safety passes on the **outgoing Git range**.
- The normal non-force GitHub push **and independent remote verification** succeed, or publication is stopped with an actionable specific reason.
- A portable, accurate handoff for the next Codex conversation is committed and discoverable.
