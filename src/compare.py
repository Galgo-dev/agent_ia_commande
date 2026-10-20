"""Comparaison déterministe d'un bon de livraison avec la commande d'achat."""
import csv
import re
from collections.abc import Iterable
from datetime import datetime, timedelta
from pathlib import Path

Commandes = dict[str, dict[str, int]]

MOTS_ABIME = ("abîm", "endommag", "cassé")
HEURES_LIMITE = 48


def cle(valeur: str) -> str:
    """Clé de comparaison : majuscules, lettres et chiffres uniquement."""
    return re.sub(r"[^A-Z0-9]", "", valeur.upper())


def trouver(valeur: str | None, officiels: Iterable[str]) -> str | None:
    """Renvoie la forme officielle (celle du CSV) qui correspond à `valeur`."""
    if not valeur:
        return None
    return next((o for o in officiels if cle(o) == cle(valeur)), None)


def charger_commandes(chemin: Path | str) -> Commandes:
    """Lit le CSV (lecture seule) : {numero_commande: {reference: quantite}}."""
    commandes: Commandes = {}
    with open(chemin, encoding="utf-8", newline="") as f:
        for ligne in csv.DictReader(f):
            lignes = commandes.setdefault(ligne["numero_commande"], {})
            lignes[ligne["reference"]] = int(ligne["quantite_commandee"])
    return commandes


def date_valide(valeur: object) -> bool:
    try:
        datetime.fromisoformat(valeur)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return True


def date_limite(date_reception: str) -> str:
    """Date de réception + 48 h, au format ISO `YYYY-MM-DDTHH:MM`."""
    limite = datetime.fromisoformat(date_reception) + timedelta(hours=HEURES_LIMITE)
    return limite.strftime("%Y-%m-%dT%H:%M")


def _ecart(nature: str, reference: str | None = None, attendue: int | None = None,
           recue: int | None = None, detail: str | None = None) -> dict:
    ecart = {"reference": reference, "qte_attendue": attendue, "qte_recue": recue, "nature": nature}
    if detail:
        ecart["detail"] = detail
    return ecart


def _doutes(bon: dict, commandes: Commandes) -> list[str]:
    """Raisons pour lesquelles le bon ne peut pas être comparé sans deviner."""
    doutes = []
    if not bon.get("lisible", False):
        doutes.append("bon illisible ou ambigu")
        doutes.extend(bon.get("doutes") or [])
    if trouver(bon.get("num_commande"), commandes) is None:
        doutes.append(f"commande introuvable : {bon.get('num_commande')!r}")
    if not date_valide(bon.get("date_reception")):
        doutes.append("date de réception absente ou invalide")
    quantites = [ligne.get("qte_recue") for ligne in bon.get("lignes") or []]
    if not all(isinstance(q, int) and not isinstance(q, bool) for q in quantites):
        doutes.append("quantité reçue absente ou illisible")
    return doutes


def _ecarts_lignes(lignes: list[dict], attendu: dict[str, int]) -> list[dict]:
    recues: dict[str, int] = {}
    for ligne in lignes:
        reference = trouver(ligne["reference"], attendu) or ligne["reference"]
        recues[reference] = recues.get(reference, 0) + ligne["qte_recue"]
    ecarts = []
    for reference, recue in recues.items():
        if reference not in attendu:
            ecarts.append(_ecart("REFERENCE_ERRONEE", reference, None, recue))
        elif recue < attendu[reference]:
            ecarts.append(_ecart("QUANTITE_MANQUANTE", reference, attendu[reference], recue))
        elif recue > attendu[reference]:
            ecarts.append(_ecart("EXCEDENT", reference, attendu[reference], recue))
    for reference, quantite in attendu.items():
        if reference not in recues:
            ecarts.append(_ecart("REFERENCE_MANQUANTE", reference, quantite, 0))
    return ecarts


def _ecarts_remarques(remarques: list[str]) -> list[dict]:
    abime = any(mot in r.lower() for r in remarques for mot in MOTS_ABIME)
    return [_ecart("COLIS_ABIME", detail="; ".join(remarques))] if abime else []


def comparer(bon: dict, commandes: Commandes, deja_livrees: set[str]) -> tuple[str, list[dict]]:
    """Renvoie (statut, écarts). `deja_livrees` est mis à jour avec la commande traitée.

    Statuts : CONFORME, NON_CONFORME ou A_VERIFIER (aucune supposition si doute).
    """
    doutes = _doutes(bon, commandes)
    if doutes:
        return "A_VERIFIER", [_ecart("A_VERIFIER", detail="; ".join(doutes))]
    numero = trouver(bon["num_commande"], commandes)
    ecarts = []
    if numero in deja_livrees:
        ecarts.append(_ecart("LIVRAISON_EN_DOUBLE", detail=f"{numero} déjà livrée"))
    deja_livrees.add(numero)
    ecarts += _ecarts_lignes(bon.get("lignes") or [], commandes[numero])
    ecarts += _ecarts_remarques(bon.get("remarques") or [])
    return ("NON_CONFORME" if ecarts else "CONFORME"), ecarts
