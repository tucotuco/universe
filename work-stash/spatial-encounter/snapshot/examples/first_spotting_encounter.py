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

world = Universe('Deliberate Spot', library=Library(config_dir=str(ROOT / 'src' / 'config')))
observer_id = world.make_being('Human', 'Observer')
known_id = world.make_being('Human', 'Partner')
target_id = world.make_object('Brick', 'Object to discover')
observer = world.get_object_by_id(observer_id)
observer.set_position(CartesianPosition(0, 0, 0))
world.get_object_by_id(known_id).set_position(CartesianPosition(0, 5, 0))
world.get_object_by_id(known_id).set_geometry(Sphere(0.5))
world.get_object_by_id(target_id).set_position(CartesianPosition(100, 0, 0))
world.get_object_by_id(target_id).set_geometry(Sphere(0.5))
encounter = Encounter(world, difficulty_class=99, start_time=0, initiated=True)
encounter.add_being(observer_id)
encounter.add_being(known_id)
encounter.add_object(target_id)
encounter.mark_aware(observer_id, known_id)

# Discovery uses the target's DC (15 by default), not Encounter attack DC.
action = SpotAction(world, observer_id, target_id, encounter.time, die_roll=15)
encounter.schedule_action(action)
encounter.step(duration=6)
print('Outcome:', action.resolution.outcome, 'roll:', action.roll,
      'aware:', encounter.is_aware(observer_id, target_id))
print('Spot is an Action; Spot skill XP:', observer.get_skill_experience('spot'))
