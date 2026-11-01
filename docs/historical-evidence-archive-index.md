# Historical Engineering Evidence Archive Index

This index locates historical Universe 4/5 engineering evidence removed from the working repository during the 5E3G–5E3H cleanup. It is a locator and recovery guide, not an authoritative simulation specification. Adopted revision-60 rules remain in [`encounters_adopted_r60/`](encounters_adopted_r60/).

## Archive location and integrity

The 5E3H archive is a private local preservation archive, not a GitHub backup:

- Archive root placeholder: `ARCHIVE_ROOT/5e3h-final-cleanup/`
- Self-contained archive: `ARCHIVE_ROOT/5e3h-final-cleanup/universe5-5e3h-cleanup-archive.tar.gz`
- SHA-256: `2cd02d2ab98828db5fad0f5c01979d92c60c9842f0ddd1e2be2b875f4edd4efb`
- Per-file path, prior status, disposition, mode, size, and SHA-256: `MANIFEST.tsv` (398 source files)
- Directory/topic summaries: `GROUPS.tsv` and `groups/*.md`
- Archived-text link inventory: `REFERENCES.tsv`

The archive contains 398 exact source files (8,349,219 bytes): all 352 files from the 17 evidence directories, plus related reports, assignments, handoffs, and ZIP files. Three unique Encounter analyses are also copied there, but are retained in this repository in portable form. The archive tar also contains the manifest, reference map, group indexes, and README. Verify a restored payload against `MANIFEST.tsv` before use.

Earlier recovery archives are catalogued in `ARCHIVE_ROOT/5e3h-final-cleanup/ARCHIVE_INVENTORY.tsv`. That inventory records the 5E3B full snapshot and artifact manifest, the 5E3G pre-cleanup snapshot and historical-document manifest, and the 5E3H archive and manifests. Consult each archive's own checksum record before restoration.

## Topic groups

Each group index under `groups/` lists original paths and locators. The source-path mapping is retained under `payload/`.

| Group | Scope |
|---|---|
| `universe4-assignment03-evidence` | Initial Encounter resolution characterization |
| `universe4-increment1-evidence`–`universe4-increment4-evidence` | Scheduling, boundary coordination, choice reservation, and immutable evaluation |
| `universe4-increment5a-evidence`–`universe4-increment5d2b-evidence` | Candidate settlement, checkpoint closure, and compatibility work |
| `encounter-resolution-analysis` | Three unique source-grounded Encounter analyses, retained here as portable Markdown |
| `legacy-increment-reports` | Superseded engineering reports; later consolidated reports and decisions remain the maintained entry points |
| `checkpoint-linked-reports` | Historical checkpoint reports whose maintained links now resolve to this index |
| `checkpoint-advanced-time` | Advanced-time checkpoint reports and assignments |
| `repository-baseline-candidate` | Candidate-baseline audits and patches |
| `preservation-handoffs` | Superseded handoff ZIPs and preservation reports |
| `cleanup-chronology` | Earlier cleanup report preserved before its portable-link correction |

The 17 complete evidence directories are enumerated below. Archive-level groups also include related historical reports and handoffs; `GROUPS.tsv` and `groups/*.md` document those combined logical groups. The source-path mapping is retained under `payload/`. The final disposition TSV records each path handled by 5E3H and its final repository/archive status.

| Original evidence directory | Files | Bytes |
|---|---:|---:|
| `docs/universe4-assignment03-evidence/` | 8 | 66,299 |
| `docs/universe4-increment1-evidence/` | 7 | 127,586 |
| `docs/universe4-increment2-evidence/` | 12 | 197,212 |
| `docs/universe4-increment3-evidence/` | 13 | 313,304 |
| `docs/universe4-increment4-evidence/` | 22 | 440,209 |
| `docs/universe4-increment5a-evidence/` | 22 | 442,151 |
| `docs/universe4-increment5b1-evidence/` | 22 | 465,022 |
| `docs/universe4-increment5b2-evidence/` | 25 | 505,355 |
| `docs/universe4-increment5b3-evidence/` | 27 | 576,965 |
| `docs/universe4-increment5c1-evidence/` | 34 | 739,130 |
| `docs/universe4-increment5c2-evidence/` | 37 | 822,036 |
| `docs/universe4-increment5c3a-evidence/` | 37 | 844,215 |
| `docs/universe4-increment5c3b-evidence/` | 15 | 387,775 |
| `docs/universe4-increment5c3c-evidence/` | 22 | 871,869 |
| `docs/universe4-increment5d1-evidence/` | 16 | 244,350 |
| `docs/universe4-increment5d2a-evidence/` | 25 | 394,833 |
| `docs/universe4-increment5d2b-evidence/` | 8 | 101,570 |
| **Total** | **352** | **7,539,881** |

## Maintained references

Several maintained documents formerly linked directly into historical evidence. Those links now target this index:

- [`universe4-checkpoint-compatibility-contract-draft.md`](universe4-checkpoint-compatibility-contract-draft.md) — see [the 5D1 observed-field catalog](#increment-5d1-observed-field-catalog) and [the 5D2B closure report and blocker matrix](#increment-5d2b-closure-report-and-blocker-matrix).
- [`universe5-transition-handoff.md`](universe5-transition-handoff.md) — see [advanced-time checkpoint reports and assignment](#advanced-time-checkpoint-reports-and-assignment).
- The retained Encounter characterization links resolve through [Assignment 03 evidence](#universe-4-assignment-03-evidence).

### Increment 5D1 observed-field catalog

Original path: `docs/universe4-increment5d1-evidence/observed-field-catalog.json`.

Restore locator: `ARCHIVE_ROOT/5e3h-final-cleanup/payload/docs/universe4-increment5d1-evidence/observed-field-catalog.json`.

### Increment 5D2B closure report and blocker matrix

Original report: `docs/universe4-increment5d2b-report.md`.

Report locator: `ARCHIVE_ROOT/5e3h-final-cleanup/payload/docs/universe4-increment5d2b-report.md`.

The referenced blocker matrix remains at its original archived path under `docs/universe4-increment5d2b-evidence/`; use `MANIFEST.tsv` to resolve its exact filename and checksum.

### Advanced-time checkpoint reports and assignment

The original 5D2C11 and 5D2C9A reports, plus the 5D2C11A assignment, are preserved in the `checkpoint-advanced-time` and `checkpoint-linked-reports` groups. Their original paths and hashes are listed in `MANIFEST.tsv`.

### Universe 4 Assignment 03 evidence

The original `docs/universe4-assignment03-evidence/` directory is preserved as a complete group. Its files and checksums are listed in `GROUPS.tsv`, its group index, and `MANIFEST.tsv`.

## Restore procedure

1. Resolve the private archive root on the machine holding the archive; `ARCHIVE_ROOT/` is deliberately a portable placeholder, not an absolute path.
2. Extract the archive to a temporary directory and verify its SHA-256 against the recorded value above.
3. Select the exact `payload/<original repository path>` entry from `MANIFEST.tsv`.
4. Copy it to the original path, restore the recorded mode, and verify byte count and SHA-256. Do not overwrite a current file without first preserving it.
5. Consult `REFERENCES.tsv` before restoring a group. Some links were already absent at capture; the table records them rather than implying they are repaired.

The preserved material is valuable historical evidence, but the current authoritative rules and implementation are the versioned repository files, not archived proposals or superseded reports.
