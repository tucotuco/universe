"""Canonical truncation for authoritative physical measurements.

Rule constants and intermediate calculations deliberately stay at their source
precision. Callers use these helpers only when committing measured state.
"""
from decimal import Decimal, InvalidOperation, ROUND_DOWN, localcontext
import math


_CENTI = Decimal("0.01")


def truncate_measurement(value):
    """Truncate a finite physical measurement toward zero to hundredths."""
    if value is None:
        return None
    if type(value) is int:
        return value
    if type(value) is not float or not math.isfinite(value):
        raise TypeError("physical measurement must be a finite int or float")
    try:
        decimal_value = Decimal(str(value))
        parts = decimal_value.as_tuple()
        with localcontext() as context:
            context.prec = max(28, len(parts.digits) + abs(parts.exponent) + 4)
            result = decimal_value.quantize(_CENTI, rounding=ROUND_DOWN)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("physical measurement cannot be quantized") from exc
    if result.is_zero():
        return 0.0
    return float(result)


def is_truncated_measurement(value):
    if value is None or type(value) is int:
        return True
    if type(value) is not float or not math.isfinite(value):
        return False
    try:
        return truncate_measurement(value) == value
    except (TypeError, ValueError, OverflowError):
        return False


def truncate_position(position):
    from spatial.state import CartesianPosition
    if type(position) is not CartesianPosition:
        raise TypeError("position must be a CartesianPosition")
    return CartesianPosition(*(truncate_measurement(value) for value in position.as_tuple()))
