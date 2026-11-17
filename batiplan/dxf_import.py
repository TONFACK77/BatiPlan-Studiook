"""Import a DXF as a grey underlay (trace over existing plans). Reads LINE, LWPOLYLINE, POLYLINE, ARC, CIRCLE, TEXT, INSERT."""
import ezdxf
from ezdxf import recover

SCALE = {0: 1.0, 1: 25.4, 2: 304.8, 4: 1.0, 5: 10.0, 6: 1000.0}


def read_underlay(path):
    try: doc = ezdxf.readfile(path)
    except Exception: doc, _ = recover.readfile(path)
    k = SCALE.get(int(doc.header.get("$INSUNITS", 4) or 4), 1.0); prims = []; f = lambda p: (p[0] * k, p[1] * k)

    def walk(ents, depth=0):
        for e in ents:
            t = e.dxftype()
            try:
                if t == "LINE": prims.append({"t": "line", "a": f(e.dxf.start), "b": f(e.dxf.end)})
                elif t == "LWPOLYLINE":
                    pts = [f(p[:2]) for p in e.get_points()]
                    if len(pts) >= 2: prims.append({"t": "poly", "pts": pts, "closed": bool(e.closed)})
                elif t == "POLYLINE":
                    pts = [f(v.dxf.location) for v in e.vertices]
                    if len(pts) >= 2: prims.append({"t": "poly", "pts": pts, "closed": bool(e.is_closed)})
                elif t == "CIRCLE": prims.append({"t": "circle", "c": f(e.dxf.center), "r": e.dxf.radius * k})
                elif t == "ARC": prims.append({"t": "arc", "c": f(e.dxf.center), "r": e.dxf.radius * k, "a0": e.dxf.start_angle, "a1": e.dxf.end_angle})
                elif t in ("TEXT", "MTEXT"):
                    s = e.dxf.text if t == "TEXT" else e.plain_text(); h = (e.dxf.height if t == "TEXT" else e.dxf.char_height) * k
                    prims.append({"t": "text", "p": f(e.dxf.insert), "s": s, "h": h, "rot": getattr(e.dxf, "rotation", 0) or 0, "anchor": "l"})
                elif t == "INSERT" and depth < 3: walk(e.virtual_entities(), depth + 1)
            except Exception: continue
    walk(doc.modelspace()); return prims
