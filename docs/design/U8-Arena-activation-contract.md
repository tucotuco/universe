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

This authority grants no Awareness, interpersonal intent, target information in
the activation record, perception, Action-prerequisite exception, or alternate
boundary protocol. Existing target-directed initiation remains Awareness-gated.
The initial implementation
supported a positioned actor's native target-free `RunAction`. The strictly
opt-in authored Draw scenario also uses this contract for a `ReadyWeaponAction`
that passes its full native prerequisite checks against the player's own
possessed Weapon. This does not relax ordinary Awareness or Action validation,
expose the target in the activation record, or grant Awareness; the Draw Choice
still identifies the exact native Weapon and must validate its custody,
drawable source-location evidence, and free hand.

## Supported first action

The generated browser accepts a one-second Run Action with an explicit zero
experience award, and the strictly opt-in authored Draw fixture accepts an
ordinary two-second Draw as the first player Choice. Native Run measures
displacement produced by Encounter movement; it does not move the Being. The
generated Arena has no authored
velocities or movement controller, so the supported proof is a committed
`no_movement` resolution at native time 1 with unchanged native position. The
browser displays that authoritative result and position. This does not imply
that future Run choices succeed or that generated Being geometry exists.

Spot remains unavailable for generated Beings because their geometry is not
modeled. No Spot target, opponent identity, Awareness, or native activation
record is returned in the player-facing projection. The browser adds no general
scheduler, movement policy, AI, or persistence.
