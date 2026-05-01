"""
High-level chip-body STEP generators: ``capc``, ``resc``, ``indc``.

Each function returns a complete STEP file as a single string. The
caller is expected to write the string to disk and/or pass it to the
.PcbLib writer (``house/altium_pcblib/``) for zlib-compressed
embedding into the matching ``Library/Models/<n>`` stream.

All three generators share the same parametric inputs ``(L, W, H, T)``:

    L : body length, mm. Along the X axis (terminal-to-terminal).
    W : body width,  mm. Along the Y axis.
    H : body height, mm. Along the Z axis. Bottom face sits at z=0.
    T : terminal length (band length), mm. The metallised end caps wrap
        ``T`` of the body's L extent on each side.

The footprint is centred on the origin in X and Y. The bottom face is
at ``z=0`` (no standoff -- chip components sit flat on the board).

Phase 1 (current): every solid is a sharp-edged box.
Phase 2: the underlying shape primitive will switch to a filleted box
with rounded edges; the function signatures here will not change.
"""

from __future__ import annotations

from . import colors
from .doc import StepDoc, Rgb
from .shapes import DEFAULT_FILLET_RADIUS_MM, filleted_box, sharp_box

# RESC metallization thickness. Real chip resistors have ~50 um of
# Ag/Pd/Sn plating on the end caps regardless of body size, so we
# parameterise it as a fraction of H with a hard floor (so the wrap
# stays visible on small 0402 chips) and a hard ceiling (so the
# substrate keeps a reasonable sandwich thickness on big 1206 chips).
RESC_METAL_THICKNESS_FRACTION = 0.10
RESC_METAL_THICKNESS_FLOOR_MM = 0.02


def _validate(L: float, W: float, H: float, T: float, name: str) -> None:
    if not (L > 0 and W > 0 and H > 0 and T > 0):
        raise ValueError(f"{name}: L,W,H,T must all be positive (got {L},{W},{H},{T})")
    # Each terminal has length T, and they wrap T from each end. The
    # central body has length L - 2T which must remain positive.
    if 2 * T >= L:
        raise ValueError(
            f"{name}: terminal length T={T}mm leaves no room for body "
            f"(2T >= L={L}mm)"
        )


def _make_terminal_pair(
    doc: StepDoc,
    L: float, W: float, H: float, T: float,
    color: Rgb,
    *,
    radius: float = DEFAULT_FILLET_RADIUS_MM,
) -> None:
    """Add the two terminal end-cap solids to ``doc`` (one at each end
    of the L axis, full W and H extent), coloured ``color``.

    Each end cap is a partial-fillet box: the OUTER L-end (the chip's
    end) is fully filleted (sphere octants + Y/Z fillets); the INNER
    L-end (where it meets the body) is FLAT, no fillet around its
    perimeter. The body emits the same flat shape on its mating face,
    so body and terminal meet flush -- no visible "double bevel" ridge
    at the junction.

    Each end cap goes through ``filleted_box`` -- which clamps the
    fillet radius to ``min(L_box, W_box, H_box)/4`` and falls back to
    a sharp box if that clamp drops the radius to zero. So callers
    don't need to think about whether the box is large enough for the
    requested radius."""
    # Left terminal: outer (-X) is filleted, inner (+X) is flat.
    term1 = filleted_box(
        doc,
        -L / 2.0,         -W / 2.0, 0.0,
        -L / 2.0 + T,     +W / 2.0, H,
        radius=radius,
        name="Terminal-",
        fillet_x_low=True,
        fillet_x_high=False,
    )
    # Right terminal: inner (-X) is flat, outer (+X) is filleted.
    term2 = filleted_box(
        doc,
        +L / 2.0 - T,     -W / 2.0, 0.0,
        +L / 2.0,         +W / 2.0, H,
        radius=radius,
        name="Terminal+",
        fillet_x_low=False,
        fillet_x_high=True,
    )
    doc.add_solid(term1, color)
    doc.add_solid(term2, color)


def capc(
    L: float, W: float, H: float, T: float,
    footprint_name: str | None = None,
    radius: float = DEFAULT_FILLET_RADIUS_MM,
) -> str:
    """Generate a STEP file for a chip ceramic capacitor (CAPC family).

    Three pieces, all with rounded edges (Phase 2):
      - dielectric body (cream/tan MLCC): central filleted box (L-2T) x W x H
      - 2 terminal end caps (silver): filleted boxes T x W x H at each L extent

    The fillet radius defaults to 0.05 mm and is automatically clamped
    by ``filleted_box`` so that on tiny footprints (e.g. CAPC0402X20
    with W=0.2 mm) the fillet doesn't eat more than 1/4 of any box
    extent. On those small parts the fillet is small but visible; on
    1206 / 1210 etc. it's a comfortable 0.05 mm.

    Returns the STEP file as text.
    """
    name = footprint_name or _default_name("CAPC", L, W, H, T)
    _validate(L, W, H, T, name)

    doc = StepDoc(name)
    doc.start_product(name)

    # Body has BOTH L-end faces flat -- the two terminal end caps will
    # be flush against them. Long X-axis edges are still filleted so
    # the body's Y/Z faces have rounded edges along its length.
    body = filleted_box(
        doc,
        -L / 2.0 + T,     -W / 2.0, 0.0,
        +L / 2.0 - T,     +W / 2.0, H,
        radius=radius,
        name="Body",
        fillet_x_low=False,
        fillet_x_high=False,
    )
    doc.add_solid(body, colors.MLCC_TAN)
    _make_terminal_pair(doc, L, W, H, T, colors.TERMINAL_SILVER, radius=radius)

    return doc.serialize()


def indc(
    L: float, W: float, H: float, T: float,
    footprint_name: str | None = None,
    radius: float = DEFAULT_FILLET_RADIUS_MM,
) -> str:
    """Generate a STEP file for a chip inductor / ferrite bead (INDC family).

    Geometry identical to ``capc`` but the body is ferrite-blue.
    Same Phase 2 rounded-edge geometry as CAPC.
    """
    name = footprint_name or _default_name("INDC", L, W, H, T)
    _validate(L, W, H, T, name)

    doc = StepDoc(name)
    doc.start_product(name)

    body = filleted_box(
        doc,
        -L / 2.0 + T,     -W / 2.0, 0.0,
        +L / 2.0 - T,     +W / 2.0, H,
        radius=radius,
        name="Body",
        fillet_x_low=False,
        fillet_x_high=False,
    )
    doc.add_solid(body, colors.INDC_BLUE)
    _make_terminal_pair(doc, L, W, H, T, colors.TERMINAL_SILVER, radius=radius)

    return doc.serialize()


def resc(
    L: float, W: float, H: float, T: float,
    footprint_name: str | None = None,
) -> str:
    """Generate a STEP file for a chip resistor (RESC family).

    Cross-section (looking at +Y face), with t = metallisation thickness:

        ┌─────┐ ┌────────────────┐ ┌─────┐    z=H
        │ TOP │ │   passivation  │ │ TOP │    z=H-t
        │     │ ├────────────────┤ │     │
        │ END │ │                │ │ END │
        │     │ │   substrate    │ │     │
        │     │ │                │ │     │
        │     │ ├────────────────┤ │     │    z=t
        │ BOT │ │      gap       │ │ BOT │    z=0
        └─────┘ └────────────────┘ └─────┘
        ←──T──→ ←──── L − 2T ────→ ←──T──→

    Eight pieces total:

      - substrate (mid grey, alumina): central box, raised off the
        floor by ``t`` and capped at ``H − t`` so it fits between
        the two C-shaped terminals (it doesn't touch the board).
      - passivation cover (near-black): fills the top sandwich slot
        between the two terminals, flush with the terminal tops at
        z=H ("comes right up to the C terminals making a flat top").
      - 2 × terminal end-cap (slightly darker grey than substrate),
        each made of three flush boxes that together form a "C"
        shape opening toward the substrate:
          * end vertical : full T × W × H at the L extreme  -- wait, no:
                           outer t × W × H at the L extreme (the metal
                           coating on the end face)
          * top wrap     : T × W × t along the top (z=H−t..H)
          * bottom wrap  : T × W × t along the bottom (z=0..t)
        The top and bottom wraps overlap the end vertical at the L
        outermost t mm to keep the topology simple (each piece is its
        own closed shell, sharing colour and Z-fighting cleanly inside
        Altium's renderer). The user-visible result on the outside is
        a clean C profile that wraps the substrate.

    Returns the STEP file as text.
    """
    name = footprint_name or _default_name("RESC", L, W, H, T)
    _validate(L, W, H, T, name)

    doc = StepDoc(name)
    doc.start_product(name)

    # Metallisation thickness in BOTH the H direction (top/bottom wraps,
    # passivation thickness) and the L direction (end-vertical
    # thickness). Same number is used in both axes; it's the
    # plating layer thickness, not the band length T.
    t = max(RESC_METAL_THICKNESS_FLOOR_MM, H * RESC_METAL_THICKNESS_FRACTION)
    # Hard ceiling: don't let metal eat more than 1/3 of H (so the
    # substrate keeps at least H/3 of sandwich thickness) or more
    # than half of T (so the L-axis vertical end fits inside the
    # band length T with room for the wraps).
    t = min(t, H / 3.0, T / 2.0)

    # ---- Substrate (mid grey alumina) -------------------------------
    # Centred box that fits snug inside the two C-terminals: it
    # extends in L-axis all the way up to each terminal's vertical
    # end face (x = +/- (L/2 - t)) -- not just to the inner edge of
    # the wrap (which would leave the substrate floating with a
    # T - t mm gap on each side). It sits on top of the terminals'
    # bottom wraps (z=t) and below their top wraps (z=H-t), flush in
    # Y with the terminals' Y faces. Geometrically the substrate
    # overlaps the C-terminal's wrap regions in x -- but only at the
    # mid-Z slab the wraps don't cover -- so there's no interference.
    subs = sharp_box(
        doc,
        -L / 2.0 + t,    -W / 2.0, t,
        +L / 2.0 - t,    +W / 2.0, H - t,
        name="Substrate",
    )
    doc.add_solid(subs, colors.RESC_SUBSTRATE_GREY)

    # ---- Passivation cover (near-black) -----------------------------
    # Same L/W footprint as the substrate's top, occupying the top
    # H/H-t slot. After this, the top of the chip from x=-L/2+T to
    # x=+L/2-T is uniformly passivation-coloured, flush with the
    # terminals' top wraps -- the "flat top surface" the user asked
    # for.
    pas = sharp_box(
        doc,
        -L / 2.0 + T,    -W / 2.0, H - t,
        +L / 2.0 - T,    +W / 2.0, H,
        name="Passivation",
    )
    doc.add_solid(pas, colors.RESC_PASSIVATION_BLACK)

    # ---- Two C-terminals, 3 boxes each ------------------------------
    for sign, side_label in [(-1.0, "Term-"), (+1.0, "Term+")]:
        x_outer = sign * (L / 2.0)
        # The end vertical sits in the outermost ``t`` mm. The top/bot
        # wraps span the whole T-wide band (and overlap the end vertical
        # at the outermost ``t`` slice -- harmless: all three boxes
        # share a colour and produce a coherent C profile).
        end_x_outer = x_outer
        end_x_inner = x_outer - sign * t
        wrap_x_outer = x_outer
        wrap_x_inner = x_outer - sign * T

        # Order extents so xmin < xmax regardless of sign.
        end_xmin, end_xmax = min(end_x_outer, end_x_inner), max(end_x_outer, end_x_inner)
        wrap_xmin, wrap_xmax = min(wrap_x_outer, wrap_x_inner), max(wrap_x_outer, wrap_x_inner)

        # End vertical (the metal layer on the chip's end face)
        end_v = sharp_box(
            doc,
            end_xmin, -W / 2.0, 0.0,
            end_xmax, +W / 2.0, H,
            name=side_label + "End",
        )
        doc.add_solid(end_v, colors.RESC_TERMINAL_DARK_GREY)

        # Bottom wrap (the floor strip of the C)
        bot_w = sharp_box(
            doc,
            wrap_xmin, -W / 2.0, 0.0,
            wrap_xmax, +W / 2.0, t,
            name=side_label + "Bot",
        )
        doc.add_solid(bot_w, colors.RESC_TERMINAL_DARK_GREY)

        # Top wrap (the ceiling strip of the C)
        top_w = sharp_box(
            doc,
            wrap_xmin, -W / 2.0, H - t,
            wrap_xmax, +W / 2.0, H,
            name=side_label + "Top",
        )
        doc.add_solid(top_w, colors.RESC_TERMINAL_DARK_GREY)

    return doc.serialize()


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


def _default_name(prefix: str, L: float, W: float, H: float, T: float) -> str:
    """Mirror the IPC-7351B name format from DDL-001 §6.1 (TYPELLWWXHH)
    when the caller doesn't pass an explicit name. Useful when the
    generator is invoked directly from a Python REPL for ad-hoc 3D model
    inspection."""
    LL = int(round(L * 10))
    WW = int(round(W * 10))
    HH = int(round(H * 100))
    return f"{prefix}{LL:02d}{WW:02d}X{HH:02d}"
