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


def declaration(action, *, _initialization=None):
    """Capture plan inputs, not mutable outcome fields or live Being state."""
    data = object.__getattribute__(action, '__dict__')
    if _initialization is not None:
        data = dict(data, **_initialization)
    names = ('id', 'universe', 'event_type', 'start_time', 'end_time', 'actor_id',
             'target_id', 'instrument_id', 'parent_event_id', 'encounter', 'reach',
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
                signatures.append((member.key, declaration(member.action)))
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
                        errors.append(ChoiceDiagnostic('active_object_conflict', member.key,
                            f'Object {object_id} is actively reserved by {other.action_id}; '
                            'edit the Object or interval (handoff requires boundary settlement)',
                            object_id, (reservation.start, reservation.boundary),
                            other.action_id, other.choice_id, (other.start, other.boundary)))
                reservations.append(reservation)
        for member, packet in packets:
            for record in (r for book in self.encounter.universe._choice_books for r in book._choices.values()):
                if record.view.id == exclude_choice:
                    continue
                if any(packet.action_id == p.action_id for p in record.prepared):
                    errors.append(ChoiceDiagnostic('action_committed', member.key,
                        'This Action already belongs to an accepted or published choice'))
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
            if (member.key, declaration(member.action)) != signature:
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
                       and object.__getattribute__(m.action, '__dict__').get('event_type') != 'delay'
                       for record in self._choices.values() if record.view.state == 'accepted'
                       for m, p in zip(record.members, record.prepared))
