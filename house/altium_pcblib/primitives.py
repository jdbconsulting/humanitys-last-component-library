"""
Altium primitive types: Coord (32-bit raw integer = 1/10000 mil),
CoordPoint, Layer enum, OLE color packing.

Internal Altium coordinates are 32-bit signed integers in units of
1/10000 of a thousandth of an inch (1 raw unit = 0.0001 mil = 25.4
nanometres). This is the resolution Altium stores all geometry at;
the on-disk binary format is just these raw integers.

Layer codes match Altium's binary layer-byte mapping (1 = Top Copper,
32 = Bottom Copper, 37 = Top Solder, 57 = Mechanical 1, 71 =
Mechanical 15, 74 = Multi-Layer, etc.). The C# AltiumSharp code's
``LayerNameToByte`` uses the same numbers; these are stable across
Altium versions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

# 1 raw Coord unit per 1/10000 mil. mm <-> raw conversion uses the
# exact mm-to-mil ratio (25.4 mm/inch -> 39.37007874... mil/mm); we
# round half-up to integer to match what AltiumSharp's Coord.FromMMs
# does.
RAW_PER_MIL = 10_000
RAW_PER_MM = RAW_PER_MIL * 1000.0 / 25.4   # 393700.787...


def mm_to_raw(mm: float) -> int:
    """Convert millimetres to internal Coord raw units (1/10000 mil).
    AltiumSharp v1.0.2's ``Coord.FromMMs`` truncates toward zero
    (i.e. C-style ``(int)``-cast on a double). For most inputs this
    matches ordinary rounding -- 0.2 mm both ways is 78740 -- but for
    inputs whose fractional part falls between 0.5 and 1.0 raw unit
    (e.g. 0.275 mm = 108267.71... raw), truncation drops the .71 and
    yields 108267, while half-away-from-zero rounding would yield
    108268. Matching the truncation behaviour keeps round-trip
    geometry byte-stable against existing C#-emitted libraries."""
    return int(mm * RAW_PER_MM)


def raw_to_mm(raw: int) -> float:
    return raw / RAW_PER_MM


def raw_to_mil_str(raw: int) -> str:
    """Format a raw Coord as the 'X.XXXmil' / 'X.XXXXmil' string Altium
    uses in parameter lists. Trim trailing zeros while preserving the
    decimal point if any. Mirrors the ToString of the AltiumSharp v1
    Coord type."""
    mil = raw / RAW_PER_MIL
    # 4 decimal places of mil = exactly the raw resolution (1 raw =
    # 0.0001 mil), so no precision is lost. Strip trailing zeros for
    # readability except keep at least one digit after the decimal
    # to match what AltiumSharp emits ("0.0001mil" not "0mil").
    s = f"{mil:.4f}"
    # Strip trailing zeros after decimal but keep '.0' if integral.
    if "." in s:
        s = s.rstrip("0").rstrip(".")
        if "." not in s:
            s = s + ".0"
    return s + "mil"


@dataclass(frozen=True)
class Coord:
    """A 32-bit signed Altium coordinate (1 unit = 1/10000 mil)."""

    raw: int

    @classmethod
    def from_mm(cls, mm: float) -> "Coord":
        return cls(mm_to_raw(mm))

    @classmethod
    def from_mil(cls, mil: float) -> "Coord":
        return cls(int(mil * RAW_PER_MIL + (0.5 if mil >= 0 else -0.5)))

    @classmethod
    def from_int32(cls, raw: int) -> "Coord":
        """Construct directly from a raw int (Altium's smallest
        representable unit). Used for sentinel values like the
        ``Coord.FromInt32(1)`` that AltiumSharp v1 needed for
        otherwise-zero fields it would silently drop."""
        return cls(int(raw))

    def to_raw(self) -> int:
        return self.raw

    def to_mm(self) -> float:
        return raw_to_mm(self.raw)

    def to_mil_str(self) -> str:
        return raw_to_mil_str(self.raw)


@dataclass(frozen=True)
class CoordPoint:
    """A 2D Coord pair."""

    x: Coord
    y: Coord

    @classmethod
    def from_mm(cls, x_mm: float, y_mm: float) -> "CoordPoint":
        return cls(Coord.from_mm(x_mm), Coord.from_mm(y_mm))

    @classmethod
    def from_int32(cls, raw: int) -> "CoordPoint":
        c = Coord.from_int32(raw)
        return cls(c, c)


class Layer(IntEnum):
    """Altium binary layer byte mapping (subset relevant to chip
    footprints). Names match the C# project's Layer enum."""

    NoLayer       = 0
    TopLayer      = 1
    BottomLayer   = 32
    TopOverlay    = 33
    BottomOverlay = 34
    TopPaste      = 35
    BottomPaste   = 36
    TopSolder     = 37
    BottomSolder  = 38
    Mechanical1   = 57
    Mechanical2   = 58
    Mechanical3   = 59
    Mechanical4   = 60
    Mechanical5   = 61
    Mechanical6   = 62
    Mechanical7   = 63
    Mechanical8   = 64
    Mechanical9   = 65
    Mechanical10  = 66
    Mechanical11  = 67
    Mechanical12  = 68
    Mechanical13  = 69
    Mechanical14  = 70
    Mechanical15  = 71
    Mechanical16  = 72
    DrillDrawing  = 73
    MultiLayer    = 74


def ole_color(r: int, g: int, b: int) -> int:
    """Pack an RGB triple into a 32-bit Windows OLE_COLOR value
    (the Altium 'BODYCOLOR3D' format), which is little-endian BGR
    in the low 24 bits with the high byte zero."""
    if not (0 <= r < 256 and 0 <= g < 256 and 0 <= b < 256):
        raise ValueError(f"RGB out of range: ({r}, {g}, {b})")
    return r | (g << 8) | (b << 16)
