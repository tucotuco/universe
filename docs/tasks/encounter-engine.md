# Encounter engine, adopted rules, persistence and verification

Back to [TASKS.md](../../TASKS.md).

## Bounded demonstrated capabilities

- **One-second native transactional progression:** supported intervals advance movement before taking a common post-movement snapshot, evaluate due Actions, then atomically publish supported effects with rollback. This is not a guarantee for every combination. See [`src/encounter.py`](../../src/encounter.py), [`src/transactional_progression.py`](../../src/transactional_progression.py), and [`tests/test_transactional_progression.py`](../../tests/test_transactional_progression.py).
- **Target-owned consequences:** Action/effect records preserve causality; resulting HP, practice, history and state remain on Targets.
- **Deliberate Spot:** revision-60 six-second Action, one target-specific check (default discovery DC 15), no Spot skill and no Spot XP. It does not define category selection or general Attention. See [`src/activities.py`](../../src/activities.py) and [`tests/test_spot_group_evidence.py`](../../tests/test_spot_group_evidence.py).
- **Group evidence:** 5E2C interim success can establish exact aggregate evidence about a supported fully visible Group. The separate `ObserveGroupAction` sampler retains provisional Spot-rank/XP behavior and needs a decision; it is not ordinary Spot.
- **Combat integration:** the bounded 5E2U example commits an Awareness-derived Thrust for 4 damage (HP 10→6) and 10 Dagger XP. Under 5E2M, Group envelopes describe aggregate extent and do not block melee; real modeled Beings/Objects still participate in physical obstruction.
- **Fresh-process continuation:** 5E1J6 restores one historical Run boundary and publishes one new Run boundary, with no imported-practice replay and native issuance for the new receipt. This Run-only scenario consumes no RNG. It does not demonstrate stochastic replay or general save/load.

## Open work and acceptance gates

- **U-PER-002:** general checkpoint/save/load, mixed Action and observer cases, and stochastic continuation.
- **U-RULE-001:** resolve or retire provisional `ObserveGroupAction` rank/XP behavior without inventing sensing mechanics.
- **U-SPOT-002:** category-directed Spot/Search, multi-candidate outcomes and sustained Attention remain unapproved.
- **U-PHY-001:** live R4 Q/B fatigue remains unintegrated; the preserved workbench is experimental.
- **U-PHY-002:** continue the authoritative combat/force issue work in the [r60 issue bridge](encounters-r60-open-issues.md).

## Normative sources and evidence

The [adopted r60 draft](../encounters_adopted_r60/encounters-working-draft-adopted-r60.md), [issue register](../encounters_adopted_r60/encounters-rule-issues-r60.md) and [generated queue](../encounters_adopted_r60/encounters-outstanding-todo.md) govern rules. Current source/tests establish implementation. Prior 5E1J6, 5E2M and 5E2U reports are available via the [historical archive index](../historical-evidence-archive-index.md); their original relative paths are recorded there.
