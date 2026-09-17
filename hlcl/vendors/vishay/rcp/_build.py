"""Build registration for Vishay RCP."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from build import VENDOR, call_main, load_module, register

def _run():
    rc = call_main(load_module(str(HERE / "importer.py")))
    if rc:
        raise SystemExit(rc)

register("vishay-rcp", kind=VENDOR, runner=_run)
