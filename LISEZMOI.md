# Coup d'Œil — les aperçus privés de Rob Jill

Le site qui héberge les maquettes envoyées aux prospects. Chaque prospect reçoit un lien privé
(`/a/<CODE>/`) avec un code de 6 caractères. Le site n'est pas référencé sur Google.

## Créer l'aperçu d'un prospect (après l'appel)

Depuis ce dossier :

```bash
python3 outils/nouvel_apercu.py --prospect "Longval service"
```

- `--prospect` va chercher le nom, le téléphone, la ville et le dirigeant dans tes listes de prospects.
- À la main : `--nom "…" --metier paysagiste --ville Rouen --tel "06 …" --dirigeant "Prénom Nom"`.
- Avec les photos du client : `--photos ~/Downloads/dossier-photos`. La 1re photo sert de fond
  d'accroche, les suivantes remplissent la galerie.
- `--titre "…"` remplace la phrase d'accroche.

Le script affiche le **lien**, le **code** et le **SMS prêt à envoyer**. Il note chaque aperçu dans
`apercus.csv`, ce qui sert de mini-CRM, et publie sur GitHub si le dossier est relié à un dépôt.

## Avant la première utilisation

1. Ouvre `config.json` et mets ton **vrai numéro**, ton e-mail et ton prix d'abonnement.
2. Remplace aussi `06 00 00 00 00` dans `index.html` et `404.html`.

## Mettre le site en ligne gratuitement (GitHub Pages)

1. Crée un compte sur github.com, puis un dépôt public nommé `coup-doeil`.
2. Dans `config.json`, remplace `TON-COMPTE-GITHUB` par ton nom d'utilisateur GitHub.
3. Relie ce dossier au dépôt (Claude peut le faire pour toi).
4. Sur GitHub : Settings > Pages > Source : « Deploy from a branch », branche `main`, dossier `/`.
5. Le site sera à l'adresse `https://<ton-compte>.github.io/coup-doeil/`.

Ensuite, chaque `nouvel_apercu.py` publie tout seul le nouvel aperçu, en ligne en environ 1 minute.

À savoir : un dépôt GitHub public est lisible par tout le monde. Les aperçus sont « privés »
parce que leur adresse est impossible à deviner et qu'ils ne sont pas sur Google, mais ce ne sont
que des maquettes avec les infos publiques de la fiche Google : rien de confidentiel.

## Les modèles

| Ambiance | Métiers |
| --- | --- |
| Jardin | paysagiste |
| Atelier | peintre, plombier, chauffagiste, électricien, maçon, menuisier, plâtrier, carreleur, couvreur |
| Fournil | boulanger, pâtissier, coiffeur, esthéticienne |

Le texte de chaque métier se modifie dans `outils/nouvel_apercu.py` (dictionnaire `METIERS`),
le design dans `outils/modele_site.html`. Pour régénérer les démos de la page d'accueil :

```bash
python3 outils/nouvel_apercu.py --nom "Les Jardins de Clara" --metier paysagiste --ville Rouen --tel "06 12 34 56 78" --dirigeant "Clara Martin" --modele-demo jardin
```

## Quand le client signe

Le site définitif reprend la même page **sans le bandeau d'aperçu**. Il sera hébergé à son nom,
avec son propre nom de domaine, comme le prévoit le contrat.
