# Verzie

Formát verzie: `RRRR-MM-DD-xxxx`
- RRRR-MM-DD: dátum vydania
- xxxx: poradové číslo verzie (začína 0001, každá zmena +1)

---

## 2026-06-17-0006

### Pridané
- Verzovanie aplikácie s changelogom
- Git tagy pre jednotlivé verzie

---

## 2026-06-16-0005

### Pridané
- Data integrity - ukladanie aktuálnych hodnôt priamo do dokladov
- `ulozit_dph_sadzby_do_dokladu()` - ukladá DPH sadzby pri vytvorení dokladu
- `ulozit_kontakt_info_do_dokladu()` - ukladá snapshot kontaktu pri vytvorení dokladu
- Historické sledovanie zmien cez `historicka_hodnota` tabuľku

---

## 2026-06-16-0004

### Pridané
- Verzovaný import/export formát s kontrolou kompatibility schémy
- `import_export.py` modul s formátom JSON
- Export s metadátami (verzia, dátum, hash schémy)
- Validácia importu s varovaniami pri nezhode schémy
- Režimy importu: Merge a Replace
- UI pre import/export v nastaveniach
- API endpoint `/api/validate-import` pre predbežnú kontrolu

---

## 2026-06-16-0003

### Pridané
- Konfigurovateľné systémové katalógy
- `system_catalog` tabuľka pre DPH sadzby, právne limity, typy dokladov
- Správcovská stránka `/system-catalog` s editáciou
- API endpointy `/api/dph-sadzby` a `/api/typy-dokladov`
- Predvolené hodnoty: DPH 23%, 19%, 5%, paušálne výdavky 60%/20000€

---

## 2026-06-16-0002

### Pridané
- Šablóny položiek dokladov
- `sablony_poloziek` tabuľka s preddefinovanými položkami
- Tlačidlá šablón v formulároch príjmov/výdavkov
- Správa šablón cez `/sablony`

---

## 2026-06-16-0001

### Pridané
- Verzovanie databázovej schémy
- Systém migrácií s číslovanými SQL skriptami
- `schema_version` tabuľka pre sledovanie aplikovaných migrácií
- Automatická migrácia pri štarte aplikácie
- Zobrazenie verzie DB v pätičke

---

## Základná verzia (pred verzovaním)

### Funkcie
- Evidencia príjmov a výdavkov
- Majetok, zásoby, pohľadávky, záväzky, odvody
- Ročný prehľad s grafmi
- Číselníky dokladov s automatickým číslovaním
- Adresár kontaktov s doručovacími adresami, kontaktnými osobami, bankovými účtami
- Agendy (viac firiem v jednej inštalácii)
- Nastavenia zobrazenia (téma, hustota, formát dátumu/čísla/meny, písmo)
- Vyhľadávanie firiem v ORSR
- Jednotky merania
