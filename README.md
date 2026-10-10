# Présidentielle 2027 — veille et publication contrôlée

Site statique neutre avec sources et contrôle quotidien automatisé des pages de la Commission des sondages et de Verian (héritier de Sofres).

## Vérifications et publication

Les tests s'exécutent avec `python -m unittest discover -s tests -v` et
`node tests/interface.cjs`. Ils sont également lancés par GitHub Actions.
La veille à 05:17 et 17:17 UTC actualise les données et publie la révision exacte
sur `main`. À la demande de l'utilisateur, le mode autonome est activé : liens
de presse contrôlés, résumés locaux sans clé API, résultats de sondages extraits
des notices compatibles et propositions explicites des sources de campagne.
Les limites et la couverture sont visibles sur le site. Voir [AUTOMATISATION.md](AUTOMATISATION.md).

Avant toute fusion, vérifier **Settings → Pages → Build and deployment → Source**.
Le réglage doit être **GitHub Actions**, car une publication depuis la branche
`main` publierait automatiquement toute mise à jour de cette branche.
Ce réglage n'est pas modifié par les fichiers de workflow.

Après validation explicite de l'utilisateur, lancer « Publication manuelle validee »
sur `main` en cochant `validation_utilisateur`. Aucun calendrier ni push ne lance
ce workflow manuel. La veille quotidienne appelle le même mécanisme de
construction sur la révision exacte qui vient d'être enregistrée.
Le site ne contient que `index.html`, `data/election.json`, `data/programmes.json`
et `data/suivi.json`. Les détections brutes et la file d'archive sont exclues.
La file `a_valider.json` n'est jamais chargée par l'interface.

## Validation éditoriale

`Retenu` est une décision de contrôle, pas une commande de publication.
Les corrections éditoriales peuvent être intégrées dans `data/election.json`
(`titre`, `description`, `source`, `url`). Les anciennes décisions sont conservées
et les rejets explicites restent exclus de la sélection. Le champ global
`publication_automatique` indique le mode actif ; les anciens champs par détection
restent des archives. Un article fermé ou un texte insuffisant n'est pas résumé
à partir de son seul titre : cette limite est affichée.

La veille examine au plus vingt URL distinctes par média et par passage.
`ok` indique l'accès à la page source ; `etat_extraction`, `liens_examines` et
`extractions_vides` décrivent séparément la qualité de l'extraction.
Les fichiers JSON manquants, invalides ou de type inattendu interrompent la
mise à jour avant écriture au lieu de remplacer l'historique par des listes vides.
Les décisions et résumés humains de la file sont conservés sans limite de cent entrées.

Le site affiche l'état des cinq sources, les extractions partielles et une
alerte si le contrôle date de plus de 48 heures. Une panne du fichier de suivi
n'empêche pas de consulter les données éditoriales.
À Paris, 05:17 UTC correspond à 07:17 en été et à 06:17 en hiver.
GitHub peut retarder les tâches planifiées ; il ne garantit pas une exécution
à la minute près.

## Limite importante
L'automatisation reste limitée aux domaines configurés et aux formats reconnus.
Les résumés sont attribués et étiquetés automatiques ; les contrôles ne constituent
pas une preuve de véracité. Les tableaux ambigus sont écartés et les données
précédentes conservées en cas de panne. Les nouvelles campagnes doivent être
ajoutées à la liste de domaines autorisés ; aucun nom n'est inventé par le robot.

## Sources surveillées
- Commission des sondages — notices Présidentielle 2027
- Verian — publications politiques
- Verian — page institutionnelle confirmant l'héritage Sofres/TNS/Kantar Public
- Mediapart, Blast et Disclose — sources indépendantes et d'investigation
- Sources officielles des personnes déjà suivies — programmes et déclarations explicites
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

Un résumé nouvellement généré passe les contrôles automatiques de source et de
cohérence avant publication, avec une attribution claire et ses limites. Il ne
doit jamais être présenté comme une information vérifiée indépendamment.

La priorité éditoriale est la fidélité et la complétude. Si une source contient de nombreux éléments importants, le résumé peut être plus long afin de ne pas les tronquer ou les diluer.
