"""Build registration stub for the Murata BLM ferrite-bead family.

The target name is ``murata-ferrites`` (plural) -- legacy alias kept
from the original top-level Makefile target. The generator script
basename is the singular ``murata-ferrite.py``.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from build import VENDOR, call_main, load_module, register


def _run() -> None:
    mod = load_module(os.path.join(_HERE, "murata-ferrite.py"))
    rc = call_main(mod)
    if rc:
        raise SystemExit(rc)


register("murata-ferrites", kind=VENDOR, runner=_run)
