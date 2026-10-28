"""Offline Vishay CRCW importer; see vendors/passive-importers.md."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from _passives import csv_main
from _vishay_passives import decode as decode_catalog, select_grades
import _config
FAMILY = "vishay-crcw"

def decode(row):
    return decode_catalog(row, FAMILY)


def select(parts):
    """TCR options from the Libraries tab: K = +/-100, N = +/-200, X = -200/+400 ppm/K."""
    return select_grades(parts, _config.current().family(FAMILY), "KNX")


def main():
    csv_main(FAMILY, "crcw", HERE / "parts.csv", decode, select=select, extras=("alternates",))

if __name__ == "__main__":
    main()
