-- Migration: 0001_initial
-- Date: 2026-06-16
-- Description: Initial schema - all base tables

CREATE TABLE IF NOT EXISTS schema_version (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL UNIQUE,
    applied_at TEXT NOT NULL DEFAULT (datetime('now')),
    description TEXT
);

CREATE TABLE IF NOT EXISTS firma (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nazov_firmy TEXT,
    ico TEXT,
    dic TEXT,
    ic_dph TEXT,
    adresa TEXT,
    mesto TEXT,
    psc TEXT,
    stat TEXT DEFAULT 'Slovensko',
    je_platitel_dph INTEGER DEFAULT 0,
    uplatnuje_pausalne_vydavky INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prijmy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cislo_dokladu TEXT,
    datum_uhrady TEXT,
    typ_dokladu TEXT,
    odberatel_nazov TEXT,
    odberatel_ico TEXT,
    odberatel_dic TEXT,
    odberatel_ic_dph TEXT,
    odberatel_adresa TEXT,
    odberatel_mesto TEXT,
    odberatel_psc TEXT,
    odberatel_stat TEXT,
    zaklad_dane REAL,
    dph REAL,
    celkova_suma REAL,
    mena TEXT DEFAULT 'EUR',
    je_zahranicny INTEGER DEFAULT 0,
    je_reverzne_zdanenie INTEGER DEFAULT 0,
    je_oslobodene INTEGER DEFAULT 0,
    poznamka TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS vydavky (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cislo_dokladu TEXT,
    datum_uhrady TEXT,
    typ_dokladu TEXT,
    dodavatel_nazov TEXT,
    dodavatel_ico TEXT,
    dodavatel_dic TEXT,
    dodavatel_ic_dph TEXT,
    dodavatel_adresa TEXT,
    dodavatel_mesto TEXT,
    dodavatel_psc TEXT,
    dodavatel_stat TEXT,
    kategoria TEXT,
    zaklad_dane REAL,
    dph REAL,
    celkova_suma REAL,
    mena TEXT DEFAULT 'EUR',
    je_zahranicny INTEGER DEFAULT 0,
    je_reverzne_zdanenie INTEGER DEFAULT 0,
    je_oslobodene INTEGER DEFAULT 0,
    poznamka TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS polozky_dokladu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doklad_id INTEGER,
    typ_dokladu TEXT,
    poradie INTEGER,
    nazov TEXT,
    poznamka TEXT,
    mnozstvo REAL,
    jednotka TEXT,
    jednotkova_cena_bez_dph REAL,
    sadzba_dph REAL,
    zaklad REAL,
    dph REAL,
    celkom REAL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ciselniky (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nazov TEXT NOT NULL,
    prefix TEXT,
    aktualne_cislo INTEGER DEFAULT 0,
    pocet_cislic INTEGER DEFAULT 3,
    rok TEXT,
    je_aktivny INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS kontakty (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    typ TEXT,
    nazov TEXT,
    ico TEXT,
    dic TEXT,
    ic_dph TEXT,
    adresa TEXT,
    mesto TEXT,
    psc TEXT,
    stat TEXT,
    telefon TEXT,
    email TEXT,
    poznamka TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS majetok (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nazov TEXT,
    typ TEXT,
    datum_nadobudnutia TEXT,
    cena_nadobudnutia REAL,
    odpisova_skupina INTEGER,
    sadzba_odpisu REAL,
    datum_zaradenia TEXT,
    datum_vyradenia TEXT,
    poznamka TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS zasoby (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nazov TEXT,
    kod TEXT,
    jednotka TEXT,
    mnozstvo REAL,
    cena_jednotkova REAL,
    celkova_cena REAL,
    poznamka TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pohladavky (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cislo_faktury TEXT,
    odberatel TEXT,
    datum_vystavenia TEXT,
    datum_splatnosti TEXT,
    datum_uhrady TEXT,
    suma REAL,
    uhradena REAL,
    stav TEXT,
    poznamka TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS zavazky (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cislo_faktury TEXT,
    dodavatel TEXT,
    datum_vystavenia TEXT,
    datum_splatnosti TEXT,
    datum_uhrady TEXT,
    suma REAL,
    uhradena REAL,
    stav TEXT,
    poznamka TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS odvody (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    typ TEXT,
    obdobie TEXT,
    datum_splatnosti TEXT,
    suma REAL,
    uhradena REAL,
    stav TEXT,
    poznamka TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jednotky (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skratka TEXT NOT NULL UNIQUE,
    nazov TEXT,
    je_aktivny INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sablony_poloziek (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nazov TEXT NOT NULL,
    typ_dokladu TEXT NOT NULL,
    popis TEXT,
    nazov_polozky TEXT,
    poznamka TEXT,
    mnozstvo REAL DEFAULT 1,
    jednotka TEXT,
    jednotkova_cena_bez_dph REAL DEFAULT 0,
    sadzba_dph REAL DEFAULT 23,
    je_aktivny INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS nastavenia_zobrazenia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kluc TEXT NOT NULL UNIQUE,
    hodnota TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO schema_version (version, description) VALUES ('2026-06-16-0001', 'Initial schema');
