# U-REPO-012 Phase B — recovery and documentation report

## Outcome

Phase B was carried out in the active `universe` checkout only. The local-only archive and four saved JSON resources were restored and verified against `universe-pre-safe`; documentation was organized without dropping the reconciled pre-safe history; the two focused code/test defects were corrected. No files were written to the other three repository directories. No push, `.venv` rebuild, dependency install, NPC Generator change, or gameplay feature work was performed.

The starting active checkout was `main` at `d59bc7d495e5d4fbd3ccbe43f8e65296d63bf2af`. The final Git status and commit hash will be recorded after the reviewed changes are committed; original untracked user inputs will remain unstaged.

## Restored local-only resources

- `legacy/`: restored 850 regular files (141,673,382 bytes) and the full directory/link tree. A recursive comparison against the pre-safe copy matched all 877 filesystem entries, including regular-file SHA-256 values, symlink targets, and file/directory modes. The comparison digest for this exact inventory encoding is `550510542a44b90d689a8276088d1c442b90adcbca15c99ddedadd4529f97058`.
- `examples/saved/universe-inhabited-scene.json`: 11,688 bytes; mode `0644`; SHA-256 `e05e0a7a9df8ad3fbf17ea7fbe68279df47bd234cc55c6f8324fc6d6868a96de`.
- `workspace/ai-encounter.json`: 7,851 bytes; mode `0644`; SHA-256 `6518a4944cf256d37685390fd165d6ff40e6d76a8362afc22bc3f54a33ad04b5`.
- `workspace/combat-session.json`: 1,643 bytes; mode `0644`; SHA-256 `e1e17d371178ad434e0269830523139498a891df1544bf55c06846b192efa56d`.
- `workspace/universe-planetary-world.json`: 818 bytes; mode `0644`; SHA-256 `f0af4f9f129ccbcfc1ac9a3cfad0ac7131637f20c222083c12aeaf7c49609c2c`.

Each JSON file matched its source bytes and mode and parsed as JSON. The four saved files and `legacy/` are explicitly ignored by Git and are absent from the tracked index. Their content was not opened or interpreted. `.venv` was not modified; its existing interpreter was used to run tests.

### Historical and untracked inventory

The pre-safe status inventory reconciles to 854 visible untracked paths: 832 visible legacy files (the remaining 18 legacy files were ignored), 13 assignment documents, two design notes, one stale root `DEVELOPMENT-PROCESS.md` duplicate, two external-target skill symlinks, and the four saved JSON files. The 13 assignments were reviewed individually: `U-ARENA-018.md` was restored at the path linked from `TASKS.md`; nine path-safe historical assignments were restored under `docs/assignments/archive/`; three repository-cleanup assignment documents containing machine-specific path content were left only in the preserved pre-safe and backup copies. The two design notes were retained: the NPC skill-development note remains directly addressable from the existing deferred task, while the older broad Playground roadmap is archived with an explicit superseded-proposal notice and a link to the revised roadmap. The stale root process duplicate was not restored because the newer canonical copy was moved. The two symlinks were not copied because their external targets were not verified. Thirty-seven intentional two-space Markdown hard breaks in restored assignment headers were rendered as explicit `<br>` tags so the restored documents retain line breaks while passing `git diff --check`. No assignment or design note was promoted to adopted Encounter authority. The idea inbox is absent in this checkout, so there were no pending submissions to process; `U-IDEA-051` remains in `TASKS.md`. No new active assignment was created.

The separate 1,448-entry ignored inventory was also reconciled: existing `.venv` (883), legacy (18), docs (6), examples (94), source (199), tests (239), tools (3), fatigue workbench (4), workspace (1), and root `.DS_Store` (1). Only the approved legacy and four JSON resources were restored; caches and machine-local environments were left in place.

## Documentation organization and references

The 17 immediate `docs/*.md` files were moved with `git mv` into `docs/process/`, `docs/experiments/`, `docs/design/`, `docs/history/encounters/`, and `docs/reports/` (with the three repository-cleanup manifests/reports grouped in `docs/reports/repository-cleanup/`). No Markdown files remain directly under `docs/`. The historical Encounter rules package and current canonical `TASKS.md` remain in their existing authority locations.

Maintained pointers in `TASKS.md`, the process document, relevant source strings, the Encounter checklist, U-ARENA-018 navigation, and the cleanup/archive reports were updated. The four preexisting untracked U-REPO assignment inputs also had their process-document path references corrected in-place; they remain unstaged. The two obsolete design proposals are labeled historical/deferred; prior reports remain records of what was true at the time. A local Markdown-link check over 33 maintained and relocated documents checked 116 relative links and found zero broken targets after the path updates. The check excluded URLs, anchors, and intentional machine-path placeholders. The immediate `docs/*.md` count is zero.

## Previously deleted documentation reconciliation

The pre-safe working tree reports 93 tracked documentation deletions. Every path was checked against its pre-safe `HEAD`, the cleanup manifests/reports, and the active checkout. All 93 have a corresponding active version: 16 root-level Markdown files and three TSV cleanup records were moved to their categorized destinations; 74 other files remain at their active paths. Eight report files intentionally use the current safe-checkout version, which differs from the old pre-safe `HEAD`; the older version remains in the untouched pre-safe/backups. No old deletion was replayed and no file was removed. Thus the reviewed `NEEDS_REVIEW` records remain preserved; the safe disposition for this pass is retain or categorize, not delete.

The three paths flagged `NEEDS_REVIEW / LEAVE_UNCHANGED` in the 5E3B manifest and `NEEDS_REVIEW / RETAINED_AMBIGUOUS_EVIDENCE` in 5E3G are the two encounter architecture/dependency analyses and the timeline/choice characterization. They remain present, grouped under design/history, and referenced by the current source/documentation where applicable. The 5E3H final-disposition manifest separately classifies seven overlapping paths as portable historical or maintained cleanup references; all remain available after relocation. No ambiguous documentation deletion was applied.

`KEEP` in the ledger means the current path/content was retained; `MOVE` means its active bytes were relocated without content loss; `KEEP-CURRENT` means the current safe branch version was retained instead of overwriting it with an older pre-safe copy. Cleanup-manifest classifications are repeated on the affected rows.

| Pre-safe deleted path | Active path | Classification | Content check and reason | Cleanup-record cross-reference |
|---|---|---|---|---|
| `docs/ai-encounter-experiment.md` | `docs/experiments/ai-encounter-experiment.md` | **MOVE** | Same bytes relocated to the categorized destination; no deletion. | — |
| `docs/armed-melee-increment.md` | `docs/design/armed-melee-increment.md` | **MOVE** | Same bytes relocated to the categorized destination; no deletion. | — |
| `docs/combat-controls-and-persistence.md` | `docs/design/combat-controls-and-persistence.md` | **MOVE** | Same bytes relocated to the categorized destination; no deletion. | — |
| `docs/combat-engagement-and-effort.md` | `docs/design/combat-engagement-and-effort.md` | **MOVE** | Same bytes relocated to the categorized destination; no deletion. | — |
| `docs/encounter-resolve-actions-architectural-audit.md` | `docs/design/encounter-resolve-actions-architectural-audit.md` | **MOVE** | Same bytes relocated to the categorized destination; no deletion. | 5e3b: NEEDS_REVIEW/LEAVE_UNCHANGED; 5e3g: NEEDS_REVIEW/RETAINED_AMBIGUOUS_EVIDENCE; 5e3h: encounter-resolution-analysis/COMMIT_PORTABLE_DOCUMENT |
| `docs/encounter-snapshot-transaction-dependency-analysis.md` | `docs/design/encounter-snapshot-transaction-dependency-analysis.md` | **MOVE** | Same bytes relocated to the categorized destination; no deletion. | 5e3b: NEEDS_REVIEW/LEAVE_UNCHANGED; 5e3g: NEEDS_REVIEW/RETAINED_AMBIGUOUS_EVIDENCE; 5e3h: encounter-resolution-analysis/COMMIT_PORTABLE_DOCUMENT |
| `docs/encounter-timeline-choice-damage-characterization.md` | `docs/history/encounters/encounter-timeline-choice-damage-characterization.md` | **MOVE** | Same bytes relocated to the categorized destination; no deletion. | 5e3b: NEEDS_REVIEW/LEAVE_UNCHANGED; 5e3g: NEEDS_REVIEW/RETAINED_AMBIGUOUS_EVIDENCE; 5e3h: encounter-resolution-analysis/COMMIT_PORTABLE_DOCUMENT |
| `docs/encounters/revision-59-to-60.diff` | `docs/encounters/revision-59-to-60.diff` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/handoffs/universe-6-to-7.md` | `docs/handoffs/universe-6-to-7.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-003A-report.md` | `docs/reports/U-ARENA-003A-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-003B-report.md` | `docs/reports/U-ARENA-003B-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-003B1-report.md` | `docs/reports/U-ARENA-003B1-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-003B2-report.md` | `docs/reports/U-ARENA-003B2-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-003B3-report.md` | `docs/reports/U-ARENA-003B3-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-003C1-report.md` | `docs/reports/U-ARENA-003C1-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-003C2-report.md` | `docs/reports/U-ARENA-003C2-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-003C3-report.md` | `docs/reports/U-ARENA-003C3-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-004A-report.md` | `docs/reports/U-ARENA-004A-report.md` | **KEEP-CURRENT** | Active safe-checkout revision differs from pre-safe HEAD; retain the current revision and preserve old copy in pre-safe backups. | — |
| `docs/reports/U-ARENA-004E-report.md` | `docs/reports/U-ARENA-004E-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-004F-report.md` | `docs/reports/U-ARENA-004F-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-004G-report.md` | `docs/reports/U-ARENA-004G-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-004H-report.md` | `docs/reports/U-ARENA-004H-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-004I-report.md` | `docs/reports/U-ARENA-004I-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-004J-report.md` | `docs/reports/U-ARENA-004J-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-004K-report.md` | `docs/reports/U-ARENA-004K-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-004L-report.md` | `docs/reports/U-ARENA-004L-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-004M-report.md` | `docs/reports/U-ARENA-004M-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-004N-report.md` | `docs/reports/U-ARENA-004N-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-004O-report.md` | `docs/reports/U-ARENA-004O-report.md` | **KEEP-CURRENT** | Active safe-checkout revision differs from pre-safe HEAD; retain the current revision and preserve old copy in pre-safe backups. | — |
| `docs/reports/U-ARENA-004P-report.md` | `docs/reports/U-ARENA-004P-report.md` | **KEEP-CURRENT** | Active safe-checkout revision differs from pre-safe HEAD; retain the current revision and preserve old copy in pre-safe backups. | — |
| `docs/reports/U-ARENA-004Q-report.md` | `docs/reports/U-ARENA-004Q-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-004R-report.md` | `docs/reports/U-ARENA-004R-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-004S-report.md` | `docs/reports/U-ARENA-004S-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-004T-report.md` | `docs/reports/U-ARENA-004T-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-004U-report.md` | `docs/reports/U-ARENA-004U-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-004V-report.md` | `docs/reports/U-ARENA-004V-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-004W-report.md` | `docs/reports/U-ARENA-004W-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-004X-report.md` | `docs/reports/U-ARENA-004X-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-004Y-report.md` | `docs/reports/U-ARENA-004Y-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-004Z-report.md` | `docs/reports/U-ARENA-004Z-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-005A-report.md` | `docs/reports/U-ARENA-005A-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-005B-report.md` | `docs/reports/U-ARENA-005B-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-005C-report.md` | `docs/reports/U-ARENA-005C-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-005D-report.md` | `docs/reports/U-ARENA-005D-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-005E-report.md` | `docs/reports/U-ARENA-005E-report.md` | **KEEP-CURRENT** | Active safe-checkout revision differs from pre-safe HEAD; retain the current revision and preserve old copy in pre-safe backups. | — |
| `docs/reports/U-ARENA-005F-report.md` | `docs/reports/U-ARENA-005F-report.md` | **KEEP-CURRENT** | Active safe-checkout revision differs from pre-safe HEAD; retain the current revision and preserve old copy in pre-safe backups. | — |
| `docs/reports/U-ARENA-005G-report.md` | `docs/reports/U-ARENA-005G-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-005H-report.md` | `docs/reports/U-ARENA-005H-report.md` | **KEEP-CURRENT** | Active safe-checkout revision differs from pre-safe HEAD; retain the current revision and preserve old copy in pre-safe backups. | — |
| `docs/reports/U-ARENA-005I-report.md` | `docs/reports/U-ARENA-005I-report.md` | **KEEP-CURRENT** | Active safe-checkout revision differs from pre-safe HEAD; retain the current revision and preserve old copy in pre-safe backups. | — |
| `docs/reports/U-ARENA-005J-report.md` | `docs/reports/U-ARENA-005J-report.md` | **KEEP-CURRENT** | Active safe-checkout revision differs from pre-safe HEAD; retain the current revision and preserve old copy in pre-safe backups. | — |
| `docs/reports/U-ARENA-005K-report.md` | `docs/reports/U-ARENA-005K-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-005L-report.md` | `docs/reports/U-ARENA-005L-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-005M-report.md` | `docs/reports/U-ARENA-005M-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-005N-report.md` | `docs/reports/U-ARENA-005N-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-005O-report.md` | `docs/reports/U-ARENA-005O-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-005P-report.md` | `docs/reports/U-ARENA-005P-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-005Q-report.md` | `docs/reports/U-ARENA-005Q-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-005R-report.md` | `docs/reports/U-ARENA-005R-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-005S-report.md` | `docs/reports/U-ARENA-005S-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-005T-report.md` | `docs/reports/U-ARENA-005T-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-006-report.md` | `docs/reports/U-ARENA-006-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-007-report.md` | `docs/reports/U-ARENA-007-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-008-report.md` | `docs/reports/U-ARENA-008-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-009-report.md` | `docs/reports/U-ARENA-009-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-ARENA-010-report.md` | `docs/reports/U-ARENA-010-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-NPC-BEING-001-report.md` | `docs/reports/U-NPC-BEING-001-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-NPC-BEING-002-report.md` | `docs/reports/U-NPC-BEING-002-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-NPC-BEING-003-report.md` | `docs/reports/U-NPC-BEING-003-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-NPC-BEING-004-report.md` | `docs/reports/U-NPC-BEING-004-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-NPC-BEING-005-report.md` | `docs/reports/U-NPC-BEING-005-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-NPC-BEING-005A-report.md` | `docs/reports/U-NPC-BEING-005A-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-NPC-BEING-005B-report.md` | `docs/reports/U-NPC-BEING-005B-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-REPO-005-report.md` | `docs/reports/U-REPO-005-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-SPATIAL-001-report.md` | `docs/reports/U-SPATIAL-001-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-THROW-001-report.md` | `docs/reports/U-THROW-001-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-THROW-001-rule-sync-proposal.patch` | `docs/reports/U-THROW-001-rule-sync-proposal.patch` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-THROW-002-report.md` | `docs/reports/U-THROW-002-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-THROW-003-report.md` | `docs/reports/U-THROW-003-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-THROW-004-report.md` | `docs/reports/U-THROW-004-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-THROW-005-report.md` | `docs/reports/U-THROW-005-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/reports/U-THROW-006-report.md` | `docs/reports/U-THROW-006-report.md` | **KEEP** | Same bytes already present at the active path; retain as historical or current evidence. | — |
| `docs/universe4-class-a-addendum-t5-f2-h2-v2-2026-10-27.md` | `docs/history/encounters/universe4-class-a-addendum-t5-f2-h2-v2-2026-10-27.md` | **MOVE** | Same bytes relocated to the categorized destination; no deletion. | — |
| `docs/universe4-class-a-decisions-2026-10-27.md` | `docs/history/encounters/universe4-class-a-decisions-2026-10-27.md` | **MOVE** | Same bytes relocated to the categorized destination; no deletion. | — |
| `docs/universe4-increment5d2c1-report.md` | `docs/reports/universe4-increment5d2c1-report.md` | **MOVE** | Same bytes relocated to the categorized destination; no deletion. | — |
| `docs/universe5-increment5e3b-cleanup-manifest.tsv` | `docs/reports/repository-cleanup/universe5-increment5e3b-cleanup-manifest.tsv` | **MOVE** | Same bytes relocated to the categorized destination; no deletion. | — |
| `docs/universe5-increment5e3b-cleanup-report.md` | `docs/reports/repository-cleanup/universe5-increment5e3b-cleanup-report.md` | **MOVE** | Same bytes relocated to the categorized destination; no deletion. | — |
| `docs/universe5-increment5e3g-cleanup-actions.tsv` | `docs/reports/repository-cleanup/universe5-increment5e3g-cleanup-actions.tsv` | **MOVE** | Same bytes relocated to the categorized destination; no deletion. | 5e3h: maintained-documentation/COMMIT_MAINTAINED_CLEANUP_REFERENCE |
| `docs/universe5-increment5e3g-cleanup-report.md` | `docs/reports/repository-cleanup/universe5-increment5e3g-cleanup-report.md` | **MOVE** | Same bytes relocated to the categorized destination; no deletion. | 5e3h: cleanup-chronology/COMMIT_PORTABLE_DOCUMENT |
| `docs/universe5-increment5e3h-cleanup-report.md` | `docs/reports/repository-cleanup/universe5-increment5e3h-cleanup-report.md` | **MOVE** | Same bytes relocated to the categorized destination; no deletion. | 5e3h: maintained-documentation/COMMIT_MAINTAINED_CLEANUP_REFERENCE |
| `docs/universe5-increment5e3h-final-disposition.tsv` | `docs/reports/repository-cleanup/universe5-increment5e3h-final-disposition.tsv` | **MOVE** | Same bytes relocated to the categorized destination; no deletion. | 5e3h: 5e3h-deliverables/COMMIT_MAINTAINED_CLEANUP_REFERENCE |
| `docs/universe5-increment5e3i-task-adoption-report.md` | `docs/reports/universe5-increment5e3i-task-adoption-report.md` | **MOVE** | Same bytes relocated to the categorized destination; no deletion. | — |
| `docs/universe7-increment-u-loc-002a-report.md` | `docs/reports/U-LOC-002A-report.md` | **MOVE** | Same bytes relocated to the categorized destination; no deletion. | — |
| `docs/universe7-u-arena-001-report.md` | `docs/reports/U-ARENA-001-report.md` | **MOVE** | Same bytes relocated to the categorized destination; no deletion. | — |

## Code and test changes

- Updated the NPC Generator integration test's physical length and weight expectations to Universe's existing two-decimal, truncate-down measurement contract (`49.59` inches and `46.8` pounds). No native measurement implementation changed.
- Corrected the Arena HTTP test import-path order: `src/` now takes precedence over the colliding example modules while the test still loads `arena_web` from `examples/`. The tests ran directly without an import shim.

Focused verification (existing `.venv`, `-B`, no install/rebuild):

| Command | Result |
|---|---:|
| `PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest test_npcgen_being_integration test_npcgen_arena_adapter` | 9 passed |
| `PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest test_arena_initialization test_arena_complete_profiles_and_kits` | 15 passed |
| `PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest test_movement_intent` | 23 passed |
| `PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest test_npc_encounter_arena_web -v` | 4 passed; loopback ephemeral listener bound normally; no shim |
| `PYTHONPATH=tests:src:examples .venv/bin/python -B -m unittest test_publication_safety` | 8 passed |

The first NPC test run exposed the stale weight assertion after the length fix; the weight expectation was corrected and the complete NPC-focused rerun passed. No full suite was run.

## Git and publication state

No push was attempted. Before each commit, the explicit staged path list and `python tools/check_publication_safety.py --staged` result will be recorded here. The report, source edits, and documentation moves are scoped to the active Universe checkout. The preexisting user-provided `U-REPO-009.md`, `U-REPO-010*.md`, `U-REPO-012.md`, and `U-REPO-010-report.md` remain unstaged. The final commit hash, branch, and status will be appended after commit verification.
