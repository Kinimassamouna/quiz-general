"""Valide les joueurs, gère la partie et lit ou écrit l'historique JSON."""

import json
import secrets
from datetime import datetime
from time import monotonic

from config import (
    CATEGORIES, CHEMIN_HISTORIQUE, DUREE_CORRECTION, DUREE_QUESTION,
    LONGUEUR_PSEUDO, MAX_JOUEURS, MAX_TOURS, POINTS_BONNE_REPONSE,
    TOLERANCE_RESEAU,
)


def valider_configuration(noms, tours, categorie):
    """Nettoie les champs du formulaire et renvoie une configuration valide."""
    if not 1 <= len(noms) <= MAX_JOUEURS:
        raise ValueError(f"Ajoutez entre 1 et {MAX_JOUEURS} joueurs.")
    joueurs = [nom.strip() for nom in noms]
    if any(not nom or len(nom) > LONGUEUR_PSEUDO for nom in joueurs):
        raise ValueError(f"Chaque pseudo doit contenir entre 1 et {LONGUEUR_PSEUDO} caractères.")
    if len({nom.casefold() for nom in joueurs}) != len(joueurs):
        raise ValueError("Deux joueurs ne peuvent pas avoir le même pseudo.")
    try:
        tours = int(tours)
    except (ValueError, TypeError):
        raise ValueError("Le nombre de tours doit être un nombre entier.") from None
    if not 1 <= tours <= MAX_TOURS:
        raise ValueError(f"Choisissez entre 1 et {MAX_TOURS} tours.")
    if categorie and categorie not in CATEGORIES:
        raise ValueError("Ce thème n'existe pas. Choisissez un thème dans la liste.")
    return joueurs, tours, categorie or None


def creer_partie(joueurs, tours, questions, hors_ligne):
    """Crée l'état privé d'une partie à partir des joueurs et des questions."""
    return {
        "id": secrets.token_urlsafe(24),
        "date": datetime.now().astimezone().isoformat(timespec="seconds"),
        "joueurs": [{"nom": nom, "score": 0} for nom in joueurs],
        "tours": tours, "questions": questions, "hors_ligne": hors_ligne,
        "index_question": 0, "debut_question": monotonic(),
        "correction": None, "fin_correction": None, "reponses": [],
        "enregistree": False, "avertissement": None,
    }


def partie_terminee(partie):
    """Indique si toutes les questions et leur correction sont passées."""
    return partie["index_question"] >= len(partie["questions"])


def secondes_restantes(partie):
    """Calcule le temps restant à partir de l'horloge du serveur."""
    return max(0, DUREE_QUESTION - (monotonic() - partie["debut_question"]))


def etat_public(partie):
    """Construit l'affichage public sans transmettre les solutions à venir."""
    if partie_terminee(partie):
        return {"terminee": True}
    index = partie["index_question"]
    question = partie["questions"][index]
    return {
        "joueurs": partie["joueurs"], "joueur_actuel": index % len(partie["joueurs"]),
        "tour": index // len(partie["joueurs"]) + 1, "total_tours": partie["tours"],
        "index_question": index, "total_questions": len(partie["questions"]),
        "question": question["question"], "reponses": question["reponses"],
        "theme": question["theme"], "secondes_restantes": secondes_restantes(partie),
        "duree_question": DUREE_QUESTION, "terminee": False,
        "hors_ligne": partie["hors_ligne"], "correction": partie["correction"],
        "pause_restante": max(0, (partie["fin_correction"] or 0) - monotonic()),
    }


def verifier_index(partie, index_question):
    """Refuse une requête visant une autre question ou une partie terminée."""
    if type(index_question) is not int or index_question != partie["index_question"]:
        raise ValueError("Cette question a déjà changé. Rechargez la page.")
    if partie_terminee(partie):
        raise ValueError("Cette partie est terminée.")


def preparer_correction(partie, reponse):
    """Compare une réponse à la solution et prépare la trace de cette question."""
    question = partie["questions"][partie["index_question"]]
    if reponse is not None and (not isinstance(reponse, str) or reponse not in question["reponses"]):
        raise ValueError("Choisissez l'une des quatre réponses proposées.")
    ecoule = monotonic() - partie["debut_question"]
    # Au-delà de la petite tolérance réseau, aucune réponse tardive n'est notée.
    if ecoule > DUREE_QUESTION + TOLERANCE_RESEAU:
        reponse = None
    joueur = partie["joueurs"][partie["index_question"] % len(partie["joueurs"])]
    return {
        "joueur": joueur["nom"], "question": question["question"],
        "theme": question["theme"], "reponse": reponse,
        "bonne_reponse": question["bonne_reponse"],
        "juste": reponse == question["bonne_reponse"],
        "temps_ecoule": ecoule >= DUREE_QUESTION,
    }


def verifier_reponse(partie, index_question, reponse):
    """Corrige une question une seule fois et ajoute les points au bon joueur."""
    verifier_index(partie, index_question)
    # Un double clic ou une nouvelle tentative réseau ne donne pas deux points.
    if partie["correction"] is not None:
        return partie["correction"]
    correction = preparer_correction(partie, reponse)
    joueur = partie["joueurs"][index_question % len(partie["joueurs"])]
    if correction["juste"]:
        joueur["score"] += POINTS_BONNE_REPONSE
    partie["reponses"].append(correction)
    partie["correction"] = correction
    partie["fin_correction"] = monotonic() + DUREE_CORRECTION
    return correction


def passer_au_joueur_suivant(partie, index_question):
    """Avance après la correction et démarre le chrono de la question suivante."""
    verifier_index(partie, index_question)
    if partie["correction"] is None:
        raise ValueError("Validez d'abord une réponse.")
    if monotonic() < partie["fin_correction"]:
        raise ValueError("La correction est encore affichée. Patientez un instant.")
    partie["index_question"] += 1
    partie["correction"] = None
    partie["fin_correction"] = None
    partie["debut_question"] = monotonic()


def calculer_resultat(partie):
    """Renvoie le classement et déclare tous les premiers ex aequo gagnants."""
    classement = sorted((dict(j) for j in partie["joueurs"]), key=lambda j: -j["score"])
    for position, joueur in enumerate(classement):
        # Deux scores égaux reçoivent le même rang (exemple : 1, 1, 3).
        joueur["rang"] = position + 1
        if position and joueur["score"] == classement[position - 1]["score"]:
            joueur["rang"] = classement[position - 1]["rang"]
    return {
        "id": partie["id"], "date": partie["date"], "tours": partie["tours"],
        "joueurs": [dict(j) for j in partie["joueurs"]], "classement": classement,
        "gagnants": [j["nom"] for j in classement if j["rang"] == 1],
        "reponses": partie["reponses"],
    }


def verifier_historique(parties):
    """Vérifie les données utiles pour éviter une erreur dans les statistiques."""
    if not isinstance(parties, list):
        raise ValueError("L'historique doit contenir une liste de parties.")
    for partie in parties:
        if not isinstance(partie, dict) or not isinstance(partie.get("joueurs"), list):
            raise ValueError("Une partie de l'historique est mal formée.")
        if not all(cle in partie for cle in ("id", "date", "gagnants", "tours")):
            raise ValueError("Une partie de l'historique est incomplète.")
        if (not isinstance(partie["id"], str) or not isinstance(partie["date"], str)
                or type(partie["tours"]) is not int or partie["tours"] < 1
                or not isinstance(partie["gagnants"], list)
                or any(not isinstance(nom, str) for nom in partie["gagnants"])):
            raise ValueError("Les informations d'une partie sont mal formées.")
        for joueur in partie["joueurs"]:
            if (not isinstance(joueur, dict) or not isinstance(joueur.get("nom"), str)
                    or type(joueur.get("score")) is not int or joueur["score"] < 0):
                raise ValueError("Un score de l'historique est mal formé.")
    return parties


def lire_historique():
    """Lit le fichier JSON ; crée une liste vide s'il n'existe pas encore."""
    try:
        if not CHEMIN_HISTORIQUE.exists():
            CHEMIN_HISTORIQUE.write_text("[]\n", encoding="utf-8")
        return verifier_historique(json.loads(CHEMIN_HISTORIQUE.read_text(encoding="utf-8")))
    except (OSError, ValueError) as erreur:
        # On ne remplace jamais silencieusement un historique endommagé.
        raise ValueError("Historique illisible : vérifiez le fichier historique.json.") from erreur


def enregistrer_partie(partie):
    """Enregistre une partie complète une seule fois et signale une erreur de fichier."""
    if partie["enregistree"] or len(partie["reponses"]) != len(partie["questions"]):
        return
    try:
        historique = lire_historique()
        if not any(p["id"] == partie["id"] for p in historique):
            historique.append(calculer_resultat(partie))
            # Le remplacement évite de laisser un demi-fichier en cas d'écriture interrompue.
            temporaire = CHEMIN_HISTORIQUE.with_suffix(".tmp")
            temporaire.write_text(json.dumps(historique, ensure_ascii=False, indent=2), encoding="utf-8")
            temporaire.replace(CHEMIN_HISTORIQUE)
        partie["enregistree"] = True
        partie["avertissement"] = None
    except (OSError, ValueError):
        partie["avertissement"] = "La partie est terminée, mais l'historique n'a pas pu être enregistré."


def calculer_statistiques(parties):
    """Calcule des statistiques à partir des scores, regroupés par pseudo."""
    par_joueur = {}
    for partie in parties:
        for joueur in partie["joueurs"]:
            cle = joueur["nom"].casefold()
            fiche = par_joueur.setdefault(cle, {"nom": joueur["nom"], "scores": []})
            fiche["scores"].append(joueur["score"])
    joueurs = [statistiques_joueur(fiche) for fiche in par_joueur.values()]
    scores = [score for fiche in par_joueur.values() for score in fiche["scores"]]
    return {
        "nombre_parties": len(parties), "meilleur_score": max(scores, default=0),
        "moyenne_globale": round(sum(scores) / len(scores), 2) if scores else 0,
        "joueurs": sorted(joueurs, key=lambda j: j["nom"].casefold()),
    }


def statistiques_joueur(fiche):
    """Transforme la liste des scores d'un joueur en une ligne de statistiques."""
    scores = fiche["scores"]
    return {"nom": fiche["nom"], "parties": len(scores), "meilleur_score": max(scores),
            "score_moyen": round(sum(scores) / len(scores), 2)}
