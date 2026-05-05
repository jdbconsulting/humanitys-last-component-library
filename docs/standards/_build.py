"""Build registration stub for the ``standards`` target -- the
HLCL-001 PDF typeset from ``docs/standards/HLCL-001.tex`` via two
``pdflatex`` passes (pass 1 writes the .aux/.toc, pass 2 resolves
\\tableofcontents + Section~N refs in the body).

This target is **not** part of ``build_all()``: pdflatex is a heavy
host-side dependency most users don't have, and as a subprocess it
can't run inside Pyodide anyway. It's flagged ``cli_only=True`` so
the orchestrator skips it on the ``all`` path and surfaces a clear
error if a Pyodide caller asks for it explicitly.

Override the LaTeX engine via the ``HLCL_PDFLATEX`` env var (default
``pdflatex``).
"""

import os
import shutil
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from build import HOUSE, register

PDFLATEX = os.environ.get("HLCL_PDFLATEX", "pdflatex")
TEX_BASENAME = "HLCL-001"


def _run() -> None:
    intermediate = os.path.join(_ROOT, "build", "intermediate", "standards")
    output_dir = os.path.join(_ROOT, "build", "output", "standards")
    os.makedirs(intermediate, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        PDFLATEX,
        "-interaction=nonstopmode",
        "-halt-on-error",
        f"-output-directory={intermediate}",
        f"{TEX_BASENAME}.tex",
    ]
    for pass_num in (1, 2):
        print(f"pdflatex pass {pass_num}/2", file=sys.stderr)
        rc = subprocess.run(cmd, cwd=_HERE).returncode
        if rc:
            raise SystemExit(rc)

    src = os.path.join(intermediate, f"{TEX_BASENAME}.pdf")
    dst = os.path.join(output_dir, f"{TEX_BASENAME}.pdf")
    shutil.copy(src, dst)
    print(f"Copied {src} -> {dst}", file=sys.stderr)


register("standards", kind=HOUSE, runner=_run, cli_only=True)
