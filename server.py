import io
import os
import re
import sys
import time
import logging
import threading
import urllib.request
from contextlib import asynccontextmanager
from pathlib import Path
from contextlib import redirect_stdout

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "src"))

from main import run_agent, warm_up
import main as agent
import tools

log = logging.getLogger("iset")
@asynccontextmanager
async def lifespan(_app):
    # Charge le modèle en arrière-plan : la 1re question n'attend plus.
    threading.Thread(target=warm_up, daemon=True).start()
    yield


app = FastAPI(title="ISET Charguia | Assistant IA", lifespan=lifespan)

# Un seul appel à la fois : run_agent écrit sur stdout, qu'on capture.
agent_lock = threading.Lock()


class HistoryItem(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=2000)


class ChatIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[HistoryItem] = Field(default_factory=list, max_length=6)


# ---------------------------------------------------------------
# Règlement : texte officiel d'un article (interface : clic sur « Article N »)
# ---------------------------------------------------------------
_ART_RE = re.compile(r"^ARTICLE\s+(\d+)\s*-\s*(.+)$", re.M)


def load_articles():
    files = sorted((BASE_DIR / "data").glob("reglement*.txt"))
    if not files:
        return {}
    text = files[0].read_text(encoding="utf-8", errors="replace")
    text = text.replace("\r", "")
    found = list(_ART_RE.finditer(text))
    articles = {}
    for i, m in enumerate(found):
        end = found[i + 1].start() if i + 1 < len(found) else len(text)
        number = int(m.group(1))
        articles[number] = {
            "article": number,
            "title": m.group(2).strip(),
            "text": text[m.end():end].strip(),
        }
    return articles


@app.get("/api/articles")
def articles_list():
    return {"articles": sorted(load_articles())}


@app.get("/api/article/{number}")
def article(number: int):
    found = load_articles().get(number)
    if found is None:
        raise HTTPException(status_code=404, detail="Article introuvable.")
    return found


def retrieved_articles(question, steps):
    """Articles que la recherche documentaire a envoyés au modèle."""
    if not any("Question scolaire détectée" in s for s in steps):
        return []
    try:
        extracts = agent.search_documents(question)
    except Exception:
        return []
    numbers = re.findall(r"ARTICLE\s+(\d+)", extracts)
    return [int(n) for n in dict.fromkeys(numbers)]


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/chat")
def chat(body: ChatIn):
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question vide.")

    buffer = io.StringIO()
    try:
        with agent_lock, redirect_stdout(buffer):
            answer = run_agent(
                question, [h.model_dump() for h in body.history]
            )
    except Exception:
        log.exception("Erreur dans run_agent")
        raise HTTPException(
            status_code=503,
            detail="L'assistant est indisponible. Vérifiez que le serveur "
                   "Ollama est démarré et que le modèle est disponible.",
        )

    steps = [
        line.strip()
        for line in buffer.getvalue().splitlines()
        if "[AGENT]" in line or "[PERFORMANCE]" in line
    ]

    # Brouillon de demande créé pendant cet appel (jamais envoyé ici) :
    # l'interface le montre et attend le clic de l'étudiant.
    drafts = tools.consume_new_drafts()
    draft = drafts[-1] if drafts else None

    return {
        "answer": str(answer),
        "steps": steps,
        "draft": draft,
        "model": agent.MODEL_NAME,
        "retrieved": retrieved_articles(question, steps),
    }


# ---------------------------------------------------------------
# Comparaison de modèles : même question, même agent, modèle différent
# ---------------------------------------------------------------
COMPARE_MODELS = [
    m.strip() for m in os.environ.get(
        "COMPARE_MODELS", "qwen3:4b-instruct,llama3.2:3b").split(",")
    if m.strip()
]


class CompareIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


@app.post("/api/compare")
def compare(body: CompareIn):
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question vide.")

    results = []
    with agent_lock:
        original = agent.MODEL_NAME
        try:
            for model in COMPARE_MODELS:
                agent.MODEL_NAME = model
                agent._ANSWER_CACHE.clear()  # le cache ne tient pas compte du modèle
                buffer = io.StringIO()
                start = time.perf_counter()
                answer, error = "", None
                try:
                    with redirect_stdout(buffer):
                        answer = agent.run_agent(question, [])
                except Exception:
                    log.exception("Comparaison : erreur avec %s", model)
                    error = (f"Modèle indisponible. Lancez : "
                             f"ollama pull {model}")
                tools.consume_new_drafts()  # jamais de brouillon en comparaison
                results.append({
                    "model": model,
                    "answer": str(answer),
                    "error": error,
                    "seconds": round(time.perf_counter() - start, 1),
                })
        finally:
            agent.MODEL_NAME = original
            agent._ANSWER_CACHE.clear()

    return {"results": results}


# Validation humaine : seul un clic de l'étudiant déclenche l'envoi.
@app.post("/api/demande/{draft_id}/confirmer")
def confirmer_demande(draft_id: str):
    return tools.confirmer_envoi(draft_id)


@app.post("/api/demande/{draft_id}/annuler")
def annuler_demande(draft_id: str):
    return tools.annuler_brouillon(draft_id)


LOGO_URL = "https://isaca-tunisie.org/wp-content/uploads/2017/03/ISET-charguia_logo.png"
LOGO_NAMES = {"iset_logo", "logo", "iset"}
LOGO_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
_logo_cache = {}


def download_logo():
    """Télécharge le logo une seule fois et le garde dans assets/."""
    target = BASE_DIR / "assets" / "iset_logo.png"
    try:
        target.parent.mkdir(exist_ok=True)
        req = urllib.request.Request(
            LOGO_URL, headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read()
        if not data.startswith(b"\x89PNG"):
            return None
        target.write_bytes(data)
        return target
    except Exception:
        log.exception("Téléchargement du logo impossible")
        return None


def find_logo():
    """Cherche le logo de l'ISET dans les dossiers habituels du projet."""
    if "path" in _logo_cache:
        return _logo_cache["path"]
    folders = [
        BASE_DIR / "assets", BASE_DIR, BASE_DIR / "web", BASE_DIR / "static",
        BASE_DIR / "src", BASE_DIR.parent / "assets", BASE_DIR.parent,
    ]
    found = None
    for folder in folders:
        if not folder.is_dir():
            continue
        for f in sorted(folder.iterdir()):
            if f.is_file() and f.stem.lower() in LOGO_NAMES \
                    and f.suffix.lower() in LOGO_EXTS:
                found = f
                break
        if found:
            break
    if found is None and not _logo_cache.get("tried"):
        _logo_cache["tried"] = True
        found = download_logo()
    if found is None:
        log.warning("Logo introuvable (attendu : assets/iset_logo.png)")
    else:
        _logo_cache["path"] = found
    return found


@app.get("/logo")
def logo():
    path = find_logo()
    if path is None:
        raise HTTPException(status_code=404, detail="Logo introuvable.")
    return FileResponse(path)


assets_dir = BASE_DIR / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "web" / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)