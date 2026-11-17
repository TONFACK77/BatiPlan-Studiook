"""Original procedural hatch patterns, clipped to a polygon (vector output)."""
import math
from shapely.geometry import LineString, Point, Polygon
from shapely import affinity

PATTERNS = ["diag", "cross", "brick", "block", "concrete", "rc", "earth", "wood", "insulation", "gravel", "stone", "tile", "steel", "solid"]
NAMES = {"diag": ("Diagonales", "Diagonal lines"), "cross": ("Quadrillage diagonal", "Cross-hatch"), "brick": ("Brique", "Brick"),
         "block": ("Agglo / parpaing", "Concrete block"), "concrete": ("Béton", "Concrete"), "rc": ("Béton armé", "Reinforced concrete"),
         "earth": ("Terre / remblai", "Earth / fill"), "wood": ("Bois", "Wood"), "insulation": ("Isolant", "Insulation"), "gravel": ("Gravier", "Gravel"),
         "stone": ("Pierre", "Stone"), "tile": ("Carrelage", "Tile"), "steel": ("Acier", "Steel"), "solid": ("Plein", "Solid")}


def _rand(i, j, k=0):
    n = (i * 73856093) ^ (j * 19349663) ^ (k * 83492791)
    n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65536.0


def _lines(poly, spacing, angle, offset=0.0):
    minx, miny, maxx, maxy = poly.bounds
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    R = math.hypot(maxx - minx, maxy - miny) / 2 + spacing
    out = []
    n = int(R / spacing) + 1
    for i in range(-n, n + 1):
        y = i * spacing + offset
        out.append(affinity.rotate(LineString([(cx - R, cy + y), (cx + R, cy + y)]), angle, origin=(cx, cy)))
    return out


def _clip(poly, geoms):
    segs = []
    for g in geoms:
        inter = poly.intersection(g)
        if inter.is_empty: continue
        for p in (inter.geoms if hasattr(inter, "geoms") else [inter]):
            if p.geom_type == "LineString" and p.length > 1e-6: segs.append(list(p.coords))
    return segs


def _points(poly, spacing, jitter=0.8):
    minx, miny, maxx, maxy = poly.bounds
    i0, j0 = int(minx // spacing) - 1, int(miny // spacing) - 1
    i1, j1 = int(maxx // spacing) + 1, int(maxy // spacing) + 1
    pts = []
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            x = (i + 0.5 + (_rand(i, j, 1) - 0.5) * jitter) * spacing
            y = (j + 0.5 + (_rand(i, j, 2) - 0.5) * jitter) * spacing
            if poly.contains(Point(x, y)): pts.append((i, j, x, y))
    return pts


def hatch_prims(points, pattern, spacing, angle=0.0, layer="hatch"):
    poly = Polygon(points)
    if not poly.is_valid: poly = poly.buffer(0)
    if poly.is_empty: return []
    sp = max(spacing, 1.0)
    prims = []
    L = lambda a, b: {"t": "line", "a": a, "b": b, "layer": layer}

    def lines_to_prims(segs):
        for s in segs:
            if len(s) == 2: prims.append(L(s[0], s[1]))
            else: prims.append({"t": "poly", "pts": s, "closed": False, "layer": layer})

    if pattern == "solid":
        return [{"t": "fill", "pts": list(poly.exterior.coords)[:-1], "holes": [list(r.coords)[:-1] for r in poly.interiors], "layer": layer, "color": "#999999"}]
    if pattern == "diag": lines_to_prims(_clip(poly, _lines(poly, sp, 45 + angle)))
    elif pattern == "steel": lines_to_prims(_clip(poly, _lines(poly, sp * 0.5, 45 + angle)))
    elif pattern == "cross": lines_to_prims(_clip(poly, _lines(poly, sp, 45 + angle) + _lines(poly, sp, 135 + angle)))
    elif pattern == "tile": lines_to_prims(_clip(poly, _lines(poly, sp * 2, angle) + _lines(poly, sp * 2, 90 + angle)))
    elif pattern == "brick":
        lines_to_prims(_clip(poly, _lines(poly, sp * 0.7, 45 + angle))); lines_to_prims(_clip(poly, _lines(poly, sp * 3.5, 135 + angle)))
    elif pattern == "block":
        lines_to_prims(_clip(poly, _lines(poly, sp, 45 + angle))); lines_to_prims(_clip(poly, _lines(poly, sp * 2, 135 + angle)))
    elif pattern == "wood":
        lines_to_prims(_clip(poly, _lines(poly, sp * 0.5, angle)))
        for i, j, x, y in _points(poly, sp * 4, 0.9):
            if _rand(i, j, 5) > 0.5: prims.append(L((x - sp, y), (x + sp, y + sp * 0.3)))
    elif pattern == "earth":
        lines_to_prims(_clip(poly, _lines(poly, sp * 1.4, 45 + angle)))
        for i, j, x, y in _points(poly, sp * 1.4, 0.2): prims.append(L((x, y), (x + sp * 0.35, y - sp * 0.35)))
    elif pattern in ("concrete", "rc"):
        for i, j, x, y in _points(poly, sp):
            if _rand(i, j, 3) < 0.55:
                prims.append({"t": "circle", "c": (x, y), "r": sp * (0.05 + 0.08 * _rand(i, j, 4)), "layer": layer})
            else:
                a = _rand(i, j, 6) * math.pi; ln = sp * (0.35 + 0.35 * _rand(i, j, 7))
                prims.append(L((x, y), (x + ln * math.cos(a), y + ln * math.sin(a))))
        if pattern == "rc": lines_to_prims(_clip(poly, _lines(poly, sp * 5, 45 + angle)))
    elif pattern == "gravel":
        for i, j, x, y in _points(poly, sp * 1.1, 0.9):
            r = sp * (0.18 + 0.22 * _rand(i, j, 8))
            if _rand(i, j, 9) < 0.5: prims.append({"t": "circle", "c": (x, y), "r": r, "layer": layer})
            else:
                a0 = _rand(i, j, 10) * math.pi
                tri = [(x + r * 1.3 * math.cos(a0 + k * 2.094), y + r * 1.3 * math.sin(a0 + k * 2.094)) for k in range(3)]
                prims.append({"t": "poly", "pts": tri, "closed": True, "layer": layer})
    elif pattern == "stone":
        for i, j, x, y in _points(poly, sp * 2.2, 0.8):
            a = _rand(i, j, 11) * math.pi; ln = sp * (1.0 + _rand(i, j, 12)); a2 = a + 1.2 + _rand(i, j, 13)
            prims.append({"t": "poly", "pts": [(x, y), (x + ln * math.cos(a), y + ln * math.sin(a)), (x + ln * math.cos(a2) * .8, y + ln * math.sin(a2) * .8)], "closed": False, "layer": layer})
    elif pattern == "insulation":
        minx, miny, maxx, maxy = poly.bounds
        amp = sp * 0.5; n = int((maxy - miny) / (sp * 1.2)) + 2; waves = []
        for k in range(n):
            y0 = miny + k * sp * 1.2
            xs = [minx + i * sp * 0.4 for i in range(int((maxx - minx) / (sp * 0.4)) + 2)]
            waves.append(LineString([(x, y0 + amp * math.sin((x - minx) / sp * 2.6)) for x in xs]))
        lines_to_prims(_clip(poly, waves))
    else:
        lines_to_prims(_clip(poly, _lines(poly, sp, 45 + angle)))
    return prims
