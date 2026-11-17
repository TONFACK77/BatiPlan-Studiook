"""Pure function Project -> list of drawing primitives (shared by GUI, DXF, PDF, PNG)."""
import math
from shapely.geometry import LineString, Polygon, Point, box
from shapely.ops import unary_union
from shapely import affinity
from . import geom as g
from .model import layer_of, LAYERS
from .units import fmt_len
from .furniture import local_prims
from .hatchlib import hatch_prims

PAPER = {"A0": (841, 1189), "A1": (594, 841), "A2": (420, 594), "A3": (297, 420), "A4": (210, 297)}


def P(t, layer, **kw):
    d = {"t": t, "layer": layer}; d.update(kw); return d


def level_text(v): return f"{v:+.3f}" if abs(v) > 1e-9 else "±0.000"


# ----------------------------------------------------------------------------- walls
def wall_poly(e):
    pts = [tuple(p) for p in e["pts"]]
    if e.get("closed") and len(pts) > 2: pts = pts + [pts[0]]
    if len(pts) < 2: return None
    return LineString(pts).buffer(e["t"] / 2.0, cap_style=2, join_style=2, mitre_limit=6.0)


def opening_frame(op, wall):
    pts = [tuple(p) for p in wall["pts"]]
    P0, u = g.point_at(pts, op["pos"], bool(wall.get("closed")))
    return P0, u, g.perp(u)


def wall_union(project, with_openings=True):
    walls = {e["id"]: e for e in project.of_type("wall") if project.visible(e)}
    polys = [wp for wp in (wall_poly(e) for e in walls.values()) if wp is not None]
    if not polys: return None
    u = unary_union(polys)
    if with_openings:
        cutters = []
        for op in project.of_type("opening"):
            w = walls.get(op.get("wall"))
            if not w or not project.visible(op): continue
            c, t, n = opening_frame(op, w); hw, ht = op["w"] / 2.0, w["t"] / 2.0 + 30
            cutters.append(Polygon([g.add(g.add(c, g.mul(t, -hw)), g.mul(n, -ht)), g.add(g.add(c, g.mul(t, hw)), g.mul(n, -ht)),
                                    g.add(g.add(c, g.mul(t, hw)), g.mul(n, ht)), g.add(g.add(c, g.mul(t, -hw)), g.mul(n, ht))]))
        if cutters: u = u.difference(unary_union(cutters))
    return u


def _polys(geom):
    if geom is None or geom.is_empty: return []
    if isinstance(geom, Polygon): return [geom]
    return [p for p in getattr(geom, "geoms", []) if isinstance(p, Polygon) and not p.is_empty]


def _poly_prims(poly, layer, fill=None, eid=None):
    out = []; ext = list(poly.exterior.coords)[:-1]; holes = [list(r.coords)[:-1] for r in poly.interiors]
    if fill: out.append(P("fill", layer, pts=ext, holes=holes, color=fill))
    out.append(P("poly", layer, pts=ext, closed=True, eid=eid))
    for h in holes: out.append(P("poly", layer, pts=h, closed=True, eid=eid))
    return out


# ----------------------------------------------------------------------------- openings
def opening_prims(op, wall, S):
    layer = layer_of(op); c, u, n = opening_frame(op, wall); w, t = op["w"], wall["t"]
    kind = op.get("kind", "door"); out = []
    A = g.add(c, g.mul(u, -w / 2)); B = g.add(c, g.mul(u, w / 2)); side = 1 if op.get("side", 1) >= 0 else -1
    if kind in ("door", "door2"):
        leaves = [(op.get("hinge", "L"), w)] if kind == "door" else [("L", w / 2), ("R", w / 2)]
        for hinge, lw in leaves:
            if kind == "door": H, Fp = (A, B) if hinge == "L" else (B, A)
            else: H, Fp = (A, g.add(A, g.mul(u, w / 2))) if hinge == "L" else (B, g.sub(B, g.mul(u, w / 2)))
            v = g.sub(Fp, H); tip = g.add(H, g.mul(n, side * lw)); th = 40; vn = g.norm(v)
            out.append(P("poly", layer, pts=[H, tip, g.add(tip, g.mul(vn, th)), g.add(H, g.mul(vn, th))], closed=True))
            a_v = g.angle_deg((0, 0), v); cross = v[0] * (n[1] * side) - v[1] * (n[0] * side)
            a0 = a_v if cross > 0 else a_v - 90
            out.append(P("arc", layer, c=H, r=lw, a0=a0 % 360, a1=(a0 % 360) + 90))
    elif kind == "slide":
        off = g.mul(n, t * 0.18); sh = g.mul(u, w * 0.5)
        panel = [g.add(A, off), g.add(B, off), g.add(B, g.add(off, g.mul(n, 40))), g.add(A, g.add(off, g.mul(n, 40)))]
        out.append(P("poly", layer, pts=panel, closed=True))
        out.append(P("poly", layer, pts=[g.add(q, sh) for q in panel], closed=True, lt="DASHED"))
    else:
        for k in (-1.0, -1 / 3, 1 / 3, 1.0):
            o = g.mul(n, k * t / 2); out.append(P("line", layer, a=g.add(A, o), b=g.add(B, o)))
    if op.get("tag"):
        tp = g.add(c, g.mul(n, side * (t / 2 + 160 * S / 100 + 2.2 * S)))
        out.append(P("text", layer, p=tp, s=op["tag"], h=2.0 * S, rot=0, anchor="c"))
    return out


# ----------------------------------------------------------------------------- columns
def _tr(shp, dx, dy): return affinity.translate(shp, dx, dy)


def column_poly(e):
    cx, cy = e["c"]; w = e.get("w", 300); h = e.get("h", w); sh = e.get("shape", "rect"); k = e.get("th", min(w, h) / 3)
    if sh == "round": shp = Point(cx, cy).buffer(w / 2.0, 24)
    elif sh == "L": shp = _tr(Polygon([(0, 0), (w, 0), (w, k), (k, k), (k, h), (0, h)]), cx - w / 2, cy - h / 2)
    elif sh == "T": shp = _tr(Polygon([(0, h - k), (w, h - k), (w, h), (0, h)]).union(box((w - k) / 2, 0, (w + k) / 2, h - k)), cx - w / 2, cy - h / 2)
    elif sh == "X": shp = _tr(box(0, (h - k) / 2, w, (h + k) / 2).union(box((w - k) / 2, 0, (w + k) / 2, h)), cx - w / 2, cy - h / 2)
    else: shp = box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    if e.get("rot"): shp = affinity.rotate(shp, e["rot"], origin=(cx, cy))
    return shp


# ----------------------------------------------------------------------------- stairs
def stair_local(e):
    w = e["w"]; n = max(2, int(e["n"])); gd = e["g"]; kind = e.get("kind", "straight"); nt = n - 1; polys, lines = [], []
    if kind == "straight":
        L = nt * gd; polys.append([(0, 0), (L, 0), (L, w), (0, w)]); lines += [((i * gd, 0), (i * gd, w)) for i in range(1, nt)]
        path = [(gd * 0.4, w / 2), (L - gd * 0.2, w / 2)]
    elif kind == "L":
        t1 = nt // 2 + (nt - 1) % 2 if False else (nt - 1 + 1) // 2; t2 = nt - 1 - t1; L1 = t1 * gd; L2 = t2 * gd; sgn = 1 if e.get("turn", "L") == "L" else -1
        polys.append([(0, 0), (L1, 0), (L1, w), (0, w)]); lines += [((i * gd, 0), (i * gd, w)) for i in range(1, t1)]
        polys.append([(L1, 0), (L1 + w, 0), (L1 + w, w), (L1, w)]); lines.append(((L1, 0), (L1 + w, w))); lines.append(((L1, w), (L1 + w, 0)))
        if sgn > 0:
            polys.append([(L1, w), (L1 + w, w), (L1 + w, w + L2), (L1, w + L2)]); lines += [((L1, w + i * gd), (L1 + w, w + i * gd)) for i in range(1, t2)]
            path = [(gd * 0.4, w / 2), (L1 + w / 2, w / 2), (L1 + w / 2, w + L2 - gd * 0.2)]
        else:
            polys.append([(L1, 0), (L1 + w, 0), (L1 + w, -L2), (L1, -L2)]); lines += [((L1, -i * gd), (L1 + w, -i * gd)) for i in range(1, t2)]
            path = [(gd * 0.4, w / 2), (L1 + w / 2, w / 2), (L1 + w / 2, -L2 + gd * 0.2)]
    else:
        gap = e.get("gap", 100); t1 = (nt - 1 + 1) // 2; t2 = nt - 1 - t1; L1 = t1 * gd; L2 = t2 * gd; H = 2 * w + gap
        polys.append([(0, 0), (L1, 0), (L1, w), (0, w)]); lines += [((i * gd, 0), (i * gd, w)) for i in range(1, t1)]
        polys.append([(L1, 0), (L1 + w, 0), (L1 + w, H), (L1, H)]); polys.append([(L1, w + gap), (L1 - L2, w + gap), (L1 - L2, H), (L1, H)])
        lines += [((L1 - i * gd, w + gap), (L1 - i * gd, H)) for i in range(1, t2)]
        path = [(gd * 0.4, w / 2), (L1 + w / 2, w / 2), (L1 + w / 2, H - w / 2), (L1 - L2 + gd * 0.2, H - w / 2)]
    return lines, polys, path


def stair_prims(e, S):
    layer = "stair"; lines, polys, path = stair_local(e); p0 = tuple(e["p"]); ang = e.get("rot", 0)
    f = lambda q: g.add(g.rot(q, ang), p0)
    out = [P("poly", layer, pts=[f(q) for q in pl], closed=True) for pl in polys] + [P("line", layer, a=f(a), b=f(b)) for a, b in lines]
    pp = [f(q) for q in path]; out.append(P("poly", layer, pts=pp, closed=False))
    a, b = pp[-2], pp[-1]; d = g.norm(g.sub(b, a)); nn = g.perp(d); hs = 2.2 * S
    out.append(P("poly", layer, pts=[b, g.add(g.sub(b, g.mul(d, hs * 1.6)), g.mul(nn, hs * 0.55)), g.sub(g.sub(b, g.mul(d, hs * 1.6)), g.mul(nn, hs * 0.55))], closed=True))
    out.append(P("circle", layer, c=pp[0], r=0.8 * S))
    r = e.get("h", 3000) / max(1, e["n"]); mid = g.lerp(pp[0], pp[1], 0.5); an = g.angle_deg(pp[0], pp[1])
    out.append(P("text", layer, p=g.add(mid, g.mul(g.perp(g.norm(g.sub(pp[1], pp[0]))), 2.2 * S)), s=(e.get("up", "UP") + " " + f"{e['n']}x{r:.0f}/{e['g']:.0f}").strip(),
                 h=1.8 * S, rot=an if abs(an) < 90 else an + 180, anchor="c"))
    return out


# ----------------------------------------------------------------------------- symbols & dims
def _arrow(p, d, size, layer):
    nn = g.perp(d)
    return P("poly", layer, pts=[p, g.add(g.sub(p, g.mul(d, size)), g.mul(nn, size * 0.3)), g.sub(g.sub(p, g.mul(d, size)), g.mul(nn, size * 0.3))], closed=True, filled=True)


def dim_prims(e, project, S):
    layer = "dim"; p1, p2 = tuple(e["p1"]), tuple(e["p2"]); L = g.dist(p1, p2)
    if L < 1e-6: return []
    u = g.norm(g.sub(p2, p1)); n = g.perp(u); off = e.get("off", 500); sg = 1 if off >= 0 else -1
    A = g.add(p1, g.mul(n, off)); B = g.add(p2, g.mul(n, off)); gap, ext, tick = 1.5 * S, 2.0 * S, 1.3 * S
    out = [P("line", layer, a=g.add(p1, g.mul(n, sg * gap)), b=g.add(A, g.mul(n, sg * ext))), P("line", layer, a=g.add(p2, g.mul(n, sg * gap)), b=g.add(B, g.mul(n, sg * ext))),
           P("line", layer, a=g.sub(A, g.mul(u, ext)), b=g.add(B, g.mul(u, ext)))]
    d45 = g.norm(g.add(u, n))
    for q in (A, B): out.append(P("line", layer, a=g.sub(q, g.mul(d45, tick)), b=g.add(q, g.mul(d45, tick))))
    ang0 = g.angle_deg(p1, p2); ang = ang0 if -90 < ang0 <= 90 else ang0 + 180; same = ang == ang0
    txt = e.get("text") or fmt_len(L, project.unit)
    tp = g.add(g.lerp(A, B, 0.5), g.mul(n, sg * 1.0 * S * (1 if same else -1)))
    out.append(P("text", layer, p=tp, s=txt, h=2.0 * S, rot=ang, anchor="c", baseline=True))
    return out


def sym_prims(e, project, S):
    layer = "symbol"; k = e["kind"]; out = []
    if k == "north":
        c = tuple(e["p"]); r = 6 * S * e.get("size", 1.0); a = e.get("rot", 0); f = lambda q: g.add(g.rot(q, a), c)
        out.append(P("circle", layer, c=c, r=r))
        out.append(P("fill", layer, pts=[f((0, r * 1.15)), f((-r * 0.42, -r * 0.7)), f((0, -r * 0.3))], holes=[], color="#222222"))
        out.append(P("poly", layer, pts=[f((0, r * 1.15)), f((r * 0.42, -r * 0.7)), f((0, -r * 0.3))], closed=True))
        out.append(P("text", layer, p=f((0, r * 1.15 + 1.6 * S)), s="N", h=3 * S, rot=0, anchor="c"))
    elif k == "level":
        p = tuple(e["p"]); s_ = 1.6 * S
        out.append(P("poly", layer, pts=[p, g.add(p, (-s_, s_ * 1.5)), g.add(p, (s_, s_ * 1.5))], closed=True))
        out.append(P("line", layer, a=g.add(p, (-s_ * 1.4, s_ * 1.5)), b=g.add(p, (s_ * 5.5, s_ * 1.5))))
        out.append(P("text", layer, p=g.add(p, (s_ * 1.7, s_ * 1.5 + 0.5 * S)), s=level_text(e.get("value", 0.0)), h=2.0 * S, rot=0, anchor="l", baseline=True))
    elif k == "bubble":
        c = tuple(e["p"]); out.append(P("circle", layer, c=c, r=4 * S)); out.append(P("text", layer, p=c, s=str(e.get("label", "A")), h=3.0 * S, rot=0, anchor="c", middle=True))
    elif k == "section":
        p1, p2 = tuple(e["p1"]), tuple(e["p2"]); u = g.norm(g.sub(p2, p1)); n = g.perp(u); sd = 1 if e.get("side", 1) >= 0 else -1
        out.append(P("line", layer, a=p1, b=p2, lt="DASHDOT"))
        for q in (p1, p2):
            out.append(P("line", layer, a=q, b=g.add(q, g.mul(n, sd * 6 * S)), w=0.5)); out.append(_arrow(g.add(q, g.mul(n, sd * 6 * S)), g.mul(n, sd), 2.5 * S, layer))
            out.append(P("text", layer, p=g.add(q, g.mul(n, sd * 9 * S)), s=e.get("label", "A"), h=3.2 * S, rot=0, anchor="c", middle=True))
    elif k == "slope":
        p1, p2 = tuple(e["p1"]), tuple(e["p2"]); u = g.norm(g.sub(p2, p1)); out.append(P("line", layer, a=p1, b=p2)); out.append(_arrow(p2, u, 2.6 * S, layer))
        ang = g.angle_deg(p1, p2); ang = ang if -90 < ang <= 90 else ang + 180
        out.append(P("text", layer, p=g.add(g.lerp(p1, p2, 0.5), g.mul(g.perp(u), 1.2 * S)), s=e.get("text", "2%"), h=2.0 * S, rot=ang, anchor="c", baseline=True))
    elif k == "break":
        p1, p2 = tuple(e["p1"]), tuple(e["p2"]); u = g.norm(g.sub(p2, p1)); n = g.perp(u); m = g.lerp(p1, p2, 0.5); a = 2.5 * S
        out.append(P("poly", layer, pts=[p1, g.sub(m, g.mul(u, a)), g.add(g.add(m, g.mul(u, -a * 0.3)), g.mul(n, a * 1.2)), g.add(g.add(m, g.mul(u, a * 0.3)), g.mul(n, -a * 1.2)), g.add(m, g.mul(u, a)), p2], closed=False))
    elif k == "symaxis":
        p1, p2 = tuple(e["p1"]), tuple(e["p2"]); u = g.norm(g.sub(p2, p1)); n = g.perp(u); out.append(P("line", layer, a=p1, b=p2, lt="DASHDOT"))
        for q, sgn in ((p1, 1), (p2, -1)):
            for dd in (0, 1.2 * S):
                c = g.add(q, g.mul(u, sgn * dd)); hh = 2.2 * S * (1 if dd == 0 else 0.7)
                out.append(P("line", layer, a=g.add(c, g.mul(n, hh)), b=g.sub(c, g.mul(n, hh))))
    elif k == "leader":
        pts = [tuple(q) for q in e["pts"]]; out.append(P("poly", layer, pts=pts, closed=False)); out.append(_arrow(pts[0], g.norm(g.sub(pts[0], pts[1])), 2.4 * S, layer))
        end, prev = pts[-1], pts[-2]; right = end[0] >= prev[0]
        out.append(P("text", layer, p=g.add(end, (0.8 * S if right else -0.8 * S, 0.6 * S)), s=e.get("text", ""), h=2.5 * S, rot=0, anchor="l" if right else "r", baseline=True))
    elif k == "detail":
        c = tuple(e["p"]); r = 5 * S
        out.append(P("circle", layer, c=c, r=r)); out.append(P("line", layer, a=g.add(c, (-r, 0)), b=g.add(c, (r, 0))))
        out.append(P("text", layer, p=g.add(c, (0, r * 0.45)), s=str(e.get("num", "1")), h=2.6 * S, rot=0, anchor="c", middle=True))
        out.append(P("text", layer, p=g.add(c, (0, -r * 0.45)), s=str(e.get("sheet", "01")), h=2.2 * S, rot=0, anchor="c", middle=True))
    return out


# ----------------------------------------------------------------------------- frame
def frame_prims(e, project, S):
    layer = "frame"; pw, ph = PAPER[e.get("size", "A3")]
    pw, ph = (max(pw, ph), min(pw, ph)) if e.get("orient", "L") == "L" else (min(pw, ph), max(pw, ph))
    x0, y0 = e["p"]; W, H = pw * S, ph * S
    out = [P("poly", layer, pts=[(x0, y0), (x0 + W, y0), (x0 + W, y0 + H), (x0, y0 + H)], closed=True, w=0.1)]
    ml, mo = 20 * S, 10 * S; ix0, iy0, ix1, iy1 = x0 + ml, y0 + mo, x0 + W - mo, y0 + H - mo
    out.append(P("poly", layer, pts=[(ix0, iy0), (ix1, iy0), (ix1, iy1), (ix0, iy1)], closed=True, w=0.5))
    tw, th = 180 * S, 45 * S; tx1, ty0 = ix1, iy0; tx0, ty1 = tx1 - tw, ty0 + th
    out.append(P("poly", layer, pts=[(tx0, ty0), (tx1, ty0), (tx1, ty1), (tx0, ty1)], closed=True, w=0.35))
    out.append(P("line", layer, a=(tx0, ty0 + th * 0.55), b=(tx1, ty0 + th * 0.55))); out.append(P("line", layer, a=(tx0 + tw * 0.62, ty0), b=(tx0 + tw * 0.62, ty0 + th * 0.55)))
    out.append(P("line", layer, a=(tx0 + tw * 0.81, ty0), b=(tx0 + tw * 0.81, ty0 + th * 0.55))); out.append(P("line", layer, a=(tx0 + tw * 0.62, ty0 + th * 0.27), b=(tx1, ty0 + th * 0.27)))
    m = project.meta; lab = e.get("labels", {})
    T = lambda x, y, s, h: out.append(P("text", layer, p=(x, y), s=s, h=h * S, rot=0, anchor="l", baseline=True))
    T(tx0 + 2 * S, ty1 - 5 * S, lab.get("project", "PROJECT"), 1.6); T(tx0 + 2 * S, ty1 - 11 * S, m.get("name", ""), 3.5)
    T(tx0 + 2 * S, ty1 - 17 * S, f'{lab.get("client", "CLIENT")}: {m.get("client", "")}', 2.2); T(tx0 + 2 * S, ty0 + th * 0.55 - 6 * S, e.get("title", ""), 3.2)
    T(tx0 + 2 * S, ty0 + 3 * S, m.get("address", ""), 1.8)
    T(tx0 + tw * 0.62 + 2 * S, ty0 + th * 0.55 - 4.5 * S, lab.get("scale", "SCALE"), 1.5); T(tx0 + tw * 0.62 + 2 * S, ty0 + th * 0.27 + 3 * S, f"1:{project.scale}", 2.6)
    T(tx0 + tw * 0.81 + 2 * S, ty0 + th * 0.55 - 4.5 * S, lab.get("sheet", "SHEET"), 1.5); T(tx0 + tw * 0.81 + 2 * S, ty0 + th * 0.27 + 3 * S, str(m.get("sheet", "")), 2.6)
    T(tx0 + tw * 0.62 + 2 * S, ty0 + th * 0.27 - 4.5 * S, lab.get("date", "DATE"), 1.5); T(tx0 + tw * 0.62 + 2 * S, ty0 + 3 * S, str(m.get("date", "")), 2.2)
    T(tx0 + tw * 0.81 + 2 * S, ty0 + th * 0.27 - 4.5 * S, lab.get("rev", "REV."), 1.5); T(tx0 + tw * 0.81 + 2 * S, ty0 + 3 * S, str(m.get("revision", "")), 2.2)
    T(tx0 + tw * 0.62 + 2 * S, ty0 + th - 4.5 * S, lab.get("author", "DRAWN BY"), 1.5); T(tx0 + tw * 0.62 + 2 * S, ty0 + th - 10 * S, m.get("author", ""), 2.2)
    return out


# ----------------------------------------------------------------------------- misc
def room_poly(e):
    p = Polygon([tuple(q) for q in e["pts"]]); return p if p.is_valid else p.buffer(0)
def room_area_m2(e): return room_poly(e).area / 1e6
def room_perimeter_m(e): return room_poly(e).length / 1000.0


def furn_prims(e):
    sx, sy = e.get("sx", e.get("s", 1.0)), e.get("sy", e.get("s", 1.0)); c = tuple(e["c"]); a = e.get("rot", 0)
    f = lambda q: g.add(g.rot((q[0] * sx, q[1] * sy), a), c); out = []
    for p in local_prims(e["block"]):
        q = dict(p); q["layer"] = "furn"
        if q["t"] == "line": q["a"], q["b"] = f(q["a"]), f(q["b"])
        elif q["t"] == "poly": q["pts"] = [f(x) for x in q["pts"]]
        elif q["t"] == "circle": q["c"] = f(q["c"]); q["r"] = q["r"] * (sx + sy) / 2
        out.append(q)
    return out


def render(project, with_underlay=True):
    S = float(project.scale); out = []; vis = lambda key: project.layer_state[key]["visible"]
    if with_underlay and vis("under"):
        for u in project.underlay: q = dict(u); q["layer"] = "under"; out.append(q)
    fillmode = project.settings.get("wall_fill", "solid"); wu = wall_union(project)
    if wu is not None:
        for poly in _polys(wu):
            out += _poly_prims(poly, "wall", fill="#3a3a3a" if fillmode == "solid" else None)
            if fillmode == "hatch": out += hatch_prims(list(poly.exterior.coords)[:-1], "diag", 1.2 * S, 0, "wall")
    walls = {e["id"]: e for e in project.of_type("wall")}
    tag = lambda prims, eid: [dict(p, eid=eid) for p in prims]
    for e in project.entities:
        if not project.visible(e): continue
        t = e["type"]
        if t == "axis":
            out.append(P("line", "axis", a=tuple(e["p1"]), b=tuple(e["p2"]), lt="DASHDOT", eid=e["id"]))
            if e.get("label"):
                u = g.norm(g.sub(tuple(e["p2"]), tuple(e["p1"]))); c = g.sub(tuple(e["p1"]), g.mul(u, 4 * S))
                out += sym_prims({"kind": "bubble", "p": c, "label": e["label"]}, project, S)
        elif t == "column": out += _poly_prims(column_poly(e), "col", fill="#3a3a3a" if fillmode != "none" else None, eid=e["id"])
        elif t == "opening":
            w = walls.get(e.get("wall"))
            if w: out += tag(opening_prims(e, w, S), e["id"])
        elif t == "stair": out += tag(stair_prims(e, S), e["id"])
        elif t == "furn": out += tag(furn_prims(e), e["id"])
        elif t == "room":
            poly = room_poly(e)
            if not poly.is_empty and e.get("label", True):
                c = poly.representative_point()
                out.append(P("text", "room", p=(c.x, c.y + 1.6 * S), s=e.get("name", ""), h=2.8 * S, rot=0, anchor="c", middle=True, eid=e["id"]))
                out.append(P("text", "room", p=(c.x, c.y - 2.4 * S), s=f"{poly.area/1e6:.2f} m²", h=2.2 * S, rot=0, anchor="c", middle=True, eid=e["id"]))
        elif t == "dim": out += tag(dim_prims(e, project, S), e["id"])
        elif t == "text": out.append(P("text", "text", p=tuple(e["p"]), s=e["s"], h=e.get("h", 3.0) * S, rot=e.get("rot", 0), anchor=e.get("anchor", "l"), eid=e["id"]))
        elif t == "sym": out += tag(sym_prims(e, project, S), e["id"])
        elif t == "hatch":
            out += tag(hatch_prims([tuple(q) for q in e["pts"]], e.get("pattern", "diag"), e.get("sp", 1.5) * S, e.get("angle", 0), "hatch"), e["id"])
            out.append(P("poly", "hatch", pts=[tuple(q) for q in e["pts"]], closed=True, eid=e["id"]))
        elif t == "frame": out += tag(frame_prims(e, project, S), e["id"])
        elif t == "line": out.append(P("line", "draw", a=tuple(e["p1"]), b=tuple(e["p2"]), eid=e["id"]))
        elif t == "poly": out.append(P("poly", "draw", pts=[tuple(q) for q in e["pts"]], closed=e.get("closed", False), eid=e["id"]))
        elif t == "circle": out.append(P("circle", "draw", c=tuple(e["c"]), r=e["r"], eid=e["id"]))
        elif t == "arc": out.append(P("arc", "draw", c=tuple(e["c"]), r=e["r"], a0=e["a0"], a1=e["a1"], eid=e["id"]))
    return [p for p in out if vis(p["layer"])]


def scene_bbox(prims):
    xs, ys = [], []
    for p in prims:
        t = p["t"]
        if t == "line": xs += [p["a"][0], p["b"][0]]; ys += [p["a"][1], p["b"][1]]
        elif t in ("poly", "fill"): xs += [q[0] for q in p["pts"]]; ys += [q[1] for q in p["pts"]]
        elif t in ("circle", "arc"): xs += [p["c"][0] - p["r"], p["c"][0] + p["r"]]; ys += [p["c"][1] - p["r"], p["c"][1] + p["r"]]
        elif t == "text": xs.append(p["p"][0]); ys.append(p["p"][1])
    return (min(xs), min(ys), max(xs), max(ys)) if xs else (0, 0, 1000, 1000)


def find_area(project, pt):
    """Closed area under the point: interior hole of the wall union, or smallest closed polyline -> list of points or None."""
    Pt = Point(pt); best = None; u = wall_union(project, with_openings=False)
    if u is not None:
        for poly in _polys(u):
            for ring in poly.interiors:
                pol = Polygon(ring)
                if pol.contains(Pt) and (best is None or pol.area < best[0]): best = (pol.area, list(ring.coords)[:-1])
    for e in project.entities:
        if e["type"] == "poly" and e.get("closed") and len(e["pts"]) >= 3:
            pol = Polygon([tuple(p) for p in e["pts"]])
            if pol.is_valid and pol.contains(Pt) and (best is None or pol.area < best[0]): best = (pol.area, [tuple(p) for p in e["pts"]])
    return best[1] if best else None
