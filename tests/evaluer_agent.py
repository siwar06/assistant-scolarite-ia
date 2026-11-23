"""Évalue l'AGENT COMPLET (run_agent) sur le jeu de 40 questions.

Contrairement à test_models.py (qui teste le modèle seul avec un prompt),
ce script passe par exactement le même chemin que l'interface web :
détection de la langue, filtrage hors sujet, recherche, outils, validation.

Usage (Ollama lancé, modèles téléchargés avec `ollama pull`) :

    python tests/evaluer_agent.py
    python tests/evaluer_agent.py --models qwen3:4b-instruct,llama3.2:3b
    python tests/evaluer_agent.py --ids 1,2,24 --models qwen3:4b-instruct

Sorties :
    evaluation_agent_40.csv   une ligne par (modèle, question)
    resultats_evaluation.md   tableaux prêts à copier dans le rapport
Avec --ids, les sorties sont evaluation_agent_partiel.csv et
resultats_evaluation_partiel.md (les résultats complets sont conservés).
"""

import argparse
import contextlib
import csv
import io
import statistics
import sys
import time
from collections import OrderedDict, defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "src"))

import main as agent  # noqa: E402  (src/main.py)
import tools  # noqa: E402

from tests.jeu_de_test import CASES, check  # noqa: E402

DEFAULT_MODELS = ["qwen3:4b-instruct", "llama3.2:3b"]
CSV_PATH = BASE_DIR / "evaluation_agent_40.csv"
MD_PATH = BASE_DIR / "resultats_evaluation.md"


def run_case(model, case):
    """Pose une question à l'agent avec `model` et note la réponse."""

    agent.MODEL_NAME = model
    agent._ANSWER_CACHE.clear()      # pas de réponse mise en cache
    tools.consume_new_drafts()       # repart sans brouillon

    start = time.perf_counter()
    error = ""

    try:
        with contextlib.redirect_stdout(io.StringIO()):
            answer = str(agent.run_agent(case["question"]))
    except Exception as exc:         # Ollama arrêté, modèle absent, etc.
        answer, error = "", f"{type(exc).__name__}: {exc}"

    duration = round(time.perf_counter() - start, 2)
    drafts = tools.consume_new_drafts()

    if error:
        problems = [f"erreur technique : {error[:120]}"]
    else:
        problems = check(case, answer, len(drafts))

    return {
        "model": model,
        "id": case["id"],
        "category": case["category"],
        "question": case["question"],
        "expected": case["expected"],
        "answer": answer,
        "passed": int(not problems),
        "problems": " | ".join(problems),
        "duration_seconds": duration,
    }


def summarize(rows, models):
    lines = ["# Résultats de l'évaluation de l'agent", "",
             f"{len({r['id'] for r in rows})} questions, "
             f"{len(models)} modèle(s).", ""]

    lines += ["## Taux de réussite global", "",
              "| Modèle | Réussies | Taux | Temps moyen (s) | Temps médian (s) |",
              "|---|---|---|---|---|"]

    for model in models:
        mine = [r for r in rows if r["model"] == model]
        passed = sum(r["passed"] for r in mine)
        times = [r["duration_seconds"] for r in mine]
        lines.append(
            f"| {model} | {passed}/{len(mine)} | "
            f"{100 * passed / len(mine):.0f} % | "
            f"{statistics.mean(times):.1f} | {statistics.median(times):.1f} |"
        )

    categories = list(OrderedDict.fromkeys(r["category"] for r in rows))

    lines += ["", "## Taux de réussite par catégorie", "",
              "| Catégorie | " + " | ".join(models) + " |",
              "|---|" + "---|" * len(models)]

    for category in categories:
        cells = []

        for model in models:
            mine = [r for r in rows
                    if r["model"] == model and r["category"] == category]
            cells.append(f"{sum(r['passed'] for r in mine)}/{len(mine)}")

        lines.append(f"| {category} | " + " | ".join(cells) + " |")

    lines += ["", "## Questions échouées", ""]
    failed = defaultdict(list)

    for r in rows:
        if not r["passed"]:
            failed[r["model"]].append(r)

    for model in models:
        lines.append(f"### {model}")

        if not failed[model]:
            lines += ["", "Aucune.", ""]
            continue

        lines.append("")

        for r in failed[model]:
            lines.append(
                f"- **#{r['id']}** ({r['category']}) {r['question']} "
                f"-> {r['problems']}"
            )

        lines.append("")

    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    parser.add_argument("--ids", default="",
                        help="numéros de questions, ex. 1,2,24")
    args = parser.parse_args(argv)

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    wanted = {int(i) for i in args.ids.split(",") if i.strip()}
    cases = [c for c in CASES if not wanted or c["id"] in wanted]

    # Un essai partiel (--ids) ne doit jamais écraser les résultats
    # complets : il écrit dans des fichiers « _partiel ».
    global CSV_PATH, MD_PATH

    if wanted:
        CSV_PATH = BASE_DIR / "evaluation_agent_partiel.csv"
        MD_PATH = BASE_DIR / "resultats_evaluation_partiel.md"

    rows = []

    for model in models:
        print(f"\n=== {model} ===")

        for case in cases:
            row = run_case(model, case)
            rows.append(row)
            mark = "OK " if row["passed"] else "KO "
            print(f"{mark} #{case['id']:>2} {case['category']:<20} "
                  f"{row['duration_seconds']:>6.1f}s  {case['question'][:50]}")

    if rows and all(r["problems"].startswith("erreur technique")
                    for r in rows):
        print("\nAucune réponse : Ollama est-il lancé et les modèles "
              "téléchargés (ollama pull <modèle>) ?")
        return 1

    with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize(rows, models)
    MD_PATH.write_text(summary, encoding="utf-8")

    print("\n" + summary)
    print(f"\nFichiers écrits : {CSV_PATH.name}, {MD_PATH.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
