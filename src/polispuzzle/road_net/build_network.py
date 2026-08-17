import csv
import gzip
import sys
from collections import Counter, defaultdict

import osmnx as ox

# This should be added in yaml confing file
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

# what about capacity

HIERARCHY = ["motorway", "motorway_link", "trunk", "trunk_link",
             "primary", "primary_link", "secondary", "secondary_link",
             "tertiary", "tertiary_link", "unclassified",
             "residential", "living_street"]

LEVELS = {
    1: ("full", set(HIGHWAY)),
    2: ("medium", {"motorway", "motorway_link", "trunk", "trunk_link",
                   "primary", "primary_link", "secondary", "secondary_link",
                   "tertiary", "tertiary_link"}),
    3: ("arterial", {"motorway", "motorway_link", "trunk", "trunk_link",
                     "primary", "primary_link", "secondary", "secondary_link"}),
}


def first(value):
    if isinstance(value, (list, tuple)):
        return value[0] if value else None
    return value


def to_int(value):
    value = first(value)
    if value is None:
        return None
    try:
        n = int(float(str(value).split(";")[0]))
        return n if n > 0 else None
    except (ValueError, TypeError):
        return None


def to_ms(value):
    value = first(value)
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


def road_type(data):
    hw = first(data.get("highway"))
    return hw if hw in HIGHWAY else None


def download(place):
    print("downloading:", place)
    G = ox.graph_from_place(place, network_type="drive")
    return ox.project_graph(G, to_crs=CRS_OUT)


def filter_types(G, allowed):
    H = G.copy()
    H.remove_edges_from([(u, v, k) for u, v, k, d in H.edges(keys=True, data=True)
                         if road_type(d) not in allowed])
    H.remove_nodes_from([n for n in list(H.nodes) if H.degree(n) == 0])
    return H


def connected(G):
    return ox.truncate.largest_component(G, strongly=True)


def link_rows(G):
    rows = []
    for u, v, d in G.edges(data=True):
        hw = road_type(d)
        if hw is None:
            continue
        lanes_def, speed_def, cap_lane = HIGHWAY[hw]

        speed = to_ms(d.get("maxspeed"))
        speed_source = "osm" if speed else "default"
        if not speed:
            speed = speed_def

        raw_lanes = to_int(d.get("lanes"))
        lanes_source = "osm" if raw_lanes else "default"
        lanes = raw_lanes or lanes_def
        if raw_lanes and not d.get("oneway", False):
            lanes = max(1, round(lanes / 2))

        rows.append({
            "u": u, "v": v,
            "highway": hw,
            "length": max(1.0, float(d.get("length", 1.0))),
            "speed": speed,
            "lanes": float(lanes),
            "capacity": cap_lane * lanes,
            "lanes_source": lanes_source,
            "speed_source": speed_source,
        })
    return rows


def stats(rows, nodes, label):
    counts = Counter()
    lengths = Counter()
    lanes_src = Counter()
    speed_src = Counter()

    for r in rows:
        counts[r["highway"]] += 1
        lengths[r["highway"]] += r["length"]
        lanes_src[r["lanes_source"]] += 1
        speed_src[r["speed_source"]] += 1

    print()
    print("=" * 62)
    print("network: %s" % label)
    print("=" * 62)
    print("nodes: %d | links: %d | length: %.1f km"
          % (nodes, len(rows), sum(lengths.values()) / 1000.0))
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


def crosstab(title, table, cols, filename, show=True):
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

    for r in rows:
        hw = r["highway"]
        speed[hw][int(round(r["speed"] * 3.6))] += 1
        capacity[hw][int(round(r["capacity"]))] += 1
        lanes[hw][int(r["lanes"])] += 1
        lanes_src[hw][r["lanes_source"]] += 1
        speed_src[hw][r["speed_source"]] += 1

    def columns(table):
        return sorted({k for h in table for k in table[h]})

    crosstab("speed (km/h) x road hierarchy", speed, columns(speed),
             "%s_crosstab_speed.csv" % name, show)
    crosstab("capacity (veh/h) x road hierarchy", capacity, columns(capacity),
             "%s_crosstab_capacity.csv" % name, show)
    crosstab("permlanes x road hierarchy", lanes, columns(lanes),
             "%s_crosstab_lanes.csv" % name, show)
    crosstab("lanes: osm tag or default value", lanes_src, ["osm", "default"],
             "%s_crosstab_lanes_source.csv" % name, show)
    crosstab("speed: osm tag or default value", speed_src, ["osm", "default"],
             "%s_crosstab_speed_source.csv" % name, show)

# Is it working in MATSim? Watch out!
def write_matsim(G, rows, path):
    ids = {n: str(i + 1) for i, n in enumerate(G.nodes)}
    with gzip.open(path, "wt", encoding="utf-8") as f:
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


def process(G, name, label, show_tables):
    rows = link_rows(G)
    stats(rows, G.number_of_nodes(), label)
    write_matsim(G, rows, "%s_network.xml.gz" % name)
    write_gpkg(G, "%s_network.gpkg" % name)
    crosstabs(rows, name, show_tables)


def ask(prompt, options):
    while True:
        answer = input(prompt).strip().lower()
        if answer in options:
            return answer
        print("options:", "/".join(options))

# This can be the example, download
def main():
    place = " ".join(sys.argv[1:]).strip()
    if not place:
        place = input("area (e.g. Kalamaria, Greece): ").strip() # No option to provide a polygon
    if not place:
        print("no area given")
        return

    show_tables = ask("print cross-tables on screen? (y/n): ", ("y", "n")) == "y"

    G = connected(download(place))
    base = place.split(",")[0].strip().lower().replace(" ", "_")
    process(G, base, "full", show_tables)

    if ask("\nsimplified version? (y/n): ", ("y", "n")) == "n":
        return

    print("\n  1  full        all drivable roads")
    print("  2  medium      without residential and local streets")
    print("  3  arterial    motorway, trunk, primary, secondary only")

    while True:
        choice = ask("level (1/2/3): ", ("1", "2", "3"))
        label, allowed = LEVELS[int(choice)]
        H = connected(filter_types(G, allowed))
        process(H, "%s_%s" % (base, label), label, show_tables)

        if ask("\nanother level? (y/n): ", ("y", "n")) == "n":
            return


if __name__ == "__main__":
    main()
