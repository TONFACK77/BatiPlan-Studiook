"""Project data model: plain dict entities -> trivially serialisable & undoable."""
import json, datetime
from .brand import APP_VERSION, FILE_EXT

# key: (dxf name, fr, en, aci colour, screen colour, lineweight mm, linetype)
LAYERS = {
    "axis":   ("BP-AXIS",   "Axes",              "Axes",               1, "#c0392b", 0.18, "DASHDOT"),
    "wall":   ("BP-WALL",   "Murs",              "Walls",              7, "#222222", 0.50, "CONTINUOUS"),
    "col":    ("BP-COLUMN", "Poteaux",           "Columns",            7, "#222222", 0.50, "CONTINUOUS"),
    "door":   ("BP-DOOR",   "Portes",            "Doors",              3, "#1e8449", 0.25, "CONTINUOUS"),
    "window": ("BP-WINDOW", "Fenêtres",          "Windows",            5, "#1f4e9c", 0.25, "CONTINUOUS"),
    "stair":  ("BP-STAIR",  "Escaliers",         "Stairs",             6, "#7d3c98", 0.25, "CONTINUOUS"),
    "furn":   ("BP-FURN",   "Mobilier",          "Furniture",          8, "#7f8c8d", 0.18, "CONTINUOUS"),
    "room":   ("BP-ROOM",   "Pièces",            "Rooms",              2, "#b9770e", 0.18, "CONTINUOUS"),
    "dim":    ("BP-DIM",    "Cotations",         "Dimensions",         4, "#117a8b", 0.13, "CONTINUOUS"),
    "text":   ("BP-TEXT",   "Textes",            "Text",               7, "#222222", 0.18, "CONTINUOUS"),
    "symbol": ("BP-SYMBOL", "Symboles",          "Symbols",            2, "#b9770e", 0.25, "CONTINUOUS"),
    "hatch":  ("BP-HATCH",  "Hachures",          "Hatching",           9, "#95a5a6", 0.09, "CONTINUOUS"),
    "draw":   ("BP-DRAW",   "Dessin libre",      "Free drawing",       7, "#222222", 0.25, "CONTINUOUS"),
    "frame":  ("BP-FRAME",  "Cadre / cartouche", "Frame / title block", 7, "#222222", 0.35, "CONTINUOUS"),
    "under":  ("BP-UNDER",  "Fond de plan",      "Underlay",           8, "#b0b0b0", 0.09, "CONTINUOUS"),
}
ENT_LAYER = {"axis": "axis", "wall": "wall", "column": "col", "stair": "stair", "furn": "furn", "room": "room", "dim": "dim", "text": "text",
             "sym": "symbol", "hatch": "hatch", "line": "draw", "poly": "draw", "circle": "draw", "arc": "draw", "frame": "frame"}


def layer_of(e):
    if e["type"] == "opening": return "window" if e.get("kind", "door").startswith("win") else "door"
    return ENT_LAYER.get(e["type"], "draw")


class Project:
    def __init__(self):
        self.meta = {"name": "", "client": "", "author": "", "date": datetime.date.today().isoformat(), "sheet": "01", "revision": "A", "address": ""}
        self.unit = "mm"; self.scale = 100; self.entities = []; self.next_id = 1; self.underlay = []
        self.settings = {"wall_fill": "solid", "level": 0.0}
        self.layer_state = {k: {"visible": True, "locked": False} for k in LAYERS}
        self.path = None; self.dirty = False; self._undo, self._redo = [], []

    def add(self, type_, **props):
        e = {"id": self.next_id, "type": type_}; e.update(props); self.next_id += 1
        self.entities.append(e); self.dirty = True; return e["id"]

    def get(self, eid):
        for e in self.entities:
            if e["id"] == eid: return e
        return None

    def remove(self, ids):
        ids = set(ids); gone = {e["id"] for e in self.entities if e["id"] in ids}
        for e in self.entities:
            if e["type"] == "opening" and e.get("wall") in gone: gone.add(e["id"])
        self.entities = [e for e in self.entities if e["id"] not in gone]; self.dirty = True; return gone

    def of_type(self, *types): return [e for e in self.entities if e["type"] in types]
    def visible(self, e): return self.layer_state[layer_of(e)]["visible"]

    def _snap(self): return json.dumps({"e": self.entities, "n": self.next_id, "s": self.settings, "u": self.unit, "sc": self.scale, "m": self.meta})

    def _load_snap(self, s):
        d = json.loads(s); self.entities, self.next_id, self.settings = d["e"], d["n"], d["s"]; self.unit, self.scale, self.meta = d["u"], d["sc"], d["m"]

    def checkpoint(self): self._undo.append(self._snap()); self._undo = self._undo[-100:]; self._redo = []
    def undo(self):
        if not self._undo: return False
        self._redo.append(self._snap()); self._load_snap(self._undo.pop()); self.dirty = True; return True
    def redo(self):
        if not self._redo: return False
        self._undo.append(self._snap()); self._load_snap(self._redo.pop()); self.dirty = True; return True

    def to_dict(self):
        return {"app": "BatiPlan", "version": APP_VERSION, "meta": self.meta, "unit": self.unit, "scale": self.scale, "settings": self.settings,
                "next_id": self.next_id, "entities": self.entities, "layers": self.layer_state, "underlay": self.underlay}

    def save(self, path=None):
        path = path or self.path
        if not path.lower().endswith(FILE_EXT): path += FILE_EXT
        with open(path, "w", encoding="utf-8") as f: json.dump(self.to_dict(), f, ensure_ascii=False)
        self.path, self.dirty = path, False; return path

    @classmethod
    def load(cls, path):
        with open(path, "r", encoding="utf-8") as f: d = json.load(f)
        p = cls(); p.meta.update(d.get("meta", {})); p.unit = d.get("unit", "mm"); p.scale = d.get("scale", 100)
        p.settings.update(d.get("settings", {})); p.entities = d.get("entities", [])
        p.next_id = d.get("next_id", 1 + max([e["id"] for e in p.entities] or [0])); p.underlay = d.get("underlay", [])
        for k, v in d.get("layers", {}).items():
            if k in p.layer_state: p.layer_state[k].update(v)
        p.path, p.dirty = path, False; return p
