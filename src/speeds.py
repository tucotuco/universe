#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "speed.py 2023-12-21T16:04:08-03:00"

# TODO: Incorporate methods for actual speed.
# TODO: Make ''' comments on classes and methods

from utils import convert_to_numeric, convert_to_speed
       
class Speed():
    def __init__(self, ambulate=0, burrow=0, climb=0, fly=0, swim=0):
        self.speeds = {}
        self.speeds['ambulate'] = convert_to_speed(ambulate)
        self.speeds['burrow'] = convert_to_speed(burrow)
        self.speeds['climb'] = convert_to_speed(climb)
        self.speeds['fly'] = convert_to_speed(fly)
        self.speeds['swim'] = convert_to_speed(swim)

    def copy(self):
        '''
        Get an independent copy of the Speed instance.
        '''
        return Speed(self.sprint(), self.burrow(), self.climb(), self.fly(), self.swim())

#     def to_json(self):
#         '''
#         Get a representation of a Speed as JSON.
#         '''
#         data = {
#             'ambulate': self.speeds['ambulate'],
#             'burrow': self.speeds['burrow'],
#             'climb': self.speeds['climb'],
#             'fly': self.speeds['fly'],
#             'swim': self.speeds['swim']
#         }
#         return json.dumps(data)

    def sprint(self):
        return self.speeds.get('ambulate')

    def burrow(self):
        return self.speeds.get('burrow')

    def climb(self):
        return self.speeds.get('climb')

    def fly(self):
        return self.speeds.get('fly')

    def swim(self):
        return self.speeds.get('swim')

    def set_max_speed(self, speed_type, new_value):
        if convert_to_numeric(new_value) is None:
            return
        v = convert_to_speed(new_value)
        if v >= 0 and speed_type in ['ambulate', 'burrow', 'climb', 'fly', 'swim']:
            self.speeds[speed_type] = v
