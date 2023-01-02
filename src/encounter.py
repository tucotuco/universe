#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2022 Rauthiflor LLC"
__version__ = "encounter.py 2023-01-02T15:45-03:00"

# An Encounter is a container for the activity that occurs in a location over a period
# of time. Each Encounter has a start time in seconds from a base epoch that anchors it 
# in a broder historical context.
class Encounter:
  def __init__(self, starttime, x, y):
    self.initiated = False
    self.starttime = starttime
    self.map = None

  # Generate an Encounter.
  def generate(self):
    self.map = EncounterMap(x,y)
    self.initiated == True

  # Load an Encounter from storage.
  def load(self):
    self.initiated = True
    pass

  # Cycle through the events in an encounter.
  # 1. make movement decisions: set movement targets, whether stationary or moving, relative or absolute.
  # 2. update acceleration, velocity, location, position, facings, engagement, etc. (include moving targets and accelerating targets)
  # 3. resolve non-movement actions and their effects
  # 4. update environment
  # 5. make action decisions (continue, change) based on currently knowable state
  # 6. map actions on timeline
  # 7. update current new round
  # 8. save state
  # 9. prompt to continue playing: if continue, go to 1 else exit
  def run(self):
    if self.initiated == False:
      self.generate()
  
    keep_going = True
    while keep_going:
      self.make_movement_decisions()
      self.move()
      self.resolve_actions()
      self.update_environment()
      self.make_action_decisions()
      self.update_timeline()
      self.save()
      
  def make_movement_decisions(self):
    pass

  def move(self):
    pass

  def resolve_actions(self):
    pass
    
  def update_environment(self):
    pass

  def make_action_decisions(self):
    pass

  def update_timeline(self):
    pass

  def save(self):
    pass

# An EncounterHistory is a container for Encounters.
class EncounterHistory:
  def __init__(self):
    self.encounters = []

  def add_encounter(self, encounter):
    self.encounters.append(encounter)
