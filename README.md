# Présidentielle 2027 — site prêt à publier

Site statique neutre avec sources et contrôle quotidien automatisé des pages de la Commission des sondages et de Verian (héritier de Sofres).

## Mise en ligne avec GitHub Pages
1. Créez un dépôt GitHub public et importez tout le contenu de ce dossier à la racine.
2. Dans **Settings → Pages → Build and deployment → Source**, choisissez **GitHub Actions**.
3. Ouvrez l'onglet **Actions** et lancez le workflow « Mise à jour quotidienne et publication » si nécessaire.
4. Le site sera disponible à l'adresse `https://VOTRE-COMPTE.github.io/NOM-DU-DEPOT/`.

Le workflow s'exécute aussi chaque jour à 05:17 UTC. Il vérifie l'accessibilité des sources officielles, enregistre la date de contrôle dans `data/status.json`, puis republie le site.

## Limite importante
Le robot ne réécrit pas automatiquement les programmes ou l'actualité politique : une modification éditoriale automatique sans validation risquerait d'introduire une interprétation, une erreur de source ou de mélanger des hypothèses de sondage. Le site affiche donc le contenu éditorial sourcé déjà vérifié et automatise la surveillance/horodatage des sources. Les nouvelles données doivent être validées avant remplacement des chiffres ou des fiches.

## Sources surveillées
- Commission des sondages — notices Présidentielle 2027
- Verian — publications politiques
- Verian — page institutionnelle confirmant l'héritage Sofres/TNS/Kantar Public
