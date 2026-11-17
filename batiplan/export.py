"""Exporters: DXF (AutoCAD / BricsCAD / GstarCAD / ZWCAD compatible), PDF & PNG at true scale."""
import math
import ezdxf
from ezdxf import const
from ezdxf.enums import TextEntityAlignment as TA
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Circle, Polygon as MPoly, PathPatch
from matplotlib.path import Path
from .model import LAYERS
from .render import render, scene_bbox, PAPER

CAP = 0.72


def _align(p):
    a = p.get("anchor", "l"); mid = p.get("middle", False)
    return {("l", False): TA.BOTTOM_LEFT, ("c", False): TA.BOTTOM_CENTER, ("r", False): TA.BOTTOM_RIGHT,
            ("l", True): TA.MIDDLE_LEFT, ("c", True): TA.MIDDLE_CENTER, ("r", True): TA.MIDDLE_RIGHT}[(a, mid)]


def _rgb(hexs):
    hexs = hexs.lstrip("#"); return tuple(int(hexs[i:i + 2], 16) for i in (0, 2, 4))


def export_dxf(project, path, prims=None):
    prims = prims if prims is not None else render(project)
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 4; doc.header["$MEASUREMENT"] = 1; doc.header["$LTSCALE"] = float(project.scale)
    try: doc.styles.get("Standard").dxf.font = "arial.ttf"
    except Exception: pass
    for key, (name, fr, en, aci, scol, lw, lt) in LAYERS.items():
        if name not in doc.layers: doc.layers.add(name, color=aci, lineweight=int(lw * 100), linetype=lt if lt in doc.linetypes else "CONTINUOUS")
    msp = doc.modelspace()
    for p in prims:
        lay = LAYERS[p["layer"]][0]; at = {"layer": lay}
        if p.get("lt") and p["lt"] in doc.linetypes: at["linetype"] = p["lt"]
        if p.get("w"): at["lineweight"] = int(p["w"] * 100)
        t = p["t"]
        if t == "line": msp.add_line(p["a"], p["b"], dxfattribs=at)
        elif t == "poly":
            pts = p["pts"]
            if len(pts) >= 2: msp.add_lwpolyline(pts, close=bool(p.get("closed")), dxfattribs=at)
            if p.get("filled") and len(pts) >= 3:
                h = msp.add_hatch(color=7, dxfattribs={"layer": lay}); h.paths.add_polyline_path(pts, is_closed=True)
        elif t == "fill":
            h = msp.add_hatch(dxfattribs={"layer": lay}); h.rgb = _rgb(p.get("color", "#333333"))
            h.paths.add_polyline_path(p["pts"], is_closed=True, flags=const.BOUNDARY_PATH_EXTERNAL)
            for hole in p.get("holes", []): h.paths.add_polyline_path(hole, is_closed=True, flags=const.BOUNDARY_PATH_OUTERMOST)
        elif t == "circle": msp.add_circle(p["c"], p["r"], dxfattribs=at)
        elif t == "arc": msp.add_arc(p["c"], p["r"], p["a0"] % 360, p["a1"] % 360, dxfattribs=at)
        elif t == "text" and p["s"]:
            r = math.radians(p.get("rot", 0))
            for i, ln in enumerate(str(p["s"]).split("\n")):
                e = msp.add_text(ln, height=p["h"], rotation=p.get("rot", 0), dxfattribs=dict(at, style="Standard")); off = i * p["h"] * 1.4
                e.set_placement((p["p"][0] + off * math.sin(r), p["p"][1] - off * math.cos(r)), align=_align(p))
    doc.saveas(path); return path


def _draw_matplotlib(ax, prims, S, mono=True, hair=1.0):
    for p in prims:
        key = p["layer"]; name, fr, en, aci, scol, lw, lt = LAYERS[key]
        col = "#000000" if mono and key not in ("hatch", "furn", "under") else (scol if not mono else "#444444" if key in ("furn", "hatch") else "#9a9a9a")
        lwp = max(0.12, p.get("w", lw)) * 72 / 25.4 * hair
        ls = {"DASHDOT": (0, (10, 2, 1.5, 2)), "DASHED": (0, (4, 2))}.get(p.get("lt", lt), "-"); t = p["t"]
        if t == "line": ax.plot([p["a"][0], p["b"][0]], [p["a"][1], p["b"][1]], color=col, lw=lwp, ls=ls, solid_capstyle="butt")
        elif t == "poly":
            xs = [q[0] for q in p["pts"]]; ys = [q[1] for q in p["pts"]]
            if p.get("closed"): xs.append(xs[0]); ys.append(ys[0])
            if p.get("filled"): ax.add_patch(MPoly(p["pts"], closed=True, fc=col, ec=col, lw=lwp))
            else: ax.plot(xs, ys, color=col, lw=lwp, ls=ls, solid_joinstyle="miter")
        elif t == "fill":
            verts, codes = [], []
            for ring in [p["pts"]] + list(p.get("holes", [])):
                verts += list(ring) + [ring[0]]; codes += [Path.MOVETO] + [Path.LINETO] * (len(ring) - 1) + [Path.CLOSEPOLY]
            ax.add_patch(PathPatch(Path(verts, codes), fc=p.get("color", "#333333"), ec="none", lw=0))
        elif t == "circle": ax.add_patch(Circle(p["c"], p["r"], fill=False, ec=col, lw=lwp))
        elif t == "arc": ax.add_patch(Arc(p["c"], 2 * p["r"], 2 * p["r"], theta1=p["a0"], theta2=p["a1"], ec=col, lw=lwp))
        elif t == "text" and p["s"]:
            ax.text(p["p"][0], p["p"][1], p["s"], fontsize=(p["h"] / S) / CAP * 72 / 25.4, rotation=p.get("rot", 0), rotation_mode="anchor",
                    ha={"l": "left", "c": "center", "r": "right"}[p.get("anchor", "l")], va="center_baseline" if p.get("middle") else "baseline", color=col, family="DejaVu Sans")


def _page_for(project, prims, paper=None, orient=None):
    S = float(project.scale); frames = project.of_type("frame")
    if frames and paper is None:
        e = frames[0]; pw, ph = PAPER[e.get("size", "A3")]
        pw, ph = (max(pw, ph), min(pw, ph)) if e.get("orient", "L") == "L" else (min(pw, ph), max(pw, ph)); x0, y0 = e["p"]
        return x0, y0, pw, ph
    bx0, by0, bx1, by1 = scene_bbox(prims); mw, mh = (bx1 - bx0) / S + 20, (by1 - by0) / S + 20
    if paper:
        pw, ph = PAPER[paper]; pw, ph = (max(pw, ph), min(pw, ph)) if (orient or "L") == "L" else (min(pw, ph), max(pw, ph))
    else: pw, ph = max(mw, 50), max(mh, 50)
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    return cx - pw * S / 2, cy - ph * S / 2, pw, ph


def _make_fig(project, prims, paper, orient, mono, watermark, dpi=None):
    S = float(project.scale); x0, y0, pw, ph = _page_for(project, prims, paper, orient)
    fig = plt.figure(figsize=(pw / 25.4, ph / 25.4), dpi=dpi or 100); ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(x0, x0 + pw * S); ax.set_ylim(y0, y0 + ph * S); ax.set_aspect("equal"); ax.axis("off")
    _draw_matplotlib(ax, prims, S, mono)
    if watermark:
        ax.text(x0 + pw * S / 2, y0 + ph * S / 2, watermark, fontsize=min(pw, ph) * 0.35, color="#cc0000", alpha=0.13, ha="center", va="center", rotation=30, family="DejaVu Sans", weight="bold")
    return fig


def export_pdf(project, path, paper=None, orient=None, mono=True, watermark=None):
    fig = _make_fig(project, render(project), paper, orient, mono, watermark); fig.savefig(path, format="pdf"); plt.close(fig); return path


def export_png(project, path, dpi=150, paper=None, orient=None, mono=False, watermark=None):
    fig = _make_fig(project, render(project), paper, orient, mono, watermark, dpi); fig.savefig(path, dpi=dpi, facecolor="white"); plt.close(fig); return path
