#!/usr/bin/env python3
"""First planetary experiment: daylight, Moon, and tidal forcing across a year."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from planetary_system import KeplerOrbit, Moon, Planet, PlanetarySystem, Star


def from_config(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    star = Star(**data['star'])
    planet_config = dict(data['planet'])
    planet_config['orbit'] = KeplerOrbit(**planet_config['orbit'])
    planet = Planet(**planet_config)
    moons = []
    for moon_config in data.get('moons', []):
        moon_config = dict(moon_config)
        moon_config['orbit'] = KeplerOrbit(**moon_config['orbit'])
        moons.append(Moon(**moon_config))
    return PlanetarySystem(star, planet, tuple(moons))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path(__file__).with_name('planetary_analogue.json'))
    parser.add_argument('--latitude', type=float, default=40.0)
    parser.add_argument('--longitude', type=float, default=0.0)
    args = parser.parse_args()
    system = from_config(args.config)
    orbit_s = system.planet.orbit.period_s
    print(f"{system.planet.name} at latitude {args.latitude:.1f}°, longitude {args.longitude:.1f}°")
    print('Day  | Solar declination | Approx. daylight | Sun altitude | Moon lit | Tidal potential')
    print('     | degrees           | hours            | degrees      | fraction | m²/s²')
    for fraction in (0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875):
        t = orbit_s * fraction
        sky = system.state_at(t, args.latitude, args.longitude)
        moon = f'{sky.moons[0].illuminated_fraction:.2f}' if sky.moons else 'n/a'
        print(f'{t/86400:4.0f} | {sky.sun_declination_deg:17.2f} | '
              f'{sky.approximate_daylight_hours:16.2f} | {sky.sun_altitude_deg:12.2f} | '
              f'{moon:8} | {sky.total_tidal_potential_m2_s2:+.3f}')
    print('\nDerived astronomy is objective model output, not automatically an Agent observation.')
    print('Daylight assumes near-constant solar declination during each day; tidal potential is not sea level.')


if __name__ == '__main__':
    main()
