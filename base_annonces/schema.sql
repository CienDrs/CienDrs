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
