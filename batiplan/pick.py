"""Hit-test geometry + snapping candidates for every entity type."""
from shapely.geometry import LineString, Polygon, Point, box
from shapely.ops import unary_union
from shapely import affinity
from . import geom as g
from .render import column_poly, room_poly, stair_local, wall_poly, opening_frame, PAPER
from .furniture import CATALOG
from .model import layer_of


def entity_geom(e, project):
    t = e["type"]; S = project.scale
    try:
        if t == "wall": return wall_poly(e)
        if t == "column": return column_poly(e)
        if t == "room": return room_poly(e)
        if t == "hatch": return Polygon([tuple(p) for p in e["pts"]]).buffer(0)
        if t in ("axis", "line"): return LineString([tuple(e["p1"]), tuple(e["p2"])])
        if t == "poly":
            pts = [tuple(p) for p in e["pts"]]; return LineString(pts + ([pts[0]] if e.get("closed") else []))
        if t == "circle": return Point(e["c"]).buffer(e["r"]).exterior
        if t == "arc": return LineString(g.arc_pts(tuple(e["c"]), e["r"], e["a0"], e["a1"]))
        if t == "opening":
            w = next((x for x in project.entities if x["id"] == e.get("wall")), None)
            if not w: return None
            c, u, n = opening_frame(e, w); hw, ht = e["w"] / 2, w["t"] / 2
            return Polygon([g.add(g.add(c, g.mul(u, -hw)), g.mul(n, -ht)), g.add(g.add(c, g.mul(u, hw)), g.mul(n, -ht)),
                            g.add(g.add(c, g.mul(u, hw)), g.mul(n, ht)), g.add(g.add(c, g.mul(u, -hw)), g.mul(n, ht))])
        if t == "stair":
            lines, polys, path = stair_local(e); f = lambda q: g.add(g.rot(q, e.get("rot", 0)), tuple(e["p"]))
            return unary_union([Polygon([f(q) for q in pl]) for pl in polys])
        if t == "furn":
            W, D = CATALOG[e["block"]][2], CATALOG[e["block"]][3]; sx, sy = e.get("sx", e.get("s", 1.0)), e.get("sy", e.get("s", 1.0))
            r = affinity.rotate(box(-W * sx / 2, -D * sy / 2, W * sx / 2, D * sy / 2), e.get("rot", 0), origin=(0, 0))
            return affinity.translate(r, e["c"][0], e["c"][1])
        if t == "dim":
            p1, p2 = tuple(e["p1"]), tuple(e["p2"]); n = g.perp(g.norm(g.sub(p2, p1))); off = e.get("off", 500)
            return LineString([g.add(p1, g.mul(n, off)), g.add(p2, g.mul(n, off))])
        if t == "text":
            h = e.get("h", 3.0) * S; lines = str(e["s"]).split("\n"); w = max(1, len(lines[0])) * h * 0.65
            r = box(0, -h * 1.4 * (len(lines) - 1), w, h); a = e.get("anchor", "l")
            r = affinity.translate(r, -w / 2 if a == "c" else (-w if a == "r" else 0), 0)
            return affinity.translate(affinity.rotate(r, e.get("rot", 0), origin=(0, 0)), e["p"][0], e["p"][1])
        if t == "sym":
            if e["kind"] == "leader": return LineString([tuple(p) for p in e["pts"]])
            if "p1" in e: return LineString([tuple(e["p1"]), tuple(e["p2"])])
            return Point(e["p"]).buffer(6 * S)
        if t == "frame":
            pw, ph = PAPER[e.get("size", "A3")]
            pw, ph = (max(pw, ph), min(pw, ph)) if e.get("orient", "L") == "L" else (min(pw, ph), max(pw, ph)); x0, y0 = e["p"]
            return box(x0, y0, x0 + pw * project.scale, y0 + ph * project.scale).exterior
    except Exception:
        return None
    return None


def pick(project, pt, tol):
    """Closest entity to pt (within tol mm). Line-like / small entities win over areas."""
    P = Point(pt); best = None
    for e in project.entities:
        if not project.visible(e) or project.layer_state[layer_of(e)]["locked"]: continue
        gm = entity_geom(e, project)
        if gm is None or gm.is_empty: continue
        d = gm.distance(P)
        if d > tol: continue
        prio = 0 if e["type"] in ("room", "hatch", "frame") else 1
        key = (round(d, 3) if d > 0 else 0, -prio, gm.area if gm.geom_type == "Polygon" else 0)
        if best is None or key < best[0]: best = (key, e["id"])
    return best[1] if best else None


def ids_in_box(project, x0, y0, x1, y1, crossing):
    rect = box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)); out = []
    for e in project.entities:
        if not project.visible(e): continue
        gm = entity_geom(e, project)
        if gm is None or gm.is_empty: continue
        if (crossing and rect.intersects(gm)) or (not crossing and rect.contains(gm)): out.append(e["id"])
    return out


def snap_points(project):
    pts = []
    mid = lambda a, b: ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, "mid")
    for e in project.entities:
        if not project.visible(e): continue
        t = e["type"]
        if t == "wall":
            p = [tuple(q) for q in e["pts"]]; pts += [(q[0], q[1], "end") for q in p]
            for a, b in g.segs(p, bool(e.get("closed"))): pts.append(mid(a, b))
        elif t in ("axis", "line"):
            a, b = tuple(e["p1"]), tuple(e["p2"]); pts += [(a[0], a[1], "end"), (b[0], b[1], "end"), mid(a, b)]
        elif t == "poly":
            p = [tuple(q) for q in e["pts"]]; pts += [(q[0], q[1], "end") for q in p]
            for a, b in g.segs(p, bool(e.get("closed"))): pts.append(mid(a, b))
        elif t in ("circle", "arc"): pts.append((e["c"][0], e["c"][1], "center"))
        elif t == "column":
            pts.append((e["c"][0], e["c"][1], "center")); pts += [(x, y, "end") for x, y in list(column_poly(e).exterior.coords)[:-1]][:12]
        elif t in ("room", "hatch"): pts += [(q[0], q[1], "end") for q in e["pts"]]
        elif t == "dim": pts += [(e["p1"][0], e["p1"][1], "end"), (e["p2"][0], e["p2"][1], "end")]
        elif t == "frame": pts += [(x, y, "end") for x, y in list(entity_geom(e, project).coords)[:4]]
        elif t == "furn": pts.append((e["c"][0], e["c"][1], "center"))
        elif t == "stair": pts.append((e["p"][0], e["p"][1], "end"))
    for u in project.underlay:
        if u["t"] == "line": pts += [(u["a"][0], u["a"][1], "end"), (u["b"][0], u["b"][1], "end")]
        elif u["t"] == "poly": pts += [(q[0], q[1], "end") for q in u["pts"]]
    return pts
