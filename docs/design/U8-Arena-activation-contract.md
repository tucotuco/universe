# Universe 8 Arena activation contract

## Adopted rule

An unstarted generated Arena Encounter may activate its native Action timeline
when its first valid player Choice is accepted. The activation is an explicit
Arena occurrence, separate from target-directed `EncounterInitiation` and
`decide_to_act`. Its immutable record identifies the Encounter, actor, accepted
Choice, activation time, and kind (`first_player_choice`); it has no target.

The Choice is prepared without publishing a draft. Preparation must satisfy the
ordinary native Action contract. Activation, Choice acceptance, publication at
the time-zero start fence, and transactional mode selection occur under the
native publication lease and schedule lock. Rejected preparation changes no
activation, ChoiceBook, event-history, clock, or RNG state. A failure during
publication restores the captured native scheduling metadata before the lease
is released.

This authority grants no Awareness, interpersonal intent, target, perception,
Action-prerequisite exception, or alternate boundary protocol. Existing
target-directed initiation remains Awareness-gated. The initial implementation
is limited to a single positioned actor's native target-free `RunAction` on a
generated Arena Encounter.

## Supported first action

The generated browser accepts a one-second Run Action with an explicit zero
experience award. Native Run measures displacement produced by Encounter
movement; it does not move the Being. The generated Arena has no authored
velocities or movement controller, so the supported proof is a committed
`no_movement` resolution at native time 1 with unchanged native position. The
browser displays that authoritative result and position. This does not imply
that future Run choices succeed or that generated Being geometry exists.

Spot remains unavailable for generated Beings because their geometry is not
modeled. No Spot target, opponent identity, Awareness, or native activation
record is returned in the player-facing projection. The browser slice supports
one first Run Choice and one native second only; it adds no general scheduler,
movement policy, AI, or persistence.
