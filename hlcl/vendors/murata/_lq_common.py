"""
Shared helpers for Murata's two LQ-prefixed chip-inductor family scripts:

* :mod:`vendors.murata.lqm.murata-lqm` -- LQM-series multilayer chip
  inductors (general-purpose / power, 0603-1206 EIA).
* :mod:`vendors.murata.lqw.murata-lqw` -- LQW-series wirewound RF
  inductors (0201-1210 EIA, plus a 1812 outlier we don't ship).

Both families consume the same parts CSV shape produced by
``vendors/murata/scrape_lq_pdfs.py`` (see that script's docstring for
the rationale on why we parse spec PDFs instead of hitting the public
PIM CSV API):

    subseries,mpn,operating_temp_min_c,operating_temp_max_c,jelf_id,
    tokens

This module hosts the bits both LQ family scripts need:

* :data:`SUBSERIES_GEOMETRY` -- per-subseries package geometry.
  Murata's LQ MPNs encode the package L x W in two characters
  (``LQM21*`` -> 2.0 x 1.25 mm, ``LQW18*`` -> 1.6 x 0.8 mm,
  ``LQW2B*`` -> 2.0 x 1.25 mm with a different height than ``LQW21*``,
  etc.), but body Z (height) is set by the subseries' technology
  letters and varies independently. Dimensions sourced from Murata's
  per-subseries reference-spec PDFs and the inductor product-numbering
  reference (`pim.murata.com/asset/pim4/inductor/PARTNUMBERING_LQ3E_PDF_INDUCTOR`).
* :func:`decode_inductance` -- pull the inductance value (uH for
  LQM, nH for LQW) out of the orderable MPN. Murata's part-numbering
  uses three encodings depending on magnitude: a leading-``R`` form
  for sub-unit values (``R47`` -> 0.47), a ``<digit>R<digit>`` form
  for 1-9.x values (``1R0`` -> 1.0), and a JEDEC two-figures-plus-
  zeros form for >=10 (``101`` -> 100, ``150`` -> 15). LQW also uses
  ``N`` in place of ``R`` to flag a nano-henry value (``2N2`` ->
  2.2 nH, ``18N`` -> 18 nH).
* :func:`decode_tolerance` -- single-letter tolerance code -> the
  human-readable ``"+/-X%"`` / ``"+/-X nH"`` form. The mapping is
  documented in the inductor part-numbering reference.
* :func:`format_inductance` -- 1.0 -> ``"1.0uH"``, 0.001 -> ``"1nH"``,
  220.0 -> ``"220uH"``. Mirrors the convention the other vendor
  scripts use to render values in the .xls Description column.
* :func:`row_for_part` -- single-row builder shared by both family
  scripts, returning the ``(row, fp_root, sheet_name)`` tuple ready
  for the .xls writer.
* :func:`build_footprint_rows` -- wraps the standard density-fanout
  helper so each family script just hands in its set of footprint
  roots.
"""

from __future__ import annotations

import os
import re
import sys
from typing import Iterable, Mapping

# Reach up one level (murata/.. == vendors/) so `_common` is importable
# whether the family script is run via `python build.py` or directly.
_HERE = os.path.dirname(os.path.abspath(__file__))
_VENDORS_DIR = os.path.normpath(os.path.join(_HERE, ".."))
if _VENDORS_DIR not in sys.path:
    sys.path.insert(0, _VENDORS_DIR)

import _common  # noqa: E402  -- vendors/_common.py


# --- Manufacturer name ----------------------------------------------------
# Plain "Murata" matches what the other Murata families (GCM, GRM,
# BLM) emit, and what Altium's Part Choices database query expects.
MFG = "Murata"

SCHLIB = r"house.SchLib"
PCBLIB = r"house.PcbLib"


# --- .xls column schema --------------------------------------------------
# Inductor variant of the standard schema. Keeps the same Library /
# Footprint slots as the resistor and capacitor families (so the
# DbLib FieldMap stays uniform), but trades the resistor-specific
# ``Tolerance / Tcr / Voltage / Power`` quartet for the inductor-
# specific ``Inductance / Tolerance / DCR / Current / SRF / Q``
# parameters. Empty cells are tolerated downstream -- LQM rows leave
# Q blank (multilayer LQM doesn't characterise Q on the spec PDFs)
# and LQW rows leave DCR-typ + I-Lchg blank.
HEADERS = [
    "Comment", "Description", "MFG", "MPN", "Package",
    "Inductance", "Tolerance", "DCR", "Current", "SRF", "Q",
    "Tr", "Qual",
    "Library Path", "Library Ref",
    "Footprint Path", "Footprint Ref",
    "Footprint Path 2", "Footprint Ref 2",
    "Footprint Path 3", "Footprint Ref 3",
]


# --- Per-subseries geometry ----------------------------------------------
# Maps the 6 or 7-character "subseries base" (everything before the
# ``_<flavour>`` suffix in the lineup-page subseries id, i.e.
# LQM21PN_GE -> "LQM21PN") to the packaging geometry the .xls/footprint
# scripts care about.
#
# Fields per entry:
#
#   eia          IPC-7351B EIA case-size code (matches the
#                ``available_sizes`` keys throughout the catalog).
#   metric       Metric size code embedded in the IPC footprint root
#                (INDC<metric>X<height>).
#   length_mm,   Body length / width / height in mm.
#   width_mm,    Heights are nominal (max-spec heights from Murata's
#   height_mm    catalog, rounded to the IPC code's two/three digits).
#   terminal_mm  IPC-7351B terminal-band length per IPC-7351B Section 4.2.
#
# Heights vary by structural family letter (the third subseries char):
#   F  film type          0.55 mm (LQM21FN)
#   D  multilayer dual    0.85-0.95 mm (LQM18DN/LQM21DN/LQM2HPN)
#   M  multilayer         0.85-0.90 mm (LQM2MPN)
#   N  multilayer std.    0.55 mm (most LQM_PN)
#   H  high-power multi   1.00 mm (LQM2HPN)
#   P  power multi        0.55-0.95 mm
#   S  super-Q wire       0.5-0.8 mm (LQW18AS, LQW2BAS)
#   T  large-current FT   1.0 mm (LQW21FT)
#   W  wirewound air-core 0.95-1.45 mm (LQM18PW)
#
# When a subseries gets added that isn't here, the build script logs
# an UNKNOWN GEOMETRY warning, drops the part, and continues. Add a
# new entry rather than deleting the warning.

SUBSERIES_GEOMETRY: Mapping[str, dict] = {
    # === LQM multilayer chip inductors (general-purpose / power) =====
    # 0603 EIA / 1608 metric body
    "LQM18DN": {"eia": "0603", "metric": "1608", "length_mm": 1.6, "width_mm": 0.8, "height_mm": 0.95, "terminal_mm": 0.30},
    "LQM18DH": {"eia": "0603", "metric": "1608", "length_mm": 1.6, "width_mm": 0.8, "height_mm": 0.95, "terminal_mm": 0.30},
    "LQM18DZ": {"eia": "0603", "metric": "1608", "length_mm": 1.6, "width_mm": 0.8, "height_mm": 0.95, "terminal_mm": 0.30},
    "LQM18FN": {"eia": "0603", "metric": "1608", "length_mm": 1.6, "width_mm": 0.8, "height_mm": 0.55, "terminal_mm": 0.30},
    "LQM18PN": {"eia": "0603", "metric": "1608", "length_mm": 1.6, "width_mm": 0.8, "height_mm": 0.80, "terminal_mm": 0.30},
    "LQM18PH": {"eia": "0603", "metric": "1608", "length_mm": 1.6, "width_mm": 0.8, "height_mm": 0.80, "terminal_mm": 0.30},
    "LQM18PZ": {"eia": "0603", "metric": "1608", "length_mm": 1.6, "width_mm": 0.8, "height_mm": 0.80, "terminal_mm": 0.30},
    "LQM18PW": {"eia": "0603", "metric": "1608", "length_mm": 1.6, "width_mm": 0.8, "height_mm": 0.95, "terminal_mm": 0.30},
    # 0805 EIA / 2012 metric body
    "LQM21DN": {"eia": "0805", "metric": "2012", "length_mm": 2.0, "width_mm": 1.25, "height_mm": 0.95, "terminal_mm": 0.50},
    "LQM21DH": {"eia": "0805", "metric": "2012", "length_mm": 2.0, "width_mm": 1.25, "height_mm": 0.95, "terminal_mm": 0.50},
    "LQM21FN": {"eia": "0805", "metric": "2012", "length_mm": 2.0, "width_mm": 1.25, "height_mm": 0.55, "terminal_mm": 0.50},
    "LQM21PN": {"eia": "0805", "metric": "2012", "length_mm": 2.0, "width_mm": 1.25, "height_mm": 0.55, "terminal_mm": 0.50},
    "LQM21PH": {"eia": "0805", "metric": "2012", "length_mm": 2.0, "width_mm": 1.25, "height_mm": 0.55, "terminal_mm": 0.50},
    "LQM21PZ": {"eia": "0805", "metric": "2012", "length_mm": 2.0, "width_mm": 1.25, "height_mm": 0.55, "terminal_mm": 0.50},
    "LQM2HPN": {"eia": "0805", "metric": "2012", "length_mm": 2.0, "width_mm": 1.25, "height_mm": 1.00, "terminal_mm": 0.50},
    "LQM2HPH": {"eia": "0805", "metric": "2012", "length_mm": 2.0, "width_mm": 1.25, "height_mm": 1.00, "terminal_mm": 0.50},
    "LQM2HPZ": {"eia": "0805", "metric": "2012", "length_mm": 2.0, "width_mm": 1.25, "height_mm": 1.00, "terminal_mm": 0.50},
    "LQM2MPN": {"eia": "0805", "metric": "2012", "length_mm": 2.0, "width_mm": 1.25, "height_mm": 0.90, "terminal_mm": 0.50},
    "LQM2MPZ": {"eia": "0805", "metric": "2012", "length_mm": 2.0, "width_mm": 1.25, "height_mm": 0.90, "terminal_mm": 0.50},
    # 1206 EIA / 3216 metric body
    "LQM31PN": {"eia": "1206", "metric": "3216", "length_mm": 3.2, "width_mm": 1.6, "height_mm": 1.60, "terminal_mm": 0.60},

    # === LQW wirewound RF inductors ===================================
    # 0201 EIA / 0603 metric body
    "LQW03AW": {"eia": "0201", "metric": "0603", "length_mm": 0.6, "width_mm": 0.3, "height_mm": 0.33, "terminal_mm": 0.15},
    # 0402 EIA / 1005 metric body
    "LQW15AN": {"eia": "0402", "metric": "1005", "length_mm": 1.0, "width_mm": 0.5, "height_mm": 0.50, "terminal_mm": 0.20},
    "LQW15AW": {"eia": "0402", "metric": "1005", "length_mm": 1.0, "width_mm": 0.5, "height_mm": 0.50, "terminal_mm": 0.20},
    "LQW15CN": {"eia": "0402", "metric": "1005", "length_mm": 1.0, "width_mm": 0.5, "height_mm": 0.50, "terminal_mm": 0.20},
    "LQW15CE": {"eia": "0402", "metric": "1005", "length_mm": 1.0, "width_mm": 0.5, "height_mm": 0.50, "terminal_mm": 0.20},
    "LQW15DN": {"eia": "0402", "metric": "1005", "length_mm": 1.0, "width_mm": 0.5, "height_mm": 0.55, "terminal_mm": 0.20},
    # 0603 EIA / 1608 metric body
    "LQW18AN": {"eia": "0603", "metric": "1608", "length_mm": 1.6, "width_mm": 0.8, "height_mm": 0.80, "terminal_mm": 0.30},
    "LQW18AS": {"eia": "0603", "metric": "1608", "length_mm": 1.6, "width_mm": 0.8, "height_mm": 0.80, "terminal_mm": 0.30},
    "LQW18CN": {"eia": "0603", "metric": "1608", "length_mm": 1.6, "width_mm": 0.8, "height_mm": 0.80, "terminal_mm": 0.30},
    # 0805 EIA / 2012 metric body
    "LQW21FT": {"eia": "0805", "metric": "2012", "length_mm": 2.0, "width_mm": 1.25, "height_mm": 1.00, "terminal_mm": 0.50},
    "LQW2BAN": {"eia": "0805", "metric": "2012", "length_mm": 2.0, "width_mm": 1.5, "height_mm": 1.00, "terminal_mm": 0.50},
    "LQW2BAS": {"eia": "0805", "metric": "2012", "length_mm": 2.0, "width_mm": 1.5, "height_mm": 1.00, "terminal_mm": 0.50},
    # 1210 EIA / 3225 metric body
    "LQW32FT": {"eia": "1210", "metric": "3225", "length_mm": 3.2, "width_mm": 2.5, "height_mm": 2.50, "terminal_mm": 0.60},
}


def subseries_base(subseries: str) -> str:
    """``"LQM21PN_GE" -> "LQM21PN"``.  The lineup pages emit the
    fully-qualified subseries (with ``_<flavour>`` suffix); the
    geometry table is keyed on the base form because all flavours
    of one subseries share L/W/H/T."""
    return subseries.split("_", 1)[0]


# --- MPN decoding ---------------------------------------------------------

# Murata LQ inductance value codes (3-char). One of three forms:
#
#   ``R<dd>``                 - leading R = 0.<dd>; e.g. R47 = 0.47.
#   ``<d>R<d>`` / ``<d>N<d>`` - middle R/N = decimal; e.g. 1R0 = 1.0,
#                               2N2 = 2.2 (with N flagging nH unit).
#   ``<dd>N``                 - trailing N = nH unit, value = <dd>;
#                               e.g. 18N = 18 (nH).
#   ``<dd><exp>``             - JEDEC two-figs-plus-exponent;
#                               e.g. 100 = 10x10^0 = 10, 101 = 10x10^1
#                               = 100, 470 = 47x10^0 = 47.
_LQ_VALUE_RE = re.compile(
    r"^(?:R(?P<a1>\d{2})"
    r"|(?P<a2>\d)(?P<dec>[RN])(?P<a3>\d)"
    r"|(?P<a4>\d{2})N"
    r"|(?P<a5>\d{2})(?P<exp>\d))$"
)


def decode_inductance(mpn: str, base: str) -> tuple[float, str] | None:
    """``("LQM21PN1R0MGEL", "LQM21PN") -> (1.0, "uH")``.

    Returns ``(value, unit)`` where ``unit`` is ``"uH"`` for LQM and
    base-LQW values >= 1 (without ``N`` flag), and ``"nH"`` for LQW
    values that carry the ``N`` indicator. Returns ``None`` if the
    code at MPN[len(base):][:3] doesn't match a known form.

    Per Murata's part-numbering reference (LQ3E):
    * LQM uses uH natively (no ``N`` form).
    * LQW uses nH for values < 0.1 uH (encoded with ``N``) and uH
      for >= 0.1 uH (encoded with ``R``); the JEDEC numeric form
      (``100``, ``150`` etc.) takes its unit from the family --
      uH for LQM, nH for LQW.
    """
    family = base[:3]  # "LQM" or "LQW"
    if family not in {"LQM", "LQW"}:
        return None
    code = mpn[len(base):len(base) + 3]
    m = _LQ_VALUE_RE.match(code)
    if not m:
        return None
    if m.group("a1") is not None:                 # R47 -> 0.47
        value = int(m.group("a1")) / 100.0
        unit_marker = "R"
    elif m.group("dec") is not None:              # 1R0 / 2N2 -> 1.0 / 2.2
        value = int(m.group("a2")) + int(m.group("a3")) / 10.0
        unit_marker = m.group("dec")
    elif m.group("a4") is not None:               # 18N -> 18
        value = float(m.group("a4"))
        unit_marker = "N"
    else:                                          # 100 / 101 -> 10 / 100
        value = int(m.group("a5")) * (10 ** int(m.group("exp")))
        unit_marker = "0"

    if family == "LQW":
        # LQW: ``N`` form anywhere in the value -> nH;
        # everything else (R-form or JEDEC) -> uH.
        if unit_marker == "N":
            return float(value), "nH"
        return float(value), "uH"
    # LQM is uH-native; the rare ``N`` form doesn't appear in LQM MPNs.
    return float(value), "uH"


# Murata LQ tolerance code (4th char after the 3-char value code).
# From the part-numbering reference:
TOLERANCE_LETTER: Mapping[str, str] = {
    "B": "+/-0.1nH",
    "C": "+/-0.2nH",
    "D": "+/-0.5nH",
    "F": "+/-1%",
    "G": "+/-2%",
    "H": "+/-3%",
    "J": "+/-5%",
    "K": "+/-10%",
    "M": "+/-20%",
    "N": "+/-30%",
    "S": "+/-0.3nH",
    "W": "+/-0.05nH",
}


def decode_tolerance(mpn: str, base: str) -> str:
    """``("LQM21PN1R0MGEL", "LQM21PN") -> "+/-20%"``. Returns ``""``
    if the byte at the expected tolerance position isn't a known
    code letter -- callers can then fall back to whatever the spec-
    PDF tail tokens carried, but in practice every orderable Murata
    LQ MPN uses one of the documented codes."""
    pos = len(base) + 3
    if pos >= len(mpn):
        return ""
    return TOLERANCE_LETTER.get(mpn[pos], "")


def format_inductance(value: float, unit: str) -> str:
    """``(1.0, "uH") -> "1.0uH"``; ``(2.2, "nH") -> "2.2nH"``;
    ``(220.0, "uH") -> "220uH"``. Strips trailing ``.0`` for integer-
    valued results so the description column reads cleanly."""
    if abs(value - round(value)) < 1e-9:
        text = f"{int(round(value))}"
    else:
        text = f"{value:g}"
    return f"{text}{unit}"


# --- Best-effort decoding of the post-MPN PDF tokens ----------------------

_NUM_RE = re.compile(r"^[\d.]+$")
_DCR_WITH_TOL_RE = re.compile(r"^([\d.]+)±[\d.]+%?$")


def _is_num(tok: str) -> bool:
    return bool(_NUM_RE.match(tok))


def _strip_inline_tol(tok: str) -> str:
    """``"0.07±25%"`` -> ``"0.07"``; ``"1.05±0.32"`` -> ``"1.05"``.
    Some Murata spec PDFs glue the DCR tolerance band onto the DCR
    value as ``"0.07±25%"`` (no spaces), causing pypdf to emit them
    as a single token. Strip the trailing ``±..."`` so callers can
    parse the leading numeric for cataloging."""
    m = _DCR_WITH_TOL_RE.match(tok)
    if m:
        return m.group(1)
    if "±" in tok:
        return tok.split("±", 1)[0]
    return tok


def parse_lqm_tokens(tokens: list[str]) -> dict[str, str]:
    """Best-effort decode of an LQM_ part row's post-MPN tokens.

    The LQM_ spec PDFs use at least four column-layout flavours
    across subseries (full L-change + temperature-rise quartet vs
    truncated max-only doublet, with and without inline DCR
    tolerances; with and without a tolerance-letter column). Rather
    than trying to discriminate per-subseries, we walk the token
    list with a simple state machine: skip the leading inductance +
    tolerance token(s), then peel off DCR / SRF / I_rated by token
    shape (a small float < 50 = DCR; the next number = SRF in MHz;
    one or more trailing currents).

    Returns a dict with possibly-empty ``dcr_max_ohm``,
    ``srf_min_mhz``, ``rated_current_max_ma`` strings."""
    out = {"dcr_max_ohm": "", "srf_min_mhz": "", "rated_current_max_ma": ""}
    if not tokens:
        return out
    # Drop the inductance (token 0) and any tolerance tokens (which
    # are letters or contain ``±``).
    rest: list[str] = []
    for i, t in enumerate(tokens):
        if i == 0:
            continue
        if i == 1 and ("±" in t or t in TOLERANCE_LETTER or t.endswith("%")):
            # Letter-only ("M"), bare ±20, or full ±20% tolerance --
            # all consumed; the tolerance is recovered from the MPN.
            continue
        if i == 2 and (
            "±" in t or t.endswith("%") or t in {":", "：", ":±", "："}
        ):
            # Some flavours print "M ：±20%" with the tol pct in a
            # third token, or just "±20" / "20%" alone.
            continue
        rest.append(t)
    rest = [_strip_inline_tol(t) for t in rest]
    nums = [t for t in rest if _is_num(t)]
    # Heuristic mapping:
    #   nums[0] = DCR_typ (sometimes); nums[1] = DCR_max
    #   following number with magnitude > 5 = SRF (MHz)
    #   then rated currents
    if len(nums) >= 2 and float(nums[0]) < 5 and float(nums[1]) < 5 \
            and float(nums[0]) <= float(nums[1]):
        # DCR_typ + DCR_max layout (LQM_*_GE flavour)
        out["dcr_max_ohm"] = nums[1]
        nums = nums[2:]
    elif nums:
        out["dcr_max_ohm"] = nums[0]
        nums = nums[1:]
    if nums:
        out["srf_min_mhz"] = nums[0]
        nums = nums[1:]
    if nums:
        # First rated-current column is most relevant for cataloging
        # (the temperature-rise-derived max). Track largest seen.
        try:
            largest = max(float(t) for t in nums if _is_num(t))
            out["rated_current_max_ma"] = f"{largest:g}"
        except ValueError:
            pass
    return out


def parse_lqw_tokens(tokens: list[str]) -> dict[str, str]:
    """Best-effort decode of an LQW_ part row's post-MPN tokens.

    LQW_ rows are simpler than LQM_: ``L_nH tol_letter? : tol Q DCR
    SRF I_rated`` is the common form. Q is unique to LQW (wirewound
    RF parts characterise it; multilayer LQM doesn't). Returns
    ``q_min``, ``dcr_max_ohm``, ``srf_min_mhz``, ``rated_current_ma``."""
    out = {
        "q_min": "",
        "dcr_max_ohm": "",
        "srf_min_mhz": "",
        "rated_current_ma": "",
    }
    if not tokens:
        return out
    rest: list[str] = []
    for i, t in enumerate(tokens):
        if i == 0:
            continue
        if i <= 3 and (
            "±" in t or t.endswith(("%", "nH"))
            or t in TOLERANCE_LETTER
            or t in {":", "：", "J:", "K:", "G:", "M:", "D:", "C:", "B:", "F:", "S:", "H:", "W:", "N:"}
        ):
            continue
        rest.append(t)
    rest = [_strip_inline_tol(t) for t in rest]
    nums = [t for t in rest if _is_num(t)]
    # Heuristic:
    #   First number = Q (typ small int < 200).
    #   Second = DCR (small float < 5 ohm typically).
    #   Third = SRF (MHz, typically 100-50000).
    #   Fourth = I_rated (mA, typically 50-2000).
    if nums:
        try:
            v = float(nums[0])
            # If it looks like a Q value (integer-ish, > 5), assume Q.
            # Otherwise, no Q column on this row -- treat as DCR.
            if v == int(v) and v >= 5:
                out["q_min"] = nums[0]
                nums = nums[1:]
        except ValueError:
            pass
    if nums:
        out["dcr_max_ohm"] = nums[0]
        nums = nums[1:]
    if nums:
        out["srf_min_mhz"] = nums[0]
        nums = nums[1:]
    if nums:
        try:
            largest = max(float(t) for t in nums if _is_num(t))
            out["rated_current_ma"] = f"{largest:g}"
        except ValueError:
            pass
    return out


# --- Per-row builder ------------------------------------------------------

def row_for_part(
    csv_row: Mapping[str, str],
    *,
    family_id: str,
    is_lqm: bool,
) -> tuple[list, str, str] | None:
    """Build one .xls row for a CSV row.

    Returns ``(row, fp_root, sheet_name)`` on success, ``None`` if
    the row should be dropped (unknown subseries geometry, undecodable
    MPN, or disabled by the active BuildConfig).

    ``fp_root`` is the IPC root sans density suffix (e.g.
    ``INDC2012X55``). ``sheet_name`` is the per-EIA worksheet the
    row belongs in -- the family scripts spread parts across one
    sheet per EIA so the .DbLib's TableN binding stays readable.
    """
    subseries = csv_row.get("subseries", "").strip()
    base = subseries_base(subseries)
    geom = SUBSERIES_GEOMETRY.get(base)
    if geom is None:
        return None  # subseries we deliberately don't ship
    eia = geom["eia"]
    if eia not in _common.enabled_sizes(family_id):
        return None  # disabled by config

    mpn = csv_row.get("mpn", "").strip()
    if not mpn:
        return None
    decoded = decode_inductance(mpn, base)
    if decoded is None:
        return None
    value, unit = decoded
    tolerance = decode_tolerance(mpn, base)

    height_code = _format_height_code(geom["height_mm"])
    fp_root = f"INDC{geom['metric']}X{height_code}"
    fp_cells = _common.xls_footprint_columns(PCBLIB, fp_root, family_id)

    inductance_str = format_inductance(value, unit)
    description = (
        f"INDUCTOR {'MULTILAYER' if is_lqm else 'WIREWOUND'} "
        f"{inductance_str} {tolerance or 'TOL'} {eia}"
    )

    tokens = (csv_row.get("tokens") or "").split("|") if csv_row.get("tokens") else []
    if is_lqm:
        params = parse_lqm_tokens(tokens)
        dcr = params["dcr_max_ohm"]
        current_ma = params["rated_current_max_ma"]
        srf = params["srf_min_mhz"]
        q = ""
    else:
        params = parse_lqw_tokens(tokens)
        dcr = params["dcr_max_ohm"]
        current_ma = params["rated_current_ma"]
        srf = params["srf_min_mhz"]
        q = params["q_min"]

    tmin = csv_row.get("operating_temp_min_c", "").strip()
    tmax = csv_row.get("operating_temp_max_c", "").strip()
    tr = f"{tmin}:{tmax}" if tmin and tmax else ""

    # AEC-Q200 qualification:
    #
    # * LQM_ flags automotive variants in the 5th-6th characters of the
    #   subseries base (the structural code right after the size digits):
    #   ``LQM21PZ`` / ``LQM21PH`` / ``LQM21DZ`` / ``LQM21DH``, etc.
    #   The ``Z`` suffix on the structural code is Murata's "automotive"
    #   marker; ``H`` is the higher-temperature (also automotive-grade)
    #   variant.
    #
    # * LQW_ flags it in the lineup-id ``_<flavour>`` suffix instead --
    #   commercial = ``_00``/``_10``/``_80``, automotive = ``_0Z`` /
    #   ``_1Z`` / ``_8Z`` / ``_0H`` / ``_2H``. The 4th-5th chars of the
    #   subseries base (``AN`` vs ``CN`` vs ``AS``) are the wirewound
    #   topology code, not an AEC marker.
    family = base[:3]
    if family == "LQM":
        qual = "AEC-Q200" if base[5:7] in {"PZ", "PH", "DZ", "DH"} else ""
    else:  # LQW
        flavour = subseries.split("_", 1)[1] if "_" in subseries else ""
        qual = "AEC-Q200" if any(c in flavour for c in "ZH") else ""

    row = [
        mpn,                          # Comment
        description,                  # Description
        MFG,                          # MFG
        mpn,                          # MPN
        eia,                          # Package
        inductance_str,               # Inductance
        tolerance,                    # Tolerance
        f"{dcr}\u03A9" if dcr else "",  # DCR (ohm symbol)
        f"{current_ma}mA" if current_ma else "",  # Current
        f"{srf}MHz" if srf else "",   # SRF
        q,                            # Q
        tr,                           # Tr
        qual,                         # Qual
        SCHLIB, "INDUCTOR",           # Library Path / Ref
    ] + fp_cells

    sheet_name = f"{family_id.split('-')[1].upper()}{eia}"
    return row, fp_root, sheet_name


def _format_height_code(h_mm: float) -> str:
    """``0.55 -> "55"``, ``1.0 -> "100"``, ``2.5 -> "250"``. Mirrors
    :func:`vendors.murata.blm.murata-ferrite._format_height_code` so the
    LQ INDC roots collide cleanly with the BLM ones whenever the
    height matches (e.g. INDC1608X80)."""
    val = round(h_mm * 100)
    if val < 0:
        raise ValueError(f"height must be non-negative (got {h_mm!r})")
    if val >= 100:
        return str(val)
    return f"{val:02d}"


# --- Per-vendor footprints JSON helper ------------------------------------

def build_footprint_rows(
    roots_with_subseries: Iterable[tuple[str, str]],
    family_id: str,
    drawing_note: str,
) -> list:
    """Expand a list of ``(fp_root, subseries_base)`` pairs into one
    JSON row per family-resolved density. The subseries base is used
    only to recover body LxWxH/T from :data:`SUBSERIES_GEOMETRY`;
    we accept it (rather than re-deriving it from the root) because
    multiple subseries can share an INDC root and we want to record
    the geometry of whichever one's row produced the root first."""
    seen = set()
    bodies = []
    for root, base in roots_with_subseries:
        if root in seen:
            continue
        seen.add(root)
        geom = SUBSERIES_GEOMETRY[base]
        bodies.append(
            {
                "root": root,
                "kind": "I",
                "drawingNote": drawing_note,
                "bodyMm": {
                    "lengthNominal":         geom["length_mm"],
                    "widthNominal":          geom["width_mm"],
                    "heightNominal":         geom["height_mm"],
                    "terminalLengthNominal": geom["terminal_mm"],
                },
            }
        )
    return _common.expand_footprint_rows(bodies, family_id)
