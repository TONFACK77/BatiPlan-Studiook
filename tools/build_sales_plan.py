# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdf_common
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from batiplan.brand import APP_NAME, APP_VERSION

OUT = sys.argv[1]; TMP = os.path.dirname(OUT)
NAVY, LIGHT, GREY = HexColor("#18365e"), HexColor("#eef2f8"), HexColor("#555555")
S = lambda n, sz, col="#222222", font="DV", **k: ParagraphStyle(n, fontName=font, fontSize=sz, leading=sz * 1.38, textColor=HexColor(col), **k)
H1, H2, B, SM = S("h1", 17, "#18365e", "DVB", spaceBefore=4, spaceAfter=6), S("h2", 11.5, "#18365e", "DVB", spaceBefore=8, spaceAfter=3), S("b", 9.2), S("sm", 8, "#555555")
BUL = S("bul", 9.2, leftIndent=11, bulletIndent=1)
P = lambda t, st=B: Paragraph(t, st)
def bl(items): return [Paragraph(t, BUL, bulletText="•") for t in items]
def tbl(rows, widths, fs=8.2):
    data = [[Paragraph(str(c), S("c", fs, font="DVB" if i == 0 else "DV")) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1)
    sty = [("GRID", (0, 0), (-1, -1), 0.3, HexColor("#b0b8c4")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("BACKGROUND", (0, 0), (-1, 0), LIGHT)]
    for i in range(2, len(rows), 2): sty.append(("BACKGROUND", (0, i), (-1, i), HexColor("#f8f9fb")))
    t.setStyle(TableStyle(sty)); return t
def box(items):
    t = Table([[bl(items)]], colWidths=[174 * mm]); t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("BOX", (0, 0), (-1, -1), 0.6, NAVY), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)])); return t

sc = {"Prudent": (4000, 0.03, 48000), "Réaliste": (10000, 0.04, 50000), "Ambitieux": (25000, 0.05, 52000)}
rev = {k: v[0] * v[1] * v[2] / 1e6 for k, v in sc.items()}; sales = {k: v[0] * v[1] for k, v in sc.items()}
fig, ax = plt.subplots(figsize=(7.2, 3.0)); bars = ax.bar(list(rev), list(rev.values()), color=["#7f9cc4", "#18365e", "#e0a030"])
for b, (k, v) in zip(bars, rev.items()): ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.1f} M XAF\n{int(sales[k])} licences", ha="center", fontsize=9)
ax.set_ylabel("Chiffre d'affaires 12 mois (M XAF)"); ax.set_ylim(0, max(rev.values()) * 1.3); ax.spines[["top", "right"]].set_visible(False); ax.set_title("Scénarios à 12 mois (hypothèses à valider à J+30)", fontsize=10)
fig.tight_layout(); fig.savefig(TMP + "/_sc.png", dpi=160); plt.close(fig)
fig, ax = plt.subplots(figsize=(7.2, 2.6)); st = ["Personnes touchées\n(contenu)", "Essais téléchargés", "Démos / échanges", "Achats"]; vals = [100, 22, 9, 4]
for i, v in enumerate(vals): ax.barh(len(st) - 1 - i, v, color="#18365e", alpha=1 - i * 0.18); ax.text(v + 1, len(st) - 1 - i, f"{v}  ", va="center", fontsize=9)
ax.set_yticks(range(len(st))); ax.set_yticklabels(st[::-1], fontsize=9); ax.set_xlim(0, 125); ax.set_xlabel("Pour 100 prospects qualifiés (indice - hypothèse de départ)"); ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(TMP + "/_fn.png", dpi=160); plt.close(fig)

def deco(c, d):
    c.saveState(); c.setFont("DV", 7.5); c.setFillColor(GREY); c.line(18 * mm, 12 * mm, 192 * mm, 12 * mm)
    c.drawString(18 * mm, 8 * mm, f"{APP_NAME} - Plan de vente v1.0 - CONFIDENTIEL (usage vendeur)"); c.drawRightString(192 * mm, 8 * mm, f"Page {d.page}"); c.restoreState()
doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=17 * mm, title=f"{APP_NAME} - Plan de vente", author="BatiPlan")
E = []
cov = Table([[Paragraph(f"<font color='white' size='30'><b>{APP_NAME}</b></font><br/><font color='#bcd0ea' size='15'>Plan de vente détaillé</font><br/><br/><font color='white' size='11'>Version {APP_VERSION} - lancement et 12 premiers mois<br/>Marché cible : Cameroun, Afrique francophone, puis international (FR / EN)</font>", S("cv", 11))]], colWidths=[174 * mm], rowHeights=[70 * mm])
cov.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY), ("LEFTPADDING", (0, 0), (-1, -1), 14), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")])); E += [cov, Spacer(1, 8 * mm)]
E += [P("1. Résumé exécutif", H1), box([
    "<b>Produit</b> : logiciel de dessin d'architecture autonome (Windows), bilingue FR/EN, hors ligne : axes, murs, portes, fenêtres, escaliers, mobilier, pièces et surfaces, cotation, hachures, cartouches A0-A4, métrés Excel, export DXF (AutoCAD) et PDF à l'échelle.",
    "<b>Promesse</b> : « Un plan d'architecture professionnel en quelques heures, à moins d'un sixième du prix d'AutoCAD LT, avec tutoriel et support en français. »",
    "<b>Cibles prioritaires</b> : dessinateurs et architectes indépendants, petits bureaux d'études et constructeurs, étudiants et écoles du BTP.",
    "<b>Offre</b> : essai gratuit 14 jours puis licence perpétuelle à partir de 25 000 XAF (Starter) ou 65 000 XAF (Pro) ; packs Cabinet et École ; lancement à 45 000 XAF pour les 50 premiers acheteurs.",
    "<b>Mécanique de vente</b> : contenu vidéo sur Facebook / WhatsApp / YouTube, téléchargement de l'essai, démonstration courte, paiement Mobile Money, envoi du code machine, clé de licence livrée en moins d'une heure.",
    "<b>Objectif 12 mois</b> : 120 (prudent), 400 (réaliste) à 1 250 (ambitieux) licences, soit 5,8 à 65 M XAF. Seuil de rentabilité : environ 35 ventes.",
    "<b>7 premiers jours</b> : valider le nom de marque, compiler et signer l'installateur, ouvrir la page de vente et le canal WhatsApp, recruter 15 bêta-testeurs, publier la vidéo de démonstration."]), Spacer(1, 3 * mm),
      P("<b>Important - ce que ce plan suppose</b> : les chiffres de marché, de conversion et de coûts sont des <b>hypothèses de départ</b> à confirmer par vos 30 premiers jours de vente. Les prix des concurrents sont des ordres de grandeur relevés dans des annonces publiques de 2026 (par exemple AutoCAD LT : environ 540 USD par an en prix catalogue, avec des promotions autour de 199 USD la première année) : vérifiez-les avant de communiquer.", SM), PageBreak()]
E += [P("2. Le produit : ce qui est vendu, et ce qui ne l'est pas encore", H1),
      P("<b>Valeur centrale</b> : dessiner vite un plan juste et propre. Le logiciel calcule les surfaces, découpe les murs aux ouvertures, nettoie les jonctions, met les textes et cotes à l'échelle, et produit des fichiers que les confrères ouvrent dans AutoCAD, BricsCAD, GstarCAD, ZWCAD ou LibreCAD."), Spacer(1, 2 * mm),
      tbl([["Famille de fonctions", "Contenu de la version 1.0", "Statut"],
           ["Système et paramètres", "Langue FR/EN, unités mm/cm/m, échelle, cartouches A0-A4, calques normalisés, accrochages, saisie au clavier", "Inclus"],
           ["Trame et gros œuvre", "Axes et trame, murs (justification, jonctions nettoyées), murs rectangulaires, poteaux (5 formes)", "Inclus"],
           ["Menuiseries", "Portes simple / double / coulissante, fenêtres avec allège, repères auto, découpe des murs", "Inclus"],
           ["Composants", "Escalier droit / L / U avec contrôle de Blondel", "Inclus"], ["Décoration", "23 objets (lits, canapés, tables, WC, lavabo, douche, cuisine, voiture…)", "Inclus"],
           ["Symboles", "Nord, niveau, repère d'axe, coupe, pente, détail, légende, coupure, axe de symétrie", "Inclus"],
           ["Statistiques et métrés", "Surfaces des pièces, emprise, portes / fenêtres / mobilier, export Excel et CSV", "Inclus"],
           ["Textes et cotes", "Textes multilignes normalisés, cotes alignées et en série", "Inclus"],
           ["Modifier et contrôler", "Déplacer, copier, pivoter, miroir, effacer, annuler / rétablir, vérification du dessin et correction", "Inclus"],
           ["Hachures", "14 motifs vectoriels originaux (béton, brique, terre, isolant, bois…)", "Inclus"], ["Échanges", "Import DXF en fond de plan ; export DXF, PDF à l'échelle, PNG", "Inclus"],
           ["À venir (feuille de route)", "Export DWG natif, cotes DIMENSION éditables, multi-niveaux, coupes et façades automatiques, impression multi-feuilles, plugin AutoCAD", "v1.1 - v2.0"]], [38, 116, 20]),
      Spacer(1, 3 * mm), P("<b>Honnêteté commerciale</b> : le produit est un logiciel de dessin autonome, pas un module greffé sur AutoCAD. Dites-le clairement dans toute communication : les plans s'échangent en DXF ; le DWG natif est annoncé pour la version suivante. Cette transparence évite les remboursements.")]
E += [PageBreak(), P("3. Positionnement et concurrence", H1),
      tbl([["Alternative", "Prix indicatif (annonces 2026)", "Forces", "Faiblesses pour votre cible"],
           ["AutoCAD LT", "≈ 540 USD / an (catalogue) ; promos ≈ 199 USD la 1re année", "Standard du marché, DWG natif", "Abonnement en devises, cher pour un indépendant, interface en anglais surtout"],
           ["GstarCAD / BricsCAD", "Licences perpétuelles, plusieurs centaines d'USD (selon revendeurs)", "Compatibles DWG, familiers", "Prix et achat à l'étranger, peu de support local"],
           ["LibreCAD / FreeCAD", "Gratuit", "Libre, gratuit", "Pas d'outils d'architecture prêts à l'emploi, courbe d'apprentissage"],
           ["Versions piratées", "Gratuit (illégal)", "Déjà installées", "Virus, pas de mises à jour, risque juridique pour un cabinet"],
           [f"<b>{APP_NAME}</b>", "<b>à partir de 25 000 XAF, paiement unique</b>", "Outils d'archi prêts à l'emploi, FR/EN, hors ligne, tutoriel, support WhatsApp", "Pas de DWG natif en v1.0 (DXF)"]], [30, 48, 46, 50]),
      Spacer(1, 3 * mm), P("<b>Phrase de positionnement</b> : « Le logiciel de plan d'architecture fait pour les dessinateurs et constructeurs francophones : simple, rapide, abordable, avec un vrai support. »"), P("<b>Réponses aux objections fréquentes</b>", H2)] + bl([
          "« J'ai déjà AutoCAD (piraté) » : vous gagnez du temps (murs, portes, pièces, métrés en un clic), vous travaillez légalement et vous exportez en DXF vers votre AutoCAD.",
          "« C'est trop cher » : un seul plan facturé rembourse la licence ; l'essai de 14 jours est gratuit ; paiement en deux fois possible sur les packs.",
          "« Et si mon ordinateur tombe en panne ? » : la clé est rééditée gratuitement une fois par an sur présentation du nouveau code machine.",
          "« Mes clients veulent du DWG » : le DXF s'ouvre partout ; ils l'enregistrent en DWG en un clic. Le DWG natif est prévu."]) + [PageBreak()]
E += [P("4. Clients cibles et personas", H1),
      tbl([["Persona", "Besoin", "Objection", "Offre et canal"],
           ["<b>Dessinateur / architecte indépendant</b> (20-45 ans)", "Produire plans, façades, permis rapidement ; sortir des PDF propres à l'échelle", "Prix, peur de changer d'outil", "Pro 65 000 XAF ; vidéos Facebook, démonstration WhatsApp"],
           ["<b>Petit bureau d'études / entreprise BTP</b> (3-10 postes)", "Uniformiser les plans, métrés rapides, former les juniors", "Compatibilité avec AutoCAD, support", "Pack Cabinet 5 postes 250 000 XAF ; visite ou visio, démonstration sur leurs plans"],
           ["<b>Étudiants et écoles du BTP</b>", "Apprendre à dessiner un plan complet, rendre des projets", "Budget", "Édition École 15 000 XAF / étudiant ; licence laboratoire 150 000 XAF ; ambassadeurs de promotion"],
           ["<b>Constructeur, promoteur, artisan</b>", "Plans simples pour devis et clients, surfaces et quantités", "Complexité des logiciels CAD", "Starter 25 000 XAF ; formation d'une demi-journée payante"]], [38, 46, 36, 54]), Spacer(1, 3 * mm),
      P("<b>Ordre de grandeur du marché (à vérifier)</b> : estimez le nombre de dessinateurs, bureaux et étudiants du BTP dans vos 3 premiers pays à partir des annuaires d'ordres professionnels, des effectifs d'écoles et de vos propres audiences. Une approche par le bas est plus fiable : <b>1 % de vos abonnés actifs qui achètent = votre premier chiffre d'affaires</b>."),
      P("5. Offre, prix et règles commerciales", H1),
      tbl([["Édition", "Contenu", "Prix XAF (≈ EUR)", "Mises à jour"],
           ["Starter", "Dessin, murs, ouvertures, cotes, export DXF et PNG ; 7 objets de mobilier, 4 hachures", "25 000 (≈ 38 €)", "6 mois"],
           ["<b>Pro</b>", "Toutes les fonctions : PDF à l'échelle, métrés Excel, escaliers, 23 objets, 14 hachures, import DXF, contrôle", "<b>65 000 (≈ 99 €)</b>", "12 mois"],
           ["Cabinet (5 postes)", "5 licences Pro, une facture, support prioritaire", "250 000 (≈ 381 €)", "12 mois"], ["École / Étudiant", "Mêmes fonctions que Pro, sur justificatif d'inscription", "15 000 (≈ 23 €)", "12 mois"],
           ["École - laboratoire", "Clé valable sur tout le laboratoire (jusqu'à 20 postes), contrat écrit", "150 000 (≈ 229 €)", "12 mois"], ["Renouvellement mises à jour", "Nouvelles versions pendant 12 mois", "20 000 (≈ 30 €)", "-"]], [32, 80, 38, 24]), Spacer(1, 2 * mm)] + bl([
          "<b>Licence perpétuelle</b> liée à un ordinateur ; changement de machine : une réémission gratuite par an.",
          "<b>Offre de lancement</b> : Pro à 45 000 XAF pour les 50 premiers acheteurs (compte à rebours public) ; ensuite prix normal. Ne baissez jamais le prix en continu : proposez plutôt des bonus (formation, modèles de cartouches).",
          "<b>Garantie satisfait ou remboursé 14 jours</b> sur présentation d'un motif : elle rassure et coûte peu quand l'essai est gratuit.",
          "<b>Prix international</b> : Pro 99 € / 119 USD, Starter 39 €. Vendez via un paiement carte (Paddle, Lemon Squeezy ou Stripe selon pays) ; vérifiez commissions et TVA.",
          "<b>Paiement local</b> : MTN MoMo, Orange Money, virement ; confirmez le paiement avant d'émettre la clé."]) + [PageBreak()]
E += [P("6. Économie du projet", H1), Image(TMP + "/_sc.png", width=165 * mm, height=165 * mm * 3.0 / 7.2), Spacer(1, 2 * mm),
      tbl([["Scénario", "Essais téléchargés", "Conversion", "Panier moyen", "Licences", "CA 12 mois"], ["Prudent", "4 000", "3 %", "48 000 XAF", "120", "5,8 M XAF"],
           ["Réaliste", "10 000", "4 %", "50 000 XAF", "400", "20 M XAF"], ["Ambitieux", "25 000", "5 %", "52 000 XAF", "1 250", "65 M XAF"]], [28, 32, 24, 32, 24, 34]),
      Spacer(1, 3 * mm), P("<b>Coûts de la première année (estimation)</b>", H2),
      tbl([["Poste", "Estimation XAF", "Remarque"], ["Certificat de signature de code (installateur sans alerte antivirus)", "≈ 150 000 - 250 000", "À vérifier chez l'autorité de certification"],
           ["Nom de domaine, page de vente, e-mail", "≈ 60 000", "Hébergement simple suffisant"], ["Publicité Facebook / WhatsApp (test puis montée en charge)", "≈ 600 000", "Commencez à 3 000 XAF / jour pendant 14 jours"],
           ["Matériel de contenu (micro, logiciel de capture)", "≈ 100 000", "Les vidéos peuvent être faites avec l'écran seul"], ["Marque, comptabilité, juridique", "≈ 300 000 - 600 000", "Voir section 12"],
           ["<b>Total</b>", "<b>≈ 1,3 à 1,6 M XAF</b>", "Hors votre temps"]], [88, 40, 46]), Spacer(1, 2 * mm),
      P("<b>Seuil de rentabilité</b> : avec un panier moyen d'environ 48 000 XAF et 3 % de frais de paiement (hypothèse à vérifier auprès des opérateurs), il faut <b>environ 35 ventes</b> pour couvrir 1,6 M XAF. Chaque vente supplémentaire apporte environ 46 500 XAF de marge brute, hors temps de support (≈ 20 minutes par vente)."), PageBreak()]
E += [P("7. Canaux et acquisition", H1), Image(TMP + "/_fn.png", width=165 * mm, height=165 * mm * 2.6 / 7.2), Spacer(1, 2 * mm),
      tbl([["Canal", "Actions concrètes", "Fréquence", "Indicateur"],
           ["<b>Page Facebook « BTP PRO CAMEROUN »</b> et groupes BTP", "Vidéos de 30-60 s « plan en 5 minutes », avant / après, astuces ; épingler l'offre d'essai ; réponses aux commentaires par messagerie", "5 posts / semaine", "Clics vers l'essai, messages reçus"],
           ["<b>WhatsApp</b> (communautés + statut)", "Communauté « BatiPlan Club » : conseils, mises à jour, démonstrations en direct ; liste de diffusion", "3 messages / semaine", "Inscrits, démos réservées"],
           ["<b>YouTube / TikTok</b>", "Découper la vidéo tutoriel en 17 courtes vidéos (une par étape) ; titres en FR et EN", "2 vidéos / semaine", "Vues, téléchargements d'essai"],
           ["<b>Écoles et universités</b> (dont ENSTP)", "Séance de présentation gratuite, concours de plans, licence laboratoire, ambassadeur étudiant par promotion (10 % de commission)", "1 école / mois", "Licences École, ambassadeurs actifs"],
           ["<b>Cabinets et entreprises</b>", "Démonstration sur leurs plans, devis Cabinet, formation d'une demi-journée", "10 visites / mois", "Devis envoyés, signés"],
           ["<b>Revendeurs / formateurs</b>", "Commission 20 % sur les ventes, kit de présentation, licence de démonstration", "Recrutement continu", "Ventes par revendeur"],
           ["<b>LinkedIn</b>", "Études de cas, posts « avant / après » pour la clientèle d'entreprises et l'international", "2 posts / semaine", "Demandes de démo"]], [32, 80, 26, 36]), PageBreak()]
E += [P("8. Processus de vente et de livraison", H1),
      tbl([["#", "Étape", "Qui / comment", "Délai cible"], ["1", "Le prospect télécharge l'essai (lien sur la page de vente, installateur signé)", "Automatique", "-"],
           ["2", "Contact WhatsApp : question sur le besoin, envoi du tutoriel PDF et de la vidéo", "Vous / un assistant", "< 2 h"], ["3", "Démonstration de 15 minutes (visio ou capture écran)", "Vous", "< 48 h"],
           ["4", "Devis ou lien de paiement (MoMo / Orange Money / carte)", "Vous", "Immédiat"], ["5", "Le client envoie son <b>code machine</b> (Aide > Licence) avec la preuve de paiement", "Client", "-"],
           ["6", "Vous générez la clé avec <b>keygen.py</b> et l'enregistrez dans le registre des licences", "Vous (2 minutes)", "< 1 h"],
           ["7", "Envoi de la clé + facture + lien vers le tutoriel ; le client colle la clé et clique Activer", "Vous", "< 1 h"], ["8", "Suivi à J+3 (aide à la prise en main) et à J+30 (retour d'expérience, avis, parrainage)", "Vous", "-"]], [8, 100, 40, 26]),
      Spacer(1, 3 * mm), P("<b>Règles de sécurité de la licence</b>", H2)] + bl([
          "Conservez <b>private_key.pem</b> hors de l'ordinateur de vente (clé USB chiffrée + sauvegarde) : sa perte empêcherait d'émettre des clés, sa fuite permettrait d'en fabriquer.",
          "Tenez le registre <b>licences_log.csv</b> (date, client, e-mail, édition, code machine, montant, mode de paiement) à jour pour chaque clé émise.",
          "Ne distribuez jamais le dossier du code source aux clients : livrez uniquement l'installateur compilé et signé."]) + [
      P("9. Plan de lancement sur 90 jours", H1),
      tbl([["Période", "Objectifs", "Actions clés"],
           ["Semaines -2 à 0 (préparation)", "Produit prêt, preuves sociales", "Compiler et signer l'installateur ; tester sur 5 PC (Windows 10 et 11) ; page de vente ; 15 bêta-testeurs avec licence gratuite contre avis et plans réels ; relire le tutoriel"],
           ["Semaines 1-2 (lancement)", "50 essais, 10 premières ventes", "Annonce Facebook + WhatsApp ; vidéo de démonstration ; offre de lancement à 45 000 XAF (50 places) ; 3 démonstrations en direct"],
           ["Semaines 3-6 (traction)", "300 essais, 40 ventes cumulées", "Une vidéo par étape du tutoriel ; témoignages des bêta-testeurs ; première école partenaire ; publicité test 3 000 XAF / jour ; mesurer la conversion"],
           ["Semaines 7-10 (accélération)", "800 essais, 90 ventes cumulées", "Programme ambassadeurs ; 5 revendeurs ; pack Cabinet ; webinaire « plan complet en 1 heure » ; correction des bugs remontés (v1.0.1)"],
           ["Semaines 11-13 (consolidation)", "1 200 essais, 140 ventes cumulées", "Version 1.1 (retours clients) ; enquête de satisfaction ; offre de renouvellement ; décider les investissements (certificat, publicité, DWG)"]], [38, 40, 96]), PageBreak()]
E += [P("10. Messages et contenus", H1),
      tbl([["Usage", "Français", "English"], ["Slogan", "Votre plan d'architecture, du premier trait à l'impression.", "Your architectural plan, from first line to print."],
           ["Accroche Facebook", "Un plan de villa complet en 30 minutes : murs, portes, surfaces, cotes, cartouche. Essai gratuit 14 jours.", "A full villa plan in 30 minutes: walls, doors, areas, dimensions, title block. Free 14-day trial."],
           ["Argument prix", "Moins d'un sixième du prix d'AutoCAD LT par an, paiement unique, support en français.", "Under a sixth of AutoCAD LT's yearly price, one-time payment, French and English support."],
           ["Appel à l'action", "Téléchargez l'essai et envoyez-nous « DÉMO » sur WhatsApp.", "Download the trial and message us “DEMO” on WhatsApp."]], [28, 73, 73]),
      Spacer(1, 2 * mm), P("<b>Douze idées de contenu</b> (un format = une vidéo courte) :", H2)] + bl([
          "« Dessiner un mur à distance exacte en tapant la longueur » ; « Poser 5 portes en 30 secondes » ; « Surfaces des pièces en un clic » ; « Escalier : le contrôle Blondel expliqué ».",
          "« Du plan au PDF à l'échelle 1:50 sur A3 » ; « Ouvrir votre plan dans AutoCAD » ; « Le métré portes et fenêtres vers Excel » ; « Les 14 hachures de matériaux ».",
          "« Avant / après : un plan de maison refait en 1 heure » ; « 3 erreurs de cotation à éviter » ; « Plan d'un magasin / bureau : étude de cas » ; « Questions des abonnés en direct »."]) + [
      P("11. Support, mises à jour et fidélisation", H1)] + bl([
          "<b>Support</b> : WhatsApp et e-mail, du lundi au samedi ; réponse sous 4 h ouvrées ; modèles de réponse prêts pour les 10 questions les plus fréquentes (voir FAQ du tutoriel).",
          "<b>Mises à jour</b> : une version corrective après 4-6 semaines, une version 1.1 à 3 mois ; les clients dans la période de mises à jour reçoivent l'installateur gratuitement.",
          "<b>Fidélisation</b> : « BatiPlan Club » (communauté), parrainage (1 mois de mises à jour offert par filleul), enquête NPS à J+30, bibliothèque de modèles de cartouches et de plans types.",
          "<b>Mesure</b> : suivez chaque semaine essais, ventes, remboursements, tickets de support, avis ; décidez les priorités de la prochaine version à partir des demandes les plus fréquentes."]) + [PageBreak()]
E += [P("12. Juridique, conformité et propriété", H1)] + bl([
          "<b>Contrat d'utilisation (EULA)</b> FR/EN fourni dans le dossier produit : à faire relire par un juriste du pays de vente (droit OHADA / droit local) avant le lancement.",
          "<b>Marque et nom</b> : « BatiPlan Studio » est un nom de travail. Avant d'investir, faites une recherche d'antériorité (par exemple auprès de l'OAPI pour l'Afrique francophone) et déposez la marque et le logo ; le nom se change en un seul fichier (batiplan/brand.py).",
          "<b>Droit d'auteur du logiciel</b> : conservez les sources, l'historique de développement et déposez le logiciel auprès de l'organisme de droit d'auteur de votre pays ; mettez votre nom ou celui de votre société dans brand.py et l'EULA.",
          "<b>Entité et fiscalité</b> : vendez via une entité déclarée (entreprise individuelle ou société) pour facturer les cabinets et écoles ; demandez conseil à un comptable (TVA, impôt, facture électronique).",
          "<b>Données personnelles</b> : le logiciel fonctionne hors ligne et ne transmet aucune donnée ; vous ne stockez que les informations de licence (nom, e-mail, code machine) : déclarez-le dans votre politique de confidentialité.",
          "<b>Composants tiers</b> : le produit utilise Python et des bibliothèques open source (ezdxf, Shapely, Matplotlib, openpyxl, Pillow, cryptography, Tk). Le fichier THIRD_PARTY_NOTICES.txt est à livrer avec le produit.",
          f"<b>Origine du code - point d'attention</b> : {APP_NAME} est une <b>œuvre originale</b>. Elle ne réutilise ni code, ni fichiers, ni bibliothèques de blocs, ni textes, ni icônes du logiciel gratuit YQArch ou d'un autre logiciel. N'utilisez pas leurs noms dans votre marketing et ne prétendez à aucune compatibilité ni affiliation. Si vous souhaitez un jour intégrer des contenus de tiers, obtenez leur autorisation écrite."]) + [
      P("13. Risques et parades", H1),
      tbl([["Risque", "Impact", "Parade"],
           ["Piratage de l'installateur ou contournement de la licence", "Ventes perdues", "Licence signée liée à la machine (déjà en place) ; compilation Nuitka et obscurcissement ; prix accessibles ; valeur du support, des mises à jour et des formations ; actions ciblées sur les revendeurs de copies"],
           ["Alerte antivirus sur un exécutable non signé", "Perte de confiance", "Certificat de signature de code ; fournir un lien de vérification ; liste blanche auprès des éditeurs d'antivirus"],
           ["Attentes irréalistes (DWG, 3D, BIM)", "Remboursements, mauvais avis", "Transparence sur le périmètre v1.0 (section 2) ; essai gratuit ; feuille de route publique"],
           ["Bogues sur des configurations Windows variées", "Support débordé", "Bêta-testeurs sur 5 types de PC ; version corrective rapide"],
           ["Concurrent gratuit ou promotion Autodesk", "Pression sur le prix", "Miser sur l'expérience (outils d'archi prêts à l'emploi, FR, support local) ; ne pas baisser le prix de base, offrir des bonus"],
           ["Perte de private_key.pem", "Impossible d'émettre des clés", "Sauvegardes chiffrées multiples ; ne jamais envoyer la clé par messagerie"],
           ["Dépendance à une seule personne (vous)", "Retards de livraison des clés", "Documenter le processus ; former un assistant ; SLA clairs"]], [48, 30, 96]), PageBreak()]
E += [P("14. Feuille de route produit orientée ventes", H1),
      tbl([["Version", "Contenu", "Raison commerciale"], ["1.0.1 (S+4)", "Corrections issues des bêta-testeurs, installateur signé", "Réduire les remboursements"],
           ["1.1 (T+3 mois)", "Export DWG (via bibliothèque sous licence appropriée), cotes DIMENSION éditables, bibliothèque de blocs personnalisés, plus de mobilier", "Argument « compatible DWG » pour les cabinets"],
           ["1.2 (T+6 mois)", "Multi-niveaux (étages), coupes et façades à partir du plan, impression multi-feuilles, modèles de cartouches", "Passage de dessinateurs à bureaux d'études"],
           ["2.0 (T+12 mois)", "Plugin pour AutoCAD / BricsCAD, rendu 3D simple, quantitatifs détaillés (BPU), version macOS", "Élargir le marché et vendre des mises à niveau"]], [26, 100, 48]), Spacer(1, 3 * mm),
      P("15. Tableau de bord hebdomadaire (KPI)", H1),
      tbl([["Indicateur", "Objectif mois 1", "Objectif mois 3", "Objectif mois 12"], ["Essais téléchargés", "300", "1 200", "10 000"], ["Taux de conversion essai → achat", "3 %", "4 %", "4 %"],
           ["Licences vendues (cumul)", "20", "140", "400"], ["Chiffre d'affaires cumulé (M XAF)", "1,1", "7", "20"], ["Taux de remboursement", "< 5 %", "< 4 %", "< 3 %"],
           ["Délai moyen de livraison de la clé", "< 2 h", "< 1 h", "< 1 h"], ["Satisfaction (NPS)", "> 30", "> 40", "> 50"]], [66, 36, 36, 36]), Spacer(1, 3 * mm),
      P("16. Liste de contrôle avant la première vente", H1)] + bl([
          "☐ Nom de marque vérifié, logo final, brand.py renseigné (société, e-mail, WhatsApp, site).", "☐ Installateur compilé sur Windows, testé sur au moins 5 ordinateurs (Windows 10 et 11), signé si possible.",
          "☐ tools/make_keys.py exécuté UNE seule fois ; private_key.pem sauvegardée en 3 endroits ; clé publique intégrée avant compilation (ne pas régénérer ensuite).",
          "☐ keygen.py testé : une clé émise active bien un ordinateur de test ; registre licences_log.csv créé.", "☐ EULA relu par un juriste ; politique de confidentialité ; conditions de remboursement publiées.",
          "☐ Page de vente (essai, prix, tutoriel, contact), compte MoMo / Orange Money professionnel, modèle de facture.", "☐ Tutoriel PDF et vidéo mp4 publiés ; messages WhatsApp et réponses types prêts (dossier seller_kit).",
          "☐ 15 bêta-testeurs recrutés et premiers témoignages ; plan de contenu des 30 premiers jours rédigé."]) + [PageBreak()]
E += [P("Annexe - Executive summary (English)", H1), box([
    f"<b>Product</b>: {APP_NAME}, a stand-alone Windows architectural drafting program, bilingual (French / English), fully offline: axis grids, walls with cleaned junctions, doors and windows, stairs, furniture, automatic rooms and areas, dimensions, hatching, A0-A4 title blocks, Excel schedules, DXF export (AutoCAD-compatible) and true-scale PDF.",
    "<b>Promise</b>: a professional plan in hours, at less than one sixth of the yearly price of AutoCAD LT (list price about US$540 per year in 2026 listings), with tutorial and local-language support.",
    "<b>Targets</b>: freelance drafters and architects, small design offices and builders, students and construction schools - first in Cameroon and French-speaking Africa, then international.",
    "<b>Offer</b>: 14-day free trial, then perpetual licence - Starter 25,000 XAF (about 38 EUR), Pro 65,000 XAF (about 99 EUR), 5-seat Office pack 250,000 XAF, Student 15,000 XAF, school lab 150,000 XAF; launch price 45,000 XAF for the first 50 buyers.",
    "<b>Sales engine</b>: short videos (Facebook, WhatsApp, YouTube) -> trial download -> 15-minute demo -> Mobile Money / card payment -> customer sends machine code -> signed offline key delivered within one hour.",
    "<b>12-month scenarios</b>: 120 / 400 / 1,250 licences = 5.8 / 20 / 65 million XAF (assumptions to be validated after 30 days). Break-even about 35 sales.",
    "<b>Key risks</b>: piracy (mitigated by machine-bound signed licences, support and updates), unsigned-installer antivirus alerts (code-signing certificate), scope expectations (DXF now, native DWG planned).",
    "<b>Legal</b>: product is original work and reuses nothing from YQArch or any third-party CAD tool; check the brand name with the trademark office before launch; have the EULA reviewed locally."]),
      Spacer(1, 4 * mm), P("All figures other than the prices of the product itself are starting hypotheses or public list prices and must be checked before use.", SM)]
doc.build(E, onFirstPage=deco, onLaterPages=deco); print("sales plan ok")
