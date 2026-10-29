# Universe 4 checkpoint and compatibility contract — DRAFT

**5D2A revision of the 5D1 draft; inactive design only. Not an active save/restore, migration or replay format.** No round trip or deterministic restored continuation has been implemented or verified. The authoritative decision record remains normative for simulation semantics. This document proposes engineering requirements for later review; it does not introduce gameplay or observer-access rules.

## 1. Readiness and format separation

Three independent assertions are required:

| Assertion | Meaning | 5D2A |
|---|---|---|
| `closure_validated` | Every required authoritative value, dependency, alias and reference has a reviewed representation and semantic validation. | Always false |
| `portable_schema_defined` | Full checkpoint semantics and all identity/ownership/compatibility bindings have a complete expressible format. | Always false |
| `restore_verified` | Isolated rehydration, identity/reference rebinding and deterministic continuation passed independent tests. | Always false |

The original diagnostic mode and opt-in native adapter mode both remain **partial inventories**. The envelope has schema `universe.checkpoint-inventory-draft/1`. It is a data/diagnostic witness, never a resumable checkpoint. `inventory_validated` means an issued inventory remains fresh under the covered native predicates and identity/content dependencies. It does **not** certify complete semantic closure. Unknown uninspected values make even that inventory result false; blocking diagnostics remain present in every candidate. `require_complete()` always refuses.

The proposed future authoritative document is provisionally called `universe.authoritative-checkpoint` with a separately reviewed schema version. That format is **not implemented**, and no existing save/session version has been changed. Neither `EncounterInspection`, its HTML, a source hash, a receipt, nor this inventory is a substitute for it.

## 2. Identity and ownership graph

Logical identity must be distinct from `id(obj)`, a lock/lease, weakref, process issuance or a content seal. No process addresses may become portable identifiers.

| Native role | Grounded identity/reference requirement | Status/gap |
|---|---|---|
| Universe | A checkpoint-root namespace plus existing `Universe.id`; current native ID defaults to `"0"`. | Scoped identity works within one isolated bundle. It is not a globally unique multi-Universe ID; cross-root merging needs a reviewed contract. |
| Encounter | Existing Event ID, specialized as Encounter, owned by the root Universe. | Must be the same node referenced by Event registry, ChoiceBook and Actions; no duplicate replacement object. |
| Being/Object/weapon/armor/group | Existing registry key and exact matching native object ID, scoped by Universe. | Retain current/original definitions, containment, equipment, possessions and spatial links. Every non-null relationship needs a typed reference and checked referent. |
| Ordinary Event | Native ID, concrete type, Universe/parent reference and timing. | Origin Event ID `"0"` remains an ordinary Event, not an Action. Unsupported Event subclasses require explicit adapters. |
| Action | Native Event ID, exact family/version tag, owning Encounter and actor/Target/instrument IDs. | Includes unpublished accepted members not yet in Event registry; they must become the same objects upon whole-choice publication. |
| Choice | Existing `ChoiceView.id`, Encounter ownership, version, state and complete member key/order. | Persist accepted records, packets, first-start fence and the counter necessary to avoid future ID reuse. Do not manufacture a valid subset. |
| Reservation | Native tuple `(choice, action, object, start, effective boundary)` plus after-settlement semantics. | All references must resolve. `[start, boundary)` and endpoint handoffs retain adopted rules. |
| Owned record/container | Typed owner-relative path, ordered slot/key and exact alias references rooted at an existing logical owner. | Proposed structural identities are owner-relative, not unrelated minted UUIDs. Must validate ownership/alias semantics and absent-vs-empty distinctions; a generic first traversal path alone is not full ownership certification. |
| Definitions/Library | Native Library identity; dictionary kind, lookup key/type and resolved data content. | Capture actual definitions, not filenames alone. Preserve shared originals and independent mutable current definitions. Unknown dictionary/definition extensions refuse. |
| Personal-history/formation ledger | Stable owned role under Being personal history or group formation, with keys/revisions/origins/order. | Reconstruct constraints from a reviewed native owner/type adapter, never serialize callbacks. |
| External Belief ledger/account list | An explicit durable binding owned and supplied by the authoritative host, including stable recipient identity, scope, owner, role, content and alias relationships. | **5D2A:** explicit host bindings are implemented for bounded native ledgers/account lists (section 9); restoring-host rebinding is not implemented. `BeliefLedger.observer_id` does not distinguish multiple ledgers for one observer; `id(list)` is not durable. Do not name a recipient after whichever Action happens to be traversed first. |
| Target interval record | Target ID + Encounter ID + boundary, with canonical incoming/outgoing effect provenance. | Target owns resulting HP, practice and state. Rebuild native history list/record identity anchors after rehydration. |
| Effect | Existing `EffectIdentity(encounter, boundary, source Action, channel, slot)`. | Unique ownership/coverage; reference reuse is not another application. Preserve all designated defenses. |
| Skill history | Target-owned native `SkillUse` or `BatchSkillUse`, chronological position and causal exercise/effect IDs. | Preserve simultaneous transitions; do not convert one batch into fictional sequential gains. Historic external Action labels need an explicit supported causal-record policy, not invented Events. |
| RNG authority | Explicit logical owner/role and exact state, plus private/shared scope and all shared bindings. | Private Cursor/Random can be proposed as an Encounter-owned role after host declaration. Module RNG or shared authority requires whole-owner closure. A copied state tuple is not proof of private ownership. |

Safe cycles must be references: World↔Event/Encounter, Encounter↔ChoiceBook, Action↔Encounter, PersonalHistory↔Being and shared templates/recipients. A restore must preserve these relationships without recursive copies or replacement identities in an already exposed graph.

## 3. Complete field closure required for a future checkpoint

The source-derived [observed field catalog](universe4-increment5d1-evidence/observed-field-catalog.json) enumerates actual fields found in native fixtures. It is evidence, **not** an approved closed-field adapter list. Unknown added fields must fail full closure until reviewed; they must never be silently treated as optional.

Classification: **A** authoritative required; **D** derived with an explicit reconstruct/validate rule; **T** transient and excluded; **U** currently unsupported/unbound. Future full closure must resolve every A/D/U relationship below.

| Source/fields | Class | Required treatment |
|---|---|---|
| `Universe`: `id`, `type`, `name`, `library`, `object_registry`, `event_history`, `_schedule_revision`, `_choice_books` | A | Whole supported world registries and all participants, including registered objects outside the selected Encounter. Preserve ordering where consulted by native operations. Validate root/index ownership and uniqueness. |
| `_schedule_lock`, publication gate/lease, route-running lock, weak issuance tables | T | Create fresh native synchronization/issuance under future restore ownership. Never load old addresses, leases or lock state. |
| Encounter Event fields; `difficulty_class`, `initiated`, `initiation`, participants, `awareness`, `map`, `local_frame`, `location` | A | Preserve actual origin, scope and physical context. Unknown map/location references refuse. Awareness is directed Target-owned observer state, not automatic evidence/Belief. |
| `time`, `last_processed_boundary`, `_coordinator_time`, `_interval_start`, queues | A/D | Must describe one coherent committed checkpoint; private clock mirrors can be reconstructed only after exact consistency validation. Support initial t=0 and native fractional original starts. No fractional tail or active second. |
| `active_boundary`, `boundary_fault`, `_advancing`, `_dispatching`, `_running`, `_boundary_context`, `_active_fatigue_frame` | T/coherence | Require idle/non-faulted values, then rebuild idle machinery. Fault/emergency recovery is not a checkpoint restore procedure. |
| `_transactional_mode` and process binding | A role / T addresses | Preserve the explicit selected mode/authority role; rebuild native binding and RNG ownership. Do not persist `encounter_identity` or `rng_owner_identity`. |
| `fatigue_frame_history`, `last_fatigue_frame`, `_physiology_registry` | A/D | Retain prior committed context and resolved profile versions as required for history/inspection; validate any reconstructible last-frame cache against recorded frames. No fatigue settlement is enabled. |
| Action common declaration, family-specific parameters, Strategy; start samples, `_activity_started`, threat snapshots; parent/Target/actor/instrument/designated-strike links | A | Complete accepted, published future, executing and settled records with nominal fractional timings and actual lifecycle. Never recalculate start positions or preparation from today's world. |
| `resolution`, `_atomic_effect_ids`, `_atomic_lifecycle`, `_atomic_acknowledged_boundary`; cancellation time/reason | A | Action causal facts and complete lifecycle only. No Action-owned Target HP-before/after or resulting ranks. Reject legacy result substitution. |
| ChoiceBook `_choices`, `_states`, `_reservations`, `_registered`, `_counter`; `_Accepted.view/members/prepared/origin` | A | Preserve current planning changes after the latest receipt, not just historical receipt schedule. Pending/future membership and reservations must agree with all packets, references and queues. |
| `_Accepted.signatures`, `_registered` declaration tuples | D | Existing `declaration()` includes Python class/object addresses. Replace with reviewed semantic reference validation, then regenerate fresh process signatures after native objects are bound. |
| `_drafts`, `_tokens`, `_closed_drafts` | T | Editable/unaccepted UI drafts are excluded. Invalidate old validation tokens; retain counter monotonicity and prevent stale-token reuse. |
| Object `original`, `current`, shape/optics/spatial state, facing, container and possession/held/equipment links | A | Preserve alias structure and negative HP, dimensions, defenses/hardness, weapon attacks/categories, body parts and all other current fields. Validate dangling containment/equipment and invalid cycles with reviewed predicates. |
| Being ranks/XP/baselines/skill-use history, abilities/states/general experience/strategy, discrete Exertion/fatigue state, effective fitness | A/D | Capture actual values and definitions. Validate derived mirrors rather than reset them. Preserve native legacy `SkillUse` meaning and Target-owned batch transitions. |
| `physical_fatigue.q/b`, `physiology_id`, original/current physiology defaults; registry definitions/inheritance/model/parameters/resolved hashes | A | Exact current reserves and reference context. Do not infer Q/B from old fatigue levels or apply R4 depletion/work/PCFS rules. |
| Target `_atomic_target_history` and `TargetCandidate` records | A | Starting/result HP, actual damage, fatal flags, protection, awareness, observer/practice transitions and all causal IDs. Preserve complete prior committed records and order. |
| Receipts: Encounter/boundary, Action/effect sets, historical RNG, notification intents, frozen inspection context | A/D | Validate complete chronological chain and authoritative provenance. Historical positions and recipient projections cannot be replaced by current state. Retain all state-bearing context. |
| Receipt `target_anchors`, `action_anchors`, `AuthorityReference.identity`, subject `ledger_identity`, weak issuance | D/T | Resolve by logical roles/IDs and canonical owned records; build new native anchors/seals only after all restored identities exist. Old digests over old addresses are not portable authenticity. |
| RealityLedger `_records`, `_revision`, `_atomic_provenance`; FactKey/value/origin/revision | A | Preserve complete ordered established facts; no overwriting, sampling or rerolling on load. Validate keys, revision ranges/order and historical constraints jointly with Target practice. |
| `_validators`, literal `EpisodeFacts` vs arbitrary generators | D/U | Literal declarations are data. Native bound constraints need reviewed owner/type/version rebinding. Arbitrary generators/validators/callbacks must refuse, never execute to infer missing state. |
| StatisticalGroup config, seed, formation/time, motion/limits/footprint; original/current membership, members, realized/arriving/departed/attached sets/history, formation traits | A | Preserve actual native relationships and keyed identities. Full group membership/realization beyond the bounded candidate family needs dedicated adapters. No eager individual realization. |
| Group `_counts` | D | Derived from committed formation facts under existing native rules; retain and validate, or reconstruct under a declared exact rule. Never realize missing composition just to populate a cache. |
| `StatisticalGroup._conditional_attributes`: specifications, `_external`, `_committed`, `_rng_for` | A + U | Current `ConditionalAttributes` owns already committed data and a lambda-backed keyed RNG provider. **5D1 gap addressed in 5D2A:** exact native store/provider data recipe is available under explicit adapter mode; custom providers refuse. External quota assignment proof and full member realization closure remain unsupported (section 9). A config/seed alone does not replace prior commitments. |
| Belief `_evidence`, `_interpretations`, `_current_reassessments`, `_belief_history`, `_reassessments`, `communication_log`, `_inquiry_history`; heard-account lists | A + U owner | Preserve distinct subjective records, ordering, identity/recipient aliases and testimony as accounts. No automatic learning, truth promotion or external delivery during capture/restore. Missing durable recipient ownership prevents closure. |
| Module/Random/Cursor state; keyed group/observation seed/key/time inputs | A + U scope | Exact RNG state including Gaussian cache and version; record owner relationships. Keyed streams preserve all identity tokens/config. No global RNG reset or draws merely to restore. |
| Unrecognized native fields, arbitrary extensions, callbacks, unsupported aliases | U | Explicit refusal until declared field/type/ownership adapters exist; generic field enumeration is not semantic approval. |

## 4. Inactive canonical inventory representation

The current envelope is immutable tuples/scalars with explicit tags. It has a compatibility header, root reference, typed graph nodes, RNG role/scope/state and false readiness flags. Known root entities/Events/choices use existing native IDs; nested nodes use owner-relative diagnostic paths. Cycles/aliases become references. These paths describe traversal in this inventory; they do not establish durable ownership of external recipients or certify arbitrary graph aliases.

Scalars distinguish null, bool, decimal integer and binary64 `float.hex()` (including signed zero). Non-finite floats refuse. Strings preserve Python Unicode content without normalization. Ordered mapping entries, tuple/list positions and ledger/history order are retained. Native object fields are sorted by name; supported scalar sets are normalized deterministically. Unknown unordered records refuse. Absent attributes, null and empty collections are distinct.

The diagnostic digest uses closed-data ASCII-escaped JSON bytes. It is **not** a durable encoder, MAC, identity or receipt authentication mechanism; validation also compares the full in-memory semantic envelope and native dependency identities. Exact Unicode/surrogate behavior and injective durable encoding must be tested before implementing a file schema. Proposed durable encoding must preserve code points without normalization/loss, explicitly handle surrogate-containing legacy strings or reject them with a compatibility error, retain exact numeric tags and represent ordered maps as ordered records. No `pickle`, executable type loading, unreviewed `repr` or arbitrary serializer is permitted.

Current compatibility inputs distinguish schema, implementation source fingerprint, selected rule-kernel source fingerprint, authoritative decision-document fingerprint, exact Python runtime/native RNG state family, numeric representation and missing restore-adapter version. Library/config/profile data are included in the actual captured graph and content comparison. Source hashes cover the dirty working source, not just Git HEAD. These are conservative draft identity inputs, not proof of semantic compatibility across versions.

## 5. Compatibility and migration matrix

| Input | Capture/design disposition | Future restoration/migration requirement |
|---|---|---|
| Native initial transactional state, explicit private RNG, no external recipient | Coherent partial inventory possible; complete flags false. | Closed field/alias/definition/reference validation and native rehydration adapters still required. |
| Native accepted unstarted choices / published future members | Represent current accepted records, prepared packets, IDs/counter, states/reservations and Action samples. | Rebuild semantic declarations/signatures without publishing/starting Actions. |
| Current committed transactional graph | Preserve Target histories and all receipt context except identified native address anchors. | New identity anchors/issuance and complete history/coverage validation before use. |
| Native shared Reality with external recipients/conditional attributes | 5D1 diagnostic mode remains blocked; 5D2A native mode represents recognized recipes with explicit bindings. Still no complete/portable result. | Complete semantic/alias proof, quota/member closure and receipt/signature reconstruction remain required. |
| Prior generic Universe JSON | Not accepted as a checkpoint candidate. | Individual complete data fields may be recoverable by reviewed adapters; loader does not reconstruct a coherent functional Being/Action/Encounter/RNG graph. Missing state cannot be invented. |
| Historical Encounter/Action JSON | Existing restore/export refusal retained. | Reject absent cursor, choices/reservations, full Target/history/practice/recipient/RNG context. HP clamping or legacy Action HP fields cannot reconstruct simultaneous causal contributions. |
| Tactical duel sessions versions 1/2/3 | Remain legacy seed/command-journal contracts in `TacticalDuel`; no transactional migration. | A pinned legacy engine can check its own trace. Commands/fingerprints omit new atomic chronology/choice/receipt/Target provenance; do not fabricate transactional equivalents. |
| AI sessions/traces | Coupled to policy decisions, observations and legacy facade ownership. | Preserve explicitly recorded legacy decisions under a compatible legacy path, not a new policy run. Incomplete ownership/randomness/input history refuses migration. |
| Developer `EncounterInspection`/text/HTML | Omniscient diagnostics, never resumes. | Cannot reconstruct omitted authoritative/unpublished state from a display. |
| Opaque Action/generator/validator/owner extension | Refuse. | Reviewed data/evaluation/rehydration contracts first; never execute a callback while importing to discover meaning. |
| Newer unknown schema / changed rule signature | Refuse with exact mismatch category. | Explicit semantic migration/adapters and equivalence/continuation tests; never silently reinterpret. |
| Changed implementation, identical declared rule signature | Not automatically compatible. | Prove adapter and restored continuation compatibility; implementation fingerprint has separate meaning. |
| Missing old Q/B or physiology | Do not infer from discrete fatigue. | Existing opt-in `read_physical_fatigue(missing='fresh')` is an explicit reset policy, not faithful deterministic checkpoint migration. Default reject. |

No faithful **general transactional checkpoint/replay migration** is implemented or claimed. Some literal values/IDs/known fields can be preserved without inventing rules; resumability still requires the entire closure.

## 6. Future two-phase identity-preserving restoration — not implemented

1. Parse a versioned data-only document in isolation, validate schema, source/rule/data/adapter compatibility, resource bounds and complete logical reference graph. Do not open an existing destination to partial mutation.
2. Allocate fresh native World/Library/Entities/Events/Actions/ChoiceBook/ledgers/recipient containers under their stable roles. Rebind all aliases/backreferences and restore data without calling Action resolvers, completion callbacks, samplers, policy or legacy planning commands.
3. Reconstruct reviewed native constraints, declaration signatures, locks, mode binding, RNG ownership, receipt seals/anchors and process issuance. Never reuse old addresses/tokens. Preserve accepted-unpublished members as unpublished; retain whole-choice and resource semantics.
4. Validate full semantic closure, including all historical constraints, prior Target states/effects/practice, current planning edits, full receipt chronology, RNG sharing and native method compatibility. No new realization or placeholder data is allowed.
5. Publish the completely validated graph as usable atomically or leave the destination unchanged. References already exposed inside the restored closure must remain the ones used by runtime/inspection. Restoring into an already exposed live graph needs an explicit destination identity/ownership protocol; it is not automatically authorized by isolated construction.

Do not use public transactional `step` to repair loaded state or recreate old consequences. `Universe.load_from_file` and existing transactional save/export refusals remain intact until this design is implemented and tested separately.

## 7. Deterministic continuation and replay acceptance gates

A future restored candidate must match its source checkpoint under logical references, then accept the same subsequent legal choices, timing, velocity/frame inputs and compatible RNG/rules. Compare every committed second: movement/time/frames, Action causal proposals and all defenses, Target negative HP/protection/fatal settlement, practice exercises/batch transitions/history constraints, shared facts/revisions, observer evidence/interpretation/Belief/testimony, lifecycle/queues/reservations/start samples, receipt coverage and RNG after-state. Include exception rollback, earlier-second preservation and controlled deterministic recovery with newly issued native process tokens.

Replay requires **additional chronological input history**, not only a checkpoint: accept/undo/replace/cancel decisions and packet versions, external motion/velocity inputs, stochastic owner context, policy decisions if used, and exact rule/version context. A printed trace or seed alone is insufficient. No replay recorder/executor is implemented here.

Authoritative checkpoint data are omniscient, separate from player/AI access. Neither checkpoints nor developer inventory may be wired into player endpoints or policies without a separately approved information-access contract.

## 8. Bounded next step

5D2A adds bounded recipes, field vocabulary and host bindings as detailed below. Before file save or active restore, complete the remaining semantic/alias/definition and receipt/signature reconstruction proofs. A proposed 5D2B should remain inactive and target these specific refusal reasons, with representative initial/accepted/committed closure examples and unknown-reference tests. Only after demonstrable closure should isolated rehydration/continuation be separately authorized. No next step is authorized by this draft.


## 9. 5D2A native adapter and binding extension

### Entry point and readiness

```python
from checkpoint_adapters import RecipientBinding
from checkpoint_inventory import capture_checkpoint_candidate, validate_checkpoint_candidate

bindings = (RecipientBinding(
    world, "campaign-host", "scout-notebook", "in_world_belief_ledger",
    (observer.id,), existing_ledger),)
candidate = capture_checkpoint_candidate(
    world, encounter, quiescent=True, rng_scope="exclusive_encounter",
    native_adapters=True, bindings=bindings)
validation = validate_checkpoint_candidate(world, encounter, candidate, quiescent=True)
```

This creates no world file, recipient, ID or restored native graph. The host supplies names and live bindings; the inventory copies only data. `native_adapters=False` retains 5D1 diagnostics. In native mode, `native-closure-recipes/1` and `host-bindings` are explicit envelope extension sections; the enclosing inventory remains `universe.checkpoint-inventory-draft/1`. This is an in-memory draft representation, not a file format version or a migration of old issued candidates. Source fingerprints invalidate older same-process inventories.

`inventory_validated` still means fresh structural/native-predicate coverage, not full validity for continuation. Unknown fields or invalid reviewed references throw; unknown unadapted value types produce explicit unsupported nodes and false inventory validation. `closure_validated=False`, `portable_schema_defined=False`, `restore_verified=False` and unconditional `require_complete()` refusal remain universal. Recognizing native callbacks does not make the entire graph resumable.

### Explicit durable recipient contract

A `RecipientBinding` is a frozen host declaration of `(world, namespace, name, role, observer_ids, existing recipient)`. The live World/recipient references remain capture inputs and private freshness dependencies; they never appear as Python handles in candidate data. The projected logical reference is `("host-recipient", world.id, namespace, name)`. Namespace/name are exact nonblank strings supplied by the host, not generated by the engine or derived from observer ID or traversal order. World IDs are scoped to one isolated bundle, as before.

Supported roles are `in_world_belief_ledger` (exact native `BeliefLedger`, exactly its one registered Being observer) and `in_world_received_accounts` (exact list, explicitly enumerated registered Being listeners). A shared account list has **one** binding listing its supported listeners; all Actions/receipt references point to that same node, and order is preserved. Two ledgers for one observer have distinct host names. Duplicate names, repeated physical recipients under separate names, foreign World roots, role/observer mismatches and sharing of internal mutable ledger collections refuse. A recipient cannot also be another recipient's internal collection. Internally shared immutable evidence references are retained; arbitrary mutable alias semantics are not certified.

A future host must supply the same scoped logical names/roles, observer mapping and alias topology, with an ownership protocol covering external writes. Reconstructing/restoring those containers or publishing into them is not implemented. These declarations do not discover hidden host references, verify names across independent processes or retroactively grant distributed ownership. Missing bindings for native Action or committed receipt recipients refuse. Explicitly bound recipients outside current Actions are also captured and validated, rather than dropped as unused.

### Native conditional-attribute recipe

Supported store type: exact `conditional_attributes.ConditionalAttributes`, owned by one exact registered `StatisticalGroup`. Closed fields are `specifications`, `_external` (names, **not external values**), `_committed`, and `_rng_for`. Scalar/container types are checked before native specification validation; unknown spec forms, dependency cycles, missing parent branches, unsupported value types and malformed committed member identities refuse. Native specification validation uses a detached `ConditionalAttributes(specifications, None, external_names)` solely to reuse its constructor checks; it never calls a provider, resolves an attribute or rehydrates world state.

The accepted provider is the exact native constructor lambda code, native module globals and single closure cell naming its owning group, with no substituted defaults/function attributes and unchanged native `_rng`/`composition_rng` references. No function body is invoked. The data recipe names `statistical_group.formation_attribute_rng` and its group reference. It means the existing native call `composition_rng(seed, group_id, "formation_attribute", member_id, attribute)`: pipe-joined native scalar tokens, UTF-8 SHA-256 first 16 bytes as a big-endian seed for Python Random. The source/runtime signature remains part of compatibility. No new token escaping, distribution, algorithm or random allocation order is introduced.

The complete group node retains seed/ID, frozen formation traits, current config, formation time, established household facts/revisions and commitments. A committed member must already have a supporting household record; no missing household is sampled. Committed internal conditional parents and outcomes are checked against their existing branch. Cached composition totals are checked using the existing pure native `_counts` calculation against established facts.

External formation traits remain a precise **semantic closure gap**. `_adult_formation_assignments` computes exact quota membership by keyed random priorities over the whole committed cohort; `_external` itself stores no outcomes. This increment captures the frozen trait data and reports `formation_trait_semantics_adapter_pending`; external-conditioned commitments also report `conditional_external_assignment_validation_pending`. It checks that outcomes are representable but does not claim the actual external branch is proven. It does not draw/reroll to validate a historical commitment, infer missing membership or invent a stored external fact. Nonempty materialized group-member extensions without reviewed native types remain unsupported.

### Constraint recipe table

| Recognized native owner/validator | Versioned data recipe and dependencies | Validation/refusal |
|---|---|---|
| Ownerless `RealityLedger` with empty validator tuple | `unconstrained-RealityLedger` | Native data records, exact keys, finite values, origin, revision chronology. Does not invent a domain constraint. |
| `PersonalHistory` with exact bound `PersonalHistory._validate` | `personal_history.validate_history_constraints`, Being reference, earliest/known-through bounds, nondeclining skills, ledger facts/revisions and complete prior `SkillUse`/`BatchSkillUse` | Reuses frozen-practice native capture/constraint predicates. Preserves Target-owned transitions, temporal comparisons and supporting episode/rank facts; does not interpolate or infer historical ranks. |
| Group composition ledger with exact bound `StatisticalGroup._validate_composition_facts` | `statistical_group.validate_composition_records`, group reference, formation time and ledger | Calls the existing extracted pure predicate on checked data; preserves committed fact keys/revisions and validates any derived count cache without realization. |
| Missing required owner constraint, wrong owner, custom method/function/subclass | None | Explicit refusal, without invoking the supplied validator. |

A future rehydrator must allocate/bind the native owner first and attach the reviewed native method by recipe/version. It must never evaluate a serialized function, revive old function addresses or call a generator to recover facts. Such rebinding is specified here, **not implemented**.

### Closed-field/reference scope and remaining proof obligations

`src/checkpoint_fields.py` is a fixed vocabulary for 115 exact native types. It was derived from constructors, declared dataclass fields, known external lifecycle writers and the original fixture field inventory, then corrected against actual committed native tests. It is not dynamically expanded from an inspected object's fields. Unknown fields refuse. Dataclass fields and unconditional constructor-written fields are required; conditional lifecycle fields remain optional. The table is also supplied as JSON evidence. Optional-field combinations, arbitrary dictionary definition semantics and all possible alias roles still need a complete proof, so a field-name match is never a completeness certificate.

Native mode retains registered world objects beyond Encounter participants and refuses dangling parent/equipment/possession IDs, containment cycles, shared live Entity state, shared owned group/history stores and ambiguous recipient topology. Safe native World/Encounter/Action backreferences remain reference edges. Mutable container cycles and unknown value types do not become complete candidates. Current accepted/future planning, prepared declarations, reservations, negative HP, multiple defenses, batch practice, Target histories and receipt chronology remain governed by existing native predicates and captured records. No Action HP-before/after representation is introduced.

The rule-source fingerprint now also includes conditional attributes, keyed group generation, personal history/experience and observer calculation modules. The broader implementation signature still covers all current Python source; neither hash detects all runtime monkeypatches or proves cross-version compatibility. Native providers/validators additionally receive exact method/code/owner checks.

Native mode requires an explicit private Cursor/Random scope assertion and refuses module/global or known shared authority. The caller must guarantee quiescence and external ownership; capture cannot prove privacy from a copied RNG state or arbitrary external aliases. All original faults/busy/reentrant/terminal/multi-Encounter restrictions remain. Receipt identity reissuance, declaration reconstruction, global field/alias semantics, final schema encoding and all restored continuation guarantees remain unresolved and block full readiness.

## 10. 5D2B bounded semantic-closure probe

5D2B tested a deliberately small but meaningful native transactional configuration: an Encounter with two committed boundaries, a Target-owned simultaneous `BatchSkillUse`, committed boundary receipts, and a separate accepted future choice. Capture and same-process freshness validation pass for this fixture. This is **not** semantic or portable closure. `closure_validated`, `portable_schema_defined`, and `restore_verified` remain false; `require_complete()` and all transactional serialization refusals remain in force.

The bounded probe exposes three independent closure blockers:

1. `ChoiceBook._Accepted.signatures` is based on `action_choice.declaration()`, whose opaque references fall back to `id(value)` and whose declaration type token uses `id(type(action))`. No reviewed data-only reconstruction rule currently establishes equivalent native signature revalidation in a fresh process.
2. Committed receipt records contain process-local Action/Target anchors and native issuance is tracked by `_COMMITTED_RECEIPTS`. No contract authorizes fresh receipt issuance/rebinding while preserving authenticity and chronology.
3. `NativeInventory.build()` still emits `semantic_closure_adapter_incomplete`. The current closed-field vocabulary does not prove semantic coverage of all declared dictionary definitions, optional-state combinations, and alias roles, even for the tested fixture.

These are observed implementation facts, not proposed rules. A later bounded design may define a native accepted-choice signature format and receipt reissuance protocol, but must first specify their trust/ownership boundaries and then supply complete field-level closure evidence for its declared configuration. It must not set readiness flags as a substitute for that proof. See `docs/universe4-increment5d2b-report.md` and the blocker matrix in `docs/universe4-increment5d2b-evidence/closure-blocker-matrix.md` for test/source evidence. No save, restore, replay, or continuation behavior is specified or enabled by this probe.

## 11. 5D2C1 portable accepted-choice descriptor

### Descriptor contract

The inactive adapter emits `universe.accepted-action-choice/1` as frozen `PortableAcceptedChoice` / `PortableActionDeclaration` records; `to_data()` projects them to a nested tuple tree containing only strings, integers, booleans, exact numeric tags, `None`, and tuples. It is not a file encoding and does not authorize restore. The ordered top-level fields are `(schema, choice_id, version, state, origin, action_ids, first_start, members, reservations)`. Each member carries its draft-local key, a stable adapter tag and logical Action ID, the complete ordered `action_choice.declaration()` input field set in portable form, optional cross-Action key, and its prepared schedule. Reservation rows preserve Action, Object logical ID, and exact start/boundary values.

Numbers retain type and precision: integers use decimal-string tags; finite floats use exact IEEE-754 `float.hex()` tags. Entity references use verified `("entity", id)` logical IDs; Universe and Encounter references use their role plus existing ID. No Python `id()`, type address, repr, pickle, callable, or live handle is emitted. The native Action adapter mapping is an exact-type allowlist, not a class-name lookup: `RunAction -> native.run-action/1` and `SpotAction -> native.spot-action/1`. It preserves accepted member order and fractional timing, checks the existing live signatures without serializing them, and validates the accepted prepared packets and reservation rows against their Action declarations.

The inventory substitutes this portable descriptor for `_Accepted.signatures` only when the adapter accepts that record. Unsupported choice families yield an explicit `portable_choice_descriptor_unsupported` diagnostic. The live `ChoiceBook` declaration/signature, revalidation, publication, and mutation guards are unchanged. Inventory readiness remains false.

### Supported subset and refusal boundary

Supported declarations are exact, pending native Run and Spot Actions in an accepted prepublication choice. Actor/target IDs must resolve uniquely to registered native Encounter entities. The current reviewed families have no active Object reservations; the descriptor records the reservation list and verifies exact agreement with prepared active-resource declarations, so an injected/missing/extra reservation refuses. Duplicate or ambiguous Action/entity IDs, stale signatures, reordered members, mismatched prepared timing, unknown fields/hooks, outcomes already written, custom subclasses, callback-bearing inquiry Actions, group-observation adapters, and combat/defense Actions are refused. These limits avoid treating native type names as proof of semantics or making new adapters for complex declarations.

### Required reconstruction and validation procedure

A future restore adapter must select the exact stable adapter tag under a compatible rules/source version; allocate native Universe, Encounter, entities and Actions; bind each logical reference uniquely; reconstruct only the whitelisted constructor inputs; rerun native validation/preparation under the owned scheduling lock; compare the newly derived portable declaration, ordered members, prepared timing, dependencies and reservations to the descriptor; and then compute fresh destination-process `action_choice.declaration()` signatures for the live ChoiceBook. It must not copy signatures from this descriptor or transplant signatures from another process. Whole-choice publication must still be atomic and preserve reservation ownership. This procedure is a contract only: no allocation, registration, save/load, restore, receipt issuance or replay has been added.

This descriptor removes the 5D2B accepted-signature portability blocker for the supported Run/Spot subset. It does not address process-local committed receipt issuance/anchors, the global definition/dictionary/alias semantic proof, unsupported Action families, or durable authenticated file schema. Therefore overall `closure_validated`, `portable_schema_defined`, and `restore_verified` remain false; all serialization and restoration refusals remain in force.
