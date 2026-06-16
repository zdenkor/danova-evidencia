-- Migration: 2026-06-16-0002
-- Date: 2026-06-16
-- Description: Add sablony_poloziek table

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

-- Default templates for prijem
INSERT INTO sablony_poloziek (nazov, typ_dokladu, popis, nazov_polozky, mnozstvo, jednotka, jednotkova_cena_bez_dph, sadzba_dph) VALUES
('Služba - konzultácia', 'prijem', 'Konzultačná služba', 'Konzultácia', 1, 'hod', 50, 23),
('Služba - programovanie', 'prijem', 'Programátorská služba', 'Programovanie', 1, 'hod', 80, 23),
('Tovar - štandardný', 'prijem', 'Predaj tovaru', 'Tovar', 1, 'ks', 25, 23);

-- Default templates for vydavok
INSERT INTO sablony_poloziek (nazov, typ_dokladu, popis, nazov_polozky, mnozstvo, jednotka, jednotkova_cena_bez_dph, sadzba_dph) VALUES
('Materiál - kancelária', 'vydavok', 'Kancelárske potreby', 'Kancelárske potreby', 1, 'ks', 15, 23),
('Služba - účtovníctvo', 'vydavok', 'Účtovné služby', 'Účtovníctvo', 1, 'mes', 150, 23),
('Energia - elektrina', 'vydavok', 'Elektrická energia', 'Elektrina', 1, 'mes', 100, 23);

INSERT OR IGNORE INTO schema_version (version, description) VALUES ('2026-06-16-0002', 'Add sablony_poloziek table');
