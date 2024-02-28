#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2024 Rauthiflor LLC"
__version__ = "utils.py 2024-01-19T07:14-03:00"

# TODO: Write test for experience_level()

import random
import re


def get_random_key(the_dict):
    """
    Get a random item from a dictionary.
    """
    if not isinstance(the_dict, dict):
        return None
    if len(the_dict) == 0:
        return None
    random_key = random.choice(list(the_dict.keys()))
    random_value = the_dict[random_key]
    return random_key


def roll_dice(dice_string):
    """
    Simulate the roll of dice with modifiers as specified by the input string which
    the format "XdY+Z" or "XdY-Z", where X is the number of dice to roll, Y is the number of
    sides on each die, and Z is an optional modifier to add to/subtract from the total.
    """
    #    match = re.match(r'^(\d+)d(\d+)([+-]\d+)$', dice_string)
    modifier = 0
    num_dice = 1
    match = re.match(r"^(\d+)d(\d+)(([-+]?\d+)?)$", dice_string)
    if not match:
        raise ValueError(f"Invalid dice string: {dice_string}")
    if match.group(1) != "":
        num_dice = int(match.group(1))
    num_sides = int(match.group(2))
    if match.group(3) != "":
        modifier = int(match.group(3))

    # Roll the dice and compute the total
    rolls = [random.randint(1, num_sides) for _ in range(num_dice)]
    total = sum(rolls) + modifier
    return total


def convert_to_numeric(value):
    """
    Interpret an input value as a numeric value, if possible.
    """
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
    """
    Interpret an input value as a boolean value, if possible.
    """
    if value is None:
        return None
    elif isinstance(value, bool):
        return value
    elif str(value)[0].lower() == "t" or str(value).lower() == "true":
        return True
    elif str(value)[0].lower() == "f" or str(value).lower() == "false":
        return False
    return None


def convert_to_ability(value):
    """
    Interpret an input value as a character ability, if possible.
    """
    n = convert_to_numeric(value)
    if isinstance(n, int):
        if n <= 0:
            return 0
        return n
    return 0


def convert_to_speed(value):
    """
    Interpret an input value as a speed, if possible.
    """
    n = convert_to_numeric(value)
    if isinstance(n, int):
        if n <= 0:
            return 0
        return n
    return 0


def convert_to_experience(value):
    """
    Interpret an input value as a value for experience, if possible.
    """
    n = convert_to_numeric(value)
    if isinstance(n, int):
        if n <= 0:
            return 0
        return n
    return 0


def experience_level(experience_points):
    """
    Get experience level from experience points.
    """
    experience_list = [
        1000,
        3000,
        6000,
        10000,
        15000,
        21000,
        28000,
        36000,
        45000,
        55000,
        66000,
        78000,
        91000,
        105000,
        120000,
        136000,
        153000,
        171000,
        190000,
    ]
    for i, value in enumerate(experience_list):
        if value > experience_points:
            break
    return i + 1


def saving_throw_experience_modifier(experience_level):
    experience_list = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10]
    return experience_list[experience_level]


def convert_to_fatigue(value):
    """
    Interpret an input value as a fatigue value, if possible.
    """
    n = convert_to_numeric(value)
    if isinstance(n, int):
        if n <= 0:
            return 0
        elif n > 5:
            return 5
        return n
    return 0


def convert_to_dc(value):
    """
    Interpret an input value as a difficulty class, if possible.
    """
    n = convert_to_numeric(value)
    if isinstance(n, int):
        if n <= 0:
            return 0
        if n > 30:
            return 30
        return n
    return 0
