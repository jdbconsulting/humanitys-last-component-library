#!/usr/bin/env python
"""
Top-level build orchestrator for Humanity's Last Component Library.

Replaces the (deleted) recursive Makefile system. Runs every per-vendor
family generator, merges per-vendor footprints JSONs into the canonical
``build/intermediate/footprints/house-footprints.json``, generates
parametric STEP 3D models, copies in the hand-maintained
``house.SchLib``, and emits ``build/output/house.PcbLib`` -- all
in-process, never via ``subprocess``.

The "in-process" property is load-bearing: the same module drives the
build from a host CLI today and from Pyodide in the browser tomorrow.
Pyodide can't fork shells, so every step had to be callable as a
Python function. Vendor scripts already had argv-driven ``main()``
entrypoints, so the orchestrator just imports each one (via
``importlib.util.spec_from_file_location``, since the scripts have
dashes in their basenames and so can't be imported by name) and calls
``main()``.

Discovery
---------
Each vendor family folder under ``vendors/<mfg>/<family>/`` and each
house component folder under ``house/<component>/`` ships a tiny
``_build.py`` that calls :func:`register` at import time. ``build.py``
globs those files and imports them; **no top-level edit is required to
add a new family** -- mirroring the old Makefile chain's
``+= VENDOR_TARGETS`` ergonomic.

CLI
---
::

    python build.py                    same as ``all``
    python build.py all                build every registered target
                                       (excluding ``standards``, which
                                       shells out to pdflatex)
    python build.py <target>           build one target plus its deps
    python build.py clean              rm -rf build/ + __pycache__
    python build.py --list             print every registered target

Library API
-----------
::

    import build
    build.discover()
    build.build_all()
    build.build_target("murata-gcm")
    build.clean()
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from dataclasses import dataclass
from glob import glob
from typing import Callable, Iterable

# The directory that contains this build.py. Every other path in the
# orchestrator is resolved relative to ROOT_DIR; nothing reads
# os.getcwd(). This is what lets Pyodide drive the build after
# mounting the source tree at an arbitrary path in its in-memory FS.
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Special pseudo-dep: house targets use this to mean "every registered
# vendor target". The expansion happens lazily at build_target() time,
# so dropping in a new vendors/<mfg>/<family>/_build.py automatically
# becomes a prerequisite of house-footprints (and transitively of
# house-step-models / house-pcblib).
ALL_VENDORS = "@vendors"

VENDOR = "vendor"
HOUSE = "house"
AGGREGATE = "aggregate"
VALID_KINDS = frozenset({VENDOR, HOUSE, AGGREGATE})


@dataclass
class Target:
    name: str
    kind: str
    runner: Callable[[], None]
    deps: tuple[str, ...] = ()
    cli_only: bool = False


_REGISTRY: dict[str, Target] = {}
_DISCOVERED = False


# ---------------------------------------------------------------------------
# Registration (called by every _build.py stub)
# ---------------------------------------------------------------------------

def register(
    name: str,
    *,
    kind: str,
    runner: Callable[[], None],
    deps: Iterable[str] = (),
    cli_only: bool = False,
) -> None:
    """Declare a build target. Called from each ``_build.py`` stub at
    import time.

    ``kind`` is one of ``vendor`` / ``house`` / ``aggregate``. ``runner``
    is a zero-arg callable that performs the build. ``deps`` is a tuple
    of target names; the special string ``@vendors`` expands at
    execution time to every currently-registered vendor target (this
    is what house-footprints uses so adding a new family is automatic).
    Targets flagged ``cli_only=True`` are skipped by :func:`build_all`
    and so don't run inside Pyodide -- reserved for ``standards``,
    which shells out to ``pdflatex``.
    """
    if kind not in VALID_KINDS:
        raise ValueError(
            f"target {name!r}: kind must be one of {sorted(VALID_KINDS)} (got {kind!r})"
        )
    if name in _REGISTRY:
        raise ValueError(f"target {name!r} already registered")
    _REGISTRY[name] = Target(
        name=name, kind=kind, runner=runner, deps=tuple(deps), cli_only=cli_only,
    )


def call_main(mod, argv: Iterable[str] = ()) -> int:
    """Invoke ``mod.main`` after temporarily patching ``sys.argv`` so
    argparse-driven entrypoints see the desired flags. Restores
    ``sys.argv`` on exit so subsequent targets see clean argv.

    Works uniformly for every flavour of generator script in this
    repo: vendor scripts whose ``main()`` takes no arguments (they
    read ``sys.argv`` via ``argparse``), house scripts that don't use
    argparse at all (``build_house_footprints.py``,
    ``build_step_models.py``), and ``build_pcblib.py`` whose
    ``main(argv)`` defaults ``argv=None`` and so falls through to
    ``sys.argv``.

    A handful of legacy vendor scripts (e.g. ``tdk-capacitors.py``)
    put their whole body at module scope rather than under a
    ``def main():``. For those the import done by :func:`load_module`
    already performed the build, and we just return 0 -- the runner
    re-executes the file from scratch on every invocation because
    :func:`load_module` always allocates a fresh module object.
    """
    saved_argv = sys.argv
    try:
        sys.argv = [getattr(mod, "__file__", "<build>")] + list(argv)
        main_fn = getattr(mod, "main", None)
        if main_fn is None:
            return 0
        rc = main_fn()
        return rc if isinstance(rc, int) else 0
    finally:
        sys.argv = saved_argv


def load_module(path: str, module_name: str | None = None):
    """Import a single Python file at ``path`` as a module and return
    it. Used by vendor ``_build.py`` stubs to pull in their
    ``<vendor>-<family>.py`` sibling, whose dashed basename can't be
    ``import``ed normally. Also used internally by :func:`discover`
    to load ``_build.py`` stubs themselves.

    Each module gets a unique synthetic ``module_name`` so multiple
    files with the same basename (e.g. several ``_build.py``) coexist
    in ``sys.modules`` without clobbering one another.
    """
    if module_name is None:
        rel = os.path.relpath(path, ROOT_DIR)
        module_name = "_hlcl_loaded__" + (
            rel.replace(os.sep, "_").replace("/", "_").replace("-", "_").replace(".py", "")
        )
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load module at {path!r}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover(root: str | None = None) -> None:
    """Find every ``_build.py`` under ``vendors/``, ``house/``, and
    ``docs/standards/`` and import it so registrations land in
    ``_REGISTRY``. Idempotent."""
    global _DISCOVERED
    if _DISCOVERED:
        return
    base = os.path.abspath(root) if root else ROOT_DIR
    patterns = [
        os.path.join(base, "vendors", "*", "*", "_build.py"),
        os.path.join(base, "house", "_build.py"),
        os.path.join(base, "house", "*", "_build.py"),
        os.path.join(base, "docs", "standards", "_build.py"),
    ]
    for pattern in patterns:
        for path in sorted(glob(pattern)):
            load_module(path)
    _register_manufacturer_aggregates()
    _DISCOVERED = True


def _register_manufacturer_aggregates() -> None:
    """Auto-create per-manufacturer aggregate phonies from the prefix
    each vendor target shares before its first dash. The convention
    the old top-level Makefile documented -- ``make panasonic`` builds
    every ``panasonic-*`` family in one shot -- generalised to every
    manufacturer with 2+ family targets registered."""
    by_prefix: dict[str, list[str]] = {}
    for t in _REGISTRY.values():
        if t.kind != VENDOR:
            continue
        prefix, sep, _ = t.name.partition("-")
        if not sep:
            continue
        by_prefix.setdefault(prefix, []).append(t.name)
    for prefix, members in by_prefix.items():
        if prefix in _REGISTRY:
            continue  # don't shadow an existing target
        if len(members) < 2:
            continue  # single-family manufacturer doesn't need an aggregate
        register(
            prefix,
            kind=AGGREGATE,
            runner=_noop,
            deps=tuple(sorted(members)),
        )


def _noop() -> None:
    """Aggregate targets are pure dep nodes -- their runner is a no-op."""


# ---------------------------------------------------------------------------
# Target resolution / execution
# ---------------------------------------------------------------------------

def list_targets() -> list[Target]:
    """Return every registered target, sorted (kind, name)."""
    discover()
    return sorted(_REGISTRY.values(), key=lambda t: (t.kind, t.name))


def _resolve_deps(name: str) -> list[str]:
    """Return ``name``'s deps in topological order (deps first),
    expanding the ``@vendors`` pseudo-dep to every currently-registered
    vendor target. Raises on cycles."""
    if name not in _REGISTRY:
        raise KeyError(
            f"unknown target {name!r}; available: {sorted(_REGISTRY)}"
        )
    order: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(n: str) -> None:
        if n in visited:
            return
        if n in visiting:
            raise RuntimeError(f"dependency cycle detected at {n!r}")
        visiting.add(n)
        for d in _REGISTRY[n].deps:
            if d == ALL_VENDORS:
                for t in _REGISTRY.values():
                    if t.kind == VENDOR:
                        visit(t.name)
            else:
                visit(d)
        visiting.discard(n)
        visited.add(n)
        order.append(n)

    visit(name)
    return order


def build_target(name: str, root: str | None = None) -> None:
    """Run ``name`` plus its (transitive) deps in topological order."""
    discover(root)
    for n in _resolve_deps(name):
        t = _REGISTRY[n]
        print(f"==> {t.name}", file=sys.stderr)
        t.runner()


def build_all(root: str | None = None) -> None:
    """Run every registered target except ``cli_only`` ones (notably
    ``standards``, which shells out to pdflatex and so can't run in
    Pyodide).

    Order: every vendor target (via the ``@vendors`` expansion baked
    into ``house-footprints``'s deps), then ``house-footprints``,
    then ``house-step-models`` + ``house-schlib``, then
    ``house-pcblib``. Achieved by walking the dep graph from the two
    terminal targets ``house-pcblib`` and ``house-schlib``.
    """
    discover(root)
    seen: set[str] = set()

    def run_chain(terminal: str) -> None:
        for n in _resolve_deps(terminal):
            if n in seen:
                continue
            t = _REGISTRY[n]
            if t.cli_only:
                continue
            print(f"==> {t.name}", file=sys.stderr)
            t.runner()
            seen.add(n)

    for terminal in ("house-pcblib", "house-schlib"):
        if terminal in _REGISTRY:
            run_chain(terminal)

    # Catch any target the terminals didn't transitively pull in
    # (e.g. a future vendor with no downstream consumer). Skips
    # cli_only and the auto-generated manufacturer aggregates (whose
    # runner is a no-op anyway).
    for t in list(_REGISTRY.values()):
        if t.name in seen or t.cli_only or t.kind == AGGREGATE:
            continue
        run_chain(t.name)


# ---------------------------------------------------------------------------
# clean
# ---------------------------------------------------------------------------

def clean(root: str | None = None) -> None:
    """Remove the ``build/`` tree and every ``__pycache__`` directory
    under ``vendors/`` and ``house/``. Equivalent of the old
    ``make clean``."""
    base = os.path.abspath(root) if root else ROOT_DIR
    build_dir = os.path.join(base, "build")
    if os.path.isdir(build_dir):
        shutil.rmtree(build_dir)
    for top in ("vendors", "house"):
        top_dir = os.path.join(base, top)
        if not os.path.isdir(top_dir):
            continue
        for dirpath, dirnames, _files in os.walk(top_dir):
            if "__pycache__" in dirnames:
                shutil.rmtree(os.path.join(dirpath, "__pycache__"))
                dirnames.remove("__pycache__")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

USAGE = """\
Usage: python build.py [<target>|all|clean|--list]

  (no arg)     same as `all`
  all          build every registered target (excludes `standards`)
  <target>     build one target plus its deps
  clean        rm -rf build/ + __pycache__
  --list, -l   print every registered target
  --help, -h   show this message
"""


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        build_all()
        return 0
    if args[:1] in (["--help"], ["-h"]):
        sys.stdout.write(USAGE)
        return 0
    if args[:1] in (["--list"], ["-l"]):
        for t in list_targets():
            print(f"  {t.name:30s}  {t.kind}")
        return 0
    if len(args) != 1:
        sys.stderr.write(USAGE)
        return 2
    arg = args[0]
    if arg == "all":
        build_all()
        return 0
    if arg == "clean":
        clean()
        return 0
    discover()
    if arg not in _REGISTRY:
        print(
            f"error: unknown target {arg!r}; "
            f"run `python build.py --list` for the full list",
            file=sys.stderr,
        )
        return 2
    build_target(arg)
    return 0


if __name__ == "__main__":
    # Avoid the dual-module pitfall: when build.py is run as a script
    # Python loads it as ``__main__``, but a later ``from build import
    # register`` from inside a ``_build.py`` stub would otherwise
    # trigger a *second* fresh load of this file under the name
    # ``build`` -- yielding two copies of ``_REGISTRY``, with the
    # stubs registering into the wrong one. Aliasing
    # ``sys.modules["build"]`` to ``__main__`` makes the second
    # ``import build`` a cache hit and keeps the registry singleton.
    sys.modules.setdefault("build", sys.modules["__main__"])
    sys.exit(main())
