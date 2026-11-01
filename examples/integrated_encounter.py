"""Revision-60 Spot timing and movement/practice example.

Run from the repository root with ``python examples/integrated_encounter.py``.
The Spot Action lasts six seconds, uses the target's discovery DC, and awards
no Spot skill practice. Run remains the legitimate skill-practice Action.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from activities import RunAction, SpotAction
from encounter import Encounter
from library import Library
from spatial import AxisAlignedBox, CartesianPosition, Sphere, VisualOcclusion
from universe import Universe


def run_scenario():
    world = Universe('Integrated Encounter', library=Library(config_dir=str(ROOT / 'src' / 'config')))
    scout_id = world.make_being('Human', 'Scout')
    companion_id = world.make_being('Human', 'Companion')
    cache_id = world.make_object('Brick', 'Cache')
    wall_id = world.make_object('Brick', 'Opaque wall')
    scout = world.get_object_by_id(scout_id)
    companion = world.get_object_by_id(companion_id)
    cache = world.get_object_by_id(cache_id)
    wall = world.get_object_by_id(wall_id)
    scout.set_position(CartesianPosition(0, 0, 0))
    companion.set_position(CartesianPosition(0, -5, 0)); companion.set_geometry(Sphere(.5))
    cache.set_position(CartesianPosition(10, 0, 0)); cache.set_geometry(Sphere(.5))
    wall.set_position(CartesianPosition(5, 0, 0)); wall.set_geometry(AxisAlignedBox(1, 2, 2))
    wall.set_visual_occlusion(VisualOcclusion(1))
    encounter = Encounter(world, difficulty_class=99, start_time=0, initiated=True)
    for being_id in (scout_id, companion_id): encounter.add_being(being_id)
    for object_id in (cache_id, wall_id): encounter.add_object(object_id)
    encounter.mark_aware(scout_id, companion_id)

    run = RunAction(world, scout_id, 0, duration=2, minimum_distance=2.5, experience=250)
    spot = SpotAction(world, scout_id, cache_id, 0, die_roll=15)
    encounter.schedule_choice((run, spot))
    states = [{'stage':'initial', 'time':0, 'position':scout.get_position().as_tuple(),
        'sightline':encounter.line_of_sight(scout_id,cache_id).status,
        'cache_aware':False, 'run_xp':0, 'spot_xp':0}]
    steps=[]
    for boundary in range(1,7):
        velocity = {scout_id:(0,1.5,0)} if boundary <= 2 else None
        steps.append(encounter.step(duration=1, velocities=velocity))
        states.append({'stage':f'boundary_{boundary}', 'time':encounter.time,
            'position':scout.get_position().as_tuple(),
            'sightline':encounter.line_of_sight(scout_id,cache_id).status,
            'cache_aware':encounter.is_aware(scout_id,cache_id),
            'run_xp':scout.get_skill_experience('run'),
            'spot_xp':scout.get_skill_experience('spot')})
    return {'world':world,'encounter':encounter,'scout':scout,'companion':companion,
        'ids':{'scout':scout_id,'companion':companion_id,'cache':cache_id,'wall':wall_id},
        'actions':{'run':run,'spot':spot},'steps':steps,'states':states}


if __name__ == '__main__':
    scenario = run_scenario()
    for state in scenario['states']:
        print('t={time:.0f} | {stage:<12} | sightline={sightline:<7} | '
              'aware={cache_aware} | Run XP={run_xp} | Spot XP={spot_xp}'.format(**state))
    print('Action outcomes:', {name:action.resolution.outcome
                               for name,action in scenario['actions'].items()})
