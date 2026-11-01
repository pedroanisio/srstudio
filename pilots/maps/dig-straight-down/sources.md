---
pilot: dig-straight-down
generated-by: claude-opus-5-5 in Claude Code
checked: 2026-11-01
---

# Sources: dig straight down

Status key: **computed** = computed by `tools/maps/antipodes.py` from the named data, quoted from its output.

| Claim on screen | Status | Evidence |
| --- | --- | --- |
| "Four in five people would come up in the ocean." | computed | GHS-POP E2025: 8,191,988,536 people, 20.18% opposite land, 79.82% opposite sea. WorldPop R2025A: 8,196,931,816 people, 20.02% and 79.98%. Land mask: Natural Earth 10m land. |
| "New York City? The Indian Ocean." | computed | GeoNames 5128581 lands at 40.714 S, 105.994 E, sea, 11.1 degrees from Australia. |
| "Beijing comes up in Argentina." | computed | GeoNames 1816670 lands at 39.907 S, 63.603 W, inside Argentina in Natural Earth countries. Beijing only: Chengdu lands in the sea and Xi'an in Chile, so the reel does not say China. |
| "Flip the far side onto this one. About an eighth of the land has land opposite." | computed | 13.10% of the land's area in Natural Earth 10m lies opposite land. An eighth is 12.5%. |
| "Madrid gets New Zealand." | computed | GeoNames 3117735 lands at 40.416 S, 176.297 E, inside New Zealand in Natural Earth countries. |

## Main references

Schiavina, M., Freire, S., Carioli, A., MacManus, K. (2023). GHS-POP R2023A, epoch 2025, 30 arc-seconds. European Commission, Joint Research Centre. https://doi.org/10.2905/2FF68A52-5B5B-4A22-8F40-C41DA8332CFE

Bondarenko, M. et al. (2025). Global mosaics 2015-2030 (1km resolution) R2025A v1. WorldPop, University of Southampton. https://doi.org/10.5258/SOTON/WP00845. WorldPop marks this release as alpha.

Natural Earth 10m land and admin 0 countries, version 5.1.1. https://www.naturalearthdata.com

GeoNames cities: the coordinates of each record named above. https://www.geonames.org

## Method and limits

- The antipode of a point flips its latitude and moves its longitude by 180 degrees. A grid cell's people count as opposite land when the cell's antipode falls on the land mask.
- A cell's antipode is decided at its centre, so coastlines are good to about 1 km of grid.
- A city is one coordinate, not its whole footprint: part of a large city can land elsewhere. London lands in the sea, 2.1 degrees from New Zealand, and is not used.
- The red dots are the channel's dots, one per million people, turned to their antipodes. The figure is the grid's, computed above, and not a count of the dots on screen.
- A hole through the Earth is a picture, not an engineering claim. Nothing in the reel states a depth.
