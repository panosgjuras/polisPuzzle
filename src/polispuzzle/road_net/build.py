import csv
import gzip
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import geopandas as gpd
import networkx as nx
import osmnx as ox

__all__ = [
    "LEVELS",
    "study_area_candidates",
    "study_polygon",
    "auto_buffer_km",
    "buffer_rings",
    "download_area",
    "filter_types",
    "connected",
    "link_rows",
    "crosstabs",
    "write_matsim",
    "write_gpkg",
    "save_network",
    "process",
]

CRS_OUT = "EPSG:2100"
KMH = 1000.0 / 3600.0

HIGHWAY = {
    "motorway":       (2, 120 * KMH, 2000.0),
    "motorway_link":  (1,  80 * KMH, 1500.0),
    "trunk":          (1,  80 * KMH, 2000.0),
    "trunk_link":     (1,  50 * KMH, 1500.0),
    "primary":        (1,  50 * KMH, 1500.0),
    "primary_link":   (1,  50 * KMH, 1500.0),
    "secondary":      (1,  50 * KMH, 1000.0),
    "secondary_link": (1,  30 * KMH, 1000.0),
    "tertiary":       (1,  40 * KMH,  600.0),
    "tertiary_link":  (1,  30 * KMH,  600.0),
    "unclassified":   (1,  40 * KMH,  600.0),
    "residential":    (1,  30 * KMH,  600.0),
    "living_street":  (1,  20 * KMH,  300.0),
}

HIERARCHY = ["motorway", "motorway_link", "trunk", "trunk_link",
             "primary", "primary_link", "secondary", "secondary_link",
             "tertiary", "tertiary_link", "unclassified",
             "residential", "living_street"]

ARTERIAL = {"motorway", "motorway_link", "trunk", "trunk_link",
            "primary", "primary_link", "secondary", "secondary_link"}

LEVELS = {
    1: ("full", set(HIGHWAY)),
    2: ("medium", ARTERIAL | {"tertiary", "tertiary_link"}),
    3: ("arterial", set(ARTERIAL)),
}

ARTERIAL_FILTER = ('["highway"~"motorway|motorway_link|trunk|trunk_link|'
                   'primary|primary_link|secondary|secondary_link"]')

NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
STUDY_AREA_TAGS = (
    "neighbourhood", "suburb", "quarter", "city_district", "borough",
    "village", "town", "city", "municipality", "county",
    "state_district", "state", "region",
)


def _first(value):
    if isinstance(value, (list, tuple)):
        return value[0] if value else None
    return value


def _to_int(value):
    value = _first(value)
    if value is None:
        return None
    try:
        n = int(float(str(value).split(";")[0]))
        return n if n > 0 else None
    except (ValueError, TypeError):
        return None


def _to_ms(value):
    value = _first(value)
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in ("none", "signals", "variable", "walk"):
        return None
    try:
        if "mph" in text:
            return float(text.replace("mph", "").strip()) * 0.44704
        return float(text.split()[0]) * KMH
    except (ValueError, IndexError):
        return None


def _road_type(data):
    hw = _first(data.get("highway"))
    return hw if hw in HIGHWAY else None


def _tag_area(G, value):
    for _, _, d in G.edges(data=True):
        d["area"] = value
    return G


def study_area_candidates(x, y, timeout=30):
    """Return OSM place and administrative names containing a WGS84 point.

    ``x`` is longitude and ``y`` is latitude, both in decimal degrees. The
    returned candidates are ordered from the smallest available place to the
    largest administrative area. Each candidate's ``query`` value can be
    passed directly to :func:`download_area`.
    """
    x = float(x)
    y = float(y)
    if not -180 <= x <= 180:
        raise ValueError("x must be a longitude between -180 and 180")
    if not -90 <= y <= 90:
        raise ValueError("y must be a latitude between -90 and 90")

    parameters = urlencode({
        "lat": y,
        "lon": x,
        "format": "jsonv2",
        "addressdetails": 1,
        "layer": "address",
        "zoom": 15,
    })
    request = Request(
        "%s?%s" % (NOMINATIM_REVERSE_URL, parameters),
        headers={"User-Agent": "PolisPuzzle/0.1 (road-network study area lookup)"},
    )
    with urlopen(request, timeout=timeout) as response:
        result = json.load(response)

    address = result.get("address", {})
    candidates = []
    seen = set()
    for index, tag in enumerate(STUDY_AREA_TAGS):
        name = address.get(tag)
        if not name or name in seen:
            continue
        seen.add(name)
        parents = [address.get(parent) for parent in STUDY_AREA_TAGS[index + 1:]]
        parents.append(address.get("country"))
        query_parts = []
        for part in [name] + parents:
            if part and part not in query_parts:
                query_parts.append(part)
        query = ", ".join(query_parts)
        candidates.append({"tag": tag, "name": name, "query": query})
    return candidates


POLYGON_FILES = (".gpkg", ".shp", ".geojson", ".json", ".kml", ".gml")


def study_polygon(source):
    if source.lower().endswith(POLYGON_FILES):
        if not os.path.exists(source):
            raise SystemExit("file not found: %s" % source)
        gdf = gpd.read_file(source)
        if gdf.empty:
            raise SystemExit("no features in %s" % source)
        if gdf.crs is None:
            raise SystemExit("file has no CRS: %s" % source)
        gdf = gdf.to_crs("EPSG:4326")
        geometry = gdf.geometry.union_all()
        if geometry.geom_type not in ("Polygon", "MultiPolygon"):
            raise SystemExit("geometry is %s, need a polygon"
                             % geometry.geom_type)
        print("study area from file: %s (%d features)" % (source, len(gdf)))
        return geometry

    gdf = ox.geocode_to_gdf(source)
    return gdf.geometry.iloc[0]


def auto_buffer_km(polygon):
    area = gpd.GeoDataFrame(geometry=[polygon], crs="EPSG:4326").to_crs(CRS_OUT)
    km2 = area.geometry.iloc[0].area / 1e6
    return min(25.0, max(5.0, round(km2 ** 0.5 * 1.5, 1)))


def buffer_rings(polygon, km):
    projected = gpd.GeoDataFrame(geometry=[polygon], crs="EPSG:4326").to_crs(CRS_OUT)
    shape = projected.geometry.iloc[0]

    inner_km = max(1.0, round(km * 0.25, 1))
    inner = shape.buffer(inner_km * 1000.0)
    outer = shape.buffer(km * 1000.0)

    back = gpd.GeoDataFrame(geometry=[inner, outer],
                            crs=CRS_OUT).to_crs("EPSG:4326").geometry
    inner_ring = back.iloc[0].difference(polygon)
    outer_ring = back.iloc[1].difference(back.iloc[0])
    return inner_ring, outer_ring, inner_km


def download_area(source, level_types):
    polygon = study_polygon(source)
    buffer_km = auto_buffer_km(polygon)

    print("downloading study area")
    study = ox.graph_from_polygon(polygon, network_type="drive",
                                  truncate_by_edge=True)
    study = filter_types(study, level_types)
    _tag_area(study, "study")

    inner_ring, outer_ring, inner_km = buffer_rings(polygon, buffer_km)

    print("downloading model area: %.1f km all roads" % inner_km)
    inner = ox.graph_from_polygon(inner_ring, network_type="drive",
                                  truncate_by_edge=True)
    inner = filter_types(inner, set(HIGHWAY))
    _tag_area(inner, "model")

    print("downloading model area: %.1f km arterials" % buffer_km)
    outer = ox.graph_from_polygon(outer_ring, network_type="drive",
                                  custom_filter=ARTERIAL_FILTER,
                                  truncate_by_edge=True)
    outer = filter_types(outer, ARTERIAL)
    _tag_area(outer, "model")

    combined = nx.compose(nx.compose(outer, inner), study)
    combined.graph["crs"] = study.graph["crs"]
    projected = ox.project_graph(combined, to_crs=CRS_OUT)

    area_polygons = gpd.GeoSeries(
        [polygon, inner_ring.union(outer_ring)], crs="EPSG:4326"
    ).to_crs(CRS_OUT)
    projected.graph["study_area_polygon"] = area_polygons.iloc[0]
    projected.graph["model_area_polygon"] = area_polygons.iloc[1]

    return projected, buffer_km


def filter_types(G, allowed):
    H = G.copy()
    H.remove_edges_from([(u, v, k) for u, v, k, d in H.edges(keys=True, data=True)
                         if _road_type(d) not in allowed])
    H.remove_nodes_from([n for n in list(H.nodes) if H.degree(n) == 0])
    return H


def connected(G):
    before_nodes = G.number_of_nodes()
    before_links = G.number_of_edges()
    study_before = sum(1 for _, _, d in G.edges(data=True)
                       if d.get("area") == "study")

    weak = nx.number_weakly_connected_components(G)
    strong = nx.number_strongly_connected_components(G)

    H = ox.truncate.largest_component(G, strongly=True)

    study_after = sum(1 for _, _, d in H.edges(data=True)
                      if d.get("area") == "study")
    lost = before_links - H.number_of_edges()

    print()
    print("connectivity")
    print("  components before: %d weak | %d strong" % (weak, strong))
    print("  removed: %d nodes | %d links (%.1f%%)"
          % (before_nodes - H.number_of_nodes(), lost,
             100.0 * lost / max(1, before_links)))
    if study_before:
        study_lost = study_before - study_after
        print("  study area removed: %d / %d links (%.1f%%)"
              % (study_lost, study_before,
                 100.0 * study_lost / max(1, study_before)))
        if study_lost > 0.02 * study_before:
            print("  warning: more than 2% of the study area was removed")
    return H


def link_rows(G):
    rows = []
    for u, v, d in G.edges(data=True):
        hw = _road_type(d)
        if hw is None:
            continue
        lanes_def, speed_def, cap_lane = HIGHWAY[hw]

        speed = _to_ms(d.get("maxspeed"))
        speed_source = "osm" if speed else "default"
        if not speed:
            speed = speed_def

        raw_lanes = _to_int(d.get("lanes"))
        lanes_source = "osm" if raw_lanes else "default"
        lanes = raw_lanes or lanes_def
        if raw_lanes and not d.get("oneway", False):
            lanes = max(1, round(lanes / 2))

        rows.append({
            "u": u, "v": v,
            "highway": hw,
            "area": d.get("area", "study"),
            "length": max(1.0, float(d.get("length", 1.0))),
            "speed": speed,
            "lanes": float(lanes),
            "capacity": cap_lane * lanes,
            "lanes_source": lanes_source,
            "speed_source": speed_source,
        })
    return rows


def _stats(rows, nodes, label):
    counts = Counter()
    lengths = Counter()
    areas = Counter()
    lanes_src = Counter()
    speed_src = Counter()

    for r in rows:
        counts[r["highway"]] += 1
        lengths[r["highway"]] += r["length"]
        areas[r["area"]] += 1
        lanes_src[r["lanes_source"]] += 1
        speed_src[r["speed_source"]] += 1

    print()
    print("=" * 62)
    print("network: %s" % label)
    print("=" * 62)
    print("nodes: %d | links: %d | length: %.1f km"
          % (nodes, len(rows), sum(lengths.values()) / 1000.0))
    if areas.get("model"):
        print("study area: %d links | model area: %d links"
              % (areas["study"], areas["model"]))
    print()
    print("%-18s %8s %12s" % ("highway", "links", "km"))
    print("-" * 40)
    for hw in sorted(counts, key=lambda h: -counts[h]):
        print("%-18s %8d %12.1f" % (hw, counts[hw], lengths[hw] / 1000.0))
    print("-" * 40)
    print("%-18s %8d %12.1f" % ("total", len(rows),
                                sum(lengths.values()) / 1000.0))
    print()
    total = max(1, len(rows))
    print("lanes from osm: %d/%d (%.1f%%)"
          % (lanes_src["osm"], total, 100 * lanes_src["osm"] / total))
    print("speed from osm: %d/%d (%.1f%%)"
          % (speed_src["osm"], total, 100 * speed_src["osm"] / total))


def _crosstab(title, table, cols, filename, show=True):
    rows = [h for h in HIERARCHY if h in table]
    rows += [h for h in sorted(table) if h not in rows]

    if show:
        print()
        print("=" * 70)
        print(title)
        print("=" * 70)
        width = max([len(r) for r in rows] + [14])
        header = "".ljust(width) + "".join(str(c).rjust(9) for c in cols) + "     total"
        print(header)
        print("-" * len(header))
        for r in rows:
            line = r.ljust(width)
            total = 0
            for c in cols:
                v = table[r].get(c, 0)
                total += v
                line += (str(v) if v else "-").rjust(9)
            print(line + str(total).rjust(10))
        line = "total".ljust(width)
        grand = 0
        for c in cols:
            s = sum(table[r].get(c, 0) for r in rows)
            grand += s
            line += str(s).rjust(9)
        print("-" * len(header))
        print(line + str(grand).rjust(10))

    with open(filename, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["highway"] + [str(c) for c in cols] + ["total"])
        for r in rows:
            values = [table[r].get(c, 0) for c in cols]
            w.writerow([r] + values + [sum(values)])
    print("saved:", filename)


def crosstabs(rows, name, show=True):
    speed = defaultdict(Counter)
    capacity = defaultdict(Counter)
    lanes = defaultdict(Counter)
    lanes_src = defaultdict(Counter)
    speed_src = defaultdict(Counter)
    area = defaultdict(Counter)

    for r in rows:
        hw = r["highway"]
        speed[hw][int(round(r["speed"] * 3.6))] += 1
        capacity[hw][int(round(r["capacity"]))] += 1
        lanes[hw][int(r["lanes"])] += 1
        lanes_src[hw][r["lanes_source"]] += 1
        speed_src[hw][r["speed_source"]] += 1
        area[hw][r["area"]] += 1

    def columns(table):
        return sorted({k for h in table for k in table[h]})

    _crosstab("speed (km/h) x road hierarchy", speed, columns(speed),
             "%s_crosstab_speed.csv" % name, show)
    _crosstab("capacity (veh/h) x road hierarchy", capacity, columns(capacity),
             "%s_crosstab_capacity.csv" % name, show)
    _crosstab("permlanes x road hierarchy", lanes, columns(lanes),
             "%s_crosstab_lanes.csv" % name, show)
    _crosstab("lanes: osm tag or default value", lanes_src, ["osm", "default"],
             "%s_crosstab_lanes_source.csv" % name, show)
    _crosstab("speed: osm tag or default value", speed_src, ["osm", "default"],
             "%s_crosstab_speed_source.csv" % name, show)
    if any("model" in area[h] for h in area):
        _crosstab("study area x model area", area, ["study", "model"],
                 "%s_crosstab_area.csv" % name, show)


def write_matsim(G, rows, path):
    ids = {n: str(i + 1) for i, n in enumerate(G.nodes)}
    opener = gzip.open if str(path).lower().endswith(".gz") else open
    with opener(path, "wt", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<!DOCTYPE network SYSTEM '
                '"http://www.matsim.org/files/dtd/network_v2.dtd">\n')
        f.write('<network>\n\t<nodes>\n')
        for n, data in G.nodes(data=True):
            f.write('\t\t<node id="%s" x="%.2f" y="%.2f" />\n'
                    % (ids[n], data["x"], data["y"]))
        f.write('\t</nodes>\n\t<links capperiod="01:00:00">\n')
        for i, r in enumerate(rows, start=1):
            f.write('\t\t<link id="%d" from="%s" to="%s" length="%.2f" '
                    'freespeed="%.4f" capacity="%.1f" permlanes="%.1f" '
                    'modes="car">\n'
                    % (i, ids[r["u"]], ids[r["v"]], r["length"], r["speed"],
                       r["capacity"], r["lanes"]))
            f.write('\t\t\t<attributes>\n')
            for key, value in (("osm:way:highway", r["highway"]),
                               ("area", r["area"]),
                               ("lanes_source", r["lanes_source"]),
                               ("speed_source", r["speed_source"])):
                f.write('\t\t\t\t<attribute name="%s" '
                        'class="java.lang.String">%s</attribute>\n'
                        % (key, value))
            f.write('\t\t\t</attributes>\n\t\t</link>\n')
        f.write('\t</links>\n</network>\n')
    print("saved:", path)


def write_gpkg(G, path):
    nodes, edges = ox.graph_to_gdfs(G)
    edges = edges.copy()
    for column in edges.columns:
        if column == "geometry":
            continue
        edges[column] = edges[column].map(
            lambda v: ";".join(map(str, v)) if isinstance(v, list) else v)
    edges.to_file(path, layer="links", driver="GPKG")
    nodes[["geometry"]].to_file(path, layer="nodes", driver="GPKG")
    print("saved:", path)


def save_network(G, output_path, name="road_network"):
    """Save a network as MATSim XML and separate link/node GeoPackages.

    A sanitized folder named after ``name`` is created inside ``output_path``.
    The returned dictionary contains the folder and all three output paths.
    """
    folder_name = re.sub(r"[^A-Za-z0-9._-]+", "_", str(name)).strip("._")
    if not folder_name:
        folder_name = "road_network"

    output_folder = Path(output_path) / folder_name
    output_folder.mkdir(parents=True, exist_ok=True)

    matsim_path = output_folder / "network.xml"
    links_path = output_folder / "links.gpkg"
    nodes_path = output_folder / "nodes.gpkg"

    rows = link_rows(G)
    write_matsim(G, rows, matsim_path)

    nodes, links = ox.graph_to_gdfs(G)
    for frame in (nodes, links):
        for column in frame.columns:
            if column != "geometry":
                frame[column] = frame[column].map(
                    lambda value: ";".join(map(str, value))
                    if isinstance(value, list) else value
                )

    links.to_file(links_path, layer="links", driver="GPKG")
    nodes.to_file(nodes_path, layer="nodes", driver="GPKG")
    print("saved:", links_path)
    print("saved:", nodes_path)

    return {
        "folder": output_folder,
        "matsim": matsim_path,
        "links": links_path,
        "nodes": nodes_path,
    }


def process(G, name, label, show_tables):
    rows = link_rows(G)
    _stats(rows, G.number_of_nodes(), label)
    write_matsim(G, rows, "%s_network.xml.gz" % name)
    write_gpkg(G, "%s_network.gpkg" % name)
    crosstabs(rows, name, show_tables)
