# Resolution on demand, Groups, Attention and relationships

Back to [TASKS.md](../../TASKS.md).

## Completed bounded demonstrations

- `StatisticalGroup(ObjectInstance)` is a population-specific prototype, not a general Group ontology. Trusted world code can select one already-counted adult and atomically publish its realization while conserving Group totals.
- A supported successful Spot can record exact aggregate Group count evidence for one observer; it does not expose unresolved slot identifiers, individual identity or position.
- The 5E2S adapter accepts only one eligible unfamiliar participating Being; zero or several candidates are refused. It is an experiment, not general Agent Attention or category-directed Spot.
- The 5E2U example connects Group count 28, independent trusted-world selection, next-boundary eligibility, later discovery and Awareness, then a native Thrust. No Group observation automatically triggers realization.
- Optional geometry supports a later ordinary Spot without changing Spot duration/DC/no-XP rules. Realization does not grant Awareness.

## ACTIVE: U-REL-001

The D1 audit and D2/D3 design contracts are complete. D2 records the confirmed exact unordered reproductive-parent-set semantics and gender-independent identities/roles. D3 adds the confirmed existence boundary: an instantiated reproductive group is nonempty, world-created only when resolution is demanded, and distinct from a potential/zero/unknown parent-set scope. `ReproductionGroup` is the preferred working name, not an adopted type or storage model. D3 distinguishes complete parentage from offspring enumeration and explains why parent-global completeness must cover uninstantiated parent sets. D4A/B subsequently implemented the bounded authored-candidate and no-Encounter publication gates summarized below. Review [`family-generation-u-rel-001-d3-completeness.md`](../design/family-generation-u-rel-001-d3-completeness.md), alongside the [D2 contract](../design/family-generation-u-rel-001-d2-contract.md) and [D1 source audit](../design/family-generation-u-rel-001-audit.md) for the adopted design constraints.

The current Being model has no age/date-of-birth or relationship graph. Reproduction offspring remain logical IDs rather than native Being instances. `StatisticalGroup` has stable latent slot IDs and aggregate counts; its Encounter member-realization transaction is separate from this no-Encounter reproductive registry. D1's edge-only B is a later integration fixture only: one edge does not instantiate a nonempty reproductive group or prove its full parent set. D3's pure authored-candidate and world-publication gates are implemented in D4A/B. Global offspring closure is unresolved without proof that the relevant parent-set domain, including uninstantiated sets, is closed. World generation changes no observer knowledge.

D4A's candidate-only implementation adds `ReproductionGroupProposal` and its prepared candidate as immutable logical-ID records; the pure preparer canonicalizes exact parent sets and refuses empty/duplicate identities. The candidate cannot claim complete offspring enumeration. It performs no registration, reservation, Reality publication, RNG use, date handling, observation, Being construction or population coupling. This is a partial engineering milestone, not a world-level family generator.

D4B adds a `Universe`-owned, in-memory registry and typed publisher for authored nonempty candidates and their offspring parentage facts. It checks per-world exact-parent-set and group-ID uniqueness, Person-ID assignments, request idempotency and registry revision; failure injection verifies rollback. It is explicitly no-Encounter and nonpersistent.

V1 adds a runnable no-Encounter seeded resolution example using an explicitly supplied `TestOnlyOffspringCountDistribution`. It samples a nonnegative count, including zero, and distinct ordered abstract origin ticks within an inclusive caller-bounded horizon. Positive outcomes publish a unique group, stable logical offspring IDs, parentage and tick facts together. Zero outcomes publish only a record scoped to that parent-set request and horizon; no group or Person IDs are created. Distribution schema and sampling algorithm versions are recorded. Preparation uses a private seeded RNG, and publication is revision-checked, idempotent and fault-injection rollback-tested.

V2 adds [`progressive_statistical_reproduction.py`](../../examples/progressive_statistical_reproduction.py): an explicitly test-only, versioned per-interval count profile over abstract integer period indices. It resolves periods 0 through T1, then atomically appends only T1+1 through T2; hash-derived period streams and IDs make that path match a fresh direct T2 resolution. Existing prefix facts are checked and retained. A zero-only prefix creates no empty ReproductionGroup; a later positive period creates the one group for that exact parent set. Overlapping horizons, profile/seed changes and conflicts with authored/V1 scopes refuse explicitly. Tests cover initial and extension rollback, idempotency, stable identities, singleton parents and the absence of Encounter, Being, population, observer, Belief or global-RNG side effects. Neither V1 weights nor V2 interval weights or integer ticks are adopted biological/calendar rules. Neither implementation infers global offspring completeness, creates Beings, alters population, or changes Awareness/Observation/Belief. Durable cross-process identity and biological meaning remain unsupported.

### Open archival prerequisite: U-ARC-001

Historical sources remain untrusted and are not runtime dependencies. Before adopting their distributions or formats, decode only selected formats safely and establish provenance and rights. The 5E3H archive index and static U-ARC-001 assessment locate material but do not resolve those questions. Do not execute archived code or bulk-import its data.

## Planned and deferred

- **U-GRP-005:** generalize Group membership/data beyond the population example; any `ObjectGroup` name or heterogeneous membership needs a separate decision. Events stay outside Object ontology.
- **U-GRP-006:** Agent interest or aggregate Group evidence cannot yet select an unresolved hidden member. Specify trusted-world authority, deterministic selection and information boundaries.
- **U-ATT-001:** ongoing mutable Attention may eventually concern categories, known Beings/Objects/Groups, or Events such as moonrise; it does not guarantee discovery and differs from a focused Spot Action.
- **U-SPOT-002:** category-directed Spot, multiple matches and Search semantics remain unapproved.
- **U-LOC-002:** Action-acquired observer-owned Object location/waypoint evidence is not yet a supported publisher effect.
- Broader uncertainty, multiple-Group membership, population lifecycle, non-adult realization and autonomous Agent policies remain future work.

## Planning and source context

[`deferred-ideas.md`](../deferred-ideas.md) is an earlier consolidated Universe backlog (reviewed 2026-10-19). It remains useful for broad direction, but later adopted rules, user decisions and current source/tests supersede stale status claims. Historical evidence and original reports are located through the [archive index](../historical-evidence-archive-index.md). Interrupted experiments remain under the [tracked work-stash](../../work-stash/README.md), with topic status files describing their limits.
