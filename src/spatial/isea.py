#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Hierarchical Icosahedral Snyder Equal Area cells on a sphere.

This module implements the small spatial kernel Universe currently needs:

* twenty triangular faces of a regular icosahedron;
* Snyder's equal-area mapping between each spherical face and a planar
  equilateral triangle;
* recursive aperture-4 subdivision of the planar triangle;
* compact hierarchical addresses (A..T followed by child digits 0..3).

Because the subdivision is performed in the equal-area face plane, all cells
at a given level have equal spherical area.  The grid is an indexing overlay;
continuous physical coordinates remain authoritative for physics.

The Snyder mapping follows the construction in:
    Snyder, J. P. 1992. An Equal-Area Map Projection for Polyhedral Globes.
    Cartographica 29(1):10-21.

The implementation was cross-checked against the generic polyhedral Snyder
formulation introduced in PROJ 9.9.  Universe keeps the implementation local
so the spatial kernel is not coupled to a cartographic runtime dependency.
"""

from __future__ import annotations

import math
from typing import Tuple, Union

from spatial.cell import CellAddress
from spatial.grid import Coordinate, SpatialGrid


_EPSILON = 1e-12
_SQRT3 = math.sqrt(3.0)

Vec3 = Tuple[float, float, float]
Point2D = Tuple[float, float]
Triangle2D = Tuple[Point2D, Point2D, Point2D]
Triangle3D = Tuple[Vec3, Vec3, Vec3]

# An arbitrary equilateral face in the equal-area plane.  Only barycentric
# position matters; absolute translation, rotation and scale do not.
_PLANAR_ROOT: Triangle2D = (
    (0.0, _SQRT3 / 2.0),
    (-0.5, 0.0),
    (0.5, 0.0),
)


def _add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _subtract(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale(a: Vec3, scalar: float) -> Vec3:
    return (a[0] * scalar, a[1] * scalar, a[2] * scalar)


def _dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _length(a: Vec3) -> float:
    return math.sqrt(_dot(a, a))


def _normalize(a: Vec3) -> Vec3:
    length = _length(a)
    if length == 0.0:
        raise ValueError("cannot normalize a zero-length vector")
    return _scale(a, 1.0 / length)


def _triple_product(a: Vec3, b: Vec3, c: Vec3) -> float:
    return _dot(a, _cross(b, c))


def _vector_difference(a: Vec3, b: Vec3) -> float:
    """Stable quantity proportional to sin(angle/2) for unit vectors."""
    difference = _length(_subtract(a, b))
    total = _length(_add(a, b))
    return difference / math.hypot(difference, total)


def _quadruple_product(a: Vec3, b: Vec3, c: Vec3, d: Vec3) -> Vec3:
    cross_cd = _cross(c, d)
    triple_acd = _dot(a, cross_cd)
    triple_bcd = _dot(b, cross_cd)
    return _subtract(_scale(b, triple_acd), _scale(a, triple_bcd))


def _spherical_triangle_area(a: Vec3, b: Vec3, c: Vec3) -> float:
    """Signed spherical excess for a unit-sphere triangle."""
    numerator = _triple_product(a, b, c)
    denominator = 1.0 + _dot(a, b) + _dot(b, c) + _dot(c, a)
    return 2.0 * math.atan2(numerator, denominator)


def _angle(a: Vec3, b: Vec3) -> float:
    value = _dot(a, b) / (_length(a) * _length(b))
    return math.acos(max(-1.0, min(1.0, value)))


def _slerp(a: Vec3, b: Vec3, fraction: float) -> Vec3:
    angle = _angle(a, b)
    if abs(angle) < 1e-15:
        return a
    sine = math.sin(angle)
    weight_a = math.sin((1.0 - fraction) * angle) / sine
    weight_b = math.sin(fraction * angle) / sine
    return _add(_scale(a, weight_a), _scale(b, weight_b))


def _face_to_barycentric(point: Point2D, triangle: Triangle2D) -> Tuple[float, float, float]:
    a, b, c = triangle
    d31 = (a[0] - c[0], a[1] - c[1])
    d23 = (c[0] - b[0], c[1] - b[1])
    d3p = (point[0] - c[0], point[1] - c[1])

    determinant = d23[0] * d31[1] - d23[1] * d31[0]
    u = (d23[0] * d3p[1] - d23[1] * d3p[0]) / determinant
    v = (d31[0] * d3p[1] - d31[1] * d3p[0]) / determinant
    return (u, v, 1.0 - u - v)


def _barycentric_to_face(
    barycentric: Tuple[float, float, float], triangle: Triangle2D
) -> Point2D:
    u, v, w = barycentric
    a, b, c = triangle
    return (
        u * a[0] + v * b[0] + w * c[0],
        u * a[1] + v * b[1] + w * c[1],
    )


def _snyder_forward(point: Vec3, spherical_triangle: Triangle3D) -> Point2D:
    """Map a unit-sphere point in one icosahedral face to its equal-area plane."""
    a, b, c = spherical_triangle
    direction = _normalize(_subtract(point, a))
    intersection = _normalize(_quadruple_product(a, direction, b, c))

    # The great-circle intersection has two antipodal solutions.  Select the
    # one on the same hemisphere as the opposite face edge.
    if _dot(intersection, b) + _dot(intersection, c) < 0.0:
        intersection = _scale(intersection, -1.0)

    denominator = _vector_difference(a, intersection)
    if denominator == 0.0:
        return _PLANAR_ROOT[0]

    h = _vector_difference(a, point) / denominator
    area_abc = _spherical_triangle_area(a, b, c)
    scaled_area = h / area_abc
    area_apc = _spherical_triangle_area(a, intersection, c)
    area_abp = _spherical_triangle_area(a, b, intersection)

    barycentric = (
        1.0 - h,
        scaled_area * area_apc,
        scaled_area * area_abp,
    )
    return _barycentric_to_face(barycentric, _PLANAR_ROOT)


def _snyder_inverse(point: Point2D, spherical_triangle: Triangle3D) -> Vec3:
    """Map a point in the equal-area face plane back to the unit sphere."""
    a, b, c = spherical_triangle
    u, v, w = _face_to_barycentric(point, _PLANAR_ROOT)

    threshold = 1.0 - 1e-14
    if u > threshold:
        return a
    if v > threshold:
        return b
    if w > threshold:
        return c

    h = 1.0 - u
    if h <= 1e-15:
        return a

    cross_bc = _cross(b, c)
    area_abc = _spherical_triangle_area(a, b, c)
    alpha = (w / h) * area_abc
    sine_alpha = math.sin(alpha)
    half_sine = math.sin(alpha / 2.0)
    one_minus_cosine = 2.0 * half_sine * half_sine

    dot_ab = _dot(a, b)
    dot_bc = _dot(b, c)
    dot_ca = _dot(c, a)
    sin_bc = _length(cross_bc)
    triple = _dot(a, cross_bc)

    f = sine_alpha * triple + one_minus_cosine * (dot_ab * dot_bc - dot_ca)
    g = one_minus_cosine * sin_bc * (1.0 + dot_ab)
    edge_angle = math.acos(max(-1.0, min(1.0, dot_bc)))
    q = (2.0 / edge_angle) * math.atan2(g, f)
    edge_point = _slerp(b, c, q)

    k = _vector_difference(a, edge_point)
    if k <= 1e-15:
        return a
    denominator = math.asin(max(-1.0, min(1.0, k)))
    numerator = math.asin(max(-1.0, min(1.0, h * k)))
    fraction = numerator / denominator
    return _normalize(_slerp(a, edge_point, fraction))


def _midpoint(a: Point2D, b: Point2D) -> Point2D:
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


def _child_triangle(triangle: Triangle2D, child: int) -> Triangle2D:
    a, b, c = triangle
    ab = _midpoint(a, b)
    bc = _midpoint(b, c)
    ca = _midpoint(c, a)
    children = (
        (a, ab, ca),
        (ab, b, bc),
        (ca, bc, c),
        (bc, ca, ab),
    )
    return children[child]


def _point_in_triangle(point: Point2D, triangle: Triangle2D, tolerance: float = _EPSILON) -> bool:
    u, v, w = _face_to_barycentric(point, triangle)
    return u >= -tolerance and v >= -tolerance and w >= -tolerance


def _unit_vector(latitude: float, longitude: float) -> Vec3:
    latitude_radians = math.radians(latitude)
    longitude_radians = math.radians(longitude)
    cos_latitude = math.cos(latitude_radians)
    return (
        cos_latitude * math.cos(longitude_radians),
        cos_latitude * math.sin(longitude_radians),
        math.sin(latitude_radians),
    )


def _lat_lon(vector: Vec3) -> Coordinate:
    vector = _normalize(vector)
    latitude = math.degrees(math.asin(max(-1.0, min(1.0, vector[2]))))
    longitude = math.degrees(math.atan2(vector[1], vector[0]))
    # Avoid -0.0 in stable serialized/debug output.
    if abs(latitude) < 1e-14:
        latitude = 0.0
    if abs(longitude) < 1e-14:
        longitude = 0.0
    return (latitude, longitude)


def _make_icosahedron() -> Tuple[Tuple[Vec3, ...], Tuple[Tuple[int, int, int], ...]]:
    """Return a pole-oriented regular icosahedron with stable face ordering.

    Faces A..E form the north cap, F..J the upper band, K..O the lower
    band and P..T the south cap.  The first upper-ring vertex lies at
    longitude 0 degrees; the lower ring is staggered by 36 degrees.
    """
    z = 1.0 / math.sqrt(5.0)
    ring_radius = 2.0 / math.sqrt(5.0)

    vertices = [(0.0, 0.0, 1.0)]
    for index in range(5):
        longitude = math.radians(index * 72.0)
        vertices.append(
            (
                ring_radius * math.cos(longitude),
                ring_radius * math.sin(longitude),
                z,
            )
        )
    for index in range(5):
        longitude = math.radians(36.0 + index * 72.0)
        vertices.append(
            (
                ring_radius * math.cos(longitude),
                ring_radius * math.sin(longitude),
                -z,
            )
        )
    vertices.append((0.0, 0.0, -1.0))

    faces = []
    # North cap.
    for index in range(5):
        faces.append((0, 1 + index, 1 + ((index + 1) % 5)))
    # Upper band, downward-pointing.
    for index in range(5):
        faces.append((1 + index, 6 + index, 1 + ((index + 1) % 5)))
    # Lower band, upward-pointing.
    for index in range(5):
        faces.append((6 + index, 6 + ((index + 1) % 5), 1 + ((index + 1) % 5)))
    # South cap.
    for index in range(5):
        faces.append((11, 6 + ((index + 1) % 5), 6 + index))

    return tuple(vertices), tuple(faces)


_ICOSAHEDRON_VERTICES, _ICOSAHEDRON_FACES = _make_icosahedron()
_ROOT_TRIANGLES: Tuple[Triangle3D, ...] = tuple(
    tuple(_ICOSAHEDRON_VERTICES[index] for index in face)  # type: ignore[misc]
    for face in _ICOSAHEDRON_FACES
)


class ISEAGrid(SpatialGrid):
    """Icosahedral Snyder Equal Area hierarchical grid for a spherical world.

    Parameters
    ----------
    radius:
        Radius of the spherical reference surface in any desired length unit.
        Cell areas are returned in the corresponding squared unit.  The default
        unit sphere intentionally avoids an Earth-specific assumption.
    """

    def __init__(self, radius: float = 1.0):
        radius = float(radius)
        if not math.isfinite(radius) or radius <= 0.0:
            raise ValueError("radius must be a finite positive number")
        self.radius = radius

    def cell_at(self, latitude: float, longitude: float, level: int) -> CellAddress:
        latitude, longitude, level = self._validate_coordinate(latitude, longitude, level)
        vector = _unit_vector(latitude, longitude)
        face = self._find_root_face(vector)
        root_triangle = _ROOT_TRIANGLES[face]
        point = _snyder_forward(vector, root_triangle)

        triangle = _PLANAR_ROOT
        path = []
        for _ in range(level):
            child_number = self._find_child(point, triangle)
            path.append(child_number)
            triangle = _child_triangle(triangle, child_number)

        return CellAddress(face, tuple(path))

    def vertices(self, cell: Union[str, CellAddress]) -> Tuple[Coordinate, Coordinate, Coordinate]:
        cell = CellAddress.parse(cell)
        planar = self._planar_triangle(cell)
        spherical_root = _ROOT_TRIANGLES[cell.face]
        return tuple(_lat_lon(_snyder_inverse(vertex, spherical_root)) for vertex in planar)  # type: ignore[return-value]

    def centroid(self, cell: Union[str, CellAddress]) -> Coordinate:
        """Return the inverse-projected planar centroid of the cell.

        This point is a stable representative interior point.  It should not be
        confused with a physical 3D centre of mass or with an area-weighted
        centroid in Cartesian space.
        """
        cell = CellAddress.parse(cell)
        triangle = self._planar_triangle(cell)
        point = (
            sum(vertex[0] for vertex in triangle) / 3.0,
            sum(vertex[1] for vertex in triangle) / 3.0,
        )
        return _lat_lon(_snyder_inverse(point, _ROOT_TRIANGLES[cell.face]))

    def area(self, cell: Union[str, CellAddress]) -> float:
        cell = CellAddress.parse(cell)
        return 4.0 * math.pi * self.radius * self.radius / (20.0 * (4 ** cell.level))

    def contains(self, cell: Union[str, CellAddress], latitude: float, longitude: float) -> bool:
        cell = CellAddress.parse(cell)
        return self.cell_at(latitude, longitude, cell.level) == cell

    def root_face_vertices(self, face: Union[int, str, CellAddress]) -> Tuple[Coordinate, Coordinate, Coordinate]:
        """Return vertices of a root face; primarily useful for inspection/tests."""
        if isinstance(face, CellAddress):
            face_index = face.face
        elif isinstance(face, str):
            parsed = CellAddress.parse(face)
            if parsed.level != 0:
                raise ValueError("root_face_vertices requires a root face")
            face_index = parsed.face
        else:
            face_index = int(face)
            CellAddress(face_index)  # validation
        return tuple(_lat_lon(vertex) for vertex in _ROOT_TRIANGLES[face_index])  # type: ignore[return-value]

    def _planar_triangle(self, cell: CellAddress) -> Triangle2D:
        triangle = _PLANAR_ROOT
        for child_number in cell.path:
            triangle = _child_triangle(triangle, child_number)
        return triangle

    @staticmethod
    def _validate_coordinate(latitude: float, longitude: float, level: int) -> Tuple[float, float, int]:
        latitude = float(latitude)
        longitude = float(longitude)
        if not math.isfinite(latitude) or not -90.0 <= latitude <= 90.0:
            raise ValueError("latitude must be finite and in the range -90..90 degrees")
        if not math.isfinite(longitude):
            raise ValueError("longitude must be finite")
        # Longitude is angular and periodic; normalize to [-180, 180).
        longitude = ((longitude + 180.0) % 360.0) - 180.0

        if not isinstance(level, int) or isinstance(level, bool) or level < 0:
            raise ValueError("level must be a non-negative integer")
        return latitude, longitude, level

    @staticmethod
    def _find_root_face(vector: Vec3) -> int:
        # At exact shared edges/vertices more than one face is mathematically
        # valid.  Stable face order A..T gives deterministic ownership.
        for face_index, triangle in enumerate(_ROOT_TRIANGLES):
            a, b, c = triangle
            if _dot(vector, a) < -_EPSILON:
                continue
            t1 = _triple_product(vector, a, b)
            t2 = _triple_product(vector, b, c)
            t3 = _triple_product(vector, c, a)
            if (
                (t1 >= -_EPSILON and t2 >= -_EPSILON and t3 >= -_EPSILON)
                or (t1 <= _EPSILON and t2 <= _EPSILON and t3 <= _EPSILON)
            ):
                return face_index
        raise RuntimeError("coordinate could not be assigned to an icosahedral face")

    @staticmethod
    def _find_child(point: Point2D, triangle: Triangle2D) -> int:
        # Stable order provides deterministic ownership on subdivision edges.
        for child_number in range(4):
            if _point_in_triangle(point, _child_triangle(triangle, child_number)):
                return child_number
        raise RuntimeError("projected coordinate could not be assigned to a child cell")
