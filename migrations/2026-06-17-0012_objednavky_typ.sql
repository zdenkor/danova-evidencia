-- Migration: 2026-06-17-0012
-- Date: 2026-06-17
-- Description: Add order type (prijata/vystavena) to objednavky

-- Pridať stĺpec typ do objednávok
ALTER TABLE objednavky ADD COLUMN typ TEXT DEFAULT 'prijata' CHECK(typ IN ('prijata', 'vystavena'));

-- Aktualizovať existujúce objednávky - nastaviť prijata ako default
UPDATE objednavky SET typ = 'prijata' WHERE typ IS NULL;

-- Zaznamenať verziu schémy
INSERT OR REPLACE INTO schema_version (version, description, applied_at)
VALUES ('2026-06-17-0012', 'Add order type (prijata/vystavena)', datetime('now'));
