"""
Build a ``PcbComponent`` from a footprint specification dict (the
shape produced by ``vendors/_common.write_footprints_json``). Direct
port of ``house/HouseLibGenerator/ChipFootprintBuilder.cs`` -- same
IPC math, same DDL drawing rules, same v1.0.2 zero-coord workarounds.

Coordinate frame (matching ``ipc.py``):

  * Body length L along X, body width W along Y.
  * Pads at (+/-spacing/2, 0).
  * Pad CAD size = (length_along_terminal, width_across_terminal),
    i.e. (X-extent, Y-extent).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping, Tuple

from . import ddl
from .ipc import compute_pad, select_rule
from .primitives import Coord, CoordPoint, Layer, ole_color
from .records import (
    PcbComponent,
    PcbComponentBody,
    PcbPad,
    PcbRegion,
    PcbTrack,
)


# Per-family body-color palette. Must match the dominant body solid
# colour in the parametric STEP file (see ``house/stepgen/colors.py``)
# so Altium's BODYCOLOR3D 2D-fill matches what the embedded STEP
# renders in 3D view.
_BODY_COLORS = {
    "C":  (184, 134,  11),     # MLCC tan       (#B7860B)
    "R":  (158, 158, 158),     # alumina grey   (#9E9E9E)
    "I":  ( 38,  77, 148),     # ferrite blue   (#264D94)
    "FB": ( 38,  77, 148),     # ferrite-bead body shares the inductor blue
}
_DEFAULT_BODY_COLOR = (160, 160, 160)


@dataclass(frozen=True)
class FootprintInput:
    """Mirror of one footprints-JSON row (see vendors/_common.py)."""

    name: str
    kind: str               # "C" / "R" / "I" / "FB"
    density: str            # "L" / "N" / "M"
    body_length_mm: float
    body_width_mm: float
    body_height_mm: float
    terminal_length_mm: float

    @classmethod
    def from_json(cls, row: Mapping) -> "FootprintInput":
        body = row["bodyMm"]
        return cls(
            name=row["name"],
            kind=row["kind"],
            density=row["density"],
            body_length_mm=float(body["lengthNominal"]),
            body_width_mm=float(body["widthNominal"]),
            body_height_mm=float(body["heightNominal"]),
            terminal_length_mm=float(body["terminalLengthNominal"]),
        )


def build_chip_footprint(input: FootprintInput) -> Tuple[PcbComponent, str]:
    """Construct one chip footprint per IPC-7351B + DDL-001. Returns
    the assembled ``PcbComponent`` and a (possibly empty) diagnostic
    string that the caller may print to stderr (e.g. "added Top
    Solder bridge region").
    """
    if len(input.density) != 1:
        raise ValueError(
            f"footprint {input.name}: density {input.density!r} must be a single character L/N/M"
        )

    rule = select_rule(input.body_length_mm, input.body_width_mm, input.density)
    pad = compute_pad(
        body_length_mm=input.body_length_mm,
        body_width_mm=input.body_width_mm,
        terminal_length_mm=input.terminal_length_mm,
        rule=rule,
    )

    pads = [
        _make_pad("1", -pad.pad_center_spacing_mm / 2.0, pad),
        _make_pad("2", +pad.pad_center_spacing_mm / 2.0, pad),
    ]

    # Solder mask bridge region when the natural sliver would fall
    # below 0.1 mm. With per-pad expansion E = 0.05 mm the sliver is
    # (G - 2E); when too tight, overlay a region rather than shrinking
    # the copper. Region geometry per DDL-001 §11.2.5: rectangle from
    # (-spacing/2, -h/2) to (+spacing/2, +h/2) on Top Solder.
    natural_sliver = pad.g_mm - 2.0 * ddl.SOLDER_MASK_EXPANSION_MM
    needs_bridge = natural_sliver < ddl.MIN_SOLDER_MASK_SLIVER_MM - 1e-9
    regions = []
    diagnostics = ""
    if needs_bridge:
        regions.append(_make_solder_mask_bridge(pad))
        diagnostics = (
            f"  {input.name}: natural mask sliver "
            f"{natural_sliver:.3f}mm < {ddl.MIN_SOLDER_MASK_SLIVER_MM}mm; "
            "added Top Solder bridge region across the two apertures"
        )

    tracks = list(_make_outline_and_centroid(input.body_length_mm, input.body_width_mm))
    body = _make_component_body(
        input.name,
        input.kind,
        input.body_length_mm,
        input.body_width_mm,
        input.body_height_mm,
    )

    fp = PcbComponent(
        name=input.name,
        height=Coord.from_mm(input.body_height_mm),
        description="",
        item_guid="",
        revision_guid="",
        pads=pads,
        regions=regions,
        tracks=tracks,
        component_bodies=[body],
    )
    return fp, diagnostics


# ----- Pad ---------------------------------------------------------


def _make_pad(designator: str, x_mm: float, pad) -> PcbPad:
    return PcbPad(
        designator=designator,
        location=CoordPoint.from_mm(x_mm, 0.0),
        # Pad CAD size: X = along-terminal (= half (Z-G)), Y = across-terminal (= X).
        size=CoordPoint.from_mm(
            pad.pad_length_along_terminal_mm,
            pad.pad_width_across_terminal_mm,
        ),
        layer=Layer.TopLayer,
        rotation_deg=0.0,
        is_plated=True,
        corner_radius_pct=ddl.PAD_CORNER_RADIUS_PERCENT,
        paste_mask_expansion=Coord(0),
        paste_mask_manual=False,
        solder_mask_expansion=Coord.from_mm(ddl.SOLDER_MASK_EXPANSION_MM),
        solder_mask_manual=True,
    )


# ----- Solder-mask bridge region ----------------------------------


def _make_solder_mask_bridge(pad) -> PcbRegion:
    half_spacing_x = pad.pad_center_spacing_mm / 2.0
    half_aperture_y = (pad.pad_width_across_terminal_mm + 2.0 * ddl.SOLDER_MASK_EXPANSION_MM) / 2.0
    return PcbRegion(
        layer=Layer.TopSolder,
        outline=[
            CoordPoint.from_mm(-half_spacing_x, -half_aperture_y),
            CoordPoint.from_mm(+half_spacing_x, -half_aperture_y),
            CoordPoint.from_mm(+half_spacing_x, +half_aperture_y),
            CoordPoint.from_mm(-half_spacing_x, +half_aperture_y),
        ],
    )


# ----- Component outline + centroid -------------------------------


def _make_outline_and_centroid(body_length_mm: float, body_width_mm: float):
    half_l = body_length_mm / 2.0
    half_w = body_width_mm  / 2.0
    width  = Coord.from_mm(ddl.OUTLINE_LINE_WIDTH_MM)

    def track(x1: float, y1: float, x2: float, y2: float) -> PcbTrack:
        return PcbTrack(
            layer=Layer.Mechanical15,
            start=CoordPoint.from_mm(x1, y1),
            end=CoordPoint.from_mm(x2, y2),
            width=width,
        )

    # Closed rectangle outline (nominal L x W).
    yield track(-half_l, -half_w, +half_l, -half_w)
    yield track(+half_l, -half_w, +half_l, +half_w)
    yield track(+half_l, +half_w, -half_l, +half_w)
    yield track(-half_l, +half_w, -half_l, -half_w)

    # Centroid crosshair, capped per DDL-001 §11.4 so each arm fits
    # inside the body outline AND is no longer than 0.5 mm.
    cross_half_x = min(half_l, ddl.MAX_CROSSHAIR_HALF_ARM_MM)
    cross_half_y = min(half_w, ddl.MAX_CROSSHAIR_HALF_ARM_MM)
    yield track(-cross_half_x, 0.0,           +cross_half_x, 0.0)
    yield track(0.0,           -cross_half_y, 0.0,           +cross_half_y)


# ----- 3D component body --------------------------------------------


def _make_component_body(
    name: str,
    kind: str,
    body_length_mm: float,
    body_width_mm: float,
    body_height_mm: float,
) -> PcbComponentBody:
    half_l = body_length_mm / 2.0
    half_w = body_width_mm  / 2.0
    rgb = _BODY_COLORS.get(kind, _DEFAULT_BODY_COLOR)
    standoff = (
        Coord.from_mm(ddl.COMPONENT_BODY_STANDOFF_MM)
        if ddl.COMPONENT_BODY_STANDOFF_MM > 0
        else Coord(1)             # v1.0.2 zero-coord workaround sentinel
    )
    return PcbComponentBody(
        layer=Layer.Mechanical1,
        v7_layer="MECHANICAL1",
        outline=[
            CoordPoint.from_mm(-half_l, -half_w),
            CoordPoint.from_mm(+half_l, -half_w),
            CoordPoint.from_mm(+half_l, +half_w),
            CoordPoint.from_mm(-half_l, +half_w),
        ],
        overall_height=Coord.from_mm(body_height_mm),
        standoff_height=standoff,
        body_color_3d=ole_color(*rgb),
        body_opacity_3d=1.0,
        identifier="ChipBody",
        name="",
        model_id=_deterministic_guid(name),
        model_embed=True,
    )


def _deterministic_guid(footprint_name: str) -> str:
    """Derive an Altium-style ``{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}``
    GUID from a footprint name via MD5. Matches what the C# project's
    ``DeterministicGuid`` produces (it constructs ``new Guid(md5)``,
    which on .NET is a little-endian repacking of the first 16 bytes
    -- the same byte order used here)."""
    h = hashlib.md5(footprint_name.encode("utf-8")).digest()
    # .NET's Guid(byte[16]) treats the first three groups as little-
    # endian, the rest as big-endian. Match that byte ordering.
    a = int.from_bytes(h[0:4],  "little")
    b = int.from_bytes(h[4:6],  "little")
    c = int.from_bytes(h[6:8],  "little")
    d = h[8:10]
    e = h[10:16]
    return (
        f"{{{a:08X}-{b:04X}-{c:04X}-"
        f"{d[0]:02X}{d[1]:02X}-"
        f"{e[0]:02X}{e[1]:02X}{e[2]:02X}{e[3]:02X}{e[4]:02X}{e[5]:02X}}}"
    )
