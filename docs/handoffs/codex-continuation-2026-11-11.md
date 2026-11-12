# Universe Codex continuation handoff — 2026-11-11

## Orientation

Universe is developed as a coherent world realized statistically and incrementally on demand. Preserve consistency with established facts; keep authoritative Reality separate from observer-owned Observation/Awareness and subjective Belief; retain deterministic, atomic, one-second Encounter resolution and rollback. NPC Generator (`npcgen`) supplies initial generated Being specifications; native Universe state owns later simulation. Do not regenerate saved Beings or copy the independent Generator source into this repository.

## Repository state and authority

- Work only in the active Universe checkout on `main`. After U-REPO-013's ordinary push, local HEAD and independently checked live GitHub `main` matched at `52cdfaba9bf99d1d52c116f5728a43b3b165f590`. This is the verified U-REPO-013 closeout commit and may be an ancestor of this handoff's later documentation update. The local `origin/main` tracking ref remained stale at `d59bc7d495e5d4fbd3ccbe43f8e65296d63bf2af` because Git could not create its lock file in the sandbox; use `git ls-remote` for live state. Every new session must verify the live `main`, ancestry, working tree, and exact current HEAD before relying on any handoff hash.
- `TASKS.md` is the sole current state and idea register. `docs/process/DEVELOPMENT-PROCESS.md` governs coordination, tests, commits, publication and handoffs. `docs/encounters/README.md` points to the adopted revision-61 Encounter baseline plus applicable revisions 62–65. Revision 66's initial-Ready proposal was not adopted.
- `docs/assignments/` contains authorized work inputs; `docs/reports/` records evidence; reports are not the current task register. Historical material under `docs/history/`, `docs/design/archive/`, and `docs/assignments/archive/` is not adopted authority.
- `docs/ideas/inbox/` was absent when this handoff was written. If it exists in the next checkout, inspect it under the process rules; do not assume an absent inbox was processed.

## Local-only material and protected boundaries

- `legacy/`, including `legacy/geography-references/`, is Git-ignored. Four source references were moved there byte-for-byte; `src/continent.py` was retained because its provenance and status remain uncertain. Do not stage or publish the local archive.
- The four local saved JSON files under `examples/saved/` and `workspace/` are individually Git-ignored. The existing `.venv` is the working environment and has been used with the installed `npcgen`; do not rebuild it without a separate request.
- `npc-generator` is an independent repository and was not modified. The three protected Universe backup checkouts remain out of scope; never clean, overwrite, or delete them.

## Completed repository work and evidence

- U-REPO-012 restored the curated local archive and saved JSONs, organized documentation, fixed two focused test defects, and preserved/reconciled the 93 historical deletions. See `docs/reports/U-REPO-012-report.md`; its recorded focused verification totals 59 tests.
- U-REPO-013 moves the four reference-only files out of active `src/`, preserves `continent.py`, and prepares this portable handoff. Its report is `docs/reports/U-REPO-013-report.md`. Focused verification during that work: NPC integration/adapter 9 passed; Arena initialization/profile smoke 15 passed; HTTP/session 4 passed without a shim; active Arena/native imports succeeded. No full test suite or browser smoke was run for this cleanup.
- U-REPO-013 was committed as `52cdfaba9bf99d1d52c116f5728a43b3b165f590`, audited over `d59bc7d495e5d4fbd3ccbe43f8e65296d63bf2af..52cdfaba9bf99d1d52c116f5728a43b3b165f590` with zero findings, pushed by ordinary fast-forward, and independently confirmed on live `main`. The local tracking-ref update failed after GitHub accepted the push, so do not use the stale local `origin/main` as the live tip. The historical U-REPO-008 sanitized-history work established the published sanitized baseline; do not rewrite published history.

## Arena status and next step

Read current `TASKS.md`: U-ARENA-018 remains partial/open and is a next candidate, not automatic authorization. The intended follow-on assignment `docs/assignments/U-ARENA-018B.md` was absent when this handoff was written. Do not invent that assignment or begin implementation: have it installed/authorized first. A new Codex conversation starts with read-only orientation: verify `main` against live GitHub, verify local-only `legacy/` and `.venv` availability, read `TASKS.md`, the process document, adopted rules, this handoff and the newest relevant report, then give a concise “Where we stand” and identify the next installed assignment.

The separately owned Generator remains the integration boundary for `npcgen.api.arena_ready_being`; do not modify its checkout in this repository task. The browser Arena has bounded movement, Actions, inventory, perception and Save/Load; consult `TASKS.md` for precise incomplete combat variants, observer/world scope and evidence levels. In-app-browser and separate Chrome evidence are not interchangeable.
