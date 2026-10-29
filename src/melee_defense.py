"""Attack-specific, timed parry and dodge in the one-on-one Encounter.

The defender selects one pending strike. A reaction must be ready when that
strike resolves; neither a later strike nor an unspecified attacker is protected.
"""

from transactional_progression import guard_legacy_action

import math

from action import Action
from scheduling import PreparedSchedule
from experience import ActionResolution, SkillExercise
from weapon import WeaponInstance
from utils import roll_dice


class MeleeDefense(Action):
    # For same-time Events, resolve the defense before incoming strikes.
    resolution_priority = -1

    def __init__(self, encounter, actor_id, attacker_id, *, kind, target_action_id, weapon_id=None):
        if kind not in ('parry', 'dodge'):
            raise ValueError('defensive reaction must be parry or dodge')
        self.encounter = encounter
        self.kind = kind
        self.defended_action_ids = ()
        self.success = False
        self.result = None
        self.target_action_id = target_action_id
        self.ready_at = None
        self.threat_at_schedule = ()
        super().__init__(encounter.universe, encounter.time, None, kind,
                         actor_id, attacker_id, weapon_id,
                         parent_event_id=encounter.id)
        # Set from the designated strike and applicable preparation time.
        self.end_time = encounter.time

    def prepare_schedule(self, encounter, *, proposed_actions=None, target_action_id=None):
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
        target_action_id = self.target_action_id if target_action_id is None else target_action_id
        proposed_actions = proposed_actions or {}
        strike = proposed_actions.get(target_action_id) or encounter.universe.get_event_by_id(target_action_id)
        if (not isinstance(strike, MeleeStrike)
                or (strike.id not in encounter.pending_action_list and strike.id not in proposed_actions)
                or strike.actor_id != attacker.id or strike.target_id != actor.id):
            raise ValueError('defense must designate one pending incoming attack')
        from scheduling import native_preparer
        native_preparer(strike)  # Do not call scheduling helpers on opaque extensions.
        if (type(strike.end_time) not in (int, float) or not math.isfinite(strike.end_time)):
            raise ValueError('Designated strike requires a finite nominal deadline')
        if self.kind == 'parry':
            weapon = self.get_instrument()
            # Existing weapon definitions specify separate swing/thrust timings.
            # Use the faster attack motion, less one second, as the first
            # concrete interpretation of draft parry timing.
            times = [t for t in (weapon.St(), weapon.Tt()) if t is not None]
            preparation = max(1, min(times) - 1)
        else:
            preparation = 2
        ready_at = self.start_time + preparation
        if ready_at > strike.end_time:
            raise ValueError('defense cannot be ready before the designated attack impacts')
        # Remain committed to this strike until its impact, even if prepared
        # earlier. The action is not a reusable defense against other strikes.
        threat = ((strike.id, strike._status(encounter)[0] == 'in_reach'),)
        return PreparedSchedule.from_action(self, end_time=strike.end_time,
            initialization=(('ready_at', ready_at), ('threat_at_schedule', threat),
                            ('target_action_id', strike.id)))

    def resolve(self, difficulty_class):
        guard_legacy_action(self, effect=True)
        from melee_combat import MeleeStrike
        actor = self.get_actor()
        attacker = self.get_target()
        if self.result is not None:
            raise RuntimeError('defensive reaction already resolved')
        strike = self.universe.get_event_by_id(self.target_action_id)
        if actor.is_helpless() or (self.kind == 'parry' and
                self.instrument_id not in actor.armed_with(self.universe).values()):
            self.result = 'unable_to_defend'
            return ActionResolution(self.result)
        # A canceled or already-finished designated attack cannot be replaced
        # by a different strike, even from the same attacker.
        if (strike.id not in self.encounter.pending_action_list or
                strike.actor_id != attacker.id or strike.target_id != actor.id or
                strike.end_time != self.end_time):
            self.result = 'no_threat'
            return ActionResolution(self.result)
        threatened = [strike] if (strike._status(self.encounter)[0] == 'in_reach' or
            (self.kind == 'dodge' and (strike.id, True) in self.threat_at_schedule)) else []
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
            from action_calculations import defense_succeeds
            defense_roll = roll_dice('1d20')
            attack_roll = roll_dice('1d20')
            if defense_succeeds(defense_roll, defender_rank, actor.strategy.defense,
                                attack_roll, attacker_rank, attacker.strategy.attack):
                strike.defended_by = self.id
                self.defended_action_ids += (strike.id,)
        self.success = bool(self.defended_action_ids) or all(
            strike._status(self.encounter)[0] != 'in_reach' for strike in threatened)
        self.result = ('deflected' if self.kind == 'parry' and self.success else
                       'evaded' if self.kind == 'dodge' and self.success else 'failed')
        return ActionResolution(self.result, (SkillExercise(skill, 10),))
