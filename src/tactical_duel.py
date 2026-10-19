"""Player-directed Encounter with observer-filtered state and reproducible sessions.

All combat state belongs to Universe entities, events, skills and Exertion.
The session document is a replayable, verified command journal, not a generic
pickle/object dump. This first format is scoped to the seeded duel scenario.
"""

import hashlib
import json
import math
import random
from pathlib import Path

from exertion import Exertion
from melee_combat import MeleeStrike
from perception import GeometricPathPerception
from strategy import Strategy
from spatial.geometry import Sphere


class TacticalDuel:
    DIRECTION = {
        'north': (0, 1), 'northeast': (1, 1), 'east': (1, 0),
        'southeast': (1, -1), 'south': (0, -1), 'southwest': (-1, -1),
        'west': (-1, 0), 'northwest': (-1, 1),
    }
    COMMANDS = ('thrust', 'swing', 'guard', 'cancel', *DIRECTION, 'wait')
    WALK_PER_SECOND = .25
    SENSE_DISTANCE = 3.0
    REACH = 2.0
    SESSION_VERSION = 2
    EFFORT_FIELDS = ('attack', 'defense', 'timing', 'extra_damage')

    def __init__(self, seed=17):
        import sys
        examples = str(Path(__file__).resolve().parents[1] / 'examples')
        if examples not in sys.path:
            sys.path.insert(0, examples)
        from armed_duel import make_duel
        external_rng = random.getstate()
        try:
            random.seed(seed)
            self.seed = seed
            self.world, self.encounter, self.player, self.foe, self.armor_id, strikes = make_duel(
                schedule_attacks=False)
            encounter_rng = random.getstate()
        finally:
            random.setstate(external_rng)
        self.player_weapon = strikes[0].instrument_id
        self.foe_weapon = strikes[1].instrument_id
        self.encounter.end_time = None
        self.perception = GeometricPathPerception(self.SENSE_DISTANCE)
        self.player.set_geometry(Sphere(.2))
        self.foe.set_geometry(Sphere(.2))
        self.encounter.clear_awareness(self.player.id, self.foe.id)
        self.encounter.clear_awareness(self.foe.id, self.player.id)
        self._perceived = {self.player.id: False, self.foe.id: False}
        # Existing Exertion defines combat cadence by activity/load; both
        # Beings retain the fatigue values, not a parallel UI-only meter.
        for being in (self.player, self.foe):
            being.exertion = Exertion(start_time=0, activity_level='combat',
                                     fatigue_level=being.get_fatigue_level(),
                                     load_level='light')
        # Each duel owns its random sequence. Other worlds or save verification
        # must not consume its future outcomes through Python's global RNG.
        self._rng_state = encounter_rng
        self.history = []
        self.commands = []
        self._frames = []
        self._audit_frames = []
        self._observe()
        self._save_frame()

    def _observe(self):
        for observer, other in ((self.player, self.foe), (self.foe, self.player)):
            self.encounter.clear_awareness(observer.id, other.id)
            observed = self.encounter.perceive(observer.id, self.perception)
            self._perceived[observer.id] = any(o.target_id == other.id for o in observed)

    def _pending(self, being):
        for action_id in self.encounter.pending_action_list:
            action = self.world.get_event_by_id(action_id)
            if action.actor_id == being.id:
                return action
        return None

    def _interrupt(self, actor):
        pending = self._pending(actor)
        if pending is None:
            return None
        self.encounter.cancel_action(pending.id)
        return pending

    def _effort_strategy(self, actor, effort):
        """Allocate a bounded pool of actual weapon-skill points to a strategy.

        A strategy applies to the new attack; the Being's defense allocation
        remains available to incoming blows. It is never a free bonus pool.
        """
        if not isinstance(effort, dict) or set(effort) != set(self.EFFORT_FIELDS):
            raise ValueError('Effort requires attack, defense, timing and extra_damage')
        if any(type(effort[key]) is not int or effort[key] < 0
               for key in self.EFFORT_FIELDS):
            raise ValueError('Effort allocations must be non-negative integers')
        weapon = 'Dagger' if actor is self.player else 'Longsword'
        budget = actor.get_weapon_skill_level(weapon) or 0
        if sum(effort.values()) > budget:
            raise ValueError(f'Effort exceeds {weapon} skill pool ({budget})')
        return Strategy(**effort)

    def _attack(self, actor, target, weapon_id, motion, strategy=None):
        # Preflight *before* abandoning an already scheduled action. Rejected
        # replacement leaves both world time and original pending action intact.
        strike = MeleeStrike(self.encounter, actor.id, target.id, weapon_id,
                             motion=motion, reach=self.REACH, strategy=strategy)
        strike.on_schedule(self.encounter)
        interrupted = self._interrupt(actor)
        self.encounter.schedule_action(strike)
        if strategy is not None:
            actor.set_strategy(strategy.attack, strategy.defense,
                               strategy.timing, strategy.extra_damage)
        return strike, interrupted

    def _foe_choice(self):
        if self._pending(self.foe) or self.foe.is_helpless():
            return {}, 'Raider continues or cannot act.'
        if not self._perceived[self.foe.id]:
            return {}, 'Raider has not detected the Scout.'
        status, _ = MeleeStrike(self.encounter, self.foe.id, self.player.id,
                                self.foe_weapon, motion='swing', reach=self.REACH)._status(self.encounter)
        if status == 'in_reach':
            self._attack(self.foe, self.player, self.foe_weapon, 'swing')
            return {}, 'Raider initiates a longsword swing.'
        src, dst = self.foe.get_position(), self.player.get_position()
        dx, dy = dst.x - src.x, dst.y - src.y
        norm = math.hypot(dx, dy)
        if norm <= 0:
            return {}, 'Raider holds position.'
        return {self.foe.id: (self.WALK_PER_SECOND * dx / norm,
                               self.WALK_PER_SECOND * dy / norm, 0)}, 'Raider closes distance.'

    def ended(self):
        return self.player.is_helpless() or self.foe.is_helpless()

    def _fatigue_tick(self, start, end):
        """Perform due Exertion checks after combat effects for this second.

        Failure increases fatigue one level (capped by Being). Timed combat
        exertion continues while guarding or preparing an attack; resting,
        recovery, load and multi-activity changes are future extensions.
        """
        events = []
        for being in (self.player, self.foe):
            tracker = being.exertion
            while end >= tracker.get_end_time() and tracker.get_end_time() > start - 1e-9:
                due = tracker.get_end_time()
                if being.get_hit_points() <= 0 or being.get_fatigue_level() >= 5:
                    break
                ok = tracker.check(being.CON())
                before = being.get_fatigue_level()
                if not ok:
                    being.add_fatigue_level(1)
                tracker.set_fatigue_level(being.get_fatigue_level())
                tracker.set_start_time(due)
                tracker.set_end_time(due + tracker.get_check_period())
                events.append({'actor': being.id, 'time': due,
                               'success': ok, 'before': before,
                               'after': being.get_fatigue_level()})
        return events

    def choose(self, command, effort=None):
        # Legacy dice code uses the module RNG. Scope it to this Encounter so
        # simultaneously active worlds and save replays cannot alter its fate.
        outside = random.getstate()
        random.setstate(self._rng_state)
        try:
            return self._choose_one(command, effort)
        finally:
            self._rng_state = random.getstate()
            random.setstate(outside)

    def _choose_one(self, command, effort=None):
        if command not in self.COMMANDS:
            raise ValueError('Unknown tactical command.')
        if self.ended():
            raise ValueError('Combat has ended.')
        if effort is not None and command not in ('thrust', 'swing', 'guard'):
            raise ValueError('Effort may be allocated only for attacks and Guard')
        strategy = self._effort_strategy(self.player, effort) if effort is not None else None
        if command == 'guard' and strategy is not None and (
                strategy.attack or strategy.timing or strategy.extra_damage):
            raise ValueError('Guard currently accepts only defensive effort')
        self._observe()
        velocities = {}
        interrupted = None
        description = ''
        if command in ('thrust', 'swing'):
            _, interrupted = self._attack(self.player, self.foe, self.player_weapon, command,
                                          strategy=strategy or Strategy(attack=1))
            # The default attack keeps its established one-point offensive stance.
            # An explicit allocation is checked against the available skill pool.
            description = f'Scout begins a dagger {command}.'
        elif command == 'guard':
            interrupted = self._interrupt(self.player)
            defense = strategy.defense if strategy is not None else 2
            self.player.set_strategy(defense=defense)
            description = f'Scout adopts a defensive stance ({defense} effort).'

        elif command == 'cancel':
            interrupted = self._interrupt(self.player)
            description = 'Scout abandons unfinished action.' if interrupted else 'Scout has no pending action.'
        elif command in self.DIRECTION:
            dx, dy = self.DIRECTION[command]
            scale = self.WALK_PER_SECOND / math.hypot(dx, dy)
            velocities[self.player.id] = (dx * scale, dy * scale, 0)
            description = f'Scout steps {command}.'
        else:
            description = 'Scout waits one second.'
        if interrupted is not None:
            description = f'Scout interrupts a {interrupted.event_type}. ' + description
        foe_velocities, foe_decision = self._foe_choice()
        velocities.update(foe_velocities)
        step = self.encounter.step(1, velocities=velocities)
        fatigue_events = self._fatigue_tick(step.start_time, step.end_time)
        self._observe()
        foe_cue = None
        if self._perceived[self.player.id]:
            foe_pending = self._pending(self.foe)
            if self.foe.id in foe_velocities:
                foe_cue = ('Raider appears to move while preparing a strike.'
                           if foe_pending else 'Raider appears to move.')
            elif foe_pending:
                # Coarse gesture cue conditional on proximity/path; not an
                # infallible recognition of intent (or of a future feint).
                foe_cue = ('Raider seems to prepare a sweeping strike.'
                           if foe_pending.event_type == 'swing' else
                           'Raider seems to prepare a thrust.')
            elif self.foe.get_hit_points() <= 0:
                foe_cue = 'Raider appears to fall.'
            else:
                foe_cue = 'Raider appears stationary.'
        results = []
        for action_id in step.completed_action_ids:
            strike = self.world.get_event_by_id(action_id)
            result = getattr(strike, 'combat_result', None)
            if result is None:
                continue
            xp = sum(ex.experience for ex in strike.resolution.skill_exercises)
            attacker = 'Scout' if result.actor_id == self.player.id else 'Raider'
            target = 'Raider' if result.target_id == self.foe.id else 'Scout'
            hp_loss = max(0, result.target_hp_before - result.target_hp_after)
            self_loss = max(0, result.actor_hp_before - result.actor_hp_after)
            details = [f'{target}: {hp_loss:g} HP damage ({result.target_hp_before:g}→{result.target_hp_after:g})'] if hp_loss else []
            if result.target_armor_damage:
                details.append(f'{target} armor: {result.target_armor_damage:g} durability lost')
            if self_loss:
                details.append(f'{attacker}: {self_loss:g} self-damage')
            details.append(f'+{xp} weapon XP')
            landed = result.outcome in ('normal', 'critical', 'fatal')
            callout = 'HIT! ' if landed else ''
            # The actor is told exact damage they inflicted as a combat-game
            # convention; hidden opponent current/max HP remain undisclosed.
            if result.actor_id == self.player.id:
                # In this combat ruleset the actor knows the numeric damage
                # inflicted by their own successful strike. Total opponent HP
                # remains private; only a broad severity estimate is shown.
                if hp_loss:
                    fraction = hp_loss / max(1, self.foe.original.hit_points)
                    severity = ('light' if fraction < .2 else
                                'substantial' if fraction < .5 else 'severe')
                    player_details = f'{hp_loss:g} HP dealt to {target} ({severity} relative to estimated endurance)'
                else:
                    player_details = '0 HP dealt'
                if result.target_armor_damage:
                    player_details += f'; {result.target_armor_damage:g} armor durability damage'
                player_text = f'{callout}Scout {result.motion}: {result.outcome} — {player_details}; +{xp} weapon XP'
            else:
                player_details = []
                if hp_loss:
                    player_details.append(f'you lose {hp_loss:g} HP ({result.target_hp_before:g}→{result.target_hp_after:g})')
                if result.target_armor_damage:
                    player_details.append(f'your armor loses {result.target_armor_damage:g} durability')
                if not player_details:
                    player_details.append('no recorded injury')
                player_text = f'{callout}Incoming {result.motion}: {result.outcome} — ' + '; '.join(player_details)
            results.append({'actor': result.actor_id, 'target': result.target_id,
                            'text': f'{callout}{attacker} {result.motion}: {result.outcome} — ' + '; '.join(details),
                            'player_text': player_text,
                            'outcome': result.outcome, 'xp': xp, 'damage': hp_loss, 'hit': landed})
        foe_pending_now = self._pending(self.foe)
        foe_activity = {'decision': foe_decision,
                        'movement': list(foe_velocities[self.foe.id])
                                    if self.foe.id in foe_velocities else None,
                        'pending': (None if foe_pending_now is None else
                                    {'motion': foe_pending_now.event_type,
                                     'due': foe_pending_now.end_time}),
                        'completed': [r['outcome'] for r in results
                                      if r['actor'] == self.foe.id]}
        self.history.append({'time': step.end_time, 'player_choice': description,
                             'foe_activity': foe_activity,
                             'foe_choice': foe_decision, 'foe_cue': foe_cue,
                             'foe_observed': self._perceived[self.player.id],
                             'player_moved': command in self.DIRECTION,
                             'foe_moved': self.foe.id in foe_velocities,
                             'results': results, 'fatigue_events': fatigue_events})
        self.commands.append(command if effort is None else {'command': command, 'effort': dict(effort)})
        self._save_frame()
        return self.state()

    def state(self, audit=False):
        """Observer-filtered state: never send undiscovered foe objective data."""
        player = self.player
        enemy_visible = self._perceived[player.id]

        def being_state(being):
            pos = being.get_position()
            weapon = 'Dagger' if being is self.player else 'Longsword'
            pending = self._pending(being)
            tracker = being.exertion
            armor = self.world.get_object_by_id(being.get_armor_id())
            return {'id': being.id, 'name': being.name,
                    'position': [pos.x, pos.y, pos.z],
                    'hp': being.get_hit_points(), 'hp_max': being.original.hit_points,
                    'weapon': weapon,
                    'weapon_skill': being.get_weapon_skill_level(weapon) or 0,
                    'xp': being.get_skill_experience(weapon),
                    'fatigue': being.get_fatigue_level(),
                    'fatigue_state': tracker.fatigue_levels[being.get_fatigue_level()]['state'],
                    'fatigue_next_check': tracker.get_end_time(),
                    'armor_hp': armor.hit_points() if armor else None,
                    'strategy': {'attack': being.strategy.attack,
                                 'defense': being.strategy.defense,
                                 'timing': being.strategy.timing,
                                 'extra_damage': being.strategy.extra_damage},
                    'pending': None if pending is None else
                               {'motion': pending.event_type, 'due': pending.end_time}}

        player_data = being_state(player)
        # Distance and line clearance are disclosed only when the foe is
        # currently detected. Range is evaluated both at attack start and
        # again at its scheduled completion (after intervening movement).
        reach_status, measured_distance = (MeleeStrike(
            self.encounter, player.id, self.foe.id, self.player_weapon,
            motion='thrust', reach=self.REACH)._status(self.encounter)
            if enemy_visible else (None, None))
        foe_data = being_state(self.foe) if audit else (
            {'name': self.foe.name,
             'position': list(self.foe.get_position().as_tuple()),
             'present': True, 'hp': None, 'weapon': None, 'xp': None,
             'apparent_action': self.history[-1].get('foe_cue') if self.history else 'Raider detected'}
            if enemy_visible else None)
        if not audit and foe_data is not None:
            foe_data['bearing_basis'] = 'current unobstructed geometric path'
        log = []
        for item in self.history:
            if audit:
                log.append(item)
            else:
                event = {'time': item['time'], 'player_choice': item['player_choice'],
                         'foe_cue': item.get('foe_cue') if item['foe_observed'] else None,
                         'player_moved': item.get('player_moved', False),
                         'foe_moved': item.get('foe_moved', False) and item['foe_observed'],
                         'results': [r.get('player_text', r['text']) for r in item['results']
                                     if r['actor'] == player.id or item['foe_observed']
                                     or (r.get('target') == player.id and r.get('damage', 0) > 0)]}
                # One's own exertion results are observable, not enemy checks.
                for f in item.get('fatigue_events', []):
                    if f['actor'] == player.id:
                        event['results'].append('Scout fatigue check: ' +
                                                ('passed' if f['success'] else
                                                 f"failed; fatigue {f['before']}→{f['after']}"))
                log.append(event)
        latest = self.history[-1] if self.history else None
        move_arrows = {'north': '↑', 'northeast': '↗', 'east': '→',
                       'southeast': '↘', 'south': '↓', 'southwest': '↙',
                       'west': '←', 'northwest': '↖'}
        player_arrow = ''
        if latest and latest.get('player_moved'):
            command = self.commands[-1] if self.commands else None
            if isinstance(command, dict):
                command = command['command']
            player_arrow = move_arrows.get(command, '➜')
        foe_arrow = '➜' if latest and latest.get('foe_moved') else ''
        player_just_struck = bool(latest and any(
            r['actor'] == self.player.id for r in latest['results']))
        foe_just_struck = bool(latest and any(
            r['actor'] == self.foe.id for r in latest['results']))
        player_symbol = ('⚔' if player_data['pending'] else
                         '▣' if player.strategy.defense > 0 else '') + player_arrow or '•'
        foe_symbol = (('⚔' if self._pending(self.foe) else '') + foe_arrow or '•') if enemy_visible else None
        return {'time': self.encounter.time, 'seed': self.seed,
                'player': player_data, 'foe': foe_data, 'observed_now': enemy_visible,
                'player_symbol': player_symbol, 'foe_symbol': foe_symbol,
                'game_over': self.ended(), 'history': log,
                'range': {'distance': measured_distance, 'reach': self.REACH,
                          'status': reach_status,
                          'in_range': reach_status == 'in_reach'} if enemy_visible else None,
                'effort_pool': player.get_weapon_skill_level('Dagger') or 0,
                'player_cues': {'attack': '⚔' if player_data['pending'] else ('✦' if player_just_struck else ''),
                                'guard': '▣' if player.strategy.defense else '',
                                'movement': player_arrow},
                'foe_cues': ({'attack': '⚔' if self._pending(self.foe) else ('✦' if foe_just_struck else ''),
                              'movement': foe_arrow} if enemy_visible else None),
                'perception_model': ('GeometricPathPerception: path and range only; '
                                     'apparent action is provisional proximity cue'),
                'commands': list(self.COMMANDS), 'audit': audit}

    def _save_frame(self):
        self._frames.append(self.state())
        self._audit_frames.append(self.state(audit=True))

    def timeline(self, *, audit=False):
        """Immutable snapshot-like observer views for browser replay."""
        return json.loads(json.dumps(self._audit_frames if audit else self._frames))

    def _signature(self):
        """Stable semantic fingerprint: IDs are intentionally not compared."""
        def being(b):
            pos = b.get_position()
            pending = self._pending(b)
            weapon = 'Dagger' if b is self.player else 'Longsword'
            return {'position': [pos.x, pos.y, pos.z],
                    'hp': b.get_hit_points(), 'fatigue': b.get_fatigue_level(),
                    'skill': b.get_weapon_skill_level(weapon),
                    'xp': b.get_skill_experience(weapon),
                    'pending': (None if pending is None else
                                [pending.event_type, pending.end_time]),
                    'strategy': [b.strategy.attack, b.strategy.defense]}
        data = {'time': self.encounter.time, 'scout': being(self.player),
                'raider': being(self.foe),
                'armor': self.world.get_object_by_id(self.armor_id).hit_points(),
                'outcomes': [[r['outcome'], r['damage'], r['xp']]
                             for h in self.history for r in h['results']],
                'cancelled': len(self.encounter.cancelled_action_list)}
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def _journal_signature(self):
        # Version 2 fingerprint also includes allocated effort and both plans.
        detail = []
        for being in (self.player, self.foe):
            strategy = being.strategy
            pending = self._pending(being)
            detail.append({'effort': [strategy.attack, strategy.defense,
                                      strategy.timing, strategy.extra_damage],
                           'pending_effort': (None if pending is None else [
                               pending.strategy.attack, pending.strategy.defense,
                               pending.strategy.timing, pending.strategy.extra_damage])})
        payload = json.dumps([self._signature(), detail,
                              hashlib.sha256(repr(self._rng_state).encode()).hexdigest()],
                             sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_session(self):
        """Versioned seed + commands + fingerprints for checked reconstruction."""
        # Replaying a save must not perturb the active encounter's RNG stream.
        rng_state = random.getstate()
        try:
            fresh = TacticalDuel(self.seed)
            checks = []
            foe_decisions = []
            foe_actions = []
            for item in self.commands:
                command, effort = self._decode_command(item)
                fresh.choose(command, effort)
                checks.append(fresh._journal_signature())
                foe_decisions.append(fresh.history[-1]['foe_choice'])
                foe_actions.append(fresh.history[-1]['foe_activity'])

            if fresh._journal_signature() != self._journal_signature():
                raise ValueError('Current encounter diverges from its command history; cannot save safely')
            return {'format': 'universe.tactical-duel', 'version': self.SESSION_VERSION,
                    'seed': self.seed, 'commands': list(self.commands), 'checks': checks,
                    'foe_decisions': foe_decisions, 'foe_actions': foe_actions}
        finally:
            random.setstate(rng_state)

    @classmethod
    def _decode_command(cls, item):
        if isinstance(item, str) and item in cls.COMMANDS:
            return item, None
        if isinstance(item, dict) and set(item) == {'command', 'effort'}:
            command = item['command']
            if isinstance(command, str) and command in ('thrust', 'swing', 'guard'):
                return command, item['effort']
        raise ValueError('Invalid session command')

    @classmethod
    def from_session(cls, payload):
        if not isinstance(payload, dict):
            raise ValueError('Invalid session structure')
        version = payload.get('version')
        expected = {'format', 'version', 'seed', 'commands', 'checks'}
        if version == cls.SESSION_VERSION:
            expected.update(('foe_decisions', 'foe_actions'))
        if not {'format', 'version', 'seed', 'commands', 'checks'} <= set(payload):
            raise ValueError('Invalid session structure')
        if payload['format'] != 'universe.tactical-duel' or version not in (1, cls.SESSION_VERSION):
            raise ValueError('Unsupported session format/version')
        if set(payload) != expected:
            raise ValueError('Invalid session structure')
        if type(payload['seed']) is not int:
            raise ValueError('Session seed must be an integer')
        commands, checks = payload['commands'], payload['checks']
        if (not isinstance(commands, list) or not isinstance(checks, list)
                or len(commands) != len(checks) or len(commands) > 100000):
            raise ValueError('Invalid session history')
        if version == cls.SESSION_VERSION:
            foes = payload['foe_decisions']
            foe_actions = payload['foe_actions']
            if (not isinstance(foes, list) or len(foes) != len(commands) or
                    not isinstance(foe_actions, list) or len(foe_actions) != len(commands)):
                raise ValueError('Invalid foe decision journal')
        else:
            foes = None
            foe_actions = None
        game = cls(payload['seed'])
        for index, (item, expected) in enumerate(zip(commands, checks)):
            command, effort = cls._decode_command(item)
            game.choose(command, effort)
            if (game._journal_signature() if foes is not None else game._signature()) != expected or (foes is not None and
                    game.history[-1]['foe_choice'] != foes[index]) or (
                    foe_actions is not None and game.history[-1]['foe_activity'] != foe_actions[index]):
                raise ValueError('Session validation failed: reconstructed world state differs')
        return game
