"""Finite generated-Arena hex footprint and read-only Cartesian projection.

Cells use flat-top regular hexagons, one yard between opposite horizontal
edges, with odd columns offset north by half a yard. Addresses are stable
``(column, row)`` pairs; they are presentation addresses, not Reality.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from spatial.state import CartesianPosition


YARDS_TO_METERS = 0.9144
SIDE_TO_SIDE_YARDS = 1.0
_SQRT3 = math.sqrt(3.0)
_SIDE_YARDS = SIDE_TO_SIDE_YARDS / _SQRT3
_COLUMN_STEP_YARDS = _SQRT3 / 2.0
_ORIGIN_X_YARDS = _SIDE_YARDS
_ORIGIN_Y_YARDS = 0.5
_TIE_EPSILON_YARDS = 1e-12
_AXIAL_NEIGHBORS = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))
ENCOUNTER_MAP_SCHEMA = "flat-top-hex-1-yard-v1"


def encounter_map_descriptor(layout: "ArenaHexLayout") -> dict:
    """Return the strict, serializable map contract used by Arena Encounters."""
    if (type(layout) is not ArenaHexLayout or type(layout.cell_ids) is not range
            or layout.cell_ids != range(layout.width_columns * layout.height_rows)):
        raise ValueError("Encounter map descriptor requires a rectangular native hex layout")
    return {"schema": ENCOUNTER_MAP_SCHEMA,
            "width_columns": layout.width_columns,
            "height_rows": layout.height_rows}


def layout_from_encounter_map(value) -> "ArenaHexLayout | None":
    """Rebuild only the adopted rectangular one-yard Arena hex convention."""
    if value is None:
        return None
    from types import MappingProxyType
    if (type(value) not in (dict, MappingProxyType)
            or set(value) != {"schema", "width_columns", "height_rows"}
            or value["schema"] != ENCOUNTER_MAP_SCHEMA
            or type(value["width_columns"]) is not int
            or type(value["height_rows"]) is not int):
        raise ValueError("unsupported Encounter map descriptor")
    return ArenaHexLayout.rectangle(value["width_columns"], value["height_rows"])


@dataclass(frozen=True, order=True)
class HexAddress:
    column: int
    row: int


@dataclass(frozen=True)
class ArenaHexLayout:
    """A bounded finite set of hexes, with explicit support for irregular edges."""

    width_columns: int
    height_rows: int
    cell_ids: range | frozenset[int]

    @classmethod
    def rectangle(cls, width_columns: int, height_rows: int) -> "ArenaHexLayout":
        if (type(width_columns) is not int or width_columns < 1
                or type(height_rows) is not int or height_rows < 1):
            raise ValueError("hex layout dimensions must be positive integers")
        return cls(width_columns, height_rows, range(width_columns * height_rows))

    @classmethod
    def irregular(cls, width_columns: int, height_rows: int,
                  addresses) -> "ArenaHexLayout":
        """Create a finite irregular outline inside the declared address bounds."""
        if type(width_columns) is not int or width_columns < 1 or type(height_rows) is not int or height_rows < 1:
            raise ValueError("hex layout dimensions must be positive integers")
        ids = set()
        for address in addresses:
            if type(address) is not HexAddress or not (
                    0 <= address.column < width_columns and 0 <= address.row < height_rows):
                raise ValueError("hex address is outside the declared layout bounds")
            ids.add(address.column * height_rows + address.row)
        return cls(width_columns, height_rows, frozenset(ids))

    @property
    def side_to_side_meters(self) -> float:
        return SIDE_TO_SIDE_YARDS * YARDS_TO_METERS

    @property
    def side_length_meters(self) -> float:
        return self.side_to_side_meters / _SQRT3

    @property
    def column_step_meters(self) -> float:
        return _COLUMN_STEP_YARDS * YARDS_TO_METERS

    @property
    def row_step_meters(self) -> float:
        return YARDS_TO_METERS

    @property
    def odd_column_offset_meters(self) -> float:
        return 0.5 * YARDS_TO_METERS

    @property
    def origin_offset_meters(self) -> tuple[float, float]:
        return (_ORIGIN_X_YARDS * YARDS_TO_METERS,
                _ORIGIN_Y_YARDS * YARDS_TO_METERS)

    @property
    def vertex_offsets_meters(self) -> tuple[tuple[float, float], ...]:
        side = self.side_length_meters
        return tuple((side * math.cos(index * math.pi / 3),
                      side * math.sin(index * math.pi / 3)) for index in range(6))

    def address_for_index(self, index: int) -> HexAddress:
        if type(index) is not int or not 0 <= index < self.width_columns * self.height_rows:
            raise ValueError("hex index is outside the declared layout bounds")
        column, row = divmod(index, self.height_rows)
        return HexAddress(column, row)

    def index_for_address(self, address: HexAddress) -> int:
        if type(address) is not HexAddress:
            raise TypeError("native HexAddress required")
        return address.column * self.height_rows + address.row

    def contains(self, address: HexAddress) -> bool:
        return (type(address) is HexAddress
                and 0 <= address.column < self.width_columns
                and 0 <= address.row < self.height_rows
                and self.index_for_address(address) in self.cell_ids)

    def addresses(self):
        for index in self.cell_ids:
            yield self.address_for_index(index)

    def center_yards(self, address: HexAddress) -> tuple[float, float]:
        if not self.contains(address):
            raise ValueError("hex address is not in this footprint")
        return (_ORIGIN_X_YARDS + address.column * _COLUMN_STEP_YARDS,
                _ORIGIN_Y_YARDS + address.row + (address.column % 2) * 0.5)

    def center_position(self, address: HexAddress, z: float = 0.0) -> CartesianPosition:
        x, y = self.center_yards(address)
        return CartesianPosition(x * YARDS_TO_METERS, y * YARDS_TO_METERS, z)

    def neighbors(self, address: HexAddress) -> tuple[HexAddress, ...]:
        """Return the six edge-sharing neighbors on the unbounded hex lattice."""
        if type(address) is not HexAddress:
            raise TypeError("native HexAddress required")
        q = address.column
        r = address.row - q // 2
        result = []
        for dq, dr in _AXIAL_NEIGHBORS:
            nq, nr = q + dq, r + dr
            result.append(HexAddress(nq, nr + nq // 2))
        return tuple(result)

    def column_row_ranges(self) -> tuple[tuple[int, tuple[tuple[int, int], ...]], ...]:
        """Compact finite footprint by column as inclusive row ranges."""
        by_column: dict[int, list[int]] = {}
        for address in self.addresses():
            by_column.setdefault(address.column, []).append(address.row)
        columns = []
        for column in sorted(by_column):
            rows = sorted(by_column[column])
            ranges = []
            first = prior = rows[0]
            for row in rows[1:]:
                if row == prior + 1:
                    prior = row
                    continue
                ranges.append((first, prior))
                first = prior = row
            ranges.append((first, prior))
            columns.append((column, tuple(ranges)))
        return tuple(columns)

    @staticmethod
    def _contains_point(center_x: float, center_y: float, x: float, y: float) -> bool:
        """Closed polygon membership; epsilon makes floating edge ties stable."""
        dx, dy = abs(x - center_x), abs(y - center_y)
        side = _SIDE_YARDS
        eps = _TIE_EPSILON_YARDS
        if dy > SIDE_TO_SIDE_YARDS / 2 + eps or dx > side + eps:
            return False
        # The two sloping edge pairs are |dy| + sqrt(3)|dx| <= 1 yard.
        return dy + _SQRT3 * dx <= SIDE_TO_SIDE_YARDS + eps

    def cell_at_position(self, position: CartesianPosition) -> HexAddress | None:
        """Return the containing in-footprint hex, without altering the position.

        Exact edge/vertex ties choose the lexicographically smallest in-map
        ``(column,row)`` address. Points outside the finite footprint return
        ``None``. Z is ignored because this display is a horizontal map layer.
        """
        if not isinstance(position, CartesianPosition):
            raise TypeError("native CartesianPosition required")
        x, y = position.x / YARDS_TO_METERS, position.y / YARDS_TO_METERS
        q_float = (x - _ORIGIN_X_YARDS) / _COLUMN_STEP_YARDS
        r_float = y - _ORIGIN_Y_YARDS - q_float / 2
        q_base, r_base = math.floor(q_float), math.floor(r_float)
        candidates = []
        for q in range(q_base - 2, q_base + 3):
            for r in range(r_base - 2, r_base + 3):
                address = HexAddress(q, r + q // 2)
                if not self.contains(address):
                    continue
                center_x, center_y = self.center_yards(address)
                if self._contains_point(center_x, center_y, x, y):
                    candidates.append(address)
        return min(candidates) if candidates else None
