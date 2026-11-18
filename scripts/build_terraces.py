#!/usr/bin/env python3
"""
Fetch every café / bar / pub / restaurant / Biergarten / ice-cream place
in Berlin from OpenStreetMap (Overpass API) and write a compact terraces.json.

Each record: [id, lat, lon, amenity, name, outdoor_seating, street, housenumber, website, beer_garden]
"""
import json, sys, time, urllib.parse, urllib.request

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
QUERY = """[out:json][timeout:300];
area["ISO3166-2"="DE-BE"]["admin_level"="4"]->.berlin;
nwr["amenity"~"^(cafe|bar|pub|restaurant|biergarten|ice_cream)$"](area.berlin);
out center tags qt;"""


def overpass():
    body = urllib.parse.urlencode({"data": QUERY}).encode()
    last = None
    for attempt in range(3):
        for url in ENDPOINTS:
            try:
                req = urllib.request.Request(url, data=body, headers={
                    "User-Agent": "sonne-berlin-builder (github.com/nicolasmarian-hub/sonne)",
                    "Content-Type": "application/x-www-form-urlencoded"})
                with urllib.request.urlopen(req, timeout=400) as r:
                    return json.load(r)["elements"]
            except Exception as e:
                last = e
                print(f"  {url} failed: {e}", flush=True)
        time.sleep(30)
    raise last


def main(out):
    rows = []
    for e in overpass():
        t = e.get("tags") or {}
        lat = e.get("lat") or (e.get("center") or {}).get("lat")
        lon = e.get("lon") or (e.get("center") or {}).get("lon")
        if lat is None or (t.get("outdoor_seating") or "").lower() == "no":
            continue
        rows.append([e["type"][0] + str(e["id"]), round(lat, 6), round(lon, 6), t.get("amenity", ""),
                     t.get("name", ""), t.get("outdoor_seating", ""), t.get("addr:street", ""),
                     t.get("addr:housenumber", ""), t.get("website", "") or t.get("contact:website", ""),
                     t.get("beer_garden", "")])
    if len(rows) < 1000:
        sys.exit(f"Only {len(rows)} places — Overpass answer looks incomplete, refusing to publish.")
    with open(f"{out}/terraces.json", "w") as fh:
        json.dump(rows, fh, ensure_ascii=False, separators=(",", ":"))
    confirmed = sum(1 for r in rows if r[5].lower() in ("yes", "garden", "terrace", "sidewalk", "pedestrian_zone") or r[3] == "biergarten")
    print(f"{len(rows)} places, {confirmed} with confirmed outdoor seating")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data")
