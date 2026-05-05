"""Build registration stub for ``house-step-models`` -- the parametric
STEP 3D model generator. Reads
``build/intermediate/footprints/house-footprints.json`` and emits one
.step file per unique footprint root into
``build/intermediate/step/*.step``. Pure-stdlib Python so the same
module runs unchanged inside Pyodide.
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
    mod = load_module(os.path.join(_HOUSE, "build_step_models.py"))
    rc = call_main(mod)
    if rc:
        raise SystemExit(rc)


register("house-step-models", kind=HOUSE, runner=_run, deps=("house-footprints",))
