"""Inactive portable descriptors for a small, closed native Action subset.

This module never reconstructs, registers, schedules, resolves, or publishes an
Action. Live ChoiceBook signatures remain process-local mutation guards.
"""
from dataclasses import dataclass
import math

from action_choice import _Accepted, ChoiceMember, ChoiceView, declaration
from scheduling import PreparedSchedule


DESCRIPTOR_SCHEMA = 'universe.accepted-action-choice/1'
_DECLARATION_FIELDS = (
    'id', 'universe', 'event_type', 'start_time', 'end_time', 'actor_id',
    'target_id', 'instrument_id', 'parent_event_id', 'encounter', 'reach',
    'kind', 'target_action_id', 'minimum_distance', 'practice_experience',
    'max_distance', 'spotting_conditions', 'declared_roll', 'episode_time', 'topic', 'generate',
    'substituted_claim', 'received_accounts', 'seed', 'random_key', 'observer',
    'interpreter', 'ledger', 'experience_policy', 'focus_category',
    'get_instrument', 'damage_potential', '_status', 'on_schedule',
    'prepare_schedule',
)
_ACTION_TYPES = None


class ChoiceDescriptorRejected(ValueError):
    """The accepted choice is outside the reviewed data-only subset."""


@dataclass(frozen=True)
class PortableActionDeclaration:
    adapter: str
    action_id: str
    fields: tuple


@dataclass(frozen=True)
class PortableChoiceMember:
    key: str
    action: PortableActionDeclaration
    target_action_key: str | None
    prepared: tuple


@dataclass(frozen=True)
class PortableAcceptedChoice:
    schema: str
    choice_id: str
    version: int
    state: str
    origin: str
    action_ids: tuple
    first_start: tuple
    members: tuple
    reservations: tuple

    def to_data(self):
        """Return a recursively immutable graph of primitive data and tuples."""
        return (self.schema, self.choice_id, self.version, self.state, self.origin,
                self.action_ids, self.first_start,
                tuple((m.key, m.action.adapter, m.action.action_id,
                       m.action.fields, m.target_action_key, m.prepared)
                      for m in self.members), self.reservations)


def _require(test, message):
    if not test:
        raise ChoiceDescriptorRejected(message)


def _number(value, label):
    _require(type(value) in (int, float), f'{label} must be an exact int or float')
    if type(value) is int:
        return ('integer', str(value))
    _require(math.isfinite(value), f'{label} must be finite')
    return ('binary64', value.hex())


def _scalar(value, label):
    if value is None:
        return ('null',)
    if type(value) is bool:
        return ('boolean', value)
    if type(value) is str:
        return ('string', value)
    if type(value) in (int, float):
        return _number(value, label)
    if type(value) is tuple and all(type(item) is str for item in value):
        return ('strings', value)
    raise ChoiceDescriptorRejected(f'{label} is not a supported declaration scalar')


def _primitive_tree(value):
    if value is None or type(value) in (str, bool, int, float):
        return True
    return type(value) is tuple and all(_primitive_tree(item) for item in value)


def _registry_ref(world, encounter, identifier, role):
    if identifier is None:
        return ('null',)
    _require(type(identifier) is str and identifier, f'{role} must be a nonempty logical ID')
    registry = world.object_registry.object_instances
    matches = [(key, value) for key, value in registry.items()
               if key == identifier or object.__getattribute__(value, '__dict__').get('id') == identifier]
    _require(len(matches) == 1 and matches[0][0] == identifier,
             f'{role} logical ID is missing or ambiguous')
    value = matches[0][1]
    from checkpoint_inventory import _TYPES
    _require(type(value) in _TYPES, f'{role} is not a reviewed native entity type')
    _require(encounter.get_entity(identifier) is value,
             f'{role} does not resolve to the registered Encounter entity')
    return ('entity', identifier)


def _action_type_map():
    global _ACTION_TYPES
    if _ACTION_TYPES is None:
        from activities import RunAction, SpotAction
        _ACTION_TYPES = {RunAction: 'native.run-action/1',
                         SpotAction: 'native.spot-action/1'}
    return _ACTION_TYPES


def _action_descriptor(action, world, encounter):
    from being import BeingInstance
    from strategy import Strategy

    adapter = _action_type_map().get(type(action))
    _require(adapter is not None,
             'only exact native RunAction and SpotAction declarations are supported')
    data = object.__getattribute__(action, '__dict__')
    _require(type(data) is dict, 'Action field storage is not native')
    expected = {
        'native.run-action/1': {
            'id','name','type','universe','event_type','start_time','end_time',
            'location','parent_event_id','actor_id','target_id','instrument_id',
            'strategy','resolution','minimum_distance','practice_experience',
            'start_position','displacement'},
        'native.spot-action/1': {
            'id','name','type','universe','event_type','start_time','end_time',
            'location','parent_event_id','actor_id','target_id','instrument_id',
            'strategy','resolution','spotting_conditions','declared_roll',
            'roll','path_status','_encounter','ledger','group_fully_visible'},
    }[adapter]
    _require(not (set(data) - expected), 'unknown native Action fields are not portable')
    action_id = data.get('id')
    _require(type(action_id) is str and action_id, 'Action requires a stable logical ID')
    _require(not any(key == action_id or
                     object.__getattribute__(event,'__dict__').get('id') == action_id
                     for key,event in world.event_history.items()),
             'Action ID collides with an existing Universe Event')
    _require(data.get('universe') is world, 'Action belongs to a different Universe')
    _require(data.get('event_type') == ('run' if adapter.startswith('native.run') else 'spot'),
             'Action event type does not match its reviewed adapter')
    _require(data.get('type') == type(action).__name__,
             'native Action type field is inconsistent')
    _require(data.get('location') is None and data.get('parent_event_id') is None,
             'Action location or parent-event semantics are not adapted')
    _require(data.get('instrument_id') is None,
             'active instrument semantics are not supported by this descriptor')
    _require(data.get('resolution') is None,
             'an Action with an existing outcome is not an accepted pending declaration')
    _require(type(data.get('strategy')) is Strategy,
             'Action strategy is not the exact native Strategy type')
    strategy = object.__getattribute__(data['strategy'], '__dict__')
    _require(type(strategy) is dict and set(strategy) ==
             {'attack','defense','timing','extra_damage'}, 'Strategy fields are not closed')
    strategy_data = tuple((name, _number(strategy[name], 'strategy.'+name))
                          for name in ('attack','defense','timing','extra_damage'))
    _require(data.get('universe') is world, 'universe reference mismatch')

    if adapter == 'native.run-action/1':
        _require(data.get('target_id') is None and data.get('start_position') is None
                 and data.get('displacement') is None,
                 'RunAction must be pending and have no target or sampled outcome')
        specific = ('minimum_distance','practice_experience')
        _require(data.get('declared_roll') is None, 'unsupported RunAction declaration field')
    else:
        _require(data.get('target_id') is not None and data.get('_encounter') is None,
                 'SpotAction must be pending and unbound to a live Encounter')
        _require(data.get('ledger') is None and data.get('group_fully_visible') is False,
                 'Group observation Spot declarations are not yet portable')
        _require(data.get('roll') is None
                 and data.get('path_status') is None,
                 'SpotAction contains sampled outcome state')
        specific = ('spotting_conditions','declared_roll')
        from discovery import SpottingConditions
        try:
            SpottingConditions(data.get('spotting_conditions'))
        except (TypeError, ValueError) as exc:
            raise ChoiceDescriptorRejected(str(exc)) from exc
    _require(_registry_ref(world, encounter, data.get('actor_id'), 'actor') != ('null',),
             'Action actor is required')
    actor = world.object_registry.object_instances[data['actor_id']]
    _require(type(actor) is BeingInstance, 'Action actor must be a registered native Being')
    supported_refs = {'actor_id','target_id'}
    for name in _DECLARATION_FIELDS:
        value = data.get(name)
        if name == 'id':
            encoded = ('action-id', action_id)
        elif name == 'universe':
            encoded = ('universe', world.id)
        elif name == 'event_type':
            encoded = ('string', data['event_type'])
        elif name in supported_refs:
            encoded = _registry_ref(world, encounter, value, name)
        elif name in specific:
            encoded = _scalar(value, name)
        elif name in ('start_time','end_time'):
            encoded = _number(value, name)
        else:
            _require(value is None, f'{name} is not adapted for {adapter}')
            encoded = ('null',)
        # The stored Action signature deliberately uses process-local addresses
        # for type/reference checks. They are not copied into this descriptor.
        if name not in ('id','universe','event_type','start_time','end_time','actor_id','target_id',*specific):
            _require(encoded == ('null',), f'{name} is not adapted for {adapter}')
    fields = tuple((name, next(encoded for field_name, encoded in _iter_encoded_fields(
        data, world, encounter, specific) if field_name == name)) for name in _DECLARATION_FIELDS)
    # Preserve display metadata separately; it is not a live scheduling input.
    name = data.get('name')
    _require(name is None or type(name) is str, 'Action name must be plain text')
    fields += (('strategy_effort', strategy_data), ('display_name', _scalar(name, 'name')))
    return PortableActionDeclaration(adapter, action_id, fields)


def _iter_encoded_fields(data, world, encounter, specific):
    for name in _DECLARATION_FIELDS:
        value = data.get(name)
        if name == 'id': encoded=('action-id', value)
        elif name == 'universe': encoded=('universe', world.id)
        elif name == 'event_type': encoded=('string', value)
        elif name in ('actor_id','target_id'): encoded=_registry_ref(world, encounter, value, name)
        elif name in specific: encoded=_scalar(value, name)
        elif name in ('start_time','end_time'): encoded=_number(value, name)
        else: encoded=('null',)
        yield name, encoded


def describe_native_declaration(action, world, encounter):
    """Describe one exact supported pending Action, without registering it."""
    return _action_descriptor(action, world, encounter)


def _prepared_data(packet, action, world, encounter, adapter):
    _require(type(packet) is PreparedSchedule, 'choice has an unreviewed schedule packet')
    _require(packet.action_id == action.id and packet.actor_id == action.actor_id,
             'prepared packet identity does not match its Action')
    _require(packet.target_id == action.target_id and packet.instrument_id is None,
             'prepared participant/resource references do not match Action declaration')
    _require(packet.parent_event_id is None, 'prepared parent-event binding is unsupported')
    _require(type(packet.active_object_ids) is tuple,
             'active-resource list is not a native tuple')
    _require(type(packet.initialization) is tuple and all(
        type(pair) is tuple and len(pair)==2 and type(pair[0]) is str
        for pair in packet.initialization),
        'prepared initialization records are not closed native pairs')
    for oid in packet.active_object_ids:
        _registry_ref(world, encounter, oid, 'reserved Object')
    initialization=[]
    for key, value in packet.initialization:
        if adapter == 'native.spot-action/1' and key == '_encounter' and value is encounter:
            initialization.append((key, ('encounter', encounter.id)))
        elif adapter == 'native.run-action/1' and key == 'start_position':
            from spatial.state import CartesianPosition
            _require(type(value) is CartesianPosition, 'RunAction preparation position is unsupported')
            initialization.append((key, ('cartesian-position', tuple(_number(v, 'position') for v in value.as_tuple()))))
        else:
            raise ChoiceDescriptorRejected('prepared Action initialization is not in the closed adapter')
    return (packet.action_id, _number(packet.start_time,'prepared.start_time'),
            _number(packet.end_time,'prepared.end_time'), ('entity',packet.actor_id),
            ('null',) if packet.target_id is None else ('entity',packet.target_id),
            ('null',) if packet.instrument_id is None else ('object',packet.instrument_id),
            ('null',) if packet.parent_event_id is None else ('event',packet.parent_event_id),
            tuple(('object', oid) for oid in packet.active_object_ids), tuple(initialization))


def _all_data(value):
    if value is None or type(value) in (str, bool, int, float):
        return True
    if type(value) is tuple:
        return all(_all_data(v) for v in value)
    return False


def describe_accepted_choice(world, encounter, choice_id):
    """Create a detached descriptor for an accepted, not-yet-published choice."""
    from universe import Universe
    from encounter import Encounter
    from action_choice import ChoiceBook

    _require(type(world) is Universe and type(encounter) is Encounter
             and encounter.universe is world, 'native Universe/Encounter roots required')
    book = encounter._choice_book
    _require(type(book) is ChoiceBook and book.encounter is encounter,
             'choice has no exact native ChoiceBook owner')
    with book.lock:
        return _describe_accepted_choice_locked(world, encounter, book, choice_id)


def _describe_accepted_choice_locked(world, encounter, book, choice_id):
    from action_choice import Reservation

    record = book._choices.get(choice_id)
    _require(type(record) is _Accepted and record.view.id == choice_id,
             'choice identity is absent or ambiguous')
    _require(record.view.state == 'accepted',
             'only accepted prepublication choices are supported')
    _require(record.origin in ('choice','single-adapter'), 'choice origin is unsupported')
    _require(type(record.view) is ChoiceView and type(record.view.version) is int
             and record.view.version > 0, 'invalid native choice view')
    _require(type(record.members) is tuple and type(record.prepared) is tuple
             and type(record.signatures) is tuple and record.members,
             'accepted choice member data is not closed')
    _require(len(record.members)==len(record.prepared)==len(record.signatures),
             'accepted choice member counts disagree')
    member_ids=[];member_keys=set();members=[];expected_reservations=[]
    for member, packet, signature in zip(record.members, record.prepared, record.signatures):
        _require(type(member) is ChoiceMember and type(member.key) is str and member.key,
                 'choice member key is unsupported')
        _require(member.key not in member_keys,'duplicate choice member key')
        member_keys.add(member.key)
        _require(member.target_action_key is None,
                 'cross-Action dependency keys require a separate native adapter')
        action = member.action
        declaration_data = _action_descriptor(action, world, encounter)
        _require(type(signature) is tuple and len(signature)==2
                 and signature[0]==member.key and _primitive_tree(signature[1]),
                 'accepted live signature is not a closed native signature tree')
        _require(signature == (member.key, declaration(action)),
                 'live accepted signature is stale; recapture after native validation')
        _require(action.id not in member_ids, 'duplicate Action logical ID in choice')
        member_ids.append(action.id)
        prepared = _prepared_data(packet, action, world, encounter, declaration_data.adapter)
        _require(_number(packet.start_time,'prepared.start_time') == _number(action.start_time,'action.start_time')
                 and _number(packet.end_time,'prepared.end_time') == _number(action.end_time,'action.end_time'),
                 'prepared fractional timing differs from accepted Action declaration')
        for object_id in packet.active_object_ids:
            expected_reservations.append((action.id, object_id, packet.start_time,
                                          math.ceil(packet.end_time)))
        members.append(PortableChoiceMember(member.key, declaration_data, None, prepared))
    other_ids=[]
    for other in book._choices.values():
        if type(other) is not _Accepted or other is record:
            continue
        _require(type(other.members) is tuple,
                 'other accepted choice has an unclosed member collection')
        for other_member in other.members:
            _require(type(other_member) is ChoiceMember,
                     'other accepted choice has an unsupported member record')
            other_action=object.__getattribute__(other_member,'__dict__').get('action')
            other_data=object.__getattribute__(other_action,'__dict__')
            other_id=other_data.get('id')
            _require(type(other_id) is str and other_id,
                     'other accepted choice has no stable Action ID')
            other_ids.append(other_id)
    _require(not set(member_ids).intersection(other_ids),
             'Action logical ID is already owned by another accepted choice')
    _require(tuple(member_ids) == record.view.action_ids,
             'choice view member order does not match accepted declarations')
    _require(_number(record.view.first_start,'choice.first_start') ==
             _number(min(packet.start_time for packet in record.prepared),'prepared.first_start'),
             'choice start fence does not match prepared member times')
    actual=[]
    _require(type(book._reservations) is tuple,
             'reservation collection is not a native tuple')
    for reservation in book._reservations:
        _require(type(reservation) is Reservation,
                 'reservation record is outside the native closed type')
        if reservation.choice_id != choice_id:
            continue
        _require(type(reservation.action_id) is str
                 and type(reservation.object_id) is str,
                 'reservation record is outside the native closed type')
        actual.append((reservation.action_id, reservation.object_id,
                       _number(reservation.start,'reservation.start'),
                       _number(reservation.boundary,'reservation.boundary')))
    expected_encoded=[(action_id,object_id,_number(start,'reservation.start'),
                       _number(boundary,'reservation.boundary'))
                      for action_id,object_id,start,boundary in expected_reservations]
    _require(actual == expected_encoded,
             'accepted Object reservations disagree with prepared active resources')
    reservations=[]
    for action_id, object_id, start, boundary in actual:
        _registry_ref(world, encounter, object_id, 'reserved Object')
        reservations.append((action_id, ('object',object_id), start, boundary))
    descriptor=PortableAcceptedChoice(
        DESCRIPTOR_SCHEMA, choice_id, record.view.version, record.view.state,
        record.origin, tuple(member_ids), _number(record.view.first_start,'choice.first_start'),
        tuple(members), tuple(reservations))
    _require(_all_data(descriptor.to_data()), 'portable choice descriptor contains a live reference')
    return descriptor
