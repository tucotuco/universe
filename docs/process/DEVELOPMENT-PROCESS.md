# Universe — Development, Task-State and Handoff Process

> **Version:** 1.0 · **Adopted:** 2026-11-11. This is an operational collaboration contract, not a change to adopted Encounter mechanics or authorization to publish Git history. **Companion single state/ideas register:** [`TASKS.md`](../../TASKS.md).

## 1. Purpose and source-of-truth boundaries

Universe is a long-running, multi-conversation engineering and simulation-design project. Decisions, experiments, source code, user ideas and unfinished work must survive transitions between ChatGPT conversations and Codex conversations without making the user repeat prior context or reread months of logs. Use a **small number of durable, version-controlled entry points**.

1. **`TASKS.md` is the sole canonical project-wide current-state and ideas list.** It includes bounded completed capabilities, at most one active implementation program (and explicitly says when none is active), next candidates, open/blocked/deferred work, a current Action inventory and all retained future ideas. It is a *state snapshot*, not a journal. Do not maintain a separate competing ideas backlog or separate canonical task list in `docs/tasks/`.
2. **`docs/process/DEVELOPMENT-PROCESS.md`** (this document) defines how people and agents maintain that state, execute code changes, report results and hand off context.
3. **Adopted rules and decisions** (e.g. `docs/encounters/README.md` and its effective revision/supplements/issue register) define simulation behavior. `TASKS.md`, assignments, code comments, examples and speculative ideas **do not create or silently amend rules**.
4. **Current code and executable tests** establish which behaviors are implemented and under what limits. Passing a bounded fixture does not establish general conformance. Reports record evidence; a report is not a substitute for source inspection.
5. **`docs/assignments/<ID>.md`** specifies an authorized Codex work outcome; **`docs/reports/<ID>-report.md`** records its execution and evidence; **Git commits** preserve the actual implementation and document edits. These are **logs/provenance**, not the current-state register.
6. **`docs/design/`, `docs/tasks/`, handoffs, archived backlogs and experiments** hold explanations, detailed proposals, rejected alternatives and historical context. Links may point into them; their embedded historical statuses must not compete with the present `TASKS.md`. Existing [`docs/design/deferred-ideas.md`](../design/deferred-ideas.md) is retained as archival source evidence after reconciliation, not maintained as a second live ideas register.

**Canonical priority for disagreements:** user-adopted decision/current applicable rule > current code/test evidence for actual implementation > current TASKS state for project tracking > current assignment/report for work scope/evidence > topic/design note > handoff/archive/conversation recollection. A task-state entry may be wrong; preserve uncertainty and repair it based on evidence, never by silently changing an adopted rule.

## 2. Project principles that all participants preserve

### Simulation and worldbuilding

- **Resolution on demand:** detail is sampled/realized when a legitimate world requirement or interaction calls for it; avoid resolving entire lives, populations or spatial environments prematurely.
- **Reality / Observation / Belief:** objective committed facts, sensory evidence and an Agent's interpretation are independent. Agents and browser players cannot inspect privileged simulation state merely because the engine has it.
- **Constraint and identity conservation:** old committed facts, temporal consequences, statistical aggregates and real Object/Being IDs constrain later realization. No duplicate individual or invented retroactive knowledge.
- **Deterministic, atomic behavior:** validate complete prospective changes, sample with reproducible owned RNG streams, evaluate against consistent snapshots and commit compatible effects together; failed proposals/transactions do not leave partial world changes or consume committed RNG.
- **Current Encounter chronology:** movement occurs before the second's nonmovement Actions; Actions due at one boundary use one common post-movement/pre-Action snapshot; consequences commit together, and same-second effects do not retroactively alter another eligible Action. No Action resolves at time zero.
- **Resolution fidelity:** exact continuous metric Cartesian positions under the adopted world-space convention; user-facing one-yard regular hexes and yards; inches/pounds for Being anthropometry; do not treat a display hex as an assumed 3-D body model. Respect current rules README and later applicable supplements.
- **Source versus state:** `npcgen` is independent authority for generated *initial* NPC specifications and age-derived starting skills. Universe instantiates/manages live Beings/Objects, experience, Action consequences, and Saved Encounters. Loading does not rerun NPC generation. A ground Object does not grant ready/equipped effects.
- **Scope-qualified observation:** the interim accurate-perceptible-property Spot/Listen rule does not grant total knowledge; future uncertainty is a separately adopted design subject.

### Engineering, ownership and evidence

- **Reuse before rebuilding:** inspect current native implementation, legacy tactical code, work-stash experiments, earlier tests and Git history before implementing apparently missing mechanics. Adapt reusable logic to the current transactional contracts; do not dispatch legacy sequential mutation within a selected transactional Encounter.
- **Outcome-oriented assignments:** prefer complete, executable capability clusters with shared dependencies over a stream of tiny reports. An approved assignment authorizes the full stated observable outcome, including ordinary debugging, dependencies, test repairs, integration, persistence, UI checks, and coherent local commits. Completion of the acceptance criteria—not a passing subtest, bounded subcommit, or report—is the stopping condition. Continue materially incomplete work within the same assignment. Only a genuine unresolved game-rule decision, external dependency, authorization boundary, or substantiated technical blocker warrants incomplete closeout; finish all independent in-scope work first. Do not manufacture new assignment boundaries to obtain routine reports. Resolve ordinary engineering dependencies autonomously; consult the user only for genuine rules/vision/authorization conflicts.
- **Durable active program:** one approved ACTIVE implementation program persists across subcommits, bounded reports, and Codex/ChatGPT conversation transitions until its outcome is achieved, the user explicitly pauses or changes it, or a genuine blocker is recorded. Completing a subordinate Action or bounded slice must not silently clear the parent ACTIVE program. Keep per-Action DONE (bounded) entries distinct from the larger program's PARTIAL/ACTIVE state in `TASKS.md`.
- **Focus tests first:** run newly added/affected tests, neighboring regressions, syntax/structural checks, and real browser smoke when relevant. Reserve the expensive full HTTP-inclusive suite for meaningful integration milestones or high-risk changes. Report which exact tests ran, timings and failures; never imply unrun suites are green.
- **Execution timestamps:** every Codex execution closeout, including a continuation of an existing assignment, records its actual start and end as ISO 8601 timestamps with explicit timezones and the calculated elapsed duration as an ISO 8601 duration (for example, `PT2H23M45S`). Capture Start when execution begins and End immediately before closeout; do not estimate or fabricate either. If an earlier Start was not recorded, say so explicitly. Put the interval in both the final Codex chat response and the persistent engineering report. For a multi-session assignment, list every execution interval separately, report active execution time as the sum of those intervals, and distinguish it from total calendar time from the first Start to the last End. Keep the chat concise by putting a session's Start, End and Elapsed on one line; the report retains the full interval history and totals.
- **Verification levels:** distinguish unit/native integration; process-restart Save/Load; HTTP/session or JavaScript harness; actual interactive Chrome/browser; full-suite. Do not call a mocked browser an end-to-end user walkthrough.
- **Preserve the working tree and local-only resources:** first inspect `git status`, branch/HEAD/upstream; never reset/clean/stash wholesale, blanket-stage unrelated files, overwrite unknown work, or modify protected archives, independent `npc-generator`, or local secrets. Before replacing a clone or publishing/migrating a checkout, inventory essential local-only assets, identify their destination and backup, record byte/mode checksums outside Git, restore and verify them before retiring the source, and explicitly ignore the restored local-only paths. Stage only reviewed paths. Make small coherent commits at actual functional boundaries (often 1–3 per assignment; more if justified), and report commit hashes.
- **No unauthorized publication/history rewrite:** never push, force-push, rebase, rewrite/sanitize historical commits, or publish private paths/data without explicit user authorization. Local commits are not equivalent to remote backups. Apply safety checks before any approved publication.
- **Inspectability:** prefer ordinary readable, version-controlled files and reproducible commands to premature database/service infrastructure.

### Publication safety and repository identity

- A configured remote name is not proof of destination identity. Before any approved push, verify the exact remote URL, intended repository and visibility, branch/refspec, tracking configuration, live remote tip, and fast-forward ancestry. Fetch the remote; stop if the destination moved or diverged.
- Ordinary feature, documentation, and handoff assignments do **not** authorize push or history rewrite. Rewrite only unpublished commits when the current user explicitly authorizes that scope. Published history requires separate, specific authorization. Never force-push by default.
- Preserve dirty/untracked user files, ignored local data, sibling repositories and private archives. For an authorized history rewrite, first create and verify a private recovery bundle/clone outside the worktree, then transform an isolated clean clone. Do not push backups or backup refs.
- Protect local resource paths, machine/user identifiers, credentials, local session/world data, and unreviewed artifacts. A `.gitignore` change does not remove committed data. Do not put actual sensitive strings in reports, task state, commit messages, or ordinary scanner output; report safe file locations, categories, and counts.
- Before **every commit**, inspect the explicit staged file list and run `python tools/check_publication_safety.py --staged` (or a documented equivalent). This covers staged text/path names and refuses actionable findings. It intentionally does not scan arbitrary untracked files.
- Before **every separately authorized push**, verify the exact proposed range and run `python tools/check_publication_safety.py --range <verified-upstream>..<proposed-tip>`. Review every new commit, changed path, path version, and newly reachable blob version, including content removed before the tip. A changed path that reuses a blob already reachable from the base is scanned too. Also inspect secrets and large/sensitive artifacts. Require zero unreviewed findings; a clean HEAD grep or `git diff --check` is not a history audit.
- Already-published findings may remain only after read-only content review confirms they are benign and the report records the exact verified public ancestor as a reviewed legacy baseline. The full-history scan may continue to report that baseline; this does not make the entire history clean. The proposed descendant range must have zero unreviewed findings, and a changed descendant that reuses a baseline disclosure must fail. Do not add broad path, folder, or filename waivers. If public content is sensitive or uncertain, stop and obtain a specific user decision.
- Review findings in context. The checker recognizes explicit `<PLACEHOLDER>` illustrations and repository-relative paths; do not add broad or undocumented allowlists. If real credentials, already-published disclosures, or ambiguous high-sensitivity material appears, stop publication and obtain a specific user decision.
- Every engineering report records the staged scan result and whether publication was authorized. If pushed, it records the verified range, history-audit result, exact normal refspec, push type, and independently confirmed remote tip. Handoffs identify unpublished commits and any publication hold or required sanitized continuation. A local hook alone is not a shared control.

## 3. `TASKS.md`: required shape and maintenance

### What a state entry means

Each tracked entry has a **permanent ID**, concise current capability/idea, **current status**, bounded evidence or implementation limit, and the *remaining* requirement if not done. Link to relevant design or last authoritative report rather than list the history of every increment.

Approved statuses:

- **DONE (bounded):** stated acceptance criteria are supported by committed source/report/tests; related broader gaps remain separate OPEN/PARTIAL items. Completed items remain visible in the register.
- **ACTIVE / ASSIGNED:** one current authorized implementation program; assigned without a report must not be labeled complete. The ACTIVE program can involve many related open items.
- **PARTIAL:** supported but explicitly narrower than intended scope; say which cases work and what remains.
- **OPEN:** not demonstrated complete; describe a useful next outcome.
- **BLOCKED:** specify the *actual* unresolved adopted-rule decision, authoritative fact, environmental dependency, or external integration; missing code/tests/GUI alone is engineering work rather than a perpetual blocker.
- **DEFERRED:** valid retained task or approved direction deliberately not active.
- **IDEA:** a proposal retained for future discussion; neither adopted mechanics nor authorized work. Describe it faithfully and neutrally.
- **VERIFY:** claims or status cannot be established from the actual checkout available; state what evidence would settle it.
- **SUPERSEDED / REJECTED:** when a previous idea or task is formally withdrawn, retain its ID and concise disposition/authoritative successor (unless it has become historically irrelevant *and* the user approves its removal). Do not silently erase it.

A checkbox `[x]` means DONE *for the bounded statement*. Open/partial/idea entries use `[ ]`. Do **not** use `[x]` merely because some adjacent experiment or plan was completed.

### Single register, no shadow backlogs

- All important ideas, including speculative ones casually agreed to be retained, are entered into `TASKS.md` with a stable `U-IDEA-*` identifier. An idea can be recorded without approving it. A line may link to a design note for substance.
- All currently actionable high-level capabilities use existing `U-*` IDs or newly allocated stable task IDs, with the next demonstrable outcome and dependencies. The Combat Action inventory may use dedicated stable IDs for visibility, but that does not imply one assignment per Action.
- Topic files remain useful for detail, and old task/idea lists remain historical sources; **do not maintain two evolving status authorities**.
- Do not turn the root file into chronological narration, dated update paragraphs, recurring test-count logs, or a list of every engineering commit. Version-control history and reports answer *how we got here*; `TASKS.md` answers *where we are and what remains*.
- Keep **at most one ACTIVE program**. When authorized implementation work is active, identify exactly one program; when none is active, say so explicitly. When the user changes immediate priorities, move that marker, leave interrupted work with honest state, and preserve unfinished scoped results rather than overwriting them.
- An idea mentioned in a conversation should become a new IDEA entry **when the user explicitly asks to preserve it, accepts a preservation suggestion, or the conversation explicitly identifies it as an agreed deferred development direction**. Do not automatically classify every exploratory question as a task; ask briefly if preservation intent is genuinely ambiguous. Record proposed and adopted semantics separately.

### When `TASKS.md` must be edited

1. **Before starting a Codex assignment:** Codex must read current `TASKS.md` and this process, identify impacted stable IDs, check for collisions and disagreements, and note the active task. It must not blindly trust a dated ChatGPT copy.
2. **As an assignment produces meaningful verified changes:** update the relevant lines' current status/limits and preserve distinct remaining gaps; create new stable IDs for genuinely new discovered capabilities/ideas with no suitable entry. Do not promote a task to DONE on planned work, compile-only, a mere catalog label, or passing an unrelated test.
3. **On completion or partial closeout:** the **same scoped implementation/documentation commit** should normally include the `TASKS.md` update (or a separate immediately adjacent scoped documentation commit if implementation staging or contention requires it). The report lists exactly which IDs changed. If state was not updated, report that as an explicit unfinished deliverable.
4. **On a decision/idea in a ChatGPT discussion:** the next repository assignment or explicit documentation-only change must incorporate that task/idea. In the meantime, ChatGPT should supply a precise patch/file rather than falsely claiming a Git update.
5. **At a conversation handoff or major milestone:** reconcile live checkout plus latest reports with `TASKS.md`; repair stale ACTIVE/OPEN claims without rewriting the historical evidence. Check older ideas for missing links.

**Conflict rule:** if the real repository has newer or additional rows than a separately prepared candidate, **merge by stable ID and current evidence, never overwrite wholesale or silently discard a local idea**. Unresolved statuses remain VERIFY, not guessed DONE. Two simultaneous Codex assignments must not race to rewrite the same file; serialize the `TASKS.md` reconciliation at commit boundaries.

## 4. Roles and work cycle

- **User:** sets vision and priorities, adopts rules, authorizes material changes and Git publication, assesses meaningful product behavior. A user-authorized assignment includes routine local commits within its approved scope; separate explicit authorization is required for Git publication or history rewriting. No need to repeat already captured decisions.
- **ChatGPT coordinator:** reconciles latest report, current task/idea state and broader vision; flags genuine rules decisions; supplies compact self-contained repository-relative assignment and exact invocation; maintains handoff coherence and prepares state/document corrections. ChatGPT cannot assert that Codex edited the local repository without an actual report/check.
- **Codex (Universe repository):** inspects true checkout and rule authority, implements/test/commits native source and UI, updates `TASKS.md` under the assignment's explicit instructions, writes engineering report, preserves unrelated work. It must not modify the independent NPC generator.
- **NPC Generator owner (separate Claude development):** maintains the independently importable `npcgen` library, its data, skill generation and initial profile contract. Universe integrates through public interface and reports cross-repo requests rather than duplicating generator code.

### Standard cycle

1. **State:** Read `TASKS.md`, this process, current adopted rules, and latest relevant engineering report. Confirm user priority and the active program or explicit absence of one; record newly accepted future ideas in the register.
2. **Assignment:** ChatGPT prepares `docs/assignments/<ID>.md`. It states the desired *observable outcome*, required authorities and evidence, the impacted `TASKS.md` IDs and explicit state-update instructions, existing source/reuse leads, likely shared dependencies, accepted test/UX boundaries, preservation rules and reporting file.
3. **Execution:** User places assignment in Universe repository; Codex runs `Execute docs/assignments/<ID>.md.`. Codex captures the actual Start timestamp as execution begins, audits current worktree before editing, solves engineering details, makes coherent commits with focused testing and no unauthorized push. A continuation in a later session records a new Start.
4. **State update:** Codex edits `TASKS.md` to represent **what is actually now true**, preserving all unrelated items and deferred ideas. If a promised goal was not achieved, leave it PARTIAL/OPEN with a precise remaining gap; report the reason. Changes should appear in a reviewed Git diff.
5. **Engineering report:** Codex writes `docs/reports/<ID>-report.md`, including commit(s), tested behavior, new/changed task IDs, actual reproducible commands and results, environmental constraints, persistence, browser evidence and remaining blockers. Prefer a terse Codex chat message linking the report.
6. **Review and next step:** ChatGPT assesses the report against assignment and adopted rules, explains **Where we stand**, differentiates passed/partial/blocked, and chooses the next outcome-oriented task without losing the broader roadmap. If materially incomplete, continue the existing assignment rather than reflexively create a new microticket.
7. **Handoff when needed:** supply a current compact handoff pointing to `TASKS.md`, this process, actual rules, the current assignment, and newest report. State verified progress against the assignment's full acceptance criteria and every remaining obligation. A handoff is navigation, not a replacement objective or permission to narrow scope. At conversation startup, verify and read these canonical files before continuing; do not copy every report or substitute a stale handoff for checking the checkout.

After the assignment owner confirms that all acceptance criteria are met, Codex moves the completed assignment into `docs/assignments/archive/`. After ChatGPT reviews and accepts an engineering report, Codex moves that report into `docs/reports/archive/`. Use `git mv` so tracked history is preserved; if a completed source was previously untracked, first add and commit that reviewed source, then use a separate Git-aware rename commit. Never delete completed assignments or reports. Update `TASKS.md`, handoffs, adopted notes, and other maintained links to the archived paths in the corresponding scoped documentation commit. Keep active or unfinished assignments and reports awaiting review in their normal directories. Record the archival execution interval in the associated persistent engineering report, using the actual timezone-qualified timestamps required below. Run the ordinary staged-content and whitespace checks for every commit; archival does not authorize a push.

Every execution records its Start, End and calculated Elapsed in the persistent report, even when the assignment continues in a later conversation. At handoff, preserve each completed interval separately; the next Codex execution starts a new interval rather than extending or replacing the previous one. The final chat closeout repeats the interval values and, for multi-session work, distinguishes summed active execution time from the full calendar span.

## 5. Mandatory Codex assignment clause (copy into every future assignment)

The following clause is the default **required** content in `docs/assignments/<ID>.md` (customize IDs and expected transitions rather than leaving the placeholders):

> ### `TASKS.md` integration (required)
> - Before editing source, read repository-root `TASKS.md` and `docs/process/DEVELOPMENT-PROCESS.md` alongside the authoritative rules, prior relevant report, `git status -sb`, HEAD and branch. Identify the IDs this assignment affects: **[explicit list]**. Inspect actual status/evidence; do not assume the assignment's preparation-time snapshot is current.
> - Preserve every unrelated task, deferred idea, existing stable ID, other Codex changes and historical completed entry. If you discover a materially new dependency or previously untracked idea, add a concise uniquely numbered OPEN/BLOCKED/IDEA entry as appropriate; ideas are not adopted mechanics.
> - At each meaningful validated capability boundary and before final report, update the affected `TASKS.md` entries to reflect **actual outcomes and remaining limits**; move the one ACTIVE marker only as authorized by current priority. Mark DONE only for exact tested bounded acceptance, leave partial/blocked work explicit, and update links to the report/design where helpful. Do not append a chronological log of steps/tests/commits.
> - Review the task-register diff and stage only reviewed files; include `TASKS.md` in the relevant scoped commit (or immediately adjacent documentation commit). In `docs/reports/<ID>-report.md`, list **Task IDs before → after**, any ideas captured, and whether the root register was actually committed. If it could not be safely reconciled, say so explicitly and leave it unchanged rather than overwrite conflicting state.

Every future assignment must also include this publication-safety clause:

> Before committing, audit staged reports, handoffs, source, tests, configuration, and paths for local/private resource paths, secrets, and unintended files with `python tools/check_publication_safety.py --staged` or a documented equivalent. This checks the staged change, not history. A push or history rewrite still requires separate explicit user authorization. If publication is separately authorized, verify the live destination and audit all newly reachable commits, metadata, changed paths, and object versions with `python tools/check_publication_safety.py --range <verified-upstream>..<proposed-tip>`; stop on unresolved findings or upstream movement. Never force-push or rewrite published history under an ordinary assignment.

### Other required assignment elements

- **Identity:** stable assignment ID, intended repository path and required report path; exact paste prompt.
- **Outcome/acceptance:** a playable or executable capability and authoritative conditions; clarity on what *does not* count (e.g. dependency inventory or inert GUI button).
- **Source authority:** current rules README, code, prior reports/tests, and applicable historical implementations to consider for reuse; never presume last week's HEAD or `npcgen` version.
- **Allowed scope and exclusions:** user-adopted invariants, no speculative physical values, no private leakage, no parallel resolver or hidden simulation shortcut.
- **Test/replay plan:** focused tests, nearby regressions, deterministic fixed seeds, rollback/identity/privacy, fresh-process persistence, real browser when applicable, exact run commands and timings. Full suite only when warranted.
- **Git safety:** current worktree inventory, preserve user files, clear commit boundaries, no push or history rewrite without explicit authorization.
- **Report contract:** what implemented, genuine limits, whether the intended user outcome is demonstrated, failed tests, environment vs logic, commits, `TASKS.md` changes and next dependencies.

## 6. Mandatory engineering report shape

An ordinary report is concise but source-grounded. Every report records each Codex execution interval with explicit-timezone ISO 8601 Start and End timestamps and its calculated ISO 8601 Elapsed duration. For multi-session assignments, list intervals separately and give both summed active execution time and total calendar time from the first Start to last End; if a prior Start was not recorded, state that explicitly. Recommended order:

1. **Where we stand / result:** accepted outcome versus promised target, complete/partial/blocked, native versus UI exposure.
2. **Repository and rules:** HEAD/branch, original dirty state, scope of changes, current adopted rules + important interpretations, unchanged independent projects.
3. **Implementation:** meaningful changes, native Action/Being/Object/evidence/state contracts, reused legacy/experimental algorithms, known limitations.
4. **Reproduction:** exact executable test/demo command, input/seed/initial conditions, observed Action boundaries and authoritative results; browser clicks if claimed.
5. **Verification:** exact commands, counts, times; new vs baseline failures; fresh-process continuation; native/HTTP/Chrome distinction; full-suite status stated explicitly.
6. **`TASKS.md` transitions:** impacted IDs and before→after, added IDEA/dependency IDs, the active marker or explicit no-active state, and confirmation of committed state or outstanding reconciliation.
7. **Publication audit:** staged-content scan command/result and findings count. If a push was separately authorized, state verified destination/range, history-level audit result, exact non-force refspec, and independently checked remote tip. Clearly distinguish “not pushed” from “audited and safe to push.”
8. **Commits and safety:** hashes, staged paths, worktree status, no unapproved push, notable unresolved environment or security concerns.
9. **Remaining gaps:** exact next demonstrable outcome and genuinely unresolved rule decisions—not a broad re-inventory of already accepted work.

After ChatGPT accepts the report, archive it with `git mv` to `docs/reports/archive/`, update maintained links, and include the move in the audited local documentation commit. Do not archive a report that has not been reviewed and accepted.

A failing pre-existing test still matters; demonstrate its baseline if claiming it predates an assignment. Do not weaken checkpoint integrity merely to silence the failure.

## 7. Handoff contract: ChatGPT and Codex

### At the start of a new ChatGPT conversation

Provide `TASKS.md` (or a verified accessible repository/library copy), `docs/process/DEVELOPMENT-PROCESS.md`, and the latest relevant report/assignment. Refer to the active Encounter rule README, newest dated handoff, and independent `npcgen` boundary if pertinent. Assistant should:

1. State the **current objective and active task, or explicitly say no implementation task is active**, recently demonstrated outcomes and concrete unresolved blockers from the register; no generic re-design of completed decisions.
2. Confirm that local Git/reports may be newer than the supplied snapshot; ask Codex to verify the actual checkout when an assignment runs, not the user to re-explain history.
3. Review the most recent Codex report or ongoing assignment; provide **Where we stand**, one compact next assignment and exact prompt when appropriate.
4. Capture any new accepted idea into the register through an explicit file/patch or the next scoped Codex task. Do not promise invisible background edits.

### At the start of a fresh Codex conversation

The first user/Codex prompt may be:

> Continue the Universe repository workflow. First read `TASKS.md`, `docs/process/DEVELOPMENT-PROCESS.md`, `docs/encounters/README.md`, the latest relevant handoff, and the currently assigned `docs/assignments/<ID>.md`; inspect the actual branch/HEAD/status and affected source/tests. Preserve unrelated work and existing stable task IDs. Execute the assignment outcome, update `TASKS.md` according to its required clause, run focused evidence, commit reviewed paths, and write the required report. Do not push or rewrite history without separate explicit authorization.

Assignments remain active through their complete observable outcome, including ordinary implementation, regression repair, persistence, and UI acceptance. Bounded subcommits and reports are progress records, not new stopping points or permission to narrow scope. The completed handoff names the actual assignment path, authoritative rules, verified results against the full criteria, and all remaining obligations. Keep the active program durable across conversation changes until completion, an explicit user priority change/pause, or a documented genuine blocker.

When the handoff explicitly confirms assignment completion, move that assignment using `git mv` into `docs/assignments/archive/`; when it confirms report acceptance, move the report using `git mv` into `docs/reports/archive/`. Update the handoff and all maintained references in the same scoped documentation change. Leave incomplete work and reports awaiting review in their normal locations. Never delete archived work.

**Chat closeout:** keep the default Codex completion response to at most six brief lines unless the user asks for detail. Include the actual Start timestamp, End timestamp and calculated ISO 8601 Elapsed duration in the final response; one line may hold all three. For a multi-session assignment, include each interval separately and distinguish summed active execution time from total calendar time. Put commands, test evidence, rule analysis, remaining gaps and the complete interval history/totals in the persistent engineering report. If an earlier Start was not recorded, state that explicitly instead of backfilling an estimate. A user-authorized assignment already covers routine coherent local commits and report corrections within scope; do not seek separate conversational approval for each one. Pushes, history rewrites, and material out-of-scope/destructive work still require the applicable explicit authorization.

A handoff document is **navigation**, not a second task register. If the handoff contradicts current `TASKS.md`, rules or source, document the conflict and resolve it from actual authority, not from a guessed chronology.

### Handoff checklist

- At most one ACTIVE program (or explicit no-active state), latest completed bounded capabilities, open/blocking dependencies and long-term idea coverage represented in `TASKS.md`.
- Current rules README/issue register and selected relevant design notes identified.
- Current branch, HEAD, upstream divergence and push/safety status **verified or labeled historical/unverified**.
- Latest assignment and actual report/commit(s) linked; reported tests and unresolved regressions named.
- No inaccessible private files presumed present, no speculative change to independent NPC Generator, no redundant history dumps.

## 8. Ongoing maintenance

`TASKS.md` is always the best available statement of current project state; this process makes it reliable over time. Reconcile it against the actual checkout and the newest evidence at assignment closeout and handoff boundaries. Completeness of every conversation's ideas cannot be guaranteed without reviewing those conversations or their exports, so keep a specific verification item in the register rather than declaring historical omniscience.

When a separately prepared register, assignment, handoff, or report conflicts with the live register, merge by stable ID against current user decisions, adopted rules, source/tests, and the newest report. Preserve unrelated dirty and untracked state. Do not infer an active task from an old assignment or promote a candidate to authorization. Keep archival/deferred source documents for provenance; update current tracking only in `TASKS.md`.
