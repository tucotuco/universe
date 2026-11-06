"""Constrained autonomous opponent on the existing Universe Encounter engine.

The planner proposes a single command each second; it never calculates a hit,
changes hit points, or bypasses MeleeStrike/MeleeDefense and Encounter.
Optional model inference is observational, not authoritative. Replay injects the
recorded legal commands rather than contacting a model again.
"""
from __future__ import annotations

import json
import math
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from melee_combat import MeleeStrike
from melee_defense import MeleeDefense
from strategy import Strategy
from tactical_duel import TacticalDuel


SIZE_CATEGORY_REFERENCE_ARM_INCHES = {
    'D': 3.5, 'T': 7, 'S': 14, 'M': 28, 'L': 56,
    'H': 112, 'G': 224, 'C': 448,
}
INCHES_TO_METERS = 0.0254
METERS_TO_YARDS = 1 / 0.9144


def reference_arm_length_inches(*, height_inches=None, length_inches=None,
                                size_category=None):
    """Resolve the adopted physical arm-length estimate without geometry inference."""
    dimensions = []
    for value in (height_inches, length_inches):
        if value is None:
            continue
        if type(value) not in (int, float):
            raise ValueError('physical height and length must be finite nonnegative inches')
        try:
            value = float(value)
        except (OverflowError, ValueError) as exc:
            raise ValueError('physical height and length must be finite nonnegative inches') from exc
        if not math.isfinite(value) or value < 0:
            raise ValueError('physical height and length must be finite nonnegative inches')
        if value == 0:  # Native definitions use zero as their unset dimension sentinel.
            continue
        dimensions.append(value)
    if dimensions:
        return max(dimensions) * (15 / 37)
    if size_category not in SIZE_CATEGORY_REFERENCE_ARM_INCHES:
        raise ValueError('a known physical dimension or size category is required for Reach')
    return SIZE_CATEGORY_REFERENCE_ARM_INCHES[size_category]


class TacticalPolicy:
    """Deterministic, inspectable baseline; not a learned model."""

    def decide(self, observation):
        if not observation['opponent']['observed']:
            return {'command': 'wait', 'reason': 'No perceived opponent; hold position.'}
        if observation['self']['pending']:
            return {'command': 'wait', 'reason': 'Finish the current timed action.'}
        incoming = observation['opponent']['incoming']
        if incoming:
            remaining = incoming['seconds_until_impact']
            if remaining >= 2 and observation['time'] % 3 != 0:
                return {'command': 'dodge', 'reason': 'An observed incoming blow allows time for a dodge.'}
            if remaining >= observation['self']['parry_preparation']:
                return {'command': 'parry', 'reason': 'An observed blow allows time for a weapon parry.'}
        distance = observation['opponent']['distance']
        if distance is not None and distance > observation['reach'] * 0.88:
            dx, dy = observation['opponent']['bearing']
            direction = (('north' if dy > 0 else 'south') if abs(dy) > abs(dx)
                         else ('east' if dx > 0 else 'west'))
            return {'command': direction, 'reason': 'Close toward the perceived opponent.'}
        if observation['self']['hp_fraction'] < .45 and observation['time'] % 5 == 0:
            return {'command': 'guard', 'reason': 'Low health: favor a defensive stance.'}
        motion = 'thrust' if observation['time'] % 3 == 0 else 'swing'
        return {'command': motion, 'reason': 'Initiate an available weapon attack.'}


class OpenAIPolicy:
    """One constrained tactical proposal from an OpenAI Responses API model.

    Only an observer-limited tactical summary is sent. The model cannot issue
    tools or mutate the simulation. The engine validates every proposed action.
    """

    def __init__(self, model, *, api_key=None, timeout=12, transport=None):
        self.model = model
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError('OpenAI policy requires OPENAI_API_KEY')
        self.timeout = timeout
        self.transport = transport or self._post
        self.auth_failure = None

    def _post(self, payload):
        request = Request('https://api.openai.com/v1/responses',
                          data=json.dumps(payload).encode('utf-8'),
                          headers={'Authorization': 'Bearer ' + self.api_key,
                                   'Content-Type': 'application/json'}, method='POST')
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code == 401:
                # Never show the API key or server response body in the UI.
                self.auth_failure = ('OpenAI API authentication failed (HTTP 401). '
                                     'Check the API key and its project access; restart the server.')
                raise ValueError(self.auth_failure) from exc
            raise ValueError(f'OpenAI API request failed (HTTP {exc.code}); '
                             'verify model access and API configuration.') from exc

    def decide(self, observation):
        if self.auth_failure:
            raise ValueError(self.auth_failure)
        schema = {'type': 'object', 'additionalProperties': False,
                  'properties': {'command': {'type': 'string', 'enum': observation['legal']},
                                 'reason': {'type': 'string'},
                                 'effort': {'type': ['object', 'null'],
                                            'additionalProperties': False,
                                            'properties': {k: {'type': 'integer', 'minimum': 0}
                                                           for k in TacticalDuel.EFFORT_FIELDS},
                                            'required': list(TacticalDuel.EFFORT_FIELDS)}},
                  'required': ['command', 'reason', 'effort']}
        request = {
            'model': self.model,
            'instructions': (
                'You are the Raider in a turn-based one-second Universe armed duel. '
                'Use ONLY the provided observation, not hidden enemy statistics. '
                'You decide independently of the human. Choose one legal command. '
                'An attack is a timed swing or thrust resolved by the existing engine; '
                'parry/dodge interrupt your current action and are only valid against '
                'an observed incoming strike. Movement may continue during an attack. '
                'You may optionally allocate your weapon skill points to attack, defense, '
                'timing, and extra_damage; all allocations must be nonnegative and '
                'total at most your weapon_skill. Use null effort for the default. '
                'Defensive effort is chosen with the action; do not reassign it mid-action. '
                'Do not invent rules, change dice, or claim a hit. Provide a brief '
                'tactical reason using only perceived information.'),
            'input': json.dumps(observation, sort_keys=True),
            'text': {'format': {'type': 'json_schema', 'name': 'tactical_choice',
                                'strict': True, 'schema': schema}},
            'max_output_tokens': 180,
        }
        data = self.transport(request)
        for item in data.get('output', []):
            if item.get('type') == 'message':
                for part in item.get('content', []):
                    if part.get('type') == 'output_text':
                        return json.loads(part['text'])
        raise ValueError('No tactical choice in model response')


class AgentDuel(TacticalDuel):
    """Same player/UI and combat resolver, with an independently chosen foe action.

    The engine supports only the existing bounded armed duel. It is *not* an
    implementation of every action described in Encounters Working Draft.
    """
    FORMAT = 'universe.ai-encounter'

    def __init__(self, seed=17, *, policy=None, legacy_reach=False):
        # TacticalDuel.__init__ saves an initial frame through self.state().
        self.policy = policy if policy is not None else TacticalPolicy()
        self.legacy_reach = legacy_reach
        self.ai_decisions = []
        self._ai_proposal = None
        self._ai_last = None
        super().__init__(seed)

    def _reach_for(self, actor, weapon_id):
        """Return impact Reach in meters for comparison with Encounter positions."""
        self.encounter.assert_legacy_consumer()
        if self.legacy_reach:
            return self.REACH  # Verify pre-reach-fix saved battles without changing history.
        weapon = self.world.get_object_by_id(weapon_id)
        arm_inches = reference_arm_length_inches(
            height_inches=actor.original.height,
            length_inches=actor.original.length)
        # Being and weapon physical lengths are inches; Encounter coordinates
        # and center-to-center impact distances are meters.
        return (arm_inches + float(weapon.original.length)) * INCHES_TO_METERS

    def _visible_equipment(self, actor, weapon_id):
        self.encounter.assert_legacy_consumer()
        weapon = self.world.get_object_by_id(weapon_id)
        armor_id = actor.get_armor_id()
        armor = self.world.get_object_by_id(armor_id) if armor_id else None
        return {'weapon': weapon.original.obj_type,
                'armor': armor.original.obj_type if armor else 'None'}

    def _reaction_options(self, defender, attacker, weapon_id):
        """Explain whether target-specific reactions can be completed in time."""
        self.encounter.assert_legacy_consumer()
        incoming = self._pending(attacker)
        possible = isinstance(incoming, MeleeStrike) and incoming.target_id == defender.id
        if not possible:
            return {'parry': 'No observed incoming strike to parry.',
                    'dodge': 'No observed incoming strike to dodge.'}, ()
        remaining = incoming.end_time - self.encounter.time
        weapon = self.world.get_object_by_id(weapon_id)
        times = [t for t in (weapon.St(), weapon.Tt()) if t is not None]
        parry_time = max(1, min(times)-1) if times else 999
        needed = {'parry': parry_time, 'dodge': 2}
        reasons = {kind: (f'Ready: {remaining:g}s until impact, {prep:g}s to prepare.'
                          if remaining >= prep else
                          f'Too late: {remaining:g}s until impact; {prep:g}s required.')
                   for kind, prep in needed.items()}
        return reasons, tuple(kind for kind, prep in needed.items() if remaining >= prep)

    def observation(self):
        """Opponent-private own state plus what its current perception reveals."""
        self.encounter.assert_legacy_consumer()
        self._observe()
        visible = self._perceived[self.foe.id]
        source = self.foe.get_position()
        target = self.player.get_position()
        dx, dy = (target.x - source.x, target.y - source.y) if visible else (0, 0)
        pending = self._pending(self.foe)
        incoming = self._pending(self.player) if visible else None
        if not isinstance(incoming, MeleeStrike) or incoming.target_id != self.foe.id:
            incoming = None
        weapon = self.world.get_object_by_id(self.foe_weapon)
        times = [t for t in (weapon.St(), weapon.Tt()) if t is not None]
        parry_ready = max(1, min(times)-1) if times else 999
        remaining = incoming.end_time - self.encounter.time if incoming else None
        legal = ['wait', *self.DIRECTION, 'cancel', 'guard']
        if visible:
            legal += ['thrust', 'swing']
        if incoming is not None and remaining >= 2:
            legal += ['dodge']
        if incoming is not None and remaining >= parry_ready:
            legal += ['parry']
        return {'time': int(self.encounter.time), 'reach': self._reach_for(self.foe, self.foe_weapon),
                'self': {'hp_fraction': round(self.foe.get_hit_points() / self.foe.original.hit_points, 3),
                         'fatigue': self.foe.get_fatigue_level(),
                         'weapon': 'Longsword',
                         'weapon_skill': self.foe.get_weapon_skill_level('Longsword') or 0,
                         'pending': (None if pending is None else
                                     {'kind': pending.event_type, 'due': pending.end_time}),
                         'parry_preparation': parry_ready},
                'opponent': {'observed': visible,
                             'distance': round(math.hypot(dx, dy), 3) if visible else None,
                             'bearing': [round(dx, 4), round(dy, 4)] if visible else None,
                             'weapon': (self._visible_equipment(self.player, self.player_weapon)['weapon']
                                        if visible else None),
                             'armor': (self._visible_equipment(self.player, self.player_weapon)['armor']
                                       if visible else None),
                             'incoming': (None if incoming is None else
                                          {'apparent_motion': incoming.event_type,
                                           'seconds_until_impact': remaining})},
                'legal': legal}

    @staticmethod
    def validate(proposal, observation):
        if not isinstance(proposal, dict) or set(proposal) not in (
                {'command', 'reason'}, {'command', 'reason', 'effort'}):
            raise ValueError('AI choice needs command, reason, and optional effort')
        command, reason = proposal['command'], proposal['reason']
        if not isinstance(command, str) or command not in observation['legal']:
            raise ValueError('AI proposed an unavailable action')
        if not isinstance(reason, str) or len(reason) > 300:
            raise ValueError('AI reason must be a short string')
        effort = proposal.get('effort')
        if effort is not None:
            if command not in ('thrust', 'swing', 'guard', 'parry', 'dodge'):
                raise ValueError('AI effort assigned to incompatible command')
            if (not isinstance(effort, dict) or set(effort) != set(TacticalDuel.EFFORT_FIELDS)
                    or any(type(n) is not int or n < 0 for n in effort.values())
                    or sum(effort.values()) > observation['self']['weapon_skill']):
                raise ValueError('AI effort exceeds available weapon skill or is invalid')
            if command in ('guard', 'parry', 'dodge') and any(
                    effort[k] for k in ('attack', 'timing', 'extra_damage')):
                raise ValueError('Reactions and Guard accept defensive effort only')
        return {'command': command, 'reason': reason, 'effort': effort}

    def choose(self, command, effort=None, *, ai_choice=None):
        self.encounter.validate_progression_entry()
        # Validate player syntax first, before calling a (possibly paid) model.
        if command not in self.COMMANDS or self.ended():
            raise ValueError('Unknown command or finished combat')
        if effort is not None:
            if command not in ('thrust', 'swing', 'guard', 'parry', 'dodge'):
                raise ValueError('Effort not accepted for this command')
            self._effort_strategy(self.player, effort)
        obs = self.observation()
        fallback = None
        if ai_choice is None:
            try:
                proposal = self.validate(self.policy.decide(obs), obs)
            except (ValueError, KeyError, TypeError, OSError, TimeoutError) as exc:
                # A model outage cannot force an illegal action or change rules.
                fallback = str(exc)[:180]
                proposal = self.validate(TacticalPolicy().decide(obs), obs)
        else:
            proposal = self.validate(ai_choice, obs)
        self._ai_proposal = proposal
        try:
            result = super().choose(command, effort)
        finally:
            self._ai_proposal = None
        self.ai_decisions.append({'choice': proposal, 'fallback': fallback})
        self._ai_last = {'choice': proposal, 'fallback': fallback}
        # The inherited choose saves a frame before we append to ai_decisions.
        self._frames[-1] = self.state()
        self._audit_frames[-1] = self.state(audit=True)
        return self.state()

    def _foe_choice(self):
        self.encounter.assert_legacy_consumer()
        proposal = self._ai_proposal
        if proposal is None:
            return super()._foe_choice()
        command = proposal['command']
        movement = {}
        effort = proposal['effort']
        allocation = self._effort_strategy(self.foe, effort) if effort is not None else None
        if command in self.DIRECTION:
            dx, dy = self.DIRECTION[command]
            norm = math.hypot(dx, dy)
            movement[self.foe.id] = (dx * self.WALK_PER_SECOND / norm,
                                     dy * self.WALK_PER_SECOND / norm, 0)
        elif command in ('swing', 'thrust'):
            self._attack(self.foe, self.player, self.foe_weapon, command,
                         allocation or Strategy(attack=1))
        elif command == 'guard':
            self._interrupt(self.foe)
            self.foe.set_strategy(defense=(allocation.defense if allocation else
                                           min(1, self.foe.get_weapon_skill_level('Longsword') or 0)))
        elif command == 'cancel':
            self._interrupt(self.foe)
            self.foe.set_strategy()
        elif command in ('parry', 'dodge'):
            incoming = self._pending(self.player)
            if not isinstance(incoming, MeleeStrike):
                # Decisions are independent: the human may cancel the attack in
                # the same second. A reaction to that vanished threat expires.
                return {}, ('Raider prepared a ' + command +
                            ', but the apparent incoming attack was withdrawn.')
            reaction = MeleeDefense(self.encounter, self.foe.id, self.player.id,
                                    kind=command, target_action_id=incoming.id,
                                    weapon_id=self.foe_weapon if command == 'parry' else None)
            previous = self._pending(self.foe)
            self.encounter.schedule_action(reaction,
                interrupt_action_id=None if previous is None else previous.id)
            if allocation is not None:
                self.foe.set_strategy(defense=allocation.defense)
        text = 'Raider autonomously chooses ' + command + ': ' + proposal['reason']
        return movement, text

    def state(self, audit=False):
        self.encounter.assert_legacy_consumer()
        state = super().state(audit=audit)
        # Convert world-space meter values only at this developer/player view
        # boundary. Encounter state, geometry and comparisons remain metric.
        for participant_key in ('player', 'foe'):
            participant = state.get(participant_key)
            if participant is not None and isinstance(participant.get('position'), list):
                participant['position'] = [v * METERS_TO_YARDS
                                           for v in participant['position']]
                participant['position_unit'] = 'yard'
        if audit:
            display_history = []
            for original in state['history']:
                item = dict(original)
                if item.get('player_movement') is not None:
                    item['player_movement'] = [v * METERS_TO_YARDS
                                               for v in item['player_movement']]
                    item['movement_unit'] = 'yard/second'
                if item.get('foe_activity') is not None:
                    activity = dict(item['foe_activity'])
                    if activity.get('movement') is not None:
                        activity['movement'] = [v * METERS_TO_YARDS
                                                for v in activity['movement']]
                        activity['movement_unit'] = 'yard/second'
                    item['foe_activity'] = activity
                display_history.append(item)
            state['history'] = display_history
        state['spatial_presentation_unit'] = 'yard'
        decision = getattr(self, '_ai_last', None)
        # Offer the human exactly the same reaction readiness information
        # the autonomous opponent receives through its legal-action filter.
        visible = self._perceived[self.player.id]
        player_legal = ['wait', *self.DIRECTION, 'cancel', 'guard']
        if visible:
            player_legal.extend(('thrust', 'swing'))
            incoming = self._pending(self.foe)
            if isinstance(incoming, MeleeStrike) and incoming.target_id == self.player.id:
                remaining = incoming.end_time - self.encounter.time
                if remaining >= 2:
                    player_legal.append('dodge')
                weapon = self.world.get_object_by_id(self.player_weapon)
                times = [t for t in (weapon.St(), weapon.Tt()) if t is not None]
                if times and remaining >= max(1, min(times) - 1):
                    player_legal.append('parry')
        reasons, _ = self._reaction_options(self.player, self.foe, self.player_weapon)
        if not visible:
            reasons = {kind: 'Opponent is not currently perceived.' for kind in ('parry', 'dodge')}
        state['reaction_readiness'] = reasons
        state['player_legal'] = player_legal
        player_reach = self._reach_for(self.player, self.player_weapon)
        foe_reach = self._reach_for(self.foe, self.foe_weapon)
        state['reach_profile'] = 'legacy shared reach' if self.legacy_reach else 'weapon-specific reach'
        # The Encounter uses meters internally; developer/player presentation
        # reports spatial distances and Reach in yards.
        if self.legacy_reach:
            state['ranges'] = {'scout': round(player_reach, 4),
                               'raider': round(foe_reach, 4), 'unit': 'yard'}
        else:
            state['ranges'] = {'scout': round(player_reach * METERS_TO_YARDS, 4),
                               'raider': round(foe_reach * METERS_TO_YARDS, 4),
                               'unit': 'yard'}
            if state['range'] is not None:
                state['range']['distance'] = round(
                    state['range']['distance'] * METERS_TO_YARDS, 4)
                state['range']['reach'] = round(
                    state['range']['reach'] * METERS_TO_YARDS, 4)
                state['range']['unit'] = 'yard'
        if state['range'] is not None:
            distance = state['range']['distance']
            opponent_reach = (foe_reach if self.legacy_reach else
                              foe_reach * METERS_TO_YARDS)
            state['range']['opponent_reach'] = opponent_reach
            state['range']['opponent_in_range'] = distance <= opponent_reach
        if state['foe'] is not None:
            # Observable equipment, not a disclosure of hidden skill or HP.
            state['foe'].update(self._visible_equipment(self.foe, self.foe_weapon))
        state['player']['armor'] = self._visible_equipment(self.player, self.player_weapon)['armor']
        state['ai_mode'] = ('OpenAI model' if isinstance(getattr(self, 'policy', None), OpenAIPolicy)
                            else 'deterministic tactical baseline')
        state['ai_last'] = decision
        state['rules_coverage'] = 'bounded armed duel; see docs/ai-encounter-experiment.md'
        return state

    def to_session(self):
        """Replay actual AI action decisions, never request fresh model calls."""
        self.encounter.assert_legacy_consumer()
        self.encounter.assert_checkpoint_exportable(replay=True)
        replay = AgentDuel(self.seed, legacy_reach=self.legacy_reach)
        checks = []
        for choice, opponent in zip(self.commands, self.ai_decisions):
            command, effort = self._decode_command(choice)
            replay.choose(command, effort, ai_choice=opponent['choice'])
            checks.append(replay._journal_signature())
        if len(self.commands) != len(self.ai_decisions) or replay._journal_signature() != self._journal_signature():
            raise ValueError('Encounter diverges from replay')
        return json.loads(json.dumps({
            'format': self.FORMAT, 'version': 1 if self.legacy_reach else 2, 'seed': self.seed,
            'commands': self.commands, 'ai_decisions': self.ai_decisions,
            'checks': checks}))

    @classmethod
    def from_session(cls, payload, *, policy=None):
        if not isinstance(payload, dict) or set(payload) != {
                'format', 'version', 'seed', 'commands', 'ai_decisions', 'checks'}:
            raise ValueError('Invalid AI encounter session')
        if payload['format'] != cls.FORMAT or payload['version'] not in (1, 2) or type(payload['seed']) is not int:
            raise ValueError('Unsupported AI encounter save')
        commands, choices, checks = payload['commands'], payload['ai_decisions'], payload['checks']
        if (not all(isinstance(x, list) for x in (commands, choices, checks))
                or len(commands) != len(choices) or len(choices) != len(checks)
                or len(commands) > 100000):
            raise ValueError('Invalid AI encounter journal')
        duel = cls(payload['seed'], policy=policy, legacy_reach=payload['version'] == 1)
        for player_cmd, item, check in zip(commands, choices, checks):
            if (not isinstance(item, dict) or set(item) != {'choice', 'fallback'}
                    or not (item['fallback'] is None or isinstance(item['fallback'], str))):
                raise ValueError('Invalid AI decision record')
            command, effort = cls._decode_command(player_cmd)
            duel.choose(command, effort, ai_choice=item['choice'])
            if duel._journal_signature() != check:
                raise ValueError('Saved AI encounter does not replay to its recorded state')
            duel.ai_decisions[-1]['fallback'] = item['fallback']
            duel._ai_last['fallback'] = item['fallback']
            duel._frames[-1] = duel.state()
            duel._audit_frames[-1] = duel.state(audit=True)
        return duel
