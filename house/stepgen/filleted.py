"""
Filleted-box B-rep generator with optional flat ends along the X axis.

A box ``[xmin..xmax] × [ymin..ymax] × [zmin..zmax]`` can be requested with
each X-end face independently set to either:

    * ``filleted`` (default) -- the L-end face is shrunk inward by ``r``
      and surrounded by 4 cylindrical fillets + 4 spherical corner
      octants. Same shape Open CASCADE produces for a fully-rounded
      box.
    * ``flat`` -- the L-end face stays at full ``W × H`` but its
      corners are replaced by 4 quarter-arcs (the X-axis cylinders
      end at the L-end plane). The resulting face has 4 line edges +
      4 arcs alternating around its boundary, like a rectangle with
      concave-rounded corners.

This second mode is what we use at the **body / terminal junction** of
chip components: the body has both X-ends flat, each terminal has its
inner end flat (and outer end filleted). Body + terminal share the
same flat-corner shape at the junction so they meet flush -- no
visible "double bevel" ridge.

Topology summary:

    * Long edges (along the **X axis**) are always filleted with a
      cylindrical fillet of radius ``r``. There are 4 of them, one
      per (sy, sz) corner.
    * Short edges (along **Y** or **Z**) are filleted **only if both
      adjacent main faces are filleted**. If either is flat, the
      short edge is a sharp line. For the chip use case Y- and
      Z-faces are always filleted, so a Y/Z edge is filleted iff its
      X-end is filleted.
    * Spherical corner octants exist only at corners where **all three
      adjacent faces are filleted**. Mixed corners (one or more flat
      faces) have no octant -- the X-axis cylinder there ends at the
      flat L-end plane with a quarter-arc cross-section.

The math for cylinder/sphere placements, vertex positions and arc
parameter directions is identical to the original fully-filleted
implementation; only the *which entities to emit* is gated by the
flat-end flags.

Coordinate frame conventions (same as ``shapes.py``):

    sx, sy, sz ∈ {-1, +1}    -- corner signs along X, Y, Z
    axis ∈ {0, 1, 2}         -- 0=X, 1=Y, 2=Z
    For a cylinder along axis ``a``, perp axes are ``b = (a+1)%3``,
    ``c = (a+2)%3``. (a, b, c) is right-handed: e_a × e_b = e_c.

This file deliberately does **not** emit ``PCURVE`` /
``SURFACE_CURVE`` parametric-curve-on-surface entries -- ``EDGE_CURVE``
references the 3D ``LINE`` or ``CIRCLE`` directly. Open CASCADE-based
readers (Altium, FreeCAD, KiCad's StepUp) accept this; if a future
reader needs the verbose form, see ``house/step/*.step`` reference
files for the layout.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Tuple

from .doc import StepDoc, Vec3

#: Default fillet radius (matches Altium IPC LP Wizard for chip
#: components). Always clamped per-call to ``min(L, W, H) / 4``.
DEFAULT_FILLET_RADIUS_MM = 0.05


# ---------------------------------------------------------------------------
# Coordinate / sign helpers
# ---------------------------------------------------------------------------

# Box bounds, packed as (xmin, ymin, zmin, xmax, ymax, zmax).
_Bounds = Tuple[float, float, float, float, float, float]
# (axis, sign) pair identifying a face (axis 0/1/2, sign -1/+1).
_FaceKey = Tuple[int, int]


def _face_coord(bounds: _Bounds, axis: int, sign: int) -> float:
    """World coordinate of the box's main face perpendicular to
    ``axis`` at ``sign``."""
    return bounds[axis] if sign < 0 else bounds[3 + axis]


def _inner_coord(bounds: _Bounds, axis: int, sign: int, r: float) -> float:
    """World coordinate of the corner sphere centre's component along
    ``axis`` for a corner at sign ``sign`` along ``axis`` -- the face
    coordinate pulled inward by ``r``."""
    return _face_coord(bounds, axis, sign) - sign * r


def _signs_to_xyz(axis: int, sa: int, sb: int, sc: int) -> Tuple[int, int, int]:
    """Given signs along ``(a, b, c) = (axis, (axis+1)%3, (axis+2)%3)``,
    return the (sx, sy, sz) sign tuple."""
    s = [0, 0, 0]
    s[axis] = sa
    s[(axis + 1) % 3] = sb
    s[(axis + 2) % 3] = sc
    return (s[0], s[1], s[2])


def _unit_along(axis: int, sign: int = +1) -> Vec3:
    """Unit vector along ``axis`` with the given sign."""
    v = [0.0, 0.0, 0.0]
    v[axis] = float(sign)
    return (v[0], v[1], v[2])


# ---------------------------------------------------------------------------
# Topology rules (driven by `flat_ends`)
# ---------------------------------------------------------------------------


def _is_flat(flat_ends: FrozenSet[_FaceKey], axis: int, sign: int) -> bool:
    return (axis, sign) in flat_ends


def _cylinder_exists(flat_ends: FrozenSet[_FaceKey], axis: int, sb: int, sc: int) -> bool:
    """A cylinder along ``axis`` at perp signs (sb, sc) exists iff both
    adjacent main faces are filleted."""
    b = (axis + 1) % 3
    c = (axis + 2) % 3
    return not _is_flat(flat_ends, b, sb) and not _is_flat(flat_ends, c, sc)


def _corner_has_sphere(flat_ends: FrozenSet[_FaceKey], sx: int, sy: int, sz: int) -> bool:
    """A corner has a sphere octant iff all 3 adjacent faces are
    filleted."""
    return (
        not _is_flat(flat_ends, 0, sx)
        and not _is_flat(flat_ends, 1, sy)
        and not _is_flat(flat_ends, 2, sz)
    )


def _short_edge_is_sharp(
    flat_ends: FrozenSet[_FaceKey],
    axis: int,
    sb: int,
    sc: int,
) -> bool:
    """The "short" edge (along the box's ``axis`` direction) at perp
    signs (sb, sc) is a sharp line (not replaced by a cylinder) iff
    its corresponding cylinder doesn't exist."""
    return not _cylinder_exists(flat_ends, axis, sb, sc)


# ---------------------------------------------------------------------------
# Vertex positions
# ---------------------------------------------------------------------------
#
# A vertex sits at the intersection of:
#   * one main face plane (face_axis perpendicular to the face)
#   * up to 2 cylinder fillets (along the perpendicular axes)
#   * 0 or 1 corner sphere octants (depends on whether the corner is
#     full-fillet)
#
# Position decomposes per-axis:
#   * Along ``face_axis``: always at the face coordinate.
#   * Along the other 2 axes ``k``: at ``inner_coord`` if the k-end
#     at this corner is filleted, else at the face coordinate.
#
# When the k-end at this corner is *flat*, the cylinder along the
# remaining axis (perpendicular to both face_axis and k) terminates
# at the flat L-end plane rather than at a sphere. Our vertex is the
# tangent point on that L-end, so the k-coordinate is the face coord,
# not the inner coord.


def _vertex_pos(
    bounds: _Bounds,
    sx: int, sy: int, sz: int,
    face_axis: int,
    r: float,
    flat_ends: FrozenSet[_FaceKey],
) -> Vec3:
    s = (sx, sy, sz)
    out = [0.0, 0.0, 0.0]
    for k in range(3):
        if k == face_axis:
            out[k] = _face_coord(bounds, k, s[k])
        elif _is_flat(flat_ends, k, s[k]):
            out[k] = _face_coord(bounds, k, s[k])
        else:
            out[k] = _inner_coord(bounds, k, s[k], r)
    return (out[0], out[1], out[2])


def _vertex_exists(
    flat_ends: FrozenSet[_FaceKey],
    sx: int, sy: int, sz: int,
    face_axis: int,
) -> bool:
    """A vertex on the ``face_axis`` face at corner (sx, sy, sz) exists
    iff that face is filleted (otherwise the perimeter is sharp and
    the vertex would coincide with a sharp box corner that doesn't
    appear in our topology)."""
    sign = (sx, sy, sz)[face_axis]
    return not _is_flat(flat_ends, face_axis, sign)


def _emit_vertices(
    doc: StepDoc,
    bounds: _Bounds,
    r: float,
    flat_ends: FrozenSet[_FaceKey],
) -> Dict[Tuple[int, int, int, int], int]:
    """Emit all vertices that exist for the given flat_ends. Returns
    a dict keyed by (sx, sy, sz, face_axis)."""
    vp: Dict[Tuple[int, int, int, int], int] = {}
    for sx in (-1, +1):
        for sy in (-1, +1):
            for sz in (-1, +1):
                for face_axis in (0, 1, 2):
                    if not _vertex_exists(flat_ends, sx, sy, sz, face_axis):
                        continue
                    pos = _vertex_pos(bounds, sx, sy, sz, face_axis, r, flat_ends)
                    vp[(sx, sy, sz, face_axis)] = doc.vertex_point(doc.cartesian_point(pos))
    return vp


# ---------------------------------------------------------------------------
# Line edges
# ---------------------------------------------------------------------------
#
# Two kinds of line edges:
#
#   1. *Cylinder tangent lines*: where a cylinder fillet meets one of
#      its 2 adjacent main faces. Each existing cylinder contributes 2.
#      Key: (axis, sb, sc, tangent_face_axis) where tangent_face_axis
#      is one of (b, c).
#
#   2. *Sharp perimeter lines*: where two main faces meet directly
#      because the cylinder that would have replaced their shared
#      edge doesn't exist (one or both adjacent main faces is flat).
#      These lie around flat L-end face perimeters. Key:
#      (axis, sb, sc) -- analogous to a cylinder identifier but the
#      cylinder doesn't exist.
#
# Both line conventions: edge_curve runs from sa=-1 to sa=+1 along
# axis ``a``, length is determined by the actual vertex positions
# (which depend on whether each end is filleted or flat).


def _emit_line_edges(
    doc: StepDoc,
    vertices: Dict[Tuple[int, int, int, int], int],
    bounds: _Bounds,
    r: float,
    flat_ends: FrozenSet[_FaceKey],
) -> Tuple[Dict[Tuple[int, int, int, int], int], Dict[Tuple[int, int, int], int]]:
    """Emit all line edges. Returns (cylinder_tangent_lines, sharp_perimeter_lines).

    cylinder_tangent_lines key: (cylinder_axis, sb, sc, tangent_face_axis)
    sharp_perimeter_lines  key: (edge_axis, sb, sc)
    """
    cyl_tangents: Dict[Tuple[int, int, int, int], int] = {}
    sharp_lines: Dict[Tuple[int, int, int], int] = {}

    for axis in range(3):
        b = (axis + 1) % 3
        c = (axis + 2) % 3
        for sb in (-1, +1):
            for sc in (-1, +1):
                if _cylinder_exists(flat_ends, axis, sb, sc):
                    # Two tangent lines: one with the b-face, one with the c-face.
                    for tangent_face_axis in (b, c):
                        start_xyz = _signs_to_xyz(axis, -1, sb, sc)
                        end_xyz   = _signs_to_xyz(axis, +1, sb, sc)
                        v_start = vertices[(*start_xyz, tangent_face_axis)]
                        v_end   = vertices[(*end_xyz,   tangent_face_axis)]
                        # Length from actual positions (depends on flat ends).
                        p_start = _vertex_pos(bounds, *start_xyz, tangent_face_axis, r, flat_ends)
                        p_end   = _vertex_pos(bounds, *end_xyz,   tangent_face_axis, r, flat_ends)
                        length  = abs(p_end[axis] - p_start[axis])
                        line_id = doc.make_line(
                            origin=p_start,
                            direction=_unit_along(axis),
                            magnitude=length,
                        )
                        ec = doc.edge_curve(v_start, v_end, line_id, same_sense=True)
                        cyl_tangents[(axis, sb, sc, tangent_face_axis)] = ec
                else:
                    # Sharp perimeter line. The two adjacent faces meet at
                    # a sharp corner along ``axis``. The line connects the
                    # two corner-vertices on that shared sharp corner.
                    #
                    # The shared edge runs from corner (sa=-1, sb, sc)
                    # to corner (sa=+1, sb, sc). The line lies on the
                    # intersection of the two adjacent faces and goes
                    # between the two cylinder-tangent vertices on this
                    # shared edge -- specifically, the vertex on the
                    # b-face (or equivalently the c-face) of each
                    # corner. The two endpoint vertices must exist;
                    # they do because we emit the b-face and c-face
                    # vertices unless their face is flat, and at a
                    # sharp short edge AT LEAST ONE of {b-face, c-face}
                    # is filleted (otherwise both faces would be flat
                    # and the edge would be a degenerate sharp box
                    # corner with no tangent reference).
                    #
                    # We pick whichever vertex exists -- prefer the
                    # b-face vertex if it does, else the c-face vertex.
                    #
                    # In the chip-component flat_ends pattern (only
                    # X-ends ever flat), this sharp-line case only
                    # arises when the X-face at this corner is flat
                    # AND axis ∈ {Y, Z}. Then b or c is X (the flat
                    # face) and the other is Y or Z (always filleted).
                    # The vertex on the FILLETED face exists, the
                    # vertex on the FLAT face doesn't -- so we always
                    # pick the filleted-face vertex.
                    pick_face = b if not _is_flat(flat_ends, b, sb) else c
                    start_xyz = _signs_to_xyz(axis, -1, sb, sc)
                    end_xyz   = _signs_to_xyz(axis, +1, sb, sc)
                    v_start = vertices[(*start_xyz, pick_face)]
                    v_end   = vertices[(*end_xyz,   pick_face)]
                    p_start = _vertex_pos(bounds, *start_xyz, pick_face, r, flat_ends)
                    p_end   = _vertex_pos(bounds, *end_xyz,   pick_face, r, flat_ends)
                    length  = abs(p_end[axis] - p_start[axis])
                    line_id = doc.make_line(
                        origin=p_start,
                        direction=_unit_along(axis),
                        magnitude=length,
                    )
                    ec = doc.edge_curve(v_start, v_end, line_id, same_sense=True)
                    sharp_lines[(axis, sb, sc)] = ec
    return cyl_tangents, sharp_lines


# ---------------------------------------------------------------------------
# Arc edges
# ---------------------------------------------------------------------------
#
# Each existing cylinder contributes 2 arc edges, one at each axial
# end. Both kinds share the same emission convention:
#
#   * Arc lies in the plane perpendicular to the cylinder's axis at
#     the cylinder's near-end coordinate.
#   * Arc connects b-face vertex -> c-face vertex (parameter 0 -> π/2).
#   * CIRCLE placement: Z-axis along ``axis`` with sign sb*sc; X-axis
#     along axis ``b`` with sign sb. (Same as original implementation.)
#
# The only difference for "flat-end" cases: the arc's centre is at
# face_coord(axis, sa) instead of inner_coord(axis, sa, r), because
# the cylinder ends at the L-end plane rather than at a sphere centre.
# This is captured by ``_vertex_pos`` -- the b- and c-face vertices'
# axis-component shift to the face coord -- so as long as we use
# those vertex positions to locate the centre, we're fine.


def _arc_centre(
    bounds: _Bounds,
    axis: int, sa: int, sb: int, sc: int,
    r: float,
    flat_ends: FrozenSet[_FaceKey],
) -> Vec3:
    """Centre of the arc on the corner sphere for the cylinder along
    ``axis`` ending at corner (sa, sb, sc). Lies in the plane
    perpendicular to ``axis`` at the cylinder's end coordinate."""
    b = (axis + 1) % 3
    c = (axis + 2) % 3
    out = [0.0, 0.0, 0.0]
    out[axis] = (
        _face_coord(bounds, axis, sa)
        if _is_flat(flat_ends, axis, sa)
        else _inner_coord(bounds, axis, sa, r)
    )
    out[b] = _inner_coord(bounds, b, sb, r)
    out[c] = _inner_coord(bounds, c, sc, r)
    return (out[0], out[1], out[2])


def _emit_arc_edges(
    doc: StepDoc,
    vertices: Dict[Tuple[int, int, int, int], int],
    bounds: _Bounds,
    r: float,
    flat_ends: FrozenSet[_FaceKey],
) -> Dict[Tuple[int, int, int, int], int]:
    """Emit all arc edges for cylinders that exist."""
    arcs: Dict[Tuple[int, int, int, int], int] = {}
    for axis in range(3):
        b = (axis + 1) % 3
        c = (axis + 2) % 3
        for sb in (-1, +1):
            for sc in (-1, +1):
                if not _cylinder_exists(flat_ends, axis, sb, sc):
                    continue
                for sa in (-1, +1):
                    corner_xyz = _signs_to_xyz(axis, sa, sb, sc)
                    v_b = vertices[(*corner_xyz, b)]
                    v_c = vertices[(*corner_xyz, c)]
                    centre = _arc_centre(bounds, axis, sa, sb, sc, r, flat_ends)
                    z_dir = _unit_along(axis, sb * sc)
                    x_dir = _unit_along(b, sb)
                    axis_id = doc.make_axis(centre, z_dir, x_dir)
                    circle_id = doc.circle(axis_id, r)
                    ec = doc.edge_curve(v_b, v_c, circle_id, same_sense=True)
                    arcs[(axis, sa, sb, sc)] = ec
    return arcs


# ---------------------------------------------------------------------------
# Main face planes
# ---------------------------------------------------------------------------
#
# A main face's edge loop topology depends on whether it's filleted or
# flat:
#
#   * **Filleted** main face: 4 cylinder-tangent line edges around the
#     perimeter (one per adjacent cylinder), all 4 tangent lines lying
#     in the face plane and connecting at the 4 vertices on the face.
#     CCW from outside.
#
#   * **Flat** main face: 8 edges alternating line-arc-line-arc...
#     The 4 lines are the sharp perimeter edges that border this face
#     (along the 4 "short" axes for this face's axis); the 4 arcs are
#     the X-axis cylinder ends (each is a quarter-arc on this plane).
#     CCW from outside.
#
# In our chip-component setup, the FLAT case only happens for X-axis
# faces. Y- and Z-axis faces are always filleted. The implementation
# below is general enough that flat Y- or Z-axis faces would also work
# (e.g. for a future "rod with capped ends along Y" use case), but
# untested for that.


def _emit_filleted_main_face(
    doc: StepDoc,
    cyl_tangents: Dict[Tuple[int, int, int, int], int],
    sharp_lines: Dict[Tuple[int, int, int], int],
    bounds: _Bounds,
    face_axis: int,
    sign: int,
    flat_ends: FrozenSet[_FaceKey],
) -> int:
    """Emit one filleted main face. 4 line edges in CCW order around
    the perimeter -- some may be cylinder tangents, others sharp
    perimeter lines, depending on which adjacent cylinders exist.

    On a fully-filleted box the 4 boundary lines are all cylinder
    tangents (sphere octants at the 4 corners). On a partially-flat
    box, edges that would have been adjacent to a "missing" cylinder
    (one whose other perp axis is in ``flat_ends``) become sharp
    perimeter lines instead. Either kind has the same start/end
    vertex format and the same edge_curve direction (sa=-1 -> sa=+1),
    so the boundary orientation logic below is identical for both."""
    b = (face_axis + 1) % 3
    c = (face_axis + 2) % 3

    # 4 line edges around this face. Some are cylinder tangents, some
    # are sharp perimeter lines -- decide per-edge by checking whether
    # the corresponding cylinder exists.
    #
    # line_b_at(sc_face): the line at b-axis direction on this face, at
    # the c-axis sign sc_face. Corresponds to:
    #   * cyl_tangents[(b, sc_face, sign, face_axis)] -- cylinder along
    #     axis b at perp signs (sb_of_cyl=sc_face, sc_of_cyl=sign).
    #     Exists iff (c, sc_face) and (face_axis, sign) NOT in flat_ends.
    #   * sharp_lines[(b, sc_face, sign)] -- the same edge as a sharp
    #     line when the cylinder doesn't exist.
    # face_axis face is filleted (we wouldn't be here otherwise), so the
    # only check is whether (c, sc_face) is flat.
    def line_b_at(sc_face: int) -> int:
        if not _is_flat(flat_ends, c, sc_face):
            return cyl_tangents[(b, sc_face, sign, face_axis)]
        return sharp_lines[(b, sc_face, sign)]

    def line_c_at(sb_face: int) -> int:
        if not _is_flat(flat_ends, b, sb_face):
            return cyl_tangents[(c, sign, sb_face, face_axis)]
        return sharp_lines[(c, sign, sb_face)]

    if sign > 0:
        boundary = [
            (line_b_at(-1),  True),
            (line_c_at(+1),  True),
            (line_b_at(+1),  False),
            (line_c_at(-1),  False),
        ]
    else:
        boundary = [
            (line_b_at(+1),  True),
            (line_c_at(+1),  False),
            (line_b_at(-1),  False),
            (line_c_at(-1),  True),
        ]

    oriented = [doc.oriented_edge(line_id, fwd) for (line_id, fwd) in boundary]
    loop = doc.edge_loop(oriented)
    bound = doc.face_bound(loop, True)

    # Plane axis: outward normal = sign * e_face_axis; X-axis along +b.
    plane_origin = (
        _face_coord(bounds, 0, +1) if face_axis == 0 and sign > 0 else _face_coord(bounds, 0, -1),
        _face_coord(bounds, 1, +1) if face_axis == 1 and sign > 0 else _face_coord(bounds, 1, -1),
        _face_coord(bounds, 2, +1) if face_axis == 2 and sign > 0 else _face_coord(bounds, 2, -1),
    )
    plane_axis = doc.make_axis(
        origin=plane_origin,
        z_dir=_unit_along(face_axis, sign),
        x_dir=_unit_along(b, +1),
    )
    plane_id = doc.plane(plane_axis)
    return doc.advanced_face([bound], plane_id, True)


def _emit_flat_main_face(
    doc: StepDoc,
    sharp_lines: Dict[Tuple[int, int, int], int],
    arc_edges: Dict[Tuple[int, int, int, int], int],
    bounds: _Bounds,
    face_axis: int,
    sign: int,
) -> int:
    """Emit one flat main face. 8 edges: 4 sharp perimeter lines +
    4 quarter-arcs (cylinder ends) alternating CCW from outside.

    Only valid for face_axis = 0 (X-axis) in the chip-component
    pattern, but the algorithm is general."""
    a = face_axis
    b = (a + 1) % 3
    c = (a + 2) % 3

    # The 4 short edges around this flat face are along axes b and c:
    #   * along b (varies sb), at sc=+/-1 (the c-axis sign)
    #   * along c (varies sc), at sb=+/-1
    #
    # Sharp-line keys: (edge_axis, sb_of_edge, sc_of_edge) where the
    # edge runs along edge_axis and (sb_of_edge, sc_of_edge) are the
    # signs along the two perpendicular axes.
    #
    # For an edge along b on this face_axis-face: edge_axis = b,
    # sb_of_edge is along (b+1)%3 = c, sc_of_edge is along (b+2)%3 = a.
    # We're on this face_axis face so sc_of_edge = sign.
    # Free index: sb_of_edge ranges over c (so it's the c-axis sign on
    # this face).
    # -> sharp_lines[(b, c_face_sign, sign)]
    #
    # For an edge along c on this face_axis-face: edge_axis = c,
    # sb_of_edge along a = sign, sc_of_edge along b.
    # -> sharp_lines[(c, sign, b_face_sign)]
    line_b = lambda c_face_sign: sharp_lines[(b, c_face_sign, sign)]
    line_c = lambda b_face_sign: sharp_lines[(c, sign, b_face_sign)]

    # The 4 corner arcs are X-axis cylinder ends at the 4 (sb, sc)
    # combinations of this face. For face_axis = 0, X is the only
    # axis at this face's perpendicular; the cylinders along X are
    # what end here.
    #
    # For face_axis = 0, the cylinders along X have axis_b = Y, axis_c = Z.
    # An X-cyl at (sy, sz) ends at this face (sx = sign) with arc keyed
    # (axis=0, sa=sign, sb=sy, sc=sz).
    #
    # For face_axis = 1 (Y face), the cylinders ending here are along Y
    # (so axis_b = Z, axis_c = X). Generically: cylinders along axis
    # ``a`` end at the face. Arc key: (axis=a, sa=sign, sb_of_cyl, sc_of_cyl).
    # Free indices are the 2 perpendicular axes.
    arc_at = lambda sb_of_cyl, sc_of_cyl: arc_edges[(a, sign, sb_of_cyl, sc_of_cyl)]

    # Walk CCW from outside (looking from +sign * e_a back toward
    # origin). With the face's b-axis to our right and c-axis up
    # (right-hand rule), CCW order visits the corners in:
    #
    #   sign>0  (looking from +a back to origin, b right, c up):
    #     CCW = (b-, c-) -> (b+, c-) -> (b+, c+) -> (b-, c+) -> back
    #   sign<0  (looking from -a back to origin, b LEFT, c up because
    #            we look the OPPOSITE way):
    #     CCW = (b-, c-) -> (b-, c+) -> (b+, c+) -> (b+, c-) -> back
    #
    # Each corner contributes 1 arc + 1 outgoing line. Order at a
    # corner (sb, sc): "arrive on incoming-line, traverse arc, depart
    # on outgoing-line".
    #
    # For sign>0, walking CCW the corner visits look like:
    #   (b-, c-) arc: arc_at(-1, -1), goes from b-vertex -> c-vertex.
    #     Going (b-, c-) -> (b+, c-) we want the arc to end pointing
    #     toward +b. The arc goes b-vertex (= (b_face=b-)) -> c-vertex
    #     (= (c_face=c-)). That ends at the c-face line -- which is
    #     line_c(sb=-1) -- a line on the b=- side of the face. Hmm.
    #
    # Let me just enumerate by looking at vertex positions for face_axis=0,
    # sign=-1 (the typical body box -X face), in (Y, Z) coordinates:
    #
    #   arc at (sy=-1, sz=-1): connects Y-tangent vertex (xmin, ymin, zmin+r)
    #                                -> Z-tangent vertex (xmin, ymin+r, zmin)
    #     In (Y, Z): (ymin, zmin+r) -> (ymin+r, zmin). This arc traverses
    #     from "left side" to "bottom side" of the face -- i.e. cuts
    #     the bottom-left corner.
    #
    #   line_c(sb=-1) (along c=Z, on the b=Y face's left side, sb=Y=-1):
    #     This is the Z-axis sharp edge at sx=face_sign, sy=-1.
    #     Its endpoints are Y-tangent vertices on this face: from
    #     (xmin, ymin, zmin+r) [bottom-left in Y/Z] to (xmin, ymin, zmax-r)
    #     [top-left]. Walks +Z.
    #
    #   line_b(sc=+1) (along b=Y at c=Z=+1, top of face):
    #     Z-axis tangent vertex at sy=-1 sz=+1 = (xmin, ymin+r, zmax)
    #     to sy=+1 sz=+1 = (xmin, ymax-r, zmax). Walks +Y.
    #
    # So a CCW traversal from outside (sign<0 means looking from -X
    # toward +X, with Y as visual *left* and Z up: walking CCW means
    # going "up the left, across the top, down the right, along the
    # bottom" but we have to FLIP the b axis because we look from -X):
    #
    # Easier: just enumerate the corners in CCW order for the chosen
    # sign, list (incoming-edge, arc-at-corner) pairs, and trust that
    # the arc edge goes b-vertex -> c-vertex which we orient
    # appropriately at each corner.

    # For face_axis == 0 (X face) the analysis above was for sign=-1;
    # by symmetry sign=+1 reverses orientation. Generalised below for
    # any face_axis (a) using the same right-hand-rule logic.
    if sign > 0:
        # CCW corners (b, c) order: (-,-) -> (+,-) -> (+,+) -> (-,+).
        # At each corner we traverse: arc (from b-vertex to c-vertex,
        # orientation depends on whether arc start matches incoming
        # edge end), then the outgoing line.
        corner_order = [(-1, -1), (+1, -1), (+1, +1), (-1, +1)]
    else:
        # For sign<0 the outward normal flips; CCW order reverses on
        # the (b, c) plane. This corresponds to walking the
        # (-,-) -> (-,+) -> (+,+) -> (+,-) sequence.
        corner_order = [(-1, -1), (-1, +1), (+1, +1), (+1, -1)]

    edges_out: List[int] = []
    for i, (sb, sc) in enumerate(corner_order):
        # Determine incoming line direction at this corner:
        # if the previous corner had different sb, the incoming line
        # was along axis b; if different sc, along axis c.
        prev_sb, prev_sc = corner_order[(i - 1) % 4]
        next_sb, next_sc = corner_order[(i + 1) % 4]

        # The arc at this corner connects b-vertex (which is on the
        # b-face at this sb) to c-vertex (on the c-face at this sc).
        # Walking CCW *into* this corner along the line along ``axis``
        # changes one of (sb, sc); when we arrive we're at one of the
        # arc's endpoints.
        #
        #   * If arrived from the b-vertex side (incoming was a c-line,
        #     sc changed): the arc start at b-vertex is correct. Use
        #     orientation .T. (b->c direction).
        #   * If arrived from the c-vertex side (incoming was a b-line,
        #     sb changed): arc start is at c-vertex, traverse reversed
        #     to b-vertex. Orientation .F.
        arc_id = arc_at(sb, sc)
        incoming_changed_sb = (prev_sb != sb)
        if incoming_changed_sb:
            # Incoming is a b-axis line -> arrives at c-vertex.
            edges_out.append(doc.oriented_edge(arc_id, False))
        else:
            # Incoming is a c-axis line -> arrives at b-vertex.
            edges_out.append(doc.oriented_edge(arc_id, True))

        # Outgoing line: it's a b-axis line at sc=this sc (if sb
        # changes between this corner and next), or a c-axis line at
        # sb=this sb (if sc changes).
        outgoing_changes_sb = (next_sb != sb)
        if outgoing_changes_sb:
            # b-axis line at sc=sc. The line edge's natural direction
            # is sa=-1 -> sa=+1 along axis b. We need to walk from
            # this corner's sb (current) to next corner's sb. Forward
            # (+b direction) iff next_sb > sb.
            line_id = line_b(sc)
            fwd = (next_sb > sb)
            edges_out.append(doc.oriented_edge(line_id, fwd))
        else:
            line_id = line_c(sb)
            fwd = (next_sc > sc)
            edges_out.append(doc.oriented_edge(line_id, fwd))

    loop = doc.edge_loop(edges_out)
    bound = doc.face_bound(loop, True)

    plane_origin = (
        _face_coord(bounds, 0, +1) if face_axis == 0 and sign > 0 else _face_coord(bounds, 0, -1),
        _face_coord(bounds, 1, +1) if face_axis == 1 and sign > 0 else _face_coord(bounds, 1, -1),
        _face_coord(bounds, 2, +1) if face_axis == 2 and sign > 0 else _face_coord(bounds, 2, -1),
    )
    plane_axis = doc.make_axis(
        origin=plane_origin,
        z_dir=_unit_along(face_axis, sign),
        x_dir=_unit_along(b, +1),
    )
    plane_id = doc.plane(plane_axis)
    return doc.advanced_face([bound], plane_id, True)


def _emit_main_faces(
    doc: StepDoc,
    cyl_tangents: Dict[Tuple[int, int, int, int], int],
    sharp_lines: Dict[Tuple[int, int, int], int],
    arc_edges: Dict[Tuple[int, int, int, int], int],
    bounds: _Bounds,
    flat_ends: FrozenSet[_FaceKey],
) -> List[int]:
    out: List[int] = []
    for face_axis in range(3):
        for sign in (-1, +1):
            if _is_flat(flat_ends, face_axis, sign):
                out.append(_emit_flat_main_face(
                    doc, sharp_lines, arc_edges, bounds, face_axis, sign,
                ))
            else:
                out.append(_emit_filleted_main_face(
                    doc, cyl_tangents, sharp_lines, bounds, face_axis, sign,
                    flat_ends,
                ))
    return out


# ---------------------------------------------------------------------------
# Cylinder strip faces
# ---------------------------------------------------------------------------


def _emit_cylinder_face(
    doc: StepDoc,
    cyl_tangents: Dict[Tuple[int, int, int, int], int],
    arc_edges: Dict[Tuple[int, int, int, int], int],
    bounds: _Bounds,
    axis: int, sb: int, sc: int,
    r: float,
    flat_ends: FrozenSet[_FaceKey],
) -> int:
    """Identical to the original fully-filleted cylinder face emission;
    arc end positions are picked up automatically from the arc-edge
    table, which already accounts for sphere vs. flat-end."""
    b = (axis + 1) % 3
    c = (axis + 2) % 3

    sb_sc = sb * sc
    sa_low  = -sb_sc
    sa_high = +sb_sc

    arc_low  = arc_edges[(axis, sa_low,  sb, sc)]
    arc_high = arc_edges[(axis, sa_high, sb, sc)]
    c_line   = cyl_tangents[(axis, sb, sc, c)]
    b_line   = cyl_tangents[(axis, sb, sc, b)]

    c_line_fwd = (sa_low == -1)
    b_line_fwd = (sa_low == +1)

    oriented = [
        doc.oriented_edge(arc_low,  True),
        doc.oriented_edge(c_line,   c_line_fwd),
        doc.oriented_edge(arc_high, False),
        doc.oriented_edge(b_line,   b_line_fwd),
    ]
    loop = doc.edge_loop(oriented)
    bound = doc.face_bound(loop, True)

    # Cylinder placement: origin at any axial point on the cylinder
    # axis. Use the box's axis-min coord (always inside the cylinder
    # span when one end is filleted; for fully-flat-along-axis
    # cylinders the min coord is also valid since the cylinder
    # extends from axis-min to axis-max).
    origin = [0.0, 0.0, 0.0]
    origin[axis]            = bounds[axis]
    origin[(axis + 1) % 3]  = _inner_coord(bounds, b, sb, r)
    origin[(axis + 2) % 3]  = _inner_coord(bounds, c, sc, r)
    cyl_axis = doc.make_axis(
        origin=(origin[0], origin[1], origin[2]),
        z_dir=_unit_along(axis, sb_sc),
        x_dir=_unit_along(b, sb),
    )
    cyl_surface = doc.cylindrical_surface(cyl_axis, r)
    return doc.advanced_face([bound], cyl_surface, True)


def _emit_cylinder_faces(
    doc: StepDoc,
    cyl_tangents: Dict[Tuple[int, int, int, int], int],
    arc_edges: Dict[Tuple[int, int, int, int], int],
    bounds: _Bounds,
    r: float,
    flat_ends: FrozenSet[_FaceKey],
) -> List[int]:
    out: List[int] = []
    for axis in range(3):
        for sb in (-1, +1):
            for sc in (-1, +1):
                if _cylinder_exists(flat_ends, axis, sb, sc):
                    out.append(_emit_cylinder_face(
                        doc, cyl_tangents, arc_edges, bounds, axis, sb, sc, r, flat_ends,
                    ))
    return out


# ---------------------------------------------------------------------------
# Sphere octant faces
# ---------------------------------------------------------------------------


def _emit_sphere_face(
    doc: StepDoc,
    arc_edges: Dict[Tuple[int, int, int, int], int],
    bounds: _Bounds,
    sx: int, sy: int, sz: int,
    r: float,
) -> int:
    """Identical to the original implementation; only emitted for
    full-fillet corners."""
    parity = sx * sy * sz

    arcs: List[int] = []
    for axis in range(3):
        b = (axis + 1) % 3
        c = (axis + 2) % 3
        sb = (sx, sy, sz)[b]
        sc = (sx, sy, sz)[c]
        sa = (sx, sy, sz)[axis]
        arcs.append(arc_edges[(axis, sa, sb, sc)])

    if parity > 0:
        oriented = [doc.oriented_edge(a, True) for a in arcs]
    else:
        oriented = [
            doc.oriented_edge(arcs[2], False),
            doc.oriented_edge(arcs[1], False),
            doc.oriented_edge(arcs[0], False),
        ]

    loop = doc.edge_loop(oriented)
    bound = doc.face_bound(loop, True)

    centre = (
        _inner_coord(bounds, 0, sx, r),
        _inner_coord(bounds, 1, sy, r),
        _inner_coord(bounds, 2, sz, r),
    )
    sphere_axis = doc.make_axis(
        origin=centre,
        z_dir=_unit_along(2, +1),
        x_dir=_unit_along(0, +1),
    )
    sphere_surface = doc.spherical_surface(sphere_axis, r)
    return doc.advanced_face([bound], sphere_surface, True)


def _emit_sphere_faces(
    doc: StepDoc,
    arc_edges: Dict[Tuple[int, int, int, int], int],
    bounds: _Bounds,
    r: float,
    flat_ends: FrozenSet[_FaceKey],
) -> List[int]:
    out: List[int] = []
    for sx in (-1, +1):
        for sy in (-1, +1):
            for sz in (-1, +1):
                if _corner_has_sphere(flat_ends, sx, sy, sz):
                    out.append(_emit_sphere_face(doc, arc_edges, bounds, sx, sy, sz, r))
    return out


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def filleted_box(
    doc: StepDoc,
    xmin: float, ymin: float, zmin: float,
    xmax: float, ymax: float, zmax: float,
    radius: float = DEFAULT_FILLET_RADIUS_MM,
    name: str = "",
    *,
    fillet_x_low: bool = True,
    fillet_x_high: bool = True,
) -> int:
    """Add a rounded-edge axis-aligned box to ``doc`` and return the
    resulting ``MANIFOLD_SOLID_BREP`` ``#id``.

    Geometry: B-rep with cylindrical edge fillets and spherical corner
    octants of radius ``min(radius, min(L, W, H) / 4)`` (Altium IPC LP
    Wizard's clamp -- a fillet can never eat more than 1/4 of any box
    extent). Falls back to ``sharp_box`` automatically when the clamped
    radius collapses to ~0.

    The two boolean flags control whether each X-axis end face has a
    filleted perimeter:

    * ``fillet_x_low=True`` (default) -- the -X face is a "shrunk"
      rectangle bordered by 4 cylinder fillets and 4 sphere octants
      at its corners. Same look as the original
      ``filleted_box(fully filleted)``.
    * ``fillet_x_low=False`` -- the -X face is a flat full-size
      rectangle whose corners are replaced by 4 quarter-arcs (each
      X-axis cylinder ends at this plane with a quarter-circle
      cross-section). This is what we use at the body / terminal
      junction so the two solids meet flush.

    ``fillet_x_high`` is the analogous flag for the +X face.

    Y- and Z-axis end faces are always treated as filleted in this
    implementation (the helper machinery is generic enough to support
    flat Y/Z ends too, but the chip-component use cases only ever
    have flat X ends, and exposing more flags would just add API
    surface that nobody calls)."""
    from .shapes import sharp_box

    L = xmax - xmin
    W = ymax - ymin
    H = zmax - zmin
    if not (L > 0 and W > 0 and H > 0):
        raise ValueError(
            f"filleted_box: bounds must be increasing; got "
            f"({xmin},{ymin},{zmin})..({xmax},{ymax},{zmax})"
        )
    if radius <= 0:
        raise ValueError(f"filleted_box: radius must be > 0; got {radius}")

    r = min(radius, min(L, W, H) / 4.0)
    if r < 1e-6:
        return sharp_box(doc, xmin, ymin, zmin, xmax, ymax, zmax, name=name)

    # Build the flat_ends set from the per-end flags. Only X axis is
    # exposed; Y and Z are always filleted.
    flat_set: List[_FaceKey] = []
    if not fillet_x_low:
        flat_set.append((0, -1))
    if not fillet_x_high:
        flat_set.append((0, +1))
    flat_ends: FrozenSet[_FaceKey] = frozenset(flat_set)

    bounds: _Bounds = (xmin, ymin, zmin, xmax, ymax, zmax)

    vertices = _emit_vertices(doc, bounds, r, flat_ends)
    cyl_tangents, sharp_lines = _emit_line_edges(doc, vertices, bounds, r, flat_ends)
    arc_edges = _emit_arc_edges(doc, vertices, bounds, r, flat_ends)

    main_faces  = _emit_main_faces(doc, cyl_tangents, sharp_lines, arc_edges, bounds, flat_ends)
    cyl_faces   = _emit_cylinder_faces(doc, cyl_tangents, arc_edges, bounds, r, flat_ends)
    sphere_faces = _emit_sphere_faces(doc, arc_edges, bounds, r, flat_ends)

    shell = doc.closed_shell(main_faces + cyl_faces + sphere_faces)
    return doc.manifold_solid_brep(shell, name=name)
