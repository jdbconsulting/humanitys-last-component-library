"""Build registration for KEMET ESD C0G."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from build import VENDOR, call_main, load_module, register

def _run():
    rc = call_main(load_module(str(HERE / "importer.py")))
    if rc:
        raise SystemExit(rc)

register("kemet-esd-c0g", kind=VENDOR, runner=_run)
