"""Render the HLCL-001 standards templates against the active
:class:`hlcl._config.BuildConfig`.

The templates (``standards.tex`` and ``standards.md``) live in
``docs/standards/`` next to the project's ECAD reference screenshots
and use a custom ``@@VAR@@`` placeholder syntax (rather than Python's
:mod:`string.Template` ``$VAR``) to avoid colliding with LaTeX math
mode delimiters. Each ``@@KEY@@`` token is replaced with the result
of :func:`render_variables`; unknown tokens raise ``KeyError`` so a
typo in a template doesn't ship to the user as a half-rendered file.

Both templates accept the same variable set, so the rendering
pipeline is template-agnostic apart from the source file selection.
"""

from __future__ import annotations

import os
import re
from typing import Mapping

import _config

# Regex for the ``@@KEY@@`` placeholder. ``KEY`` is one or more
# uppercase letters, digits, or underscores. Anchoring the prefix /
# suffix to the literal ``@@`` keeps the substitution well-defined
# even if a template happens to contain a single ``@`` for some
# unrelated reason.
_PLACEHOLDER = re.compile(r"@@([A-Z0-9_]+)@@")

# mm <-> mil conversion factor. 1 mm = 1000 / 25.4 = 39.37007874… mil.
_MIL_PER_MM = 1000.0 / 25.4


def _fmt_mm(value: float) -> str:
    """Format a millimetre dimension. Trailing zeros are dropped, but a
    leading 0 is preserved so ``0.05`` stays as ``0.05`` (not ``.05``).
    Integer-valued mm dimensions render without a decimal point so e.g.
    a 0 standoff reads as ``0`` rather than ``0.0``.
    """
    if value == int(value):
        return str(int(value))
    # Six places is enough for any setting we expose; trim trailing
    # zeros after formatting so 0.050000 -> 0.05.
    s = f"{value:.6f}".rstrip("0").rstrip(".")
    return s if s else "0"


def _fmt_mil(mm_value: float) -> str:
    """Convert a millimetre value to mils, rounded to two decimal
    places. Matches the existing wording in the published HLCL-001
    standard (``0.05 mm (1.97 mil)``)."""
    mil = mm_value * _MIL_PER_MM
    return f"{mil:.2f}"


def render_variables(cfg: _config.BuildConfig) -> Mapping[str, str]:
    """Build the mapping of placeholder name -> formatted value for
    the currently-active config.

    Every value the configurator exposes for *drawing standards*
    (HlclSettings + the ``stepgen`` default fillet radius) gets a
    placeholder here. Vendor-driven values (per-family densities /
    sizes / pad-radius overrides, the colour palette, the IPC
    fab/placement tolerances) are intentionally NOT templated because
    the published standard's prose discusses them generically rather
    than quoting a specific number.
    """
    h = cfg.settings.hlcl
    s = cfg.settings.stepgen
    return {
        "PAD_CORNER_RADIUS_PERCENT": str(int(h.pad_corner_radius_percent)),
        "SOLDER_MASK_EXPANSION_MM": _fmt_mm(h.solder_mask_expansion_mm),
        "SOLDER_MASK_EXPANSION_MIL": _fmt_mil(h.solder_mask_expansion_mm),
        "MIN_SOLDER_MASK_SLIVER_MM": _fmt_mm(h.min_solder_mask_sliver_mm),
        "OUTLINE_LINE_WIDTH_MM": _fmt_mm(h.outline_line_width_mm),
        "MAX_CROSSHAIR_HALF_ARM_MM": _fmt_mm(h.max_crosshair_half_arm_mm),
        "MAX_CROSSHAIR_FULL_LENGTH_MM": _fmt_mm(h.max_crosshair_half_arm_mm * 2.0),
        "COMPONENT_BODY_STANDOFF_MM": _fmt_mm(h.component_body_standoff_mm),
        "DEFAULT_FILLET_RADIUS_MM": _fmt_mm(s.default_fillet_radius_mm),
    }


def substitute(template: str, variables: Mapping[str, str]) -> str:
    """Replace every ``@@KEY@@`` token in ``template`` with
    ``variables[KEY]``. Raises ``KeyError`` (with the offending key)
    on the first unknown token -- a typo in the template should fail
    the build loudly rather than ship a half-rendered file."""
    def repl(match: "re.Match[str]") -> str:
        key = match.group(1)
        if key not in variables:
            raise KeyError(f"unknown @@{key}@@ placeholder in template")
        return variables[key]
    return _PLACEHOLDER.sub(repl, template)


def find_template(filename: str, hlcl_root: str) -> str:
    """Locate the source template ``filename`` (one of
    ``standards.tex`` / ``standards.md``) on disk.

    Two well-known locations are tried in order:

      1. ``<hlcl_root>/standards/<filename>`` -- the path the Vite
         plugin packs the docs/standards/ templates to in the Pyodide
         build-inputs tarball.
      2. ``<hlcl_root>/../docs/standards/<filename>`` -- the canonical
         project-root location used by the host CLI build.

    Raises ``FileNotFoundError`` if neither candidate exists; that's
    a coordination bug between this script and the Vite plugin /
    project layout, not a user error.
    """
    candidates = [
        os.path.join(hlcl_root, "standards", filename),
        os.path.join(os.path.dirname(hlcl_root), "docs", "standards", filename),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    raise FileNotFoundError(
        f"could not locate {filename!r}; tried: {candidates}"
    )


def render_template(filename: str, hlcl_root: str, cfg: _config.BuildConfig) -> str:
    """Locate, read, and substitute the named template. Returns the
    fully-populated text ready to be written to the build output."""
    src = find_template(filename, hlcl_root)
    with open(src, "r", encoding="utf-8") as f:
        text = f.read()
    return substitute(text, render_variables(cfg))
