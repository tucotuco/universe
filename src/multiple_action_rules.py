"""Pure priority-allocation rules for declared Multiple-action programs.

This module encodes only the adopted overlap penalty table. It does not
authorize an Action combination, allocate skill/ability points, or resolve
effects; those remain responsibilities of the complete native program.
"""

import math


class MultipleActionRuleError(ValueError):
    """A proposed priority allocation contradicts the adopted rule table."""


_PENALTY_MULTISETS = {
    1: ((0,),),
    2: ((0, 3), (1, 2)),
    3: ((0, 1, 5), (0, 2, 4), (1, 2, 3)),
    4: ((0, 1, 2, 6), (0, 1, 3, 5), (0, 2, 3, 4)),
}


def validate_priority_penalties(penalties):
    """Validate one simultaneous action set's assigned penalty magnitudes.

    Penalty magnitudes are nonnegative integers; a caller applies them as
    negative adjustments to the component actions. Since the adopted rule
    permits assigning any table priority to any action, action order is not
    relevant to this multiset check.
    """
    if type(penalties) not in (tuple, list) or not 1 <= len(penalties) <= 4:
        raise MultipleActionRuleError('priority allocation must contain one through four simultaneous Actions')
    if any(type(value) is not int or value < 0 for value in penalties):
        raise MultipleActionRuleError('priority penalties must be nonnegative integers')
    values = tuple(sorted(penalties))
    if values not in _PENALTY_MULTISETS[len(values)]:
        required = 3 * (len(values) - 1)
        raise MultipleActionRuleError(
            f'priority penalties must match an adopted {len(values)}-Action allocation totaling {required}')
    return values


def validate_priority_schedule(intervals, penalties):
    """Validate fixed priorities across every overlapping interval segment.

    ``intervals`` maps component IDs to half-open ``(start, end)`` times;
    ``penalties`` maps the same IDs to their fixed priority penalty magnitude.
    Actions that never overlap impose no simultaneous penalty-table check.
    """
    if type(intervals) is not dict or not intervals:
        raise MultipleActionRuleError('a Multiple-action schedule needs component intervals')
    if type(penalties) is not dict or set(penalties) != set(intervals):
        raise MultipleActionRuleError('every component needs exactly one fixed priority penalty')
    points = set()
    for identity, interval in intervals.items():
        if type(identity) is not str or not identity:
            raise MultipleActionRuleError('component identities must be nonempty text')
        if type(interval) not in (tuple, list) or len(interval) != 2:
            raise MultipleActionRuleError('component interval must be a start/end pair')
        start, end = interval
        if (type(start) not in (int, float) or type(end) not in (int, float)
                or not math.isfinite(start) or not math.isfinite(end) or end <= start):
            raise MultipleActionRuleError('component intervals must be finite and positive')
        points.update((float(start), float(end)))
    for value in penalties.values():
        if type(value) is not int or value < 0:
            raise MultipleActionRuleError('priority penalties must be nonnegative integers')

    ordered = sorted(points)
    for start, end in zip(ordered, ordered[1:]):
        if end <= start:
            continue
        active = tuple(identity for identity, (first, last) in intervals.items()
                       if first < end and last > start)
        if len(active) > 1:
            validate_priority_penalties(tuple(penalties[identity] for identity in active))
    return True


def validate_resource_budget(skill_pools, priorities, strategies, *, strength_points=0,
                             dexterity_points=0):
    """Check adopted shared-defense and total point-allocation limits.

    ``strategies`` maps component IDs to (attack, defense, timing, extra_damage).
    Skill points are component-specific; positive STR/DEX points are a single
    program-wide reserve. This deliberately does not assign an ability point
    to a particular component or change action-specific eligibility rules.
    """
    keys = set(skill_pools)
    if (not keys or set(priorities) != keys or set(strategies) != keys
            or any(type(key) is not str or not key for key in keys)):
        raise MultipleActionRuleError('resource allocation must cover every program component exactly once')
    if (type(strength_points) is not int or strength_points < 0
            or type(dexterity_points) is not int or dexterity_points < 0):
        raise MultipleActionRuleError('STR and DEX allocation reserves must be nonnegative integers')
    defenses = set()
    remaining_skill_points = 0
    allocated_points = 0
    timing_points = 0
    extra_damage_points = 0
    for key in keys:
        pool, priority = skill_pools[key], priorities[key]
        values = strategies[key]
        if type(pool) is not int or pool < 0 or type(priority) is not int or priority < 0:
            raise MultipleActionRuleError('component skill pools and priorities must be nonnegative integers')
        if type(values) not in (tuple, list) or len(values) != 4:
            raise MultipleActionRuleError('component strategy must contain attack, defense, timing, and extra damage')
        if any(type(value) is not int or value < 0 for value in values):
            raise MultipleActionRuleError('strategy allocations must be nonnegative integers')
        attack, defense, timing, damage = values
        defenses.add(defense)
        # Priority is an outcome penalty, not an eligibility gate: an Action
        # with no discretionary points can still proceed at a negative total.
        remaining_skill_points += max(0, pool - priority - defense)
        allocated_points += attack + timing + damage
        timing_points += timing
        extra_damage_points += damage
    if len(defenses) != 1:
        raise MultipleActionRuleError('all components of one Multiple-action program share a defense allocation')
    ability_points = strength_points + dexterity_points
    if max(0, timing_points - remaining_skill_points) > dexterity_points:
        raise MultipleActionRuleError('DEX may reduce timing, but STR points cannot fund timing')
    if max(0, extra_damage_points - remaining_skill_points) > strength_points:
        raise MultipleActionRuleError('STR may fund extra damage, but DEX points cannot fund extra damage')
    if allocated_points > remaining_skill_points + ability_points:
        raise MultipleActionRuleError('component strategies exceed the available skill and one-time ability points')
    return True
