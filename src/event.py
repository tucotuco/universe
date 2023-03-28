#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "event.py 2023-02-08T19:25-03:00"

# TODO:

from identifiable import Identifiable

class Event(Identifiable):
    def __init__(self, location, starttime, endtime=None, name="", parent=None, id=None):
        Identifiable.__init__(self, name, id)
        self.starttime = starttime
        self.endtime = endtime
        self.location = location
        self.parent = parent

    def __eq__(self, other):
        if isinstance(other, Event):
            if self.location != other.location:
                return False
            if self.starttime != other.starttime:
                return False
            if self.endtime is None or other.endtime is None:
                if self.endtime != other.endtime:
                    return False
            else:
                if self.endtime != other.endtime:
                    return False
            return True
        return False
