using System.Security.Cryptography;
using System.Text;
using OriginalCircuit.AltiumSharp;
using OriginalCircuit.AltiumSharp.BasicTypes;
using OriginalCircuit.AltiumSharp.Records;

namespace HouseLibGenerator;

/// <summary>
/// Builds an Altium <see cref="PcbComponent"/> for a single
/// CAPC / RESC / INDC two-terminal chip footprint, applying both
/// IPC-7351B math and the DDL-001 drawing conventions.
///
/// Coordinate frame (matching <see cref="PadCalculator"/>):
///   * Body length (L) along X, body width (W) along Y.
///   * Pads laid out at (+/-spacing/2, 0) -- terminals on left/right.
///   * Pad CAD size = (LengthAlongTerminal, WidthAcrossTerminal),
///     i.e. (X-extent, Y-extent).
/// </summary>
internal static class ChipFootprintBuilder
{
    public static PcbComponent Build(FootprintInput input, out string diagnostics)
    {
        var diagBuf = new System.Text.StringBuilder();

        if (input.Density.Length != 1)
            throw new ArgumentException(
                $"footprint {input.Name}: density '{input.Density}' must be a single character L/N/M");

        char density = input.Density[0];
        var rule = IpcRules.SelectRule(input.BodyMm.LengthNominal, input.BodyMm.WidthNominal, density);

        var pad = PadCalculator.Compute(
            bodyLengthMm:     input.BodyMm.LengthNominal,
            bodyWidthMm:      input.BodyMm.WidthNominal,
            terminalLengthMm: input.BodyMm.TerminalLengthNominal,
            rule:             rule);

        var fp = new PcbComponent
        {
            Pattern      = input.Name,
            Description  = "",                              // DDL-001 §11: no description on footprint
            Height       = Coord.FromMMs(input.BodyMm.HeightNominal),
            ItemGuid     = "",
            RevisionGuid = "",
        };

        // ---- Pads (Top Layer, rounded rect, 25% radius, manual SM expansion 0.05mm).
        AddPad(fp, "1", -pad.PadCenterSpacingMm / 2.0, pad);
        AddPad(fp, "2", +pad.PadCenterSpacingMm / 2.0, pad);

        // ---- Solder mask bridge if the natural mask sliver is too tight.
        //
        // DDL-001 §11.2.5 requires >= 0.1 mm sliver between adjacent
        // mask apertures. With per-pad expansion E = 0.05 mm, the sliver
        // is (G - 2E). When that comes out below 0.1 mm we *don't*
        // shrink the copper -- IPC pads stay at IPC dimensions -- we
        // overlay a single mask region that bridges the two apertures
        // into one. The region is a rectangle: X spans pad-1-centre to
        // pad-2-centre (so it overlaps each pad by half its length and
        // therefore swallows the inner rounded aperture corners), Y
        // matches the aperture height (pad-width-across-terminal +
        // 2*E).
        double naturalSliverMm =
            pad.GMm - 2.0 * DdlConventions.SolderMaskExpansionMm;
        bool needsBridge = naturalSliverMm < DdlConventions.MinSolderMaskSliverMm - 1e-9;
        if (needsBridge)
        {
            AddSolderMaskBridge(fp, pad);
            diagBuf.AppendLine(
                $"  {input.Name}: natural mask sliver "
                + $"{naturalSliverMm:0.000}mm < "
                + $"{DdlConventions.MinSolderMaskSliverMm}mm; "
                + "added Top Solder bridge region across the two apertures");
        }

        // ---- Component outline + centroid (Mechanical 15, 0.1mm line).
        AddOutlineAndCentroid(fp, input.BodyMm.LengthNominal, input.BodyMm.WidthNominal);

        // ---- 3D body (Mechanical 1, extruded box, nominal L x W x H).
        AddComponentBody(fp,
            bodyLengthMm: input.BodyMm.LengthNominal,
            bodyWidthMm:  input.BodyMm.WidthNominal,
            bodyHeightMm: input.BodyMm.HeightNominal);

        diagnostics = diagBuf.ToString();
        return fp;
    }

    private static void AddPad(PcbComponent fp, string designator, double xMm, IpcChipPad pad)
    {
        // Pad CAD size: X-extent = along-terminal, Y-extent = across-terminal.
        // (See the IPC vs CAD axis convention block in PadCalculator.cs.)
        var size = CoordPoint.FromMMs(
            pad.PadLengthAlongTerminalMm,   // CAD X
            pad.PadWidthAcrossTerminalMm);  // CAD Y
        var p = new PcbPad(PcbPadTemplate.SmtTop)
        {
            Designator                 = designator,
            Layer                      = Layer.TopLayer,
            Location                   = CoordPoint.FromMMs(xMm, 0.0),
            // SizeTop / Middle / Bottom must all be set for the writer
            // to round-trip cleanly even though Simple-stack pads only
            // use SizeTop in practice.
            Size                       = size,
            SizeTop                    = size,
            SizeMiddle                 = size,
            SizeBottom                 = size,
            Shape                      = PcbPadShape.RoundedRectangle,
            ShapeTop                   = PcbPadShape.RoundedRectangle,
            ShapeMiddle                = PcbPadShape.RoundedRectangle,
            ShapeBottom                = PcbPadShape.RoundedRectangle,
            CornerRadius               = (byte)DdlConventions.PadCornerRadiusPercent,
            CornerRadiusTop            = (byte)DdlConventions.PadCornerRadiusPercent,
            CornerRadiusMid            = (byte)DdlConventions.PadCornerRadiusPercent,
            CornerRadiusBot            = (byte)DdlConventions.PadCornerRadiusPercent,
            StackMode                  = PcbStackMode.Simple,
            HoleSize                   = Coord.FromMMs(0),
            HoleShape                  = PcbPadHoleShape.Round,
            // Manual 0.05 mm solder mask expansion (DDL-001 §11.2.5).
            SolderMaskExpansion        = Coord.FromMMs(DdlConventions.SolderMaskExpansionMm),
            SolderMaskExpansionManual  = true,
            // Paste mask: inherit the board-level rule (DDL-001 §11.2.4).
            PasteMaskExpansion         = Coord.FromMMs(0),
            PasteMaskExpansionManual   = false,
        };
        fp.Primitives.Add(p);
    }

    /// <summary>
    /// Add a solder mask region that bridges the two pad apertures into
    /// a single opening. Geometry per DDL-001 §11.2.5:
    /// rectangle from (-spacing/2, -h/2) to (+spacing/2, +h/2),
    /// where h is the aperture height (pad-width-across-terminal + 2*E).
    /// </summary>
    private static void AddSolderMaskBridge(PcbComponent fp, IpcChipPad pad)
    {
        double halfSpacingX = pad.PadCenterSpacingMm / 2.0;
        double halfApertureY =
            (pad.PadWidthAcrossTerminalMm + 2.0 * DdlConventions.SolderMaskExpansionMm) / 2.0;

        var region = new PcbRegion { Layer = Layer.TopSolder };
        region.Outline.Add(CoordPoint.FromMMs(-halfSpacingX, -halfApertureY));
        region.Outline.Add(CoordPoint.FromMMs(+halfSpacingX, -halfApertureY));
        region.Outline.Add(CoordPoint.FromMMs(+halfSpacingX, +halfApertureY));
        region.Outline.Add(CoordPoint.FromMMs(-halfSpacingX, +halfApertureY));
        fp.Primitives.Add(region);
    }

    private static void AddOutlineAndCentroid(PcbComponent fp, double bodyLengthMm, double bodyWidthMm)
    {
        var halfL = bodyLengthMm / 2.0;
        var halfW = bodyWidthMm  / 2.0;
        var w     = Coord.FromMMs(DdlConventions.OutlineLineWidthMm);

        void Track(double x1, double y1, double x2, double y2) =>
            fp.Primitives.Add(new PcbTrack
            {
                Layer = Layer.Mechanical15,
                Start = CoordPoint.FromMMs(x1, y1),
                End   = CoordPoint.FromMMs(x2, y2),
                Width = w,
            });

        // Closed rectangle (nominal L x W).
        Track(-halfL, -halfW, +halfL, -halfW);
        Track(+halfL, -halfW, +halfL, +halfW);
        Track(+halfL, +halfW, -halfL, +halfW);
        Track(-halfL, +halfW, -halfL, -halfW);

        // Centroid crosshair, sized to be visible without overshooting
        // the component outline. Each arm = min(halfBodyAxis,
        // MaxCrosshairHalfArmMm) so the cross stays inside the
        // rectangle drawn above and never grows beyond the per-axis
        // cap (DDL-001 §11.4: total cross length capped at 1 mm).
        double crossHalfX = Math.Min(halfL, DdlConventions.MaxCrosshairHalfArmMm);
        double crossHalfY = Math.Min(halfW, DdlConventions.MaxCrosshairHalfArmMm);
        Track(-crossHalfX, 0,           +crossHalfX, 0);
        Track(0,           -crossHalfY, 0,           +crossHalfY);
    }

    private static void AddComponentBody(PcbComponent fp,
        double bodyLengthMm,
        double bodyWidthMm,
        double bodyHeightMm)
    {
        var halfL = bodyLengthMm / 2.0;
        var halfW = bodyWidthMm  / 2.0;

        // *** v1 zero-Coord/zero-double round-trip workaround ***
        // AltiumSharp 1.0.2's parameter-collection writer omits the
        // *value* for any 0-valued Coord, double or false bool when
        // `ignoreDefaultValue` is true (the default). The matching
        // strict-parsing reader paths then throw on the empty value.
        // To keep the file friendly to round-tripping tools (and to
        // defend against any other parser that strict-parses these),
        // we bump the otherwise-zero body fields to a sub-display
        // precision value (1 internal Coord unit ~= 25 nm, far below
        // Altium's default 0.001 mm display threshold).
        //
        // Also: V7Layer must be set to "MECHANICAL1" (not the empty
        // string) -- without it Altium's properties dialog shows
        // "Layer not defined" for the body even though the binary
        // Layer field is correct.
        var subPicoCoord = Coord.FromInt32(1);
        var subPicoPoint = new CoordPoint(subPicoCoord, subPicoCoord);
        var body = new PcbComponentBody
        {
            Layer            = Layer.Mechanical1,
            V7Layer          = "MECHANICAL1",
            StandOffHeight   =
                DdlConventions.ComponentBodyStandoffMm > 0
                    ? Coord.FromMMs(DdlConventions.ComponentBodyStandoffMm)
                    : subPicoCoord,
            OverallHeight    = Coord.FromMMs(bodyHeightMm),
            ArcResolution    = subPicoCoord,
            Model3DDz        = subPicoCoord,
            TextureCenter    = subPicoPoint,
            TextureSize      = subPicoPoint,
            Model2DLocation  = subPicoPoint,
            IsShapeBased     = true,
            Identifier       = "ChipBody",
            Name             = "",
            StepModel        = "",
            // Deterministic GUID from the footprint name (MD5 -> Guid).
            // The reader uses ModelId as the key linking the binary
            // model stream back to the body, so it just has to be
            // unique within the .pcblib; deriving it from the name
            // makes the build reproducible byte-for-byte and makes
            // diffs across builds easy to read.
            ModelId          = DeterministicGuid(fp.Pattern),
            Texture          = "",
            BodyOpacity3D    = 1.0,
            ModelEmbed       = true,
            TextureRotation  = 1e-6,
            // Mid-grey for resistors, off-white for caps/inductors --
            // makes the library easier to scan in 3D view.
            BodyColor3D      = ChipColorFor(fp.Pattern),
        };
        body.Outline.Add(CoordPoint.FromMMs(-halfL, -halfW));
        body.Outline.Add(CoordPoint.FromMMs(+halfL, -halfW));
        body.Outline.Add(CoordPoint.FromMMs(+halfL, +halfW));
        body.Outline.Add(CoordPoint.FromMMs(-halfL, +halfW));
        fp.Primitives.Add(body);
    }

    private static System.Drawing.Color ChipColorFor(string footprintName)
    {
        // Body colors must match the dominant body solid in the
        // matching parametric STEP file (see house/stepgen/colors.py).
        // Altium uses BodyColor3D when the embedded STEP fails to
        // load and as the 2D-top-view fill for the body outline; the
        // 3D rendering picks up COLOUR_RGB from the STEP itself.
        if (footprintName.StartsWith("RESC", StringComparison.Ordinal))
            return System.Drawing.Color.FromArgb(158, 158, 158);  // alumina substrate (#9E9E9E)
        if (footprintName.StartsWith("CAPC", StringComparison.Ordinal))
            return System.Drawing.Color.FromArgb(184, 134, 11);   // MLCC tan (#B7860B)
        if (footprintName.StartsWith("INDC", StringComparison.Ordinal))
            return System.Drawing.Color.FromArgb(38, 77, 148);    // ferrite blue (#264D94)
        return System.Drawing.Color.FromArgb(160, 160, 160);
    }

    /// <summary>
    /// Derive a deterministic Altium-flavoured GUID
    /// ("{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}") from a footprint
    /// name. MD5 is fine here -- this is purely an in-file ID, no
    /// security implication -- and it gives us byte-stable .pcblib
    /// outputs across builds without needing a state file.
    /// </summary>
    private static string DeterministicGuid(string footprintName)
    {
        var hash = MD5.HashData(Encoding.UTF8.GetBytes(footprintName));
        return new Guid(hash).ToString("B").ToUpperInvariant();
    }
}
