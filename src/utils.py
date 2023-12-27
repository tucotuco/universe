#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "utils.py 2023-04-23T22:58+02:00"

# TODO: 

import random
import re

def get_random_key(the_dict):
    '''
    Get a random item from a dictionary.
    '''
    if not isinstance(the_dict, dict):
        return None
    if len(the_dict) == 0:
        return None
    random_key = random.choice(list(the_dict.keys()))
    random_value = the_dict[random_key]
    return random_key

def roll_dice(dice_string):
    '''
    Simulate the roll of dice with modifiers as specified by the input string which 
    the format "XdY+Z" or "XdY-Z", where X is the number of dice to roll, Y is the number of 
    sides on each die, and Z is an optional modifier to add to/subtract from the total.
    '''
    match = re.match(r'^(\d+)d(\d+)([+-]\d+)$', dice_string)
    if not match:
        raise ValueError(f'Invalid dice string: {dice_string}')
    num_dice = int(match.group(1))
    num_sides = int(match.group(2))
    modifier = int(match.group(3))
    
    # Roll the dice and compute the total
    rolls = [random.randint(1, num_sides) for _ in range(num_dice)]
    total = sum(rolls) + modifier
    return total

def convert_to_numeric(value):
    '''
    Interpret an input value as a numeric value, if possible.
    '''
    if value is None:
        return None
    elif len(str(value)) == 0:
        return None
    elif convert_to_boolean(value) == True:
        return 1
    elif convert_to_boolean(value) == False:
        return 0
    elif isinstance(value, int) or isinstance(value, float):
        return value
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return None

def convert_to_boolean(value):
    '''
    Interpret an input value as a boolean value, if possible.
    '''
    if value is None:
        return None
    elif isinstance(value, bool):
        return value
    elif str(value)[0].lower() == 't' or str(value).lower() == 'true':
        return True
    elif str(value)[0].lower() == 'f' or str(value).lower() == 'false':
        return False
    return None

def convert_to_ability(value):
    '''
    Interpret an input value as a character ability, if possible.
    '''
    n = convert_to_numeric(value)
    if isinstance(n, int):
        if n <= 0:
            return 0
        return n
    return 0

def convert_to_speed(value):
    '''
    Interpret an input value as a speed, if possible.
    '''
    n = convert_to_numeric(value)
    if isinstance(n, int):
        if n <= 0:
            return 0
        return n
    return 0
    
def convert_to_experience(value):
    '''
    Interpret an input value as a value for experience, if possible.
    '''
    n = convert_to_numeric(value)
    if isinstance(n, int):
        if n <= 0:
            return 0
        return n
    return 0

def convert_to_fatigue(value):
    '''
    Interpret an input value as a fatigue value, if possible.
    '''
    n = convert_to_numeric(value)
    if isinstance(n, int):
        if n <= 0:
            return 0
        elif n > 5:
            return 5
        return n
    return 0
    
def convert_to_dc(value):
    '''
    Interpret an input value as a difficulty class, if possible.
    '''
    n = convert_to_numeric(value)
    if isinstance(n, int):
        if n <= 0:
            return 0
        if n > 30:
            return 30
        return n
    return 0
