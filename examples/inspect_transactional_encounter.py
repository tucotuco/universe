"""Explicit developer diagnostic demo; native progression, no server or replay.

Run from the repository root:
  PYTHONDONTWRITEBYTECODE=1 python examples/inspect_transactional_encounter.py
  PYTHONDONTWRITEBYTECODE=1 python examples/inspect_transactional_encounter.py --html
  PYTHONDONTWRITEBYTECODE=1 python examples/inspect_transactional_encounter.py --boundary 1

Output goes only to stdout. Optional shell redirection is a caller decision;
rendered documents are non-authoritative and have no import/resume mechanism.
"""
import argparse
from pathlib import Path
import random
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT/'src') not in sys.path:
    sys.path.insert(0,str(ROOT/'src'))

from universe import Universe
from library import Library
from encounter import Encounter
from atomic_publication import RNGCursor
from activities import RunAction, SpotAction
from spatial.state import CartesianPosition
from spatial.geometry import Sphere
from developer_inspection import format_inspection_text, render_inspection_html


def build_demo_view(boundary=None):
    """Build a fresh native scene, commit six seconds, acquire one guarded view.

    Seed, choices, positions and physics inputs are fixed. Native UUIDs/process
    identities remain fresh; this is not a cross-process replay fingerprint.
    """
    world=Universe('Developer diagnostic',library=Library(config_dir=str(ROOT/'src/config')))
    runner=world.get_object_by_id(world.make_being('Human','Runner'))
    observer=world.get_object_by_id(world.make_being('Human','Observer'))
    for being,x in ((runner,0),(observer,3)):
        being.set_position(CartesianPosition(x,0,0));being.set_geometry(Sphere(.25))
    encounter=Encounter(world,10,0,initiated=True);world.add_event(encounter)
    encounter.add_being(runner.id);encounter.add_being(observer.id)
    encounter.mark_aware(runner.id,observer.id);encounter.mark_aware(observer.id,runner.id)
    encounter.enable_transactional_progression(quiescent=True,rng_owner=RNGCursor(random.Random(141).getstate()))
    run=RunAction(world,runner.id,.25,1,1,experience=7)
    spot=SpotAction(world,observer.id,runner.id,0,duration=6,die_roll=20)
    encounter.schedule_choice((run,spot));encounter.step(6,velocities={runner.id:(1,0,0)})
    return encounter.inspect_committed(boundary)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html',action='store_true',help='print inert HTML instead of text')
    parser.add_argument('--boundary',type=int,choices=(5,6),help='select a committed historical boundary')
    args=parser.parse_args(argv)
    view=build_demo_view(args.boundary)
    sys.stdout.write(render_inspection_html(view) if args.html else format_inspection_text(view))


if __name__=='__main__':
    main()
