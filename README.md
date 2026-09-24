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
## Règles éditoriales pour les programmes et les actualités

L'objectif du site est de présenter une synthèse factuelle, fidèle, complète et compréhensible des informations disponibles, sans recommander, classer ou noter les personnes suivies.

### Fidélité des résumés

Un résumé ne doit pas chercher à être court au détriment de l'information. Il doit conserver tous les éléments substantiels nécessaires pour comprendre correctement la source.

Pour chaque proposition ou information importante, conserver lorsque ces éléments existent :

- la mesure ou la décision annoncée ;
- les montants et objectifs chiffrés ;
- le calendrier ou l'échéance ;
- le mode de financement annoncé ;
- les économies ou dépenses annoncées ;
- les personnes ou catégories concernées ;
- les conditions, exceptions et limites de la mesure ;
- les modalités de mise en œuvre précisées ;
- le contexte nécessaire à la compréhension ;
- la date et la source.

Ne jamais inventer un montant, un financement, une conséquence ou une modalité absente des sources.

Lorsqu'une information importante n'est pas précisée, l'indiquer explicitement : « non précisé », « non chiffré » ou formulation équivalente.

### Statut des propositions

Toujours distinguer clairement :

- proposition présentée pour 2027 ;
- orientation annoncée pour 2027 ;
- programme 2027 en préparation ;
- position ou programme antérieur non encore confirmé pour 2027 ;
- information en cours de vérification ;
- aucune proposition suffisamment précise identifiée dans les sources vérifiées.

Une proposition issue d'une campagne antérieure ne doit jamais être présentée comme un engagement pour 2027 sans confirmation récente.

### Sources

Privilégier la source primaire lorsqu'elle existe : document officiel, programme, discours, publication ou site officiel de la personne ou de son organisation.

Les sources journalistiques, institutionnelles ou d'instituts reconnus peuvent compléter la source primaire, notamment pour apporter du contexte, un chiffrage ou des précisions absentes de celle-ci.

Une source politique ou de campagne permet d'établir ce que son auteur propose ou affirme. Les justifications, estimations et conséquences annoncées par cet auteur ne doivent pas être transformées en faits établis.

Les informations importantes doivent pouvoir être rattachées à une source identifiable.

### Programmes

Les fiches doivent présenter directement les éléments importants des propositions. Les liens vers les sources servent à vérifier et approfondir l'information ; ils ne remplacent pas le résumé.

Pour les thèmes École, Santé, Énergie, Fiscalité et Écologie, rechercher notamment :

- les mesures concrètes ;
- les montants annoncés ;
- leur financement annoncé ;
- les personnes concernées ;
- les conséquences explicitement prévues ou décrites par la proposition ;
- les éléments restant non chiffrés ou non précisés.

Pour l'École, une attention spécifique est également portée au handicap, aux AESH et à l'école inclusive.

### Actualités

Chaque actualité doit permettre de comprendre au minimum :

- ce qui s'est passé ;
- qui est concerné ;
- la date ou la période ;
- le contexte utile ;
- les annonces, décisions ou déclarations importantes ;
- les chiffres significatifs lorsqu'ils existent ;
- la source.

Distinguer explicitement un fait rapporté d'une déclaration, d'une promesse, d'une critique, d'une estimation ou d'une analyse attribuée à une personne ou à un média.

### Interdiction de l'interprétation éditoriale

Le site ne doit pas déduire les intentions d'une personne, prédire les effets d'une proposition ou transformer une hypothèse en certitude.

Il ne doit pas déterminer quelle proposition est meilleure, plus réaliste ou préférable.

La « solidité documentaire » concerne uniquement le niveau de documentation d'une fiche. Elle ne constitue ni une note de la personne, ni une évaluation de la qualité, de la faisabilité ou de l'efficacité de sa proposition.

### Automatisation

Le robot peut détecter de nouvelles publications, enregistrer leur existence et signaler qu'une vérification est nécessaire.

Il ne doit pas publier automatiquement comme information politique vérifiée un résumé nouvellement généré sans contrôle préalable de la source et du contenu.

La priorité éditoriale est la fidélité et la complétude. Si une source contient de nombreux éléments importants, le résumé peut être plus long afin de ne pas les tronquer ou les diluer.
