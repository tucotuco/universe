# AI-directed encounter — human and autonomous opponent

**Status:** first bounded *armed duel* experiment, **not** full implementation
of `docs/Encounters Working Draft.pdf` (67 pages). The PDF is the authoritative
reference. This experiment identifies the implemented subset and deliberately
rejects or omits mechanics that are not implemented instead of improvising them.

## Why this experiment

The purpose is to separate **creative tactical choice** from **authoritative
resolution**. The human and AI each make choices; both use the same `Encounter`,
`MeleeStrike`, `MeleeDefense`, `Strategy`, `Exertion`, weapon/armor and skill
systems. AI is a planner, **not** a second combat engine. A proposal that falls
outside legal choices never reaches the resolver; model errors invoke a
clearly labeled deterministic fallback policy. The AI cannot write arbitrary
code, invent moves, change die results or directly change HP.

The action planners have independent information and initiative. The AI chooses
using a filtered observation of its own state and a perceived opponent **before
the current human command is applied**. Each second, the preselected AI plan
and the human command are submitted to the same encounter time step. An
incoming attack canceled in that same step causes a previously anticipated
reaction to expire. The human does not see the AI's upcoming choice; its reason
appears after the step. This is not a real-time simultaneous hidden-commitment
or multiplayer architecture.

## Running

From the Universe repository root:

```bash
python examples/ai_encounter.py --open
```

The default is a deterministic, inspectable tactical policy. To test an **actual
LLM-controlled opponent**, first provide an API key to the server process,
then opt in explicitly:

```bash
export OPENAI_API_KEY='your-key'   # Do not commit this or paste it into the UI
python examples/ai_encounter.py --ai openai --model gpt-4.1-mini --open
```

This makes a paid external request **for each player command**. Only a compact
observation (AI's own combat status, observed distance/bearing, observed
incoming attack, and legal commands) is sent, not the full world, the PDF, the
human's HP or skills, or any hidden opponent state. Keys remain server-side.
An invalid response or network outage falls back to a deterministic tactical
policy; the UI labels the fallback. Response generation is not deterministic;
**replaying recorded actions is**.

Use the same UI controls as `examples/live_combat.py`: thrust/swing, Guard,
attack-specific Parry/Dodge, eight directions of movement, Cancel, Wait,
strategy allocation, inspection, save and timeline review. The new AI card
shows its **completed** choice and explanation. `--audit` deliberately exposes
hidden details for testing; normal mode is observer-filtered.

Save in `workspace/ai-encounter.json` using the UI. Reopen with:

```bash
python examples/ai_encounter.py --load workspace/ai-encounter.json --open
python examples/ai_encounter.py --replay workspace/ai-encounter.json --open
```

Replay **never** makes an LLM request. It validates the recorded AI commands
and player actions by rerunning the authoritative resolver, matching the
journal's state fingerprints. The fingerprints detect accidental/tampered
state mismatches; they are not cryptographic authentication of a save.

## Combat rules coverage and known gaps

The PDF's page references below refer to the **printed page numbers** in its
contents, not PDF file page indices. `Supported` describes the established
implementation, not a claim of exhaustive rule-by-rule conformance.

| Draft section | Current coverage | Remaining work for full rules |
| --- | --- | --- |
| Encounters, spotting/hearing, surprise (pp. 6–8) | Partial: geometrical path/range awareness of the one foe | Full spotting, hearing, surprise, encounter distance modifiers |
| Rounds and simultaneous actions (pp. 8–9) | Partial: one-second time steps, timed event resolution, eligibility frozen for equal-time strikes | Six-second rounds and full simultaneous consequences of all impacts |
| Location and movement (pp. 9–11) | Partial: map, eight directions, movement during pending actions | Hex/vertical model, five movement rates, load/terrain/visibility penalties, collisions, facing |
| Attack rolls, critical damage, modifiers, reach, flank, engage (pp. 11–14) | Partial: inherited attack/critical resolver, explicit reach/path at impact | Full modifier table, physical reach by body and weapon, flank/behind/facing and engagement rules |
| Injury and healing (pp. 14–15) | Partial: hit points, armor durability, helplessness | Massive damage, subdual, complete recovery/healing and death rules |
| Strategy allocation (pp. 15–17) | Partial: bounded attack/defense/timing/damage points and adjustment of attack duration | Exact total pool across combat skill + weapon + ability modifiers; timing/extradamage-specific caps across all combat types |
| Combat types (pp. 15–23) | Armed melee with dagger and longsword **only** | Unarmed, archery, siege/catapults, throwing, mounted, aerial, aquatic |
| Physical/mental fatigue (pp. 23–25) | Partial: established combat Exertion and physical fatigue checks | Complete fatigue activity/rate/recovery rules; mental stress |
| Equipment (pp. 26–38) | Partial: instantiated dagger, longsword and leather armor, inherited weapon and armor resolution | Full weapon tables, sizes, shields, armor timing/donning and all equipment effects |
| Skills (pp. 44–49) | Partial: weapon skill, experience from attempts, selected defense/tumble XP | Full skill prerequisites, modifiers, special skills and progression interactions |
| Special attack actions (pp. 50–58) | **Strike** (swing or thrust) supported as bounded melee; Cancel and movement available | Charge, grapple, grab, disarm, feint, break weapon, trip, stun, ready/delay, multi-actions and remaining actions |
| Defense actions (p. 59) | Partial: attack-specific timed Parry/Dodge; Guard as a tactical stance | Block, deflect, disengage, yield; precise multi-attacker defense rules |

For this AI encounter, the shared `TacticalDuel` resolver now accepts a
weapon-specific reach provider. The scenario calculates reach as 3/8 of Being
height plus weapon length using the draft's values in feet, with one map unit
explicitly defined as one yard. Scout/dagger reach is about 1.14 yards;
Raider/longsword reach is about 1.89 yards, measured between actor reference
points. Full facing, engagement/disengagement rolls, and detailed anatomical
contact geometry are still missing, and a clear straight ray does not prove
that a complete swing arc is unobstructed. Thus even *armed melee* is
not yet fully faithful to the source. Resolving these discrepancies is a
**rules-engine** task, not an instruction-prompt task. Neither a more capable
LLM nor more elaborate narration can cure them.

## Experimental evaluation

Compare the deterministic tactical policy with the LLM policy while keeping
initial seed, character statistics and the legal rules interface unchanged.
Inspect decisions and recorded reasons; examine whether the AI can anticipate,
react, retreat, approach, distribute effort, and adapt without invalid moves.

A successful experiment demonstrates the boundary between AI agency and
rule-governed reality. It **does not** demonstrate full rules fidelity,
realistic tactical competence, or independent multi-agent continuous time.
Those claims require a comprehensive extracted rules specification and much
more extensive tests against worked examples in the draft.

## Regression and exploratory tests

```bash
python -m unittest discover tests -p 'test_ai_encounter.py' -v
bash run_tests.sh
```

The UI must be checked locally in a browser. The test suite exercises engine
integration, limited-visibility snapshots, illegal command fallback, live
HTTP endpoint and origin handling, reaction timing, strategy bounds, and
export/replay. Model transport is mocked in automated tests; actual network
integration requires a configured API key and may incur charges.

## Follow-up UI and authentication clarifications

- The Scout and Raider have **different** attack reaches, computed from the
  existing Being height and weapon lengths. Two dashed circles represent the
  independent ranges; reach is evaluated again at impact after movement.
- Parry and Dodge are **reactions to an identified incoming strike**, not
  automatically enabled when the Scout finishes attacking. Each button now
  explains whether an incoming attack exists and whether its remaining time
  permits preparation: dagger parry 3 seconds; dodge 2 seconds. Preparing a
  defense cancels an incompatible pending action. Advance time, move, or Guard
  if no reaction is currently legal. Proactive generic parry is *not* implemented.
- Effort is set only in the dialog for the action being initiated. Movement and
  waiting do not silently reassign effort during a pending timed action. An
  explicit newly chosen action may interrupt and replace it.
- Replay adds first/last, step, play/pause/stop (stop rewinds), and configurable
  real-seconds-per-simulation-second timing. It reads recorded frames and makes
  **no** new model requests.
- HTTP 401 from OpenAI means the server rejected API authentication. A real
  OpenAI API key with the required project authorization must be supplied to
  the local server process; a ChatGPT subscription does not substitute for an
  API key. Restart after correcting the environment. After a 401, this process
  no longer retries until restart; rule-bound tactical fallback remains active.

Old version-1 AI encounter sessions retain their original shared 2-unit
reach and are replayed under that legacy profile to preserve historical
outcomes. New encounters use weapon-specific reach and save as version 2.
A loaded legacy encounter continues using the legacy profile; start a new
encounter to use the corrected reach rules.
