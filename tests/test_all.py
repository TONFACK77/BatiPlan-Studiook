"""Run:  python tests/test_all.py   (no pytest needed). Exit code 0 = everything OK."""
import os, sys, re, glob, tempfile, datetime, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, ROOT)
os.environ["APPDATA"] = tempfile.mkdtemp()
import ezdxf, openpyxl
from batiplan import license as L, export as EXP, schedule as SCH, checks as CHK
from batiplan.model import Project
from batiplan.samples import build_house
from batiplan.render import render, wall_union
from batiplan.i18n import tr, set_lang
from batiplan.i18n_data import DATA
from batiplan.units import parse_len, fmt_len
from batiplan.furniture import CATALOG
from batiplan.hatchlib import PATTERNS

ok = 0
def check(cond, label):
    global ok
    if not cond: print("FAIL:", label); sys.exit(1)
    ok += 1; print("ok  ", label)

check(abs(parse_len("2,5", "m") - 2500) < 1e-9 and parse_len("250cm", "mm") == 2500 and fmt_len(2500, "m") == "2.500", "units parse/format")
p = build_house(); rooms = {r["name"]: r["area"] for r in SCH.room_rows(p)}
check(abs(rooms["Chambre 1"] - 3.425 * 3.025) < 0.01, "room area = inner net area (Chambre 1)")
check(abs(SCH.building_area(p)[0] - 10.2 * 8.2) < 0.01, "gross footprint = 10.2 x 8.2 m")
check(wall_union(p, False).area - wall_union(p, True).area > 3e6, "openings are cut out of the walls")
q = Project()
for i, b in enumerate(CATALOG): q.add("furn", block=b, c=[i * 3000, 0], rot=15)
for i, pat in enumerate(PATTERNS): q.add("hatch", pts=[[i * 2000, 3000], [i * 2000 + 1500, 3000], [i * 2000 + 1500, 4500], [i * 2000, 4500]], pattern=pat, sp=2.0)
for kind in ("straight", "L", "U"):
    for turn in ("L", "R"): q.add("stair", p=[0, -5000], rot=0, kind=kind, turn=turn, w=1000, h=3000, n=17, g=250, up="UP")
for k in ("north", "level", "bubble", "detail"): q.add("sym", kind=k, p=[0, 6000], value=3.2, label="A", num="1", sheet="02", rot=0)
for k in ("section", "slope", "break", "symaxis"): q.add("sym", kind=k, p1=[0, 7000], p2=[3000, 7000], label="A", side=1, text="2%")
q.add("sym", kind="leader", pts=[[0, 8000], [500, 8500], [1500, 8500]], text="x")
for sh in ("rect", "round", "L", "T", "X"): q.add("column", c=[0, 0], shape=sh, w=400, h=400, rot=30)
check(len(render(q)) > 500, "every furniture / hatch / stair / symbol / column type renders")
d = tempfile.mkdtemp(); EXP.export_dxf(p, d + "/a.dxf"); doc = ezdxf.readfile(d + "/a.dxf")
check(len(doc.audit().errors) == 0 and len(doc.modelspace()) > 800 and int(doc.header["$INSUNITS"]) == 4, "DXF valid (audit clean, mm units)")
EXP.export_dxf(q, d + "/b.dxf"); check(len(ezdxf.readfile(d + "/b.dxf").audit().errors) == 0, "DXF of the stress project is valid")
EXP.export_pdf(p, d + "/a.pdf"); check("A3" in subprocess.run(["pdfinfo", d + "/a.pdf"], capture_output=True, text=True).stdout, "PDF page size follows the A3 frame")
EXP.export_png(p, d + "/a.png", dpi=60); check(os.path.getsize(d + "/a.png") > 20000, "PNG export")
SCH.export_xlsx(p, d + "/a.xlsx"); check(len(openpyxl.load_workbook(d + "/a.xlsx").sheetnames) == 4, "XLSX schedules (4 sheets)")
SCH.export_csv(p, d + "/a.csv"); check(os.path.getsize(d + "/a.csv") > 100, "CSV schedules")
p.save(d + "/a.bpl"); p2 = Project.load(d + "/a.bpl"); check(p2.entities == p.entities and p2.scale == p.scale, "save/load round trip")
n = len(p2.entities); p2.checkpoint(); p2.add("line", p1=[0, 0], p2=[1, 1]); p2.undo(); check(len(p2.entities) == n, "undo")
w = p2.of_type("wall")[0]["id"]; before = len(p2.entities); p2.remove([w]); check(len(p2.entities) < before - 1, "removing a wall removes its openings")
check(CHK.run_checks(p)[0]["key"] == "chk_all_ok", "clean project passes checks")
bad = Project(); wid = bad.add("wall", pts=[[0, 0], [3000, 0]], t=200); bad.add("wall", pts=[[0, 0], [3000, 0]], t=200)
bad.add("opening", wall=wid, pos=1500, w=900, kind="door"); bad.add("opening", wall=wid, pos=1700, w=900, kind="door"); bad.add("stair", p=[0, 0], rot=0, kind="straight", w=700, h=3000, n=10, g=400)
check({"chk_dup_wall", "chk_open_overlap", "chk_blondel", "chk_stair_w"} <= {r["key"] for r in CHK.run_checks(bad)}, "checks detect duplicates, overlaps, Blondel, narrow stair")
check(CHK.autofix(bad) >= 1, "autofix removes duplicates")
mc = L.machine_code(); check(mc == L.machine_code() and len(mc) == 19, "machine code is stable")
pem = "seller_kit/private_key.pem"; key = L.issue_key(pem, "Test", "t@e.com", "pro", mc)
check(L.verify_key(key).ok and L.verify_key(key).edition == "pro", "valid key accepted")
check(L.verify_key(key, "AAAA-BBBB-CCCC-DDDD").reason == "machine", "key refused on another machine")
check(L.verify_key(key[:-3] + "AAA").reason == "signature", "tampered key refused")
exp = L.issue_key(pem, "Old", "o@e.com", "pro", mc, (datetime.date.today() - datetime.timedelta(days=1)).isoformat()); check(L.verify_key(exp).reason == "expired", "expired key refused")
check(L.verify_key(L.issue_key(pem, "School", "s@e.com", "edu", "*")).ok, "wildcard (lab) key accepted")
check(L.trial_days_left() == 14 and L.trial_days_left(datetime.date.today() + datetime.timedelta(days=20)) == 0, "14-day trial then expiry")
check(L.trial_days_left(datetime.date.today() - datetime.timedelta(days=3)) == 0, "clock roll-back detected")
os.remove(os.path.join(L.config_dir(), "state.dat")); L.activate(key); check(L.current_licence().edition == "pro", "activation persists")
check("dxf" not in L.FEATURES["demo"] and "pdf" not in L.FEATURES["demo"], "demo mode cannot export DXF/PDF")
src = "".join(open(f, encoding="utf8").read() for f in glob.glob("batiplan/*.py"))
used = set(re.findall(r'\btr\(\s*["\']([A-Za-z0-9_\-]+)["\']', src)) | set(re.findall(r'"((?:o|p|t|m|pr|chk|msg|lic|lvl|col|sched|set|lay|lib|sum|ent|tab|btn|dlg|st|fr)_[a-z0-9_]+)"', src))
ATTR = {"st_prompt", "st_xy", "st_mode", "st_lic"}
missing = sorted(k for k in used if k not in DATA and k not in ATTR and k != "lang_code" and not k.endswith("_"))
check(not missing, f"all translation keys exist {missing[:5]}")
check(all(isinstance(v, tuple) and len(v) == 2 and v[0] and v[1] for v in DATA.values()), "every string has FR and EN")
fmt_ok = all(sorted(re.findall(r"\{(\w+)\}", a)) == sorted(re.findall(r"\{(\w+)\}", b)) for a, b in DATA.values()); check(fmt_ok, "FR/EN placeholders match")
for lang in ("fr", "en"): set_lang(lang); check(all(tr(k) for k in DATA if "{" not in DATA[k][0]), f"all strings render ({lang})")
set_lang("fr"); print(f"\nALL {ok} CHECKS PASSED")
