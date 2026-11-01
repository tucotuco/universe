# Combat replay and weapon experience

The first visual one-on-one simulation uses **the existing Universe, Encounter,
Being, weapon, armor and Action instances**. This is an offline, time-steppable
**replay**, not yet live command-driven combat.

Run from the repository root:

```sh
python examples/combat_visual.py --seed 17 --open
bash run_tests.sh
```

The script saves a self-contained `combat_replay.html` file in the repository
root; `--output PATH` changes the path and `--open` asks the default browser
to display it. The replay has previous/next, play/pause, a restricted view for
each Being and a developer audit view. The developer audit exposes all trace
data for debugging. This is a single local HTML file, **not a security boundary**.

## Rules exercised

- Dagger thrust takes 4 seconds; longsword swing takes 6 seconds.
- Scripted Raider movement on the first two seconds updates authoritative
  continuous positions before the attacks complete.
- Hit/miss, damage, armor wear, range and equipment checks use existing
  Encounter/Action semantics, not synthetic browser outcomes.
- A *resolved attempted* weapon strike records 10 XP for its actual weapon
  type through `ActionResolution` and the existing progressive Being skill
  system; both hits and misses count. A canceled strike records none.
- `Library` registers weapon names and categories into the ordinary skill
  dictionary, allowing validation and advancement; no separate combat XP
  bookkeeping is introduced.
- The provisional range-only perception model establishes awareness but **not
  direction, accurate distance, enemy health, equipment or intention**. Normal
  Being views therefore suppress enemy coordinates and private state.

## Deliberate limitations

The replay decisions are scripted; there is no player tactical control yet.
The frame has an explicit reach threshold in Encounter coordinate units, not
an independently calibrated weapon/body reach model. No obstacle geometry,
facing or simultaneous-action resolution is modeled in this particular duel.
The full developer audit trace is embedded in the HTML for convenient replay.
