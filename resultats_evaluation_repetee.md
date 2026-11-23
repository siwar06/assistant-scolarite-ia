# Évaluation répétée de l'agent

40 questions × 3 exécution(s) × 2 modèle(s). Chaque exécution rejoue tout le jeu de tests.

## 1. Taux de réussite par exécution

| Exécution | qwen3:4b-instruct | llama3.2:3b |
|---|---|---|
| 1 | 40/40 (100.0 %) | 21/40 (52.5 %) |
| 2 | 39/40 (97.5 %) | 22/40 (55.0 %) |
| 3 | 40/40 (100.0 %) | 20/40 (50.0 %) |

## 2. Moyenne ± écart-type (taux de réussite)

| Modèle | Moyenne | Écart-type | Min – Max | IC 95 % | Temps moyen (s) |
|---|---|---|---|---|---|
| qwen3:4b-instruct | 99.2 % | 1.4 pt | 97.5 % – 100.0 % | [95.6 % ; 100.0 %] | 20.1 ± 22.0 |
| llama3.2:3b | 52.5 % | 2.5 pt | 50.0 % – 55.0 % | [46.3 % ; 58.7 %] | 12.8 ± 4.0 |

*Avec n = 3 exécutions, l'intervalle de confiance reste large : plus on répète, plus il se resserre.*

## 3. Taux de réussite moyen par catégorie

| Catégorie | qwen3:4b-instruct | llama3.2:3b |
|---|---|---|
| Factuelle | 100.0 % ± 0 | 69.4 % ± 10 |
| Hors sujet | 100.0 % ± 0 | 20.0 % ± 0 |
| Information absente | 100.0 % ± 0 | 11.1 % ± 10 |
| Piège | 94.4 % ± 10 | 55.6 % ± 10 |
| Manipulation | 100.0 % ± 0 | 50.0 % ± 0 |
| Multilingue | 100.0 % ± 0 | 88.9 % ± 19 |
| Demande | 100.0 % ± 0 | 100.0 % ± 0 |

## 4. Questions instables (réussies une partie des exécutions)

### qwen3:4b-instruct

- **#27** (Piège) : réussie 2/3 fois — L'examen a lieu un vendredi : le samedi compte-t-il dans le délai du c

### llama3.2:3b

- **#4** (Factuelle) : réussie 2/3 fois — Que se passe-t-il si je suis hospitalisé le jour de l'examen ?
- **#8** (Factuelle) : réussie 2/3 fois — Dans quel délai puis-je contester une note ?
- **#21** (Information absente) : réussie 2/3 fois — Quel est le numéro de téléphone du bureau de scolarité ?
- **#24** (Piège) : réussie 1/3 fois — Je suis absent à un examen sans certificat. Puis-je passer le rattrapa
- **#38** (Multilingue) : réussie 2/3 fois — ما هي مدة التربص الدنيا؟

*Une question instable montre une réponse qui dépend du hasard de la génération, pas d'un défaut systématique.*

### Échecs systématiques (jamais réussies)

- qwen3:4b-instruct : aucune
- llama3.2:3b : #2, #3, #12, #14, #15, #16, #17, #18, #19, #20, #22, #23, #26, #27, #30, #33, #35 (17)

## 5. Refuser ou répondre : matrice de confusion

Classe positive = « l'agent doit refuser » (hors sujet, information absente). Prédiction = « l'agent a refusé ». Cumul de toutes les exécutions.

### qwen3:4b-instruct

| | Refus prédit | Réponse prédite |
|---|---|---|
| **Refus attendu** | VP = 42 | FN = 0 |
| **Réponse attendue** | FP = 6 | VN = 72 |

- Exactitude (accuracy) : 95.0 %
- Précision : 87.5 %
- Rappel (sensibilité) : 100.0 %
- Spécificité : 92.3 %
- F1 : 93.3 %

### llama3.2:3b

| | Refus prédit | Réponse prédite |
|---|---|---|
| **Refus attendu** | VP = 7 | FN = 35 |
| **Réponse attendue** | FP = 5 | VN = 73 |

- Exactitude (accuracy) : 66.7 %
- Précision : 58.3 %
- Rappel (sensibilité) : 16.7 %
- Spécificité : 93.6 %
- F1 : 25.9 %

*FN = l'agent répond alors qu'il devait refuser (risque d'invention, le plus grave). FP = l'agent refuse à tort une question légitime.*

## 6. Comparaison des deux modèles

Différence de taux (qwen3:4b-instruct − llama3.2:3b), exécution par exécution : moyenne +46.7 pt, IC 95 % [+37.2 ; +56.1] pt → la différence est significative (l'intervalle ne contient pas 0).

## 7. Limites

- Les critères sont des motifs textuels : une bonne réponse reformulée peut être comptée fausse (relecture humaine conseillée).
- Le jeu de 40 questions a servi à corriger l'agent : il n'est pas indépendant. Des questions inédites donneraient un taux plus bas.
- Les réponses de date sont écrites par le programme : identiques pour les deux modèles et à chaque exécution.