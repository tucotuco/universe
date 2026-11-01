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


def racial_discovery_bonus(race, action):
    """Revision-60 action aptitude bonus; no unlisted bonus is inferred."""
    if action != 'spot':
        return 0
    return {'Elf': 2, 'Half-elf': 1}.get(race, 0)


def discovery_dc(value):
    """Normalize an explicitly defined Entity DC or the adopted default."""
    if value is None:
        return 15
    if type(value) is not int or value < 0:
        raise ValueError('discovery DC must be a nonnegative integer or None')
    return value
