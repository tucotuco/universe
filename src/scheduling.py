"""Increment 1: native, read-only preparation of a single Action schedule.

Only reviewed native preparers execute. This is not a sandbox for arbitrary
Python callbacks, a choice store, or a resolution transaction.
"""
from dataclasses import dataclass
import inspect


class UnsupportedScheduleExtension(TypeError):
    """An extension has no reviewed, side-effect-free scheduling adapter."""


@dataclass(frozen=True)
class PreparedSchedule:
    action_id: str
    start_time: float
    end_time: float
    actor_id: str
    target_id: str | None
    instrument_id: str | None
    parent_event_id: str | None
    active_object_ids: tuple = ()
    initialization: tuple = ()

    @classmethod
    def from_action(cls, action, *, end_time=None, initialization=()):
        # No action getters, descriptors, hooks, or external callbacks execute.
        data = object.__getattribute__(action, '__dict__')
        instrument = data.get('instrument_id')
        active = ((instrument,) if instrument is not None and
                  data['event_type'] in ('swing', 'thrust', 'parry', 'throw') else ())
        return cls(data['id'], data['start_time'],
                   data['end_time'] if end_time is None else end_time,
                   data['actor_id'], data.get('target_id'), instrument,
                   data.get('parent_event_id'), active, tuple(initialization))


def native_preparer(action):
    """Return trusted code without invoking an extension to test its purity.

    Resolver-only Action subclasses may inherit the base scheduling contract.
    Custom scheduling and specialized subclasses require a reviewed adapter;
    merely naming a callback prepare_schedule does not make it safe.
    """
    from action import Action
    from activities import RunAction, SpotAction
    from activities import ThrowAction
    from melee_combat import MeleeStrike
    from melee_defense import MeleeDefense
    from group_observation import ObserveGroupAction
    from history_conversation import AskAboutPastAction

    cls = type(action)
    native = (Action, RunAction, SpotAction, ThrowAction, MeleeStrike, MeleeDefense,
              ObserveGroupAction, AskAboutPastAction)
    if not issubclass(cls, Action):
        raise UnsupportedScheduleExtension(
            'Encounter scheduling requires an Action with a native preparation '
            'contract; ordinary Universe Events remain separate')
    # Inspect class metadata before reading instance data; an extension may
    # otherwise hide executable descriptors even behind __dict__.
    for owner in type.__getattribute__(cls, '__mro__'):
        if owner in native:
            break
        if '__dict__' in type.__getattribute__(owner, '__dict__'):
            raise UnsupportedScheduleExtension('Custom instance dictionary descriptors are unsupported')
    data = object.__getattribute__(action, '__dict__')
    if (inspect.getattr_static(cls, '__getattribute__') is not object.__getattribute__
            or inspect.getattr_static(cls, '__getattr__', None) is not None
            or inspect.getattr_static(cls, '__setattr__') is not object.__setattr__
            or 'on_schedule' in data
            or inspect.getattr_static(cls, 'on_schedule', None) is not None
            or 'prepare_schedule' in data):
        raise UnsupportedScheduleExtension(
            'Opaque scheduling hooks/attribute callbacks are unsupported; '
            'use an inherited native preparation contract or a reviewed adapter')
    for name in ('get_instrument', 'damage_potential', '_status'):
        if name in data:
            raise UnsupportedScheduleExtension('Scheduling helper overrides require a reviewed adapter')
    for name in ('id', 'actor_id', 'target_id', 'instrument_id', 'parent_event_id',
                 'target_action_id', 'event_type'):
        value = data.get(name)
        if value is not None and type(value) is not str:
            raise ValueError(f'Scheduling field {name} must be a native string ID/name')
    for name in ('start_time', 'end_time'):
        value = data.get(name)
        if value is not None and type(value) not in (int, float):
            raise ValueError(f'Scheduling field {name} must be a native numeric time')
    if cls not in native:
        if inspect.getattr_static(cls, 'prepare_schedule', None) is not Action.prepare_schedule:
            raise UnsupportedScheduleExtension('Custom prepare_schedule requires a reviewed native adapter')
        for name in ('id', 'universe', 'event_type', 'start_time', 'end_time',
                     'actor_id', 'target_id', 'instrument_id', 'parent_event_id'):
            if inspect.getattr_static(cls, name, None) is not None:
                raise UnsupportedScheduleExtension('Scheduling field descriptors require a reviewed adapter')
        return Action.prepare_schedule
    return cls.prepare_schedule
