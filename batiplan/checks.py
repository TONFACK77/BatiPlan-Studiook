"""Drawing checks ("check & correct"): returns a list of findings; some can be auto-fixed."""
from . import geom as g
from .i18n import tr
from .render import room_poly


def run_checks(project):
    out = []
    add = lambda lvl, key, eid=None, **kw: out.append({"level": lvl, "msg": tr(key).format(**kw), "eid": eid, "key": key})
    seen = {}
    for e in project.of_type("wall"):
        pts = [tuple(p) for p in e["pts"]]
        for a, b in g.segs(pts, bool(e.get("closed"))):
            if g.dist(a, b) < 5: add("warn", "chk_zero_wall", e["id"], id=e["id"]); break
        k = tuple(pts)
        if k in seen or tuple(reversed(pts)) in seen: add("warn", "chk_dup_wall", e["id"], id=e["id"])
        seen[k] = e["id"]
        if e["t"] < 60 or e["t"] > 1000: add("info", "chk_thick", e["id"], id=e["id"], t=round(e["t"]))
    walls = {e["id"]: e for e in project.of_type("wall")}; by_wall = {}
    for o in project.of_type("opening"):
        w = walls.get(o.get("wall"))
        if not w: add("warn", "chk_orphan_open", o["id"], id=o["id"]); continue
        L = g.poly_length([tuple(p) for p in w["pts"]], bool(w.get("closed")))
        if o["pos"] - o["w"] / 2 < -1 or o["pos"] + o["w"] / 2 > L + 1: add("warn", "chk_open_out", o["id"], id=o["id"])
        by_wall.setdefault(w["id"], []).append(o)
    for ops in by_wall.values():
        ops.sort(key=lambda o: o["pos"])
        for a, b in zip(ops[:-1], ops[1:]):
            if b["pos"] - a["pos"] < (a["w"] + b["w"]) / 2 - 1: add("warn", "chk_open_overlap", b["id"], a=a["id"], b=b["id"])
    for s in project.of_type("stair"):
        r = s.get("h", 3000) / max(1, s["n"]); gd = s["g"]; bl = 2 * r + gd
        if not (600 <= bl <= 650): add("warn", "chk_blondel", s["id"], id=s["id"], bl=round(bl), r=round(r), g=round(gd))
        if r > 200 or r < 130: add("warn", "chk_riser", s["id"], id=s["id"], r=round(r))
        if s["w"] < 800: add("info", "chk_stair_w", s["id"], id=s["id"], w=round(s["w"]))
    for r in project.of_type("room"):
        p = room_poly(r)
        if p.is_empty or p.area < 1e6: add("info", "chk_small_room", r["id"], name=r.get("name", ""))
    for t in project.of_type("text"):
        if not str(t.get("s", "")).strip(): add("info", "chk_empty_text", t["id"])
    if not out: add("ok", "chk_all_ok")
    return out


def autofix(project):
    n = 0; walls = {e["id"] for e in project.of_type("wall")}
    drop = [o["id"] for o in project.of_type("opening") if o.get("wall") not in walls] + [t["id"] for t in project.of_type("text") if not str(t.get("s", "")).strip()]
    seen = set()
    for e in project.of_type("wall"):
        k = tuple(tuple(p) for p in e["pts"])
        if k in seen or tuple(reversed(k)) in seen: drop.append(e["id"])
        seen.add(k); pts = [tuple(p) for p in e["pts"]]; clean = [pts[0]]
        for q in pts[1:]:
            if g.dist(q, clean[-1]) >= 5: clean.append(q)
        if len(clean) != len(pts) and len(clean) >= 2: e["pts"] = clean; n += 1
    if drop: project.remove(drop); n += len(set(drop))
    return n
