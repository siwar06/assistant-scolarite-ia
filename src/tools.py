"""Outils de l'assistant de scolarité (ISET Charguia).

Ce fichier est la SEULE implémentation des outils. Il est utilisé :
  - par l'agent (src/main.py), qui les appelle quand le modèle le demande ;
  - par le serveur MCP (mcp_server.py), qui les expose à tout client MCP.

Le modèle ne fait que DEMANDER un outil : c'est ce programme qui l'exécute.

Outils :
  1. search_reglement(query)   : recherche dans le règlement et le calendrier
  2. get_calendrier(module)    : dates d'examen et de rattrapage d'un module
  3. generer_demande(...)      : prépare un BROUILLON de demande de rattrapage

Action sensible : l'envoi d'une demande. Il n'existe AUCUN outil d'envoi :
generer_demande ne fait que créer un brouillon. L'envoi n'est possible que
par confirmer_envoi(), appelée par l'interface après un clic explicite de
l'étudiant (validation humaine).
"""

import os
import re
import smtplib
import threading
import unicodedata
import uuid
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CALENDRIER_PATH = BASE_DIR / "data" / "calendrier_janvier_2027.txt"
OUTBOX_DIR = BASE_DIR / "demandes_envoyees"

MOTIFS = {
    "maladie": {"article_delai": 4, "jours": 3, "label": "maladie"},
    "hospitalisation": {"article_delai": 6, "jours": 7,
                        "label": "hospitalisation"},
}


# --------------------------------------------------
# Utilitaires
# --------------------------------------------------

def _norm(text):
    text = unicodedata.normalize("NFD", str(text).lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", text).strip()


def _parse_date(text):
    return datetime.strptime(text, "%d/%m/%Y")


def _fmt(date):
    return date.strftime("%d/%m/%Y")


def add_business_days(start, days):
    """Ajoute des jours ouvrables (lun-ven). Le jour de départ n'est pas
    compté (article 4 du règlement)."""

    current = start

    while days > 0:
        current += timedelta(days=1)

        if current.weekday() < 5:
            days -= 1

    return current


# --------------------------------------------------
# Calendrier
# --------------------------------------------------

def load_calendrier():
    """Lit le calendrier et renvoie {nom du module: {champs}}."""

    text = CALENDRIER_PATH.read_text(encoding="utf-8", errors="replace")
    modules = {}

    for block in re.split(r"(?m)^MODULE\s*:\s*", text)[1:]:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        name = lines[0]
        info = {"module": name}

        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                info[_norm(key)] = value.strip()

        modules[name] = info

    return modules


MODULE_ALIASES = {
    "bd": "bases de donnees",
    "bdd": "bases de donnees",
    "base de donnees": "bases de donnees",
    "database": "bases de donnees",
    "databases": "bases de donnees",
    "reseau": "reseaux",
    "networks": "reseaux",
    "networking": "reseaux",
    "algo": "algorithmique",
    "english": "anglais",
    "projet": "projet de fin de module",
}


def has_rattrapage(info):
    """Vrai seulement si le calendrier donne une vraie date de rattrapage
    (le module Projet contient « Rattrapage : Aucun »)."""

    return bool(re.search(r"\d{2}/\d{2}/\d{4}", info.get("rattrapage", "")))


def find_module(name):
    """Retrouve un module du calendrier à partir d'un nom approximatif."""

    if not isinstance(name, str) or not name.strip():
        return None

    wanted = _norm(name)
    wanted = MODULE_ALIASES.get(wanted, wanted)

    for module, info in load_calendrier().items():
        if _norm(module) == wanted:
            return info

    for module, info in load_calendrier().items():
        if wanted in _norm(module) or _norm(module) in wanted:
            return info

    return None


# --------------------------------------------------
# Outil 1 : recherche dans les documents
# --------------------------------------------------

def search_reglement(query):
    """Recherche dans le règlement et le calendrier (voir main.py)."""

    from main import search_documents  # import tardif : évite la boucle

    return search_documents(query)


# --------------------------------------------------
# Outil 2 : calendrier
# --------------------------------------------------

def get_calendrier(module):
    """Date d'examen et de rattrapage d'un module."""

    info = find_module(module)

    if info is None:
        known = ", ".join(load_calendrier())
        return (
            f"Module introuvable dans le calendrier : « {module} ». "
            f"Modules connus : {known}."
        )

    if not has_rattrapage(info):
        return (
            f"Module : {info['module']}. "
            f"Évaluation : {info.get('evaluation', 'projet')}. "
            f"Date de remise : {info.get('date de remise', 'non précisée')}. "
            "Pas de session de rattrapage (Article 10)."
        )

    return (
        f"Module : {info['module']}. "
        f"Examen : {info['examen']} ({info['lieu']}). "
        f"Rattrapage : {info['rattrapage']} "
        f"({info['lieu du rattrapage']})."
    )


# --------------------------------------------------
# Outil 3 : génération d'un BROUILLON de demande
# --------------------------------------------------

_DRAFTS = {}
_NEW_DRAFT_IDS = []
_LOCK = threading.Lock()


def _clean_field(value, max_len):
    value = re.sub(r"[\r\n\t]+", " ", str(value)).strip()
    return value[:max_len]


def generer_demande(nom_etudiant, numero_etudiant, module, motif):
    """Prépare le BROUILLON d'une demande de rattrapage (Articles 7 et 8).

    N'envoie rien. Renvoie le texte du brouillon ou une erreur claire."""

    nom = _clean_field(nom_etudiant, 80)
    numero = _clean_field(numero_etudiant, 20)
    motif_key = _norm(motif or "")

    if len(nom) < 3 or not re.fullmatch(r"[\w' .-]+", nom):
        return "Erreur : le nom complet de l'étudiant est invalide ou absent."

    if not re.fullmatch(r"[A-Za-z0-9-]{4,20}", numero):
        return ("Erreur : le numéro étudiant est invalide ou absent "
                "(4 à 20 lettres ou chiffres).")

    if motif_key not in MOTIFS:
        return ("Erreur : le motif doit être « maladie » ou "
                "« hospitalisation ».")

    info = find_module(module)

    if info is None:
        return (f"Erreur : module introuvable dans le calendrier : "
                f"« {module} ».")

    if not has_rattrapage(info):
        return (f"Erreur : le module {info['module']} est évalué par projet "
                "et ne bénéficie pas de rattrapage (Article 10).")

    rule = MOTIFS[motif_key]
    exam_date = _parse_date(info["examen"].split(" à ")[0])
    deadline = add_business_days(exam_date, rule["jours"])
    today = os.environ.get("DATE_DEMANDE") or _fmt(datetime.now())

    pieces = ["certificat médical daté du jour de l'examen ou de la veille, "
              "signé et cacheté, précisant la durée de l'incapacité "
              "(Article 5)"]

    if motif_key == "hospitalisation":
        pieces = ["bulletin d'hospitalisation (Article 6)"]

    letter = (
        f"Date : {today}\n"
        f"Objet : Demande de session de rattrapage - module "
        f"{info['module']}\n\n"
        "À l'attention du responsable du bureau de scolarité,\n"
        "ISET Charguia\n\n"
        "Madame, Monsieur,\n\n"
        f"Je soussigné(e) {nom}, numéro étudiant {numero}, vous prie de "
        f"bien vouloir m'autoriser à passer la session de rattrapage du "
        f"module {info['module']}.\n\n"
        f"J'étais absent(e) à l'examen du {_fmt(exam_date)} pour cause de "
        f"{rule['label']}. Conformément aux articles 4, 7 et 8 du "
        f"règlement des études, je joins à cette demande les pièces "
        f"justificatives suivantes : {pieces[0]}.\n\n"
        f"Le rattrapage est prévu le {info['rattrapage']} "
        f"({info['lieu du rattrapage']}).\n\n"
        "Veuillez agréer, Madame, Monsieur, l'expression de mes "
        "salutations distinguées.\n\n"
        f"{nom}\nNuméro étudiant : {numero}"
    )

    draft_id = uuid.uuid4().hex[:8]

    with _LOCK:
        _DRAFTS[draft_id] = {
            "id": draft_id,
            "text": letter,
            "module": info["module"],
            "deadline": _fmt(deadline),
            "status": "en_attente",
        }
        _NEW_DRAFT_IDS.append(draft_id)

    return (
        f"BROUILLON {draft_id} créé (NON ENVOYÉ). "
        f"Date limite de dépôt du justificatif : {_fmt(deadline)} "
        f"({rule['jours']} jours ouvrables après l'examen, "
        f"Article {rule['article_delai']}). "
        "L'étudiant doit relire le brouillon et le confirmer dans "
        "l'interface avant tout envoi.\n\n" + letter
    )


# --------------------------------------------------
# Validation humaine : brouillons et envoi
# --------------------------------------------------

def consume_new_drafts():
    """Brouillons créés depuis le dernier appel (pour l'interface)."""

    with _LOCK:
        ids = list(_NEW_DRAFT_IDS)
        _NEW_DRAFT_IDS.clear()
        return [dict(_DRAFTS[i]) for i in ids if i in _DRAFTS]


def annuler_brouillon(draft_id):
    with _LOCK:
        draft = _DRAFTS.get(draft_id)

        if not draft or draft["status"] != "en_attente":
            return {"ok": False, "message": "Brouillon introuvable."}

        draft["status"] = "annule"

    return {"ok": True, "message": "Brouillon annulé. Rien n'a été envoyé."}


def confirmer_envoi(draft_id):
    """Envoie la demande APRÈS accord explicite de l'étudiant.

    Si le SMTP n'est pas configuré (variables d'environnement SMTP_HOST,
    SMTP_USER, SMTP_PASSWORD, SCOLARITE_EMAIL), la demande est seulement
    enregistrée dans demandes_envoyees/ (mode démonstration)."""

    with _LOCK:
        draft = _DRAFTS.get(draft_id)

        if not draft or draft["status"] != "en_attente":
            return {"ok": False, "message": "Brouillon introuvable ou déjà "
                                            "traité."}

        draft["status"] = "envoye"
        text, module = draft["text"], draft["module"]

    host = os.environ.get("SMTP_HOST")
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    target = os.environ.get("SCOLARITE_EMAIL")

    if host and user and password and target:
        msg = EmailMessage()
        msg["Subject"] = f"Demande de rattrapage - {module}"
        msg["From"] = user
        msg["To"] = target
        msg.set_content(text)

        try:
            with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", 587)),
                              timeout=15) as smtp:
                smtp.starttls()
                smtp.login(user, password)
                smtp.send_message(msg)
        except Exception as error:
            with _LOCK:
                draft["status"] = "en_attente"
            return {"ok": False,
                    "message": f"Échec de l'envoi : {error}"}

        return {"ok": True, "message": "Demande envoyée au bureau de "
                                       "scolarité."}

    OUTBOX_DIR.mkdir(exist_ok=True)
    (OUTBOX_DIR / f"demande_{draft_id}.txt").write_text(
        text, encoding="utf-8")

    return {"ok": True,
            "message": "Mode démonstration (SMTP non configuré) : demande "
                       f"enregistrée dans demandes_envoyees/demande_"
                       f"{draft_id}.txt."}
