"""Build the map kit's layers under src/srstudio/assets/maps/ from Natural Earth and GHS-POP.

Run (about 4 GB of memory, a minute or two):
  uv run -q --no-project --with numpy --with rasterio --with shapely python tools/maps/build_layers.py DATA

DATA defaults to $SRSTUDIO_MAPS_DATA, else generated/data/maps. It holds the population grid, which is not in git, and
ne-5.1.2/, filled from the pinned tag of nvkelso/natural-earth-vector on the first run. The output is deterministic, and
layers.json records what each layer came from, with the SHA-256 of its input.

land and borders are Natural Earth 1:50m with their coordinates rounded to :data:`PLACES` decimals and their properties
dropped. Boundaries are kept as Natural Earth draws them; nothing is added or moved, and the only points removed are the
ones that run Antarctica's outline along the South Pole (see :func:`thin`). The large lakes are cut out of the land as
holes (see :func:`cut_lakes`): as a layer of their own they would be empty in any frame that holds none, an ocean for
instance, which the strict encode reports.

dots is the population as one dot per :data:`DOT` people. Every cell of the 30 arc-second grid is put in one of three
zones, by the rule of circle.py: its centre is within :data:`RADIUS` km of :data:`MONG_KHET`, of :data:`ADELAIDE`, or of
neither. The cells of a zone are summed to 0.1 degrees and walked along a Hilbert curve, and a dot falls where the
running total passes each half-million above a multiple of a million. So a zone holds exactly its total in dots, rounded
to the nearest million, and a dot stands for people near it.
"""

import hashlib
import json
import math
import os
import pathlib
import sys
import urllib.request

import numpy as np
import rasterio
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "src/srstudio/assets/maps"
DATA = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SRSTUDIO_MAPS_DATA", "generated/data/maps"))
NE_TAG = "v5.1.2"
NE_COMMIT = "f1890d9f152c896d250a77557a5751a93d494776"
NE_URL = f"https://raw.githubusercontent.com/nvkelso/natural-earth-vector/{NE_COMMIT}/geojson/"
NE_FILES = {
    "land": "ne_50m_land.geojson",
    "lakes": "ne_50m_lakes.geojson",
    "borders": "ne_50m_admin_0_boundary_lines_land.geojson",
}
LAKE_RANK = 3  # Natural Earth's scalerank: the lakes that read at the scale of a phone
GRID = "GHS_POP_E2025_GLOBE_R2023A_4326_30ss_V1_0.tif"
PLACES = 2
DOT = 1_000_000
RADIUS = 3300.0
R = 6371.0088  # as circle.py: IUGG mean radius
MONG_KHET = (21.70282, 99.34224)  # GeoNames 11154258
ADELAIDE = (-34.92866, 138.59863)  # GeoNames 2078025
CELL = 12  # 30 arc-second cells to a 0.1 degree cell
BATCHES = 6  # a zone's dots appear in this many waves
SEED = 2025


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def natural_earth(name: str) -> pathlib.Path:
    path = DATA / "ne-5.1.2" / NE_FILES[name]
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(NE_URL + NE_FILES[name], timeout=60) as reply:  # the pinned commit
            path.write_bytes(reply.read())
    return path


def rounded(value):
    if isinstance(value, float | int):
        return round(float(value), PLACES)
    return [rounded(v) for v in value]


def thin(coordinates):
    """Drop a point that rounds onto the one before it; the rings stay closed. Natural Earth closes Antarctica along the
    line of latitude -90, an edge a globe would draw as a line across the ice to the pole: the ring is left to close
    around the pole, its only change."""
    if coordinates and isinstance(coordinates[0][0], float):
        kept = [coordinates[0]]
        for point in coordinates[1:]:
            if point != kept[-1] and point[1] > -90.0:
                kept.append(point)
        return kept
    return [thin(part) for part in coordinates]


def cut_lakes(features: list) -> None:
    """Cut the large lakes out of the land, before any rounding: Natural Earth's polygons are valid as they stand, and
    a lake such as Malaren reaches the coast, so it cannot simply be added to its polygon as an inner ring."""
    lakes = natural_earth("lakes")
    water = unary_union(
        [
            shape(feature["geometry"])
            for feature in json.loads(lakes.read_text())["features"]
            if feature["properties"].get("scalerank", 99) <= LAKE_RANK
        ]
    )
    for feature in features:
        land = shape(feature["geometry"])
        if land.intersects(water):
            feature["geometry"] = mapping(land.difference(water))


def write(name: str, features: list, sources: dict) -> None:
    path = OUT / f"{name}.geojson"
    text = json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":"))
    path.write_text(text + "\n")
    sources[name]["sha256"] = sha256(path)
    sources[name]["bytes"] = path.stat().st_size


def natural_earth_layer(name: str, sources: dict) -> None:
    path = natural_earth(name)
    features = []
    raw = json.loads(path.read_text())["features"]
    if name == "land":
        cut_lakes(raw)
    for feature in raw:
        geometry = feature["geometry"]
        coordinates = thin(rounded(geometry["coordinates"]))
        features.append(
            {"type": "Feature", "properties": {}, "geometry": {"type": geometry["type"], "coordinates": coordinates}}
        )
    sources[name] = {
        "source": f"Natural Earth 1:50m {NE_FILES[name]}, nvkelso/natural-earth-vector {NE_TAG} ({NE_COMMIT})",
        "input_sha256": sha256(path),
        "licence": "public domain",
    }
    if name == "land":
        sources[name]["source"] += f", with the lakes of {NE_FILES['lakes']} to scalerank {LAKE_RANK} cut out as holes"
        sources[name]["lakes_sha256"] = sha256(natural_earth("lakes"))
    write(name, features, sources)


def within(lats: np.ndarray, lons: np.ndarray, lat0: float, lon0: float) -> np.ndarray:
    """One row's cells whose centres lie within :data:`RADIUS` km of the centre, as circle.py sums them."""
    p0, p, dl = math.radians(lat0), np.radians(lats), np.radians(lons - lon0)
    cosine = math.sin(p0) * np.sin(p) + math.cos(p0) * np.cos(p) * np.cos(dl)
    return cosine >= math.cos(RADIUS / R)


def hilbert(x: np.ndarray, y: np.ndarray, order: int) -> np.ndarray:
    """The distance along a Hilbert curve of side ``2 ** order`` of each cell."""
    x, y, d = x.astype(np.int64).copy(), y.astype(np.int64).copy(), np.zeros_like(x, dtype=np.int64)
    s = 1 << (order - 1)
    while s:
        rx, ry = (x & s) > 0, (y & s) > 0
        d += s * s * ((3 * rx.astype(np.int64)) ^ ry.astype(np.int64))
        flip = ~ry
        swap = rx & flip
        x[swap], y[swap] = s - 1 - (x[swap] & (s - 1)), s - 1 - (y[swap] & (s - 1))
        x[flip], y[flip] = y[flip].copy(), x[flip].copy()
        x, y = x & (s - 1), y & (s - 1)
        s >>= 1
    return d


def read_zones() -> tuple[dict, float, float]:
    """Per zone, the people in each 0.1 degree cell, and the origin of that grid."""
    with rasterio.open(DATA / GRID) as source:
        a = source.read(1).astype(np.float64)
        t = source.transform
    a[~np.isfinite(a) | (a < 0)] = 0.0
    rows, cols = a.shape
    lats = t.f + t.e * (np.arange(rows) + 0.5)
    lons = t.c + t.a * (np.arange(cols) + 0.5)
    shape = (rows // CELL + 1, cols // CELL + 1)
    zones = {name: np.zeros(shape) for name in ("inside", "adelaide", "rest")}
    for row in range(rows):
        values = a[row]
        if not values.any():
            continue
        lat = np.full(cols, lats[row])
        inside = within(lat, lons, *MONG_KHET)
        adelaide = within(lat, lons, *ADELAIDE)
        rest = ~(inside | adelaide)
        for name, mask in (("inside", inside), ("adelaide", adelaide), ("rest", rest)):
            zones[name][row // CELL] += np.bincount(
                np.nonzero(mask)[0] // CELL, weights=values[mask], minlength=shape[1]
            )
    return zones, float(t.f), float(t.c)


def dots(zone: np.ndarray, north: float, west: float, rng: np.random.Generator) -> list[list[float]]:
    row, col = np.nonzero(zone)
    order = np.argsort(hilbert(col, row, 12), kind="stable")
    row, col, people = row[order], col[order], zone[row[order], col[order]]
    running = np.cumsum(people)
    count = int(math.floor(running[-1] / DOT + 0.5))
    marks = (np.arange(count) + 0.5) * DOT
    cells = np.searchsorted(running, marks)
    size = CELL * 30 / 3600
    lons = west + (col[cells] + rng.random(count)) * size
    lats = north - (row[cells] + rng.random(count)) * size
    return [[round(float(lon), PLACES), round(float(lat), PLACES)] for lon, lat in zip(lons, lats, strict=True)]


def population_layer(sources: dict) -> None:
    zones, north, west = read_zones()
    rng = np.random.default_rng(SEED)
    features, counts, people = [], {}, {}
    for name in ("inside", "adelaide", "rest"):
        points = dots(zones[name], north, west, rng)
        counts[name] = len(points)
        people[name] = round(float(zones[name].sum()))
        order = rng.permutation(len(points))
        points = [points[i] for i in order]
        groups = [[p] for p in points] if name == "adelaide" else [points[i::BATCHES] for i in range(BATCHES)]
        for i, group in enumerate(groups):
            features.append(
                {
                    "type": "Feature",
                    "id": f"{name}-{i}",
                    "properties": {"k": f"{name}-{i}", "zone": name},
                    "geometry": {"type": "MultiPoint", "coordinates": group},
                }
            )
    sources["dots"] = {
        "source": "GHS-POP R2023A, epoch 2025, 30 arc-seconds (GHS_POP_E2025_GLOBE_R2023A_4326_30ss_V1_0)",
        "input_sha256": sha256(DATA / GRID),
        "licence": "CC BY 4.0, European Commission JRC: summed inside circles, drawn as dots, recoloured",
        "people_per_dot": DOT,
        "radius_km": RADIUS,
        "centres": {"inside": MONG_KHET, "adelaide": ADELAIDE},
        "dots": counts,
        "people": people,
        "seed": SEED,
    }
    write("dots", features, sources)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sources: dict = {}
    for name in ("land", "borders"):
        natural_earth_layer(name, sources)
    population_layer(sources)
    manifest = {"schema_version": "1.0.0", "generated-by": "tools/maps/build_layers.py", "layers": sources}
    (OUT / "layers.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    for name, layer in sources.items():
        print(name, layer["bytes"], layer.get("dots", ""), layer.get("people", ""))


if __name__ == "__main__":
    main()
