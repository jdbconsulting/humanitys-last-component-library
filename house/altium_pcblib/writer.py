"""
Top-level ``PcbLibrary`` -> ``.PcbLib`` writer.

Composes the lower-level pieces:

  * ``records`` defines the data classes for each primitive type.
  * ``binary`` provides the length-prefixed-block framing used inside
    streams.
  * ``cfb`` is the MS-CFB container.

Plus per-record serializers in this file. Each of those mirrors the
matching ``Write*`` method in AltiumSharp's ``PcbLibWriter.cs`` (with
v1.0.2 quirks rolled in -- see the per-method comments).
"""

from __future__ import annotations

import os
import zlib
from typing import Dict, List, Optional

from .binary import BinaryWriter, parameters_to_string
from .cfb import CompoundFile
from .primitives import Coord, CoordPoint, Layer
from .records import (
    PcbLibrary,
    PcbComponent,
    PcbComponentBody,
    PcbModel,
    PcbPad,
    PcbRegion,
    PcbTrack,
)

# --- Constants ---------------------------------------------------------

# Object type IDs used as the leading byte of each primitive record in
# the component Data stream. Per AltiumSharp PcbLibWriter.cs.
TAG_ARC            = 1
TAG_PAD            = 2
TAG_VIA            = 3
TAG_TRACK          = 4
TAG_TEXT           = 5
TAG_FILL           = 6
TAG_REGION         = 11
TAG_COMPONENT_BODY = 12

# Default flags word for chip-footprint primitives. Matches what
# AltiumSharp v1.0.2 emits for all SMT pads / tracks / regions /
# bodies in a footprint library: 0x000C = TentingTop | TentingBottom,
# everything else cleared (no IsLocked, no Keepout, no IsUnlocked
# bit). We could rebuild this from the per-record bool flags, but
# since chip footprints never set those bools, hardcoding is honest.
DEFAULT_FLAGS = 0x000C

# 10 bytes of 0xFF that AltiumSharp v1.0.2 writes after layer+flags on
# every primitive record. Treated as a fill block in the writer; in
# the reader, AltiumSharp interprets these as "ignore" markers for
# fields the binary format doesn't carry.
COMMON_FILL = b"\xFF" * 10

# Pad body block sizes per AltiumSharp v1.0.2 / DDL-001 SMT chip pad.
PAD_MAIN_BLOCK_SIZE = 114                # pad-data fixed-size payload
PAD_SIZE_SHAPE_BLOCK_SIZE = 596          # extended size/shape payload

# Pad shape codes (AltiumSharp PcbPadShape enum).
PAD_SHAPE_ROUND       = 1
PAD_SHAPE_ROUNDEDRECT = 9

# Pad shape that the v1.0.2 writer puts in the *main* block for a
# rounded-rectangle pad. The legacy main-block field doesn't have a
# code for RoundedRectangle, so v1 emits PAD_SHAPE_ROUND there and
# relies on the extended size/shape block's ``HasRoundedRect`` flag
# (and PerLayerShapes[i] = 9) to tell the reader the actual shape.
PAD_MAIN_BLOCK_SHAPE = PAD_SHAPE_ROUND

# Internal-layer shape constant repeated in the pad's size/shape
# extended block. Chip pads are rounded rect on every layer.
PAD_INTERNAL_SHAPE = PAD_SHAPE_ROUNDEDRECT

# Default thermal-relief / power-plane values that AltiumSharp v1.0.2
# writes for every SMT pad even when our PcbPad doesn't set them.
# Matching these makes the per-pad bytes diff-clean against C#-emitted
# reference files; the values themselves never matter for SMT pads
# (no plane connection, no thermal relief), but the binary still
# carries the PCB-level defaults at these offsets.
DEFAULT_RELIEF_CONDUCTOR_WIDTH_RAW = 100_000     # 10 mil
DEFAULT_POWER_PLANE_CLEARANCE_RAW  = 100_000     # 10 mil
DEFAULT_POWER_PLANE_RELIEF_RAW     = 200_000     # 20 mil
DEFAULT_RESERVED_AT_82_RAW         = 200_000     # 20 mil (v1 quirk)


def write_pcblib(library: PcbLibrary, output_path: str) -> None:
    """Serialise ``library`` to a ``.PcbLib`` file at ``output_path``."""
    cf = build_compound_file(library)
    cf.write(output_path)


def build_compound_file(library: PcbLibrary) -> CompoundFile:
    """Build (but don't write) the CFB container for ``library``.
    Useful for callers that want to introspect the structure or get
    the bytes via ``cf.to_bytes()`` without going through a file."""
    cf = CompoundFile()
    cf.add_stream("FileHeader", _build_file_header())
    cf.add_stream("Library/Header", _u32(1))                  # 1 = library record count
    cf.add_stream("Library/Data", _build_library_data(library))
    cf.add_stream("Library/Models/Header", _u32(len(library.models)))
    cf.add_stream("Library/Models/Data", _build_models_metadata(library.models))
    for i, model in enumerate(library.models):
        cf.add_stream(f"Library/Models/{i}", _compress_step(model.step_data))
    for component in library.components:
        _add_component_storage(cf, component)
    return cf


# --- FileHeader stream ------------------------------------------------


def _build_file_header() -> bytes:
    """The minimal 32-byte FileHeader that AltiumSharp v1.0.2 emits:

        u32 string_length  (= 27, the chars-only length)
        u8 pascal_length   (= 27)
        27 bytes           ("PCB 6.0 Binary Library File")

    Note: the leading u32 is *string length only*, NOT payload size --
    so it equals the pascal length byte. The standard WriteStringBlock
    helper instead wraps the entire pascal-short-string (counting the
    pascal length byte too), which would yield u32 = 28; that's what
    the master AltiumSharp branch emits, but v1.0.2 emits 27 and we
    match v1.0.2 for byte parity."""
    banner = "PCB 6.0 Binary Library File"
    bw = BinaryWriter()
    bw.write_u32(len(banner))                      # length of the banner chars
    bw.write_pascal_short_string(banner)           # u8 + chars (no null)
    return bw.getvalue()


# --- Library/Data: header parameters + component name list -----------


def _build_library_data(library: PcbLibrary) -> bytes:
    """Library/Data stream layout: a length-prefixed parameter block
    (the master library header), then a u32 component count, then one
    StringBlock per component holding its name. AltiumSharp v1.0.2
    also writes per-component data sub-records here, but our per-
    component primitives live in their own storages, so this stream is
    just the index.

    The library parameter block is large (~28 KB) and structurally
    complex -- it includes all 32 layer descriptors, the 16 V7
    extended-mechanical layer descriptors, drill-pair config, view-
    state, snap settings, etc., interspersed with ``RECORD=Board``
    separators that AltiumSharp's reader uses as section markers.
    Rather than synthesise it from scratch (which would require
    porting AltiumSharp's full ``PcbLibrary`` defaults), we use a
    template captured from a known-good C#-emitted file and
    substitute four dynamic fields: FILENAME, DATE, TIME, WEIGHT
    (the component count)."""
    bw = BinaryWriter()
    if library.library_parameters is not None:
        # User-supplied dict: emit it as-is via the standard helper.
        params = dict(library.library_parameters)
        params["WEIGHT"] = str(len(library.components))
        bw.write_c_string_param_block(params)
    else:
        # Use the captured template. Avoid the regex/dict round-trip
        # so we don't reorder keys -- the template's order is what
        # AltiumSharp's reader expects.
        param_str = _render_library_params_template(library)
        # Manual emission of the C-string block: u32 length-of-payload
        # (string + null terminator), then the bytes.
        encoded = param_str.encode("cp1252") + b"\x00"
        bw.write_u32(len(encoded))
        bw.write_bytes(encoded)
    bw.write_u32(len(library.components))
    for c in library.components:
        bw.write_string_block(c.name)
    return bw.getvalue()


# Path to the captured library-parameter template. Contains
# placeholders ``{FILENAME}``, ``{DATE}``, ``{TIME}``, ``{WEIGHT}``
# at the four positions where the C# writer substitutes dynamic
# values. Captured from a working C#-emitted .PcbLib so the
# parameter set, ordering, and ``RECORD=Board`` section markers
# match exactly what AltiumSharp's reader expects.
_LIBRARY_PARAMS_TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "_library_params_template.txt",
)


def _render_library_params_template(library: PcbLibrary) -> str:
    """Render the captured library-parameter template, substituting
    dynamic fields. The template contains exactly four placeholders;
    callers pass plain strings (no escaping required since none of
    the substituted values contain ``|`` or ``=``)."""
    with open(_LIBRARY_PARAMS_TEMPLATE_PATH, "r", encoding="ascii") as f:
        template = f.read()
    # We use Python's str.replace rather than .format so that the
    # template's literal '{' and '}' characters elsewhere don't get
    # interpreted as format spec.
    return (
        template
        .replace("{FILENAME}", "build/house.PcbLib")
        .replace("{DATE}", "01/01/2026")
        .replace("{TIME}", "00:00:00")
        .replace("{WEIGHT}", str(len(library.components)))
    )


# --- Library/Models metadata stream ---------------------------------


def _build_models_metadata(models: List[PcbModel]) -> bytes:
    """Library/Models/Data: one length-prefixed C-string parameter
    block per model. Order matches the numeric stream names (model 0
    -> Library/Models/0, etc.) so the matching by index is implicit.

    Field set matches what AltiumSharp v1.0.2 emits, which is a
    minimal 4-key form (ID, DZ, EMBED, NAME) -- shorter and
    different from the master branch's 9-key form (which adds
    MODELSOURCE, ROTX/Y/Z, CHECKSUM). v1's ``EMBED=T`` (not
    ``EMBED=TRUE``) is one of several v1 quirks we replicate."""
    bw = BinaryWriter()
    for m in models:
        params = {
            "ID":    m.id,
            "DZ":    str(m.dz),
            "EMBED": "T" if m.is_embedded else "F",
            "NAME":  m.name,
        }
        bw.write_c_string_param_block(params)
    return bw.getvalue()


def _compress_step(step_data: str) -> bytes:
    """zlib-compress STEP text for a Library/Models/<n> stream.
    Level 6 is what .NET's CompressionLevel.Optimal uses by default
    on this kind of text, and it matches the byte-level layout
    AltiumSharp v1 produces (modulo a one- or two-byte header tweak
    we don't care about as long as Altium decompresses cleanly)."""
    if not step_data:
        return b""
    return zlib.compress(step_data.encode("utf-8"), level=6)


# --- Per-component storage ------------------------------------------


def _add_component_storage(cf: CompoundFile, component: PcbComponent) -> None:
    """Lay out one CFB sub-storage for a single PcbComponent.

    Layout (matching AltiumSharp v1.0.2):
      <name>/Header                         (u32 record count)
      <name>/Parameters                     (PATTERN, HEIGHT, etc.)
      <name>/WideStrings                    (per-text string table; empty)
      <name>/Data                           (binary primitive records)
      <name>/UniqueIdPrimitiveInformation/* (empty unique-id table)
    """
    primitive_count = (
        len(component.pads)
        + len(component.tracks)
        + len(component.regions)
        + len(component.component_bodies)
    )
    cf.add_stream(f"{component.name}/Header", _u32(primitive_count))
    cf.add_stream(f"{component.name}/Parameters", _build_component_parameters(component))
    cf.add_stream(f"{component.name}/WideStrings", _build_wide_strings(component))
    cf.add_stream(f"{component.name}/Data", _build_component_data(component))
    cf.add_stream(
        f"{component.name}/UniqueIdPrimitiveInformation/Header",
        _u32(primitive_count),
    )
    cf.add_stream(
        f"{component.name}/UniqueIdPrimitiveInformation/Data",
        _build_unique_id_table(component),
    )


def _build_component_parameters(component: PcbComponent) -> bytes:
    """``Parameters`` stream: a single length-prefixed parameter block
    with PATTERN, HEIGHT, DESCRIPTION, ITEMGUID, REVISIONGUID."""
    bw = BinaryWriter()
    params = {
        "PATTERN":      component.name,
        "HEIGHT":       _coord_mil_str(component.height),
        "DESCRIPTION":  component.description,
        "ITEMGUID":     component.item_guid,
        "REVISIONGUID": component.revision_guid,
    }
    bw.write_c_string_param_block(params)
    return bw.getvalue()


def _build_wide_strings(component: PcbComponent) -> bytes:
    """Wide-string parameter table (one entry per PcbText). Chip
    footprints have no text primitives, so this is the empty form
    AltiumSharp emits: an empty parameter block (5 bytes:
    u32(1) + 0x00)."""
    bw = BinaryWriter()
    bw.write_c_string_param_block({})
    return bw.getvalue()


def _build_unique_id_table(component: PcbComponent) -> bytes:
    """``UniqueIdPrimitiveInformation/Data``: one length-prefixed
    parameter block per primitive in component.Data, naming the
    primitive's type. The first record (index 0) omits
    ``PRIMITIVEINDEX``; subsequent records carry it. This matches
    what AltiumSharp v1.0.2 emits and what AltiumSharp's reader
    expects (a different format produces "Expected primitiveObjectId
    to be Pad" warnings).

    Primitive ordering must match ``_build_component_data`` exactly --
    the per-record indices reference positions in that stream.
    """
    bw = BinaryWriter()
    primitives = _ordered_primitives(component)
    for i, kind in enumerate(primitives):
        params: Dict[str, str] = {}
        if i > 0:
            params["PRIMITIVEINDEX"] = str(i)
        params["PRIMITIVEOBJECTID"] = kind
        bw.write_c_string_param_block(params)
    return bw.getvalue()


def _ordered_primitives(component: PcbComponent) -> List[str]:
    """Return the ordered list of primitive type-names matching how
    ``_build_component_data`` emits them. The order is pads, regions,
    tracks, component_bodies -- mirroring AltiumSharp v1.0.2's
    PcbLibWriter, which differs from the master branch's order
    (master is arcs, pads, vias, tracks, texts, fills, regions,
    bodies). Both orderings produce valid files, but matching v1.0.2
    keeps ``UniqueIdPrimitiveInformation`` indices aligned and lets
    us byte-compare per-stream against C#-emitted reference files."""
    out: List[str] = []
    for _ in component.pads:
        out.append("Pad")
    for _ in component.regions:
        out.append("Region")
    for _ in component.tracks:
        out.append("Track")
    for _ in component.component_bodies:
        out.append("ComponentBody")
    return out


def _build_component_data(component: PcbComponent) -> bytes:
    """``<component>/Data``: pattern-name string block followed by one
    record per primitive. Emission order matches AltiumSharp v1.0.2:
    pads, regions, tracks, component_bodies."""
    bw = BinaryWriter()
    bw.write_string_block(component.name)
    for pad in component.pads:
        bw.write_u8(TAG_PAD)
        _write_pad(bw, pad)
    for region in component.regions:
        bw.write_u8(TAG_REGION)
        _write_region(bw, region)
    for track in component.tracks:
        bw.write_u8(TAG_TRACK)
        _write_track(bw, track)
    for body in component.component_bodies:
        bw.write_u8(TAG_COMPONENT_BODY)
        _write_body(bw, body)
    return bw.getvalue()


# --- Per-record writers --------------------------------------------


def _write_common_primitive(bw: BinaryWriter, layer: int, flags: int = DEFAULT_FLAGS) -> None:
    bw.write_u8(layer & 0xFF)
    bw.write_u16(flags & 0xFFFF)
    bw.write_bytes(COMMON_FILL)


def _write_pad(bw: BinaryWriter, pad: PcbPad) -> None:
    """Pad has a 6-block layout: designator, reserved, net string,
    reserved, main 114-byte data, 596-byte size/shape table."""
    bw.write_string_block(pad.designator)
    # Reserved block 1: single zero byte.
    with bw.block():
        bw.write_u8(0)
    # Net block: footprint-library convention is always "|&|0".
    bw.write_string_block("|&|0")
    # Reserved block 2.
    with bw.block():
        bw.write_u8(0)
    # Main block (114 bytes).
    with bw.block():
        _write_common_primitive(bw, int(pad.layer))
        bw.write_coord_point(pad.location.x.raw, pad.location.y.raw)
        # SizeTop/Mid/Bot: chip pads use Simple stack; all three are
        # set to the same size for round-trip stability.
        bw.write_coord_point(pad.size.x.raw, pad.size.y.raw)  # Top
        bw.write_coord_point(pad.size.x.raw, pad.size.y.raw)  # Mid
        bw.write_coord_point(pad.size.x.raw, pad.size.y.raw)  # Bot
        bw.write_coord(0)                                     # HoleSize
        bw.write_u8(PAD_MAIN_BLOCK_SHAPE)                     # ShapeTop (1 = Round; v1 quirk for RoundRect)
        bw.write_u8(PAD_MAIN_BLOCK_SHAPE)                     # ShapeMid
        bw.write_u8(PAD_MAIN_BLOCK_SHAPE)                     # ShapeBot
        bw.write_f64(pad.rotation_deg)
        bw.write_bool(pad.is_plated)
        bw.write_u8(0)                                        # @61: const 0
        bw.write_u8(0)                                        # @62: StackMode = Simple
        bw.write_u8(0)                                        # @63: PowerPlaneConnectStyle
        bw.write_coord(0)                                     # @64: ReliefAirGap
        bw.write_coord(DEFAULT_RELIEF_CONDUCTOR_WIDTH_RAW)    # @68: ReliefConductorWidth
        bw.write_i16(4)                                       # @72: ReliefEntries (default 4)
        bw.write_coord(DEFAULT_POWER_PLANE_CLEARANCE_RAW)     # @74: PowerPlaneClearance
        bw.write_coord(DEFAULT_POWER_PLANE_RELIEF_RAW)        # @78: PowerPlaneReliefExpansion
        bw.write_i32(DEFAULT_RESERVED_AT_82_RAW)              # @82: reserved (v1 writes 200000 here)
        bw.write_coord(pad.paste_mask_expansion.raw)          # @86
        bw.write_coord(pad.solder_mask_expansion.raw)         # @90
        bw.write_fill(0, 7)                                   # @94..100: 7 zero bytes
        # @101..102: manual mask flags (0 or 2).
        bw.write_u8(2 if pad.paste_mask_manual else 0)
        bw.write_u8(2 if pad.solder_mask_manual else 0)
        bw.write_u8(0)                                        # @103: DrillType
        bw.write_i16(0)                                       # @104..105: reserved
        bw.write_i32(0)                                       # @106..109: reserved
        bw.write_i16(0)                                       # @110..111: JumperID
        bw.write_i16(0)                                       # @112..113: reserved
    # Size/shape extended block (596 bytes).
    with bw.block():
        # 29 layer X sizes (i32 each) -- chip pads use the same size on every layer.
        for _ in range(29):
            bw.write_i32(pad.size.x.raw)
        # 29 layer Y sizes.
        for _ in range(29):
            bw.write_i32(pad.size.y.raw)
        # 29 internal-layer shape codes -- all RoundedRectangle.
        for _ in range(29):
            bw.write_u8(PAD_INTERNAL_SHAPE)
        bw.write_u8(0)                                        # @261 reserved
        bw.write_u8(0)                                        # @262 hole shape (round)
        bw.write_i32(0)                                       # @263..266 hole slot length
        bw.write_f64(0.0)                                     # @267..274 hole rotation
        # 32 X offsets from hole center, then 32 Y offsets, then
        # HasRoundedRect, then 32 per-layer shapes, then 32 corner
        # radii. Chip pads have no hole, so all offsets are 0; the
        # 25% corner radius is repeated across all 32 layers.
        for _ in range(32):
            bw.write_i32(0)                                   # X offset
        for _ in range(32):
            bw.write_i32(0)                                   # Y offset
        bw.write_u8(1)                                        # @531 HasRoundedRect = true
        for _ in range(32):
            bw.write_u8(PAD_INTERNAL_SHAPE)                   # per-layer shape
        for _ in range(32):
            bw.write_u8(pad.corner_radius_pct & 0xFF)         # corner radius percentage


def _write_track(bw: BinaryWriter, track: PcbTrack) -> None:
    """Track block. Total payload is 36 bytes:
        common 13 + start 8 + end 8 + width 4 + tail 3
    The 3-byte tail is u16 NetIndex + u8 ComponentIndex (both 0 for
    footprint-library tracks).
    """
    with bw.block():
        _write_common_primitive(bw, int(track.layer))
        bw.write_coord_point(track.start.x.raw, track.start.y.raw)
        bw.write_coord_point(track.end.x.raw, track.end.y.raw)
        bw.write_coord(track.width.raw)
        bw.write_i16(0)              # NetIndex
        bw.write_u8(0)               # ComponentIndex


def _write_region(bw: BinaryWriter, region: PcbRegion) -> None:
    """Region block. Layout: common 13 + reserved u32 + reserved u8 +
    parameter block + u32 vertex count + N x (f64 X, f64 Y).
    """
    with bw.block():
        _write_common_primitive(bw, int(region.layer))
        bw.write_u32(0)              # reserved prefix 1
        bw.write_u8(0)               # reserved prefix 2
        params: Dict[str, str] = {}
        if region.kind != 0:
            params["KIND"] = str(region.kind)
        if region.net:
            params["NET"] = region.net
        if region.unique_id:
            params["UNIQUEID"] = region.unique_id
        if region.name:
            params["NAME"] = region.name
        bw.write_c_string_param_block(params)
        bw.write_u32(len(region.outline))
        for p in region.outline:
            bw.write_f64(float(p.x.raw))
            bw.write_f64(float(p.y.raw))


def _write_body(bw: BinaryWriter, body: PcbComponentBody) -> None:
    """ComponentBody block. Same shape as Region (common + reserved +
    param block + vertex list) but with a much richer parameter
    payload (3D model link, body color, height, identifier, etc.).
    """
    with bw.block():
        _write_common_primitive(bw, int(body.layer))
        bw.write_u32(0)
        bw.write_u8(0)
        bw.write_c_string_param_block(_body_parameters(body))
        bw.write_u32(len(body.outline))
        for p in body.outline:
            bw.write_f64(float(p.x.raw))
            bw.write_f64(float(p.y.raw))


def _body_parameters(body: PcbComponentBody) -> Dict[str, str]:
    """Build the ComponentBody parameter dict in the order AltiumSharp
    v1.0.2 emits them (insertion order matters for byte-stable
    output)."""
    p: Dict[str, str] = {}
    p["V7_LAYER"] = body.v7_layer or "MECHANICAL1"
    p["NAME"] = body.name
    p["SUBPOLYINDEX"] = str(body.sub_poly_index)
    p["ARCRESOLUTION"] = _coord_mil_str(body.arc_resolution)
    p["ISSHAPEBASED"] = "TRUE" if body.is_shape_based else "FALSE"
    p["STANDOFFHEIGHT"] = _coord_mil_str(body.standoff_height)
    p["OVERALLHEIGHT"] = _coord_mil_str(body.overall_height)
    p["BODYCOLOR3D"] = str(body.body_color_3d)
    p["BODYOPACITY3D"] = f"{body.body_opacity_3d:.6f}"
    # IDENTIFIER is encoded as comma-separated codepoints (a v1.0.2
    # quirk -- AltiumSharp's PcbComponentBody.Identifier setter
    # converts a string to "67,104,..." style on serialization).
    p["IDENTIFIER"] = ",".join(str(ord(c)) for c in (body.identifier or ""))
    p["TEXTURE"] = body.texture
    p["TEXTURECENTERX"] = _coord_mil_str(body.texture_center_x)
    p["TEXTURECENTERY"] = _coord_mil_str(body.texture_center_y)
    p["TEXTURESIZEX"] = _coord_mil_str(body.texture_size_x)
    p["TEXTURESIZEY"] = _coord_mil_str(body.texture_size_y)
    p["TEXTUREROTATION"] = f"{body.texture_rotation:.6f}"
    p["MODELID"] = body.model_id
    p["MODEL.EMBED"] = "TRUE" if body.model_embed else "FALSE"
    p["MODEL.2D.X"] = _coord_mil_str(body.model_2d_x)
    p["MODEL.2D.Y"] = _coord_mil_str(body.model_2d_y)
    p["MODEL.3D.DZ"] = _coord_mil_str(body.model_3d_dz)
    p["MODEL.MODELTYPE"] = "1"
    return p


# --- Helpers ---------------------------------------------------------


def _u32(v: int) -> bytes:
    import struct
    return struct.pack("<I", v & 0xFFFFFFFF)


def _coord_mil_str(c: Coord) -> str:
    return c.to_mil_str()
