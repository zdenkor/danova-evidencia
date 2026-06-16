-- Migration: 2026-06-16-0004
-- Date: 2026-06-16
-- Description: Conditional fields based on effective date

-- Note: ALTER TABLE ADD COLUMN is handled in Python to check for existing columns
-- See database.py init_db() for column additions

-- Table for tracking historical values (for legal compliance)
CREATE TABLE IF NOT EXISTS historicka_hodnota (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tabulka TEXT NOT NULL,
    stlpec TEXT NOT NULL,
    zaznam_id INTEGER NOT NULL,
    hodnota TEXT,
    hodnota_cislo REAL,
    platnost_od TEXT,
    platnost_do TEXT,
    dovody_zmeny TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_historicka_hodnota_lookup 
ON historicka_hodnota(tabulka, stlpec, zaznam_id);

INSERT OR IGNORE INTO schema_version (version, description) VALUES ('2026-06-16-0004', 'Conditional fields based on effective date');
