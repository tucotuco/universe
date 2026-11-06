# Universe 8 Arena v1 — requirements baseline and unresolved decisions

**Status:** Requirements record for the proposed Universe 8 Arena v1. This document records the baseline supplied in U-ARENA-004A; it is not an Encounter rule amendment, a generator contract, or authorization to implement features. **Reviewed:** 2026-11-06.

## 1. Product boundary

Arena v1 is a local-browser interface over the native Universe simulation. A new session starts with no active Encounter and offers **Generate Encounter** or **Load Encounter**. Universe owns authoritative Being/Object state, identity, Action resolution, chronology, observation history, and continuation state after generation. The NPC Generator remains a separately maintained source pending the ownership decision recorded in the [U-ARENA-004A audit](../reports/U-ARENA-004A-report.md).

The browser is an operator/player interface, not a second simulation engine. Native Universe state and supported Encounter operations remain authoritative. A displayed grid, marker, name, movement arrow, or estimate is a presentation over that state and must not create competing simulation state. Arena v1 does not add victory conditions, sophisticated opponent tactics, terrain, global geography, synthetic perception noise, extra Beings, or multiplayer.

## 2. Adopted functional baseline

### 2.1 Startup and generated encounter

- The empty Arena offers **Generate Encounter** and **Load Encounter**.
- The Generate form has three required integer text inputs: common starting experience `>= 0`; initial map width `>= 5`; and initial map height `>= 5`. Width and height are measured in one-yard cells.
- Generate is enabled only while all three values are valid. Activation generates exactly two independent random NPC-Generator-scope Beings at the requested starting experience and starts Encounter elapsed time at 0. One Being is player-controlled; the other is Arena-controlled.
- The generated candidate data must become complete, legitimate native Universe Being/Object state without silently dropping source fields or inventing mechanics. Native Universe owns authoritative mutable state and history after generation.
- Existing `npcgen-npc` importers are bounded examples, not the complete Arena contract. Generator changes may be needed. The transfer must preserve the actual requested/generated experience and generated Objects.

### 2.2 Initial Objects and placement

- Place each Being and each distinct generated non-Being Object in a different randomly selected, initially unoccupied map cell. Each generated Object begins on the ground, unpossessed, and unequipped. Inspect and preserve the source’s ownership/containment semantics when extracting Objects.
- A cell is initially occupied only for this placement operation. This does not establish a game-wide collision or occupancy rule.
- When no cell is available, append one randomly selected cell sharing an edge with the existing footprint, then place the next Object. Repeat as necessary. The connected footprint may be irregular.
- The map is a presentation/placement coordinate frame. Native continuous Cartesian geometry, motion, and physical interactions remain authoritative. Placement randomness must be reproducible and preserved as required by continuation; it must not replace or silently consume simulation randomness.

### 2.3 Spatial and marker presentation

- Each displayed cell is a square yard. The cell display must make native facing geometry visually intelligible; it must not quantize native movement or assume that facing has only four directions.
- A Being is shown as a circle with a contrasting background and the first visible character of its current name. Another Object is shown as a triangle with a contrasting background and the first visible character of its current name.
- The user chooses an intended movement destination. A movement arrow is attached to the Being. Selecting the arrow shows destination, speed, and estimated arrival time when the native state supports those values.
- Clicking a visible Being or Object opens an information dialog, subject to the observer-information limits below.
- Encounter, Being, and non-Being Object names are editable, including in a loaded Encounter, with immediate marker-label updates. Names are ephemeral presentation metadata, not identity or required historical facts. Other properties change only through legitimate simulation mechanisms.

### 2.4 Observer view and information limits

- The player’s world view contains only Objects, Actions, and properties perceived by the controlled Being. For this stage, information is accurate objective information about properties that are perceptible under the circumstances; no synthetic noise is added.
- Do not expose unseen identity or inaccessible Reality through the map, popups, timelines, Action choices, generated metadata, or other interface surfaces.
- Initial perception/contact must have an explicit implementation source or be recorded as a design gap before it is used. Generation, placement, and source metadata alone grant no Awareness or Observation.
- Reality, observer-specific Observation, and Belief remain distinct. Native Encounter inspection can be developer/GM-omniscient only when clearly separated from the observer-facing view.

### 2.5 Actions, movement, and chronology

- Show Encounter name and elapsed seconds, plus both Beings’ current movement, Action, and expected Action resolution time.
- Offer player movement and Action choices, including required targets and parameters. Show the full known Action catalog: unimplemented Actions disabled and greyed; implemented but currently invalid Actions disabled and visually distinct; legal implemented Actions selectable. Native engine validation is authoritative.
- Reuse the existing second-by-second decision/advance interaction: native movement precedes Actions at each one-second boundary; simultaneous Actions use the common snapshot and commit together; history is not retroactively mutated.
- Both choices can be inspected. Advance one second at a time until a new choice is needed. Changing a choice at a decision/second cancels an in-progress Action under adopted cancellation semantics; it is not a whole-choice undo after execution has started. The audit identifies which prototype behavior exists only in legacy code and must not replace native resolution.

### 2.6 Arena-controlled opponent

- The Arena-controlled Being specifically opposes the player-controlled Being.
- Four initial strategy choices are supported: `random`, `attack only`, `defense only`, and `mixed attack and defense only`. Expansion to named, user-configured strategies is deferred.
- Strategy selection and persistence, and behavior when a strategy has no legal candidate Action, must be determined without inventing attack/defense eligibility or granting hidden knowledge.

### 2.7 Save and load

- Save is available at every stable UI decision/input point, including an initial Action-choice point, but never during an uncommitted transaction.
- The user chooses file name and location through normal OS-mediated local-browser file pickers.
- Load validates the selected file fully before replacing active Arena state. On invalid input show exactly `not a valid Encounter file` and leave the previous state unchanged. Loaded state comes wholly from the file; do not regenerate or fill defaults.
- A resumable save must close over all applicable Entities and stable IDs, native mutable state and histories, elapsed time, geometry, source records/provenance, observer evidence, accepted/active Actions and movement, scheduling/choice state, and deterministic RNG state. Stable checkpoints may include cancellable Actions, but not a partial transaction.
- Existing fixed S6/S7/S8 examples do not demonstrate generalized save/load. No save exists until Arena explicitly saves one. Checksums/digests alone are not receipt authentication.

## 3. Unresolved semantics and technical unknowns

The following are intentionally not decided by this requirements record:

1. **Object dialog versus perception:** whether an Object dialog must use only the controlled Being’s perceived properties, and which safe label/details an undiscovered or partly perceived Object can show.
2. **Renaming hidden entities:** how global direct name editing can coexist with not revealing an undiscovered Entity’s existence or identity. The UI may need distinct operator and player surfaces; no policy is selected here.
3. **Facing and square cells:** how native facing (including adopted hex-side/hex-point orientations) is drawn over square-yard presentation cells while movement remains continuous and unquantized.
4. **Opponent strategy:** when a strategy is chosen, whether it is session/save data or presentation preference, how it obtains legal candidates only from available knowledge, and what it does when none exist.
5. **Initial contact:** what native mechanism gives the controlled Being its initial perceptible world view; initial generated participants do not automatically become known.
6. **Generator contract and XP:** the NPC Generator currently owns random generation and uses per-character experience vectors. A stable contract must define how one integer starting-experience input is applied without conflating it with Universe earned/practice experience or fabricating class/level rules.
7. **Complete generated Objects:** source possessions include structured item strings, exchanges, and gold; no general native Object mapping is adopted. A typed export or explicit mapping/rejection contract is required before claiming complete transfer.
8. **Grid projection:** how initial random cell placement maps to native metric coordinates, geometry, multi-cell Objects, and initial exclusivity where native shape/size is unavailable must be explicit. The map must not become a competing collision model.
9. **Random stream ownership:** generation, initial placement, opponent choices, and simulation may need separate deterministic streams; stream boundaries, seeds, and persisted state require a contract.
10. **File picker/browser support:** browser APIs for native pickers have different compatibility and secure-context requirements. Choose supported browser scope and fallback behavior without claiming every browser can save to an arbitrary selected path.
11. **Native save closure:** the fixed Arena restore path is host-approved and tightly bound to one scenario. A general save requires an authoritative atomic load contract, provenance/receipt handling, active Action reconstruction, observer evidence closure, and deterministic continuation.

## 4. Authority and implementation constraints

The adopted Encounter package is revision 61, limited by revision 62 for physical units, reference arm/Reach/Throw matters and by revision 63 for authoritative spatial-coordinate precision. Use [`docs/encounters/README.md`](../encounters/README.md) for precedence. This Arena document does not alter those rules.

Implementations must use native Encounter Choice validation/admission, one-second progression, movement-before-Action snapshots, transactional publication, rollback, and supported Action resolvers. Legacy `TacticalDuel`/`AgentDuel` code and the NPC Generator are not alternative Universe authorities. Do not change unsupported source fields into native mechanics by inference. Keep the generator separately inspectable until a reviewed ownership/contract decision explicitly changes it.

The next implementation assignment is selected after review of the audit and confirmation of the generator-ownership recommendation and any blocking design decisions.
