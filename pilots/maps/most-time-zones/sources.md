---
pilot: most-time-zones
generated-by: claude-opus-5-5 in Claude Code
checked: 2026-11-01
---

# Sources: most time zones

Status key: **computed** = computed by `tools/maps/time_zones.py`, quoted from its output; **data file** = read from the named file.

| Claim on screen | Status | Evidence |
| --- | --- | --- |
| "Most time zones on Earth? France." | computed, with a scope | tz database 2026c, distinct UTC offsets on 15 July 2026: France 12, Russia 11, United States 10. On 15 January France and Russia tie at 11. The stamp says July and the caption says January. |
| "Twelve clocks in July. Russia has eleven." | computed | July offsets for France: -10, -9.5, -9, -4, -3, -2, 2, 3, 4, 5, 11, 12. Russia has 11 in both months. |
| "Tahiti is France. Reunion is France." | data file | Natural Earth 5.1.1 lists French Polynesia as a dependency with sovereign France, and holds Reunion inside France's own record. The tz zones are `Pacific/Tahiti` and `Indian/Reunion`. A fetch of the French Constitution, article 72-3, was refused by the host, so the statute was not read. |
| "France has a land border with Brazil." | data file | Natural Earth 5.1.1: the France-Brazil boundary through French Guiana measures 518 km. |
| "The sun never sets on France." | computed | Seven towns (Papeete, Mata-Utu, Fort-de-France, Cayenne, Paris, Saint-Denis, Noumea), 105,120 moments at 5-minute steps through 2026: at none of them is every town dark. Lowest best altitude 19.7 degrees, 18 June 04:35 UTC. Without Noumea the result holds, lowest 15.5 degrees, 2 July 04:15 UTC. |

## Limits

- The day the reel runs is 18 June 2026 UTC, the day of the year the seven towns come closest to all dark. The dots turn on the sun's altitude at five-minute steps, and the build stops if a step of that day has no town lit.

- Antarctic claims are left out. So is Clipperton, which is French and uninhabited but has no tz zone. Counting it would change January's tie.
- "France" here means every territory France governs, so the claim is about the French Republic, not the mainland.
- A claim about France's longest border was dropped: on Natural Earth 5.1.1 Spain is 567 km and Brazil 518 km.
- New Caledonia's status may change. It is not named aloud, and the sun check holds without it.

## Main references

Eggert, P. et al. tz database, release 2026c. https://www.iana.org/time-zones

Natural Earth 10m admin 0 countries, version 5.1.1. https://www.naturalearthdata.com
