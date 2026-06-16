# Daňová evidencia

Webová aplikácia pre vedenie daňovej evidencie podľa § 6 ods. 11 zákona č. 595/2003 Z. z. o dani z príjmov pre SZČO a živnostníkov na Slovensku.

## Funkcie

- **Evidencia príjmov** - záznam všetkých príjmov s číslom dokladu, dátumom, odberateľom, sumou
- **Evidencia výdavkov** - záznam daňových výdavkov s kategorizáciou
- **Pohľadávky** - sledovanie vystavených faktúr a ich úhrad
- **Záväzky** - sledovanie prijatých faktúr a ich úhrad
- **Majetok** - evidencia hmotného a nehmotného majetku
- **Zásoby** - evidencia tovaru a materiálu
- **Odvody** - záznam sociálneho a zdravotného poistenia
- **Ročný prehľad** - výpočet základu dane, grafy, podklady pre daňové priznanie

## Technológie

- **Backend**: Python + Flask
- **Databáza**: SQLite (súborová, žiadny externý server)
- **Frontend**: Bootstrap 5 + Chart.js
- **Pripojenie**: Webový prehliadač (localhost)

## Inštalácia a spustenie

### 1. Požiadavky
- Python 3.8 alebo novší

### 2. Inštalácia závislostí
```bash
pip install Flask
```

### 3. Spustenie aplikácie
```bash
python app.py
```

### 4. Otvorenie v prehliadači
```
http://127.0.0.1:8080
```

## Daňové nastavenia

V časti **Nastavenia** si nastavte:
- Názov firmy / meno a priezvisko
- IČO, DIČ, IČ DPH
- Adresu
- Či uplatňujete paušálne výdavky (60% z príjmov, max. 20 000 € ročne)
- Či ste platiteľom DPH

## Zálohovanie

Všetky dáta sú uložené v súbore `danova_evidencia.db` v priečinku aplikácie.
Pre zálohovanie jednoducho skopírujte tento súbor.

## Právne informácie

Táto aplikácia slúži na vedenie daňovej evidencie podľa zákona č. 595/2003 Z. z. o dani z príjmov.
Podnikatelia vedúci daňovú evidenciu nie sú účtovnými jednotkami a nepodliehajú povinnostiam podľa zákona o účtovníctve.

## Autor

Vytvorené: Jún 2026
