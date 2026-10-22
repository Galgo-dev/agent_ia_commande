# Fiche de configuration — installation du projet sur une autre machine

Fiche destinée à **Claude Code** (et à son utilisateur) pour installer et lancer le projet
*E03 — Rapprochement des bons de livraison* depuis le dépôt GitHub.
Lis d'abord `CLAUDE.md` à la racine : il fait foi pour les règles du projet.

## 1. Contexte en trois lignes

- Agent Python local : le LLM (`claude-haiku-4-5`) **extrait** les bons de livraison texte,
  le code Python **compare** avec les commandes d'achat (CSV) et écrit des fiches d'écart dans `output/`.
- Stdlib uniquement, plus `anthropic` (extraction) et `pytest` (tests). Pas d'API web, pas de BDD, pas d'UI.
- Les données d'entrée sont fournies dans `ressource/` et sont en **lecture seule**.

## 2. Prérequis sur la machine

| Outil | Version | Vérification |
|-------|---------|--------------|
| Python | 3.11 ou plus | `python --version` |
| Git | récent | `git --version` |
| Clé API Anthropic | valide | fournie par l'utilisateur, jamais dans le dépôt |

## 3. Installation pas à pas

### 3.1 Cloner le dépôt

```bash
git clone https://github.com/Galgo-dev/agent_ia_commande.git
cd agent_ia_commande
```

> La branche `main` contient le projet complet (code, tests, README, données) : rester dessus.

### 3.2 Créer l'environnement virtuel et installer les dépendances

Windows (PowerShell) :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS / Linux :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3.3 Fournir la clé API

Le programme lit `ANTHROPIC_API_KEY` dans l'environnement, sinon dans un fichier `.env` à la racine
(une seule ligne). Ce fichier est ignoré par Git.

```
ANTHROPIC_API_KEY=sk-ant-...
```

Règles pour Claude Code :
- **c'est l'utilisateur qui crée ce fichier et y colle sa clé**, pas Claude ;
- ne jamais lire, afficher ni modifier `.env` ;
- ne jamais committer une clé.

### 3.4 Vérifier avec les tests (aucun appel LLM, aucune clé nécessaire)

```bash
python -m pytest -q
```

Résultat attendu : **9 tests verts**.

### 3.5 Lancer l'agent (appelle le LLM)

```bash
python -m src.main
```

Options : `--bons ressource/BonCommande --commandes ressource/commandes_achat.csv --out output`.

Résultat attendu sur les 15 bons fournis : **15 livraisons, 7 conformes, 8 fiches** dans `output/`
(`fiche_<num_commande>.json` par livraison non conforme + `recap_<date>.md`).
La table de vérité complète est dans le README.

## 4. Règles à respecter (résumé de CLAUDE.md)

- **Le LLM extrait, le code compare** : toute comparaison et tout calcul de date restent en Python.
- Écriture **uniquement dans `output/`** ; `ressource/` n'est jamais modifié ni complété (15 bons, pas un de plus).
- Bon illisible ou ambigu → fiche `A_VERIFIER`, jamais de valeur inventée.
- Pas de nouvelle dépendance, pas d'API web, pas de feature hors périmètre.
- Code simple : fonctions courtes, type hints, pas de classes inutiles. Maximum 10 tests par fonction.
- Relancer `pytest -q` après toute modification de `compare.py`.

## 5. Conventions Git

- Ne jamais travailler directement sur `main`.
- Une branche par fonctionnalité : `feature/<nom-court>`, `docs/<nom>` pour la documentation.
- Intégration par pull request vers `main`.
- Messages de commit **en français**.
- **Ne jamais pousser (`git push`) sans l'accord explicite de l'utilisateur.**
- Ne supprimer aucun commit.

Pour démarrer une nouvelle fonctionnalité :

```bash
git checkout -b feature/<nom-court>
```

## 6. Dépannage rapide

| Symptôme | Cause probable | Solution |
|----------|----------------|----------|
| `ModuleNotFoundError: anthropic` | venv non activé ou dépendances non installées | activer `.venv`, relancer `pip install -r requirements.txt` |
| Erreur d'authentification Anthropic | clé absente ou invalide | vérifier `.env` ou la variable `ANTHROPIC_API_KEY` |
| `python -m src.main` lancé depuis un autre dossier | chemins relatifs | se placer à la racine du dépôt |
| Tests introuvables | mauvaise branche | `git checkout main` |
| `Activate.ps1` refusé par PowerShell | politique d'exécution | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` puis réessayer |

## 7. Checklist de fin d'installation

- [ ] dépôt cloné, sur la branche `main`
- [ ] `.venv` activé, `pip install -r requirements.txt` sans erreur
- [ ] `.env` créé par l'utilisateur avec `ANTHROPIC_API_KEY`
- [ ] `python -m pytest -q` : 9 tests verts
- [ ] `python -m src.main` : 7 conformes, 8 fiches dans `output/`
