"""Native whole-choice planning and bounded schedule publication (Increment 3).

The lock serializes planning/reservation operations. Publication rollback covers
only native scheduling dictionaries/lists/metadata, never world effects or RNG.
"""

from transactional_progression import guard_legacy_encounter, planning_entry, validate_action_contract, validate_choice_actions
from dataclasses import dataclass, replace
import math

from scheduling import UnsupportedScheduleExtension


@dataclass(frozen=True)
class ChoiceMember:
    key: str
    action: object
    target_action_key: str | None = None
    priority_penalty: int | None = None


@dataclass(frozen=True)
class ChoiceDraft:
    id: str
    version: int
    members: tuple


@dataclass(frozen=True)
class ChoiceDiagnostic:
    code: str
    member: str
    reason: str
    object_id: str | None = None
    interval: tuple | None = None
    conflicting_action: str | None = None
    conflicting_choice: str | None = None
    conflicting_interval: tuple | None = None


class ChoiceRejected(ValueError):
    def __init__(self, diagnostics):
        self.diagnostics = tuple(diagnostics)
        super().__init__('; '.join(f'{d.member}: {d.reason}' for d in self.diagnostics))


@dataclass(frozen=True)
class ChoiceValidation:
    id: str
    draft_id: str
    draft_version: int
    revision: int
    diagnostics: tuple
    signatures: tuple

    @property
    def valid(self):
        return not self.diagnostics


@dataclass(frozen=True)
class Reservation:
    choice_id: str
    action_id: str
    object_id: str
    start: float
    boundary: float


@dataclass(frozen=True)
class ChoiceView:
    id: str
    version: int
    state: str
    action_ids: tuple
    first_start: float


@dataclass(frozen=True)
class _Accepted:
    view: ChoiceView
    members: tuple
    prepared: tuple
    signatures: tuple
    origin: str = 'choice'


def _freeze(value):
    if value is None or type(value) in (str, int, float, bool):
        return (type(value).__name__, repr(value))
    if type(value) in (tuple, list):
        return tuple(_freeze(x) for x in value)
    if type(value) is dict:
        return tuple(sorted(((_freeze(k), _freeze(v)) for k, v in value.items()), key=repr))
    return ('identity', id(value))


def _requires_multiple_action_capacity(action):
    # Run is the adopted movement exception. A declared willing Touch also
    # retains its specific no-Multiple-action exception (revision 68).
    data = object.__getattribute__(action, '__dict__')
    if data.get('event_type') == 'touch' and data.get('touch_willing') is True:
        return False
    return data.get('event_type') != 'run'


def _compatible_simultaneous_object_claims(first, second, object_id):
    """Permit only same-boundary same-holder Object Grip/Wrest contests."""
    if first is None or second is None or type(first) is not type(second):
        return False
    first_data=object.__getattribute__(first,'__dict__')
    second_data=object.__getattribute__(second,'__dict__')
    event_type=first_data.get('event_type')
    return (event_type in ('grab object','wrest')
        and second_data.get('event_type')==event_type
        and first.target_id==second.target_id==object_id
        and first.actor_id!=second.actor_id
        and first_data.get('holder_id')==second_data.get('holder_id')
        and first_data.get('holder_hand')==second_data.get('holder_hand')
        and first.start_time==second.start_time
        and math.ceil(first.end_time)==math.ceil(second.end_time))


def _resource_skill_pool(encounter, action):
    actor = encounter.get_being(action.actor_id)
    if actor is None:
        return 0
    skills = {str(name).casefold(): value
              for name, value in actor.current.skills.get_skills().items()}
    event = getattr(action, 'event_type', '').casefold()
    if event in ('swing', 'thrust', 'subdue', 'disarm', 'strike object', 'break weapon',
                 'parry', 'block'):
        combat = skills.get('armed combat', 0) or 0
    elif event in ('stun',):
        combat = 2 * (skills.get('unarmed combat', 0) or 0)
        combat += math.floor((actor.STR() - 10) / 2) + math.floor((actor.DEX() - 10) / 2)
        armor_id = actor.current.armor_id
        if armor_id is not None:
            armor = encounter.universe.get_object_by_id(armor_id)
            if armor is None:
                raise ValueError('Stun strategy pool has unsupported armor')
            combat -= armor.current.armor_check_penalty
    elif event in ('grab', 'hold', 'break hold', 'grapple', 'grapple escape',
                   'takedown', 'reverse', 'pin', 'trip', 'bull rush', 'overrun', 'wrest', 'grab object'):
        combat = skills.get('unarmed combat', 0) or 0
    elif event == 'dodge':
        combat = skills.get('tumble', 0) or 0
    else:
        combat = skills.get(event, 0) or 0
    weapon_rank = 0
    instrument_id = getattr(action, 'instrument_id', None)
    if instrument_id is not None:
        weapon = encounter.universe.get_object_by_id(instrument_id)
        original = getattr(weapon, 'original', None)
        weapon_type = getattr(original, 'obj_type', None)
        if weapon_type is not None:
            weapon_rank = actor.get_weapon_skill_level(weapon_type) or 0
    pool = combat + weapon_rank
    if event == 'stun':
        pool = max(0, pool)
    if type(pool) is not int or pool < 0:
        raise ValueError('Multiple-action skill ranks must be nonnegative integers')
    return pool


def _equipment_hand_resource_keys(encounter, action):
    """Return explicit hand slots occupied by this Action over its interval."""
    actor = encounter.get_being(action.actor_id)
    if actor is None:
        return ()
    parts = getattr(actor.current, 'body_parts', {})
    if type(parts) is not dict:
        return ()
    data = object.__getattribute__(action, '__dict__')
    represented = {name for name in ('left hand', 'right hand') if name in parts}
    used = set()
    if data.get('two_handed') is True:
        used.update(represented)
    elif data.get('shield_bash') is True:
        hand = data.get('shield_hand')
        if hand in represented:
            used.add(hand)
    elif data.get('event_type') == 'ready weapon':
        hand = data.get('hand')
        if hand in represented:
            used.add(hand)
    elif data.get('event_type') in ('grab', 'grab object'):
        hand = data.get('grab_hand')
        if hand in represented:
            used.add(hand)
    elif data.get('event_type') == 'ready object':
        object_id = getattr(action, 'target_id', None)
        used.update(hand for hand in represented if parts.get(hand) == object_id)
    else:
        instrument_id = getattr(action, 'instrument_id', None)
        if instrument_id is not None:
            used.update(hand for hand in represented if parts.get(hand) == instrument_id)
    return tuple(f'@hand/{actor.id}/{hand}' for hand in sorted(used))


def declaration(action, *, _initialization=None):
    """Capture plan inputs, not mutable outcome fields or live Being state."""
    data = object.__getattribute__(action, '__dict__')
    if _initialization is not None:
        data = dict(data, **_initialization)
    names = ('id', 'universe', 'event_type', 'start_time', 'end_time', 'actor_id',
             'target_id', 'instrument_id', 'parent_event_id', 'encounter', 'reach',
             'motion', 'body_region',
             'two_handed',
             'shield_bash',
             'shield_hand',
             'kind', 'target_action_id', 'minimum_distance', 'practice_experience',
             'max_distance', 'spotting_conditions', 'declared_roll', 'episode_time', 'topic', 'generate',
             'substituted_claim', 'received_accounts', 'seed', 'random_key',
             'observer', 'interpreter', 'ledger', 'experience_policy', 'focus_category')
    names += ('grab_hand', 'touch_action_id', 'grip_id', 'grapple_id',
              'grapple_position','trip_source_action_id','trip_defender_ability','trip_size_categories')
    names += ('heavy_load_reference_lb','elevation_degrees','azimuth_degrees','landing_elevation_m')
    names += ('group_fully_visible', 'location_ledger', 'object_ledger')
    names += ('map_width_cells', 'map_height_cells')
    names += ('hand',)
    names += ('ready_motion', 'readying_seconds')
    names += ('charge_continuation_source_id',)
    names += ('end_run_exit_position','end_run_movement_conditions',
              'end_run_occupant_willing','end_run_rate')
    names += ('get_instrument', 'damage_potential', '_status', 'on_schedule', 'prepare_schedule')
    strategy = data.get('strategy')
    from strategy import Strategy
    if strategy is not None and type(strategy) is not Strategy:
        raise UnsupportedScheduleExtension('Custom strategy descriptors require a reviewed scheduling adapter')
    effort = tuple(strategy.__dict__.get(name) if strategy is not None else 0
                   for name in ('attack', 'defense', 'timing', 'extra_damage'))
    if any(type(value) not in (int, float, bool) or not math.isfinite(value) for value in effort):
        raise ValueError('Native strategy fields must be finite numeric values')
    fields = tuple((name, ('identity', id(data[name])) if name == 'received_accounts'
                    and data.get(name) is not None else _freeze(data.get(name))) for name in names)
    return (id(type(action)), fields, tuple(_freeze(value) for value in effort))


class ChoiceBook:
    def __init__(self, encounter):
        self.encounter = encounter
        self.lock = encounter.universe._schedule_lock
        self._counter = 0
        self._drafts = {}
        self._closed_drafts = set()
        self._tokens = {}
        self._choices = {}
        self._reservations = ()
        self._registered = {}  # id -> (choice id, prepared packet, declaration)
        self._states = {}      # registered, executing, finished, cancelled
        self._paused = {}      # action id -> committed remaining-time/pause receipt
        with self.lock:
            encounter.universe._choice_books.append(self)

    @property
    def revision(self):
        return self.encounter.universe._schedule_revision

    @revision.setter
    def revision(self, value):
        self.encounter.universe._schedule_revision = value

    def _all_reservations(self):
        return tuple(r for book in self.encounter.universe._choice_books for r in book._reservations)

    def _id(self, kind):
        self._counter += 1
        return f'{self.encounter.id}/{kind}/{self._counter}'

    def _reject(self, code, reason, member='choice'):
        raise ChoiceRejected((ChoiceDiagnostic(code, member, reason),))

    def _members(self, actions):
        if type(actions) is dict:
            return tuple(value if isinstance(value, ChoiceMember) else ChoiceMember(key, value)
                         for key, value in actions.items())
        return tuple(value if isinstance(value, ChoiceMember) else ChoiceMember(str(i), value)
                     for i, value in enumerate(actions))

    def propose(self, actions):
        planning_entry(self.encounter)
        with self.lock:
            self.encounter._assert_timeline()
            draft = ChoiceDraft(self._id('draft'), 1, self._members(actions))
            self._drafts[draft.id] = draft
            return draft

    def edit(self, draft, actions):
        planning_entry(self.encounter)
        with self.lock:
            self.encounter._assert_timeline()
            current = self._drafts.get(draft.id)
            if current is not draft or draft.id in self._closed_drafts:
                self._reject('stale_draft', 'Edit the current open draft, not an accepted or stale version')
            updated = ChoiceDraft(draft.id, draft.version + 1, self._members(actions))
            self._drafts[draft.id] = updated
            return updated

    def _evaluate(self, draft, *, exclude_choice=None, interrupt=None,
                  allow_arena_uninitiated=False):
        from melee_defense import MeleeDefense
        from scheduling import native_preparer
        from encounter import BoundaryInvariantError
        errors, packets, signatures = [], [], []
        keys, ids = set(), set()
        candidates = {}
        if not draft.members:
            errors.append(ChoiceDiagnostic('empty_choice', 'choice', 'Propose at least one Action; use undo to remove a selection'))
        for member in draft.members:
            try:
                if type(member.key) is not str or not member.key or member.key in keys:
                    raise ValueError('Draft-local keys must be nonempty and unique')
                keys.add(member.key)
                native_preparer(member.action)  # Reject opaque code before reading plan inputs.
                if member.action.id in ids:
                    raise ValueError('An Action may occur only once in a complete choice')
                ids.add(member.action.id)
                candidates[member.key] = member.action
                live_declaration = declaration(member.action)
                signatures.append((member.key, member.priority_penalty, live_declaration)
                                  if member.priority_penalty is not None
                                  else (member.key, live_declaration))
            except (TypeError, ValueError) as exc:
                errors.append(ChoiceDiagnostic('unsupported' if isinstance(exc, UnsupportedScheduleExtension)
                                               else 'invalid_member',
                                               member.key if type(member.key) is str else '<invalid-key>', str(exc)))
        for member in draft.members:
            if type(member.key) is not str or member.key not in candidates:
                continue
            try:
                reference = None
                if member.target_action_key is not None:
                    if (type(member.action) is not MeleeDefense or type(member.target_action_key) is not str
                            or member.target_action_key not in candidates):
                        raise ValueError('A defense reference must name a strike key in this complete choice')
                    reference = candidates[member.target_action_key].id
                elif type(member.action) is MeleeDefense and member.action.target_action_id in candidates:
                    reference = candidates[member.action.target_action_id].id
                proposed = {a.id: a for a in candidates.values()}
                packet = self.encounter.prepare_action(member.action,
                    _proposed_actions=proposed, _target_action_id=reference,
                    _arena_activation_preparation=allow_arena_uninitiated)
                packets.append((member, packet))
            except (TypeError, ValueError, RuntimeError) as exc:
                code = ('unsupported' if isinstance(exc, UnsupportedScheduleExtension) else
                        'boundary' if isinstance(exc, BoundaryInvariantError) else 'invalid_schedule')
                errors.append(ChoiceDiagnostic(code, member.key, str(exc)))
        reservations = []
        for member, packet in packets:
            for object_id in packet.active_object_ids:
                reservation = Reservation(draft.id, packet.action_id, object_id,
                                          packet.start_time, math.ceil(packet.end_time))
                for other in tuple(reservations) + self._all_reservations():
                    if other.choice_id == exclude_choice or other.action_id == interrupt:
                        continue
                    overlap = max(reservation.start, other.start) < min(reservation.boundary, other.boundary)
                    unsettled = (reservation.start <= other.boundary < reservation.boundary
                                 and any(book.encounter.active_boundary == other.boundary
                                         and other in book._reservations
                                         for book in self.encounter.universe._choice_books))
                    if object_id == other.object_id and (overlap or unsettled):
                        prior_action = (self.encounter.universe.get_event_by_id(other.action_id)
                            or next((candidate for candidate in candidates.values()
                                     if candidate.id == other.action_id), None)
                            or next((member.action for book in self.encounter.universe._choice_books
                                for record in book._choices.values()
                                for member, packet in zip(record.members, record.prepared)
                                if packet.action_id == other.action_id), None))
                        if _compatible_simultaneous_object_claims(
                                prior_action,member.action,object_id):
                            continue
                        errors.append(ChoiceDiagnostic('active_object_conflict', member.key,
                            f'Object {object_id} is actively reserved by {other.action_id}; '
                            'edit the Object or interval (handoff requires boundary settlement)',
                            object_id, (reservation.start, reservation.boundary),
                            other.action_id, other.choice_id, (other.start, other.boundary)))
                reservations.append(reservation)
        proposed_hands = []
        from transactional_progression import is_automatic_hold_schedule
        for member, packet in packets:
            for hand_key in _equipment_hand_resource_keys(self.encounter, member.action):
                proposed_hands.append((member, packet, hand_key))
        for index, (member, packet, hand_key) in enumerate(proposed_hands):
            for other_member, other_packet, other_key in proposed_hands[:index]:
                if (hand_key == other_key
                        and max(packet.start_time, other_packet.start_time)
                            < min(packet.end_time, other_packet.end_time)):
                    hand_name = hand_key.rsplit('/', 1)[-1]
                    errors.append(ChoiceDiagnostic('active_hand_conflict', member.key,
                        f'Hand resource {hand_name} is claimed by another overlapping Action',
                        interval=(packet.start_time, packet.end_time),
                        conflicting_action=other_packet.action_id,
                        conflicting_interval=(other_packet.start_time, other_packet.end_time)))
            for book in self.encounter.universe._choice_books:
                for record in book._choices.values():
                    if (record.view.id == exclude_choice
                            or record.view.state not in ('accepted', 'executing')):
                        continue
                    for other_member, other_packet in zip(record.members, record.prepared):
                        if other_packet.action_id == interrupt:
                            continue
                        if is_automatic_hold_schedule(book.encounter, other_member.action):
                            continue
                        if (hand_key in _equipment_hand_resource_keys(
                                book.encounter, other_member.action)
                                and max(packet.start_time, other_packet.start_time)
                                    < min(packet.end_time, other_packet.end_time)):
                            hand_name = hand_key.rsplit('/', 1)[-1]
                            errors.append(ChoiceDiagnostic('active_hand_conflict', member.key,
                                f'Hand resource {hand_name} is claimed by another overlapping Action',
                                interval=(packet.start_time, packet.end_time),
                                conflicting_action=other_packet.action_id,
                                conflicting_choice=record.view.id,
                                conflicting_interval=(other_packet.start_time,
                                                     other_packet.end_time)))
        for member, packet in packets:
            for record in (r for book in self.encounter.universe._choice_books for r in book._choices.values()):
                if record.view.id == exclude_choice:
                    continue
                if any(packet.action_id == p.action_id for p in record.prepared):
                    errors.append(ChoiceDiagnostic('action_committed', member.key,
                        'This Action already belongs to an accepted or published choice'))
        by_actor = {}
        for member, packet in packets:
            if _requires_multiple_action_capacity(member.action):
                by_actor.setdefault(packet.actor_id, []).append((member, packet))
        from multiple_action_rules import (MultipleActionRuleError,
            validate_priority_schedule, validate_resource_budget)
        for actor_id, components in by_actor.items():
            if len(components) < 2:
                if components and components[0][0].priority_penalty is not None:
                    errors.append(ChoiceDiagnostic('orphaned_priority', components[0][0].key,
                        'A priority penalty is valid only within an overlapping Multiple-action program'))
                continue
            intervals = {member.key: (packet.start_time, packet.end_time)
                         for member, packet in components}
            # Defense is a characteristic of the whole declared program. A
            # component cannot silently use a different defensive allocation.
            defenses = {getattr(getattr(member.action, 'strategy', None), 'defense', 0)
                        for member, _ in components}
            if len(defenses) > 1:
                errors.append(ChoiceDiagnostic('multiple_action_shared_defense',
                    components[0][0].key,
                    'All components of a Multiple-action program must share one defense level'))
            overlaps = {member.key: any(
                other.key != member.key
                and max(packet.start_time, other_packet.start_time)
                    < min(packet.end_time, other_packet.end_time)
                for other, other_packet in components)
                for member, packet in components}
            if not any(overlaps.values()):
                if any(member.priority_penalty is not None for member, _ in components):
                    errors.append(ChoiceDiagnostic('orphaned_priority', components[0][0].key,
                        'Priority penalties are used only while Actions overlap'))
                continue
            actor = self.encounter.get_being(actor_id)
            if actor is None or (actor.get_skill_level('multi-action') or 0) <= 0:
                for member, _ in components:
                    if overlaps[member.key]:
                        errors.append(ChoiceDiagnostic('multiple_action_skill', member.key,
                            'Overlapping Actions by one Being require acquired Multi-action skill'))
                continue
            for member, _ in components:
                if overlaps[member.key] and type(member.priority_penalty) is not int:
                    errors.append(ChoiceDiagnostic('multiple_action_priority', member.key,
                        'Every overlapping Action needs one fixed integer Multiple-action priority penalty'))
                elif not overlaps[member.key] and member.priority_penalty is not None:
                    errors.append(ChoiceDiagnostic('orphaned_priority', member.key,
                        'A nonoverlapping Action does not receive a Multiple-action priority penalty'))
            if all(not overlaps[member.key] or type(member.priority_penalty) is int
                   for member, _ in components):
                penalties = {member.key: member.priority_penalty for member, _ in components
                             if overlaps[member.key]}
                participating_intervals = {key: intervals[key] for key in penalties}
                priority_schedule_valid = True
                try:
                    validate_priority_schedule(participating_intervals, penalties)
                except MultipleActionRuleError as exc:
                    priority_schedule_valid = False
                    errors.append(ChoiceDiagnostic('multiple_action_priority', components[0][0].key,
                        str(exc)))
                if priority_schedule_valid:
                    try:
                        strategies = {}
                        skill_pools = {}
                        all_priorities = {}
                        for member, _ in components:
                            strategy = getattr(member.action, 'strategy', None)
                            values = tuple(getattr(strategy, name, 0)
                                           for name in ('attack', 'defense', 'timing', 'extra_damage'))
                            strategies[member.key] = values
                            skill_pools[member.key] = _resource_skill_pool(
                                self.encounter, member.action)
                            all_priorities[member.key] = member.priority_penalty or 0
                        actor = self.encounter.get_being(actor_id)
                        strength = max(0, (actor.STR() - 10) // 2)
                        dexterity = max(0, (actor.DEX() - 10) // 2)
                        validate_resource_budget(skill_pools, all_priorities,
                            strategies, strength_points=strength,
                            dexterity_points=dexterity)
                    except (MultipleActionRuleError, TypeError, ValueError) as exc:
                        errors.append(ChoiceDiagnostic('multiple_action_resources',
                            components[0][0].key, str(exc)))
        # Components accepted through separate choices are not a declared
        # Multiple-action program. Refuse any same-actor interval overlap with
        # another live choice, even when both choices individually validate.
        proposed_by_actor = {}
        for member, packet in packets:
            if _requires_multiple_action_capacity(member.action):
                proposed_by_actor.setdefault(packet.actor_id, []).append((member, packet))
        for book in self.encounter.universe._choice_books:
            for record in book._choices.values():
                if record.view.id == exclude_choice or record.view.state not in ('accepted', 'executing'):
                    continue
                for existing_member, existing_packet in zip(record.members, record.prepared):
                    if not _requires_multiple_action_capacity(existing_member.action):
                        continue
                    if existing_packet.action_id == interrupt:
                        continue
                    if is_automatic_hold_schedule(book.encounter, existing_member.action):
                        continue
                    for member, packet in proposed_by_actor.get(existing_packet.actor_id, ()):
                        if is_automatic_hold_schedule(self.encounter, member.action):
                            continue
                        if (packet.action_id != existing_packet.action_id
                                and max(packet.start_time, existing_packet.start_time)
                                    < min(packet.end_time, existing_packet.end_time)):
                            errors.append(ChoiceDiagnostic('multiple_action_split', member.key,
                                'Overlapping Actions by one Being must be declared in the same Multiple-action program',
                                conflicting_action=existing_packet.action_id,
                                conflicting_choice=record.view.id,
                                interval=(packet.start_time, packet.end_time),
                                conflicting_interval=(existing_packet.start_time,
                                                      existing_packet.end_time)))
        if interrupt is not None:
            old = self.encounter.universe.get_event_by_id(interrupt)
            if (len(packets) != 1 or interrupt not in self.encounter.pending_action_list
                    or old is None or old.actor_id != packets[0][1].actor_id):
                errors.append(ChoiceDiagnostic('invalid_interruption', 'choice',
                    "Interruption requires this actor's pending Action"))
        return tuple(errors), tuple(p for _, p in packets), tuple(signatures), tuple(reservations)

    def validate(self, draft, *, replacing=None, _arena_activation_preparation=False):
        planning_entry(self.encounter)
        with self.lock:
            self.encounter._assert_timeline()
            if self._drafts.get(draft.id) is not draft or draft.id in self._closed_drafts:
                self._reject('stale_draft', 'Validate the current open draft')
            if replacing is not None:
                self._undoable(replacing)
            errors, _, signatures, _ = self._evaluate(
                draft, exclude_choice=replacing,
                allow_arena_uninitiated=_arena_activation_preparation)
            token = ChoiceValidation(self._id('validation'), draft.id, draft.version,
                                     self.revision, errors, signatures)
            self._tokens[token.id] = (token, replacing)
            return token

    def _authorized(self, token, replacing=None):
        issued = self._tokens.get(token.id) if isinstance(token, ChoiceValidation) else None
        if issued is None or issued[0] is not token or issued[1] != replacing:
            self._reject('invalid_validation', 'Use validation issued for this operation')
        draft = self._drafts.get(token.draft_id)
        if (draft is None or draft.version != token.draft_version or draft.id in self._closed_drafts
                or token.revision != self.revision):
            self._reject('stale_validation', 'The draft or commitments changed; validate the complete set again')
        if not token.valid:
            raise ChoiceRejected(token.diagnostics)
        errors, packets, signatures, reservations = self._evaluate(draft, exclude_choice=replacing)
        if signatures != token.signatures:
            self._reject('edited_action', 'Action declarations changed; edit and validate the complete draft')
        if errors:
            raise ChoiceRejected(errors)
        return draft, packets, signatures, reservations

    def accept(self, token, *, origin='choice'):
        planning_entry(self.encounter)
        with self.lock:
            self.encounter._assert_timeline()
            draft, packets, signatures, reservations = self._authorized(token)
            return self._accept(draft, packets, signatures, reservations, origin=origin)

    def _accept(self, draft, packets, signatures, reservations, *, replacing=None, origin='choice'):
        planning_entry(self.encounter)
        choice_id = replacing or draft.id
        version = self._choices[replacing].view.version + 1 if replacing else 1
        view = ChoiceView(choice_id, version, 'accepted', tuple(p.action_id for p in packets),
                          min(p.start_time for p in packets))
        record = _Accepted(view, draft.members, packets, signatures, origin)
        # Prepare both replacement collections before their lock-protected swap.
        new_reservations = tuple(r for r in self._reservations if r.choice_id != replacing) + tuple(
            replace(r, choice_id=choice_id) for r in reservations)
        self._choices[choice_id] = record
        self._reservations = new_reservations
        self._closed_drafts.add(draft.id)
        self.revision += 1
        return view

    def _undoable(self, choice_id):
        record = self._choices.get(choice_id)
        if record is None or record.view.state != 'accepted':
            self._reject('already_started', 'Whole-choice undo/replacement is available only before any member starts')
        return record

    def undo(self, choice_id):
        planning_entry(self.encounter)
        with self.lock:
            self.encounter._assert_timeline()
            self._undoable(choice_id)
            self._reservations = tuple(r for r in self._reservations if r.choice_id != choice_id)
            del self._choices[choice_id]
            self.revision += 1

    def replace(self, choice_id, token):
        planning_entry(self.encounter)
        with self.lock:
            self.encounter._assert_timeline()
            self._undoable(choice_id)
            draft, packets, signatures, reservations = self._authorized(token, choice_id)
            return self._accept(draft, packets, signatures, reservations, replacing=choice_id)

    def view(self, choice_id):
        with self.lock:
            if choice_id not in self._choices:
                self._reject('unknown_choice', 'Inspect a current accepted/published choice identity')
            return self._choices[choice_id].view

    def for_action(self, action_id):
        with self.lock:
            return next((r.view for r in self._choices.values()
                         if action_id in r.view.action_ids), None)

    def abort_multiple_action(self, choice_id, *, reason='aborted'):
        """Cancel every unresolved member, preserving actions already finished."""
        planning_entry(self.encounter)
        with self.lock:
            record = self._choices.get(choice_id)
            if (record is None or record.view.state != 'executing'
                    or len(record.members) < 2
                    or not any(member.priority_penalty is not None
                               for member in record.members)):
                self._reject('not_active_multiple_action',
                    'Only an executing declared Multiple-action program can be aborted')
            pending = tuple(aid for aid in record.view.action_ids
                            if aid in self.encounter.pending_action_list)
            for action_id in pending:
                self.encounter._cancel_action(action_id, reason=reason,
                                              _abort_program=False)
            return self._choices[choice_id].view

    def _repeat_completed_programs(self, boundary):
        """Queue one unchanged successor cycle for each completed program."""
        from action import Action
        from copy import copy
        from identifiable import Identifiable

        with self.lock:
            completed = tuple(record for record in self._choices.values()
                if record.view.state == 'finished'
                and record.origin in ('choice', 'multiple-action-cycle')
                and len(record.members) > 1
                and any(member.priority_penalty is not None for member in record.members)
                and all(self._states.get(aid) == 'finished' for aid in record.view.action_ids))
            for record in completed:
                if (self.encounter.end_time is not None
                        and boundary >= self.encounter.end_time):
                    self._choices[record.view.id] = replace(
                        record, origin='multiple-action-cycle-complete')
                    continue
                if any(not isinstance(member.action, Action)
                       or any(callable(object.__getattribute__(member.action, '__dict__').get(name))
                              for name in ('on_schedule', 'on_completed', 'resolve'))
                       or getattr(member.action, 'target_action_id', None) is not None
                       for member in record.members):
                    self._choices[record.view.id] = replace(
                        record, origin='multiple-action-cycle-complete')
                    continue
                first_start = min(packet.start_time for packet in record.prepared)
                last_end = max(packet.end_time for packet in record.prepared)
                cycle_length = last_end - first_start
                if cycle_length <= 0 or (self.encounter.end_time is not None
                                         and boundary + cycle_length > self.encounter.end_time):
                    self._choices[record.view.id] = replace(
                        record, origin='multiple-action-cycle-complete')
                    continue
                members = []
                for member, packet in zip(record.members, record.prepared):
                    action = copy(member.action)
                    data = object.__getattribute__(action, '__dict__')
                    start = boundary + packet.start_time - first_start
                    duration = packet.end_time - packet.start_time
                    data.update(start_time=start, end_time=start + duration,
                                parent_event_id=None, resolution=None)
                    for name in ('result', 'combat_result', 'hit_type', 'canceled_at',
                                 'cancellation_reason', '_activity_started',
                                 '_atomic_acknowledged_boundary', '_atomic_effect_ids',
                                 '_atomic_lifecycle'):
                        data.pop(name, None)
                    Identifiable.__init__(action, data.get('name'))
                    if data.get('strategy') is not None:
                        data['strategy'] = data['strategy'].copy()
                    members.append(ChoiceMember(member.key, action,
                        target_action_key=member.target_action_key,
                        priority_penalty=member.priority_penalty))
                self._choices[record.view.id] = replace(
                    record, origin='multiple-action-cycle-complete')
                view = self.encounter.schedule_choice(tuple(members))
                self._choices[view.id] = replace(self._choices[view.id],
                                                  origin='multiple-action-cycle')

    @property
    def reservations(self):
        with self.lock:
            return self._reservations

    def summary(self):
        with self.lock:
            return {'version': 1,
                'choices': [dict(id=r.view.id, version=r.view.version, state=r.view.state,
                                 action_ids=list(r.view.action_ids), first_start=r.view.first_start)
                            for r in self._choices.values()],
                'reservations': [dict(choice_id=r.choice_id, action_id=r.action_id,
                    object_id=r.object_id, start=r.start, boundary=r.boundary) for r in self._reservations],
                'actions': dict(self._states)}

    def assert_registered(self, action):
        from encounter import BoundaryInvariantError
        known = self._registered.get(action.id)
        if known is None or self._states.get(action.id) not in ('registered', 'executing'):
            raise BoundaryInvariantError('Pending Action bypassed native whole-choice publication')
        if not any(m.action is action for m in self._choices[known[0]].members):
            raise BoundaryInvariantError('Registered Action identity was replaced outside native scheduling')
        if declaration(action) != known[2]:
            raise BoundaryInvariantError('Published Action declaration changed outside native scheduling')

    def assert_accepted(self):
        """Reject edited accepted inputs before physical progression begins."""
        with self.lock:
            for record in self._choices.values():
                if record.view.state == 'accepted':
                    self._publication_check(record)

    def next_start(self, now):
        with self.lock:
            times = [r.view.first_start for r in self._choices.values() if r.view.state == 'accepted']
            times += [p.start_time for aid, (_, p, _) in self._registered.items()
                      if self._states[aid] == 'registered']
            return min((t for t in times if t > now), default=math.inf)

    def _publication_check(self, record):
        for member, packet, signature in zip(record.members, record.prepared, record.signatures):
            current_declaration = declaration(member.action)
            current_signature = ((member.key, member.priority_penalty, current_declaration)
                                 if member.priority_penalty is not None
                                 else (member.key, current_declaration))
            if current_signature != signature:
                self._reject('edited_action', 'Accepted declarations changed; undo or replace the whole choice')
            self.encounter._validate_prepared_schedule(member.action, packet)
            if packet.start_time == self.encounter.time and self.encounter.active_boundary is None:
                self._handoff_ready(record.view.id, packet)
        if type(self.encounter.pending_action_list) is not list or type(self.encounter.universe.event_history) is not dict:
            self._reject('unsupported_registry', 'Publication requires native list/dict scheduling stores')

    def _handoff_ready(self, choice_id, packet):
        for book in self.encounter.universe._choice_books:
            for old in book._reservations:
                if (old.choice_id != choice_id and old.object_id in packet.active_object_ids
                        and old.boundary <= packet.start_time
                        and book.encounter.last_processed_boundary < old.boundary):
                    self._reject('handoff_unsettled',
                        f'Object {old.object_id} requires prior boundary {old.boundary} '
                        'settlement before this Action starts')

    def _publish_updates(self, record):
        """Only plain native metadata writes; deliberately no extension callbacks."""
        guard_legacy_encounter(self.encounter, "direct ChoiceBook._publish_updates")
        enc = self.encounter
        for member, packet in zip(record.members, record.prepared):
            data = object.__getattribute__(member.action, '__dict__')
            data.update((name, value) for name, value in packet.initialization if name != 'start_position')
            data.update(end_time=packet.end_time, parent_event_id=enc.id)
        enc.universe.event_history.update({m.action.id: m.action for m in record.members})
        enc.pending_action_list.extend(record.view.action_ids)
        for member, packet in zip(record.members, record.prepared):
            self._registered[packet.action_id] = (record.view.id, packet, declaration(member.action))
            self._states[packet.action_id] = 'registered'
        self._choices[record.view.id] = replace(record, view=replace(record.view, state='executing'))

    def publish(self, choice_id):
        guard_legacy_encounter(self.encounter, "direct ChoiceBook.publish")
        with self.lock:
            enc = self.encounter
            enc._assert_timeline()
            record = self._undoable(choice_id)
            if enc.active_boundary is not None or record.view.first_start != enc.time:
                self._reject('start_fence', 'Publish exactly at first start, after any boundary settlement')
            self._publication_check(record)
            actions_before = [(m.action, dict(object.__getattribute__(m.action, '__dict__'))) for m in record.members]
            history, pending = dict(enc.universe.event_history), list(enc.pending_action_list)
            registered, states = dict(self._registered), dict(self._states)
            try:
                self._publish_updates(record)
                self._start_due(enc.time, record.view.action_ids)
            except Exception:
                # Bounded publication rollback, not rollback of Action effects.
                for action, data in actions_before:
                    target = object.__getattribute__(action, '__dict__')
                    target.clear(); target.update(data)
                enc.universe.event_history.clear(); enc.universe.event_history.update(history)
                enc.pending_action_list[:] = pending
                self._registered, self._states = registered, states
                self._choices[choice_id] = record
                raise
            self.revision += 1
            return self._choices[choice_id].view

    def _start_due(self, now, action_ids=None):
        guard_legacy_encounter(self.encounter, "direct ChoiceBook._start_due")
        from activities import RunAction
        from melee_defense import MeleeDefense
        updates = []
        for aid, (_, packet, _) in self._registered.items():
            if action_ids is not None and aid not in action_ids:
                continue
            if self._states[aid] != 'registered' or packet.start_time != now:
                continue
            self._handoff_ready(self._registered[aid][0], packet)
            action = self.encounter.universe.get_event_by_id(aid)
            initial = {}
            if type(action) is RunAction:
                actor = self.encounter.get_being(action.actor_id)
                initial['start_position'] = None if actor is None else actor.get_position()
            if type(action) is MeleeDefense:
                strike = self.encounter.universe.get_event_by_id(action.target_action_id)
                if strike is not None:
                    initial['threat_at_schedule'] = ((strike.id, strike._status(self.encounter)[0] == 'in_reach'),)
                if action.kind == 'yield':
                    actor = self.encounter.get_being(action.actor_id)
                    attacker = self.encounter.get_being(action.target_id)
                    initial['start_position'] = None if actor is None else actor.get_position()
                    initial['target_position'] = None if attacker is None else attacker.get_position()
            updates.append((aid, action, initial))
        for aid, action, initial in updates:
            initial['_activity_started'] = True
            object.__getattribute__(action, '__dict__').update(initial)
            self._states[aid] = 'executing'

    def publish_due(self, now):
        guard_legacy_encounter(self.encounter, "direct ChoiceBook.publish_due")
        with self.lock:
            for cid, record in tuple(self._choices.items()):
                if record.view.state == 'accepted':
                    if record.view.first_start < now:
                        self._reject('missed_start', 'Accepted choice start fence was missed')
                    if record.view.first_start == now:
                        self.publish(cid)
            self._start_due(now)

    def completed(self, action_id):
        guard_legacy_encounter(self.encounter, "direct ChoiceBook.completed")
        with self.lock:
            self._states[action_id] = 'finished'
            self.revision += 1

    def cancelled(self, action_id):
        planning_entry(self.encounter)
        with self.lock:
            self._states[action_id] = 'cancelled'
            active = self.encounter.active_boundary
            self._reservations = tuple(
                replace(r, boundary=active) if r.action_id == action_id else r
                for r in self._reservations if r.action_id != action_id or (
                    active is not None and r.start <= active))
            if active is None:
                for cid, record in tuple(self._choices.items()):
                    if record.view.state == 'executing' and all(
                            self._states.get(aid) in ('finished', 'cancelled') for aid in record.view.action_ids):
                        self._choices[cid] = replace(record, view=replace(record.view, state='finished'))
            self.revision += 1

    def settled(self, boundary):
        guard_legacy_encounter(self.encounter, "direct ChoiceBook.settled")
        with self.lock:
            self._reservations = tuple(r for r in self._reservations if r.boundary > boundary)
            for cid, record in tuple(self._choices.items()):
                if record.view.state == 'executing' and all(
                        self._states.get(aid) in ('finished', 'cancelled') for aid in record.view.action_ids):
                    self._choices[cid] = replace(record, view=replace(record.view, state='finished'))
            self.revision += 1

    def assert_exportable(self, *, replay=False):
        with self.lock:
            for owner, record in ((book, r) for book in self.encounter.universe._choice_books
                                  for r in book._choices.values()):
                live = record.view.state == 'accepted' or any(
                    owner._states.get(aid) in ('registered', 'executing') for aid in record.view.action_ids)
                live = live or any(r.choice_id == record.view.id for r in owner._reservations)
                if live and not (replay and owner is self and record.origin == 'single-adapter'
                                 and record.view.state == 'executing'
                                 and all(owner._states.get(aid) != 'registered' for aid in record.view.action_ids)):
                    self._reject('unsupported_choice_export',
                        'Live choice commitments require unsupported coherent restore; '
                        'only checked single-Action facade replay is supported')

    def _schedule_snapshot(self, actions):
        enc = self.encounter
        return ([(a, dict(object.__getattribute__(a, '__dict__'))) for a in actions],
                dict(enc.universe.event_history), list(enc.pending_action_list),
                list(enc.cancelled_action_list), dict(self._choices), self._reservations,
                dict(self._registered), dict(self._states), self.revision, set(self._closed_drafts))

    def _restore_schedule(self, snapshot):
        actions, events, pending, cancelled, choices, reservations, registered, states, revision, closed = snapshot
        enc = self.encounter
        for action, data in actions:
            target = object.__getattribute__(action, '__dict__')
            target.clear(); target.update(data)
        enc.universe.event_history.clear(); enc.universe.event_history.update(events)
        enc.pending_action_list[:] = pending
        enc.cancelled_action_list[:] = cancelled
        self._choices, self._reservations = choices, reservations
        self._registered, self._states = registered, states
        self.revision, self._closed_drafts = revision, closed

    def schedule_single(self, action, interrupt=None):
        planning_entry(self.encounter)
        validate_action_contract(self.encounter, action)
        from encounter import BoundaryInvariantError
        with self.lock:
            enc = self.encounter
            enc._assert_timeline()
            if not enc.initiated:
                raise RuntimeError('Encounter must be initiated before scheduling actions')
            draft = self.propose((action,))
            errors, packets, signatures, reservations = self._evaluate(draft, interrupt=interrupt)
            if errors:
                first = errors[0]
                if first.code == 'unsupported':
                    raise UnsupportedScheduleExtension(first.reason)
                if first.code == 'boundary':
                    raise BoundaryInvariantError(first.reason)
                raise ChoiceRejected(errors)
            affected = [action]
            if interrupt is not None:
                affected.append(enc.universe.get_event_by_id(interrupt))
            snapshot = self._schedule_snapshot(affected)
            try:
                view = self._accept(draft, packets, signatures, reservations, origin='single-adapter')
                if interrupt is not None:
                    enc.cancel_action(interrupt)
                if view.first_start == enc.time and enc.active_boundary is None and enc.progression_mode == 'legacy':
                    self.publish(view.id)
            except Exception:
                self._restore_schedule(snapshot)
                raise
            return action.id

    def schedule_complete(self, actions):
        """Convenience adapter: one locked complete-set validation/publication."""
        planning_entry(self.encounter)
        validate_choice_actions(self.encounter, actions)
        with self.lock:
            self.encounter._assert_timeline()
            draft = self.propose(actions)
            errors, packets, signatures, reservations = self._evaluate(draft)
            if errors:
                raise ChoiceRejected(errors)
            snapshot = self._schedule_snapshot([m.action for m in draft.members])
            try:
                view = self._accept(draft, packets, signatures, reservations)
                if view.first_start == self.encounter.time and self.encounter.active_boundary is None and self.encounter.progression_mode == 'legacy':
                    view = self.publish(view.id)
                return view
            except Exception:
                self._restore_schedule(snapshot)
                raise

    def actor_planned_now(self, actor_id):
        with self.lock:
            return any(p.actor_id == actor_id and p.start_time <= self.encounter.time
                       and self._paused.get(p.action_id, {}).get('paused_at') is None
                       and object.__getattribute__(m.action, '__dict__').get('event_type') not in ('delay', 'hold')
                       for record in self._choices.values() if record.view.state == 'accepted'
                       for m, p in zip(record.members, record.prepared))

    def effective_end(self, action):
        with self.lock:
            row=self._paused.get(action.id)
            if row is None:return action.end_time
            if row['paused_at'] is not None:
                return self.encounter.time + row['remaining']
            return row['effective_end']

    def is_paused(self, action_id):
        with self.lock:
            row=self._paused.get(action_id)
            return row is not None and row['paused_at'] is not None

    def pause_action(self, action_id):
        """Pause one eligible running Action at the current committed second."""
        planning_entry(self.encounter)
        with self.lock:
            self.encounter._assert_timeline()
            action=self.encounter.universe.get_event_by_id(action_id)
            if (action is None or action_id not in self.encounter.pending_action_list
                    or self._states.get(action_id)!='executing'
                    or action.start_time>=self.encounter.time):
                raise ValueError('Pause requires this Being’s started pending Action after a committed second')
            event=object.__getattribute__(action,'__dict__').get('event_type')
            if event in ('swing','thrust','charge','spell','cast','spellcasting'):
                raise ValueError('Momentum-dependent Actions and spellcasting cannot be paused')
            if self.is_paused(action_id):
                raise ValueError('Action is already paused')
            end=self.effective_end(action)
            remaining=end-self.encounter.time
            if remaining<=0:
                raise ValueError('Action has no remaining duration to pause')
            prior=self._paused.get(action_id, {})
            self._paused[action_id]={
                'original_end': action.end_time,
                'effective_end': end,
                'paused_at': self.encounter.time,
                'remaining': remaining,
                'total_paused': prior.get('total_paused',0),
            }
            self.revision=self.revision+1
            return self._paused[action_id].copy()

    def resume_action(self, action_id):
        """Resume the same Action identity with its unspent active duration."""
        planning_entry(self.encounter)
        with self.lock:
            self.encounter._assert_timeline()
            row=self._paused.get(action_id)
            if (row is None or row['paused_at'] is None
                    or action_id not in self.encounter.pending_action_list
                    or self._states.get(action_id)!='executing'):
                raise ValueError('Resume requires this Being’s paused pending Action')
            elapsed=self.encounter.time-row['paused_at']
            if elapsed<0:
                raise ValueError('Encounter time precedes the pause boundary')
            remaining=row['remaining']
            row['effective_end']=self.encounter.time+remaining
            row['total_paused']+=elapsed
            row['paused_at']=None
            row['remaining']=None
            self.revision=self.revision+1
            return row.copy()
