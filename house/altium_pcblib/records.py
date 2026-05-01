"""
Dataclasses for the PCB primitive records this writer emits. Field
names mirror AltiumSharp's PcbPad / PcbTrack / PcbRegion /
PcbComponentBody / PcbComponent / PcbModel / PcbLibrary classes
where reasonable; we only carry the fields chip footprints need.

These are pure data containers -- the binary-emit logic lives in
``writer.py``. Splitting them this way keeps record definitions easy
to read and lets the writer iterate generically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .primitives import Coord, CoordPoint, Layer


# --- Pad ---------------------------------------------------------------


@dataclass
class PcbPad:
    """SMT chip pad. Fields populated by the chip-footprint factory
    (see ``footprint.py``); other paths set them directly. We default
    to AltiumSharp's ``SmtTop`` template values where they're stable
    across all our footprints."""

    designator: str
    location: CoordPoint
    size: CoordPoint                            # X-extent x Y-extent (= size_top here)
    layer: Layer = Layer.TopLayer
    rotation_deg: float = 0.0
    is_plated: bool = True
    corner_radius_pct: int = 25                 # 25% rounded-rect corner radius
    paste_mask_expansion: Coord = Coord(0)
    paste_mask_manual: bool = False
    solder_mask_expansion: Coord = Coord(0)
    solder_mask_manual: bool = False


# --- Track -------------------------------------------------------------


@dataclass
class PcbTrack:
    """Straight line segment (used for component outline + centroid
    crosshairs in chip footprints)."""

    layer: Layer
    start: CoordPoint
    end: CoordPoint
    width: Coord


# --- Region ------------------------------------------------------------


@dataclass
class PcbRegion:
    """Polygon region (used for solder-mask bridge between adjacent
    pad apertures when the natural sliver is too narrow)."""

    layer: Layer
    outline: List[CoordPoint] = field(default_factory=list)
    # AltiumSharp's region has KIND/NET/UNIQUEID/NAME parameter
    # fields. Our chip footprints don't set any of them -- the
    # parameter block is just an empty C-string. Kept here for
    # completeness in case future record types need them.
    kind: int = 0
    net: str = ""
    unique_id: str = ""
    name: str = ""


# --- Component body (3D model envelope) -------------------------------


@dataclass
class PcbComponentBody:
    """3D body envelope. Carries the polygon outline (top-down
    silhouette of the body), the body height parameters, the body
    colour, and -- if a STEP model is embedded -- the link
    (``model_id``) to the matching ``Library/Models/<n>`` stream."""

    layer: Layer = Layer.Mechanical1
    v7_layer: str = "MECHANICAL1"
    outline: List[CoordPoint] = field(default_factory=list)

    name: str = ""
    sub_poly_index: int = -1
    union_index: int = 0
    is_shape_based: bool = True
    cavity_height: Coord = Coord(0)
    standoff_height: Coord = Coord(1)            # v1 0-coord workaround sentinel
    overall_height: Coord = Coord(0)
    arc_resolution: Coord = Coord(1)             # v1 sentinel
    body_color_3d: int = 0xA0A0A0                # OLE_COLOR (BGR-packed)
    body_opacity_3d: float = 1.0
    body_projection: int = 0
    identifier: str = "ChipBody"                 # written as comma-separated codepoints
    texture: str = ""
    model_id: str = ""                           # GUID linking to Library/Models/<n>
    model_embed: bool = True
    model_2d_x: Coord = Coord(1)
    model_2d_y: Coord = Coord(1)
    model_2d_rotation: float = 0.0
    model_3d_dz: Coord = Coord(1)
    texture_center_x: Coord = Coord(1)
    texture_center_y: Coord = Coord(1)
    texture_size_x: Coord = Coord(1)
    texture_size_y: Coord = Coord(1)
    texture_rotation: float = 1e-6               # v1 0-double workaround sentinel


# --- Component & library -----------------------------------------------


@dataclass
class PcbComponent:
    """A single footprint (one storage in the .pcblib).

    Primitive lists are emitted in the order: arcs, pads, vias,
    tracks, texts, fills, regions, component_bodies (matching the
    AltiumSharp writer's emission order so consumers get bytes in a
    predictable arrangement)."""

    name: str
    height: Coord
    description: str = ""
    item_guid: str = ""
    revision_guid: str = ""

    pads: List[PcbPad] = field(default_factory=list)
    tracks: List[PcbTrack] = field(default_factory=list)
    regions: List[PcbRegion] = field(default_factory=list)
    component_bodies: List[PcbComponentBody] = field(default_factory=list)


# --- 3D model (one entry in Library/Models) ---------------------------


@dataclass
class PcbModel:
    """One entry in the ``Library/Models`` storage. ``step_data`` is
    the raw STEP text; ``writer.py`` will zlib-compress it before
    writing the matching ``Library/Models/<n>`` stream."""

    id: str                           # GUID, matches PcbComponentBody.model_id
    name: str = "ChipBody.STEP"
    is_embedded: bool = True
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    rotation_z: float = 0.0
    dz: int = 1                       # raw Coord; 1 = v1 0-coord workaround sentinel
    checksum: int = 0
    model_source: str = ""
    step_data: str = ""               # uncompressed STEP text


# --- Library -----------------------------------------------------------


@dataclass
class PcbLibrary:
    """Top-level library object. ``unique_id`` is the 8-character
    library identifier in FileHeader; AltiumSharp v1 doesn't write
    that field at all (file is just 32 bytes), so we don't either by
    default. ``components`` and ``models`` are the body of the file."""

    components: List[PcbComponent] = field(default_factory=list)
    models: List[PcbModel] = field(default_factory=list)
    library_parameters: Optional[Dict[str, str]] = None
