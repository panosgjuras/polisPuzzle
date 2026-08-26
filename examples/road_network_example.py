"""Download and prepare a drivable road network for a study area."""

from pathlib import Path

from polispuzzle import road_net

# %% Step 1. Define the study area

# Preferred option: provide a polygon file. Set this to None when unavailable.
# Supported formats: GPKG, SHP, GeoJSON, JSON, KML, and GML.
polygon_path = Path("data/study_area.gpkg")

# If there is no polygon, provide a known OSM place name directly. Leave this
# as None to discover the correct names from a coordinate instead.
city = None  # Example: "Kalamaria, Greece"

# Coordinates use WGS84 decimal degrees: x = longitude, y = latitude.
x = 22.8016
y = 37.5673

if polygon_path is not None and polygon_path.is_file():
    study_area = str(polygon_path)
elif city:
    study_area = city
else:
    candidates = road_net.study_area_candidates(x, y)
    if not candidates:
        raise RuntimeError("No OSM study-area names were found for the coordinate")

    print("OSM study-area candidates:")
    for index, candidate in enumerate(candidates, start=1):
        print(f"  {index}: {candidate['name']} ({candidate['tag']})")

    selection = int(input("Select the study area number: ")) - 1
    study_area = candidates[selection]["query"]

print(f"Selected study area: {study_area}")

# %% Step 2. Select the level of detail

# There are three levels of detail
level_descriptions = {
    1: "all supported drivable roads",
    2: "main and intermediate roads; excludes local and residential streets",
    3: "major arterial roads only",
}

print("\nRoad-network detail levels:")
for level, (level_label, road_types) in road_net.LEVELS.items():
    print(f"\n  {level}  {level_label}")
    print(f"     {level_descriptions[level]}")
    print(f"     OSM highway categories: {', '.join(sorted(road_types))}")

while True:
    try:
        detail_level = int(input("\nSelect the detail level (1/2/3): "))
        if detail_level in road_net.LEVELS:
            break
    except ValueError:
        pass
    print("Please enter 1, 2, or 3.")

label, allowed_road_types = road_net.LEVELS[detail_level]

# %% Step 3. Download the road network and visualize

# The surrounding model area is added automatically to reduce boundary effects.
network, buffer_km = road_net.download_area(study_area, allowed_road_types)

print(f"Downloaded {network.number_of_edges()} road links ({label})")
print(f"Automatic model-area buffer: {buffer_km:.1f} km")

road_net.plotNetwork(network, study_area) # A first plot for inspection

# %% Step 4. Check connectivity
network = road_net.connected(network)

# %% Step 5. Save the network

# A new subfolder is created. It contains network.xml, links.gpkg, and nodes.gpkg.
output_path = "/Users/panosgtzouras/Desktop/datasets" # Change the path, it is a local path
city = "Nafplio"
network_name = f"scenario{city}_{label}"
saved_files = road_net.save_network(network, output_path, network_name)

print(f"Network outputs saved in: {saved_files['folder']}")
