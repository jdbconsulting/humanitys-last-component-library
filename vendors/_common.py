"""
Shared helper for the per-vendor footprint generators.

Each vendor's generator script (``vendors/<vendor>/<vendor>-*.py``) ends
with a call to ``write_footprints_json`` to publish the unique
CAPC / RESC / INDC footprints it requires into
``build/intermediate/footprints/<vendor>-footprints.json``. The
downstream pipeline consumes those JSON files in two places:

  1. ``house/build_house_footprints.py`` merges every
     ``build/intermediate/footprints/*-footprints.json`` into a
     single ``build/intermediate/footprints/house-footprints.json``
     (priority resolution per ``settings.toml``).

  2. ``house/build_step_models.py`` and ``house/build_pcblib.py``
     read the merged JSON to emit parametric STEP 3D models and the
     final ``build/output/house.PcbLib`` respectively.

In addition to ``write_footprints_json``, importing this module
monkey-patches a long-standing xlwt bug that made every database
``.xls`` we emit unreadable by Altium until a human opened the file
in Excel first. See ``_apply_xlwt_writeaccess_patch`` below for the
gory details. Every vendor script imports this module before it
calls ``Workbook.save``, so the fix is applied in one place.
"""

from __future__ import annotations

import json
import os
import re
from typing import Iterable, Mapping

#: JSON schema version. Bump (and update the readers) when fields
#: change shape. Adding optional fields is fine without a bump as long
#: as readers tolerate missing keys.
SCHEMA_VERSION = 1

#: Recognised footprint name prefix -> chip kind code stored in the
#: JSON. The downstream STEP generator branches on ``kind`` to pick
#: the right body topology and colour palette.
PREFIX_TO_KIND = {
    "CAPC": "C",   # chip ceramic capacitor
    "RESC": "R",   # chip resistor
    "INDC": "I",   # chip inductor
    # Ferrite beads share the chip-inductor footprint family but get
    # their own kind so the STEP generator can colour them differently.
    "INDCFB": "FB",
}
_FOOTPRINT_NAME_RE = re.compile(r"^(?P<prefix>CAPC|RESC|INDC)\d{4}X\d+(?P<density>[LMN])$")

#: Permitted density-level codes. Mirrors IPC-7351B's L (Least), N
#: (Nominal), M (Most) labels.
_VALID_DENSITY = frozenset("LNM")


def _validate_footprint(fp: Mapping) -> None:
    """Cheap sanity check on a footprint dict before serialising. Errors
    are programmer mistakes in the calling vendor script, so we raise
    rather than silently emitting bad JSON."""
    name = fp.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError(f"footprint missing 'name': {fp!r}")
    m = _FOOTPRINT_NAME_RE.match(name)
    if not m:
        raise ValueError(
            f"footprint {name!r}: name must match CAPC|RESC|INDC + LLWW + X + HH + L|N|M"
        )

    kind = fp.get("kind")
    if kind not in {"C", "R", "I", "FB"}:
        raise ValueError(f"footprint {name!r}: kind must be C/R/I/FB (got {kind!r})")

    density = fp.get("density")
    if density not in _VALID_DENSITY:
        raise ValueError(f"footprint {name!r}: density must be L/N/M (got {density!r})")
    if density != m.group("density"):
        raise ValueError(
            f"footprint {name!r}: density field {density!r} disagrees with name suffix {m.group('density')!r}"
        )

    body = fp.get("bodyMm") or {}
    for key in ("lengthNominal", "widthNominal", "heightNominal", "terminalLengthNominal"):
        v = body.get(key)
        if not isinstance(v, (int, float)) or v <= 0:
            raise ValueError(
                f"footprint {name!r}: bodyMm.{key} must be a positive number (got {v!r})"
            )


def write_footprints_json(
    path: str,
    vendor: str,
    footprints: Iterable[Mapping],
) -> None:
    """Emit a ``<vendor>-footprints.json`` file at ``path``.

    Each item in ``footprints`` is a dict with this shape:

        {
            "name":        "RESC0402X13L",         # required, matches IPC-7351B naming
            "kind":        "R",                    # one of C / R / I / FB
            "density":     "L",                    # one of L / N / M (must match name suffix)
            "drawingNote": "Dimensions from ...",  # free text, traceable back to a datasheet
            "bodyMm": {
                "lengthNominal":          0.4,   # along terminal axis (X)
                "widthNominal":           0.2,   # across terminal axis (Y)
                "heightNominal":          0.13,  # extruded body height (Z)
                "terminalLengthNominal":  0.1,   # band length T per IPC-7351B
            },
        }

    The output file is a plain UTF-8 (ASCII-safe) JSON document with
    indent=2 and a trailing newline. Footprints are sorted by ``name``
    so re-runs produce byte-identical output (subject to upstream
    determinism).

    Raises ``ValueError`` on any per-row validation failure -- vendor
    scripts should never produce malformed footprints, so any bad row
    is a regression and the build fails loudly."""
    fps = []
    for fp in footprints:
        _validate_footprint(fp)
        fps.append(dict(fp))  # shallow copy so caller can keep using its own dicts
    fps.sort(key=lambda fp: fp["name"])

    doc = {
        "schemaVersion": SCHEMA_VERSION,
        "vendor": vendor,
        "footprints": fps,
    }

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="ascii") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# xlwt WRITEACCESS (BIFF record 0x005C) compatibility patch
# ---------------------------------------------------------------------------
#
# Symptom: every ``.xls`` produced by xlwt was unreadable by Altium
# Designer's DbLib OLE DB binding until the file had been opened (and
# closed -- no save needed) in Microsoft Excel. ``cmp`` of the pre-/
# post-Excel files showed the first divergence at byte 553 (= file
# offset 0x229), inside the BIFF8 ``WRITEACCESS`` record:
#
#   Excel-fixed: 5c 00 70 00  05 00 00  61 64 6d 69 6e  20 20 ...
#   xlwt:        5c 00 70 00  4e 6f 6e 65 20 20 20 20  20 20 ...
#                ^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^^^^^^
#                rec hdr      payload (112 bytes)
#
# Per [MS-XLS] §2.4.351, the WRITEACCESS payload is a fixed-length
# 112-byte ``XLUnicodeString`` -- a uint16 ``cch``, a 1-byte
# ``fHighByte`` flag, then ``cch`` (or 2*cch) chars of name, padded
# with U+0020 to fill the body. The Excel-rewritten file follows that
# spec exactly: cch=5, flags=0 (8-bit/compressed), "admin", spaces.
#
# Stock xlwt-1.3 (see ``BIFFRecords.WriteAccessRecord``) skips the
# ``cch``/``fHighByte`` framing entirely and just dumps the owner
# string as raw ASCII followed by space padding. To make matters
# worse, the default owner on a fresh ``Workbook()`` is the literal
# Python string ``'None'`` (Workbook.py line 57), so out of the box
# every xlwt-produced .xls starts the WRITEACCESS payload with the
# bytes ``4e 6f 6e 65`` rather than a length prefix. Microsoft's
# reader silently repairs the record on open; the ACE/Jet OLE DB
# driver Altium uses does not, and silently fails to load the table.
#
# The patch below replaces ``WriteAccessRecord.__init__`` with a
# spec-compliant emitter. After applying it, .xls files generated by
# any vendor script open directly in Altium.
def _apply_xlwt_writeaccess_patch() -> None:
    """Replace xlwt's malformed WRITEACCESS record writer with a
    BIFF8-spec-compliant one. Idempotent and a no-op if xlwt is not
    importable."""
    try:
        from xlwt import BIFFRecords as _br
    except ImportError:
        return

    if getattr(_br.WriteAccessRecord, "_bdwip_writeaccess_patched", False):
        return

    from struct import pack

    # WRITEACCESS body is fixed at 112 bytes (0x70). Three bytes are
    # consumed by cch (uint16) + fHighByte (uint8), leaving 109 bytes
    # for chars + space padding. With 8-bit chars that caps the name
    # at 109 characters; we'll never get close in practice.
    _BODY_LEN = 0x70
    _MAX_CCH = _BODY_LEN - 3

    def _patched_init(self, owner):
        s = "" if owner is None else str(owner)
        s = s[:_MAX_CCH]
        # ``replace`` rather than ``strict`` so a stray non-ASCII
        # owner name (unlikely, but cheap to defend against) doesn't
        # take down a build over a metadata field.
        encoded = s.encode("ascii", errors="replace")
        cch = len(encoded)
        pad_len = _BODY_LEN - 3 - cch
        self._rec_data = pack("<HB", cch, 0x00) + encoded + b" " * pad_len

    _br.WriteAccessRecord.__init__ = _patched_init
    _br.WriteAccessRecord._bdwip_writeaccess_patched = True


_apply_xlwt_writeaccess_patch()
