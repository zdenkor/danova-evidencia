# TODO - Daňová evidencia

## Dokončené ✅

- Auto-fill and hide Dodávateľ/Odberateľ sections
- Update DPH rates to 23/19/5/0
- Remove number input spinners
- Add Poznámka field under item name
- Create units (jednotky) management in settings
- Fix DPH calculation to update in real-time (oninput)
- Fix dark mode table colors
- Add alternating row colors (striped)
- Fix automatic document number generation
- Ensure units management accessible from Settings
- Fix editor errors in pridat_prijem.html (Jinja2 in JS)
- Rename Jednotky merania to Jednotky
- Fix pridanie položky (window.jednotkyData scope)
- Compact table layout for item rows
- Update upravit_prijem.html pridajPolozku() to match new features
- Update upravit_vydavok.html pridajPolozku() to match new features
- Fix table header duplicate # column in upravit forms
- Browser test all changes
- Rename Pohodlná to Komfortná in display settings
- Add per-component font size settings (poznámky, tabuľky, hlavičky, formuláre)
- Mark default values in display settings dropdowns
- Fix inline font-size styles overriding per-component CSS
- Change default density from Komfortná to Normálna
- Fix status bar vertical alignment (center height)
- Fix automatic document number generation (wrong column names in JS)
- Rename Číselníky dokladov to Číselníky in UI
- Create database schema for šablóny (templates table)
- Create šablóny management page in settings
- Add šablóna selection icon in item rows (left of delete button)
- Implement šablóna application to fill row fields

## Plánované (budúcnosť) 📋

### Databázová architektúra
- [ ] [FUTURE] Database schema versioning (schema_version table)
- [ ] [FUTURE] Migration system (migrations/ folder with numbered scripts)
- [ ] [FUTURE] Configurable system catalogs (DPH rates, legal thresholds in DB)
- [ ] [FUTURE] Conditional fields based on effective date (required only for new records)
- [ ] [FUTURE] Versioned import/export format with schema compatibility checks
- [ ] [FUTURE] Data integrity: store actual values, not references, for legal compliance

---

*Posledná aktualizácia: 2026-06-16*
