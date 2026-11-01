# Universe 5 — continuity handoff

**Prepared:** 2026-10-29  
**Transition point:** After Codex Increment 5D2C11, before Increment 5D2C11A.  
**Status:** Context handoff, not a new source of simulation rules. Verify the actual checkout before making changes.

## 1. Project vision — preserve the larger purpose

Universe is a persistent, extensible world-building and simulation system that can integrate physical, geographic, ecological, social and individual-agent processes. Its essential principles are:

- **Resolution on demand:** represent broad regions and populations at low detail; realize detail only when a question, observation or interaction needs it; preserve established coarse constraints.
- **Reality / Observation / Belief:** one objective established Reality, potentially different evidence and beliefs for different observers.
- **Statistical to realized:** correlated stochastic attributes become reproducible concrete facts only when necessary, and remain established thereafter.
- **Consistent causality and history:** what happens to entities and why must be reconstructible without treating observer knowledge as omniscient Reality.
- **Multi-resolution spatial context:** ISEA TriFold is the accepted grid basis; broader geography, astronomy, populations and world generation remain largely exploratory.
- **Experience goal:** a playable/explorable vertical slice joining spatial context, Agents, Encounter actions, observation, statistical realization and accumulated experience—not merely an elaborate combat engine.

**Do not** mistake the current persistence work for the end product. Once a first save-and-resume demonstration works, prioritize wider vertical-slice integration over indefinite infrastructure deepening.

## 2. Key established Encounter architecture

Consult `docs/universe4-authoritative-decisions-2026-10-27.md` in the user's actual repository (not this summary) for authoritative details.

- Integer-second completion boundaries: movement advances to the boundary; all due non-movement Actions evaluate against one frozen post-movement/pre-action snapshot and commit consequences atomically.
- Valid whole-choice scheduling, object-use reservations, pure preparation, accepted-choice editing before execution, and transactional RNG.
- Consequences and experiences are Target-owned; Action records identify what the Action did, its Targets and causal effects. Do not infer Target HP change or skill progress by subtracting Action fields.
- Simultaneous practice is one Target-owned `BatchSkillUse` transition with multiple causal exercises, not a sequence of independent level changes.
- Ordinary damage adds and may produce negative HP; fatal hits have separately adopted non-stacking semantics.
- Reality, Observation and Belief are separate; objective batch realizations are shared where appropriate, subjective outcomes are observer-specific.
- Physical fatigue Revision 4 uses Q and B persistent reserves, with PCFS fixed at five, but *live Q/B settlement is still deferred*.
- Legacy progression remains the default; transactional progression is opt-in for supported scenarios. Existing refusal/compatibility behavior must remain intact.

## 3. Engineering progress through 5D2C11

**Evidence:** the previous Codex reports, supplied by the user and assessed in Universe 4. Test counts below are Codex-reported, not independently rerun by ChatGPT.

### Completed or demonstrated in a bounded subset

1. Transaction preparation, whole-choice scheduling, one-second atomic commit, target-side effects/history, and developer inspections (5C series).
2. Data-only portable accepted future Run/Spot choices (5D2C1).
3. Detached committed Run/Spot receipt descriptors and explicit rebinding obligations (5D2C2).
4. Closed native field/alias/definition/ownership check for restricted Run/Spot graph (5D2C3).
5. Coherent inactive in-memory checkpoint envelope (5D2C4).
6. Deterministic canonical JSON bytes and strict decoding, with byte-identical cross-process round trip (5D2C5).
7. Fresh initial zero-boundary native Universe/Encounter reconstruction in quarantine, including supported future Run/Spot choices (5D2C6).
8. Precise refusal of one committed boundary pending safe historical projection (5D2C7).
9. Pure detached, cross-process one-boundary Spot historical projection, including simultaneous Target-owned practice (5D2C8).
10. Quarantine API corrected to expose only immutable detached views; privately retained native graph (5D2C9A).
11. Private identity shells bound to two simultaneous Spot Actions and one target-owned practice transition without issuing receipts (5D2C9B).
12. Fresh private native Beings materialized with their actual post-boundary state (HP, location, Q/B, skills, experience, etc.), while committed history remains in a detached sidecar (5D2C10).

**Not yet implemented:** authentic restored receipt creation; installation/validation of authoritative committed historical Target/Action records; permission to run a reconstructed world; user-facing save/load; true deterministic save-and-resume; general support for other Actions, entities, observers, Reality additions, and multiple boundaries. `closure_validated`, `portable_schema_defined`, and `restore_verified` remain **false**.

### Current precise blocker: 5D2C11

Codex correctly stopped before production changes. Ordinary `Encounter.__init__` explicitly rejects `time != start_time` with `BoundaryInvariantError('Restoring an advanced Encounter requires an unsupported checkpoint migration')` (`src/encounter.py:102–110` in the reported checkout). It also initializes boundary/coordinator/ChoiceBook state after this guard. Starting at time zero then using `Encounter.step()` to arrive at time one would run simulation and is not restoration. The report says the private Being materialization and historical sidecar remain intact, but there is **no reviewed constructor for a quarantined Encounter at an already-committed cursor**.

One-boundary fixture: Encounter starts at 0 and has one committed boundary at 1, with two simultaneous native Spot Actions by one actor against one observed Being, one Target-owned `BatchSkillUse` transition (3 + 4 = 7 experience). The post-boundary source Being has 24 Spot experience and rank 2. Do not let these fixture-specific values become general rules.

5D2C11 reported **72 focused tests** and **1,523 full regression tests including HTTP**, all passing after loopback permission was granted. No production edits were made in 5D2C11.

## 4. Next work: 5D2C11A

**Narrow goal:** introduce and validate an *explicitly reviewed, quarantine-only* native construction path for an advanced-time Encounter. It must preserve the ordinary constructor's advanced-time refusal, validate timing/ownership invariants, construct boundary/coordinator/ChoiceBook context coherently, and expose no native graph or ability to step or issue receipts. Do not attach the 5D2C10 historical sidecar or authorize resumption in this increment. See the [archived 5D2C11A assignment](historical-evidence-archive-index.md#advanced-time-checkpoint-reports-and-assignment) for the precise Codex instructions.

If unsafe/incomplete, Codex should report the exact blocker rather than bypassing constructors or mutating timing after creation. The next later step would finish 5D2C11 by connecting the approved Encounter to already materialized Beings and sidecar, *still without issuing receipts or running it*.

## 5. Git and preservation policy

- Last deliberately consolidated and verified **R5 core baseline commit**: `c345e68e918659d1d3f976975ab4c681e9984087` (on `main`); Git tree `40567424ebf39e439018264ddb6125fe9559ef60`.
- 79 core files were committed in that baseline. Numerous other workbench, reports, optional projects and other files were intentionally retained untracked.
- All later checkpoint increments 5D2C1–5D2C10 are **uncommitted** in the user-local checkout. The Codex 5D2C11 report says no new production edits and no commit/push. Never reset, stash, clean, rewrite, or accidentally delete these files.
- Work only against the actual checkout. Previous reports and handoffs are evidence and task instructions, not a replacement for source/authoritative decisions.
- Prior full regression baseline: 1,523 tests pass from `tests/` with `PYTHONPATH=../src python -m unittest discover`; HTTP tests may require loopback socket permission. During development run focused tests, then **one** final complete suite. Avoid repeated costly broad audits and huge evidence bundles. Do not commit/push unless specifically authorized.

## 6. Required recurring assistant–Codex workflow

After the user posts a Codex report:

1. **Critically assess** completion against authorized scope, including any blockers, accidental behavior changes, actual tests, Git state, and unverified claims. Distinguish *reported* evidence from independent verification.
2. Provide **a brief plain-language “Where we stand” status** on every report: completed major steps, currently active increment/blocker, immediate next step, and connection to first genuine save-and-resume and broader Universe vision. Explain unexpected subtasks: why they are necessary and what they unblock.
3. **Automatically produce the next small, bounded, ready-to-use Codex handoff** in the same answer (unless the user changes direction): an actual downloadable ZIP with standalone Markdown assignment, brief README and verified SHA-256 sums; also an exact copy/paste Codex message. Create and verify files before linking. A blocker warrants a bounded design/verification task rather than speculative implementation.
4. Keep explanations comprehensible and avoid long lists of cryptic engineering terms. GPT-6 Luna in Codex and compact instructions have been effective for the user's usage limits; avoid recommending a switch absent a concrete reason.
5. Protect authoritative decisions and unchanged simulation semantics; no unapproved new rules, no claims of save/restore readiness until demonstrated. Stop at the authorized increment.
6. No need to produce the consolidated to-do document after each small increment. The user has local `encounters-outstanding-todo-updated.md` (revision 60, 2026-10-24). At **the first verified save-and-resume milestone**, produce an updated downloadable Universe-wide backlog reconciled with current code and reports, distinguishing done, pending, unresolved and deferred; retain original issue register authority.

## 7. Persistence strategy

The current strict file/JSON wire representation is a development and inspectability tool, **not a commitment to database architecture**. The user currently prefers inspectable files, which can be diffed and version-controlled. Do not introduce SQLite or another datastore prematurely; reconsider only if a demonstrated requirement justifies it.

## 8. Source-of-truth reading order

1. Actual repository source/tests for the current task, including `src/encounter.py`, `src/checkpoint_binding.py`, `src/checkpoint_reconstruction.py`, `src/checkpoint_views.py`, `src/checkpoint_wire.py`, `src/checkpoint_projection.py`, `src/transactional_progression.py` as relevant.
2. `docs/universe4-authoritative-decisions-2026-10-27.md`.
3. `docs/universe4-checkpoint-compatibility-contract-draft.md` and any later amendments in the checkout.
4. The recent Codex reports and assignment are preserved in the [historical archive index](historical-evidence-archive-index.md#advanced-time-checkpoint-reports-and-assignment).
5. Existing Encounters rules and working issue register for any mechanics questions.

## 9. Exact first message for the new Universe 5 chat

> This is **Universe 5**, continuing my Universe world-building/simulation project from Universe 4. I have attached `universe5-transition-handoff.md`; please read it and preserve its project context and established workflow, including the **plain-language “Where we stand” summary with every Codex report assessment**. The current Codex result is 5D2C11: it correctly stopped because the normal Encounter constructor refuses advanced-time reconstruction. The next authorized increment is 5D2C11A, a safe quarantine-only advanced-time Encounter construction contract, specified in the [archived 5D2C11A assignment](historical-evidence-archive-index.md#advanced-time-checkpoint-reports-and-assignment). Continue assessing each Codex report and automatically provide the next compact downloadable assignment with an exact paste-ready Codex prompt. Preserve all uncommitted work, authoritative decisions and existing refusals. Prioritize the first authentic save-and-resume demonstration, then broader integrated Universe work. Do not introduce a database yet.

**Attach this Markdown handoff when starting Universe 5.** Optionally attach the next Codex assignment too; it is also available as a separate file in the ZIP. It is not necessary to paste the entire historical conversation.
