# Historical composition queries and realization (experimental)

- A Group's original household count and individual household composition are
  now committed **once** in its `RealityLedger`. They are not independently
  stored in an additional mutable Group cache. Group totals are derived.
- `state_at(t)` returns what is **already committed** at a valid Group time,
  including a partial original composition (known minima) and dated membership
  changes. It does not generate missing households or pretend to know their totals.
- `refine_formation_at(t, household=None)` commits an original composition fact
  using the Group's configured CDFs. It can be requested at a later simulation
  time for an earlier formation state and never replaces a prior commitment.
- Membership history remains Group-owned and is replayed for current composition
  at historical `t`; it is not copied into the realization ledger. A Group's
  formation population is immutable, while its historical membership changes.
- This first adapter is **limited to formation composition and dated Group
  membership**. It does not reconstruct historical Entity health, skill state,
  positions, individual lives, or evolving household membership. Persisting an
  entire Group and its Ledger together also remains future work.
- Queries for uncommitted detail never reveal it to an Agent automatically.
  Observation, Perception, and Belief retain separate semantics.
- The ledger is a private Group implementation detail; Group methods are the
  supported composition API. Future domains should use the same validation
  and commitment contract without assuming Group-specific distributions.
