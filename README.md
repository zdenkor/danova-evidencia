# Daňová evidencia

Webová aplikácia pre vedenie daňovej evidencie podľa § 6 ods. 11 zákona č. 595/2003 Z. z. o dani z príjmov pre SZČO a živnostníkov na Slovensku.

## Na čo slúži

Aplikácia slúži na evidenciu príjmov a výdavkov, sledovanie pohľadávok a záväzkov, evidenciu majetku a zásob, záznam odvodov na sociálne a zdravotné poistenie, vedenie adresára kontaktov a prípravu podkladov pre daňové priznanie.

## Ako spustiť

### Windows (portable)

1. Stiahnite ZIP z [Releases](https://github.com/zdenkor/danova-evidencia/releases)
2. Rozbaľte ZIP súbor
3. Spustite `start.bat`
4. Otvorte prehliadač na `http://localhost:8080`

### Docker

```bash
docker-compose up -d
```

### Vývoj

```bash
pip install -r requirements.txt
python app.py
```

## Zálohovanie

Dáta sú v súbore `danova_evidencia.db` a v priečinku `agendy/`. Pre zálohovanie skopírujte tieto súbory.

## Právne informácie

Táto aplikácia slúži na vedenie daňovej evidencie podľa zákona č. 595/2003 Z. z. o dani z príjmov.
Podnikatelia vedúci daňovú evidenciu nie sú účtovnými jednotkami a nepodliehajú povinnostiam podľa zákona o účtovníctve.

## Licencia

MIT License - voľné použitie pre osobné aj komerčné účely.

## Autor

Vytvorené: Jún 2026
GitHub: https://github.com/zdenkor/danova-evidencia
