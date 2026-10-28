"""Offline Vishay TNPW importer (e3 and SnPb); see vendors/passive-importers.md."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from _passives import code_value, csv_main
from _vishay_passives import decode as decode_catalog, in_series, select_grades
import _config
FAMILY = "vishay-tnpw"
SNPB_REELS = ("TA", "TD", "TP", "CN")


def decode(row):
    return decode_catalog(row, FAMILY)


def select(parts):
    """Libraries-tab options: terminations (e3 pure tin, SnPb lead-bearing),
    value series (every datasheet value, or E24/E96 only), then the TCR
    (H/E/X/Y = 50/25/15/10 ppm/K) and tolerance (F/D/B = 1/0.5/0.1%) grades."""
    options = _config.current().family(FAMILY)
    finishes = set(options.get_option("terminations", ["e3"]))
    if finishes - {"e3", "snpb"}:
        raise ValueError(f"{FAMILY}: unknown terminations {sorted(finishes - {'e3', 'snpb'})}")
    parts = [p for p in parts if ("snpb" if p.mpn[14:] in SNPB_REELS else "e3") in finishes]
    if options.get_option("value_series", "e192") == "e96":
        parts = [p for p in parts
                 if in_series(code_value(p.mpn[8:12]), "E24") or in_series(code_value(p.mpn[8:12]), "E96")]
    return select_grades(parts, options, "HEXY", "FDB")


def main():
    csv_main(FAMILY, "tnpw", HERE / "parts.csv", decode, select=select, extras=("alternates",))

if __name__ == "__main__":
    main()
