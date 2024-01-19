#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "main.py 2024-01-19T02:12-08:00"

# TODO: Figure out what this will do and implement it. Requires complete refactor.

import argparse
import os

from identifiable import Identifiable
from universe import Universe
from library import Library
from utils import roll_dice

from actiondictionary import ActionDictionary
from object import ObjectInstance, ObjectDefinition, ObjectRegistry
from being import BeingInstance, BeingDefinition, BeingDictionary
from encounter import Encounter
from speeds import Speed
from weapon import WeaponInstance, WeaponDefinition, WeaponDictionary

def test1(library, universe_output_file):
  # Make a Universe to play in
  tobes_universe = Universe(name="Tobe's Universe", library=library)

  # Make an Encounter to play in
  encounter = Encounter(tobes_universe, difficulty_class=15, start_time=0, end_time=None, 
                 event_type="Encounter", location=None, name="Tobe's Big Day", 
                 parent_event=None, id=None, initiated=False, map=None)
  tobes_universe.add_event(encounter)

  # Make a Being
  tobe_id = encounter.make_being("Half-elf", "Tobe")

  # Make a another Being
  grak_id = encounter.make_being("Kobold", "Grak")

  print(f"Being list: {encounter.being_list}")
  # Here you could modify the Beings' properties

  # Here you give the Beings possessions, arm them, armor them, etc.

  # Make an Object for a Being
  tobes_rock_id = encounter.make_object_for_being(tobe_id, "Rock", "Tobe's rock")
  tobes_rock = tobes_universe.get_object_by_id(tobes_rock_id)
  tobes_rock.resize_percent(0.2)
  tobes_rock.reweight_percent(0.2)

  # Make a Weapon for a Being
  weapon_id = encounter.make_weapon_for_being(tobe_id, "Longsword", "Loki")
  encounter.arm_being(tobe_id, weapon_id, "right hand")

  # Make a Weapon for a Being
  weapon_id = encounter.make_weapon_for_being(grak_id, "Short sword", "Pilfer")
  encounter.arm_being(grak_id, weapon_id, "right hand")

  tobe = tobes_universe.get_object_by_id(tobe_id)
#  print(f"Tobe: {tobe.to_json()}")

  grak = tobes_universe.get_object_by_id(grak_id)
#  print(f"Grak: {grak.to_json()}")
  encounter.run()

  tobes_universe.save_to_file(universe_output_file)
  print(f"Tobe's Universe saved to {universe_output_file}")

def _getoptions():
  ''' Parse command line options and return them.'''
  parser = argparse.ArgumentParser()

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

  if options.workspace is None or len(options.workspace)==0:
    s =  'syntax:\n'
    s += 'python main.py'
    s += ' -w ./workspace'
    s += ' -i universe.json'
    s += ' -o universe.json'
    s += ' -l DEBUG'
    print(f'{s}')
    return

  if not os.path.isdir(options.workspace):
    try:
      os.makedirs(options.workspace)
    except OSError as error:
      print(f"Error creating directory{options.workspace}: {error}")

  library = Library()
    
  test1(library, f'{options.workspace}/{options.outputfile}')
#   sum=0
#   for i in range(1,100000):
#       sum += roll_dice('1d8')
# #      print(f"{roll_dice('1d8')}")
#   print(f"sum={sum} mean = {sum/100000}")

if __name__ == '__main__':
  main()
