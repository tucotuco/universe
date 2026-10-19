"""Bounded turn-by-turn tactical controller over a real Universe Encounter.

Player decisions run the simulation forward by one second. A lightweight
opponent policy schedules actions on the very same Event/Action timeline.
No independent HP/position/XP game state is maintained here.
"""

import math
import random

from melee_combat import MeleeStrike
from perception import GeometricPathPerception
from spatial.geometry import Sphere


class TacticalDuel:
    COMMANDS = ('thrust', 'swing', 'guard', 'north', 'south', 'east', 'west', 'wait')
    WALK_PER_SECOND = .25  # provisional Encounter coordinate units per second
    SENSE_DISTANCE = 3.0
    REACH = 2.0             # explicit in Encounter units; not derived from weapon lengths

    def __init__(self, seed=17):
        # Avoid depending on an unseen global RNG policy; this demonstration
        # remains a single-process seeded simulation, as in armed_duel.py.
        from pathlib import Path
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
        # A proxy body envelope permits geometric-path *detection*. It does
        # not establish real-world visibility (eye point, lighting, etc.).
        self.player.set_geometry(Sphere(.2))
        self.foe.set_geometry(Sphere(.2))
        self.encounter.clear_awareness(self.player.id, self.foe.id)
        self.encounter.clear_awareness(self.foe.id, self.player.id)
        self._perceived = {self.player.id: False, self.foe.id: False}
        self.history = []
        self._observe()

    def _observe(self):
        for observer in (self.player, self.foe):
            self.encounter.clear_awareness(observer.id,
                                            self.foe.id if observer is self.player else self.player.id)
            observed = self.encounter.perceive(observer.id, self.perception)
            other = self.foe if observer is self.player else self.player
            self._perceived[observer.id] = any(o.target_id == other.id for o in observed)

    def _pending(self, being):
        for action_id in self.encounter.pending_action_list:
            action = self.world.get_event_by_id(action_id)
            if action.actor_id == being.id:
                return action
        return None

    def _attack(self, actor, target, weapon_id, motion):
        if self._pending(actor):
            raise ValueError('Attack already in progress; wait or move.')
        strike = MeleeStrike(self.encounter, actor.id, target.id, weapon_id,
                             motion=motion, reach=self.REACH)
        self.encounter.schedule_action(strike)
        return strike

    def _foe_choice(self):
        if self._pending(self.foe) or self.foe.get_hit_points() <= 0:
            return {}, 'Raider continues an action.'
        if not self._perceived[self.foe.id]:
            return {}, 'Raider has not detected the Scout.'
        status, _ = MeleeStrike(self.encounter, self.foe.id, self.player.id,
                                self.foe_weapon, motion='swing', reach=self.REACH)._status(self.encounter)
        if status == 'in_reach':
            self._attack(self.foe, self.player, self.foe_weapon, 'swing')
            return {}, 'Raider initiates a longsword swing.'
        src = self.foe.get_position()
        dst = self.player.get_position()
        dx, dy = dst.x - src.x, dst.y - src.y
        norm = math.hypot(dx, dy)
        if norm <= 0:
            return {}, 'Raider holds position.'
        return {self.foe.id: (self.WALK_PER_SECOND * dx / norm,
                               self.WALK_PER_SECOND * dy / norm, 0)}, 'Raider closes distance.'

    def ended(self):
        return self.player.get_hit_points() <= 0 or self.foe.get_hit_points() <= 0

    def choose(self, command):
        if command not in self.COMMANDS:
            raise ValueError('Unknown tactical command.')
        if self.ended():
            raise ValueError('Combat has ended.')
        self._observe()
        velocities = {}
        description = {'wait': 'Scout waits one second.', 'guard': 'Scout adopts a defensive stance.',
                       'thrust': 'Scout begins a dagger thrust.',
                       'swing': 'Scout begins a dagger swing.',
                       'north': 'Scout steps north.', 'south': 'Scout steps south.',
                       'east': 'Scout steps east.', 'west': 'Scout steps west.'}[command]
        if command in ('thrust', 'swing'):
            self._attack(self.player, self.foe, self.player_weapon, command)
            # Attacking relinquishes the temporary defensive stance.
            self.player.set_strategy(attack=1, defense=0)
        elif command == 'guard':
            if self._pending(self.player):
                raise ValueError('Cannot adopt a guard during an unfinished attack.')
            self.player.set_strategy(defense=2)
        elif command in ('north', 'south', 'east', 'west'):
            vectors = {'north': (0, self.WALK_PER_SECOND, 0),
                       'south': (0, -self.WALK_PER_SECOND, 0),
                       'east': (self.WALK_PER_SECOND, 0, 0),
                       'west': (-self.WALK_PER_SECOND, 0, 0)}
            velocities[self.player.id] = vectors[command]
        foe_velocities, foe_decision = self._foe_choice()
        velocities.update(foe_velocities)
        step = self.encounter.step(1, velocities=velocities)
        self._observe()
        results = []
        for action_id in step.completed_action_ids:
            strike = self.world.get_event_by_id(action_id)
            result = strike.combat_result
            if result is None:
                continue
            xp = sum(exercise.experience for exercise in strike.resolution.skill_exercises)
            results.append({'actor': result.actor_id,
                            'text': ('Scout' if result.actor_id == self.player.id else 'Raider') +
                                    f' {result.motion}: {result.outcome}; +{xp} weapon XP',
                            'outcome': result.outcome, 'xp': xp})
        self.history.append({'time': step.end_time, 'player_choice': description,
                             'foe_choice': foe_decision, 'results': results,
                             'foe_observed': self._perceived[self.player.id]})
        return self.state()

    def state(self, audit=False):
        """Return only permitted player-facing data unless explicitly audited."""
        player = self.player
        enemy_visible = self._perceived[player.id]
        def being_state(being):
            p = being.get_position()
            weapon = 'Dagger' if being is self.player else 'Longsword'
            pending = self._pending(being)
            return {'id': being.id, 'name': being.name, 'position': [p.x,p.y,p.z],
                    'hp': being.get_hit_points(), 'weapon': weapon,
                    'weapon_skill': being.get_weapon_skill_level(weapon) or 0,
                    'xp': being.get_skill_experience(weapon),
                    'strategy': {'attack': being.strategy.attack,
                                 'defense': being.strategy.defense},
                    'pending': None if pending is None else
                               {'motion': pending.event_type, 'due': pending.end_time}}
        player_data = being_state(player)
        # Never send undiscovered objective opponent state to the browser.
        foe_data = being_state(self.foe) if audit else ({'name': self.foe.name,
            'position': list(self.foe.get_position().as_tuple()),
            'present': True, 'hp': None, 'weapon': None, 'xp': None}
            if enemy_visible else None)
        if not audit and foe_data is not None:
            # The geometric-path model provides a positional cue for *this tick*,
            # not health, ability, equipment knowledge, or persistent tracking.
            foe_data['bearing_basis'] = 'current unobstructed geometric path'
        log = []
        for item in self.history:
            if audit:
                log.append(item)
            else:
                # The Scout knows its own decisions. Opponent actions are
                # simplified, rather than leaking hidden AI planning state.
                log.append({'time': item['time'], 'player_choice': item['player_choice'],
                            'results': [r['text'] for r in item['results']
                                        if r['actor'] == player.id or item['foe_observed']]})
        return {'time': self.encounter.time, 'seed': self.seed,
                'player': player_data, 'foe': foe_data, 'observed_now': enemy_visible,
                'game_over': self.ended(), 'history': log,
                'perception_model': 'GeometricPathPerception: path and range only; not full vision',
                'commands': list(self.COMMANDS), 'audit': audit}
