"""Build registration stub for the Yageo RC (general-purpose thick-film)
resistor family.

Auto-discovered by ``build.py`` via ``vendors/*/*/_build.py`` glob.
The actual generator lives in the dashed-basename sibling
``yageo-rc.py``, loaded here through ``importlib`` since dashed
filenames can't be ``import``ed by name.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from build import VENDOR, call_main, load_module, register


def _run() -> None:
    mod = load_module(os.path.join(_HERE, "yageo-rc.py"))
    rc = call_main(mod)
    if rc:
        raise SystemExit(rc)


register("yageo-rc", kind=VENDOR, runner=_run)
