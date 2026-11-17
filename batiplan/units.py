"""Length units. Internal storage is ALWAYS millimetres."""
import re
UNITS = {"mm": 1.0, "cm": 10.0, "m": 1000.0}
DECIMALS = {"mm": 0, "cm": 1, "m": 3}


def to_mm(value, unit): return float(value) * UNITS[unit]
def from_mm(value_mm, unit): return float(value_mm) / UNITS[unit]


def fmt_len(value_mm, unit, with_unit=False):
    s = f"{from_mm(value_mm, unit):.{DECIMALS[unit]}f}"
    return f"{s} {unit}" if with_unit else s


_num = re.compile(r"^\s*([-+]?\d+(?:[.,]\d+)?)\s*(mm|cm|m)?\s*$", re.I)


def parse_len(text, unit):
    """Parse '2.5', '2,5', '250cm', '2.5 m' -> millimetres. Raises ValueError."""
    m = _num.match(str(text))
    if not m: raise ValueError(text)
    return float(m.group(1).replace(",", ".")) * UNITS[(m.group(2) or unit).lower()]
