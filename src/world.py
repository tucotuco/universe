#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2022 Rauthiflor LLC"
__version__ = "world.py 2023-01-02T15:41-03:00"

from encounter import EncounterHistory
from worldmap import WorldMap

# A World consists of the spatio-temporal context of an EncounterHistory.
class World:
  def __init__(self, worldname, x, y, starttime=0):
    self.worldname = worldname
    self.starttime = starttime
    self.encounters = EncounterHistory()
    self.map = WorldMap(x,y)

  def save(self):
    pass
