---
pilot: inside-the-circle
generated-by: claude-opus-5-5 in Claude Code
checked: 2026-10-31
---

# Sources: inside the circle

Status key: **computed** = recomputed from the named grid by `tools/maps/circle.py` and `tools/maps/circle_refine.py`, quoted from their output; **full text** = the source itself was read; **data file** = read from the named file; **secondary source only** = the claim rests on another source, named in the row; **not read** = the source could not be reached.

## The answer

**The claim no longer holds at 3,300 km.** In 2025, a circle of 3,300 km around Mong Khet holds 48.3% of the world, so more people live outside it than inside. No circle of that radius reaches half: the best-placed one holds 49.0%, centred about 780 km further north. Two separate 2025 grids agree to within 0.1 of a point on the Mong Khet figure.

**Headline the reel may use (9 words):** "Nearly half of all people live inside this circle."

**Stamp (8 words):** "Inside 3.95 bn. Outside 4.24 bn. GHS-POP 2025."

**Escalation stamp (8 words):** "Same circle over Australia: 44 million. GHS-POP 2025."

To keep the original hook "More people live inside this circle than outside it", the circle has to grow: around Mong Khet, 3,500 km holds 50.2%. That is true on both grids, by about 36 million people out of 8.2 billion. It is a redrawn circle with a thin margin, and the share is falling, so the recommendation is **"Nearly half"** at 3,300 km.

## Main references

Schiavina, Marcello; Freire, Sergio; Alessandra Carioli; MacManus, Kytt (2023): GHS-POP R2023A - GHS population grid multitemporal (1975-2030). European Commission, Joint Research Centre (JRC) [Dataset] doi: 10.2905/2FF68A52-5B5B-4A22-8F40-C41DA8332CFE PID: http://data.europa.eu/89h/2ff68a52-5b5b-4a22-8f40-c41da8332cfe

Product used: `GHS_POP_E2025_GLOBE_R2023A_4326_30ss_V1_0`: epoch 2025, 30 arc-seconds (about 1 km at the equator), WGS84, downloaded 2026-10-31 without login. Epoch 2015 of the same product is used for the then-and-now check. Method and citation are from the GHSL Data Package 2023, section 2.5, pp. 45–48, shipped in the download and read there.

Cross-check grid: Bondarenko M. et al. (2025), Global mosaics 2015-2030 (1km resolution) R2025A v1, WorldPop, University of Southampton. https://doi.org/10.5258/SOTON/WP00845. File `global_pop_2025_CN_1km_R2025A_UA_v1.tif`. WorldPop marks this release as an alpha version. The file name and path suggest constrained and UN-adjusted; the page does not state the adjustment.

World total: United Nations, Department of Economic and Social Affairs, Population Division (2024). World Population Prospects 2024, file GEN/01/REV1, medium variant. CC BY 3.0 IGO. Read from the workbook.

Quah, D. (2015). The world's tightest cluster of people. LSE Mathematics blog, 16 December 2015, reposted from the author's blog of September 2015. https://blogs.lse.ac.uk/maths/2015/12/16/the-worlds-tightest-cluster-of-people/. Read in full.

Centre: GeoNames 11154258 Mongkhet, 21.70282, 99.34224, an ADM3 township record, CC BY 4.0, MM extract downloaded 2026-10-31. Quah says "near Mong Khet" and gives no coordinates, so this point is a stand-in for his centre.

## Method

- A cell counts as inside when its centre is within the great-circle distance, on a sphere of radius 6371.0088 km.
- `tools/maps/circle.py` uses fast per-row sums. A brute-force haversine over every cell gave the same total, with a difference of 0 people.
- Circle area from summed cell areas: 33,453,877 km². Exact spherical cap: 33,453,846 km².
- Sphere against WGS84 geodesics on a 0.1° grid: 48.31% and 48.35%. The choice does not change the rounded figure.
- `tools/maps/circle_refine.py` scans best-placed centres every 0.25° over 10–45°N, 80–125°E on the full grid, then climbs from the top five. A 2° global scan in `tools/maps/circle.py` put the best centres in this same region.
- Country splits use Natural Earth 5.1.1 polygons on a 0.1° grid. They are approximate, and coastal cells can fall outside every polygon.

## World total against the UN

| Grid | Grid total | UN WPP 2024, 1 January | UN WPP 2024, 1 July | Grid against 1 January | Grid against 1 July |
|---|---|---|---|---|---|
| GHS-POP R2023A, 2025 | 8,191,988,536 | 8,196,980,849 | 8,231,613,070 | −0.06% | −0.48% |
| GHS-POP R2023A, 2015 | 7,426,597,609 | 7,426,477,815 | 7,470,491,872 | +0.00% | −0.59% |
| WorldPop R2025A, 2025 | 8,196,931,816 | 8,196,980,849 | 8,231,613,070 | −0.00% | −0.42% |

The 2025 GHS total also equals the data package's Table 20 figure exactly (8,191,988,536, p. 48). GHS-POP is fitted to the older UN WPP 2022 (p. 46), so the small gap to WPP 2024 is expected.

The 2025 epoch is modelled, not a census count. The package calls 2025 and 2030 "future epochs" for built-up surface, solved by "interpolation or extrapolation" (p. 6), and its population estimates are carried forward from census years (p. 46).

## Claims a reel can safely make

| # | Plain-words claim | Exact figure | Source | Where | Status |
|---|---|---|---|---|---|
| 1 | About 8.19 billion people on this grid. | 8,191,988,536 | GHS-POP R2023A E2025 30ss | whole grid | computed |
| 2 | Nearly half live inside 3,300 km of Mong Khet. | 3,954,047,236 = 48.27% | GHS-POP R2023A E2025 30ss | `tools/maps/circle.py` | computed |
| 3 | The rest live outside it. | 4,237,941,300 = 51.73% | GHS-POP R2023A E2025 30ss | `tools/maps/circle.py` | computed |
| 4 | A second grid agrees. | 3,953,350,929 = 48.23% | WorldPop R2025A 2025 | `tools/maps/circle.py` | computed |
| 5 | Even the best-placed 3,300 km circle falls short of half. | GHS 4,016,685,391 = 49.03%, centre 28.69, 99.98 (near Daocheng, China); WorldPop 48.91%, centre 28.68, 99.97 | Both grids | `tools/maps/circle_refine.py` | computed |
| 6 | Reaching half now takes about 3,440 km, still near Mong Khet. | Best-placed: GHS about 3,442 km, WorldPop about 3,443 km, centre 20.93, 100.37 (28 km from Möng Yawng, Myanmar) | Both grids | `tools/maps/circle_refine.py` | computed |
| 7 | Centred exactly on the Mong Khet point, half takes about 3,470 km. | GHS 3,472.2 km; WorldPop 3,474.1 km | Both grids | `tools/maps/circle.py` | computed |
| 8 | The circle covers about 7% of Earth's surface. | 33,453,846 km² = 6.56% | Spherical cap | `tools/maps/circle.py` | computed |
| 9 | It covers about one-eighth of the land. | 12.7% of Natural Earth land (0.1° grid), 18,589,234 km² | Natural Earth 5.1.1 land | `tools/maps/circle.py` | computed |
| 10 | Ten years ago the same circle held a larger share. | 3,671,456,195 = 49.44% in 2015; 48.27% in 2025 | GHS-POP R2023A, E2015 and E2025 | `tools/maps/circle.py` | computed |
| 11 | In 2015, a best-placed circle of this radius did reach half. | 3,736,817,715 = 50.32%, centre 28.69, 99.98 | GHS-POP R2023A E2015 | `tools/maps/circle.py` | computed |
| 12 | Same circle over Australia, centred on Adelaide: about 44 million people. The whole of Australia fits. | 43,750,398 = 0.534%; WorldPop 42,812,569 = 0.522%; about 1 person in 187 | GHS-POP R2023A E2025; centre GeoNames 2078025, -34.92866, 138.59863 | `tools/maps/circle_refine.py` | computed |
| 13 | The Mong Khet circle holds about 90 times as many. | 90.4 times (GHS); 92.3 times (WorldPop) | Rows 2, 12 | `tools/maps/circle_refine.py` | computed |

Sensitivity of row 2 to the radius (GHS-POP E2025): 3,200 km 46.74%; 3,250 km 47.64%; 3,280 km 48.03%; 3,320 km 48.75%; 3,350 km 49.02%; 3,400 km 49.46%; 3,500 km 50.22%. So "about 3,300 km" does not hide a majority: it takes well over 3,400 km to get there.

## Which comparison circle

**Recommendation: Australia, centred on Adelaide (GeoNames 2078025, -34.92866, 138.59863).** The whole country fits inside, and the count is about 44 million.

Canada fails as a demonstration. Any circle holding most of Canada also takes in much of the United States, so the number shows Americans, not Canadian emptiness. A centroid is no better for Australia: it reaches Java.

| Centre | Inside (GHS-POP E2025) | Share | What's inside | Verdict |
|---|---|---|---|---|
| Australia centroid, -25.261, 134.390 | 160,355,346 | 1.96% | Indonesia 109.5M, Australia 25.0M | Reject: two-thirds Indonesian |
| Alice Springs | 182,344,789 | 2.23% | Indonesia 130.3M, Australia 25.0M | Reject, same reason |
| **Adelaide** | **43,750,398** | **0.534%** | Australia 25.02M, Papua New Guinea 6.25M, New Zealand 3.73M, Indonesia 3.36M, East Timor 1.35M | **Use** |
| Melbourne | 34,633,135 | 0.423% | Australia 24.98M, New Zealand 4.32M, Papua New Guinea 1.27M | Sound, lower, but the circle sits off-centre on the continent |
| Canada centroid, 57.608, -97.772 | 366,918,474 | 4.48% | USA 312.8M, Canada 37.6M, Mexico 6.9M | Reject: mostly Americans |
| Baker Lake | 233,141,368 | 2.85% | USA 188.3M, Canada 37.6M | Reject |
| Cambridge Bay | 106,262,854 | 1.30% | USA 68.2M, Canada 35.8M | Reject |
| Northern Ellesmere, 82, -83 | 6,370,559 | 0.08% | Canada 1.1M, Russia 1.1M, Norway 0.9M | Lowest found with a centre on Canadian land; mostly Arctic Ocean, and it wouldn't read as "over Canada" |

The Adelaide circle is not all Australians: about 19 million of the 44 million live elsewhere, mostly in Papua New Guinea, New Zealand and Indonesia. "Over Australia: 44 million" is true. "44 million Australians" is not. The centre was chosen so the circle holds the country and largely misses Java, and that choice should be stated in the caption.

## Origin of the claim

| # | Claim | What the source says | Where | Status |
|---|---|---|---|---|
| 14 | Ken Myers drew the original circle in 2013. | "In 2013 Ken Myers guessed and verified that his Valeriepieris circle – a circular region on a 2-dimensional map, centred in the South China Sea and about 4,000 km in radius – contained more than half the world's population." | Quah 2015 | full text |
| 15 | Quah found the smallest such circle for 2015. | "the smallest circle on our planet containing a majority of the world turns out to be that circle centred near Mong Khet, in Myanmar, with great-circle distance 3,300km" | Quah 2015 | full text |
| 16 | Quah's data. | "population data with 100 km resolution on Earth's surface"; dataset not named; no share given; "Details and code will be made available presently." | Quah 2015 | full text |
| 17 | The map was a Reddit post by a user called valeriepieris. | Wikipedia: "a map posted on Reddit in 2013, made by an American ESL teacher named Ken Myers", "whose username on the site gave the figure its name". Quah does not mention Reddit. | https://en.wikipedia.org/wiki/Valeriepieris_circle, citing r/MapPorn post 1dqh7d | secondary source only |
| 18 | The Reddit post itself. | Reddit refused the fetch. Title, date and wording are unverified. | https://www.reddit.com/r/MapPorn/comments/1dqh7d/ | not read |
| 19 | Quah's original September 2015 post. | Returned 404. The LSE repost was read instead. | dannyquah.com | not read |
| 20 | Formal treatment of such circles. | Wiley returned 403. | Arthur (2023), https://doi.org/10.1111/gean.12383 | not read |

These 2015 figures do not contradict Quah. He used a different, unnamed grid at much coarser resolution and gave no exact centre. GHS-POP 2015 also estimates that year after the fact, fitted to UN WPP 2022.

## Wrong or weaker versions to avoid

| Don't say | Why | Say instead |
|---|---|---|
| "More people live inside this circle than outside it." (at 3,300 km) | False on both 2025 grids: 48.27% and 48.23%. | "Nearly half of all people live inside this circle." |
| "Half the world lives here." | It rounds generously, and the brief's rule is not to overclaim. | "Nearly half", or "48%". |
| "This is the smallest circle holding half of humanity." | True of Quah's 2015 result. In 2025 that takes about 3,440 km. | Leave "smallest" out. |
| "The best circle of this size." | The best 3,300 km circle in 2025 is centred near Daocheng, China. | Say only "around Mong Khet". |
| "44 million Australians." | About 25 million are. | "Over Australia: 44 million." |
| "Canada's circle holds 37 million." | That is Canadians only; the circle holds about 367 million. | Don't use Canada. |
| "Quah was wrong." | Different data, resolution and year. | "In 2015 it held; by 2025, nearly half." |
| Any on-screen total without a year | The brief requires dataset and year. | "GHS-POP 2025". |

## Projection

**Lambert azimuthal equal-area, re-centred on each circle.** For Mong Khet: `+proj=laea +lat_0=21.70282 +lon_0=99.34224`. For Adelaide: `+proj=laea +lat_0=-34.92866 +lon_0=138.59863`.

- It is equal-area, which this reel needs because it compares how much ground holds how many people.
- It is the equal-area projection that draws a true great-circle radius as a perfect circle around its centre, with a screen radius of 2R·sin(r/2R).
- That radius is the same for both circles at the same map scale, so the "same size" claim is literally true on screen.
- Don't show both circles on one world map. On Equal Earth or Mollweide, areas stay honest, but a true circle far from the centre is drawn skewed.
- Name it on screen or in the caption: "Lambert equal-area."

A turning orthographic globe is fine as a move between the two views, but not as the view that carries the comparison, because the globe foreshortens area near its edge.

## Licences and credit

| Data | Licence | Credit wording |
|---|---|---|
| GHS-POP R2023A | CC BY 4.0: "Reuse is allowed provided appropriate credit is given and any changes are indicated." © European Union, 1995-2026 (file `copyright.txt`) | Short: "GHS-POP R2023A, European Commission JRC, CC BY 4.0." Full citation as above in `sources.md`. Changes to indicate: summed inside circles, recoloured. |
| GHSL methodology | | Pesaresi, Martino, Marcello Schiavina, Panagiotis Politis, Sergio Freire, Katarzyna Krasnodębska, Johannes H. Uhl, Alessandra Carioli, et al. (2024). Advances on the Global Human Settlement Layer by Joint Assessment of Earth Observation and Population Survey Data. *International Journal of Digital Earth 17*(1). doi:10.1080/17538947.2024.2390454 |
| WorldPop R2025A (cross-check only) | CC BY 4.0, except data derived from OpenStreetMap or Microsoft building and road data, which fall under ODbL | Needed only if the reel shows WorldPop figures. |
| UN WPP 2024 | CC BY 3.0 IGO, stated in the workbook | Cite as above if quoted. |
| GeoNames | CC BY 4.0 | "Coordinates: GeoNames (geonames.org), CC BY 4.0." |
| Natural Earth | Public domain. "No permission is needed to use Natural Earth. Crediting the authors is unnecessary." | Optional: "Made with Natural Earth." https://www.naturalearthdata.com/about/terms-of-use/ |
| Boundaries | Natural Earth "shows de facto boundaries by default according to who controls the territory" (admin-0 countries, version 5.1.1). Use as they are. | State no view on disputed territory. Keep country splits off the screen. |

GHS-POP needs credit in the reel's caption and `sources.md`. The population layer on screen must be labelled with its year.

## Where the brief needs correcting

1. **"More people live inside this circle than outside it".** False at 3,300 km with 2025 data. Use "Nearly half".
2. **Who found what.** Myers's circle, per Quah, was about 4,000 km in radius and centred in the South China Sea. The 3,300 km circle near Mong Khet is Quah's.
3. **"Radius".** Quah writes "great-circle distance 3,300km". Radius is the only reading that fits, and row 11 supports it.
4. **"Checked it in 2015".** He did more than check: he solved for the smallest circle, in September 2015, with data he doesn't name.
5. **"Canada or Australia".** Use Australia. See the comparison table.
6. **GPW.** Not needed separately: GHS-POP is built from GPWv4.11 census data (p. 46).
