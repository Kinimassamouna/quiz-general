/* Ce fichier anime le formulaire et le jeu ; Python décide des bonnes réponses. */
"use strict";

const configuration = JSON.parse(document.querySelector("#configuration").textContent);

// 1. Configuration : ajouter, retirer et vérifier les pseudos sans recharger.
function initialiserFormulaire() {
    // Cette fonction ne s'exécute que sur la page d'accueil.
    const formulaire = document.querySelector("#form-configuration");
    if (!formulaire) return;
    const liste = document.querySelector("#liste-joueurs");
    document.querySelector("#ajouter-joueur").addEventListener("click", () => {
        if (liste.children.length >= configuration.max_joueurs) return;
        const champ = liste.firstElementChild.cloneNode(true);
        champ.querySelector("input").value = "";
        champ.querySelector("input").setCustomValidity("");
        liste.append(champ);
        renumeroterJoueurs();
        champ.querySelector("input").focus();
    });
    liste.addEventListener("click", retirerJoueur);
    liste.addEventListener("input", verifierPseudos);
    formulaire.addEventListener("submit", preparerDemarrage);
    renumeroterJoueurs();
}

function renumeroterJoueurs() {
    // Chaque champ garde un numéro et un label correspondant à son input.
    const champs = document.querySelectorAll(".champ-joueur");
    champs.forEach((champ, index) => {
        const saisie = champ.querySelector("input");
        saisie.id = `joueur-${index + 1}`;
        saisie.placeholder = `Pseudo du joueur ${index + 1}`;
        const label = champ.querySelector("label");
        label.htmlFor = saisie.id;
        label.textContent = `Joueur ${index + 1}`;
        const retrait = champ.querySelector("[data-retirer]");
        retrait.hidden = index === 0;
        retrait.disabled = index === 0;
        retrait.setAttribute("aria-label", `Retirer le joueur ${index + 1}`);
    });
    document.querySelector("#ajouter-joueur").disabled = champs.length >= configuration.max_joueurs;
    verifierPseudos();
}

function retirerJoueur(evenement) {
    // La délégation de clic fonctionne aussi pour les nouveaux champs.
    const bouton = evenement.target.closest("[data-retirer]");
    if (!bouton || bouton.disabled) return;
    bouton.closest(".champ-joueur").remove();
    renumeroterJoueurs();
}

function verifierPseudos() {
    // On refait exactement ces contrôles en Python : le JS peut être contourné.
    const noms = new Set();
    document.querySelectorAll(".champ-joueur input").forEach(saisie => {
        const nom = saisie.value.trim();
        let erreur = "";
        if (!nom) erreur = "Saisissez un pseudo.";
        else if (nom.length > configuration.longueur_pseudo) erreur = "Pseudo trop long.";
        else if (noms.has(nom.toLocaleLowerCase("fr"))) erreur = "Ce pseudo est déjà utilisé.";
        saisie.setCustomValidity(erreur);
        noms.add(nom.toLocaleLowerCase("fr"));
    });
}

function preparerDemarrage(evenement) {
    // Le formulaire habituel fait un POST vers Flask après les vérifications.
    verifierPseudos();
    if (!evenement.target.reportValidity()) {
        evenement.preventDefault();
        return;
    }
    const bouton = evenement.target.querySelector('[type="submit"]');
    bouton.disabled = true;
    bouton.textContent = "Préparation des questions…";
}

// 2. État d'affichage : aucune solution n'est connue avant la correction Python.
let etat = null;
let reponseChoisie = null;
let envoiEnCours = false;
let erreurReseau = false;
let finChronometre = 0;
let intervalleChrono = null;
let attenteCorrection = null;

function initialiserJeu() {
    // L'état initial ne contient que la question visible et ses quatre choix.
    const donnees = document.querySelector("#etat-initial");
    if (!donnees) return;
    document.querySelectorAll(".reponse").forEach(bouton => {
        bouton.addEventListener("click", () => selectionnerReponse(Number(bouton.dataset.reponse)));
    });
    document.querySelector("#valider").addEventListener("click", () => {
        if (etat.correction) passerQuestion();
        else validerReponse();
    });
    afficherEtat(JSON.parse(donnees.textContent));
}

function afficherEtat(nouvelEtat) {
    // Chaque nouvel état remplace l'affichage ; un seul chrono reste actif.
    clearInterval(intervalleChrono);
    clearTimeout(attenteCorrection);
    if (nouvelEtat.terminee) {
        window.location.href = "/resultats";
        return;
    }
    etat = nouvelEtat;
    reponseChoisie = null;
    envoiEnCours = false;
    erreurReseau = false;
    afficherQuestion();
    afficherJoueurs();
    finChronometre = performance.now() + etat.secondes_restantes * 1000;
    dessinerChronometre(etat.secondes_restantes);
    if (etat.correction) afficherCorrection();
    else {
        intervalleChrono = setInterval(actualiserChronometre, 100);
        actualiserChronometre();
    }
}

function afficherQuestion() {
    // textContent affiche les textes reçus comme du texte, jamais comme du HTML.
    document.querySelector("#question").textContent = etat.question;
    document.querySelector("#theme").textContent = etat.theme;
    document.querySelector("#progression-tour").textContent = `Tour ${etat.tour} / ${etat.total_tours}`;
    document.querySelector("#progression-question").textContent = `Question ${etat.index_question + 1} sur ${etat.total_questions}`;
    const retour = document.querySelector("#retour-reponse");
    retour.textContent = "";
    retour.classList.remove("succes", "echec");
    document.querySelectorAll(".reponse").forEach((bouton, index) => {
        const texte = bouton.querySelector(".texte-reponse");
        if (texte) texte.textContent = etat.reponses[index];
        else bouton.textContent = etat.reponses[index];
        bouton.classList.remove("selectionnee", "correcte", "incorrecte", "attente");
        bouton.disabled = false;
        bouton.setAttribute("aria-pressed", "false");
    });
    document.querySelector("#valider").textContent = "Valider";
    document.querySelector("#valider").disabled = true;
}

function afficherJoueurs() {
    // Le joueur mis en lumière et le message viennent du même index Python.
    document.querySelectorAll("[data-joueur]").forEach(element => {
        const actif = Number(element.dataset.joueur) === etat.joueur_actuel;
        element.classList.toggle("actif", actif);
        if (actif) element.setAttribute("aria-current", "true");
        else element.removeAttribute("aria-current");
    });
    document.querySelector("#message-joueur").textContent = `À vous de jouer ${etat.joueurs[etat.joueur_actuel].nom} !`;
    document.querySelectorAll("[data-score-joueur]").forEach(element => {
        const numero = Number(element.dataset.scoreJoueur);
        const score = etat.joueurs[numero].score;
        element.classList.toggle("actif", numero === etat.joueur_actuel);
        const valeur = element.querySelector(".valeur-score");
        element.classList.remove("pulse");
        if (Number(valeur.textContent) < score) element.classList.add("pulse");
        valeur.textContent = score;
        element.querySelector(".legende-score").textContent = score === 1 ? "point" : "points";
    });
}

function selectionnerReponse(index) {
    // Le choix peut changer tant que la question n'est pas validée et qu'il reste du temps.
    if (envoiEnCours || erreurReseau || etat.correction || performance.now() >= finChronometre) return;
    reponseChoisie = etat.reponses[index];
    document.querySelectorAll(".reponse").forEach((bouton, numero) => {
        bouton.classList.toggle("selectionnee", numero === index);
        bouton.setAttribute("aria-pressed", String(numero === index));
    });
    document.querySelector("#valider").disabled = false;
}

function actualiserChronometre() {
    // L'horloge réelle évite que les ralentissements d'un onglet allongent la partie.
    const restant = Math.max(0, (finChronometre - performance.now()) / 1000);
    dessinerChronometre(restant);
    if (restant === 0 && !envoiEnCours && !erreurReseau) validerReponse();
}

function dessinerChronometre(restant) {
    // Le cercle SVG utilise pathLength=100 : la valeur représente un pourcentage.
    document.querySelector("#temps-restant").textContent = Math.ceil(restant);
    document.querySelector(".chrono-progression").style.strokeDashoffset = 100 * (1 - restant / etat.duree_question);
    const chrono = document.querySelector("#chrono");
    chrono.classList.toggle("urgent", restant <= 10 && restant > 5);
    chrono.classList.toggle("critique", restant <= 5);
    chrono.setAttribute("aria-label", `${Math.ceil(restant)} secondes restantes`);
}

async function envoyerJSON(url, donnees) {
    // Les réponses et les scores sont toujours calculés par Flask.
    const controle = new AbortController();
    const delai = setTimeout(() => controle.abort(), 8000);
    try {
        const reponse = await fetch(url, {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify(donnees), signal: controle.signal,
        });
        const resultat = await reponse.json();
        if (!reponse.ok) {
            const erreur = new Error(resultat.erreur);
            erreur.status = reponse.status;
            throw erreur;
        }
        return resultat;
    } finally {
        clearTimeout(delai);
    }
}

async function validerReponse() {
    // Une requête déjà envoyée ne peut pas être doublée par le chrono.
    if (envoiEnCours || etat.correction) return;
    verrouillerBoutons();
    try {
        const resultat = await envoyerJSON("/api/repondre", {
            index_question: etat.index_question, reponse: reponseChoisie,
        });
        afficherEtat(resultat.etat);
    } catch (erreur) {
        await afficherErreurReseau(erreur);
    }
}

function verrouillerBoutons() {
    // On conserve le choix envoyé pour pouvoir retenter la même requête.
    envoiEnCours = true;
    document.querySelectorAll(".reponse").forEach(bouton => bouton.disabled = true);
    document.querySelector("#valider").disabled = true;
}

function afficherCorrection() {
    // La solution n'arrive dans le navigateur qu'après la validation.
    const correction = etat.correction;
    const retour = document.querySelector("#retour-reponse");
    retour.classList.add(correction.juste ? "succes" : "echec");
    const debut = correction.juste ? "Bonne réponse !" : "Mauvaise réponse.";
    retour.textContent = `${correction.reponse === null ? "Aucune réponse." : debut} La bonne réponse : ${correction.bonne_reponse}`;
    document.querySelectorAll(".reponse").forEach((bouton, index) => {
        bouton.disabled = true;
        bouton.classList.toggle("correcte", etat.reponses[index] === correction.bonne_reponse);
        bouton.classList.toggle("incorrecte", !correction.juste && etat.reponses[index] === correction.reponse);
    });
    document.querySelector("#valider").disabled = true;
    document.querySelector("#valider").textContent = "Correction…";
    attenteCorrection = setTimeout(passerQuestion, etat.pause_restante * 1000 + 100);
}

async function passerQuestion() {
    // Après la pause donnée par le serveur, on demande le prochain état.
    if (envoiEnCours) return;
    verrouillerBoutons();
    try {
        afficherEtat(await envoyerJSON("/api/suivante", {index_question: etat.index_question}));
    } catch (erreur) {
        await afficherErreurReseau(erreur);
    }
}

async function afficherErreurReseau(erreur) {
    // Une requête perdue peut avoir réussi côté serveur : on se resynchronise.
    envoiEnCours = false;
    erreurReseau = true;
    if (erreur.status === 400) {
        try {
            const reponse = await fetch("/api/etat", {cache: "no-store"});
            if (reponse.ok) { afficherEtat(await reponse.json()); return; }
        } catch (_) { /* Le message ci-dessous permet une nouvelle tentative. */ }
    }
    const retour = document.querySelector("#retour-reponse");
    retour.classList.add("echec");
    retour.textContent = erreur.status === 404 ? erreur.message : "Connexion interrompue. Vérifiez le serveur puis cliquez sur Réessayer.";
    const bouton = document.querySelector("#valider");
    bouton.textContent = "Réessayer";
    bouton.disabled = erreur.status === 404;
}

initialiserFormulaire();
initialiserJeu();
