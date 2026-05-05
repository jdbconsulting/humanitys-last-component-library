"""Build registration stub for the ``standards`` target -- renders
the HLCL-001 drawing-standards templates against the active
:class:`hlcl._config.BuildConfig` and stages the populated files
under ``build/output/standards/``.

The target replaces the previous pdflatex-based ``standards`` target
that lived under ``docs/standards/_build.py``. Two key changes:

  * The output is the *populated* template (``.tex`` and / or ``.md``)
    rather than a typeset PDF -- no host LaTeX toolchain required, and
    the same code path runs identically under host CPython and Pyodide.
  * Both formats are gated by individual artifact flags
    (``standards_tex`` / ``standards_md``), so users can opt in to one,
    both, or neither. The accompanying figures (``example-symbol.png``,
    ``example-footprint.png``) are copied alongside whichever rendering
    is requested so the .tex / .md is self-contained on download.

The source templates live at ``<project>/docs/standards/standards.tex``
and ``<project>/docs/standards/standards.md`` for the host CLI build,
and at ``/hlcl/standards/...`` inside the Pyodide build-inputs tarball
(see ``vite/plugins/hlcl-build-assets.ts``). :func:`render.find_template`
tries both.
"""

import os
import shutil
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_HLCL_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
if _HLCL_ROOT not in sys.path:
    sys.path.insert(0, _HLCL_ROOT)

import _config
from build import HOUSE, load_module, register

# render.py is a sibling of this _build.py and is loaded at register
# time so its `_config` import binds to the same module instance the
# orchestrator just installed -- the same pattern every other house
# target uses for its driver scripts.
render = load_module(os.path.join(_HERE, "render.py"))


# Image filenames (referenced by both standards.tex and standards.md)
# that need to ship alongside the rendering for the file to be
# self-contained. Looked up in the same candidate directories as the
# templates themselves.
_FIGURES = ("example-symbol.png", "example-footprint.png")


def _output_dir() -> str:
    return os.path.join(_HLCL_ROOT, "build", "output", "standards")


def _copy_figures(into: str) -> None:
    """Copy the reference screenshots from wherever the templates live
    into the build output. Missing figures are tolerated -- a contributor
    deliberately stripping the binaries from their checkout shouldn't
    break the rest of the build."""
    # Reuse the template-finder to locate the figures in the right
    # candidate directory. We pass each figure name through
    # `find_template` -- it doesn't care what extension the file has.
    for name in _FIGURES:
        try:
            src = render.find_template(name, _HLCL_ROOT)
        except FileNotFoundError:
            print(f"  (skipping {name}: not found alongside template)", file=sys.stderr)
            continue
        dst = os.path.join(into, name)
        shutil.copy(src, dst)
        print(f"  copied {os.path.basename(src)} -> {dst}", file=sys.stderr)


def _run() -> None:
    cfg = _config.current()
    want_tex = cfg.is_artifact_enabled("standards_tex")
    want_md = cfg.is_artifact_enabled("standards_md")

    if not (want_tex or want_md):
        # Defensive: build_target() should have already filtered us
        # out via is_target_enabled(), but if a future caller invokes
        # the runner directly we still want to fail loudly rather than
        # silently emit nothing.
        print("  (no standards artifact enabled; skipping)", file=sys.stderr)
        return

    out_dir = _output_dir()
    os.makedirs(out_dir, exist_ok=True)

    if want_tex:
        text = render.render_template("standards.tex", _HLCL_ROOT, cfg)
        dst = os.path.join(out_dir, "standards.tex")
        with open(dst, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"  wrote {dst}", file=sys.stderr)

    if want_md:
        text = render.render_template("standards.md", _HLCL_ROOT, cfg)
        dst = os.path.join(out_dir, "standards.md")
        with open(dst, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"  wrote {dst}", file=sys.stderr)

    # Both renderings reference the same two screenshots; copy them
    # once whenever either format is being shipped.
    _copy_figures(out_dir)


register("standards", kind=HOUSE, runner=_run)
