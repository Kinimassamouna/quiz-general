# Ce fichier récupère les questions en ligne et complète avec le fichier de secours.
import json
import math
import random
import re
import unicodedata

import requests

from config import CATEGORIES, CHEMIN_SECOURS, DELAI_API, URL_API


def normaliser_texte(texte):
    """Transforme un texte en une clé comparable, sans accents ni ponctuation."""
    texte = unicodedata.normalize("NFKD", texte.casefold())
    texte = "".join(lettre for lettre in texte if not unicodedata.combining(lettre))
    return " ".join(re.findall(r"\w+", texte))


def convertir_question(donnee, categorie=None):
    """Vérifie une question brute et renvoie son format interne, ou None."""
    if not isinstance(donnee, dict):
        return None
    question, bonne = donnee.get("question"), donnee.get("answer")
    mauvaises, theme = donnee.get("badAnswers"), donnee.get("category")
    if not isinstance(theme, str) or theme not in CATEGORIES:
        return None
    if categorie and theme != categorie:
        return None  # Le secours respecte aussi le thème choisi.
    if not isinstance(mauvaises, list) or len(mauvaises) != 3:
        return None
    textes = [question, bonne, *mauvaises]
    if any(not isinstance(texte, str) or not normaliser_texte(texte) for texte in textes):
        return None
    reponses = [texte.strip() for texte in [bonne, *mauvaises]]
    if len({normaliser_texte(texte) for texte in reponses}) != 4:
        return None  # Les quatre boutons doivent proposer des réponses distinctes.
    random.shuffle(reponses)
    return {"question": question.strip(), "reponses": reponses,
            "bonne_reponse": bonne.strip(), "theme": CATEGORIES[theme]}


def interroger_api(nombre, categorie):
    """Demande des questions pour un thème ; une erreur donne une liste vide."""
    try:
        # La difficulté est volontairement absente : aucun filtre n'est demandé.
        reponse = requests.get(URL_API, params={"limit": nombre, "category": categorie},
                               timeout=DELAI_API)
        reponse.raise_for_status()
        contenu = reponse.json()
        questions = contenu.get("quizzes", []) if isinstance(contenu, dict) else []
        return questions if isinstance(questions, list) else []
    except (requests.RequestException, ValueError):
        return []  # Le jeu essaiera alors son fichier local.


def charger_secours():
    """Lit la liste de secours ; un fichier absent ou illisible donne []."""
    try:
        with CHEMIN_SECOURS.open(encoding="utf-8") as fichier:
            questions = json.load(fichier)
        return questions if isinstance(questions, list) else []
    except (OSError, ValueError):
        return []


def ajouter_questions(source, questions, identifiants, textes, categorie=None):
    """Ajoute les questions valides sans répéter un identifiant ni un énoncé."""
    for donnee in source:
        question = convertir_question(donnee, categorie)
        if question is None:
            continue
        # L'exemple du cahier utilise _id ; l'API actuelle peut renvoyer id.
        identifiant = donnee.get("_id") or donnee.get("id")
        identifiant = identifiant.strip() if isinstance(identifiant, str) else None
        texte = normaliser_texte(question["question"])
        if texte in textes or (identifiant and identifiant in identifiants):
            continue
        questions.append(question)
        textes.add(texte)
        if identifiant:
            identifiants.add(identifiant)


def recuperer_questions(nombre, categorie=None):
    """Renvoie (questions uniques, secours utilisé), ou une erreur en français."""
    if type(nombre) is not int or nombre < 1:
        raise ValueError("Le nombre de questions doit être un entier positif.")
    if categorie is not None and (not isinstance(categorie, str) or categorie not in CATEGORIES):
        raise ValueError("Le thème choisi est inconnu.")
    questions, identifiants, textes = [], set(), set()
    # Tous les thèmes : un petit appel pour chacune des onze catégories.
    categories = [categorie] if categorie else list(CATEGORIES)
    limite = nombre if categorie else max(2, math.ceil(nombre / len(CATEGORIES)))
    for theme in categories:
        ajouter_questions(interroger_api(limite, theme), questions, identifiants, textes, theme)
    avant_secours = len(questions)
    if len(questions) < nombre:
        ajouter_questions(charger_secours(), questions, identifiants, textes, categorie)
    if len(questions) < nombre:
        raise ValueError(f"Seulement {len(questions)} questions différentes disponibles. "
                         "Choisissez moins de tours, Tous les thèmes, ou réessayez avec Internet.")
    random.shuffle(questions)
    return questions[:nombre], avant_secours < nombre
