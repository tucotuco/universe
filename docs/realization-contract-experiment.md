## First shared realization contract experiment (2026-10)

- **Goal:** let the builder also discover the world. A query may request
  previously unresolved objective detail; the world generator proposes it,
  and a domain model validates it before that detail is committed. No complete
  hidden fine-grained world is generated in advance.
- `RealityLedger` (experimental) distinguishes non-realizing `inspect()` from
  potentially realizing `ask()`. Facts carry an optional *in-world* time,
  provenance, and a distinct commitment revision. Repeated interrogation reuses
  committed facts. Batch proposals are all-or-nothing; impossible proposals
  are rejected without rewriting established reality. Explicit JSON export and
  validation on restoration preserve this prototype's discoveries.
- **Observation interrogates reality; perception and belief are separate.**
  This mechanism returns objective facts to a *simulation* caller, never
  automatically to a Being. Testimony, deception, and mistaken perception do
  not become world facts merely because someone said or perceived them.
- Three deliberately narrow constraint probes share the contract: a Group
  composition quota, a historical training detail compatible with an established
  lifespan, and an intermediate 3D position checked against established past
  and future positions under an optional maximum-speed model. Physical speed
  bounds are necessary checks, not general trajectory/dynamics reconstruction.
  Temporal constraints apply only when the corresponding domain rules exist.
- These are **fixtures testing a common contract**, not live adapters to
  `StatisticalGroup`, `BeingInstance`, or Encounter state. Existing Group/Being
  registries remain authoritative for their respective live state. **Do not
  create a second mutable source of truth** when integrating the contract;
  choose a single authoritative state provider or a derived projection.
- Sampling rules remain domain specific. A fixed seed is helpful for test
  replay, but the important invariant is that *committed* history survives
  reload and is not changed by later requests. Different orders of entirely
  uncommitted inquiries may legitimately produce different admissible worlds.
- Next: integrate the contract into one existing system with a single source of
  truth, and develop time-addressable historical reconstruction/refinement
  before generalizing constraint propagation or world-scale simulation.
