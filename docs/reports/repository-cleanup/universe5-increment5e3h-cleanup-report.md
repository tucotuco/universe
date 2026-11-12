# Universe 5 Increment 5E3H — Final grouped cleanup

## Result

Completed the final grouped archival and authoritative-document commit from baseline `03c5e9a874c88ac21686b0c0da58d24a736a4cd4` (`main`, tree `1d76b052b7a8dc6ec04e050db5bcd1981591f922`). The selective documentation commit is `Version adopted Encounter rules and historical archive index`. Its exact commit ID is reported in the completion message; the report is part of that commit and therefore cannot contain its own commit hash without a second commit.

## Archive and preservation

The private local archive is addressed portably as `ARCHIVE_ROOT/5e3h-final-cleanup/`. Its manifest covers 398 source files (8,349,219 bytes), preserving original repository-relative paths, modes, sizes and SHA-256 values. The self-contained archive SHA-256 is `2cd02d2ab98828db5fad0f5c01979d92c60c9842f0ddd1e2be2b875f4edd4efb`; all 398 payload entries were rechecked against the manifest before cleanup. The archive is local recovery material and was not pushed to GitHub.

The archived set includes all 352 files (7,539,881 bytes) from the 17 historical evidence directories, including 255 formerly untracked files and 97 ignored logs; associated historical reports, assignments, patches, handoffs and ZIPs make up the balance. `MANIFEST.tsv`, `GROUPS.tsv`, per-group indexes, `REFERENCES.tsv`, and `ARCHIVE_INVENTORY.tsv` provide path, checksum, mode, grouping, link and recovery information. The maintained index is [historical-evidence-archive-index.md](../../history/historical-evidence-archive-index.md).

After byte, size and mode comparison against the archive, 394 original files were removed. The three unique Encounter analyses were retained in portable form and their original bytes remain archived. The current 5E3G cleanup report was retained after replacing machine-specific paths with portable references; its pre-edit version remains archived. No other source, test, gameplay or committed `work-stash/` file was changed.

Earlier 5E3B and 5E3G recovery archives were checksum-verified again. All 78 committed `work-stash/` snapshots matched their manifest hashes. The four local saved-session/world files were preserved unchanged:

- `examples/saved/universe-inhabited-scene.json`
- `workspace/ai-encounter.json`
- `workspace/combat-session.json`
- `workspace/universe-planetary-world.json`

These are the only intended local-data exceptions after the documentation commit. They are not ignored, staged or treated as disposable.

## Maintained references and rule documents

Versioned the complete 15-file `docs/encounters_adopted_r60/` tree and `docs/universe5-transition-handoff.md`. The adopted documents were verified against their preserved source copies. The three retained Encounter analyses, checkpoint compatibility draft and transition handoff now link historical details through the portable archive index; this changes links only, not rules or simulation behavior.

The 5E3G cleanup chronology and its 463-row action manifest are also included so the successive cleanup record remains available. Archive `REFERENCES.tsv` records 1,409 links found in archived text, including links already absent at capture; the index does not claim those historical links are repaired or that the archive is a GitHub backup.

Checks performed: 138 maintained Markdown/HTML links were checked with no missing target; `python tools/generate_outstanding_todo.py --check` and `python tools/update_encounters_toc.py --check` passed. The staged whitespace check reports only preserved source-format findings: 71 CRLF rows in `encounters-check-inventory-r22.csv`; one trailing-space line in the adopted draft; 20 trailing-space lines and one terminal blank line in `revision-59-to-60.diff`; and two intentional Markdown hard-line-break spaces in the transition handoff. These source bytes were preserved as required. The three new 5E3H records, edited compatibility/analysis documents, and corrected 5E3G report have no whitespace findings; one extra terminal blank line in the characterization report was removed.

No full regression was rerun because this increment changed documentation and archived historical evidence only. The latest clean-export full HTTP-inclusive regression remains 1,573 passing tests from 5E3G. Production code and tests remain at the verified baseline.

## Commit and final working-tree state

The one selective commit contains exactly 25 documentation paths: the 15 adopted-r60 files, the transition handoff, the checkpoint compatibility draft with archive-link updates, three portable Encounter analyses, the 5E3G cleanup report and action manifest, and the three 5E3H deliverables (this report, final disposition, and archive index). No archive payload, local-data JSON, source or test file is committed.

The commit was verified to have the expected baseline parent, exact path set and clean index. The only remaining uncommitted paths are the four named local-data JSON files. There is no push. No `TASKS.md` or family-relationship work was started.

## Cleanup conclusion

Historical evidence now has a complete private recovery path and portable in-repository index. Adopted Encounter rules are versioned. The four saved-data files are explicit, legitimate local exceptions; no further cleanup audit is needed before proceeding to `TASKS.md`.
