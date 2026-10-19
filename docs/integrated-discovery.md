# First integrated discovery scenario — experimental vertical slice

Run from the Universe repository root:

```shell
python examples/integrated_discovery.py
python examples/integrated_discovery.py --audit
bash run_tests.sh
```

This fixture exercises an existing `Universe` registry, `StatisticalGroup`,
`BeingInstance`, `Encounter` Action timeline, range-based awareness,
`ObserveGroupAction`, fallible `FieldObservation` and `BeliefLedger`, and
`PersonalHistory` backed by the `RealityLedger`. Its only new behavioral bridge
is `AskAboutPastAction`, which carries an inquiry through an Encounter and
returns a listener-accessible `HeardAccount`.

## Sequence and authority

1. An original adult is realized from one nomadic Group; all other members
   remain statistical. The same globally registered Being persists.
2. A dated running skill-use record is established at time 50, with rank 2.
3. At time 100, an explorer encounters the moving Group and its herder.
   The explorer's Group observation reports uncertain population evidence,
   interpreted in the existing observer-relative belief ledger. It does not
   materialize the entire Group.
4. At time 101, the explorer asks about the herder's training at time 10.
   If the episode is unresolved, the Being's existing `PersonalHistory`
   conditionally realizes and commits an admissible episode and a corresponding
   rank-1 fact. The observer hears the resulting testimony, not a privileged
   objective-history record. The original later skill-use event remains intact.
5. At time 102, a second question revisits the same historical topic. No new
   objective history is generated. A scenario-configured substituted statement
   conflicts with the first one. The two accounts are evidence of what was
   *said*, not evidence of which statement was accurate or deliberately false.
6. Time is advanced together for the traveling Group and Encounter. The
   explorer explicitly moves alongside the herder; Group affiliation does not
   imply the explorer follows Group motion.

The procedural episode's mentor, location, and circumstance are sampled from
bounded alternatives. The stable world seed, Being identity, and episode topic
key the proposal. The answer is **not** explicitly specified in the example,
although the candidate vocabulary and applicable historical skill rule are.

`--audit` exposes committed objective history in a **developer-only** view.
The default narrative does not reveal that authoritative history to the
explorer. Merely hearing words produces no belief about their truth.

## Invariants covered by integration tests

- A Group member is not replaced or multiply realized when interviewed.
- Out-of-range or uninitiated inquiries do not realize objective history.
- Existing episodes are retrieved, not resampled, on repeated interrogation.
- An incompatible proposed childhood skill rank is rejected atomically.
- The present Being and pre-existing later skill Event remain unchanged.
- Historical Group composition and the unresolved remainder remain consistent.
- Group observation belongs to the observer and retains its uncertainty.
- Heard testimony belongs to the listening Being and carries **no truth flag**.
- Encounter records the accepted Action and applies its awareness consequence.
- The personal-history commitment is exportable and restorable.

## Deliberate limitations

This is an **automated integration experiment**, not yet an interactive text
adventure, hearing/speech model, natural language understanding engine, or
Agent-driven conversational policy. The second (contradictory) statement is
chosen by the scenario, *not* produced by a model of deception or fallible
memory. There is no inference about motive, no evidence-corrobation engine,
no general belief representation for a biography, and no automatic truth
revelation. Range is a provisional communication feasibility gate, not modeled
sound propagation. Existing World persistence is not yet a complete archive
of the Encounter and all observer evidence; the historical fact ledger has
its own export/restore contract.

The next meaningful experiment is to allow the **explorer** to choose which
question to pursue and what evidence to investigate next, while leaving
objective truth hidden until justified by the applicable observation process.
