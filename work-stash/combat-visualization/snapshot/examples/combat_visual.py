"""Visual replay of an actual one-on-one Encounter with weapon experience.

Run from any working directory:
    python examples/combat_visual.py --seed 17 --open

This replay is offline and observational, not an interactive combat controller.
"""

import argparse
import json
from pathlib import Path
import random
import sys
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'examples'))

from armed_duel import make_duel
from perception import RangePerception


WEAPONS = ('Dagger', 'Longsword')


def snapshot(world, encounter, combatants, weapon_names, decisions=(), events=()):
    """Read only authoritative state; keep perceived evidence in its own field."""
    beings = []
    for being, weapon_type in zip(combatants, weapon_names):
        pos = being.get_position()
        beings.append({
            'id': being.id,
            'name': being.name,
            'position': None if pos is None else list(pos.as_tuple()),
            'hp': being.get_hit_points(),
            'weapon': weapon_type,
            'skill_rank': being.get_weapon_skill_level(weapon_type) or 0,
            'experience': being.get_skill_experience(weapon_type),
            'skill_uses': sum(use.skill_name == weapon_type for use in being.skill_use_history),
            'aware_of': encounter.aware_beings(being.id),
        })
    pending = []
    for event_id in encounter.pending_action_list:
        action = world.get_event_by_id(event_id)
        pending.append({'actor_id': action.actor_id, 'motion': action.event_type,
                        'due': action.end_time})
    return {'time': encounter.time, 'beings': beings, 'pending': pending,
            'decisions': list(decisions), 'events': list(events)}


def simulate(seed=17):
    """Return authentic Encounter snapshots including the two completed Actions."""
    random.seed(seed)
    world, encounter, scout, raider, armor_id, strikes = make_duel()
    scout_id, raider_id = scout.id, raider.id
    # The currently available range-only perception establishes awareness,
    # not a bearing or perfect vision.  Keep that distinction in the viewer.
    encounter.clear_awareness(scout_id, raider_id)
    encounter.clear_awareness(raider_id, scout_id)
    detection = RangePerception(3.0)
    first_observations = encounter.perceive(scout_id, detection)
    second_observations = encounter.perceive(raider_id, detection)
    initial_events = [
        {'actor_id': observation.observer_id,
         'text': 'Range observation establishes awareness of ' +
                 world.get_object_by_id(observation.target_id).name + '.'}
        for observation in (*first_observations, *second_observations)
    ]
    frames = [snapshot(world, encounter, (scout, raider), WEAPONS,
                       decisions=({'actor_id': scout_id, 'text': 'Attack with dagger thrust (scripted)'},
                                  {'actor_id': raider_id, 'text': 'Attack with longsword swing (scripted)'}),
                       events=initial_events)]
    for second in range(1, 7):
        move = {raider_id: (0, .2, 0)} if second in (1, 2) else {}
        tick = encounter.step(duration=1, velocities=move)
        events = []
        for action_id in tick.completed_action_ids:
            action = world.get_event_by_id(action_id)
            record = action.combat_result
            actor = world.get_object_by_id(record.actor_id)
            awarded = sum(item.experience for item in action.resolution.skill_exercises)
            events.append({'actor_id': record.actor_id, 'target_id': record.target_id,
                           'motion': record.motion, 'outcome': record.outcome,
                           'experience': awarded,
                           'text': f'{actor.name} {record.motion}: {record.outcome}; '
                                   f'target HP {record.target_hp_before} → '
                                   f'{record.target_hp_after}; +{awarded} weapon XP.'})
        decisions = ([{'actor_id': raider_id, 'text': 'Move +0.2 on Y axis (scripted)'}]
                     if move else [])
        frames.append(snapshot(world, encounter, (scout, raider), WEAPONS,
                               decisions=decisions, events=events))
    return {
        'title': 'Encounter at the ford', 'seed': seed,
        'perception_model': 'RangePerception (3.0 coordinate units): provisional awareness, not vision',
        'frames': frames,
    }


def render(trace):
    template = (ROOT / 'examples/combat_viewer_template.html').read_text(encoding='utf-8')
    # Escape script-closing sequences even if a future text field is user-derived.
    serialized = json.dumps(trace, ensure_ascii=True).replace('<', r'\u003c')
    return template.replace('__COMBAT_TRACE__', serialized)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=17)
    parser.add_argument('--output', type=Path, default=ROOT / 'combat_replay.html')
    parser.add_argument('--open', action='store_true', help='open replay in your default browser')
    args = parser.parse_args(argv)
    trace = simulate(args.seed)
    output = args.output.expanduser().resolve()
    output.write_text(render(trace), encoding='utf-8')
    print(f'Combat replay: {output}')
    if args.open:
        webbrowser.open(output.as_uri())
    return output


if __name__ == '__main__':
    main()
