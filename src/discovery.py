"""Closed, data-only inputs for adopted discovery Action modifiers."""

from dataclasses import dataclass


# Revision-60 Spotting Modifiers Table.  Inputs name a documented circumstance;
# arbitrary numeric modifiers are deliberately not accepted.
SPOTTING_DC_ADJUSTMENTS = {
    'high_contrast': -5, 'camouflage': 5, 'target_moving': -5,
    'spotter_moving': 5, 'concealment_25': 1, 'concealment_50': 2,
    'concealment_75': 3, 'concealment_90': 4, 'starlight': 4,
    'full_moonlight': 3, 'into_sun': 3, 'into_shadows': 2,
    'to_light_source': -10, 'size_diminutive': 3, 'size_tiny': 2,
    'size_small': 1, 'size_medium': 0, 'size_large': -1,
    'size_huge': -2, 'size_gargantuan': -3, 'size_colossal': -4,
    'clear_water': 0, 'cloudy_water': 5, 'light_fog': 1,
    'heavy_fog': 3, 'light_rain': 1, 'heavy_rain': 2,
    'light_snow': 1, 'heavy_snow': 3, 'light_forest': 1,
    'dense_forest': 3,
}

# Adopted Hearing Modifiers Table. Silence and deafness make the check
# impossible rather than assigning a numeric adjustment.
HEARING_DC_ADJUSTMENTS = {
    'sleeping': 5, 'burbling_brook': 1, 'light_rain': 1,
    'heavy_rain': 2, 'outside_enclosure': 3, 'into_enclosure': 3,
    'through_door': 1, 'through_wall': 2, 'through_thick_wall': 3,
    'through_conversation': 2, 'through_yelling_or_singing': 5,
    'light_breeze': 1, 'moderate_wind': 2, 'strong_wind': 3,
    'gale': 4, 'storm': 5, 'hurricane': 6,
}

@dataclass(frozen=True)
class SpottingConditions:
    """Named scenario circumstances supplied with one deliberate Spot choice."""
    values: tuple = ()

    def __post_init__(self):
        if type(self.values) is not tuple:
            raise ValueError('SpottingConditions.values must be a tuple')
        if any(type(value) is not str or value not in SPOTTING_DC_ADJUSTMENTS
               for value in self.values):
            raise ValueError('unknown adopted Spotting table condition')
        if len(set(self.values)) != len(self.values):
            raise ValueError('duplicate Spotting table condition')

    @property
    def dc_adjustment(self):
        return sum(SPOTTING_DC_ADJUSTMENTS[value] for value in self.values)


@dataclass(frozen=True)
class HearingConditions:
    """Authored Hearing-table circumstances; no sound physics is inferred."""
    values: tuple = ()

    def __post_init__(self):
        if type(self.values) is not tuple:
            raise ValueError('HearingConditions.values must be a tuple')
        allowed = frozenset(HEARING_DC_ADJUSTMENTS) | {'area_of_silence', 'deaf'}
        if any(type(value) is not str or value not in allowed for value in self.values):
            raise ValueError('unknown adopted Hearing table condition')
        if len(set(self.values)) != len(self.values):
            raise ValueError('duplicate Hearing table condition')

    @property
    def impossible(self):
        return any(value in ('area_of_silence', 'deaf') for value in self.values)

    @property
    def dc_adjustment(self):
        return sum(HEARING_DC_ADJUSTMENTS[value] for value in self.values
                   if value in HEARING_DC_ADJUSTMENTS)


def racial_discovery_bonus(race, action):
    """Adopted Search/Spot/Listen aptitude as a d20 result bonus.

    This is intentionally separate from trainable-skill XP modifiers. Unknown
    races and Action names receive no inferred aptitude.
    """
    if action not in ('search', 'spot', 'listen'):
        return 0
    bonuses = {
        'search': {'Elf': 2, 'Half-elf': 1},
        'spot': {'Elf': 2, 'Half-elf': 1},
        'listen': {'Elf': 2, 'Half-elf': 1, 'Gnome': 2, 'Halfling': 2},
    }
    return bonuses[action].get(race, 0)


def discovery_dc(value):
    """Normalize an explicitly defined Entity DC or the adopted default."""
    if value is None:
        return 15
    if type(value) is not int or value < 0:
        raise ValueError('discovery DC must be a nonnegative integer or None')
    return value
