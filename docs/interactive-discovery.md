# Interactive discovery loop — experimental vertical slice

The first player-directed exploration scenario extends the existing integrated
caravan demonstration. It uses the same `Universe`, `StatisticalGroup`,
`BeingInstance`, `Encounter`, `ObserveGroupAction`, `AskAboutPastAction`,
`BeliefLedger`, and `PersonalHistory`/`RealityLedger`. The new controller is in
`examples/interactive_discovery.py`; no separate world model is created.

## Use

From the repository root:

```sh
python examples/interactive_discovery.py
python examples/interactive_discovery.py --seed 392
python examples/interactive_discovery.py --commands 'look;observe humans;ask childhood;ask later;ask childhood;notes;compare;quit'
python examples/interactive_discovery.py --commands 'ask childhood;quit' --audit
bash run_tests.sh
```

At the `Explorer>` prompt, use:

- `look`: a range-proxy environmental check, without committing personal history.
- `observe humans`, `observe livestock`, `observe dogs`: a one-second Encounter
  Action that can fail, or can produce skill-dependent uncertain count evidence.
- `ask childhood` or `ask later`: a one-second Encounter Action requesting an
  episode at world time 10 or 20. Only that historical topic is realized if
  previously unresolved and the exchange is in range. A second inquiry about
  the same topic uses a scenario-scripted conflicting claim but does not
  regenerate the committed episode.
- `notes`: reread collected FieldObservations and HeardAccounts without
  realization or advancing time.
- `compare`: compare the listener's testimony for internal discrepancies and
  any incompatible reported count intervals. This comparison does **not**
  identify which testimony was true or whether anyone intended deception.
- `follow on` or `follow off`: choose whether future action steps and waits
  move the explorer alongside the caravan. Turning it off allows meaningful
  separation; membership itself does not carry the explorer.
- `wait` or `wait N` (1–20): advance Encounter and Group clocks together,
  without requesting history realization.
- `quit`: stop the session, leaving unresolved topics unresolved.

`--commands` runs a choice sequence without waiting for input, useful for
replay or automated checks. It does not commit a saved world across processes.
`--audit` displays a **separately labeled out-of-world developer view** after
commands; `audit` is not an explorer command. The terminal controller holds a
reference to the developer world, but it does not disclose the objective
biography in ordinary responses. This is an application-level separation,
**not** a security boundary against someone inspecting Python internals.

## Reality and discovery invariants

1. Asking about a new topic can trigger an atomic objective-life commitment;
   inspecting the evidence notebook or comparing accounts cannot.
2. An already resolved episode is retrieved, never resampled. Order of inquiry
   may affect which still-unresolved facts get committed, but no committed fact
   is overwritten.
3. PersonalHistory's explicitly non-declining running-skill model rejects an
   earlier skill rank incompatible with the established later skill-use Event.
4. A successful inquiry records `HeardAccount` as the *listener's evidence of
   words spoken*, not evidence that those words were true. A failed range gate
   commits neither episode nor testimony.
5. Group count observations are noisy and can fail. Notebook reports and
   derived count comparisons use the listener's `BeliefLedger`, not
   authoritative original Group composition.
6. The same persistent Being and Group are used across all turns. Historical
   realization does not mutate present skill rank or erase later Events.
7. Group and Encounter clocks advance together. The explorer follows the
   moving Group only as a deliberate scene-level movement command.

## Limitations

This is a **small interactive experiment** rather than an open-ended
conversation, hearing/vision/physics model, NPC cognition system, or playable
world with save/resume. There are two predefined questions about the same
running skill, with seeded bounded narrative alternatives. The second account
is an explicit scenario fixture, not an emergent lie, deception judgment,
changed recollection, or policy for future NPCs. The observer does not
investigate the actual historical event directly and cannot yet establish the
truth of the competing accounts by independent corroboration.

The group sensor is a range scaffold using its original committed counts;
its samples do not realize individual members. The player's decisions can
alter what becomes established and what remains unresolved, but this example
does not implement cross-domain inference, save/restoration of the entire
Encounter, or social belief propagation.
