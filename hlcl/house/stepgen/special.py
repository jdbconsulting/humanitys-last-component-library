"""Conservative assembly-envelope models for metal-terminal MLCCs.

KRM55Q outline/feet follow Murata KRM55_25V-100V_E (2025), pp. 4-6.
The hidden ceramic and lead thickness are visual approximations, not tooling
dimensions. The overall envelope and PCB contact plane are authoritative.
"""

from .doc import StepDoc
from .shapes import sharp_box
from . import colors


def metal_terminal(L, W, H, T, footprint_name):
    if min(L, W, H, T) <= 0 or 2*T >= L or H <= 0.4:
        raise ValueError("invalid metal-terminal envelope")
    doc = StepDoc(footprint_name)
    doc.start_product(footprint_name)
    # A raised ceramic with two folded metal leads; contacts sit at z=0.
    ceramic = sharp_box(doc, -L/2+.15, -W/2, .4, L/2-.15, W/2, H, name="Ceramic")
    doc.add_solid(ceramic, colors.MLCC_TAN)
    for sign in (-1, 1):
        outer = sign*L/2
        inner = outer-sign*.15
        lo, hi = sorted((outer, inner))
        end = sharp_box(doc, lo, -W/2, 0, hi, W/2, H-.15, name="Lead")
        doc.add_solid(end, colors.TERMINAL_SILVER)
        lo, hi = sorted((outer, outer-sign*T))
        foot = sharp_box(doc, lo, -W/2, 0, hi, W/2, .15, name="Foot")
        doc.add_solid(foot, colors.TERMINAL_SILVER)
    return doc.serialize()
