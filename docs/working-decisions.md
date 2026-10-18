# Universe working decisions

This short record is maintained with the code; it should not require separate user upkeep.

## Current direction

- Complete a small Encounter-centered vertical slice before building a general Universe framework.
- Continuous 3D coordinates are authoritative. ISEA cells and local Encounter grids are derived overlays, not the physical space.
- An Encounter is initiated by awareness **and** a decision to act. Perception is directed and its result should retain its basis.
- Provisional Encounter environments may be generated independently of a planet's terrain. Their generated details should be retainable as constraints or evidence for eventual broader world generation; do not assume they are already consistent with an uninstantiated world.
- Terrain synthesis and consistency-preserving refinement are deferred, not discarded.
- Use skill definitions and existing Action/Event IDs. An Action's `required_skill` is a prerequisite, not proof that the skill was exercised.
- Being-instance skill-use records capture history and per-skill earned experience. The initial progression curve follows the Encounter draft's increasing cost by rank; its awards and future replacement with configurable policies remain explicit.
- Ordinary skills can be practiced from rank zero. Extraordinary skills need prior training. Non-progressive skills can be used and recorded, but not improved by progressive-rank practice.

## Next work

- Determine how resolved Actions declare **actual exercised skills**, success and difficulty, and an experience-award policy, without conflating them with action prerequisites.
- Model richer Event and Agent-relative Experience histories, then decide how experience relates to abilities, weapon-category transfer, learning and temporary capability modifiers.
- Eventually add context-constrained entity generation, scalable statistical groups and resolution-on-demand detail.
