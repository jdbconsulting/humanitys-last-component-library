namespace HouseLibGenerator;

/// <summary>
/// IPC-7351B chip-component land pattern math (per §3.1.4 equations
/// for two-terminal rectangular chip parts).
///
/// All inputs and outputs are in millimetres, all dimensions are
/// nominal-only (the repo's per-pin tolerance policy is 0% and the
/// JSON sidecar enforces L_min == L_max etc. before this code runs).
///
/// Frame conventions used throughout the generator:
///
///   * The component is laid out horizontally, terminals to the left
///     and right. The body's *length* L is along the X axis (between
///     the two pads); the body's *width* W is along the Y axis.
///   * IPC's "Z, G, Y" land-pattern dimensions are along X (the
///     terminal axis). IPC's "X" land-pattern dimension is along Y
///     (perpendicular to the terminal axis).
///   * Pad CAD size therefore is `(LengthAlongTerminal, WidthAcrossTerminal)`,
///     i.e. (along-X-extent, along-Y-extent). The naming in this file
///     uses the "along-terminal" / "across-terminal" terms rather than
///     bare X/Y so the IPC-vs-CAD axis swap can't be confused.
/// </summary>
internal static class PadCalculator
{
    /// <summary>Fabrication tolerance F, mm (IPC-7351B §3.1.3).</summary>
    public const double FabricationToleranceMm = IpcRules.FabricationToleranceMm;

    /// <summary>Placement tolerance P, mm (IPC-7351B §3.1.3).</summary>
    public const double PlacementToleranceMm   = IpcRules.PlacementToleranceMm;

    /// <summary>
    /// IPC-7351B equations (§3.1.4):
    ///
    ///   Z_max = L_min + 2*J_T + sqrt(C_L^2 + F^2 + P^2)
    ///   G_min = S_max - 2*J_H - sqrt(C_S^2 + F^2 + P^2)
    ///   X_max = W_min + 2*J_S + sqrt(C_W^2 + F^2 + P^2)
    ///
    /// where S_max = L_max - 2*T_min  (gap between terminations,
    /// max condition; collapses to L - 2T when tolerances are 0).
    /// All component tolerances C_* are 0 by repo policy.
    /// </summary>
    public static IpcChipPad Compute(
        double bodyLengthMm,
        double bodyWidthMm,
        double terminalLengthMm,
        IpcChipRule rule)
    {
        // Component tolerance C terms are zero (repo policy), so the
        // RMS tolerance reduces to sqrt(F^2 + P^2).
        double rms = Math.Sqrt(
            FabricationToleranceMm * FabricationToleranceMm +
            PlacementToleranceMm   * PlacementToleranceMm);

        double sMax = bodyLengthMm - 2.0 * terminalLengthMm;
        double zMax = bodyLengthMm + 2.0 * rule.ToeJt  + rms;
        double gMin = sMax          - 2.0 * rule.HeelJh - rms;
        double xMax = bodyWidthMm   + 2.0 * rule.SideJs + rms;

        // Round to the table's round-off granularity. IPC-7351B says
        // "round to the nearest 0.05 mm" (Tbl 3-5) or "0.02 mm" (Tbl 3-6).
        // Use banker's rounding away-from-zero on .5 to match the
        // behaviour of Altium's IPC LP Calculator.
        double zR = RoundToStep(zMax, rule.RoundOffMm);
        double gR = RoundToStep(gMin, rule.RoundOffMm);
        double xR = RoundToStep(xMax, rule.RoundOffMm);

        // Per-pad geometry derived from Z/G/X. Centre-to-centre spacing
        // along the terminal axis is (Z+G)/2; per-pad length along the
        // terminal is (Z-G)/2; per-pad width across the terminal is X.
        double padCenterSpacing      = (zR + gR) / 2.0;
        double padLengthAlongTerm    = (zR - gR) / 2.0;
        double padWidthAcrossTerm    = xR;

        return new IpcChipPad(
            ZMm:                      zR,
            GMm:                      gR,
            XMm:                      xR,
            PadCenterSpacingMm:       padCenterSpacing,
            PadLengthAlongTerminalMm: padLengthAlongTerm,
            PadWidthAcrossTerminalMm: padWidthAcrossTerm);
    }

    /// <summary>
    /// Round to the nearest multiple of <paramref name="stepMm"/>, with
    /// .5 rounding away from zero (matching Altium's behaviour).
    /// </summary>
    private static double RoundToStep(double value, double stepMm)
    {
        if (stepMm <= 0.0) return value;
        double rounded = Math.Round(value / stepMm, MidpointRounding.AwayFromZero) * stepMm;
        // Re-quantise the result to a clean 4-decimal representation
        // so the .PcbLib doesn't accumulate IEEE-754 noise.
        return Math.Round(rounded, 4);
    }
}

/// <summary>
/// IPC pad geometry result for a two-terminal chip. All in mm.
///
/// (Z, G, X) are the canonical IPC-7351B outputs; the per-pad fields
/// are derived (so callers don't have to recompute them) and named
/// "along-terminal" / "across-terminal" rather than bare X/Y to keep
/// the IPC-vs-CAD axis mapping unambiguous (see <see cref="PadCalculator"/>
/// for the convention).
/// </summary>
internal readonly record struct IpcChipPad(
    double ZMm,
    double GMm,
    double XMm,
    double PadCenterSpacingMm,
    double PadLengthAlongTerminalMm,
    double PadWidthAcrossTerminalMm);
