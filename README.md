# Sonne Berlin ☀

Which café terraces in Berlin are in the sun right now, or at any time you pick.
Inspired by [jveuxdusoleil.fr](https://jveuxdusoleil.fr).

**Live:** https://nicolasmarian-hub.github.io/sonne/

## How it works

- **Buildings** come from the official cadastre, *ALKIS Berlin Gebäude* (Geoportal Berlin,
  licence [dl-de/zero-2.0](https://www.govdata.de/dl-de/zero-2-0)): about 780,000 footprints with storey counts.
  Height = storeys × 3.5 m + 1 m. `scripts/build_buildings.py` turns them into small map tiles.
- **Cafés, bars, pubs, restaurants, Biergärten and ice-cream places** come from OpenStreetMap.
  Places tagged `outdoor_seating=yes` (and all Biergärten) count as terraces.
  `scripts/build_terraces.py` fetches them.
- **Shadows** are worked out in the browser from the sun's position and building heights.
  Trees, awnings and weather are ignored.

## Updating

The GitHub Action in `.github/workflows/build.yml` runs:
- on every push to `main`,
- every Monday, to refresh cafés,
- every 3 February, to rebuild buildings. You can also run it by hand from the *Actions* tab
  (tick "Re-download all buildings").

Building tiles are cached as an asset on the `buildings-data` release, so normal runs take about a minute.

## Missing or wrong terraces

Only places that OpenStreetMap marks with `outdoor_seating=yes` (plus all Biergärten) appear by default.
Two ways to fix one:

1. **Best: fix OpenStreetMap itself.** Add "outdoor seating: yes" to the place, on openstreetmap.org
   or in the StreetComplete phone app. The site picks it up the following Monday, and every other map benefits too.
2. **Quick: edit [`terraces_overrides.csv`](terraces_overrides.csv)** on GitHub (pencil icon → commit).
   The site rebuilds in about 2 minutes.
   - `osm_id,terrace,…` marks an OpenStreetMap place as a terrace (find the id with the "OSM" link in its popup, e.g. `n3778102238`).
   - `osm_id,hide,…` hides a place.
   - `,terrace,Name,52.49,13.42,cafe,` adds a place that isn't in OpenStreetMap at all.
