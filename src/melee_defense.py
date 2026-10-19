"""Timed, event-backed parry and dodge reactions in the one-on-one Encounter.

A reaction protects against strikes completing at the same instant. A dodge
also moves the actor in physical space through the Encounter's kinematic step.
There is no claim yet of general multi-attacker or facing geometry.
"""

from action import Action
from experience import ActionResolution, SkillExercise
from weapon import WeaponInstance
from utils import roll_dice


class MeleeDefense(Action):
    # For same-time Events, resolve the defense before incoming strikes.
    resolution_priority = -1

    def __init__(self, encounter, actor_id, attacker_id, *, kind, weapon_id=None):
        if kind not in ('parry', 'dodge'):
            raise ValueError('defensive reaction must be parry or dodge')
        self.encounter = encounter
        self.kind = kind
        self.defended_action_ids = ()
        self.success = False
        self.result = None
        self.threat_at_schedule = ()
        super().__init__(encounter.universe, encounter.time, None, kind,
                         actor_id, attacker_id, weapon_id,
                         parent_event_id=encounter.id)
        self.end_time = encounter.time + 1

    def on_schedule(self, encounter):
        from melee_combat import MeleeStrike
        if encounter is not self.encounter:
            raise ValueError('reaction belongs to a different Encounter')
        actor = encounter.get_being(self.actor_id)
        attacker = encounter.get_being(self.target_id)
        if actor is None or attacker is None or actor is attacker:
            raise ValueError('reaction requires two distinct participating Beings')
        if actor.is_helpless():
            raise ValueError('incapacitated Being cannot react')
        if not encounter.is_aware(self.actor_id, self.target_id):
            raise ValueError('reactor must be aware of attacker')
        if self.kind == 'parry':
            weapon = self.get_instrument()
            if not isinstance(weapon, WeaponInstance) or (
                    self.instrument_id not in actor.armed_with(encounter.universe).values()):
                raise ValueError('parry requires a held weapon')
        threats = []
        for action_id in encounter.pending_action_list:
            attack = encounter.universe.get_event_by_id(action_id)
            if (isinstance(attack, MeleeStrike) and attack.actor_id == attacker.id
                    and attack.target_id == actor.id and attack.end_time == self.end_time):
                threats.append((attack.id, attack._status(encounter)[0] == 'in_reach'))
        self.threat_at_schedule = tuple(threats)

    def resolve(self, difficulty_class):
        from melee_combat import MeleeStrike
        actor = self.get_actor()
        attacker = self.get_target()
        if self.result is not None:
            raise RuntimeError('defensive reaction already resolved')
        incoming = []
        for action_id in self.encounter.pending_action_list:
            strike = self.universe.get_event_by_id(action_id)
            if (isinstance(strike, MeleeStrike) and strike.actor_id == attacker.id
                    and strike.target_id == actor.id and strike.end_time == self.end_time):
                incoming.append(strike)
        if actor.is_helpless() or (self.kind == 'parry' and
                self.instrument_id not in actor.armed_with(self.universe).values()):
            self.result = 'unable_to_defend'
            return ActionResolution(self.result)
        # An impending attack is required for XP, even when moving away
        # from it made the strike fail reach by the time of resolution.
        threatened = [strike for strike in incoming if (
            strike._status(self.encounter)[0] == 'in_reach' or
            (self.kind == 'dodge' and (strike.id, True) in self.threat_at_schedule))]
        if not threatened:
            self.result = 'no_threat'
            return ActionResolution(self.result)
        skill = (self.get_instrument().original.obj_type if self.kind == 'parry'
                 else 'tumble')
        defender_rank = (actor.get_weapon_skill_level(skill) if self.kind == 'parry'
                         else actor.get_skill_level(skill)) or 0
        # The contest is provisional: an active attempt must earn its practice
        # whether it succeeds or fails. A dodge may also succeed geometrically.
        for strike in threatened:
            if strike._status(self.encounter)[0] != 'in_reach':
                continue
            weapon = strike.get_instrument()
            attacker_rank = attacker.get_weapon_skill_level(weapon.original.obj_type) or 0
            defense_roll = roll_dice('1d20') + defender_rank + actor.strategy.defense
            attack_roll = roll_dice('1d20') + attacker_rank + attacker.strategy.attack
            if defense_roll >= attack_roll:
                strike.defended_by = self.id
                self.defended_action_ids += (strike.id,)
        self.success = bool(self.defended_action_ids) or all(
            strike._status(self.encounter)[0] != 'in_reach' for strike in threatened)
        self.result = ('deflected' if self.kind == 'parry' and self.success else
                       'evaded' if self.kind == 'dodge' and self.success else 'failed')
        return ActionResolution(self.result, (SkillExercise(skill, 10),))
