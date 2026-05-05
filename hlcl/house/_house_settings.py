"""
Compatibility shim re-exporting the user-tunable IPC / HLCL / 3D / colour
settings as the dataclass tree the modules under ``house/`` already
import. The single source of truth is now :mod:`hlcl._config` (which
loads + validates the JSON ``BuildConfig``); this module is kept as a
short-named alias so existing ``from _house_settings import SETTINGS``
imports keep working with zero diff.

Why a shim instead of editing the consumers
-------------------------------------------
Every house module pulls a handful of values out of ``SETTINGS`` at
*import* time and binds them to module-level constants (e.g.
``PAD_CORNER_RADIUS_PERCENT = SETTINGS.hlcl.pad_corner_radius_percent``
in ``altium_pcblib/hlcl.py``). That pattern is fine as long as the
config is set before those modules import. The orchestrator
(``hlcl/build.py``) explicitly calls :func:`hlcl._config.set_current`
before running any target, so the import-time captures see a populated
config. Direct script invocations (``python house/build_pcblib.py``)
trigger :func:`hlcl._config.bootstrap` via the import below, which
finds ``--config`` in ``sys.argv`` (peeling it off so the script's own
argparse doesn't choke) or falls back to ``hlcl/factory-defaults.json``.

Failure mode
------------
Same as the old TOML loader — if no config is available, the import
raises immediately rather than silently using compiled-in defaults.
The error message points at the missing ``--config`` flag and the
expected ``factory-defaults.json`` path so the fix is obvious.

Field translation
-----------------
The ``SETTINGS.colors.*`` namespace is FLATTER than the JSON
``settings.colors.{capc,indc,fb,resc,default}.*`` shape — house code
expects ``SETTINGS.colors.capc_body`` rather than
``SETTINGS.colors.capc.body``. The flattening lives in
:func:`hlcl._config._parse_settings`, so no consumer touches a nested
table here.
"""

from __future__ import annotations

import os
import sys

# `hlcl/` (the directory that contains _config.py) is added to sys.path
# by every _build.py stub before they `from build import ...`, so we can
# rely on the same ambient path here without an extra setup. Direct
# `python house/<script>.py` invocations don't run _build.py first
# though, so we add the parent of THIS file's parent (== `hlcl/`) just
# in case.
_HERE = os.path.dirname(os.path.abspath(__file__))
_HLCL_ROOT = os.path.dirname(_HERE)
if _HLCL_ROOT not in sys.path:
    sys.path.insert(0, _HLCL_ROOT)

import _config  # noqa: E402

# Trigger bootstrap immediately so the SETTINGS binding below resolves.
# `_config.bootstrap()` is idempotent: if `set_current` has already been
# called (the orchestrated path), it's a no-op; otherwise it consumes
# `--config <path>` off `sys.argv` or loads `factory-defaults.json`.
_CFG = _config.bootstrap()

# Re-export the dataclass types so any caller that used to do
# `from _house_settings import HouseSettings` (or `IpcSettings`, etc.)
# can keep doing so. The tree is now defined in :mod:`hlcl._config`;
# this re-export preserves the old import surface verbatim.
from _config import (  # noqa: E402, F401
    ColorSettings,
    HlclSettings,
    IpcSettings,
    Rgb,
    Settings as HouseSettings,
    StepGenSettings,
)

#: The eagerly-loaded settings consumed by the rest of ``house/``.
#: Identical shape to the previous TOML-driven version: every existing
#: ``SETTINGS.<section>.<field>`` access keeps working.
SETTINGS: HouseSettings = _CFG.settings
