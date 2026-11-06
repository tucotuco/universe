# Historical Being realization experiment (2026-10)

## Boundary of this increment

`BeingInstance.begin_personal_history(earliest=..., known_through=...,
nondeclining_skills=...)` attaches an **opt-in** `PersonalHistory` to an
existing Being. The Being's live skills and its `skill_use_history` remain the
authoritative source for established skill-use Events; the ledger does **not**
duplicate those events or attempt to infer historical mutable state.

Historical detail is committed to `PersonalHistory.reality` using the shared
`RealityLedger` contract. `inspect_episode(time, topic)` and `facts_at(time)`
**never generate**. `realize_episode(time, topic, propose)` can commit a
previously unresolved episode and related facts atomically. Repeating an
inquiry retrieves the existing episode without resampling it.

The experiment permits two historical fact types:

- `episode`: a short objective narrative detail, optionally with structured
  `skill` and `rank_after` evidence.
- `skill_rank`: a dated nonnegative rank, only for skills explicitly configured
  as *nondeclining* in the experiment. A training episode must commit its
  matching dated rank in the same realization transaction.

An earlier skill rank cannot exceed a known later skill-use event's
`level_before` or fall below an earlier known event's `level_after`, under the
**explicit non-decline assumption**. Previously committed historical ranks
cannot decrease through time. Historical proposals are checked against live
skill-use history; a new skill-use record is checked against committed personal
history **before** updating the Being's skills or recording experience.

Only applicable constraints are enforced. There is **no general claim** that
skills cannot decline, that history is fully inferred from present capabilities,
or that real-world training progress follows the experimental rank model.
Skills not explicitly listed as nondeclining are not modeled by these rules.

`PersonalHistory.to_jsonable()`/`from_jsonable(being, data)` serialize and
revalidate committed detail against the existing Being and known skill uses;
`BeingInstance.to_json()` includes the optional history if enabled. This is
**not** a full Universe save/restore implementation. `BeingInstance.reset()` rejects attempts to discard committed
personal history; an empty optional history may be reset.

## Architectural implications

- A retrospectively realized Episode is **objective reality**, not a memory,
  report, Perception, or Belief. A later conversation could reveal the event,
  misrepresent it, or establish conflicting testimony, but those mechanisms
  are not built by this patch.
- Inquiry order need not determine the outcome once a fact is committed;
  prospective incompatible stories are rejected without modifying prior facts.
- Group membership, historical population counts, current Being state, and
  dated skill-use evidence remain in their respective authoritative stores.
  Personal history does not mirror or rewrite those stores.
- The model is **intentionally incomplete**: no general personal chronology,
  causal back-story generator, aging, health/injury timeline, skill decay,
  temporal spatial paths, historical Encounter replay, or automatically
  synchronized Universe lifecycle. An episode description is narrative text;
  only its explicit structured claims are validated.

Run `python examples/historical_being_realization.py` from the repository root
and `bash run_tests.sh` for the full regression suite.
