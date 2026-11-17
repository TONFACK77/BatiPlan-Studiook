# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from PIL import Image
import pdf_common
from tutorial_data import STEPS
from batiplan.brand import APP_NAME, APP_VERSION, VENDOR, SUPPORT_EMAIL, SUPPORT_WHATSAPP, WEBSITE, TRIAL_DAYS

SHOTS = sys.argv[1]; OUT = sys.argv[2]; LOGO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logo.png")
W, H = landscape(A4); M = 10 * mm; GAP = 8 * mm; CW = (W - 2 * M - GAP) / 2
NAVY, GREY, LIGHT = HexColor("#18365e"), HexColor("#555555"), HexColor("#eef2f8")
st = lambda sz=9, col="#222222", font="DV": ParagraphStyle("x", fontName=font, fontSize=sz, leading=sz * 1.35, textColor=HexColor(col))
c = canvas.Canvas(OUT, pagesize=(W, H)); c.setTitle(f"{APP_NAME} - Tutoriel / Tutorial"); c.setAuthor(VENDOR); page = [0]


def footer(label=""):
    page[0] += 1; c.setFont("DV", 7); c.setFillColor(GREY); c.line(M, 8 * mm, W - M, 8 * mm)
    c.drawString(M, 4.5 * mm, f"{APP_NAME} {APP_VERSION}  |  {label}"); c.drawRightString(W - M, 4.5 * mm, f"{page[0]}"); c.drawCentredString(W / 2 + 25 * mm, 4.5 * mm, f"{SUPPORT_EMAIL}  |  {SUPPORT_WHATSAPP}")


def band(tfr, ten, num=None):
    c.setFillColor(NAVY); c.rect(0, H - 17 * mm, W, 17 * mm, fill=1, stroke=0); c.setFillColor(white); c.setFont("DVB", 13); pre = f"{num}.  " if num else ""
    c.drawString(M, H - 11 * mm, pre + tfr); c.drawString(M + CW + GAP, H - 11 * mm, pre + ten)
    c.setFont("DV", 7); c.setFillColor(HexColor("#bcd0ea")); c.drawString(M, H - 15 * mm, "FRANÇAIS"); c.drawString(M + CW + GAP, H - 15 * mm, "ENGLISH")


def paras(items, x, ytop, width, size=9, bullet=True):
    y = ytop
    for t in items:
        p = Paragraph(("•&nbsp;&nbsp;" if bullet else "") + t, st(size)); w, h = p.wrap(width, 400); p.drawOn(c, x, y - h); y -= h + 2.4 * mm
    return y


def image(path, x, ytop, width):
    im = Image.open(path); h = width * im.height / im.width
    c.drawImage(path, x, ytop - h, width, h); c.setStrokeColor(HexColor("#999999")); c.setLineWidth(0.5); c.rect(x, ytop - h, width, h, fill=0); return ytop - h


c.setFillColor(NAVY); c.rect(0, 0, W, H, fill=1, stroke=0); c.drawImage(LOGO, 20 * mm, H - 75 * mm, 45 * mm, 45 * mm, mask="auto")
c.setFillColor(white); c.setFont("DVB", 34); c.drawString(75 * mm, H - 52 * mm, APP_NAME); c.setFont("DV", 14); c.setFillColor(HexColor("#bcd0ea")); c.drawString(75 * mm, H - 62 * mm, f"Version {APP_VERSION}")
c.setFillColor(white); c.setFont("DVB", 20); c.drawString(20 * mm, H - 100 * mm, "Tutoriel complet pas à pas"); c.setFont("DV", 16); c.drawString(20 * mm, H - 110 * mm, "Dessiner un plan d'architecture, de la trame d'axes à l'export DXF / PDF")
c.setFont("DVB", 20); c.drawString(20 * mm, H - 130 * mm, "Complete step-by-step tutorial"); c.setFont("DV", 16); c.drawString(20 * mm, H - 140 * mm, "Draw an architectural plan, from axis grid to DXF / PDF export")
c.setFont("DV", 10); c.setFillColor(HexColor("#bcd0ea")); c.drawString(20 * mm, 30 * mm, "FR (colonne de gauche) / EN (right-hand column)"); c.drawString(20 * mm, 24 * mm, f"{VENDOR}  |  {SUPPORT_EMAIL}  |  {SUPPORT_WHATSAPP}  |  {WEBSITE}")
c.showPage(); page[0] += 1

band("Bienvenue et installation", "Welcome and installation")
fr = ["<b>Installer</b> : lancez l'installateur « BatiPlanStudio_Setup.exe », suivez l'assistant (Suivant, Installer). Un raccourci est créé sur le Bureau.",
      "<b>Premier lancement</b> : choisissez la langue (Français ou English). Elle se change à tout moment dans le menu « Langue / Language ».",
      f"<b>Essai gratuit de {TRIAL_DAYS} jours</b> : toutes les fonctions sont actives. Le compteur est visible en bas à droite.",
      "<b>Activer</b> : menu Aide > Licence et activation. Copiez le code machine, envoyez-le au vendeur après paiement, collez la clé reçue, cliquez Activer. Aucune connexion Internet n'est nécessaire.",
      "<b>Fichiers</b> : vos plans sont enregistrés en .bpl. Les exemples du dossier « Exemples » s'ouvrent par Fichier > Ouvrir.",
      "<b>Ouvrir dans AutoCAD</b> : Fichier > Exporter DXF. Les calques BP-WALL, BP-DOOR… sont créés ; l'unité du dessin est le millimètre."]
en = ["<b>Install</b>: run “BatiPlanStudio_Setup.exe” and follow the wizard (Next, Install). A Desktop shortcut is created.",
      "<b>First launch</b>: choose the language (Français or English). You can change it at any time in the “Langue / Language” menu.",
      f"<b>Free {TRIAL_DAYS}-day trial</b>: every feature is enabled. The counter is shown at the bottom right.",
      "<b>Activate</b>: Help > Licence and activation. Copy the machine code, send it to the seller after payment, paste the key you receive, click Activate. No Internet connection is needed.",
      "<b>Files</b>: your plans are saved as .bpl. The samples in the “Samples” folder open with File > Open.",
      "<b>Open in AutoCAD</b>: File > Export DXF. The BP-WALL, BP-DOOR… layers are created; drawing unit is the millimetre."]
paras(fr, M, H - 24 * mm, CW); paras(en, M + CW + GAP, H - 24 * mm, CW); footer("Installation"); c.showPage()
band("Méthode de travail conseillée en 10 étapes", "Recommended 10-step workflow")
fr = ["Régler projet, échelle, unité (étape 2).", "Poser la trame d'axes (3).", "Dessiner murs extérieurs puis cloisons (4).", "Poser portes et fenêtres (5).", "Créer les pièces et leurs surfaces (6).",
      "Ajouter escaliers et mobilier (7, 8).", "Hachurer matériaux et coupes (9).", "Coter, annoter, symboles (10, 11).", "Mettre en page : cadre + cartouche (12), puis Vérifier (14).", "Exporter DXF / PDF / Excel (15, 16)."]
en = ["Set project, scale, unit (step 2).", "Lay out the axis grid (3).", "Draw exterior walls then partitions (4).", "Place doors and windows (5).", "Create the rooms and their areas (6).",
      "Add stairs and furniture (7, 8).", "Hatch materials and sections (9).", "Dimension, annotate, symbols (10, 11).", "Lay out the sheet: frame + title block (12), then Check (14).", "Export DXF / PDF / Excel (15, 16)."]
paras([f"<b>{i + 1}.</b> {t}" for i, t in enumerate(fr)], M, H - 24 * mm, CW, 10, False); paras([f"<b>{i + 1}.</b> {t}" for i, t in enumerate(en)], M + CW + GAP, H - 24 * mm, CW, 10, False); footer("Workflow"); c.showPage()

for n, (sid, (tfr, ten), (bfr, ben), (cfr, cen)) in enumerate(STEPS, 1):
    band(tfr, ten, n)
    for col, (bul, cap, lang) in enumerate(((bfr, cfr, "fr"), (ben, cen, "en"))):
        x = M + col * (CW + GAP); y = paras(bul, x, H - 24 * mm, CW, 8.6); key = "pdfpreview" if sid == "s16_export" else sid
        yb = image(os.path.join(SHOTS, lang, key + ".png"), x, min(y, H - 34 * mm) - 1 * mm, CW)
        c.setFont("DVI", 7.5); c.setFillColor(GREY); c.drawString(x, yb - 4 * mm, "▲ " + cap)
    footer(f"{n}/{len(STEPS)}"); c.showPage()

band("Raccourcis clavier et souris", "Keyboard and mouse shortcuts")
rows = [("F8", "Mode orthogonal", "Ortho mode"), ("F3", "Accrochage aux objets", "Object snap"), ("F7", "Accrochage à la grille", "Grid snap"), ("Ctrl+Z / Ctrl+Y", "Annuler / Rétablir", "Undo / Redo"),
        ("Ctrl+S / Ctrl+O / Ctrl+N", "Enregistrer / Ouvrir / Nouveau", "Save / Open / New"), ("Suppr", "Effacer la sélection", "Erase selection"), ("Échap", "Annuler l'outil, désélectionner", "Cancel tool, deselect"),
        ("Entrée / Espace", "Terminer ou répéter l'outil précédent", "Finish or repeat the previous tool"), ("Molette", "Zoom centré sur le curseur", "Zoom at cursor"), ("Bouton du milieu (glisser)", "Déplacer la vue", "Pan the view"),
        ("R (outil Mobilier)", "Pivoter de 90°", "Rotate by 90°"), ("Clic droit / double-clic", "Terminer un mur, une polyligne", "Finish a wall, a polyline"),
        ("Chiffres + Entrée", "Distance exacte dans la direction du curseur", "Exact distance along cursor direction"), ("x;y   @dx,dy   d<angle", "Coordonnées absolues, relatives, polaires", "Absolute, relative, polar coordinates")]
data = [[Paragraph("<b>Touche / Key</b>", st(8.5)), Paragraph("<b>Français</b>", st(8.5)), Paragraph("<b>English</b>", st(8.5))]] + [[a, Paragraph(b, st(8.5)), Paragraph(e, st(8.5))] for a, b, e in rows]
t = Table(data, colWidths=[55 * mm, 100 * mm, 100 * mm]); t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), LIGHT), ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#aaaaaa")), ("FONTNAME", (0, 1), (0, -1), "DVB"), ("FONTSIZE", (0, 0), (0, -1), 8.5), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
t.wrapOn(c, W, H); t.drawOn(c, M, H - 24 * mm - t._height); footer("Shortcuts"); c.showPage()
band("Questions fréquentes", "Frequently asked questions")
fr = ["<b>Mon antivirus signale le programme ?</b> Un exécutable non signé peut être signalé à tort. Ajoutez le dossier d'installation aux exclusions ou demandez la version signée.",
      "<b>Le DXF s'ouvre à la mauvaise échelle ?</b> Le DXF est en millimètres (INSUNITS = 4). Dans AutoCAD, vérifiez l'unité du dessin ou utilisez _SCALE avec le facteur adapté.",
      "<b>Les textes sont trop petits / grands ?</b> Les textes sont en mm papier × échelle. Changez l'échelle dans Projet > Paramètres.",
      "<b>Je change d'ordinateur ?</b> La licence est liée à la machine : écrivez au support avec le nouveau code machine pour obtenir une nouvelle clé.",
      "<b>Comment sauvegarder ?</b> Fichier > Enregistrer (.bpl). Copiez vos fichiers régulièrement sur une clé USB ou un cloud.", f"<b>Support</b> : {SUPPORT_EMAIL}  |  WhatsApp {SUPPORT_WHATSAPP}."]
en = ["<b>My antivirus flags the program?</b> An unsigned executable may be flagged by mistake. Add the install folder to the exclusions or ask for the signed build.",
      "<b>The DXF opens at the wrong scale?</b> The DXF is in millimetres (INSUNITS = 4). In AutoCAD, check the drawing unit or use _SCALE with the right factor.",
      "<b>Text is too small / large?</b> Text is paper mm × scale. Change the scale in Project > Settings.",
      "<b>I change computer?</b> The licence is machine-bound: write to support with the new machine code to get a new key.",
      "<b>How do I back up?</b> File > Save (.bpl). Copy your files regularly to a USB drive or cloud.", f"<b>Support</b>: {SUPPORT_EMAIL}  |  WhatsApp {SUPPORT_WHATSAPP}."]
paras(fr, M, H - 24 * mm, CW, 9); paras(en, M + CW + GAP, H - 24 * mm, CW, 9); footer("FAQ"); c.showPage(); c.save(); print("pdf pages", page[0])
