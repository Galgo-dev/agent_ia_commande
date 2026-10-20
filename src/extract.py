"""Extraction LLM : texte d'un bon de livraison -> dict structuré (le LLM extrait, il ne compare pas)."""
import json

MODELE = "claude-haiku-4-5"

PROMPT = """Tu lis un bon de livraison. Extrais sans rien deviner.
Si une valeur est illisible ou ambiguë, mets `lisible:false` et décris-la dans `doutes`.
Réponds uniquement avec un objet JSON, sans aucun texte autour, de cette forme :
{"num_commande": "...", "date_reception": "AAAA-MM-JJTHH:MM",
 "lignes": [{"reference": "...", "qte_recue": 0}],
 "remarques": ["..."], "lisible": true, "doutes": []}
Règles :
- num_commande et reference : recopie-les tels qu'écrits sur le bon (null si absent).
- date_reception : date et heure de réception, converties au format ISO. Les dates sont écrites jour/mois/année.
- qte_recue : nombre entier, ou null si la quantité est illisible ou ambiguë (par exemple « 3? »).
- remarques : les observations ou mentions du bon, recopiées telles quelles (liste vide si rien).
"""

ECHEC = {"num_commande": None, "date_reception": None, "lignes": [], "remarques": [],
         "lisible": False, "doutes": ["extraction impossible : réponse du modèle invalide"]}


def _appeler_modele(texte: str, client) -> str:
    reponse = client.messages.create(
        model=MODELE, max_tokens=1024, system=PROMPT,
        messages=[{"role": "user", "content": texte}],
    )
    return "".join(b.text for b in reponse.content if b.type == "text")


def _parser_json(reponse: str) -> dict:
    """Isole l'objet JSON de la réponse (même entouré de ```) ; ValueError si invalide."""
    debut, fin = reponse.find("{"), reponse.rfind("}")
    if debut == -1 or fin < debut:
        raise ValueError("aucun objet JSON dans la réponse")
    bon = json.loads(reponse[debut:fin + 1])
    if not isinstance(bon, dict) or not isinstance(bon.get("lignes", []), list):
        raise ValueError("structure JSON inattendue")
    return bon


def _entier(valeur: object) -> int | None:
    if isinstance(valeur, int) and not isinstance(valeur, bool):
        return valeur
    if isinstance(valeur, str) and valeur.strip().isdigit():
        return int(valeur.strip())
    return None


def _texte(valeur: object) -> str | None:
    return str(valeur).strip().upper() if valeur and str(valeur).strip() else None


def normaliser(bon: dict) -> dict:
    """Normalisation en code : majuscules, espaces retirés, quantités entières ou None."""
    return {
        "num_commande": _texte(bon.get("num_commande")),
        "date_reception": bon.get("date_reception"),
        "lignes": [{"reference": _texte(ligne.get("reference")) or "", "qte_recue": _entier(ligne.get("qte_recue"))}
                   for ligne in bon.get("lignes") or [] if isinstance(ligne, dict)],
        "remarques": [str(r).strip() for r in bon.get("remarques") or [] if str(r).strip()],
        "lisible": bon.get("lisible") is True,
        "doutes": [str(d) for d in bon.get("doutes") or []],
    }


def extraire_bon(texte: str, client) -> dict:
    """Extrait un bon ; JSON invalide -> 1 retry, puis bon illisible (fiche A_VERIFIER)."""
    for _ in range(2):
        try:
            return normaliser(_parser_json(_appeler_modele(texte, client)))
        except ValueError:
            continue
    return dict(ECHEC)
