# -*- coding: utf-8 -*-
"""Builds the bilingual tutorial MP4 from the REAL application screenshots (FR UI left / EN UI right)."""
import os, sys, subprocess, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFont
from tutorial_data import STEPS
from batiplan.brand import APP_NAME, APP_VERSION, VENDOR, SUPPORT_EMAIL, SUPPORT_WHATSAPP, WEBSITE, TRIAL_DAYS
SHOTS, OUT = sys.argv[1], sys.argv[2]; ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); FW, FH, FPS = 1920, 1080, 25
F = lambda sz, b=False: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if b else ""), sz)
NAVY, BLUE, WHITE, SOFT = (16, 36, 63), (24, 54, 94), (255, 255, 255), (188, 208, 234)
work = os.path.join(os.path.dirname(OUT), "_vframes"); shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
EXTRA = {"s03_grid_dialog": ("Saisie des entraxes de la trame", "Entering the grid bay widths"), "s04_walls_a": ("Aperçu du mur pendant le tracé", "Wall preview while drawing"),
         "s05_openings_a": ("Aperçu de la porte : le mur sera découpé", "Door preview: the wall will be cut")}
seq = []
for n, (sid, (tfr, ten), bul, (cfr, cen)) in enumerate(STEPS, 1):
    pre = {"s03_grid": "s03_grid_dialog", "s04_walls": "s04_walls_a", "s05_openings": "s05_openings_a"}.get(sid)
    if pre: seq.append((n, tfr, ten, pre, EXTRA[pre][0], EXTRA[pre][1], 4.0))
    seq.append((n, tfr, ten, "pdfpreview" if sid == "s16_export" else sid, cfr, cen, 5.5))
shot = lambda lang, key: Image.open(os.path.join(SHOTS, lang, key + ".png")).convert("RGB")


def wrap(draw, text, font, width):
    out, line = [], ""
    for w in text.split():
        t = (line + " " + w).strip()
        if draw.textlength(t, font=font) <= width: line = t
        else: out.append(line); line = w
    return out + [line]


def frame_for(n, tfr, ten, key, cfr, cen, total):
    im = Image.new("RGB", (FW, FH), NAVY); d = ImageDraw.Draw(im); d.rectangle((0, 0, FW, 120), fill=BLUE)
    d.text((40, 16), f"ÉTAPE {n} / {total}", font=F(20, True), fill=SOFT); d.text((40, 46), tfr, font=F(40, True), fill=WHITE)
    d.text((FW // 2 + 20, 16), f"STEP {n} / {total}", font=F(20, True), fill=SOFT); d.text((FW // 2 + 20, 46), ten, font=F(40, True), fill=WHITE)
    w, h = 930, int(930 * 815 / 1400)
    for i, (lang, cap) in enumerate((("fr", cfr), ("en", cen))):
        x = 30 + i * (w + 30); img = shot(lang, key)
        img = img.resize((w, int(w * img.height / img.width))) if key == "pdfpreview" else img.resize((w, h), Image.LANCZOS)
        im.paste(img, (x, 150)); d.rectangle((x - 1, 149, x + w, 150 + img.height), outline=(120, 150, 190), width=2)
        d.text((x, 150 + h + 18), "FRANÇAIS" if lang == "fr" else "ENGLISH", font=F(16, True), fill=SOFT)
        for k, ln in enumerate(wrap(d, cap, F(34, True), w)[:2]): d.text((x, 150 + h + 44 + k * 44), ln, font=F(34, True), fill=WHITE)
    d.rectangle((0, FH - 14, int(FW * n / total), FH), fill=(255, 190, 70)); return im


def card(lines, sub=None):
    im = Image.new("RGB", (FW, FH), BLUE); d = ImageDraw.Draw(im); lg = Image.open(os.path.join(ROOT, "assets", "logo.png")).resize((260, 260)); im.paste(lg, (130, 150), lg); y = 190
    for txt, sz, b, col in lines: d.text((470, y), txt, font=F(sz, b), fill=col); y += int(sz * 1.5)
    yy = 640
    for txt, sz, b, col in (sub or []): d.text((130, yy), txt, font=F(sz, b), fill=col); yy += int(sz * 1.55)
    return im


total = len(STEPS); frames = [(card([(APP_NAME, 96, True, WHITE), (f"Version {APP_VERSION}", 34, False, SOFT)],
        [("Tutoriel complet : de la trame d'axes à l'export DXF / PDF", 44, True, WHITE), ("Complete tutorial: from axis grid to DXF / PDF export", 44, False, SOFT), (f"{total} étapes / steps  -  FR + EN", 28, False, SOFT)]), 5.0)]
for (n, tfr, ten, key, cfr, cen, sec) in seq: frames.append((frame_for(n, tfr, ten, key, cfr, cen, total), sec))
frames.append((card([(APP_NAME, 70, True, WHITE), (f"Essai gratuit {TRIAL_DAYS} jours  /  Free {TRIAL_DAYS}-day trial", 36, False, SOFT)],
        [("Merci ! / Thank you!", 52, True, WHITE), (f"{SUPPORT_EMAIL}   |   WhatsApp {SUPPORT_WHATSAPP}", 32, False, SOFT), (WEBSITE, 32, False, SOFT),
         ("Licence hors ligne : envoyez votre code machine / Offline licence: send your machine code", 28, False, SOFT)]), 7.0))
lines = []; idx = 0; DISS = 10
for k, (img, sec) in enumerate(frames):
    p = os.path.join(work, f"f{idx:05d}.png"); img.save(p); lines.append(f"file '{p}'\nduration {max(sec - DISS / FPS, 0.1):.3f}"); idx += 1
    if k + 1 < len(frames):
        for j in range(1, DISS + 1):
            p = os.path.join(work, f"f{idx:05d}.png"); Image.blend(img, frames[k + 1][0], j / (DISS + 1)).save(p); lines.append(f"file '{p}'\nduration {1 / FPS:.4f}"); idx += 1
lines.append(f"file '{p}'"); open(os.path.join(work, "list.txt"), "w").write("\n".join(lines))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", os.path.join(work, "list.txt"), "-vf", f"fps={FPS},format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "22",
                "-movflags", "+faststart", "-metadata", f"title={APP_NAME} tutorial FR/EN", "-metadata", f"artist={VENDOR}", OUT], check=True)
shutil.rmtree(work, ignore_errors=True); print("video ok", OUT)
