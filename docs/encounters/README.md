# Encounters — adopted working package (Revision 63)

**Controlling rules:** [Revision 61 Markdown](encounters-working-draft-adopted-r61.md), subject to the limited adopted [revision-62 addendum](encounters-consistency-decisions-r62.md), [issue supplement](encounters-rule-issues-r62.md), and the [revision-63 spatial-precision clarification](encounters-consistency-decisions-r63.md).

Revision 61 remains the adopted baseline, supplemented by revision 62 for physical dimensions, reference arm length, Reach terminology, and throwing velocity scaling, and by revision 63 for authoritative spatial precision only. Revision 63 supersedes revision 61's nearest-0.1-m movement-state commitment rule; all other revision-61 and revision-62 decisions remain unchanged. Dated revision-59/62 records remain historical decision provenance. Existing customary-unit tables are unchanged. The pure throwing helper is not connected to a native Throw Action or trajectory resolver; general physical force/Grapple work remains open.

## Compact package — latest of each document type

- [Adopted rules baseline](encounters-working-draft-adopted-r61.md), with the controlling [revision-62 addendum](encounters-consistency-decisions-r62.md), [issue supplement](encounters-rule-issues-r62.md), and [revision-63 spatial-precision clarification](encounters-consistency-decisions-r63.md)
- [Cumulative decisions through revision 60](encounters-consistency-decisions-r60.md) and [supplemental revision-62 decisions](encounters-consistency-decisions-r62.md)
- [Issue history through revision 60](encounters-rule-issues-r60.md) and [revision-62 issue supplement](encounters-rule-issues-r62.md)
- [Outstanding-only to-do](encounters-outstanding-todo.md)
- [Latest ES-041 analysis](es-041-strength-force-calibration-r60.md)
- [Latest skill audit R25](encounters-skill-specification-audit-r25.md)
- [Latest check inventory R22](encounters-check-inventory-r22.md) and [CSV](encounters-check-inventory-r22.csv)
- [Latest saving audit R7](encounters-saving-check-audit-r7.md)
- [Implementation checklist (older baseline)](encounters-implementation-checklist.md)
- [Revision 59 to 60 diff](revision-59-to-60.diff)

Past revisions excluded; existing older audits not revalidated.

Run `python tools/generate_outstanding_todo.py` and `python tools/update_encounters_toc.py` after editorial modifications.

Revision 60 additionally standardizes gravity at 10 m/s², defaults release height to Being body height with override, and recalculates the reference trajectory columns. Drag and wind are deferred to the later launched-projectile review.
