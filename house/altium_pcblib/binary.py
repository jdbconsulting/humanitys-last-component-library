"""
Length-prefixed binary block framing matching AltiumSharp's
``BinaryFormatWriter``. Used inside CFB streams (component ``Data``,
``Parameters``, etc.).

All multi-byte integers are little-endian. Strings are encoded in
Windows-1252 (the historical Altium encoding); ASCII content -- which
is everything our chip footprints emit -- is identical in both
encodings, but using cp1252 keeps the door open for non-ASCII
parameter values without introducing a different bug class.
"""

from __future__ import annotations

import io
import struct
from typing import Callable, Dict, Iterable, List, Optional


# Altium uses Windows-1252 in nearly every binary format string field.
ALTIUM_ENCODING = "cp1252"


class BinaryWriter:
    """Mutable byte buffer with helpers matching the C# class. All
    methods write directly to ``self.buf``; call ``getvalue()`` to
    extract the assembled bytes."""

    __slots__ = ("buf",)

    def __init__(self) -> None:
        self.buf = io.BytesIO()

    # ----- Primitive write methods --------------------------------

    def write_u8(self, v: int) -> None:
        self.buf.write(struct.pack("<B", v & 0xFF))

    def write_u16(self, v: int) -> None:
        self.buf.write(struct.pack("<H", v & 0xFFFF))

    def write_i16(self, v: int) -> None:
        self.buf.write(struct.pack("<h", v))

    def write_u32(self, v: int) -> None:
        self.buf.write(struct.pack("<I", v & 0xFFFFFFFF))

    def write_i32(self, v: int) -> None:
        self.buf.write(struct.pack("<i", v))

    def write_f64(self, v: float) -> None:
        self.buf.write(struct.pack("<d", v))

    def write_bool(self, v: bool) -> None:
        self.buf.write(b"\x01" if v else b"\x00")

    def write_bytes(self, data: bytes) -> None:
        self.buf.write(data)

    def write_fill(self, value: int, count: int) -> None:
        if count > 0:
            self.buf.write(bytes([value & 0xFF]) * count)

    # ----- Coord / CoordPoint shortcuts ---------------------------

    def write_coord(self, raw: int) -> None:
        """Write a Coord value (i32 little-endian, raw units)."""
        self.write_i32(raw)

    def write_coord_point(self, raw_x: int, raw_y: int) -> None:
        self.write_i32(raw_x)
        self.write_i32(raw_y)

    # ----- Pascal / C-string helpers ------------------------------

    def write_pascal_short_string(self, s: str) -> None:
        """1-byte length prefix + Windows-1252 chars (no null
        terminator). Length is clamped to 255."""
        encoded = s.encode(ALTIUM_ENCODING) if s else b""
        n = min(len(encoded), 255)
        self.write_u8(n)
        if n:
            self.buf.write(encoded[:n])

    def write_string_block(self, s: str) -> None:
        """``WriteBlock(w => w.WritePascalShortString(s))``: u32 size
        prefix wrapping a 1-byte-len pascal string. Used for the
        component name and pad designator."""
        with self.block():
            self.write_pascal_short_string(s)

    def write_c_string(self, s: str) -> None:
        """Bare null-terminated C string in Windows-1252. No size prefix."""
        encoded = s.encode(ALTIUM_ENCODING) if s else b""
        self.buf.write(encoded)
        self.write_u8(0)

    def write_c_string_param_block(self, params: Dict[str, str]) -> None:
        """``WriteBlock(w => w.WriteCString(ParametersToString(params)))``:
        u32 size prefix wrapping a null-terminated ``|KEY=VAL|...``
        string. Used for component parameters, region/body parameter
        blobs, and the library header."""
        param_str = parameters_to_string(params)
        with self.block():
            self.write_c_string(param_str)

    # ----- Block (size-prefixed) ----------------------------------

    def block(self) -> "_BlockContext":
        """Context manager that emits a u32 length prefix and back-
        patches it once the inner writes finish::

            with bw.block():
                bw.write_u8(...)
                bw.write_coord(...)
        """
        return _BlockContext(self)

    def write_block_bytes(self, payload: bytes) -> None:
        """Convenience: ``write_u32(len(payload)); write_bytes(payload)``."""
        self.write_u32(len(payload))
        if payload:
            self.buf.write(payload)

    # ----- Output -------------------------------------------------

    def getvalue(self) -> bytes:
        return self.buf.getvalue()


class _BlockContext:
    __slots__ = ("_w", "_start")

    def __init__(self, w: BinaryWriter) -> None:
        self._w = w
        self._start = -1

    def __enter__(self) -> BinaryWriter:
        # Reserve 4 bytes for the size prefix; we'll back-patch on exit.
        self._start = self._w.buf.tell()
        self._w.buf.write(b"\x00\x00\x00\x00")
        return self._w

    def __exit__(self, exc_type, exc, tb) -> None:
        end = self._w.buf.tell()
        length = end - self._start - 4
        self._w.buf.seek(self._start)
        self._w.buf.write(struct.pack("<I", length))
        self._w.buf.seek(end)


def parameters_to_string(params: Optional[Dict[str, str]]) -> str:
    """Format a dict as ``|K1=V1|K2=V2|...``. Order is the dict's
    insertion order (Python 3.7+ guarantees this), which matches the
    order the C# writer emits when fed an ``OrderedDict`` -- callers
    pass a plain dict here knowing that they're picking the on-wire
    order."""
    if not params:
        return ""
    parts: List[str] = []
    for k, v in params.items():
        parts.append("|")
        parts.append(k)
        parts.append("=")
        parts.append("" if v is None else str(v))
    return "".join(parts)
