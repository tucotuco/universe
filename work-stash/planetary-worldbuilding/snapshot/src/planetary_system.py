"""Deterministic, time-addressable planetary illumination and tide forcing.

A deliberately bounded first planetary experiment for Universe.  Its clock is
seconds since a declared system epoch and its coordinates are in an inertial
Cartesian frame in SI units.  Keplerian osculating elements are treated as the
*specified physical model*, not as a high-precision N-body approximation.

This module has no RNG and does not commit facts when queried.  It calculates
consequences of already committed orbital/rotational parameters.  Observation,
perception, and later higher-resolution physics remain separate concerns.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Tuple

G = 6.67430e-11  # m^3 kg^-1 s^-2
TAU = 2.0 * math.pi
Vec3 = Tuple[float, float, float]


def _finite(name: str, value: float) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _positive(name: str, value: float) -> float:
    value = _finite(name, value)
    if value <= 0.0:
        raise ValueError(f"{name} must be positive")
    return value


def _add(a: Vec3, b: Vec3) -> Vec3:
    return tuple(x + y for x, y in zip(a, b))  # type: ignore[return-value]


def _sub(a: Vec3, b: Vec3) -> Vec3:
    return tuple(x - y for x, y in zip(a, b))  # type: ignore[return-value]


def _dot(a: Vec3, b: Vec3) -> float:
    return sum(x * y for x, y in zip(a, b))


def _length(v: Vec3) -> float:
    return math.sqrt(_dot(v, v))


def _unit(v: Vec3) -> Vec3:
    size = _length(v)
    if size <= 0:
        raise ValueError("cannot normalize a zero-length vector")
    return tuple(x / size for x in v)  # type: ignore[return-value]


def _clamp(v: float) -> float:
    return max(-1.0, min(1.0, v))


@dataclass(frozen=True)
class KeplerOrbit:
    """Bound elliptic orbit in an inertial x-y reference plane.

    Orbital orientation uses inclination, longitude of ascending node, and
    argument of periapsis in radians.  All times are seconds since epoch 0.
    The period is explicitly configured: the Keplerian gravitational-parameter
    relationship is *not* silently imposed on this first approximate model.
    """

    semi_major_axis_m: float
    period_s: float
    eccentricity: float = 0.0
    mean_anomaly_at_epoch_rad: float = 0.0
    inclination_rad: float = 0.0
    ascending_node_rad: float = 0.0
    periapsis_rad: float = 0.0

    def __post_init__(self) -> None:
        _positive("semi_major_axis_m", self.semi_major_axis_m)
        _positive("period_s", self.period_s)
        e = _finite("eccentricity", self.eccentricity)
        if not 0 <= e < 1:
            raise ValueError("eccentricity must be in [0, 1) for a bound elliptic orbit")
        for key in ("mean_anomaly_at_epoch_rad", "inclination_rad",
                    "ascending_node_rad", "periapsis_rad"):
            _finite(key, getattr(self, key))

    def keplerian_period_s(self, central_mass_kg: float, orbiting_mass_kg: float) -> float:
        """Newtonian two-body period for comparison with configured period."""
        mass = _positive("total gravitating mass", central_mass_kg + orbiting_mass_kg)
        return TAU * math.sqrt(self.semi_major_axis_m**3 / (G * mass))

    def position_at(self, time_s: float) -> Vec3:
        """Position relative to the central body; no state is mutated."""
        t = _finite("time_s", time_s)
        m = (self.mean_anomaly_at_epoch_rad + TAU * (t / self.period_s) + math.pi) % TAU - math.pi
        e = self.eccentricity
        eccentric_anomaly = m if e < 0.8 else math.copysign(math.pi, m)
        for _ in range(100):
            delta = ((eccentric_anomaly - e * math.sin(eccentric_anomaly) - m)
                     / (1.0 - e * math.cos(eccentric_anomaly)))
            eccentric_anomaly -= delta
            if abs(delta) < 1e-13:
                break
        else:
            raise ArithmeticError("Kepler solver failed to converge")

        a = self.semi_major_axis_m
        xp = a * (math.cos(eccentric_anomaly) - e)
        yp = a * math.sqrt(1.0 - e * e) * math.sin(eccentric_anomaly)
        w, node, inc = self.periapsis_rad, self.ascending_node_rad, self.inclination_rad
        cw, sw = math.cos(w), math.sin(w)
        x1, y1 = xp * cw - yp * sw, xp * sw + yp * cw
        ci, si = math.cos(inc), math.sin(inc)
        cn, sn = math.cos(node), math.sin(node)
        return (cn * x1 - sn * ci * y1,
                sn * x1 + cn * ci * y1,
                si * y1)


@dataclass(frozen=True)
class Star:
    name: str
    mass_kg: float
    luminosity_w: float

    def __post_init__(self) -> None:
        _positive("star mass_kg", self.mass_kg)
        _positive("luminosity_w", self.luminosity_w)


@dataclass(frozen=True)
class Planet:
    name: str
    mass_kg: float
    radius_m: float
    orbit: KeplerOrbit
    rotation_period_s: float
    obliquity_rad: float
    rotation_phase_at_epoch_rad: float = math.pi
    axis_azimuth_rad: float = 0.0

    def __post_init__(self) -> None:
        _positive("planet mass_kg", self.mass_kg)
        _positive("planet radius_m", self.radius_m)
        _positive("rotation_period_s", self.rotation_period_s)
        for key in ("obliquity_rad", "rotation_phase_at_epoch_rad", "axis_azimuth_rad"):
            _finite(key, getattr(self, key))
        if not 0 <= self.obliquity_rad <= math.pi:
            raise ValueError("obliquity_rad must be in [0, pi]")
        if not isinstance(self.orbit, KeplerOrbit):
            raise TypeError("planet orbit must be KeplerOrbit")

    def spin_axis(self) -> Vec3:
        tilt, az = self.obliquity_rad, self.axis_azimuth_rad
        return (math.sin(tilt) * math.cos(az),
                math.sin(tilt) * math.sin(az), math.cos(tilt))

    def surface_normal(self, time_s: float, latitude_deg: float, longitude_deg: float) -> Vec3:
        """Geocentric radial direction of a fixed site in inertial coordinates.

        Latitude and longitude are planet-body-fixed, not inertial angles.
        A spherical body is assumed; terrain elevation is deferred.
        """
        t = _finite("time_s", time_s)
        lat = math.radians(_finite("latitude_deg", latitude_deg))
        if not -math.pi / 2 <= lat <= math.pi / 2:
            raise ValueError("latitude_deg must be in [-90, 90]")
        lon = math.radians(_finite("longitude_deg", longitude_deg))
        tilt, az = self.obliquity_rad, self.axis_azimuth_rad
        axis = self.spin_axis()
        equator_x = (math.cos(tilt) * math.cos(az),
                     math.cos(tilt) * math.sin(az), -math.sin(tilt))
        equator_y = (-math.sin(az), math.cos(az), 0.0)
        phase = self.rotation_phase_at_epoch_rad + TAU * (t / self.rotation_period_s) + lon
        clat, slat = math.cos(lat), math.sin(lat)
        return tuple(clat * (math.cos(phase) * equator_x[i] +
                             math.sin(phase) * equator_y[i]) + slat * axis[i]
                     for i in range(3))  # type: ignore[return-value]

    def approximate_solar_day_s(self) -> float:
        """Mean prograde synodic rotation period, not actual sunrise interval."""
        rate = 1.0 / self.rotation_period_s - 1.0 / self.orbit.period_s
        return math.inf if abs(rate) < 1e-18 else 1.0 / abs(rate)


@dataclass(frozen=True)
class Moon:
    name: str
    mass_kg: float
    radius_m: float
    orbit: KeplerOrbit  # Relative to planet, in same inertial frame

    def __post_init__(self) -> None:
        _positive("moon mass_kg", self.mass_kg)
        _positive("moon radius_m", self.radius_m)
        if not isinstance(self.orbit, KeplerOrbit):
            raise TypeError("moon orbit must be KeplerOrbit")
        if self.orbit.semi_major_axis_m * (1 - self.orbit.eccentricity) <= self.radius_m:
            raise ValueError("moon orbit intersects its own center")


@dataclass(frozen=True)
class MoonSky:
    name: str
    distance_from_planet_m: float
    altitude_deg: float
    illuminated_fraction: float
    tidal_potential_m2_s2: float


@dataclass(frozen=True)
class SurfaceSky:
    time_s: float
    latitude_deg: float
    longitude_deg: float
    sun_altitude_deg: float
    sun_declination_deg: float
    stellar_flux_w_m2: float
    surface_insolation_w_m2: float
    approximate_daylight_hours: float
    approximate_solar_day_hours: float
    stellar_tidal_potential_m2_s2: float
    total_tidal_potential_m2_s2: float
    moons: Tuple[MoonSky, ...]


def _tidal_potential(body_mass_kg: float, radius_m: float, separation: Vec3, normal: Vec3) -> float:
    """Quadrupole tide-generating potential at a spherical surface site.

    This is *forcing*, not sea level.  Local ocean tides additionally require
    bathymetry, coastline, fluid dynamics, resonance and other processes.
    """
    distance = _length(separation)
    cosine = _dot(_unit(separation), normal)
    return (G * body_mass_kg * radius_m * radius_m / distance**3
            * (3.0 * cosine * cosine - 1.0) / 2.0)


@dataclass(frozen=True)
class PlanetarySystem:
    star: Star
    planet: Planet
    moons: Tuple[Moon, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.star, Star) or not isinstance(self.planet, Planet):
            raise TypeError("PlanetarySystem requires a Star and a Planet")
        if any(not isinstance(m, Moon) for m in self.moons):
            raise TypeError("moons must contain Moon instances")
        if len({m.name for m in self.moons}) != len(self.moons):
            raise ValueError("moon names must be unique")
        if self.planet.orbit.semi_major_axis_m * (1 - self.planet.orbit.eccentricity) <= self.planet.radius_m:
            raise ValueError("planet orbit intersects the star's origin")
        # A configured period is permitted (e.g. measured mean periods include
        # perturbations), but it must be compatible with the gravitational
        # model to within 2%.  Otherwise a "planetary year" could violate the
        # same Newtonian dynamics used to derive tidal forcing.
        def check_period(label: str, orbit: KeplerOrbit, central_mass: float, satellite_mass: float) -> None:
            theoretical = orbit.keplerian_period_s(central_mass, satellite_mass)
            if abs(orbit.period_s / theoretical - 1.0) > 0.02:
                raise ValueError(f"{label} period is incompatible with its masses and orbital radius")

        check_period(self.planet.name, self.planet.orbit, self.star.mass_kg,
                     self.planet.mass_kg)
        for moon in self.moons:
            if moon.orbit.semi_major_axis_m * (1 - moon.orbit.eccentricity) <= self.planet.radius_m + moon.radius_m:
                raise ValueError(f"moon {moon.name} orbit intersects the planet")
            check_period(moon.name, moon.orbit, self.planet.mass_kg, moon.mass_kg)

    def state_at(self, time_s: float, latitude_deg: float, longitude_deg: float) -> SurfaceSky:
        """Derive local astronomical conditions at arbitrary simulation time.

        Read-only query: no generated content is committed, no random numbers
        are drawn, and no observer automatically acquires this information.
        """
        t = _finite("time_s", time_s)
        site_normal = self.planet.surface_normal(t, latitude_deg, longitude_deg)
        planet_xyz = self.planet.orbit.position_at(t)
        star_vec = tuple(-x for x in planet_xyz)  # star fixed at inertial origin
        star_distance = _length(star_vec)
        sun_unit = _unit(star_vec)
        sun_alt = math.degrees(math.asin(_clamp(_dot(site_normal, sun_unit))))
        declination = math.asin(_clamp(_dot(self.planet.spin_axis(), sun_unit)))
        lat = math.radians(float(latitude_deg))
        a = math.sin(lat) * math.sin(declination)
        b = math.cos(lat) * math.cos(declination)
        if abs(b) < 1e-14:
            daylight_fraction = 1.0 if a > 1e-14 else (0.0 if a < -1e-14 else 0.5)
        else:
            threshold = -a / b
            daylight_fraction = (1.0 if threshold <= -1 else
                                 0.0 if threshold >= 1 else
                                 math.acos(threshold) / math.pi)
        approx_solar_hours = self.planet.approximate_solar_day_s() / 3600.0
        flux = self.star.luminosity_w / (4.0 * math.pi * star_distance**2)
        sun_incidence = max(0.0, _dot(site_normal, sun_unit))
        stellar_tide = _tidal_potential(self.star.mass_kg, self.planet.radius_m,
                                       star_vec, site_normal)
        observer_xyz = _add(planet_xyz, tuple(self.planet.radius_m * n for n in site_normal))
        moon_states = []
        total_tide = stellar_tide
        for moon in self.moons:
            separation = moon.orbit.position_at(t)
            moon_xyz = _add(planet_xyz, separation)
            observer_to_moon = _sub(moon_xyz, observer_xyz)
            moon_to_sun = tuple(-x for x in moon_xyz)
            moon_to_observer = _sub(observer_xyz, moon_xyz)
            cos_phase = _dot(_unit(moon_to_sun), _unit(moon_to_observer))
            illuminated = (1.0 + _clamp(cos_phase)) / 2.0
            altitude = math.degrees(math.asin(_clamp(_dot(site_normal, _unit(observer_to_moon)))))
            moon_tide = _tidal_potential(moon.mass_kg, self.planet.radius_m,
                                         separation, site_normal)
            total_tide += moon_tide
            moon_states.append(MoonSky(moon.name, _length(separation), altitude,
                                       illuminated, moon_tide))
        return SurfaceSky(t, float(latitude_deg), float(longitude_deg), sun_alt,
                          math.degrees(declination), flux, flux * sun_incidence,
                          approx_solar_hours * daylight_fraction, approx_solar_hours,
                          stellar_tide, total_tide, tuple(moon_states))
