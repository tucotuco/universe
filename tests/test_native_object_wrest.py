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
    @staticmethod
    def _three_being_native_encounter():
        from action import Action
        from arena_hex_map import ArenaHexLayout, encounter_map_descriptor
        from encounter import Encounter
        from library import Library
        from atomic_publication import RNGCursor
        from spatial.geometry import Sphere
        from spatial.state import CartesianPosition
        from universe import Universe

        world=Universe('Three-Being simultaneous custody',
            library=Library(config_dir=str(ROOT/'src/config')))
        actor=world.get_object_by_id(world.make_being('Human','First challenger'))
        holder=world.get_object_by_id(world.make_being('Human','Object holder'))
        third=world.get_object_by_id(world.make_being('Human','Second challenger'))
        layout=ArenaHexLayout.rectangle(5,5)
        origin=layout.center_position(layout.address_for_index(12))
        actor.set_position(origin)
        holder.set_position(CartesianPosition(origin.x+.3,origin.y,origin.z))
        third.set_position(CartesianPosition(origin.x+.3,origin.y+.3,origin.z))
        for being in (actor,holder,third):
            being.set_geometry(Sphere(.1));being.set_hit_points(100)
            being.size_category='medium';being.set_posture('standing')
        actor.set_hex_facing(0);holder.set_hex_facing(6);third.set_hex_facing(9)
        object_id=world.make_weapon_for_being(holder.id,'Dagger','One shared Dagger')
        world.arm_being(holder.id,object_id,'right hand')
        world.get_object_by_id(object_id).parent_container_id=holder.id
        encounter=Encounter(world,20,0,initiated=True)
        encounter.map=encounter_map_descriptor(layout)
        for being in (actor,holder,third):encounter.add_being(being.id)
        for observer in (actor,holder,third):
            for target in (actor,holder,third):
                if observer is not target:encounter.mark_aware(observer.id,target.id)
            encounter.mark_aware(observer.id,object_id)
        encounter.add_object(object_id);world.add_event(encounter)
        encounter.enable_transactional_progression(quiescent=True,
            rng_owner=RNGCursor(random.Random(17).getstate()))
        actor.strategy.attack=1000;third.strategy.attack=1000;holder.strategy.defense=0
        return world,encounter,actor,holder,third,object_id

    @staticmethod
    def _scripted_step(encounter,rolls):
        from action_evaluation import _ProvisionalRandom,RandomDraw
        from unittest.mock import patch
        values=iter(rolls)
        def scripted(ctx,dice):
            value=next(values)
            ctx.trace.append(RandomDraw(ctx.action_id,dice,int(dice[2:].split('+')[0]),value))
            return value
        with patch.object(_ProvisionalRandom,'roll',scripted):encounter.step(1)

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
        self.assertTrue(any('You grip' in row and 'holds it in right hand' in row
            for row in grabbed['contact_status']))
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

    def test_wrest_late_publication_fault_restores_custody_receipts_and_rng(self):
        from atomic_publication import PublicationFailure
        from physical_contact import active_object_grip_state
        from unittest.mock import patch
        from tests.test_atomic_publication import raw_graph

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
        self.assertEqual(len(active_object_grip_state(candidate.encounter)),1)
        request(session,'/api/generated/grappling',{'handle':handle,'action':'wrest'})

        # Seed a known winning contest so transfer custody writes and receipt
        # publication are staged before the injected late fault.
        session._rng_cursor.state=random.Random(3).getstate()
        before_rng=session._rng_cursor.state
        before=raw_graph(candidate.universe,candidate.encounter)
        from atomic_publication import publish_interval_candidate
        def inject(encounter,interval,**kwargs):
            return publish_interval_candidate(encounter,interval,
                _fail_after='rng',**kwargs)
        with patch('atomic_publication.publish_interval_candidate',side_effect=inject):
            with self.assertRaises(PublicationFailure):
                candidate.encounter.step(1)

        self.assertEqual(raw_graph(candidate.universe,candidate.encounter),before)
        self.assertEqual(session._rng_cursor.state,before_rng)
        obj=candidate.universe.get_object_by_id(object_id)
        self.assertEqual(obj.parent_container_id,holder.id)
        self.assertEqual(holder.current.body_parts['right hand'],object_id)
        self.assertIsNone(actor.current.body_parts['left hand'])
        self.assertEqual(len(active_object_grip_state(candidate.encounter)),1)
        wrest=next(member.action
                   for choice in candidate.encounter._choice_book._choices.values()
                   for member in choice.members
                   if getattr(member.action,'event_type',None)=='wrest')
        self.assertIsNone(wrest.resolution)
        self.assertFalse(any(row.boundary==candidate.encounter.time+1
                             for row in candidate.encounter._atomic_interval_history))
        with self.assertRaises(Exception):
            session.save_encounter_bytes()

    def test_same_boundary_object_grabs_establish_independent_receipts(self):
        from action import Action
        from physical_contact import active_object_grip_state
        world,encounter,actor,holder,third,object_id=self._three_being_native_encounter()
        first=Action(world,0,1,'grab object',actor.id,object_id,None)
        first.holder_id=holder.id;first.holder_hand='right hand';first.grab_hand='left hand'
        second=Action(world,0,1,'grab object',third.id,object_id,None)
        second.holder_id=holder.id;second.holder_hand='right hand';second.grab_hand='left hand'
        encounter.schedule_choice((first,second))
        self.assertEqual(sum(row.object_id==object_id
            for row in encounter._choice_book._reservations),2)
        self._scripted_step(encounter,[20,20])
        actions=[row for row in world.event_history.values()
                 if getattr(row,'event_type',None)=='grab object']
        self.assertEqual([row.resolution.outcome for row in actions],['success','success'])
        self.assertEqual(holder.current.body_parts['right hand'],object_id)
        self.assertEqual(world.get_object_by_id(object_id).parent_container_id,holder.id)
        grips=active_object_grip_state(encounter)
        self.assertEqual({row[2] for row in grips},{actor.id,third.id})

    def test_three_being_simultaneous_wrest_shares_same_object_and_persists(self):
        from action import Action
        from physical_contact import active_object_grip_state,shared_object_holders
        world,encounter,actor,holder,third,object_id=self._three_being_native_encounter()
        grab_one=Action(world,0,1,'grab object',actor.id,object_id,None)
        grab_one.holder_id=holder.id;grab_one.holder_hand='right hand';grab_one.grab_hand='left hand'
        grab_two=Action(world,0,1,'grab object',third.id,object_id,None)
        grab_two.holder_id=holder.id;grab_two.holder_hand='right hand';grab_two.grab_hand='left hand'
        encounter.schedule_choice((grab_one,grab_two))
        self._scripted_step(encounter,[20,20])
        grips=active_object_grip_state(encounter)
        self.assertEqual({row[2] for row in grips},{actor.id,third.id})

        actor.current.abilities.abilities['STR']=30
        third.current.abilities.abilities['STR']=30
        holder.current.abilities.abilities['STR']=3
        by_actor={row[2]:row for row in grips}
        first=Action(world,2,3,'wrest',actor.id,object_id,None)
        first.holder_id=holder.id;first.holder_hand='right hand'
        first.grab_hand='left hand';first.object_grip_id=by_actor[actor.id][1]
        second=Action(world,2,3,'wrest',third.id,object_id,None)
        second.holder_id=holder.id;second.holder_hand='right hand'
        second.grab_hand='left hand';second.object_grip_id=by_actor[third.id][1]
        encounter.schedule_choice((first,second))
        encounter.step(1)  # Activate both one-second contests at the common start fence.
        self._scripted_step(encounter,[6,6,6,1,1,1,6,6,6,1,1,1])
        self.assertEqual((first.resolution.outcome,second.resolution.outcome),('success','success'))
        self.assertEqual(active_object_grip_state(encounter),())
        self.assertEqual(set(shared_object_holders(encounter,object_id)),
                         {(actor.id,'left hand'),(third.id,'left hand')})
        obj=world.get_object_by_id(object_id)
        self.assertEqual(obj.id,object_id)
        self.assertEqual(obj.parent_container_id,min(actor.id,third.id))
        self.assertNotIn(object_id,holder.current.body_parts.values())
        self.assertNotIn(object_id,holder.weapons)
        for receiver in (actor,third):
            self.assertEqual(receiver.current.body_parts['left hand'],object_id)
            self.assertEqual(receiver.weapons.count(object_id),1)
            self.assertEqual(receiver.possessions.count(object_id),1)
        from types import SimpleNamespace
        projection=GeneratedArenaSession()
        projection._view_handles[object_id]='opaque-shared-object'
        projection._display_names[object_id]='One shared Dagger'
        candidate=SimpleNamespace(universe=world,encounter=encounter)
        for receiver in (actor,third):
            inventory=projection._native_inventory_projection(candidate,receiver)
            self.assertEqual(inventory['status'],'available')
            self.assertEqual(sum(row['handle']=='opaque-shared-object'
                for row in inventory['items']),1)
            self.assertNotIn(object_id,json.dumps(inventory))
        from transactional_progression import _BINDINGS
        from arena_native_snapshot import capture,encode
        saved=encode(capture(world,encounter,_BINDINGS[id(encounter)].rng_owner))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'joint-hold.json';path.write_bytes(saved)
            verify=("import sys; from arena_native_snapshot import decode,restore; "
                "from physical_contact import shared_object_holders; "
                "w,e,r=restore(decode(open(sys.argv[1],'rb').read())); oid=sys.argv[2]; "
                "assert len(shared_object_holders(e,oid))==2; o=w.get_object_by_id(oid); "
                "assert o.id==oid and o.parent_container_id==min(sys.argv[3],sys.argv[4]); "
                "assert sum(w.get_object_by_id(x).current.body_parts.get('left hand')==oid "
                "for x in e.being_list)==2")
            child_env=dict(os.environ)
            child_env['PYTHONPATH']=os.pathsep.join((str(ROOT/'tests'),str(ROOT/'src'),str(ROOT/'examples')))
            restored=subprocess.run([sys.executable,'-c',verify,str(path),object_id,actor.id,third.id],
                cwd=ROOT,env=child_env,check=False,capture_output=True,text=True,timeout=60)
            self.assertEqual(restored.returncode,0,restored.stderr)

    def test_simultaneous_wrest_late_fault_restores_all_custody_receipts_and_rng(self):
        from action import Action
        from atomic_publication import PublicationFailure
        from physical_contact import active_object_grip_state
        from tests.test_atomic_publication import raw_graph
        from unittest.mock import patch
        import atomic_publication

        world,encounter,actor,holder,third,object_id=self._three_being_native_encounter()
        grab_one=Action(world,0,1,'grab object',actor.id,object_id,None)
        grab_one.holder_id=holder.id;grab_one.holder_hand='right hand';grab_one.grab_hand='left hand'
        grab_two=Action(world,0,1,'grab object',third.id,object_id,None)
        grab_two.holder_id=holder.id;grab_two.holder_hand='right hand';grab_two.grab_hand='left hand'
        encounter.schedule_choice((grab_one,grab_two))
        self._scripted_step(encounter,[20,20])
        grips={row[2]:row for row in active_object_grip_state(encounter)}
        actor.current.abilities.abilities['STR']=1000
        third.current.abilities.abilities['STR']=1000
        first=Action(world,1,2,'wrest',actor.id,object_id,None)
        first.holder_id=holder.id;first.holder_hand='right hand'
        first.grab_hand='left hand';first.object_grip_id=grips[actor.id][1]
        second=Action(world,1,2,'wrest',third.id,object_id,None)
        second.holder_id=holder.id;second.holder_hand='right hand'
        second.grab_hand='left hand';second.object_grip_id=grips[third.id][1]
        encounter.schedule_choice((first,second))
        from transactional_progression import _BINDINGS
        rng_owner=_BINDINGS[id(encounter)].rng_owner
        before_rng=rng_owner.state
        before=raw_graph(world,encounter)
        publish=atomic_publication.publish_interval_candidate
        def inject(target,interval,**kwargs):
            return publish(target,interval,_fail_after='rng',**kwargs)
        with patch('atomic_publication.publish_interval_candidate',side_effect=inject):
            with self.assertRaises(PublicationFailure):encounter.step(1)
        self.assertEqual(raw_graph(world,encounter),before)
        self.assertEqual(rng_owner.state,before_rng)
        self.assertEqual(world.get_object_by_id(object_id).parent_container_id,holder.id)
        self.assertEqual(holder.current.body_parts['right hand'],object_id)
        self.assertIsNone(actor.current.body_parts['left hand'])
        self.assertIsNone(third.current.body_parts['left hand'])
        self.assertEqual({row[2] for row in active_object_grip_state(encounter)},
                         {actor.id,third.id})
        self.assertIsNone(first.resolution);self.assertIsNone(second.resolution)

    def test_same_boundary_disarm_prevents_wrest_transfer(self):
        from action import Action
        from strategy import Strategy
        from melee_combat import effective_melee_reach_meters
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
        self.assertEqual(request(session,'/api/generated/grappling',{
            'handle':handle,'action':'wrest'})[0],200)

        third_id=candidate.universe.make_being('Human','Disarming participant')
        third=candidate.universe.get_object_by_id(third_id)
        from spatial.state import CartesianPosition
        hp=holder.get_position()
        ap=actor.get_position();dx,dy=ap.x-hp.x,ap.y-hp.y;norm=(dx*dx+dy*dy)**.5
        third.set_position(CartesianPosition(hp.x-.5*dy/norm,hp.y+.5*dx/norm,hp.z))
        third.set_hit_points(100)
        from spatial.geometry import Sphere
        third.set_geometry(Sphere(.1))
        candidate.encounter.add_being(third.id)
        from arena_perception import ArenaPerceptionLedger
        third._arena_perception_ledger=ArenaPerceptionLedger(third.id)
        candidate.encounter.mark_aware(third.id,holder.id)
        candidate.encounter.mark_aware(holder.id,third.id)
        tool_id=candidate.universe.make_weapon_for_being(third.id,'Dagger','Disarm dagger')
        candidate.universe.arm_being(third.id,tool_id,'right hand')
        third.current.skills.weapon_skills['Dagger']=10
        tool=candidate.universe.get_object_by_id(tool_id)
        disarm=Action(candidate.universe,candidate.encounter.time,
            candidate.encounter.time+1,'disarm',third.id,holder.id,tool_id,
            strategy=Strategy(timing=6))
        disarm.disarm_weapon_id=object_id;disarm.disarm_motion='thrust'
        disarm.reach=effective_melee_reach_meters(third.current,tool.current)
        candidate.encounter.schedule_action(disarm)
        candidate.encounter.step(1)

        wrest=next(row for row in candidate.universe.event_history.values()
                   if getattr(row,'event_type',None)=='wrest')
        self.assertEqual(wrest.resolution.outcome,'custody_conflict')
        item=candidate.universe.get_object_by_id(object_id)
        self.assertNotEqual(item.parent_container_id,actor.id)
        self.assertNotIn(object_id,actor.current.body_parts.values())
        self.assertIsNotNone(disarm.resolution)
        if disarm.resolution.outcome=='disarmed':
            self.assertIsNone(item.parent_container_id)
            self.assertEqual(item.get_position(),holder.get_position())
        else:
            self.assertEqual(item.parent_container_id,holder.id)
            self.assertEqual(holder.current.body_parts['right hand'],object_id)

    def test_earlier_disarm_invalidates_accepted_future_wrest_with_three_beings(self):
        """Arena map and explicit test Geometry exercise stale custody cleanly."""
        from action import Action
        from action_evaluation import _ProvisionalRandom, RandomDraw
        from encounter import Encounter
        from library import Library
        from melee_combat import effective_melee_reach_meters
        from arena_hex_map import ArenaHexLayout, encounter_map_descriptor
        from spatial.geometry import Sphere
        from spatial.state import CartesianPosition
        from universe import Universe
        from strategy import Strategy
        from unittest.mock import patch

        world=Universe('Three-Being custody race',
            library=Library(config_dir=str(ROOT/'src/config')))
        actor=world.get_object_by_id(world.make_being('Human','Wrestler'))
        holder=world.get_object_by_id(world.make_being('Human','Holder'))
        disarmer=world.get_object_by_id(world.make_being('Human','Disarmer'))
        layout=ArenaHexLayout.rectangle(5,5)
        origin=layout.center_position(layout.address_for_index(12))
        actor.set_position(origin)
        holder.set_position(CartesianPosition(origin.x+.3,origin.y,origin.z))
        disarmer.set_position(CartesianPosition(origin.x+.3,origin.y+.3,origin.z))
        for being in (actor,holder,disarmer):
            being.set_geometry(Sphere(.1))
            being.set_hit_points(100)
            being.size_category='medium'
            being.set_posture('standing')
        actor.set_hex_facing(0)
        holder.set_hex_facing(6)
        disarmer.set_hex_facing(9)
        world_weapon=world.make_weapon_for_being(holder.id,'Dagger','Held dagger')
        world.arm_being(holder.id,world_weapon,'right hand')
        disarm_weapon=world.make_weapon_for_being(disarmer.id,'Dagger','Disarm dagger')
        world.arm_being(disarmer.id,disarm_weapon,'right hand')
        world.get_object_by_id(world_weapon).parent_container_id=holder.id
        world.get_object_by_id(disarm_weapon).parent_container_id=disarmer.id
        disarmer.current.skills.weapon_skills['Dagger']=10
        disarmer.strategy.attack=10
        actor.strategy.attack=100
        holder.strategy.defense=0

        encounter=Encounter(world,20,0,initiated=True)
        # The adopted Arena path classifier excludes carried Objects because
        # they have no independent world position; keep that rule in the
        # fixture rather than weakening the general non-Arena path contract.
        encounter.map=encounter_map_descriptor(layout)
        for being in (actor,holder,disarmer):
            encounter.add_being(being.id)
        for observer in (actor,holder,disarmer):
            for target in (actor,holder,disarmer):
                if observer is not target:
                    encounter.mark_aware(observer.id,target.id)
        encounter.add_object(world_weapon)
        encounter.add_object(disarm_weapon)
        encounter.mark_aware(actor.id,world_weapon)
        self.assertTrue(encounter.is_aware(actor.id,holder.id))
        world.add_event(encounter)
        encounter.enable_transactional_progression(quiescent=True)
        from weapon import WeaponInstance
        native_world_weapon=world.get_object_by_id(world_weapon)
        self.assertIs(type(native_world_weapon),WeaponInstance)
        self.assertIn(world_weapon,holder.weapons)
        self.assertEqual(native_world_weapon.parent_container_id,holder.id)
        self.assertIsNone(native_world_weapon.spatial_state)

        grab=Action(world,0,1,'grab object',actor.id,world_weapon,None)
        grab.holder_id=holder.id;grab.holder_hand='right hand';grab.grab_hand='left hand'
        encounter.schedule_action(grab)
        def step_with(rolls):
            values=iter(rolls)
            def scripted(ctx,dice):
                value=next(values)
                ctx.trace.append(RandomDraw(ctx.action_id,dice,
                    int(dice[2:].split('+')[0]),value))
                return value
            with patch.object(_ProvisionalRandom,'roll',scripted):
                encounter.step(1)
        step_with([10])
        self.assertEqual(grab.resolution.outcome,'success')
        grip=active_object_grip_state(encounter)[0]
        self.assertIsNotNone(actor.get_position())
        self.assertIsNotNone(holder.get_position())
        self.assertIsNotNone(disarmer.get_position())
        self.assertIsNotNone(layout.cell_at_position(disarmer.get_position()))

        disarm=Action(world,1,2,'disarm',disarmer.id,holder.id,disarm_weapon,
                      strategy=Strategy(timing=6))
        disarm.disarm_weapon_id=world_weapon;disarm.disarm_motion='thrust'
        disarm.reach=effective_melee_reach_meters(disarmer.current,
            world.get_object_by_id(disarm_weapon).current)
        wrest=Action(world,2,3,'wrest',actor.id,world_weapon,None)
        wrest.holder_id=holder.id;wrest.holder_hand='right hand'
        wrest.grab_hand='left hand';wrest.object_grip_id=grip[1]
        encounter.schedule_choice((disarm,wrest))

        # Disarm commits at second 2 while Wrest is accepted to start there and
        # resolve at 3. All Beings have explicit test Geometry and valid facing.
        step_with([20,1])
        self.assertEqual(disarm.resolution.outcome,'landing_choice_pending')
        from atomic_publication import disarm_landing_options,choose_disarm_landing
        cell=disarm_landing_options(encounter,world_weapon)[0]
        choose_disarm_landing(encounter,world_weapon,cell.column,cell.row)
        self.assertIn(wrest.id,encounter.pending_action_list)
        with patch.object(_ProvisionalRandom,'roll',side_effect=AssertionError(
                'stale Wrest must be rejected before drawing RNG')):
            encounter.step(1)
        self.assertEqual(wrest.resolution.outcome,'not_held')
        self.assertEqual(active_object_grip_state(encounter),())
        dropped=world.get_object_by_id(world_weapon)
        self.assertIsNone(dropped.parent_container_id)
        self.assertEqual(dropped.get_position(),encounter.inspect_committed().target(world_weapon).position)
        self.assertNotIn(world_weapon,holder.current.body_parts.values())
        self.assertNotIn(world_weapon,actor.current.body_parts.values())

    def test_cancelled_pending_wrest_keeps_receipt_custody_and_rng(self):
        from action import Action
        from physical_contact import active_object_grip_state
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
        grip=active_object_grip_state(candidate.encounter)[0]

        # Before the start fence, the same user route withdraws an accepted
        # future Action by undoing its sole-member Choice.
        now=candidate.encounter.time
        accepted=Action(candidate.universe,now+1,now+2,'wrest',actor.id,object_id,None)
        accepted.holder_id=holder.id;accepted.holder_hand='right hand'
        accepted.grab_hand='left hand';accepted.object_grip_id=grip[1]
        candidate.encounter.schedule_action(accepted)
        before_rng=session._rng_cursor.state
        status,withdrawn=request(session,'/api/generated/cancel-contact',{})
        self.assertEqual(status,200)
        self.assertNotIn(accepted.id,json.dumps(withdrawn))
        self.assertFalse(candidate.encounter._choice_book.actor_planned_now(actor.id))
        self.assertEqual(session._rng_cursor.state,before_rng)

        # Start the next one-second Wrest one second in the future. At that start
        # fence the native scheduler publishes it as pending; it can then be
        # withdrawn before the following boundary resolves it.
        now=candidate.encounter.time
        wrest=Action(candidate.universe,now+1,now+2,'wrest',actor.id,object_id,None)
        wrest.holder_id=holder.id;wrest.holder_hand='right hand'
        wrest.grab_hand='left hand';wrest.object_grip_id=grip[1]
        candidate.encounter.schedule_action(wrest)
        request(session,'/api/generated/advance',{'seconds':1})
        self.assertIn(wrest.id,candidate.encounter.pending_action_list)
        before_rng=session._rng_cursor.state
        status,withdrawn=request(session,'/api/generated/cancel-contact',{})
        self.assertEqual(status,200)
        self.assertEqual(withdrawn['grappling_action']['status'],'cancelled')
        self.assertNotIn(wrest.id,json.dumps(withdrawn))
        request(session,'/api/generated/advance',{'seconds':1})

        self.assertIn(wrest.id,candidate.encounter.cancelled_action_list)
        self.assertNotIn(wrest.id,candidate.encounter.finished_action_list)
        self.assertIsNone(wrest.resolution)
        self.assertEqual(session._rng_cursor.state,before_rng)
        item=candidate.universe.get_object_by_id(object_id)
        self.assertEqual(item.parent_container_id,holder.id)
        self.assertEqual(holder.current.body_parts['right hand'],object_id)
        self.assertIsNone(actor.current.body_parts['left hand'])
        self.assertEqual(len(active_object_grip_state(candidate.encounter)),1)

if __name__=='__main__':
    unittest.main()
