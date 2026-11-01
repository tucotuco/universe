"""Explicit native checkpoint inventory diagnostic; no save, restore or replay.

Run: PYTHONDONTWRITEBYTECODE=1 python examples/inspect_checkpoint_closure.py
Run: PYTHONDONTWRITEBYTECODE=1 python examples/inspect_checkpoint_closure.py --seconds 1
Only a diagnostic summary is printed; no checkpoint bytes or files are created.
"""
import argparse
from pathlib import Path
import random
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT/'src')not in sys.path:sys.path.insert(0,str(ROOT/'src'))
from universe import Universe
from library import Library
from encounter import Encounter
from activities import RunAction
from atomic_publication import RNGCursor
from spatial.state import CartesianPosition
from checkpoint_inventory import capture_checkpoint_candidate,validate_checkpoint_candidate


def demo(seconds=0):
    world=Universe('Checkpoint closure audit',library=Library(config_dir=str(ROOT/'src/config')))
    being=world.get_object_by_id(world.make_being('Human','Runner'))
    being.set_position(CartesianPosition(0,0,0))
    enc=Encounter(world,10,0,initiated=True);world.add_event(enc);enc.add_being(being.id)
    enc.enable_transactional_progression(quiescent=True,rng_owner=RNGCursor(random.Random(17).getstate()))
    enc.schedule_choice((RunAction(world,being.id,.25,1,1,experience=7),))
    if seconds:enc.step(seconds,velocities={being.id:(1,0,0)})
    candidate=capture_checkpoint_candidate(world,enc,quiescent=True,rng_scope='exclusive_encounter')
    validation=validate_checkpoint_candidate(world,enc,candidate,quiescent=True)
    return candidate,validation


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds',type=int,choices=(0,1,2),default=0)
    args=parser.parse_args(argv)
    candidate,result=demo(args.seconds)
    print('INACTIVE checkpoint closure INVENTORY; NOT a save or resumable checkpoint')
    print('Coherent same-process inventory:',result.inventory_validated)
    print('closure_validated:',result.closure_validated)
    print('portable_schema_defined:',result.portable_schema_defined)
    print('restore_verified:',result.restore_verified)
    print('Diagnostic codes:',', '.join(sorted({d.code for d in candidate.diagnostics})))


if __name__=='__main__':main()
