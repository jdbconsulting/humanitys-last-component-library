using System.Text.Json;
using OriginalCircuit.AltiumSharp;
using OriginalCircuit.AltiumSharp.BasicTypes;
using HouseLibGenerator;

// Usage:
//   dotnet run --project house/HouseLibGenerator
//       [--input    build/footprints/house-footprints.json]
//       [--output   build/house.PcbLib]
//       [--step-dir build/step]
//
// All paths default to the repo's standard locations; Make wires them
// in explicitly anyway so this can be tested from any working directory.
//
// --step-dir points at the directory of parametric .step files emitted
// by `house/build_step_models.py`. The body geometry of a chip is
// identical across the L / N / M density variants (those only change
// pad math, not the component itself), so the Python generator emits
// one .step per *footprint root* — the FootprintName minus its
// trailing density letter — and we look up the matching file here by
// stripping the same suffix. All three density variants of a root
// therefore embed (and share) the same STEP body. When the file is
// present its contents are stuffed into the matching component body's
// `StepModel` field so AltiumSharp can zlib-compress + embed it. When
// absent the .pcblib still builds, but each component's 3D model
// degrades to the bare extruded outline that the v1 writer falls back
// to when StepModel is empty.

string inputPath  = "build/footprints/house-footprints.json";
string outputPath = "build/house.PcbLib";
string stepDir    = "build/step";

for (int i = 0; i < args.Length; i++)
{
    switch (args[i])
    {
        case "--input"    when i + 1 < args.Length: inputPath  = args[++i]; break;
        case "--output"   when i + 1 < args.Length: outputPath = args[++i]; break;
        case "--step-dir" when i + 1 < args.Length: stepDir    = args[++i]; break;
        case "-h":
        case "--help":
            Console.WriteLine(
                "Usage: dotnet run --project house/HouseLibGenerator -- " +
                "[--input <house-footprints.json>] [--output <house.PcbLib>] " +
                "[--step-dir <build/step>]");
            return 0;
        default:
            Console.Error.WriteLine($"unknown argument: {args[i]}");
            return 2;
    }
}

if (!File.Exists(inputPath))
{
    Console.Error.WriteLine(
        $"error: input JSON not found: {inputPath}\n" +
        "Run `make house-footprints` (or `python house/build_house_footprints.py`) first.");
    return 1;
}

var jsonOpts = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
var doc = JsonSerializer.Deserialize<HouseFootprintsDoc>(
    File.ReadAllText(inputPath), jsonOpts)
    ?? throw new InvalidOperationException($"failed to deserialize {inputPath}");

if (doc.SchemaVersion != 1)
{
    Console.Error.WriteLine(
        $"error: schemaVersion {doc.SchemaVersion} not supported by this generator (expected 1). " +
        "Update house/HouseLibGenerator/FootprintInput.cs and re-run.");
    return 1;
}

var lib = new PcbLib();
// Default library units. Altium reads this and sets the editor's
// display unit when the .PcbLib is opened; without it Altium falls
// back to mils. mm is the unit DDL-001 specifies for everything in
// this library.
lib.Header.DisplayUnit = Unit.Millimeter;

int kindUnsupported = 0;
int stepEmbedded   = 0;
int stepMissing    = 0;
var diagnostics = new List<string>();

// Cache STEP file contents by root so we read each file at most once
// even though L / N / M variants of the same root all embed it. Null
// values memoise misses (file genuinely doesn't exist). Also tracks
// which roots actually got embedded into at least one component, for
// the post-build diagnostic.
var stepCache    = new Dictionary<string, string?>(StringComparer.Ordinal);
var stepRootsUsed = new HashSet<string>(StringComparer.Ordinal);

foreach (var fp in doc.Footprints)
{
    if (fp.Kind != "C" && fp.Kind != "R")
    {
        // INDC chip inductors and FB ferrite beads share the chip
        // body geometry but the repo doesn't ship them yet. Skip with
        // a counted warning so the build doesn't silently drop rows
        // when a future per-vendor script starts emitting them.
        kindUnsupported++;
        continue;
    }

    var component = ChipFootprintBuilder.Build(fp, out string fpDiag);

    // Strip the trailing density letter (L/N/M) to derive the root
    // the Python STEP generator keyed by. The vendor-side schema in
    // vendors/_common.py guarantees exactly one trailing density
    // character, so this is safe.
    string root = fp.Name.Length > 0 ? fp.Name[..^1] : fp.Name;
    if (!stepCache.TryGetValue(root, out string? stepText))
    {
        var stepPath = Path.Combine(stepDir, $"{root}.step");
        stepText = File.Exists(stepPath) ? File.ReadAllText(stepPath) : null;
        stepCache[root] = stepText;
    }

    if (stepText is not null)
    {
        foreach (var prim in component.Primitives.OfType<OriginalCircuit.AltiumSharp.Records.PcbComponentBody>())
        {
            prim.StepModel = stepText;
            prim.ModelEmbed = true;
        }
        stepEmbedded++;
        stepRootsUsed.Add(root);
    }
    else
    {
        stepMissing++;
    }

    lib.Items.Add(component);
    if (!string.IsNullOrWhiteSpace(fpDiag))
        diagnostics.Add(fpDiag.TrimEnd());
}

if (kindUnsupported > 0)
{
    Console.Error.WriteLine(
        $"NOTE: skipped {kindUnsupported} footprint(s) with kind != C/R " +
        "(INDC / FB chip families are not implemented yet; add a builder under " +
        "house/HouseLibGenerator/ when needed).");
}

Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(outputPath))!);
using (var w = new PcbLibWriter())
    w.Write(lib, outputPath, overwrite: true);

var info = new FileInfo(outputPath);
Console.WriteLine(
    $"Wrote {outputPath}: {lib.Items.Count} footprints, {info.Length} bytes.");
Console.WriteLine(
    $"  3D models: {stepEmbedded} embedded ({stepRootsUsed.Count} unique " +
    $".step files from {stepDir}/, shared across L/N/M density variants), " +
    $"{stepMissing} missing");
if (stepMissing > 0)
{
    Console.Error.WriteLine(
        $"NOTE: {stepMissing} footprint(s) had no matching .step file in " +
        $"{stepDir}/. Run `make house-step-models` to regenerate them.");
}

if (diagnostics.Count > 0)
{
    Console.Error.WriteLine();
    Console.Error.WriteLine($"Mask-bridge notices ({diagnostics.Count}):");
    foreach (var d in diagnostics)
        Console.Error.WriteLine(d);
}

return 0;
