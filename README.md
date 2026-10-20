# E03 — Rapprochement des bons de livraison

Agent local : le LLM (`claude-haiku-4-5`) **extrait** les bons de livraison texte,
le code Python **compare** avec les commandes d'achat et écrit les fiches d'écart.

## Lancement

```bash
pip install -r requirements.txt
python -m src.main     # options : --bons ressource/BonCommande --commandes ressource/commandes_achat.csv --out output
python -m pytest -q    # tests (sans appel LLM)
```

La clé se lit dans `ANTHROPIC_API_KEY` (variable d'environnement, ou fichier `.env` non versionné).

## Structure

| Chemin | Rôle |
|--------|------|
| `ressource/` | données fournies, **lecture seule** (15 bons + CSV des commandes) |
| `src/extract.py` | LLM : texte du bon → dict structuré |
| `src/compare.py` | déterministe : bon + commande → écarts, date limite (+48 h) |
| `src/report.py` | écriture des fiches et du récap, uniquement dans `output/` |
| `src/main.py` | point d'entrée |
| `tests/test_compare.py` | tests de `compare.py` |
| `output/` | fiches `fiche_<commande>.json` et `recap_<date>.md` (recréé à chaque run) |

## Résultat attendu (table de vérité)

15 livraisons : **7 conformes, 8 fiches**.

| Bon | Résultat attendu |
|-----|------------------|
| 0401, 0403, 0409, 0411, 0413, 0414 | conforme |
| 0402 | conforme malgré « CMD 2026 0402 » et « REF 4417 B » |
| 0404 | `EXCEDENT` (26 / 20) |
| 0405 | `QUANTITE_MANQUANTE` (36 / 40) |
| 0406 | `REFERENCE_ERRONEE` (REF-5502B) + `REFERENCE_MANQUANTE` (REF-5520B) |
| 0407 | `QUANTITE_MANQUANTE` (15 / 18) |
| 0408 | `COLIS_ABIME` |
| 0410 | `QUANTITE_MANQUANTE` (5 / 8) |
| 0412 | `A_VERIFIER` (quantité « 3? ») |
| 0415 | `LIVRAISON_EN_DOUBLE` (commande 0414 déjà livrée par le bon 0414) |

## Fonctionnement

1. `main.py` lit les commandes puis chaque bon (ordre alphabétique des fichiers).
2. `extract.py` demande au modèle un JSON (commande, date, lignes, remarques, `lisible`, `doutes`).
   JSON invalide : 1 retry, puis le bon est traité comme illisible.
3. `compare.py` compare en Python pur. Un bon illisible, sans commande connue ou sans date valide
   donne `A_VERIFIER` : aucune valeur n'est jamais inventée.
4. `report.py` écrit une fiche par livraison non conforme et le récapitulatif, dont les écarts sont triés
   par date limite (réception + 48 h).

Garde-fou : seul un dossier nommé `output` est écrit (et recréé à chaque run), `ressource/` n'est jamais modifié.

## Tests

`tests/test_compare.py` : 9 tests, sans appel LLM, sur le CSV fourni et des bons déjà extraits
(conforme, quantité manquante, référence erronée, illisible, date limite, excédent, colis abîmé,
fautes de frappe, livraison en double).

## Dernier run

`python -m src.main` sur les 15 bons : 15 livraisons, **7 conformes, 8 fiches**, conforme à la table ci-dessus.
