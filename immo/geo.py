"""Géocodage et risques du terrain (exigences A4, B19, O7, R5, R6).

- Géocodage : Nominatim (OpenStreetMap), ~1 requête/s, avec repli sur la commune signalé « approximatif ».
- Risques : couches ArcGIS REST du géoportail wallon configurées dans parametres.toml
  (aléa d'inondation, contraintes géotechniques, plan de secteur).
Chaque résultat est stocké dans la table `enrichissement` avec sa source et sa date ; une source
indisponible laisse la valeur vide (relançable) sans bloquer l'enregistrement du bien (NF12).
"""
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

from immo import parametres
from immo.statbel import normaliser

USER_AGENT = "analyse-immo/1.0 (usage personnel)"
_derniere_requete = [0.0]


class SourceIndisponible(Exception):
    pass


def _service(url):
    """Nom lisible d'un service pour les messages d'erreur (sans l'URL complète)."""
    parts = urllib.parse.urlsplit(url)
    chemin = parts.path.split("/rest/services/")[-1].split("/MapServer")[0] if "/rest/services/" in parts.path else ""
    return chemin or parts.netloc


def http_json(url, timeout=20):
    """GET JSON avec 1 requête/seconde au maximum (politesse Nominatim)."""
    attente = 1.0 - (time.monotonic() - _derniere_requete[0])
    if attente > 0:
        time.sleep(attente)
    _derniere_requete[0] = time.monotonic()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "fr"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise SourceIndisponible(f"{_service(url)} : erreur HTTP {e.code}") from e
    except urllib.error.URLError as e:
        raise SourceIndisponible(f"{_service(url)} : service injoignable ({e.reason})") from e
    except (TimeoutError, OSError) as e:
        raise SourceIndisponible(f"{_service(url)} : délai dépassé") from e
    except ValueError as e:
        raise SourceIndisponible(f"{_service(url)} : réponse illisible") from e


def distance_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


def distance_centre(lat, lon, p=None):
    p = p or parametres.charger()
    return distance_km(lat, lon, p["zone"]["centre_lat"], p["zone"]["centre_lon"])


def geocoder(rue=None, numero=None, code_postal=None, commune=None, http=http_json):
    """Retourne {latitude, longitude, approximatif, source} ou lève SourceIndisponible."""
    base = "https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=be&"
    essais = []
    if rue:
        essais.append((dict(street=f"{numero or ''} {rue}".strip(), postalcode=code_postal or "",
                            city=commune or ""), False))
    essais.append((dict(postalcode=code_postal or "", city=commune or ""), True))
    for params, approx in essais:
        res = http(base + urllib.parse.urlencode({k: v for k, v in params.items() if v}))
        if res:
            return {"latitude": float(res[0]["lat"]), "longitude": float(res[0]["lon"]),
                    "approximatif": approx, "source": "Nominatim (OpenStreetMap)"}
    return None


CHAMPS_TECHNIQUES = {"objectid", "fid", "shape", "shape_area", "shape_length", "shape.area", "shape.len",
                     "st_area(shape)", "st_length(shape)", "globalid", "pixel value"}
VALEURS_VIDES = {"", "null", "nodata", "none", "<null>", "0"}


def _lisible(v):
    """Garde les valeurs utiles à l'utilisateur : ni liens, ni identifiants techniques, ni valeurs vides."""
    if v is None:
        return None
    t = str(v).strip()
    if t.lower() in VALEURS_VIDES or t.lower().startswith(("http://", "https://", "www.", "{")):
        return None
    if t.replace(".", "", 1).replace("-", "", 1).isdigit():       # identifiants et codes numériques
        return None
    return t


def interroger_service(url, lat, lon, http=http_json):
    """Opération ArcGIS « identify » sur toutes les couches d'un service MapServer, au point (lat, lon).

    Retourne une liste de {couche, valeur, attributs} pour les entités qui contiennent le point.
    L'opération porte sur toutes les couches (y compris les couches de groupe), contrairement à
    « query » qui ne vise qu'une couche d'entités précise.
    """
    d = 0.0005
    q = urllib.parse.urlencode({
        "geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "sr": 4326,
        "layers": "all", "tolerance": 1, "mapExtent": f"{lon - d},{lat - d},{lon + d},{lat + d}",
        "imageDisplay": "400,400,96", "returnGeometry": "false", "f": "json"})
    service = url.split("/MapServer")[0] + "/MapServer"
    res = http(f"{service}/identify?{q}")
    if isinstance(res, dict) and "error" in res:
        err = res["error"]
        raise SourceIndisponible(f"{_service(url)} : {err.get('message', 'erreur du service')} "
                                 f"(code {err.get('code', '?')})")
    resultats = []
    for r in (res or {}).get("results", []):
        attributs = {k: v for k, v in (r.get("attributes") or {}).items()
                     if k.lower() not in CHAMPS_TECHNIQUES and _lisible(v)}
        valeur = _lisible(r.get("value"))
        if valeur is None and not attributs:
            continue                       # pixel « NoData » ou entité sans information
        resultats.append({"couche": r.get("layerName") or "", "valeur": valeur, "attributs": attributs})
    return resultats


def _resume(entites, max_lignes=4):
    lignes = []
    for e in entites:
        texte = e["valeur"] or ", ".join(str(v) for v in list(e["attributs"].values())[:2])
        ligne = f"{e['couche']} : {texte}" if e["couche"] else texte
        if ligne not in lignes:
            lignes.append(ligne)
    reste = len(lignes) - max_lignes
    return " · ".join(lignes[:max_lignes]) + (f" (+{reste})" if reste > 0 else "")


def verifier_risques(lat, lon, p=None, http=http_json):
    """{cle: {libelle, touche (bool|None), bloquant, details, erreur, source}} pour chaque service configuré."""
    p = p or parametres.charger()
    resultats = {}
    for couche in p["risques"]["couches"]:
        r = {"libelle": couche["libelle"], "touche": None, "bloquant": False, "details": "", "erreur": None,
             "source": couche["url"].split("/MapServer")[0] + "/MapServer"}
        try:
            entites = interroger_service(couche["url"], lat, lon, http)
            r["touche"] = bool(entites)
            r["details"] = _resume(entites) if entites else "aucune zone au point du bien"
            if entites and couche.get("bloquant"):
                texte = normaliser(" ".join(f"{e['couche']} {e['valeur'] or ''}" for e in entites))
                r["bloquant"] = not any(normaliser(m) in texte for m in couche.get("non_bloquant_si", []))
        except SourceIndisponible as e:
            r["erreur"] = str(e)
        resultats[couche["cle"]] = r
    return resultats


# --------------------------------------------------------- persistance (enrichissement)

def enregistrer(con, immoweb_id, cle, valeur, source):
    con.execute("INSERT OR REPLACE INTO enrichissement VALUES (?, ?, ?, ?, ?)",
                (str(immoweb_id), cle, None if valeur is None else json.dumps(valeur, ensure_ascii=False),
                 source, date.today().isoformat()))
    con.commit()


def lire(con, immoweb_id):
    return {cle: {"valeur": json.loads(v) if v else None, "source": s, "date": d}
            for cle, v, s, d in con.execute("SELECT cle, valeur, source, date FROM enrichissement "
                                            "WHERE immoweb_id = ?", (str(immoweb_id),))}


def enrichir(con, bien: dict, p=None, http=http_json):
    """Géocode le bien si nécessaire, puis vérifie les risques ; ne lève jamais d'exception."""
    p = p or parametres.charger()
    ident = bien["immoweb_id"]
    lat, lon = bien.get("latitude"), bien.get("longitude")
    messages = []
    if lat is None or lon is None or (isinstance(lat, float) and math.isnan(lat)):
        try:
            g = geocoder(bien.get("rue"), bien.get("numero"), bien.get("code_postal"), bien.get("commune"), http)
        except SourceIndisponible as e:
            g, _ = None, messages.append(f"Géocodage indisponible ({e})")
        enregistrer(con, ident, "geocodage", g, "Nominatim (OpenStreetMap)")
        if g:
            lat, lon = g["latitude"], g["longitude"]
            con.execute("UPDATE annonces SET latitude = ?, longitude = ?, distance_mons_km = ?, "
                        "adresse_approximative = ? WHERE immoweb_id = ?",
                        (lat, lon, round(distance_centre(lat, lon, p), 2), int(g["approximatif"]), ident))
            con.commit()
    if lat is not None and lon is not None:
        risques = verifier_risques(lat, lon, p, http)
        enregistrer(con, ident, "risques_auto", risques, "Géoportail de la Wallonie (WalOnMap)")
        messages += [f"{r['libelle']} : source indisponible" for r in risques.values() if r["erreur"]]
    return messages
