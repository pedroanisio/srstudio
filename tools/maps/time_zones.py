"""How many clocks each country runs, and whether the sun ever sets on France: the figures behind Most Time Zones.

Run: python3 tools/maps/time_zones.py

Reads the system's tz database (zone.tab and tzdata.zi, which names its version) and fetches nothing. A country's
territories are the ISO codes in :data:`COUNTRIES`; a clock is a distinct UTC offset in force at a moment. Antarctic
claims are left out, and so are places with no tz zone: uninhabited Clipperton (France), Baker and Howland
(United States) are not counted. The sun's altitude uses the Astronomical Almanac's low-precision formulae, sampled
every five minutes of 2026, and a town counts as lit above -0.833 degrees (the sun's rim, with refraction).
"""

import collections
import datetime as dt
import math
import pathlib
import zoneinfo

ZONES = pathlib.Path("/usr/share/zoneinfo")
YEAR = 2026
COUNTRIES = {
    "France": "FR GF PF TF NC YT RE GP MQ MF BL PM WF",
    "Russia": "RU",
    "United States": "US PR VI GU MP AS UM",
    "United Kingdom": "GB BM GI IO KY FK GS MS PN SH TC VG AI",
    "Australia": "AU CC CX NF",
    "Denmark": "DK FO GL",
    "New Zealand": "NZ CK NU TK",
    "Canada": "CA",
}
TOWNS = {  # GeoNames coordinates of inhabited France, far apart
    "Papeete": (-17.5334, -149.5667),
    "Mata-Utu": (-13.2825, -176.1736),
    "Fort-de-France": (14.6089, -61.0733),
    "Cayenne": (4.9333, -52.3333),
    "Paris": (48.8534, 2.3488),
    "Saint-Denis": (-20.8823, 55.4504),
    "Noumea": (-22.2763, 166.4572),
}
HORIZON = -0.833


def zones_of(codes: str) -> list[str]:
    table = collections.defaultdict(list)
    for line in (ZONES / "zone.tab").read_text().splitlines():
        if not line.startswith("#"):
            cells = line.split("\t")
            table[cells[0]].append(cells[2])
    return [zone for code in codes.split() for zone in table[code]]


def clocks(zones: list[str], moment: dt.datetime) -> set[float]:
    offsets = (moment.astimezone(zoneinfo.ZoneInfo(zone)).utcoffset() for zone in zones)
    return {offset.total_seconds() / 3600 for offset in offsets if offset is not None}


def altitude(lat: float, lon: float, t: dt.datetime) -> float:
    d = (t - dt.datetime(2000, 1, 1, 12, tzinfo=dt.timezone.utc)).total_seconds() / 86400
    g = math.radians((357.528 + 0.9856003 * d) % 360)
    ecliptic = math.radians((280.460 + 0.9856474 * d) % 360 + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g))
    tilt = math.radians(23.439 - 4e-7 * d)
    ascension = math.atan2(math.cos(tilt) * math.sin(ecliptic), math.cos(ecliptic))
    declination = math.asin(math.sin(tilt) * math.sin(ecliptic))
    hour = math.radians((280.46061837 + 360.98564736629 * d) % 360 + lon) - ascension
    la = math.radians(lat)
    return math.degrees(
        math.asin(math.sin(la) * math.sin(declination) + math.cos(la) * math.cos(declination) * math.cos(hour))
    )


def sun(towns: dict[str, tuple[float, float]]) -> None:
    t = dt.datetime(YEAR, 1, 1, tzinfo=dt.timezone.utc)
    samples, dark, lowest = 0, 0, (90.0, t)
    while t.year == YEAR:
        best = max(altitude(*p, t) for p in towns.values())
        samples, dark = samples + 1, dark + (best <= HORIZON)
        lowest = min(lowest, (best, t))
        t += dt.timedelta(minutes=5)
    print(f"{len(towns)} towns, {samples} moments in {YEAR}: {dark} with no town lit; lowest best altitude "
          f"{lowest[0]:.1f} deg at {lowest[1]:%d %b %H:%M} UTC")  # fmt: skip


def main() -> None:
    print((ZONES / "tzdata.zi").read_text().splitlines()[0])
    for name, codes in COUNTRIES.items():
        zones = zones_of(codes)
        january = clocks(zones, dt.datetime(YEAR, 1, 15, 12, tzinfo=dt.timezone.utc))
        july = clocks(zones, dt.datetime(YEAR, 7, 15, 12, tzinfo=dt.timezone.utc))
        print(f"{name}: January {len(january)}, July {len(july)}")
        if name == "France":
            print(f"  January {sorted(january)}\n  July {sorted(july)}")
    sun(TOWNS)
    sun({k: v for k, v in TOWNS.items() if k != "Noumea"})


if __name__ == "__main__":
    main()
