"""How many people, and how much land, stand opposite land: the figures behind the reel Dig Straight Down.

Run (about 6 GB of memory, a minute or two):
  uv run -q --no-project --with numpy --with rasterio --with shapely --with pyshp python tools/maps/antipodes.py DATA

DATA defaults to $SRSTUDIO_MAPS_DATA, else generated/data/maps, and holds the population grids and Natural Earth 1:10m
land and countries, as tools/maps/circle.py expects them. No file is fetched. Land is Natural Earth's polygons burned
into a cell-centred grid at each population grid's own resolution; a cell of people stands opposite land when the cell
at its antipode is land. Lakes count as land, which favours land and leaves the sea's share a slight understatement.
"""

import csv
import io
import os
import pathlib
import sys
import tempfile
import zipfile

DATA = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SRSTUDIO_MAPS_DATA", "generated/data/maps"))
GRIDS = ("GHS_POP_E2025_GLOBE_R2023A_4326_30ss_V1_0.tif", "global_pop_2025_CN_1km_R2025A_UA_v1.tif")
CITIES = (
    ("New York City", "US"), ("Beijing", "CN"), ("Shanghai", "CN"), ("Madrid", "ES"), ("Auckland", "NZ"),
    ("London", "GB"), ("Delhi", "IN"), ("Lagos", "NG"),
)  # fmt: skip


def antipode(lat: float, lon: float) -> tuple[float, float]:
    """The point on the far side of a sphere."""
    return -lat, lon - 180.0 if lon > 0 else lon + 180.0


def unpack(name: str, into: str):
    import shapefile

    zipfile.ZipFile(DATA / f"{name}.zip").extractall(into)
    return shapefile.Reader(f"{into}/{name}.shp", encoding="utf8")


def shares(tif: str, land: list[dict]) -> None:
    import numpy as np
    import rasterio
    from rasterio import features
    from rasterio.transform import from_origin

    grid = rasterio.open(DATA / tif)
    people = grid.read(1).astype("float64")
    people[~np.isfinite(people) | (people < 0)] = 0.0
    t = grid.transform
    lats = t.f + t.e * (np.arange(people.shape[0]) + 0.5)
    lons = t.c + t.a * (np.arange(people.shape[1]) + 0.5)
    rows, cols = round(180 / abs(t.e)), round(360 / t.a)
    dy, dx = 180 / rows, 360 / cols
    mask = features.rasterize(
        ((g, 1) for g in land), out_shape=(rows, cols), transform=from_origin(-180, 90, dx, dy), fill=0, dtype="uint8"
    ).astype(bool)
    weight = np.cos(np.radians(90 - (np.arange(rows) + 0.5) * dy))[:, None]
    far = np.roll(mask[::-1, :], cols // 2, axis=1)
    land_area = float((mask * weight).sum())
    both = float(((mask & far) * weight).sum())
    print(
        f"land {land_area / (weight.sum() * cols):.4%} of the Earth; land opposite land {both / land_area:.2%} of land"
    )
    at_row = np.clip(((90 + lats) / dy).astype(int), 0, rows - 1)
    at_col = (((lons + 360) % 360) / dx).astype(int) % cols
    opposite = mask[np.ix_(at_row, at_col)]
    total, on_land = people.sum(), people[opposite].sum()
    print(
        f"{tif}: {total:,.0f} people; opposite land {on_land:,.0f} = {on_land / total:.2%}; "
        f"sea {1 - on_land / total:.2%}"
    )


def cities(countries) -> None:
    from shapely.geometry import Point, shape
    from shapely.strtree import STRtree

    names = [r["ADMIN"] for r in countries.records()]
    shapes = [shape(s.__geo_interface__).buffer(0) for s in countries.shapes()]
    tree = STRtree(shapes)
    rows: dict[tuple[str, str], tuple[int, str, float, float]] = {}
    with zipfile.ZipFile(DATA / "cities15000.zip").open("cities15000.txt") as f:
        for line in io.TextIOWrapper(f, "utf8"):
            cell = next(csv.reader([line], delimiter="\t", quoting=csv.QUOTE_NONE))
            key = (cell[1], cell[8])
            if key in CITIES and int(cell[14]) > rows.get(key, (0,))[0]:
                rows[key] = (int(cell[14]), cell[0], float(cell[4]), float(cell[5]))
    for key in CITIES:
        _, geonameid, lat, lon = rows[key]
        far = antipode(lat, lon)
        p = Point(far[1], far[0])
        hit = [names[i] for i in tree.query(p) if shapes[i].contains(p)]
        near = tree.nearest(p)
        where = hit[0] if hit else f"sea, {shapes[near].distance(p):.1f} deg from {names[near]}"
        print(f"{key[0]} GeoNames {geonameid} {lat:.5f},{lon:.5f} -> {far[0]:.3f},{far[1]:.3f}: {where}")


def main() -> None:
    with tempfile.TemporaryDirectory() as folder:
        land = [s.__geo_interface__ for s in unpack("ne_10m_land", folder).shapes()]
        for tif in GRIDS:
            shares(tif, land)
        cities(unpack("ne_10m_admin_0_countries", folder))


if __name__ == "__main__":
    main()
