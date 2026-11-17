"""BatiPlan Studio main window (Tkinter)."""
import os, math, re, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from collections import defaultdict
from .brand import *
from .i18n import tr, set_lang, get_lang
from .i18n_data import DATA
from .model import Project, LAYERS
from .units import fmt_len, parse_len, UNITS
from .gui_core import CanvasMixin, load_cfg, save_cfg
from .tools import TOOLS
from .furniture import CATALOG, build as furn_build
from .hatchlib import PATTERNS, NAMES
from . import license as LIC, export as EXP, schedule as SCH, checks as CHK
from .dxf_import import read_underlay

RIBBON = [
    ("tab_arch", [("axis", "┼", "t_axis"), ("grid", "▦", "t_grid"), ("wall", "▬", "t_wall"), ("rectwall", "▭", "t_rectwall"), ("column", "■", "t_column"), ("door", "◜", "t_door"),
                  ("window", "▤", "t_window"), ("stair", "☰", "t_stair"), ("room", "⌂", "t_room"), ("furn", "🛏", "t_furn"), ("hatch", "▨", "t_hatch")]),
    ("tab_draw", [("line", "╱", "t_line"), ("poly", "⌇", "t_poly"), ("rect", "▯", "t_rect"), ("circle", "○", "t_circle"), ("arc", "◠", "t_arc")]),
    ("tab_annot", [("dim", "↔", "t_dim"), ("dimchain", "⇹", "t_dimchain"), ("text", "A", "t_text"), ("north", "N", "t_north"), ("level", "▽", "t_level"), ("bubble", "Ⓐ", "t_bubble"),
                   ("section", "✂", "t_section"), ("slope", "↘", "t_slope"), ("break", "≀", "t_break"), ("symaxis", "⫼", "t_symaxis"), ("leader", "↗", "t_leader"),
                   ("detail", "◐", "t_detail"), ("frame", "▣", "t_frame")]),
    ("tab_modify", [("select", "↖", "t_select"), ("move", "✥", "t_move"), ("copy", "⧉", "t_copy"), ("rotate", "↻", "t_rotate"), ("mirror", "⇋", "t_mirror"),
                    ("erase", "✖", "t_erase"), ("undo", "↶", "t_undo"), ("redo", "↷", "t_redo")]),
    ("tab_tools", [("measure", "📏", "t_measure"), ("check", "✔", "t_check"), ("sched", "▥", "t_sched"), ("import", "⇩", "t_import"), ("exp_dxf", "DXF", "t_exp_dxf"),
                   ("exp_pdf", "PDF", "t_exp_pdf"), ("exp_png", "PNG", "t_exp_png")]),
]
SCHEMA = {
    "wall": [("t", "p_thick", "len")],
    "opening": [("kind", "p_kind", "choice", ["door", "door2", "slide", "window", "win_param"]), ("w", "p_width", "len"), ("h", "p_height", "len"), ("sill", "p_sill", "len"),
                ("pos", "p_pos", "len"), ("tag", "p_tag", "str"), ("side", "p_side", "choice", [1, -1]), ("hinge", "p_hinge", "choice", ["L", "R"])],
    "column": [("shape", "p_shape", "choice", ["rect", "round", "L", "T", "X"]), ("w", "p_width", "len"), ("h", "p_depth", "len"), ("rot", "p_rot", "num")],
    "stair": [("kind", "p_kind", "choice", ["straight", "L", "U"]), ("turn", "p_turn", "choice", ["L", "R"]), ("w", "p_width", "len"), ("n", "p_risers", "int"), ("g", "p_tread", "len"),
              ("h", "p_total_h", "len"), ("rot", "p_rot", "num")],
    "furn": [("block", "p_block", "choice", list(CATALOG)), ("rot", "p_rot", "num"), ("sx", "p_sx", "num"), ("sy", "p_sy", "num")],
    "room": [("name", "p_name", "str")], "text": [("s", "p_text", "str"), ("h", "p_texth", "num"), ("rot", "p_rot", "num")],
    "dim": [("off", "p_offset", "len"), ("text", "p_text_override", "str")], "hatch": [("pattern", "p_pattern", "choice", PATTERNS), ("sp", "p_spacing", "num"), ("angle", "p_rot", "num")],
    "axis": [("label", "p_label", "str")], "sym": [("label", "p_label", "str"), ("text", "p_text", "str"), ("value", "p_level", "num"), ("rot", "p_rot", "num")],
    "frame": [("size", "o_paper", "choice", ["A4", "A3", "A2", "A1", "A0"]), ("orient", "o_orient", "choice", ["L", "P"]), ("title", "o_title", "str")],
}


def choice_label(v):
    k = "ch_" + str(v)
    if k in DATA: return tr(k)
    if v in CATALOG: return CATALOG[v][0 if get_lang() == "fr" else 1]
    if v in NAMES: return NAMES[v][0 if get_lang() == "fr" else 1]
    return str(v)


class Tip:
    def __init__(self, w, text_fn):
        self.w, self.fn, self.tw = w, text_fn, None
        w.bind("<Enter>", self.show, add="+"); w.bind("<Leave>", self.hide, add="+")
    def show(self, e=None):
        self.tw = tk.Toplevel(self.w); self.tw.wm_overrideredirect(True)
        self.tw.geometry(f"+{self.w.winfo_rootx() + 8}+{self.w.winfo_rooty() + self.w.winfo_height() + 4}")
        tk.Label(self.tw, text=self.fn(), bg="#ffffe0", relief="solid", bd=1, font=("DejaVu Sans", 9)).pack()
    def hide(self, e=None):
        if self.tw: self.tw.destroy(); self.tw = None


class App(tk.Tk, CanvasMixin):
    def __init__(self, path=None, geometry=None):
        super().__init__()
        self.cfg = load_cfg(); set_lang(self.cfg.get("lang", "fr"))
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(geometry or f"{min(1360, sw - 20)}x{min(780, sh - 110)}+10+10"); self.minsize(900, 560)
        self.prj = Project(); self.prj.unit = self.cfg.get("unit", "mm"); self.lic = LIC.current_licence(); self.init_view()
        self.snap_grid_visible = True; self.optv = defaultdict(dict); self.opt_vars = {}
        self.tool = None; self.tool_name = "select"; self.prev_tool = "select"; self.tool_btns = {}
        self.build_ui()
        if path and os.path.exists(path): self.open_path(path)
        self.set_tool("select"); self.protocol("WM_DELETE_WINDOW", self.quit_app); self.after(200, self.zoom_extents); self.after(400, self.first_run_check)

    # ================================================================= UI
    def build_ui(self):
        for w in self.winfo_children(): w.destroy()
        self.title(f"{APP_NAME} {APP_VERSION}"); self.build_menu(); self.style = ttk.Style(self)
        try: self.style.theme_use("clam")
        except Exception: pass
        self.style.configure("Ribbon.TNotebook.Tab", padding=(14, 4))
        bottom = tk.Frame(self, bd=1, relief="sunken"); bottom.pack(side="bottom", fill="x"); self.cmd_var = tk.StringVar()
        tk.Label(bottom, text=tr("lbl_command"), font=("DejaVu Sans", 9, "bold")).pack(side="left", padx=(6, 2))
        self.cmd = tk.Entry(bottom, textvariable=self.cmd_var, width=26); self.cmd.pack(side="left", padx=2, pady=2); self.cmd.bind("<Return>", self.on_cmd)
        self.st_prompt = tk.Label(bottom, text="", anchor="w", font=("DejaVu Sans", 9), fg="#0b3d91"); self.st_prompt.pack(side="left", padx=10, fill="x", expand=True)
        self.st_lic = tk.Label(bottom, text="", font=("DejaVu Sans", 9, "bold")); self.st_lic.pack(side="right", padx=8)
        self.st_mode = tk.Label(bottom, text="", font=("DejaVu Sans", 9)); self.st_mode.pack(side="right", padx=8)
        self.st_xy = tk.Label(bottom, text="", font=("DejaVu Sans Mono", 9), width=36); self.st_xy.pack(side="right", padx=8)
        self.nb = ttk.Notebook(self, style="Ribbon.TNotebook"); self.nb.pack(side="top", fill="x"); self.tool_btns = {}
        for tabkey, items in RIBBON:
            f = tk.Frame(self.nb, bg="#f3f3f3"); self.nb.add(f, text=tr(tabkey))
            for name, icon, tip in items:
                b = tk.Button(f, text=f"{icon}\n{tr(tip)}", width=9, height=3, font=("DejaVu Sans", 8), relief="raised", bd=1, bg="#f3f3f3", activebackground="#dbe8ff", command=lambda n=name: self.on_ribbon(n))
                b.pack(side="left", padx=1, pady=2); Tip(b, lambda t=tip: tr(t + "_tip")); self.tool_btns[name] = b
        self.optbar = tk.Frame(self, bg="#e8eef7", bd=1, relief="groove"); self.optbar.pack(side="top", fill="x")
        main = tk.PanedWindow(self, orient="horizontal", sashwidth=4); main.pack(side="top", fill="both", expand=True)
        self.canvas = tk.Canvas(main, bg="white", highlightthickness=0, cursor="crosshair"); main.add(self.canvas, stretch="always")
        right = tk.Frame(main, width=290); main.add(right, stretch="never"); self.rnb = ttk.Notebook(right); self.rnb.pack(fill="both", expand=True)
        self.p_props = tk.Frame(self.rnb); self.p_layers = tk.Frame(self.rnb); self.p_lib = tk.Frame(self.rnb)
        self.rnb.add(self.p_props, text=tr("tab_props")); self.rnb.add(self.p_layers, text=tr("tab_layers")); self.rnb.add(self.p_lib, text=tr("tab_library"))
        self.build_layers(); self.build_library(); self.refresh_props(); self.bind_canvas()
        for seq, fn in [("<Control-z>", lambda e: self.undo()), ("<Control-y>", lambda e: self.redo()), ("<Control-s>", lambda e: self.save()), ("<Control-o>", lambda e: self.open_dialog()),
                        ("<Control-n>", lambda e: self.new()), ("<Control-a>", lambda e: self.select_all()), ("<F8>", lambda e: self.toggle("ortho")), ("<F3>", lambda e: self.toggle("snap_obj")),
                        ("<F7>", lambda e: self.toggle("snap_grid")), ("<Delete>", lambda e: self.erase_selected()), ("<Escape>", lambda e: self.escape()),
                        ("<Return>", lambda e: self.enter_key()), ("<space>", lambda e: self.enter_key()), ("<F1>", lambda e: self.quick_guide())]: self.bind(seq, fn)
        self.bind("<Key>", self.on_key); self.update_status()

    def build_menu(self):
        m = tk.Menu(self); self.config(menu=m)
        f = tk.Menu(m, tearoff=0); m.add_cascade(label=tr("m_file"), menu=f)
        for k, fn, acc in [("m_new", self.new, "Ctrl+N"), ("m_open", self.open_dialog, "Ctrl+O"), ("m_save", self.save, "Ctrl+S"), ("m_saveas", self.save_as, "")]: f.add_command(label=tr(k), command=fn, accelerator=acc)
        f.add_separator(); f.add_command(label=tr("m_import_dxf"), command=self.import_dxf); f.add_command(label=tr("m_clear_underlay"), command=self.clear_underlay); f.add_separator()
        for k, fn in [("m_exp_dxf", self.export_dxf), ("m_exp_pdf", self.export_pdf), ("m_exp_png", self.export_png), ("m_exp_xlsx", self.export_xlsx), ("m_exp_csv", self.export_csv)]: f.add_command(label=tr(k), command=fn)
        f.add_separator(); f.add_command(label=tr("m_quit"), command=self.quit_app)
        e = tk.Menu(m, tearoff=0); m.add_cascade(label=tr("m_edit"), menu=e)
        e.add_command(label=tr("t_undo"), command=self.undo, accelerator="Ctrl+Z"); e.add_command(label=tr("t_redo"), command=self.redo, accelerator="Ctrl+Y"); e.add_separator()
        e.add_command(label=tr("m_select_all"), command=self.select_all, accelerator="Ctrl+A"); e.add_command(label=tr("t_erase"), command=self.erase_selected, accelerator="Del")
        v = tk.Menu(m, tearoff=0); m.add_cascade(label=tr("m_view"), menu=v); v.add_command(label=tr("m_zoom_ext"), command=self.zoom_extents)
        self.v_ortho = tk.BooleanVar(value=self.ortho); self.v_snapo = tk.BooleanVar(value=self.snap_obj); self.v_snapg = tk.BooleanVar(value=self.snap_grid)
        self.v_grid = tk.BooleanVar(value=True); self.v_lw = tk.BooleanVar(value=self.show_lw)
        v.add_checkbutton(label=tr("m_ortho") + "  F8", variable=self.v_ortho, command=lambda: self.toggle("ortho", True))
        v.add_checkbutton(label=tr("m_snap_obj") + "  F3", variable=self.v_snapo, command=lambda: self.toggle("snap_obj", True))
        v.add_checkbutton(label=tr("m_snap_grid") + "  F7", variable=self.v_snapg, command=lambda: self.toggle("snap_grid", True))
        v.add_checkbutton(label=tr("m_show_grid"), variable=self.v_grid, command=self.toggle_grid); v.add_checkbutton(label=tr("m_show_lw"), variable=self.v_lw, command=self.toggle_lw)
        p = tk.Menu(m, tearoff=0); m.add_cascade(label=tr("m_project"), menu=p); p.add_command(label=tr("m_settings"), command=self.project_settings)
        u = tk.Menu(p, tearoff=0); p.add_cascade(label=tr("m_units"), menu=u)
        for k in UNITS: u.add_command(label=k, command=lambda k=k: self.set_unit(k))
        t = tk.Menu(m, tearoff=0); m.add_cascade(label=tr("m_tools"), menu=t)
        t.add_command(label=tr("t_check"), command=self.check_window); t.add_command(label=tr("t_sched"), command=self.sched_window); t.add_command(label=tr("m_stats"), command=self.stats_window)
        l = tk.Menu(m, tearoff=0); m.add_cascade(label=tr("m_language"), menu=l)
        l.add_command(label="Français", command=lambda: self.change_lang("fr")); l.add_command(label="English", command=lambda: self.change_lang("en"))
        h = tk.Menu(m, tearoff=0); m.add_cascade(label=tr("m_help"), menu=h)
        h.add_command(label=tr("m_guide"), command=self.quick_guide, accelerator="F1"); h.add_command(label=tr("m_licence"), command=self.licence_dialog); h.add_command(label=tr("m_about"), command=self.about)

    # ================================================================= ribbon / tools
    def on_ribbon(self, name):
        direct = {"grid": self.grid_dialog, "undo": self.undo, "redo": self.redo, "check": self.check_window, "sched": self.sched_window, "import": self.import_dxf,
                  "exp_dxf": self.export_dxf, "exp_pdf": self.export_pdf, "exp_png": self.export_png}
        if name in direct: direct[name](); return
        self.set_tool(name)

    def set_tool(self, name):
        if self.tool: self.tool.finish(self)
        if self.tool_name != name: self.prev_tool = self.tool_name
        self.tool_name = name; self.tool = TOOLS[name](); self.tool.start(self); self.preview = []
        for n, b in self.tool_btns.items(): b.config(relief="sunken" if n == name else "raised", bg="#cfe0ff" if n == name else "#f3f3f3")
        self.rebuild_options(); self.canvas.config(cursor="arrow" if name == "select" else "crosshair")
        if name == "furn": self.rnb.select(self.p_lib)
        self.update_status(); self.request_redraw()

    def escape(self):
        if self.tool: self.tool.finish(self)
        self.sel = set(); self.on_selection(); self.request_redraw()

    def enter_key(self):
        if self.focus_get() is self.cmd: return
        if self.tool and self.tool.pts: self.tool.finish(self)
        elif self.prev_tool and self.prev_tool != self.tool_name: self.set_tool(self.prev_tool)

    def on_key(self, ev):
        if ev.widget is self.cmd or isinstance(ev.widget, (tk.Entry, ttk.Entry, ttk.Combobox, tk.Text)): return
        if ev.char and ev.char in "0123456789.-+@,": self.cmd.focus_set(); self.cmd_var.set(self.cmd_var.get() + ev.char); self.cmd.icursor("end"); return
        if self.tool and ev.char: self.tool.key(self, ev.char)

    # ---------------------------------------------------------------- options bar
    def get_opt(self, tool, key):
        spec = next((o for o in TOOLS[tool].options if o[0] == key), None)
        if key in self.optv[tool]: return self.optv[tool][key]
        return spec[3] if spec else None

    def set_opt(self, tool, key, val): self.optv[tool][key] = val

    def rebuild_options(self):
        for w in self.optbar.winfo_children(): w.destroy()
        self.opt_vars = {}; tool = self.tool_name
        tk.Label(self.optbar, text=tr("t_" + tool) if ("t_" + tool) in DATA else tool, bg="#e8eef7", font=("DejaVu Sans", 9, "bold")).pack(side="left", padx=8)
        for key, lab, kind, default, choices in TOOLS[tool].options:
            val = self.get_opt(tool, key); tk.Label(self.optbar, text=tr(lab), bg="#e8eef7", font=("DejaVu Sans", 9)).pack(side="left", padx=(8, 2))
            if kind == "choice":
                labels = [choice_label(c) for c in choices]; var = tk.StringVar(value=choice_label(val))
                cb = ttk.Combobox(self.optbar, textvariable=var, values=labels, state="readonly", width=max(8, min(24, max(len(x) for x in labels) + 1))); cb.pack(side="left")
                cb.bind("<<ComboboxSelected>>", lambda e, t=tool, k=key, ch=choices, c=cb: self._opt_choice(t, k, ch, c))
            elif kind == "bool":
                var = tk.BooleanVar(value=bool(val)); ttk.Checkbutton(self.optbar, variable=var, command=lambda t=tool, k=key, v=var: self.set_opt(t, k, v.get())).pack(side="left")
            else:
                var = tk.StringVar(value=fmt_len(val, self.prj.unit) if kind == "len" else str(val)); en = tk.Entry(self.optbar, textvariable=var, width=9 if kind != "str" else 12); en.pack(side="left")
                en.bind("<KeyRelease>", lambda e, t=tool, k=key, kd=kind, v=var: self._opt_text(t, k, kd, v)); en.bind("<Return>", lambda e: self.canvas.focus_set())
            self.opt_vars[key] = var
        if tool == "select": tk.Label(self.optbar, text=tr("pr_select"), bg="#e8eef7").pack(side="left", padx=8)

    def _opt_choice(self, tool, key, choices, cb):
        self.set_opt(tool, key, choices[cb.current()])
        if tool == "furn" and key == "block": self.lib_select_block(choices[cb.current()])

    def _opt_text(self, tool, key, kind, var):
        s = var.get()
        try:
            v = parse_len(s, self.prj.unit) if kind == "len" else float(s.replace(",", ".")) if kind == "num" else int(float(s)) if kind == "int" else s
            self.set_opt(tool, key, v)
        except ValueError: pass

    # ================================================================= editing helpers
    def begin(self): self.prj.checkpoint()
    def changed(self): self.prj.dirty = True; self._snaps = None; self.preview = []; self.refresh_props(); self.request_redraw()
    def canvas_rings(self, gm): return self._rings(gm)

    def msg(self, text, popup=False):
        self.st_prompt.config(text=text)
        if popup: messagebox.showinfo(APP_NAME, text, parent=self)

    def ask_text(self, title, initial=""):
        d = tk.Toplevel(self); self.after(20, lambda d=d: self.place_dialog(d)); d.title(title); d.transient(self); d.grab_set(); res = {"v": None}
        t = tk.Text(d, width=40, height=5, font=("DejaVu Sans", 10)); t.pack(padx=8, pady=8); t.insert("1.0", initial); t.focus_set()
        def ok(e=None): res["v"] = t.get("1.0", "end").rstrip("\n"); d.destroy()
        bf = tk.Frame(d); bf.pack(pady=(0, 8)); ttk.Button(bf, text=tr("btn_ok"), command=ok).pack(side="left", padx=4); ttk.Button(bf, text=tr("btn_cancel"), command=d.destroy).pack(side="left", padx=4)
        d.bind("<Control-Return>", ok); self.wait_window(d); return res["v"]

    def lic_ok(self, feature):
        if self.lic.allows(feature): return True
        messagebox.showinfo(APP_NAME, tr("msg_feature_locked", edition=self.lic.edition.upper()), parent=self); return False

    def toggle(self, what, from_menu=False):
        if what == "ortho": self.ortho = self.v_ortho.get() if from_menu else not self.ortho; self.v_ortho.set(self.ortho)
        elif what == "snap_obj": self.snap_obj = self.v_snapo.get() if from_menu else not self.snap_obj; self.v_snapo.set(self.snap_obj)
        else: self.snap_grid = self.v_snapg.get() if from_menu else not self.snap_grid; self.v_snapg.set(self.snap_grid)
        self.update_status()

    def toggle_grid(self): self.snap_grid_visible = self.v_grid.get(); self.request_redraw()
    def toggle_lw(self): self.show_lw = self.v_lw.get(); self.request_redraw()
    def undo(self):
        if self.prj.undo(): self.sel = set(); self.on_selection(); self._snaps = None; self.request_redraw()
    def redo(self):
        if self.prj.redo(): self.sel = set(); self.on_selection(); self._snaps = None; self.request_redraw()
    def select_all(self): self.sel = {e["id"] for e in self.prj.entities if self.prj.visible(e)}; self.on_selection(); self.request_redraw()
    def erase_selected(self):
        if self.sel: self.begin(); self.prj.remove(list(self.sel)); self.sel = set(); self.changed(); self.on_selection()

    # ================================================================= command line
    def on_cmd(self, ev=None):
        s = self.cmd_var.get().strip(); self.cmd_var.set(""); self.canvas.focus_set()
        if not s: self.enter_key(); return
        if self.tool and hasattr(self.tool, "typed") and re.fullmatch(r"[-+]?\d+([.,]\d+)?", s):
            try: self.tool.typed(self, s.replace(",", ".")); return
            except Exception: pass
        pt = self.parse_point(s)
        if pt is None: self.msg(tr("msg_bad_input")); return
        self.cursor = pt
        if self.tool: self.tool.click(self, pt, None)

    def parse_point(self, s):
        u = self.prj.unit; lp = self.last_pt
        try:
            if s.startswith("@") and lp: a, b = s[1:].split(",")[:2]; return (lp[0] + parse_len(a, u), lp[1] + parse_len(b, u))
            if "<" in s and lp:
                d, ang = s.split("<"); d = parse_len(d, u); r = math.radians(float(ang)); return (lp[0] + d * math.cos(r), lp[1] + d * math.sin(r))
            if ";" in s: a, b = s.split(";"); return (parse_len(a, u), parse_len(b, u))
            if "," in s and (not lp or re.search(r"\d\s*,\s*[-+]?\d", s)):
                a, b = s.split(",")[:2]; return (parse_len(a, u), parse_len(b, u))
            if lp:
                d = parse_len(s, u); dx, dy = self.cursor[0] - lp[0], self.cursor[1] - lp[1]
                if self.ortho: dx, dy = (math.copysign(1, dx), 0.0) if abs(dx) >= abs(dy) else (0.0, math.copysign(1, dy))
                n = math.hypot(dx, dy)
                if n < 1e-9: dx, dy, n = 1.0, 0.0, 1.0
                return (lp[0] + dx / n * d, lp[1] + dy / n * d)
        except Exception: return None
        return None

    # ================================================================= status
    def update_status(self):
        if not (hasattr(self, "st_prompt") and self.st_prompt.winfo_exists()): return
        self.st_prompt.config(text=tr(self.tool.prompt if self.tool else "pr_select")); u = self.prj.unit
        self.st_xy.config(text=f"X {fmt_len(self.cursor[0], u)}  Y {fmt_len(self.cursor[1], u)} {u}")
        self.st_mode.config(text=f"{'OBJ ' if self.snap_obj else ''}{'GRID ' if self.snap_grid else ''}{'ORTHO ' if self.ortho else ''}| 1:{self.prj.scale} | {u}")
        l = self.lic
        if l.edition == "trial": self.st_lic.config(text=tr("st_trial", n=l.trial_left), fg="#b9770e")
        elif l.ok: self.st_lic.config(text=f"{l.edition.upper()} - {l.name}", fg="#1e8449")
        else: self.st_lic.config(text=tr("st_demo"), fg="#c0392b")

    # ================================================================= right panels
    def on_selection(self): self.refresh_props()

    def refresh_props(self):
        if not hasattr(self, "p_props"): return
        for w in self.p_props.winfo_children(): w.destroy()
        ids = [i for i in self.sel if self.prj.get(i)]
        if not ids:
            tk.Label(self.p_props, text=tr("props_none"), wraplength=250, justify="left", fg="#666").pack(padx=10, pady=14, anchor="w"); self.draw_summary(); return
        types = {self.prj.get(i)["type"] for i in ids}; tk.Label(self.p_props, text=tr("props_sel", n=len(ids)), font=("DejaVu Sans", 10, "bold")).pack(anchor="w", padx=8, pady=6)
        if len(types) != 1: return
        t = types.pop(); e0 = self.prj.get(ids[0]); schema = SCHEMA.get(t, [])
        if t == "sym":
            k0 = e0.get("kind"); schema = [s for s in schema if (s[0] == "label" and k0 in ("bubble", "section")) or (s[0] == "text" and k0 in ("slope", "leader")) or (s[0] == "value" and k0 == "level") or (s[0] == "rot" and k0 == "north")]
        form = tk.Frame(self.p_props); form.pack(fill="x", padx=8); tk.Label(form, text=tr("ent_" + t), fg="#0b3d91", font=("DejaVu Sans", 9, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
        for r, sp in enumerate(schema, 1):
            key, lab, kind = sp[0], sp[1], sp[2]; tk.Label(form, text=tr(lab), font=("DejaVu Sans", 9)).grid(row=r, column=0, sticky="w", pady=2); val = e0.get(key, "")
            if kind == "choice":
                var = tk.StringVar(value=choice_label(val) if val != "" else ""); cb = ttk.Combobox(form, textvariable=var, values=[choice_label(c) for c in sp[3]], state="readonly", width=18); cb.grid(row=r, column=1, pady=2)
                cb.bind("<<ComboboxSelected>>", lambda ev, k=key, ch=sp[3], c=cb: self.apply_prop(ids, k, ch[c.current()]))
            else:
                var = tk.StringVar(value=fmt_len(val, self.prj.unit) if kind == "len" and val != "" else str(val)); en = tk.Entry(form, textvariable=var, width=20); en.grid(row=r, column=1, pady=2)
                en.bind("<Return>", lambda ev, k=key, kd=kind, v=var: self.apply_prop(ids, k, self.conv(kd, v.get()))); en.bind("<FocusOut>", lambda ev, k=key, kd=kind, v=var: self.apply_prop(ids, k, self.conv(kd, v.get())))
        self.draw_summary()

    def conv(self, kind, s):
        try:
            if kind == "len": return parse_len(s, self.prj.unit)
            if kind == "num": return float(s.replace(",", "."))
            if kind == "int": return int(float(s))
        except ValueError: return None
        return s

    def apply_prop(self, ids, key, val):
        if val is None: return
        changed = False
        for i in ids:
            e = self.prj.get(i)
            if e is not None and e.get(key) != val:
                if not changed: self.begin()
                e[key] = val; changed = True
        if changed: self.prj.dirty = True; self.request_redraw()

    def draw_summary(self):
        gross, net = SCH.building_area(self.prj); f = tk.LabelFrame(self.p_props, text=tr("sum_title")); f.pack(fill="x", padx=8, pady=12, side="bottom")
        for txt in (tr("sum_ent", n=len(self.prj.entities)), tr("sum_gross") + f": {gross} m²", tr("sum_net") + f": {net} m²"): tk.Label(f, text=txt, anchor="w").pack(fill="x", padx=6)

    def build_layers(self):
        self.lv = {}; tk.Label(self.p_layers, text=tr("lay_hint"), fg="#666", wraplength=250, justify="left").pack(anchor="w", padx=8, pady=6)
        for key, (name, fr, en, aci, scol, lw, lt) in LAYERS.items():
            row = tk.Frame(self.p_layers); row.pack(fill="x", padx=8, pady=1); tk.Label(row, bg=scol, width=2).pack(side="left", padx=(0, 6))
            v = tk.BooleanVar(value=self.prj.layer_state[key]["visible"]); l = tk.BooleanVar(value=self.prj.layer_state[key]["locked"])
            ttk.Checkbutton(row, variable=v, command=lambda k=key, v=v: self.set_layer(k, "visible", v.get())).pack(side="left")
            tk.Label(row, text=fr if get_lang() == "fr" else en, width=18, anchor="w").pack(side="left")
            ttk.Checkbutton(row, text="🔒", variable=l, command=lambda k=key, l=l: self.set_layer(k, "locked", l.get())).pack(side="left"); self.lv[key] = (v, l)

    def set_layer(self, key, what, val): self.prj.layer_state[key][what] = val; self.request_redraw()

    def build_library(self):
        p = self.p_lib; tk.Label(p, text=tr("lib_furn"), font=("DejaVu Sans", 9, "bold")).pack(anchor="w", padx=8, pady=(8, 2))
        self.lb = tk.Listbox(p, height=11, exportselection=False); self.lb.pack(fill="x", padx=8); self.lib_keys = list(CATALOG)
        for k in self.lib_keys: self.lb.insert("end", CATALOG[k][0 if get_lang() == "fr" else 1])
        self.lb.bind("<<ListboxSelect>>", self.lib_pick)
        self.lprev = tk.Canvas(p, width=250, height=130, bg="white", highlightthickness=1, highlightbackground="#aaa"); self.lprev.pack(padx=8, pady=6)
        tk.Label(p, text=tr("lib_hatch"), font=("DejaVu Sans", 9, "bold")).pack(anchor="w", padx=8, pady=(4, 2))
        self.hb = tk.Listbox(p, height=7, exportselection=False); self.hb.pack(fill="x", padx=8)
        for k in PATTERNS: self.hb.insert("end", NAMES[k][0 if get_lang() == "fr" else 1])
        self.hb.bind("<<ListboxSelect>>", self.hatch_pick)

    def lib_pick(self, ev=None):
        s = self.lb.curselection()
        if s:
            k = self.lib_keys[s[0]]; self.set_opt("furn", "block", k); self.draw_lib_prev(k)
            if self.tool_name != "furn": self.set_tool("furn")
            else: self.rebuild_options()

    def lib_select_block(self, k):
        if k in self.lib_keys: self.lb.selection_clear(0, "end"); self.lb.selection_set(self.lib_keys.index(k)); self.draw_lib_prev(k)

    def draw_lib_prev(self, k):
        c = self.lprev; c.delete("all"); W, D = CATALOG[k][2], CATALOG[k][3]; s = min(230 / W, 110 / D)
        for p in furn_build(k):
            if p["t"] == "poly":
                pts = [v for q in p["pts"] for v in (125 + q[0] * s, 65 - q[1] * s)]; c.create_line(*(pts + (pts[:2] if p.get("closed") else [])), fill="#333")
            elif p["t"] == "line": c.create_line(125 + p["a"][0] * s, 65 - p["a"][1] * s, 125 + p["b"][0] * s, 65 - p["b"][1] * s, fill="#333")
            elif p["t"] == "circle":
                x, y, r = 125 + p["c"][0] * s, 65 - p["c"][1] * s, p["r"] * s; c.create_oval(x - r, y - r, x + r, y + r, outline="#333")
        c.create_text(6, 118, anchor="w", text=f"{W} x {D} mm", fill="#666", font=("DejaVu Sans", 8))

    def hatch_pick(self, ev=None):
        s = self.hb.curselection()
        if s: self.set_opt("hatch", "pattern", PATTERNS[s[0]]); self.set_tool("hatch")

    # ================================================================= files
    def new(self):
        if not self.ask_save(): return
        keep = self.prj.unit; self.prj = Project(); self.prj.unit = keep; self.sel = set(); self.changed(); self.zoom_extents(); self.title_update()
    def title_update(self): self.title(f"{APP_NAME} {APP_VERSION} - {os.path.basename(self.prj.path) if self.prj.path else tr('untitled')}{' *' if self.prj.dirty else ''}")
    def ask_save(self):
        if not self.prj.dirty: return True
        r = messagebox.askyesnocancel(APP_NAME, tr("msg_save_changes"), parent=self)
        if r is None: return False
        return self.save() if r else True
    def open_dialog(self):
        if not self.ask_save(): return
        p = filedialog.askopenfilename(parent=self, filetypes=[(APP_NAME, "*" + FILE_EXT), ("*", "*.*")])
        if p: self.open_path(p)
    def open_path(self, p):
        try: self.prj = Project.load(p)
        except Exception as ex: messagebox.showerror(APP_NAME, str(ex), parent=self); return
        self.sel = set(); self.changed(); self.zoom_extents(); self.title_update()
    def save(self):
        if not self.prj.path: return self.save_as()
        self.prj.save(); self.title_update(); return True
    def save_as(self):
        p = filedialog.asksaveasfilename(parent=self, defaultextension=FILE_EXT, filetypes=[(APP_NAME, "*" + FILE_EXT)])
        if not p: return False
        self.prj.save(p); self.title_update(); return True
    def quit_app(self):
        if self.ask_save(): save_cfg(dict(self.cfg, lang=get_lang(), unit=self.prj.unit)); self.destroy()

    def import_dxf(self):
        if not self.lic_ok("underlay"): return
        p = filedialog.askopenfilename(parent=self, filetypes=[("DXF", "*.dxf")])
        if not p: return
        try: prims = read_underlay(p)
        except Exception as ex: messagebox.showerror(APP_NAME, str(ex), parent=self); return
        self.begin(); self.prj.underlay = prims; self.changed(); self.zoom_extents(); self.msg(tr("msg_underlay", n=len(prims)))
    def clear_underlay(self): self.begin(); self.prj.underlay = []; self.changed()

    def _out(self, ext, title):
        base = os.path.splitext(os.path.basename(self.prj.path or "plan"))[0]
        return filedialog.asksaveasfilename(parent=self, defaultextension=ext, initialfile=base + ext, title=title, filetypes=[(ext.upper(), "*" + ext)])
    def _export(self, feature, ext, key, fn):
        if not self.lic_ok(feature): return
        p = self._out(ext, tr(key))
        if p: fn(p); self.msg(tr("msg_exported", p=p), True)
    def export_dxf(self): self._export("dxf", ".dxf", "m_exp_dxf", lambda p: EXP.export_dxf(self.prj, p))
    def export_pdf(self): self._export("pdf", ".pdf", "m_exp_pdf", lambda p: EXP.export_pdf(self.prj, p, watermark=self.lic.watermark))
    def export_png(self): self._export("png", ".png", "m_exp_png", lambda p: EXP.export_png(self.prj, p, watermark=self.lic.watermark))
    def export_xlsx(self): self._export("xlsx", ".xlsx", "m_exp_xlsx", lambda p: SCH.export_xlsx(self.prj, p))
    def export_csv(self): self._export("xlsx", ".csv", "m_exp_csv", lambda p: SCH.export_csv(self.prj, p))

    # ================================================================= dialogs
    def place_dialog(self, d):
        try:
            d.update_idletasks()
            d.geometry(f"+{self.winfo_rootx() + max(10, (self.winfo_width() - d.winfo_width()) // 2)}+{self.winfo_rooty() + max(10, (self.winfo_height() - d.winfo_height()) // 3)}")
        except tk.TclError: pass

    def close_dialogs(self):
        for w in self.winfo_children():
            if isinstance(w, tk.Toplevel): w.destroy()

    def _dlg(self, title, modal=True):
        d = tk.Toplevel(self); self.after(20, lambda d=d: self.place_dialog(d)); d.title(title)
        if modal: d.transient(self); d.grab_set()
        return d

    def set_unit(self, u): self.prj.unit = u; self.rebuild_options(); self.refresh_props(); self.request_redraw()

    def change_lang(self, code):
        set_lang(code); self.cfg["lang"] = code; save_cfg(dict(self.cfg, lang=code, unit=self.prj.unit))
        keep = self.tool_name; self.build_ui(); self.set_tool(keep); self.request_redraw()

    def project_settings(self):
        d = self._dlg(tr("m_settings")); m = self.prj.meta; v = {}
        rows = [("name", "set_name"), ("client", "set_client"), ("author", "set_author"), ("date", "set_date"), ("address", "set_address"), ("sheet", "set_sheet"), ("revision", "set_rev")]
        for r, (k, lab) in enumerate(rows):
            tk.Label(d, text=tr(lab)).grid(row=r, column=0, sticky="w", padx=8, pady=3); v[k] = tk.StringVar(value=m.get(k, "")); tk.Entry(d, textvariable=v[k], width=34).grid(row=r, column=1, padx=8)
        r = len(rows); tk.Label(d, text=tr("set_scale")).grid(row=r, column=0, sticky="w", padx=8); sc = tk.StringVar(value=f"1:{self.prj.scale}")
        ttk.Combobox(d, textvariable=sc, values=[f"1:{s}" for s in (20, 25, 50, 75, 100, 125, 150, 200, 250, 500)], width=10).grid(row=r, column=1, sticky="w", padx=8)
        tk.Label(d, text=tr("set_unit")).grid(row=r + 1, column=0, sticky="w", padx=8); un = tk.StringVar(value=self.prj.unit)
        ttk.Combobox(d, textvariable=un, values=list(UNITS), state="readonly", width=10).grid(row=r + 1, column=1, sticky="w", padx=8)
        tk.Label(d, text=tr("set_wallfill")).grid(row=r + 2, column=0, sticky="w", padx=8); wf = tk.StringVar(value=choice_label(self.prj.settings.get("wall_fill", "solid")))
        ttk.Combobox(d, textvariable=wf, values=[choice_label(x) for x in ("none", "solid", "hatch")], state="readonly", width=14).grid(row=r + 2, column=1, sticky="w", padx=8)
        tk.Label(d, text=tr("set_grid")).grid(row=r + 3, column=0, sticky="w", padx=8); gs = tk.StringVar(value=fmt_len(self.grid_step, self.prj.unit)); tk.Entry(d, textvariable=gs, width=10).grid(row=r + 3, column=1, sticky="w", padx=8)
        def ok():
            self.begin()
            for k in v: m[k] = v[k].get()
            try: self.prj.scale = int(sc.get().split(":")[-1])
            except ValueError: pass
            self.prj.unit = un.get(); self.prj.settings["wall_fill"] = ["none", "solid", "hatch"][[choice_label(x) for x in ("none", "solid", "hatch")].index(wf.get())]
            try: self.grid_step = max(1.0, parse_len(gs.get(), self.prj.unit))
            except ValueError: pass
            d.destroy(); self.changed(); self.rebuild_options()
        bf = tk.Frame(d); bf.grid(row=r + 4, column=0, columnspan=2, pady=10); ttk.Button(bf, text=tr("btn_ok"), command=ok).pack(side="left", padx=4); ttk.Button(bf, text=tr("btn_cancel"), command=d.destroy).pack(side="left", padx=4)

    def parse_list(self, s):
        out = []
        for tok in re.split(r"[;,\s]+", s.strip()):
            if not tok: continue
            m = re.fullmatch(r"(\d+)[x*](.+)", tok)
            if m: out += [parse_len(m.group(2), self.prj.unit)] * int(m.group(1))
            else: out.append(parse_len(tok, self.prj.unit))
        return out

    def grid_dialog(self):
        d = self._dlg(tr("t_grid")); tk.Label(d, text=tr("grid_hint"), wraplength=380, justify="left", fg="#555").grid(row=0, column=0, columnspan=2, padx=8, pady=6)
        xs = tk.StringVar(value="4x" + fmt_len(5000, self.prj.unit)); ys = tk.StringVar(value="3x" + fmt_len(4500, self.prj.unit))
        tk.Label(d, text=tr("grid_x")).grid(row=1, column=0, sticky="w", padx=8); tk.Entry(d, textvariable=xs, width=34).grid(row=1, column=1, padx=8, pady=3)
        tk.Label(d, text=tr("grid_y")).grid(row=2, column=0, sticky="w", padx=8); tk.Entry(d, textvariable=ys, width=34).grid(row=2, column=1, padx=8, pady=3)
        def ok():
            try: X, Y = self.parse_list(xs.get()), self.parse_list(ys.get())
            except ValueError: messagebox.showerror(APP_NAME, tr("msg_bad_input"), parent=d); return
            ext = 1500.0; x = [0.0]; y = [0.0]
            for a in X: x.append(x[-1] + a)
            for a in Y: y.append(y[-1] + a)
            self.begin()
            for i, xv in enumerate(x): self.prj.add("axis", p1=[xv, y[0] - ext], p2=[xv, y[-1] + ext], label=str(i + 1))
            for j, yv in enumerate(y): self.prj.add("axis", p1=[x[0] - ext, yv], p2=[x[-1] + ext, yv], label=chr(65 + j) if j < 26 else str(j))
            d.destroy(); self.changed(); self.zoom_extents()
        bf = tk.Frame(d); bf.grid(row=3, column=0, columnspan=2, pady=10); ttk.Button(bf, text=tr("btn_ok"), command=ok).pack(side="left", padx=4); ttk.Button(bf, text=tr("btn_cancel"), command=d.destroy).pack(side="left", padx=4)

    def check_window(self):
        if not self.lic_ok("check"): return
        d = self._dlg(tr("t_check"), False); d.geometry("640x380")
        tv = ttk.Treeview(d, columns=("lvl", "msg"), show="headings"); tv.heading("lvl", text=tr("col_level")); tv.heading("msg", text=tr("col_message"))
        tv.column("lvl", width=70, stretch=False); tv.column("msg", width=540); tv.pack(fill="both", expand=True, padx=6, pady=6)
        def fill():
            tv.delete(*tv.get_children())
            for r in CHK.run_checks(self.prj): tv.insert("", "end", values=(tr("lvl_" + r["level"]), r["msg"]), tags=(str(r["eid"]),))
        def fix(): self.begin(); n = CHK.autofix(self.prj); self.changed(); fill(); messagebox.showinfo(APP_NAME, tr("msg_fixed", n=n), parent=d)
        def goto(e):
            s = tv.selection()
            if s:
                t = tv.item(s[0], "tags")
                if t and t[0] != "None": self.sel = {int(t[0])}; self.on_selection(); self.request_redraw()
        tv.bind("<<TreeviewSelect>>", goto); bf = tk.Frame(d); bf.pack(pady=4)
        ttk.Button(bf, text=tr("btn_fix"), command=fix).pack(side="left", padx=4); ttk.Button(bf, text=tr("btn_refresh"), command=fill).pack(side="left", padx=4); fill()

    def sched_window(self):
        d = self._dlg(tr("t_sched"), False); d.geometry("760x420"); nb = ttk.Notebook(d); nb.pack(fill="both", expand=True, padx=6, pady=6)
        def table(title, cols, rows):
            f = tk.Frame(nb); nb.add(f, text=title); tv = ttk.Treeview(f, columns=[c[0] for c in cols], show="headings")
            for k, lab in cols: tv.heading(k, text=lab); tv.column(k, width=110, anchor="center")
            for r in rows: tv.insert("", "end", values=[r[k] for k, _ in cols])
            tv.pack(fill="both", expand=True)
        table(tr("sched_openings"), [("tag", tr("col_tag")), ("kind", tr("col_type")), ("w", tr("col_w")), ("h", tr("col_h")), ("sill", tr("col_sill")), ("qty", tr("col_qty")), ("area", tr("col_area"))], SCH.opening_rows(self.prj))
        table(tr("sched_rooms"), [("name", tr("col_room")), ("area", tr("col_area_m2")), ("perim", tr("col_perim"))], SCH.room_rows(self.prj))
        table(tr("sched_furniture"), [("name", tr("col_item")), ("qty", tr("col_qty"))], SCH.furniture_rows(self.prj))
        bf = tk.Frame(d); bf.pack(pady=4); ttk.Button(bf, text=tr("m_exp_xlsx"), command=self.export_xlsx).pack(side="left", padx=4); ttk.Button(bf, text=tr("m_exp_csv"), command=self.export_csv).pack(side="left", padx=4)

    def stats_window(self):
        gross, net = SCH.building_area(self.prj); wl = sum(r["len"] for r in SCH.wall_rows(self.prj))
        messagebox.showinfo(tr("m_stats"), f"{tr('sum_gross')}: {gross} m²\n{tr('sum_net')}: {net} m²\n{tr('sum_walls_len')}: {wl:.2f} m\n{tr('sum_ent', n=len(self.prj.entities))}", parent=self)

    def licence_dialog(self):
        d = self._dlg(tr("m_licence")); l = self.lic
        state = tr("lic_trial", n=l.trial_left) if l.edition == "trial" else (tr("lic_ok", ed=l.edition.upper(), name=l.name) if l.ok else tr("lic_demo"))
        tk.Label(d, text=state, font=("DejaVu Sans", 10, "bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=8); tk.Label(d, text=tr("lic_code")).grid(row=1, column=0, sticky="w", padx=10)
        mc = tk.Entry(d, width=30, font=("DejaVu Sans Mono", 11)); mc.insert(0, LIC.machine_code()); mc.config(state="readonly"); mc.grid(row=1, column=1, padx=10)
        tk.Label(d, text=tr("lic_how", email=SUPPORT_EMAIL, wa=SUPPORT_WHATSAPP), wraplength=420, justify="left", fg="#555").grid(row=2, column=0, columnspan=2, padx=10, pady=6)
        tk.Label(d, text=tr("lic_key")).grid(row=3, column=0, sticky="nw", padx=10); t = tk.Text(d, width=50, height=4); t.grid(row=3, column=1, padx=10, pady=4)
        def act():
            r = LIC.activate(t.get("1.0", "end"))
            if r.ok: self.lic = LIC.current_licence(); messagebox.showinfo(APP_NAME, tr("lic_activated"), parent=d); d.destroy(); self.update_status()
            else: messagebox.showerror(APP_NAME, tr("lic_err_" + r.reason) if ("lic_err_" + r.reason) in DATA else tr("lic_err_signature"), parent=d)
        bf = tk.Frame(d); bf.grid(row=4, column=0, columnspan=2, pady=10); ttk.Button(bf, text=tr("btn_activate"), command=act).pack(side="left", padx=4); ttk.Button(bf, text=tr("btn_close"), command=d.destroy).pack(side="left", padx=4)

    def about(self): messagebox.showinfo(tr("m_about"), f"{APP_NAME} {APP_VERSION}\n\n{tr('about_text')}\n\n{VENDOR}\n{SUPPORT_EMAIL}  |  {SUPPORT_WHATSAPP}\n{WEBSITE}", parent=self)

    def quick_guide(self):
        d = self._dlg(tr("m_guide"), False); d.geometry("560x520"); t = tk.Text(d, wrap="word", font=("DejaVu Sans", 10)); t.pack(fill="both", expand=True); t.insert("1.0", tr("guide_text")); t.config(state="disabled")

    def first_run_check(self):
        if "lang" not in self.cfg:
            r = messagebox.askyesno("Language / Langue", "Français ?   (Non = English)", parent=self); self.change_lang("fr" if r else "en")
        elif self.lic.edition == "trial" and self.lic.trial_left <= 3: self.msg(tr("st_trial", n=self.lic.trial_left))


def main(path=None): App(path).mainloop()
