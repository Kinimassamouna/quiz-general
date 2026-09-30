<!-- Ce fichier explique l'installation, les règles, le code et la présentation orale. -->
# Quiz de culture générale

Le projet consiste à développer une application web permettant à un utilisateur de tester ses connaissances générales à travers une série de différentes questions dans le thème de la célèbre émission les 12 coup de midi.

Un projet étudiant en **Python, Flask, HTML, CSS et JavaScript simple**, inspiré de l'ambiance des *12 Coups de Midi*. De 1 à 4 joueurs répondent chacun leur tour à des QCM et gagnent des points. Les dessins et les animations sont réalisés dans le projet, en CSS et SVG.

## Installer et lancer

Il faut **Python 3.10 ou une version plus récente**, un navigateur et une connexion Internet pour installer les deux bibliothèques. Le jeu peut ensuite utiliser ses questions locales quand QuizzAPI est inaccessible.

Décompresser le projet, puis ouvrir un terminal **dans le dossier `quiz-general`**, celui qui contient `app.py`.

### Windows — PowerShell

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Si Windows reconnaît `py` mais pas `python`, utiliser `py -m venv .venv` pour créer l'environnement. Si PowerShell bloque l'activation, on peut utiliser directement le Python de cet environnement :

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

### Linux ou macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Ouvrir ensuite [http://127.0.0.1:5000](http://127.0.0.1:5000) dans le navigateur. Garder le terminal ouvert pendant la partie ; `Ctrl+C` arrête le serveur. Les joueurs partagent l'écran et jouent à tour de rôle. L'adresse locale fonctionne sur l'ordinateur qui lance Flask.

Pour les prochains lancements, il suffit de se replacer dans ce dossier, de réactiver l'environnement et d'exécuter `python app.py`. Les dépendances ne sont pas à réinstaller à chaque partie.

## Le projet en cinq étapes

Les cinq étapes demandées sont présentes. Les propositions indiquées après chacune sont **des idées non codées**, à choisir avec le groupe avant toute intégration.

### Étape 1 — Préparer les joueurs et la partie

L'accueil affiche un seul champ de pseudo. Le bouton **+** ajoute un joueur, jusqu'à quatre. La croix retire un joueur ajouté ; le premier champ reste toujours présent. Un pseudo doit contenir de 1 à 15 caractères après suppression des espaces au début et à la fin. Deux pseudos identiques, même avec une casse différente, sont refusés par Python.

Choisir de **1 à 10 tours**, avec **5 tours par défaut**, puis un thème parmi les onze proposés ou **Tous les thèmes**. Un tour signifie que **chaque joueur répond à une question**. Par exemple, 4 joueurs et 5 tours demandent 20 questions. Le bouton **Commencer** prépare la partie.

**Proposition — non intégrée :** mémoriser les pseudos dans le navigateur éviterait de les ressaisir au prochain lancement ; difficulté **simple**, à ajouter seulement avec l'accord du groupe.

### Étape 2 — Charger les questions

Toutes les requêtes vers [QuizzAPI](https://quizzapi.fr) se trouvent dans `api_questions.py`. La fonction `recuperer_questions(nombre, categorie=None)` renvoie la liste des questions et un booléen indiquant si le secours a été utilisé.

- Pour un thème précis : **un seul appel**, avec `category` et `limit = joueurs × tours`.
- Pour tous les thèmes : **un appel par catégorie**, avec `limit = max(2, arrondi supérieur du nombre nécessaire / 11)`, puis regroupement, mélange et sélection.
- Aucun paramètre `difficulty` n'est envoyé.
- Chaque requête utilise `timeout=5`. Les erreurs réseau, HTTP et JSON sont traitées.
- Les questions incomplètes, les catégories inconnues et les choix non distincts sont ignorés.
- Les doublons sont écartés par `_id` (ou `id`, renvoyé par l'API actuelle) et par énoncé normalisé, sans tenir compte de la casse, des accents ou de la ponctuation.

Les onze appels sont successifs. S'ils attendent chacun environ 5 secondes, la préparation peut déjà prendre environ **55 secondes** avant le secours. Ce chiffre n'est pas une limite globale garantie : le délai de `requests` porte sur les attentes réseau, pas sur la durée totale de tous les transferts.

Le fichier `questions_secours.json` contient **220 questions en français : 20 par catégorie**, au même format brut que l'API. Les deux sources passent donc par la même fonction de conversion. Les quatre réponses sont mélangées ; chaque question interne contient uniquement `question`, `reponses`, `bonne_reponse` et `theme`.

Le message **« Mode hors-ligne : questions de secours »** apparaît dès que des questions locales complètent le lot, même si une partie des questions provient de l'API. Un thème choisi est toujours respecté : le secours ne pioche pas dans les autres thèmes pour combler un manque.

Avec une API indisponible, un thème précis permet **20 questions au maximum** : par exemple 4 joueurs × 5 tours, ou 2 joueurs × 10 tours. Si la configuration demande davantage de questions uniques que le stock disponible, un message invite à réduire les tours, choisir Tous les thèmes ou réessayer avec Internet. Avec tous les thèmes, les 220 questions locales couvrent les 40 questions maximales de l'application.

**Proposition — non intégrée :** afficher le nombre de questions locales disponibles par thème aiderait à choisir les tours sans dépasser le stock hors ligne ; difficulté **simple**, à ajouter seulement avec l'accord du groupe.

### Étape 3 — Répondre et marquer des points

Le joueur actif est mis en évidence dans la barre du haut et dans **« À vous de jouer [Nom] ! »**. Les réponses occupent les quatre coins de la zone de jeu ; le chronomètre est au centre et le thème en bas.

Cliquer sur une réponse, éventuellement changer de sélection, puis cliquer sur **Valider**. À zéro, JavaScript envoie automatiquement la sélection en cours ; une absence de sélection compte comme une mauvaise réponse. Une bonne réponse rapporte **1 point** et fait pulser l'étoile du joueur.

Le chronomètre dure **30 secondes**, définies une seule fois par `DUREE_QUESTION` dans `config.py`. Le navigateur reçoit cette valeur depuis Python. Le serveur calcule aussi le temps écoulé : modifier l'affichage du navigateur ne remet pas le délai à zéro. Une tolérance de **1 seconde** laisse parvenir une sélection envoyée à l'expiration ; au-delà de cette tolérance, Python enregistre une absence de réponse.

La correction affiche la bonne réponse, avec du vert pour une réussite et du rouge pour une erreur. La pause de **2 secondes** est contrôlée par le serveur avant le passage au joueur suivant. Un double clic ou une répétition de la même requête ne peut pas donner deux fois les points.

Si une requête échoue pendant la partie, l'interface propose **Réessayer**. Recharger la page retrouve la partie conservée par le serveur et son temps restant ; cela ne redémarre pas le chronomètre. Si le serveur a été arrêté, il faut commencer une nouvelle partie.

**Proposition — non intégrée :** proposer les touches A, B, C et D pour sélectionner une réponse faciliterait le jeu au clavier ; difficulté **simple**, à ajouter seulement avec l'accord du groupe.

### Étape 4 — Afficher le résultat

Après toutes les questions, l'écran présente le classement par score décroissant. Tous les joueurs à égalité au meilleur score sont gagnants, y compris si personne n'a marqué de point. Les ex æquo partagent leur rang : par exemple 1, 1, 3. Le bouton **Rejouer** ramène à la configuration.

**Proposition — non intégrée :** ajouter un bouton pour copier le classement en texte permettrait de le partager facilement avec la classe ; difficulté **simple**, à ajouter seulement avec l'accord du groupe.

### Étape 5 — Relire les réponses, l'historique et les statistiques

Sous le classement, la correction détaillée reprend chaque question, le joueur concerné, sa réponse, la bonne réponse et le résultat juste ou faux. Chaque question appartient au joueur qui devait y répondre.

Une partie complète est enregistrée une seule fois dans `historique.json`, avec son identifiant, sa date de début, ses joueurs et scores, son nombre de tours, ses gagnants, son classement et ses réponses. Le fichier est créé automatiquement lors de sa première utilisation. La page **Historique** affiche les parties les plus récentes en premier. Le fichier reste présent après l'arrêt du serveur.

La page **Statistiques** présente le nombre de parties terminées, le meilleur score et la moyenne globale, puis le nombre de parties, le meilleur score et la moyenne de chaque pseudo. Les pseudos sont regroupés sans distinction de casse : `Alice` et `alice` désignent le même groupe statistique. Ce sont des noms de jeu, sans système de comptes.

Les moyennes sont des **scores bruts par partie**, pas des pourcentages : une partie de 10 tours offre plus de points possibles qu'une partie de 2 tours. La moyenne globale porte sur l'ensemble des scores de joueurs enregistrés. L'affichage arrondit les moyennes à une décimale.

Un historique absent est créé vide. Un historique illisible déclenche un message et n'est pas effacé automatiquement. Une erreur d'enregistrement est signalée sur la page des résultats.

**Proposition — non intégrée :** filtrer l'historique par pseudo permettrait de retrouver plus vite les parties d'un joueur ; difficulté **simple**, à ajouter seulement avec l'accord du groupe.

## Comprendre les fichiers

```text
quiz-general/
├── app.py                     Routes Flask et lien entre les pages et Python
├── config.py                  Constantes, catégories, chemins et clé de session
├── api_questions.py           Appels QuizzAPI, conversion, doublons et secours
├── logique_jeu.py              Validation, tours, temps, scores et fichiers JSON
├── questions_secours.json      220 questions au format de l'API
├── historique.json            Créé automatiquement ; données locales ignorées par Git
├── requirements.txt           Flask et requests
├── README.md                  Installation, explications et préparation de l'oral
├── .gitignore                 Fichiers à ne pas envoyer sur GitHub
├── templates/
│   ├── base.html               Structure commune, navigation, CSS et JavaScript
│   ├── macros.html             Petites fonctions Jinja réutilisant les dessins SVG
│   ├── index.html              Configuration des joueurs, tours et thème
│   ├── jeu.html                Plateau de jeu
│   ├── resultats.html          Classement et correction détaillée
│   ├── historique.html         Liste des parties enregistrées
│   └── statistiques.html       Totaux et moyennes
└── static/
    ├── css/style.css           Couleurs, disposition responsive et animations
    └── js/jeu.js               Champs joueurs, clics, chrono, fetch et affichage
```

`base.html` évite de recopier l'en-tête de chaque page. `macros.html` réutilise les mêmes étoiles SVG pour le titre et les scores. Aucune image externe, police distante, bibliothèque d'animation ni base SQL n'est nécessaire.

### Parcours des données

```text
PRÉPARATION
Navigateur : joueurs, tours, thème
    -> Flask : validation Python
    -> API QuizzAPI : questions brutes
       + fichier de secours si nécessaire
    -> Conversion, suppression des doublons et mélange
    -> Mémoire du serveur : questions et solutions privées
    -> Page du jeu : énoncé, quatre choix, thème, joueur et temps restant

RÉPONSE
Navigateur : choix + index de la question
    -> Flask : contrôle de la question et du temps
    -> Correction Python et mise à jour du score
    -> Navigateur : bonne réponse et scores actualisés
    -> Pause de correction, puis question suivante
    -> Fin de partie : classement et historique.json
    -> Pages Historique et Statistiques
```

### Où vit la partie ?

Par défaut, la session Flask est stockée dans un **cookie signé, mais lisible** par le navigateur. Elle ne doit donc pas contenir les bonnes réponses. Dans ce projet, `session` contient seulement `partie_id`, un identifiant aléatoire. Le dictionnaire `PARTIES` de `app.py` conserve côté serveur les joueurs, questions, solutions, scores et réponses. Cette séparation s'appuie sur le fonctionnement décrit dans la [documentation officielle des sessions Flask](https://flask.palletsprojects.com/en/stable/quickstart/#sessions).

`etat_public()` prépare la seule partie des données autorisée à être envoyée au navigateur. Avant validation, celui-ci voit les quatre choix sans savoir lequel est correct. Après validation, il reçoit la correction de la question jouée. JavaScript gère l'affichage ; **Python choisit les questions, valide les réponses et calcule les scores**.

Le stockage en mémoire convient à la démonstration avec **un seul processus Python**. Arrêter ou redémarrer le serveur efface les parties en cours, même si la clé de session reste identique. Les parties déjà écrites dans `historique.json` restent disponibles. Plusieurs onglets d'un même navigateur partagent leur session et donc leur partie.

Un verrou empêche deux requêtes concurrentes de modifier les scores en même temps. L'index de question empêche de répondre à une ancienne question ; une correction déjà calculée est renvoyée telle quelle sans ajouter de points.

## Modifier les réglages et partager sur GitHub

Les réglages principaux se trouvent dans `config.py` :

| Constante | Valeur initiale | Rôle |
| --- | --- | --- |
| `DUREE_QUESTION` | 30 | Durée d'une question en secondes |
| `DUREE_CORRECTION` | 2 | Pause avant la question suivante |
| `TOLERANCE_RESEAU` | 1 | Marge de réception de la réponse en secondes |
| `POINTS_BONNE_REPONSE` | 1 | Points gagnés pour une bonne réponse |
| `MAX_JOUEURS` | 4 | Nombre maximal de joueurs |
| `LONGUEUR_PSEUDO` | 15 | Nombre maximal de caractères d'un pseudo |
| `TOURS_PAR_DEFAUT` | 5 | Nombre de tours proposé à l'accueil |
| `MAX_TOURS` | 10 | Nombre maximal de tours accepté |
| `DELAI_API` | 5 | Délai d'attente utilisé par chaque appel API |

Après une modification Python, arrêter puis relancer le serveur. Si l'on augmente le nombre de tours ou de joueurs, il faut aussi tenir compte du nombre de questions uniques disponibles.

`CLE_SECRETE` utilise la variable d'environnement facultative `SECRET_KEY`. Si elle n'est pas définie, une clé aléatoire est générée au lancement : aucune clé secrète fixe n'est écrite dans le code. Changer cette clé invalide les anciens cookies de session. Un éventuel fichier `.env` n'est pas chargé automatiquement : ce projet n'utilise pas `python-dotenv`.

Le `.gitignore` exclut notamment les environnements virtuels, `__pycache__`, les fichiers `.env`, `historique.json` et le fichier temporaire d'historique. Partager les sources, les questions locales et `requirements.txt` sur GitHub ; conserver les secrets et les données de parties en local.

## Vérifications effectuées

Les 34 tests automatiques de préparation ont réussi : validation des joueurs, API et secours, doublons, ordre des tours, chrono, score unique, égalités, confidentialité des solutions, historique et statistiques. Un appel réel à QuizzAPI a aussi renvoyé une réponse HTTP 200 au format attendu.

Le parcours a été vérifié dans un navigateur : ajout et retrait de joueurs, limite à quatre, changement de sélection, correction, passage au joueur suivant, validation automatique de la sélection à zéro, égalité finale, historique et statistiques. Le rendu a été contrôlé sur ordinateur et à une largeur mobile de 390 pixels.

## Pour mon oral

### Résumé en neuf lignes

1. Notre application est un quiz de culture générale de un à quatre joueurs.
2. Flask reçoit les demandes du navigateur dans les routes courtes de `app.py`.
3. `config.py` centralise les réglages : temps, points, joueurs, tours et catégories.
4. `api_questions.py` charge QuizzAPI, complète avec le JSON local et évite les doublons.
5. Les templates HTML présentent les pages ; le CSS et les SVG créent l'ambiance du jeu.
6. JavaScript ajoute les champs joueurs, affiche le chrono et envoie le choix avec `fetch`.
7. Les solutions restent en mémoire côté serveur ; le cookie contient seulement l'identifiant de partie.
8. `logique_jeu.py` vérifie la réponse et le délai, ajoute les points et passe au joueur suivant.
9. À la fin, le classement et les corrections sont affichés, puis le JSON alimente l'historique et les statistiques.

### Trois questions difficiles et leurs réponses

**1. Pourquoi ne pas placer toutes les questions et leurs solutions directement dans `session` ?**

La session Flask standard utilise un cookie signé : sa signature protège contre une modification non autorisée, mais elle ne chiffre pas son contenu. Le navigateur pourrait donc lire les solutions. Notre cookie contient seulement un identifiant aléatoire ; les solutions restent dans `PARTIES` sur le serveur. Ce choix simple implique de perdre les parties en cours lorsque le processus s'arrête.

**2. Un joueur peut-il gagner des points en modifiant le JavaScript ou en envoyant un faux score ?**

Le serveur ne reçoit pas de score à appliquer. Il reçoit le choix et l'index de la question, contrôle que ce choix fait partie des quatre réponses, vérifie le délai avec sa propre horloge et compare à sa solution privée. Le chrono affiché n'est donc pas la référence pour le calcul. La tolérance réseau est explicite : une seconde au-delà des trente secondes affichées, puis la réponse est considérée absente.

**3. Pourquoi un double clic ou une nouvelle tentative réseau ne compte-t-il pas deux fois ?**

Les requêtes modifiant une partie passent sous un verrou. Pour une même question, `verifier_reponse()` renvoie la correction existante si elle a déjà été calculée, sans modifier le score. Une requête visant un ancien index est refusée. De même, l'historique utilise l'identifiant de partie pour éviter d'enregistrer deux fois la même partie.
