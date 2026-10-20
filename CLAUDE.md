# CLAUDE.md — E03 Rapprochement des bons de livraison

## Objectif (timebox : 1 h)

Agent local qui lit les bons de livraison texte du jour, les rapproche des commandes d'achat (CSV),
écrit une **fiche d'écart JSON par livraison non conforme** et un **récapitulatif journalier**.
Projet volontairement minimal : pas d'API web, pas de base de données, pas d'UI.

## Stack

- Python 3.11+, stdlib uniquement sauf : `anthropic` (extraction) et `pytest` (tests)
- Modèle : `claude-haiku-4-5` via SDK Anthropic (clé dans `ANTHROPIC_API_KEY`)
- Principe clé : **le LLM extrait, le code compare.** Toute comparaison de quantités / références
  et tout calcul de date est déterministe en Python, jamais confié au modèle.

## Arborescence

```
e03/
├── CLAUDE.md
├── requirements.txt          # anthropic, pytest
├── data/
│   ├── bons/                 # 15 bons .txt (LECTURE SEULE)
│   └── commandes.csv         # LECTURE SEULE
├── output/                   # seul dossier en écriture (recréé à chaque run)
├── src/
│   ├── main.py               # point d'entrée : python -m src.main
│   ├── extract.py            # LLM : texte du bon -> dict structuré
│   ├── compare.py            # déterministe : bon + commande -> liste d'écarts
│   └── report.py             # écriture fiches + récap
└── tests/
    └── test_compare.py
```

## Données d'entrée

### `data/commandes.csv`
```
num_commande;reference;designation;qte_commandee;distributeur
CA-1001;REF-A12;Palette eau 6x1.5L;20;DistriNord
```

### `data/bons/*.txt` (15 fichiers fictifs à générer en premier)
Formats volontairement hétérogènes (3 transporteurs : tableau, liste « clé: valeur », texte libre).
Répartition à respecter pour couvrir tous les cas :

| Nb | Cas | Exemple |
|----|-----|---------|
| 8 | Conforme | quantités = commande |
| 2 | Quantité manquante | 18 reçus / 20 commandés |
| 1 | Référence erronée | REF-A13 au lieu de REF-A12 (ou réf. absente de la commande) |
| 1 | Colis abîmé | mention manuscrite « 2 cartons abîmés » |
| 1 | Faute de frappe tolérable | « Comande CA1001 », « qté » → doit rester **conforme** |
| 1 | Illisible / ambigu | quantité « 1? », n° commande manquant → **à vérifier** |
| 1 | Excédent | 22 reçus / 20 commandés |

Chaque bon contient : n° de commande, date + heure de réception, lignes (référence, quantité reçue), remarques éventuelles.

## Pipeline

1. **Lire** `commandes.csv` → `dict[num_commande] -> {reference: qte}`.
2. **Extraire** chaque bon via le LLM (`extract.py`) → JSON strict :
   ```json
   {"num_commande": "CA-1001", "date_reception": "2026-10-20T08:30",
    "lignes": [{"reference": "REF-A12", "qte_recue": 18}],
    "remarques": ["2 cartons abîmés"], "lisible": true, "doutes": []}
   ```
   - Prompt : « Extrais sans rien deviner. Si une valeur est illisible ou ambiguë, mets `lisible:false` et décris-la dans `doutes`. » Réponse JSON uniquement.
   - Normaliser ensuite en code : majuscules, trim, `CA1001` → `CA-1001`.
3. **Comparer** (`compare.py`, pur Python, testable sans LLM). Types d'écart :
   `QUANTITE_MANQUANTE`, `EXCEDENT`, `REFERENCE_ERRONEE`, `REFERENCE_MANQUANTE`, `COLIS_ABIME`, `A_VERIFIER`.
   - `lisible == false` ou commande introuvable → `A_VERIFIER`, aucune supposition.
   - Remarque contenant « abîm », « endommag », « cassé » → `COLIS_ABIME`.
4. **Date limite** = `date_reception + timedelta(hours=48)` (format ISO).
5. **Écrire** dans `output/` :
   - `fiche_<num_commande>.json` par livraison non conforme
   - `recap_<date>.md` : nb livraisons, nb conformes, tableau des écarts **trié par date limite croissante**

### Format d'une fiche
```json
{
  "num_commande": "CA-1001",
  "fichier_bon": "bon_03.txt",
  "statut": "NON_CONFORME",          // ou "A_VERIFIER"
  "date_reception": "2026-10-20T08:30",
  "date_limite_signalement": "2026-10-22T08:30",
  "ecarts": [
    {"reference": "REF-A12", "qte_attendue": 20, "qte_recue": 18, "nature": "QUANTITE_MANQUANTE"}
  ],
  "a_relire_par": "agent administratif"
}
```

## Contraintes (non négociables)

- **Écriture uniquement dans `output/`**. Ne jamais ouvrir `data/` en mode écriture.
  Vérifier dans `report.py` que tout chemin écrit est sous `output/` (`Path.resolve()`).
- Bon illisible / ambigu → fiche `A_VERIFIER`, jamais de valeur inventée.
- Lancement complet en **une seule commande** :
  ```bash
  python -m src.main            # options : --bons data/bons --commandes data/commandes.csv --out output
  ```

## Tests (limités, 5 max — `pytest -q`)

Tous sur `compare.py` + date, **sans appel LLM** (on passe des dicts déjà extraits) :

1. Livraison conforme → aucun écart.
2. Quantité manquante → `QUANTITE_MANQUANTE` avec qte attendue/reçue correctes.
3. Référence absente de la commande → `REFERENCE_ERRONEE`.
4. `lisible: false` → statut `A_VERIFIER`.
5. Date limite = réception + 48 h (ex. `2026-10-30T16:00` → `2026-11-01T16:00`, passage de mois).

## Plan d'exécution (60 min)

| Min | Tâche |
|-----|-------|
| 0–10 | Générer `commandes.csv` + 15 bons selon le tableau des cas |
| 10–25 | `compare.py` + date limite + les 5 tests (verts) |
| 25–40 | `extract.py` (prompt + parsing JSON + normalisation) |
| 40–50 | `report.py` + `main.py`, run complet |
| 50–60 | Vérifier le récap : 8 conformes, 7 fiches, 0 faux écart ; README court |

## Conventions pour Claude

- Code simple, fonctions courtes, type hints, pas de classes inutiles.
- Ne pas ajouter de dépendances, d'API web ni de features hors périmètre (extensions = hors scope).
- Toujours relancer `pytest -q` après modification de `compare.py`.
- En cas d'erreur d'extraction LLM (JSON invalide) : 1 retry, puis fiche `A_VERIFIER`.
- Utilise le clean code
- Simplifie au maximum les fonctionalité
- Ne lis jamais le .env, nis le modifié
- Maximum 10 tests par fonction
- Architecture simplifié

## Git
- Dépôt : https://github.com/Galgo-dev/agent_ia_commande.git — branche principale `main`.
- Si main 'inexistant', création first commit + rajout de la structure existante add origin 
- **Chaque nouvelle fonctionnalité se développe sur une nouvelle branche** (`feature/<nom-court>`,
  `docs/<nom>` pour la documentation), jamais directement sur `main`. Intégration par pull request.
- Messages de commit en français.
- Ne push jamais sans ma permission
- Ne supprime aucun commit

