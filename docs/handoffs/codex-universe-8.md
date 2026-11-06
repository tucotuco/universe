# Codex handoff — Universe 8 repository support

**Status:** execution context for a fresh Codex conversation. This document does not authorize a feature.

## Startup and current checkout

Work only in the Universe repository. Verify `git status -sb`, `git rev-parse HEAD`, `git branch -vv`, `git remote -v`, `git log --oneline -15`, `TASKS.md`, `docs/tasks/`, and this handoff before acting. At preparation, local `main` was `e698b1d2eff1e77a4ebeec99195a9f9607b32baa`; `origin/main` was `10ba6c85f329ccced15332b24f19faddf9303d85`; local was 55 commits ahead and 0 behind. U-REPO-006's handoff commit advances local HEAD. Verify current state instead of assuming these hashes remain current.

**Push is not authorized by this handoff.** U-REPO-006 found an unpublished historical commit containing a machine-specific home-directory path. Its assignment forbids rewriting history; the normal push was withheld. Do not push, force-push, rebase, or sanitize history unless the user separately authorizes a specific safe procedure. Current `origin` is `https://github.com/tucotuco/universe.git`.

The working tree intentionally contains user-managed deletions and untracked material. Never use `git clean`, `git reset --hard`, blanket `git restore`, `git add -A`, `git add .`, or `commit -a`. Protect `.agents/`, `.claude/`, `legacy/`, `examples/saved/`, `workspace/*.json`, independent projects, and unrelated docs. Stage only reviewed explicit paths. Do not modify adopted rules or historical input bytes without scope.

## Required reading and authority

1. [`TASKS.md`](../../TASKS.md), all five active [`docs/tasks/`](../tasks/) files, especially `encounter-engine.md`, `generation-and-attention.md`, and `repository-workflow.md`.
2. [`docs/encounters/README.md`](../encounters/README.md), adopted revision-61 rules and revision-62/63 supplements, the current issue bridge, and relevant source/tests.
3. [`docs/design/U-PERCEPTION-FOREST-WATCH-DESIGN-v2.md`](../design/U-PERCEPTION-FOREST-WATCH-DESIGN-v2.md) and [`deferred-object-event-perception.md`](../design/deferred-object-event-perception.md), both design/requirements material only.
4. [`U-REPO-005 report`](../reports/U-REPO-005-report.md) and [`U-REPO-006 report`](../reports/U-REPO-006-report.md) for current bounded regression and repository publication status.

Current rules: revision 61 baseline; revision 62 changes only adopted physical units/reference-arm/Reach/Throw matters; revision 63 supersedes only authoritative spatial coordinate rounding. The interim accurate-perceptible-property Spot/Listen simplification remains adopted. Quantitative uncertainty, general Object/Event/motion perception, Remain Aware capacity, and reacquisition rules remain unadopted/deferred.

## Bounded verified regression picture

U-REPO-005 used discovery only: 1,797 unittest IDs in 185 modules, zero import errors with `PYTHONPATH=src:tests`. It ran 279 selected tests, all passing: 30 checkpoint-inventory tests; 169 atomic-publication/interval-staging/shared-Reality tests; 43 physical-work/fatigue/exertion tests; and 37 group/reproduction-realization tests. It did **not** run a full suite. A root-directory invocation of tests with `config_dir='../src/config'` fails during setup; the physical cohort passed when invoked from `tests/`. One loopback bind attempt was denied by the environment, so listener-based HTTP tests remain unverified. The older 1,759-test full run (1,591 pass, 43 fail, 125 errors) is historical and unclassified as a whole. Do not claim global green.

Use current package checks:

```sh
python docs/encounters/tools/generate_outstanding_todo.py --check
python docs/encounters/tools/update_encounters_toc.py --check docs/encounters/encounters-working-draft-adopted-r61.md
```

For repository tests, set `PYTHONPATH=src:tests` from the repository root unless a test's fixtures explicitly require running from `tests/`. Do not repeat the full suite during a documentation-only task. If a future assignment requires HTTP, report listener restrictions as environment-unverified and provide a normal-host command.

## Implemented mechanisms and limits

- Native transactional Encounters process integer-second boundaries in chronological order; movement precedes Actions; Actions evaluate a common post-movement/pre-action snapshot; candidate consequences publish atomically with rollback and deterministic retry. Use current source, not a historical report, as implementation evidence.
- Native choice proposal/validation/admission, one-second progression, melee/Throw, Object motion, observer Awareness and narrowly scoped evidence exist. Supported integrations are bounded; arbitrary Actions/consumers may still refuse.
- StatisticalGroup adult member realization is an opt-in typed world operation, atomic with ObjectRegistry, Group membership/realization and Encounter participation; the Being becomes eligible at a later boundary. It is not generalized entity generation or an automatic consequence of Spot.
- ReproductionGroup is a separate world-level identity/parent-membership model with bounded generation and checkpoints. Parentage does not imply population, place, residence, or observer knowledge.
- NPC Generator import is narrow and source-preserving. The separate `npc-generator-web` repository is independently owned/read-only; do not infer skills, equipment, history or biology from unverified source fields.
- Checkpoint formats are bounded (Run/Spot and reproduction-related slices); they do not establish general portable Universe save/restore or authenticated historical receipt transfer.

## Universe 8 workflow and next decision

The user's first requested activity is a **review and prioritization**, not implementation. Compare world-demanded on-demand Encounter instantiation (forest-watch scenario) with targeted Remain Aware/contact loss/reacquisition and other open tasks. Treat the forest-watch note as a requirements illustration, not permission to invent encounter frequency, target selection, geography, or discovery rules. Explain the smallest executable first slice, uncertainties, and tests. Wait for the user's explicit choice before implementing.

For an approved assignment, inspect the actual checkout and instructions first; use an executable vertical slice; preserve unrelated work; make 1–3 small green commits with exact path staging; run focused tests and the appropriate complete suite only when required; provide a concise report with real commands/results/limitations. The user expects the assistant to assess the report, state `Where we stand`, and supply the next compact assignment. No push without separate explicit authorization.
