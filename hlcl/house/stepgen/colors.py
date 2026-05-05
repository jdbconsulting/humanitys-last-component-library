"""
Named RGB colors used by the chip-body 3D model generator.

All values are 3-tuples of floats in [0.0 .. 1.0], matching the STEP
``COLOUR_RGB`` convention. They are derived from the 24-bit-int
[0..255] palette in ``settings.colors.*`` of the active
:class:`hlcl._config.BuildConfig` by dividing each channel by 255.0;
the same int-RGB triples also feed
``house/altium_pcblib/footprint.py``'s BodyColor3D 24-bit packing,
so Altium's 2D and 3D views always agree on the chip's colour.
"""

from _house_settings import SETTINGS


def _to_float_rgb(int_rgb):
    """Convert an int [0..255] RGB triple from the active BuildConfig
    to the float [0..1] tuple STEP's COLOUR_RGB requires."""
    r, g, b = int_rgb
    return (r / 255.0, g / 255.0, b / 255.0)


# --- CAPC (multi-layer ceramic capacitor) -----------------------------------

#: MLCC body (cream/tan ceramic). Default int-RGB (184, 134, 11) ~= #B7860B.
MLCC_TAN = _to_float_rgb(SETTINGS.colors.capc_body)


# --- INDC (chip inductor / ferrite bead) ------------------------------------

#: Ferrite-blue chip inductor body. Default int-RGB (38, 77, 148) ~= #264D94.
INDC_BLUE = _to_float_rgb(SETTINGS.colors.indc_body)


# --- RESC (chip resistor) ---------------------------------------------------
#
# Three colors per resistor: a mid-grey alumina substrate, a near-black
# passivation cover sitting on top of it, and slightly-darker-grey end caps
# for the terminals so they're visible against the substrate.

#: Alumina substrate (resistor base). Mid grey.
RESC_SUBSTRATE_GREY = _to_float_rgb(SETTINGS.colors.resc_substrate)

#: Passivation / circuit cover on top of the resistor's substrate.
#: Near-black, the colour you usually see on the top face of a real chip
#: resistor.
RESC_PASSIVATION_BLACK = _to_float_rgb(SETTINGS.colors.resc_passivation)

#: Resistor end-cap terminals. Distinctly darker than the substrate so the
#: contrast is visible in 3D view.
RESC_TERMINAL_DARK_GREY = _to_float_rgb(SETTINGS.colors.resc_terminal)


# --- Common terminal colour (CAPC + INDC) ----------------------------------

#: Default terminal cap colour for non-resistor chips. Sn-plated finish.
#: Both CAPC and INDC families use this; FB inherits via INDC.
TERMINAL_SILVER = _to_float_rgb(SETTINGS.colors.capc_terminal)


def to_int_rgb(rgb):
    """Convert a (r, g, b) tuple in [0..1] to a 24-bit packed int 0xRRGGBB."""
    r, g, b = rgb
    return (
        (max(0, min(255, round(r * 255))) << 16) |
        (max(0, min(255, round(g * 255))) <<  8) |
        (max(0, min(255, round(b * 255))) <<  0)
    )
