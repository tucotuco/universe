"""Native held-Object Grab/Wrest receipt, custody, and restart regression."""

import json
import os
import random
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import io

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'examples'));sys.path.insert(0,str(ROOT/'src'))

from physical_contact import active_object_grip_state
from arena_browser_session import GeneratedArenaSession
from arena_browser_session import ArenaBrowserRequestError
from arena_web import make_handler


def request(session,path,payload=None):
    handler_type=make_handler(session)
    handler=object.__new__(handler_type)
    handler.path=path;handler.server=type('FakeServer',(),{'server_port':8000})()
    handler.wfile=io.BytesIO();handler.headers={}
    if payload is not None:
        body=json.dumps(payload).encode();handler.rfile=io.BytesIO(body)
        handler.headers={'Content-Length':str(len(body)),'Content-Type':'application/json'}
    result={}
    handler._send=lambda status,body,content_type='application/json; charset=utf-8':result.update(
        status=status,body=body,content_type=content_type)
    (handler.do_GET if payload is None else handler.do_POST)()
    body=result['body']
    if result['content_type'].startswith('application/json'):
        body=json.loads(json.dumps(body) if type(body) is not str else body)
    return result['status'],body


class TestNativeObjectWrest(unittest.TestCase):
    def test_out_of_reach_and_missing_grip_are_closed_before_rng(self):
        session=GeneratedArenaSession(root_seed_factory=lambda:20261107)
        request(session,'/api/generated/generate',{
            'starting_experience':'10000','width_cells':'5','height_cells':'5',
            'root_seed':'20261107','equipment_mode':'equipped','opponent_strategy':'none'})
        candidate=session.active_candidate
        actor=candidate.participants[0].native.being
        holder=candidate.participants[1].native.being
        object_id=holder.current.body_parts['right hand']
        handle=session._view_handles[object_id]
        request(session,'/api/generated/run',{})
        request(session,'/api/generated/advance',{'seconds':1})
        request(session,'/api/generated/inspect',{'handle':handle})
        rows=session.public_view()['action_catalog']['entries']
        self.assertEqual(next(row for row in rows if row['name']=='wrest')['status'],'unavailable')
        far=max(candidate.arena_map.layout.addresses(),key=lambda address:
            __import__('math').dist(actor.get_position().as_tuple(),
                candidate.arena_map.layout.center_position(address).as_tuple()))
        actor.set_position(candidate.arena_map.layout.center_position(far))
        rng=session._rng_cursor.state
        status,response=request(session,'/api/generated/grappling',{
            'handle':handle,'action':'grab object','hand':'left hand'})
        self.assertEqual(status,409)
        self.assertIn('outside your native arm reach',response['error'])
        self.assertEqual(session._rng_cursor.state,rng)
        self.assertEqual(holder.current.body_parts['right hand'],object_id)
        self.assertEqual(candidate.universe.get_object_by_id(object_id).parent_container_id,holder.id)

    def test_object_grab_uses_holder_defense_and_plus_five_dc(self):
        cases=((6,0,0,'failed'),(5,5,0,'success'),(5,5,5,'failed'))
        for dice_seed,actor_attack,holder_defense,expected in cases:
            session=GeneratedArenaSession(root_seed_factory=lambda:20261107)
            request(session,'/api/generated/generate',{
                'starting_experience':'10000','width_cells':'5','height_cells':'5',
                'root_seed':'20261107','equipment_mode':'equipped','opponent_strategy':'none'})
            candidate=session.active_candidate
            actor=candidate.participants[0].native.being
            holder=candidate.participants[1].native.being
            object_id=holder.current.body_parts['right hand']
            obj=candidate.universe.get_object_by_id(object_id)
            candidate.encounter.difficulty_class=15
            actor.strategy.attack=actor_attack;holder.strategy.defense=holder_defense
            self.assertEqual(obj.current.weapon_size,'T')
            self.assertEqual(candidate.encounter.difficulty_class,15)
            request(session,'/api/generated/run',{})
            request(session,'/api/generated/advance',{'seconds':1})
            handle=session._view_handles[object_id]
            request(session,'/api/generated/inspect',{'handle':handle})
            status,_=request(session,'/api/generated/grappling',{
                'handle':handle,'action':'grab object','hand':'left hand'})
            self.assertEqual(status,200)
            session._rng_cursor.state=random.Random(dice_seed).getstate()
            result=request(session,'/api/generated/advance',{'seconds':1})[1]
            self.assertEqual(result['grappling_action']['outcome'],expected)
            self.assertEqual(candidate.universe.get_object_by_id(object_id).parent_container_id,holder.id)

    def test_generated_http_grab_and_fresh_process_wrest_preserves_object_identity(self):
        session=GeneratedArenaSession(root_seed_factory=lambda:20261107)
        status,_=request(session,'/api/generated/generate',{
            'starting_experience':'10000','width_cells':'5','height_cells':'5',
            'root_seed':'20261107','equipment_mode':'equipped','opponent_strategy':'none'})
        self.assertEqual(status,200)
        candidate=session.active_candidate
        actor=candidate.participants[0].native.being
        holder=candidate.participants[1].native.being
        object_id=holder.current.body_parts['right hand']
        native_object=candidate.universe.get_object_by_id(object_id)
        self.assertEqual(native_object.parent_container_id,holder.id)
        self.assertEqual(holder.weapons.count(object_id),1)

        self.assertEqual(request(session,'/api/generated/run',{})[0],200)
        self.assertEqual(request(session,'/api/generated/advance',{'seconds':1})[0],200)
        handle=session._view_handles[object_id]
        inspected=request(session,'/api/generated/inspect',{'handle':handle})[1]
        row=next(item for item in inspected['action_catalog']['entries']
                 if item['name']=='grab object')
        self.assertEqual(row['status'],'available')
        self.assertNotIn(object_id,json.dumps(inspected))
        before_rng=session._rng_cursor.state
        self.assertEqual(request(session,'/api/generated/grappling',{
            'handle':'unobserved-object-handle','action':'grab object','hand':'left hand'})[0],409)
        self.assertEqual(request(session,'/api/generated/grappling',{
            'handle':handle,'action':'grab object','hand':'right hand'})[0],409)
        self.assertEqual(session._rng_cursor.state,before_rng)
        status,accepted=request(session,'/api/generated/grappling',{
            'handle':handle,'action':'grab object','hand':'left hand'})
        self.assertEqual(status,200)
        duplicate_rng=session._rng_cursor.state
        self.assertEqual(request(session,'/api/generated/grappling',{
            'handle':handle,'action':'grab object','hand':'left hand'})[0],409)
        self.assertEqual(session._rng_cursor.state,duplicate_rng)
        self.assertNotIn(object_id,json.dumps(accepted))
        grabbed=request(session,'/api/generated/advance',{'seconds':1})[1]
        self.assertEqual(grabbed['grappling_action']['outcome'],'success')
        self.assertEqual(native_object.parent_container_id,holder.id)
        self.assertEqual(holder.current.body_parts['right hand'],object_id)
        self.assertEqual(actor.current.body_parts['left hand'],None)
        grips=active_object_grip_state(candidate.encounter)
        self.assertEqual(len(grips),1)
        self.assertEqual(grips[0][0],object_id)
        grip_wire=session.save_encounter_bytes()

        with tempfile.TemporaryDirectory() as directory:
            grip_path=Path(directory)/'object-grip.json'
            grip_path.write_bytes(grip_wire)
            continuation=(
                "import json,sys; from arena_browser_session import GeneratedArenaSession; "
                "from physical_contact import active_object_grip_state; "
                "s=GeneratedArenaSession(root_seed_factory=lambda:17); "
                "s.load_encounter_bytes(open(sys.argv[1],'rb').read()); "
                "c=s.active_candidate; oid=sys.argv[2]; a=c.participants[0].native.being; "
                "h=c.participants[1].native.being; v=s._view_unlocked(); "
                "handle=s._view_handles[oid]; s.inspect_entity({'handle':handle}); "
                "row=next(x for x in s._view_unlocked()['action_catalog']['entries'] if x['name']=='wrest'); "
                "assert row['status']=='available',row; "
                "s.choose_grappling({'handle':handle,'action':'wrest'}); v=s.advance_one_second(); "
                "o=c.universe.get_object_by_id(oid); action=next(x for x in c.universe.event_history.values() "
                "if getattr(x,'event_type',None)=='wrest'); "
                "assert action.resolution.outcome=='success',action.resolution.outcome; "
                "assert o.parent_container_id==a.id and a.current.body_parts['left hand']==oid; "
                "assert oid not in h.weapons and oid not in h.current.body_parts.values(); "
                "assert active_object_grip_state(c.encounter)==(); "
                "open(sys.argv[3],'wb').write(s.save_encounter_bytes()); "
                "print(json.dumps({'time':v['time_seconds'],'outcome':action.resolution.outcome,"
                "'object_id':oid,'owner':o.parent_container_id}))")
            wrest_path=Path(directory)/'object-wrested.json'
            child_env=dict(os.environ)
            child_env['PYTHONPATH']=os.pathsep.join((str(ROOT/'tests'),str(ROOT/'src'),str(ROOT/'examples')))
            restored=subprocess.run([sys.executable,'-c',continuation,str(grip_path),object_id,str(wrest_path)],
                cwd=ROOT,env=child_env,check=False,capture_output=True,text=True,timeout=60)
            self.assertEqual(restored.returncode,0,restored.stderr)
            evidence=json.loads(restored.stdout)
            self.assertEqual(evidence['time'],3)
            self.assertEqual(evidence['outcome'],'success')
            self.assertEqual(evidence['object_id'],object_id)
            verify=("import json,sys; from arena_browser_session import GeneratedArenaSession; "
                "s=GeneratedArenaSession(root_seed_factory=lambda:23); "
                "s.load_encounter_bytes(open(sys.argv[1],'rb').read()); c=s.active_candidate; "
                "oid=sys.argv[2]; a=c.participants[0].native.being; h=c.participants[1].native.being; "
                "o=c.universe.get_object_by_id(oid); action=next(x for x in c.universe.event_history.values() "
                "if getattr(x,'event_type',None)=='wrest'); "
                "assert action.resolution.outcome=='success' and o.parent_container_id==a.id; "
                "assert a.current.body_parts['left hand']==oid and oid not in h.weapons; "
                "print(json.dumps({'time':c.encounter.time,'outcome':action.resolution.outcome,"
                "'same_id':oid==o.id,'owner':o.parent_container_id}))")
            final=subprocess.run([sys.executable,'-c',verify,str(wrest_path),object_id],
                cwd=ROOT,env=child_env,check=False,capture_output=True,text=True,timeout=60)
            self.assertEqual(final.returncode,0,final.stderr)
            final_evidence=json.loads(final.stdout)
            self.assertEqual(final_evidence['outcome'],'success')
            self.assertTrue(final_evidence['same_id'])
            self.assertEqual(final_evidence['owner'],actor.id)

    def test_failed_and_tied_wrest_leave_same_object_in_holder_hand(self):
        outcomes=[]
        for dice_seed in (0,1):
            dice=random.Random(dice_seed)
            actor_roll=sum(dice.randint(1,6) for _ in range(3))
            holder_roll=sum(dice.randint(1,6) for _ in range(3))
            self.assertLessEqual(actor_roll,holder_roll)
            if dice_seed==1:self.assertEqual(actor_roll,holder_roll)
            session=GeneratedArenaSession(root_seed_factory=lambda:20261107)
            self.assertEqual(request(session,'/api/generated/generate',{
                'starting_experience':'10000','width_cells':'5','height_cells':'5',
                'root_seed':'20261107','equipment_mode':'equipped','opponent_strategy':'none'})[0],200)
            candidate=session.active_candidate
            actor=candidate.participants[0].native.being
            holder=candidate.participants[1].native.being
            object_id=holder.current.body_parts['right hand']
            for being in (actor,holder):being.current.abilities.abilities['STR']=10
            request(session,'/api/generated/run',{})
            request(session,'/api/generated/advance',{'seconds':1})
            handle=session._view_handles[object_id]
            request(session,'/api/generated/inspect',{'handle':handle})
            status,_=request(session,'/api/generated/grappling',{
                'handle':handle,'action':'grab object','hand':'left hand'})
            self.assertEqual(status,200)
            request(session,'/api/generated/advance',{'seconds':1})
            session._rng_cursor.state=random.Random(dice_seed).getstate()
            status,_=request(session,'/api/generated/grappling',{'handle':handle,'action':'wrest'})
            self.assertEqual(status,200)
            request(session,'/api/generated/advance',{'seconds':1})
            action=next(row for row in candidate.universe.event_history.values()
                if getattr(row,'event_type',None)=='wrest')
            outcomes.append(action.resolution.outcome)
            native_object=candidate.universe.get_object_by_id(object_id)
            self.assertEqual(action.resolution.outcome,'failed')
            self.assertEqual(native_object.parent_container_id,holder.id)
            self.assertEqual(holder.current.body_parts['right hand'],object_id)
            self.assertNotIn(object_id,actor.current.body_parts.values())
            self.assertEqual(len(active_object_grip_state(candidate.encounter)),1)
        self.assertEqual(outcomes,['failed','failed'])

    def test_holder_weapon_attack_competing_with_wrest_preserves_custody(self):
        from melee_combat import MeleeStrike,effective_melee_reach_meters
        session=GeneratedArenaSession(root_seed_factory=lambda:20261107)
        request(session,'/api/generated/generate',{
            'starting_experience':'10000','width_cells':'5','height_cells':'5',
            'root_seed':'20261107','equipment_mode':'equipped','opponent_strategy':'none'})
        candidate=session.active_candidate
        actor=candidate.participants[0].native.being
        holder=candidate.participants[1].native.being
        object_id=holder.current.body_parts['right hand']
        request(session,'/api/generated/run',{})
        request(session,'/api/generated/advance',{'seconds':1})
        handle=session._view_handles[object_id]
        request(session,'/api/generated/inspect',{'handle':handle})
        self.assertEqual(request(session,'/api/generated/grappling',{
            'handle':handle,'action':'grab object','hand':'left hand'})[0],200)
        request(session,'/api/generated/advance',{'seconds':1})
        weapon=candidate.universe.get_object_by_id(object_id)
        attack=MeleeStrike(candidate.encounter,holder.id,actor.id,object_id,
            motion='thrust',reach=effective_melee_reach_meters(holder.current,weapon.current))
        candidate.encounter.schedule_action(attack)
        self.assertEqual(request(session,'/api/generated/grappling',{
            'handle':handle,'action':'wrest'})[0],409)
        self.assertEqual(weapon.parent_container_id,holder.id)
        self.assertEqual(holder.current.body_parts['right hand'],object_id)
        self.assertEqual(actor.current.body_parts['left hand'],None)
        self.assertEqual(len(active_object_grip_state(candidate.encounter)),1)


if __name__=='__main__':
    unittest.main()
