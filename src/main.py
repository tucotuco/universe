#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "John Wieczorek"
__copyright__ = "Copyright 2024 Rauthiflor LLC"
__version__ = "main.py 2024-02-17T23:15-03:00"

# TODO: Figure out what this will do and implement it. Requires complete refactor.
# TODO: Make a clear method for populating Universe and Encounter with Beings and their possessions.

import argparse
import csv
import cProfile
import pstats
import os

from identifiable import Identifiable
from itertools import combinations
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

def test2(library, universe_output_file):
  # Make the universe
  the_arena = Universe(name="The Arena", library=library)

  # Make equal contestants
  tobe_id = the_arena.make_being("Human", "Tobe")
  nottobe_id = the_arena.make_being("Human", "NotTobe")
  tobe = the_arena.get_object_by_id(tobe_id)
  nottobe = the_arena.get_object_by_id(nottobe_id)
  
  # Set up to capture results
  results = {}

  # Set up distinct combinations of weapons
#  weapon_combinations = combinations(the_arena.get_weapon_dictionary().objects, 2)

  weapon_a_name = 'Dagger'
  weapon_b_name = 'Longsword'
  if weapon_a_name == "Lasso" or weapon_a_name == "Net":
    print("{weapon_a_name} supports only the Entangle penetration type")
    exit()
  if weapon_b_name == "Lasso" or weapon_b_name == "Net":
    print("{weapon_b_name} supports only the Entangle penetration type")
    exit()

  # Make the first weapon
  tobe_weapon_id = the_arena.make_weapon(weapon_a_name, f"{weapon_a_name}")
  tobe_weapon = the_arena.get_object_by_id(tobe_weapon_id)

  # Arm the first contestant
  the_arena.arm_being(tobe_id, tobe_weapon.id, "right hand")

  # Continue if the first weapon does not support melee actions
  if tobe.melee_action_supported(the_arena) == False:
    print(f"{weapon_a_name} does not support melee actions")
    exit()

  # Make the second weapon
  nottobe_weapon_id = the_arena.make_weapon(weapon_b_name, f"{weapon_b_name}")
  nottobe_weapon = the_arena.get_object_by_id(nottobe_weapon_id)
      
  # Arm the second contestant
  the_arena.arm_being(nottobe_id, nottobe_weapon.id, "right hand")

  # Break if the second weapon does not support melee actions
  if nottobe.melee_action_supported(the_arena) == False:
    print(f"{weapon_b_name} does not support melee actions")
    exit()

  matchup = f"{tobe_weapon.name} vs. {nottobe_weapon.name}"
  print(f'{matchup}')
  results[matchup] = { "wins":0, "losses":0, "draws":0, "hp given":0, "hp taken":0, "turns":0}

  i = 0
  for trial in range(1000):
    # Make an Encounter to play in
    encounter = Encounter(the_arena, difficulty_class=15, start_time=0, end_time=None, 
    event_type="Encounter", location=None, 
    name=f"The Big Matchup {i}-{trial+1} {matchup}")

    # Add the contestants to the match
    encounter.add_being(tobe_id)
    encounter.add_being(nottobe_id)

    # Add the match to the arena
    the_arena.add_event(encounter)

    # Run the match
    encounter.run()

    # Log the outcome
    hp_given = nottobe.original.hit_points - nottobe.hit_points()
    hp_taken = tobe.original.hit_points - tobe.hit_points()
    turns = encounter.time
    results[matchup]["hp given"] += hp_given
    results[matchup]["hp taken"] += hp_taken
    results[matchup]["turns"] += turns

    if hp_given > hp_taken:
      results[matchup]["wins"] +=1
    elif hp_given < hp_taken:
      results[matchup]["losses"] +=1
    else:
      results[matchup]["draws"] +=1

    tobe.set_hit_points(tobe.original.hit_points)
    nottobe.set_hit_points(nottobe.original.hit_points)
    tobe_weapon.hit_points = tobe_weapon.original.hit_points
    nottobe_weapon.hit_points = nottobe_weapon.original.hit_points

  print(f"Results:\n {results}")
#   for combination in weapon_combinations:
#     i+=1
#     weapon_a_name, weapon_b_name = combination
#     if weapon_a_name == "Lasso" or weapon_a_name == "Net" or weapon_b_name == "Lasso" or weapon_b_name == "Net" or i > 140:
#       continue
#   
#     # Make the first weapon
#     tobe_weapon_id = the_arena.make_weapon(weapon_a_name, f"{weapon_a_name}")
#     tobe_weapon = the_arena.get_object_by_id(tobe_weapon_id)
# 
#     # Arm the first contestant
#     the_arena.arm_being(tobe_id, tobe_weapon.id, "right hand")
# 
#     # Continue if the first weapon does not support melee actions
#     if tobe.melee_action_supported(the_arena) == False:
# #      print(f"{weapon_a_name} does not support melee actions")
#       continue
# 
#     # Make the second weapon
#     nottobe_weapon_id = the_arena.make_weapon(weapon_b_name, f"{weapon_b_name}")
#     nottobe_weapon = the_arena.get_object_by_id(nottobe_weapon_id)
#       
#     # Arm the second contestant
#     the_arena.arm_being(nottobe_id, nottobe_weapon.id, "right hand")
# 
#     # Break if the second weapon does not support melee actions
#     if nottobe.melee_action_supported(the_arena) == False:
# #      print(f"{weapon_b_name} does not support melee actions")
#       continue
# 
#     matchup = f"{tobe_weapon.name} vs. {nottobe_weapon.name}"
#     print(f'{i} {matchup}')
# 
#     results[matchup] = { "wins":0, "losses":0, "draws":0, "hp given":0, "hp taken":0, "turns":0}
# 
#     for trial in range(10):
#       # Make an Encounter to play in
#       encounter = Encounter(the_arena, difficulty_class=15, start_time=0, end_time=None, 
#         event_type="Encounter", location=None, 
#         name=f"The Big Matchup {i}-{trial+1} {matchup}", 
#         parent_event=None, id=None, initiated=False, map=None)
# 
#       # Add the contestants to the match
#       encounter.add_being(tobe_id)
#       encounter.add_being(nottobe_id)
# 
#       # Add the match to the arena
#       the_arena.add_event(encounter)
# 
#       # Run the match
#       encounter.run()
# 
#       # Log the outcome
#       hp_given = nottobe.original.hit_points - nottobe.hit_points()
#       hp_taken = tobe.original.hit_points - tobe.hit_points()
#       turns = encounter.time
#       results[matchup]["hp given"] += hp_given
#       results[matchup]["hp taken"] += hp_taken
#       results[matchup]["turns"] += turns
# 
#       if hp_given > hp_taken:
#         results[matchup]["wins"] +=1
#       elif hp_given < hp_taken:
#         results[matchup]["losses"] +=1
#       else:
#         results[matchup]["draws"] +=1
# 
#       tobe.set_hit_points(tobe.original.hit_points)
#       nottobe.set_hit_points(nottobe.original.hit_points)
#       tobe_weapon.hit_points = tobe_weapon.original.hit_points
#       nottobe_weapon.hit_points = nottobe_weapon.original.hit_points
# 
#   # Open a CSV file for writing
#   with open('../workspace/weapon_results.csv', 'w', newline='') as csvfile:
#     # Define the header row
#     fieldnames = ['Matchup'] + list(next(iter(results.values())).keys())  # Extract the keys from the first inner dictionary
# 
#     # Create a CSV writer object
#     writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
# 
#     # Write the header row
#     writer.writeheader()
# 
#     # Iterate over the entries in dictionary D
#     for entry, inner_dict in results.items():
#         # Write a row for each entry, with the entry name as the first column
#         row = {'Matchup': entry}
#         row.update(inner_dict)  # Update the row with the values from the inner dictionary
#         writer.writerow(row)

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
    s += ' -w ../workspace'
    s += ' -i universe.json'
    s += ' -o universe.json'
    s += ' -l DEBUG'
    print(f'{s}')
    return

  if not os.path.isdir(options.workspace):
    try:
      os.makedirs(options.workspace)
    except OSError as error:
      print(f"Error creating directory {options.workspace}: {error}")

  library = Library()
    
#  test1(library, f'{options.workspace}/{options.outputfile}')
  test2(library, f'{options.workspace}/{options.outputfile}')


if __name__ == '__main__':
  main()

# if __name__ == "__main__":
#     # Run the profiler on your script
#     profiler = cProfile.Profile()
#     profiler.enable()
#     main()
#     profiler.disable()
# 
#     # Create a Stats object from the profiler's output
#     stats = pstats.Stats(profiler)
# 
#     # Sort the stats by the time spent in each function
#     stats.sort_stats("time")
# 
#     # Print the statistics
#     stats.print_stats()
