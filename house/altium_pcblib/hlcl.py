"""
HLCL-001 (Humanity's Last Component Library) drawing-standards
constants.

Values are sourced from ``settings.toml`` (the [hlcl] section) so the
.PcbLib writer, the standards document at ``docs/standards/HLCL-001.tex``,
and any reviewer checking the build all read the same numbers from
one place. If you change a value in ``settings.toml``, also update the
matching section of the standards document and re-run
``python build.py all`` (plus ``python build.py standards`` if you
want the regenerated PDF) so the .PcbLib + standards PDF stay in sync.
"""

from _house_settings import SETTINGS


# §11.2 Pads:
#   shape:   rounded rectangle, 25% corner radius
#   sm exp:  manual 0.05 mm per pad
#   pm exp:  inherit board rule (no per-pad override)
#   sliver:  >= 0.1 mm between adjacent mask apertures, otherwise
#            bridge with a single Top Solder region instead of
#            shrinking the copper.
PAD_CORNER_RADIUS_PERCENT = SETTINGS.hlcl.pad_corner_radius_percent
SOLDER_MASK_EXPANSION_MM  = SETTINGS.hlcl.solder_mask_expansion_mm
MIN_SOLDER_MASK_SLIVER_MM = SETTINGS.hlcl.min_solder_mask_sliver_mm

# §11.4 Component outline + centroid (Mechanical 15):
#   line width 0.1 mm, closed rectangle = nominal L x W. Centroid is a
#   crosshair clipped to the component outline with each arm capped at
#   MAX_CROSSHAIR_HALF_ARM_MM so the total cross length is never longer
#   than 2 * MAX_CROSSHAIR_HALF_ARM_MM = 1 mm.
OUTLINE_LINE_WIDTH_MM     = SETTINGS.hlcl.outline_line_width_mm
MAX_CROSSHAIR_HALF_ARM_MM = SETTINGS.hlcl.max_crosshair_half_arm_mm

# §11.3 3D body (Mechanical 1): nominal L x W x H, Z=0. Chip
# components sit on the board so there's no standoff.
COMPONENT_BODY_STANDOFF_MM = SETTINGS.hlcl.component_body_standoff_mm
