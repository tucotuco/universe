"""Transactional, timed melee defenses against one designated incoming strike.

The Block adapter uses an actually equipped native shield and the adopted
shield-size timing. Dodge/Parry retain their older targeted implementation
pending the adopted preparation and strategy-rule reconciliation.
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

    def __init__(self, encounter, actor_id, attacker_id=None, *, kind,
                 target_action_id=None, weapon_id=None, parry_motion=None,
                 prepared_defense_action_id=None, strategy=None):
        if kind not in ('parry', 'dodge', 'block', 'yield'):
            raise ValueError('defensive reaction kind is unsupported')
        self.encounter = encounter
        self.kind = kind
        self.defended_action_ids = ()
        self.success = False
        self.result = None
        self.target_action_id = target_action_id
        self.prepared_defense_action_id = prepared_defense_action_id
        actor = encounter.get_being(actor_id)
        prepared = (encounter.universe.get_event_by_id(prepared_defense_action_id)
                    if type(prepared_defense_action_id) is str else None)
        if prepared_defense_action_id is not None:
            from strategy import Strategy
            if type(prepared) is not MeleeDefense:
                raise ValueError('prepared defense identity is not a native MeleeDefense Action')
            weapon_id = prepared.instrument_id if weapon_id is None else weapon_id
            strategy = prepared.strategy.copy() if strategy is None else strategy
            parry_motion = prepared.parry_motion if parry_motion is None else parry_motion
        self.parry_motion = parry_motion
        self.strategy_pool = (None if kind != 'dodge' or actor is None else
                              self.dodge_strategy_pool(actor, encounter.universe))
        self.ready_at = None
        self.threat_at_schedule = ()
        self.start_position = None
        self.target_position = None
        super().__init__(encounter.universe, encounter.time, None, kind,
                         actor_id, attacker_id, weapon_id,
                         strategy=strategy, parent_event_id=encounter.id)
        # Set from the designated strike and applicable preparation time.
        self.end_time = encounter.time

    def prepare_schedule(self, encounter, *, proposed_actions=None, target_action_id=None):
        from melee_combat import MeleeStrike
        if encounter is not self.encounter:
            raise ValueError('reaction belongs to a different Encounter')
        actor = encounter.get_being(self.actor_id)
        attacker = encounter.get_being(self.target_id)
        if actor is None:
            raise ValueError('reaction requires a participating Being')
        if actor.is_helpless():
            raise ValueError('incapacitated Being cannot react')

        if self.prepared_defense_action_id is not None:
            if self.kind not in ('dodge', 'parry') or attacker is None or attacker is actor:
                raise ValueError('a retained Dodge or Parry must be committed to a distinct attacker')
            if not encounter.is_aware(self.actor_id, attacker.id):
                raise ValueError('defender must be aware of the attacker before committing a retained defense')
            source = encounter.universe.get_event_by_id(self.prepared_defense_action_id)
            source_resolution = None if source is None else source.resolution
            if (type(source) is not MeleeDefense or source.actor_id != actor.id
                    or source.kind != self.kind or source.target_action_id is not None
                    or source_resolution is None or source_resolution.outcome != 'ready'
                    or source.ready_at is None
                    or source.ready_at > encounter.time
                    or source.id not in encounter.finished_action_list):
                raise ValueError('referenced native defense is not ready and retained')
            if self.kind == 'parry' and source.instrument_id not in actor.armed_with(encounter.universe).values():
                raise ValueError('Parry weapon is no longer held')
            if self.kind == 'dodge':
                current_pool = self.dodge_strategy_pool(actor, encounter.universe)
                if source.strategy.defense + source.strategy.timing != current_pool:
                    raise ValueError('Dodge Dexterity, Tumble, or armor state changed after preparation')
            if any(type(old) is MeleeDefense and old.prepared_defense_action_id == source.id
                   for old in encounter.universe.event_history.values()):
                raise ValueError('retained defense has already been committed')
            if any(type(other) is MeleeDefense and other is not self
                   and other.prepared_defense_action_id == source.id
                   for other in (proposed_actions or {}).values()):
                raise ValueError('one retained defense cannot be assigned more than once in a Choice')
            target_action_id = self.target_action_id if target_action_id is None else target_action_id
            strike = encounter.universe.get_event_by_id(target_action_id) if type(target_action_id) is str else None
            if (type(strike) is not MeleeStrike or strike.id not in encounter.pending_action_list
                    or strike.actor_id != attacker.id or strike.target_id != actor.id):
                raise ValueError('retained defense requires an observed pending native melee strike')
            if strike._status(encounter)[0] != 'in_reach':
                raise ValueError('retained defense can be assigned only to an eligible in-reach strike')
            if self.kind == 'parry':
                weapon = encounter.universe.get_object_by_id(source.instrument_id)
                incoming = strike.get_instrument()
                if weapon is None or incoming is None:
                    raise ValueError('Parry requires both native weapons')
                incoming_weight = incoming.current.weight
                parrying_weight = weapon.current.weight
                if (type(incoming_weight) not in (int, float)
                        or type(parrying_weight) not in (int, float)
                        or incoming_weight > 3 * parrying_weight):
                    raise ValueError('incoming weapon exceeds the native Parry weight limit')
                if actor.get_weapon_skill_level(weapon.original.obj_type) <= 1:
                    raise ValueError('Parry requires advanced skill with its held weapon')
            ready_at = source.ready_at
            if ready_at > strike.end_time:
                raise ValueError('retained defense will not be ready by the strike boundary')
            return PreparedSchedule.from_action(self, end_time=strike.end_time,
                initialization=(('ready_at', ready_at), ('threat_at_schedule', ()),
                                ('target_action_id', strike.id)))

        # Revision 61 allows Dodge and Parry to be prepared without naming any
        # opponent or incoming Action. Their completed native Action remains
        # in event history as the identity-bearing ready record.
        if self.target_action_id is None and target_action_id is None:
            if self.kind not in ('dodge', 'parry') or self.target_id is not None:
                raise ValueError('only Dodge and Parry can be prepared without a target')
            if self.kind == 'dodge':
                dexterity = actor.DEX()
                current_pool = self.dodge_strategy_pool(actor, encounter.universe)
                if self.strategy_pool != current_pool:
                    raise ValueError('Dodge ability, Tumble, or armor state changed after its declaration')
                defense = self.strategy.defense
                timing = self.strategy.timing
                if (type(defense) is not int or type(timing) is not int
                        or defense < 0 or timing < 0
                        or defense + timing != current_pool):
                    raise ValueError('Dodge must allocate its full Dexterity and Tumble strategy pool to defense and timing')
                preparation = max(1, 2 - self.strategy.timing_adjustment())
            else:
                weapon = self.get_instrument()
                if (not isinstance(weapon, WeaponInstance)
                        or self.instrument_id not in actor.armed_with(encounter.universe).values()):
                    raise ValueError('Parry preparation requires an actually held native weapon')
                if self.parry_motion not in ('swing', 'thrust'):
                    raise ValueError('Parry preparation requires a selected swing or thrust timing')
                if actor.get_weapon_skill_level(weapon.original.obj_type) <= 1:
                    raise ValueError('Parry with this weapon requires its adopted advanced weapon skill')
                weapon_timing = (weapon.St() if self.parry_motion == 'swing'
                                 else weapon.Tt())
                if type(weapon_timing) is not int or weapon_timing < 1:
                    raise ValueError('selected Parry weapon motion has no supported native timing')
                preparation = max(1, weapon_timing - 1)
            ready_at = self.start_time + preparation
            return PreparedSchedule.from_action(self, end_time=ready_at,
                initialization=(('ready_at', ready_at),
                                ('threat_at_schedule', ()),
                                ('target_action_id', None)))

        if attacker is None or attacker is actor:
            raise ValueError('reaction requires two distinct participating Beings')
        if not encounter.is_aware(self.actor_id, self.target_id):
            raise ValueError('reactor must be aware of attacker')
        if self.kind == 'parry':
            weapon = self.get_instrument()
            if not isinstance(weapon, WeaponInstance) or (
                    self.instrument_id not in actor.armed_with(encounter.universe).values()):
                raise ValueError('parry requires a held weapon')
        if self.kind == 'block':
            shield = self.get_instrument()
            if (type(shield) is not WeaponInstance
                    or self.instrument_id not in actor.shielded_with(encounter.universe).values()):
                raise ValueError('block requires an actually equipped native shield')
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
            if self.parry_motion not in ('swing', 'thrust'):
                raise ValueError('Parry requires an explicitly selected weapon motion timing')
            weapon_timing = weapon.St() if self.parry_motion == 'swing' else weapon.Tt()
            if type(weapon_timing) is not int or weapon_timing < 1:
                raise ValueError('selected Parry weapon motion has no supported native timing')
            preparation = max(1, weapon_timing - 1)
        else:
            preparation = (2 if self.kind == 'dodge' else
                           int(self.get_instrument().get_weapon_size()) if self.kind == 'block' else 1)
            if self.kind == 'block' and preparation < 1:
                raise ValueError('block requires a positive native shield-size duration')
        ready_at = self.start_time + preparation
        if self.kind in ('block', 'yield'):
            if ready_at != strike.end_time:
                required = ('Block must complete its shield-size timing' if self.kind == 'block'
                            else 'Yield must complete its one-second step at')
                raise ValueError(f'{required} the incoming strike boundary')
        elif ready_at > strike.end_time:
            raise ValueError('defense cannot be ready before the designated attack impacts')
        # Remain committed to this strike until its impact, even if prepared
        # earlier. The action is not a reusable defense against other strikes.
        threat = ((strike.id, strike._status(encounter)[0] == 'in_reach'),)
        return PreparedSchedule.from_action(self, end_time=strike.end_time,
            initialization=(('ready_at', ready_at), ('threat_at_schedule', threat),
                            ('target_action_id', strike.id)))

    @staticmethod
    def dexterity_modifier(score):
        if type(score) is not int or score < 1 or score > 25:
            raise ValueError('Dodge Dexterity modifier is outside the adopted ability table')
        if score == 1:
            return -5
        return (score - 10) // 2

    @classmethod
    def dodge_strategy_pool(cls, actor, universe):
        """Dexterity modifier plus Tumble ranks, less native armor penalty."""
        modifier = cls.dexterity_modifier(actor.DEX())
        tumble = actor.get_skill_level('tumble') or 0
        if type(tumble) is not int or tumble < 0:
            raise ValueError('Dodge Tumble level must be a nonnegative native rank')
        penalty = 0
        armor_id = actor.get_armor_id()
        if armor_id is not None:
            from armor import ArmorInstance
            armor = universe.get_object_by_id(armor_id)
            if type(armor) is not ArmorInstance:
                raise ValueError('Dodge armor check penalty is not available from native armor state')
            penalty = armor.current.armor_check_penalty
            if type(penalty) is not int or penalty < 0:
                raise ValueError('Dodge armor check penalty must be a native nonnegative value')
        return max(0, modifier + tumble - penalty)

    def resolve(self, difficulty_class):
        guard_legacy_action(self, effect=True)
        from melee_combat import MeleeStrike
        actor = self.get_actor()
        attacker = self.get_target()
        if self.result is not None:
            raise RuntimeError('defensive reaction already resolved')
        if self.target_action_id is None:
            if self.kind not in ('dodge', 'parry'):
                raise ValueError('only Dodge and Parry have a target-free preparation phase')
            self.success = True
            self.result = 'ready'
            return ActionResolution(self.result)
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
        if self.kind == 'block':
            self.success = True
            self.result = 'blocked'
            return ActionResolution(self.result)
        if self.kind == 'yield':
            start = self.start_position
            attacker_start = self.target_position
            actor_position = actor.get_position()
            attacker_position = attacker.get_position()
            if (start is None or attacker_start is None or actor_position is None
                    or attacker_position is None
                    or math.dist(actor_position.as_tuple(), attacker_position.as_tuple())
                       <= math.dist(start.as_tuple(), attacker_start.as_tuple())):
                self.result = 'no_space'
                return ActionResolution(self.result)
            self.success = True
            self.result = 'yielded'
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
