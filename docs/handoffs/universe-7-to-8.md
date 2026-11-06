# Universe 7 → Universe 8 — Review and prioritize the next capability

**Prepared:** 6 November 2026. **Purpose:** a self-contained starting point for a new Universe 8 discussion. This is a planning handoff, not an implementation assignment.

## Verified starting point

At handoff preparation, local `main` was at `e698b1d2eff1e77a4ebeec99195a9f9607b32baa`, with `origin/main` at `10ba6c85f329ccced15332b24f19faddf9303d85` (55 local commits ahead, 0 behind). U-REPO-006's final handoff commit may advance local HEAD; verify the actual checkout before acting. The worktree contains deliberate existing deletions and untracked user material. The index was empty at the start of the handoff commit. The remote is `https://github.com/tucotuco/universe.git`; the current closeout push is blocked, as explained below.

**Current regression evidence is bounded, not global.** U-REPO-005 discovered 1,797 unittest IDs in 185 modules with no import errors under `PYTHONPATH=src:tests`; it ran 279 selected tests successfully across checkpoint inventory, transactional publication/snapshots, physical work/fatigue/exertion, and Group/reproduction realization. The Encounter documentation checkers passed. One test cohort initially errored from the repository root because fixtures use `../src/config`; all 43 tests passed when run from `tests/`. A single loopback bind probe was denied (`Operation not permitted`), so HTTP listener tests remain environment-unverified. The historical 1,759-test result (1,591 passes, 43 failures, 125 errors) is still not classified as a whole. No full suite was run for U-REPO-005.

U-REPO-006 found one publication blocker in the unpublished history: the original Universe 6→7 handoff commit contains a machine-specific home-directory path. The task forbids history rewriting, so no push was attempted. Do not describe this history as published or attempt a normal push until the user explicitly authorizes a safe history-sanitization operation. See the [U-REPO-006 report](../reports/U-REPO-006-report.md).

## What Universe is building

Universe aims to refine a coherent objective world only when a request requires more detail. Objective **Reality**, observer-relative **Observation**, and subjective **Belief** remain distinct. World resolution and materialization do not automatically reveal identities, family relationships, object state, or locations to observers. Native Beings are Objects; Events remain a separate ontology. A `StatisticalGroup` is a population prototype, not a general social or heterogeneous Group model. `ReproductionGroup` represents exact reproductive parent membership and offspring, not population, household, residence, or social affiliation.

The user's established workflow is: inspect the actual checkout and authority; critically assess the last engineering result; state a plain-language **Where we stand**; supply a compact downloadable assignment and exact prompt; then implement one bounded runnable slice only after the user chooses and authorizes it. Prefer 1–3 small, independently verifiable commits, precise tests and limits, surgical staging, and no push without explicit approval.

## Demonstrated capabilities, with limits

- **Native Encounter:** chronological integer-second boundaries; movement before Actions; a shared post-movement/pre-action snapshot; staged simultaneous effects; atomic publication with rollback and deterministic retry. Target state/history owns resulting HP and practice; Actions preserve causal attribution. The native transactional pathway is opt-in and supports a bounded Action subset, not every adopted rule.
- **Encounter Arena/NPC import:** two source-preserving NPC Generator candidates can bind to distinct native Beings. The loopback developer Arena submits native choices and reads committed results. The narrow importer maps only validated fields; source class, family, possessions and unsupported mechanics are not inferred. `npc-generator-web` is separately owned.
- **Spot and evidence:** deliberate Spot follows the adopted six-second/default-DC/no-Spot-XP rule. Successful native Spot can create observer-owned Awareness and, in the bounded U-WORLD-001B case, immutable historical location evidence from the boundary snapshot. Failed Spot creates neither. Awareness and evidence do not grant continuing access to present Reality after contact changes.
- **Throw and motion:** the bounded native Throw releases a possessed Object, advances a drag-free point-mass trajectory, and records exact fractional impact metadata. A second Being may Run during flight; native Spot can observe the airborne Object. General collision, interception, drag/wind and arbitrary moving-Object perception remain open.
- **World/population integration:** a counted adult StatisticalGroup member can be realized atomically as the same native Being, participate from the next boundary, Run, be discovered by another observer, and receive a genuine native Thrust. Group count remains conserved; geometry is explicit; realization itself does not grant Awareness. This is a single bounded example, not general population generation.
- **Reproduction:** world-only ReproductionGroup generation supports exact parent-set membership, partial resolution, merge aliases, derived bounded kinship, and reproduction-domain checkpoints. One pristine native Being can participate in a separate bounded combined checkpoint. These formats are not general Universe or Encounter save/resume.
- **Spatial state:** native Cartesian coordinates and geometry are metric at full floating precision; ISEA TriFold is derived. Being measurements use inches and pounds; presentation distances use yards. Local demos do not establish globally coherent geography, terrain, or collision physics.

For exact scope and provenance read [TASKS](../../TASKS.md), the [topic task files](../tasks/), the [Encounter package](../encounters/README.md), the [U-REPO-005 report](../reports/U-REPO-005-report.md), and current examples/tests. Historical reports and designs are evidence, not substitutes for current source or adopted rules.

## Controlling rules and boundaries

The current adopted Encounter package is revision 61 with the limited revision 62 (physical units/Reach/Throw) and revision 63 (spatial precision) supplements. Use the package README for precedence. The historical revision-60 decision record remains an input to the inactive checkpoint compatibility fingerprint; it is preserved separately under `docs/history/`, not a replacement for current rules.

The interim observation simplification remains adopted: successful Spot/Listen reports accurate objective information only about properties perceptible under the circumstances, with no invented uncertainty model, extra property roll, automatic identity disclosure, or Spot XP. Quantitative uncertainty remains deferred. An accurate past location is not automatically a current location. Targeted **Remain Aware**, contact loss and reacquisition are separate open design work; no attention capacity or loss formula is adopted.

## First Universe 8 activity: review, do not implement automatically

Compare and prioritize these candidates against `TASKS.md` and current source:

1. **Leading candidate — world-demanded on-demand Encounter instantiation.** Use the forest-watch design note as a requirements illustration: a world request demands a potential encounter; resolve only the necessary objective Being, population, history, spatial context and chronology; preserve identity and constraints; then allow each observer's lawful perception to resolve independently. The design note is not an adopted encounter-rate, selection, placement, or sensing rule. The first slice must identify which existing native mechanism can support a minimal case and ask for any genuine rule decisions before implementation.
2. **Distinct candidate — targeted awareness lifecycle.** Evaluate deliberate Remain Aware, observer-specific contact, loss from current visibility when contact is broken, immutable last-seen evidence, Belief, and later reacquisition. Do not treat this as an automatic extension of one Spot result or assume capacity/concurrency rules.

Other open areas include generalized Object/Event/Action perception; category-directed Spot/Search; richer Agent choices; population and Group generalization; global geography and terrain; general checkpoint/authenticated history; broader revision-61/62/63 conformance; and experimental historical-data provenance. Review the task register rather than reviving old backlog statuses.

**No substantive implementation is authorized by this handoff.** The first response in Universe 8 should verify the live checkout, review/prioritize these candidates, explain blockers and alternatives, and obtain the user's scope choice before producing the next Codex assignment.
