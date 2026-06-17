# Daňová evidencia

Webová aplikácia pre vedenie daňovej evidencie podľa § 6 ods. 11 zákona č. 595/2003 Z. z. o dani z príjmov pre SZČO a živnostníkov na Slovensku.

## Funkcie

### Základné
- **Evidencia príjmov** - záznam všetkých príjmov s číslom dokladu, dátumom, odberateľom, sumou
- **Evidencia výdavkov** - záznam daňových výdavkov s kategorizáciou
- **Pohľadávky** - sledovanie vystavených faktúr a ich úhrad
- **Záväzky** - sledovanie prijatých faktúr a ich úhrad
- **Majetok** - evidencia hmotného a nehmotného majetku
- **Zásoby** - evidencia tovaru a materiálu
- **Odvody** - záznam sociálneho a zdravotného poistenia
- **Adresár** - evidencia kontaktov (odberatelia, dodávatelia)
- **Ročný prehľad** - výpočet základu dane, grafy, podklady pre daňové priznanie

### Pokročilé
- **Účtovný mód** - Zjednodušená evidencia (daňová evidencia) alebo Jednoduché účtovníctvo (FUTURE)
- **Systémové katalógy** - konfigurovateľné DPH sadzby, právne limity, typy dokladov
- **Šablóny položiek** - preddefinované položky pre rýchle vypĺňanie
- **Jednotky** - správa jednotiek merania
- **Číselníky dokladov** - automatická generácia čísel dokladov
- **Import/Export** - JSON export/import s verziovaním schémy
- **Agendy** - viacero firiem v jednej inštalácii

## Distribúcia

### 1. Portable ZIP (Windows)

Stiahnite najnovší release:
```
https://github.com/zdenkor/danova-evidencia/releases
```

1. Rozbaľte ZIP
2. Spustite `start.bat`
3. Otvorte prehliadač na `http://localhost:8080`

### 2. Docker

```bash
# Pull image
docker pull ghcr.io/zdenkor/danova-evidencia:latest

# Spustenie s persistenciou dát
docker run -d \
  -p 8080:8080 \
  -v danova-data:/data \
  -e DB_PATH=/data/danova_evidencia.db \
  ghcr.io/zdenkor/danova-evidencia:latest
```

Alebo cez docker-compose:
```bash
docker-compose up -d
```

### 3. Vývoj (zo zdrojov)

```bash
# Klonovanie repozitára
git clone https://github.com/zdenkor/danova-evidencia.git
cd danova-evidencia

# Vytvorenie virtuálneho prostredia
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Inštalácia závislostí
pip install -r requirements.txt

# Spustenie
python app.py
```

## Technológie

- **Backend**: Python 3.12 + Flask
- **Databáza**: SQLite (súborová, žiadny externý server)
- **Frontend**: Bootstrap 5 + vanilla JavaScript
- **Docker**: Oficiálny image na ghcr.io

## Daňové nastavenia

V časti **Nastavenia → Firma** si nastavte:
- Názov firmy / meno a priezvisko
- IČO, DIČ, IČ DPH
- Adresu
- Účtovný mód (Zjednodušená evidencia / Jednoduché účtovníctvo)
- Či uplatňujete paušálne výdavky (60% z príjmov, max. 20 000 € ročne)
- Či ste platiteľom DPH

V časti **Nastavenia → Systémové katalógy** môžete upravovať:
- DPH sadzby (základná, znížená, super-znížená, oslobodené)
- Právne limity
- Typy dokladov

## Zálohovanie

### SQLite (portable / vývoj)
Všetky dáta sú v súbore `danova_evidencia.db`. Pre zálohovanie skopírujte tento súbor.

### Docker
```bash
# Záloha databázy
docker cp danova-evidencia:/data/danova_evidencia.db ./backup.db

# Obnova
docker cp ./backup.db danova-evidencia:/data/danova_evidencia.db
```

## CI/CD

Projekt používa GitHub Actions:
- **Automatický build ZIP** pri každom tagu `v*`
- **Docker image** pushovaný do `ghcr.io/zdenkor/danova-evidencia`
- **Release** s priloženým ZIP balíkom

## Právne informácie

Táto aplikácia slúži na vedenie daňovej evidencie podľa zákona č. 595/2003 Z. z. o dani z príjmov.
Podnikatelia vedúci daňovú evidenciu nie sú účtovnými jednotkami a nepodliehajú povinnostiam podľa zákona o účtovníctve.

## Licencia

MIT License - voľné použitie pre osobné aj komerčné účely.

## Autor

Vytvorené: Jún 2026
GitHub: https://github.com/zdenkor/danova-evidencia
