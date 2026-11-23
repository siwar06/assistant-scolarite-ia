"""Affiche les réponses des questions échouées d'un CSV d'évaluation.

    python tests/voir_echecs.py                                  # jeu inédit, qwen, exécution 1
    python tests/voir_echecs.py evaluation_inedit.csv 103,109
    python tests/voir_echecs.py evaluation_repetee.csv 27 llama

Écrit aussi echecs.txt (UTF-8) pour pouvoir le copier / l'envoyer.
Aucune dépendance (pas besoin de pandas).
"""

import csv
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

path = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DIR / "evaluation_inedit.csv"
ids = {int(x) for x in sys.argv[2].split(",")} if len(sys.argv) > 2 else {103, 109}
model = sys.argv[3] if len(sys.argv) > 3 else "qwen"

with open(path, newline="", encoding="utf-8-sig") as handle:
    rows = [r for r in csv.DictReader(handle)
            if int(r["id"]) in ids and model in r["model"] and r["run"] == "1"]

lines = []
for r in sorted(rows, key=lambda r: int(r["id"])):
    lines += [f"#{r['id']} [{r['category']}] passed={r['passed']}",
              f"Question : {r['question']}",
              f"Attendu  : {r['expected']}",
              f"Problème : {r['problems'] or '-'}",
              f"Réponse  : {r['answer']}", "-" * 70]

text = "\n".join(lines) or "Aucune ligne trouvée (vérifie le fichier, les numéros, le modèle)."
(BASE_DIR / "echecs.txt").write_text(text, encoding="utf-8")
print(text)
