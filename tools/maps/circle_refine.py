"""Second stage of circle.py: dense scans and the comparison-circle choice.

Run after circle.py, same environment:
  uv run -q --no-project --with numpy --with rasterio --with geopandas --with pyproj \
      python tools/maps/circle_refine.py DATA

Stage 1 scans centres every 0.25 deg over 10-45N, 80-125E on the full 30-arcsec
grid and climbs from the top five, for r = 3300 km and for the smallest radius
reaching half. Stage 2 scores named GeoNames centres over Canada and Australia,
and scans Australian land for circles that hold essentially all of Australia.
"""

import math
import multiprocessing as mp
import sys
import zipfile
from pathlib import Path

import numpy as np
from rasterio import features
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).parent))
import circle as c  # noqa: E402

G = None
CENTRES = [(float(a), float(b)) for a in np.arange(10, 45.01, 0.25) for b in np.arange(80, 125.01, 0.25)]


def _one(args):
    la, lo, r = args
    return G.inside(la, lo, r), la, lo


def scan(pool, r):
    res = pool.map(_one, [(a, b, r) for a, b in CENTRES], chunksize=200)
    res.sort(reverse=True)
    out = [c.climb(G, (la, lo), r, steps=(0.1, 0.02)) for _, la, lo in res[:5]]
    return max(out, key=lambda t: t[2])


def main():
    global G
    places = c.load_places()
    with zipfile.ZipFile(c.DATA / "cities500.zip") as z:
        rows = {}
        for line in z.read("cities500.txt").decode().splitlines():
            f = line.split("\t")
            if f[8] in ("CA", "AU"):
                k = (f[1], f[8])
                if k not in rows or int(f[14]) > rows[k][2]:
                    rows[k] = (float(f[4]), float(f[5]), int(f[14]), f[0])
    admin = c.gpd.read_file(c.DATA / "ne/ne_10m_admin_0_countries.shp").reset_index(drop=True)
    names = {i + 1: n for i, n in enumerate(admin["ADMIN"])}
    tf = from_origin(-180, 90, 0.1, 0.1)
    ids = features.rasterize(
        ((g, i + 1) for i, g in enumerate(admin.geometry)), out_shape=(1800, 3600), transform=tf, fill=0, dtype="int32"
    )

    for label in ("GHS-POP R2023A E2025 30ss", "WorldPop R2025A 2025 constrained UN-adj 30ss"):
        print("=" * 78 + f"\n{label}\n" + "=" * 78)
        G = c.Grid(c.DATA / c.GRIDS[label])
        with mp.Pool(10) as pool:
            la, lo, v = scan(pool, c.RADIUS)
            print(
                f"Dense scan, r 3300: best centre {la:.2f}, {lo:.2f}: inside {c.fmt(v)} = {100 * v / G.total:.2f}%; "
                f"nearest {c.nearest(places, la, lo)}"
            )
            lo_r, hi_r = 3380.0, 3520.0
            hit = None
            while hi_r - lo_r > 2.0:
                mid = (lo_r + hi_r) / 2
                a, b, v = scan(pool, mid)
                print(f"  r {mid:.1f}: best {a:.2f}, {b:.2f}: {100 * v / G.total:.3f}%")
                if v >= G.total / 2:
                    hi_r, hit = mid, (a, b, v)
                else:
                    lo_r = mid
            if hit:
                print(
                    f"Smallest half circle: radius about {hi_r:.0f} km, centre {hit[0]:.2f}, {hit[1]:.2f}, "
                    f"{100 * hit[2] / G.total:.3f}%; nearest {c.nearest(places, hit[0], hit[1])}"
                )

        coarse = c.coarsen(G)

        def part(mask, coarse=coarse):
            p = c.Grid.__new__(c.Grid)
            p.__dict__.update(coarse.__dict__)
            p.a = coarse.a * mask
            p.finish()
            return p

        au_id = [k for k, n in names.items() if n == "Australia"][0]
        ca_id = [k for k, n in names.items() if n == "Canada"][0]
        us_id = [k for k, n in names.items() if n == "United States of America"][0]
        id_ = [k for k, n in names.items() if n == "Indonesia"][0]
        au, ca, us, indo = part(ids == au_id), part(ids == ca_id), part(ids == us_id), part(ids == id_)

        print("Named centres, Australia (r 3300):")
        for n in (
            "Adelaide",
            "Port Augusta",
            "Coober Pedy",
            "Broken Hill",
            "Mildura",
            "Melbourne",
            "Alice Springs",
            "Sydney",
        ):
            if (n, "AU") not in rows:
                print(" ", n, "not in cities500")
                continue
            a, b, _, gid = rows[(n, "AU")]
            v = G.inside(a, b)
            print(
                f"  {n} (GeoNames {gid}, {a:.5f}, {b:.5f}): inside {c.fmt(v)} = {100 * v / G.total:.3f}%; "
                f"Australia {au.inside(a, b) / 1e6:.1f} of {au.total / 1e6:.1f}M, "
                f"Indonesia {indo.inside(a, b) / 1e6:.1f}M"
            )
        print("Chosen and runner-up escalation centres, by country on the 0.1 deg grid:")
        mk = G.inside(*c.MONG_KHET)
        for n in ("Adelaide", "Melbourne"):
            a, b = rows[(n, "AU")][:2]
            h = (
                np.sin(np.radians(coarse.lat[:, None] - a) / 2) ** 2
                + np.cos(np.radians(coarse.lat[:, None]))
                * math.cos(math.radians(a))
                * np.sin(np.radians(coarse.lon[None, :] - b) / 2) ** 2
            )
            m = 2 * c.R * np.arcsin(np.sqrt(h)) <= c.RADIUS
            tot = np.bincount(ids[m], weights=coarse.a[m], minlength=len(names) + 1)
            top = np.argsort(tot[1:])[::-1][:7] + 1
            print(
                f"  {n}: "
                + ", ".join(f"{names[i]} {tot[i] / 1e6:,.2f}M" for i in top)
                + f"; unassigned {tot[0] / 1e6:.2f}M; full-grid total {c.fmt(G.inside(a, b))}; "
                f"Mong Khet circle holds {mk / G.inside(a, b):.1f} times as many; "
                f"1 in {G.total / G.inside(a, b):.0f} people"
            )
        print("Scan of Australian land, 1 deg, circles holding at least 99% of Australia, lowest total first:")
        rr, cc = np.nonzero(ids == au_id)
        pts = sorted({(round(coarse.lat[r]), round(coarse.lon[k])) for r, k in zip(rr, cc, strict=False)})
        good = sorted((G.inside(a, b), a, b) for a, b in pts if au.inside(a, b) >= 0.99 * au.total)
        for v, a, b in good[:5]:
            print(
                f"  {a}, {b}: inside {c.fmt(v)} = {100 * v / G.total:.3f}%; Australia {au.inside(a, b) / 1e6:.1f}M, "
                f"Indonesia {indo.inside(a, b) / 1e6:.1f}M; nearest {c.nearest(places, a, b)}"
            )
        print(f"  {len(good)} of {len(pts)} points qualify")

        print("Named centres, Canada (r 3300):")
        for n in (
            "Yellowknife",
            "Cambridge Bay",
            "Baker Lake",
            "Rankin Inlet",
            "Iqaluit",
            "Whitehorse",
            "Inuvik",
            "Churchill",
        ):
            if (n, "CA") not in rows:
                print(" ", n, "not in cities500")
                continue
            a, b, _, gid = rows[(n, "CA")]
            v = G.inside(a, b)
            print(
                f"  {n} (GeoNames {gid}, {a:.5f}, {b:.5f}): inside {c.fmt(v)} = {100 * v / G.total:.3f}%; "
                f"Canada {ca.inside(a, b) / 1e6:.1f} of {ca.total / 1e6:.1f}M, USA {us.inside(a, b) / 1e6:.1f}M"
            )
        G = None


if __name__ == "__main__":
    main()
