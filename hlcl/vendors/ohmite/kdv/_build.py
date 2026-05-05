"""Build registration stub for the Ohmite KDV current-sense resistor family."""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from build import VENDOR, call_main, load_module, register


def _run() -> None:
    mod = load_module(os.path.join(_HERE, "ohmite-kdv.py"))
    rc = call_main(mod)
    if rc:
        raise SystemExit(rc)


register("ohmite-kdv", kind=VENDOR, runner=_run)
