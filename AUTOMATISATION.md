# Publication automatique des liens de presse

Activée à la demande de l'utilisateur. La veille à 05:17 et 17:17 UTC
publie jusqu'à sept liens par média (21 au total), en plus des contenus éditoriaux existants.
Les contrôles portent sur le domaine autorisé, le chemin de l'article, le titre
fourni par le média, la date de publication, la pertinence
électorale et les doublons. Sans date exploitable ou si la page est inaccessible,
le lien est exclu. Les rejets manuels existants restent exclus. Jusqu'à 30 jours,
les liens sont récents ; de 31 à 180 jours, ils portent la mention « enquête antérieure ».
Au-delà, ils sont exclus. Les formats JSON-LD de Disclose et Nuxt de Blast sont
lus en associant la date à l'URL exacte de l'article, sans utiliser les dates
des recommandations voisines.

Les contrôles réseau sont exécutés pendant la veille, en parallèle et avec
un cache limité au passage courant. La sélection est enregistrée dans
publications_auto.json avec l'horodatage du contrôle ; la publication reconstruit
ce paquet hors réseau. Un paquet désynchronisé bloque la publication.

Les nouveaux liens sont également présentés dans les programmes par thème et
dans le suivi des personnes mentionnées. Les dernières notices de la Commission
des sondages sont publiées comme documents officiels, sans déduire de résultats
chiffrés ni confondre enquête thématique et intention de vote. Ces rubriques
enrichissent automatiquement les sources consultables ; elles ne transforment
pas un article de presse en engagement de programme ou en candidature confirmée.

Le titre et le lien sont attribués au média et étiquetés comme sélection automatique.
Aucun résumé synthétique, chiffre de sondage, statut de candidature ou programme
n'est généré automatiquement. Le contrôle technique ne constitue pas une
vérification indépendante de la véracité des articles.

Les fichiers de détections et d'archives ne sont pas exposés dans le site public.
Le champ global `publication_automatique` du suivi indique le mode actif ; les
anciens champs par détection conservent leur rôle d'archive de revue manuelle.
Pour désactiver ce mode, mettre ce champ à false dans le statut produit par update.py.

Ce fonctionnement remplace l'obligation de validation humaine décrite dans
l'audit initial pour les liens de presse. Les textes éditoriaux existants restent
inchangés et conservent leur date de vérification.
