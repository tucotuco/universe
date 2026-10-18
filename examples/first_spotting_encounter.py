"""Run from repository root: python examples/first_spotting_encounter.py"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from activities import SpotAction
from encounter import Encounter
from library import Library
from spatial import CartesianPosition, Sphere
from universe import Universe

world = Universe('Observation practice', library=Library(config_dir=str(ROOT / 'src' / 'config')))
observer_id = world.make_being('Human', 'Observer')
known_id = world.make_being('Human', 'Partner')
target_id = world.make_object('Brick', 'Object to discover')
observer = world.get_object_by_id(observer_id)
observer.set_position(CartesianPosition(0, 0, 0))
world.get_object_by_id(known_id).set_position(CartesianPosition(0, 5, 0))
world.get_object_by_id(known_id).set_geometry(Sphere(0.5))
world.get_object_by_id(target_id).set_position(CartesianPosition(10, 0, 0))
world.get_object_by_id(target_id).set_geometry(Sphere(0.5))
encounter = Encounter(world, difficulty_class=11, start_time=0)
encounter.add_being(observer_id)
encounter.add_being(known_id)
encounter.add_object(target_id)
encounter.mark_aware(observer_id, known_id)
encounter.decide_to_act(observer_id, known_id, 'search area')

for xp in (250, 0):
    action = SpotAction(world, observer_id, target_id, encounter.time,
                        duration=1, max_distance=15, die_roll=10,
                        experience=xp)
    encounter.schedule_action(action)
    encounter.step()
    print('Outcome:', action.resolution.outcome,
          'roll:', action.roll, 'skill used:', action.skill_level_used,
          'new rank:', observer.get_skill_level('spot'),
          'aware:', encounter.is_aware(observer_id, target_id))
print('Skill-use history:', [record.to_dict() for record in observer.skill_use_history])
