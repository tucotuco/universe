#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "utils.py 2023-03-17T08:31-03:00"

# TODO:

def convert_to_numeric(value):
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
    n = convert_to_numeric(value)
    if isinstance(n, int):
        if n <= 0:
            return 0
        return n
    return 0
    
def convert_to_speed(value):
    n = convert_to_numeric(value)
    if isinstance(n, int):
        if n <= 0:
            return 0
        return n
    return 0
    
def convert_to_experience(value):
    n = convert_to_numeric(value)
    if isinstance(n, int):
        if n <= 0:
            return 0
        return n
    return 0

def convert_to_fatigue(value):
    n = convert_to_numeric(value)
    if isinstance(n, int):
        if n <= 0:
            return 0
        elif n > 5:
            return 5
        return n
    return 0