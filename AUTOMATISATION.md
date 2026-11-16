# Mise à jour autonome des informations, sondages et programmes

Activée à la demande de l'utilisateur. La veille à 05:17 et 17:17 UTC
publie jusqu'à sept liens par média (21 au total), en plus des contenus éditoriaux existants.
Les contrôles portent sur le domaine autorisé, le chemin de l'article, le titre
fourni par le média, la date de publication, la pertinence
électorale et les doublons. Sans date exploitable, le lien est exclu. Une panne
réseau transitoire conserve pendant sept jours au maximum les articles déjà
contrôlés et leurs résumés validés, avec la date de dernière vérification affichée.
Une page supprimée, un accès interdit, des métadonnées devenues invalides ou
un rejet humain ne déclenchent pas ce repli. Les rejets manuels existants restent exclus. Jusqu'à 30 jours,
les liens sont récents ; de 31 à 180 jours, ils portent la mention « enquête antérieure ».
Au-delà, ils sont exclus. Les formats JSON-LD de Disclose et Nuxt de Blast sont
lus en associant la date à l'URL exacte de l'article, sans utiliser les dates
des recommandations voisines.

Les contrôles réseau sont exécutés pendant la veille, en parallèle et avec
un cache limité au passage courant. La sélection est enregistrée dans
publications_auto.json avec l'horodatage du contrôle ; la publication reconstruit
ce paquet hors réseau. Un paquet désynchronisé bloque la publication.
Les téléchargements HTML sont limités à 8 Mo et les PDF à 20 Mo. Chaque lecture
réseau expire après 15 secondes sans données ; le téléchargement est interrompu
après un budget de 45 secondes, au plus tard à la fin de la lecture en cours.
Un serveur qui transmet très lentement ne peut donc pas immobiliser la veille.

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
avec interruption réelle sur le runner Linux après vingt minutes par article
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

# Actualisation du 16 novembre 2026 : candidats et propositions

La veille d'actualités exige maintenant un candidat identifié dans le titre ou
dans le début d'un texte traitant de campagne/propositions. Une mention isolée
en fin de page, une ancienne liste de mentions, « gouvernement », « ministre »
ou « présidentielle » seuls ne suffisent plus. La même restriction s'applique
aux replis après panne, aux anciennes actualités et au paquet public hors réseau.
Les personnes suivies peuvent être déclarées ou seulement envisagées : leur
présence dans la veille ne change jamais leur statut de candidature.

Les synthèses de campagne apparaissent séparément de la presse, avec un filtre
par personne, le document de référence, les propositions, l'état d'avancement,
les limites et la date de contrôle. Aucun lecteur vidéo ni transcription brute
n'est publié. Le Bourget du 7 novembre est traité à partir de sa transcription
officielle ; des fiches des programmes Philippe et Retailleau complètent ce
premier lot. Leur sélection n'est ni un classement ni une couverture exhaustive.

`discours_auto.py` découvre aussi des supports sur les domaines de campagne
autorisés, suivant une règle identique pour chacun. Il exige un texte suffisant,
un auteur établi et un rattachement à la campagne. Une vidéo sans transcription
accessible n'est pas résumée. Les pages sans date non encore identifiées sont
écartées. Le moteur local, sans clé API, peut résumer de nouveaux documents ;
son budget est borné à dix minutes pour ce suivi. Les documents inchangés
réutilisent leur synthèse. Si le texte change, l'ancienne synthèse n'est pas
présentée comme celle du nouveau document. Une panne conserve la version datée
avec avertissement. La découverte est bornée à 32 documents et trois liens par
racine ; ce suivi ne promet donc pas de couvrir tous les discours ni YouTube.

Une modification de page est distinguée d'une nouvelle proposition politique.
Sans ancienne version comparable, la nouveauté d'une mesure reste non établie.
Une promesse n'est jamais présentée comme une loi adoptée, un financement
vérifié ou un résultat acquis. Les limites de faisabilité et d'accès sont
explicites. Les sondages et la périodicité existante restent conservés.

# Points de réflexion associés aux actualités

Le paquet public calcule hors réseau un point de réflexion pour chaque actualité
retenue. Il couvre l'école, les finances publiques, la santé, le travail et le
pouvoir d'achat, la fiscalité, l'énergie et l'industrie, l'écologie, les
institutions et libertés, l'immigration, l'international et la défense, ainsi
que le handicap et les AESH. Les formes fléchies et les pluriels sont reconnus.

Le point distingue la nature de l'information, les thèmes documentés, le lien
avec les cinq fiches programme prioritaires, les enjeux de financement, les
questions encore ouvertes et les thèmes absents de l'actualité. L'absence d'un
thème ne vaut jamais absence de proposition. L'« avis de lecture » qualifie
l'utilité documentaire de l'article : il ne note ni le candidat, ni la qualité
politique, ni la faisabilité réelle de la mesure et ne recommande aucun vote.
Cette analyse déterministe est recalculée à chaque construction, y compris pour
les anciennes actualités et après une mise à jour automatique ; elle ne dépend
d'aucune clé API et n'ajoute aucun fait au contenu source.

