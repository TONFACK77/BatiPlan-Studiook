"""Ready-made sample projects (used for tests, the tutorial and the 'samples' folder)."""
from .model import Project
from .render import find_area


def _room(p, pt, name):
    ring = find_area(p, pt)
    if ring: p.add("room", pts=[list(q) for q in ring], name=name)


def build_house(unit="mm", lang_fr=True):
    p = Project(); p.unit = unit; p.scale = 50
    p.meta.update(name="Villa R+0 - Type F3" if lang_fr else "Single-storey house - Type F3", client="M. Exemple" if lang_fr else "Mr. Example",
                  author="BatiPlan", date="2026-01-15", address="Yaoundé" if lang_fr else "Yaounde", sheet="01", revision="A")
    X, Y = [0, 3600, 5800, 10000], [0, 3200, 8000]
    for i, x in enumerate(X): p.add("axis", p1=[x, -1500], p2=[x, 9500], label=str(i + 1))
    for j, y in enumerate(Y): p.add("axis", p1=[-1500, y], p2=[11500, y], label="ABC"[j])
    ext = p.add("wall", pts=[[0, 0], [10000, 0], [10000, 8000], [0, 8000]], t=200, closed=True)
    h1 = p.add("wall", pts=[[0, 3200], [10000, 3200]], t=150); p.add("wall", pts=[[3600, 0], [3600, 3200]], t=150); p.add("wall", pts=[[5800, 0], [5800, 3200]], t=150)
    v3 = p.add("wall", pts=[[6200, 3200], [6200, 8000]], t=150)
    D = lambda w, pos, wd, tag, kind="door", side=1, hinge="L": p.add("opening", wall=w, pos=pos, w=wd, kind=kind, h=2100, side=side, hinge=hinge, tag=tag)
    Wn = lambda w, pos, wd, tag: p.add("opening", wall=w, pos=pos, w=wd, kind="window", h=1200, sill=900, tag=tag)
    D(ext, 25000, 1000, "M1", "door2", 1, "L"); D(h1, 1800, 900, "M2", "door", -1, "L"); D(h1, 4700, 800, "M3", "door", -1, "R"); D(h1, 7900, 900, "M2", "door", -1, "L"); D(v3, 2400, 900, "M4", "slide", 1)
    Wn(ext, 1800, 1200, "F1"); Wn(ext, 4700, 600, "F2"); Wn(ext, 7900, 1500, "F3"); Wn(ext, 11600, 1200, "F1"); Wn(ext, 15600, 1200, "F1")
    Wn(ext, 19900, 1000, "F4"); Wn(ext, 23700, 1500, "F3"); Wn(ext, 26500, 1500, "F3"); Wn(ext, 30400, 2000, "F5"); Wn(ext, 34400, 1200, "F1")
    p.add("column", c=[5000, 6200], w=300, h=300, shape="round")
    names = [("Chambre 1", "Bedroom 1"), ("Salle d'eau", "Bathroom"), ("Chambre 2", "Bedroom 2"), ("Séjour", "Living room"), ("Cuisine", "Kitchen")]; i = 0 if lang_fr else 1
    for pt, nm in zip(((1800, 1600), (4700, 1600), (7900, 1600), (3000, 5600), (8000, 5600)), names): _room(p, pt, nm[i])
    F = lambda b, x, y, r=0: p.add("furn", block=b, c=[x, y], rot=r)
    F("bed_double", 2300, 1750); F("wardrobe", 750, 2800); F("bed_double", 8900, 1700, 90); F("wardrobe", 6600, 2750); F("wc", 4000, 2650); F("basin", 5300, 2800); F("shower", 4400, 750)
    F("sofa3", 2400, 4400); F("coffee_table", 2400, 5500); F("tv_unit", 2400, 7600, 180); F("dining6", 4600, 5600); F("plant", 5600, 7550)
    F("fridge", 6800, 7550, 180); F("kitchen_sink", 8200, 7620, 180); F("cooker", 9500, 7600, 180)
    for a, b in zip(X[:-1], X[1:]): p.add("dim", p1=[a, 0], p2=[b, 0], off=-1100)
    p.add("dim", p1=[0, 0], p2=[10000, 0], off=-2000)
    for a, b in ((0, 3200), (3200, 8000)): p.add("dim", p1=[10000, a], p2=[10000, b], off=-1100)
    p.add("dim", p1=[10000, 0], p2=[10000, 8000], off=-2000)
    p.add("sym", kind="north", p=[12000, 9300], rot=0); p.add("sym", kind="level", p=[1500, -3000], value=0.0); p.add("sym", kind="section", p1=[1000, 8900], p2=[1000, -900], label="A", side=1)
    p.add("sym", kind="detail", p=[11700, 5200], num="1", sheet="02")
    p.add("text", p=[3200, -3400], s="PLAN DU REZ-DE-CHAUSSÉE" if lang_fr else "GROUND FLOOR PLAN", h=5.0, rot=0, anchor="l")
    for k, pat in enumerate(["concrete", "rc", "brick", "block", "earth", "insulation", "wood", "gravel", "stone", "steel"]):
        x0 = 13000; y0 = 8800 - k * 1050
        p.add("hatch", pts=[[x0, y0], [x0 + 2200, y0], [x0 + 2200, y0 + 800], [x0, y0 + 800]], pattern=pat, sp=2.0, angle=0); p.add("text", p=[x0 + 2500, y0 + 250], s=pat, h=2.5, rot=0, anchor="l")
    p.add("frame", p=[-2200, -4600], size="A3", orient="L", title="PLAN RDC - 1/50" if lang_fr else "GROUND FLOOR PLAN - 1/50",
          labels={"project": "PROJET" if lang_fr else "PROJECT", "client": "CLIENT", "scale": "ÉCHELLE" if lang_fr else "SCALE", "sheet": "PLANCHE" if lang_fr else "SHEET",
                  "date": "DATE", "rev": "INDICE" if lang_fr else "REV.", "author": "DESSINÉ PAR" if lang_fr else "DRAWN BY"})
    p.dirty = False; return p


def build_stairs():
    p = Project(); p.scale = 50; p.meta.update(name="Escaliers - démonstration")
    for kind, x in (("straight", 0), ("L", 6000), ("U", 12500)): p.add("stair", p=[x, 0], rot=0, kind=kind, turn="L", w=1000, h=3000, n=17, g=250, up="MONTE")
    return p
