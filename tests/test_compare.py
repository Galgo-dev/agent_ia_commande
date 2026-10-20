"""Tests de compare.py sur les données fournies (CSV réel, bons déjà extraits, sans LLM)."""
from pathlib import Path

from src.compare import charger_commandes, comparer, date_limite

COMMANDES = charger_commandes(Path(__file__).parent.parent / "ressource" / "commandes_achat.csv")


def bon(num: str | None, reception: str, lignes: list[tuple[str, int | None]],
        remarques: list[str] | None = None, lisible: bool = True) -> dict:
    return {"num_commande": num, "date_reception": reception,
            "lignes": [{"reference": r, "qte_recue": q} for r, q in lignes],
            "remarques": remarques or [], "lisible": lisible, "doutes": []}


def natures(ecarts: list[dict]) -> list[str]:
    return [e["nature"] for e in ecarts]


def test_livraison_conforme():  # BL-2026-0401
    resultat = comparer(bon("CMD-2026-0401", "2026-10-10T08:30", [("REF-2201A", 40)]), COMMANDES, set())
    assert resultat == ("CONFORME", [])


def test_quantite_manquante():  # BL-2026-0405 : 36 reçus / 40 commandés
    statut, ecarts = comparer(bon("CMD-2026-0405", "2026-10-12T09:15", [("REF-2215A", 36)]), COMMANDES, set())
    assert statut == "NON_CONFORME"
    assert ecarts == [{"reference": "REF-2215A", "qte_attendue": 40, "qte_recue": 36, "nature": "QUANTITE_MANQUANTE"}]


def test_reference_absente_de_la_commande():  # BL-2026-0406 : REF-5502B au lieu de REF-5520B
    _, ecarts = comparer(bon("CMD-2026-0406", "2026-10-10T17:30", [("REF-5502B", 12)]), COMMANDES, set())
    assert natures(ecarts) == ["REFERENCE_ERRONEE", "REFERENCE_MANQUANTE"]


def test_bon_illisible_est_a_verifier():  # BL-2026-0412 : quantité « 3? »
    illisible = bon("CMD-2026-0412", "2026-10-13T07:55", [("REF-1215D", None), ("REF-1216D", 24)], lisible=False)
    statut, ecarts = comparer(illisible, COMMANDES, set())
    assert statut == "A_VERIFIER"
    assert natures(ecarts) == ["A_VERIFIER"]


def test_date_limite_passage_de_mois():
    assert date_limite("2026-10-30T16:00") == "2026-11-01T16:00"


def test_excedent():  # BL-2026-0404 : 26 reçus / 20 commandés
    _, ecarts = comparer(bon("CMD-2026-0404", "2026-10-10T14:20", [("REF-1180D", 26)]), COMMANDES, set())
    assert natures(ecarts) == ["EXCEDENT"]


def test_colis_abime():  # BL-2026-0408
    abime = bon("CMD-2026-0408", "2026-10-12T10:05", [("REF-1190D", 12)], ["Mention manuscrite : « 2 cartons abîmés »"])
    statut, ecarts = comparer(abime, COMMANDES, set())
    assert (statut, natures(ecarts)) == ("NON_CONFORME", ["COLIS_ABIME"])


def test_fautes_de_frappe_restent_conformes():  # BL-2026-0402 : « CMD 2026 0402 », « REF 4417 B »
    typos = bon("CMD 2026 0402", "2026-10-10T11:20", [("REF 4417 B", 12), ("REF-4420B", 24)])
    assert comparer(typos, COMMANDES, set()) == ("CONFORME", [])


def test_commande_livree_deux_fois():  # BL-2026-0414 puis BL-2026-0415
    deja_livrees: set[str] = set()
    premiere = bon("CMD-2026-0414", "2026-10-07T10:00", [("REF-4600B", 50)])
    seconde = bon("CMD-2026-0414", "2026-10-13T16:10", [("REF-4600B", 50)])
    assert comparer(premiere, COMMANDES, deja_livrees)[0] == "CONFORME"
    statut, ecarts = comparer(seconde, COMMANDES, deja_livrees)
    assert (statut, natures(ecarts)) == ("NON_CONFORME", ["LIVRAISON_EN_DOUBLE"])
