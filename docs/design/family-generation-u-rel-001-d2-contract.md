# U-REL-001D2 — FamilyGroups and world-level family-generation contract

**PROPOSED — NOT ADOPTED. Design-only.** No production source, tests, rules, or legacy files were changed. No legacy code was executed or imported, and no legacy data was copied into the runtime.

## 1. Evidence and checkout state

- Start branch: `main`.
- Start HEAD: `d079e414dbd0ccb41168031fabf5bf64357aeb6c`; parent `a22c284909d7f64c14cad919518f9da319bcf1ed`. HEAD is the D1 documentation commit, `Document bounded family-generation design audit`; `git cat-file` and `git ls-files` confirm [`family-generation-u-rel-001-audit.md`](family-generation-u-rel-001-audit.md) is in that commit.
- At start, staged and tracked working-tree diffs were empty. `main` was one commit ahead of `origin/main`.
- Start `git status --porcelain -uall` counted 1,166 untracked paths, 1,149 beneath `legacy/`. `git ls-files -- legacy` returned zero. Nested `.git` entries are `legacy/Lands/lands.wiki/.git` and `legacy/Lands/lands/.git`. The tree was read-only/untrusted; none of its files or nested repositories were used for execution, staging, or commit.
- The supplied revised assignment ZIP SHA-256 is `90f18bee47ff310de9b410096681f99df506217e3b57efe28df34d3e71fac575`; it was extracted to `/tmp/universe-u-rel-001d2-assignment/`, outside the repository.
- **D1 path discrepancy:** the committed D1 audit cites `legacy/src/history.py`, but that path does not exist in the current `legacy/` tree. A read-only `find` confirmed there is no `history.py` under `legacy/`. The currently present historical files used below are named explicitly; no substitute Python history source was assumed. This does not invalidate D1’s current-source findings, but its historical-source citation must be understood as evidence from the earlier local archive state, not a present file.

### Source evidence matrix

| Exact path | Inspected native/historical contract | Design implication and boundary |
|---|---|---|
| `src/universe.py` | `Universe` owns `ObjectRegistry`, `event_history`, and a schedule lock (`26–44`); Objects register through the registry (`91–99`); Actions cannot be added as ordinary Events (`101–109`); transactional save/restore refuses unsupported state (`111–140`). | A family unit could be a Universe-level domain entity, but no family registry or world-level family publisher exists. Do not add it to the physical Object registry merely to obtain an ID or lifecycle. Events remain separate. |
| `src/identifiable.py` | Explicit IDs are accepted; otherwise UUID4 is generated (`13–23`). | Stable IDs are possible, but no family/latent-person namespace or reservation/high-water contract exists. |
| `src/object.py` | `ObjectRegistry` stores ObjectInstances by ID and only inserts absent keys (`409–426`). | Registry membership currently means ObjectInstance presence. A family structure and an unresolved person need not be physical Objects or Beings. |
| `src/statistical_group.py` | `StatisticalGroup` is an `ObjectInstance`; categories are adults, children, livestock and dogs (`138–142`). Formation uses a RealityLedger and separate member/realized/Group membership stores (`149–176`). Counts are derived (`292–302`). `member()` mutates `_members` and assigns a key-derived ID (`308–323`). Adult realization is supported; child and animal Being definitions explicitly refuse (`493–544`, especially `510–511`). | Population counts, household composition, a FamilyGroup, and Person identity must remain distinct. A counted slot may be linked without materializing a Being; family membership must not imply a new population count. Candidate preparation must not call `member()` as a read. |
| `src/group_member_realization.py` | Adult slot candidate is frozen/detached and includes read dependencies, first eligible boundary and explicit write/rollback sets (`28–103`, `252–348`). | This is a narrow adult realization precedent only. It does not provide child identities, family relations, or a no-Encounter family transaction. |
| `src/being.py` | `BeingInstance` owns current mutable Being state and optional `personal_history` (`346–399`). There is no native birth date, age, or relationship graph field. | Persistent individual identity can be distinct from whether a Being is instantiated. Age/chronology rules cannot be inferred from current Being state. |
| `src/realization.py` | `FactKey` is time/detail keyed; `RealityLedger.commit()` validates the whole candidate, treats identical same-key claims idempotently, rejects conflicts, and makes no partial ledger update (`25–40`, `94–174`). `ask()` does not produce Observation or Belief (`160–174`). | Useful candidate semantics for objective facts; not a family schema, global identity reservation service, or cross-registry publisher. |
| `src/objective_reality.py` | Frozen Group objective views, composition facts and seeded/keyed sampling use the Group RealityLedger (`70–107`, `194–225`, `271–299`). | Existing deterministic composition patterns can inform a candidate design; no offspring model or family distribution is defined. |
| `src/interval_staging.py` | Frozen read sets capture selected identities, aliases, values and revisions (`190–289`); candidate validation checks completeness and next-boundary adult eligibility (`498–536`); interval construction accepts only its reviewed operations (`546–575`). | Detached preflight is reusable as a pattern, not as a world-only transaction. |
| `src/atomic_publication.py` | `RNGCursor` is caller-owned (`68–71`); the publisher has an owned lock protocol, ordered write phases and inverse journal (`30–42`, `264–323`); interval candidate application and rollback are Encounter-bound (`377–400`, `588–640`). | A FamilyGroup operation must not fabricate an Action or receipt or create an artificial Encounter. A separate world-owned transaction or a deliberate publisher extension is required. |
| `src/field_observation.py`, `src/encounter.py` | `BeliefLedger` is observer-owned (`149–161`, `232–275`); `aware_beings(observer_id)` returns only that observer’s aware participants (`614–651`). | Generation is world authority; no evidence, Awareness, or Belief is created unless a separate observation consequence explicitly does so. |
| `src/personal_history.py` | Historical skill-use constraints belong to an individual Being (`14–110`). | Personal history is not a shared multi-person kinship graph. |
| `src/checkpoint_restore_continuation.py`, `src/universe.py`, `src/encounter.py` | The supported fresh-process continuation is bounded to Run history and a later Run interval (`checkpoint_restore_continuation.py:74–78`, `109–175`); transactional Universe/Encounter serialization remains restricted (`universe.py:111–140`, `encounter.py:1050–1058`). | FamilyGroup persistence and cross-process family replay are separate future work; this design does not claim them. |
| `tests/test_transactional_group_member_realization.py`, `examples/nomadic_group.json` | The focused fixture asserts total humans equal 11 (`tests/test_transactional_group_member_realization.py:45–75`, assertion at line 59); the configuration supplies composition CDFs and motion/observation settings. | Eleven is the fixture’s total-human invariant, not evidence of individual age, exact parentage, or already materialized member identities. B must validate actual category counts and slot existence rather than assume an adult/child pair. |
| `legacy/FAMTREE/FAMTREE.C` | `FAMILY`/`ID` contain mother/child/sibling pointers, dates and lifespan; `dad` is declared (`8–25`). Navigation lazily expands an ancestor or offspring family (`84–133`), but child counts/dates and sibling chains are generated eagerly within a family (`135–207`, `209–282`). | Historical on-demand navigation concept only; not a stable-ID, complete, multi-parent, constraint-safe or atomic model. The inspected generator does not populate `dad`. |
| `legacy/FAMTREE/LIFESPAN.C` | Uses age-stage values and survival weights with random rolls (`6–27`). | Historical lifespan idea only; no adopted current distribution semantics. |
| `legacy/src/data/offspring_human_wlist.csv`, `legacy/src/data/age_human_list.csv` | One legacy weighted offspring table has count rows 0–14; the age table contains labels and values 15, 20, 40, 80, 90, 100, 120. | Unverified historical data formats, not calibrated or approved Universe rules. No import or runtime use. |
| `legacy/src/longevity.py` | A stored percentile is described for later lifespan-table mapping (`22–59`); the source contains an incomplete inserted text fragment. | Not a usable sampler. Do not execute or port. |
| `legacy/src/HISTORY.C`, `legacy/FAMTREE/NPC.H`, `legacy/NPC/npc90/NPC.H` | HISTORY samples child count/rank, dates and survival for a printed narrative (`12–85`). Headers hold fixed NPC age/sex/body-stat fields (`legacy/FAMTREE/NPC.H:78–91`; `legacy/NPC/npc90/NPC.H:126–167`). | Snapshot and presentation precedents only; no durable relationship graph or modern identity contract. |
| `docs/design/family-generation-u-rel-001-audit.md`, `docs/historical-evidence-archive-index.md` | D1 recommends B as the smallest relationship primitive; the archive index gives private archive locators/checksums and says it is not a specification. | D2 expands the objective to a first-class FamilyGroup candidate and preserves D1 as evidence. Historical format decoding, provenance and rights remain open under U-ARC-001. |

No source, test or adopted Encounter rule supports a FamilyGroup ontology today. D1’s B proof is only a relationship primitive; it cannot by itself demonstrate observation-free creation or complete family generation.

## 2. Ontology and boundaries

**Recommendation: design FamilyGroup as a first-class world-level reproductive structure, not a `StatisticalGroup` subtype and not necessarily an `ObjectInstance`.** It should own the scope, constraint inputs, parent/offspring links, revision, provenance and explicit completeness claims for one reproductive-family unit. The implementation representation could be a typed immutable record in a Universe-owned family registry/Reality service. That registry, durable identity namespace, and atomic owner are design dependencies, not existing APIs. A stable FamilyGroup ID must be distinct from all Being and population-member IDs.

| Candidate | Benefit | Problem / boundary | Recommendation |
|---|---|---|---|
| **A. First-class FamilyGroup world entity / generative structure** | Gives a natural place for family-scoped constraints, unresolved state, progressive resolution and scoped completeness. Can exist without any Being or Encounter. Cross-family links can reference the same Person identity. | Requires new typed storage, identity and world transaction contracts. Must not inherit ObjectInstance’s physical-object semantics by convenience. | **Preferred design candidate, unadopted.** A domain entity/value in a Universe-owned family registry is the least misleading first representation. |
| **B. FamilyGroup as StatisticalGroup specialization** | Could reuse some keyed sampling and Reality utilities. | StatisticalGroup means aggregate population composition/households and has physical motion/footprint, member slots and current membership. FamilyGroup concerns parentage, not population count or residence; a person can span family structures and Groups. Inheritance would make those distinctions easy to violate. | Reject as the initial design. Reuse narrowly reviewed deterministic/ledger ideas, not the subtype. |
| **C. Relation-graph-only design** | A shared graph can represent cross-family parentage and derive kinship without an entity hierarchy. | A bare graph has no clear family-specific distribution/constraint boundary, unresolved state, request scope, or completeness marker. It may still be the internal edge store beneath FamilyGroup. | Useful storage primitive, insufficient as the whole authoring/resolution API. |

### Distinct concepts

- **FamilyGroup:** one explicitly scoped reproductive configuration and its parent/offspring constraints. It is not a household, residence, social unit, population cohort, or generic relation bundle.
- **StatisticalGroup / population:** aggregate, potentially counted membership. Family membership does not add a member to a StatisticalGroup. A person can be represented by one stable identity in several family structures and at most once in a given population count, subject to that population’s rules.
- **Being:** fully instantiated individual state, using the same identity as a reserved latent person if/when instantiated. A family member need not yet be a Being and may be historical/deceased or outside the current population.
- **Household, care, adoption, partnership:** separate relation families and scope. They must not be implied by reproductive parentage.
- **Events:** birth, death, migration, conception, or other time-bearing occurrences may eventually be typed world facts; Events remain ontologically distinct from Objects.

## 3. Reproductive scope, roles, time and derivation

“Parents and their children only” should bound the FamilyGroup’s declared reproductive parentage. It should not imply a shared household, exclusive couple, fixed number of parents, gender mapping, fertility, gestation, co-residence, adoption, care, or social siblings.

Two parent-set semantics remain open:

1. **Exact shared parent-set:** every child in the FamilyGroup has the same complete parent/contributor set. This gives compact completeness and sibling inference, but it excludes families with different co-parents or contributors.
2. **Flexible per-child sets:** each child has its own typed set of parentage/contribution roles within a FamilyGroup scope. This supports more configurations and non-human reproductive systems, but “FamilyGroup” is then a scoped organizer rather than a single shared-parent family.

**Proposed default for review:** use flexible per-child parentage links; record the role and provenance for each link. Do not equate all roles. Candidate role vocabulary should distinguish genetic/progenitor contribution, gestational contribution, birth event/parent where meaningful, and separately authored adoptive/social/caregiving relations. Do not assume every species has gendered, paired, fertile, or gestational parents. Role ontology needs explicit approval before implementation.

Store objective atomic facts that are needed for consistency: stable person endpoint IDs, typed relation role, effective/event time, temporal validity if a relation can end, source/provenance, and the family scope/record ID. Derive sibling and ancestor queries from approved parentage facts where semantics allow. Do not separately store “sibling” as an independent fact unless a distinct social/legal sibling rule is approved. A parentage ancestry cycle should be rejected if the chosen relation semantics require acyclic descent; temporal ordering should be validated against explicitly modeled events, not invented universal ages. Current Being has no age/birth-date field. Gestation and other reproductive timing cannot be inferred from legacy tables.

## 4. Progressive elaboration and completeness

The proposed model separates these operations; each can be committed independently only with a suitable revision and dependency contract:

1. **Create unresolved FamilyGroup:** allocate a stable family ID; store authored constraints/distribution references and provenance. Parent identities, child count, child identities, relations, attributes, and Being instances may all remain unresolved. Creation can happen with no Encounter and no Observation.
2. **Resolve parent/child roles:** determine exact role membership or reserve logical identities. A zero-offspring result is distinct from “offspring count unknown.” Reserving a latent identity does not construct a Being or add a population member.
3. **Establish parentage and chronological facts:** add complete typed links and event/effective times after joint validation against prior Reality and other FamilyGroups.
4. **Resolve individual attributes:** fill explicitly requested traits such as age/date, physiology or history under approved distributions and constraints. Family completeness does not imply attribute completeness.
5. **Instantiate a Being:** materialize an already reserved identity through its own native constructor and publication boundary. The identity must not change; Being state can remain partial only where native model permits. It is distinct from family membership and population membership.

### Completeness claims

“Complete” must always be scoped. A claim should name the FamilyGroup or global query, relation semantics and roles covered, horizon (including its inclusive/exclusive boundary), member-identity status, parentage status, and schema/revision. Independent dimensions should say `unresolved`, `partial`, or `complete` for parent roles, child identities, parentage, chronology, selected attributes, and Being instantiation.

Example: “All children of parent identity P, for reproductive role R, with event time `<= t`, in FamilyGroup FG, have identified logical person IDs and committed parentage; their other attributes and Being instances may remain unresolved.” This must not mean “P has no other children in other FamilyGroups,” “all siblings are known,” or “the child’s attributes are complete.” A later contradictory child within the closed claim must be refused or require an explicit, versioned correction/supersession; a child outside the role/time/group scope is not a contradiction.

- **Zero children:** commit count zero plus a completeness claim for the exact scope/horizon. Unknown count has no zero claim.
- **Deceased or migrated children:** identity and historical parentage remain in Reality. Death/migration is separate typed time history. A deceased or moved child is not silently removed from the FamilyGroup’s historical scope.
- **Population overlap:** a FamilyGroup does not change any StatisticalGroup count. If a generated person belongs to an established counted population, bind that person identity to one already-counted slot or run a separate explicitly authorized population transaction. Never count the same Being twice because it participates in several FamilyGroups.
- **Unresolved details:** family role completeness may be true while individual attributes, life events, observation, or Being instantiation remain unresolved.

## 5. Cross-FamilyGroup parentage

The same stable person identity may be a child in `FG-A` and a parent in `FG-B`, without creating two Beings or two population memberships. A person may also appear in more than one reproductive configuration (for example, different contributor sets or temporal contexts) if the adopted role semantics allow it. FamilyGroup membership is therefore many-to-many references, not ownership of a Being.

A local “all children in FG-A” completeness claim closes only that family’s declared scope. A global “all offspring of P through t” query must union applicable parentage facts across every relevant FamilyGroup and any explicitly supported non-FamilyGroup parentage source. It needs a global resolver/index and a global completeness claim. Completion of one FamilyGroup must never assert that no other FamilyGroup contains offspring of P. Deduplication is by Person identity and relation semantics, not family count or population slot count.

## 6. World request, detached candidate and result

The following is a candidate data contract, not an API declaration:

- **`FamilyGroupSpec` (data only):** stable FamilyGroup ID; schema/version; relation semantics selected by the author; time domain; explicit anchors and constraints; optional validated distribution IDs/versions; parent-set mode; provenance; and requested completeness scope. It contains no executable generator.
- **`FamilyResolutionRequest` (frozen):** trusted world-authority origin; idempotency key; one or more FamilyGroup IDs or a specifically global offspring query; anchor identities; inclusive/exclusive horizon; requested elaboration levels; expected Reality/family/Group revisions; deterministic seed/draw-owner reference where approved; and provenance. It has no Agent recipient or Observation argument.
- **`FamilyResolutionCandidate` (detached immutable):** normalized request; exact read/dependency set; logical identity reservations; all proposed objective relation/lifecycle/population facts; resolution completeness claims; deterministic provisional draw trace/state; coverage certificate; and exact write/rollback/alias plan. Preparation neither calls mutating `StatisticalGroup.member()` nor allocates authoritative IDs, mutates caches, consumes authoritative RNG, changes counts, changes Beings, or touches Belief/Awareness.
- **`FamilyResolutionResult` (data only):** commit revision, stable FamilyGroup/person identities, committed facts/provenance, resolution level and exact completeness claims. It is a world-authoring result; it contains no evidence, Awareness or Belief update.

### Identity and population closure

Reserve logical Person IDs in a world-level namespace independent of names, materialization, Group membership, or Being object allocation. Existing Being/Group slot IDs may be referenced only when their ownership/read dependencies prove membership. A person reserved under a FamilyGroup identity must be reusable by later FamilyGroups and Being materialization; collision checks span the Universe ObjectRegistry, all family reservations, Group slots, history, and Encounter participants where present. Do not expose unresolved identity reservations to Agents. The actual namespace and deterministic derivation rule need approval.

For a counted Group, candidate closure must prove every referenced slot exists in its committed category/household count; preserve the entire category-count map and totals, not just total humans. New offspring not already represented by a counted slot may exist as historical/out-of-Group logical people, but must not be injected into a Group count implicitly. If the intended result changes population counts, that requires a separate authored population write and transaction.

### Determinism, requests and refusal

Candidate construction is pure. Authored complete family data needs no random draw. If later approved distribution sampling is used, derive provisional draws from stable world seed + FamilyGroup/member/fact namespace and the canonical generation scope, with recorded algorithm/table versions. Commit RNG advancement only with successful publication. Do not use observer RNG or an ambient module-global stream.

**Replay** requires the same initial state, schema, ordered requests and draw owner to reproduce the same results. **Request-order independence** requires independent facts for the same anchors to be invariant to unrelated request order. These are different guarantees. Per-member keyed streams help independent resolution; a family-wide child count, shared constraints or coupled sibling dates may still depend on joint canonical resolution. The initial B gate should be authored and nonrandom; no RNG guarantee should be claimed beyond purity.

Reject stale dependencies, duplicate or colliding reservations, incomplete candidate coverage, incompatible time/roles, contradiction with committed Reality, and unsatisfiable constraint sets before writes. Do not reroll to conceal a contradiction, select a different parent silently, shift a date, or overwrite a prior fact. Same idempotency key and identical normalized request returns the original result without additional facts/revision; same key with different content refuses. Any publication failure restores all world/family/population writes and RNG in place; observer ledgers remain unchanged. The current Encounter publisher does not implement this no-Encounter world transaction.

## 7. Worked pseudodata examples (not executable code)

### FG0 — observation-free FamilyGroup creation and full authored elaboration

At world time `t0`, an author creates `FG0` directly in the world family registry. No Encounter exists and no Agent or Observation is supplied.

**Unresolved form:** `FG0` has a stable FamilyGroup ID, authored role semantics version, time domain and source provenance; parent identities and offspring count are unresolved; no person slots, relation facts or completeness claims have been committed. The record says explicitly that it is unresolved, not childless.

**Fully elaborated authored form:** the author supplies logical people `P-a`, `P-b`, and `C-a`; typed per-child parentage roles selected under the adopted schema; the required event/effective times; and an exact roster/parentage completeness claim for `FG0` through `t0`. Person attributes may remain unresolved and none of the three needs to be instantiated as a Being for this family structure to be objective. A separate no-Encounter world transaction validates all references and constraints and commits all facts together. Agent evidence, Awareness, Belief and Observer histories are unchanged. The example intentionally does not prescribe how many parent roles or their biological meaning.

### B — one relation between two already-counted slots in the 11-human Group

World-authorized pseudoreferences `P-slot` and `C-slot` name an already-counted adult slot and child slot in the existing 11-human StatisticalGroup after its committed category counts are checked. Candidate proposes one explicitly authored typed parentage edge and its time/provenance. It creates no FamilyGroup membership distribution, no Being, and no population entry. Before/after `adults`, `children`, `livestock`, `dogs`, `humans=11`, and household totals are identical. No Observation/Belief changes. If the actual seeded category map cannot supply a compatible pair or the approved temporal rule fails, refuse; do not infer a pair from total count 11. This is the smallest relation/identity/atomicity engineering primitive, not the eventual FamilyGroup generation API.

### A — all offspring of one Being through time `t`

Request `Q-A` anchors existing person P, declares approved offspring roles, scope and inclusive horizon `<= t`, and asks for a complete objective result. The resolver consults already committed child relations in `FG1` and `FG2`, deduplicates shared child identity `C-a`, and resolves any still-unresolved offspring facts required by that scope. One child `C-b` is deceased and another `C-c` belongs to a different/currently uncounted population; both remain in the historical offspring result without being added to the 11-human Group. The result records that P's offspring in the approved role set through `t` are complete across all named/relevant FamilyGroups. It does not assert completeness after `t`, for another parentage role, or for another person's children; children with event time `>t` may later be added. No Agent learns the result automatically. This request is invalid until “offspring,” relevant family registry coverage, deceased-child inclusion, and group-count treatment are approved.

## 8. Decision table — all choices remain NOT ADOPTED

| Decision | Competing options | Proposed direction | Consequence / approval need |
|---|---|---|---|
| Ontology | first-class FamilyGroup; StatisticalGroup subtype; relation graph only | First-class world family structure, not a StatisticalGroup or physical Object subtype; graph may store its edges | Approve ownership/registry semantics and stable IDs. |
| Parent set | exact shared set for every child; flexible per-child sets | Flexible per-child typed sets | Approve role taxonomy, multiple contributors and whether a parent can participate in overlapping configurations. |
| Relationship types | one generic parent link; reproductive role links plus distinct social/adoptive/care roles | Typed, distinct facts; do not imply social/household meaning | Approve which reproductive roles are in D1/D2 scope and which are explicitly excluded. |
| Time | timeless links; one timestamp; validity interval plus typed events | Separate event/effective time and optional interval; no fixed age thresholds | Choose calendar, precision, boundary inclusivity, birth/death/gestation semantics and cycle checks. |
| Completeness | whole FamilyGroup flag; per-dimension scoped claims | Per-dimension claims scoped by FamilyGroup/query, role and horizon | Approve closure meaning and versioned correction rule. |
| Childless | empty unresolved roster; explicit zero offspring | Distinguish unknown from explicit zero + closed scope | Approve whether zero is generated/authored and how long that claim closes. |
| Identity | Being ID only after materialization; latent person ID first; Group slot as identity | Stable logical Person identity before Being; optional binding to existing Group slot | Approve namespace, derivation, collision registry and cross-family reuse. |
| Group overlap | family owns count; Group owns count; independent many-to-many membership | Group count remains population authority; family links reference identities/slots | Approve handling of new/out-of-Group/deceased persons and any explicit count change. |
| Authoring vs sampling | fully authored; sampled distributions; hybrid constraints | First proof author-supplied and nonrandom; sampling later only from adopted versioned distributions | Historical weights remain unused pending provenance/rights review. |
| RNG | ambient stream; one sequence stream; keyed per family/person | No draws for B; later use private provisional, versioned keyed draws with commit-only advancement | Decide replay scope vs request-order independence; test both separately if required. |
| Completeness across families | local group implies all offspring; global query across all family sources | Local completion never implies global completion; A requires explicit global coverage | Approve registry/index completeness and sources in “all offspring.” |
| Publication owner | Encounter publisher; separate world transaction; direct ledger mutation | Separate world-owned atomic transaction for no-Encounter generation | Approve authority and lock/rollback closure. Do not create a dummy Encounter or fake receipt. |
| Persistence | in-memory only; general save/restore immediately | Keep persistence out of first proof; define versioned representation later | Existing continuation does not cover FamilyGroups. |

Safe implementation choices after rule decisions: immutable dataclasses, detached mapping/tuple storage, exact dependency hashes, explicit non-executable schema/version IDs, direct refusal of unsupported fields, and fault injection. Choices requiring user approval: all semantics in this table, especially the meaning of reproductive parentage, time, childless completeness, global scope, ID derivation, sampling and transaction owner.

## 9. Bounded future proof gates (not implementation)

1. **Pure contract and B candidate:** after semantic approvals, build immutable request/candidate/result data plus a validator for one authored edge between two world-authorized already-counted slots. No commit or Being creation. Test count-category validation, reservation collisions, stale read, time/role contradiction, idempotency and no RNG/Belief mutation.
2. **FamilyGroup objective store and identity reservation:** create an unresolved FG0 and commit explicit parent/child role identities/constraints in a world-owned ledger. Test cross-FamilyGroup shared identities, partial resolution, scoped completeness, zero children and population conservation. Do not subclass StatisticalGroup.
3. **No-Encounter atomic publisher:** implement typed world authority, full read-set/write-set/rollback, alias preservation, RNG commit, consistency verification and failure injection. Prove B and FG0 authored facts; no Action/Encounter receipt and no Observation/Belief writes.
4. **Observation-free generation demonstration:** author one bounded FG0 end-to-end with explicit complete roster and parentage, including a zero-offspring case or an authored nonzero case only as separately approved. Then add deterministic distribution resolution or A’s cross-FG all-offspring query only after its scopes/data are approved. Keep Being instantiation as a separate later operation.

## 10. Task maintenance and outcome

`TASKS.md` retains U-REL-001 as the **only ACTIVE development objective** and links this proposed D2 contract. `docs/tasks/generation-and-attention.md` distinguishes the new FamilyGroup candidate from StatisticalGroup and links both D1 and D2. U-ARC-001 remains open for safe decoding, provenance and rights work. Existing IDs/statuses other than the minimal U-REL-001 description remain unchanged; the revision-60 issue register, queue and Encounter rules are untouched.

The recommended next user decision is to approve or revise the first ontology, reproductive-role vocabulary, and time/completeness semantics. Until those decisions are made, the proof gates remain proposals. In particular, do not treat Alternative B as permission to invent biological age or to infer a parent–child pair from aggregate count alone.
