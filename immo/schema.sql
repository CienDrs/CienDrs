-- Base des annonces de maisons à vendre (Immoweb) — région de Mons
-- SQLite. Les dates sont au format ISO AAAA-MM-JJ.

CREATE TABLE IF NOT EXISTS annonces (
    immoweb_id          TEXT PRIMARY KEY,          -- code de l'annonce Immoweb
    url                 TEXT,
    type_bien           TEXT DEFAULT 'maison',
    rue                 TEXT,
    numero              TEXT,
    code_postal         TEXT,
    commune             TEXT,
    latitude            REAL,
    longitude           REAL,
    adresse_precise     INTEGER DEFAULT 0,         -- 1 si l'adresse exacte est publiée
    distance_mons_km    REAL,                      -- distance à la Grand-Place de Mons
    surface_habitable   REAL,                      -- m²
    surface_terrain     REAL,                      -- m²
    chambres            INTEGER,
    salles_de_bain      INTEGER,
    facades             INTEGER,
    annee_construction  INTEGER,
    etat                TEXT,                      -- état du bâtiment selon Immoweb
    peb_lettre          TEXT,                      -- A++ … G
    peb_kwh_m2          REAL,                      -- consommation spécifique (kWh/m²/an)
    description         TEXT,                      -- sans téléphones ni e-mails (RGPD)
    titre               TEXT,
    province            TEXT,
    adresse_approximative INTEGER,                 -- 1 si Immoweb signale une localisation approximative
    revenu_cadastral    REAL,
    peb_reference       TEXT,                      -- numéro unique du certificat PEB
    chauffage           TEXT,
    cuisine             TEXT,
    surface_jardin      REAL,
    surface_terrasse    REAL,
    nb_etages           INTEGER,
    cave                INTEGER,
    grenier             INTEGER,
    vendeur_type        TEXT,                      -- agence / particulier
    prix_ancien_immoweb REAL,                      -- ancien prix affiché par Immoweb (baisse signalée)
    nb_vues             INTEGER,
    nb_favoris          INTEGER,
    source              TEXT,                      -- immoweb / texte / manuel / csv
    date_publication    TEXT,
    premiere_observation TEXT NOT NULL,
    derniere_observation TEXT NOT NULL,
    date_retrait        TEXT,                      -- NULL = annonce toujours en ligne
    derniere_maj_detail TEXT                       -- dernière lecture de la page détaillée (collecte)
);

-- Une ligne à chaque fois qu'un prix différent est observé (historique des prix demandés)
CREATE TABLE IF NOT EXISTS historique_prix (
    immoweb_id      TEXT NOT NULL REFERENCES annonces(immoweb_id) ON DELETE CASCADE,
    date_observation TEXT NOT NULL,
    prix            REAL NOT NULL,
    PRIMARY KEY (immoweb_id, date_observation)
);

-- Indice d'évolution des prix des maisons par zone et par trimestre (ex. Statbel)
CREATE TABLE IF NOT EXISTS indices_prix (
    zone    TEXT NOT NULL,       -- ex. 'Hainaut', 'Wallonie', 'Mons'
    periode TEXT NOT NULL,       -- 'AAAA-Tn'
    indice  REAL NOT NULL,
    source  TEXT,
    PRIMARY KEY (zone, periode)
);

CREATE INDEX IF NOT EXISTS idx_annonces_commune ON annonces(commune);
CREATE INDEX IF NOT EXISTS idx_annonces_surface ON annonces(surface_habitable);

-- Données enrichies (géocodage, risques WalOnMap…) : chaque valeur garde sa source et sa date
CREATE TABLE IF NOT EXISTS enrichissement (
    immoweb_id  TEXT NOT NULL REFERENCES annonces(immoweb_id) ON DELETE CASCADE,
    cle         TEXT NOT NULL,
    valeur      TEXT,                -- JSON ; NULL = source indisponible, relançable
    source      TEXT,
    date        TEXT NOT NULL,
    PRIMARY KEY (immoweb_id, cle)
);

-- Communes et prix médians Statbel
CREATE TABLE IF NOT EXISTS communes (
    nis         TEXT PRIMARY KEY,
    nom         TEXT NOT NULL,
    nom_normalise TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS codes_postaux (
    code_postal TEXT NOT NULL,
    localite    TEXT,
    commune     TEXT NOT NULL,         -- nom de la commune (fusionnée)
    PRIMARY KEY (code_postal, localite)
);
CREATE TABLE IF NOT EXISTS medianes_statbel (
    nis         TEXT NOT NULL,
    annee       INTEGER NOT NULL,
    periode     TEXT NOT NULL,         -- 'A' (année) ou 'T1'…'T4' / 'S1', 'S2'
    type_bien   TEXT NOT NULL,         -- 'maison' (2-3 façades, 4 façades, toutes)
    mediane     REAL NOT NULL,
    nb_transactions INTEGER,
    source      TEXT,
    PRIMARY KEY (nis, annee, periode, type_bien)
);

-- Hypothèses d'opération saisies pour un bien, et analyses enregistrées (versionnées)
CREATE TABLE IF NOT EXISTS hypotheses_operation (
    immoweb_id  TEXT PRIMARY KEY REFERENCES annonces(immoweb_id) ON DELETE CASCADE,
    hypotheses  TEXT NOT NULL,         -- JSON
    date        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS analyses (
    immoweb_id  TEXT NOT NULL REFERENCES annonces(immoweb_id) ON DELETE CASCADE,
    date        TEXT NOT NULL,
    version_modele TEXT NOT NULL,
    resultat    TEXT NOT NULL,         -- JSON : estimations, bilan, décision
    PRIMARY KEY (immoweb_id, date, version_modele)
);

-- Mises à jour automatiques des sources externes (Statbel…)
CREATE TABLE IF NOT EXISTS mises_a_jour (
    source      TEXT PRIMARY KEY,
    date        TEXT NOT NULL,          -- date et heure ISO de la dernière tentative
    statut      TEXT NOT NULL,          -- 'ok' ou 'erreur'
    lignes      INTEGER,
    message     TEXT,
    date_succes TEXT                    -- dernière mise à jour réussie
);

-- Liens des photos d'une annonce (affichées depuis le site d'origine, jamais redistribuées)
CREATE TABLE IF NOT EXISTS photos (
    immoweb_id    TEXT NOT NULL REFERENCES annonces(immoweb_id) ON DELETE CASCADE,
    ordre         INTEGER NOT NULL,
    url_miniature TEXT,
    url_grande    TEXT,
    PRIMARY KEY (immoweb_id, ordre)
);

-- Chantier composé poste par poste pour un bien (onglet « Estimation des travaux »)
CREATE TABLE IF NOT EXISTS travaux_bien (
    immoweb_id    TEXT PRIMARY KEY REFERENCES annonces(immoweb_id) ON DELETE CASCADE,
    configuration TEXT NOT NULL,       -- JSON : lignes (poste, quantité, niveau ou prix saisi), imprévus, durée
    date          TEXT NOT NULL
);

-- Journal des collectes automatiques
CREATE TABLE IF NOT EXISTS collectes (
    debut       TEXT PRIMARY KEY,
    fin         TEXT,
    source      TEXT,
    statut      TEXT,                  -- 'ok', 'erreur', 'bloquée'
    vues        INTEGER,
    nouvelles   INTEGER,
    modifiees   INTEGER,
    retirees    INTEGER,
    erreurs     TEXT
);
