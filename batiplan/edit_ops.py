"""Modify operations on entity dicts: move / rotate / mirror (in place)."""
from . import geom as g

PT_KEYS = {"axis": ("p1", "p2"), "line": ("p1", "p2"), "dim": ("p1", "p2"), "circle": ("c",), "arc": ("c",), "column": ("c",), "furn": ("c",), "stair": ("p",), "text": ("p",), "frame": ("p",)}
LIST_KEYS = {"wall": "pts", "poly": "pts", "room": "pts", "hatch": "pts"}


def _map_points(e, fn):
    t = e["type"]
    if t in PT_KEYS:
        for k in PT_KEYS[t]: e[k] = list(fn(tuple(e[k])))
    if t in LIST_KEYS: e[LIST_KEYS[t]] = [list(fn(tuple(p))) for p in e[LIST_KEYS[t]]]
    if t == "sym":
        for k in ("p", "p1", "p2"):
            if k in e: e[k] = list(fn(tuple(e[k])))
        if "pts" in e: e["pts"] = [list(fn(tuple(p))) for p in e["pts"]]


def move(e, d):
    if e["type"] == "opening": return
    _map_points(e, lambda p: (p[0] + d[0], p[1] + d[1]))


def rotate(e, ang, c):
    if e["type"] == "opening": return
    _map_points(e, lambda p: g.rot(p, ang, c))
    if e["type"] in ("column", "furn", "stair", "text") or (e["type"] == "sym" and e.get("kind") == "north"): e["rot"] = (e.get("rot", 0) + ang) % 360
    if e["type"] == "arc": e["a0"] = (e["a0"] + ang) % 360; e["a1"] = (e["a1"] + ang) % 360


def mirror(e, a, b):
    if e["type"] == "opening": e["side"] = -e.get("side", 1); return
    def fn(p):
        ab = g.sub(b, a); t = g.dot(g.sub(p, a), ab) / g.dot(ab, ab); foot = g.add(a, g.mul(ab, t)); return g.sub(g.mul(foot, 2), p)
    _map_points(e, fn); ang = g.angle_deg(a, b)
    if e["type"] in ("column", "furn", "stair", "text"): e["rot"] = (2 * ang - e.get("rot", 0)) % 360
    if e["type"] == "stair": e["turn"] = "R" if e.get("turn", "L") == "L" else "L"
    if e["type"] == "arc": a0, a1 = e["a0"], e["a1"]; e["a0"], e["a1"] = (2 * ang - a1) % 360, (2 * ang - a0) % 360
