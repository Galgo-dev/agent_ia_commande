"""Écriture des fiches d'écart et du récapitulatif, uniquement sous `output/`."""
import json
import shutil
from pathlib import Path

from src.compare import date_limite, date_valide

NOM_SORTIE = "output"
RELECTEUR = "agent administratif"


def _racine_output(out_dir: Path) -> Path:
    racine = out_dir.resolve()
    if racine.name != NOM_SORTIE:
        raise ValueError(f"Le dossier de sortie doit s'appeler '{NOM_SORTIE}' : {racine}")
    return racine


def _verifier_sous_output(chemin: Path, out_dir: Path) -> Path:
    resolu = chemin.resolve()
    if not resolu.is_relative_to(_racine_output(out_dir)):
        raise ValueError(f"Écriture refusée hors de '{NOM_SORTIE}' : {resolu}")
    return resolu


def _ecrire(chemin: Path, contenu: str, out_dir: Path) -> Path:
    cible = _verifier_sous_output(chemin, out_dir)
    cible.write_text(contenu, encoding="utf-8")
    return cible


def preparer_output(out_dir: Path) -> None:
    """Recrée le dossier de sortie vide."""
    racine = _racine_output(out_dir)
    if racine.exists():
        shutil.rmtree(racine)
    racine.mkdir(parents=True)


def construire_fiche(nom_bon: str, bon: dict, numero: str | None, statut: str, ecarts: list[dict]) -> dict:
    """Assemble la fiche d'une livraison (format du CLAUDE.md)."""
    reception = bon.get("date_reception")
    valide = date_valide(reception)
    return {
        "num_commande": numero,
        "fichier_bon": nom_bon,
        "statut": statut,
        "date_reception": reception if valide else None,
        "date_limite_signalement": date_limite(reception) if valide else None,
        "ecarts": ecarts,
        "a_relire_par": RELECTEUR,
    }


def ecrire_fiche(out_dir: Path, fiche: dict) -> Path:
    """Écrit `fiche_<commande>.json` ; le nom du bon est ajouté si le nom est inconnu ou déjà pris."""
    numero = fiche["num_commande"] or "INCONNU"
    chemin = out_dir / f"fiche_{numero}.json"
    if numero == "INCONNU" or chemin.exists():
        chemin = out_dir / f"fiche_{numero}_{Path(fiche['fichier_bon']).stem}.json"
    return _ecrire(chemin, json.dumps(fiche, ensure_ascii=False, indent=2), out_dir)


def _lignes_ecarts(fiches: list[dict]) -> list[str]:
    triees = sorted(fiches, key=lambda f: (f["date_limite_signalement"] is None, f["date_limite_signalement"] or ""))
    lignes = []
    for fiche in triees:
        for e in fiche["ecarts"]:
            valeurs = [fiche["date_limite_signalement"] or "inconnue", fiche["num_commande"] or "inconnue",
                       fiche["fichier_bon"], fiche["statut"], e["nature"], e["reference"] or "-",
                       e["qte_attendue"], e["qte_recue"], e.get("detail") or ""]
            lignes.append("| " + " | ".join("-" if v is None else str(v) for v in valeurs) + " |")
    return lignes


def ecrire_recap(out_dir: Path, date: str, resultats: list[dict]) -> Path:
    """Écrit `recap_<date>.md` : totaux puis écarts triés par date limite croissante.

    `resultats` contient une fiche (dict) par livraison, conformes comprises.
    """
    non_conformes = [r for r in resultats if r["statut"] != "CONFORME"]
    contenu = [
        f"# Récapitulatif des livraisons du {date}", "",
        f"- Livraisons : {len(resultats)}",
        f"- Conformes : {len(resultats) - len(non_conformes)}",
        f"- Fiches d'écart : {len(non_conformes)}", "",
        "| Date limite | Commande | Bon | Statut | Nature | Référence | Attendu | Reçu | Détail |",
        "|---|---|---|---|---|---|---|---|---|",
        *_lignes_ecarts(non_conformes),
    ]
    return _ecrire(out_dir / f"recap_{date}.md", "\n".join(contenu) + "\n", out_dir)
