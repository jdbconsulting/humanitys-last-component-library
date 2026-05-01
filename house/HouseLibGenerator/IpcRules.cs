namespace HouseLibGenerator;

/// <summary>
/// IPC-7351B rules for two-terminal rectangular chip components
/// (RESC / CAPC / INDC). All values copied straight from the standard
/// (June 2010 edition); see references/ipc-7351b-*.pdf in the repo.
///
/// We model two body-size regimes:
///   * Tbl 3-5 -- bodies >= metric 1608 (imperial 0603)
///   * Tbl 3-6 -- bodies <  metric 1608
/// Both tables share a heel goal of 0 (no heel fillet needed for chip
/// terminations).
///
/// Fabrication tolerance F and placement tolerance P
/// -------------------------------------------------
/// IPC-7351B does NOT include F and P in the per-family J-factor
/// tables (Tbl 3-2 through 3-22). Section 3.1.4 (page 12 of the PDF)
/// provides the only explicit numeric values, embedded in the SOIC
/// worked example:
///
///     "F is 0.1 mm (assumed fabrication tolerance);
///      P is 0.05 mm (assumed assembly equipment placement tolerance)"
///
/// Section 3.1.5 (page 15) further notes that "individual tolerances
/// for fabrication ('F') and component placement equipment accuracy
/// ('P') are assumed to be as given in the IPC-7351 land pattern
/// libraries", i.e. they live in the LP Calculator's built-in library
/// and may be overridden per-user. The standard PDF therefore
/// effectively recommends F=0.10/P=0.05 as the textbook defaults, and
/// keeps them constant across density variants -- only the J factors
/// and round-off granularity change with density.
///
/// This is intentionally NOT what Altium's IPC Compliant Footprint
/// Wizard ships with. Altium's LP wizard appears to default to
/// F=0.05/P=0.05 for chip components (~0.04 mm smaller pads on each
/// side); on Density C (Least) for sub-1608 chips the side fillet
/// J_S=-0.05 mm combined with that smaller F/P drives the pad's
/// across-terminal width below the component's body width
/// (e.g. 0402 -> 0.18 mm pad width on a 0.20 mm body), which is the
/// "pad smaller than component" effect noted in this repo's commit
/// history. We stick with the IPC-7351B standard-text values.
///
/// If you want to compare against Altium's output, drop the constants
/// below to F=0.05/P=0.05; otherwise leave them at the standard text.
/// </summary>
internal static class IpcRules
{
    /// <summary>
    /// Fabrication tolerance F, mm (IPC-7351B §3.1.4 SOIC worked
    /// example, page 12 of the PDF).
    /// </summary>
    public const double FabricationToleranceMm = 0.10;

    /// <summary>
    /// Placement tolerance P, mm (IPC-7351B §3.1.4 SOIC worked
    /// example, page 12 of the PDF).
    /// </summary>
    public const double PlacementToleranceMm = 0.05;

    /// <summary>
    /// Pick which J/round-off table applies to a given body. The
    /// crossover sits at metric 1608 (imperial 0603): metric 1608 itself
    /// uses Table 3-5, anything smaller uses Table 3-6.
    /// </summary>
    public static IpcChipRule SelectRule(double bodyLengthMm, double bodyWidthMm, char density)
    {
        // The "1608 boundary" in IPC text is on body length (the long
        // axis along which the toe extends). Use that as the threshold.
        bool isLargeBody = bodyLengthMm >= 1.6 - 0.001;
        return isLargeBody ? Table_3_5(density) : Table_3_6(density);
    }

    // Table 3-5: Rectangular chip components >= 1608 metric.
    private static IpcChipRule Table_3_5(char density) => density switch
    {
        'M' => new IpcChipRule(   ToeJt: 0.55, HeelJh: 0.00, SideJs:  0.05, RoundOffMm: 0.05, CourtyardExcessMm: 0.5),
        'N' => new IpcChipRule(   ToeJt: 0.35, HeelJh: 0.00, SideJs:  0.00, RoundOffMm: 0.05, CourtyardExcessMm: 0.25),
        'L' => new IpcChipRule(   ToeJt: 0.15, HeelJh: 0.00, SideJs: -0.05, RoundOffMm: 0.05, CourtyardExcessMm: 0.1),
        _   => throw new ArgumentException($"unknown density '{density}'; expected L/N/M")
    };

    // Table 3-6: Rectangular chip components < 1608 metric.
    private static IpcChipRule Table_3_6(char density) => density switch
    {
        'M' => new IpcChipRule(   ToeJt: 0.30, HeelJh: 0.00, SideJs:  0.05, RoundOffMm: 0.02, CourtyardExcessMm: 0.2),
        'N' => new IpcChipRule(   ToeJt: 0.20, HeelJh: 0.00, SideJs:  0.00, RoundOffMm: 0.02, CourtyardExcessMm: 0.15),
        'L' => new IpcChipRule(   ToeJt: 0.10, HeelJh: 0.00, SideJs: -0.05, RoundOffMm: 0.02, CourtyardExcessMm: 0.1),
        _   => throw new ArgumentException($"unknown density '{density}'; expected L/N/M")
    };
}

/// <summary>Per-density IPC rule set for chip components.</summary>
/// <param name="ToeJt">Toe land protrusion goal J_T (mm).</param>
/// <param name="HeelJh">Heel land protrusion goal J_H (mm). Always 0 for chips.</param>
/// <param name="SideJs">Side land protrusion goal J_S (mm). Can be negative.</param>
/// <param name="RoundOffMm">Round-off granularity per the table footer.</param>
/// <param name="CourtyardExcessMm">Courtyard excess (we don't draw a courtyard, but kept here for completeness).</param>
internal readonly record struct IpcChipRule(
    double ToeJt,
    double HeelJh,
    double SideJs,
    double RoundOffMm,
    double CourtyardExcessMm);
