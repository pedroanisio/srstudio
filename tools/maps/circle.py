"""Population inside a great-circle radius: recompute of the Valeriepieris claim.

Run (about 10 GB RAM per grid, a few minutes):
  uv run -q --no-project --with numpy --with rasterio --with geopandas --with pyproj \
      python tools/maps/circle.py DATA

Inputs, all under DATA (the argument, else $SRSTUDIO_MAPS_DATA, else generated/data/maps; no login needed):
  GHS_POP_E2025_GLOBE_R2023A_4326_30ss_V1_0.tif   GHS-POP R2023A, epoch 2025, 30 arcsec
  GHS_POP_E2015_GLOBE_R2023A_4326_30ss_V1_0.tif   GHS-POP R2023A, epoch 2015, 30 arcsec
  global_pop_2025_CN_1km_R2025A_UA_v1.tif         WorldPop R2025A, 2025, constrained, UN-adjusted, 30 arcsec
  cities15000.zip, MM.zip                         GeoNames
  ne/ne_10m_land.shp, ne/ne_10m_admin_0_countries.shp   Natural Earth

Method: a cell counts as inside when its centre is within the great-circle
distance (sphere, R = 6371.0088 km, IUGG mean radius). The fast routine uses
per-row prefix sums. It is checked against a brute-force haversine over every
cell, and the sphere is checked against WGS84 geodesics on a 0.1 degree grid.
"""

import math
import os
import pathlib
import sys
import zipfile

import geopandas as gpd
import numpy as np
import pyproj
import rasterio
from rasterio import features
from rasterio.transform import from_origin

DATA = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SRSTUDIO_MAPS_DATA", "generated/data/maps"))
R = 6371.0088
RADIUS = 3300.0
MONG_KHET = (21.70282, 99.34224)  # GeoNames 11154258 Mongkhet, ADM3 township point
GRIDS = {
    "GHS-POP R2023A E2025 30ss": "GHS_POP_E2025_GLOBE_R2023A_4326_30ss_V1_0.tif",
    "GHS-POP R2023A E2015 30ss": "GHS_POP_E2015_GLOBE_R2023A_4326_30ss_V1_0.tif",
    "WorldPop R2025A 2025 constrained UN-adj 30ss": "global_pop_2025_CN_1km_R2025A_UA_v1.tif",
}


class Grid:
    def __init__(self, path):
        with rasterio.open(path) as d:
            a = d.read(1).astype(np.float64)
            t = d.transform
        a[~np.isfinite(a) | (a < 0)] = 0.0
        self.rows, self.cols = a.shape
        self.dlon, self.dlat = t.a, -t.e
        self.lon0 = t.c + self.dlon / 2
        self.lat = t.f - self.dlat * (np.arange(self.rows) + 0.5)
        self.lon = self.lon0 + self.dlon * np.arange(self.cols)
        self.a = a
        self.finish()

    def finish(self):
        self.cum = np.zeros((self.rows, self.cols + 1))
        self.cum[:, 1:] = np.cumsum(self.a, axis=1)
        self.rowtot = self.cum[:, -1]
        self.sin = np.sin(np.radians(self.lat))
        self.cos = np.cos(np.radians(self.lat))
        self.total = float(self.rowtot.sum())
        top = np.radians(self.lat + self.dlat / 2)
        bot = np.radians(self.lat - self.dlat / 2)
        self.cell_area = R * R * math.radians(self.dlon) * (np.sin(top) - np.sin(bot))

    def inside(self, lat0, lon0, r=RADIUS):
        """Fast sum, cell-centre rule."""
        c = r / R
        s0, c0 = math.sin(math.radians(lat0)), math.cos(math.radians(lat0))
        x = (math.cos(c) - self.sin * s0) / (self.cos * c0)
        full = x <= -1
        part = (x > -1) & (x < 1)
        total = self.rowtot[full].sum()
        rows = np.nonzero(part)[0]
        d = np.degrees(np.arccos(x[rows]))
        for k in (-360.0, 0.0, 360.0):
            lo = np.ceil((lon0 + k - d - self.lon0) / self.dlon).astype(np.int64)
            hi = np.floor((lon0 + k + d - self.lon0) / self.dlon).astype(np.int64)
            lo = np.clip(lo, 0, self.cols)
            hi = np.clip(hi + 1, 0, self.cols)
            ok = hi > lo
            total += (self.cum[rows[ok], hi[ok]] - self.cum[rows[ok], lo[ok]]).sum()
        return float(total)

    def brute(self, lat0, lon0, r=RADIUS):
        """Haversine distance to every cell in every row; also returns the area."""
        p0 = math.radians(lat0)
        lam = np.radians(self.lon - lon0)
        sl2 = np.sin(lam / 2) ** 2
        pop = area = 0.0
        for i in range(self.rows):
            p = math.radians(self.lat[i])
            h = math.sin((p - p0) / 2) ** 2 + math.cos(p) * math.cos(p0) * sl2
            m = 2 * R * np.arcsin(np.sqrt(h)) <= r
            pop += self.a[i, m].sum()
            area += self.cell_area[i] * m.sum()
        return float(pop), float(area)


def coarsen(g, step=0.1):
    """Sum a grid onto a regular global grid of the given step, as a Grid."""
    n_lon, n_lat = int(round(360 / step)), int(round(180 / step))
    ci = np.clip(np.floor((g.lon + 180) / step).astype(int), 0, n_lon - 1)
    ri = np.clip(np.floor((90 - g.lat) / step).astype(int), 0, n_lat - 1)
    out = np.zeros((n_lat, n_lon))
    cedges = np.nonzero(np.r_[True, ci[1:] != ci[:-1]])[0]
    tmp = np.add.reduceat(g.a, cedges, axis=1)
    cc = ci[cedges]
    for i in range(g.rows):
        out[ri[i], cc] += tmp[i]
    c = Grid.__new__(Grid)
    c.a, c.rows, c.cols, c.dlon, c.dlat = out, n_lat, n_lon, step, step
    c.lon0 = -180 + step / 2
    c.lat = 90 - step * (np.arange(n_lat) + 0.5)
    c.lon = c.lon0 + step * np.arange(n_lon)
    c.finish()
    return c


def wrap(lon):
    return (lon + 180) % 360 - 180


def climb(g, start, r=RADIUS, steps=(1.0, 0.25, 0.05, 0.01), sign=1):
    lat, lon = start
    best = g.inside(lat, lon, r)
    for s in steps:
        moved = True
        while moved:
            moved = False
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                la, lo = lat + dy * s, wrap(lon + dx * s)
                if abs(la) > 85:
                    continue
                v = g.inside(la, lo, r)
                if sign * v > sign * best:
                    best, lat, lon, moved = v, la, lo, True
    return lat, lon, best


def best_circle(g, coarse, r=RADIUS, step=2.0):
    """Global scan on the coarse grid, then climb from the top starts on the full grid."""
    res = [(coarse.inside(la, lo, r), la, lo) for la in np.arange(-80, 80.1, step) for lo in np.arange(-180, 180, step)]
    res.sort(reverse=True)
    starts, kept = [], []
    for _v, la, lo in res:
        if all(abs(la - a) + abs(wrap(lo - b)) > 12 for a, b in kept):
            kept.append((la, lo))
            starts.append((la, lo))
        if len(starts) == 3:
            break
    out = [climb(g, (la, lo), r) for la, lo in starts]
    return max(out, key=lambda t: t[2])


def smallest_half(g, start):
    """Smallest radius whose best-placed circle reaches half the grid total."""
    lo, hi = 2500.0, 4500.0
    centre = start
    while hi - lo > 1.0:
        mid = (lo + hi) / 2
        la, ln, v = climb(g, centre, mid, steps=(0.25, 0.05, 0.01))
        if v >= g.total / 2:
            hi, centre = mid, (la, ln)
        else:
            lo = mid
    return hi, centre


def half_radius_at(g, lat, lon):
    lo, hi = 1000.0, 9000.0
    while hi - lo > 0.5:
        mid = (lo + hi) / 2
        if g.inside(lat, lon, mid) >= g.total / 2:
            hi = mid
        else:
            lo = mid
    return hi


def nearest(places, lat, lon):
    la = np.radians(places["lat"])
    dl = np.radians(places["lon"] - lon)
    p0 = math.radians(lat)
    h = np.sin((la - p0) / 2) ** 2 + np.cos(la) * np.cos(p0) * np.sin(dl / 2) ** 2
    i = int(np.argmin(h))
    km = 2 * R * math.asin(math.sqrt(h[i]))
    return f"{places['name'][i]} ({places['cc'][i]}, {places['lat'][i]:.3f}, {places['lon'][i]:.3f}), {km:.0f} km away"


def load_places():
    rows = []
    with zipfile.ZipFile(DATA / "cities15000.zip") as z:
        for line in z.read("cities15000.txt").decode().splitlines():
            f = line.split("\t")
            rows.append((f[1], float(f[4]), float(f[5]), f[8]))
    return {
        "name": [r[0] for r in rows],
        "lat": np.array([r[1] for r in rows]),
        "lon": np.array([r[2] for r in rows]),
        "cc": [r[3] for r in rows],
    }


def fmt(x):
    return f"{x:,.0f}"


def report(name, g, lat, lon, r=RADIUS):
    v = g.inside(lat, lon, r)
    print(
        f"  {name}: centre {lat:.3f}, {lon:.3f}, r {r:.0f} km: inside {fmt(v)} = {100 * v / g.total:.2f}% ; "
        f"outside {fmt(g.total - v)}"
    )
    return v


def main():
    places = load_places()
    land = gpd.read_file(DATA / "ne/ne_10m_land.shp")
    admin = gpd.read_file(DATA / "ne/ne_10m_admin_0_countries.shp")
    print("Natural Earth version:", (DATA / "ne/ne_10m_admin_0_countries.VERSION.txt").read_text().strip())
    tf = from_origin(-180, 90, 0.1, 0.1)
    land_mask = features.rasterize(land.geometry, out_shape=(1800, 3600), transform=tf, fill=0, default_value=1)
    admin = admin.reset_index(drop=True)
    admin_ids = features.rasterize(
        ((geom, i + 1) for i, geom in enumerate(admin.geometry)),
        out_shape=(1800, 3600),
        transform=tf,
        fill=0,
        dtype="int32",
    )
    names = {i + 1: n for i, n in enumerate(admin["ADMIN"])}
    centres = {}
    for country, col in (("Canada", "ADMIN"), ("Australia", "ADMIN")):
        poly = admin[admin[col] == country].to_crs("EPSG:6933")
        c = poly.geometry.iloc[0].centroid
        lon, lat = pyproj.Transformer.from_crs("EPSG:6933", "EPSG:4326", always_xy=True).transform(c.x, c.y)
        centres[country] = (lat, lon)
        print(
            f"{country} area-weighted centroid (Natural Earth admin-0, EPSG:6933): {lat:.3f}, {lon:.3f}; "
            f"nearest GeoNames city: {nearest(places, lat, lon)}"
        )
    alice = (places["lat"][places["name"].index("Alice Springs")], places["lon"][places["name"].index("Alice Springs")])
    print(f"Alice Springs (GeoNames cities15000): {alice[0]:.5f}, {alice[1]:.5f}")

    for label, fn in GRIDS.items():
        print("\n" + "=" * 78 + f"\n{label}\n" + "=" * 78)
        g = Grid(DATA / fn)
        print(f"grid {g.cols} x {g.rows}, cell {g.dlon:.10f} deg, world total {fmt(g.total)}")
        coarse = coarsen(g)
        print(f"coarse 0.1 deg grid total {fmt(coarse.total)}")

        print("Mong Khet circle:")
        v = report("fast", g, *MONG_KHET)
        pop, area = g.brute(*MONG_KHET)
        cap = 2 * math.pi * R * R * (1 - math.cos(RADIUS / R))
        print(
            f"  brute-force haversine: inside {fmt(pop)} = {100 * pop / g.total:.2f}%; "
            f"difference from fast {pop - v:,.0f}"
        )
        print(
            f"  circle area from cells {fmt(area)} km2; spherical cap {fmt(cap)} km2; "
            f"share of Earth surface {100 * cap / (4 * math.pi * R * R):.2f}%"
        )
        for r in (3200, 3250, 3280, 3320, 3350, 3400, 3500):
            report(f"radius {r}", g, *MONG_KHET, r)
        print(f"  radius at which a Mong Khet circle reaches half: {half_radius_at(g, *MONG_KHET):.1f} km")

        la, lo, b = best_circle(g, coarse)
        print("Best-placed circle of 3,300 km:")
        report("best", g, la, lo)
        print(f"  nearest GeoNames city: {nearest(places, la, lo)}")
        print(
            f"  distance from Mong Khet point: "
            f"{pyproj.Geod(a=R * 1000, b=R * 1000).inv(MONG_KHET[1], MONG_KHET[0], lo, la)[2] / 1000:.0f} km"
        )
        r50, c50 = smallest_half(g, (la, lo))
        print(
            "Half-the-people circle, local climb only (see circle_refine.py for the scan): "
            f"radius {r50:.1f} km, centre {c50[0]:.3f}, {c50[1]:.3f}; "
            f"nearest city {nearest(places, *c50)}"
        )

        # WGS84 geodesic against the sphere, on the 0.1 degree grid
        rr, cc = np.nonzero(coarse.a)
        ln, lt = coarse.lon[cc], coarse.lat[rr]
        geod = pyproj.Geod(ellps="WGS84")
        _, _, dist = geod.inv(np.full(ln.shape, MONG_KHET[1]), np.full(ln.shape, MONG_KHET[0]), ln, lt)
        vg = coarse.a[rr, cc][dist <= RADIUS * 1000].sum()
        print(
            f"0.1 deg grid: WGS84 geodesic inside {fmt(vg)} = {100 * vg / coarse.total:.2f}%; "
            f"sphere on same grid {100 * coarse.inside(*MONG_KHET) / coarse.total:.2f}%"
        )

        def breakdown(lat, lon, coarse=coarse, top=6):
            h = (
                np.sin(np.radians(coarse.lat[:, None] - lat) / 2) ** 2
                + np.cos(np.radians(coarse.lat[:, None]))
                * math.cos(math.radians(lat))
                * np.sin(np.radians(coarse.lon[None, :] - lon) / 2) ** 2
            )
            m = 2 * R * np.arcsin(np.sqrt(h)) <= RADIUS
            ids = admin_ids[m]
            pops = coarse.a[m]
            tot = np.bincount(ids, weights=pops, minlength=len(names) + 1)
            areas = coarse.cell_area[:, None] * np.ones((1, coarse.cols))
            land_km2 = areas[m & (land_mask > 0)].sum()
            order = np.argsort(tot[1:])[::-1][:top] + 1
            txt = ", ".join(f"{names[i]} {tot[i] / 1e6:,.1f}M" for i in order)
            share = 100 * land_km2 / areas[land_mask > 0].sum()
            print(f"  land inside {fmt(land_km2)} km2 = {share:.1f}% of Natural Earth land")
            print(f"  by country (0.1 deg): {txt}; unassigned {tot[0] / 1e6:.1f}M")

        print("Breakdown, Mong Khet:")
        breakdown(*MONG_KHET)
        print("Breakdown, best-placed:")
        breakdown(la, lo)

        print("Comparison circles, 3,300 km:")
        mk = g.inside(*MONG_KHET)
        for name, (cl, cn) in (
            ("Canada centroid", centres["Canada"]),
            ("Australia centroid", centres["Australia"]),
            ("Alice Springs", alice),
        ):
            v = report(name, g, cl, cn)
            print(f"  Mong Khet circle holds {mk / v:.1f} times as many")
            breakdown(cl, cn)
        for country in ("Canada", "Australia"):
            cid = [k for k, n in names.items() if n == country][0]
            rows, cols = np.nonzero(admin_ids == cid)
            pts = sorted({(round(coarse.lat[r]), round(coarse.lon[c])) for r, c in zip(rows, cols, strict=False)})
            scored = sorted((g.inside(a, b), a, b) for a, b in pts)
            v, a, b = scored[0]
            print(f"Lowest-population centre on {country} land (1 deg scan of {len(pts)} points):")
            report(country + " lowest", g, a, b)
            print(f"  nearest city: {nearest(places, a, b)}")
            print(f"  Mong Khet circle holds {mk / v:.1f} times as many")
            breakdown(a, b)
        del g, coarse


if __name__ == "__main__":
    main()
