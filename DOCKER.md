# Daňová evidencia - Docker

## Rýchly štart

```bash
# Build a spustenie
docker-compose up -d

# Aplikácia beží na http://localhost:8080
```

## Premenné prostredia

| Premenná | Popis | Default |
|----------|-------|---------|
| `DB_PATH` | Cesta k databáze (vnútri kontajnera) | `/data/danova_evidencia.db` |
| `FLASK_PORT` | Port na ktorom beží Flask | `8080` |
| `FLASK_HOST` | Host na ktorom počúva Flask | `0.0.0.0` |

## Volume

Databáza sa ukladá do volume `danova-evidencia-data`, ktorý je mimo zdrojového kódu:

```yaml
volumes:
  - danova-evidencia-data:/data
```

## Manuálny build

```bash
docker build -t danova-evidencia .
docker run -d -p 8080:8080 -v danova-evidencia-data:/data danova-evidencia
```

## Export/Import dát

Databáza je SQLite súbor v `/data/danova_evidencia.db`. Môžete ju zálohovať:

```bash
docker cp danova-evidencia:/data/danova_evidencia.db ./backup.db
```
