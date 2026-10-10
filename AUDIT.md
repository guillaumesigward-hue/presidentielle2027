# Audit technique — 10 octobre 2026

Base : `9ff143c`, branche de travail `audit-finalisation-2027`.
Exécution examinée : https://github.com/guillaumesigward-hue/presidentielle2027/actions/runs/38063279964
Elle a réussi, mais ne comportait aucun test fonctionnel.

| Priorité | Constat initial | Traitement |
|---|---|---|
| P0 | L'interface assimilait `publication_automatique: true` à une validation et chargeait la file de contrôle | Suppression de ce chemin : seules les actualités éditoriales sont affichées |
| P0 | JSON invalide ou manquant remplacé silencieusement par un contenu vide | Arrêt explicite avant écriture ; remplacement atomique de chaque fichier |
| P0 | Déploiement existant lié à `main` | Aucun push sur main ni déploiement ; workflow manuel préparé. Réglage Pages à vérifier avant fusion |
| P1 | Traitement d'articles hors boucle, code inaccessible après `continue`, sorties de boucle interrompant les sources | Traitement par article, limite de vingt URL uniques par source et bilan de chacune des cinq sources |
| P1 | URL de confidentialité, rubriques et liens externes inclus ; liens relatifs incomplets | Filtre commun, résolution relative, exclusion des index et déduplication |
| P1 | Métadonnées avec apostrophes mal extraites, recommandations mêlées à un article court | Parseur HTML standard, métadonnées quel que soit l'ordre des attributs ; pas de repli sur les paragraphes externes si un article existe |
| P1 | Résumés humains écrasés, décisions perdues après plafonnement de la file | Conservation des entrées et des textes humains, statut indépendant de la publication |
| P1 | Aucun contrôle avant commit automatique, `git add -A` | Tests Python et interface ; ajout limité aux quatre fichiers de suivi ; exécution sur main seulement ; concurrence et durée limitées |
| P2 | Liens potentiellement non HTTP, valeurs documentaires non numériques, boutons sans état accessible | Liens HTTP/HTTPS seulement, valeur invalide « Non évaluée », `aria-pressed` et dates annoncées aux lecteurs d'écran |

## Validation

- Tests déterministes Python : extraction, filtres, vingt articles distincts, panne source, JSON corrompu, décisions humaines, exécution complète isolée et conservation éditoriale.
- Test JavaScript exécutant le script réel avec les JSON du dépôt : toutes les sections, cinq thèmes, exclusion de la file de contrôle, échappement HTML et liens.
- Navigateur local : six sections chargées, huit fiches programmes, Santé et Écologie testés ; téléphone à 390 × 844, aucun débordement horizontal.
- Réseau réel, copie isolée, deux articles maximum par média : Commission 167 notices ; Verian accessible ; Mediapart 161 liens et deux extractions non vides ; Disclose 181 liens et deux extractions non vides ; Blast 116 liens et deux extractions vides. Ces six articles ne suffisent pas à mesurer la couverture politique.
- Site public existant accessible ; historique GitHub attestant une publication de `9ff143c` dans l'environnement `github-pages`.

## Points restant soumis à validation ou configuration

1. Le réglage distant a été confirmé par API : Pages utilise actuellement `legacy`, branche `main`, chemin `/`. Il doit passer à « GitHub Actions » avant toute fusion.
2. Après accord explicite, tester le workflow manuel dans GitHub. Aucun déploiement n'a été exécuté ici ; la configuration distante, les droits et l'environnement restent à confirmer.
3. Les textes politiques, statuts de candidature, chiffres des sondages et pourcentages de solidité documentaire ont été conservés. Leurs sources doivent être recontrôlées humainement ; la réussite technique ne les valide pas.
4. Blast peut fournir des pages sans texte exploitable ; ce cas apparaît désormais dans le bilan d'extraction. Pas de contournement de paywall ni de résumé inventé.
5. L'ancienne file contient des faux positifs (confidentialité et rubrique). Ils sont conservés pour préserver les décisions existantes, mais aucune nouvelle entrée de ces types n'est ajoutée et aucune n'est affichée publiquement.
6. La liste des personnes et médias surveillés demeure celle du dépôt. Elle nécessite une revue humaine de couverture pour établir la neutralité et l'exhaustivité ; elle n'a pas été élargie arbitrairement.

Les fichiers éditoriaux de données restent identiques à la base. Les essais réseau écrivent uniquement dans `.preview/`, exclu de Git.

## Finalisation de l'actualisation quotidienne

- Dix tests Python passent, dont deux passages successifs de la veille, conservation d'un résumé humain et exclusion des contenus non validés du paquet public.
- Passage réel complet isolé : Commission 167 notices ; Verian accessible ; Mediapart 16 articles examinés, deux détections ; Blast 16 articles examinés, une détection, six extractions vides ; Disclose 20 articles examinés, une détection. Aucun fichier éditorial de production modifié.
- La veille est désormais raccordée à la reconstruction quotidienne du site sur la révision exacte qu'elle vient d'enregistrer. Les programmes et actualités demeurent les données éditoriales existantes.
- Un fichier `suivi.json` public contient uniquement les dates et compteurs techniques. Les titres, résumés automatiques et décisions de validation sont exclus du paquet livré.
- L'interface signale les sources indisponibles, les extractions partielles et une date de contrôle dépassant 48 heures.
- Le contrôle GitHub permet un passage réseau isolé sur la branche de travail sans déployer. Le passage de production, la fusion et la première mise en ligne demeurent soumis à validation explicite de l'utilisateur.
