#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2024 Rauthiflor LLC"
__version__ = "exertion.py 2024-03-28T20:53-3:00"

# TODO: 

import json

from utils import ability_check, convert_to_numeric, convert_to_fatigue

class Exertion():
    """
    An exertion and fatigue tracker.
    """

    def __init__(self, 
        start_time=0,
        end_time=None,
        activity_level="inactive", 
        fatigue_level=0,
        load_level = "light",
        accumulated_exertion=0):
        
        self.check_periods = {
          "inactive":{"light":3600, "medium":1800, "heavy":900 }, 
          "normal":{"light":600, "medium":300, "heavy":150 }, 
          "walk":{"light":600, "medium":300, "heavy":150 }, 
          "above normal":{"light":300, "medium":150, "heavy":45 }, 
          "husstle":{"light":300, "medium":150, "heavy":45 }, 
          "jog":{"light":60, "medium":30, "heavy":15 }, 
          "swim":{"light":30, "medium":15, "heavy":1 }, 
          "run":{"light":30, "medium":15, "heavy":1 }, 
          "combat":{"light":6, "medium":3, "heavy":1 }, 
          "sprint":{"light":1, "medium":1, "heavy":1 }
          }
        
        self.fatigue_levels = {
          0:{ "state":"fresh", "ability_adjustment":0, "maximum_movement_rate":"sprint"},
          1:{ "state":"winded", "ability_adjustment":0, "maximum_movement_rate":"run"},
          2:{ "state":"tired", "ability_adjustment":-1, "maximum_movement_rate":"jog"},
          3:{ "state":"weary", "ability_adjustment":-2, "maximum_movement_rate":"hustle"},
          4:{ "state":"exhausted", "ability_adjustment":-3, "maximum_movement_rate":"walk"},
          5:{ "state":"incapacitated", "ability_adjustment":None, "maximum_movement_rate":None}
          }

        self.start_time = None
        self.end_time = None
        self.activity_level = None
        self.fatigue_level = None
        self.load_level = None
        
        self.set_start_time(start_time)
        self.set_activity_level(activity_level)
        self.set_fatigue_level(fatigue_level)
        self.set_load_level(load_level)
        if end_time is not None: 
            self.set_end_time(end_time)
        else:
            self.set_end_time(self.calculate_end_time())
        self.accumulated_exertion = convert_to_numeric(accumulated_exertion)
        if self.accumulated_exertion < 0:
            self.accumulated_exertion = 0

    def to_json(self):
        """
        Serialize the Exertion as JSON.
        """
        data = {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "activity_level": self.activity_level,
            "fatigue_level": self.fatigue_level,
            "load_level": self.load_level,
            "accumulated_exertion": self.accumulated_exertion
        }
        return json.dumps(data, indent = 2)

    def set_start_time(self, start_time):
        """
        Set the start time.
        """
        self.start_time = convert_to_numeric(start_time)

    def set_end_time(self, end_time):
        """
        Set the end time.
        """
        self.end_time = convert_to_numeric(end_time)
        if self.end_time <= self.start_time:
            self.end_time = self.start_time

    def set_activity_level(self, activity_level):
        """
        Set the current activity level.
        """
        activity_periods = self.check_periods.get(activity_level)
        if activity_periods is None:
            return
        self.activity_level = activity_level
        
    def set_fatigue_level(self, fatigue_level):
        """
        Set the current activity level.
        """
        self.fatigue_level = convert_to_fatigue(fatigue_level)

    def set_load_level(self, load_level):
        """
        Set the current load level.
        """
        activity_periods = self.check_periods.get(self.activity_level)
        if activity_periods is None:
            return
        period = activity_periods.get(load_level)
        if period is None:
            return
        self.load_level = load_level

    def set_accumulated_exertion(self, accumulated_exertion):
        """
        Set the current load level.
        """
        self.accumulated_exertion = convert_to_numeric(accumulated_exertion)
        if self.accumulated_exertion < 0:
            self.accumulated_exertion = 0            

    def add_exertion(self, added_exertion):
        """
        Add exertion to the accumulated exertion.
        """
        self.set_accumulated_exertion(self.accumulated_exertion + \
            convert_to_numeric(added_exertion))

    def get_start_time(self):
        """
        Get the start time.
        """
        return self.start_time

    def get_end_time(self):
        """
        Get the end time.
        """
        return self.end_time

    def get_activity_level(self):
        """
        Get the current activity level.
        """
        return self.activity_level
        
    def get_fatigue_level(self):
        """
        Get the current fatigue level.
        """
        return self.fatigue_level

    def get_load_level(self):
        """
        Get the current load level.
        """
        return self.load_level

    def get_accumulated_exertion(self):
        """
        Get the current load level.
        """
        return self.accumulated_exertion

    def get_check_period(self):
        """
        Get the the check period, in seconds, based on the activity and load levels.
        """
        activity_periods = self.check_periods.get(self.activity_level)
        if activity_periods is None:
            return 0
        period = activity_periods.get(self.load_level)
        if period is None:
            return 0
        return period

    def calculate_end_time(self):
        """
        Determine when the next Exertion check will happen.
        """
        return self.start_time + self.get_check_period()

    def check(self, ability_value):
        """
        Determine if an Exertion check succeeds.
        """
        return ability_check(ability_value)
