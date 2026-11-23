"""Évaluation RÉPÉTÉE de l'agent : moyenne, écart-type, matrice de confusion.

Pourquoi répéter ? Le modèle génère du texte avec un peu d'aléatoire
(temperature 0.2) : une seule exécution peut être « chanceuse » ou
« malchanceuse ». On lance donc le jeu de 40 questions N fois par modèle,
puis on raisonne comme en Machine Learning : moyenne ± écart-type, intervalle
de confiance, matrice de confusion, précision / rappel / F1, comparaison de
deux modèles.

Usage (Ollama lancé, modèles téléchargés) :

    python tests/evaluer_repetee.py                 # 3 exécutions
    python tests/evaluer_repetee.py --runs 5
    python tests/evaluer_repetee.py --runs 3 --models qwen3:4b-instruct,llama3.2:3b
    python tests/evaluer_repetee.py --from-csv evaluation_repetee.csv   # recalcul sans relancer
    python tests/evaluer_repetee.py --jeu inedit --runs 3   # test set (15 questions jamais vues)

Compter ~15 min par exécution pour les 2 modèles (40 questions chacun).

Sorties (à la racine du projet) :
    evaluation_repetee.csv            une ligne par (exécution, modèle, question)
    resultats_evaluation_repetee.md   tableaux prêts à copier dans le rapport
    figure_evaluation.png             graphique (si matplotlib est installé)
"""

import argparse
import csv
import math
import re
import statistics
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "src"))

import tests.evaluer_agent as ev  # noqa: E402  (run_case : même chemin que l'UI)
from tests.jeu_de_test import CASES, REFUSAL, norm  # noqa: E402
from tests.jeu_de_test_inedit import CASES as CASES_INEDIT  # noqa: E402

CSV_PATH = BASE_DIR / "evaluation_repetee.csv"
MD_PATH = BASE_DIR / "resultats_evaluation_repetee.md"
FIG_PATH = BASE_DIR / "figure_evaluation.png"

# Matrice « refuser / répondre » : seules ces catégories y entrent.
#   positif = l'agent DOIT refuser ; négatif = l'agent DOIT répondre.
# Manipulation et Demande sont exclues : leur bon comportement (résister,
# préparer un brouillon) n'est pas forcément une formule de refus.
POS_CATS = {"Hors sujet", "Information absente"}
NEG_CATS = {"Factuelle", "Piège", "Multilingue"}

# Une question plus longue que ça = machine en veille ou modèle bloqué,
# pas une vraie réponse : écartée des temps moyens.
OUTLIER_S = 120

# Valeurs de la loi de Student (95 %, bilatéral) selon n-1 degrés de liberté.
T95 = {1: 12.71, 2: 4.30, 3: 3.18, 4: 2.78, 5: 2.57, 6: 2.45,
       7: 2.36, 8: 2.31, 9: 2.26}


# ------------------------------------------------------------------
# Outils statistiques (bibliothèque standard uniquement)
# ------------------------------------------------------------------

def mean_std(values):
    mean = statistics.mean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0.0
    return mean, std


def ci95(values):
    """Intervalle de confiance à 95 % de la moyenne (loi de Student)."""
    mean, std = mean_std(values)
    n = len(values)

    if n < 2:
        return mean, mean

    t = T95.get(n - 1, 2.0)
    half = t * std / math.sqrt(n)
    return mean - half, mean + half


def pct(x):
    return f"{100 * x:.1f} %"


# ------------------------------------------------------------------
# Refus de l'agent = problème de classification binaire
#   positif  = « l'agent DOIT refuser » (hors sujet, information absente)
#   prédit   = « l'agent a refusé »     (formule de refus dans la réponse)
# ------------------------------------------------------------------

def expected_refusal(case):
    return int(case["category"] in POS_CATS)


def predicted_refusal(answer):
    text = norm(answer)
    return int(any(re.search(p, text) for p in REFUSAL))


def confusion(rows):
    rows = [r for r in rows if r["category"] in POS_CATS | NEG_CATS]
    tp = sum(1 for r in rows if r["expected_refusal"] and r["predicted_refusal"])
    fn = sum(1 for r in rows if r["expected_refusal"] and not r["predicted_refusal"])
    fp = sum(1 for r in rows if not r["expected_refusal"] and r["predicted_refusal"])
    tn = sum(1 for r in rows if not r["expected_refusal"] and not r["predicted_refusal"])
    return tp, fn, fp, tn


def metrics(tp, fn, fp, tn):
    def div(a, b):
        return a / b if b else 0.0

    precision = div(tp, tp + fp)
    recall = div(tp, tp + fn)           # sensibilité
    return {
        "accuracy": div(tp + tn, tp + fn + fp + tn),
        "precision": precision,
        "recall": recall,
        "specificity": div(tn, tn + fp),
        "f1": div(2 * precision * recall, precision + recall),
    }


# ------------------------------------------------------------------
# Rapport
# ------------------------------------------------------------------

def summarize(rows, models, runs, held_out=False):
    by = defaultdict(list)
    for r in rows:
        by[(r["model"], r["run"])].append(r)

    rate = {m: [sum(x["passed"] for x in by[(m, k)]) / len(by[(m, k)])
                for k in range(1, runs + 1) if by[(m, k)]] for m in models}
    def normal_times(m):
        return [r["duration_seconds"] for r in rows
                if r["model"] == m and r["duration_seconds"] < OUTLIER_S]

    outliers = {m: [r for r in rows if r["model"] == m
                    and r["duration_seconds"] >= OUTLIER_S] for m in models}
    n_questions = len({r["id"] for r in rows})

    L = ["# Évaluation répétée de l'agent"
         + (" : jeu inédit (test set)" if held_out else ""), "",
         f"{n_questions} questions × {runs} exécution(s) × {len(models)} "
         "modèle(s). Chaque exécution rejoue tout le jeu de tests.", ""]

    # 1. Taux par exécution
    L += ["## 1. Taux de réussite par exécution", "",
          "| Exécution | " + " | ".join(models) + " |",
          "|---|" + "---|" * len(models)]
    for k in range(1, runs + 1):
        cells = []
        for m in models:
            rr = by[(m, k)]
            ok = sum(x["passed"] for x in rr)
            cells.append(f"{ok}/{len(rr)} ({pct(ok / len(rr))})" if rr else "-")
        L.append(f"| {k} | " + " | ".join(cells) + " |")

    # 2. Moyenne, écart-type, IC95
    L += ["", "## 2. Moyenne ± écart-type (taux de réussite)", "",
          "| Modèle | Moyenne | Écart-type | Min – Max | IC 95 % | Temps médian (s) |",
          "|---|---|---|---|---|---|"]
    for m in models:
        mean, std = mean_std(rate[m])
        lo, hi = ci95(rate[m])
        tmed = statistics.median(normal_times(m))
        L.append(f"| {m} | {pct(mean)} | {100 * std:.1f} pt | "
                 f"{pct(min(rate[m]))} – {pct(max(rate[m]))} | "
                 f"[{pct(max(lo, 0))} ; {pct(min(hi, 1))}] | "
                 f"{tmed:.1f} |")
    L += ["", f"*Avec n = {runs} exécutions, l'intervalle de confiance reste "
              "large : plus on répète, plus il se resserre.*"]
    slow = [f"{m} : {len(v)} question(s) à plus de {OUTLIER_S} s "
            f"({', '.join(f'#{r['id']} = {r['duration_seconds'] / 60:.0f} min' for r in v)})"
            for m, v in outliers.items() if v]
    if slow:
        L += ["", "*Temps : médiane (robuste), car des valeurs aberrantes "
                  "(machine en veille, modèle bloqué) faussent la moyenne. "
                  "Écartées : " + " ; ".join(slow) + ".*"]

    # 3. Par catégorie
    categories = list(OrderedDict.fromkeys(r["category"] for r in rows))
    L += ["", "## 3. Taux de réussite moyen par catégorie", "",
          "| Catégorie | " + " | ".join(models) + " |",
          "|---|" + "---|" * len(models)]
    for c in categories:
        cells = []
        for m in models:
            per_run = []
            for k in range(1, runs + 1):
                rr = [x for x in by[(m, k)] if x["category"] == c]
                if rr:
                    per_run.append(sum(x["passed"] for x in rr) / len(rr))
            mean, std = mean_std(per_run)
            cells.append(f"{pct(mean)} ± {100 * std:.0f}")
        L.append(f"| {c} | " + " | ".join(cells) + " |")

    # 4. Stabilité par question
    L += ["", "## 4. Questions instables (réussies une partie des exécutions)", ""]
    unstable = False
    for m in models:
        L.append(f"### {m}")
        L.append("")
        seen = False
        ids = sorted({r["id"] for r in rows})
        for qid in ids:
            rr = [r for r in rows if r["model"] == m and r["id"] == qid]
            ok = sum(r["passed"] for r in rr)
            if 0 < ok < len(rr):
                seen = unstable = True
                L.append(f"- **#{qid}** ({rr[0]['category']}) : réussie "
                         f"{ok}/{len(rr)} fois — {rr[0]['question'][:70]}")
        if not seen:
            L.append("Aucune : résultats identiques à chaque exécution.")
        L.append("")
    if unstable:
        L.append("*Une question instable montre une réponse qui dépend du "
                 "hasard de la génération, pas d'un défaut systématique.*")
        L.append("")

    always_fail = {m: [qid for qid in sorted({r['id'] for r in rows})
                       if all(not r['passed'] for r in rows
                              if r['model'] == m and r['id'] == qid)]
                   for m in models}
    L += ["### Échecs systématiques (jamais réussies)", ""]
    for m in models:
        ids = always_fail[m]
        L.append(f"- {m} : " + (", ".join(f"#{i}" for i in ids) if ids
                                else "aucune") + (f" ({len(ids)})" if ids else ""))

    # 5. Matrice de confusion
    cases_by_id = {c["id"]: c for c in CASES}
    L += ["", "## 5. Refuser ou répondre : matrice de confusion", "",
          "Classe positive = « l'agent doit refuser » (hors sujet, "
          "information absente). Classe négative = « l'agent doit "
          "répondre » (factuelles, pièges, multilingues). Prédiction = "
          "« la réponse contient une formule de refus ». Les manipulations "
          "et les demandes ne sont pas comptées ici. Cumul de toutes les "
          "exécutions.", ""]
    all_metrics = {}
    for m in models:
        rr = [r for r in rows if r["model"] == m]
        tp, fn, fp, tn = confusion(rr)
        mt = metrics(tp, fn, fp, tn)
        all_metrics[m] = (tp, fn, fp, tn, mt)
        L += [f"### {m}", "",
              "| | Refus prédit | Réponse prédite |", "|---|---|---|",
              f"| **Refus attendu** | VP = {tp} | FN = {fn} |",
              f"| **Réponse attendue** | FP = {fp} | VN = {tn} |", "",
              f"- Exactitude (accuracy) : {pct(mt['accuracy'])}",
              f"- Précision : {pct(mt['precision'])}",
              f"- Rappel (sensibilité) : {pct(mt['recall'])}",
              f"- Spécificité : {pct(mt['specificity'])}",
              f"- F1 : {pct(mt['f1'])}", ""]
    L += ["*FN = l'agent répond alors qu'il devait refuser (risque d'invention, "
          "le plus grave). FP = la réponse contient une formule de refus alors "
          "qu'une réponse était attendue ; souvent un refus partiel dans une "
          "réponse correcte (« ce n'est pas précisé »), pas une vraie erreur.*",
          ""]

    # 6. Comparaison des deux modèles
    if len(models) == 2 and runs >= 2:
        a, b = models
        diffs = [x - y for x, y in zip(rate[a], rate[b])]
        mean, _ = mean_std(diffs)
        lo, hi = ci95(diffs)
        verdict = ("la différence est significative (l'intervalle ne contient "
                   "pas 0)" if lo > 0 or hi < 0 else
                   "différence non concluante (l'intervalle contient 0)")
        L += ["## 6. Comparaison des deux modèles", "",
              f"Différence de taux ({a} − {b}), exécution par exécution : "
              f"moyenne {100 * mean:+.1f} pt, IC 95 % "
              f"[{100 * lo:+.1f} ; {100 * hi:+.1f}] pt → {verdict}.", ""]

    dev_line = (
        "- Jeu INÉDIT (test set) : ces questions n'ont jamais servi à "
        "corriger l'agent ; l'agent n'a pas été modifié après les avoir vues. "
        "Peu de questions : chaque question pèse plusieurs points de "
        "pourcentage." if held_out else
        "- Le jeu de 40 questions a servi à corriger l'agent : il n'est pas "
        "indépendant. Des questions inédites donneraient un taux plus bas.")
    L += ["## 7. Limites", "",
          "- Les critères sont des motifs textuels : une bonne réponse "
          "reformulée peut être comptée fausse (relecture humaine conseillée).",
          dev_line,
          "- Les réponses de date sont écrites par le programme : identiques "
          "pour les deux modèles et à chaque exécution."]
    return "\n".join(L), all_metrics, rate


def draw_figure(models, rate, all_metrics):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib absent : figure non générée (pip install matplotlib).")
        return False

    n = len(models)
    fig, axes = plt.subplots(1, 1 + n, figsize=(4.2 * (1 + n), 3.8))

    ax = axes[0]
    means = [100 * statistics.mean(rate[m]) for m in models]
    stds = [100 * (statistics.stdev(rate[m]) if len(rate[m]) > 1 else 0)
            for m in models]
    ax.bar(range(n), means, yerr=stds, capsize=6, color="#16A6A1", alpha=.85)
    for i, m in enumerate(models):
        ax.scatter([i] * len(rate[m]), [100 * v for v in rate[m]],
                   color="#1D3345", zorder=3, s=18)
    ax.set_xticks(range(n))
    ax.set_xticklabels(models, fontsize=8)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Taux de réussite (%)")
    ax.set_title("Moyenne ± écart-type\n(points = exécutions)", fontsize=10)

    for ax, m in zip(axes[1:], models):
        tp, fn, fp, tn, _ = all_metrics[m]
        grid = [[tp, fn], [fp, tn]]
        ax.imshow(grid, cmap="Blues")
        for i in range(2):
            for j in range(2):
                ax.text(j, i, grid[i][j], ha="center", va="center",
                        fontsize=14, color="black")
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Refus", "Réponse"])
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["Refus attendu", "Réponse attendue"])
        ax.set_xlabel("Prédit")
        ax.set_title(f"Matrice de confusion\n{m}", fontsize=10)

    fig.tight_layout()
    fig.savefig(FIG_PATH, dpi=160)
    return True


def write_csv(rows):
    with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def from_csv(path, held_out=False):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    for r in rows:
        r["id"] = int(r["id"])
        r["run"] = int(r["run"])
        r["passed"] = int(r["passed"])
        r["duration_seconds"] = float(r["duration_seconds"])
        r["expected_refusal"] = int(r["category"] in POS_CATS)
        r["predicted_refusal"] = predicted_refusal(r["answer"])

    models = list(OrderedDict.fromkeys(r["model"] for r in rows))
    runs = max(r["run"] for r in rows)
    summary, all_metrics, rate = summarize(rows, models, runs, held_out)
    MD_PATH.write_text(summary, encoding="utf-8")
    draw_figure(models, rate, all_metrics)
    print(summary)
    print(f"\nFichiers écrits : {MD_PATH.name}, {FIG_PATH.name}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--runs", type=int, default=3,
                        help="nombre d'exécutions complètes (3 à 5)")
    parser.add_argument("--models", default=",".join(ev.DEFAULT_MODELS))
    parser.add_argument("--jeu", choices=["dev", "inedit"], default="dev",
                        help="dev = 40 questions ; inedit = 15 questions "
                             "jamais vues (test set)")
    parser.add_argument("--from-csv", default="",
                        help="recalcule le rapport depuis un CSV existant, "
                             "sans relancer les modèles")
    parser.add_argument("--ids", default="",
                        help="numéros de questions (essai rapide), ex. 1,2,24")
    args = parser.parse_args(argv)
    held_out = args.jeu == "inedit"

    global CSV_PATH, MD_PATH, FIG_PATH
    if held_out:
        CSV_PATH = BASE_DIR / "evaluation_inedit.csv"
        MD_PATH = BASE_DIR / "resultats_evaluation_inedit.md"
        FIG_PATH = BASE_DIR / "figure_evaluation_inedit.png"

    if args.from_csv:
        return from_csv(Path(args.from_csv), held_out)

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    wanted = {int(i) for i in args.ids.split(",") if i.strip()}
    pool = CASES_INEDIT if held_out else CASES
    cases = [c for c in pool if not wanted or c["id"] in wanted]
    runs = max(1, args.runs)

    rows = []

    for run in range(1, runs + 1):
        for model in models:
            print(f"\n=== Exécution {run}/{runs} · {model} ===")

            for case in cases:
                row = ev.run_case(model, case)
                row["run"] = run
                row["expected_refusal"] = expected_refusal(case)
                row["predicted_refusal"] = predicted_refusal(row["answer"])
                rows.append(row)
                mark = "OK " if row["passed"] else "KO "
                print(f"{mark} #{case['id']:>2} {case['category']:<20} "
                      f"{row['duration_seconds']:>6.1f}s")

            # Sauvegarde après chaque série : rien n'est perdu si on arrête.
            write_csv(rows)

            if all(r["problems"].startswith("erreur technique")
                   for r in rows):
                print("\nAucune réponse : Ollama est-il lancé et les modèles "
                      "téléchargés (ollama pull <modèle>) ?")
                return 1

    summary, all_metrics, rate = summarize(rows, models, runs, held_out)
    MD_PATH.write_text(summary, encoding="utf-8")
    drew = draw_figure(models, rate, all_metrics)

    print("\n" + summary)
    print(f"\nFichiers écrits : {CSV_PATH.name}, {MD_PATH.name}"
          + (f", {FIG_PATH.name}" if drew else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
