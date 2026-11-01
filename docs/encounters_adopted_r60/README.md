# Encounters — adopted working package (Revision 60)

**Controlling rules:** [Revision 60 Markdown](encounters-working-draft-adopted-r60.md).

Revision 60 ratifies Medium arm length 0.8 m, doubling reference geometry per size category, throwing acceleration distance equal to arm length, smooth empirical velocity response, and work-energy square-root-of-length scaling. Absolute Strength and carrying/lifting limits are independent of size. Historical curve retained for provenance, not used for velocity calculations. General physical force/Grapple work remains open. No Universe engine code changed.

## Compact package — latest of each document type

- [Adopted rules](encounters-working-draft-adopted-r60.md)
- [Cumulative decisions](encounters-consistency-decisions-r60.md)
- [Complete issue history](encounters-rule-issues-r60.md)
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
