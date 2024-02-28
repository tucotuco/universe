#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "John Wieczorek"
__copyright__ = "Copyright 2024 Rauthiflor LLC"
__version__ = "object.py 2024-02-25T11:20-03:00"

# TODO: Make size category function from largest of length, width, height
# TODO: Make ''' comments on classes and methods

import json

from identifiable import Identifiable
from utils import convert_to_numeric

class ObjectDefinition:
    '''
    A template for characteristics of Objects.
    '''
    def __init__(self, obj_type, length, width, height, weight, cost, hardness, 
                 hit_points, is_magical=False, tags=None, weapon_categories=None):
        self.obj_type = obj_type
        self.length = convert_to_numeric(length)
        self.width = convert_to_numeric(width)
        self.height = convert_to_numeric(height)
        self.weight = convert_to_numeric(weight)
        self.cost = convert_to_numeric(cost)
        self.hardness = convert_to_numeric(hardness)
        self.hit_points = convert_to_numeric(hit_points)
        self.is_magical = is_magical
        self.tags = tags or {}
        self.weapon_categories = weapon_categories or []
        if weapon_categories is not None:
            self.weapon_categories = weapon_categories

    def copy(self):
        '''
        Get an independent copy of the ObjectDefinition.
        '''
        new_definition = ObjectDefinition(
            self.obj_type,
            self.length,
            self.width,
            self.height,
            self.weight,
            self.cost,
            self.hardness,
            self.hit_points,
            self.is_magical,
            self.tags.copy(),
            self.weapon_categories)
        return new_definition

    def to_json(self):
        '''
        Get a representation of a ObjectDefinition as JSON.
        '''
        data = {
            'type': self.obj_type,
            'length': self.length,
            'width': self.width,
            'height': self.height,
            'weight': self.weight,
            'cost': self.cost,
            'hardness': self.hardness,
            'hit_points': self.hit_points,
            'is_magical': self.is_magical,
            'tags': self.tags,
            'weapon_categories': self.weapon_categories
        }
        return json.dumps(data)

    def size_category(self):
        # TODO: return size category based on dimensions using the categories:
        # 'diminuitive (D)', 'tiny (T), small (S)', 'medium (M)', 'large (L), 'huge (H)', 'gargantuan (G), colossal (C)'
        return 'M' 

    def tag(self, tag):
        return self.tags.get(tag)

    def set_tag(self, tag, added_tag):
        self.tags[tag] = added_tag

    def set_tags(self, new_tag_dict):
        self.tags = new_tag_dict

    def set_weapon_categories(self, weapon_categories):
        self.weapon_categories = weapon_categories

    def add_weapon_category(self, added_weapon_category):
        if self.weapon_categories is None:
            self.weapon_categories = []
        if added_weapon_category not in self.weapon_categories:
            self.weapon_categories.append(added_weapon_category)

class ObjectInstance(Identifiable):
    ''' 
    An ObjectInstance is an Identifiable that has a Size and occupies space for a period 
    of time. It is not necessarily stationary or permanent. It has normal properties that 
    indicate its original state and current values that are in effect at the time they are 
    accessed. Instances have unique identifiers.
    '''
    def __init__(self, object_definition, name=None, id=None):
        Identifiable.__init__(self, name, id)
        self.top_facing = 0 # up 
        self.front_facing = 1 # whichever horizontal orientation (1-6 on hex) 1 refers to
        self.original = object_definition
        self.current = object_definition.copy() or None
        self.parent_container_id = None

    def to_json(self):
        def handle_circular_refs(obj):
            from library import Library
            from universe import Universe
            if isinstance(obj, (Library, Universe)):
                return obj.id  # Return only the ID for Universe and Event instances
            return obj.__dict__

        data = {
            "type": self.type,
            "name": self.name,
            "id": self.id,
            "top_facing": self.top_facing,
            "front_facing": self.front_facing,
            "original": self.original,
            "current": self.current,
            "parent_container_id": self.parent_container_id
        }
        return json.dumps(data, default=handle_circular_refs, sort_keys=False, indent=2)

    def obj_type(self):
        return self.current.obj_type

    def length(self):
        return self.current.length

    def width(self):
        return self.current.width

    def height(self):
        return self.current.height

    def weight(self):
        return self.current.weight

    def cost(self):
        return self.current.cost

    def hardness(self):
        return self.current.hardness

    def hit_points(self):
        return self.current.hit_points

    def is_magical(self):
        return self.current.is_magical

    def tags(self):
        return self.current.tags

    def tag(self, tag):
        return self.current.tag(tag)

    def weapon_categories(self):
        return self.current.weapon_categories

    def has_weapon_category(self, weapon_category):
        if weapon_category in self.current.weapon_categories:
            return True
        return False

    def set_size(self, new_length, new_width, new_height):
        self.current.length = convert_to_numeric(new_length)
        self.current.width = convert_to_numeric(new_width)
        self.current.height = convert_to_numeric(new_height)

    def lengthen(self, added_length):
        added_length = convert_to_numeric(added_length)
        self.current.length += added_length

    def widen(self, added_width):
        added_width = convert_to_numeric(added_width)
        self.current.width += added_width

    def deepen(self, added_height):
        added_height = convert_to_numeric(added_height)
        self.current.height += added_height

    def resize_percent(self, new_percent):
        percent = convert_to_numeric(new_percent)
        if self.current.length is not None:
            self.current.length = self.current.length*percent/100
        if self.current.width is not None:
            self.current.width = self.current.width*percent/100
        if self.current.height is not None:
            self.current.height = self.current.height*percent/100

    def reweight_percent(self, new_percent):
        percent = convert_to_numeric(new_percent)
        if self.current.weight is not None:
            self.current.weight = self.current.weight*percent/100

    def set_tag(self, tag, tag_value):
        self.current.tags[tag] = tag_value

    def set_tags(self, new_tag_dict):
        self.current.tags = new_tag_dict

    def add_weapon_category(self, weapon_category):
        if self.current.weapon_categories is None:
            self.current.weapon_categories = []
        self.current.weapon_categories.append(weapon_category)

    def get_parent_container_id(self):
        return self.parent_container_id

    def set_parent_container_id(self, object_registry, new_parent_container_id):
        if new_parent_container_id == self.get_id():
            return
        if new_parent_container_id is None:
            self.parent_container_id = 'universe'
            return
        if not isinstance(object_registry, ObjectRegistry):
            return
        if object_registry.get_object_by_id(new_parent_container_id) is not None:
            self.parent_container_id = new_parent_container_id

    def damage(self, damage):
        if damage > self.current.hit_points:
            self.current.hit_points = 0
        else:
            self.current.hit_points -= damage

class ObjectDictionary:
    '''
    A reference for information about ObjectDefinitions.
    '''
    def __init__(self, dictionary_file=None):
        self.object_categories = {}
        self.objects = {}

        if dictionary_file is not None:
            self.load_objects(dictionary_file)

    def to_json(self):
        '''
        Get a representation of an ObjectDictionary as JSON.
        '''
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=2)

    def get_object_definition(self, object_name):
        '''
        Get the ObjectDefinition out of the ObjectDictionary. 
        If not in the dictionary, return None
        '''
        return self.objects.get(object_name)

    def get_objects_in_category(self, object_category):
        '''
        Get a list of objects in a category.
        '''
        return self.object_categories.get(object_category)

    def add_object_categories(self, obj_category_dict):
        '''
        Add object categories from a dict.
        '''
        self.object_categories = obj_category_dict
            
    def load_object_categories(self, file_path):
        '''
        Get object categories from a JSON file.
        '''
        with open(file_path) as f:
            self.object_categories = json.load(f)
            
    def add_objects(self, obj_dict):
        '''
        Add objects from a dict.
        '''
        self.objects = obj_dict
            
    def load_objects(self, filename):
        '''
        Get ObjectDefinitions from a CSV file.
        '''
        p = True
        with open(filename, 'r') as f:
            lines = f.readlines()
            headers = lines[0].strip().split('\t')
            if p==True:
                p = False
            for line in lines[1:]:
                fields = line.strip().split('\t')
                object_dict = {}
                for i in range(len(headers)):
                    object_dict[headers[i]] = fields[i]
                object = ObjectDefinition(**object_dict)
                self.objects[object.obj_type] = object

    def load_from_dict(self, object_dict):
        self.object_categories = object_dict.get('object_categories')
        self.objects = object_dict.get('objects')

class ObjectRegistry:
    '''
    A dictionary of all ObjectInstances with their ids as keys.
    '''
    def __init__(self):
        self.object_instances = {}

    def add_object(self, obj):
        if isinstance(obj, ObjectInstance):
            if self.object_instances.get(obj.id) is None:
                if obj.name is None:
                    object_type_str = type(instance).__name__
                    obj.set_name(f"{object_type_str}{len(self.object_instances)}")
#                print(f"object.py: Adding ObjectInstance with name={obj.name} and object_id={obj.id} to ObjectRegistry")
                self.object_instances[obj.id] = obj

    def get_object_by_id(self, obj_id):
        return self.object_instances.get(obj_id)

    def get_object_contents(self, container_object_id):
        contents = []
        for object_id, object in self.object_instances:
            if object.parent_object_id == container_object_id:
                contents.append(object_id)

    def load_from_dict(self, object_dict):
        self.object_instances = object_dict.get('object_instances')

    def len(self):
        return len(self.object_instances)
        
    def __iter__(self):
        return iter(self.object_instances.items())