"""Tk application shell: canvas, view, snapping, selection, drawing of primitives."""
import math, os, json, tkinter as tk
from .model import LAYERS
from .render import render, scene_bbox
from .pick import snap_points, entity_geom
from . import geom as g

CAP = 0.72


def cfg_path():
    from .license import config_dir
    return os.path.join(config_dir(), "settings.json")


def load_cfg():
    try: return json.load(open(cfg_path()))
    except Exception: return {}


def save_cfg(c):
    try: json.dump(c, open(cfg_path(), "w"))
    except Exception: pass


class CanvasMixin:
    def init_view(self):
        self.zoom, self.ox, self.oy = 0.08, -2000.0, -2000.0
        self.snap_obj, self.snap_grid, self.ortho = True, True, False
        self.grid_step = 100.0; self.cursor = (0.0, 0.0); self.snap_kind = None; self._snaps = None
        self._redraw_pending = False; self._pan = None; self._box = None
        self.sel = set(); self.last_pt = None; self.preview = []; self.show_lw = True

    def w2s(self, p): return ((p[0] - self.ox) * self.zoom, self.ch - (p[1] - self.oy) * self.zoom)
    def s2w(self, x, y): return (x / self.zoom + self.ox, (self.ch - y) / self.zoom + self.oy)

    def request_redraw(self):
        if not self._redraw_pending: self._redraw_pending = True; self.after_idle(self.redraw)

    def zoom_extents(self):
        x0, y0, x1, y1 = scene_bbox(render(self.prj)); w, h = max(x1 - x0, 1000), max(y1 - y0, 1000)
        self.update_idletasks(); self.cw, self.ch = max(self.canvas.winfo_width(), 200), max(self.canvas.winfo_height(), 200)
        self.zoom = min(self.cw / (w * 1.15), self.ch / (h * 1.15))
        self.ox = (x0 + x1) / 2 - self.cw / 2 / self.zoom; self.oy = (y0 + y1) / 2 - self.ch / 2 / self.zoom; self.request_redraw()

    def redraw(self):
        self._redraw_pending = False; c = self.canvas; c.delete("all")
        self.cw, self.ch = c.winfo_width(), c.winfo_height(); self._snaps = None
        self.draw_grid(); self.draw_prims(render(self.prj))
        for eid in self.sel:
            e = self.prj.get(eid); gm = entity_geom(e, self.prj) if e else None
            if gm is not None and not gm.is_empty:
                for ring in self._rings(gm):
                    pts = [coord for p in ring for coord in self.w2s(p)]
                    if len(pts) >= 4: c.create_line(*pts, fill="#ff7f00", width=2, dash=(4, 2))
        if self.preview: self.draw_prims(self.preview, override="#0078d7", dash=(3, 2))
        if self._box:
            x0, y0, x1, y1 = self._box; c.create_rectangle(x0, y0, x1, y1, outline="#0078d7" if x1 >= x0 else "#1e8449", dash=(3, 3), fill="")
        self.draw_snap_marker(); self.update_status()

    @staticmethod
    def _rings(gm):
        if gm.geom_type == "Polygon": return [list(gm.exterior.coords)] + [list(r.coords) for r in gm.interiors]
        if gm.geom_type in ("LineString", "LinearRing"): return [list(gm.coords)]
        if hasattr(gm, "geoms"): return [r for s in gm.geoms for r in CanvasMixin._rings(s)]
        return []

    def draw_grid(self):
        c = self.canvas
        if not self.snap_grid_visible: return
        step = self.grid_step
        while step * self.zoom < 14: step *= 5
        x0, y0 = self.s2w(0, self.ch); x1, y1 = self.s2w(self.cw, 0)
        i0, i1, j0, j1 = int(x0 // step), int(x1 // step) + 1, int(y0 // step), int(y1 // step) + 1
        if (i1 - i0) * (j1 - j0) > 9000: return
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                sx, sy = self.w2s((i * step, j * step)); c.create_line(sx, sy, sx + 1, sy, fill="#c8c8c8" if (i % 5 or j % 5) else "#8a8a8a")
        ax, ay = self.w2s((0, 0)); c.create_line(ax - 10, ay, ax + 10, ay, fill="#d35400"); c.create_line(ax, ay - 10, ax, ay + 10, fill="#d35400")

    def draw_prims(self, prims, override=None, dash=None):
        c = self.canvas; z = self.zoom
        for p in prims:
            key = p["layer"]; col = override or p.get("scol") or LAYERS[key][4]; lw = p.get("w", LAYERS[key][5])
            wpx = max(1, min(4, round(lw * 4 * min(1.0, z * 40 + 0.4)))) if self.show_lw else 1
            ds = dash or ((6, 3, 1, 3) if p.get("lt") == "DASHDOT" else (4, 3) if p.get("lt") == "DASHED" else None); t = p["t"]
            if t == "line":
                x0, y0 = self.w2s(p["a"]); x1, y1 = self.w2s(p["b"]); c.create_line(x0, y0, x1, y1, fill=col, width=wpx, dash=ds)
            elif t == "poly":
                pts = [v for q in p["pts"] for v in self.w2s(q)]
                if len(pts) < 4: continue
                if p.get("closed"):
                    if p.get("filled"): c.create_polygon(*pts, fill=col, outline=col)
                    else: c.create_line(*(pts + pts[:2]), fill=col, width=wpx, dash=ds)
                else: c.create_line(*pts, fill=col, width=wpx, dash=ds)
            elif t == "fill":
                if override: continue
                pts = [v for q in p["pts"] for v in self.w2s(q)]
                if len(pts) >= 6: c.create_polygon(*pts, fill=p.get("color", "#333"), outline="")
                for h in p.get("holes", []):
                    hp = [v for q in h for v in self.w2s(q)]
                    if len(hp) >= 6: c.create_polygon(*hp, fill="white", outline="")
            elif t == "circle":
                cx, cy = self.w2s(p["c"]); r = p["r"] * z; c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=col, width=wpx, dash=ds)
            elif t == "arc":
                c.create_line(*[v for q in g.arc_pts(p["c"], p["r"], p["a0"], p["a1"]) for v in self.w2s(q)], fill=col, width=wpx)
            elif t == "text" and p["s"]:
                px = p["h"] * z / CAP
                if px < 4: continue
                x, y = self.w2s(p["p"]); a = p.get("anchor", "l"); mid = p.get("middle", False)
                anc = {("l", False): "sw", ("c", False): "s", ("r", False): "se", ("l", True): "w", ("c", True): "center", ("r", True): "e"}[(a, mid)]
                c.create_text(x, y, text=p["s"], fill=col, anchor=anc, angle=p.get("rot", 0), font=("DejaVu Sans", -int(max(px * 0.85, 5))))

    def snap(self, wp, raw=False):
        tol = 10.0 / self.zoom; kind = None; best = None
        if self.snap_obj and not raw:
            if self._snaps is None: self._snaps = snap_points(self.prj)
            for x, y, k in self._snaps:
                d = math.hypot(x - wp[0], y - wp[1])
                if d < tol and (best is None or d < best[0]): best = (d, (x, y), k)
        if best: pt, kind = best[1], best[2]
        elif self.snap_grid and not raw:
            s = self.grid_step; gp = (round(wp[0] / s) * s, round(wp[1] / s) * s)
            pt, kind = (gp, "grid") if math.hypot(gp[0] - wp[0], gp[1] - wp[1]) < tol * 1.5 else (wp, None)
        else: pt = wp
        if self.ortho and self.last_pt is not None and kind not in ("end", "mid", "center"):
            dx, dy = pt[0] - self.last_pt[0], pt[1] - self.last_pt[1]
            pt = (pt[0], self.last_pt[1]) if abs(dx) >= abs(dy) else (self.last_pt[0], pt[1])
        return pt, kind

    def draw_snap_marker(self):
        if not self.snap_kind: return
        x, y = self.w2s(self.cursor); c = self.canvas; k = self.snap_kind
        if k == "end": c.create_rectangle(x - 5, y - 5, x + 5, y + 5, outline="#d81b60", width=2)
        elif k == "mid": c.create_polygon(x, y - 6, x - 6, y + 5, x + 6, y + 5, outline="#d81b60", fill="", width=2)
        elif k == "center": c.create_oval(x - 5, y - 5, x + 5, y + 5, outline="#d81b60", width=2)
        elif k == "grid": c.create_line(x - 4, y, x + 4, y, fill="#d81b60"); c.create_line(x, y - 4, x, y + 4, fill="#d81b60")

    def bind_canvas(self):
        c = self.canvas
        c.bind("<Motion>", self.on_motion); c.bind("<Button-1>", self.on_click); c.bind("<B1-Motion>", self.on_drag); c.bind("<ButtonRelease-1>", self.on_release)
        c.bind("<Double-Button-1>", self.on_double); c.bind("<Button-3>", self.on_right); c.bind("<ButtonPress-2>", self.pan_start); c.bind("<B2-Motion>", self.pan_move)
        c.bind("<MouseWheel>", self.on_wheel); c.bind("<Button-4>", self.on_wheel); c.bind("<Button-5>", self.on_wheel)
        c.bind("<Configure>", lambda e: self.request_redraw()); c.bind("<Enter>", lambda e: c.focus_set())

    def on_wheel(self, ev):
        f = 1.25 if (ev.num == 4 or getattr(ev, "delta", 0) > 0) else 0.8; wp = self.s2w(ev.x, ev.y); self.zoom *= f
        self.ox = wp[0] - ev.x / self.zoom; self.oy = wp[1] - (self.ch - ev.y) / self.zoom; self.request_redraw()

    def pan_start(self, ev): self._pan = (ev.x, ev.y, self.ox, self.oy)
    def pan_move(self, ev):
        if self._pan: x, y, ox, oy = self._pan; self.ox = ox - (ev.x - x) / self.zoom; self.oy = oy + (ev.y - y) / self.zoom; self.request_redraw()

    def pointer(self, ev):
        pt, kind = self.snap(self.s2w(ev.x, ev.y)); self.cursor, self.snap_kind = pt, kind; return pt

    def on_motion(self, ev):
        pt = self.pointer(ev); self.preview = self.tool.preview(self, pt) if self.tool else []; self.request_redraw()

    def on_click(self, ev):
        self.canvas.focus_set(); pt = self.pointer(ev)
        if self.tool: self.tool.click(self, pt, ev)

    def on_drag(self, ev):
        if self.tool and hasattr(self.tool, "drag"): self.tool.drag(self, ev)
    def on_release(self, ev):
        if self.tool and hasattr(self.tool, "release"): self.tool.release(self, ev)
    def on_double(self, ev):
        if self.tool and hasattr(self.tool, "double"): self.tool.double(self, ev)
    def on_right(self, ev):
        if self.tool: self.tool.finish(self)
