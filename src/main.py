"""Point d'entrée : python -m src.main"""
import argparse
import os
from datetime import date
from pathlib import Path

import anthropic

from src.compare import charger_commandes, comparer, trouver
from src.extract import extraire_bon
from src.report import construire_fiche, ecrire_fiche, ecrire_recap, preparer_output


def charger_cle_api(fichier_env: Path = Path(".env")) -> None:
    """Utilise ANTHROPIC_API_KEY de l'environnement, sinon celle du .env (cette seule clé)."""
    if os.environ.get("ANTHROPIC_API_KEY") or not fichier_env.is_file():
        return
    for ligne in fichier_env.read_text(encoding="utf-8").splitlines():
        nom, _, valeur = ligne.partition("=")
        if nom.strip() == "ANTHROPIC_API_KEY":
            os.environ[nom.strip()] = valeur.strip().strip("\"'")


def traiter_bon(chemin: Path, commandes: dict, deja_livrees: set[str], client) -> dict:
    """Extrait, compare et renvoie la fiche de la livraison (conforme ou non)."""
    bon = extraire_bon(chemin.read_text(encoding="utf-8"), client)
    statut, ecarts = comparer(bon, commandes, deja_livrees)
    numero = trouver(bon["num_commande"], commandes) or bon["num_commande"]
    return construire_fiche(chemin.name, bon, numero, statut, ecarts)


def lire_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rapprochement des bons de livraison")
    parser.add_argument("--bons", default="ressource/BonCommande")
    parser.add_argument("--commandes", default="ressource/commandes_achat.csv")
    parser.add_argument("--out", default="output")
    return parser.parse_args()


def main() -> int:
    args = lire_arguments()
    charger_cle_api()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY introuvable (variable d'environnement ou .env).")
        return 1
    commandes = charger_commandes(args.commandes)
    client = anthropic.Anthropic()
    out = Path(args.out)
    preparer_output(out)
    deja_livrees: set[str] = set()
    fiches = []
    for chemin in sorted(Path(args.bons).glob("*.txt")):
        fiche = traiter_bon(chemin, commandes, deja_livrees, client)
        fiches.append(fiche)
        if fiche["statut"] != "CONFORME":
            ecrire_fiche(out, fiche)
        print(f"{chemin.name} : {fiche['statut']}")
    recap = ecrire_recap(out, date.today().isoformat(), fiches)
    conformes = sum(f["statut"] == "CONFORME" for f in fiches)
    print(f"{len(fiches)} livraisons, {conformes} conformes, {len(fiches) - conformes} fiches -> {recap}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
