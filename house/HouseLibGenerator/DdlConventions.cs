namespace HouseLibGenerator;

/// <summary>
/// Constants pulled from <c>docs/standards/DDL-001.tex</c> (the DD Labs
/// EEE Component Standards). If you change one of these, also update
/// the LaTeX standards doc -- and re-build the resulting .PcbLib so
/// all consumers see the same numbers.
/// </summary>
internal static class DdlConventions
{
    // §11.2 Pads:
    //   shape:   rounded rectangle, 25% corner radius
    //   sm exp:  manual 0.05 mm per pad
    //   pm exp:  inherit board rule (no per-pad override)
    //   sliver:  >= 0.1 mm between adjacent mask apertures, otherwise
    //            bridge with a single Top Solder region instead of
    //            shrinking the copper.
    public const int    PadCornerRadiusPercent = 25;
    public const double SolderMaskExpansionMm  = 0.05;
    public const double MinSolderMaskSliverMm  = 0.1;

    // §11.4 Component outline + centroid (Mechanical 15):
    //   line width 0.1 mm, closed rectangle = nominal L x W. Centroid
    //   is a crosshair clipped to the component outline with each arm
    //   capped at MaxCrosshairHalfArmMm so the total cross length is
    //   never longer than 2 * MaxCrosshairHalfArmMm = 1 mm.
    public const double OutlineLineWidthMm    = 0.1;
    public const double MaxCrosshairHalfArmMm = 0.5;

    // §11.3 3D body (Mechanical 1): nominal L x W x H, Z=0.
    // Chip components sit on the board so there's no standoff.
    public const double ComponentBodyStandoffMm = 0.0;
}
