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
    """3D body envelope. Field set matches what the current
    AltiumSharp v2 writer emits (which in turn matches what Altium
    Designer itself emits when saving a PcbLib that contains a
    STEP-driven body), verified against the AltiumSharp v2 source at
    ``Serialization/Writers/PcbLibWriter.cs::WriteComponentBody``.

    Why every field below is needed (even when its value is 0):
    Altium reads the parameter block by name lookup, then carries
    the resulting ``IPCB_ComponentBody`` along three completely
    different code paths -- the in-PcbLib 3D viewer, the
    Components-pane preview, and the PcbDoc placement path. The
    viewer is forgiving and renders the embedded STEP from
    ``Library/Models/<n>`` even when most parameters are missing.
    The other two paths are not: they decide whether to load the
    STEP or fall back to extruding the polygon outline based on the
    full parameter set. Empirically, omitting any of ``KIND``,
    ``UNIONINDEX``, ``CAVITYHEIGHT``, ``BODYPROJECTION``,
    ``MODEL.2D.ROTATION``, ``MODEL.3D.ROTX/Y/Z`` or
    ``MODEL.CHECKSUM`` is enough to send those paths down the
    extruded-outline branch even though ``ISSHAPEBASED=FALSE``.
    AltiumSharp v2 emits all of them (with 0 for unset values), so
    we do too.

    ``is_shape_based`` defaults to ``False``: ``ISSHAPEBASED=TRUE``
    tells Altium "render the polygon outline as an extrusion with
    StandoffHeight..OverallHeight"; ``FALSE`` tells it "load the
    embedded model identified by MODELID from Library/Models/<n>".
    For 3D-STEP-driven bodies we want the latter."""

    layer: Layer = Layer.Mechanical1
    v7_layer: str = "MECHANICAL1"
    outline: List[CoordPoint] = field(default_factory=list)

    name: str = ""
    kind: int = 0
    sub_poly_index: int = 0
    union_index: int = 0
    arc_resolution: Coord = Coord(0)
    is_shape_based: bool = False
    cavity_height: Coord = Coord(0)
    standoff_height: Coord = Coord(0)
    overall_height: Coord = Coord(0)
    body_color_3d: int = 0xA0A0A0                # OLE_COLOR (BGR-packed)
    body_opacity_3d: float = 1.0
    body_projection: int = 0
    identifier: str = "ChipBody"
    texture: str = ""

    model_id: str = ""                           # GUID linking to Library/Models/<n>
    model_embed: bool = True
    model_2d_x: Coord = Coord(0)
    model_2d_y: Coord = Coord(0)
    model_2d_rotation: float = 0.0
    model_3d_rot_x: float = 0.0
    model_3d_rot_y: float = 0.0
    model_3d_rot_z: float = 0.0
    model_3d_dz: Coord = Coord(0)
    # Altium writes its own checksum of the embedded STEP bytes here
    # using a proprietary algorithm; AltiumSharp v2 documents this
    # field as "set to 0 for newly created models" and Altium
    # tolerates 0 as a "no checksum, accept the bytes as-is" sentinel.
    model_checksum: int = 0
    # Display filename Altium shows in the body Properties dialog and
    # uses to reconstruct the model link when the component is placed
    # into a PcbDoc. Should match the matching ``Library/Models/<n>``
    # entry's ``NAME`` field; the writer auto-fills this if empty.
    model_name: str = ""
    model_type: int = 1                          # 1 = STEP/file model (vs. 0 = extrusion)
    # Altium uses literal ``"Undefined"`` for embedded models (vs.
    # filesystem paths or server URLs for linked ones); see
    # AltiumSharp v2's PcbModel.ModelSource default.
    model_source: str = "Undefined"


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
    writing the matching ``Library/Models/<n>`` stream.

    Defaults match what AltiumSharp v2 emits (which in turn matches
    what Altium itself emits when saving a library that contains a
    STEP-driven body): 9-key ``Library/Models/Data`` entries with
    ``EMBED=TRUE``, ``MODELSOURCE=Undefined``, and 0-valued
    rotations / dz / checksum unless the caller overrides."""

    id: str                           # GUID, matches PcbComponentBody.model_id
    name: str = "ChipBody.STEP"
    is_embedded: bool = True
    model_source: str = "Undefined"
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    rotation_z: float = 0.0
    dz: int = 0                       # raw Coord
    checksum: int = 0
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
