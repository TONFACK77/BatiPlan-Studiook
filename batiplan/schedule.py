"""Quantity take-off: door/window schedule, room table, areas, furniture list -> CSV / XLSX."""
import csv, collections
from shapely.geometry import Polygon
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from .render import room_area_m2, room_perimeter_m, wall_union, _polys
from .furniture import CATALOG
from .i18n import tr
from . import geom as g


def opening_rows(project):
    rows = collections.OrderedDict()
    for e in project.of_type("opening"):
        door = e.get("kind", "door").startswith(("door", "slide"))
        key = (e.get("tag", ""), e.get("kind", "door"), round(e["w"]), round(e.get("h", 2100 if door else 1200)), round(e.get("sill", 0 if door else 900)))
        rows[key] = rows.get(key, 0) + 1
    return [{"tag": tag, "kind": tr("kind_" + kind), "w": w, "h": h, "sill": sill, "qty": n, "area": round(w * h / 1e6 * n, 2)}
            for (tag, kind, w, h, sill), n in sorted(rows.items(), key=lambda kv: (kv[0][1], kv[0][0], kv[0][2]))]


def room_rows(project): return [{"name": e.get("name", ""), "area": round(room_area_m2(e), 2), "perim": round(room_perimeter_m(e), 2)} for e in project.of_type("room")]


def wall_rows(project):
    tot = collections.defaultdict(float)
    for e in project.of_type("wall"): tot[round(e["t"])] += g.poly_length([tuple(p) for p in e["pts"]], bool(e.get("closed")))
    return [{"t": t, "len": round(L / 1000.0, 2)} for t, L in sorted(tot.items())]


def furniture_rows(project):
    cnt = collections.Counter(e["block"] for e in project.of_type("furn")); i = 0 if tr("lang_code") == "fr" else 1
    return [{"name": CATALOG[k][i], "qty": n} for k, n in sorted(cnt.items())]


def building_area(project):
    u = wall_union(project, with_openings=False)
    gross = sum(Polygon(p.exterior).area for p in _polys(u)) / 1e6 if u is not None else 0.0
    return round(gross, 2), round(sum(room_area_m2(e) for e in project.of_type("room")), 2)


def export_csv(project, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";"); w.writerow([tr("sched_openings")])
        w.writerow([tr("col_tag"), tr("col_type"), tr("col_w"), tr("col_h"), tr("col_sill"), tr("col_qty"), tr("col_area")])
        for r in opening_rows(project): w.writerow([r["tag"], r["kind"], r["w"], r["h"], r["sill"], r["qty"], r["area"]])
        w.writerow([]); w.writerow([tr("sched_rooms")]); w.writerow([tr("col_room"), tr("col_area_m2"), tr("col_perim")])
        for r in room_rows(project): w.writerow([r["name"], r["area"], r["perim"]])
    return path


def export_xlsx(project, path):
    wb = Workbook(); hdr = PatternFill("solid", fgColor="D9D9D9"); thin = Side(style="thin", color="A6A6A6"); bd = Border(left=thin, right=thin, top=thin, bottom=thin)

    def sheet(ws, title, headers, rows):
        ws.title = title[:30]; ws["A1"] = f"{project.meta.get('name','')}  -  {title}"; ws["A1"].font = Font(name="Arial", bold=True, size=13)
        for j, h in enumerate(headers, 1):
            c = ws.cell(row=3, column=j, value=h); c.font = Font(name="Arial", bold=True); c.fill = hdr; c.border = bd; c.alignment = Alignment(horizontal="center", wrap_text=True)
        for i, r in enumerate(rows, 4):
            for j, v in enumerate(r, 1): c = ws.cell(row=i, column=j, value=v); c.font = Font(name="Arial"); c.border = bd
        for j in range(1, len(headers) + 1): ws.column_dimensions[chr(64 + j)].width = 18
        ws.page_setup.paperSize = 9; ws.page_setup.fitToWidth = 1; ws.page_setup.fitToHeight = 0; ws.sheet_properties.pageSetUpPr.fitToPage = True
        return 4 + len(rows)

    ws = wb.active; rows = [[r["tag"], r["kind"], r["w"], r["h"], r["sill"], r["qty"], r["area"]] for r in opening_rows(project)]
    n = sheet(ws, tr("sched_openings"), [tr("col_tag"), tr("col_type"), tr("col_w"), tr("col_h"), tr("col_sill"), tr("col_qty"), tr("col_area")], rows)
    if rows: ws.cell(row=n + 1, column=6, value=f"=SUM(F4:F{n-1})")
    ws2 = wb.create_sheet(); rr = [[r["name"], r["area"], r["perim"]] for r in room_rows(project)]
    n2 = sheet(ws2, tr("sched_rooms"), [tr("col_room"), tr("col_area_m2"), tr("col_perim")], rr)
    if rr:
        ws2.cell(row=n2 + 1, column=1, value=tr("col_total")).font = Font(name="Arial", bold=True)
        ws2.cell(row=n2 + 1, column=2, value=f"=SUM(B4:B{n2-1})").font = Font(name="Arial", bold=True)
    gross, net = building_area(project)
    sheet(wb.create_sheet(), tr("sched_summary"), [tr("col_item"), tr("col_value")], [[tr("sum_gross"), gross], [tr("sum_net"), net], [tr("sum_walls_len"), sum(r["len"] for r in wall_rows(project))]])
    sheet(wb.create_sheet(), tr("sched_furniture"), [tr("col_item"), tr("col_qty")], [[r["name"], r["qty"]] for r in furniture_rows(project)])
    wb.save(path); return path
