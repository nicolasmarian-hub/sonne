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
