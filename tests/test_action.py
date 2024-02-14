#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "test_action.py 2024-02-14T01:23-08:00"

import unittest
import sys
import os
#from unittest.mock import Mock

sys.path.insert(0, os.path.abspath('../src'))

from action import Action
from armor import ArmorInstance
from being import BeingDefinition, BeingInstance
from encounter import Encounter
from library import Library
from object import ObjectInstance
from strategy import Strategy
from universe import Universe
	
class TestAction(unittest.TestCase):

    def setUp(self):
        self.universe = Universe(name="Test Universe", library=Library(config_dir="../src/config"))
        self.start_time = 0
        self.end_time = 10
        # Actor: Tobez, zombie in tattered normal clothing with a longsword and wooden buckler
        # Target: Gordo, skeleton in rusty Ring mail with a short sword and buckler
        self.actor_id = self.universe.make_being("Zombie", "Tobez")
        self.instrument_id = self.universe.make_weapon_for_being(self.actor_id, "Longsword", "Loki")
        self.universe.arm_being(self.actor_id, self.instrument_id, "left hand")
        self.actor_shield_id = self.universe.make_weapon_for_being(self.actor_id, "Wooden buckler", "Woody")
        self.universe.arm_being(self.actor_id, self.actor_shield_id, "right hand")
        self.actor_armor_id = self.universe.make_armor_for_being(self.actor_id, "Normal clothing", "Tatters")

        self.target_id = self.universe.make_being("Skeleton", "Gordo")
        self.target_weapon_id = self.universe.make_weapon_for_being(self.target_id, "Short sword", "Tetanus")
        self.universe.arm_being(self.target_id, self.target_weapon_id, "right hand")
        self.target_shield_id = self.universe.make_weapon_for_being(self.target_id, "Buckler", "Buckles")
        self.universe.arm_being(self.target_id, self.target_shield_id, "left hand")
        self.target_armor_id = self.universe.make_armor_for_being(self.target_id, "Ring mail", "Rusty")

        self.strategy = Strategy()
        self.location = None
        self.parent_event_id = None

        self.action = Action(self.universe, self.start_time, self.end_time, "action",
                             self.actor_id, self.target_id, self.instrument_id, self.strategy,
                             self.location, "Test Action", self.parent_event_id)

        self.swing = Action(self.universe, self.start_time, self.end_time, "swing",
                             self.actor_id, self.target_id, self.instrument_id, self.strategy,
                             self.location, "Test Swing", self.parent_event_id)

        self.thrust = Action(self.universe, self.start_time, self.end_time, "thrust",
                             self.actor_id, self.target_id, self.instrument_id, self.strategy,
                             self.location, "Test Thrust", self.parent_event_id)

    # Test setters
    def test_set_actor_id(self):
        # Test setting an actor_id
        self.action.set_actor_id("test id")
        # actor_id set to None if no such Being exists in the Universe
        self.assertIsNone(self.action.actor_id)
        self.action.set_actor_id(self.target_id)
        # actor_id set if Being exists in the Universe
        self.assertEqual(self.action.actor_id, self.target_id)

    def test_set_target_id(self):
        # Test setting a target_id
        self.action.set_target_id("test id")
        # target_id set to None if no such Being exists in the Universe
        self.assertIsNone(self.action.target_id)
        self.action.set_target_id(self.actor_id)
        # target_id set if Being exists in the Universe
        self.assertEqual(self.action.target_id, self.actor_id)

    def test_set_instrument_id(self):
        # Test setting a instrument_id
        self.action.set_instrument_id("test id")
        # instrument_id set to None if no such Object exists in the Universe
        self.assertIsNone(self.action.instrument_id)

        new_instrument = self.universe.make_weapon("Short sword", "Scratchy")
        self.action.set_instrument_id(new_instrument)
        # instrument_id set if Object exists in the Universe
        self.assertEqual(self.action.instrument_id, new_instrument)

    def test_set_strategy(self):
        # Test setting an Action Strategy
        strategy = Strategy(1,2,3,4)
        self.action.set_strategy(strategy)
        self.assertEqual(self.action.strategy, strategy)

    # Test getters
    def test_get_actor(self):
        # Test getting the actor
        actor = self.action.get_actor()
        self.assertIsNotNone(actor)
        self.assertTrue(isinstance(actor,BeingInstance))
        self.assertEqual(actor.id, self.action.actor_id)

    def test_get_actor_armor_id(self):
        # Test getting the actor's armor id
        actor = self.action.get_actor()
        armor_id = self.action.get_actor_armor_id()
        self.assertEqual(armor_id, actor.get_armor_id())

    def test_get_actor_strategy(self):
        # Test getting the actor's strategy
        actor = self.action.get_actor()
        strategy = self.action.get_actor_strategy()
        self.assertEqual(strategy, actor.strategy)

    def test_get_target(self):
        # Test getting the target
        target = self.action.get_target()
        self.assertIsNotNone(target)
        self.assertTrue(isinstance(target,BeingInstance))
        self.assertEqual(target.id, self.action.target_id)

    def test_get_target_armor_id(self):
        # Test getting the target's armor id
        target = self.action.get_target()
        armor_id = self.action.get_target_armor_id()
        self.assertEqual(armor_id, target.get_armor_id())

    def test_get_target_strategy(self):
        # Test getting the target's strategy
        target = self.action.get_target()
        strategy = self.action.get_target_strategy()
        self.assertEqual(strategy,target.strategy)

    def test_get_instrument(self):
        # Test getting the instrument used in the Action
        instrument = self.action.get_instrument()
        self.assertIsNotNone(instrument)
        self.assertTrue(isinstance(instrument,ObjectInstance))
        self.assertEqual(instrument.id, self.action.instrument_id)

    def test_resolve_damage_to_actor_shield(self):
        # Test resolve the damage to the actor's shield
        # Run many times
        for i in range(100):
            self.setUp()
            gets_through = self.action._resolve_damage_to_actor_shield(5)
            actor = self.action.get_actor()
            actor_shield_id = actor.shielded_with(self.universe)["right hand"]
            shield = self.universe.get_object_by_id(actor_shield_id)
#            print(f"{i}) {shield.hit_points()} {gets_through}")
            self.assertTrue(shield.hit_points() == 11 or shield.hit_points() == 16)
            self.assertTrue(gets_through == 5 or gets_through == 4)

    def test_resolve_damage_to_target_shield(self):
        # Test resolve the damage to the target's shield
        # Run many times
        for i in range(100):
            self.setUp()
            gets_through = self.action._resolve_damage_to_target_shield(5)
            target = self.action.get_target()
            target_shield_id = target.shielded_with(self.universe)["left hand"]
            shield = self.universe.get_object_by_id(target_shield_id)
#            print(f"{i}) {shield.hit_points()} {gets_through}")
            self.assertTrue(shield.hit_points() == 11 or shield.hit_points() == 16)
            self.assertTrue(gets_through == 5 or gets_through == 4)

    def test_resolve_damage_to_actor_armor(self):
        # Test resolve the damage to the actor's armor
        self.setUp()
        gets_through = self.action._resolve_damage_to_actor_armor(2)
        actor = self.action.get_actor()
        actor_armor_id = actor.armored_with()
        armor = self.universe.get_object_by_id(actor_armor_id)
#        print(f"Armor hit points after {self.action.event_type}: {armor.hit_points()}, {gets_through} gets through")
        self.assertTrue(armor.hit_points() == 3)
        self.assertTrue(gets_through == 2)

        self.setUp()
        gets_through = self.swing._resolve_damage_to_actor_armor(2)
        actor = self.swing.get_actor()
        actor_armor_id = actor.armored_with()
        armor = self.universe.get_object_by_id(actor_armor_id)
#        print(f"Armor hit points after {self.swing.event_type}: {armor.hit_points()}, {gets_through} gets through")
        self.assertTrue(armor.hit_points() == 1)
        self.assertTrue(gets_through == 2)

        self.setUp()
        gets_through = self.thrust._resolve_damage_to_actor_armor(2)
        actor = self.thrust.get_actor()
        actor_armor_id = actor.armored_with()
        armor = self.universe.get_object_by_id(actor_armor_id)
#        print(f"Armor hit points after {self.thrust.event_type}: {armor.hit_points()}, {gets_through} gets through")
        self.assertTrue(armor.hit_points() == 3)
        self.assertTrue(gets_through == 2)

    def test_resolve_damage_to_target_armor(self):
        # Test resolve the damage to the target's armor
        self.setUp()
        # Longsword for 5 damage via Swing against Ring Mail
        gets_through = self.swing._resolve_damage_to_target_armor(5)
        actor = self.swing.get_actor()
        target = self.swing.get_target()
        target_armor_id = target.armored_with()
        armor = self.universe.get_object_by_id(target_armor_id)
#        print(f"Armor hit points after {self.swing.event_type}: {armor.hit_points()}, {gets_through} gets through")
        self.assertTrue(armor.hit_points() == 37)
        self.assertTrue(gets_through == 1)

        self.setUp()
        # Longsword for 5 damage via Thrust against Ring Mail
        gets_through = self.thrust._resolve_damage_to_target_armor(5)
        actor = self.thrust.get_actor()
        target = self.thrust.get_target()
        target_armor_id = target.armored_with()
        armor = self.universe.get_object_by_id(target_armor_id)
#        print(f"{armor.obj_type} hit points after {self.thrust.event_type}: {armor.hit_points()}, {gets_through} gets through")
        self.assertTrue(armor.hit_points() == 40)
        self.assertTrue(gets_through == 4)

    def test_damage_potential(self):
        self.assertEqual(self.swing.damage_potential(),8)
        self.assertEqual(self.thrust.damage_potential(),7)

    def test_do_critical_failure(self):               # Test swing critical failure        for i in range(100):
            self.setUp()
            actor = self.action.get_actor()
            actor_shield = self.universe.get_object_by_id(self.actor_shield_id)
            actor_armor = self.universe.get_object_by_id(self.actor_armor_id)
            target = self.action.get_target()
            target_shield = self.universe.get_object_by_id(self.target_shield_id)
            target_armor = self.universe.get_object_by_id(self.target_armor_id)
            self.swing.do_critical_failure()
#            print(f"{i} shield: {actor_shield.hit_points()} armor: {actor_armor.hit_points()} actor: {actor.hit_points()}")
            # TODO: Document expected range for remaining hit points on shield, armor, and target
            self.assertTrue(actor_shield.hit_points() >= 8 and actor_shield.hit_points() <= 16)
            self.assertTrue(actor_armor.hit_points() >= -5 and actor_armor.hit_points() <= 3)
            self.assertTrue(actor.hit_points() >= 14 and actor.hit_points() <= 22)
            self.assertEqual(target_shield.hit_points(),16)
            self.assertEqual(target_armor.hit_points(),40)
            self.assertEqual(target.hit_points(),13)

        # Test thrust critical failure        for i in range(100):
            self.setUp()
            actor = self.action.get_actor()
            actor_shield = self.universe.get_object_by_id(self.actor_shield_id)
            actor_armor = self.universe.get_object_by_id(self.actor_armor_id)
            target = self.action.get_target()
            target_shield = self.universe.get_object_by_id(self.target_shield_id)
            target_armor = self.universe.get_object_by_id(self.target_armor_id)
            self.thrust.do_critical_failure()
#            print(f"{i} shield: {actor_shield.hit_points()} armor: {actor_armor.hit_points()} actor: {actor.hit_points()}")
            # TODO: Document expected range for remaining hit points on shield, armor, and target
            self.assertTrue(actor_shield.hit_points() >= 9 and actor_shield.hit_points() <= 16)
            self.assertTrue(actor_armor.hit_points() >= -4 and actor_armor.hit_points() <= 3)
            self.assertTrue(actor.hit_points() >= 15 and actor.hit_points() <= 22)
            self.assertEqual(target_shield.hit_points(),16)
            self.assertEqual(target_armor.hit_points(),40)
            self.assertEqual(target.hit_points(),13)

    def test_do_critical_hit(self):               # Test swing critical hit
        for i in range(100):
            self.setUp()
            actor = self.action.get_actor()
            actor_shield = self.universe.get_object_by_id(self.actor_shield_id)
            actor_armor = self.universe.get_object_by_id(self.actor_armor_id)
            target = self.action.get_target()
            target_shield = self.universe.get_object_by_id(self.target_shield_id)
            target_armor = self.universe.get_object_by_id(self.target_armor_id)
            self.swing.do_critical_hit()
#            print(f"{i} shield: {target_shield.hit_points()} armor: {target_armor.hit_points()} target: {target.hit_points()}")
            # TODO: Document expected range for remaining hit points on shield, armor, and target
            self.assertTrue(target_shield.hit_points() >= 8 and target_shield.hit_points() <= 16)
            self.assertTrue(target_armor.hit_points() >= 32 and target_armor.hit_points() <= 40)
            self.assertTrue(target.hit_points() >= -3 and target.hit_points() <= 13)
            self.assertEqual(actor_shield.hit_points(),16)
            self.assertEqual(actor_armor.hit_points(),3)
            self.assertEqual(actor.hit_points(),22)

        # Test swing critical hit
        for i in range(100):
            self.setUp()
            actor = self.action.get_actor()
            actor_shield = self.universe.get_object_by_id(self.actor_shield_id)
            actor_armor = self.universe.get_object_by_id(self.actor_armor_id)
            target = self.action.get_target()
            target_shield = self.universe.get_object_by_id(self.target_shield_id)
            target_armor = self.universe.get_object_by_id(self.target_armor_id)
            self.thrust.do_critical_hit()
#            print(f"{i} shield: {target_shield.hit_points()} armor: {target_armor.hit_points()} target: {target.hit_points()}")
            # TODO: Document expected range for remaining hit points on shield, armor, and target
            self.assertTrue(target_shield.hit_points() >= 9 and target_shield.hit_points() <= 16)
            self.assertTrue(target_armor.hit_points() >= 33 and target_armor.hit_points() <= 40)
            self.assertTrue(target.hit_points() >= -1 and target.hit_points() <= 13)
            self.assertEqual(actor_shield.hit_points(),16)
            self.assertEqual(actor_armor.hit_points(),3)
            self.assertEqual(actor.hit_points(),22)

    def test_do_drop_weapon(self):               # Test drop weapon
        # TODO: Not implemented
        pass

    def test_do_fatal_hit(self):               # Test fatal hit
        self.setUp()
        target = self.action.get_target()
        self.action.do_fatal_hit()
        self.assertEqual(target.hit_points(),-10)

        self.setUp()
        target = self.action.get_target()
        self.swing.do_fatal_hit()
        self.assertEqual(target.hit_points(),-10)

        self.setUp()
        target = self.action.get_target()
        self.thrust.do_fatal_hit()
        self.assertEqual(target.hit_points(),-10)

        self.setUp()
        target = self.action.get_target()
        target.set_hit_points(-11)
        self.action.do_fatal_hit()
        self.assertEqual(target.hit_points(),-11)

        self.setUp()
        target = self.action.get_target()
        target.set_hit_points(-12)
        self.swing.do_fatal_hit()
        self.assertEqual(target.hit_points(),-12)

        self.setUp()
        target = self.action.get_target()
        target.set_hit_points(-13)
        self.thrust.do_fatal_hit()
        self.assertEqual(target.hit_points(),-13)

    def test_do_miss(self):
        # Test miss
        self.setUp()
        actor = self.action.get_actor()
        target = self.action.get_target()
        self.action.do_miss()
        self.assertEqual(actor.hit_points(),22)
        self.assertEqual(target.hit_points(),13)

    def test_do_spectacular_miss(self):
        # Test spectacular miss
        self.setUp()
        actor = self.action.get_actor()
        target = self.action.get_target()
        self.action.do_spectacular_miss()
        self.assertEqual(actor.hit_points(),22)
        self.assertEqual(target.hit_points(),13)

    def test_do_normal_hit(self):
        # Test hit
        # Swing
        for i in range(100):
            self.setUp()
            actor = self.action.get_actor()
            target = self.action.get_target()
            self.swing.do_normal_hit()
#            print(f"{i} target: {target.hit_points()}")
            # TODO: Document expected range for remaining hit points on shield, armor, and target
            self.assertEqual(actor.hit_points(),22)
            self.assertTrue(target.hit_points() <=13 and target.hit_points() >= 9)

        # Thrust
        for i in range(100):
            self.setUp()
            actor = self.action.get_actor()
            target = self.action.get_target()
            self.thrust.do_normal_hit()
#            print(f"{i} target: {target.hit_points()}")
            # TODO: Document expected range for remaining hit points on shield, armor, and target
            self.assertEqual(actor.hit_points(),22)
            self.assertTrue(target.hit_points() <=13 and target.hit_points() >= 7)

    def test_do_hit_result(self):
        # Test hit result
        for i in range(100):
            self.setUp()
            result = self.action.hit_result(10)
            self.assertTrue(result in ["fatal", "critical", "normal", "hit self", "miss", "spectacular miss", "drop weapon"])
#            print(f"{i} {result}")

    def test_resolve(self):
        # Test resolve
        # No necessary test
        pass
        
    def test_roll_hits(self):
        # Test roll_hits method with various scenarios
        self.assertFalse(self.action.roll_hits(9,10))
        self.assertTrue(self.action.roll_hits(10,10))
        self.assertTrue(self.action.roll_hits(11,10))

        self.assertFalse(self.action.roll_hits(14,15))
        self.assertTrue(self.action.roll_hits(15,15))
        self.assertTrue(self.action.roll_hits(20,20))

    def test_calculate_end_time(self):
        self.assertEqual(self.action.calculate_end_time(5,6), 1)
        self.assertEqual(self.action.calculate_end_time(5,5), 1)
        self.assertEqual(self.action.calculate_end_time(5,4), 1)
        self.assertEqual(self.action.calculate_end_time(5,3), 2)
        self.assertEqual(self.action.calculate_end_time(5,1), 4)
        self.assertEqual(self.action.calculate_end_time(5,0), 5)

if __name__ == '__main__':
    unittest.main()

if __name__ == '__main__':
    unittest.main()
