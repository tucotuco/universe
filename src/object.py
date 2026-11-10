#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "John Wieczorek"
__copyright__ = "Copyright 2024 Rauthiflor LLC"
__version__ = "object.py 2024-03-15T22:50-03:00"

# TODO: Make size category function from largest of length, width, height
# TODO: Make ''' comments on classes and methods

import json

from identifiable import Identifiable
from spatial.state import CartesianPosition, SpatialState
from spatial.geometry import Geometry3D
from spatial.occlusion import VisualOcclusion
from utils import convert_to_numeric

class ObjectDefinition:
    '''
    A template for characteristics of Objects.
    '''
    _MEASURED_ATTRIBUTES = frozenset(("length", "width", "height", "weight"))

    def __setattr__(self, name, value):
        if name in self._MEASURED_ATTRIBUTES and value is not None:
            from measured_values import truncate_measurement
            value = truncate_measurement(value)
        object.__setattr__(self, name, value)

    def __init__(self, obj_type, length, width, height, weight, cost, hardness, 
                 hit_points, is_magical=False, tags=None, weapon_categories=None,
                 discovery_dc=None):
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
        if discovery_dc is not None and (type(discovery_dc) is not int or discovery_dc < 0):
            raise ValueError("discovery_dc must be a nonnegative integer or None")
        self.discovery_dc = discovery_dc

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
            self.weapon_categories,
            self.discovery_dc)
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
            'weapon_categories': self.weapon_categories,
            'discovery_dc': self.discovery_dc
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
    def __init__(self, object_definition, name=None, id=None, spatial_state=None,
                 geometry=None, visual_occlusion=None):
        Identifiable.__init__(self, name, id)
        self.top_facing = 0 # up 
        self.front_facing = 1 # whichever horizontal orientation (1-6 on hex) 1 refers to
        self.original = object_definition
        self.current = object_definition.copy() or None
        self.parent_container_id = None
        self.spatial_state = None
        self.geometry = None
        self.visual_occlusion = None  # unknown; not automatically transparent or opaque
        if spatial_state is not None:
            self.set_spatial_state(spatial_state)
        if geometry is not None:
            self.set_geometry(geometry)
        if visual_occlusion is not None:
            self.set_visual_occlusion(visual_occlusion)

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
            "parent_container_id": self.parent_container_id,
            "spatial_state": self.spatial_state,
            "geometry": self.geometry.to_dict() if self.geometry is not None else None,
            "visual_occlusion": (self.visual_occlusion.to_dict()
                                 if self.visual_occlusion is not None else None)
        }
        return json.dumps(data, default=handle_circular_refs, sort_keys=False, indent=2)

    def set_geometry(self, geometry):
        """Assign physical extent; None means geometry has not been modeled.

        Definition dimensions are physical quantities in their subtype's
        native units. They are deliberately not interpreted as world-space
        dimensions or collision geometry; geometry must be authored separately.
        """
        if geometry is not None and not isinstance(geometry, Geometry3D):
            raise TypeError("geometry must be a Geometry3D or None")
        self.geometry = geometry

    def set_visual_occlusion(self, visual_occlusion):
        """Set a physical Entity's nominal visual opacity independently of shape."""
        if visual_occlusion is not None and not isinstance(visual_occlusion, VisualOcclusion):
            raise TypeError("visual_occlusion must be a VisualOcclusion or None")
        self.visual_occlusion = visual_occlusion

    def spatial_bounds(self):
        """Return global bounds, or None until both shape and position exist."""
        if self.geometry is None or self.get_position() is None:
            return None
        return self.geometry.bounds(self.get_position())

    def occupies_point(self, position):
        """Test physical occupancy in continuous global 3D coordinates."""
        if not isinstance(position, CartesianPosition):
            raise TypeError("position must be a CartesianPosition")
        if self.geometry is None or self.get_position() is None:
            return False
        return self.geometry.contains(position, self.get_position())

    def segment_intersection(self, start, end):
        """Geometric intersection interval; does NOT imply visual obstruction.

        Returns None when no geometry or position is assigned. A later
        visibility evaluator may use this together with ``visual_occlusion``.
        """
        if not isinstance(start, CartesianPosition) or not isinstance(end, CartesianPosition):
            raise TypeError("segment endpoints must be CartesianPosition values")
        if self.geometry is None or self.get_position() is None:
            return None
        return self.geometry.segment_interval(start, end, self.get_position())

    def get_spatial_state(self):
        return self.spatial_state

    def set_spatial_state(self, spatial_state):
        if spatial_state is not None and not isinstance(spatial_state, SpatialState):
            raise TypeError("spatial_state must be a SpatialState or None")
        self.spatial_state = spatial_state

    def get_position(self):
        if self.spatial_state is None:
            return None
        return self.spatial_state.position

    def set_position(self, position):
        if not isinstance(position, CartesianPosition):
            raise TypeError("position must be a CartesianPosition")
        if self.spatial_state is None:
            self.spatial_state = SpatialState(position)
        else:
            self.spatial_state.set_position(position)

    def spatial_cell(self, grid, level, origin=None):
        if self.spatial_state is None:
            return None
        return self.spatial_state.cell(grid, level, origin)

    def spatial_relation_to(self, other):
        """Return the current continuous spatial relation to another object.

        ``None`` is returned while either object has not yet been placed.
        The relation is derived from current positions and is not stored.
        """
        if not isinstance(other, ObjectInstance):
            raise TypeError("other must be an ObjectInstance")
        if self.spatial_state is None or other.spatial_state is None:
            return None
        from spatial.relation import SpatialRelation
        return SpatialRelation(self.get_position(), other.get_position())

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
            self.load(dictionary_file)

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
            
    def load(self, filename):
        '''
        Get predefined ObjectDefinitions from a CSV file.
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
