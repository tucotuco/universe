# Compact combat exploration interface

Builds on the attack-specific defense UI increment. **This is an interface-only change:** the Encounter, Being, attack timing, effort allocation, skills, experience, defense targeting, perception filtering, and save format are unchanged.

- The left column contains the map followed **immediately** by a compact, newest-first Encounter history. The latest event remains at the top of the history, and the map height is bounded relative to the viewport so the newest event is easier to see without page scrolling. The history itself scrolls independently.
- The narrower right column contains only categorized command buttons (offense, defense, eight directions, wait/cancel/effort, and saved-Encounter controls). `Effort n/N` opens a modal containing the existing skill-effort inputs. Historical replay scrubbing is next to the Encounter history instead of in the command column.
- Hovering a Being marker gives a short, three-line SVG tooltip: **HP remaining/maximum**, **active or apparent actions** (including simultaneous movement when available), and **expected resolution times**. An unscheduled sustained Guard has no impact time. Clicking the marker still opens the more detailed Being dialog.
- The Scout's own HP and pending-action deadline are known precisely. The Raider's precise HP and unobserved action deadlines stay **unknown in the ordinary explorer view**; the observer currently has no measurement to establish them. Developer `--audit` includes objective fields. We do not convert uncertainty into fabricated numeric state for appearance's sake.
- Arrow keys continue to command cardinal movement, except when a text/number input is active, a detail/effort modal is open, or a replay is active.

Run `bash run_tests.sh` then `python examples/live_combat.py --open`. Inspect both hover states, click-to-inspect dialogs, the effort modal, and the recent log at different browser sizes. Automated graphical rendering may not be available in the development environment; confirm visually in your local browser.
