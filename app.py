"""Application d'analyse achat-rénovation-revente — V1 (MVP du cahier des charges).

Lancement :  poetry run streamlit run app.py   (ou : streamlit run app.py après pip install -r requirements.txt)
"""
import json
import os
import re
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from immo import analyse, annonces, extraction_texte, finance, geo, parametres, statbel, travaux

RACINE = Path(__file__).resolve().parent
BASE = Path(os.environ.get("IMMO_BASE", RACINE / "data" / "annonces.sqlite"))
P = parametres.charger()
BLEU, ORANGE, GRIS = "#2a78d6", "#eb6834", "#8a8984"
ETATS = list(annonces.ETATS_IMMOWEB.values())
PEB = travaux.CLASSES_PEB
RISQUES_MANUELS = [c["libelle"] for c in P["risques"]["couches"] if c.get("bloquant")] + [
    "Infraction urbanistique non régularisable", "Pollution du sol (BDES)", "Problème de stabilité / structure",
    "Zone d'aléa d'inondation élevé"]

st.set_page_config(page_title="Analyse immo — Mons", page_icon="🏠", layout="wide")


# ------------------------------------------------------------------ utilitaires

def con():
    return annonces.connecter(BASE)


def eur(x, signe=False):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    s = f"{x:+,.0f}" if signe else f"{x:,.0f}"
    return s.replace(",", " ") + " €"


def pct(x, signe=True):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    return (f"{x:+.1%}" if signe else f"{x:.1%}").replace(".", ",")


def _layout(fig, titre_x, titre_y, hauteur=360):
    fig.update_layout(height=hauteur, margin=dict(l=10, r=10, t=30, b=10), showlegend=True,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
                      xaxis_title=titre_x, yaxis_title=titre_y, hovermode="closest")
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.15)")
    return fig


def afficher(fig, col=None):
    (col or st).plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def aller_fiche(ident):
    st.session_state["bien"] = str(ident)
    st.switch_page(PAGE_FICHE)


CODE_POSTAL_WALLON = re.compile(r"^(1[34]\d\d|[4-7]\d\d\d)$")


# ------------------------------------------------------------------ page : biens

def page_biens():
    st.title("📋 Biens")
    c = con()
    df = annonces.tableau_annonces(c)
    if df.empty:
        st.info("La base est vide. Ajoutez un bien (page **Ajouter un bien**) ou chargez les données d'exemple "
                "(page **Données**).")
        return
    dec = pd.read_sql("SELECT immoweb_id, date, resultat FROM analyses ORDER BY date", c)
    if not dec.empty:
        dec["décision"] = dec["resultat"].map(lambda r: (json.loads(r).get("decision") or {}).get("statut"))
        df = df.merge(dec.groupby("immoweb_id").last()[["décision"]], left_on="immoweb_id", right_index=True,
                      how="left")
    else:
        df["décision"] = None

    f1, f2, f3, f4 = st.columns([2, 2, 1, 1])
    communes = f1.multiselect("Communes", sorted(df["commune"].dropna().unique()), placeholder="Toutes")
    etats = f2.multiselect("État", ETATS, placeholder="Tous")
    en_ligne = f3.toggle("En ligne uniquement", value=True)
    sans_exemples = f4.toggle("Masquer les exemples fictifs", value=False)
    vue = df
    if communes:
        vue = vue[vue["commune"].isin(communes)]
    if etats:
        vue = vue[vue["etat"].isin(etats)]
    if en_ligne:
        vue = vue[vue["en_ligne"]]
    if sans_exemples:
        vue = vue[vue["source"].fillna("") != "exemple fictif"]

    colonnes = {"immoweb_id": "Annonce", "commune": "Commune", "prix_actuel": "Prix (€)",
                "surface_habitable": "Surface (m²)", "prix_m2": "Prix/m² (€)", "chambres": "Ch.",
                "etat": "État", "peb_lettre": "PEB", "distance_mons_km": "Distance (km)",
                "jours_en_ligne": "Jours en ligne", "nb_baisses_prix": "Baisses", "variation_prix_pct": "Variation (%)",
                "en_ligne": "En ligne", "décision": "Dernière décision"}
    tableau = vue[list(colonnes)].rename(columns=colonnes).sort_values("Prix/m² (€)")
    st.caption(f"{len(tableau)} biens affichés sur {len(df)}. Cliquez sur une ligne pour ouvrir la fiche.")
    sel = st.dataframe(
        tableau, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
        column_config={"Prix (€)": st.column_config.NumberColumn(format="%.0f"),
                       "Prix/m² (€)": st.column_config.NumberColumn(format="%.0f"),
                       "Variation (%)": st.column_config.NumberColumn(format="%.1f"),
                       "Distance (km)": st.column_config.NumberColumn(format="%.1f")})
    if sel.selection.rows:
        aller_fiche(tableau.iloc[sel.selection.rows[0]]["Annonce"])


# ------------------------------------------------------------------ page : ajouter

def formulaire_verification(brouillon):
    st.subheader("Vérification avant enregistrement")
    st.caption("L'extraction propose, vous validez : corrigez ou complétez les champs. "
               "Les champs indispensables manquants sont signalés.")
    for a in brouillon.get("_avertissements", []):
        st.warning(a)
    manquants = [lib for cle, lib in annonces.CHAMPS_ESSENTIELS.items() if not brouillon.get(cle)]
    if manquants:
        st.warning("À compléter ou à demander à l'agence : " + ", ".join(manquants))

    def num(col, label, cle, pas=1.0, fmt="%.0f"):
        v = brouillon.get(cle)
        return col.number_input(label, value=float(v) if v not in (None, "") else None, step=pas, format=fmt,
                                placeholder="non communiqué")

    with st.form("verification"):
        a, b, c = st.columns(3)
        ident = a.text_input("Identifiant (code Immoweb ou M…)", brouillon.get("immoweb_id") or "")
        titre = b.text_input("Titre", brouillon.get("titre") or "")
        prix = num(c, "Prix demandé (€) *", "prix", 1000.0)
        a, b, c, d = st.columns([3, 1, 1, 2])
        rue = a.text_input("Rue", brouillon.get("rue") or "")
        numero = b.text_input("Numéro", brouillon.get("numero") or "")
        cp = c.text_input("Code postal *", brouillon.get("code_postal") or "")
        commune = d.text_input("Commune / localité *", brouillon.get("commune") or "")
        a, b, c, d = st.columns(4)
        surface = num(a, "Surface habitable (m²) *", "surface_habitable")
        terrain = num(b, "Surface du terrain (m²)", "surface_terrain")
        chambres = num(c, "Chambres", "chambres")
        sdb = num(d, "Salles d'eau", "salles_de_bain")
        a, b, c, d = st.columns(4)
        facades = num(a, "Façades", "facades")
        annee = num(b, "Année de construction", "annee_construction")
        etat_v = brouillon.get("etat")
        etat = c.selectbox("État du bâtiment", [None] + ETATS, index=([None] + ETATS).index(etat_v)
                           if etat_v in ETATS else 0, format_func=lambda x: x or "non communiqué")
        rc = num(d, "Revenu cadastral (€)", "revenu_cadastral")
        a, b, c = st.columns(3)
        peb_v = brouillon.get("peb_lettre")
        peb = a.selectbox("Classe PEB", [None] + PEB, index=([None] + PEB).index(peb_v) if peb_v in PEB else 0,
                          format_func=lambda x: x or "non communiqué")
        kwh = num(b, "Consommation PEB (kWh/m²/an)", "peb_kwh_m2")
        date_pub = c.text_input("Date de publication (AAAA-MM-JJ)", brouillon.get("date_publication") or "")
        description = st.text_area("Description (téléphones et e-mails retirés)", brouillon.get("description") or "",
                                   height=120)
        envoyer = st.form_submit_button("✅ Valider et enregistrer", type="primary")

    if envoyer:
        erreurs = []
        if not prix or prix <= 0:
            erreurs.append("le prix doit être > 0")
        if surface is not None and surface <= 0:
            erreurs.append("la surface doit être > 0")
        if not CODE_POSTAL_WALLON.match(cp.strip()):
            erreurs.append("code postal wallon attendu (1300-1499 ou 4000-7999)")
        if not commune.strip():
            erreurs.append("commune obligatoire")
        if date_pub and not re.match(r"^\d{4}-\d{2}-\d{2}$", date_pub):
            erreurs.append("date de publication au format AAAA-MM-JJ")
        if erreurs:
            st.error("Corrigez : " + " ; ".join(erreurs))
            return
        c_ = con()
        ident = ident.strip() or analyse.nouvel_identifiant_manuel(c_)
        champs = dict(url=brouillon.get("url"), titre=titre or None, rue=rue or None, numero=numero or None,
                      code_postal=cp.strip(), commune=commune.strip(), surface_habitable=surface,
                      surface_terrain=terrain, chambres=chambres, salles_de_bain=sdb, facades=facades,
                      annee_construction=annee, etat=etat, revenu_cadastral=rc, peb_lettre=peb, peb_kwh_m2=kwh,
                      date_publication=date_pub or None, description=description or None,
                      source=brouillon.get("source", "manuel"), type_bien="maison")
        for cle in ("latitude", "longitude", "adresse_precise", "adresse_approximative", "province", "chauffage",
                    "cuisine", "surface_jardin", "surface_terrasse", "nb_etages", "cave", "grenier",
                    "vendeur_type", "prix_ancien_immoweb", "nb_vues", "nb_favoris", "peb_reference"):
            if brouillon.get(cle) is not None:
                champs[cle] = brouillon[cle]
        annonces.enregistrer_observation(c_, ident, prix, date.today().isoformat(), **champs)
        with st.spinner("Géocodage et vérification des risques…"):
            messages = geo.enrichir(c_, analyse.charger_bien(c_, ident)[0], P)
        for m in messages:
            st.warning(m)
        st.session_state.pop("brouillon", None)
        st.success(f"Bien {ident} enregistré.")
        aller_fiche(ident)


def page_ajouter():
    st.title("➕ Ajouter un bien")
    t1, t2, t3 = st.tabs(["Page Immoweb", "Texte collé (tous sites)", "Saisie manuelle"])
    with t1:
        url = st.text_input("Lien de l'annonce Immoweb (facultatif)")
        m = re.search(r"/(\d{6,10})(?:[/?#]|$)", url or "")
        if m:
            st.info(f"Annonce **{m.group(1)}**. L'outil ne télécharge pas les pages Immoweb lui-même : ouvrez "
                    "l'annonce dans votre navigateur, enregistrez-la (Ctrl+S, « Page web, HTML uniquement ») "
                    "puis déposez le fichier ci-dessous.")
        fichier = st.file_uploader("Page d'annonce enregistrée (.html)", type=["html", "htm", "txt"])
        if fichier and st.button("Extraire l'annonce", type="primary"):
            try:
                champs = annonces.extraire_page_immoweb(fichier.getvalue().decode("utf-8", errors="replace"))
                st.session_state["brouillon"] = {**champs, "source": "immoweb"}
            except Exception as e:
                st.error(f"Extraction impossible ({e}). Utilisez l'onglet « Texte collé » ou la saisie manuelle.")
    with t2:
        llm = extraction_texte.identifiants_claude_disponibles()
        st.caption("Extraction par l'API Claude (identifiants détectés)" if llm else
                   "Extraction par expressions régulières. Pour une extraction plus fiable, configurez "
                   "ANTHROPIC_API_KEY (quelques centimes par annonce).")
        texte = st.text_area("Texte de l'annonce", height=220)
        if texte and st.button("Extraire le texte", type="primary"):
            with st.spinner("Extraction…"):
                r = extraction_texte.extraire(texte, utiliser_llm=llm)
            st.session_state["brouillon"] = {**r["champs"], "source": "texte",
                                             "_avertissements": r["avertissements"]}
            st.caption(f"Méthode : {r['methode']}")
    with t3:
        if st.button("Nouveau bien vierge"):
            st.session_state["brouillon"] = {"source": "manuel"}
    if "brouillon" in st.session_state:
        st.divider()
        formulaire_verification(st.session_state["brouillon"])


# ------------------------------------------------------------------ page : fiche

STATUTS = {finance.GO: ("success", "✅"), finance.GO_SOUS_CONDITIONS: ("warning", "⚠️"),
           finance.NO_GO: ("error", "⛔")}


def bloc_decision(res):
    d = res["decision"]
    if d is None:
        st.warning("Décision impossible : il manque " + ", ".join(res["manquants_decision"]) +
                   ". Complétez le bien ou saisissez les hypothèses dans l'onglet « Opération ».")
        return
    genre, icone = STATUTS[d["statut"]]
    getattr(st, genre)(f"**{d['statut']}** au prix d'achat de {eur(res['hypotheses']['prix_achat'])}", icon=icone)
    a, b, c = st.columns(3)
    a.metric("Prix cible (−20 %)", eur(d["prix_cible"]))
    b.metric("Prix d'achat maximum (marge ≥ 30 000 €, prudent)", eur(d["prix_max"]))
    c.metric("Offre recommandée", eur(d["prix_offre_recommande"]),
             help="Minimum du prix cible et du prix maximum")
    regles = pd.DataFrame([{"Règle": r["code"], "Critère": r["libelle"],
                            "Résultat": "✅ oui" if r["ok"] else ("❌ non" if r["ok"] is False else "❔ non évalué"),
                            "Détail": r["detail"], "Type": "obligatoire" if r["obligatoire"] else "recommandée"}
                           for r in d["regles"]])
    st.dataframe(regles, hide_index=True, width="stretch")

    lignes = [("Prix d'achat", "prix_achat"), ("Frais d'acquisition", ("frais_acquisition", "total")),
              ("Travaux (imprévus compris)", "travaux_total"), ("Portage", ("portage", "total")),
              ("Prix de revient", "prix_revient"), ("Prix de revente", "prix_revente"),
              ("Frais de revente", ("frais_revente", "total")), ("Plus-value nette avant impôt", "plus_value"),
              ("Impôt indicatif", "impot"), ("Plus-value après impôt", "plus_value_apres_impot")]
    tab = {}
    for sc in finance.SCENARIOS:
        b_ = d["bilans"][sc]
        tab[f"{sc.capitalize()} ({b_['duree_mois']:g} mois)"] = [
            eur(b_[k[0]][k[1]] if isinstance(k, tuple) else b_[k]) for _, k in lignes] + [pct(b_["marge_sur_revient"], False)]
    st.markdown("**Bilan de l'opération**")
    st.dataframe(pd.DataFrame(tab, index=[l for l, _ in lignes] + ["Marge sur prix de revient"]),
                 width="stretch")


def graphique_comparables(res):
    v = res["valeur_en_l_etat"]
    comp = v["comparables"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=comp["surface_habitable"], y=comp["prix_actualise"], mode="markers", name="Comparables",
        marker=dict(color=BLEU, size=9, line=dict(color="white", width=2)),
        customdata=comp[["immoweb_id", "commune", "etat", "prix_m2_actualise"]],
        hovertemplate="%{customdata[0]} — %{customdata[1]}<br>%{x:.0f} m² · %{y:,.0f} €<br>"
                      "%{customdata[2]} · %{customdata[3]:,.0f} €/m²<extra></extra>"))
    b = res["bien"]
    fig.add_trace(go.Scatter(x=[b["surface_habitable"]], y=[b["prix_actuel"]], mode="markers+text",
                             name="Ce bien", text=["Ce bien"], textposition="top center",
                             marker=dict(color=ORANGE, size=14, symbol="diamond", line=dict(color="white", width=2)),
                             hovertemplate="Ce bien<br>%{x:.0f} m² · %{y:,.0f} €<extra></extra>"))
    return _layout(fig, "Surface habitable (m²)", "Prix demandé actualisé (€)")


def graphique_distribution(res):
    v = res["valeur_en_l_etat"]
    fig = go.Figure(go.Histogram(x=v["comparables"]["prix_m2_actualise"], nbinsx=15, name="Comparables",
                                 marker=dict(color=BLEU, line=dict(color="white", width=2)),
                                 hovertemplate="%{x} €/m² : %{y} biens<extra></extra>"))
    if res["prix_m2"]:
        fig.add_vline(x=res["prix_m2"], line=dict(color=ORANGE, width=2),
                      annotation_text=f"Ce bien : {res['prix_m2']:,.0f} €/m²".replace(",", " "))
    fig = _layout(fig, "Prix/m² demandé actualisé (€)", "Nombre de biens", 300)
    return fig.update_yaxes(tickformat="d", dtick=1)


def carte(res):
    comp = res["valeur_en_l_etat"]["comparables"].dropna(subset=["latitude", "longitude"])
    b = res["bien"]
    fig = go.Figure()
    fig.add_trace(go.Scattermap(lat=comp["latitude"], lon=comp["longitude"], mode="markers", name="Comparables",
                                marker=dict(size=10, color=BLEU), text=comp["immoweb_id"] + " — " +
                                comp["prix_actualise"].map(lambda x: eur(x)), hoverinfo="text"))
    if b.get("latitude") is not None:
        fig.add_trace(go.Scattermap(lat=[b["latitude"]], lon=[b["longitude"]], mode="markers", name="Ce bien",
                                    marker=dict(size=16, color=ORANGE), text=["Ce bien"], hoverinfo="text"))
        centre = dict(lat=b["latitude"], lon=b["longitude"])
    else:
        centre = dict(lat=P["zone"]["centre_lat"], lon=P["zone"]["centre_lon"])
    fig.update_layout(map=dict(style="open-street-map", center=centre, zoom=12), height=380,
                      margin=dict(l=0, r=0, t=0, b=0), legend=dict(orientation="h", y=1.02, x=0))
    return fig


def onglet_prix(res):
    v, apres, sb = res["valeur_en_l_etat"], res["valeur_apres_travaux"], res["statbel"]
    a, b, c = st.columns(3)
    with a:
        st.markdown("**Écart au médian communal (Statbel)**")
        if sb:
            types = {"maison_2_3_facades": "maisons 2-3 façades", "maison_4_facades": "maisons 4 façades",
                     "maison": "maisons"}
            st.metric(f"{sb['commune']} — {sb['annee']} ({types.get(sb['type_bien'], sb['type_bien'])})",
                      eur(sb["mediane"]), pct(sb["ecart"]), delta_color="inverse")
            st.caption(f"Source : {sb['source']}")
        else:
            st.caption("Médiane Statbel indisponible pour cette commune (importez le fichier Statbel, page Données).")
    with b:
        st.markdown("**Prix/m² vs comparables**")
        if res.get("position_prix_m2"):
            pos = res["position_prix_m2"]
            st.metric("Médiane des comparables", eur(pos["mediane_comparables"]) + "/m²", pct(pos["ecart"]),
                      delta_color="inverse")
            st.caption(f"Ce bien : {eur(res['prix_m2'])}/m² — percentile {pos['percentile']:.0f}")
        else:
            st.caption("Pas de comparables (surface manquante ou base trop petite).")
    with c:
        st.markdown("**Résidu du modèle hédonique**")
        st.caption("Prévu en V2 (au moins 30 maisons dans le secteur).")
    st.divider()
    a, b = st.columns(2)
    for col, titre, val in ((a, "Valeur en l'état", v), (b, "Valeur après travaux (« Fraîchement rénové »)", apres)):
        with col:
            st.markdown(f"**{titre}**")
            if val.get("disponible"):
                st.metric("Estimation centrale", eur(val["centrale"]),
                          help="Comparables ramenés à cet état, corrigés de la marge de négociation")
                st.caption(f"Fourchette : {eur(val['basse'])} – {eur(val['haute'])} · {val['n']} comparables "
                           f"({val['n_meme_etat']} dans le même état) · confiance **{val['confiance']}** · "
                           f"{val['criteres']}")
                if val.get("alerte_sur_renovation"):
                    st.warning("Valeur après travaux au-dessus du 90e percentile du secteur : risque de sur-rénovation.")
            else:
                st.caption(f"Indisponible : {val.get('raison')}")
    if v.get("disponible"):
        g1, g2 = st.columns(2)
        afficher(graphique_comparables(res), g1)
        afficher(graphique_distribution(res), g2)
        afficher(carte(res))
        with st.expander(f"Tableau des {v['n']} comparables"):
            cols = {"immoweb_id": "Annonce", "commune": "Commune", "distance_km": "Distance (km)",
                    "surface_habitable": "Surface", "chambres": "Ch.", "etat": "État", "peb_lettre": "PEB",
                    "prix_actualise": "Prix actualisé", "prix_m2_actualise": "€/m²",
                    "prix_m2_ramene": "€/m² ramené à l'état", "en_ligne": "En ligne", "nb_baisses_prix": "Baisses"}
            st.dataframe(v["comparables"][list(cols)].rename(columns=cols).round(1), hide_index=True,
                         width="stretch")


def onglet_operation(c, res):
    h, t = res["hypotheses"], res["travaux"]
    st.markdown("**Pré-chiffrage des travaux**")
    if t.get("central"):
        st.caption(f"{t['libelle_niveau']} (état « {res['bien'].get('etat') or '?'} »), "
                   f"{t['classes_peb_gagnees']} classe(s) PEB gagnée(s) vers "
                   f"{P['estimation']['peb_classe_cible_defaut']} : {eur(t['bas'])} – {eur(t['haut'])}, "
                   f"central {eur(t['central'])} TVAC hors imprévus ({pct(t['taux_imprevus'], False)}). "
                   "Ratios indicatifs à remplacer par les devis.")
    else:
        st.caption("Surface inconnue : saisissez le coût des travaux ci-dessous.")
    with st.form("hypotheses"):
        st.markdown("**Hypothèses de l'opération** (pré-remplies, modifiables)")
        a, b, c_ = st.columns(3)
        prix_achat = a.number_input("Prix d'achat (€)", value=float(h["prix_achat"] or 0), step=1000.0)
        travaux_ = b.number_input("Travaux TVAC hors imprévus (€)", value=float(h["travaux"] or 0), step=1000.0)
        imprevus = c_.number_input("Imprévus (%)", value=float(h["taux_imprevus"] or 0) * 100, step=1.0)
        a, b, c_ = st.columns(3)
        revente = a.number_input("Prix de revente après travaux (€)", value=float(h["prix_revente"] or 0), step=1000.0)
        duree = b.number_input("Durée de l'opération (mois)", value=float(h["duree_mois"]), step=1.0)
        regime = c_.selectbox("Régime", ["personne_physique", "marchand_de_biens"],
                              index=0 if h["regime"] == "personne_physique" else 1,
                              format_func=lambda x: {"personne_physique": "Personne physique (12,5 %)",
                                                     "marchand_de_biens": "Marchand de biens (≈ 5 %)"}[x])
        a, b, c_ = st.columns(3)
        valeur = a.number_input("Valeur en l'état (€)", value=float(h["valeur_en_l_etat"] or 0), step=1000.0)
        portage = b.number_input("Portage mensuel forfaitaire (€, 0 = calcul détaillé)",
                                 value=float(h["portage_mensuel"] or 0), step=100.0)
        agence = c_.checkbox("Revente via agence", value=bool(h["vente_par_agence"]))
        g, r = st.columns(2)
        sauver = g.form_submit_button("💾 Enregistrer les hypothèses", type="primary")
        reinit = r.form_submit_button("↺ Revenir aux valeurs estimées")
    if sauver:
        analyse.enregistrer_hypotheses(c, res["bien"]["immoweb_id"], {
            "prix_achat": prix_achat, "travaux": travaux_, "taux_imprevus": imprevus / 100,
            "prix_revente": revente or None, "duree_mois": duree, "regime": regime,
            "valeur_en_l_etat": valeur or None, "portage_mensuel": portage or None, "vente_par_agence": agence})
        st.rerun()
    if reinit:
        analyse.enregistrer_hypotheses(c, res["bien"]["immoweb_id"], {})
        st.rerun()
    d = res["decision"]
    if d:
        p = d["bilans"]["central"]["portage"]
        st.caption("Portage (central) : " + " · ".join(f"{k.replace('_', ' ')} {eur(v)}" for k, v in p.items()))


def onglet_risques(c, res):
    b = res["bien"]
    if b.get("latitude") is not None:
        st.caption(f"Coordonnées : {b['latitude']:.5f}, {b['longitude']:.5f}"
                   + (" (position approximative)" if b.get("adresse_approximative") else "")
                   + f" — à {b.get('distance_mons_km') or geo.distance_centre(b['latitude'], b['longitude'], P):.1f} km "
                     f"de la {P['zone']['centre_nom']}")
    auto, leves = res["risques"]["auto"], res["risques"].get("leves", [])
    if auto:
        st.markdown(f"**Vérification automatique** — géoportail de la Wallonie, {res['risques']['auto_date']}")

        def resultat(cle, r):
            if r["erreur"]:
                return "❔ non vérifié (service indisponible)"
            if r["bloquant"]:
                return "✅ vérifié, non bloquant" if cle in leves else "⛔ concerné — bloquant"
            return "⚠️ concerné" if r["touche"] else "✅ non concerné"

        for cle, r in auto.items():
            with st.container(border=True):
                g, d = st.columns([2, 3])
                g.markdown(f"**{r['libelle']}**  \n{resultat(cle, r)}")
                d.markdown(r["erreur"] or r["details"] or "—")
                if r.get("source"):
                    d.caption(f"Source : [service du géoportail]({r['source']})")
        concernes = {cle: r["libelle"] for cle, r in auto.items() if r.get("bloquant")}
        if concernes:
            choix = st.multiselect("Risques automatiques vérifiés sur place ou auprès de l'administration et jugés "
                                   "non bloquants", options=list(concernes), default=[k for k in leves if k in concernes],
                                   format_func=concernes.get, placeholder="Aucun")
            if set(choix) != set(leves) and st.button("Enregistrer la vérification"):
                analyse.enregistrer_risques_leves(c, b["immoweb_id"], choix)
                st.rerun()
    else:
        st.info("Risques pas encore vérifiés pour ce bien.")
    if st.button("🔄 Géocoder et vérifier les risques"):
        with st.spinner("Interrogation de Nominatim et du géoportail wallon…"):
            for m in geo.enrichir(c, b, P):
                st.warning(m)
        st.rerun()
    st.markdown("**Risques constatés manuellement** (WalOnMap, renseignements urbanistiques, BDES, visite)")
    st.caption("[Ouvrir WalOnMap](https://geoportail.wallonie.be/walonmap) · "
               "[Banque de données de l'état des sols](https://bdes.wallonie.be) — un risque coché est bloquant (R5).")
    choix = st.multiselect("Risques bloquants", placeholder="Aucun", options=RISQUES_MANUELS + [
        r for r in res["risques"]["manuels"] if r not in RISQUES_MANUELS], default=res["risques"]["manuels"])
    if choix != res["risques"]["manuels"] and st.button("Enregistrer les risques"):
        analyse.enregistrer_risques_manuels(c, b["immoweb_id"], choix)
        st.rerun()


def onglet_historique(c, res):
    b = res["bien"]
    hist = pd.read_sql("SELECT date_observation, prix FROM historique_prix WHERE immoweb_id = ? "
                       "ORDER BY date_observation", c, params=(b["immoweb_id"],))
    a, b_, c_ = st.columns(3)
    a.metric("Jours en ligne", f"{b.get('jours_en_ligne') or 0:.0f}")
    b_.metric("Baisses de prix", f"{b.get('nb_baisses_prix') or 0:.0f}", pct((b.get("variation_prix_pct") or 0) / 100))
    c_.metric("Statut", "En ligne" if b.get("en_ligne") else f"Retirée le {b.get('date_retrait')}")
    if len(hist) > 1:
        fig = go.Figure(go.Scatter(x=hist["date_observation"], y=hist["prix"], mode="lines+markers", name="Prix",
                                   line=dict(color=BLEU, width=2, shape="hv"), marker=dict(size=8),
                                   hovertemplate="%{x} : %{y:,.0f} €<extra></extra>"))
        afficher(_layout(fig, "Date", "Prix demandé (€)", 300).update_layout(showlegend=False),
                        width="stretch")
    else:
        st.caption("Un seul prix observé : l'historique se construit à chaque réimport de l'annonce.")
    an = pd.read_sql("SELECT date, version_modele, resultat FROM analyses WHERE immoweb_id = ? ORDER BY date DESC",
                     c, params=(b["immoweb_id"],))
    if not an.empty:
        an["décision"] = an["resultat"].map(lambda r: (json.loads(r).get("decision") or {}).get("statut"))
        an["prix max"] = an["resultat"].map(lambda r: eur((json.loads(r).get("decision") or {}).get("prix_max")))
        st.markdown("**Analyses enregistrées**")
        st.dataframe(an[["date", "version_modele", "décision", "prix max"]], hide_index=True)


def onglet_donnees(c, res):
    b = res["bien"]
    if res["champs_manquants"]:
        st.warning("À demander à l'agence : " + ", ".join(res["champs_manquants"]))
    with st.form("completer"):
        st.markdown("**Compléter / corriger**")
        a, b_, c_, d = st.columns(4)
        surface = a.number_input("Surface habitable (m²)", value=b.get("surface_habitable"), step=1.0)
        terrain = b_.number_input("Terrain (m²)", value=b.get("surface_terrain"), step=1.0)
        annee = c_.number_input("Année de construction", value=b.get("annee_construction"), step=1.0, format="%.0f")
        etat = d.selectbox("État", [None] + ETATS, index=([None] + ETATS).index(b.get("etat"))
                           if b.get("etat") in ETATS else 0, format_func=lambda x: x or "—")
        if st.form_submit_button("Enregistrer"):
            annonces.completer(c, b["immoweb_id"], surface_habitable=surface, surface_terrain=terrain,
                               annee_construction=annee, etat=etat)
            st.rerun()
    champs = {k: v for k, v in b.items() if v is not None and k not in ("historique_prix",)}
    st.dataframe(pd.DataFrame({"Champ": list(champs), "Valeur": [str(v) for v in champs.values()]}),
                 hide_index=True, width="stretch", height=400)


def page_fiche():
    c = con()
    ids = [r[0] for r in c.execute("SELECT immoweb_id FROM annonces ORDER BY derniere_observation DESC")]
    if not ids:
        st.title("🏠 Fiche du bien")
        st.info("Aucun bien en base.")
        return
    courant = st.session_state.get("bien")
    libelles = dict(c.execute("SELECT immoweb_id, immoweb_id || ' — ' || COALESCE(commune, '?') || ' — ' || "
                              "COALESCE(CAST(surface_habitable AS INT) || ' m²', 'surface ?') FROM annonces"))
    ident = st.selectbox("Bien", ids, index=ids.index(courant) if courant in ids else 0,
                         format_func=lambda i: libelles.get(i, i))
    st.session_state["bien"] = ident
    res = analyse.analyser(c, ident, P)
    b = res["bien"]
    st.title(f"🏠 {b.get('titre') or 'Maison'} — {b.get('commune') or ''}")
    lien = b.get("url") or ""
    rue = " ".join(x for x in (b.get("rue"), b.get("numero")) if x)
    ville = " ".join(x for x in (b.get("code_postal"), b.get("commune")) if x)
    st.caption(", ".join(x for x in (rue, ville) if x)
               + f" · {b.get('etat') or 'état ?'} · PEB {b.get('peb_lettre') or '?'} · source : {b.get('source') or '?'}"
               + (f" · [annonce]({lien})" if lien.startswith("http") else ""))
    if b.get("source") == "exemple fictif":
        st.warning("Annonce **fictive** (données d'exemple) : les chiffres ne décrivent pas le marché réel.")
    d = res["decision"]
    m = st.columns(6)
    m[0].metric("Prix demandé", eur(b.get("prix_actuel")))
    m[1].metric("Prix/m²", eur(res["prix_m2"]))
    m[2].metric("Écart médian communal", pct(res["statbel"]["ecart"]) if res["statbel"] else "—")
    m[3].metric("Valeur en l'état", eur(res["valeur_en_l_etat"].get("centrale")))
    m[4].metric("Prix d'achat maximum", eur(d["prix_max"]) if d else "—")
    m[5].metric("Décision", d["statut"] if d else "incomplète")
    onglets = st.tabs(["Décision", "Prix & comparables", "Opération", "Risques", "Historique", "Données du bien"])
    with onglets[0]:
        bloc_decision(res)
        if st.button("📌 Enregistrer cette analyse"):
            analyse.enregistrer_analyse(c, res)
            st.success("Analyse enregistrée (onglet Historique).")
    with onglets[1]:
        onglet_prix(res)
    with onglets[2]:
        onglet_operation(c, res)
    with onglets[3]:
        onglet_risques(c, res)
    with onglets[4]:
        onglet_historique(c, res)
    with onglets[5]:
        onglet_donnees(c, res)


# ------------------------------------------------------------------ page : données

def charger_exemples(c):
    annonces.importer_csv(c, RACINE / "data" / "annonces_exemple.csv")
    annonces.maj_statut(c, 14)


def mise_a_jour_automatique(c, force=False):
    """Codes postaux de la zone + médianes Statbel, une fois par session (et au plus tous les N jours)."""
    statbel.importer_codes_postaux_par_defaut(c, RACINE / "data" / "codes_postaux_zone_mons.csv")
    if os.environ.get("IMMO_HORS_LIGNE") and not force:
        return None
    if force or (not st.session_state.get("_statbel_verifie") and statbel.a_mettre_a_jour(c, P)):
        with st.spinner("Mise à jour des prix médians Statbel…"):
            r = statbel.mettre_a_jour(c, P, force=True)
        st.session_state["_statbel_verifie"] = True
        return r
    st.session_state["_statbel_verifie"] = True
    return None


def page_donnees():
    st.title("🗂️ Données")
    c = con()
    n = {"Annonces": "annonces", "Prix observés": "historique_prix", "Communes": "communes",
         "Médianes Statbel": "medianes_statbel", "Codes postaux": "codes_postaux", "Analyses": "analyses"}
    for col, (lib, t) in zip(st.columns(len(n)), n.items()):
        col.metric(lib, c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])

    st.subheader("Prix médians Statbel")
    st.caption("Importés automatiquement par l'application (au démarrage, au plus tous les "
               f"{P['statbel']['frequence_jours']} jours) depuis les sources officielles. L'indice d'évolution des "
               "prix est recalculé à chaque mise à jour.")
    etat = statbel.etat_mise_a_jour(c)
    a, b, d = st.columns(3)
    if etat:
        a.metric("Dernière mise à jour réussie", (etat["date_succes"] or "jamais")[:16].replace("T", " "))
        b.metric("Dernière tentative", etat["date"][:16].replace("T", " "))
        b.caption("✅ réussie" if etat["statut"] == "ok" else "⛔ échec")
        annees = c.execute("SELECT MIN(annee), MAX(annee) FROM medianes_statbel").fetchone()
        d.metric("Années disponibles", f"{annees[0]} – {annees[1]}" if annees[0] else "—")
        if etat["statut"] == "ok":
            st.success(f"Source : {etat['message']} — {etat['lignes']} médianes importées.")
        else:
            st.error("La dernière mise à jour a échoué. Détail : " + (etat["message"] or ""))
    else:
        st.info("Les prix médians Statbel n'ont pas encore été importés.")
    if st.button("🔄 Mettre à jour maintenant"):
        r = mise_a_jour_automatique(c, force=True)
        if r and r["statut"] == "ok":
            st.success(f"{r['lignes']} médianes importées ({r['source']}).")
        st.rerun()
    med = pd.read_sql("SELECT c.nom AS Commune, m.annee AS Année, m.type_bien AS Type, m.mediane AS 'Prix médian (€)', "
                      "m.nb_transactions AS Transactions FROM medianes_statbel m JOIN communes c ON c.nis = m.nis "
                      "JOIN (SELECT DISTINCT commune FROM codes_postaux) z ON z.commune = c.nom "
                      "WHERE m.annee = (SELECT MAX(annee) FROM medianes_statbel) ORDER BY c.nom, m.type_bien", c)
    if not med.empty:
        med["Type"] = med["Type"].map({"maison_2_3_facades": "Maisons 2-3 façades", "maison_4_facades": "Maisons 4 façades",
                                       "maison": "Maisons"}).fillna(med["Type"])
        with st.expander(f"Médianes de la zone ({len(med)} lignes, dernière année)"):
            st.dataframe(med, hide_index=True, width="stretch",
                         column_config={"Prix médian (€)": st.column_config.NumberColumn(format="%.0f")})

    st.subheader("Annonces")
    a, b, d = st.columns(3)
    jours = a.number_input("Retirer les annonces non revues depuis (jours)", value=14, step=1)
    if a.button("Mettre à jour les statuts"):
        st.success(f"{annonces.maj_statut(c, int(jours))} annonces marquées retirées")
    b.download_button("⬇️ Exporter les annonces (CSV)", annonces.tableau_annonces(c).to_csv(index=False),
                      "annonces.csv", "text/csv")
    if d.button("Charger des annonces d'exemple (fictives)"):
        charger_exemples(c)
        st.success("180 annonces fictives chargées (marquées « exemple fictif »).")
        st.rerun()
    f = st.file_uploader("Importer des annonces (CSV d'observations, format de data/annonces_exemple.csv)", type=["csv"])
    if f and st.button("Importer les annonces"):
        tmp = RACINE / "data" / "_import_annonces.csv"
        tmp.write_bytes(f.getvalue())
        st.success(f"{annonces.importer_csv(c, tmp)} observations importées")
        tmp.unlink()


# ------------------------------------------------------------------ page : paramètres

def _pourcent(col, label, valeur, aide=None, maxi=100.0, pas=0.5):
    return col.number_input(label, min_value=0.0, max_value=maxi, value=round(float(valeur) * 100, 3), step=pas,
                            format="%.2f", help=aide) / 100


def _euros(col, label, valeur, aide=None, pas=100.0):
    return col.number_input(label, min_value=0.0, value=float(valeur), step=pas, format="%.0f", help=aide)


def _bouton_enregistrer(cle):
    return st.form_submit_button("💾 Enregistrer", type="primary", key=cle)


def page_parametres():
    st.title("⚙️ Paramètres")
    st.caption("Les modifications s'appliquent immédiatement à toutes les analyses. Les taux fiscaux et les prix des "
               "travaux sont indicatifs : faites-les valider par un notaire ou un fiscaliste, et calibrez-les avec vos devis.")
    D = parametres.defauts()
    onglets = st.tabs(["🎯 Stratégie", "🏛️ Achat et fiscalité", "🏦 Financement", "🔁 Revente", "🛠️ Travaux",
                       "📈 Scénarios", "📊 Estimation"])

    with onglets[0], st.form("strategie"):
        s = P["strategie"]
        a, b = st.columns(2)
        decote = _pourcent(a, "Décote visée sous la valeur du marché (%)", s["decote_cible"],
                           "Prix cible = valeur en l'état × (1 − décote). Règle R2.")
        tol = _pourcent(b, "Tolérance sur la décote (%)", s.get("tolerance_decote", 0),
                        "Ex. 2 % : un achat à 82 % de la valeur reste accepté.")
        a, b, d = st.columns(3)
        pv = _euros(a, "Plus-value nette minimale (€)", s["plus_value_min"], "Dans le scénario prudent. Règle R1.", 1000.0)
        marge = _pourcent(b, "Marge minimale sur le prix de revient (%)", s["marge_min_pct_revient"], "Règle R3.")
        duree = d.number_input("Durée maximale de l'opération (mois)", 1, 60, int(s["duree_max_mois"]), help="Règle R7.")
        rayon = st.slider("Rayon de la zone autour de Mons (km)", 1, 30, int(P["zone"]["rayon_km"]), help="Règle R6.")
        if _bouton_enregistrer("e1"):
            parametres.enregistrer({"strategie": {"decote_cible": decote, "tolerance_decote": tol, "plus_value_min": pv,
                                                  "marge_min_pct_revient": marge, "duree_max_mois": duree},
                                    "zone": {"rayon_km": rayon}})
            st.rerun()

    with onglets[1], st.form("achat"):
        ac, fi = P["acquisition"], P["fiscalite"]
        regimes = {"personne_physique": "Personne physique", "marchand_de_biens": "Marchand de biens (société)"}
        regime = st.radio("Régime par défaut", list(regimes), format_func=regimes.get, horizontal=True,
                          index=list(regimes).index(ac["regime"]))
        a, b, d = st.columns(3)
        dpp = _pourcent(a, "Droits d'enregistrement — personne physique (%)", ac["droits_personne_physique"])
        dmb = _pourcent(b, "Droits d'enregistrement — marchand de biens (%)", ac["droits_marchand_de_biens"])
        notaire = _euros(d, "Honoraires et frais du notaire (€)", ac["frais_notaire_fixes"], "Forfait TVAC.")
        st.markdown("**Impôt sur la plus-value (indicatif)**")
        a, b, d = st.columns(3)
        tpp = _pourcent(a, "Taux plus-value — personne physique (%)", fi["taux_plus_value_pp"],
                        "Plus-value sur immeuble bâti revendu dans les 5 ans.")
        add = _pourcent(b, "Additionnels communaux (%)", fi["additionnels_communaux"])
        isoc = _pourcent(d, "Impôt des sociétés (%)", fi["taux_isoc"])
        if _bouton_enregistrer("e2"):
            parametres.enregistrer({"acquisition": {"regime": regime, "droits_personne_physique": dpp,
                                                    "droits_marchand_de_biens": dmb, "frais_notaire_fixes": notaire},
                                    "fiscalite": {"taux_plus_value_pp": tpp, "additionnels_communaux": add,
                                                  "taux_isoc": isoc}})
            st.rerun()

    with onglets[2], st.form("financement"):
        po = P["portage"]
        forfait = _euros(st, "Coût de portage forfaitaire par mois (€) — 0 pour le calcul détaillé ci-dessous",
                         po.get("portage_mensuel", 0), pas=50.0)
        a, b, d = st.columns(3)
        taux = _pourcent(a, "Taux d'intérêt annuel (%)", po["taux_interet"], pas=0.1)
        quotite = _pourcent(b, "Part financée par emprunt (%)", po["quotite_financee"], pas=5.0)
        acte = _pourcent(d, "Frais de l'acte de crédit (% de l'emprunt)", po["frais_acte_credit"], pas=0.1)
        a, b, d, e = st.columns(4)
        index = a.number_input("Indexation du revenu cadastral", 1.0, 5.0, float(po["indexation_revenu_cadastral"]),
                               0.01, format="%.4f", help="Coefficient de l'année (SPF Finances).")
        prec = _pourcent(b, "Précompte régional (%)", po["taux_precompte_regional"], pas=0.05)
        cent = d.number_input("Centimes additionnels", 0, 10000, int(po["centimes_additionnels"]), 50)
        charges = _euros(e, "Charges mensuelles (€)", po["charges_mensuelles"], "Assurance, énergie, eau…", 10.0)
        if _bouton_enregistrer("e3"):
            parametres.enregistrer({"portage": {"portage_mensuel": forfait, "taux_interet": taux,
                                                "quotite_financee": quotite, "frais_acte_credit": acte,
                                                "indexation_revenu_cadastral": index, "taux_precompte_regional": prec,
                                                "centimes_additionnels": cent, "charges_mensuelles": charges}})
            st.rerun()

    with onglets[3], st.form("revente"):
        r = P["revente"]
        a, b, d = st.columns(3)
        com = _pourcent(a, "Commission d'agence (% HTVA)", r["commission_agence"], pas=0.25)
        tva = _pourcent(b, "TVA sur la commission (%)", r["tva_commission"])
        fixes = _euros(d, "Frais fixes de revente (€)", r["frais_fixes"], "Certificat PEB, contrôle électrique, attestation de sol…", 50.0)
        if _bouton_enregistrer("e4"):
            parametres.enregistrer({"revente": {"commission_agence": com, "tva_commission": tva, "frais_fixes": fixes}})
            st.rerun()

    with onglets[4], st.form("travaux"):
        t = P["travaux"]
        noms = {"rafraichissement": "Rafraîchissement", "renovation_moyenne": "Rénovation moyenne",
                "renovation_lourde": "Rénovation lourde"}
        st.markdown("**Coût au m² par niveau de rénovation (TVAC, hors imprévus)** — utilisé pour le pré-chiffrage")
        tableau = pd.DataFrame([{"Niveau": noms[k], "Bas (€/m²)": v[0], "Haut (€/m²)": v[1],
                                 "Imprévus (%)": t["imprevus"][k] * 100} for k, v in t["niveaux"].items()])
        edite = st.data_editor(tableau, hide_index=True, disabled=["Niveau"], width="stretch",
                               column_config={"Bas (€/m²)": st.column_config.NumberColumn(min_value=0, step=10),
                                              "Haut (€/m²)": st.column_config.NumberColumn(min_value=0, step=10),
                                              "Imprévus (%)": st.column_config.NumberColumn(min_value=0, max_value=100)})
        a, b = st.columns(2)
        duree = a.number_input("Durée par défaut de l'opération (mois)", 1, 36, int(t["duree_defaut_mois"]))
        supp = _euros(b, "Supplément par classe PEB gagnée (€/m²)", t["supplement_par_classe_peb_m2"], pas=5.0)
        if _bouton_enregistrer("e5"):
            cles = list(t["niveaux"])
            parametres.enregistrer({"travaux": {
                "niveaux": {k: [float(edite.iloc[i]["Bas (€/m²)"]), float(edite.iloc[i]["Haut (€/m²)"])]
                            for i, k in enumerate(cles)},
                "imprevus": {k: float(edite.iloc[i]["Imprévus (%)"]) / 100 for i, k in enumerate(cles)},
                "duree_defaut_mois": duree, "supplement_par_classe_peb_m2": supp}})
            st.rerun()

    with onglets[5], st.form("scenarios"):
        sc = P["scenarios"]
        valeurs = {}
        for col, nom, titre in zip(st.columns(2), ("prudent", "optimiste"), ("Scénario prudent", "Scénario optimiste")):
            col.markdown(f"**{titre}**")
            valeurs[nom] = {
                "revente": col.number_input("Prix de revente (± %)", -50.0, 50.0, sc[nom]["revente"] * 100, 1.0,
                                            key=f"r{nom}") / 100,
                "travaux": col.number_input("Coût des travaux (± %)", -50.0, 100.0, sc[nom]["travaux"] * 100, 1.0,
                                            key=f"t{nom}") / 100,
                "mois": col.number_input("Durée (± mois)", -12, 24, int(sc[nom]["mois"]), key=f"m{nom}")}
        if _bouton_enregistrer("e6"):
            parametres.enregistrer({"scenarios": valeurs})
            st.rerun()

    with onglets[6], st.form("estimation"):
        es = P["estimation"]
        a, b, d = st.columns(3)
        nego = _pourcent(a, "Marge de négociation (prix demandé → prix de vente, %)", es["marge_negociation"])
        mini = b.number_input("Nombre minimal de comparables", 1, 50, int(es["min_comparables"]))
        cible = d.selectbox("Classe PEB visée après travaux", travaux.CLASSES_PEB,
                            index=travaux.CLASSES_PEB.index(es["peb_classe_cible_defaut"]))
        st.markdown("**Valeur relative selon l'état du bien** (base « Bon » = 100 %)")
        coefs = st.data_editor(pd.DataFrame([{"État": k, "Valeur (%)": v * 100} for k, v in es["coef_etat"].items()]),
                               hide_index=True, disabled=["État"], width="stretch",
                               column_config={"Valeur (%)": st.column_config.NumberColumn(min_value=10, max_value=200)})
        if _bouton_enregistrer("e7"):
            parametres.enregistrer({"estimation": {
                "marge_negociation": nego, "min_comparables": mini, "peb_classe_cible_defaut": cible,
                "coef_etat": {r["État"]: float(r["Valeur (%)"]) / 100 for _, r in coefs.iterrows()}}})
            st.rerun()

    st.divider()
    a, b = st.columns([3, 1])
    modifies = parametres.surcharges()
    a.caption(f"{sum(len(v) if isinstance(v, dict) else 1 for v in modifies.values())} valeur(s) modifiée(s) par "
              "rapport aux valeurs par défaut." if modifies else "Toutes les valeurs sont celles par défaut.")
    if modifies and b.button("↺ Revenir aux valeurs par défaut"):
        parametres.reinitialiser()
        st.rerun()
    if D != P:
        with st.expander("Voir les valeurs modifiées"):
            lignes = []
            for section, vals in modifies.items():
                for cle, v in (vals.items() if isinstance(vals, dict) else [(section, vals)]):
                    if not isinstance(v, dict):
                        lignes.append({"Section": section, "Paramètre": cle, "Valeur": str(v),
                                       "Par défaut": str(D.get(section, {}).get(cle))})
            st.dataframe(pd.DataFrame(lignes), hide_index=True, width="stretch")


PAGE_BIENS = st.Page(page_biens, title="Biens", icon="📋", default=True)
PAGE_AJOUTER = st.Page(page_ajouter, title="Ajouter un bien", icon="➕")
PAGE_FICHE = st.Page(page_fiche, title="Fiche du bien", icon="🏠")
PAGE_DONNEES = st.Page(page_donnees, title="Données", icon="🗂️")
PAGE_PARAMETRES = st.Page(page_parametres, title="Paramètres", icon="⚙️")

mise_a_jour_automatique(con())
PAGES = {"biens": page_biens, "ajouter": page_ajouter, "fiche": page_fiche, "donnees": page_donnees,
         "parametres": page_parametres}
if st.session_state.get("_page_test") in PAGES:      # utilisé par les tests automatisés (AppTest)
    PAGES[st.session_state["_page_test"]]()
else:
    st.navigation([PAGE_BIENS, PAGE_AJOUTER, PAGE_FICHE, PAGE_DONNEES, PAGE_PARAMETRES]).run()
