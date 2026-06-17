-- Migration: 2026-06-17-0010
-- Date: 2026-06-17
-- Description: Add orders (objednavky) module

-- Tabuľka objednávok
CREATE TABLE IF NOT EXISTS objednavky (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cislo_objednavky TEXT NOT NULL,
    datum_vystavenia DATE NOT NULL,
    datum_platnosti DATE,
    odberatel_id INTEGER,
    odberatel_nazov TEXT,
    odberatel_ico TEXT,
    odberatel_dic TEXT,
    odberatel_ic_dph TEXT,
    odberatel_adresa TEXT,
    odberatel_mesto TEXT,
    odberatel_psc TEXT,
    odberatel_stat TEXT DEFAULT 'Slovensko',
    dodavatel_id INTEGER,
    dodavatel_nazov TEXT,
    dodavatel_ico TEXT,
    dodavatel_dic TEXT,
    dodavatel_ic_dph TEXT,
    dodavatel_adresa TEXT,
    dodavatel_mesto TEXT,
    dodavatel_psc TEXT,
    dodavatel_stat TEXT DEFAULT 'Slovensko',
    stav TEXT DEFAULT 'nova' CHECK(stav IN ('nova', 'potvrdena', 'vybavena', 'stornovana')),
    suma DECIMAL(10,2) DEFAULT 0,
    dph DECIMAL(10,2) DEFAULT 0,
    zaklad_dane DECIMAL(10,2) DEFAULT 0,
    celkova_suma DECIMAL(10,2) DEFAULT 0,
    mena TEXT DEFAULT 'EUR',
    poznamka TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Položky objednávky
CREATE TABLE IF NOT EXISTS objednavky_polozky (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objednavka_id INTEGER NOT NULL,
    nazov TEXT NOT NULL,
    poznamka TEXT,
    mnozstvo DECIMAL(10,2) DEFAULT 1,
    jednotka TEXT DEFAULT 'ks',
    jednotkova_cena_bez_dph DECIMAL(10,2) NOT NULL,
    sadzba_dph TEXT DEFAULT '23',
    zaklad_dane DECIMAL(10,2) NOT NULL,
    dph DECIMAL(10,2) DEFAULT 0,
    celkova_suma DECIMAL(10,2) NOT NULL,
    poradie INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (objednavka_id) REFERENCES objednavky(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_objednavky_stav ON objednavky(stav);
CREATE INDEX IF NOT EXISTS idx_objednavky_datum ON objednavky(datum_vystavenia);

INSERT OR IGNORE INTO schema_version (version, description) VALUES ('2026-06-17-0010', 'Add orders (objednavky) module');
