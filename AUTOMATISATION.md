# Publication automatique des liens de presse

Activée à la demande de l'utilisateur. La veille quotidienne à 05:17 UTC
publie jusqu'à 20 liens de presse récents, en plus des contenus éditoriaux existants.
Les contrôles portent sur le domaine autorisé, le chemin de l'article, le titre
fourni par le média, la date de publication (30 jours maximum), la pertinence
électorale et les doublons. Sans date exploitable ou si la page est inaccessible,
le lien est exclu. Les rejets manuels existants restent exclus.

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
