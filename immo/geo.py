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
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        raise SourceIndisponible(f"{urllib.parse.urlsplit(url).netloc} : {e}") from e


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


def interroger_couche(url, lat, lon, http=http_json):
    """Entités d'une couche ArcGIS REST qui contiennent le point (liste d'attributs)."""
    q = urllib.parse.urlencode({
        "geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects", "outFields": "*", "returnGeometry": "false", "f": "json"})
    res = http(f"{url.rstrip('/')}/query?{q}")
    if "error" in res:
        raise SourceIndisponible(f"{url} : {res['error'].get('message', res['error'])}")
    return [f.get("attributes", {}) for f in res.get("features", [])]


def verifier_risques(lat, lon, p=None, http=http_json):
    """{cle: {libelle, touche (bool|None), bloquant, details, erreur}} pour chaque couche configurée."""
    p = p or parametres.charger()
    resultats = {}
    for couche in p["risques"]["couches"]:
        r = {"libelle": couche["libelle"], "touche": None, "bloquant": False, "details": "", "erreur": None,
             "source": couche["url"]}
        try:
            entites = interroger_couche(couche["url"], lat, lon, http)
            r["touche"] = bool(entites)
            valeurs = sorted({str(v) for e in entites for k, v in e.items()
                              if v not in (None, "") and k.lower() not in ("objectid", "shape_area", "shape_length")})
            r["details"] = ", ".join(valeurs)[:300]
            if entites and couche.get("bloquant"):
                texte = normaliser(" ".join(valeurs))
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
