"""
Shape primitives for the chip-body STEP generator.

Phase 1 (this file): ``sharp_box`` only -- an axis-aligned rectangular
solid with 8 vertices, 12 edges, 6 faces. Enough to ship a working
multi-coloured 3D model end-to-end through the .pcblib pipeline.

Phase 2 will add ``filleted_box(min, size, radius)`` with the full
26-face B-rep (6 main + 12 cylindrical fillet strips + 8 spherical
corner octants) -- same callsite signature as ``sharp_box``, just a
richer implementation. Callers in ``chip.py`` won't need to change.

Coordinate system convention (used here and throughout the package):

* Body length L is along **X** (terminals at the +X / -X ends).
* Body width  W is along **Y**.
* Body height H is along **Z**, with ``z=0`` on the board surface and
  ``z=H`` at the top of the part. (Chip components sit flat -- no
  standoff -- so the bottom face is on the board.)
"""

from __future__ import annotations

from .doc import StepDoc, Vec3
from .filleted import DEFAULT_FILLET_RADIUS_MM, filleted_box  # re-export

__all__ = ["sharp_box", "filleted_box", "DEFAULT_FILLET_RADIUS_MM"]


def sharp_box(
    doc: StepDoc,
    xmin: float, ymin: float, zmin: float,
    xmax: float, ymax: float, zmax: float,
    name: str = "",
) -> int:
    """Add a sharp-edged axis-aligned box to ``doc`` and return the
    resulting ``MANIFOLD_SOLID_BREP``'s ``#id``.

    The returned id is what callers pass to ``doc.add_solid(...)`` so
    the box gets a colour and ends up in the file's shape rep.

    Topology (6 faces, 12 edges, 8 vertices):

        Vertices (corners):

                7---------6
               /|        /|
              / |       / |
             4---------5  |
             |  3------|--2
             | /       | /
             |/        |/
             0---------1
              -- x along bottom edge 0->1 --
              y along front edge 0->3
              z along left edge  0->4

    Each main face is a rectangular ``PLANE`` whose outward normal points
    away from the box body. The 4 ``ORIENTED_EDGE`` entries on each face's
    ``EDGE_LOOP`` are traversed CCW from outside (right-hand rule).

    Args:
        doc:                                 the StepDoc to write into
        xmin, ymin, zmin, xmax, ymax, zmax:  box extents, in mm
        name:                                stored in the
                                             MANIFOLD_SOLID_BREP's name
                                             field (useful for debugging
                                             when multiple boxes share a
                                             STEP file)

    Returns:
        The MANIFOLD_SOLID_BREP id, suitable for ``doc.add_solid``.
    """
    if not (xmax > xmin and ymax > ymin and zmax > zmin):
        raise ValueError(
            f"sharp_box requires xmax>xmin etc.; got "
            f"({xmin},{ymin},{zmin})..({xmax},{ymax},{zmax})"
        )

    # 8 corner positions, indexed as in the docstring picture above.
    corners: list[Vec3] = [
        (xmin, ymin, zmin),  # 0
        (xmax, ymin, zmin),  # 1
        (xmax, ymax, zmin),  # 2
        (xmin, ymax, zmin),  # 3
        (xmin, ymin, zmax),  # 4
        (xmax, ymin, zmax),  # 5
        (xmax, ymax, zmax),  # 6
        (xmin, ymax, zmax),  # 7
    ]

    # Emit the 8 VERTEX_POINTs.
    vp = [doc.vertex_point(doc.cartesian_point(c)) for c in corners]

    # 12 edge curves. Each entry is a (start_vertex_idx, end_vertex_idx)
    # pair; the edge curve's direction is start -> end. Ordering chosen
    # so all edges run from "low" to "high" (i.e. -X to +X, -Y to +Y,
    # -Z to +Z) so face traversal sense is easy to reason about.
    edges_def = [
        (0, 1),  # 0:  -y, -z, x-axis
        (3, 2),  # 1:  +y, -z, x-axis
        (4, 5),  # 2:  -y, +z, x-axis
        (7, 6),  # 3:  +y, +z, x-axis
        (0, 3),  # 4:  -x, -z, y-axis
        (1, 2),  # 5:  +x, -z, y-axis
        (4, 7),  # 6:  -x, +z, y-axis
        (5, 6),  # 7:  +x, +z, y-axis
        (0, 4),  # 8:  -x, -y, z-axis
        (1, 5),  # 9:  +x, -y, z-axis
        (2, 6),  # 10: +x, +y, z-axis
        (3, 7),  # 11: -x, +y, z-axis
    ]
    edge_curves: list[int] = []
    for a, b in edges_def:
        ax_, ay_, az_ = corners[a]
        bx_, by_, bz_ = corners[b]
        dx, dy, dz = bx_ - ax_, by_ - ay_, bz_ - az_
        mag = (dx * dx + dy * dy + dz * dz) ** 0.5
        d_norm = (dx / mag, dy / mag, dz / mag)
        line_id = doc.make_line(origin=corners[a], direction=d_norm, magnitude=mag)
        edge_curves.append(doc.edge_curve(vp[a], vp[b], line_id))

    # 6 faces. For each face we list the 4 (edge_index, orientation)
    # pairs that traverse the face CCW from outside, plus the surface
    # plane's z-axis direction (= outward normal) and a chosen x-axis
    # direction lying in the face.
    #
    # Edge index reference (from edges_def above):
    #     0:  0->1  (x at y=ymin, z=zmin)
    #     1:  3->2  (x at y=ymax, z=zmin)
    #     2:  4->5  (x at y=ymin, z=zmax)
    #     3:  7->6  (x at y=ymax, z=zmax)
    #     4:  0->3  (y at x=xmin, z=zmin)
    #     5:  1->2  (y at x=xmax, z=zmin)
    #     6:  4->7  (y at x=xmin, z=zmax)
    #     7:  5->6  (y at x=xmax, z=zmax)
    #     8:  0->4  (z at x=xmin, y=ymin)
    #     9:  1->5  (z at x=xmax, y=ymin)
    #    10:  2->6  (z at x=xmax, y=ymax)
    #    11:  3->7  (z at x=xmin, y=ymax)
    #
    # Orientation: True keeps the edge in its declared direction
    # (start->end); False reverses it.
    FaceSpec = tuple
    faces_def: list[tuple[
        list[tuple[int, bool]],  # (edge_index, orientation) sequence, CCW
        Vec3,                    # plane origin (a point on the face)
        Vec3,                    # plane outward normal
        Vec3,                    # plane x-axis (any direction lying in the face)
    ]] = [
        # ---- Bottom face (z=zmin), outward normal -z. CCW from below: 0 -> 3 -> 2 -> 1.
        (
            [(4, True), (1, True), (5, False), (0, False)],
            (xmin, ymin, zmin),
            (0.0, 0.0, -1.0),
            (1.0, 0.0, 0.0),
        ),
        # ---- Top face (z=zmax), outward normal +z. CCW from above: 4 -> 5 -> 6 -> 7.
        (
            [(2, True), (7, True), (3, False), (6, False)],
            (xmin, ymin, zmax),
            (0.0, 0.0, 1.0),
            (1.0, 0.0, 0.0),
        ),
        # ---- Front face (y=ymin), outward normal -y. CCW from -y looking +y:
        # 0 -> 1 -> 5 -> 4.
        (
            [(0, True), (9, True), (2, False), (8, False)],
            (xmin, ymin, zmin),
            (0.0, -1.0, 0.0),
            (1.0, 0.0, 0.0),
        ),
        # ---- Back face (y=ymax), outward normal +y. CCW from +y looking -y:
        # 3 -> 7 -> 6 -> 2.
        (
            [(11, True), (3, True), (10, False), (1, False)],
            (xmin, ymax, zmin),
            (0.0, 1.0, 0.0),
            (1.0, 0.0, 0.0),
        ),
        # ---- Left face (x=xmin), outward normal -x. CCW from -x looking +x:
        # 0 -> 4 -> 7 -> 3.
        (
            [(8, True), (6, True), (11, False), (4, False)],
            (xmin, ymin, zmin),
            (-1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
        ),
        # ---- Right face (x=xmax), outward normal +x. CCW from +x looking -x:
        # 1 -> 2 -> 6 -> 5.
        (
            [(5, True), (10, True), (7, False), (9, False)],
            (xmax, ymin, zmin),
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
        ),
    ]

    face_ids: list[int] = []
    for edges, origin, z_dir, x_dir in faces_def:
        oriented = [doc.oriented_edge(edge_curves[idx], orient) for idx, orient in edges]
        loop = doc.edge_loop(oriented)
        bound = doc.face_bound(loop, True)
        plane_axis = doc.make_axis(origin=origin, z_dir=z_dir, x_dir=x_dir)
        plane_id = doc.plane(plane_axis)
        # same_sense=True because we built the plane axis to face the
        # outward normal; the EDGE_LOOP is traversed CCW around that
        # normal (right-hand rule).
        face_ids.append(doc.advanced_face([bound], plane_id, True))

    shell = doc.closed_shell(face_ids)
    return doc.manifold_solid_brep(shell, name=name)
