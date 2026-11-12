"""Receipt-backed physical Grab/Hold and distinct Grapple-control projections."""

from action_evaluation import GrappleStateEffect, ObjectGripEffect


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
    precedence = {'establish': 0, 'transition': 1, 'maintain': 2, 'set': 3, 'release': 4}
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
            if effect.kind == 'posture':
                continue
            table = grips if effect.kind == 'grip' else controls
            if effect.operation == 'establish':
                table[effect.state_id] = (effect.state_id, effect.actor_id,
                    effect.target_id, effect.hand, boundary, effect.next_check)
                if effect.kind == 'control':
                    table[effect.state_id] += (effect.position or 'standing',)
            elif effect.operation == 'maintain':
                prior = table.get(effect.state_id)
                if prior is None:
                    raise ValueError('maintenance effect has no established native state')
                table[effect.state_id] = (*prior[:5], effect.next_check)
                if effect.kind == 'control':
                    table[effect.state_id] += (effect.position if effect.position is not None
                        else (prior[6] if len(prior)>6 else 'standing'),)
            elif effect.operation == 'transition':
                prior = table.get(effect.state_id)
                if prior is None or effect.kind != 'control' or effect.position is None:
                    raise ValueError('position transition has no established Grapple control')
                table[effect.state_id] = (*prior[:5], effect.next_check, effect.position)
            elif effect.operation == 'release':
                table.pop(effect.state_id, None)
            else:
                raise ValueError('unknown native Grapple state transition')
    return tuple(grips[key] for key in sorted(grips)), tuple(controls[key] for key in sorted(controls))


def active_object_grip_state(encounter):
    """Fold committed Object-owned receipts and retain only exact live custody."""
    objects=encounter.universe.object_registry.object_instances
    active={}
    for object_id,obj in objects.items():
        history=object.__getattribute__(obj,'__dict__').get('_atomic_target_history',[])
        for record in history:
            state=getattr(record,'state',None)
            for identified in getattr(state,'incoming',()):
                effect=getattr(identified,'effect',None)
                if type(effect) is not ObjectGripEffect or effect.target_id!=object_id:
                    continue
                if effect.operation=='establish':
                    active[object_id]=(object_id,effect.state_id,effect.actor_id,effect.holder_id,
                        effect.actor_hand,effect.holder_hand,record.boundary)
                elif effect.operation=='transfer':
                    active.pop(object_id,None)
                else:
                    raise ValueError('unknown native Object Grip transition')
    valid=[]
    being_grips,_controls=active_contact_state(encounter)
    occupied_hands={(row[1],row[3]) for row in being_grips if row[3] is not None}
    for object_id,row in active.items():
        _object_id,_state_id,actor_id,holder_id,actor_hand,holder_hand,_boundary=row
        actor=objects.get(actor_id);holder=objects.get(holder_id);obj=objects.get(object_id)
        if (actor is None or holder is None or obj is None
                or obj.parent_container_id!=holder_id or obj.spatial_state is not None
                or holder.current.body_parts.get(holder_hand)!=object_id
                or object_id not in holder.weapons
                or actor.current.body_parts.get(actor_hand,'missing') is not None
                or (actor_id,actor_hand) in occupied_hands):
            continue
        valid.append(row)
    return tuple(sorted(valid))


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


def trip_contact_kind(encounter, action_id, actor_id, target_id):
    """Return the adopted prior contact kind when its committed receipt qualifies Trip."""
    from action import Action
    from melee_combat import MeleeStrike
    action = encounter.universe.get_event_by_id(action_id)
    if (action is None or action.actor_id != actor_id or action.target_id != target_id
            or action_id not in encounter.finished_action_list or action.resolution is None):
        return None
    if type(action) is Action and action.event_type == 'touch':
        valid = action.resolution.outcome == 'touched'
        kind = 'touch'
    elif type(action) is Action and action.event_type == 'grab':
        valid = action.resolution.outcome == 'success'
        kind = 'grab'
    elif type(action) is MeleeStrike and action.event_type in ('swing', 'thrust'):
        valid = action.resolution.outcome in ('normal', 'critical', 'fatal')
        kind = 'strike'
    else:
        return None
    if not valid:
        return None
    from atomic_publication import PublishedInterval
    return kind if any(type(record) is PublishedInterval and record.committed
        and record.boundary == action.end_time and action_id in record.action_ids
        for record in encounter._atomic_interval_history) else None
