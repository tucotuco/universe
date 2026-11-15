# U-PLAYTEST-001 — Frozen Arena playtest release

## Result

**Release delivered; report awaiting ChatGPT review.** The frozen U-CAP-008A Arena runs outside both development checkouts, generates with bundled `npcgen`, serves on loopback, and supports Player vs Arena and Arena vs Arena. Chrome demonstrated native gameplay and Save/Load; a save from the final extracted archive restored in a fresh OS process and continued. No Universe combat implementation or perception code was changed.

- Start: **2026-11-14T19:20:19-08:00** (captured when this execution began)
- End: **to be set at final closeout**
- Elapsed: **to be calculated at final closeout**

## Frozen sources and repository state

- Universe source snapshot: `ef71e42514094d2372b976be5d64acf3ea077fa9`, the accepted U-CAP-008A Arena controller implementation. It precedes later in-progress repository work and includes Arena mode, scheduling and schema-7 persistence.
- Controlling Encounter rules: revision 70. Generated Arena save schema 7; explicit migrations for schemas 4, 5 and 6.
- Bundled NPC Generator: `e8db44091b820f3e4c3cd602dbabfcc7659e0ef5`, `npcgen` 2.1.0, including required package data. That separate repo was inspected read-only and left untouched; at inspection its user worktree contained an existing deletion and untracked files, preserved as found.
- Runtime tested: macOS 26.1, arm64, CPython 3.14.3. The Arena has no third-party Python runtime dependencies. The offline installer requires a host CPython 3.14 or newer and builds its own relocatable-local venv after extraction; the ZIP does not contain a portable venv.
- Development repository started at `72e9d84e814692f45a696694ada27155085e6e88`, `main`. No Arena source, tests, `.venv`, ignored `legacy/`, local saved worlds, independent NPC Generator, backups, or user save were edited. The untracked `docs/assignments/universe-arena.json` remains untouched.

## Delivered release

- Installed folder: `~/Projects/universe-arena-playtest/U-CAP-008A-2026-11-14/`
- Backup ZIP: `~/Projects/universe-arena-playtest/Universe-Arena-Playtest-U-CAP-008A-2026-11-14.zip`
- ZIP SHA-256: `3df28bd7354a55ec7a97425ed19a708265e86bec8eb6db85a92b36f27ce4668f`
- Manifest build time: `2026-11-14T21:09:50-08:00`; 383 static packaged files are listed in `SHA256SUMS.txt` (runtime venv and mutable saves excluded). The archive contains 384 files including the manifest itself and no `.git`, development environment, caches, or user save.
- `Install or Repair.command` and `Play Arena.command` are executable. Extract, double-click the installer once, then double-click the launcher. The launcher prints the version, source paths and loopback URL, opens the default browser with `/usr/bin/open`, and can be stopped with Ctrl-C in its Terminal window. If Gatekeeper objects to this local `.command`, use Finder’s Open action for this file only; do not turn off system-wide protection.
- Runtime/source/vendor/config are inside the release; saves are stored separately under `userdata/saves/` when the user moves the browser-downloaded JSON there. Repair reconstructs runtime without overwriting saves. The release requires no network after Python is installed.

## Acceptance verification

| Criterion | Result | Evidence |
|---|---|---|
| Frozen source and compatible `npcgen` | Met | Exact accepted Universe/npcgen revisions above; package is a clean revision export with required config/data. Imports and launch output identify only release-local Arena, `npcgen`, and config paths. |
| Separate macOS installation and double-click launcher | Met | Both `.command` files have executable mode. Installer and launcher passed from extracted whitespace paths in a clean environment. Final launcher opened default browser and served `127.0.0.1:50480`; no dev `PYTHONPATH` or user-site was present. |
| Player vs Arena browser outcome | Met | Release Chrome, seed 14, XP 10,000, 10×5, equipped, no ground Objects, `attack_only` opponent. Walk+turn toward (8,1), then Dagger Thrust. At t=5 the native receipt was completed/hit/normal with damage committed, distance 1.3532922818075925 m; opponent independently resolved Thrust normally. |
| Arena vs Arena browser outcome and privacy | Met | Release Chrome, seed 14, XP 1,000, 5×5, equipped, no ground Objects, A `attack_only`, B `defense_only`. B Dodge ready at t=2; A Thrust hit for 2 native damage at t=6; B Dodge failed at t=6; A Thrust hit for 4 at t=10; B Dodge failed at t=10. Spectator chronology is labeled separate from Being observations and the mode has no manual tactical controls. |
| Save/Load and fresh-process continuation | Met | Chrome Save and Load were exercised on the installed release; Load restored t=10, both strategies and chronology. A-V-A schema-7 save hash `fe6a7f7a0a6fca4a5699c205f140d8f44f89c1a3e04ca5d3b89285e018fe3973` restored in a new OS process without regeneration, including native IDs, time, mode, strategies, hit receipt/damage and RNG-backed continuation; process advanced to t=11. P-v-A save hash `5032c39b243dd540b51ed49e6c4e25b9787fd8db2347566d7cbe6e989756445e` restored at t=5 and advanced to t=6. The extracted-copy browser Save produced `zip-extracted-ava-save.json` in the temporary test area, SHA-256 `3d7e97e068ee529b499904da2cdb53155f9ee65ca7eed450e534c2474f55a337`; extracted runtime restored that exact file at t=10 and advanced to t=11. |
| Independent archive extraction and startup | Met | Final archive extracted to `a fresh extraction path containing spaces` (space in path). Offline install verified all 383 checksums and rebuilt CPython 3.14.3 runtime. Clean-environment launch reported only extracted paths, opened the browser, and served a 200 page containing the Arena UI. ZIP has no runtime venv, `.git`, bytecode or saved encounter. |
| Offline manual and maintained links | Met with a visual-check limitation | Both Markdown and self-contained HTML manuals are packaged. Python’s standard HTML parser found 8 in-page anchors, 11 references, zero broken local/anchor links and zero remote resources; all three relative companion files exist. Chrome’s computer-use URL policy blocked `file://` navigation, so a visual offline rendering was not claimed. The HTML itself is static and all resources are embedded/local. |
| Scope, privacy and preservation | Met | No perception work or new combat mechanics. Existing starter ground Objects can yield `uncertain_path`; the tested walkthrough explicitly uses No ground Objects, without changing geometry or resolver rules. Five pre-existing staged historical archive entries and `universe-arena.json` remain untouched. No push. |

### Reproducible commands and focused checks

- Chrome P-v-A and A-v-A walkthroughs were performed against the separate release served from loopback, not the development checkout. The generated native results and exact control texts are recorded above and in the release `BUILD-REPORT.md`.
- Fresh-process restore of the final archive’s extracted browser save:

  ```sh
  PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 \
    '<extracted release>/runtime/venv/bin/python' -B '<temporary restore script>'
  ```

  Result: schema-7 A-v-A, t=10, A `attack_only`, B `defense_only`, same native entity handles and completed hit/damage receipt; continued to t=11. The later final package rebuild only changed the packaged launcher/report/manifest/checksums, and was independently extracted and started again from `Final2`.
- Offline install command from a clean environment: `env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME=<home-directory> /bin/bash -c 'cd "<extracted release>" && ./Install\ or\ Repair.command'`; result: checksum verification passed, isolated runtime CPython 3.14.3 ready.
- Final static file audit: `shasum -a 256 -c SHA256SUMS.txt` — **383/383 OK**. ZIP SHA-256 is the value above. `unzip -l` confirms no `.git`, local user save or packaged runtime; final ZIP size 1,229,065 bytes.
- Served-page smoke: `curl --fail --silent --show-error http://127.0.0.1:50427/` returned 87,110 bytes and contained the Arena page and Generate Encounter control. Final extracted launch bound to `127.0.0.1:50480` and opened the default browser.
- The U-CAP-008A focused Arena/browser and persistence suites and source compilation results are retained in its archived report; no full Universe suite was run for this packaging assignment.

## Task state, docs and Git audit

- `TASKS.md` before → after: U-CAP-008A ACTIVE → accepted DONE (bounded), with links moved to archive; U-OBS-001 DEFERRED → sole ACTIVE; U-PLAYTEST-001 added as a completed packaging milestone whose report awaits ChatGPT review. U-CAP-009 remains unchanged. `docs/ideas/inbox/` is absent; the existing processed idea file was left unchanged.
- U-CAP-008A assignment/report were moved with `git mv` to `docs/assignments/archive/` and `docs/reports/archive/`; maintained TASKS/handoff links now use archive locations. U-PLAYTEST-001 assignment and this report remain active/unarchived until review.
- Starting HEAD was `72e9d84e814692f45a696694ada27155085e6e88`. Initial unrelated index entries preserved, not committed: deletions of `docs/assignments/U-CAP-002.md`, `docs/assignments/U-CAP-003.md`, `docs/reports/U-CAP-002-report.md`, `docs/reports/U-CAP-003-report.md`, and the U-THROW-001 patch archive rename. The untracked `docs/assignments/universe-arena.json` remains unchanged and unstaged.
- Intended local documentation commits, scoped to this assignment/report, TASKS, maintained handoff and the U-CAP-008A archive moves: to be recorded after the staged safety audit. No push or history rewrite.
- Required commands before commit: `git diff --cached --check`; `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 .venv/bin/python -B tools/check_publication_safety.py --staged`; maintained Markdown-link check. Final changed paths and commit hashes to be added after commit.

## Remaining limitations

Shoot, Deflect, broader Throw, unsupported physical geometry/route clearance, and perception expansion remain outside/bounded in this frozen release. The starter ground Objects can make some movement/attack routes uncertain. The host must provide macOS CPython 3.14 or newer; it is not bundled. No separate npcgen LICENSE file was found, so the user manual does not assert a broader redistribution grant. Chrome `file://` visual-opening verification is limited by the computer-use browser policy; ordinary direct user opening is not claimed as tool-verified.
