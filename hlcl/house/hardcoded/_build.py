"""Build registration stub for ``house-schlib`` -- copies the
hand-maintained ``house/hardcoded/house.SchLib`` into
``build/output/`` so it sits next to every per-vendor ``.DbLib``
that references it via ``LibrarySearchPath=.``. The .SchLib is the
only "user-facing" artifact in the build that isn't programmatically
generated -- there's no Python SchLib writer yet.
"""

import os
import shutil
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from build import HOUSE, register


def _run() -> None:
    src = os.path.join(_HERE, "house.SchLib")
    dst = os.path.join(_ROOT, "build", "output", "house.SchLib")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy(src, dst)
    print(f"Copied {src} -> {dst}", file=sys.stderr)


register("house-schlib", kind=HOUSE, runner=_run)
