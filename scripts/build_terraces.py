#!/usr/bin/env python3
"""
Fetch every café / bar / pub / restaurant / Biergarten / ice-cream place
in Berlin from OpenStreetMap (Overpass API) and write a compact terraces.json.

Each record: [id, lat, lon, amenity, name, outdoor_seating, street, housenumber, website, beer_garden]
"""
import csv, hashlib, json, os, sys, time, urllib.parse, urllib.request

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


def apply_overrides(rows, path=os.path.join(os.path.dirname(__file__), "..", "terraces_overrides.csv")):
    """terraces_overrides.csv — hand-curated fixes on top of OpenStreetMap.
    action=terrace : show this place as a terrace (by osm_id, or add a new place with name/lat/lon)
    action=hide    : never show this place
    """
    if not os.path.exists(path):
        return rows
    by_id = {r[0]: r for r in rows}
    hidden = set()
    with open(path, newline="", encoding="utf-8") as fh:
        for o in csv.DictReader(fh):
            oid, act = (o.get("osm_id") or "").strip(), (o.get("action") or "").strip().lower()
            if act == "hide" and oid:
                hidden.add(oid)
            elif act == "terrace":
                if oid in by_id:
                    by_id[oid][5] = "yes"
                    if o.get("name"):
                        by_id[oid][4] = by_id[oid][4] or o["name"]
                elif o.get("lat") and o.get("lon"):
                    nid = oid or "x" + hashlib.md5(f"{o['name']}{o['lat']}{o['lon']}".encode()).hexdigest()[:10]
                    rows.append([nid, float(o["lat"]), float(o["lon"]), o.get("amenity") or "cafe",
                                 o.get("name") or "", "yes", "", "", "", ""])
                else:
                    print(f"  override for {oid or o.get('name')} skipped: not in OSM and no lat/lon")
    print(f"  overrides: {len(hidden)} hidden, file {path}")
    return [r for r in rows if r[0] not in hidden]


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
    rows = apply_overrides(rows)
    if len(rows) < 1000:
        sys.exit(f"Only {len(rows)} places — Overpass answer looks incomplete, refusing to publish.")
    with open(f"{out}/terraces.json", "w") as fh:
        json.dump(rows, fh, ensure_ascii=False, separators=(",", ":"))
    confirmed = sum(1 for r in rows if r[5].lower() in ("yes", "garden", "terrace", "sidewalk", "pedestrian_zone") or r[3] == "biergarten")
    print(f"{len(rows)} places, {confirmed} with confirmed outdoor seating")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data")
