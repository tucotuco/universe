"""5C3C pure developer presentation; native guard tests remain separate from DTO formatting."""
from dataclasses import dataclass, replace
from html.parser import HTMLParser
from pathlib import Path
import json
import random
import sys
from types import MappingProxyType
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'examples')]
import test_encounter_inspection as fixtures
from developer_inspection import (LABEL, PresentationRejected, format_inspection_text,
                                  render_inspection_html)
from encounter_inspection import InspectionRejected
from atomic_publication import publication_boundary, PublicationOwnershipError
from field_observation import BeliefLedger
from history_conversation import AskAboutPastAction
from activities import RunAction
from melee_defense import MeleeDefense
from inspect_transactional_encounter import build_demo_view, main


class Parsed(HTMLParser):
    def __init__(self, document):
        super().__init__(convert_charrefs=True)
        self.tags=[];self.attributes=[];self.text=[];self.feed(document);self.close()
    def handle_starttag(self,tag,attrs):
        self.tags.append(tag);self.attributes.extend((tag,key,value) for key,value in attrs)
    def handle_data(self,data):self.text.append(data)


class TestDeveloperPresentation(fixtures.InspectionFixture):
    def render(self,view):
        return format_inspection_text(view),render_inspection_html(view)

    def test_successful_committed_text_and_html_have_explicit_scope(self):
        action=self.commit();before=self.raw();view=self.enc.inspect_committed()
        text,html=self.render(view)
        self.assertEqual(before,self.raw())
        self.assertIn(LABEL,text);self.assertIn(LABEL, ''.join(Parsed(html).text))
        self.assertIn('Selected committed boundary: 1',text)
        self.assertIn(action.id,text);self.assertIn('Actual resolution boundary: 1',text)
        self.assertTrue(html.startswith('<!doctype html>'))
        self.assertIn('native',view.schema)

    def test_historical_boundary_is_clearly_distinguished(self):
        self.commit();self.enc.step(1,velocities={self.a.id:(1,0,0)})
        old=self.enc.inspect_committed(1);latest=self.enc.inspect_committed()
        text,html=self.render(old)
        self.assertIn('Selected committed boundary: 1',text)
        self.assertIn('Latest committed boundary at acquisition: 2',text)
        self.assertIn('Historical selection: yes',text)
        self.assertNotEqual(format_inspection_text(latest),text)
        self.assertIn('Boundary 1 | interval 0 -&gt; 1',html)
        self.assertNotIn('Boundary 2 | interval',html)

    def test_static_navigation_offline_and_inert_html(self):
        self.commit();html=render_inspection_html(self.enc.inspect_committed());parsed=Parsed(html)
        self.assertFalse(set(parsed.tags)&{'script','iframe','img','link','object','embed','form','button','input','canvas','video'})
        ids=[value for tag,key,value in parsed.attributes if key=='id']
        links=[value for tag,key,value in parsed.attributes if key=='href']
        self.assertEqual(len(ids),len(set(ids)))
        self.assertTrue(links);self.assertTrue(all(url.startswith('#') and url[1:] in ids for url in links))
        self.assertFalse(any(key in ('src','srcset','action','onload','onclick') for _,key,_ in parsed.attributes))
        self.assertIn('default-src',html);self.assertIn('<details>',html)
        for section in ('actions','targets','history','defenses','practice','reality','observers','beliefs','testimony','lifecycle','effects'):
            self.assertIn(section,ids)

    def test_all_causal_effects_and_due_sets_are_present(self):
        self.commit();view=self.enc.inspect_committed();text,html=self.render(view)
        for aid in view.actions:self.assertIn(aid,text)
        for eid in view.effects:
            self.assertIn(eid.source_action_id,text);self.assertIn('slot: '+str(eid.slot),text)
        self.assertIn('Complete causal effect index',html)
        self.assertIn('Due Action IDs',text);self.assertIn('Start fences',text)

    def test_two_exercises_one_target_transition_has_causal_records(self):
        self.a.record_skill_use(self.world.get_skill_dictionary(),'run',1240,action_id='prior',time=-2)
        self.enable();one,two=(RunAction(self.world,self.a.id,0,1,.5,experience=3),
                              RunAction(self.world,self.a.id,0,1,.5,experience=4))
        self.enc.schedule_choice((one,two));self.enc.step(1,velocities={self.a.id:(1,0,0)})
        view=self.enc.inspect_committed();text,html=self.render(view)
        self.assertEqual(len(view.target(self.a.id).state.practice_state.transitions),1)
        self.assertIn('BatchSkillUse',text);self.assertIn('CandidatePracticeUse',text)
        self.assertIn('Target-owned practice and experience',html)
        self.assertIn(one.id,text);self.assertIn(two.id,text)
        action_part=text.split('Actions: causality and outcomes')[1].split('Targets: selected-boundary')[0]
        self.assertNotIn('level_after',action_part)

    def mixed(self,payload='Prior lessons'):
        group=self.f.f.f.group();history=self.f.f.f.history();la,lb=BeliefLedger(self.a.id),BeliefLedger(self.b.id);accounts=[]
        self.enable();one,two=self.f.f.observe(self.a,group,ledger=la),self.f.f.observe(self.b,group,ledger=lb)
        ask=AskAboutPastAction(self.world,self.c.id,self.a.id,0,episode_time=0,topic='lessons',
            generate=self.f.f.f.recipe(history,description=payload),substituted_claim=payload+' (heard)',received_accounts=accounts)
        self.enc.schedule_choice((one,two,ask));self.enc.step(1)
        return self.enc.inspect_committed(),group,one,two,ask,accounts

    def test_shared_truth_subjective_evidence_beliefs_and_heard_accounts_separate(self):
        view,group,one,two,ask,accounts=self.mixed();before=self.raw();text,html=self.render(view)
        self.assertEqual(before,self.raw());self.assertEqual(len(view.objective[group.id].facts),4)
        self.assertNotEqual(view.target(self.a.id).state.observer_state.observations[one.id].reported_position,
                            view.target(self.b.id).state.observer_state.observations[two.id].reported_position)
        for label in ('Shared objective Reality','Observer-specific evidence','Belief recipients','Testimony and heard accounts'):
            self.assertIn(label,text);self.assertIn(label,html)
        self.assertIn('A heard account is not an assertion of objective historical truth.',text)
        self.assertIn('HeardAccount',text);self.assertIn('revision: 1',text)
        self.assertIn(accounts[0].words,text)

    def test_native_adversarial_name_fact_and_account_strings_are_escaped(self):
        payload='<script>alert("X")</script><img src=x onerror=boom> & \'quoted\'\n\x1b[31m\u202e'
        self.a.name=payload
        view,_,_,_,_,_=self.mixed(payload)
        text,html=self.render(view);parsed=Parsed(html)
        self.assertNotIn('script',parsed.tags);self.assertNotIn('img',parsed.tags)
        self.assertNotIn(payload,html)
        self.assertIn('&lt;script&gt;',html);self.assertIn('&amp;',html)
        self.assertNotIn('\x1b',text);self.assertNotIn('\u202e',text)
        self.assertIn('\\u001b',text);self.assertIn('\\u202e',text)
        self.assertIn('\\n',text)
        # Angle-bracket text is inert even when words are facts or testimony.
        self.assertIn('<script>', ''.join(parsed.text))

    def test_deterministic_for_same_view_and_reordered_maps(self):
        self.commit();view=self.enc.inspect_committed();expected=self.render(view)
        self.assertEqual(expected,self.render(view))
        reverse=lambda mapping:MappingProxyType(dict(reversed(tuple(mapping.items()))))
        changed=replace(view,actions=reverse(view.actions),targets=reverse(view.targets),effects=reverse(view.effects),
                        objective=reverse(view.objective),recipients=reverse(view.recipients),histories=reverse(view.histories))
        self.assertEqual(expected,self.render(changed))

    def test_no_live_reads_or_rng_during_dto_rendering(self):
        self.commit();view=self.enc.inspect_committed();before=self.raw()
        with (patch('encounter.Encounter.inspect_committed',side_effect=AssertionError('live read')),
              patch('action_evaluation.evaluate_snapshot',side_effect=AssertionError('evaluate')),
              patch('group_observation.sample_group_evidence',side_effect=AssertionError('sample')),
              patch.object(random,'getstate',side_effect=AssertionError('RNG read')),
              patch.object(random,'randint',side_effect=AssertionError('RNG draw'))):
            text,html=self.render(view)
        self.assertTrue(text);self.assertTrue(html);self.assertEqual(before,self.raw())

    def test_old_detached_view_is_stable_after_live_mutation_or_fault(self):
        self.commit();view=self.enc.inspect_committed();expected=self.render(view)
        self.a.current.hit_points=-999;self.a.name='Changed';self.enc.boundary_fault={'fault':'diagnostic'}
        self.assertEqual(expected,self.render(view))
        with self.assertRaises(InspectionRejected):self.enc.inspect_committed()

    def test_wrong_schema_and_audience_are_explicitly_refused(self):
        self.commit();view=self.enc.inspect_committed()
        for changed in (replace(view,schema='legacy'),replace(view,audience='player'),
                        replace(view,audience='observer filtered'),replace(view,audience=None)):
            for renderer in (format_inspection_text,render_inspection_html):
                with self.assertRaises(PresentationRejected):renderer(changed)

    def test_opaque_objects_and_custom_formatters_are_never_invoked(self):
        seen=[]
        @dataclass(frozen=True)
        class Opaque:
            def __repr__(self):seen.append('repr');raise AssertionError
            def __str__(self):seen.append('str');raise AssertionError
            def __format__(self,spec):seen.append('format');raise AssertionError
            def to_dict(self):seen.append('serialize');raise AssertionError
        for renderer in (format_inspection_text,render_inspection_html):
            with self.assertRaises(PresentationRejected):renderer(Opaque())
        self.commit();view=self.enc.inspect_committed()
        for renderer in (format_inspection_text,render_inspection_html):
            with self.assertRaises(PresentationRejected):renderer(replace(view,participants=(Opaque(),)))
        self.assertEqual(seen,[])

    def test_frozen_shape_incomplete_data_and_legacy_values_refuse(self):
        self.commit();view=self.enc.inspect_committed()
        for value in (None,{},self.enc,replace(view,actions=dict(view.actions)),replace(view,timeline=()),
                      replace(view,histories=MappingProxyType({})),replace(view,schedule=None),replace(view,schedule=object())):
            with self.subTest(kind=type(value).__name__):
                for renderer in (format_inspection_text,render_inspection_html):
                    with self.assertRaises(PresentationRejected):renderer(value)

    def test_limits_are_explicit_refusals_without_silent_truncation(self):
        self.commit();view=self.enc.inspect_committed()
        with patch('developer_inspection._MAX_OUTPUT',20):
            with self.assertRaisesRegex(PresentationRejected,'limit'):format_inspection_text(view)
            with self.assertRaisesRegex(PresentationRejected,'limit'):render_inspection_html(view)
        with patch('developer_inspection._MAX_NODES',1):
            with self.assertRaisesRegex(PresentationRejected,'limit'):format_inspection_text(view)
        huge=replace(view,participants=('x'*65_537,))
        with self.assertRaisesRegex(PresentationRejected,'limit'):format_inspection_text(huge)

    def test_native_acquisition_refusals_are_not_bypassed_by_formatting(self):
        before=self.raw()
        with self.assertRaises(InspectionRejected):format_inspection_text(self.enc.inspect_committed())
        self.assertEqual(before,self.raw());self.commit();before=self.raw()
        with publication_boundary(self.enc,quiescent=True):
            with self.assertRaises(InspectionRejected):render_inspection_html(self.enc.inspect_committed())
        with patch('atomic_publication._EMERGENCIES',{1:object()}):
            with self.assertRaises(PublicationOwnershipError):format_inspection_text(self.enc.inspect_committed())
        receipt=self.enc._atomic_interval_history[0]
        with self.assertRaises(InspectionRejected):format_inspection_text(self.enc.inspect_committed(receipt=replace(receipt)))
        self.assertEqual(before,self.raw())
        self.enc.boundary_fault={'error':'fault'}
        with self.assertRaises(InspectionRejected):render_inspection_html(self.enc.inspect_committed())

    def test_pure_dto_formatting_is_not_native_receipt_authentication(self):
        self.commit();view=self.enc.inspect_committed()
        # A same-schema detached diagnostic copy is formatable. This grants no
        # receipt/control authority and is never handed to a native publisher.
        display=replace(view)
        self.assertEqual(self.render(display),self.render(view))
        receipt=replace(self.enc._atomic_interval_history[0])
        with self.assertRaises(InspectionRejected):self.enc.inspect_committed(receipt=receipt)

    def test_cancelled_fractional_action_and_no_movement_are_readable(self):
        self.enable();spot=RunAction(self.world,self.a.id,.25,1,.5,experience=1);run=RunAction(self.world,self.c.id,0,1,1)
        self.enc.schedule_choice((spot,run));self.enc.step(1);self.enc.cancel_action(spot.id);self.enc.step(1)
        text,html=self.render(self.enc.inspect_committed())
        self.assertIn('Nominal start: 0.25; nominal end: 1.25',text)
        self.assertIn('Actual resolution boundary: 2',text)
        self.assertIn('cancelled',text);self.assertIn('interrupted',html);self.assertIn('no_movement',text)

    def test_facade_policy_commands_and_exports_remain_refused(self):
        from tactical_duel import TacticalDuel
        from ai_duel import AgentDuel
        self.commit();before=self.raw()
        for kind in (TacticalDuel,AgentDuel):
            game=kind(seed=17);game.encounter=self.enc
            for operation in (lambda:game.state(),lambda:game.choose('wait'),lambda:game.to_session()):
                with self.assertRaises(ValueError):operation()
            if kind is AgentDuel:
                with self.assertRaises(ValueError):game.observation()
        for operation in (lambda:self.enc.run(),lambda:self.enc.resolve_actions(),lambda:self.world.to_json()):
            with self.assertRaises((ValueError,TypeError)):operation()
        self.assertEqual(before,self.raw())

    def test_programmatic_demo_uses_real_native_commits(self):
        before=random.getstate();view=build_demo_view(5);text,html=self.render(view)
        self.assertEqual(random.getstate(),before)
        self.assertEqual((view.boundary,view.latest_boundary),(5,6))
        self.assertEqual(len(view.actions),1)
        self.assertTrue(view.schedule.pending)
        self.assertIn('Developer',text);self.assertIn('Developer',html)
        later=build_demo_view();self.assertEqual(later.boundary,6)
        self.assertIn('success',[action.facts.outcome for action in later.actions.values()])
        actor_target=next(target for target in later.targets.values()
                          if target.state.practice_state.skill_experience.get('run') == 7)
        self.assertNotIn('spot',actor_target.state.practice_state.skill_experience)

    def test_demo_cli_writes_only_explicit_stdout(self):
        import io
        output=io.StringIO()
        with patch('sys.stdout',output):main(['--html','--boundary','5'])
        self.assertTrue(output.getvalue().startswith('<!doctype html>'))
        self.assertIn('Selected committed boundary: 5',output.getvalue())


class TestCombatDeveloperPresentation(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.TestCombatInspection();self.f.setUp()

    def render(self,view):return format_inspection_text(view),render_inspection_html(view)

    def test_additive8_and7_from12_target_negative_and_no_action_hp_fields(self):
        f=self.f;f.b.current.hit_points=12;one,two=f.f.attack(extra=4),f.f.attack(f.f.w2,extra=3)
        view=f.resolve((one,two),(15,4,15,4));text,html=self.render(view)
        self.assertIn('Target HP before: 12\nTarget HP after: -3\nActual damage: 15',text)
        action_text=text.split('Actions: causality and outcomes')[1].split('Targets: selected-boundary')[0]
        self.assertNotIn('Target HP',action_text)
        self.assertEqual([sum(view.action(a.id).damage_by_target[f.b.id].values()) for a in (one,two)],[8,7])
        self.assertIn('8',action_text);self.assertIn('7',action_text);self.assertIn('Target HP after: -3',html)

    def test_armor_and_shield_negative_damage_and_protection_are_distinct(self):
        f=self.f
        aid=f.world.make_armor_for_being(f.b.id,'Leather armor','Armor');f.world.armor_being(f.b.id,aid)
        sid=f.world.make_weapon_for_being(f.b.id,'Small shield','Shield');f.world.arm_being(f.b.id,sid,'shield hand')
        for oid in (aid,sid):f.world.get_object_by_id(oid).current.hit_points=1
        one,two=f.f.attack(extra=10),f.f.attack(f.f.w2,extra=10)
        view=f.resolve((one,two),(15,4,1,15,4,1));text,html=self.render(view)
        for oid in (aid,sid):
            self.assertLess(view.target(oid).state.projected_hp,0)
            self.assertIn('Target HP after: '+str(view.target(oid).state.projected_hp),text)
        self.assertIn('ProtectionEffect',text);self.assertIn('DamageEffect',html)
        self.assertIn('not another damage charge',text)

    def test_multi_release_order_is_independent_of_mapping_insertion(self):
        f=self.f;one,two=f.f.attack(),f.f.attack(f.f.w2)
        view=f.resolve((one,two),(15,4,15,4));expected=self.render(view)
        reordered=replace(view,effects=MappingProxyType(dict(reversed(tuple(view.effects.items())))))
        self.assertEqual(self.render(reordered),expected)

    def test_fatal_floor_is_target_owned_once_not_fabricated_damage(self):
        f=self.f;one,two=f.f.attack(),f.f.attack(f.f.w2)
        view=f.resolve((one,two),(20,20,1,20,20,1));text,html=self.render(view)
        self.assertIn('Target HP after: -10\nActual damage: 0',text)
        self.assertIn('Fatal floor reduction (Target-owned; applied once): 110',text)
        action_text=text.split('Actions: causality and outcomes')[1].split('Targets: selected-boundary')[0]
        self.assertNotIn('floor reduction',action_text)
        self.assertIn('FatalEffect',html)

    def test_all_defenses_failed_and_successful_with_target_practice(self):
        f=self.f;strike=f.f.attack(melee=True)
        one=MeleeDefense(f.enc,f.b.id,f.a.id,kind='dodge',target_action_id=strike.id)
        two=MeleeDefense(f.enc,f.b.id,f.a.id,kind='dodge',target_action_id=strike.id)
        view=f.resolve((strike,one,two),(20,1,1,20));text,html=self.render(view)
        defense_text=text.split('All designated defenses')[1].split('Target-owned practice and experience')[0]
        self.assertIn(one.id,defense_text);self.assertIn(two.id,defense_text)
        self.assertIn('success: true',defense_text);self.assertIn('success: false',defense_text)
        self.assertIn('eligible: true',defense_text);self.assertIn('BatchSkillUse',text)
        self.assertIn('dodged',html)

    def test_ordinary_miss_and_endpoint_release_handoff(self):
        f=self.f;one=f.f.attack();view=f.resolve((one,),(2,));text,_=self.render(view)
        self.assertIn('Outcome: "miss"',text)
        f=fixtures.TestCombatInspection();f.setUp();old=f.f.attack(melee=True);boundary=__import__('math').ceil(old.end_time)
        new=f.f.attack(melee=True);new.start_time=boundary;new.end_time+=boundary
        view=f.resolve((old,new),(15,4,15,4));text,html=self.render(view)
        self.assertIn('ReservationReleaseEffect',text);self.assertIn('after_settlement: true',text)
        self.assertIn('after-settlement handoffs',html);self.assertIn(new.id,text)


if __name__=='__main__':unittest.main()
