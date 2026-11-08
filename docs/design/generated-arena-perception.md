# Generated Arena perception and visible Objects

The generated Arena has an explicit unobstructed initial-environment premise. On private candidate creation, both Beings receive independent native perception ledgers covering the other Being and all realized physical Objects. This is the scoped revision-65 initial observation, not an invocation of Spot and not a browser query over the global Universe registry.

The ledger stores observer/entity identity internally, perceptible name and type, current position/state, boundary/time, and the adopted evidence basis. Browser state is projected only from the player's ledger. It maps internal subject IDs to random opaque per-session handles; it returns no native IDs, source records, hidden Being attributes, private choices, or RNG state.

At each committed Encounter interval, the native atomic publication stages ledger updates using the detached shared post-movement snapshot. Pickup custody effects are reflected in that same publication: a carried Object remains in observation history and the visible entity list, while its ground marker and position disappear. Failed intervals leave observer state unchanged.

Pick up remains a separate native Action governed by revision 64. The server resolves a submitted opaque handle through the player's current evidence, rechecks the native Object and current coordinates, then schedules the native `PickUpAction` through the Encounter ChoiceBook. Same-hex accessibility is not a perception or discovery restriction. Weapon readiness is not inferred.

If the Arena later models obstructions or unknown spatial geometry, this initial open-world rule cannot be used to claim a clear path. That environment needs a separately adopted perception contract before the passive projection can expand.

For an explicit local demonstration with ordinary test equipment and terminal tracing, run from the repository root:

```sh
PYTHONPATH=../npc-generator .venv/bin/python examples/generated_arena_browser.py --ground-loadout-profile tests/fixtures/arena/test_ground_loadout_profile.json --trace-ui
```

Without `--ground-loadout-profile`, the generated Arena still opens with no ground equipment. Its normal Generate form continues to request only starting XP and map dimensions. `ARENA_TRACE_UI=1` remains an equivalent tracing opt-in.
