"""Build registration stub for ``house-footprints`` -- the merge step
that consumes every per-vendor ``<vendor>-footprints.json`` and writes
``build/intermediate/footprints/house-footprints.json`` (priority
resolution per ``settings.house_footprints.priority`` in the active
:class:`hlcl._config.BuildConfig`).

Its ``@vendors`` dep expands at run time to every registered vendor
target, so adding a new ``vendors/<mfg>/<family>/_build.py`` is
automatically picked up as a prerequisite of the merge.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from build import ALL_VENDORS, HOUSE, call_main, load_module, register


def _run() -> None:
    mod = load_module(os.path.join(_HERE, "build_house_footprints.py"))
    rc = call_main(mod)
    if rc:
        raise SystemExit(rc)


register("house-footprints", kind=HOUSE, runner=_run, deps=(ALL_VENDORS,))
