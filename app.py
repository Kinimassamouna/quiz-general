"""Relie les pages et les requêtes du navigateur aux fonctions Python du quiz."""

from threading import Lock

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

import config
from api_questions import recuperer_questions
from logique_jeu import (
    calculer_resultat, calculer_statistiques, creer_partie, enregistrer_partie,
    etat_public, lire_historique, partie_terminee, passer_au_joueur_suivant,
    valider_configuration, verifier_reponse,
)

app = Flask(__name__)
app.config.update(SECRET_KEY=config.CLE_SECRETE, SESSION_COOKIE_HTTPONLY=True,
                  SESSION_COOKIE_SAMESITE="Lax", MAX_CONTENT_LENGTH=16 * 1024)

# Une session possède un identifiant. Les solutions restent dans ce dictionnaire
# du serveur. Ce choix simple convient à un seul processus pour la démonstration.
PARTIES = {}
VERROU = Lock()  # Empêche deux requêtes simultanées de compter deux fois une réponse.


@app.context_processor
def configuration_affichage():
    """Fournit aux templates les constantes utiles à l'affichage seulement."""
    return {"config_ui": {
        "duree_question": config.DUREE_QUESTION, "max_joueurs": config.MAX_JOUEURS,
        "tours_defaut": config.TOURS_PAR_DEFAUT, "max_tours": config.MAX_TOURS,
        "points": config.POINTS_BONNE_REPONSE, "longueur_pseudo": config.LONGUEUR_PSEUDO,
    }}


@app.get("/")
def index():
    """Affiche le formulaire de préparation d'une partie."""
    return render_template("index.html", joueurs=[""], tours=config.TOURS_PAR_DEFAUT,
                           categorie="", categories=config.CATEGORIES, erreur=None)


@app.post("/commencer")
def commencer():
    """Valide le formulaire, charge les questions et crée la partie côté serveur."""
    noms, tours = request.form.getlist("joueurs"), request.form.get("tours", "")
    categorie = request.form.get("categorie", "")
    try:
        joueurs, nombre_tours, theme = valider_configuration(noms, tours, categorie)
        questions, secours = recuperer_questions(len(joueurs) * nombre_tours, theme)
    except ValueError as erreur:
        return render_template("index.html", joueurs=noms[:config.MAX_JOUEURS] or [""],
                               tours=tours, categorie=categorie, categories=config.CATEGORIES,
                               erreur=str(erreur)), 400
    partie = creer_partie(joueurs, nombre_tours, questions, secours)
    with VERROU:
        PARTIES.pop(session.get("partie_id"), None)
        PARTIES[partie["id"]] = partie
    session.clear()
    session["partie_id"] = partie["id"]
    return redirect(url_for("jeu"))


@app.get("/jeu")
def jeu():
    """Affiche la question en cours sans donner sa bonne réponse."""
    with VERROU:
        partie = PARTIES.get(session.get("partie_id"))
        if partie is None:
            return redirect(url_for("index"))
        if partie_terminee(partie):
            return redirect(url_for("resultats"))
        return render_template("jeu.html", etat=etat_public(partie))


@app.get("/api/etat")
def obtenir_etat():
    """Permet au navigateur de retrouver l'état après une erreur réseau."""
    with VERROU:
        partie = PARTIES.get(session.get("partie_id"))
        if partie is None:
            return jsonify(erreur="La partie n'existe plus. Revenez à l'accueil."), 404
        return jsonify(etat_public(partie))


@app.post("/api/repondre")
def repondre():
    """Reçoit uniquement le choix du joueur et demande sa correction au serveur."""
    donnees = request.get_json(silent=True)
    if not isinstance(donnees, dict):
        return jsonify(erreur="La réponse envoyée est invalide."), 400
    with VERROU:
        partie = PARTIES.get(session.get("partie_id"))
        if partie is None:
            return jsonify(erreur="La partie n'existe plus. Revenez à l'accueil."), 404
        try:
            correction = verifier_reponse(partie, donnees.get("index_question"), donnees.get("reponse"))
        except ValueError as erreur:
            return jsonify(erreur=str(erreur)), 400
        enregistrer_partie(partie)
        return jsonify(correction=correction, etat=etat_public(partie))


@app.post("/api/suivante")
def suivante():
    """Passe à la question suivante seulement après la correction."""
    donnees = request.get_json(silent=True)
    if not isinstance(donnees, dict):
        return jsonify(erreur="La demande est invalide."), 400
    with VERROU:
        partie = PARTIES.get(session.get("partie_id"))
        if partie is None:
            return jsonify(erreur="La partie n'existe plus. Revenez à l'accueil."), 404
        try:
            passer_au_joueur_suivant(partie, donnees.get("index_question"))
        except ValueError as erreur:
            return jsonify(erreur=str(erreur)), 400
        return jsonify(etat_public(partie))


@app.get("/resultats")
def resultats():
    """Montre le classement et les réponses d'une partie terminée."""
    with VERROU:
        partie = PARTIES.get(session.get("partie_id"))
        if partie is None:
            return redirect(url_for("index"))
        if not partie_terminee(partie):
            return redirect(url_for("jeu"))
        enregistrer_partie(partie)
        return render_template("resultats.html", resultat=calculer_resultat(partie),
                               avertissement=partie["avertissement"])


@app.get("/historique")
def historique():
    """Affiche les parties conservées dans le fichier JSON."""
    try:
        with VERROU:
            parties = lire_historique()
        return render_template("historique.html", parties=list(reversed(parties)), erreur=None)
    except ValueError as erreur:
        return render_template("historique.html", parties=[], erreur=str(erreur))


@app.get("/statistiques")
def statistiques():
    """Affiche les totaux et les moyennes par pseudo."""
    try:
        with VERROU:
            parties = lire_historique()
        erreur = None
    except ValueError as probleme:
        parties, erreur = [], str(probleme)
    return render_template("statistiques.html", stats=calculer_statistiques(parties), erreur=erreur)


if __name__ == "__main__":
    # Le mode debug reste désactivé. Ouvrir http://127.0.0.1:5000 dans un navigateur.
    app.run(host="127.0.0.1", port=5000, debug=False)
