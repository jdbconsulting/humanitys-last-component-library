"""Build registration stub for ``house-pcblib`` -- the .PcbLib
autogenerator. Driver is ``house/build_pcblib.py``; the writer
package itself is the sibling ``house/altium_pcblib/``. Consumes the
merged footprints JSON + the parametric .step files, emits
``build/output/house.PcbLib`` with each STEP zlib-embedded so the
.PcbLib is self-contained.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_HOUSE = os.path.normpath(os.path.join(_HERE, ".."))
_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from build import HOUSE, call_main, load_module, register


def _run() -> None:
    mod = load_module(os.path.join(_HOUSE, "build_pcblib.py"))
    rc = call_main(
        mod,
        argv=[
            "--input",    os.path.join(_ROOT, "build", "intermediate", "footprints", "house-footprints.json"),
            "--output",   os.path.join(_ROOT, "build", "output", "house.PcbLib"),
            "--step-dir", os.path.join(_ROOT, "build", "intermediate", "step"),
        ],
    )
    if rc:
        raise SystemExit(rc)


register(
    "house-pcblib",
    kind=HOUSE,
    runner=_run,
    deps=("house-footprints", "house-step-models"),
)
