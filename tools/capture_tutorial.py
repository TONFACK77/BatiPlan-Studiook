"""Drives the REAL application under Xvfb and records one screenshot per tutorial step (run once per language)."""
import sys, os, time, subprocess, json, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
lang = sys.argv[1]; outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
shutil.rmtree(f"/tmp/appdata_tut_{lang}", ignore_errors=True); os.environ["APPDATA"] = f"/tmp/appdata_tut_{lang}"; os.makedirs(os.environ["APPDATA"] + "/batiplan", exist_ok=True)
json.dump({"lang": lang, "unit": "mm"}, open(os.environ["APPDATA"] + "/batiplan/settings.json", "w"))
from batiplan.gui import App
from batiplan.model import Project
from batiplan.samples import build_house
from batiplan import export as EXP
from batiplan.i18n import tr
fr = lang == "fr"
app = App(geometry="1400x790+0+0"); app.update(); time.sleep(0.5); app.update()
class Ev:
    def __init__(s, x, y, st=0): s.x, s.y, s.state, s.num, s.delta = int(x), int(y), st, 1, 0
def pump(n=3):
    for _ in range(n): app.update(); time.sleep(0.12)
def shot(name):
    pump(); subprocess.run(["import", "-display", os.environ["DISPLAY"], "-window", "root", "-crop", "1400x815+0+0", "+repage", f"{outdir}/{name}.png"])
def click(pt):
    sx, sy = app.w2s(pt); app.cursor = pt; app.tool.click(app, pt, Ev(sx, sy)); pump(1)
def hover(pt): app.cursor = pt; app.preview = app.tool.preview(app, pt); app.request_redraw(); pump(2)
def view(x0, y0, x1, y1):
    app.update(); w, h = app.canvas.winfo_width(), app.canvas.winfo_height()
    app.zoom = min(w / (x1 - x0), h / (y1 - y0)) * 0.92; app.ox = (x0 + x1) / 2 - w / 2 / app.zoom; app.oy = (y0 + y1) / 2 - h / 2 / app.zoom; app.request_redraw(); pump(2)
app.prj = build_house(); app.sel = set(); app.zoom_extents(); pump(3); shot("s01_overview")
app.prj = Project(); app.prj.scale = 50; M = app.prj.meta; view(-2000, -1500, 12000, 10000)
M.update(name="Villa R+0 - Type F3" if fr else "Single-storey house - Type F3", client="M. Exemple" if fr else "Mr. Example", author="BatiPlan", address="Yaoundé" if fr else "Yaounde")
app.project_settings(); pump(5); shot("s02_settings"); app.close_dialogs(); pump(2)
app.grid_dialog(); pump(5); shot("s03_grid_dialog"); app.close_dialogs(); pump(2)
X, Y = [0, 3600, 5800, 10000], [0, 3200, 8000]
for i, x in enumerate(X): app.prj.add("axis", p1=[x, -1500], p2=[x, 9500], label=str(i + 1))
for j, y in enumerate(Y): app.prj.add("axis", p1=[-1500, y], p2=[11500, y], label="ABC"[j])
view(-2200, -2200, 12200, 10200); shot("s03_grid")
app.set_tool("rectwall"); app.set_opt("rectwall", "t", 200); app.rebuild_options(); pump(2); click((0, 0)); hover((10000, 8000)); shot("s04_walls_a"); click((10000, 8000))
app.set_tool("wall"); app.set_opt("wall", "t", 150); app.rebuild_options()
for a, b in (((0, 3200), (10000, 3200)), ((3600, 0), (3600, 3200)), ((5800, 0), (5800, 3200)), ((6200, 3200), (6200, 8000))): click(a); click(b); app.tool.finish(app)
view(-2200, -2200, 12200, 10200); shot("s04_walls")
app.set_tool("door"); app.set_opt("door", "w", 900); app.rebuild_options(); hover((1800, 3150)); shot("s05_openings_a")
for pt, w, kind, tag in (((1800, 3300), 900, "door", "M2"), ((4700, 3300), 800, "door", "M3"), ((7900, 3300), 900, "door", "M2")):
    app.set_opt("door", "w", w); app.set_opt("door", "kind", kind); app.set_opt("door", "tag", tag); click(pt)
app.set_opt("door", "w", 1000); app.set_opt("door", "kind", "door2"); app.set_opt("door", "tag", "M1"); click((3000, 7900))
app.set_opt("door", "kind", "slide"); app.set_opt("door", "w", 900); app.set_opt("door", "tag", "M4"); click((6200, 5000))
app.set_tool("window"); TAGS = {1200: "F1", 600: "F2", 1500: "F3", 1000: "F4", 2000: "F5"}
for pt, w in (((1800, -60), 1200), ((4700, -60), 600), ((7900, -60), 1500), ((10060, 1600), 1200), ((10060, 5600), 1200), ((-60, 5600), 2000), ((-60, 1600), 1200), ((1500, 8060), 1500), ((4300, 8060), 1500), ((8100, 8060), 1000)):
    app.set_opt("window", "w", w); app.set_opt("window", "tag", TAGS[w]); click(pt)
view(-1500, -1500, 11500, 9500); shot("s05_openings")
app.set_tool("room"); nm = ["Chambre 1", "Salle d'eau", "Chambre 2", "Séjour", "Cuisine"] if fr else ["Bedroom 1", "Bathroom", "Bedroom 2", "Living room", "Kitchen"]
for pt, n in zip(((1800, 1600), (4700, 1600), (7900, 1600), (3000, 5600), (8000, 5600)), nm): app.set_opt("room", "name", n); click(pt)
shot("s06_rooms")
app.set_tool("stair"); app.set_opt("stair", "kind", "L"); app.set_opt("stair", "w", 900); app.rebuild_options()
sid = app.prj.add("stair", p=[400, 4300], rot=0, kind="straight", turn="L", w=800, h=3000, n=17, g=250, up=tr("lbl_up")); hover((700, 6000)); shot("s07_stairs"); app.prj.remove([sid])
F = lambda b, x, y, r=0: app.prj.add("furn", block=b, c=[x, y], rot=r)
app.set_tool("furn"); app.rnb.select(app.p_lib); app.set_opt("furn", "block", "bed_double"); app.lib_select_block("bed_double"); app.rebuild_options()
for b, x, y, r in (("bed_double", 2300, 1750, 0), ("wardrobe", 750, 2800, 0), ("bed_double", 8900, 1700, 90), ("wardrobe", 6600, 2750, 0), ("wc", 4000, 2650, 0), ("basin", 5300, 2800, 0),
                   ("shower", 4400, 750, 0), ("sofa3", 2400, 4400, 0), ("coffee_table", 2400, 5500, 0), ("tv_unit", 2400, 7600, 180), ("dining6", 4600, 5600, 0), ("plant", 5600, 7550, 0),
                   ("fridge", 6800, 7550, 180), ("kitchen_sink", 8200, 7620, 180), ("cooker", 9500, 7600, 180)): F(b, x, y, r)
app.draw_lib_prev("bed_double"); hover((2300, 1750)); shot("s08_furniture")
for k, pat in enumerate(["concrete", "rc", "brick", "block", "earth", "insulation", "wood", "gravel", "stone", "steel"]):
    x0 = 13000; y0 = 8800 - k * 1050
    app.prj.add("hatch", pts=[[x0, y0], [x0 + 2200, y0], [x0 + 2200, y0 + 800], [x0, y0 + 800]], pattern=pat, sp=2.0, angle=0); app.prj.add("text", p=[x0 + 2500, y0 + 250], s=pat, h=2.5, rot=0, anchor="l")
app.set_tool("hatch"); app.rnb.select(app.p_lib); view(-1500, -1500, 17500, 10200); shot("s09_hatch")
app.set_tool("dimchain")
for p in ((0, 0), (3600, 0), (5800, 0), (10000, 0)): click(p)
app.tool.finish(app); app.tool.finish(app)
for a, b in zip(X[:-1], X[1:]): app.prj.add("dim", p1=[a, 0], p2=[b, 0], off=-1100)
app.prj.add("dim", p1=[0, 0], p2=[10000, 0], off=-2000)
for a, b in ((0, 3200), (3200, 8000)): app.prj.add("dim", p1=[10000, a], p2=[10000, b], off=-1100)
app.prj.add("dim", p1=[10000, 0], p2=[10000, 8000], off=-2000); app.set_tool("select"); view(-2200, -3200, 12200, 10200); shot("s10_dims")
app.prj.add("sym", kind="north", p=[12000, 9300], rot=0); app.prj.add("sym", kind="level", p=[1500, -3000], value=0.0)
app.prj.add("sym", kind="section", p1=[1000, 8900], p2=[1000, -900], label="A", side=1); app.prj.add("sym", kind="detail", p=[11700, 5200], num="1", sheet="02")
app.prj.add("text", p=[3200, -3400], s="PLAN DU REZ-DE-CHAUSSÉE" if fr else "GROUND FLOOR PLAN", h=5.0, rot=0, anchor="l")
app.set_tool("section"); view(-2200, -4200, 17500, 10200); shot("s11_annotation")
app.set_tool("frame"); app.set_opt("frame", "title", "PLAN RDC - 1/50" if fr else "GROUND FLOOR PLAN - 1/50"); app.rebuild_options(); pump(2)
click((-2200, -4600)); app.set_tool("select"); app.zoom_extents(); pump(3); shot("s12_frame")
op = next(e["id"] for e in app.prj.entities if e["type"] == "opening" and e.get("tag") == "M2")
app.sel = {op}; app.on_selection(); app.rnb.select(app.p_props); view(500, 2000, 3300, 4300); shot("s13_properties"); app.sel = set(); app.on_selection()
dup = app.prj.add("wall", pts=[[0, 0], [10000, 0]], t=200); app.check_window(); pump(5); shot("s14_check"); app.close_dialogs(); app.prj.remove([dup])
app.zoom_extents(); app.sched_window(); pump(5); shot("s15_schedules"); app.close_dialogs()
pdf = f"{outdir}/plan.pdf"; EXP.export_pdf(app.prj, pdf); subprocess.run(["pdftoppm", "-png", "-r", "70", "-singlefile", pdf, f"{outdir}/pdfpreview"])
EXP.export_dxf(app.prj, f"{outdir}/plan.dxf"); app.prj.save(f"{outdir}/plan.bpl")
app.licence_dialog(); pump(5); shot("s17_licence"); app.close_dialogs(); app.destroy(); print("done", lang)
