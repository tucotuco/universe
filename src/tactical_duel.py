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
    SESSION_VERSION = 1

    def __init__(self, seed=17):
        import sys
        examples = str(Path(__file__).resolve().parents[1] / 'examples')
        if examples not in sys.path:
            sys.path.insert(0, examples)
        from armed_duel import make_duel
        random.seed(seed)
        self.seed = seed
        self.world, self.encounter, self.player, self.foe, self.armor_id, strikes = make_duel(
            schedule_attacks=False)
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

    def _attack(self, actor, target, weapon_id, motion):
        # Preflight *before* abandoning an already scheduled action. Rejected
        # replacement leaves both world time and original pending action intact.
        strike = MeleeStrike(self.encounter, actor.id, target.id, weapon_id,
                             motion=motion, reach=self.REACH)
        strike.on_schedule(self.encounter)
        interrupted = self._interrupt(actor)
        self.encounter.schedule_action(strike)
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

    def choose(self, command):
        if command not in self.COMMANDS:
            raise ValueError('Unknown tactical command.')
        if self.ended():
            raise ValueError('Combat has ended.')
        self._observe()
        velocities = {}
        interrupted = None
        description = ''
        if command in ('thrust', 'swing'):
            _, interrupted = self._attack(self.player, self.foe, self.player_weapon, command)
            self.player.set_strategy(attack=1, defense=0)
            description = f'Scout begins a dagger {command}.'
        elif command == 'guard':
            interrupted = self._interrupt(self.player)
            self.player.set_strategy(defense=2)
            description = 'Scout adopts a defensive stance.'
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
                foe_cue = 'Raider appears to move.'
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
            # Exact opponent HP/armor durability is objective audit data, not
            # something the range/path sensor has established for the Scout.
            if result.actor_id == self.player.id:
                player_details = ('impact sensed; opponent damage not established'
                                  if hp_loss or result.target_armor_damage else 'no confirmed damage')
                player_text = f'Scout {result.motion}: {result.outcome} — {player_details}; +{xp} weapon XP'
            else:
                player_details = []
                if hp_loss:
                    player_details.append(f'you lose {hp_loss:g} HP ({result.target_hp_before:g}→{result.target_hp_after:g})')
                if result.target_armor_damage:
                    player_details.append(f'your armor loses {result.target_armor_damage:g} durability')
                if not player_details:
                    player_details.append('no recorded injury')
                player_text = f'Incoming {result.motion}: {result.outcome} — ' + '; '.join(player_details)
            results.append({'actor': result.actor_id, 'target': result.target_id,
                            'text': f'{attacker} {result.motion}: {result.outcome} — ' + '; '.join(details),
                            'player_text': player_text,
                            'outcome': result.outcome, 'xp': xp, 'damage': hp_loss})
        self.history.append({'time': step.end_time, 'player_choice': description,
                             'foe_choice': foe_decision, 'foe_cue': foe_cue,
                             'foe_observed': self._perceived[self.player.id],
                             'player_moved': command in self.DIRECTION,
                             'foe_moved': self.foe.id in foe_velocities,
                             'results': results, 'fatigue_events': fatigue_events})
        self.commands.append(command)
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
                                 'defense': being.strategy.defense},
                    'pending': None if pending is None else
                               {'motion': pending.event_type, 'due': pending.end_time}}

        player_data = being_state(player)
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
            player_arrow = move_arrows.get(command, '➜')
        foe_arrow = '➜' if latest and latest.get('foe_moved') else ''
        player_symbol = ('⚔' if player_data['pending'] else
                         '▣' if player.strategy.defense > 0 else '') + player_arrow or '•'
        foe_symbol = (('⚔' if self._pending(self.foe) else '') + foe_arrow or '•') if enemy_visible else None
        return {'time': self.encounter.time, 'seed': self.seed,
                'player': player_data, 'foe': foe_data, 'observed_now': enemy_visible,
                'player_symbol': player_symbol, 'foe_symbol': foe_symbol,
                'game_over': self.ended(), 'history': log,
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

    def to_session(self):
        """Versioned seed + commands + fingerprints for checked reconstruction."""
        # Replaying a save must not perturb the active encounter's RNG stream.
        rng_state = random.getstate()
        try:
            fresh = TacticalDuel(self.seed)
            checks = []
            for command in self.commands:
                fresh.choose(command)
                checks.append(fresh._signature())
            if fresh._signature() != self._signature():
                raise ValueError('Current encounter diverges from its command history; cannot save safely')
            return {'format': 'universe.tactical-duel', 'version': self.SESSION_VERSION,
                    'seed': self.seed, 'commands': list(self.commands), 'checks': checks}
        finally:
            random.setstate(rng_state)

    @classmethod
    def from_session(cls, payload):
        if not isinstance(payload, dict) or set(payload) != {'format', 'version', 'seed', 'commands', 'checks'}:
            raise ValueError('Invalid session structure')
        if payload['format'] != 'universe.tactical-duel' or payload['version'] != cls.SESSION_VERSION:
            raise ValueError('Unsupported session format/version')
        if type(payload['seed']) is not int:
            raise ValueError('Session seed must be an integer')
        commands, checks = payload['commands'], payload['checks']
        if (not isinstance(commands, list) or not isinstance(checks, list)
                or len(commands) != len(checks) or len(commands) > 100000):
            raise ValueError('Invalid session history')
        game = cls(payload['seed'])
        for command, expected in zip(commands, checks):
            if not isinstance(command, str) or command not in cls.COMMANDS:
                raise ValueError('Invalid session command')
            game.choose(command)
            if game._signature() != expected:
                raise ValueError('Session validation failed: reconstructed world state differs')
        return game
