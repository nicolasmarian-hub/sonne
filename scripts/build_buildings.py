#!/usr/bin/env python3
"""
Download every building in Berlin from the official ALKIS WFS
(Geoportal Berlin, licence dl-de/zero-2.0) and write compact
z16 tiles for the Sonne Berlin page.

Output: <out>/b/<x>/<y>.json   — [[h*10, lon0*1e6, lat0*1e6, dlon, dlat, ...], ...]
        <out>/buildings_meta.json

Only the Python standard library is used.
"""
import json, math, os, sys, time, urllib.parse, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

WFS = "https://gdi.berlin.de/services/wfs/alkis_gebaeude"
TYPENAME = "alkis_gebaeude:gebaeude"
# Berlin extent in EPSG:25833 (metres), with margin
X0, X1, Y0, Y1 = 368000, 417000, 5797000, 5839000
CELL = 1500
TZ = 16
STOREY_M = 3.5   # Berlin floors are tall (Altbau ~3.5-4 m)
ROOF_M = 1.0


def fetch(params, tries=5):
    url = WFS + "?" + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "sonne-berlin-builder (github.com/nicolasmarian-hub/sonne)"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))


def cell_features(x, y):
    base = {
        "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
        "TYPENAMES": TYPENAME, "OUTPUTFORMAT": "application/json",
        "SRSNAME": "EPSG:4326",
        "BBOX": f"{x},{y},{x + CELL},{y + CELL},urn:ogc:def:crs:EPSG::25833",
    }
    try:
        return fetch({**base, "PROPERTYNAME": "aog,ofl,bezofl,gfk,shape_area,geom"})["features"]
    except Exception:
        return fetch(base)["features"]   # server refused PROPERTYNAME: take everything


def height(p):
    aog = p.get("aog")
    if isinstance(aog, (int, float)) and aog > 0:
        return aog * STOREY_M + ROOF_M
    area = p.get("shape_area") or 0
    return 3.0 if area < 80 else 8.0


def tile_of(lon, lat):
    n = 2 ** TZ
    x = int((lon + 180) / 360 * n)
    r = math.radians(lat)
    y = int((1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * n)
    return x, y


def encode_ring(ring):
    pts = []
    for lon, lat in ring:
        q = (round(lon * 1e6), round(lat * 1e6))
        if pts and abs(q[0] - pts[-1][0]) < 3 and abs(q[1] - pts[-1][1]) < 3:
            continue                       # drop points closer than ~0.2-0.3 m
        pts.append(q)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    if len(pts) < 3:
        return None
    out = [pts[0][0], pts[0][1]]
    for a, b in zip(pts, pts[1:]):
        out += [b[0] - a[0], b[1] - a[1]]
    return out


def main(out):
    cells = [(x, y) for x in range(X0, X1, CELL) for y in range(Y0, Y1, CELL)]
    print(f"{len(cells)} cells to query", flush=True)
    seen, tiles = set(), defaultdict(list)
    stats = defaultdict(int)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(cell_features, *c): c for c in cells}
        for k, f in enumerate(as_completed(futs), 1):
            for feat in f.result():
                fid = feat.get("id") or feat["properties"].get("uuid")
                if fid in seen:
                    continue
                seen.add(fid)
                p = feat.get("properties") or {}
                if "unter" in str(p.get("bezofl") or "").lower():
                    stats["underground"] += 1
                    continue
                g = feat.get("geometry") or {}
                polys = g.get("coordinates") or []
                if g.get("type") == "Polygon":
                    polys = [polys]
                h = height(p)
                stats["with_storeys" if p.get("aog") else "default_height"] += 1
                for poly in polys:
                    if not poly:
                        continue
                    enc = encode_ring(poly[0])        # outer ring only
                    if not enc:
                        continue
                    lon = sum(c[0] for c in poly[0]) / len(poly[0])
                    lat = sum(c[1] for c in poly[0]) / len(poly[0])
                    tiles[tile_of(lon, lat)].append([round(h * 10)] + enc)
                    stats["rings"] += 1
            if k % 50 == 0:
                print(f"  {k}/{len(cells)} cells · {len(seen)} buildings · {time.time() - t0:.0f}s", flush=True)

    total_bytes = 0
    for (x, y), arr in tiles.items():
        d = os.path.join(out, "b", str(x))
        os.makedirs(d, exist_ok=True)
        s = json.dumps(arr, separators=(",", ":"))
        total_bytes += len(s)
        with open(os.path.join(d, f"{y}.json"), "w") as fh:
            fh.write(s)
    lons, lats = [], []
    for (x, y) in tiles:
        n = 2 ** TZ
        lons += [x / n * 360 - 180, (x + 1) / n * 360 - 180]
        for yy in (y, y + 1):
            lats.append(math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * yy / n)))))
    meta = {
        "source": "ALKIS Berlin Gebäude, Geoportal Berlin (dl-de/zero-2.0)",
        "built": time.strftime("%Y-%m-%d"),
        "tz": TZ,
        "bbox": [min(lons), min(lats), max(lons), max(lats)],
        "buildings": len(seen), "tiles": len(tiles), "bytes": total_bytes, **stats,
    }
    with open(os.path.join(out, "buildings_meta.json"), "w") as fh:
        json.dump(meta, fh, indent=1)
    print(json.dumps(meta, indent=1))
    if len(seen) < 100000:
        sys.exit("Suspiciously few buildings — refusing to publish this build.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data")
