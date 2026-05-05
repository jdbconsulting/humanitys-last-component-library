"""
Single source of truth for runtime build configuration.

The canonical contract is the JSON document defined by
``hlcl/build-config.schema.json`` (auto-generated from
``src/lib/schema.ts`` by the Vite plugin). This module is the
**Python-side library** every generator script imports to read that
contract — no per-script TOML parsing, no per-script argv plumbing,
no duplicated default values.

Lifecycle
---------
There are three legal ways the current config gets into ``_CURRENT``:

1. **Orchestrated**: ``hlcl/build.py`` parses ``--config <path>`` and
   calls :func:`set_current` *before* importing any house / vendor
   module. This is the path the CLI and the Pyodide-side runner take.

2. **Direct script invocation**: ``python hlcl/house/build_pcblib.py``
   triggers an import of :mod:`house._house_settings`, which calls
   :func:`bootstrap` on import. Bootstrap peels ``--config <path>``
   off ``sys.argv`` (so the script's own argparse doesn't choke),
   falls back to ``hlcl/factory-defaults.json`` next to ``build.py``,
   and raises ``RuntimeError`` if neither is available.

3. **Programmatic**: tests / notebooks call :func:`set_current`
   directly with a ``BuildConfig`` instance.

Once set, ``_CURRENT`` is immutable for the lifetime of the process.
Calling :func:`set_current` a second time **replaces** it; this is
intentional — the same Python interpreter can drive back-to-back
builds with different configs (the in-browser configurator does
exactly this each time the user clicks "Run build" with new
options).

Family-id resolution
--------------------
Some catalog ids don't match their on-disk vendor key 1:1 — the
canonical example is ``murata-ferrites`` (the build-target / catalog
id) vs. ``murata-ferrite`` (the file basename used in
``priority`` / per-vendor JSON keys). :func:`vendor_key_for` exposes
that mapping so vendor scripts and the merge step can stay in sync.

Why hand-rolled validation?
---------------------------
This module deliberately avoids ``pydantic`` / ``jsonschema`` /
``cattrs`` and any other third-party dep so it loads cleanly under
Pyodide without an extra ``micropip`` install. The validation is
roughly an order of magnitude less rich than what Zod gives us on the
TS side — that's fine: the JS app validates upstream, the JSON file
arriving here is already known-good, and our checks are mostly a
defensive belt-and-braces for hand-edited CLI configs.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Tuple

# ---------------------------------------------------------------------------
# Public schema-version contract
# ---------------------------------------------------------------------------

#: Canonical contract version. Bumped in lockstep with
#: ``BUILD_CONFIG_VERSION`` in ``src/lib/schema.ts``.
SCHEMA_VERSION = "1.0.0"

#: The closed set of IPC-7351B density-level codes the pipeline knows
#: about. Order matters for the .xls Footprint 1/2/3 slot assignment:
#: slot 1 prefers the first enabled density in this order, falling
#: back as needed.
DENSITY_ORDER: Tuple[str, ...] = ("N", "L", "M")

#: All density codes we recognise (set form, for membership checks).
ALL_DENSITIES: frozenset = frozenset(DENSITY_ORDER)

# Family id ↔ on-disk vendor key. Most ids match 1:1; the few that
# don't are listed here. Keep this dict tiny and well-commented so
# future vendor folder drops obey the convention by default.
_FAMILY_TO_VENDOR_KEY: Mapping[str, str] = {
    # Build-target / catalog id is plural to match the historical
    # `make murata-ferrites` invocation; the per-vendor footprint JSON
    # / .xls / DbLib basenames stayed singular (`murata-ferrite`).
    # `house_footprints.priority` references the singular form because
    # that's what `*-footprints.json` discovers on disk.
    "murata-ferrites": "murata-ferrite",
}


def vendor_key_for(family_id: str) -> str:
    """Map a catalog/build-target id (e.g. ``murata-ferrites``) to the
    on-disk vendor key used in the per-vendor footprints JSON basename
    and in ``settings.house_footprints.priority`` (e.g.
    ``murata-ferrite``). Defaults to identity for the common case where
    the two match."""
    return _FAMILY_TO_VENDOR_KEY.get(family_id, family_id)


# ---------------------------------------------------------------------------
# Settings dataclasses (1:1 mirror of `src/lib/schema.ts::settingsSchema`)
# ---------------------------------------------------------------------------

Rgb = Tuple[int, int, int]


@dataclass(frozen=True)
class HouseFootprintsSettings:
    """[house_footprints] -- vendor priority list for the merge step."""

    priority: Tuple[str, ...]


@dataclass(frozen=True)
class IpcSettings:
    """[ipc] -- IPC-7351B §3.1.4 fab + placement tolerances."""

    fabrication_tolerance_mm: float
    placement_tolerance_mm: float


@dataclass(frozen=True)
class HlclSettings:
    """[hlcl] -- HLCL-001 drawing standards + global footprint emission flags."""

    pad_corner_radius_percent: int
    solder_mask_expansion_mm: float
    min_solder_mask_sliver_mm: float
    outline_line_width_mm: float
    max_crosshair_half_arm_mm: float
    component_body_standoff_mm: float
    enabled_densities: Tuple[str, ...]
    enabled_sizes: Tuple[str, ...]


@dataclass(frozen=True)
class StepGenSettings:
    """[stepgen] -- 3D body geometry knobs."""

    default_fillet_radius_mm: float
    resc_metal_thickness_fraction: float
    resc_metal_thickness_floor_mm: float


@dataclass(frozen=True)
class ColorSettings:
    """[colors.*] -- per-family RGB palette (24-bit ints, [0..255])."""

    default_body: Rgb
    capc_body: Rgb
    capc_terminal: Rgb
    indc_body: Rgb
    indc_terminal: Rgb
    fb_body: Rgb
    fb_terminal: Rgb
    resc_substrate: Rgb
    resc_passivation: Rgb
    resc_terminal: Rgb


@dataclass(frozen=True)
class Settings:
    """Mirror of the JSON ``settings`` block. Replaces ``settings.toml``."""

    house_footprints: HouseFootprintsSettings
    ipc: IpcSettings
    hlcl: HlclSettings
    stepgen: StepGenSettings
    colors: ColorSettings


# ---------------------------------------------------------------------------
# Per-family / artifact / crosslink dataclasses
# ---------------------------------------------------------------------------

# Per-family option ids that the resolution helpers below recognise.
# These match the catalog-derived ids in ``src/lib/libraries.ts``.
_OPT_ENABLED_DENSITIES = "enabled_densities"
_OPT_SIZES = "sizes"
_OPT_PAD_RADIUS = "override_pad_radius"


@dataclass(frozen=True)
class FamilyConfig:
    """Per-family entry from the JSON ``families.<id>`` map.

    ``options`` and ``overrides`` are intentionally ``dict`` (rather
    than nested dataclasses) because each family declares its own
    option set in ``catalog.json``; pinning them to fixed fields would
    defeat the purpose of the catalog-driven UI.
    """

    enabled: bool
    options: Mapping[str, Any]
    overrides: Mapping[str, bool]

    def get_option(self, key: str, default: Any = None) -> Any:
        """Return the per-family option value, or ``default`` if unset.

        Use this in a vendor script for family-specific knobs
        (``min_voltage`` for Murata GCM, etc.). For options with a
        global counterpart (densities, sizes, pad radius) prefer
        the resolution helpers on :class:`BuildConfig` instead, which
        consult the override flag for you.
        """
        return self.options.get(key, default)

    def overrides_global(self, key: str) -> bool:
        """True if the per-family value should win over the global
        ``settings.hlcl.*`` setting for ``key``. False (the default)
        means inherit the global."""
        return bool(self.overrides.get(key, False))


@dataclass(frozen=True)
class Artifacts:
    """Per-target emit flags. Each maps to one or more build targets;
    see :func:`BuildConfig.is_target_enabled` for the wiring."""

    xls: bool
    dblib: bool
    footprints_json: bool
    house_footprints_merge: bool
    step_models: bool
    pcblib: bool
    schlib: bool
    # When either standards flag is on, the `standards` house target
    # renders the corresponding template (docs/standards/standards.tex
    # / standards.md) into build/output/standards/. Both are gated on
    # the same target -- the runner consults the individual flags to
    # decide which output(s) to emit.
    standards_tex: bool
    standards_md: bool
    zip_output: bool


@dataclass(frozen=True)
class Crosslink:
    """One MPN substitution entry. Reserved for a future BOM-side
    consumer; the build pipeline doesn't read this today."""

    primary_mpn: str
    primary_mfg: str
    substitute_mpn: str
    substitute_mfg: str
    notes: str


# ---------------------------------------------------------------------------
# Top-level BuildConfig + resolution helpers
# ---------------------------------------------------------------------------

# Mapping target name → artifact flag that gates it. Targets not in
# this map run unconditionally as long as something downstream (or
# build_all itself) pulls them in. Manufacturer aggregates inherit
# from their members, so they're absent here too.
_TARGET_TO_ARTIFACT: Mapping[str, str] = {
    # Vendor targets emit the .xls + .DbLib + per-vendor footprints
    # JSON together — the underlying script can't toggle them
    # individually. We treat the trio as enabled if ANY of the three
    # corresponding flags is on.
    "house-footprints": "house_footprints_merge",
    "house-step-models": "step_models",
    "house-pcblib": "pcblib",
    "house-schlib": "schlib",
}

#: ``standards`` target output flags: enabled iff any of these flags is on.
#: Mirrors the ``_VENDOR_ARTIFACT_FLAGS`` pattern so the runner gates the
#: target on the union of "is at least one rendering requested?".
_STANDARDS_ARTIFACT_FLAGS: Tuple[str, ...] = ("standards_tex", "standards_md")

#: Vendor target output trio: enabled iff any of these flags is on.
_VENDOR_ARTIFACT_FLAGS: Tuple[str, ...] = ("xls", "dblib", "footprints_json")


@dataclass(frozen=True)
class BuildConfig:
    """The whole canonical config tree. Mirrors the JSON 1:1 and
    grows resolution helpers on top of it."""

    schema_version: str
    families: Mapping[str, FamilyConfig]
    settings: Settings
    artifacts: Artifacts
    crosslinks: Tuple[Crosslink, ...]

    # ---- family lookup -----------------------------------------------------

    def family(self, family_id: str) -> FamilyConfig:
        """Per-family config entry, or a disabled-empty stand-in if
        the id isn't in the JSON. The stand-in lets new vendor
        scripts come up under an old config without crashing — the
        family is simply treated as disabled, matching what the user
        would see if they hadn't ticked the box yet."""
        cfg = self.families.get(family_id)
        if cfg is None:
            return FamilyConfig(enabled=False, options={}, overrides={})
        return cfg

    def is_family_enabled(self, family_id: str) -> bool:
        return self.family(family_id).enabled

    # ---- override-aware resolution -----------------------------------------

    def densities_for(self, family_id: str) -> Tuple[str, ...]:
        """The ordered tuple of IPC-7351B density codes (subset of
        ``DENSITY_ORDER``) the family should emit footprints for.

        Resolution: if the family flips ``overrides.enabled_densities``
        on, take the per-family ``options.enabled_densities`` list;
        otherwise inherit ``settings.hlcl.enabled_densities``.
        Unknown / out-of-order codes are silently dropped — the
        ordering follows ``DENSITY_ORDER`` regardless of input order
        so .xls slot assignment is deterministic.
        """
        fam = self.family(family_id)
        if fam.overrides_global(_OPT_ENABLED_DENSITIES):
            raw = fam.get_option(_OPT_ENABLED_DENSITIES, [])
        else:
            raw = self.settings.hlcl.enabled_densities
        wanted = {d for d in (raw or ()) if d in ALL_DENSITIES}
        return tuple(d for d in DENSITY_ORDER if d in wanted)

    def sizes_for(self, family_id: str) -> Tuple[str, ...]:
        """The ordered tuple of EIA case-size codes the family should
        emit. Order is the *family* declaration order from the JSON
        (or the global declaration order when inheriting); we don't
        impose a canonical order here because vendors organise their
        catalogs by size descending."""
        fam = self.family(family_id)
        if fam.overrides_global(_OPT_SIZES):
            raw = fam.get_option(_OPT_SIZES, [])
        else:
            raw = self.settings.hlcl.enabled_sizes
        return tuple(str(s) for s in (raw or ()))

    def pad_corner_radius_percent_for(self, family_id: str) -> int:
        """The pad corner-radius (% of shorter pad side) the family
        should use. Resolves the ``override_pad_radius`` flag against
        the global ``settings.hlcl.pad_corner_radius_percent``."""
        fam = self.family(family_id)
        if fam.overrides_global(_OPT_PAD_RADIUS):
            v = fam.get_option(_OPT_PAD_RADIUS, self.settings.hlcl.pad_corner_radius_percent)
            try:
                return int(v)
            except (TypeError, ValueError):
                return self.settings.hlcl.pad_corner_radius_percent
        return self.settings.hlcl.pad_corner_radius_percent

    # ---- artifact / target gating ------------------------------------------

    def is_artifact_enabled(self, name: str) -> bool:
        """Look up an entry of the ``artifacts`` block by name."""
        return bool(getattr(self.artifacts, name, False))

    def is_target_enabled(self, target_name: str, kind: str) -> bool:
        """Should ``target_name`` (a build.py registry entry of
        ``kind`` ∈ vendor/house/aggregate) execute under this
        config?

        Rules:
          * ``aggregate`` targets always run (they're no-op phonies
            whose only job is to pull deps in; the deps themselves
            get filtered).
          * ``vendor`` targets run iff (a) the family is enabled
            AND (b) any of the xls / dblib / footprints_json flags
            is on.
          * ``house`` targets run iff their corresponding artifact
            flag is on (see ``_TARGET_TO_ARTIFACT``).
        """
        if kind == "aggregate":
            return True
        if kind == "vendor":
            if not self.is_family_enabled(target_name):
                return False
            return any(self.is_artifact_enabled(f) for f in _VENDOR_ARTIFACT_FLAGS)
        if kind == "house":
            # The `standards` house target multiplexes two flags --
            # standards_tex and standards_md -- because either one
            # being on means the same render step needs to run (the
            # runner picks which file(s) to emit based on the
            # individual flags). Gate on the union.
            if target_name == "standards":
                return any(self.is_artifact_enabled(f) for f in _STANDARDS_ARTIFACT_FLAGS)
            flag = _TARGET_TO_ARTIFACT.get(target_name)
            if flag is None:
                # Unknown house target — let it run (forward-compat
                # for new house targets that haven't been wired
                # into the artifact map yet).
                return True
            return self.is_artifact_enabled(flag)
        # Unknown kind: don't surprise the user, run it.
        return True


# ---------------------------------------------------------------------------
# JSON → BuildConfig (with hand-rolled validation)
# ---------------------------------------------------------------------------


def _err(path: str, msg: str) -> None:
    raise ValueError(f"BuildConfig: {path}: {msg}")


def _require(d: Mapping[str, Any], key: str, where: str) -> Any:
    if key not in d:
        _err(f"{where}.{key}" if where else key, "missing required field")
    return d[key]


def _as_table(d: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(d, dict):
        _err(where, f"expected object, got {type(d).__name__}")
    return d


def _as_list(d: Any, where: str) -> list:
    if not isinstance(d, list):
        _err(where, f"expected array, got {type(d).__name__}")
    return d


def _as_str(d: Any, where: str) -> str:
    if not isinstance(d, str):
        _err(where, f"expected string, got {type(d).__name__}")
    return d


def _as_bool(d: Any, where: str) -> bool:
    if not isinstance(d, bool):
        _err(where, f"expected boolean, got {type(d).__name__}")
    return d


def _as_number(d: Any, where: str) -> float:
    # JSON numbers are int or float; bool is a subclass of int in
    # Python so reject it explicitly.
    if isinstance(d, bool) or not isinstance(d, (int, float)):
        _err(where, f"expected number, got {type(d).__name__}")
    return float(d)


def _as_int(d: Any, where: str) -> int:
    if isinstance(d, bool) or not isinstance(d, int):
        _err(where, f"expected integer, got {type(d).__name__}")
    return d


def _as_str_list(d: Any, where: str) -> Tuple[str, ...]:
    out = _as_list(d, where)
    return tuple(_as_str(v, f"{where}[{i}]") for i, v in enumerate(out))


def _as_rgb(d: Any, where: str) -> Rgb:
    out = _as_list(d, where)
    if len(out) != 3:
        _err(where, f"expected 3-element array, got {len(out)}")
    parsed = []
    for i, v in enumerate(out):
        x = _as_int(v, f"{where}[{i}]")
        if not 0 <= x <= 255:
            _err(f"{where}[{i}]", f"must be in [0..255], got {x}")
        parsed.append(x)
    return (parsed[0], parsed[1], parsed[2])


def _parse_settings(raw: Mapping[str, Any]) -> Settings:
    s = _as_table(raw, "settings")

    hf = _as_table(_require(s, "house_footprints", "settings"), "settings.house_footprints")
    house_footprints = HouseFootprintsSettings(
        priority=_as_str_list(_require(hf, "priority", "settings.house_footprints"),
                              "settings.house_footprints.priority"),
    )

    ipc = _as_table(_require(s, "ipc", "settings"), "settings.ipc")
    ipc_settings = IpcSettings(
        fabrication_tolerance_mm=_as_number(
            _require(ipc, "fabrication_tolerance_mm", "settings.ipc"),
            "settings.ipc.fabrication_tolerance_mm",
        ),
        placement_tolerance_mm=_as_number(
            _require(ipc, "placement_tolerance_mm", "settings.ipc"),
            "settings.ipc.placement_tolerance_mm",
        ),
    )

    h = _as_table(_require(s, "hlcl", "settings"), "settings.hlcl")
    hlcl_settings = HlclSettings(
        pad_corner_radius_percent=_as_int(
            _require(h, "pad_corner_radius_percent", "settings.hlcl"),
            "settings.hlcl.pad_corner_radius_percent",
        ),
        solder_mask_expansion_mm=_as_number(
            _require(h, "solder_mask_expansion_mm", "settings.hlcl"),
            "settings.hlcl.solder_mask_expansion_mm",
        ),
        min_solder_mask_sliver_mm=_as_number(
            _require(h, "min_solder_mask_sliver_mm", "settings.hlcl"),
            "settings.hlcl.min_solder_mask_sliver_mm",
        ),
        outline_line_width_mm=_as_number(
            _require(h, "outline_line_width_mm", "settings.hlcl"),
            "settings.hlcl.outline_line_width_mm",
        ),
        max_crosshair_half_arm_mm=_as_number(
            _require(h, "max_crosshair_half_arm_mm", "settings.hlcl"),
            "settings.hlcl.max_crosshair_half_arm_mm",
        ),
        component_body_standoff_mm=_as_number(
            _require(h, "component_body_standoff_mm", "settings.hlcl"),
            "settings.hlcl.component_body_standoff_mm",
        ),
        # Defaults handle older configs missing the new global lists.
        enabled_densities=_as_str_list(
            h.get("enabled_densities", list(DENSITY_ORDER)),
            "settings.hlcl.enabled_densities",
        ),
        enabled_sizes=_as_str_list(
            h.get(
                "enabled_sizes",
                ["01005", "0201", "0402", "0603", "0805", "1206", "1210"],
            ),
            "settings.hlcl.enabled_sizes",
        ),
    )

    sg = _as_table(_require(s, "stepgen", "settings"), "settings.stepgen")
    stepgen_settings = StepGenSettings(
        default_fillet_radius_mm=_as_number(
            _require(sg, "default_fillet_radius_mm", "settings.stepgen"),
            "settings.stepgen.default_fillet_radius_mm",
        ),
        resc_metal_thickness_fraction=_as_number(
            _require(sg, "resc_metal_thickness_fraction", "settings.stepgen"),
            "settings.stepgen.resc_metal_thickness_fraction",
        ),
        resc_metal_thickness_floor_mm=_as_number(
            _require(sg, "resc_metal_thickness_floor_mm", "settings.stepgen"),
            "settings.stepgen.resc_metal_thickness_floor_mm",
        ),
    )

    c = _as_table(_require(s, "colors", "settings"), "settings.colors")
    default_t = _as_table(_require(c, "default", "settings.colors"), "settings.colors.default")
    capc_t = _as_table(_require(c, "capc", "settings.colors"), "settings.colors.capc")
    indc_t = _as_table(_require(c, "indc", "settings.colors"), "settings.colors.indc")
    fb_t = _as_table(_require(c, "fb", "settings.colors"), "settings.colors.fb")
    resc_t = _as_table(_require(c, "resc", "settings.colors"), "settings.colors.resc")
    color_settings = ColorSettings(
        default_body=_as_rgb(_require(default_t, "body", "settings.colors.default"),
                              "settings.colors.default.body"),
        capc_body=_as_rgb(_require(capc_t, "body", "settings.colors.capc"),
                           "settings.colors.capc.body"),
        capc_terminal=_as_rgb(_require(capc_t, "terminal", "settings.colors.capc"),
                               "settings.colors.capc.terminal"),
        indc_body=_as_rgb(_require(indc_t, "body", "settings.colors.indc"),
                           "settings.colors.indc.body"),
        indc_terminal=_as_rgb(_require(indc_t, "terminal", "settings.colors.indc"),
                               "settings.colors.indc.terminal"),
        fb_body=_as_rgb(_require(fb_t, "body", "settings.colors.fb"),
                         "settings.colors.fb.body"),
        fb_terminal=_as_rgb(_require(fb_t, "terminal", "settings.colors.fb"),
                             "settings.colors.fb.terminal"),
        resc_substrate=_as_rgb(_require(resc_t, "substrate", "settings.colors.resc"),
                                "settings.colors.resc.substrate"),
        resc_passivation=_as_rgb(_require(resc_t, "passivation", "settings.colors.resc"),
                                  "settings.colors.resc.passivation"),
        resc_terminal=_as_rgb(_require(resc_t, "terminal", "settings.colors.resc"),
                               "settings.colors.resc.terminal"),
    )

    return Settings(
        house_footprints=house_footprints,
        ipc=ipc_settings,
        hlcl=hlcl_settings,
        stepgen=stepgen_settings,
        colors=color_settings,
    )


def _parse_family(raw: Any, where: str) -> FamilyConfig:
    t = _as_table(raw, where)
    enabled = _as_bool(_require(t, "enabled", where), f"{where}.enabled")
    # `options` and `overrides` carry forward as-is; we don't enforce
    # value types here because option types vary per-family.
    options = t.get("options", {})
    overrides = t.get("overrides", {})
    if not isinstance(options, dict):
        _err(f"{where}.options", "expected object")
    if not isinstance(overrides, dict):
        _err(f"{where}.overrides", "expected object")
    return FamilyConfig(
        enabled=enabled,
        options=dict(options),
        overrides={k: bool(v) for k, v in overrides.items()},
    )


def _parse_artifacts(raw: Any) -> Artifacts:
    a = _as_table(raw, "artifacts")
    return Artifacts(
        xls=_as_bool(_require(a, "xls", "artifacts"), "artifacts.xls"),
        dblib=_as_bool(_require(a, "dblib", "artifacts"), "artifacts.dblib"),
        footprints_json=_as_bool(
            _require(a, "footprints_json", "artifacts"), "artifacts.footprints_json"
        ),
        house_footprints_merge=_as_bool(
            _require(a, "house_footprints_merge", "artifacts"),
            "artifacts.house_footprints_merge",
        ),
        step_models=_as_bool(
            _require(a, "step_models", "artifacts"), "artifacts.step_models"
        ),
        pcblib=_as_bool(_require(a, "pcblib", "artifacts"), "artifacts.pcblib"),
        schlib=_as_bool(_require(a, "schlib", "artifacts"), "artifacts.schlib"),
        standards_tex=_as_bool(
            _require(a, "standards_tex", "artifacts"), "artifacts.standards_tex"
        ),
        standards_md=_as_bool(
            _require(a, "standards_md", "artifacts"), "artifacts.standards_md"
        ),
        zip_output=_as_bool(_require(a, "zip_output", "artifacts"), "artifacts.zip_output"),
    )


def _parse_crosslinks(raw: Any) -> Tuple[Crosslink, ...]:
    if raw is None:
        return ()
    items = _as_list(raw, "crosslinks")
    out = []
    for i, v in enumerate(items):
        t = _as_table(v, f"crosslinks[{i}]")
        out.append(
            Crosslink(
                primary_mpn=_as_str(_require(t, "primary_mpn", f"crosslinks[{i}]"),
                                    f"crosslinks[{i}].primary_mpn"),
                primary_mfg=_as_str(_require(t, "primary_mfg", f"crosslinks[{i}]"),
                                    f"crosslinks[{i}].primary_mfg"),
                substitute_mpn=_as_str(_require(t, "substitute_mpn", f"crosslinks[{i}]"),
                                       f"crosslinks[{i}].substitute_mpn"),
                substitute_mfg=_as_str(_require(t, "substitute_mfg", f"crosslinks[{i}]"),
                                       f"crosslinks[{i}].substitute_mfg"),
                notes=_as_str(t.get("notes", ""), f"crosslinks[{i}].notes"),
            )
        )
    return tuple(out)


def from_dict(raw: Mapping[str, Any]) -> BuildConfig:
    """Validate + convert a plain dict to a frozen :class:`BuildConfig`.

    Raises :class:`ValueError` with a dotted path if any required
    field is missing or has the wrong type. Tolerates extra fields
    (forward-compat with v1.x file formats).
    """
    if not isinstance(raw, dict):
        raise ValueError("BuildConfig: expected JSON object at top level")

    sv = raw.get("schema_version")
    if not isinstance(sv, str) or not sv.strip():
        raise ValueError("BuildConfig: missing or invalid schema_version")
    # We accept any 1.x.y as a v1 reader; bumps within the major
    # version are guaranteed additive by policy.
    if not sv.startswith("1."):
        raise ValueError(
            f"BuildConfig: schema_version {sv!r} is not v1.x — "
            f"this build of hlcl/_config.py only understands v1.x"
        )

    families_raw = _as_table(_require(raw, "families", ""), "families")
    families = {
        fid: _parse_family(fcfg, f"families.{fid}") for fid, fcfg in families_raw.items()
    }

    return BuildConfig(
        schema_version=sv,
        families=families,
        settings=_parse_settings(_require(raw, "settings", "")),
        artifacts=_parse_artifacts(_require(raw, "artifacts", "")),
        crosslinks=_parse_crosslinks(raw.get("crosslinks", [])),
    )


def load(path: str | os.PathLike) -> BuildConfig:
    """Load + validate a BuildConfig from a JSON file. Raises
    ``FileNotFoundError`` / ``ValueError`` / ``json.JSONDecodeError``
    on failure (deliberately not catching — callers should let the
    error propagate so the build fails loudly)."""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return from_dict(raw)


# ---------------------------------------------------------------------------
# Module-level current() / set_current() / bootstrap()
# ---------------------------------------------------------------------------

_CURRENT: BuildConfig | None = None


def set_current(cfg: BuildConfig) -> BuildConfig:
    """Install ``cfg`` as the process-wide current config. Returns
    the installed config so call sites can chain
    ``cfg = set_current(load(path))``."""
    global _CURRENT
    if not isinstance(cfg, BuildConfig):
        raise TypeError(f"expected BuildConfig, got {type(cfg).__name__}")
    _CURRENT = cfg
    return cfg


def current() -> BuildConfig:
    """The active BuildConfig. Auto-bootstraps via :func:`bootstrap`
    on first call if no config has been installed yet (the path
    direct script invocations take). Subsequent calls return the
    cached instance."""
    if _CURRENT is None:
        return bootstrap()
    return _CURRENT


def is_set() -> bool:
    """Has a config been installed in this process?"""
    return _CURRENT is not None


# Track the location of this module so bootstrap can find the
# auto-generated factory-defaults sibling next to ``build.py``.
_HERE = os.path.dirname(os.path.abspath(__file__))


def factory_defaults_path() -> str:
    """Absolute path to the auto-generated ``hlcl/factory-defaults.json``
    (regenerated by the Vite plugin in ``vite/plugins/``)."""
    return os.path.join(_HERE, "factory-defaults.json")


def _peel_config_argv(argv: list[str]) -> str | None:
    """Find ``--config <path>`` (or ``--config=<path>``) anywhere in
    ``argv`` and remove BOTH tokens in place. Returns the path if
    found, ``None`` otherwise. Mutates ``argv`` so a script's own
    argparse pass doesn't choke on the extra flag."""
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--config":
            if i + 1 >= len(argv):
                raise ValueError("--config requires a path argument")
            path = argv[i + 1]
            del argv[i : i + 2]
            return path
        if a.startswith("--config="):
            path = a[len("--config=") :]
            del argv[i]
            return path
        i += 1
    return None


def bootstrap(argv: list[str] | None = None) -> BuildConfig:
    """Load a BuildConfig from ``--config`` in ``argv`` (default
    :data:`sys.argv`), or fall back to ``hlcl/factory-defaults.json``.

    Idempotent: if a config has already been installed via
    :func:`set_current`, returns it unchanged. Otherwise installs
    the loaded config as ``_CURRENT`` so subsequent ``current()``
    calls are O(1).

    Raises ``RuntimeError`` if neither a ``--config`` flag nor a
    factory-defaults file is available.
    """
    if _CURRENT is not None:
        return _CURRENT

    argv_target = argv if argv is not None else sys.argv
    path = _peel_config_argv(argv_target)
    if path is None and os.path.isfile(factory_defaults_path()):
        path = factory_defaults_path()
    if path is None:
        raise RuntimeError(
            "No build configuration available. Pass `--config <path>` "
            "or generate `hlcl/factory-defaults.json` (run `npm run dev` "
            "or `npm run regen` once)."
        )
    return set_current(load(path))


# ---------------------------------------------------------------------------
# Footprint slot helpers (shared by every vendor row builder)
# ---------------------------------------------------------------------------


def order_densities(densities: Iterable[str]) -> Tuple[str, ...]:
    """Re-order an arbitrary iterable of density codes to the
    canonical .xls slot assignment order (Nominal first, then Least,
    then Most). Unknown codes are dropped silently. Useful when a
    caller has a list in hand from a per-family override and wants
    to drive a footprint emission loop."""
    seen = set()
    out = []
    for d in densities:
        if d in ALL_DENSITIES and d not in seen:
            seen.add(d)
            out.append(d)
    # Filter further by canonical order so caller doesn't have to
    # care what order their input was in.
    return tuple(d for d in DENSITY_ORDER if d in seen)


def footprint_columns(library_path: str, fp_root: str, densities: Iterable[str]) -> list:
    """Return the six .xls cells (``Library Path 1, Footprint 1,
    Library Path 2, Footprint 2, Library Path 3, Footprint 3``) for
    a part with footprint root ``fp_root``.

    Slot assignment uses :data:`DENSITY_ORDER` (N → L → M). Disabled
    slots are filled with empty strings on both the path and name
    columns so the .xls schema stays fixed-width and Altium's DbLib
    doesn't trip on missing cells.
    """
    ordered = order_densities(densities)
    cells: list = []
    for i in range(3):
        if i < len(ordered):
            cells.extend([library_path, fp_root + ordered[i]])
        else:
            cells.extend(["", ""])
    return cells
