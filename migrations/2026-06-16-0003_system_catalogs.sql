-- Migration: 2026-06-16-0003
-- Date: 2026-06-16
-- Description: Configurable system catalogs

CREATE TABLE IF NOT EXISTS system_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kategoria TEXT NOT NULL,
    kod TEXT NOT NULL,
    nazov TEXT NOT NULL,
    hodnota TEXT,
    hodnota_cislo REAL,
    popis TEXT,
    je_aktivny INTEGER DEFAULT 1,
    platnost_od TEXT,
    platnost_do TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_system_catalog_kategoria_kod 
ON system_catalog(kategoria, kod);

-- DPH rates
INSERT OR IGNORE INTO system_catalog (kategoria, kod, nazov, hodnota_cislo, popis, platnost_od) VALUES
('dph_sadzba', 'zakladna', 'Základná', 23, 'Základná sadzba DPH', '2024-01-01'),
('dph_sadzba', 'znizena', 'Znížená', 19, 'Znížená sadzba DPH', '2024-01-01'),
('dph_sadzba', 'super_znizena', 'Super-znížená', 5, 'Super-znížená sadzba DPH', '2024-01-01'),
('dph_sadzba', 'oslobodene', 'Oslobodené', 0, 'Oslobodené od DPH', '2024-01-01');

-- Legal thresholds
INSERT OR IGNORE INTO system_catalog (kategoria, kod, nazov, hodnota_cislo, popis, platnost_od) VALUES
('limit', 'pausalne_vydavky_max', 'Maximálne paušálne výdavky', 20000, 'Maximálna suma paušálnych výdavkov (60% z príjmov)', '2024-01-01'),
('limit', 'pausalne_vydavko_percento', 'Percento paušálnych výdavkov', 60, 'Percento paušálnych výdavkov z príjmov', '2024-01-01'),
('limit', 'dph_registracia', 'Limit pre registráciu DPH', 49920, 'Obrat pre povinnú registráciu k DPH (12 mesiacov)', '2024-01-01');

-- Document types for income
INSERT OR IGNORE INTO system_catalog (kategoria, kod, nazov, popis, je_aktivny) VALUES
('typ_dokladu_prijem', 'faktura_vydana', 'Faktúra vydaná', 'Vydaná faktúra (príjem)', 1),
('typ_dokladu_prijem', 'pokladnicny_doklad', 'Pokladničný doklad', 'Pokladničný doklad (príjem)', 1),
('typ_dokladu_prijem', 'bankovy_vypis', 'Bankový výpis', 'Bankový výpis (príjem)', 1),
('typ_dokladu_prijem', 'interny_doklad', 'Interný doklad', 'Interný doklad (príjem)', 1),
('typ_dokladu_prijem', 'iny', 'Iný doklad', 'Iný doklad (príjem)', 1);

-- Document types for expense
INSERT OR IGNORE INTO system_catalog (kategoria, kod, nazov, popis, je_aktivny) VALUES
('typ_dokladu_vydavok', 'faktura_prijata', 'Faktúra prijatá', 'Prijatá faktúra (výdavok)', 1),
('typ_dokladu_vydavok', 'pokladnicny_doklad', 'Pokladničný doklad', 'Pokladničný doklad (výdavok)', 1),
('typ_dokladu_vydavok', 'bankovy_vypis', 'Bankový výpis', 'Bankový výpis (výdavok)', 1),
('typ_dokladu_vydavok', 'interny_doklad', 'Interný doklad', 'Interný doklad (výdavok)', 1),
('typ_dokladu_vydavok', 'iny', 'Iný doklad', 'Iný doklad (výdavok)', 1);

INSERT OR IGNORE INTO schema_version (version, description) VALUES ('2026-06-16-0003', 'Configurable system catalogs');
