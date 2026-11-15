# U-PLAYTEST-001 — Freeze a standalone playable Arena edition with a user manual

**Purpose:** deliver a genuinely executable, separate, fixed-version local Arena for the user to play while Universe development continues.

**Install this assignment at:** `docs/assignments/U-PLAYTEST-001.md` in the active Universe checkout.
**Execution report:** `docs/reports/U-PLAYTEST-001-report.md`, plus an identical release-specific `BUILD-REPORT.md` in the finished distribution.
**Codex invocation:** `Execute docs/assignments/U-PLAYTEST-001.md.`
**Type:** independent, time-bounded **packaging side task**, NOT a replacement for or implementation step of `U-OBS-001`; keep `U-OBS-001` the sole ACTIVE capability program. Do not begin perception changes in this packaging task.

## Required delivered outcome

Create a **working, frozen, separately installed macOS playtest edition** of the accepted **U-CAP-008A Arena**, with a double-clickable launcher, an independently installed runtime and a substantial **USER MANUAL**. It must remain playable after any later commits or edits to the live `~/Projects/universe` or `~/Projects/npc-generator` repositories. It must support both:

1. **Player vs Arena** (default): the user controls Being A, while Being B follows its selected Arena strategy.
2. **Arena vs Arena**: both Beings are autonomous, independently selecting supported strategies; the user is a spectator and can Advance, Run (bounded) and Pause.

The completed distribution is the primary deliverable. Merely writing build instructions, producing a source-only ZIP without a working launch path, or claiming success solely because the development checkout launches is **not** completion. **Do not substitute a demonstration app** for the actual current Arena or recode combat mechanics for the release. Include real native Action/Choice, `npcgen` initial-generation, observer privacy, both strategies, and Save/Load behavior.

Recommended immutable release label: **`Universe Arena Playtest — U-CAP-008A (2026-11-14)`**. Put the finished distribution *outside* every development repository, e.g.:

```text
~/Projects/universe-arena-playtest/
  U-CAP-008A-2026-11-14/
    Play Arena.command          # double-click Mac entrypoint; executable
    Install or Repair.command   # if needed for relocated/archive install
    USER-MANUAL.html           # readable without Python or network
    USER-MANUAL.md             # human-readable source
    README-FIRST.md
    BUILD-REPORT.md
    RELEASE-MANIFEST.json
    SHA256SUMS.txt
    app/                      # frozen working Universe runtime sources/assets
    vendor/                   # frozen compatible npcgen runtime and data
    runtime/                  # own Python environment/dependencies, not symlinks to development venv
    userdata/saves/           # separate user-writable saves (never overwritten on repair)
  Universe-Arena-Playtest-U-CAP-008A-2026-11-14.zip
```

The precise internally correct layout is yours to determine after inspecting the checkout; **verify the deliverables, not just the names**. If an existing output directory or ZIP exists, **do not overwrite**; use a noncolliding release directory/archive and report the exact paths. Do not include confidential/untracked local saves, backups, secrets, developer caches, `.git`, or unrelated historical files.

## A. Freeze the *accepted* revision, not a development worktree

- At startup inspect `git status --porcelain=v1`, branch, HEAD, `TASKS.md`, the current process document (`docs/DEVELOPMENT-PROCESS.md` or the repository's actual location), accepted `docs/reports/U-CAP-008-report.md` and `docs/reports/U-CAP-008A-report.md` (including archived locations), the current `U-OBS-001` assignment, and existing launch/runtime code. Find the actual **last accepted U-CAP-008A runtime revision**, including the controller implementation commit `ef71e42514094d2372b976be5d64acf3ea077fa9`, without inadvertently including in-progress U-OBS-001 or later changes. Record the exact source commit and why chosen. **Do not assume today's live HEAD is the accepted snapshot.** Use Git archive or an equivalent clean immutable export, not a copy of a potentially dirty development worktree.
- Identify the exact compatible `npc-generator` revision/library data needed to import `npcgen` and generate the U-CAP-008A Beings. Inspect its actual Git status **read-only**; export/copy a fixed compatible source revision (plus required package data), preserving provenance and its licensing/attribution where applicable. Do not edit, commit, push or install anything in the independent `npc-generator` repository.
- Produce a release manifest with Universe and `npc-generator` commit hashes, build timestamp, Python version and architecture, dependency versions/hashes where obtainable, Encounter controlling revision 70, generated Arena save schema `/7` and supported older versions `/4–/6` where confirmed, release scope, exact launch command, build platform and release-content hashes. Verify that the code imports the **bundled** `npcgen`, not `../npc-generator` or any live package in an external editable installation.
- Include all genuine runtime assets, native rule tables/config and web UI assets needed by `examples/generated_arena_browser.py`/`examples/arena_web.py`, as required by the actual source. Use those existing entrypoints and their supported server lifecycle, rather than creating a new simulator. Do not incorporate post-U-CAP-008A perception work or unsupported Action claims.

## B. Launchable, isolated environment

- On the user's Mac, provide an actual **double-clickable `Play Arena.command`**, tested with paths containing spaces. It must start a server bound to **loopback only** (`127.0.0.1`), choose an available port or detect/report a conflict, open the browser at the actual listening URL, show useful launch errors, and make quitting/restarting straightforward. A visible terminal window with Ctrl-C stop is acceptable. If native `.app` packaging can be added *without compromising reliability*, it is optional, not a substitute for the verified `.command` launch.
- Use a self-contained local application/source layout with an **independent runtime**: neither the development `.venv` nor imports from `~/Projects/universe`, `~/Projects/universe-old`, `~/Projects/npc-generator`, or their mutable files. Construct/package isolated Python dependencies. The finished installed release must start **without network access**; if an archive must be unpacked and installed once, include and test an `Install or Repair.command` that reconstructs the local runtime from packaged, checksum-verified resources **without requiring the live repositories**. A bundled wheelhouse or other appropriate offline dependency mechanism is preferred; if the host Python interpreter is a deliberate external prerequisite, document its exact minimum version and make errors actionable. **Do not promise a portable .venv if relocation invalidates its shebang paths.**
- Include a reusable versioned ZIP/archive of the release **separate from the runnable installed folder**. Test extraction to a different path (ideally including whitespace), installation/repair if needed, launching, generation and Save/Load **without access to development-source paths**. Use executable permissions appropriate for macOS and describe any normal Gatekeeper/script-launch workaround without instructing users to disable system-wide protections. No privileged installs, global `pip install`, remote service or permanent background agent required.
- Use a distinct `userdata/saves/` or equivalent user-selected location; maintain immutable release code versus mutable saves. Document how the browser's download and upload controls work and how to move downloaded saves into the release's user saves folder. Never silently migrate/overwrite a saved world. A new playtest release later must be able to coexist with this one.

## C. User manual — practical, tested, not merely API documentation

Supply **both** `USER-MANUAL.html` and `USER-MANUAL.md` (fully offline) in the distribution, preferably with a concise `README-FIRST.md`. Match the **actual frozen UI**; test instructions by following them yourself in the released copy. Include:

1. What the Arena Playtest Edition is, frozen version, supported scope, limitations and source-of-truth distinction: **this is a test version** and its saved data are not automatically compatible with future development builds.
2. Installation/first launch, startup prerequisites, ports, local-only server, stopping/restarting, where your files and saved Encounters live; archive extraction and repair.
3. **Generate Encounter**: common XP input for two `npcgen` Beings, map width/height (at least 5), root seed/reproducibility, equipment modes and optional ground profile, player-controlled/auto-controlled roles, mode selector and legal strategy options. Show only controls actually present; for Arena vs Arena, documented supported `attack_only` and `defense_only` independently per side (verify if others truly supported at the selected snapshot). Explain Generate versus Load without regeneration.
4. **Player vs Arena** walkthrough: movement destination and rates (walk/jog/run/sprint where available), hex grid versus continuous native position, facing/turn and reaching an opponent, selecting a target/own Action catalog, Draw versus Ready and motion-specific preparation, attack declaration and one-second Advance, timing until resolution, inspecting `not_facing`/out-of-reach/hit/miss and committed feedback. Explain Action composition and defensive actions to the extent actually shown.
5. **Arena vs Arena** walkthrough: choose distinct strategies, Generate, Step/Run (ten-second bounded run as accepted)/Pause, observe the referee/spectator chronology versus Being A's own observations, and why manually issuing tactical actions is disabled in this mode.
6. **Two verified reproducible examples from accepted reports**, recheck them in the release rather than promising the exact outcome by assumption:
   - Player vs Arena: seed **14**, XP **10000**, **10×5**, equipped, opponent `attack_only`; move with Walk and `turn` toward hex **(8,1)** and use Dagger Thrust. The accepted U-CAP-008 demonstration had native hits, but report the released build's actual receipt/outcome.
   - Arena vs Arena: seed **14**, XP **1000**, **5×5**, equipped, A `attack_only`, B `defense_only`; step/run ten seconds. The accepted U-CAP-008A demonstration had B Dodge and A Dagger Thrusts; report the released build's actual receipt/outcome.
7. **Save Encounter and Load Encounter**: browser Download/Upload steps, backed-up saves, version compatibility, strict rejection messages, fresh-process continuation, avoiding loss of the current Encounter. Distinguish the former Chrome *automation extension* upload limitation from ordinary human use; test real browser Load if possible and state exactly what was tested.
8. Visibility/privacy and current uncertainty: player Action catalog versus opponent information, current availability reasons, referee chronology not an NPC knowledge source, consequences seen in the UI versus hidden native state.
9. Controls/strategies table, glossary of Action/Being/Object/Observer/Encounter, troubleshooting (port busy, dependencies, file permissions, stale browser cache, empty Action choices, missing equipment, `not_facing`, invalid save/version), and known unimplemented/bounded work (Shoot, Deflect, broader Throw, unmodeled physics/geometry, perception expansion).
10. Release manifest, exact version, licensing notes as appropriate, where to report a bug (with seed, settings, game time, result and safely shareable save), and an explanation that **future repo development does not update this frozen copy**.

Optional screenshots should be genuine captures from the released app, clearly labeled; never use stock or fabricated gameplay screenshots.

## D. Acceptance — demonstrate actual play from the frozen release

Produce and record all of the following, running **from the separate release folder**, not the development checkout:

1. **Finder-style launch smoke:** invoke the same double-clickable launcher or its exact tested equivalent; show correct browser page and version. Confirm process cwd, Python executable, module origin of `npcgen`, web asset paths and config origin are **inside the release** (except deliberate standard-library/System Python components). Show browser opens only loopback.
2. **Player vs Arena end-to-end:** Generate from the release; independently reperform supported movement/facing, weapon Action and a committed combat result in a served browser, or report an exact reproducible divergence with a fix before claiming DONE.
3. **Arena vs Arena end-to-end:** Generate and run two independently controlled Beings from the release with real native Actions and a committed nonzero consequence in the served browser. Confirm spectator cannot issue player combat commands and AI does not read the spectator chronology.
4. **Save/Load:** use a save created by this release and restore/continue it in a **new operating-system process**, comparing native IDs, time, mode, strategies, HP, Action results and RNG. Confirm old schema migrations where represented; do not claim a browser upload if only tested through native/HTTP route.
5. **Independence test:** start the installed release after making the live Universe and `npc-generator` paths inaccessible to the release process or otherwise proving no mutable-repository import is possible; don't rename/mutate someone else's live directories. Perform a separate extracted-archive smoke in a new path. Show no network is required for an already installed launch.
6. **Manual test:** follow each documented quick-start walkthrough against the frozen executable and correct inaccuracies. Verify offline HTML opens, document hyperlinks and launch scripts resolve, and `SHA256SUMS.txt` matches the actual archived release. State the precise macOS/Python/architecture tested.
7. **Focused tests:** reuse selected seed-14 Player-vs-Arena and Arena-vs-Arena regression tests, persistence, source-import isolation, launcher/archive smoke and manual links. Report actual commands, pass/fail results, elapsed times. Do not run/claim the entire long Universe test suite unless needed. No success claims based solely on tests run against the development checkout.

If an unavoidable hard blocker prevents a release actually starting and being playable, report the blocker and **do not mark DONE**. It is better to leave the release unapproved than to give the user a nonfunctional ZIP.

## E. Repository/process safety and report

- **Keep `U-OBS-001` the sole ACTIVE development program**; this sidecar release operation must not adopt perception changes, replace that ID, install the conflicting `U-CAP-009` draft, or mutate the main Arena code. If U-OBS-001 is already underway, export U-CAP-008A's verified *historical commit* rather than freezing uncommitted newer source.
- At startup inspect the five pre-existing staged historical U-CAP-002/U-CAP-003 and U-THROW-001 archive paths plus the untracked `docs/assignments/universe-arena.json`. Preserve actual current index state; **never** `git add -A`, reset, clean, stash, overwrite or package the user's untracked save. No pushes, forced Git operations, permission changes to unrelated paths, or edits to `npc-generator`, `universe-geology`, backups, historical source.
- Read actual current `TASKS.md`, adopted rules and development process, and inventory `docs/ideas/inbox/*.md` on startup **and before any final task-register commit**. Register any complete independent idea safely as IDEA without treating it as authorized implementation; do not invent idea submissions. Avoid concurrent edits to TASKS when U-OBS-001 is being changed; coordinate at a safe commit boundary. If safe, add a new **U-PLAYTEST-001 packaging milestone** to the register without changing the one ACTIVE program; otherwise document why this nonimplementation side task was not registered and leave the active task untouched. Report intake ID mappings/pending exceptions.
- The **separate distribution** is the requested user artifact. Version its release layout and provide a stable final folder path plus ZIP path in the Codex report. A copy may be backed up elsewhere by the user. Do not check in the binaries, large bundled Python runtime or generated saves to the development repository. Only version this assignment, concise engineering report, and optionally small launcher/release recipes when explicitly needed and independently safe.
- Write `docs/reports/U-PLAYTEST-001-report.md` with outcome matrix, paths and SHA-256, frozen commit IDs, tested launch/browser steps and modes, Save/Load, offline/archive relocation test, manual completion, exact test commands/results, Git index/worktree state, independent-repo preservation and actual **ISO 8601 Start, End and Elapsed** timestamps. Also include a user-facing `BUILD-REPORT.md` inside the release. Keep this assignment/report unarchived until ChatGPT accepts/consumes them; preserve any concurrent U-OBS assignment/report.
- Make small scoped audited local documentation/recipe commits only if safe: enumerate staged paths, `git diff --cached --check` and `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 .venv/bin/python -B tools/check_publication_safety.py --staged`; explicitly scope commits so prior staged changes remain untouched. **No remote push or history rewrite.** Do not hold up the playable separate distribution solely for a low-risk documentation commit if concurrent U-OBS edits make that unsafe; report the result accurately.

**Completion standard:** a player can independently open the separately saved playtest edition on the same Mac, enter either mode, play/observe genuine native combat, save and later resume the Encounter, consult an accurate offline manual, and continue to do so even as both development repositories change afterward.
