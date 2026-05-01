"""
Pure-Python parametric STEP file generator for two-terminal chip
component bodies (CAPC, RESC, INDC).

Public API:

    from stepgen import capc, resc, indc

    step_text = capc(L=1.0, W=0.5, H=0.5, T=0.2)  # returns STEP file as str
    open("CAPC1005X05N.step", "w").write(step_text)

The generator's design constraints:

* Pure stdlib -- no CadQuery / OCP / FreeCAD dependency. Designed so
  the same module can run unmodified in Pyodide (browser) for a future
  open-source web UI.
* Output is ASCII STEP (AP214 ``AUTOMOTIVE_DESIGN``, mm units, B-rep
  solids), compatible with the Open CASCADE-based reader Altium uses.
* Three component families today (CAPC / RESC / INDC); the body
  topology is "rectangular box with rounded edges" in all three, with
  per-family layering and colour distinctions.

Phase 1 (sharp-edged boxes) is the first cut so the .pcblib pipeline
can be exercised end-to-end. Phase 2 will replace ``sharp_box`` in
``shapes`` with a full filleted-box B-rep (cylindrical edge fillets +
spherical corner octants). The high-level chip generators below won't
change.
"""

from . import colors
from .chip import capc, indc, resc
from .doc import StepDoc
from .shapes import DEFAULT_FILLET_RADIUS_MM, filleted_box, sharp_box

__all__ = [
    "capc",
    "indc",
    "resc",
    "StepDoc",
    "sharp_box",
    "filleted_box",
    "DEFAULT_FILLET_RADIUS_MM",
    "colors",
]
