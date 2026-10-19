# Attack-specific defense and interactive control surface

Base: `578284e` (`Add impact-time reach checks and timed parry dodge reactions`) as described by the user. This increment leaves `src/library.py`, previously generated combat replay HTML, untracked examples, and `workspace/` unmodified.

- Arrow keys command north/south/east/west on the active combat view only. Keyboard movement is suppressed inside editable inputs and dialogs, while saving, during replay, or after the Encounter ends. Diagonal buttons remain available.
- Move, attack and defense controls, the effort allocation panel, and the save/replay controls are on the right. Clicking either map Being opens a details dialog. The Scout's own HP, fatigue, weapon and skill history are available; Raider details remain observer-filtered. Audit explicitly reveals objective data.
- Reactions select the currently *perceived* pending Raider strike in this bounded one-on-one encounter. The selected action ID is stored in the actual `MeleeDefense`; the UI does **not** expose the hidden strike ID. An untargeted or too-late reaction is rejected before replacing an unfinished attack. Move does not interrupt ongoing attack/Guard or reaction preparation.
- Parry preparation uses faster available weapon attack timing minus one second; Dodge preparation takes two seconds. A defense ready earlier is maintained until the chosen strike impacts. Dodge displacement happens at impact. Defense applies to its designated strike only, not any later strike, while incidental geometric displacement can affect other attacks.
- Versioned deterministic command replay supports the new rules. This is still a provisional single-attacker simulation without physical facing, multiple-attack allocation, validated gesture recognition, or true simultaneous effect application.

Run `bash run_tests.sh`, then `python examples/live_combat.py --open` (or `--audit --open`). Inspect target availability by clicking the Raider circle; the tactical panel enables Parry/Dodge only while a current apparent strike is available. Late defenses report an error without advancing time.
