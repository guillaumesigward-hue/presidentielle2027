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
Qwen2.5-14B-Instruct, exécuté en français sur le processeur du workflow, sans clé API ni appel à un
service d'IA payant. La révision du modèle est épinglée et seules des pondérations
GGUF sont chargées par llama.cpp. Le modèle et le moteur proviennent de leurs dépôts officiels ; leurs fichiers sont vérifiés par SHA-256. Les textes
inchangés réutilisent leur résumé. Les articles trop courts ou fermés restent
explicitement sans résumé. Le modèle traite jusqu'à 1 600 mots accessibles ;
pour les articles longs, il conserve le début et la fin (où figurent souvent
les réponses des personnes mises en cause), et signale la partie intermédiaire omise.
Un premier passage produit la synthèse ; une reformulation intervient si nécessaire.
Le calcul des nouveaux résumés dispose d’un budget de 45 minutes par passage,
avec interruption réelle sur le runner Linux après cinq minutes par article
(démarrage et reformulation compris), ou plus tôt si le budget restant est épuisé.
Les articles reportés sont prioritaires au passage suivant. Les articles inchangés
réutilisent les résumés validés lors d’un passage antérieur. Les contrôles
recherchent des chiffres ou noms propres absents du texte, des copies longues,
des citations excessives et des répétitions anormales. Une sortie signalée
est rejetée ; ces contrôles ne prouvent
pas la véracité du résumé. Le lecteur voit toujours l'attribution au média et
le caractère automatique. Le contrôle technique ne constitue pas une
vérification indépendante de la véracité des articles.

Les sources primaires de campagne sont surveillées sur les domaines autorisés.
Une proposition explicite liée à 2027 peut enrichir la fiche par un extrait court
attribué et sourcé ; la fiche détaillée existante reste affichée et conserve
sa date de vérification. Un extrait bref ne remplace pas les explications
déjà documentées. Aucune notation
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

## Exécution et reprise

La veille se lance à 05:17 et 17:17 UTC et après un push humain ou une fusion sur
main. Le push du robot ne crée pas de boucle. La préparation du moteur est limitée
à 15 minutes ; son échec laisse fonctionner les autres rubriques. La sauvegarde
facultative du cache a lieu après l'enregistrement des données, avec une limite de
cinq minutes. Les diagnostics sont conservés sept jours dans les artifacts Actions.

Le site et son interface sont validés sur les nouvelles données avant tout commit.
En cas d'avance de main, les modifications indépendantes sont reprises et validées
avant de retenter le push (trois tentatives, jamais de push forcé). Une modification
concurrente des données interrompt ce passage pour ne pas écraser le travail humain ;
la prochaine veille repart des données récentes. Le site précédent reste consultable.

Le test manuel des sources avec `--require-summary` ignore les résumés antérieurs et
exige une génération nouvelle. Un contrôle vert hors réseau ne remplace pas cet essai.
Chaque article sélectionné est traité, mais un texte fermé, trop court, un dépassement
de temps ou une sortie rejetée reste explicitement sans résumé. Le dispositif ne peut
garantir un résumé pour un contenu auquel il n'a pas accès.

