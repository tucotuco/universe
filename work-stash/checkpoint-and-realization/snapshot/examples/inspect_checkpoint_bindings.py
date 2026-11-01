"""Native 5D2A diagnostic example; no checkpoint file, restore or replay.

Run: PYTHONDONTWRITEBYTECODE=1 python examples/inspect_checkpoint_bindings.py
Only summary data are printed. The example commits one native second first,
then demonstrates read-only capture with host-owned recipient bindings.
"""
from pathlib import Path
import json
import random
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from universe import Universe
from library import Library
from encounter import Encounter
from atomic_publication import RNGCursor
from spatial.state import CartesianPosition
from spatial.geometry import Sphere
from statistical_group import StatisticalGroup
from group_observation import ObserveGroupAction
from history_conversation import AskAboutPastAction
from field_observation import BeliefLedger
from objective_reality import EpisodeFacts
from realization import Fact
from checkpoint_adapters import RecipientBinding
from checkpoint_inventory import capture_checkpoint_candidate,validate_checkpoint_candidate


def demo():
    world=Universe('Native binding example',library=Library(config_dir=str(ROOT/'src/config')))
    scout,speaker=[world.get_object_by_id(world.make_being('Human',name)) for name in ('Scout','Speaker')]
    enc=Encounter(world,10,0,initiated=True);world.add_event(enc)
    for i,being in enumerate((scout,speaker)):
        being.set_position(CartesianPosition(i*2,0,0));being.set_geometry(Sphere(.2));enc.add_being(being.id)
    enc.mark_aware(scout.id,speaker.id);enc.mark_aware(speaker.id,scout.id)
    scout.set_skill_level(world.library.skill_dictionary,'spot',6)
    history=speaker.begin_personal_history(earliest=-10,known_through=0,nondeclining_skills=('spot',))
    config=json.loads((ROOT/'examples/nomadic_group.json').read_text());config['motion']['position']=[30,0,0]
    group=StatisticalGroup('Group','example-group',config,81);world.add_object(group);enc.add_object(group.id)
    ledger=BeliefLedger(scout.id);accounts=[]
    binding=(RecipientBinding(world,'example-host','scout-ledger','in_world_belief_ledger',(scout.id,),ledger),
             RecipientBinding(world,'example-host','heard-accounts','in_world_received_accounts',(scout.id,),accounts))
    cursor=RNGCursor(random.Random(343).getstate());enc.enable_transactional_progression(quiescent=True,rng_owner=cursor)
    observe=ObserveGroupAction(world,scout.id,group.id,0,ledger=ledger,seed=2,
        observation={'coarse_range_m':100,'detailed_range_m':50})
    ask=AskAboutPastAction(world,scout.id,speaker.id,0,episode_time=0,topic='lessons',
        generate=EpisodeFacts((Fact(history.episode_key(0,'lessons'),{'description':'Earlier lessons'},'declared_history'),)),received_accounts=accounts)
    enc.schedule_choice((observe,ask));enc.step(1)
    before=(enc.time,cursor.state,tuple(accounts),tuple(ledger._evidence))
    c=capture_checkpoint_candidate(world,enc,quiescent=True,rng_scope='exclusive_encounter',native_adapters=True,bindings=binding)
    v=validate_checkpoint_candidate(world,enc,c,quiescent=True)
    assert before==(enc.time,cursor.state,tuple(accounts),tuple(ledger._evidence))
    return {'notice':'INACTIVE diagnostic, not a save or resumable checkpoint','boundary':enc.time,
        'inventory_validated':v.inventory_validated,'closure_validated':v.closure_validated,
        'portable_schema_defined':v.portable_schema_defined,'restore_verified':v.restore_verified,
        'bindings':[(b.namespace,b.name,b.role) for b in binding],
        'heard_accounts':len(accounts),'evidence_records':len(ledger._evidence),
        'diagnostic_codes':sorted({d.code for d in c.diagnostics})}


if __name__=='__main__':print(json.dumps(demo(),indent=2))
