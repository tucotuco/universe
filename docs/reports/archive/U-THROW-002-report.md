# U-THROW-002 — Adopted throwing and Reach rule synchronization

## Result

Completed the revision-62 documentation synchronization on disk. The active package now identifies revision 61 as its baseline and adopted revision 62 as controlling for customary physical units, reference arm length, Reach terminology, and throwing velocity scaling. The dated revision-59/60 records were not edited or relabeled. No gameplay code, tests, or published tables were changed.

## Rule changes recorded

- Positive measured Being height/length determines reference arm length and personal Reach as `(15/37) × max(height_inches, length_inches)`. Without a positive measured dimension, use only an explicit Size Category: Diminutive 3.5, Tiny 7, Small 14, Medium 28, Large 56, Huge 112, Gargantuan 224, or Colossal 448 inches. No category inference or individual anatomical variation is introduced.
- Effective weapon Reach is personal Reach plus applicable weapon length; Reach is a scalar distance. Being/Object weight remains pounds. Movement and player-facing spatial distances remain yards; world geometry and trajectory state remain metric. A yard and meter are not interchangeable.
- The release velocity is recorded in yards/second as `Vrelease_yd_s = Vmax_yd_s × exp(−(x / 0.08081)^0.6010) × sqrt(L_inches / 28 inches)`, with `x = projectile_weight_lb / heavy_load_reference_lb`. Existing Throw modifier, maximum throwable-weight constraint, and 5 yd/s effective-adjacent-hex threshold remain. Trajectory conventions remain SI under revision 60.
- The 0.800 m and interim 30-inch reference anchors are explicitly historical/superseded for current reference-arm and throwing-denominator use. Existing customary tables retain their published values and labels; the new category reference table is separate.

Revision 62 resolves only the throwing-calibration portion of ES-041. Non-throwing force/Grapple questions remain open. `src/throwing.py` is still a pure helper: no native Throw Action, maximum-weight enforcement path, or projectile trajectory resolver was added.

## Files changed

On-disk, user-moved Encounter package (authorized edits; remains untracked and unstaged):

- `docs/encounters/encounters-working-draft-adopted-r61.md` — controlling-status pointer, dated historical revision-59 entry, current dimensions/units/Reach, throwing equation, and yard/meter language.
- `docs/encounters/encounters-consistency-decisions-r62.md` — new adopted revision-62 decision addendum.
- `docs/encounters/encounters-rule-issues-r62.md` — new issue-status supplement; resolves the throwing subissue only.
- `docs/encounters/README.md` — current package status and links identify r61 plus the controlling r62 supplements.
- `docs/encounters/tools/generate_outstanding_todo.py` and generated `encounters-outstanding-todo.md` — current baseline/supplement status and the remaining non-throwing ES-041 work are described accurately.
- `docs/encounters/encounters-implementation-checklist.md` — notes r62 adoption without checking implementation boxes.

Tracked task/report paths prepared for the bounded documentation commit:

- `TASKS.md` — U-THROW-001 and U-THROW-002 marked complete within scope; future native Throw work is not represented as an invented task ID.
- `docs/tasks/encounter-engine.md` — records the on-disk rule synchronization and the remaining implementation boundary.
- `docs/reports/U-THROW-002-report.md` — this report.

The existing `docs/reports/U-THROW-001-rule-sync-proposal.patch` remains unchanged (SHA-256 `b43c7cc6e19bd52daaeb20bc14029265fc2fc5a400dfffda89bdb39bbefc9516`); it remains historical proposal input and is not to be applied over the completed edits.

## Verification

- `python docs/encounters/tools/generate_outstanding_todo.py --check` — passed.
- `python docs/encounters/tools/update_encounters_toc.py --check encounters-working-draft-adopted-r61.md` — passed.
- Revision-62 controlling links among README, r61, decision addendum, and issue supplement resolve.
- Text checks confirmed the 28-inch formula, measured-first rule, category values, scalar Reach, yards-versus-metric distinction, explicit supersession of 0.800 m/30-inch anchors, and native Throw limitation.
- Comparison against the pre-edit r61 copy found existing published table rows unchanged; only the new explicit reference-arm table was added.
- `git diff --check -- TASKS.md docs/tasks/encounter-engine.md` — passed. The documentation generator and TOC checks passed after regeneration.
- No engine tests or full suite were run; this was a documentation-only increment.

The package move is incomplete: several older README links (ES-041 analysis, skill/check/saving audits, inventory files, and the r59-to-r60 diff) and one r61 saving-audit link point to files absent from the current `docs/encounters/` directory. The same checkout also has pre-existing links in `TASKS.md` and `docs/tasks/encounter-engine.md` to paths deleted by the user-managed documentation move (including the historical archive index, handoff, and adopted-r60 copies). The new U-THROW-002 report links and new controlling revision-62 links resolve. These migration gaps were left untouched to avoid expanding this assignment into repository reorganization.

## Hash inventory

The following before hashes were captured before editing from the moved-document snapshot; after hashes identify the final on-disk versions. SHA-256 is used throughout.

| Path | Before | After |
| --- | --- | --- |
| `docs/encounters/README.md` | `aa76473f305b77d7e92b2e82b106478a6c406884ad6604bd22fef3fdf945d211` | `a7c0f5cc1915d53367adcee2957bb9bd246a6bf9f3666e3ea2cf113f00d03e18` |
| `docs/encounters/encounters-working-draft-adopted-r61.md` | `87671bebaff7a67b32d4e6caf4f20732ab5cad156a0417d9b91bcbaefd6adcae` | `f92a362e2e7385969d2e310d7e1f438f4e2a5e35ec06efbf158edbb7c6684d99` |
| `docs/encounters/encounters-implementation-checklist.md` | `b7f81856a48995488086cc809402a7f642d3995857b342f828f05a4285bb3395` | `8b76afdf7a716c6671d737e8d4cc55486603424f6dd1a665725db6febc89705c` |
| `docs/encounters/encounters-outstanding-todo.md` | `68e8e435b1616b29d9fae89e298dba5bb1633f1c51f4d6c478a04379ac60cf1c` | `a177f5fd429afff38d92e7fae454d6bb6f7cca84e0368ea25840a28b980ee968` |
| `docs/encounters/tools/generate_outstanding_todo.py` | `e370c918d37737a114ad82e2b88b3af927a0b656f16d7f0a8a681d67c2b7d59e` | `ca0ca2754d25b3aca2b3a50a8bc87c72ec76f167ddb8e66ce193c0c0eefece33` |
| `docs/encounters/encounters-consistency-decisions-r62.md` | new file | `250b6966d3204e2aaeb12e8ed3c458b46f4c9165f56c22f7ffd0a6b95d0e8805` |
| `docs/encounters/encounters-rule-issues-r62.md` | new file | `858fd99f29a6576786aa3583760a64e8933f6db5b561a7842f2658c8841c3953` |

The r60 dated decision/rule records were not edited. The source-proposal patch hash above is unchanged.

## Git state and disposition

Work began on branch `main` at `8dffcf77a4261fc30a508e6d1971f3a982baabe1`; the index was empty. The `docs/encounters/` package is a user-managed untracked move, and remains untracked/unstaged. Existing deletions and unrelated untracked files were preserved. Only the three explicit tracked paths listed above are eligible for the documentation commit; no push is authorized.

## Remaining limitation

The rule synchronization is complete on disk, but not included in Git because the active package is part of the user's untracked documentation reorganization. Native Throw gameplay remains future work; no action timing, target, obstacle, projectile, or flight rules were invented here.
