"""Regroupe les réglages du quiz : c'est ici que l'on change les règles."""

import os
import secrets
from pathlib import Path

# Toutes les durées sont exprimées en secondes.
DUREE_QUESTION = 30
DUREE_CORRECTION = 2
TOLERANCE_RESEAU = 1  # Laisse arriver la validation envoyée à la fin du chrono.
POINTS_BONNE_REPONSE = 1
MAX_JOUEURS = 4
LONGUEUR_PSEUDO = 15
TOURS_PAR_DEFAUT = 5
MAX_TOURS = 10

URL_API = "https://quizzapi.fr/api/v2/quiz"
DELAI_API = 5
DOSSIER_PROJET = Path(__file__).resolve().parent
CHEMIN_SECOURS = DOSSIER_PROJET / "questions_secours.json"
CHEMIN_HISTORIQUE = DOSSIER_PROJET / "historique.json"

# Aucun secret n'est écrit dans GitHub. En local, une clé aléatoire est créée
# au lancement. On peut aussi définir la variable d'environnement SECRET_KEY.
# La session signée contient uniquement un identifiant, jamais les réponses.
CLE_SECRETE = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

CATEGORIES = {
    "musique": "Musique",
    "culture_generale": "Culture générale",
    "art_litterature": "Arts et littérature",
    "tv_cinema": "TV et cinéma",
    "actu_politique": "Actualités et politique",
    "sport": "Sport",
    "jeux_videos": "Jeux vidéos",
    "histoire": "Histoire",
    "geographie": "Géographie",
    "science": "Science",
    "gastronomie": "Gastronomie",
}
