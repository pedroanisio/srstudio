---
pilot: further-north
generated-by: claude-opus-5-5 in Claude Code
checked: 2026-10-31
---

# Sources: further north

Status key: **gazetteer** = read from the named data file; **computed** = arithmetic on those records; **full text** = the paper itself was read; **abstract** = only the abstract was read; **secondary source only** = the claim rests on another source, named in the row.

## Main references

GeoNames, cities15000 extract, downloaded 2026-10-31 (server date of the file: 2026-10-31). https://download.geonames.org/export/dump/. CC BY 4.0. Coordinates are WGS84 decimal degrees. All latitudes on screen come from this one file.

Natural Earth 1:10m Populated Places, version 5.1.2 (public domain), is the cross-check only. City limits are from OpenStreetMap through Nominatim, queried 2026-10-31 (© OpenStreetMap contributors, ODbL), used as a check and not shown on screen.

Seager, R., Battisti, D. S., Yin, J., Gordon, N., Naik, N., Clement, A. C., & Cane, M. A. (2002). Is the Gulf Stream responsible for Europe's mild winters? *Quarterly Journal of the Royal Meteorological Society, 128*, 2563–2586. https://doi.org/10.1256/qj.01.128

Read in full from the author's copy: https://ocp.ldeo.columbia.edu/res/div/ocp/gs/pubs/Seager_etal_QJ_2002.pdf

Seager, R. (2006). The source of Europe's mild climate. *American Scientist, 94*(4), 334–341. Read in full: https://ocp.ldeo.columbia.edu/res/div/ocp/gs/pubs/Seager_AmSci_2006.pdf

## Which point is measured

Each latitude is GeoNames' single point for a populated place. It is neither a named landmark nor a stated centroid: GeoNames' About page does not say how the point is chosen, and only states that coordinates use WGS84. So call it "the GeoNames point for the city", not "the city centre".

That matters less than it sounds. For the three reel pairs the two cities' limits do not overlap at all (table below), so the comparison holds wherever in each city you measure.

## How to round on screen

**Show one decimal, and say so: "Latitudes rounded to 0.1°. GeoNames, 2026."**

- One decimal keeps all three comparisons visibly true: 41.9 over 40.7, 48.9 over 45.5, 51.5 over 51.1.
- Don't use whole degrees. London against Calgary would read 52 and 51, which looks like a full degree when the gap is 0.46°.
- Calgary is **51.1**, not the brief's 51.0. The record is 51.05011, which rounds up.
- Label the pin **New York City**. New York State reaches 45.02°N, north of Rome, so "New York" alone invites a true objection.

## Claims a reel can safely make

| # | Plain-words claim | Exact figure | Source | Where | Status |
|---|---|---|---|---|---|
| 1 | Rome sits at 41.9°N. | 41.89193 | GeoNames 3169070, PPLC, record modified 2025-07-22 | cities15000 | gazetteer |
| 2 | New York City sits at 40.7°N. | 40.71427 | GeoNames 5128581, PPL, modified 2026-03-07 | cities15000 | gazetteer |
| 3 | Rome is further north than New York City. | Gap 1.17766°, 130.8 km along a meridian | Rows 1, 2; WGS84 geodesic | computed | computed |
| 4 | Paris sits at 48.9°N. | 48.85341 | GeoNames 2988507, PPLC, modified 2026-02-23 | cities15000 | gazetteer |
| 5 | Montreal sits at 45.5°N. | 45.50884 | GeoNames 6077243, PPLA2, modified 2026-02-23 | cities15000 | gazetteer |
| 6 | Paris is further north than Montreal. | Gap 3.34457°, 371.8 km | Rows 4, 5; WGS84 geodesic | computed | computed |
| 7 | London sits at 51.5°N. | 51.50853 | GeoNames 2643743, PPLC, modified 2026-08-17 | cities15000 | gazetteer |
| 8 | Calgary sits at 51.1°N. | 51.05011 | GeoNames 5913490, PPL, modified 2026-01-20 | cities15000 | gazetteer |
| 9 | London is further north than Calgary, by about 50 km. | Gap 0.45842°, 51.0 km | Rows 7, 8; WGS84 geodesic | computed | computed |

## Do the comparisons hold?

All three hold in both gazetteers, and on city limits too. London against Calgary is the closest, and it holds with about 8 km to spare between the limits.

| Pair | GeoNames | Natural Earth 5.1.2 | Southern limit of the first city | Northern limit of the second | Verdict |
|---|---|---|---|---|---|
| Rome, New York City | 41.89, 40.71 | 41.90, 40.75 | 41.66 | 40.92 | Holds |
| Paris, Montreal | 48.85, 45.51 | 48.87, 45.50 | 48.82 | 45.70 | Holds |
| London, Calgary | 51.51, 51.05 | 51.50, 51.08 | 51.29 (Greater London) | 51.21 | Holds; gap 0.074° between limits |

Limits are the OpenStreetMap boundary box of each administrative area. The two gazetteers place New York City differently enough to round to 40.7 and 40.8, which is why the reel should use one source throughout.

## A third escalation

All three pairs below were verified the same way, and each pair's limits are fully separate.

| Rank | Claim | GeoNames | Gap | On screen | Natural Earth | Limits check |
|---|---|---|---|---|---|---|
| 1 | Oslo is further north than Juneau, the capital of Alaska. | 59.91273, 58.30194 | 1.61°, 179.4 km | 59.9, 58.3 | 59.92, 58.31 | Oslo south 59.81; Juneau borough north 58.97 |
| 2 | Algiers is further north than Tokyo. | 36.73225, 35.68950 | 1.04°, 115.7 km | 36.7, 35.7 | 36.77, 35.69 | Algiers point against Tokyo north 35.90 (OSM has no Algiers boundary box; it returned a place node) |
| 3 | Venice is further north than Toronto. | 45.43713, 43.70643 | 1.73°, 192.3 km | 45.4, 43.7 | 45.44, 43.70 | Venice south 45.23; Toronto north 43.86 |

**Recommendation: Oslo over Juneau.** Alaska is the place viewers file as far north, so it is the strongest of the three.

Rejected pairs:

- **Edinburgh over Moscow.** True on the pins (55.95206, 55.75204, 22 km), but the limits overlap: Edinburgh 55.82–56.00, Moscow 55.14–56.02.
- **Rome over Chicago.** 41.89193, 41.85003: only 4.7 km, and both round to 41.9.
- **Barcelona over New York City, Madrid over Beijing.** True, but less surprising than the three above, and both tie in whole degrees if the rounding changes.
- **Paris over Seattle** is sound (48.85341, 47.60621) but repeats Paris.

## The optional turn: why Europe stays mild

**One short true line exists, but only if it leaves the Gulf Stream out:** "Why so mild? Winter winds off the Atlantic."

**Recommendation: put that line in the caption, and spend the reel's time on Oslo over Juneau.** The surprise in the turn would be "not the Gulf Stream", and that part can't be both short and true. Without it the line has little kick, and the reel's trigger is being wrong, which another pair serves better.

| # | What the source supports | Quote or figure | Where | Status |
|---|---|---|---|---|
| 10 | Winds are the main cause of the winter contrast across the Atlantic. | "the principal cause of this temperature difference is advection by the mean winds. South-westerlies bring warm maritime air into Europe" | Seager et al. 2002, summary, p. 2563 | full text |
| 11 | Most winter heat released by the ocean was stored earlier. | "the majority of the heat released during winter from the ocean to the atmosphere is accounted for by the seasonal release of heat previously absorbed" | Seager et al. 2002, summary, p. 2563 | full text |
| 12 | The contrast is large. | "as much as 15–20 degC" | Seager et al. 2002, p. 2563 | full text |
| 13 | The ocean's heat transport still warms both sides, by a few degrees. | "OHT warms winters on both sides of the North Atlantic Ocean by a few degC"; in one model it contributes "at most 2 degC out of the total contrast of about 15 degC" south of 60°N | Seager et al. 2002, pp. 2577–2578, 2584 | full text |
| 14 | Mountains matter too. | Net orography "accounts for almost half of the observed winter temperature contrast" | Seager et al. 2002, conclusion (iv), p. 2584 | full text |
| 15 | Seager does not say the Gulf Stream does nothing. | "The Gulf Stream indeed contributes to Europe's warmth, but it is wrong to conflate the climate difference across the North Atlantic with the northward flow of warm water in the Gulf Stream." | Seager 2006, p. 334 | full text |

The result is about the **difference** between Europe and eastern North America in winter, not about why Europe is warm in absolute terms. It is also not settled:

- Scientific American reports Rhines and Häkkinen arguing that stored heat in the eastern Atlantic, carried by the prevailing winds, largely backs Maury's Gulf Stream idea. https://www.scientificamerican.com/article/new-simulations-question-gulf-stream-role-tempering-europes-winters/ (secondary source only; their paper was not read).
- Palter (2015), *Annual Review of Marine Science*, is reported in a search result to call the question a strenuous debate (secondary source only; the review was not read).

The proposed line survives because both sides have the heat arriving on the winds.

## Wrong or weaker versions to avoid

| Don't say | Why | Say instead |
|---|---|---|
| "Most people guess New York." | The brief's assumption. No source measures it. | Ask the question and let the viewer guess. |
| "Rome or New York?" with no pin label | New York State reaches 45.02°N. | Pin and label New York City. |
| "Calgary, 51.0°N" | The record rounds to 51.1. | 51.1 |
| "It's not the Gulf Stream." | Seager himself says it contributes, and the question is still argued. | "Winter winds off the Atlantic." |
| "The Gulf Stream is a myth." | Seager's 2006 subtitle says this, about a narrower claim, and rows 13 and 15 qualify it. | Leave it out. |
| "Seager proved..." | One research group's models and analysis, contested since. | Name no proof. |
| "Calgary is cold because..." | Seager's contrast is Europe against eastern North America and the Pacific coast. Calgary, inland, is not what was analysed. | Keep the climate line off the Calgary beat. |
| "City centre" | GeoNames doesn't state what its point is. | "GeoNames point", or just the latitude. |

## Projection

**Orthographic globe for the hook, equirectangular for the reveal.**

- The reel compares latitude, not area, so any projection is fair if parallels read true.
- On a tilted globe, parallels curve, so a city near the edge can look higher or lower than it is. That is fine for the hook and wrong for the answer.
- On equirectangular, parallels are straight, level and evenly spaced, so "further north" means "higher on screen", exactly.
- Mercator also gives straight parallels, but it stretches spacing toward the poles, so equal gaps in latitude stop looking equal.

Name both on screen or in the caption: "Orthographic globe, then equirectangular."

## Licences and credit

| Data | Licence | Credit wording |
|---|---|---|
| GeoNames | CC BY 4.0, stated in the extract's readme and on https://www.geonames.org/about.html | Required. "Coordinates: GeoNames (geonames.org), CC BY 4.0." The data is "as is", without warranty. |
| Natural Earth | Public domain. "No permission is needed to use Natural Earth. Crediting the authors is unnecessary." | Optional. Their suggested text: "Made with Natural Earth." Long form: "Made with Natural Earth. Free vector and raster map data @ naturalearthdata.com." https://www.naturalearthdata.com/about/terms-of-use/ |
| Boundaries | Natural Earth "shows de facto boundaries by default according to who controls the territory" (admin-0 countries, version 5.1.1). Use as they are. | State no view on disputed territory. |

## Where the brief needs correcting

1. **Calgary "about 51.0°N".** It should be 51.1 at one decimal.
2. **"New York".** It should be New York City on screen.
3. **"Most viewers guess New York".** Unmeasured. Keep it out of any on-screen claim.
4. **The other figures** (41.9, 40.7, 48.9, 45.5, 51.5) check out at one decimal.
5. **Seager et al. (2002).** The brief's summary is fair: more weight on the atmosphere and the ocean's stored heat. Add that the finding concerns the contrast, not Europe's warmth as a whole.
