"""Offline Vishay CRCW importer; see vendors/passive-importers.md."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from _passives import csv_main
from _vishay_passives import decode as decode_catalog
import _config
FAMILY = "vishay-crcw"

#: TCR code (14th MPN character) -> rank, tightest first:
#: K = +/-100, N = +/-200, X = -200/+400 ppm/K. Jumpers (Z0) have none.
TCR_RANK = {"K": 0, "N": 1, "X": 2}


def decode(row):
    return decode_catalog(row, FAMILY)


def select(parts):
    """Apply the family's TCR options: keep the ticked TCR grades and,
    with lowest_tcr_only, only the tightest one per size, value,
    tolerance and reel."""
    family = _config.current().family(FAMILY)
    allowed = set(family.get_option("tcr_options", list(TCR_RANK)))
    if allowed - set(TCR_RANK):
        raise ValueError(f"{FAMILY}: unknown tcr_options {sorted(allowed - set(TCR_RANK))}")
    kept = [p for p in parts if p.mpn[13] not in TCR_RANK or p.mpn[13] in allowed]
    if not family.get_option("lowest_tcr_only", False):
        return kept
    key = lambda p: (p.mpn[:12], p.mpn[12], p.mpn[14:])  # model, size, value; tolerance; reel
    rank = lambda p: TCR_RANK.get(p.mpn[13], -1)
    best = {}
    for p in kept:
        if key(p) not in best or rank(p) < rank(best[key(p)]):
            best[key(p)] = p
    return [p for p in kept if best[key(p)] is p]


def main():
    csv_main(FAMILY, "crcw", HERE / "parts.csv", decode, select=select, extras=("alternates",))

if __name__ == "__main__":
    main()
