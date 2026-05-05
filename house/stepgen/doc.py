"""
``StepDoc``: build an ISO-10303-21 STEP file by emitting numbered entities,
then serialise the result to text.

Why a hand-rolled STEP writer instead of CadQuery / OCP / FreeCAD?
- This generator only needs to produce ~150 chip-body STEP files of a very
  constrained shape family (rectangular box w/ optional rounded edges, three
  variants: CAPC, RESC, INDC). A full B-rep kernel is overkill.
- The repo's design constraint is a stdlib-only Python pipeline so the
  whole thing can be ported to a browser (Pyodide) for a future
  open-source web UI.
- The Altium reader is OpenCASCADE-based; we mimic the entity layout it
  expects (AP214 AUTOMOTIVE_DESIGN, mm units, B-rep solids) so what we
  emit is what Open CASCADE round-trips through the existing reference
  files in ``house/step/``.

The DATA section is built by calling ``emit("BODY_OF_ENTITY")`` for each
ENTITY which returns the assigned ``#id`` (1-based, monotonically
increasing). Helper methods on this class wrap the most common entity
forms (``cartesian_point``, ``vertex_point``, ``line``, etc.) so callers
don't have to handcraft the STEP syntax. ``serialize()`` finalises the
file, prepending the standard ISO-10303-21 header.
"""

from __future__ import annotations

import datetime
import os
from typing import Iterable, List, Sequence, Tuple

Vec3 = Tuple[float, float, float]
Rgb = Tuple[float, float, float]


# Reproducible-builds support. If `SOURCE_DATE_EPOCH` is set in the
# environment (the de-facto standard for reproducible builds; see
# https://reproducible-builds.org/docs/source-date-epoch/) we use it
# verbatim. Otherwise we use a fixed sentinel timestamp -- NOT the
# current wall clock -- so each rerun of the generator produces
# byte-identical .step files. The timestamp only appears in the
# STEP header's FILE_NAME field; it has no semantic meaning for the
# geometry or for Altium's reader.
_FIXED_SENTINEL_TIMESTAMP = "2024-01-01T00:00:00"


def _build_timestamp() -> str:
    s = os.environ.get("SOURCE_DATE_EPOCH")
    if s is None or not s.strip():
        return _FIXED_SENTINEL_TIMESTAMP
    try:
        epoch = int(s)
    except ValueError:
        return _FIXED_SENTINEL_TIMESTAMP
    return datetime.datetime.fromtimestamp(
        epoch, tz=datetime.timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%S")


def _fmt(x: float) -> str:
    """Format a float for STEP. Open CASCADE outputs ``-0.`` and ``5.E-02``
    style values; we follow that exactly so the diff against the
    reference Altium files in ``house/step/`` is minimal.

    - Whole-number values are emitted as ``"42."`` (trailing dot, no
      decimal digits).
    - Other values use repr-style formatting trimmed to <=12 significant
      digits with the special case that very small magnitudes (<= 1e-4)
      switch to scientific notation matching Open CASCADE's output.
    """
    if x == 0.0:
        return "0."
    if x == float(int(x)) and abs(x) < 1e15:
        return f"{int(x)}."
    ax = abs(x)
    if ax < 1e-4 or ax >= 1e7:
        # Scientific notation matching Open CASCADE: "5.E-02"
        # Python's default %g uses lowercase 'e'; STEP uses uppercase 'E'.
        s = f"{x:.6E}"
        # Trim trailing zeros in mantissa: 5.000000E-02 -> 5.E-02
        mantissa, exp = s.split("E")
        if "." in mantissa:
            mantissa = mantissa.rstrip("0")
            if mantissa.endswith("."):
                pass  # keep trailing "."
        # Drop leading "+" in exponent and align to 2 digits if possible
        sign = "-" if exp.startswith("-") else ""
        exp_abs = exp.lstrip("+-").lstrip("0") or "0"
        return f"{mantissa}E{sign}{exp_abs}"
    # Plain decimal. Trim trailing zeros after the decimal point but
    # keep at least one digit after the decimal.
    s = f"{x:.12f}".rstrip("0")
    if s.endswith("."):
        s += "0"
    return s


def _step_string(s: str) -> str:
    """Quote a string for a STEP literal: wrap in single quotes, escape
    embedded single quotes by doubling them. Non-ASCII characters are
    rejected (caller's job to keep them out)."""
    if not isinstance(s, str):
        raise TypeError(f"expected str, got {type(s).__name__}")
    if not s.isascii():
        raise ValueError(f"non-ASCII in STEP literal: {s!r}")
    return "'" + s.replace("'", "''") + "'"


class StepDoc:
    """Build a STEP DATA section, then serialise as text.

    Lifecycle:
      1. Create the doc with the product/file name.
      2. Call ``start_product()`` once. This emits the standard preamble
         (application context, units, geometric context, world origin
         placement) and stashes the relevant ``#id``s on ``self``.
      3. Build geometry by calling helper emitters and feeding the
         returned ``#id``s into successive calls. End with one or more
         ``add_solid(manifold_solid_brep_id, color_rgb)``.
      4. ``serialize()`` returns the full STEP file as a string. After
         calling ``serialize()`` the doc is "sealed" -- emitting more
         entities is undefined.

    All numeric coordinates are in millimetres (the schema we declare in
    the preamble is ``LENGTH_UNIT() SI_UNIT(.MILLI.,.METRE.)``).
    """

    # Class-level constants used in the header
    PREPROCESSOR_VERSION = "house/stepgen 1.0"
    ORIGINATING_SYSTEM   = "HouseLibGenerator"
    AUTHOR_NAME          = "Humanity's Last Component Library"
    SCHEMA_NAME          = "AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }"

    def __init__(self, name: str):
        self.name: str = name
        self._entities: List[Tuple[int, str]] = []
        self._next_id: int = 1
        self._sealed: bool = False

        # Filled in by start_product()
        self.app_context: int | None = None
        self.geom_context_3d: int | None = None
        self.product_def: int | None = None
        self.product_def_shape: int | None = None
        self.world_axis: int | None = None  # AXIS2_PLACEMENT_3D at origin

        # Filled in by add_solid()
        self._solids: List[int] = []
        self._color_items: List[Tuple[int, Rgb]] = []

    # ------------------------------------------------------------------
    # Low-level entity emission
    # ------------------------------------------------------------------

    def emit(self, body: str) -> int:
        """Emit one entity body string, return its ``#id``."""
        if self._sealed:
            raise RuntimeError("StepDoc has already been serialised; cannot add more entities")
        i = self._next_id
        self._next_id += 1
        self._entities.append((i, f"#{i} = {body};"))
        return i

    # ------------------------------------------------------------------
    # Geometry primitives -- one method per STEP entity type.
    #
    # The ones below cover the subset Phase-1 sharp boxes need. Phase-2
    # filleted boxes will need additional helpers (circle, vector_axis_2,
    # cylindrical_surface, spherical_surface, surface_curve, pcurve)
    # which can be added without disturbing the existing API.
    # ------------------------------------------------------------------

    def cartesian_point(self, p: Vec3) -> int:
        x, y, z = p
        return self.emit(f"CARTESIAN_POINT('',({_fmt(x)},{_fmt(y)},{_fmt(z)}))")

    def direction(self, d: Vec3) -> int:
        x, y, z = d
        return self.emit(f"DIRECTION('',({_fmt(x)},{_fmt(y)},{_fmt(z)}))")

    def vector(self, direction_id: int, magnitude: float) -> int:
        return self.emit(f"VECTOR('',#{direction_id},{_fmt(magnitude)})")

    def line(self, point_id: int, vector_id: int) -> int:
        return self.emit(f"LINE('',#{point_id},#{vector_id})")

    def vertex_point(self, point_id: int) -> int:
        return self.emit(f"VERTEX_POINT('',#{point_id})")

    def edge_curve(self, v_start: int, v_end: int, curve_id: int, same_sense: bool = True) -> int:
        s = ".T." if same_sense else ".F."
        return self.emit(f"EDGE_CURVE('',#{v_start},#{v_end},#{curve_id},{s})")

    def oriented_edge(self, edge_curve_id: int, orientation: bool) -> int:
        # The two starred fields are start/end vertex; STEP allows ``*``
        # to mean "look it up from the underlying EDGE_CURVE", which is
        # what every realistic emitter (Open CASCADE included) uses.
        o = ".T." if orientation else ".F."
        return self.emit(f"ORIENTED_EDGE('',*,*,#{edge_curve_id},{o})")

    def edge_loop(self, oriented_edges: Sequence[int]) -> int:
        items = ",".join(f"#{e}" for e in oriented_edges)
        return self.emit(f"EDGE_LOOP('',({items}))")

    def face_bound(self, edge_loop_id: int, orientation: bool = True) -> int:
        o = ".T." if orientation else ".F."
        return self.emit(f"FACE_BOUND('',#{edge_loop_id},{o})")

    def axis2_placement_3d(self, origin_id: int, z_dir_id: int, x_dir_id: int) -> int:
        return self.emit(f"AXIS2_PLACEMENT_3D('',#{origin_id},#{z_dir_id},#{x_dir_id})")

    def plane(self, axis_id: int) -> int:
        return self.emit(f"PLANE('',#{axis_id})")

    # Curved surfaces and the curves they carry. Each surface is
    # placed in space via an AXIS2_PLACEMENT_3D whose Z-axis defines
    # the surface's natural "up":
    #
    #   CYLINDRICAL_SURFACE  -- cylinder axis is the placement Z-axis;
    #                           radius is the perpendicular distance
    #                           from axis to surface; surface
    #                           parameter (u, v) = (theta, axial),
    #                           outward normal points radially out.
    #   SPHERICAL_SURFACE    -- sphere centre is the placement origin;
    #                           radius is the surface radius;
    #                           outward normal points radially out
    #                           from the centre.
    #   CIRCLE               -- placement origin is the circle centre;
    #                           Z-axis is the disk normal (so the
    #                           circle lies in the placement's X-Y
    #                           plane); X-axis is the parameter-zero
    #                           direction, parameter increases CCW
    #                           around Z (right-hand rule).

    def circle(self, axis_id: int, radius: float) -> int:
        return self.emit(f"CIRCLE('',#{axis_id},{_fmt(radius)})")

    def cylindrical_surface(self, axis_id: int, radius: float) -> int:
        return self.emit(f"CYLINDRICAL_SURFACE('',#{axis_id},{_fmt(radius)})")

    def spherical_surface(self, axis_id: int, radius: float) -> int:
        return self.emit(f"SPHERICAL_SURFACE('',#{axis_id},{_fmt(radius)})")

    def advanced_face(
        self,
        face_bounds: Sequence[int],
        surface_id: int,
        same_sense: bool,
    ) -> int:
        bounds = ",".join(f"#{b}" for b in face_bounds)
        s = ".T." if same_sense else ".F."
        return self.emit(f"ADVANCED_FACE('',({bounds}),#{surface_id},{s})")

    def closed_shell(self, faces: Sequence[int]) -> int:
        items = ",".join(f"#{f}" for f in faces)
        return self.emit(f"CLOSED_SHELL('',({items}))")

    def manifold_solid_brep(self, shell_id: int, name: str = "") -> int:
        return self.emit(f"MANIFOLD_SOLID_BREP({_step_string(name)},#{shell_id})")

    # ------------------------------------------------------------------
    # Higher-level helpers
    # ------------------------------------------------------------------

    def make_axis(self, origin: Vec3, z_dir: Vec3, x_dir: Vec3) -> int:
        """Convenience: emit CARTESIAN_POINT + 2 DIRECTIONs + AXIS2_PLACEMENT_3D
        in one call. Returns the AXIS2_PLACEMENT_3D's ``#id``."""
        op = self.cartesian_point(origin)
        zd = self.direction(z_dir)
        xd = self.direction(x_dir)
        return self.axis2_placement_3d(op, zd, xd)

    def make_line(self, origin: Vec3, direction: Vec3, magnitude: float = 1.0) -> int:
        """Emit a LINE geometry: CARTESIAN_POINT origin + DIRECTION + VECTOR
        + LINE. Returns the LINE's ``#id``."""
        op = self.cartesian_point(origin)
        di = self.direction(direction)
        ve = self.vector(di, magnitude)
        return self.line(op, ve)

    # ------------------------------------------------------------------
    # Preamble (call once, before any geometry)
    # ------------------------------------------------------------------

    def start_product(self, product_name: str | None = None) -> None:
        """Emit the standard STEP preamble for a single PRODUCT.

        The preamble pulls in the application context, declares mm
        units with a 1e-7 mm tolerance, and sets up the world origin
        AXIS2_PLACEMENT_3D that every shape representation will
        reference. After this returns, the doc has these ``#id``s
        stashed on ``self`` for use by ``serialize()``:

            self.app_context        -> APPLICATION_CONTEXT
            self.geom_context_3d    -> GEOMETRIC_REPRESENTATION_CONTEXT(3)
            self.product_def        -> PRODUCT_DEFINITION
            self.product_def_shape  -> PRODUCT_DEFINITION_SHAPE
            self.world_axis         -> AXIS2_PLACEMENT_3D at origin
        """
        if self.app_context is not None:
            raise RuntimeError("start_product() already called")
        product_name = product_name or self.name

        ac = self.emit(
            "APPLICATION_CONTEXT('core data for automotive mechanical design processes')"
        )
        self.app_context = ac
        self.emit(
            f"APPLICATION_PROTOCOL_DEFINITION('international standard',"
            f"'automotive_design',2000,#{ac})"
        )
        pc = self.emit(f"PRODUCT_CONTEXT('',#{ac},'mechanical')")
        prod = self.emit(
            f"PRODUCT({_step_string(product_name)},{_step_string(product_name)},'',(#{pc}))"
        )
        self.emit(f"PRODUCT_RELATED_PRODUCT_CATEGORY('part',$,(#{prod}))")
        pdf = self.emit(f"PRODUCT_DEFINITION_FORMATION('','',#{prod})")
        pdc = self.emit(f"PRODUCT_DEFINITION_CONTEXT('part definition',#{ac},'design')")
        pd = self.emit(f"PRODUCT_DEFINITION('design','',#{pdf},#{pdc})")
        self.product_def = pd
        pds = self.emit(f"PRODUCT_DEFINITION_SHAPE('','',#{pd})")
        self.product_def_shape = pds

        # Units block: every Open CASCADE-emitted file has this exact
        # quartet, in this order, so we follow suit. The compound
        # ``( X() Y() Z() )`` syntax is a STEP "complex entity" -- this
        # is the standard way to declare a unit that's both a LENGTH_UNIT
        # AND a NAMED_UNIT AND an SI_UNIT all at once.
        u_len = self.emit("( LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.) )")
        u_ang = self.emit("( NAMED_UNIT(*) PLANE_ANGLE_UNIT() SI_UNIT($,.RADIAN.) )")
        u_solid = self.emit("( NAMED_UNIT(*) SI_UNIT($,.STERADIAN.) SOLID_ANGLE_UNIT() )")
        unc = self.emit(
            f"UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-07),#{u_len},"
            "'distance_accuracy_value','confusion accuracy')"
        )
        ctx = self.emit(
            f"( GEOMETRIC_REPRESENTATION_CONTEXT(3) "
            f"GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#{unc})) "
            f"GLOBAL_UNIT_ASSIGNED_CONTEXT((#{u_len},#{u_ang},#{u_solid})) "
            f"REPRESENTATION_CONTEXT('Context #1','3D Context with UNIT and UNCERTAINTY') )"
        )
        self.geom_context_3d = ctx

        # World origin placement: every shape rep references it.
        self.world_axis = self.make_axis(
            origin=(0.0, 0.0, 0.0),
            z_dir=(0.0, 0.0, 1.0),
            x_dir=(1.0, 0.0, 0.0),
        )

    # ------------------------------------------------------------------
    # Solid registration + colour
    # ------------------------------------------------------------------

    def add_solid(
        self,
        manifold_solid_id: int,
        color_rgb: Rgb | None = None,
    ) -> None:
        """Register a MANIFOLD_SOLID_BREP for inclusion in the file's
        single ADVANCED_BREP_SHAPE_REPRESENTATION, optionally with a
        per-solid colour (emitted via STYLED_ITEM in ``serialize()``).

        Multiple calls add multiple solids to the same shape rep; this is
        how we get a 3-piece chip cap (body + 2 terminals) into one
        STEP file with three different colours."""
        if self.product_def_shape is None:
            raise RuntimeError("call start_product() before add_solid()")
        self._solids.append(manifold_solid_id)
        if color_rgb is not None:
            self._color_items.append((manifold_solid_id, color_rgb))

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def serialize(self) -> str:
        """Return the full STEP file as text."""
        if self._sealed:
            raise RuntimeError("StepDoc has already been serialised")
        if self.product_def is None:
            raise RuntimeError("call start_product() before serialize()")
        if not self._solids:
            raise RuntimeError("at least one add_solid() is required before serialize()")

        # Tie all the solids into a single ADVANCED_BREP_SHAPE_REPRESENTATION.
        # The first item is the world axis; the rest are the solids in
        # registration order.
        items = ",".join(
            [f"#{self.world_axis}"] + [f"#{s}" for s in self._solids]
        )
        absr = self.emit(
            f"ADVANCED_BREP_SHAPE_REPRESENTATION('',({items}),#{self.geom_context_3d})"
        )
        self.emit(
            f"SHAPE_DEFINITION_REPRESENTATION(#{self.product_def_shape},#{absr})"
        )

        # Per-solid presentation blocks. STEP's colour assignment chain
        # is famously verbose (8 entities per coloured solid). Layout
        # taken from Altium / Open CASCADE reference output:
        #
        #   COLOUR_RGB
        #   FILL_AREA_STYLE_COLOUR        -> COLOUR_RGB
        #   FILL_AREA_STYLE               -> FILL_AREA_STYLE_COLOUR
        #   SURFACE_STYLE_FILL_AREA       -> FILL_AREA_STYLE
        #   SURFACE_SIDE_STYLE            -> SURFACE_STYLE_FILL_AREA
        #   SURFACE_STYLE_USAGE(.BOTH.)   -> SURFACE_SIDE_STYLE
        #   PRESENTATION_STYLE_ASSIGNMENT -> SURFACE_STYLE_USAGE
        #   STYLED_ITEM                   -> PRESENTATION_STYLE_ASSIGNMENT, target solid
        #   MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION
        #                                 -> STYLED_ITEM, geometric context
        for solid_id, (r, g, b) in self._color_items:
            color = self.emit(
                f"COLOUR_RGB('',{_fmt(r)},{_fmt(g)},{_fmt(b)})"
            )
            fac = self.emit(f"FILL_AREA_STYLE_COLOUR('',#{color})")
            fas = self.emit(f"FILL_AREA_STYLE('',(#{fac}))")
            ssfa = self.emit(f"SURFACE_STYLE_FILL_AREA(#{fas})")
            sss = self.emit(f"SURFACE_SIDE_STYLE('',(#{ssfa}))")
            ssu = self.emit(f"SURFACE_STYLE_USAGE(.BOTH.,#{sss})")
            psa = self.emit(f"PRESENTATION_STYLE_ASSIGNMENT((#{ssu}))")
            si = self.emit(
                f"STYLED_ITEM('color',(#{psa}),#{solid_id})"
            )
            self.emit(
                f"MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION"
                f"('',(#{si}),#{self.geom_context_3d})"
            )

        self._sealed = True

        # Header. The timestamp comes from SOURCE_DATE_EPOCH if set
        # (reproducible builds) or a fixed sentinel otherwise -- never
        # wall clock -- so successive runs of the generator produce
        # byte-identical files.
        date = _build_timestamp()
        header = (
            "ISO-10303-21;\n"
            "HEADER;\n"
            f"FILE_DESCRIPTION(({_step_string(self.name)}),'2;1');\n"
            f"FILE_NAME({_step_string(self.name)},'{date}',"
            f"({_step_string(self.AUTHOR_NAME)}),"
            f"({_step_string(self.AUTHOR_NAME)}),"
            f"{_step_string(self.PREPROCESSOR_VERSION)},"
            f"{_step_string(self.ORIGINATING_SYSTEM)},'Unknown');\n"
            f"FILE_SCHEMA(({_step_string(self.SCHEMA_NAME)}));\n"
            "ENDSEC;\n"
        )
        body_lines = ["DATA;"] + [line for _, line in self._entities] + [
            "ENDSEC;",
            "END-ISO-10303-21;",
        ]
        return header + "\n".join(body_lines) + "\n"

    # ------------------------------------------------------------------
    # Diagnostic helpers (not strictly needed but handy for tests)
    # ------------------------------------------------------------------

    @property
    def entity_count(self) -> int:
        return len(self._entities)
