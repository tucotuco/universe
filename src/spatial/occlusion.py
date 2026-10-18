#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Optical properties separate from physical geometry.

Opacity is currently a declarative, effective visual property, *not* an
implemented radiative-transfer law. Geometry intersection and future perception
must not equate occupied volume with optical obstruction.
"""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class VisualOcclusion:
    """Nominal visible-light opacity: 0 transparent, 1 opaque, between partial."""

    opacity: float = 0.0

    def __post_init__(self):
        try:
            value = float(self.opacity)
        except (TypeError, ValueError, OverflowError) as exc:
            raise TypeError("opacity must be numeric") from exc
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError("opacity must be finite and between 0 and 1")
        object.__setattr__(self, "opacity", value)

    @property
    def opaque(self):
        return self.opacity == 1.0

    def to_dict(self):
        return {"opacity": self.opacity}
