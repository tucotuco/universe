"""Receipt-backed physical Grab/Hold and distinct Grapple-control projections."""

from action_evaluation import GrappleStateEffect


def _history_effects(being):
    history = object.__getattribute__(being, '__dict__').get('_atomic_target_history')
    if history is None:
        history = []
    if type(history) is not list:
        raise ValueError('native Target history is unavailable for physical contact state')
    rows = []
    for record in history:
        state = getattr(record, 'state', None)
        for identified in getattr(state, 'incoming', ()):
            effect = getattr(identified, 'effect', None)
            if type(effect) is GrappleStateEffect:
                rows.append((record.boundary, identified.identity, effect))
    precedence = {'establish': 0, 'maintain': 1, 'release': 2}
    return tuple(sorted(rows, key=lambda row: (row[0], row[2].kind,
        row[2].state_id, precedence[row[2].operation], row[1])))


def active_contact_state(encounter):
    """Fold only committed, Target-owned typed effects; no live-state replay."""
    objects = encounter.universe.object_registry.object_instances
    grips, controls = {}, {}
    for target_id in encounter.being_list:
        being = objects.get(target_id)
        if being is None:
            raise ValueError('Encounter Target identity is missing')
        for boundary, identity, effect in _history_effects(being):
            if effect.target_id != target_id:
                raise ValueError('Grapple effect is stored under a different Target')
            table = grips if effect.kind == 'grip' else controls
            if effect.operation == 'establish':
                table[effect.state_id] = (effect.state_id, effect.actor_id,
                    effect.target_id, effect.hand, boundary, effect.next_check)
            elif effect.operation == 'maintain':
                prior = table.get(effect.state_id)
                if prior is None:
                    raise ValueError('maintenance effect has no established native state')
                table[effect.state_id] = (*prior[:5], effect.next_check)
            elif effect.operation == 'release':
                table.pop(effect.state_id, None)
            else:
                raise ValueError('unknown native Grapple state transition')
    return tuple(grips[key] for key in sorted(grips)), tuple(controls[key] for key in sorted(controls))


def successful_touch(encounter, action_id, actor_id, target_id):
    """Require a completed native Touch receipt and matching Action identity."""
    action = encounter.universe.get_event_by_id(action_id)
    from action import Action
    if (type(action) is not Action or action.event_type != 'touch'
            or action.actor_id != actor_id or action.target_id != target_id
            or action_id not in encounter.finished_action_list
            or action.resolution is None or action.resolution.outcome != 'touched'):
        return False
    from atomic_publication import PublishedInterval
    records = [r for r in encounter._atomic_interval_history
               if type(r) is PublishedInterval and r.committed
               and r.boundary == action.end_time and action_id in r.action_ids]
    return bool(records)
