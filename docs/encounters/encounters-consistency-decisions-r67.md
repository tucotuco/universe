# Revision 67 — Hold maintenance is automatic and costs no Action

**Adopted ruling (U-ARENA-018D, 12 November 2026):** The opposed Grab check to maintain an individual physical Hold occurs automatically every six seconds. It requires no separate player declaration, consumes no Action, and does not use the holder's action capacity. The system resolves the check at that Grip's maintenance boundary alongside any other Actions due in that second, from the common post-movement/pre-Action snapshot. A higher holder total maintains only that Grip; a tie or lower total ends only that Grip.

The existing initial-Grapple substitution remains in force: when the first Grapple check for a prerequisite Grip is due at the same boundary as that Grip's maintenance check, resolve the Grapple check only. Other independent Grips retain their own six-second schedules. This supplement changes no opposed-check formula, Action timing, hand occupancy, movement constraint, or the distinction between physical Holds and Grapple control.

The system check may be represented internally as a receipt-bearing native event so it shares deterministic RNG, common-snapshot evaluation, atomic publication, replay, and Save/Load. That implementation representation does not make Hold maintenance a declared or capacity-consuming Action.
