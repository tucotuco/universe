#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "main.py 2023-01-02T15:46-03:00"

# TODO: Figure out what this will do an implement it. Requires complete refactor.

import argparse

from identifiable import Identifiable
from universe import Universe

from worldmap import WorldMap
from object import Object
from being import Being
from encounter import Encounter, EncounterHistory
from weapon import Weapon, WeaponDefinition

def test():
  nl = '\n'
  universe = Thing(name='The Universe')
  print(f'{universe.as_text()}{nl}')

  earth = World('Earth', 100, 100)
  
  rock = Object(mass=1, length=0.2, width=0.2, height=0.2, hp=2, name="Tobe's rock")
  print(f'{rock.as_text()}{nl}')
  
  npc = Being(mass=172.5, length=1, width=2, height=5.75, hp=6, name='Tobe')
  print(f'{npc.as_text()}{nl}')

  encounter = Encounter(starttime=0, x=0, y=0)
  encounter_history = EncounterHistory()
  encounter_history.add_encounter(encounter)

  weapon_definitions = setup_weapons_list()
  loki = Weapon(mass=1, length=2, width=0.1, height=0.1, hp=6, name='Loki')
  loki.set_weapon_definition(weapon_definitions.get('longsword'))

def setup_weapons_list():
  weapon_definitions = {}

  weapon_name = 'longsword'
  weapon_definition = WeaponDefinition(weapon_name)
  weapon_definition.add_attack_category('Blunt throw', 'Throw', 'Bludgeon', 6, 4, 3.5)
  weapon_definition.add_attack_category('Piercing throw', 'Throw', 'Pierce', 6, 7, 3.5)
  weapon_definition.add_attack_category('Blunt swing', 'Swing', 'Bludgeon', 6, 4, 3.5)
  weapon_definition.add_attack_category('Slashing swing', 'Swing', 'Slash', 6, 8, 3.5)
  weapon_definition.add_attack_category('Blunt thrust', 'Thrust', 'Bludgeon', 5, 3, 0.5)
  weapon_definition.add_attack_category('Piercing thrust', 'Thrust', 'Pierce', 5, 7, 3.5)
  weapon_definitions[weapon_name] = weapon_definition
  
  weapon_name = 'dagger'
  weapon_definition = WeaponDefinition(weapon_name)
  weapon_definition.add_attack_category('Blunt throw', 'Throw', 'Bludgeon', 4, 3, 3.5)
  weapon_definition.add_attack_category('Piercing throw', 'Throw', 'Pierce', 4, 4, 3.5)
  weapon_definition.add_attack_category('Blunt swing', 'Swing', 'Bludgeon', 4, 3, 3.5)
  weapon_definition.add_attack_category('Slashing swing', 'Swing', 'Slash', 4, 4, 3.5)
  weapon_definition.add_attack_category('Blunt thrust', 'Thrust', 'Bludgeon', 4, 3, 0.5)
  weapon_definition.add_attack_category('Piercing thrust', 'Thrust', 'Pierce', 4, 4, 3.5)
  weapon_definitions[weapon_name] = weapon_definition

  weapon_name = 'battleaxe'
  weapon_definition = WeaponDefinition(weapon_name)
  weapon_definition.add_attack_category('Blunt throw', 'Throw', 'Bludgeon', 4, 3, 3.5)
  weapon_definition.add_attack_category('Piercing throw', 'Throw', 'Pierce', 4, 4, 3.5)
  weapon_definition.add_attack_category('Blunt swing', 'Swing', 'Bludgeon', 4, 3, 3.5)
  weapon_definition.add_attack_category('Slashing swing', 'Swing', 'Slash', 4, 4, 3.5)
  weapon_definition.add_attack_category('Blunt thrust', 'Thrust', 'Bludgeon', 4, 3, 0.5)
  weapon_definition.add_attack_category('Piercing thrust', 'Thrust', 'Pierce', 4, 4, 3.5)
  weapon_definitions[weapon_name] = weapon_definition

  return weapon_definitions

def _getoptions():
  ''' Parse command line options and return them.'''
  parser = argparse.ArgumentParser()

  help = 'weapon to loo up (required)'
  parser.add_argument("-c", "--choice", help=help)

  help = 'directory for the output file (optional)'
  parser.add_argument("-w", "--workspace", help=help)

  help = 'full path to the input file (required)'
  parser.add_argument("-i", "--inputfile", help=help)

  help = 'output file name, no path (optional)'
  parser.add_argument("-o", "--outputfile", help=help)

  help = 'log level (e.g., DEBUG, WARNING, INFO) (optional)'
  parser.add_argument("-l", "--loglevel", help=help)

  return parser.parse_args()

def main():
  options = _getoptions()

  if options.choice is None or len(options.choice)==0:
    s =  'syntax:\n'
    s += 'python object.py'
    s += ' -c Longsword'
    s += ' -w ./workspace'
    s += ' -i universe.json'
    s += ' -o universe.json'
    s += ' -l DEBUG'
    print(f'{s}')
    return

  test()

  weapons_list = setup_weapons_list()
  weapon = weapons_list.get(options.choice)
  if weapon is not None:
    s = weapon.as_text('\n')
    print(f'{s}')
  else:
    print(f'Weapon "{options.choice}" not found in the weapons list')

if __name__ == '__main__':
  main()
