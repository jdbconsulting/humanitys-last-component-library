"""
Single source of truth for the user-tunable IPC / HLCL / 3D / colour
parameters consumed by the modules under ``house/``.

The values live in ``house/settings.toml`` (the same file that
configures ``house_footprints.priority`` for the merge step). This
module loads + validates that file once at import time and exposes a
frozen ``SETTINGS`` dataclass tree that the rest of ``house/`` reads
from.

Failure mode: by repo policy, missing or malformed settings are a
build error -- this module raises immediately rather than silently
falling back to compiled-in defaults. That way an out-of-date
``settings.toml`` can never produce a partially-correct .PcbLib that
nobody catches.

Resolution: the file is found by walking up from this module's own
location, so the loader works regardless of cwd or how the script
that triggered the import was invoked.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from typing import Any, Mapping, Tuple

Rgb = Tuple[int, int, int]


# ---------------------------------------------------------------------------
# Dataclasses (one per [section] in settings.toml)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IpcSettings:
    """[ipc] -- IPC-7351B §3.1.4 fab + placement tolerances."""

    fabrication_tolerance_mm: float
    placement_tolerance_mm: float


@dataclass(frozen=True)
class HlclSettings:
    """[hlcl] -- HLCL-001 (Humanity's Last Component Library)
    drawing-standard constants."""

    pad_corner_radius_percent: int
    solder_mask_expansion_mm: float
    min_solder_mask_sliver_mm: float
    outline_line_width_mm: float
    max_crosshair_half_arm_mm: float
    component_body_standoff_mm: float


@dataclass(frozen=True)
class StepGenSettings:
    """[stepgen] -- 3D body geometry knobs."""

    default_fillet_radius_mm: float
    resc_metal_thickness_fraction: float
    resc_metal_thickness_floor_mm: float


@dataclass(frozen=True)
class ColorSettings:
    """[colors.*] -- per-family RGB palette (24-bit ints, [0..255])."""

    default_body: Rgb
    capc_body: Rgb
    capc_terminal: Rgb
    indc_body: Rgb
    indc_terminal: Rgb
    fb_body: Rgb
    fb_terminal: Rgb
    resc_substrate: Rgb
    resc_passivation: Rgb
    resc_terminal: Rgb


@dataclass(frozen=True)
class HouseSettings:
    """Top-level container for everything ``house/`` reads from
    ``settings.toml``."""

    source_path: str
    ipc: IpcSettings
    hlcl: HlclSettings
    stepgen: StepGenSettings
    colors: ColorSettings


# ---------------------------------------------------------------------------
# Loader + validator
# ---------------------------------------------------------------------------


_HERE = os.path.dirname(os.path.abspath(__file__))


def _find_settings_toml() -> str:
    """Walk up from this module's directory until a ``settings.toml``
    is found. Normally that's ``house/settings.toml`` (this module's
    own folder, found in the first iteration). The walk-up is kept
    for robustness in case the file ever moves up the tree again --
    caller's cwd has no effect on the result either way."""
    cur = _HERE
    while True:
        candidate = os.path.join(cur, "settings.toml")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(cur)
        if parent == cur:
            raise FileNotFoundError(
                f"settings.toml not found at or above {_HERE}; the "
                "house/ scripts can't run without it. The expected "
                "location is house/settings.toml."
            )
        cur = parent


def _require(table: Mapping[str, Any], key: str, where: str) -> Any:
    if key not in table:
        raise KeyError(
            f"settings.toml: missing required key '{where}.{key}' "
            f"(or '{key}' if {where!r} is the top level)"
        )
    return table[key]


def _require_table(parent: Mapping[str, Any], key: str, where: str) -> Mapping[str, Any]:
    val = _require(parent, key, where)
    if not isinstance(val, dict):
        raise TypeError(
            f"settings.toml: '{where + '.' if where else ''}{key}' must be a "
            f"table/section (got {type(val).__name__})"
        )
    return val


def _require_number(table: Mapping[str, Any], key: str, where: str) -> float:
    val = _require(table, key, where)
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise TypeError(
            f"settings.toml: '{where}.{key}' must be a number (got {type(val).__name__})"
        )
    return float(val)


def _require_int(table: Mapping[str, Any], key: str, where: str) -> int:
    val = _require(table, key, where)
    if isinstance(val, bool) or not isinstance(val, int):
        raise TypeError(
            f"settings.toml: '{where}.{key}' must be an integer (got {type(val).__name__})"
        )
    return val


def _require_rgb(table: Mapping[str, Any], key: str, where: str) -> Rgb:
    val = _require(table, key, where)
    where_full = f"{where}.{key}"
    if not isinstance(val, list) or len(val) != 3:
        raise TypeError(
            f"settings.toml: '{where_full}' must be a 3-element list "
            f"of integers in [0..255] (got {val!r})"
        )
    out: list[int] = []
    for i, x in enumerate(val):
        if isinstance(x, bool) or not isinstance(x, int):
            raise TypeError(
                f"settings.toml: '{where_full}[{i}]' must be an integer "
                f"in [0..255] (got {type(x).__name__})"
            )
        if not 0 <= x <= 255:
            raise ValueError(
                f"settings.toml: '{where_full}[{i}]' must be in [0..255] "
                f"(got {x})"
            )
        out.append(x)
    return (out[0], out[1], out[2])


def _load_ipc(cfg: Mapping[str, Any]) -> IpcSettings:
    t = _require_table(cfg, "ipc", "")
    return IpcSettings(
        fabrication_tolerance_mm=_require_number(t, "fabrication_tolerance_mm", "ipc"),
        placement_tolerance_mm=_require_number(t, "placement_tolerance_mm", "ipc"),
    )


def _load_hlcl(cfg: Mapping[str, Any]) -> HlclSettings:
    t = _require_table(cfg, "hlcl", "")
    return HlclSettings(
        pad_corner_radius_percent=_require_int(t, "pad_corner_radius_percent", "hlcl"),
        solder_mask_expansion_mm=_require_number(t, "solder_mask_expansion_mm", "hlcl"),
        min_solder_mask_sliver_mm=_require_number(t, "min_solder_mask_sliver_mm", "hlcl"),
        outline_line_width_mm=_require_number(t, "outline_line_width_mm", "hlcl"),
        max_crosshair_half_arm_mm=_require_number(t, "max_crosshair_half_arm_mm", "hlcl"),
        component_body_standoff_mm=_require_number(t, "component_body_standoff_mm", "hlcl"),
    )


def _load_stepgen(cfg: Mapping[str, Any]) -> StepGenSettings:
    t = _require_table(cfg, "stepgen", "")
    return StepGenSettings(
        default_fillet_radius_mm=_require_number(t, "default_fillet_radius_mm", "stepgen"),
        resc_metal_thickness_fraction=_require_number(t, "resc_metal_thickness_fraction", "stepgen"),
        resc_metal_thickness_floor_mm=_require_number(t, "resc_metal_thickness_floor_mm", "stepgen"),
    )


def _load_colors(cfg: Mapping[str, Any]) -> ColorSettings:
    colors = _require_table(cfg, "colors", "")
    default = _require_table(colors, "default", "colors")
    capc    = _require_table(colors, "capc",    "colors")
    indc    = _require_table(colors, "indc",    "colors")
    fb      = _require_table(colors, "fb",      "colors")
    resc    = _require_table(colors, "resc",    "colors")
    return ColorSettings(
        default_body     = _require_rgb(default, "body",        "colors.default"),
        capc_body        = _require_rgb(capc,    "body",        "colors.capc"),
        capc_terminal    = _require_rgb(capc,    "terminal",    "colors.capc"),
        indc_body        = _require_rgb(indc,    "body",        "colors.indc"),
        indc_terminal    = _require_rgb(indc,    "terminal",    "colors.indc"),
        fb_body          = _require_rgb(fb,      "body",        "colors.fb"),
        fb_terminal      = _require_rgb(fb,      "terminal",    "colors.fb"),
        resc_substrate   = _require_rgb(resc,    "substrate",   "colors.resc"),
        resc_passivation = _require_rgb(resc,    "passivation", "colors.resc"),
        resc_terminal    = _require_rgb(resc,    "terminal",    "colors.resc"),
    )


def load_settings(path: str | None = None) -> HouseSettings:
    """Load + validate ``settings.toml`` and return a HouseSettings.

    Raises FileNotFoundError if the file is missing, and KeyError /
    TypeError / ValueError with a precise dotted path if any required
    field is missing or malformed. By design, no silent fallbacks.
    """
    settings_path = path if path is not None else _find_settings_toml()
    with open(settings_path, "rb") as f:
        cfg = tomllib.load(f)
    return HouseSettings(
        source_path = settings_path,
        ipc         = _load_ipc(cfg),
        hlcl        = _load_hlcl(cfg),
        stepgen     = _load_stepgen(cfg),
        colors      = _load_colors(cfg),
    )


#: Eagerly-loaded singleton consumed by the rest of ``house/``. Loaded
#: at import time so a malformed settings.toml fails the build at the
#: first import of any consuming module rather than only when a
#: specific code path runs.
SETTINGS: HouseSettings = load_settings()
