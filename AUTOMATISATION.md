# Mise à jour autonome des informations, sondages et programmes

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
des sondages sont publiées comme documents officiels. Les tableaux de premier
tour compatibles sont également lus dans les PDF : colonne explicitement
« résultats publiés », total 100 %, institut, commanditaire, échantillon et terrain.
Les formats ambigus, enquêtes de popularité et tableaux bruts sont écartés.
Plusieurs scénarios d'une même enquête restent distincts. Le lecteur actuel
reconnaît les notices de structure Ifop ; les autres formats restent signalés
comme non exploitables, sans fabriquer de résultats. Ces rubriques
enrichissent automatiquement les sources consultables ; elles ne transforment
pas un article de presse en engagement de programme ou en candidature confirmée.

Le titre et le lien sont attribués au média et étiquetés comme sélection automatique.
Les articles accessibles sont résumés par le modèle libre multilingue
Qwen2.5-1.5B-Instruct, exécuté en français sur le processeur du workflow, sans clé API ni appel à un
service d'IA payant. La révision du modèle est épinglée et seules des pondérations
safetensors sont chargées, sans exécuter le code du dépôt du modèle. Les textes
inchangés réutilisent leur résumé. Les articles trop courts ou fermés restent
explicitement sans résumé. Le modèle traite jusqu'à 2 400 mots accessibles ;
pour les articles longs, il conserve le début et la fin (où figurent souvent
les réponses des personnes mises en cause), et signale la partie intermédiaire omise.
Un chiffre ou nom propre ajouté provoque le rejet ; ces contrôles ne prouvent
pas la véracité du résumé. Le lecteur voit toujours l'attribution au média et
le caractère automatique. Le contrôle technique ne constitue pas une
vérification indépendante de la véracité des articles.

Les sources primaires de campagne sont surveillées sur les domaines autorisés.
Une proposition explicite liée à 2027 peut enrichir la fiche par un extrait court
attribué et sourcé ; la fiche antérieure reste consultable. Aucune notation
politique, estimation budgétaire ou population bénéficiaire n'est extrapolée.
Les statuts ne changent que pour une déclaration personnelle explicite de
candidature ou de retrait pour 2027. Les pages de programmes 2022 sont écartées.
Les nouvelles personnes figurant dans les tableaux de sondages sont ajoutées
automatiquement comme « personnes testées », sans leur attribuer une candidature
déclarée ni un programme. Les domaines de nouvelles campagnes doivent être
ajoutés à la liste autorisée avant de pouvoir extraire leurs propositions.

Les fichiers de détections et d'archives ne sont pas exposés dans le site public.
Le champ global `publication_automatique` du suivi indique le mode actif ; les
anciens champs par détection conservent leur rôle d'archive de revue manuelle.
Pour désactiver ce mode, mettre ce champ à false dans le statut produit par update.py.

Ce fonctionnement remplace l'obligation de validation humaine décrite dans
l'audit initial, à la demande de l'utilisateur. En cas d'échec d'extraction,
les chiffres et fiches précédemment disponibles sont conservés ; la date de
contrôle automatique ne remplace pas leur date de vérification éditoriale.
La construction et la publication réutilisent exactement les données du passage
réussi. Le suivi public indique la couverture et les extractions manquantes.
