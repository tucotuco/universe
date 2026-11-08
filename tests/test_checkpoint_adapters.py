"""5D2A inactive recipes/bindings, not restoration or complete closure."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dataclasses import replace
from unittest.mock import patch
import random
import unittest
import test_encounter_inspection as fixtures
from checkpoint_inventory import capture_checkpoint_candidate as capture,validate_checkpoint_candidate as validate,CheckpointRejected
from checkpoint_adapters import RecipientBinding
from field_observation import BeliefLedger
from history_conversation import AskAboutPastAction
from activities import RunAction
from encounter import ArenaActionActivation, EncounterInitiation
from realization import Fact, FactKey, CommittedFact
from conditional_attributes import ConditionalAttributes
from statistical_group import StatisticalGroup
from personal_history import PersonalHistory
from test_checkpoint_inventory import strings,tags
from interval_staging import IntervalIntegrityError


class TestNativeCheckpointAdapters(fixtures.InspectionFixture):
    def capture(self,bindings=(),**kwargs):
        return capture(self.world,self.enc,quiescent=True,rng_scope='exclusive_encounter',native_adapters=True,bindings=bindings,**kwargs)

    def binding(self,value,name='one',observers=None,**changes):
        role='in_world_belief_ledger' if type(value)is BeliefLedger else 'in_world_received_accounts'
        ids=(value.observer_id,) if type(value)is BeliefLedger else (self.c.id,)
        return replace(RecipientBinding(self.world,'test-host',name,role,ids if observers is None else observers,value),**changes)

    def assert_partial(self,c):
        result=validate(self.world,self.enc,c,quiescent=True)
        self.assertTrue(result.inventory_validated)
        self.assertFalse(result.closure_validated);self.assertFalse(result.portable_schema_defined);self.assertFalse(result.restore_verified)
        with self.assertRaises(CheckpointRejected):result.require_complete()

    def group(self,name='group-one'):return self.f.f.f.group(name=name)

    def mixed(self):
        group=self.group();history=self.f.f.f.history();ledger=BeliefLedger(self.a.id);accounts=[]
        self.enable();one=self.f.f.observe(self.a,group,ledger=ledger)
        ask=AskAboutPastAction(self.world,self.c.id,self.a.id,0,episode_time=0,topic='lessons',generate=self.f.f.f.recipe(history),received_accounts=accounts)
        self.enc.schedule_choice((one,ask));self.enc.step(1)
        return group,history,ledger,accounts,(self.binding(ledger,'belief'),self.binding(accounts,'testimony'))

    def test_initial_native_closed_vocabulary_is_partial_readonly(self):
        self.enable();before=self.raw();c=self.capture();self.assert_partial(c)
        self.assertEqual(before,self.raw());self.assertIn('native-closure-recipes/1',set(strings(c.envelope)))

    def test_unstarted_arena_opt_in_is_outside_the_initiated_checkpoint_path(self):
        self.enable()
        self.enc.arena_activation_enabled = True
        self.enc.initiated = False
        with self.assertRaisesRegex(IntervalIntegrityError, 'interval requires an initiated Encounter'):
            self.capture()

    def test_activated_arena_is_refused_without_capture_mutation(self):
        self.enable()
        self.enc.arena_activation_enabled = True
        self.enc.initiated = True
        self.enc.arena_activation = ArenaActionActivation(
            self.enc.id, self.a.id, 'choice-authored-test', self.enc.time)
        before = self.raw()
        with self.assertRaisesRegex(CheckpointRejected, 'activated Arena Encounter cannot be resumed'):
            self.capture()
        self.assertEqual(before, self.raw())

    def test_target_directed_initiation_is_not_confused_with_arena_activation(self):
        self.enable()
        self.enc.initiated = True
        self.enc.initiation = EncounterInitiation(self.a.id, self.b.id, 'approach', self.enc.time)
        candidate = self.capture()
        reasons = tuple(item.reason for item in candidate.diagnostics)
        self.assertTrue(any('target-directed Encounter initiation' in reason for reason in reasons))
        self.assertNotIn('bounded_run_spot_closure_verified',
                         {item.code for item in candidate.diagnostics})

    def test_hex_facing_requires_unknown_or_canonical_integer(self):
        self.enable()
        self.a.set_hex_facing(0)
        self.assert_partial(self.capture())
        self.a.set_hex_facing(11)
        self.assert_partial(self.capture())
        self.a.hex_facing = True
        candidate = self.capture()
        self.assertTrue(any('invalid native hex facing' in item.reason
                            for item in candidate.diagnostics))
        self.assertNotIn('bounded_run_spot_closure_verified',
                         {item.code for item in candidate.diagnostics})

    def test_missing_hex_facing_is_rejected_by_closed_required_inventory(self):
        self.enable()
        del self.a.hex_facing
        with self.assertRaisesRegex(CheckpointRejected, 'missing native fields: being.BeingInstance'):
            self.capture()

    def test_accepted_unstarted_future_and_fractional_positions(self):
        self.enable();a=RunAction(self.world,self.a.id,.25,1,1);b=self.f.spot(self.c,start=3)
        self.enc.schedule_choice((a,b));first=self.capture();self.assert_partial(first)
        self.enc.step(1,velocities={self.a.id:(2,0,0)})
        with self.assertRaisesRegex(ValueError,'stale'):validate(self.world,self.enc,first,quiescent=True)
        c=self.capture();self.assert_partial(c);self.assertIn(float(.25).hex(),set(strings(c.envelope)))
        self.assertIn(b.id,set(strings(c.envelope)));self.assertIn('start_position',set(strings(c.envelope)))

    def test_multisecond_receipts_and_new_planning_stale_inventory(self):
        self.commit();self.enc.step(2);c=self.capture();self.assert_partial(c)
        self.enc.schedule_action(self.f.spot(start=4))
        with self.assertRaises(ValueError):validate(self.world,self.enc,c,quiescent=True)
        self.assert_partial(self.capture())

    def test_empty_native_conditional_store_and_keyed_recipe_no_draws(self):
        g=self.group();self.enable();before=self.raw()
        with patch.object(ConditionalAttributes,'resolve',side_effect=AssertionError('resolve')):
            c=self.capture();self.assert_partial(c)
        self.assertEqual(before,self.raw());self.assertIn('conditional_attributes.ConditionalAttributes',tags(c))
        self.assertIn('statistical_group.formation_attribute_rng',set(strings(c.envelope)))
        self.assertNotIn('conditional_attribute_adapter_missing',{d.code for d in c.diagnostics})

    def test_conditional_specs_dependencies_and_existing_values(self):
        g=self.group();store=g._conditional_attributes
        store.specifications={'color':{'cdf':[['red',1.0]]},'tone':{'given':'color','conditional_cdfs':{'red':[['bright',1.0]]}}}
        # Establish facts through existing native API before capture; capture never samples.
        g.household_count;g.household(0);identity=g.id+'/0/adults/0'
        store.resolve(identity,'tone');self.enable();before=self.raw();c=self.capture();self.assert_partial(c)
        self.assertEqual(before,self.raw());self.assertIn('bright',set(strings(c.envelope)))
        store._committed[identity]['tone']='impossible'
        with self.assertRaisesRegex(ValueError,'impossible'):self.capture()

    def test_conditional_external_names_are_not_external_values(self):
        g=self.group();g._formation_traits={'adults':{'trained':{}}};s=g._conditional_attributes;s._external={'trained'}
        s.specifications={'color':{'given':'trained','conditional_cdfs':{'true':[['red',1]],'false':[['blue',1]]}}}
        g.household_count;g.household(0);s._committed[g.id+'/0/adults/0']={'color':'red'}
        self.enable();c=self.capture();self.assert_partial(c)
        self.assertIn('conditional_external_assignment_validation_pending',{d.code for d in c.diagnostics})

    def test_invalid_conditional_specs_and_cycles_refuse(self):
        g=self.group();self.enable()
        for specs in ({'a':{'unknown':[]}}, {'a':{'given':'a','conditional_cdfs':{'x':[['y',1]]}}}, {'a':{'cdf':[['x',.5]]}}):
            g._conditional_attributes.specifications=specs
            with self.subTest(specs=specs),self.assertRaises(ValueError):self.capture()

    def test_conditional_missing_parent_and_unestablished_member_refuse(self):
        g=self.group();self.enable();s=g._conditional_attributes
        s.specifications={'a':{'cdf':[['x',1]]},'b':{'given':'a','conditional_cdfs':{'x':[['y',1]]}}}
        s._committed[g.id+'/0/adults/0']={'b':'y'}
        with self.assertRaisesRegex(ValueError,'household'):self.capture()
        g.household_count;g.household(0)
        with self.assertRaisesRegex(ValueError,'parent'):self.capture()

    def test_unknown_provider_not_invoked_and_foreign_lambda_refused(self):
        g=self.group();self.enable();seen=[];g._conditional_attributes._rng_for=lambda *a:seen.append(a)
        with self.assertRaisesRegex(ValueError,'provider'):self.capture()
        self.assertEqual(seen,[])
        other=self.group("other-group");g._conditional_attributes._rng_for=other._conditional_attributes._rng_for
        with self.assertRaises((ValueError,TypeError)):self.capture()

    def test_shared_conditional_store_refused(self):
        one=self.group();two=self.group("second-group");two._conditional_attributes=one._conditional_attributes;self.enable()
        with self.assertRaisesRegex(ValueError,'shared native owner'):self.capture()

    def test_bound_native_objective_and_subjective_state(self):
        g,h,l,a,b=self.mixed();before=self.raw();c=self.capture(b);self.assert_partial(c);self.assertEqual(before,self.raw())
        text=set(strings(c.envelope))
        for recipe in ('personal_history.validate_history_constraints','statistical_group.validate_composition_records','host-recipient'):
            self.assertIn(recipe,text)
        for obj in (l,a,h.reality,g._composition_reality):self.assertNotIn(str(id(obj)),text)
        self.assertFalse({'unbound_recipient_identity','unbound_external_recipient','validator_rehydration_required'} & {d.code for d in c.diagnostics})

    def test_missing_external_binding_refused(self):
        self.mixed()
        with self.assertRaisesRegex(ValueError,'binding'):self.capture()

    def test_two_ledgers_one_observer_have_distinct_explicit_names(self):
        self.enable();a,b=BeliefLedger(self.a.id),BeliefLedger(self.a.id)
        c=self.capture((self.binding(a,'first'),self.binding(b,'second')));self.assert_partial(c)
        self.assertIn('first',set(strings(c.envelope)));self.assertIn('second',set(strings(c.envelope)))

    def test_shared_account_container_preserves_one_binding(self):
        self.f.f.f.history();accounts=[];self.enable()
        for actor in (self.b,self.c):
            action=AskAboutPastAction(self.world,actor.id,self.a.id,0,episode_time=0,topic='lessons',generate=self.f.f.f.recipe(self.a.personal_history),received_accounts=accounts)
            self.enc.schedule_action(action)
        binding=self.binding(accounts,observers=(self.b.id,self.c.id));c=self.capture((binding,));self.assert_partial(c)
        nodes=c.envelope[1][2][1]
        self.assertEqual(sum(n[0]==('host-recipient',self.world.id,'test-host','one') for n in nodes),1)
        self.enc.step(1);self.assert_partial(self.capture((binding,)));self.assertEqual(len(accounts),2)

    def test_duplicate_names_and_duplicate_physical_recipient_refuse(self):
        self.enable();a,b=BeliefLedger(self.a.id),BeliefLedger(self.a.id)
        for bindings in ((self.binding(a),self.binding(b)),(self.binding(a,'a'),self.binding(a,'b'))):
            with self.subTest(bindings=bindings),self.assertRaises(ValueError):self.capture(bindings)

    def test_foreign_binding_root_role_and_observer_refuse(self):
        self.enable();ledger=BeliefLedger(self.a.id);other=fixtures.InspectionFixture();other.setUp()
        binding=self.binding(ledger)
        for b in (replace(binding,world=other.world),replace(binding,role='unknown'),replace(binding,observer_ids=(self.b.id,)),replace(binding,observer_ids=('absent',)),replace(binding,name='')):
            with self.subTest(b=b),self.assertRaises(ValueError):self.capture((b,))

    def test_aliased_ledger_internals_refuse(self):
        self.enable();a,b=BeliefLedger(self.a.id),BeliefLedger(self.b.id);b._evidence=a._evidence
        with self.assertRaisesRegex(ValueError,'shared recipient internal'):self.capture((self.binding(a,'a'),self.binding(b,'b')))

    def test_opaque_binding_argument_never_invokes_equality(self):
        self.enable();seen=[]
        class Hostile:
            def __eq__(self,other):seen.append('eq');raise AssertionError('callback')
        with self.assertRaises(ValueError):capture(self.world,self.enc,quiescent=True,bindings=Hostile())
        self.assertEqual(seen,[])

    def test_bindings_must_be_explicit_tuple_and_adapter_mode(self):
        self.enable()
        with self.assertRaises(ValueError):self.capture([])
        with self.assertRaises(ValueError):capture(self.world,self.enc,quiescent=True,bindings=(self.binding([]),))

    def test_binding_changed_name_and_equal_content_replacement_are_stale(self):
        self.enable();ledger=BeliefLedger(self.a.id);binding=self.binding(ledger);c=self.capture((binding,))
        ledger._evidence={}
        with self.assertRaisesRegex(ValueError,'stale'):validate(self.world,self.enc,c,quiescent=True)
        c=self.capture((binding,));object.__setattr__(binding,'name','changed')
        with self.assertRaisesRegex(ValueError,'stale'):validate(self.world,self.enc,c,quiescent=True)

    def test_history_native_recipe_preserves_facts_prior_experience_and_bounds(self):
        h=self.f.f.f.history();self.enable();before=self.raw();c=self.capture();self.assert_partial(c)
        self.assertIn('personal_history.validate_history_constraints',set(strings(c.envelope)));self.assertEqual(before,self.raw())
        h.known_through=-11
        with self.assertRaises((ValueError,TypeError)):self.capture()

    def test_custom_history_and_group_validators_never_invoked(self):
        h=self.f.f.f.history();g=self.group();self.enable();seen=[]
        native=h.reality._validators;h.reality._validators=(lambda v:seen.append(v),)
        with self.assertRaises((ValueError,TypeError)):self.capture()
        h.reality._validators=native;g._composition_reality._validators=(lambda v:seen.append(v),)
        with self.assertRaises((ValueError,TypeError)):self.capture()
        self.assertEqual(seen,[])

    def test_missing_native_constraint_and_revision_corruption_refused(self):
        g=self.group();self.enable();g._composition_reality._validators=()
        with self.assertRaises((ValueError,TypeError)):self.capture()
        g._composition_reality._validators=(g._validate_composition_facts,);g.household_count
        g._composition_reality._revision+=1
        with self.assertRaises((ValueError,TypeError)):self.capture()

    def test_extra_fields_on_world_definitions_and_conditional_store_refuse(self):
        g=self.group();self.enable()
        for obj in (self.world,self.a.current,self.world.library,g._conditional_attributes):
            obj.unreviewed=0
            with self.subTest(obj=type(obj)),self.assertRaisesRegex(ValueError,'unknown native fields'):self.capture()
            del obj.unreviewed

    def test_closed_field_table_rejects_dataclass_missing_field(self):
        self.enable();del self.a.physical_fatigue.__dict__['q']
        with self.assertRaises((ValueError,KeyError)):self.capture()

    def test_container_cycles_and_shared_entity_state_refuse(self):
        self.enable();self.a.current.tags['loop']=self.a.current.tags
        with self.assertRaises((ValueError,TypeError)):self.capture()
        self.a.current.tags.pop('loop');self.b.current=self.a.current
        with self.assertRaisesRegex(ValueError,'shared live entity'):self.capture()

    def test_unreferenced_entity_dangling_links_and_cycles_refuse(self):
        self.enable();self.a.parent_container_id='missing'
        with self.assertRaises((ValueError,TypeError)):self.capture()
        self.a.parent_container_id=self.b.id;self.b.parent_container_id=self.a.id
        with self.assertRaises((ValueError,TypeError)):self.capture()

    def test_dangling_equipment_and_possessions_refuse(self):
        self.enable();self.a.possessions.append('missing')
        with self.assertRaisesRegex(ValueError,'dangling equipment'):self.capture()

    def test_native_adapter_requires_private_rng_assertion(self):
        self.enable()
        with self.assertRaisesRegex(ValueError,'private RNG'):capture(self.world,self.enc,quiescent=True,native_adapters=True)

    def test_no_evaluation_publication_or_serialization_on_capture(self):
        self.enable();before=self.raw()
        with patch('observer_proposals.build_supported_candidate',side_effect=AssertionError('evaluate')), \
             patch.object(self.enc,'step',side_effect=AssertionError('step')):
            # A method injected into an authoritative native instance is an unknown field.
            with self.assertRaises((ValueError,TypeError)):self.capture()
        with patch('observer_proposals.build_supported_candidate',side_effect=AssertionError('evaluate')):
            self.assert_partial(self.capture())
        self.assertEqual(before,self.raw())
        with self.assertRaises(ValueError):self.world.to_json()
        with self.assertRaises(ValueError):self.enc.to_json()

    def test_cancelled_action_lifecycle_is_a_known_native_shape(self):
        self.enable();action=self.f.spot(start=.25);self.enc.schedule_action(action);self.enc.step(1)
        self.enc.cancel_action(action.id);self.enc.step(1)
        c=self.capture();self.assert_partial(c)
        self.assertIn('canceled_at',set(strings(c.envelope)))
        self.assertIn('cancelled',set(strings(c.envelope)))

    def test_qb_and_physiology_references_have_native_field_adapters(self):
        from physical_fatigue import PhysicalFatigueState
        from physiology_registry import PhysiologyRegistry,PhysiologyDefinition
        self.a.physical_fatigue=PhysicalFatigueState(.75,.5)
        self.enc.set_physiology_registry(PhysiologyRegistry((PhysiologyDefinition('human@1',model='human-r4'),)))
        for being in (self.a,self.b,self.c):being.physiology_id='human@1'
        self.enable();before=self.raw();c=self.capture();self.assert_partial(c)
        self.assertIn('physiology_registry.PhysiologyDefinition',tags(c));self.assertEqual(before,self.raw())
        self.assertEqual(self.a.physical_fatigue.q,.75)

    def test_simultaneous_practice_remains_target_owned(self):
        self.enable();a=RunAction(self.world,self.a.id,0,1,.5,experience=3);b=RunAction(self.world,self.a.id,0,1,.5,experience=4);self.enc.schedule_choice((a,b));self.enc.step(1,velocities={self.a.id:(1,0,0)})
        c=self.capture();self.assert_partial(c);self.assertIn('experience.BatchSkillUse',tags(c))

    def test_unknown_subclasses_are_not_promoted(self):
        g=self.group();self.enable()
        class Custom(ConditionalAttributes):pass
        g._conditional_attributes.__class__=Custom
        with self.assertRaises((ValueError,TypeError)):self.capture()

    def test_detached_stable_recapture_and_modified_readiness_refused(self):
        self.enable();c=self.capture();d=self.capture();self.assertEqual(c.envelope,d.envelope)
        self.assertEqual(c.diagnostics,d.diagnostics)
        with self.assertRaises(ValueError):validate(self.world,self.enc,replace(c,closure_validated=True),quiescent=True)


    def test_cached_group_totals_are_validated_without_realization(self):
        g=self.group();g.counts();self.enable();self.assert_partial(self.capture())
        g._counts['adults']+=1
        with self.assertRaisesRegex(ValueError,'cache'):self.capture()

    def test_external_only_belief_records_get_native_validation(self):
        self.enable();ledger=BeliefLedger(self.a.id);ledger._evidence['bad']=1
        with self.assertRaises((ValueError,TypeError)):self.capture((self.binding(ledger),))

    def test_binding_cannot_relabel_another_recipients_internal_list(self):
        self.enable();ledger=BeliefLedger(self.a.id)
        with self.assertRaisesRegex(ValueError,'aliases another recipient'):
            self.capture((self.binding(ledger,'belief'),self.binding(ledger.communication_log,'accounts')))


class TestNativeCombatClosureAdapters(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.TestCombatInspection();self.f.setUp()

    def capture(self):
        f=self.f
        c=capture(f.world,f.enc,quiescent=True,rng_scope='exclusive_encounter',native_adapters=True)
        self.assertTrue(validate(f.world,f.enc,c,quiescent=True).inventory_validated)
        self.assertFalse(c.closure_validated);self.assertFalse(c.restore_verified)
        return c

    def test_additive_negative_hp_and_target_owned_results(self):
        f=self.f;f.b.current.hit_points=12;one,two=f.f.attack(extra=4),f.f.attack(f.f.w2,extra=3)
        f.resolve((one,two),(15,4,15,4));c=self.capture()
        self.assertEqual(f.b.current.hit_points,-3);self.assertIn('action_settlement.TargetCandidate',tags(c))
        self.assertFalse(any('hp_before' in k or 'hp_after' in k for k in vars(one.resolution)))

    def test_nonstacking_fatal_effects_are_preserved(self):
        f=self.f;one,two=f.f.attack(),f.f.attack(f.f.w2)
        f.resolve((one,two),(20,20,1,20,20,1));c=self.capture()
        self.assertEqual(f.b.current.hit_points,-10);self.assertIn('action_evaluation.FatalEffect',tags(c))

    def test_all_designated_defenses_are_preserved(self):
        from melee_defense import MeleeDefense
        f=self.f;strike=f.f.attack(melee=True)
        defenses=[MeleeDefense(f.enc,f.b.id,f.a.id,kind='dodge',target_action_id=strike.id) for _ in range(2)]
        f.resolve((strike,*defenses),(20,1,1,20));c=self.capture()
        for d in defenses:self.assertIn(d.id,set(strings(c.envelope)))
        self.assertEqual(len(strike.resolution.defenses),2)

    def test_negative_armor_and_passive_shield_remain_objects(self):
        for equipment in ('armor','shield'):
            with self.subTest(equipment=equipment):
                self.setUp();f=self.f
                if equipment=='armor':
                    eid=f.world.make_armor_for_being(f.b.id,'Leather armor','Jacket');f.world.armor_being(f.b.id,eid);rolls=(15,4,15,4)
                else:
                    eid=f.world.make_weapon_for_being(f.b.id,'Small shield','Shield');f.world.arm_being(f.b.id,eid,'shield hand');rolls=(15,4,1,15,4,1)
                obj=f.world.get_object_by_id(eid);obj.current.hit_points=1
                f.resolve((f.f.attack(),f.f.attack(f.f.w2)),rolls);c=self.capture()
                self.assertLess(obj.current.hit_points,0);self.assertIn(eid,set(strings(c.envelope)))


if __name__=='__main__':unittest.main()
