#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "actiontimeline.py 2023-03-28T04:02-03:00"

# TODO: Everything
# TODO: Decide if this should be an EventTimeline or a separate thing.
# TODO: Make Action a subtype of Event
# TODO: Make ''' comments on classes and methods

import json
import heapq

from being import BeingInstance

class ActionTimeline:
    def __init__(self):
        self.action_heap = []

    def add_action(self, being_inst, start_time, end_time, action_type):
        action = Action(being_inst, start_time, end_time, action_type)
        if action is not None:
            heapq.heappush(self.action_heap, action)

    def resolve_actions(self, current_time):
        finished_actions = []
        while self.action_heap and self.action_heap[0].start_time <= current_time:
            action = heapq.heappop(self.action_heap)
            finished_actions.append(action)
        return finished_actions

    def clear_actions(self):
        self.action_heap = []

class Action:
    def __init__(self, actor, start_time, end_time, action_type):
        self.start_time = start_time
        self.end_time = end_time
        self.action_type = action_type
        self.actor = self.set_actor(actor)

    # Define a method to compare actions by start time
    def __lt__(self, other):
        return self.start_time < other.start_time

    # Define a method to add an actor to the action
    def set_actor(self, actor):
        if isinstance(actor, BeingInstance):
            self.actor = actor
            return actor
        else:
            raise TypeError('actor must be an instance of the BeingInstance class')
        return None

# Initialize an empty heap to store actions
# action_heap = []
# 
# # Define a function to add an action to the heap
# def add_action(start_time, end_time, action_type):
#     action = Action(start_time, end_time, action_type)
#     heapq.heappush(action_heap, action)
# 
# # Define a function to check for and resolve finished actions
# def resolve_actions(current_time):
#     finished_actions = []
#     while action_heap and action_heap[0].start_time <= current_time:
#         action = heapq.heappop(action_heap)
#         finished_actions.append(action)
#     return finished_actions

# Example usage
# add_action(5, 10, "attack")
# add_action(7, 12, "dodge")
# add_action(15, 20, "block")
# 
# for current_time in range(0, 25):
#     print("Current time:", current_time)
#     finished_actions = resolve_actions(current_time)
#     if finished_actions:
#         print("Finished actions:")
#         for action in finished_actions:
#             print(action.action_type)
