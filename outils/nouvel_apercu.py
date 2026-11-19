#!/usr/bin/env python3
"""
Crée l'aperçu privé du site d'un prospect sur Coup d'Œil, puis le publie.

Exemples :
    # À partir de la liste de prospects (nom exact ou début du nom) :
    python3 outils/nouvel_apercu.py --prospect "Longval service"

    # À la main :
    python3 outils/nouvel_apercu.py --nom "Longval Service" --metier paysagiste \
        --ville Rouen --tel "06 27 81 24 83" --dirigeant "Tom Longval"

    # Avec les photos du client (dossier de .jpg / .png / .webp) :
    python3 outils/nouvel_apercu.py --prospect "Longval service" --photos ~/Downloads/longval

Le script affiche le lien privé et le SMS prêt à envoyer, note l'aperçu dans apercus.csv,
et publie sur GitHub si le dossier est relié à un dépôt.
"""
import argparse
import csv
import datetime as dt
import glob
import html
import json
import os
import re
import secrets
import shutil
import subprocess
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELE = os.path.join(RACINE, "outils", "modele_site.html")
JOURNAL = os.path.join(RACINE, "apercus.csv")
DOSSIER_PROSPECTS = os.path.join(os.path.dirname(RACINE), "prospection")
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # sans 0/O, 1/I/L : pas de confusion au téléphone

POLICES = {
    "jardin": "family=Young+Serif&family=Figtree:wght@400;600;700",
    "atelier": "family=Archivo+Narrow:wght@700&family=Public+Sans:wght@400;600;700",
    "fournil": "family=DM+Serif+Display&family=Karla:wght@400;600;700",
}

# Contenu par métier : ambiance, titres, services, engagements, étapes, options du devis
METIERS = {
    "paysagiste": {
        "ambiance": "jardin", "titre_metier": "Paysagiste",
        "titre": "Des jardins entretenus et aménagés avec soin",
        "accroche": "Création, entretien et taille autour de {ville}. Un interlocuteur unique, du premier coup de fil au dernier coup de râteau.",
        "titre_services": "Tout votre extérieur, en un seul contact",
        "intro_services": "Particuliers, copropriétés et professionnels : on s'adapte à la taille de votre terrain et à la saison.",
        "services": [
            ("Entretien de jardin", "Tonte, désherbage, ramassage des feuilles, passages réguliers ou ponctuels."),
            ("Taille et élagage", "Haies, arbustes et arbres, avec évacuation des déchets verts."),
            ("Création et aménagement", "Massifs, gazon, plantations, allées et bordures."),
            ("Débroussaillage", "Remise en état de terrains laissés à l'abandon."),
        ],
        "engagements": ["Devis gratuit sous 48 h", "Évacuation des déchets verts", "Particuliers et professionnels", "Paiement possible en CESU selon prestation"],
        "options": ["Entretien régulier", "Taille de haie", "Élagage", "Création de jardin", "Autre"],
        "galerie": ["Haie taillée", "Massif fleuri", "Pelouse remise à neuf", "Allée en gravier", "Terrain débroussaillé", "Jardin d'été"],
    },
    "peintre": {
        "ambiance": "atelier", "titre_metier": "Peintre en bâtiment",
        "titre": "Peinture intérieure et extérieure, finitions nettes",
        "accroche": "Murs, plafonds, façades et boiseries autour de {ville}. Chantier protégé, propre et rendu à la date prévue.",
        "titre_services": "Du rafraîchissement à la rénovation complète",
        "intro_services": "Préparation des supports, peinture, revêtements : on traite chaque pièce comme si c'était chez nous.",
        "services": [
            ("Peinture intérieure", "Murs, plafonds, boiseries, préparation et rebouchage inclus."),
            ("Façades et extérieurs", "Nettoyage, traitement et mise en peinture des façades et volets."),
            ("Revêtements muraux", "Pose de papier peint, toile de verre et enduits décoratifs."),
            ("Rénovation après sinistre", "Remise en état après dégât des eaux ou fumée."),
        ],
        "engagements": ["Devis gratuit et détaillé", "Protection complète du chantier", "Délais annoncés et tenus", "Particuliers et professionnels"],
        "options": ["Peinture intérieure", "Façade", "Papier peint", "Rénovation complète", "Autre"],
        "galerie": ["Salon repeint", "Façade rénovée", "Cage d'escalier", "Chambre", "Volets", "Bureau professionnel"],
    },
    "batiment": {
        "ambiance": "atelier", "titre_metier": "Artisan du bâtiment",
        "titre": "Vos travaux faits proprement, dans les délais",
        "accroche": "Interventions et chantiers autour de {ville}. Un devis clair, un artisan joignable, un travail soigné.",
        "titre_services": "Nos interventions",
        "intro_services": "Dépannage, installation ou rénovation : décrivez votre besoin, on vous rappelle rapidement.",
        "services": [
            ("Dépannage", "Intervention rapide pour les urgences et petites réparations."),
            ("Installation", "Pose et mise en service de vos équipements neufs."),
            ("Rénovation", "Remise aux normes et modernisation de votre logement."),
            ("Entretien", "Visites régulières pour éviter les mauvaises surprises."),
        ],
        "engagements": ["Devis gratuit", "Intervention rapide", "Chantier laissé propre", "Particuliers et professionnels"],
        "options": ["Dépannage", "Installation", "Rénovation", "Entretien", "Autre"],
        "galerie": ["Chantier en cours", "Rénovation", "Installation", "Finitions", "Avant / après", "Intervention"],
    },
    "boulangerie": {
        "ambiance": "fournil", "titre_metier": "Boulangerie pâtisserie",
        "titre": "Du pain cuit sur place, chaque matin",
        "accroche": "Pains, viennoiseries et pâtisseries maison à {ville}. Commandez vos gâteaux à l'avance et passez les retirer.",
        "titre_services": "Ce qui sort de notre fournil",
        "intro_services": "Tout est fabriqué ici, avec des farines choisies et des recettes travaillées.",
        "services": [
            ("Pains", "Baguettes de tradition, pains spéciaux et pains au levain."),
            ("Viennoiseries", "Croissants pur beurre, pains au chocolat et brioches."),
            ("Pâtisseries", "Entremets, tartes de saison et gâteaux individuels."),
            ("Commandes", "Gâteaux d'anniversaire, pièces montées et plateaux pour vos événements."),
        ],
        "engagements": ["Fabrication maison", "Commandes de gâteaux à l'avance", "Ouvert le dimanche matin", "Produits de saison"],
        "options": ["Gâteau d'anniversaire", "Pièce montée", "Plateau pour événement", "Autre"],
        "galerie": ["Baguettes du matin", "Croissants", "Tarte de saison", "Entremets", "Pains spéciaux", "Vitrine"],
    },
    "beaute": {
        "ambiance": "fournil", "titre_metier": "Salon",
        "titre": "Prenez soin de vous, on s'occupe du reste",
        "accroche": "Votre salon à {ville}. Prise de rendez-vous simple, conseils personnalisés et produits de qualité.",
        "titre_services": "Nos prestations",
        "intro_services": "Des prestations pensées pour vous, dans un cadre chaleureux.",
        "services": [
            ("Coupe et coiffage", "Femmes, hommes et enfants, avec diagnostic personnalisé."),
            ("Couleur", "Coloration, mèches et balayage adaptés à votre style."),
            ("Soins", "Soins profonds et rituels de beauté."),
            ("Événements", "Mariages et cérémonies, sur rendez-vous."),
        ],
        "engagements": ["Sur rendez-vous", "Conseils personnalisés", "Produits professionnels", "Cartes cadeaux"],
        "options": ["Prise de rendez-vous", "Mariage ou événement", "Carte cadeau", "Autre"],
        "galerie": ["Le salon", "Coupe", "Couleur", "Soin", "Coiffure de mariage", "Produits"],
    },
    "menuisier": {
        "ambiance": "atelier", "titre_metier": "Menuisier",
        "titre": "Portes, fenêtres et agencements sur mesure",
        "accroche": "Menuiserie bois et alu autour de {ville}. Fabrication à l'atelier, pose soignée et conseils pour chaque pièce.",
        "titre_services": "Du sur-mesure, de l'atelier à chez vous",
        "intro_services": "On fabrique et on pose : vous avez un seul interlocuteur du devis à la finition.",
        "services": [
            ("Portes et fenêtres", "Fabrication et pose, bois ou aluminium, avec isolation renforcée."),
            ("Escaliers", "Escaliers droits, quart tournant ou suspendus, dessinés pour votre maison."),
            ("Placards et dressings", "Rangements sur mesure qui exploitent chaque centimètre."),
            ("Terrasses bois", "Terrasses, pergolas et bardages en bois durable."),
        ],
        "engagements": ["Devis gratuit sous 48 h", "Fabrication dans notre atelier", "Pose par nos soins", "Garantie sur la pose"],
        "options": ["Porte ou fenêtre", "Escalier", "Placard ou dressing", "Terrasse", "Autre"],
        "galerie": ["Escalier en chêne", "Dressing sur mesure", "Porte d'entrée", "Terrasse en pin", "Fenêtres bois", "Bibliothèque"],
    },
    "restaurant": {
        "ambiance": "fournil", "titre_metier": "Pizzeria",
        "titre": "Pizzas au feu de bois, pâte maison",
        "accroche": "À {ville}, sur place ou à emporter. Pâte reposée 48 heures, produits italiens et four à bois.",
        "titre_services": "Sur place, à emporter ou en livraison",
        "intro_services": "Commandez par téléphone, on prépare votre pizza à l'heure qui vous arrange.",
        "services": [
            ("Pizzas au feu de bois", "Une vingtaine de recettes, des classiques aux pizzas du moment."),
            ("À emporter", "Commande par téléphone, prête à l'heure annoncée."),
            ("Livraison", "Livraison dans un rayon de 5 km, le soir du mardi au dimanche."),
            ("Desserts maison", "Tiramisu, panna cotta et pizzas sucrées."),
        ],
        "engagements": ["Pâte maison reposée 48 h", "Four à bois", "Commande par téléphone", "Ouvert 6 soirs sur 7"],
        "options": ["Réserver une table", "Commander à emporter", "Événement ou groupe", "Autre"],
        "galerie": ["La Margherita", "Le four à bois", "La salle", "Calzone", "Tiramisu maison", "La terrasse"],
    },
    "garage": {
        "ambiance": "atelier", "titre_metier": "Garage automobile",
        "titre": "Entretien et réparation toutes marques",
        "accroche": "Votre garage à {ville}. Devis avant chaque intervention, délais annoncés et pièces garanties.",
        "titre_services": "Tout l'entretien de votre véhicule",
        "intro_services": "Voitures particulières et utilitaires, toutes marques, sur rendez-vous.",
        "services": [
            ("Révision et vidange", "Entretien constructeur sans perdre votre garantie."),
            ("Freinage et pneus", "Plaquettes, disques, pneus et géométrie."),
            ("Diagnostic", "Lecture des voyants et recherche de panne électronique."),
            ("Préparation au contrôle technique", "On vérifie tout avant le passage, et on s'occupe de la contre-visite."),
        ],
        "engagements": ["Devis avant intervention", "Toutes marques", "Pièces garanties", "Véhicule de prêt sur demande"],
        "options": ["Révision", "Freins ou pneus", "Diagnostic", "Contrôle technique", "Autre"],
        "galerie": ["L'atelier", "Pont élévateur", "Diagnostic", "Pneumatiques", "Utilitaire", "Accueil"],
    },
}
ALIAS = {"plombier": "batiment", "chauffagiste": "batiment", "electricien": "batiment", "macon": "batiment",
         "platrier": "batiment", "carreleur": "batiment", "couvreur": "batiment",
         "patissier": "boulangerie", "boulanger": "boulangerie", "coiffeur": "beaute", "estheticienne": "beaute",
         "pizzeria": "restaurant"}

ETAPES = [
    ("Vous nous appelez", "Ou vous remplissez le formulaire : on vous rappelle rapidement."),
    ("On vient voir", "Visite sur place, conseils et devis détaillé, gratuitement."),
    ("On réalise", "Aux dates convenues, avec un travail propre et soigné."),
]
# Textes pour les commerces (pas de « chantier » ni de visite sur place)
COMMERCE = {
    "surtitre_galerie": "En images", "titre_galerie": "Un aperçu de la maison",
    "intro_galerie": "La boutique, l'équipe et ce qu'on prépare chaque jour à {ville}.",
    "titre_etapes": "Commander, c'est simple",
    "etapes": [
        ("Vous appelez ou écrivez", "Dites-nous ce qui vous ferait plaisir et pour quand."),
        ("On prépare", "Tout est fait sur place, au dernier moment, pour être servi au mieux."),
        ("Vous passez", "À l'heure convenue : votre commande vous attend."),
    ],
}
for _cle in ("boulangerie", "restaurant", "beaute"):
    METIERS[_cle].update({k: v for k, v in COMMERCE.items() if k not in METIERS[_cle]})
METIERS["beaute"].update({"titre_etapes": "Prendre rendez-vous", "titre_galerie": "Le salon en images",
                          "etapes": [("Vous appelez", "On trouve ensemble le créneau qui vous convient."),
                                     ("On vous conseille", "Un vrai temps d'échange avant chaque prestation."),
                                     ("Vous repartez ravie", "Avec des conseils pour garder le résultat longtemps.")]})

MOTIFS = {
    "jardin": '<svg viewBox="0 0 120 120" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><defs><pattern id="m" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M20 4c9 8 9 24 0 32C11 28 11 12 20 4z" fill="none" stroke="#fff" stroke-width="1.5"/><path d="M20 8v26" stroke="#fff" stroke-width="1"/></pattern></defs><rect width="120" height="120" fill="url(#m)"/></svg>',
    "atelier": '<svg viewBox="0 0 120 120" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><defs><pattern id="m" width="24" height="24" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="10" height="24" fill="#fff"/></pattern></defs><rect width="120" height="120" fill="url(#m)"/></svg>',
    "fournil": '<svg viewBox="0 0 120 120" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><defs><pattern id="m" width="30" height="30" patternUnits="userSpaceOnUse"><ellipse cx="15" cy="15" rx="9" ry="4" fill="none" stroke="#fff" stroke-width="1.5" transform="rotate(-35 15 15)"/></pattern></defs><rect width="120" height="120" fill="url(#m)"/></svg>',
}


def e(texte):
    return html.escape(str(texte or ""), quote=True)


def charger_config():
    with open(os.path.join(RACINE, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def nouveau_code(existants):
    while True:
        code = "".join(secrets.choice(ALPHABET) for _ in range(6))
        if code not in existants:
            return code


def lire_prospect(recherche):
    fichiers = sorted(glob.glob(os.path.join(DOSSIER_PROSPECTS, "prospects_*.csv")), key=os.path.getmtime, reverse=True)
    cible = recherche.lower().strip()
    for chemin in fichiers:
        with open(chemin, encoding="utf-8-sig") as f:
            lignes = list(csv.DictReader(f))
        for exact in (True, False):
            for l in lignes:
                nom = l.get("entreprise", "").lower().strip()
                if (nom == cible) if exact else nom.startswith(cible):
                    metier = os.path.basename(chemin).split("_")[1]
                    return l, metier
    sys.exit("Prospect « %s » introuvable dans les listes de prospects." % recherche)


def joli_nom(nom):
    """BEAU JARDIN -> Beau Jardin ; garde les noms déjà en minuscules/majuscules mélangées."""
    return nom.title() if nom.isupper() or nom.islower() else nom


def construire(infos, config, code, photos_relatives, apercu=True):
    m = METIERS[infos["metier_cle"]]
    ville = infos["ville"] or "votre secteur"
    tel = infos["tel"]
    tel_lien = re.sub(r"[^\d+]", "", tel)
    if tel_lien.startswith("0"):
        tel_lien = "+33" + tel_lien[1:]
    ambiance = m["ambiance"]

    if photos_relatives:
        fond = '<div class="photo" style="background-image:url(\'%s\')"></div>' % e(photos_relatives[0])
        tuiles = ['<figure><img src="%s" alt="Réalisation de %s" loading="lazy"></figure>' % (e(p), e(infos["nom"]))
                  for p in photos_relatives[1:7] or photos_relatives[:1]]
    else:
        fond = '<div class="motif">%s</div>' % MOTIFS[ambiance]
        tuiles = ['<figure><div class="vide">%s<span>%s</span></div></figure>' % (MOTIFS[ambiance], e(t))
                  for t in m["galerie"]]

    lignes_adresse = ('<div><dt>Adresse</dt><dd>%s</dd></div>' % e(infos["adresse"])) if infos.get("adresse") else ""
    lignes_dirigeant = ('<div><dt>Votre interlocuteur</dt><dd>%s</dd></div>' % e(infos["dirigeant"])) if infos.get("dirigeant") else ""

    bandeau = ""
    if infos.get("demo"):
        bandeau = (
            '<aside class="apercu" aria-label="Site de démonstration"><div class="cadre">'
            '<span><strong>Site de démonstration</strong> · entreprise fictive · réalisé par %s</span>'
            '<span class="liens"><a href="../../index.html#realisations">Voir les autres exemples</a>'
            '<a class="secondaire" href="../../index.html#contact">Le même pour mon entreprise</a>'
            '<button type="button" id="fermer-apercu">Masquer</button></span>'
            '</div></aside>'
        ) % e(config["marque"])
    elif apercu:
        lien_sms = "sms:%s" % re.sub(r"[^\d+]", "", config["telephone_vendeur"])
        bandeau = (
            '<aside class="apercu" aria-label="Aperçu privé"><div class="cadre">'
            '<span><strong>Aperçu privé</strong> préparé pour %s par %s · %s %s</span>'
            '<span class="liens"><a href="%s">Ce site me plaît</a>'
            '<a class="secondaire" href="tel:%s">Appeler %s</a>'
            '<button type="button" id="fermer-apercu">Masquer</button></span>'
            '</div></aside>'
        ) % (e(infos["nom"]), e(config["marque"]), e(config["prix_site"]), e(config.get("abonnement", "")),
             e(lien_sms), e(re.sub(r"[^\d+]", "", config["telephone_vendeur"])), e(config["prenom_vendeur"]))

    remplacements = {
        "AMBIANCE": ambiance,
        "POLICES": POLICES[ambiance],
        "NOM": e(infos["nom"]),
        "METIER": e(m["titre_metier"].lower()),
        "METIER_TITRE": e(m["titre_metier"]),
        "VILLE": e(ville),
        "ZONE": e("%s et alentours" % ville),
        "TITRE": e(infos.get("titre") or m["titre"]),
        "ACCROCHE": e(m["accroche"].format(ville=ville)),
        "TEL": e(tel),
        "TEL_LIEN": e(tel_lien),
        "FOND_ACCROCHE": fond,
        "ENGAGEMENTS": "".join("<li>%s</li>" % e(x) for x in m["engagements"]),
        "TITRE_SERVICES": e(m["titre_services"]),
        "INTRO_SERVICES": e(m["intro_services"]),
        "SERVICES": "".join('<article class="service"><div class="marque"></div><h3>%s</h3><p>%s</p></article>'
                            % (e(t), e(d)) for t, d in m["services"]),
        "GALERIE": "".join(tuiles),
        "ETAPES": "".join("<li><h3>%s</h3><p>%s</p></li>" % (e(t), e(d)) for t, d in m.get("etapes", ETAPES)),
        "SURTITRE_GALERIE": e(m.get("surtitre_galerie", "Réalisations")),
        "TITRE_GALERIE": e(m.get("titre_galerie", "Quelques chantiers récents")),
        "INTRO_GALERIE": e(m.get("intro_galerie", "Des photos de nos interventions autour de {ville}.").format(ville=ville)),
        "TITRE_ETAPES": e(m.get("titre_etapes", "De votre appel à la fin du chantier")),
        "LIGNE_ADRESSE": lignes_adresse,
        "LIGNE_DIRIGEANT": lignes_dirigeant,
        "OPTIONS_DEVIS": "".join("<option>%s</option>" % e(o) for o in m["options"]),
        "ANNEE": str(dt.date.today().year),
        "BANDEAU_APERCU": bandeau,
    }
    with open(MODELE, encoding="utf-8") as f:
        page = f.read()
    for cle, valeur in remplacements.items():
        page = page.replace("{{%s}}" % cle, valeur)
    reste = re.findall(r"\{\{[A-Z_]+\}\}", page)
    if reste:
        sys.exit("Modèle incomplet, champs non remplis : %s" % ", ".join(sorted(set(reste))))
    return page


def publier_git(message):
    if not os.path.isdir(os.path.join(RACINE, ".git")):
        return "pas de dépôt Git : site créé en local seulement (voir LISEZMOI.md pour le mettre en ligne)"
    try:
        subprocess.run(["git", "-C", RACINE, "add", "-A"], check=True, capture_output=True)
        subprocess.run(["git", "-C", RACINE, "commit", "-m", message], check=True, capture_output=True)
        distant = subprocess.run(["git", "-C", RACINE, "remote"], capture_output=True, text=True).stdout.strip()
        if not distant:
            return "enregistré dans Git, mais aucun dépôt GitHub relié : rien n'est en ligne"
        subprocess.run(["git", "-C", RACINE, "push"], check=True, capture_output=True, timeout=120)
        return "publié sur GitHub (en ligne d'ici 1 minute environ)"
    except subprocess.CalledProcessError as err:
        return "échec de la publication Git : %s" % (err.stderr or b"").decode(errors="replace").strip()[:300]


def main():
    p = argparse.ArgumentParser(description="Crée et publie l'aperçu privé du site d'un prospect.")
    p.add_argument("--prospect", help="nom de l'entreprise dans ta liste de prospects")
    p.add_argument("--nom")
    p.add_argument("--metier", help="paysagiste, peintre, plombier, boulanger, coiffeur…")
    p.add_argument("--ville")
    p.add_argument("--tel")
    p.add_argument("--dirigeant")
    p.add_argument("--adresse")
    p.add_argument("--titre", help="phrase d'accroche personnalisée (facultatif)")
    p.add_argument("--photos", help="dossier contenant les photos du client")
    p.add_argument("--modele-demo", metavar="DOSSIER", help="(interne) crée une page de démo dans modeles/DOSSIER")
    p.add_argument("--exemple", metavar="DOSSIER", help="(interne) crée une réalisation fictive dans realisations/DOSSIER")
    p.add_argument("--sans-publier", action="store_true", help="ne pas publier sur GitHub")
    args = p.parse_args()

    config = charger_config()
    infos = {}
    if args.prospect:
        ligne, metier = lire_prospect(args.prospect)
        infos = {"nom": joli_nom(ligne["entreprise"]), "ville": ligne.get("ville", ""), "tel": ligne.get("telephone", ""),
                 "dirigeant": ligne.get("dirigeant", ""), "adresse": "", "metier": metier}
    for cle in ("nom", "ville", "tel", "dirigeant", "adresse", "metier", "titre"):
        if getattr(args, cle):
            infos[cle] = getattr(args, cle)
    manque = [c for c in ("nom", "metier", "tel") if not infos.get(c)]
    if manque:
        p.error("il manque : %s (ou utilise --prospect)" % ", ".join("--" + c for c in manque))
    cle_metier = ALIAS.get(infos["metier"], infos["metier"])
    if cle_metier not in METIERS:
        cle_metier = "batiment"
    infos["metier_cle"] = cle_metier

    if args.exemple:
        infos["demo"] = True
        dossier = os.path.join(RACINE, "realisations", args.exemple)
        code = None
    elif args.modele_demo:
        dossier = os.path.join(RACINE, "modeles", args.modele_demo)
        code = None
    else:
        existants = set(os.listdir(os.path.join(RACINE, "a"))) if os.path.isdir(os.path.join(RACINE, "a")) else set()
        code = nouveau_code(existants)
        dossier = os.path.join(RACINE, "a", code)
    os.makedirs(dossier, exist_ok=True)

    photos_relatives = []
    if args.photos:
        sources = sorted(f for f in glob.glob(os.path.join(os.path.expanduser(args.photos), "*"))
                         if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")))
        os.makedirs(os.path.join(dossier, "photos"), exist_ok=True)
        for i, src in enumerate(sources[:8], 1):
            nom = "photo-%d%s" % (i, os.path.splitext(src)[1].lower())
            shutil.copy(src, os.path.join(dossier, "photos", nom))
            photos_relatives.append("photos/" + nom)

    page = construire(infos, config, code, photos_relatives, apercu=not (args.modele_demo or args.exemple))
    with open(os.path.join(dossier, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)

    if args.exemple:
        print("Réalisation fictive créée : realisations/%s/index.html" % args.exemple)
        return
    if args.modele_demo:
        print("Modèle de démo créé : modeles/%s/index.html" % args.modele_demo)
        return

    lien = "%s/a/%s/" % (config["url_site"].rstrip("/"), code)
    nouveau = not os.path.exists(JOURNAL)
    with open(JOURNAL, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if nouveau:
            w.writerow(["date", "code", "entreprise", "telephone", "ville", "metier", "lien", "statut"])
        w.writerow([dt.datetime.now().strftime("%Y-%m-%d %H:%M"), code, infos["nom"], infos["tel"],
                    infos.get("ville", ""), infos["metier"], lien, "envoyé"])

    etat = "publication désactivée" if args.sans_publier else publier_git("Aperçu %s pour %s" % (code, infos["nom"]))
    prenom_client = (infos.get("dirigeant") or "").split(" ")[0]
    sms = ("Bonjour%s, c'est %s, on s'est appelés il y a quelques minutes. Voici l'aperçu du site que j'ai préparé "
           "pour %s : %s (code %s). Prenez le temps de le regarder, et dites-moi ce que vous en pensez !"
           % (" " + prenom_client if prenom_client else "", config["prenom_vendeur"], infos["nom"], lien, code))

    print("\nAperçu créé pour %s" % infos["nom"])
    print("  Code  : %s" % code)
    print("  Lien  : %s" % lien)
    print("  État  : %s" % etat)
    print("  Fichier local : a/%s/index.html" % code)
    print("\nSMS à envoyer au %s :\n\n%s\n" % (infos["tel"], sms))


if __name__ == "__main__":
    main()
