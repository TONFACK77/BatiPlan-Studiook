"""Interactive tools (state machines). Each tool: click / preview / finish."""
import re, copy
from shapely.geometry import Polygon, LineString
from . import geom as g
from .i18n import tr
from .units import fmt_len
from .render import wall_poly, furn_prims, stair_prims, column_poly, dim_prims, sym_prims, frame_prims, opening_prims, find_area
from .hatchlib import PATTERNS
from .furniture import CATALOG
from .pick import pick, ids_in_box, entity_geom
from . import edit_ops


def inc_tag(s):
    m = re.match(r"^(.*?)(\d+)$", s or "")
    if m: return m.group(1) + str(int(m.group(2)) + 1)
    if s and len(s) == 1 and s.isalpha(): return chr(ord(s) + 1)
    return s


class Tool:
    name = "tool"; prompt = "pr_select"; options = []; needs_sel = False
    def __init__(self): self.pts = []
    def start(self, app): self.pts = []; app.last_pt = None
    def click(self, app, pt, ev=None): pass
    def preview(self, app, pt): return []
    def finish(self, app): self.pts = []; app.last_pt = None; app.preview = []; app.request_redraw()
    def key(self, app, ch): pass
    def opt(self, app, k): return app.get_opt(self.name, k)


class SelectTool(Tool):
    name = "select"; prompt = "pr_select"
    def start(self, app): super().start(app); self.drag0 = None
    def click(self, app, pt, ev=None):
        if ev is None: return
        eid = pick(app.prj, app.s2w(ev.x, ev.y), 8.0 / app.zoom); shift = bool(ev.state & 0x0001)
        if eid is not None:
            app.sel = (app.sel ^ {eid}) if shift else {eid}; self.drag0 = None
        else:
            if not shift: app.sel = set()
            self.drag0 = (ev.x, ev.y)
        app.on_selection(); app.request_redraw()
    def drag(self, app, ev):
        if self.drag0: app._box = (self.drag0[0], self.drag0[1], ev.x, ev.y); app.request_redraw()
    def release(self, app, ev):
        if self.drag0 and app._box:
            x0, y0, x1, y1 = app._box
            if abs(x1 - x0) > 4 and abs(y1 - y0) > 4:
                a, b = app.s2w(x0, y0), app.s2w(x1, y1); app.sel |= set(ids_in_box(app.prj, a[0], a[1], b[0], b[1], crossing=(x1 < x0)))
        self.drag0 = None; app._box = None; app.on_selection(); app.request_redraw()


class LineTool(Tool):
    name = "line"; prompt = "pr_line_next"
    def click(self, app, pt, ev=None):
        if self.pts: app.begin(); app.prj.add("line", p1=list(self.pts[-1]), p2=list(pt)); app.changed()
        self.pts = [pt]; app.last_pt = pt
    def preview(self, app, pt): return [{"t": "line", "a": self.pts[-1], "b": pt, "layer": "draw"}] if self.pts else []


class PolyTool(Tool):
    name = "poly"; prompt = "pr_poly_next"
    def click(self, app, pt, ev=None):
        if not self.pts or g.dist(pt, self.pts[-1]) > 1: self.pts.append(pt)
        app.last_pt = pt
    def preview(self, app, pt): return [{"t": "poly", "pts": self.pts + [pt], "closed": False, "layer": "draw"}] if self.pts else []
    def finish(self, app):
        if len(self.pts) >= 2: app.begin(); app.prj.add("poly", pts=[list(p) for p in self.pts], closed=False); app.changed()
        super().finish(app)


class RectTool(Tool):
    name = "rect"; prompt = "pr_rect_next"
    def click(self, app, pt, ev=None):
        if not self.pts: self.pts = [pt]; app.last_pt = pt; return
        a, b = self.pts[0], pt
        if abs(a[0] - b[0]) > 1 and abs(a[1] - b[1]) > 1:
            app.begin(); app.prj.add("poly", pts=[[a[0], a[1]], [b[0], a[1]], [b[0], b[1]], [a[0], b[1]]], closed=True); app.changed()
        super().finish(app)
    def preview(self, app, pt):
        if not self.pts: return []
        a = self.pts[0]; return [{"t": "poly", "pts": [a, (pt[0], a[1]), pt, (a[0], pt[1])], "closed": True, "layer": "draw"}]


class CircleTool(Tool):
    name = "circle"; prompt = "pr_circle_next"
    def click(self, app, pt, ev=None):
        if not self.pts: self.pts = [pt]; app.last_pt = pt; return
        r = g.dist(self.pts[0], pt)
        if r > 1: app.begin(); app.prj.add("circle", c=list(self.pts[0]), r=r); app.changed()
        super().finish(app)
    def preview(self, app, pt): return [{"t": "circle", "c": self.pts[0], "r": g.dist(self.pts[0], pt), "layer": "draw"}] if self.pts else []


class ArcTool(Tool):
    name = "arc"; prompt = "pr_arc_next"
    def click(self, app, pt, ev=None):
        self.pts.append(pt); app.last_pt = pt
        if len(self.pts) == 3:
            c, s, e = self.pts; r = g.dist(c, s)
            if r > 1: app.begin(); app.prj.add("arc", c=list(c), r=r, a0=g.angle_deg(c, s) % 360, a1=g.angle_deg(c, e) % 360); app.changed()
            super().finish(app)
    def preview(self, app, pt):
        if len(self.pts) == 1: return [{"t": "line", "a": self.pts[0], "b": pt, "layer": "draw"}]
        if len(self.pts) == 2:
            c, s = self.pts; return [{"t": "arc", "c": c, "r": g.dist(c, s), "a0": g.angle_deg(c, s) % 360, "a1": g.angle_deg(c, pt) % 360, "layer": "draw"}]
        return []


class AxisTool(Tool):
    name = "axis"; prompt = "pr_axis_next"; options = [("label", "o_label", "str", "1", None)]
    def click(self, app, pt, ev=None):
        if not self.pts: self.pts = [pt]; app.last_pt = pt; return
        lab = self.opt(app, "label"); app.begin(); app.prj.add("axis", p1=list(self.pts[0]), p2=list(pt), label=lab); app.changed()
        app.set_opt("axis", "label", inc_tag(lab)); app.rebuild_options(); super().finish(app)
    def preview(self, app, pt): return [{"t": "line", "a": self.pts[0], "b": pt, "layer": "axis", "lt": "DASHDOT"}] if self.pts else []


class WallTool(Tool):
    name = "wall"; prompt = "pr_wall_next"
    options = [("t", "o_thick", "len", 200, None), ("just", "o_just", "choice", "c", ["c", "l", "r"])]
    def click(self, app, pt, ev=None):
        if len(self.pts) >= 3 and g.dist(pt, self.pts[0]) < 1.0: self.create(app, self.pts, True); return
        if not self.pts or g.dist(pt, self.pts[-1]) > 1: self.pts.append(pt)
        app.last_pt = pt
    def double(self, app, ev): self.finish(app)
    def preview(self, app, pt):
        if not self.pts: return []
        gm = LineString(self.pts + [pt]).buffer(self.opt(app, "t") / 2, cap_style=2, join_style=2)
        return [{"t": "poly", "pts": list(gm.exterior.coords)[:-1], "closed": True, "layer": "wall"}] if not gm.is_empty else []
    def create(self, app, pts, closed):
        t = self.opt(app, "t"); just = self.opt(app, "just"); pts = [tuple(p) for p in pts]
        if just != "c" and not closed:
            o = LineString(pts).offset_curve((t / 2) * (1 if just == "r" else -1), join_style=2)
            if o.geom_type == "LineString" and not o.is_empty:
                oc = list(o.coords)
                if g.dist(oc[0], pts[0]) > g.dist(oc[-1], pts[0]): oc.reverse()
                pts = oc
        app.begin(); app.prj.add("wall", pts=[list(p) for p in pts], t=t, closed=closed); app.changed(); super().finish(app)
    def finish(self, app):
        if len(self.pts) >= 2: self.create(app, self.pts, False)
        else: super().finish(app)


class RectWallTool(Tool):
    name = "rectwall"; prompt = "pr_rect_next"
    options = [("t", "o_thick", "len", 200, None), ("just", "o_just_rect", "choice", "c", ["c", "i", "o"])]
    def click(self, app, pt, ev=None):
        if not self.pts: self.pts = [pt]; app.last_pt = pt; return
        pts = self.rect_pts(app, self.pts[0], pt)
        if pts: app.begin(); app.prj.add("wall", pts=[list(p) for p in pts], t=self.opt(app, "t"), closed=True); app.changed()
        super().finish(app)
    def rect_pts(self, app, a, b):
        if abs(a[0] - b[0]) < 1 or abs(a[1] - b[1]) < 1: return None
        x0, x1 = sorted([a[0], b[0]]); y0, y1 = sorted([a[1], b[1]]); t = self.opt(app, "t")
        d = {"c": 0, "i": t / 2, "o": -t / 2}[self.opt(app, "just")]; x0, y0, x1, y1 = x0 + d, y0 + d, x1 - d, y1 - d
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)] if x1 > x0 and y1 > y0 else None
    def preview(self, app, pt):
        if not self.pts: return []
        pts = self.rect_pts(app, self.pts[0], pt)
        if not pts: return []
        gm = Polygon(pts).exterior.buffer(self.opt(app, "t") / 2, join_style=2)
        return [{"t": "poly", "pts": list(gm.exterior.coords)[:-1], "closed": True, "layer": "wall"}] + [{"t": "poly", "pts": list(r.coords)[:-1], "closed": True, "layer": "wall"} for r in gm.interiors]


class ColumnTool(Tool):
    name = "column"; prompt = "pr_column"
    options = [("shape", "o_shape", "choice", "rect", ["rect", "round", "L", "T", "X"]), ("w", "o_width", "len", 300, None), ("h", "o_depth", "len", 300, None)]
    def make(self, app, pt): return {"c": list(pt), "shape": self.opt(app, "shape"), "w": self.opt(app, "w"), "h": self.opt(app, "h")}
    def click(self, app, pt, ev=None): app.begin(); app.prj.add("column", **self.make(app, pt)); app.changed()
    def preview(self, app, pt):
        gm = column_poly(self.make(app, pt)); return [{"t": "poly", "pts": list(gm.exterior.coords)[:-1], "closed": True, "layer": "col"}]


class OpeningTool(Tool):
    def locate(self, app, pt):
        best = None
        for w in app.prj.of_type("wall"):
            if not app.prj.visible(w): continue
            d, s, foot = g.project_on_poly(pt, [tuple(p) for p in w["pts"]], bool(w.get("closed")))
            if d <= w["t"] / 2 + 400 / max(app.zoom * 10, 1) and (best is None or d < best[0]): best = (d, w, s, foot)
        return best
    def build(self, app, pt):
        b = self.locate(app, pt)
        if not b: return None
        d, w, s, foot = b; ow = self.opt(app, "w"); pts = [tuple(p) for p in w["pts"]]; closed = bool(w.get("closed"))
        L = g.poly_length(pts, closed); s = min(max(s, ow / 2), max(L - ow / 2, ow / 2)); c, u = g.point_at(pts, s, closed)
        side = 1 if g.dot(g.sub(pt, c), g.perp(u)) >= 0 else -1
        e = {"wall": w["id"], "pos": s, "w": ow, "kind": self.opt(app, "kind"), "h": self.opt(app, "h"), "side": side, "hinge": self.opt(app, "hinge"), "tag": self.opt(app, "tag")}
        if any(o[0] == "sill" for o in self.options): e["sill"] = self.opt(app, "sill")
        return e
    def click(self, app, pt, ev=None):
        e = self.build(app, pt)
        if not e: app.msg(tr("msg_no_wall")); return
        app.begin(); app.prj.add("opening", **e); app.changed(); app.set_opt(self.name, "tag", inc_tag(e["tag"])); app.rebuild_options()
    def preview(self, app, pt):
        e = self.build(app, pt)
        if not e: return []
        return opening_prims(dict(e, id=0, type="opening"), app.prj.get(e["wall"]), app.prj.scale)


class DoorTool(OpeningTool):
    name = "door"; prompt = "pr_door"
    options = [("kind", "o_kind", "choice", "door", ["door", "door2", "slide"]), ("w", "o_width", "len", 900, None), ("h", "o_height", "len", 2100, None),
               ("hinge", "o_hinge", "choice", "L", ["L", "R"]), ("tag", "o_tag", "str", "M1", None)]


class WindowTool(OpeningTool):
    name = "window"; prompt = "pr_window"
    options = [("kind", "o_kind", "choice", "window", ["window", "win_param"]), ("w", "o_width", "len", 1200, None), ("h", "o_height", "len", 1200, None),
               ("sill", "o_sill", "len", 900, None), ("hinge", "o_hinge", "choice", "L", ["L", "R"]), ("tag", "o_tag", "str", "F1", None)]


class StairTool(Tool):
    name = "stair"; prompt = "pr_stair"
    options = [("kind", "o_stair_kind", "choice", "straight", ["straight", "L", "U"]), ("turn", "o_turn", "choice", "L", ["L", "R"]), ("w", "o_width", "len", 1000, None),
               ("h", "o_total_h", "len", 3000, None), ("n", "o_risers", "int", 17, None), ("g", "o_tread", "len", 250, None)]
    def make(self, app, p, rot):
        return {"p": list(p), "rot": rot, "kind": self.opt(app, "kind"), "turn": self.opt(app, "turn"), "w": self.opt(app, "w"), "h": self.opt(app, "h"), "n": self.opt(app, "n"), "g": self.opt(app, "g"), "up": tr("lbl_up")}
    def click(self, app, pt, ev=None):
        if not self.pts: self.pts = [pt]; app.last_pt = pt; return
        app.begin(); app.prj.add("stair", **self.make(app, self.pts[0], g.angle_deg(self.pts[0], pt))); app.changed(); super().finish(app)
    def preview(self, app, pt):
        return stair_prims(self.make(app, pt, 0), app.prj.scale) if not self.pts else stair_prims(self.make(app, self.pts[0], g.angle_deg(self.pts[0], pt)), app.prj.scale)


class FurnTool(Tool):
    name = "furn"; prompt = "pr_furn"
    options = [("block", "o_block", "choice", "bed_double", list(CATALOG)), ("rot", "o_rot", "num", 0, None)]
    def make(self, app, pt): return {"block": self.opt(app, "block"), "c": list(pt), "rot": self.opt(app, "rot")}
    def click(self, app, pt, ev=None):
        free = ("bed_single", "bed_double", "table_rect", "chair", "wc", "basin", "sofa3")
        if self.opt(app, "block") not in free and not app.lic_ok("furniture_all"): return
        app.begin(); app.prj.add("furn", **self.make(app, pt)); app.changed()
    def key(self, app, ch):
        if ch.lower() == "r": app.set_opt("furn", "rot", (self.opt(app, "rot") + 90) % 360); app.rebuild_options(); app.request_redraw()
    def preview(self, app, pt): return furn_prims(self.make(app, pt))


def area_at(app, pt): return find_area(app.prj, pt)


class RoomTool(Tool):
    name = "room"; prompt = "pr_room"; options = [("name", "o_name", "str", "", None)]
    def click(self, app, pt, ev=None):
        ring = area_at(app, pt)
        if not ring: app.msg(tr("msg_no_area")); return
        name = self.opt(app, "name") or tr("lbl_room_n", n=len(app.prj.of_type("room")) + 1)
        app.begin(); app.prj.add("room", pts=[list(p) for p in ring], name=name); app.changed(); app.set_opt("room", "name", ""); app.rebuild_options()


class HatchTool(Tool):
    name = "hatch"; prompt = "pr_hatch"
    options = [("pattern", "o_pattern", "choice", "concrete", PATTERNS), ("sp", "o_spacing", "num", 2.0, None), ("angle", "o_angle", "num", 0, None)]
    def click(self, app, pt, ev=None):
        if not self.pts:
            ring = area_at(app, pt)
            if ring: self.create(app, ring); return
        if not self.pts or g.dist(pt, self.pts[-1]) > 1: self.pts.append(pt)
        app.last_pt = pt
    def create(self, app, ring):
        pat = self.opt(app, "pattern")
        if pat not in ("diag", "cross", "solid", "tile") and not app.lic_ok("hatch_all"): return
        app.begin(); app.prj.add("hatch", pts=[list(p) for p in ring], pattern=pat, sp=self.opt(app, "sp"), angle=self.opt(app, "angle")); app.changed(); super().finish(app)
    def finish(self, app):
        if len(self.pts) >= 3: self.create(app, self.pts)
        else: super().finish(app)
    def preview(self, app, pt): return [{"t": "poly", "pts": self.pts + [pt], "closed": False, "layer": "hatch"}] if self.pts else []


class DimTool(Tool):
    name = "dim"; prompt = "pr_dim_1"
    def click(self, app, pt, ev=None):
        self.pts.append(pt); app.last_pt = pt
        if len(self.pts) == 3:
            p1, p2, q = self.pts; n = g.perp(g.norm(g.sub(p2, p1)))
            app.begin(); app.prj.add("dim", p1=list(p1), p2=list(p2), off=g.dot(g.sub(q, p1), n)); app.changed(); super().finish(app)
    def preview(self, app, pt):
        if len(self.pts) == 1: return [{"t": "line", "a": self.pts[0], "b": pt, "layer": "dim"}]
        if len(self.pts) == 2:
            p1, p2 = self.pts; n = g.perp(g.norm(g.sub(p2, p1))); return dim_prims({"p1": p1, "p2": p2, "off": g.dot(g.sub(pt, p1), n)}, app.prj, app.prj.scale)
        return []


class DimChainTool(Tool):
    name = "dimchain"; prompt = "pr_dimchain"
    def start(self, app): super().start(app); self.stage = 0
    def click(self, app, pt, ev=None):
        if self.stage == 0:
            if len(self.pts) >= 2 and g.dist(pt, self.pts[-1]) < 1: self.stage = 1; return
            self.pts.append(pt); app.last_pt = pt
        else: self.commit(app, pt)
    def double(self, app, ev): self.stage = 1 if len(self.pts) >= 2 else 0
    def finish(self, app):
        if self.stage == 0 and len(self.pts) >= 2: self.stage = 1; return
        self.stage = 0; super().finish(app)
    def proj(self):
        p0 = self.pts[0]; u = g.norm(g.sub(self.pts[1], p0)); P = [g.add(p0, g.mul(u, g.dot(g.sub(q, p0), u))) for q in self.pts]
        P.sort(key=lambda q: g.dot(g.sub(q, P[0]), u)); return P, u
    def commit(self, app, pt):
        P, u = self.proj(); off = g.dot(g.sub(pt, self.pts[0]), g.perp(u)); app.begin()
        for a, b in zip(P[:-1], P[1:]):
            if g.dist(a, b) > 1: app.prj.add("dim", p1=list(a), p2=list(b), off=off)
        app.changed(); self.stage = 0; super().finish(app)
    def preview(self, app, pt):
        if self.stage == 0: return [{"t": "poly", "pts": self.pts + [pt], "closed": False, "layer": "dim"}] if self.pts else []
        P, u = self.proj(); off = g.dot(g.sub(pt, self.pts[0]), g.perp(u)); out = []
        for a, b in zip(P[:-1], P[1:]):
            if g.dist(a, b) > 1: out += dim_prims({"p1": a, "p2": b, "off": off}, app.prj, app.prj.scale)
        return out


class TextTool(Tool):
    name = "text"; prompt = "pr_text"
    options = [("h", "o_text_h", "choice", "3.5", ["2.0", "2.5", "3.5", "5.0", "7.0", "10.0"]), ("rot", "o_rot", "num", 0, None)]
    def click(self, app, pt, ev=None):
        s = app.ask_text(tr("dlg_text"), "")
        if s and s.strip(): app.begin(); app.prj.add("text", p=list(pt), s=s, h=float(self.opt(app, "h")), rot=self.opt(app, "rot"), anchor="l"); app.changed()
    def preview(self, app, pt): return [{"t": "text", "p": pt, "s": "Abc", "h": float(self.opt(app, "h")) * app.prj.scale, "rot": self.opt(app, "rot"), "layer": "text"}]


class OnePointSym(Tool):
    kind = "north"
    def make(self, app, pt): return dict({"kind": self.kind, "p": list(pt)}, **self.extra_vals(app))
    def extra_vals(self, app): return {}
    def click(self, app, pt, ev=None): app.begin(); app.prj.add("sym", **self.make(app, pt)); app.changed(); self.after(app)
    def after(self, app): pass
    def preview(self, app, pt): return sym_prims(self.make(app, pt), app.prj, app.prj.scale)


class NorthTool(OnePointSym):
    name = "north"; kind = "north"; prompt = "pr_one_click"; options = [("rot", "o_rot", "num", 0, None)]
    def extra_vals(self, app): return {"rot": self.opt(app, "rot")}


class LevelTool(OnePointSym):
    name = "level"; kind = "level"; prompt = "pr_one_click"; options = [("value", "o_level", "num", 0.0, None)]
    def extra_vals(self, app): return {"value": self.opt(app, "value")}


class BubbleTool(OnePointSym):
    name = "bubble"; kind = "bubble"; prompt = "pr_one_click"; options = [("label", "o_label", "str", "A", None)]
    def extra_vals(self, app): return {"label": self.opt(app, "label")}
    def after(self, app): app.set_opt("bubble", "label", inc_tag(self.opt(app, "label"))); app.rebuild_options()


class DetailTool(OnePointSym):
    name = "detail"; kind = "detail"; prompt = "pr_one_click"; options = [("num", "o_label", "str", "1", None), ("sheet", "o_sheet", "str", "01", None)]
    def extra_vals(self, app): return {"num": self.opt(app, "num"), "sheet": self.opt(app, "sheet")}
    def after(self, app): app.set_opt("detail", "num", inc_tag(self.opt(app, "num"))); app.rebuild_options()


class TwoPointSym(Tool):
    kind = "section"; prompt = "pr_two_click"
    def extra_vals(self, app): return {}
    def click(self, app, pt, ev=None):
        if not self.pts: self.pts = [pt]; app.last_pt = pt; return
        app.begin(); app.prj.add("sym", kind=self.kind, p1=list(self.pts[0]), p2=list(pt), **self.extra_vals(app)); app.changed(); self.after(app); super().finish(app)
    def after(self, app): pass
    def preview(self, app, pt): return sym_prims(dict({"kind": self.kind, "p1": self.pts[0], "p2": pt}, **self.extra_vals(app)), app.prj, app.prj.scale) if self.pts else []


class SectionTool(TwoPointSym):
    name = "section"; kind = "section"; options = [("label", "o_label", "str", "A", None), ("side", "o_side", "choice", "1", ["1", "-1"])]
    def extra_vals(self, app): return {"label": self.opt(app, "label"), "side": int(self.opt(app, "side"))}
    def after(self, app): app.set_opt("section", "label", inc_tag(self.opt(app, "label"))); app.rebuild_options()


class SlopeTool(TwoPointSym):
    name = "slope"; kind = "slope"; options = [("text", "o_text", "str", "2%", None)]
    def extra_vals(self, app): return {"text": self.opt(app, "text")}


class BreakTool(TwoPointSym): name = "break"; kind = "break"
class SymAxisTool(TwoPointSym): name = "symaxis"; kind = "symaxis"


class LeaderTool(Tool):
    name = "leader"; prompt = "pr_leader"
    def click(self, app, pt, ev=None):
        if not self.pts or g.dist(pt, self.pts[-1]) > 1: self.pts.append(pt)
        app.last_pt = pt
    def double(self, app, ev): self.finish(app)
    def finish(self, app):
        if len(self.pts) >= 2:
            s = app.ask_text(tr("dlg_text"), "")
            if s: app.begin(); app.prj.add("sym", kind="leader", pts=[list(p) for p in self.pts], text=s); app.changed()
        super().finish(app)
    def preview(self, app, pt): return [{"t": "poly", "pts": self.pts + [pt], "closed": False, "layer": "symbol"}] if self.pts else []


class FrameTool(Tool):
    name = "frame"; prompt = "pr_frame"
    options = [("size", "o_paper", "choice", "A3", ["A4", "A3", "A2", "A1", "A0"]), ("orient", "o_orient", "choice", "L", ["L", "P"]), ("title", "o_title", "str", "", None)]
    def make(self, app, pt):
        return {"p": list(pt), "size": self.opt(app, "size"), "orient": self.opt(app, "orient"), "title": self.opt(app, "title"),
                "labels": {"project": tr("fr_project"), "client": tr("fr_client"), "scale": tr("fr_scale"), "sheet": tr("fr_sheet"), "date": tr("fr_date"), "rev": tr("fr_rev"), "author": tr("fr_author")}}
    def click(self, app, pt, ev=None): app.begin(); app.prj.add("frame", **self.make(app, pt)); app.changed()
    def preview(self, app, pt): return frame_prims(self.make(app, pt), app.prj, app.prj.scale)


class SelTransform(Tool):
    needs_sel = True
    def ids(self, app): return [i for i in app.sel if app.prj.get(i)]


class MoveTool(SelTransform):
    name = "move"; prompt = "pr_move_1"; copy = False
    def click(self, app, pt, ev=None):
        if not self.ids(app): app.msg(tr("msg_select_first")); return
        if not self.pts: self.pts = [pt]; app.last_pt = pt; return
        d = g.sub(pt, self.pts[0]); app.begin(); new = []
        for i in self.ids(app):
            e = app.prj.get(i)
            if self.copy:
                e2 = copy.deepcopy(e); e2["id"] = app.prj.next_id; app.prj.next_id += 1; app.prj.entities.append(e2); edit_ops.move(e2, d); new.append(e2["id"])
                if e["type"] == "wall":
                    for o in [x for x in app.prj.entities if x["type"] == "opening" and x.get("wall") == e["id"]]:
                        o2 = copy.deepcopy(o); o2["id"] = app.prj.next_id; app.prj.next_id += 1; o2["wall"] = e2["id"]; app.prj.entities.append(o2)
            else: edit_ops.move(e, d)
        if self.copy: app.sel = set(new)
        app.changed(); self.pts = [pt] if self.copy else []; app.last_pt = pt if self.copy else None
    def preview(self, app, pt):
        if not self.pts: return []
        d = g.sub(pt, self.pts[0]); out = []
        for i in self.ids(app):
            e = copy.deepcopy(app.prj.get(i)); edit_ops.move(e, d); gm = entity_geom(e, app.prj)
            if gm is not None and not gm.is_empty:
                for ring in app.canvas_rings(gm): out.append({"t": "poly", "pts": ring, "closed": False, "layer": "draw"})
        return out


class CopyTool(MoveTool): name = "copy"; prompt = "pr_copy_1"; copy = True


class RotateTool(SelTransform):
    name = "rotate"; prompt = "pr_rotate_1"
    def click(self, app, pt, ev=None):
        if not self.ids(app): app.msg(tr("msg_select_first")); return
        if not self.pts: self.pts = [pt]; app.last_pt = pt; return
        self.apply(app, g.angle_deg(self.pts[0], pt))
    def apply(self, app, ang):
        app.begin()
        for i in self.ids(app): edit_ops.rotate(app.prj.get(i), ang, self.pts[0])
        app.changed(); super().finish(app)
    def typed(self, app, val):
        if self.pts: self.apply(app, float(val))


class MirrorTool(SelTransform):
    name = "mirror"; prompt = "pr_mirror_1"; options = [("keep", "o_keep", "bool", True, None)]
    def click(self, app, pt, ev=None):
        if not self.ids(app): app.msg(tr("msg_select_first")); return
        if not self.pts: self.pts = [pt]; app.last_pt = pt; return
        a, b = self.pts[0], pt; app.begin()
        for i in self.ids(app):
            e = app.prj.get(i)
            if self.opt(app, "keep"):
                e2 = copy.deepcopy(e); e2["id"] = app.prj.next_id; app.prj.next_id += 1; app.prj.entities.append(e2); edit_ops.mirror(e2, a, b)
            else: edit_ops.mirror(e, a, b)
        app.changed(); super().finish(app)
    def preview(self, app, pt): return [{"t": "line", "a": self.pts[0], "b": pt, "layer": "draw", "lt": "DASHDOT"}] if self.pts else []


class EraseTool(SelTransform):
    name = "erase"; prompt = "pr_erase"
    def click(self, app, pt, ev=None):
        eid = pick(app.prj, app.s2w(ev.x, ev.y), 8.0 / app.zoom) if ev else None
        ids = self.ids(app) if not eid else [eid]
        if ids: app.begin(); app.prj.remove(ids); app.sel -= set(ids); app.changed()


class MeasureTool(Tool):
    name = "measure"; prompt = "pr_two_click"
    def click(self, app, pt, ev=None):
        if not self.pts: self.pts = [pt]; app.last_pt = pt; return
        a, b = self.pts[0], pt; u = app.prj.unit
        app.msg(tr("msg_measure", d=fmt_len(g.dist(a, b), u, True), dx=fmt_len(abs(b[0] - a[0]), u, True), dy=fmt_len(abs(b[1] - a[1]), u, True), a=f"{g.angle_deg(a, b) % 360:.1f}"), popup=True)
        super().finish(app)
    def preview(self, app, pt): return [{"t": "line", "a": self.pts[0], "b": pt, "layer": "dim"}] if self.pts else []


TOOLS = {c.name: c for c in [SelectTool, LineTool, PolyTool, RectTool, CircleTool, ArcTool, AxisTool, WallTool, RectWallTool, ColumnTool, DoorTool, WindowTool, StairTool, FurnTool,
                              RoomTool, HatchTool, DimTool, DimChainTool, TextTool, NorthTool, LevelTool, BubbleTool, DetailTool, SectionTool, SlopeTool, BreakTool, SymAxisTool,
                              LeaderTool, FrameTool, MoveTool, CopyTool, RotateTool, MirrorTool, EraseTool, MeasureTool]}
