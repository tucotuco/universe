# U-REL-001D3 — On-demand ReproductionGroups and completeness

**HISTORICAL DESIGN RECORD.** Parent-set and existence semantics in §1 were user-confirmed. D4A/B and V1–V11 have since implemented bounded world-only slices. The V10R partial-membership correction below supersedes D3 statements that required a fully resolved parent set before a ReproductionGroup could exist. V11 adds versioned checkpoint support for that correction; broader biology, chronology, completeness, legacy-profile, and persistence proposals in this document remain unadopted unless separately approved.

## V10R correction — structural parent membership may be partial

`ReproductionGroup` is the sole structural authority for objective reproductive parentage. A nonempty group may contain at least one established offspring and one or more known reproductive-parent members while `parents_complete=false`. Such membership is positive known Reality, but it does not claim that all parents are known. Additive member resolution preserves the group and offspring identities; marking a group complete explicitly closes its parent set. One-parent complete groups remain valid. Parent-set completeness does not imply complete offspring enumeration.

Only completed exact parent sets are unique and indexed by their full canonical unordered set. Incomplete groups are not merged or keyed by their current member subset; overlapping known members are insufficient to infer the same group. If completion collides with an already completed set, publication refuses atomically; no merge policy is introduced. Parent lookup tables are derived indexes of ReproductionGroup membership, not a second authoritative parentage ledger.

At V10R, V4 reproduction and V6 combined checkpoints preserved complete-group state only and could not represent partial membership or elaboration history. V11 introduces reproduction-checkpoint V2 and combined-checkpoint V2 to represent both. V1 reproduction and combined checkpoints remain readable with their original complete-parent-set meaning; a V1 checkpoint cannot encode partial membership or membership-elaboration history. Digests detect corruption but do not authenticate checkpoint provenance.

Accordingly, the following D3 language is superseded: §3's requirement to instantiate only after the exact set is resolved; §4's “Do not instantiate while the parent set is unresolved”; §7's candidate requirement for an exact parent-set index on every initial group; and acceptance/example statements that assume every initially published group's parent set is complete. The true constraints retained are: each group is nonempty, all of its offspring share the same actual complete reproductive-parent set, known members are objective facts, and exact-set uniqueness applies when completeness is established.

## 1. Confirmed semantics and boundaries

- An instantiated **ReproductionGroup is a nonempty reproductive unit**: it has at least one offspring. It is not a social/cultural family, household, partnership, marriage, or population cohort. A potential parent set, unknown status, or zero-offspring outcome is not a group.
- Resolution is world-level and on demand. A group is not eagerly created for every possible parent set. An author, simulator, genealogy query, or observation-triggered request may demand resolution; Observation is optional and is not a prerequisite. Resolution changes objective state only and grants no Agent Awareness, evidence, testimony, or Belief.
- A group is keyed by one exact unordered set of stable reproductive-parent identities and includes all offspring with exactly that set. One-parent `{P}` is a complete parent set for asexual reproduction; it does not mean one child. Gender and event-specific reproductive roles are independent of identity. Same-set offspring are full siblings; kinship across overlapping sets is derived. One Being may be offspring in one group and parent in others.
- ReproductionGroup is distinct from `StatisticalGroup`, `BeingInstance`, household, and social/adoptive relations. It creates or counts no Being or Encounter participant implicitly. Same-gender, one-gender, multi-parent, and role-switching/hermaphroditic systems remain possible under future species rules.

## 2. Checkout and evidence

- Start branch: `main`; HEAD `7b9d986d8b2b06cee84a3da80ee2d7cfee3dae53`, parent `3df9783cf25ca8c71ea1317e0a4a919810fdf97f`. `origin/main` is `a22c284909d7f64c14cad919518f9da319bcf1ed`; local `main` is three commits ahead. D1, D2, and the task updates are tracked and committed at the start HEAD. Before this increment, the index and tracked working tree were clean.
- At start, 1,168 paths were untracked: 19 outside `legacy/`, 1,149 under `legacy/`. `git ls-files -- legacy` is empty. Assignment archive SHA-256: `9bcc0373917a315d2677dc8595412774790f38bb7322d0c101f22b0131c32f84`; extracted under `/tmp/universe-u-rel-001d3/`.
- Source boundaries: `src/realization.py` calls `RealityLedger` an experiment, not a replacement for authoritative Universe state. `src/statistical_group.py` models counted population, physical footprint and adult-Human realization; its direct realization mutates Universe and Group state. `src/group_member_realization.py` and `src/atomic_publication.py` demonstrate detached candidates and an Encounter-owned publisher for a narrow adult-realization operation, not a no-Encounter family transaction. `src/field_observation.py` and `Encounter.aware_beings()` keep knowledge observer-scoped. None defines reproductive relationships, empty-family semantics, or parent-global closure.
- `legacy/FAMTREE/FAMTREE.C` was read only as untrusted historical text. It was not executed or staged. The D1 audit cites `legacy/src/history.py`, absent from this checkout; no substitute was invented.

## 3. Terminology and lifecycle

Keep three states distinct:

1. **Potential/constraint scope:** a world-level, non-group statement about an exact or unresolved candidate parent set and a time horizon. Status may be `possible`, `unknown`, or an explicitly justified `zero offspring through T`. It is not a group under another name.
2. **Resolution request/outcome:** an authorized world request to author or sample a bounded reproductive result. A zero-child sample returns `no group`; it may add a zero-through-T constraint only if the request and evidence justify that exact closure. Unknown is not zero.
3. **ReproductionGroup:** instantiate atomically only with a resolved exact parent identity set and at least one offspring fact carrying a stable reserved Person ID. An offspring may have unknown name, attributes, event details, Being materialization, population membership, or Observation. An anonymous existence claim without a stable logical Person identity is insufficient to attach a child. A complete parent set does not imply a complete offspring enumeration.

After instantiation, the group's offspring enumeration may be partial. Later compatible offspring may extend it. A scoped complete-through-T claim closes only the declared scope through inclusive T. No empty placeholder or zero-offspring group state is allowed.

## 4. Existence and identity invariant

Once parent identities resolve, canonicalize the full unordered set for comparison and enforce one ReproductionGroup identity for that exact set across time. Recommended engineering choice: a distinct stable `ReproductionGroupId` plus a unique full-set index, so the ID need not change with event order; a hash may index but never replace full-set equality. Concrete ID derivation and namespaces remain unapproved.

Do not instantiate while the parent set is unresolved. Keep prospective constraints separate. If two prospective records later resolve to one exact set, atomically deduplicate compatible constraints and offspring references into the unique group identity or refuse the conflict. Preserve provenance and all prior zero/closure facts; never silently overwrite or create a duplicate. The merge/versioning policy remains open.

The exact set is independent of event-role ordering. Singleton `{P}` is valid for asexual reproduction. If P fills two roles in one event, P remains one parent identity. Full siblings share the complete set; overlap across distinct sets supports derived half-/partial-sibling relations. Labels for overlap among sets larger than two require species/schema policy.

## 5. Local completeness

Represent at least these dimensions separately: exact parent-set completeness, offspring enumeration, event/time completeness, attributes, and Being instantiation. Completeness of one says nothing about another.

- For an instantiated group, “exactly N offspring through inclusive T” with N >= 1 requires a proof that every in-scope offspring is represented, has the exact parent set, and has an event time comparable with T. Unknown origin time blocks horizon completeness unless an approved rule resolves it.
- **Zero offspring through T** belongs to a parent-set/time constraint outside ReproductionGroup, even if a group with that set is later instantiated by a child after T. Preserve zero-through-T when adding a T+1 child; an earlier/equal-T child contradicts it absent explicit, versioned correction/supersession.
- Unknown is not zero. Deceased, migrated, nonresident, or non-instantiated children remain in historical scope when their origin time qualifies; death, migration, residence, attributes, and Being materialization are separate facts.
- A closure claim names exact parent set, schema/role semantics, inclusive horizon, identity/parentage and chronology coverage, provenance, and source revision. It does not imply all Being attributes are known.

## 6. Parent-global completeness

`AllOffspring(P, through=T)` cannot be proven by listing instantiated groups containing P. Its domain must account for `{P,Q}`, `{P,R}`, `{P}`, every other species-valid exact set containing P, and sets not yet instantiated. Each scoped set must be represented either by a compatible nonempty group with offspring closed through T or by a justified zero-through-T constraint. The world must additionally establish that the candidate parent-set domain itself is closed for P and the selected role/species/time scope through T.

An authored or committed generative decision could close that domain by defining eligible identities and parent-set possibilities and recording covered constraint/reproduction revisions. Mere index exhaustion, no current group, or an unknown potential set is not evidence of zero. If future/unresolved parent identities could form a qualifying set, the result is **unresolved**, not complete. A later qualifying event at or before T contradicts global closure absent correction; an event after T is permitted. This proof requires species/domain semantics and is outside the first vertical slice.

## 7. World authority and transaction

Proposed request/candidate/result are frozen data without Agent/Observation arguments or executable callbacks. Candidate preparation captures parent-set indexes, constraints, Reality revisions, identity reservations, exact dependencies/write coverage, and any provisional draw trace without mutation. Atomic commit includes **the group identity/index and first offspring fact together**. It may also commit compatible scope constraints, revisions, idempotency result, and RNG state only after complete validation; a group is never visible with zero offspring.

There is no dummy Encounter, Action, or Action receipt. Do not change population counts, instantiate a Being, or update Awareness/Belief. On failure restore group/constraint/Reality registries, mappings, aliases, revisions, and RNG in place. Identical idempotency key and request returns the original result; key reuse with different content refuses. Contradictions/unsatisfiable constraints refuse without rerolling, changing dates/parents, or erasing facts.

A zero sample returns `no group`; record a scoped negative only if the request/distribution supports zero-through-T. Do not retry conditioned on positive offspring. Authored RG0 should be deterministic and nonrandom. Later sampling must specify algorithm/version, seed ownership, and whether it promises deterministic replay (same ordered requests/state), request-order invariance, or both. Preparation must not advance authoritative RNG.

**Open transaction gate:** current publication owns Encounter intervals and is not a general world publisher. Decide whether family publication may occur while an Encounter is active. If so, define coordinated world/Encounter ownership and read revisions preventing a race with the Encounter snapshot. Do not write ledgers directly or reuse the Encounter publisher without a typed approved operation.

## 8. Ontology alternatives

| Option | Assessment |
|---|---|
| **First-class world-level ReproductionGroup** | Preferred working model: names reproductive scope and supports nonempty existence, exact-set uniqueness, provenance, partial offspring, and local completeness without implying physical location or social household. Could be a Universe-owned domain record/registry. Concrete Python type, storage, and interface are **unapproved**. |
| **StatisticalGroup subtype** | Not recommended. StatisticalGroup is a counted spatial population prototype; reproductive scope need not imply population membership or physical grouping. Inheritance would conflate counts/residence and kinship. |
| **Graph-only parentage** | Useful internal edge storage and kinship derivation, but alone lacks a clear nonempty group identity, exact-set uniqueness, scoped completeness, zero constraints, and resolution boundary. Could back a first-class domain contract. |

`ReproductionGroup` is more precise than `FamilyGroup`, which can imply social/cultural family. Adoption, fostering, partnership, care, and household relations remain separate. Events remain distinct from Objects. The name recommendation does not adopt a class/storage model.

## 9. Worked cases

- **RG-PQ:** `{P,Q}` has C1 and C2: one group and full siblings. If complete through T, adding a child at T+1 is allowed; at/before T contradicts closure absent correction. Unknown date blocks horizon proof. Deceased/nonresident C1 remains historical.
- **Potential-PQ-zero:** an authorized scope asserts `{P,Q}` has zero offspring through T. No group exists. A T+1 child may instantiate `RG-PQ` while preserving that fact; a child at/before T refuses absent correction.
- **RG-PR:** `{P,R}` has C3. In this two-parent overlap, C3 is a half-sibling of C1/C2. Closing `RG-PQ` does not close P's offspring globally.
- **RG-P-asexual:** `{P}` is complete as a singleton parent set and A1 exists, so the group is nonempty. Enumeration may remain partial. Do not infer a role from gender or synthesize a second parent.
- **No-observer request:** author nonempty RG0 with `{P,Q}` and one or two stable logical offspring IDs without Encounter, Observation, Being instantiation, or population-count change. No Agent learns it.
- **Zero draw:** a sampled zero produces `no group` and, only if justified, a negative fact through T. Never create an empty group or retry for positive count.
- **Potential collisions:** two prospective claims later resolve to the same exact set. Prevent duplicate groups; atomically deduplicate compatible constraints/facts with provenance, or refuse conflict. Preserve existing offspring and negative facts; do not silently rewrite.

## 10. First vertical slice and acceptance scenarios

Prefer authored, observation-free, nonempty **RG0** with exact parent set and one or two logical offspring, plus a separate zero-through-T test for a potential set proving no group is created. This directly tests the existence/completeness rule. **B** (one edge within the 11-human StatisticalGroup) is a later integration fixture: an edge alone proves neither full parent set nor nonempty enumeration and depends on unresolved temporal/age semantics; do not make it the first product API.

Acceptance scenarios, prose only:

1. Author RG0 without Encounter/Observation; commit one exact parent set and stable offspring identity, with no Being, population-count, or Belief change.
2. Record zero offspring through T for potential `{P,Q}`; verify no group exists and unknown is distinct from zero.
3. Add a first child at T+1 and instantiate the unique group while preserving zero-through-T; reject a child at/before T absent correction.
4. Accept `{P}` as a complete singleton parent set only with at least one offspring, independently of gender and offspring-enumeration completeness.
5. Verify same-set full siblings and cross-set `{P,Q}`/`{P,R}` kinship; closing one group does not close P globally.
6. Refuse unknown origin time in horizon closure, missing identity reservation, stale revisions, duplicate exact-set identity, and conflicting zero/offspring facts without mutation.
7. A zero sample returns no group without positive-conditioned reroll or unsupported negative closure.
8. Inject failure during group-plus-first-offspring commit; restore registries, aliases, constraints, revisions, and provisional RNG, then verify deterministic retry.

## 11. Decision register and next gate

### Confirmed user semantics

Nonempty reproductive group; exact unordered parent set; same-set offspring; derived cross-set kinship; singleton asexual parent set; identity independent of gender/role; world-only on-demand resolution with no automatic Agent knowledge; distinct parent-set versus offspring-enumeration completeness; no group for potential/unknown/zero offspring; no implicit population, Being, or Encounter changes.

### Proposed engineering choices (not adopted)

Use `ReproductionGroup` as a first-class world-domain record; separate stable group ID plus canonical full-set uniqueness index; reserve a stable logical Person ID before linking the first offspring; store potential/zero scope in a separate constraint ledger/index; commit group and first offspring atomically; start with authored, nonrandom RG0; never resample zero to force nonempty; defer B, sampling, active-Encounter concurrency, and global queries.

### Still open

- Concrete type, storage owner, ID namespaces/derivation, and handling unresolved parent aliases.
- Species-supported parent cardinalities, multiple origin sets per child, event-role vocabulary, origin/birth semantics, calendar/precision, unknown times, and cycle rules.
- Proof standard for local zero and N>=1 closure, corrections/supersession, parent-set-domain closure, and global completeness across uninstantiated sets.
- Population overlap, RNG/replay guarantees, persistence/versioning, and transaction ownership/concurrency with active Encounters.
- Whether potential/zero scopes need a dedicated registry or another authoritative store; current experimental `RealityLedger` does not settle this.

### Recommended first implementation increment after review

After approving the minimal schema and authority choices, implement a pure candidate plus one no-Encounter in-memory atomic commit for authored RG0: resolved exact parent set, at least one reserved logical child identity, unique set index, group-plus-first-offspring atomicity, idempotency, and rollback. In the same bounded fixture, record a justified zero-through-T potential-set fact and assert no group; test T+1 extension and pre-T refusal. No Being creation, population change, sampling, Observation, persistence, or Encounter integration. If there is no safe world transaction owner, define that narrow authority before adding family storage.

## 12. Task tracking

`U-REL-001` remains the sole ACTIVE development objective; U-ARC-001 remains OPEN. No family generation is marked implemented. Adopted Encounter and historical issue status are unchanged.
