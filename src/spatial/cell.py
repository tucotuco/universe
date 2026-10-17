#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Hierarchical addresses for triangular spatial cells."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Union


_FACE_LABELS = "ABCDEFGHIJKLMNOPQRST"


@dataclass(frozen=True, order=True)
class CellAddress:
    """Address of one cell in a 20-face, aperture-4 triangular hierarchy.

    ``face`` is one of the twenty root icosahedral faces, numbered 0..19 and
    rendered A..T.  ``path`` contains one child number (0..3) per refinement
    level.  Thus ``A`` is a root face, ``A0`` is one of its four children and
    ``A031`` is a level-3 descendant.

    Child numbering is geometric but deliberately simple:

    * 0: corner at the parent's first vertex
    * 1: corner at the parent's second vertex
    * 2: corner at the parent's third vertex
    * 3: central triangle

    The address records hierarchy only.  It is not a physical coordinate.
    """

    face: int
    path: Tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.face, int) or isinstance(self.face, bool):
            raise TypeError("face must be an integer in the range 0..19")
        if not 0 <= self.face < 20:
            raise ValueError("face must be in the range 0..19")

        normalized_path = tuple(self.path)
        for child in normalized_path:
            if not isinstance(child, int) or isinstance(child, bool):
                raise TypeError("cell path entries must be integers in the range 0..3")
            if not 0 <= child <= 3:
                raise ValueError("cell path entries must be in the range 0..3")
        object.__setattr__(self, "path", normalized_path)

    @classmethod
    def parse(cls, value: Union[str, "CellAddress"]) -> "CellAddress":
        """Parse the compact A..T + base-4 path representation."""
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise TypeError("cell address must be a string or CellAddress")
        value = value.strip().upper()
        if not value:
            raise ValueError("cell address cannot be empty")
        if value[0] not in _FACE_LABELS:
            raise ValueError("cell address must begin with a root face A..T")
        path_text = value[1:]
        if any(character not in "0123" for character in path_text):
            raise ValueError("cell path must contain only digits 0..3")
        return cls(_FACE_LABELS.index(value[0]), tuple(int(c) for c in path_text))

    @property
    def face_label(self) -> str:
        return _FACE_LABELS[self.face]

    @property
    def level(self) -> int:
        return len(self.path)

    @property
    def parent(self) -> Optional["CellAddress"]:
        if not self.path:
            return None
        return CellAddress(self.face, self.path[:-1])

    def child(self, child_number: int) -> "CellAddress":
        return CellAddress(self.face, self.path + (child_number,))

    @property
    def children(self) -> Tuple["CellAddress", ...]:
        return tuple(self.child(i) for i in range(4))

    def ancestors(self, include_self: bool = False) -> Tuple["CellAddress", ...]:
        """Return ancestors from the root face down toward this cell."""
        end = self.level + 1 if include_self else self.level
        return tuple(CellAddress(self.face, self.path[:level]) for level in range(end))

    def is_ancestor_of(self, other: Union[str, "CellAddress"]) -> bool:
        other = CellAddress.parse(other)
        return (
            self.face == other.face
            and self.level < other.level
            and other.path[: self.level] == self.path
        )

    def is_ancestor_or_self_of(self, other: Union[str, "CellAddress"]) -> bool:
        other = CellAddress.parse(other)
        return (
            self.face == other.face
            and self.level <= other.level
            and other.path[: self.level] == self.path
        )

    def __str__(self) -> str:
        return self.face_label + "".join(str(child) for child in self.path)
