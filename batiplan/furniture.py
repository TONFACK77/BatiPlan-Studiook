"""Original parametric furniture / fixtures library (plan symbols, local frame centred on 0,0)."""
import math

CATALOG = {  # key: (fr, en, W, D)
    "bed_single": ("Lit 1 place", "Single bed", 900, 2000), "bed_double": ("Lit 2 places", "Double bed", 1600, 2000),
    "sofa2": ("Canapé 2 places", "Sofa 2-seat", 1600, 900), "sofa3": ("Canapé 3 places", "Sofa 3-seat", 2100, 900),
    "armchair": ("Fauteuil", "Armchair", 800, 800), "table_rect": ("Table rectangulaire", "Rectangular table", 1600, 900),
    "table_round": ("Table ronde", "Round table", 1000, 1000), "dining6": ("Table à manger + 6 chaises", "Dining table + 6 chairs", 1800, 1500),
    "chair": ("Chaise", "Chair", 450, 450), "desk": ("Bureau + chaise", "Desk + chair", 1400, 1100), "wardrobe": ("Armoire / placard", "Wardrobe", 1200, 600),
    "tv_unit": ("Meuble TV", "TV unit", 1500, 400), "coffee_table": ("Table basse", "Coffee table", 1000, 500), "wc": ("WC", "Toilet", 400, 700),
    "basin": ("Lavabo", "Washbasin", 600, 450), "bathtub": ("Baignoire", "Bathtub", 1700, 750), "shower": ("Douche", "Shower", 900, 900),
    "kitchen_sink": ("Évier cuisine 2 bacs", "Kitchen sink", 1200, 600), "cooker": ("Cuisinière 4 feux", "Cooker 4-burner", 600, 600),
    "fridge": ("Réfrigérateur", "Fridge", 600, 650), "washer": ("Lave-linge", "Washing machine", 600, 600), "plant": ("Plante", "Plant", 500, 500),
    "car": ("Voiture", "Car", 4500, 1800),
}


def _rect(x0, y0, x1, y1): return {"t": "poly", "pts": [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "closed": True}
def _line(a, b): return {"t": "line", "a": a, "b": b}
def _circ(c, r): return {"t": "circle", "c": c, "r": r}
def _ell(c, rx, ry, n=28): return {"t": "poly", "pts": [(c[0] + rx * math.cos(2 * math.pi * i / n), c[1] + ry * math.sin(2 * math.pi * i / n)) for i in range(n)], "closed": True}


def _xf(p, dx, dy, rot):
    r = math.radians(rot); c, s = math.cos(r), math.sin(r)
    f = lambda q: (q[0] * c - q[1] * s + dx, q[0] * s + q[1] * c + dy)
    q = dict(p)
    for k in ("a", "b", "c"):
        if k in q: q[k] = f(q[k])
    if "pts" in q: q["pts"] = [f(x) for x in q["pts"]]
    return q


def _chair(cx, cy, s=450, rot=0):
    h = s / 2
    return [_xf(p, cx, cy, rot) for p in (_rect(-h, -h, h, h), _line((-h, h * 0.7), (h, h * 0.7)))]


def build(name):
    W, D = CATALOG[name][2], CATALOG[name][3]; w, d = W / 2, D / 2
    out = [_rect(-w, -d, w, d)]
    if name == "bed_single": out += [_rect(-w + 80, d - 480, w - 80, d - 60), _line((-w, d - 600), (w, d - 600))]
    elif name == "bed_double": out += [_rect(-w + 80, d - 480, -40, d - 60), _rect(40, d - 480, w - 80, d - 60), _line((-w, d - 600), (w, d - 600))]
    elif name in ("sofa2", "sofa3"):
        n = 2 if name == "sofa2" else 3
        out += [_rect(-w, d - 200, w, d), _rect(-w, -d, -w + 180, d - 200), _rect(w - 180, -d, w, d - 200)]
        seat = (W - 360) / n
        for i in range(1, n): out.append(_line((-w + 180 + seat * i, -d), (-w + 180 + seat * i, d - 200)))
    elif name == "armchair": out += [_rect(-w, d - 180, w, d), _rect(-w, -d, -w + 160, d - 180), _rect(w - 160, -d, w, d - 180)]
    elif name == "table_rect": out += [_rect(-w + 60, -d + 60, w - 60, d - 60)]
    elif name == "table_round": out = [_circ((0, 0), w), _circ((0, 0), w - 60)]
    elif name == "dining6":
        out = [_rect(-900, -450, 900, 450)]
        for x in (-600, 0, 600): out += _chair(x, 700, 450, 0) + _chair(x, -700, 450, 180)
    elif name == "chair": out = _chair(0, 0, 450)
    elif name == "desk": out = [_rect(-700, 100, 700, 550), _rect(-700, 100, -400, 550), _line((-400, 100), (-400, 550))] + _chair(0, -150, 450, 180)
    elif name == "wardrobe": out += [_line((-w, -d), (w, d)), _line((-w, d), (w, -d))]
    elif name == "tv_unit": out += [_rect(-250, -d + 60, 250, d - 60)]
    elif name == "coffee_table": out = [_rect(-w, -d, w, d), _rect(-w + 40, -d + 40, w - 40, d - 40)]
    elif name == "wc": out = [_rect(-w, d - 200, w, d), _ell((0, -40), 180, 270), _ell((0, -40), 130, 215)]
    elif name == "basin": out += [_ell((0, 0), w - 90, d - 70), _circ((0, 0), 25)]
    elif name == "bathtub": out += [_rect(-w + 70, -d + 70, w - 70, d - 70), _ell((-w + 260, 0), 90, 60), _circ((-w + 260, 0), 20)]
    elif name == "shower": out += [_line((-w, -d), (w, d)), _circ((0, 0), 45)]
    elif name == "kitchen_sink": out += [_rect(-w + 60, -d + 80, -20, d - 80), _rect(20, -d + 80, w - 60, d - 80), _circ((0, d - 40), 20)]
    elif name == "cooker":
        for sx in (-1, 1):
            for sy in (-1, 1): out.append(_circ((sx * 150, sy * 150), 80 if sx * sy > 0 else 60))
    elif name == "fridge": out += [_line((-w, d - 180), (w, d - 180)), _line((-w + 80, d - 40), (-w + 80, d - 140))]
    elif name == "washer": out = [_rect(-w, -d, w, d), _circ((0, 0), 210), _circ((0, 0), 150), _rect(-w + 40, d - 80, w - 40, d - 30)]
    elif name == "plant": out = [_circ((0, 0), w)] + [_line((0, 0), (w * math.cos(math.radians(a)), w * math.sin(math.radians(a)))) for a in range(0, 360, 45)]
    elif name == "car":
        out = [_rect(-w, -d, w, d), _rect(-w + 900, -d + 150, w - 700, d - 150), _rect(w - 600, -d + 100, w - 80, d - 100),
               _rect(-w + 80, -d + 80, -w + 280, -d + 360), _rect(-w + 80, d - 360, -w + 280, d - 80)]
    return out


def local_prims(name): return build(name)
