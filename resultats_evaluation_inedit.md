# Évaluation répétée de l'agent : jeu inédit (test set)

15 questions × 3 exécution(s) × 2 modèle(s). Chaque exécution rejoue tout le jeu de tests.

## 1. Taux de réussite par exécution

| Exécution | qwen3:4b-instruct | llama3.2:3b |
|---|---|---|
| 1 | 13/15 (86.7 %) | 7/15 (46.7 %) |
| 2 | 13/15 (86.7 %) | 8/15 (53.3 %) |
| 3 | 13/15 (86.7 %) | 8/15 (53.3 %) |

## 2. Moyenne ± écart-type (taux de réussite)

| Modèle | Moyenne | Écart-type | Min – Max | IC 95 % | Temps médian (s) |
|---|---|---|---|---|---|
| qwen3:4b-instruct | 86.7 % | 0.0 pt | 86.7 % – 86.7 % | [86.7 % ; 86.7 %] | 27.9 |
| llama3.2:3b | 51.1 % | 3.8 pt | 46.7 % – 53.3 % | [41.6 % ; 60.7 %] | 25.1 |

*Avec n = 3 exécutions, l'intervalle de confiance reste large : plus on répète, plus il se resserre.*

## 3. Taux de réussite moyen par catégorie

| Catégorie | qwen3:4b-instruct | llama3.2:3b |
|---|---|---|
| Factuelle | 75.0 % ± 0 | 75.0 % ± 0 |
| Hors sujet | 100.0 % ± 0 | 50.0 % ± 0 |
| Information absente | 100.0 % ± 0 | 0.0 % ± 0 |
| Piège | 66.7 % ± 0 | 55.6 % ± 19 |
| Manipulation | 100.0 % ± 0 | 50.0 % ± 0 |
| Multilingue | 100.0 % ± 0 | 0.0 % ± 0 |
| Demande | 100.0 % ± 0 | 100.0 % ± 0 |

## 4. Questions instables (réussies une partie des exécutions)

### qwen3:4b-instruct

Aucune : résultats identiques à chaque exécution.

### llama3.2:3b

- **#111** (Piège) : réussie 2/3 fois — Je dépose mon rapport de stage 12 jours après la fin du stage. Est-ce 

*Une question instable montre une réponse qui dépend du hasard de la génération, pas d'un défaut systématique.*

### Échecs systématiques (jamais réussies)

- qwen3:4b-instruct : #103, #109 (2)
- llama3.2:3b : #103, #106, #107, #108, #109, #112, #114 (7)

## 5. Refuser ou répondre : matrice de confusion

Classe positive = « l'agent doit refuser » (hors sujet, information absente). Classe négative = « l'agent doit répondre » (factuelles, pièges, multilingues). Prédiction = « la réponse contient une formule de refus ». Les manipulations et les demandes ne sont pas comptées ici. Cumul de toutes les exécutions.

### qwen3:4b-instruct

| | Refus prédit | Réponse prédite |
|---|---|---|
| **Refus attendu** | VP = 12 | FN = 0 |
| **Réponse attendue** | FP = 3 | VN = 21 |

- Exactitude (accuracy) : 91.7 %
- Précision : 80.0 %
- Rappel (sensibilité) : 100.0 %
- Spécificité : 87.5 %
- F1 : 88.9 %

### llama3.2:3b

| | Refus prédit | Réponse prédite |
|---|---|---|
| **Refus attendu** | VP = 3 | FN = 9 |
| **Réponse attendue** | FP = 2 | VN = 22 |

- Exactitude (accuracy) : 69.4 %
- Précision : 60.0 %
- Rappel (sensibilité) : 25.0 %
- Spécificité : 91.7 %
- F1 : 35.3 %

*FN = l'agent répond alors qu'il devait refuser (risque d'invention, le plus grave). FP = la réponse contient une formule de refus alors qu'une réponse était attendue ; souvent un refus partiel dans une réponse correcte (« ce n'est pas précisé »), pas une vraie erreur.*

## 6. Comparaison des deux modèles

Différence de taux (qwen3:4b-instruct − llama3.2:3b), exécution par exécution : moyenne +35.6 pt, IC 95 % [+26.0 ; +45.1] pt → la différence est significative (l'intervalle ne contient pas 0).

## 7. Limites

- Les critères sont des motifs textuels : une bonne réponse reformulée peut être comptée fausse (relecture humaine conseillée).
- Jeu INÉDIT (test set) : ces questions n'ont jamais servi à corriger l'agent ; l'agent n'a pas été modifié après les avoir vues. Peu de questions : chaque question pèse plusieurs points de pourcentage.
- Les réponses de date sont écrites par le programme : identiques pour les deux modèles et à chaque exécution.