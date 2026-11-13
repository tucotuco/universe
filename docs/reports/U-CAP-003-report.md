# U-CAP-003 engineering report

**Status: ACTIVE — implementation underway.** U-CAP-002 has been reconciled as DONE (bounded); its reviewed assignment and consumed report are archived. This report remains active until ChatGPT reviews and accepts it.

## Current outcome and acceptance matrix

The assignment requires a playable native/generated-Arena weapon and equipment lifecycle, with lawful Object identity, hand/shield resource use, native Action settlement, observer-safe controls and fresh-process persistence. The matrix will be updated against the assignment's A–D criteria as work is implemented and verified.

| Area | Current status | Required evidence / remaining work |
|---|---|---|
| A. Draw, Ready, hands and weapon use | In progress | Verify native source custody and hand facts, weapon-size eligibility, one-/two-handed use, motion-specific Draw/Ready, consumption and conflicts. |
| B. Shields and equipment resources | In progress | Verify shield/buckler/tower rules, Shield bash, protection/durability and supported timed equipment transitions. |
| C. Strike Objects and durability | In progress | Verify native attack eligibility, hardness/HP, atomic same-second durability and observer result distinctions. |
| D. Generated Arena and persistence | In progress | Demonstrate at least two supported weapon/shield configurations, legal and refused choices, actual native receipts and fresh-process continuation without leaking identifiers. |

## Execution intervals

| Session | Start (ISO 8601) | End (ISO 8601) | Elapsed (ISO 8601 duration) |
|---|---|---|---|
| Current U-CAP-003 execution | 2026-11-13T15:37:40-08:00 | In progress | Not yet calculable |

## Verification and implementation notes

No implementation changes or test runs are claimed yet. The pre-existing `test_action_settlement` overlap-fixture failures described in the archived U-CAP-002 report remain historical baseline evidence; they will be reassessed only if shared Choice behavior is changed.

## Repository, archival and safety

- Initial branch: `main`; initial HEAD `4d0ed65fdf78a1b03846888a70073bc7abdd9ada`.
- U-CAP-002 archival is in progress under the user's explicit acceptance and archival authorization. Its Git-aware moves and maintained-link updates are recorded in the archival/status commit.
- The unrelated user-staged historical move `docs/reports/U-THROW-001-rule-sync-proposal.patch` → `docs/reports/archive/U-THROW-001-rule-sync-proposal.patch` is preserved and excluded from assignment commits.
- `docs/assignments/U-CAP-003.md` was supplied as an untracked assignment input and is kept active. The incompatible `universe-arena.json` save, if present, remains untracked and untouched. No protected local environment, save, backup or sibling repository will be modified.
- No push is authorized or planned.
