"""Run from the repository root: python examples/first_running_encounter.py"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from activities import RunAction
from encounter import Encounter
from library import Library
from spatial.state import CartesianPosition
from universe import Universe


world = Universe('First running encounter',
                 library=Library(config_dir=str(ROOT / 'src' / 'config')))
runner_id = world.make_being('Human', 'Runner')
marker_id = world.make_object('Brick', 'Destination')
runner = world.get_object_by_id(runner_id)
runner.set_position(CartesianPosition(0, 0, 0))
world.get_object_by_id(marker_id).set_position(CartesianPosition(10, 0, 0))

encounter = Encounter(world, difficulty_class=10, start_time=0)
encounter.add_being(runner_id)
encounter.add_object(marker_id)
encounter.mark_aware(runner_id, marker_id)
encounter.decide_to_act(runner_id, marker_id, 'approach')

# A deliberately illustrative award to demonstrate one skill rank advancing.
action = RunAction(world, runner_id, start_time=0, duration=2,
                   minimum_distance=3.0, experience=250)
encounter.schedule_action(action)
for _ in range(2):
    encounter.step(duration=1, velocities={runner_id: (2, 0, 0)})

print('Position:', runner.get_position().as_tuple())
print('Action:', action.resolution.outcome)
print('Displacement:', action.displacement)
print('Run experience:', runner.get_skill_experience('run'))
print('Run skill level:', runner.get_skill_level('run'))
print('Practice record:', runner.skill_use_history[-1].to_dict())
