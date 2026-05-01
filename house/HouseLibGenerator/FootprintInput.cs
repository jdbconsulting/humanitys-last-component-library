using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace HouseLibGenerator;

// Mirrors the schema written by house/build_house_footprints.py
// (search for "JSON sidecar" in that file). schemaVersion = 1.

internal sealed class HouseFootprintsDoc
{
    [JsonPropertyName("schemaVersion")] public int SchemaVersion { get; set; }
    [JsonPropertyName("vendorPriority")] public List<string> VendorPriority { get; set; } = new();
    [JsonPropertyName("footprints")] public List<FootprintInput> Footprints { get; set; } = new();
}

internal sealed class FootprintInput
{
    [JsonPropertyName("name")]        public string Name { get; set; } = "";
    [JsonPropertyName("vendor")]      public string Vendor { get; set; } = "";
    [JsonPropertyName("drawingNote")] public string DrawingNote { get; set; } = "";
    [JsonPropertyName("kind")]        public string Kind { get; set; } = "";
    [JsonPropertyName("density")]     public string Density { get; set; } = "";
    [JsonPropertyName("bodyMm")]      public BodyDimensions BodyMm { get; set; } = new();
}

internal sealed class BodyDimensions
{
    [JsonPropertyName("lengthNominal")]          public double LengthNominal { get; set; }
    [JsonPropertyName("widthNominal")]           public double WidthNominal { get; set; }
    [JsonPropertyName("heightNominal")]          public double HeightNominal { get; set; }
    [JsonPropertyName("terminalLengthNominal")]  public double TerminalLengthNominal { get; set; }
}
