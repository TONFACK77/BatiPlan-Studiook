"""Bilingual (FR / EN) text engine. Every user-visible string lives in i18n_data.py as (fr, en)."""
from .i18n_data import DATA

_lang = "fr"


def set_lang(code):
    global _lang
    _lang = "en" if str(code).lower().startswith("en") else "fr"


def get_lang(): return _lang


def tr(key, **kw):
    if key == "lang_code": return _lang
    v = DATA.get(key)
    if v is None: return key
    s = v[1] if _lang == "en" else v[0]
    return s.format(**kw) if kw else s
