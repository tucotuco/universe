# U-ARENA-004Q — Generated Arena movement slice

## Outcome

This increment delivered the native prerequisites supported by the current
rules and state model: reproducible initial hex facing, nearest-facing
turn-and-move selection, exact in-interval destination arrival, and an explicit
generated-Arena environment premise. The player browser view now shows only
the player's facing, its direction marker, and the Arena's unobstructed Plains
on Road premise. It also explains why movement is unavailable.

The requested playable destination interaction is blocked by a prerequisite
the assignment explicitly disallows inventing: BeingInstance and its current
native state have no posture field or other adopted representation of standing,
crouching, or lying. The r61 movement evaluator requires an explicit posture
because its rate depends on posture. Supplying standing in the Arena UI or
passing it as a favorable caller default would invent a Being fact. The
generated page therefore exposes no destination/rate/policy controls and does
not send movement intents. The native movement path remains fail-closed for
unknown posture. This report does not claim the first playable browser movement
slice is complete.

No adopted r61/r62/r63 rule documents, NPC Generator files, checkpoint schema,
or historical compatibility behavior were changed. U-ARENA-004P's explicit
refusal of activated Arena checkpoints remains intact.

## Implemented behavior

### Independent reproducible initial facing

src/arena_initialization.py derives a role-specific seed using the separate
initial-facing-v1 namespace and existing root seed plus npcgen engine
identity. A private random.Random instance selects one value in 0..11 for
each Being; NPC candidate selection, placement, module/global RNG, and Encounter
RNG are not consumed. ArenaParticipant retains the facing seed and selection
provenance. Only the player's facing enters GeneratedArenaSession.public_view;
the opponent's facing, ID, name, position, and Generator provenance remain
private. The generated canvas draws the player's committed hex-facing arrow.

### Turn, maintain, and exact native arrival

src/hex_facing.py adds nearest-heading selection from the continuous horizontal
destination vector. Exact midpoint ties choose the numerically smaller facing,
including the wraparound 11/0 tie choosing 0. A tolerance of 16 binary64 ULPs
in facing-step units handles computed exact boundaries. A supplied
MovementIntent.target_facing hint is accepted only if it equals this derived
nearest facing. Maintain-facing classification and its adopted non-forward
1 yd/s cap remain as before.

src/movement_intent.py now permits destinations reachable in the current
one-second rate. It computes the within-second arrival instant and keeps the
maximum legal velocity only until that instant. src/interval_staging.py splits
staged movement at arrival, publishes the exact authored Cartesian destination
there, and has no displacement for the rest of the interval. The native
Encounter still commits at the integer boundary, and Actions resolving there
observe the post-movement position and facing. Zero-distance decisions refuse
without movement; no hex snapping, acceleration, pathfinding, body geometry,
collision, or arrival inference was added.

### Generated-Arena environment and browser boundary

ArenaWorldPremise records the initial environment as Plains/Road with the
existing r61 terrain multiplier of 1.0, hampered multiplier 1.0, and the
adopted unobstructed premise. The player projection labels collision and
physical overlap as unadjudicated; a visually empty hex is not presented as
proof of clearance.

The existing Generate form remains exactly three inputs (XP, columns, rows).
The generated page continues to keep Load and Spot unavailable, and the first
target-free Run Choice remains an explicit player choice. It is not inserted by
a destination click. No movement-only activation bypass or extra Action
Choice protocol was introduced. No destination controls or HTTP destination
route were added while the legal movement rate is unknown.

## Interactive demo

From the repository root, in an environment that permits IPv4 loopback binding,
run: PYTHONDONTWRITEBYTECODE=1 .venv/bin/python examples/generated_arena_browser.py

Open http://127.0.0.1:8000/, generate an Arena with the default XP and map
dimensions, and inspect the player's facing arrow, exact position/hex
occupancy, and the Plains/Road/unobstructed premise. The page reports that
destination movement is unavailable because there is no native posture state.
The existing explicit Choose Run and Advance 1 second controls still
demonstrate target-free activation and native clock progression, but they do
not move the Being. Do not treat this as a playable destination demo.

I attempted to start the local HTTP server on loopback port 8765 for a browser
smoke test. The environment rejected the bind with
PermissionError: [Errno 1] Operation not permitted; no real browser smoke test
ran. Handler/HTML tests passed, but they are not reported as visual browser
verification.

## Verification

Commands ran with .venv/bin/python from the repository root unless a working
directory is shown. Times are wall-clock time results.

| Command | Result |
|---|---|
| time .venv/bin/python -m unittest discover -s tests -p 'test_movement_intent.py' -q | 17 passed; 3.382 s. Includes all 12 headings, 12 midpoint ties, wraparound, maintained non-forward cap, exact arrival, zero distance, rollback during an arriving movement, and co-resolving Action observation. |
| time .venv/bin/python -m unittest discover -s tests -p 'test_generated_arena_browser.py' -q | 9 passed; 2.509 s. Includes the allowlisted facing, explicit environment premise, and fail-closed posture reason. |
| time .venv/bin/python -m unittest discover -s tests -p 'test_arena_initialization.py' -q | 7 passed; 0.981 s. |
| time .venv/bin/python -m unittest discover -s tests -p 'test_arena_hex_map.py' -q | 4 passed; 0.196 s. |
| time .venv/bin/python -m unittest discover -s tests -p 'test_arena_target_free_activation.py' -q | 3 passed; 1.184 s. |
| time .venv/bin/python -m unittest discover -s tests -p 'test_action_evaluation.py' -q | 47 passed; 0.749 s. |
| time .venv/bin/python -m unittest discover -s tests -p 'test_atomic_publication.py' -q | 70 passed; 42.770 s. |
| time .venv/bin/python -m unittest discover -s tests -p 'test_checkpoint_adapters.py' -q | 47 total: 46 passed, 1 failure, 0 errors; 20.230 s. The remaining known U-ARENA-004P dangling-equipment diagnostic mismatch is described below. |
| time .venv/bin/python -m unittest discover -s tests -p 'test_checkpoint_identity_binding.py' -q | 11 passed; 10.771 s. |
| time .venv/bin/python -m unittest discover -s tests -p 'test_checkpoint_reconstruction.py' -q | 7 passed; 3.207 s. |
| time .venv/bin/python -m unittest discover -s tests -p 'test_reproduction_being_checkpoint.py' -q | 13 passed; 2.096 s. |
| From tests/: time PYTHONPATH=../src ../.venv/bin/python -m unittest test_encounter_frame -q | 4 passed; 0.126 s. Pyenv emitted a non-fatal shim rehash permission warning. |
| .venv/bin/python -m py_compile for all changed Python files | Passed. |
| git diff --check | Passed. |

The known checkpoint adapter failure is
test_dangling_equipment_and_possessions_refuse: its assertion expects
ValueError: dangling equipment, but the earlier native action-evaluation
preflight raises EvaluationIntegrityError: unknown transitive Object identity.
It is the same independent reference-validation diagnostic issue reported by
U-ARENA-004P. This increment left it unchanged. The full repository suite was
not run.

The 004Q browser movement prerequisite was tested directly: native code contains
no Being posture field and no other existing native posture contract. A
caller-supplied standing condition would bypass that missing authoritative
fact, so the Arena route remains unavailable. The environment's HTTP bind
restriction also prevented a visual browser smoke test.

## Commits, limits, and next slice

The implementation, tests, and active design update are in commit 768f410
(Add Arena facing and exact arrival foundations). This report is a separate
documentation commit. No push was made.

The smallest next implementation slice is to adopt and implement a native
posture state representation, including transactional publication, common
snapshot inclusion, and closed-checkpoint binding/reconstruction policy. Then
the generated Arena can author an explicit initial standing state and supply
posture from native committed state to the existing rate evaluator. After that,
add the browser destination/rate/facing-policy controls and prove repeated
one-second movement and revised destinations through the native transaction.
Keep collision/overlap visibly unadjudicated until authoritative geometry and
contact rules exist.
