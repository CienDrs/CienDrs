"""Import d'une annonce depuis un texte collé, de n'importe quel site (mode M3).

1. Extraction par expressions régulières (hors ligne, gratuite) ;
2. si des identifiants Claude sont configurés (ANTHROPIC_API_KEY ou profil `ant auth login`),
   extraction par l'API Claude en sortie structurée JSON, complétée par les expressions régulières.
Le résultat est toujours présenté à l'écran de vérification avant enregistrement.
"""
import json
import re

from immo.annonces import ETATS_IMMOWEB, anonymiser

MODELE = "claude-opus-5-5"
ETATS = list(ETATS_IMMOWEB.values())
PEB = ["A++", "A+", "A", "B", "C", "D", "E", "F", "G"]
CHAMPS = {
    "prix": "number", "rue": "string", "numero": "string", "code_postal": "string", "commune": "string",
    "surface_habitable": "number", "surface_terrain": "number", "chambres": "integer",
    "salles_de_bain": "integer", "facades": "integer", "annee_construction": "integer",
    "etat": "string", "peb_lettre": "string", "peb_kwh_m2": "number", "revenu_cadastral": "number",
    "chauffage": "string", "titre": "string",
}


def _nombre(txt):
    return float(re.sub(r"[\s.  ]", "", txt).replace(",", "."))


def extraire_regex(texte: str) -> dict:
    t = texte.replace(" ", " ").replace(" ", " ")
    r = {}

    def cherche(cle, motif, conv=lambda m: m.group(1), flags=re.I):
        if r.get(cle) is None:
            m = re.search(motif, t, flags)
            if m:
                try:
                    r[cle] = conv(m)
                except ValueError:
                    pass

    cherche("prix", r"(?:prix|price)\s*(?:demandé)?\s*[:=]?\s*€?\s*(\d{2,3}(?:[ .]\d{3})+|\d{5,7})\s*€?",
            lambda m: _nombre(m.group(1)))
    cherche("prix", r"(\d{2,3}(?:[ .]\d{3})+|\d{5,7})\s*(?:€|eur)", lambda m: _nombre(m.group(1)))
    cherche("surface_habitable", r"(?:surface\s+habitable|habitable)\s*[:=]?\s*(\d{2,4}(?:[.,]\d+)?)\s*m",
            lambda m: _nombre(m.group(1)))
    cherche("surface_habitable", r"(\d{2,4})\s*m(?:²|2)\s+(?:habitables?|de surface habitable)",
            lambda m: _nombre(m.group(1)))
    cherche("surface_terrain", r"(?:surface\s+du\s+terrain|terrain)\s*(?:de)?\s*[:=]?\s*(\d{2,6}(?:[.,]\d+)?)\s*m",
            lambda m: _nombre(m.group(1)))
    cherche("surface_terrain", r"(?:(\d+)\s*(?:a|ares)\s+(\d+)\s*(?:ca|centiares))",
            lambda m: float(m.group(1)) * 100 + float(m.group(2)))
    cherche("chambres", r"(\d{1,2})\s*chambres?", lambda m: int(m.group(1)))
    cherche("chambres", r"chambres?\s*[:=]\s*(\d{1,2})", lambda m: int(m.group(1)))
    cherche("salles_de_bain", r"(\d)\s*salles?\s+(?:de\s+bains?|d'eau)", lambda m: int(m.group(1)))
    cherche("facades", r"(\d)\s*fa[çc]ades?", lambda m: int(m.group(1)))
    cherche("facades", r"fa[çc]ades?\s*[:=]\s*(\d)", lambda m: int(m.group(1)))
    cherche("annee_construction", r"(?:construit[e]?\s+en|construction\s*[:=]?|ann[ée]e\s+de\s+construction\s*[:=]?)\s*(1[89]\d\d|20[0-4]\d)",
            lambda m: int(m.group(1)))
    cherche("peb_kwh_m2", r"(\d{2,4})\s*kwh\s*/\s*m", lambda m: _nombre(m.group(1)))
    cherche("peb_lettre", r"\b(?:PEB|EPC|classe\s+[ée]nerg[ée]tique)\s*[:=]?\s*(?:classe\s*)?(A\+\+|A\+|[A-G])\b",
            lambda m: m.group(1).upper())
    cherche("revenu_cadastral", r"revenu\s+cadastral\s*[:=]?\s*(?:de\s*)?(\d[\d .]*)\s*(?:€|eur)",
            lambda m: _nombre(m.group(1)))
    cherche("code_postal", r"\b(7\d{3}|[1-6]\d{3})\s+([A-ZÉÈ][\w'éèêâîôûç-]+(?:[ -][A-ZÉÈ][\w'éèêâîôûç-]+)*)",
            lambda m: m.group(1), flags=0)
    if r.get("code_postal"):
        m = re.search(rf"\b{r['code_postal']}\s+([A-ZÉÈ][\w'éèêâîôûç-]+(?:[ -][A-ZÉÈ][\w'éèêâîôûç-]+)*)", t)
        if m:
            r["commune"] = m.group(1)
    tl = t.lower()
    for etat, motifs in [("À restaurer", ["à restaurer", "a restaurer"]), ("À rénover", ["à rénover", "a renover", "travaux à prévoir"]),
                         ("À rafraîchir", ["à rafraîchir", "a rafraichir", "rafraîchissement"]),
                         ("Fraîchement rénové", ["fraîchement rénové", "entièrement rénové", "récemment rénové"]),
                         ("Comme neuf", ["comme neuf"]), ("Bon", ["bon état"])]:
        if any(m in tl for m in motifs):
            r["etat"] = etat
            break
    for chauffage, motifs in [("Gaz", ["gaz"]), ("Mazout", ["mazout"]), ("Pompe à chaleur", ["pompe à chaleur"]),
                              ("Électrique", ["chauffage électrique", "électrique"])]:
        if any(m in tl for m in motifs):
            r["chauffage"] = chauffage
            break
    return r


def schema_json():
    props = {}
    for k, t in CHAMPS.items():
        props[k] = {"anyOf": [{"type": t}, {"type": "null"}]}
    props["etat"] = {"anyOf": [{"type": "string", "enum": ETATS}, {"type": "null"}]}
    props["peb_lettre"] = {"anyOf": [{"type": "string", "enum": PEB}, {"type": "null"}]}
    return {"type": "object", "properties": props, "required": list(CHAMPS), "additionalProperties": False}


CONSIGNE = (
    "Tu extrais les caractéristiques d'une annonce de maison à vendre en Belgique. Réponds uniquement avec "
    "les valeurs explicitement présentes dans le texte ; mets null quand une information est absente ou "
    "ambiguë, sans rien deviner. Prix en euros, surfaces en m² (convertis les ares : 1 a = 100 m²). "
    "« surface_habitable » est la surface habitable du logement, pas celle du terrain. "
    "« etat » reprend l'état du bâtiment s'il est indiqué. « facades » est le nombre de façades."
)


def extraire_llm(texte: str, client=None) -> dict:
    """Extraction par l'API Claude (sortie JSON structurée). Lève une exception en cas d'échec."""
    import anthropic

    client = client or anthropic.Anthropic()
    reponse = client.beta.messages.create(
        model=MODELE,
        max_tokens=2000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema_json()}},
        system=CONSIGNE,
        messages=[{"role": "user", "content": f"Texte de l'annonce :\n\n{texte}"}],
    )
    if reponse.stop_reason == "refusal":
        raise RuntimeError("Le modèle a refusé la demande")
    if reponse.stop_reason == "max_tokens":
        raise RuntimeError("Réponse tronquée")
    contenu = next(b.text for b in reponse.content if b.type == "text")
    return {k: v for k, v in json.loads(contenu).items() if v is not None}


def identifiants_claude_disponibles():
    import os
    import shutil
    import subprocess

    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    if shutil.which("ant"):
        try:
            return subprocess.run(["ant", "auth", "status"], capture_output=True, timeout=10).returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False
    return False


def extraire(texte: str, utiliser_llm=None, client=None) -> dict:
    """Champs extraits + méta-informations (méthode utilisée, avertissements)."""
    regex = extraire_regex(texte)
    resultat, methode, avertissements = dict(regex), "expressions régulières", []
    if utiliser_llm is None:
        utiliser_llm = client is not None or identifiants_claude_disponibles()
    if utiliser_llm:
        try:
            llm = extraire_llm(texte, client)
            resultat = {**regex, **llm}
            methode = "API Claude + expressions régulières"
        except Exception as e:  # le secours ne doit jamais bloquer l'import
            avertissements.append(f"Extraction par l'API Claude indisponible ({type(e).__name__}: {e}) ; "
                                  "seules les expressions régulières ont été utilisées.")
    resultat["description"] = anonymiser(texte.strip())[:5000]
    return {"champs": resultat, "methode": methode, "avertissements": avertissements}
