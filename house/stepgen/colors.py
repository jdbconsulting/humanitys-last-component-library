"""
Named RGB colors used by the chip-body 3D model generator.

All values are 3-tuples of floats in [0.0 .. 1.0], matching the STEP
``COLOUR_RGB`` convention. The same colors are also written into the
matching ``PcbComponentBody.BodyColor3D`` 24-bit RGB field on the C# side
so Altium's 2D and 3D views agree.
"""


# --- CAPC (multi-layer ceramic capacitor) -----------------------------------

#: MLCC body (cream/tan ceramic). Matches the value Altium's IPC Compliant
#: Footprint Wizard writes for chip caps in the existing ``house/step/*.step``
#: reference files (#B78600).
MLCC_TAN = (0.722, 0.525, 0.043)


# --- INDC (chip inductor / ferrite bead) ------------------------------------

#: Ferrite-blue chip inductor body. Approximate but recognisable.
INDC_BLUE = (0.150, 0.300, 0.580)


# --- RESC (chip resistor) ---------------------------------------------------
#
# Three colors per resistor: a mid-grey alumina substrate, a near-black
# passivation cover sitting on top of it, and slightly-darker-grey end caps
# for the terminals so they're visible against the substrate.

#: Alumina substrate (resistor base). Mid grey.
RESC_SUBSTRATE_GREY = (0.620, 0.620, 0.620)

#: Passivation / circuit cover on top of the resistor's substrate.
#: Near-black, the colour you usually see on the top face of a real chip
#: resistor.
RESC_PASSIVATION_BLACK = (0.090, 0.090, 0.090)

#: Resistor end-cap terminals. Distinctly darker than the substrate so the
#: contrast is visible in 3D view.
RESC_TERMINAL_DARK_GREY = (0.500, 0.500, 0.500)


# --- Common terminal colour (CAPC + INDC) ----------------------------------

#: Default terminal cap colour for non-resistor chips. Sn-plated finish.
TERMINAL_SILVER = (0.800, 0.800, 0.800)


def to_int_rgb(rgb):
    """Convert a (r, g, b) tuple in [0..1] to a 24-bit packed int 0xRRGGBB."""
    r, g, b = rgb
    return (
        (max(0, min(255, round(r * 255))) << 16) |
        (max(0, min(255, round(g * 255))) <<  8) |
        (max(0, min(255, round(b * 255))) <<  0)
    )
