from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from database import (get_db, init_db, set_db_path, DEFAULT_DB_PATH, get_agendy_dir,
                      get_agendy, get_aktivna_agenda, vytvorit_agendu, otvorit_agendu,
                      exportovat_agendu, importovat_agendu, zmazat_agendu, resetnut_agendu,
                      get_zobrazenie, update_zobrazenie,
                      get_jednotky, pridat_jednotku, upravit_jednotku, zmazat_jednotku,
                      get_sablony, get_sablona, pridat_sablonu, upravit_sablonu, zmazat_sablonu,
                      get_prijem_polozky, pridat_prijem_polozku, upravit_prijem_polozku, zmazat_prijem_polozku,
                      get_vydavok_polozky, pridat_vydavok_polozku, upravit_vydavok_polozku, zmazat_vydavok_polozku,
                      get_system_catalog, get_system_catalog_item, get_dph_sadzby,
                      get_typy_dokladov_prijem, get_typy_dokladov_vydavok, get_legal_limit,
                      update_system_catalog, ulozit_dph_sadzby_do_dokladu, ulozit_kontakt_info_do_dokladu)
from migrations import get_current_version
from import_export import export_data, import_data, validate_import
from datetime import datetime, date
import calendar
import re
import requests
from bs4 import BeautifulSoup
import os
import json

app = Flask(__name__)
app.secret_key = 'danova-evidencia-secret-key-2026'

# Inicializácia databázy pri štarte
init_db()


@app.before_request
def before_request():
    """Pred každým requestom skontroluje či aktívna agenda má inicializovanú tabuľku zobrazenie."""
    try:
        db = get_db()
        cursor = db.cursor()
        # Skontrolovať či existuje tabuľka zobrazenie
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='zobrazenie'")
        if not cursor.fetchone():
            # Vytvoriť tabuľku zobrazenie
            cursor.execute('''
                CREATE TABLE zobrazenie (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tema TEXT DEFAULT 'light',
                    hustota TEXT DEFAULT 'comfortable',
                    format_datumu TEXT DEFAULT 'sk',
                    format_cisla TEXT DEFAULT 'sk',
                    format_meny TEXT DEFAULT 'sk',
                    jazyk TEXT DEFAULT 'sk',
                    font_family TEXT DEFAULT '',
                    font_size TEXT DEFAULT '16',
                    font_size_nadpisy TEXT DEFAULT '',
                    font_size_tabulky TEXT DEFAULT '',
                    font_size_formulare TEXT DEFAULT '',
                    font_size_poznamky TEXT DEFAULT '0.85',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute("INSERT INTO zobrazenie (tema, hustota) VALUES ('light', 'normal')")
            db.commit()
        else:
            # Pridať nové stĺpce ak neexistujú
            cursor.execute("PRAGMA table_info(zobrazenie)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'font_size_nadpisy' not in columns:
                cursor.execute("ALTER TABLE zobrazenie ADD COLUMN font_size_nadpisy TEXT DEFAULT ''")
            if 'font_size_tabulky' not in columns:
                cursor.execute("ALTER TABLE zobrazenie ADD COLUMN font_size_tabulky TEXT DEFAULT ''")
            if 'font_size_formulare' not in columns:
                cursor.execute("ALTER TABLE zobrazenie ADD COLUMN font_size_formulare TEXT DEFAULT ''")
            if 'font_size_poznamky' not in columns:
                cursor.execute("ALTER TABLE zobrazenie ADD COLUMN font_size_poznamky TEXT DEFAULT '0.85'")
            db.commit()
        db.close()
    except Exception:
        pass


# ==================== SLOVENSKÉ FORMÁTOVANIE ====================

MESIACE_SK = ['', 'január', 'február', 'marec', 'apríl', 'máj', 'jún',
              'júl', 'august', 'september', 'október', 'november', 'december']

MESIACE_SK_KRATKE = ['', 'jan', 'feb', 'mar', 'apr', 'máj', 'jún',
                     'júl', 'aug', 'sep', 'okt', 'nov', 'dec']


def format_mena(hodnota, mena='EUR'):
    """Formátuje sumu podľa nastavení zobrazenia."""
    if hodnota is None:
        hodnota = 0
    try:
        z = get_zobrazenie()
        fmt = z.get('format_meny', 'sk')
    except:
        fmt = 'sk'

    num = float(hodnota)
    if fmt == 'en':
        text = f"{num:,.2f}"
        return mena + text
    elif fmt == 'symbol':
        text = f"{num:,.2f}"
        text = text.replace(',', 'X').replace('.', ',').replace('X', ' ')
        return text + ' ' + ('€' if mena == 'EUR' else mena)
    else:  # sk
        text = f"{num:,.2f}"
        text = text.replace(',', 'X').replace('.', ',').replace('X', ' ')
        return text + ' ' + mena


def format_datum(datum_str):
    """Formátuje dátum podľa nastavení zobrazenia."""
    if not datum_str:
        return ''
    try:
        z = get_zobrazenie()
        fmt = z.get('format_datumu', 'sk')
    except:
        fmt = 'sk'

    try:
        if isinstance(datum_str, str):
            try:
                d = datetime.strptime(datum_str, '%Y-%m-%d')
            except ValueError:
                d = datetime.strptime(datum_str, '%Y-%m-%d %H:%M:%S')
        else:
            d = datum_str

        if fmt == 'iso':
            return d.strftime('%Y-%m-%d')
        elif fmt == 'eu':
            return d.strftime('%d. %m. %Y')
        elif fmt == 'us':
            return d.strftime('%m/%d/%Y')
        elif fmt == 'sk_long':
            return f"{d.day}. {MESIACE_SK[d.month]} {d.year}"
        else:  # sk
            return f"{d.day}. {MESIACE_SK_KRATKE[d.month]} {d.year}"
    except:
        return str(datum_str)


def format_datum_dlhy(datum_str):
    """Formátuje dátum do dlhého slovenského formátu."""
    if not datum_str:
        return ''
    try:
        if isinstance(datum_str, str):
            try:
                d = datetime.strptime(datum_str, '%Y-%m-%d')
            except ValueError:
                d = datetime.strptime(datum_str, '%Y-%m-%d %H:%M:%S')
        else:
            d = datum_str
        return f"{d.day}. {MESIACE_SK[d.month]} {d.year}"
    except:
        return str(datum_str)


# ==================== CONTEXT PROCESSORS ====================

@app.context_processor
def inject_globals():
    """Vloží globálne premenné do všetkých šablón."""
    # Aktuálna agenda
    agenda = get_aktivna_agenda()
    nazov_firmy = ''
    firma = None
    if agenda:
        nazov_firmy = agenda['nazov']
        # Načítať detaily firmy z nastavení aktuálnej agendy
        try:
            db = get_db()
            firma = db.execute('SELECT nazov_firmy, ico, dic, ic_dph, adresa, mesto, psc FROM nastavenia LIMIT 1').fetchone()
            db.close()
        except:
            firma = None
    else:
        # Fallback - skúsiť načítať z nastavení
        try:
            db = get_db()
            nastavenia = db.execute('SELECT nazov_firmy, ico, dic, ic_dph, adresa, mesto, psc FROM nastavenia LIMIT 1').fetchone()
            db.close()
            if nastavenia:
                nazov_firmy = nastavenia['nazov_firmy'] or 'Neznáma firma'
                firma = nastavenia
        except:
            nazov_firmy = 'Neznáma firma'

    # Aktuálny dátum zo session alebo dnešný
    aktualny_datum = session.get('aktualny_datum', datetime.now().strftime('%Y-%m-%d'))

    # Nastavenia zobrazenia
    zobrazenie = get_zobrazenie()

    # Database version
    db_verzia = get_current_version(DEFAULT_DB_PATH)

    return {
        'now': datetime.now(),
        'aktualna_agenda': agenda,
        'nazov_firmy': nazov_firmy,
        'firma': firma,
        'aktualny_datum': aktualny_datum,
        'format_mena': format_mena,
        'format_datum': format_datum,
        'format_datum_dlhy': format_datum_dlhy,
        'MESIACE_SK': MESIACE_SK,
        'MESIACE_SK_KRATKE': MESIACE_SK_KRATKE,
        'zobrazenie': zobrazenie,
        'db_verzia': db_verzia
    }


# ==================== POMOCNÉ FUNKCIE PRE ČÍSELNÍKY ====================

def generuj_cislo_dokladu(ciselnik_id, datum=None):
    """Vygeneruje ďalšie číslo dokladu podľa číselníka."""
    db = get_db()
    ciselnik = db.execute('SELECT * FROM ciselniky_dokladov WHERE id = ?', (ciselnik_id,)).fetchone()
    if not ciselnik:
        db.close()
        return None

    if datum is None:
        datum = datetime.now()

    # Zvýšime aktuálne číslo
    nove_cislo = ciselnik['aktualne_cislo'] + 1
    db.execute('UPDATE ciselniky_dokladov SET aktualne_cislo = ? WHERE id = ?', (nove_cislo, ciselnik_id))
    db.commit()
    db.close()

    # Formátovanie čísla podľa počtu číslic
    cislo_str = str(nove_cislo).zfill(ciselnik['pocet_cislic'])

    # Nahradenie placeholderov vo vzore
    vzor = ciselnik['vzor']
    prefix = ciselnik['prefix'] or ''
    oddelovac = ciselnik['oddelovac'] or ''

    # Rok: RR (2 číslice) alebo RRRR (4 číslice)
    vzor = vzor.replace('RRRR', str(datum.year))
    vzor = vzor.replace('RR', str(datum.year)[-2:])

    # Mesiac: MM
    vzor = vzor.replace('MM', str(datum.month).zfill(2))

    # Deň: DD
    vzor = vzor.replace('DD', str(datum.day).zfill(2))

    # Číslo: NNNNNN (podľa počtu číslic)
    n_pattern = 'N' * ciselnik['pocet_cislic']
    vzor = vzor.replace(n_pattern, cislo_str)
    # Fallback pre iné počty N
    vzor = re.sub(r'N+', cislo_str, vzor)

    # Pridanie prefixu
    if prefix:
        vzor = prefix + oddelovac + vzor if oddelovac else prefix + vzor

    return vzor


def dalsie_cislo_dokladu(ciselnik_id, datum=None):
    """Vráti náhľad ďalšieho čísla dokladu bez zvýšenia čítača."""
    db = get_db()
    ciselnik = db.execute('SELECT * FROM ciselniky_dokladov WHERE id = ?', (ciselnik_id,)).fetchone()
    if not ciselnik:
        db.close()
        return None
    db.close()

    if datum is None:
        datum = datetime.now()

    nove_cislo = ciselnik['aktualne_cislo'] + 1
    cislo_str = str(nove_cislo).zfill(ciselnik['pocet_cislic'])

    vzor = ciselnik['vzor']
    prefix = ciselnik['prefix'] or ''
    oddelovac = ciselnik['oddelovac'] or ''

    vzor = vzor.replace('RRRR', str(datum.year))
    vzor = vzor.replace('RR', str(datum.year)[-2:])
    vzor = vzor.replace('MM', str(datum.month).zfill(2))
    vzor = vzor.replace('DD', str(datum.day).zfill(2))

    n_pattern = 'N' * ciselnik['pocet_cislic']
    vzor = vzor.replace(n_pattern, cislo_str)
    vzor = re.sub(r'N+', cislo_str, vzor)

    if prefix:
        vzor = prefix + oddelovac + vzor if oddelovac else prefix + vzor

    return vzor


# Kontextový procesor pre šablóny
@app.context_processor
def inject_now():
    return {'now': datetime.now}


@app.route('/')
def index():
    db = get_db()
    nastavenia = db.execute('SELECT * FROM nastavenia LIMIT 1').fetchone()

    # Štatistiky za aktuálny rok
    rok = datetime.now().year

    # Celkové príjmy
    prijmy = db.execute('''
        SELECT COALESCE(SUM(suma), 0) as total FROM prijmy
        WHERE strftime('%Y', datum_prijetia) = ? AND danovy_prijem = 1
    ''', (str(rok),)).fetchone()

    # Celkové výdavky
    vydavky = db.execute('''
        SELECT COALESCE(SUM(suma), 0) as total FROM vydavky
        WHERE strftime('%Y', datum_uhrady) = ? AND danovy_vydavok = 1
    ''', (str(rok),)).fetchone()

    # Paušálne výdavky (60% z príjmov, max 20 000 EUR)
    pausalne = min(prijmy['total'] * 0.60, 20000)

    # Skutočné výdavky
    skutocne_vydavky = vydavky['total']

    # Počet neuhradených pohľadávok
    pohladavky_neuhr = db.execute('''
        SELECT COUNT(*) as count, COALESCE(SUM(suma), 0) as total FROM pohladavky
        WHERE stav = 'neuhradena'
    ''').fetchone()

    # Počet neuhradených záväzkov
    zavazky_neuhr = db.execute('''
        SELECT COUNT(*) as count, COALESCE(SUM(suma), 0) as total FROM zavazky
        WHERE stav = 'neuhradena'
    ''').fetchone()

    db.close()

    return render_template('index.html',
                           nastavenia=nastavenia,
                           rok=rok,
                           prijmy=prijmy['total'],
                           vydavky=vydavky['total'],
                           pausalne=pausalne,
                           skutocne_vydavky=skutocne_vydavky,
                           pohladavky_count=pohladavky_neuhr['count'],
                           pohladavky_sum=pohladavky_neuhr['total'],
                           zavazky_count=zavazky_neuhr['count'],
                           zavazky_sum=zavazky_neuhr['total'])


# ==================== PRÍJMY ====================

@app.route('/prijmy')
def prijmy():
    db = get_db()
    rok = request.args.get('rok', datetime.now().year, type=int)
    prijmy_data = db.execute('''
        SELECT * FROM prijmy
        WHERE strftime('%Y', datum_prijetia) = ?
        ORDER BY datum_prijetia DESC
    ''', (str(rok),)).fetchall()

    # Súčet
    total = db.execute('''
        SELECT COALESCE(SUM(suma), 0) as total FROM prijmy
        WHERE strftime('%Y', datum_prijetia) = ? AND danovy_prijem = 1
    ''', (str(rok),)).fetchone()

    db.close()
    return render_template('prijmy.html', prijmy=prijmy_data, rok=rok, total=total['total'])


@app.route('/pridat-prijem', methods=['GET', 'POST'])
def pridat_prijem():
    if request.method == 'POST':
        db = get_db()

        # Ak je zvolený číselník, vygenerujeme číslo automaticky
        cislo_dokladu = request.form['cislo_dokladu']
        ciselnik_id = request.form.get('ciselnik_id')
        datum_prijetia = request.form['datum_prijetia']
        if ciselnik_id and ciselnik_id != '':
            datum = datetime.strptime(datum_prijetia, '%Y-%m-%d')
            cislo_dokladu = generuj_cislo_dokladu(int(ciselnik_id), datum)

        # Vypočítať sumy z položiek
        zaklad_dane = float(request.form.get('zaklad_dane', 0))
        dph_suma = float(request.form.get('dph', 0))
        celkova_suma = float(request.form.get('celkova_suma', 0))

        db.execute('''
            INSERT INTO prijmy (
                datum_prijetia, datum_vystavenia, datum_splatnosti, datum_dodania,
                cislo_dokladu, typ_dokladu, popis,
                odberatel_id, odberatel, odberatel_nazov, odberatel_ico, odberatel_dic, odberatel_ic_dph,
                odberatel_adresa, odberatel_mesto, odberatel_psc, odberatel_stat,
                dodavatel_nazov, dodavatel_ico, dodavatel_dic, dodavatel_ic_dph,
                dodavatel_adresa, dodavatel_mesto, dodavatel_psc, dodavatel_stat,
                suma, dph, zaklad_dane, celkova_suma, sadzba_dph, mena,
                forma_uhrady, danovy_prijem, poznamka,
                cislo_objednavky, miesto_dodania,
                je_zahranicny, je_reverzne_zdanenie, je_oslobodene
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datum_prijetia,
            request.form.get('datum_vystavenia') or datum_prijetia,
            request.form.get('datum_splatnosti') or datum_prijetia,
            request.form.get('datum_dodania') or datum_prijetia,
            cislo_dokladu,
            request.form['typ_dokladu'],
            request.form.get('popis', ''),
            request.form.get('odberatel_id') or None,
            request.form.get('odberatel', ''),
            request.form.get('odberatel_nazov', ''),
            request.form.get('odberatel_ico', ''),
            request.form.get('odberatel_dic', ''),
            request.form.get('odberatel_ic_dph', ''),
            request.form.get('odberatel_adresa', ''),
            request.form.get('odberatel_mesto', ''),
            request.form.get('odberatel_psc', ''),
            request.form.get('odberatel_stat', 'Slovensko'),
            request.form.get('dodavatel_nazov', ''),
            request.form.get('dodavatel_ico', ''),
            request.form.get('dodavatel_dic', ''),
            request.form.get('dodavatel_ic_dph', ''),
            request.form.get('dodavatel_adresa', ''),
            request.form.get('dodavatel_mesto', ''),
            request.form.get('dodavatel_psc', ''),
            request.form.get('dodavatel_stat', 'Slovensko'),
            float(request.form.get('suma', 0)),
            dph_suma,
            zaklad_dane,
            celkova_suma,
            request.form.get('sadzba_dph', '23'),
            request.form.get('mena', 'EUR'),
            request.form.get('forma_uhrady', ''),
            1 if request.form.get('danovy_prijem') else 0,
            request.form.get('poznamka', ''),
            request.form.get('cislo_objednavky', ''),
            request.form.get('miesto_dodania', ''),
            1 if request.form.get('je_zahranicny') else 0,
            1 if request.form.get('je_reverzne_zdanenie') else 0,
            1 if request.form.get('je_oslobodene') else 0
        ))
        prijem_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

        # Ulož aktuálne DPH sadzby a kontaktné info pre právnu istotu
        datum_prijetia_dt = datetime.strptime(datum_prijetia, '%Y-%m-%d')
        ulozit_dph_sadzby_do_dokladu(prijem_id, 'prijmy', datum_prijetia_dt)
        odberatel_id = request.form.get('odberatel_id')
        if odberatel_id:
            ulozit_kontakt_info_do_dokladu(prijem_id, 'prijmy', int(odberatel_id))

        # Uložiť položky (riadky faktúry) - používame rovnaké db spojenie
        polozky_nazvy = request.form.getlist('polozka_nazov[]')
        polozky_poznamky = request.form.getlist('polozka_poznamka[]')
        polozky_mnozstva = request.form.getlist('polozka_mnozstvo[]')
        polozky_jednotky = request.form.getlist('polozka_jednotka[]')
        polozky_ceny = request.form.getlist('polozka_cena[]')
        polozky_sadzby = request.form.getlist('polozka_sadzba_dph[]')
        polozky_zaklady = request.form.getlist('polozka_zaklad[]')
        polozky_dph = request.form.getlist('polozka_dph[]')
        polozky_celkom = request.form.getlist('polozka_celkom[]')

        for i in range(len(polozky_nazvy)):
            if polozky_nazvy[i].strip():
                db.execute('''
                    INSERT INTO prijmy_polozky
                    (prijem_id, nazov, poznamka, mnozstvo, jednotka, jednotkova_cena_bez_dph,
                     sadzba_dph, zaklad_dane, dph, celkova_suma, poradie)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    prijem_id, polozky_nazvy[i],
                    polozky_poznamky[i] if i < len(polozky_poznamky) else '',
                    float(polozky_mnozstva[i]) if i < len(polozky_mnozstva) else 1,
                    polozky_jednotky[i] if i < len(polozky_jednotky) else 'ks',
                    float(polozky_ceny[i]) if i < len(polozky_ceny) else 0,
                    polozky_sadzby[i] if i < len(polozky_sadzby) else '23',
                    float(polozky_zaklady[i]) if i < len(polozky_zaklady) else 0,
                    float(polozky_dph[i]) if i < len(polozky_dph) else 0,
                    float(polozky_celkom[i]) if i < len(polozky_celkom) else 0,
                    i + 1
                ))

        db.commit()
        db.close()
        flash('Príjem bol úspešne pridaný!', 'success')
        return redirect(url_for('prijmy'))

    db = get_db()
    ciselniky = [dict(c) for c in db.execute('''
        SELECT * FROM ciselniky_dokladov
        WHERE je_aktivny = 1
        ORDER BY typ_dokladu, nazov
    ''').fetchall()]

    # Načítať kontakty s adresami a kontaktnými osobami
    kontakty_raw = db.execute('''
        SELECT * FROM adresar WHERE je_aktivny = 1 ORDER BY nazov
    ''').fetchall()
    kontakty = []
    for k in kontakty_raw:
        kdict = dict(k)
        kdict['adresy'] = db.execute('''
            SELECT * FROM adresar_dorucovacie_adresy WHERE kontakt_id = ? AND je_aktivny = 1 ORDER BY nazov
        ''', (k['id'],)).fetchall()
        kdict['kontakty'] = db.execute('''
            SELECT * FROM adresar_kontakty WHERE kontakt_id = ? AND je_aktivny = 1 ORDER BY meno
        ''', (k['id'],)).fetchall()
        kontakty.append(kdict)

    db.close()
    jednotky = [dict(j) for j in get_jednotky()]
    return render_template('pridat_prijem.html', ciselniky=ciselniky, kontakty=kontakty, jednotky=jednotky)


@app.route('/upravit-prijem/<int:id>', methods=['GET', 'POST'])
def upravit_prijem(id):
    db = get_db()
    if request.method == 'POST':
        datum_prijetia = request.form['datum_prijetia']
        zaklad_dane = float(request.form.get('zaklad_dane', 0))
        dph_suma = float(request.form.get('dph', 0))
        celkova_suma = float(request.form.get('celkova_suma', 0))

        db.execute('''
            UPDATE prijmy SET
                datum_prijetia = ?, datum_vystavenia = ?, datum_splatnosti = ?, datum_dodania = ?,
                cislo_dokladu = ?, typ_dokladu = ?, popis = ?,
                odberatel_id = ?, odberatel = ?, odberatel_nazov = ?, odberatel_ico = ?,
                odberatel_dic = ?, odberatel_ic_dph = ?,
                odberatel_adresa = ?, odberatel_mesto = ?, odberatel_psc = ?, odberatel_stat = ?,
                dodavatel_nazov = ?, dodavatel_ico = ?, dodavatel_dic = ?, dodavatel_ic_dph = ?,
                dodavatel_adresa = ?, dodavatel_mesto = ?, dodavatel_psc = ?, dodavatel_stat = ?,
                suma = ?, dph = ?, zaklad_dane = ?, celkova_suma = ?, sadzba_dph = ?, mena = ?,
                forma_uhrady = ?, danovy_prijem = ?, poznamka = ?,
                cislo_objednavky = ?, miesto_dodania = ?,
                je_zahranicny = ?, je_reverzne_zdanenie = ?, je_oslobodene = ?
            WHERE id = ?
        ''', (
            datum_prijetia,
            request.form.get('datum_vystavenia') or datum_prijetia,
            request.form.get('datum_splatnosti') or datum_prijetia,
            request.form.get('datum_dodania') or datum_prijetia,
            request.form['cislo_dokladu'],
            request.form['typ_dokladu'],
            request.form.get('popis', ''),
            request.form.get('odberatel_id') or None,
            request.form.get('odberatel', ''),
            request.form.get('odberatel_nazov', ''),
            request.form.get('odberatel_ico', ''),
            request.form.get('odberatel_dic', ''),
            request.form.get('odberatel_ic_dph', ''),
            request.form.get('odberatel_adresa', ''),
            request.form.get('odberatel_mesto', ''),
            request.form.get('odberatel_psc', ''),
            request.form.get('odberatel_stat', 'Slovensko'),
            request.form.get('dodavatel_nazov', ''),
            request.form.get('dodavatel_ico', ''),
            request.form.get('dodavatel_dic', ''),
            request.form.get('dodavatel_ic_dph', ''),
            request.form.get('dodavatel_adresa', ''),
            request.form.get('dodavatel_mesto', ''),
            request.form.get('dodavatel_psc', ''),
            request.form.get('dodavatel_stat', 'Slovensko'),
            float(request.form.get('suma', 0)),
            dph_suma,
            zaklad_dane,
            celkova_suma,
            request.form.get('sadzba_dph', '23'),
            request.form.get('mena', 'EUR'),
            request.form.get('forma_uhrady', ''),
            1 if request.form.get('danovy_prijem') else 0,
            request.form.get('poznamka', ''),
            request.form.get('cislo_objednavky', ''),
            request.form.get('miesto_dodania', ''),
            1 if request.form.get('je_zahranicny') else 0,
            1 if request.form.get('je_reverzne_zdanenie') else 0,
            1 if request.form.get('je_oslobodene') else 0,
            id
        ))

        # Zmazať staré položky a pridať nové
        db.execute('DELETE FROM prijmy_polozky WHERE prijem_id = ?', (id,))
        polozky_nazvy = request.form.getlist('polozka_nazov[]')
        polozky_poznamky = request.form.getlist('polozka_poznamka[]')
        polozky_mnozstva = request.form.getlist('polozka_mnozstvo[]')
        polozky_jednotky = request.form.getlist('polozka_jednotka[]')
        polozky_ceny = request.form.getlist('polozka_cena[]')
        polozky_sadzby = request.form.getlist('polozka_sadzba_dph[]')
        polozky_zaklady = request.form.getlist('polozka_zaklad[]')
        polozky_dph = request.form.getlist('polozka_dph[]')
        polozky_celkom = request.form.getlist('polozka_celkom[]')

        for i in range(len(polozky_nazvy)):
            if polozky_nazvy[i].strip():
                db.execute('''
                    INSERT INTO prijmy_polozky
                    (prijem_id, nazov, poznamka, mnozstvo, jednotka, jednotkova_cena_bez_dph,
                     sadzba_dph, zaklad_dane, dph, celkova_suma, poradie)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    id, polozky_nazvy[i],
                    polozky_poznamky[i] if i < len(polozky_poznamky) else '',
                    float(polozky_mnozstva[i]) if i < len(polozky_mnozstva) else 1,
                    polozky_jednotky[i] if i < len(polozky_jednotky) else 'ks',
                    float(polozky_ceny[i]) if i < len(polozky_ceny) else 0,
                    polozky_sadzby[i] if i < len(polozky_sadzby) else '23',
                    float(polozky_zaklady[i]) if i < len(polozky_zaklady) else 0,
                    float(polozky_dph[i]) if i < len(polozky_dph) else 0,
                    float(polozky_celkom[i]) if i < len(polozky_celkom) else 0,
                    i + 1
                ))

        db.commit()
        db.close()
        flash('Príjem bol upravený!', 'success')
        return redirect(url_for('prijmy'))

    prijem = db.execute('SELECT * FROM prijmy WHERE id = ?', (id,)).fetchone()
    polozky = get_prijem_polozky(id)

    # Načítať kontakty
    kontakty_raw = db.execute('SELECT * FROM adresar WHERE je_aktivny = 1 ORDER BY nazov').fetchall()
    kontakty = []
    for k in kontakty_raw:
        kdict = dict(k)
        kdict['adresy'] = db.execute('''
            SELECT * FROM adresar_dorucovacie_adresy WHERE kontakt_id = ? AND je_aktivny = 1 ORDER BY nazov
        ''', (k['id'],)).fetchall()
        kdict['kontakty'] = db.execute('''
            SELECT * FROM adresar_kontakty WHERE kontakt_id = ? AND je_aktivny = 1 ORDER BY meno
        ''', (k['id'],)).fetchall()
        kontakty.append(kdict)

    ciselniky = [dict(c) for c in db.execute('''
        SELECT * FROM ciselniky_dokladov WHERE je_aktivny = 1 ORDER BY typ_dokladu, nazov
    ''').fetchall()]

    db.close()
    jednotky = [dict(j) for j in get_jednotky()]
    return render_template('upravit_prijem.html', prijem=prijem, polozky=polozky, kontakty=kontakty, ciselniky=ciselniky, jednotky=jednotky)


@app.route('/zmazat-prijem/<int:id>')
def zmazat_prijem(id):
    db = get_db()
    db.execute('DELETE FROM prijmy_polozky WHERE prijem_id = ?', (id,))
    db.execute('DELETE FROM prijmy WHERE id = ?', (id,))
    db.commit()
    db.close()
    flash('Príjem bol zmazaný!', 'danger')
    return redirect(url_for('prijmy'))


# ==================== VÝDAVKY ====================

@app.route('/vydavky')
def vydavky():
    db = get_db()
    rok = request.args.get('rok', datetime.now().year, type=int)
    vydavky_data = db.execute('''
        SELECT * FROM vydavky
        WHERE strftime('%Y', datum_uhrady) = ?
        ORDER BY datum_uhrady DESC
    ''', (str(rok),)).fetchall()

    total = db.execute('''
        SELECT COALESCE(SUM(suma), 0) as total FROM vydavky
        WHERE strftime('%Y', datum_uhrady) = ? AND danovy_vydavok = 1
    ''', (str(rok),)).fetchone()

    db.close()
    return render_template('vydavky.html', vydavky=vydavky_data, rok=rok, total=total['total'])


@app.route('/pridat-vydavok', methods=['GET', 'POST'])
def pridat_vydavok():
    if request.method == 'POST':
        db = get_db()

        # Ak je zvolený číselník, vygenerujeme číslo automaticky
        cislo_dokladu = request.form['cislo_dokladu']
        ciselnik_id = request.form.get('ciselnik_id')
        datum_uhrady = request.form['datum_uhrady']
        if ciselnik_id and ciselnik_id != '':
            datum = datetime.strptime(datum_uhrady, '%Y-%m-%d')
            cislo_dokladu = generuj_cislo_dokladu(int(ciselnik_id), datum)

        # Vypočítať sumy z položiek
        zaklad_dane = float(request.form.get('zaklad_dane', 0))
        dph_suma = float(request.form.get('dph', 0))
        celkova_suma = float(request.form.get('celkova_suma', 0))

        db.execute('''
            INSERT INTO vydavky (
                datum_uhrady, datum_vystavenia, datum_splatnosti, datum_dodania,
                cislo_dokladu, typ_dokladu, popis,
                dodavatel_id, dodavatel, dodavatel_nazov, dodavatel_ico, dodavatel_dic, dodavatel_ic_dph,
                dodavatel_adresa, dodavatel_mesto, dodavatel_psc, dodavatel_stat,
                odberatel_nazov, odberatel_ico, odberatel_dic, odberatel_ic_dph,
                odberatel_adresa, odberatel_mesto, odberatel_psc, odberatel_stat,
                suma, dph, zaklad_dane, celkova_suma, sadzba_dph, mena,
                forma_uhrady, danovy_vydavok, kategoria, poznamka,
                cislo_objednavky, miesto_dodania,
                je_zahranicny, je_reverzne_zdanenie, je_oslobodene
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datum_uhrady,
            request.form.get('datum_vystavenia') or datum_uhrady,
            request.form.get('datum_splatnosti') or datum_uhrady,
            request.form.get('datum_dodania') or datum_uhrady,
            cislo_dokladu,
            request.form['typ_dokladu'],
            request.form.get('popis', ''),
            request.form.get('dodavatel_id') or None,
            request.form.get('dodavatel', ''),
            request.form.get('dodavatel_nazov', ''),
            request.form.get('dodavatel_ico', ''),
            request.form.get('dodavatel_dic', ''),
            request.form.get('dodavatel_ic_dph', ''),
            request.form.get('dodavatel_adresa', ''),
            request.form.get('dodavatel_mesto', ''),
            request.form.get('dodavatel_psc', ''),
            request.form.get('dodavatel_stat', 'Slovensko'),
            request.form.get('odberatel_nazov', ''),
            request.form.get('odberatel_ico', ''),
            request.form.get('odberatel_dic', ''),
            request.form.get('odberatel_ic_dph', ''),
            request.form.get('odberatel_adresa', ''),
            request.form.get('odberatel_mesto', ''),
            request.form.get('odberatel_psc', ''),
            request.form.get('odberatel_stat', 'Slovensko'),
            float(request.form.get('suma', 0)),
            dph_suma,
            zaklad_dane,
            celkova_suma,
            request.form.get('sadzba_dph', '23'),
            request.form.get('mena', 'EUR'),
            request.form.get('forma_uhrady', ''),
            1 if request.form.get('danovy_vydavok') else 0,
            request.form.get('kategoria', ''),
            request.form.get('poznamka', ''),
            request.form.get('cislo_objednavky', ''),
            request.form.get('miesto_dodania', ''),
            1 if request.form.get('je_zahranicny') else 0,
            1 if request.form.get('je_reverzne_zdanenie') else 0,
            1 if request.form.get('je_oslobodene') else 0
        ))
        vydavok_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

        # Ulož aktuálne DPH sadzby a kontaktné info pre právnu istotu
        datum_uhrady_dt = datetime.strptime(datum_uhrady, '%Y-%m-%d')
        ulozit_dph_sadzby_do_dokladu(vydavok_id, 'vydavky', datum_uhrady_dt)
        dodavatel_id = request.form.get('dodavatel_id')
        if dodavatel_id:
            ulozit_kontakt_info_do_dokladu(vydavok_id, 'vydavky', int(dodavatel_id))

        # Uložiť položky (riadky faktúry)
        polozky_nazvy = request.form.getlist('polozka_nazov[]')
        polozky_poznamky = request.form.getlist('polozka_poznamka[]')
        polozky_mnozstva = request.form.getlist('polozka_mnozstvo[]')
        polozky_jednotky = request.form.getlist('polozka_jednotka[]')
        polozky_ceny = request.form.getlist('polozka_cena[]')
        polozky_sadzby = request.form.getlist('polozka_sadzba_dph[]')
        polozky_zaklady = request.form.getlist('polozka_zaklad[]')
        polozky_dph = request.form.getlist('polozka_dph[]')
        polozky_celkom = request.form.getlist('polozka_celkom[]')

        for i in range(len(polozky_nazvy)):
            if polozky_nazvy[i].strip():
                db.execute('''
                    INSERT INTO vydavky_polozky
                    (vydavok_id, nazov, poznamka, mnozstvo, jednotka, jednotkova_cena_bez_dph,
                     sadzba_dph, zaklad_dane, dph, celkova_suma, poradie)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    vydavok_id, polozky_nazvy[i],
                    polozky_poznamky[i] if i < len(polozky_poznamky) else '',
                    float(polozky_mnozstva[i]) if i < len(polozky_mnozstva) else 1,
                    polozky_jednotky[i] if i < len(polozky_jednotky) else 'ks',
                    float(polozky_ceny[i]) if i < len(polozky_ceny) else 0,
                    polozky_sadzby[i] if i < len(polozky_sadzby) else '23',
                    float(polozky_zaklady[i]) if i < len(polozky_zaklady) else 0,
                    float(polozky_dph[i]) if i < len(polozky_dph) else 0,
                    float(polozky_celkom[i]) if i < len(polozky_celkom) else 0,
                    i + 1
                ))

        db.commit()
        db.close()
        flash('Výdavok bol úspešne pridaný!', 'success')
        return redirect(url_for('vydavky'))

    db = get_db()
    ciselniky = [dict(c) for c in db.execute('''
        SELECT * FROM ciselniky_dokladov
        WHERE typ_dokladu = 'vydavok' AND je_aktivny = 1
        ORDER BY nazov
    ''').fetchall()]

    # Načítať kontakty s adresami a kontaktnými osobami
    kontakty_raw = db.execute('''
        SELECT * FROM adresar WHERE je_aktivny = 1 ORDER BY nazov
    ''').fetchall()
    kontakty = []
    for k in kontakty_raw:
        kdict = dict(k)
        kdict['adresy'] = db.execute('''
            SELECT * FROM adresar_dorucovacie_adresy WHERE kontakt_id = ? AND je_aktivny = 1 ORDER BY nazov
        ''', (k['id'],)).fetchall()
        kdict['kontakty'] = db.execute('''
            SELECT * FROM adresar_kontakty WHERE kontakt_id = ? AND je_aktivny = 1 ORDER BY meno
        ''', (k['id'],)).fetchall()
        kontakty.append(kdict)

    db.close()
    jednotky = [dict(j) for j in get_jednotky()]
    return render_template('pridat_vydavok.html', ciselniky=ciselniky, kontakty=kontakty, jednotky=jednotky)


@app.route('/upravit-vydavok/<int:id>', methods=['GET', 'POST'])
def upravit_vydavok(id):
    db = get_db()
    if request.method == 'POST':
        datum_uhrady = request.form['datum_uhrady']
        zaklad_dane = float(request.form.get('zaklad_dane', 0))
        dph_suma = float(request.form.get('dph', 0))
        celkova_suma = float(request.form.get('celkova_suma', 0))

        db.execute('''
            UPDATE vydavky SET
                datum_uhrady = ?, datum_vystavenia = ?, datum_splatnosti = ?, datum_dodania = ?,
                cislo_dokladu = ?, typ_dokladu = ?, popis = ?,
                dodavatel_id = ?, dodavatel = ?, dodavatel_nazov = ?, dodavatel_ico = ?,
                dodavatel_dic = ?, dodavatel_ic_dph = ?,
                dodavatel_adresa = ?, dodavatel_mesto = ?, dodavatel_psc = ?, dodavatel_stat = ?,
                odberatel_nazov = ?, odberatel_ico = ?, odberatel_dic = ?, odberatel_ic_dph = ?,
                odberatel_adresa = ?, odberatel_mesto = ?, odberatel_psc = ?, odberatel_stat = ?,
                suma = ?, dph = ?, zaklad_dane = ?, celkova_suma = ?, sadzba_dph = ?, mena = ?,
                forma_uhrady = ?, danovy_vydavok = ?, kategoria = ?, poznamka = ?,
                cislo_objednavky = ?, miesto_dodania = ?,
                je_zahranicny = ?, je_reverzne_zdanenie = ?, je_oslobodene = ?
            WHERE id = ?
        ''', (
            datum_uhrady,
            request.form.get('datum_vystavenia') or datum_uhrady,
            request.form.get('datum_splatnosti') or datum_uhrady,
            request.form.get('datum_dodania') or datum_uhrady,
            request.form['cislo_dokladu'],
            request.form['typ_dokladu'],
            request.form.get('popis', ''),
            request.form.get('dodavatel_id') or None,
            request.form.get('dodavatel', ''),
            request.form.get('dodavatel_nazov', ''),
            request.form.get('dodavatel_ico', ''),
            request.form.get('dodavatel_dic', ''),
            request.form.get('dodavatel_ic_dph', ''),
            request.form.get('dodavatel_adresa', ''),
            request.form.get('dodavatel_mesto', ''),
            request.form.get('dodavatel_psc', ''),
            request.form.get('dodavatel_stat', 'Slovensko'),
            request.form.get('odberatel_nazov', ''),
            request.form.get('odberatel_ico', ''),
            request.form.get('odberatel_dic', ''),
            request.form.get('odberatel_ic_dph', ''),
            request.form.get('odberatel_adresa', ''),
            request.form.get('odberatel_mesto', ''),
            request.form.get('odberatel_psc', ''),
            request.form.get('odberatel_stat', 'Slovensko'),
            float(request.form.get('suma', 0)),
            dph_suma,
            zaklad_dane,
            celkova_suma,
            request.form.get('sadzba_dph', '23'),
            request.form.get('mena', 'EUR'),
            request.form.get('forma_uhrady', ''),
            1 if request.form.get('danovy_vydavok') else 0,
            request.form.get('kategoria', ''),
            request.form.get('poznamka', ''),
            request.form.get('cislo_objednavky', ''),
            request.form.get('miesto_dodania', ''),
            1 if request.form.get('je_zahranicny') else 0,
            1 if request.form.get('je_reverzne_zdanenie') else 0,
            1 if request.form.get('je_oslobodene') else 0,
            id
        ))

        # Zmazať staré položky a pridať nové
        db.execute('DELETE FROM vydavky_polozky WHERE vydavok_id = ?', (id,))
        polozky_nazvy = request.form.getlist('polozka_nazov[]')
        polozky_poznamky = request.form.getlist('polozka_poznamka[]')
        polozky_mnozstva = request.form.getlist('polozka_mnozstvo[]')
        polozky_jednotky = request.form.getlist('polozka_jednotka[]')
        polozky_ceny = request.form.getlist('polozka_cena[]')
        polozky_sadzby = request.form.getlist('polozka_sadzba_dph[]')
        polozky_zaklady = request.form.getlist('polozka_zaklad[]')
        polozky_dph = request.form.getlist('polozka_dph[]')
        polozky_celkom = request.form.getlist('polozka_celkom[]')

        for i in range(len(polozky_nazvy)):
            if polozky_nazvy[i].strip():
                db.execute('''
                    INSERT INTO vydavky_polozky
                    (vydavok_id, nazov, poznamka, mnozstvo, jednotka, jednotkova_cena_bez_dph,
                     sadzba_dph, zaklad_dane, dph, celkova_suma, poradie)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    id, polozky_nazvy[i],
                    polozky_poznamky[i] if i < len(polozky_poznamky) else '',
                    float(polozky_mnozstva[i]) if i < len(polozky_mnozstva) else 1,
                    polozky_jednotky[i] if i < len(polozky_jednotky) else 'ks',
                    float(polozky_ceny[i]) if i < len(polozky_ceny) else 0,
                    polozky_sadzby[i] if i < len(polozky_sadzby) else '23',
                    float(polozky_zaklady[i]) if i < len(polozky_zaklady) else 0,
                    float(polozky_dph[i]) if i < len(polozky_dph) else 0,
                    float(polozky_celkom[i]) if i < len(polozky_celkom) else 0,
                    i + 1
                ))

        db.commit()
        db.close()
        flash('Výdavok bol upravený!', 'success')
        return redirect(url_for('vydavky'))

    vydavok = db.execute('SELECT * FROM vydavky WHERE id = ?', (id,)).fetchone()
    polozky = get_vydavok_polozky(id)

    # Načítať kontakty
    kontakty_raw = db.execute('SELECT * FROM adresar WHERE je_aktivny = 1 ORDER BY nazov').fetchall()
    kontakty = []
    for k in kontakty_raw:
        kdict = dict(k)
        kdict['adresy'] = db.execute('''
            SELECT * FROM adresar_dorucovacie_adresy WHERE kontakt_id = ? AND je_aktivny = 1 ORDER BY nazov
        ''', (k['id'],)).fetchall()
        kdict['kontakty'] = db.execute('''
            SELECT * FROM adresar_kontakty WHERE kontakt_id = ? AND je_aktivny = 1 ORDER BY meno
        ''', (k['id'],)).fetchall()
        kontakty.append(kdict)

    ciselniky = [dict(c) for c in db.execute('''
        SELECT * FROM ciselniky_dokladov WHERE je_aktivny = 1 ORDER BY typ_dokladu, nazov
    ''').fetchall()]

    db.close()
    jednotky = [dict(j) for j in get_jednotky()]
    return render_template('upravit_vydavok.html', vydavok=vydavok, polozky=polozky, kontakty=kontakty, ciselniky=ciselniky, jednotky=jednotky)


@app.route('/zmazat-vydavok/<int:id>')
def zmazat_vydavok(id):
    db = get_db()
    db.execute('DELETE FROM vydavky_polozky WHERE vydavok_id = ?', (id,))
    db.execute('DELETE FROM vydavky WHERE id = ?', (id,))
    db.commit()
    db.close()
    flash('Výdavok bol zmazaný!', 'danger')
    return redirect(url_for('vydavky'))


# ==================== MAJETOK ====================

@app.route('/majetok')
def majetok():
    db = get_db()
    majetok_data = db.execute('SELECT * FROM majetok ORDER BY datum_obstarania DESC').fetchall()
    db.close()
    return render_template('majetok.html', majetok=majetok_data)


@app.route('/pridat-majetok', methods=['GET', 'POST'])
def pridat_majetok():
    if request.method == 'POST':
        db = get_db()
        vstupna_cena = float(request.form['vstupna_cena'])
        db.execute('''
            INSERT INTO majetok (nazov, druh_majetku, datum_obstarania, datum_zaradenia,
                               vstupna_cena, odpisova_skupina, zostatkova_cena, poznamka)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.form['nazov'],
            request.form['druh_majetku'],
            request.form['datum_obstarania'],
            request.form.get('datum_zaradenia', ''),
            vstupna_cena,
            request.form.get('odpisova_skupina', None),
            vstupna_cena,
            request.form.get('poznamka', '')
        ))
        db.commit()
        db.close()
        flash('Majetok bol pridaný!', 'success')
        return redirect(url_for('majetok'))
    return render_template('pridat_majetok.html')


@app.route('/zmazat-majetok/<int:id>')
def zmazat_majetok(id):
    db = get_db()
    db.execute('DELETE FROM majetok WHERE id = ?', (id,))
    db.commit()
    db.close()
    flash('Majetok bol zmazaný!', 'danger')
    return redirect(url_for('majetok'))


# ==================== POHĽADÁVKY ====================

@app.route('/pohladavky')
def pohladavky():
    db = get_db()
    pohladavky_data = db.execute('''
        SELECT * FROM pohladavky ORDER BY datum_vystavenia DESC
    ''').fetchall()
    db.close()
    return render_template('pohladavky.html', pohladavky=pohladavky_data)


@app.route('/pridat-pohladavku', methods=['GET', 'POST'])
def pridat_pohladavku():
    if request.method == 'POST':
        db = get_db()
        db.execute('''
            INSERT INTO pohladavky (cislo_faktury, odberatel, ico_odberatela,
                                  datum_vystavenia, datum_splatnosti, suma, dph, mena, poznamka)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.form['cislo_faktury'],
            request.form['odberatel'],
            request.form.get('ico_odberatela', ''),
            request.form['datum_vystavenia'],
            request.form['datum_splatnosti'],
            float(request.form['suma']),
            float(request.form.get('dph', 0)),
            request.form.get('mena', 'EUR'),
            request.form.get('poznamka', '')
        ))
        db.commit()
        db.close()
        flash('Pohľadávka bola pridaná!', 'success')
        return redirect(url_for('pohladavky'))
    return render_template('pridat_pohladavku.html')


@app.route('/uhradit-pohladavku/<int:id>', methods=['POST'])
def uhradit_pohladavku(id):
    db = get_db()
    db.execute('''
        UPDATE pohladavky SET
            stav = 'uhradena',
            datum_uhrady = ?,
            uhradena_suma = ?,
            forma_uhrady = ?
        WHERE id = ?
    ''', (
        request.form['datum_uhrady'],
        float(request.form['uhradena_suma']),
        request.form.get('forma_uhrady', ''),
        id
    ))
    db.commit()
    db.close()
    flash('Pohľadávka bola uhradená!', 'success')
    return redirect(url_for('pohladavky'))


@app.route('/zmazat-pohladavku/<int:id>')
def zmazat_pohladavku(id):
    db = get_db()
    db.execute('DELETE FROM pohladavky WHERE id = ?', (id,))
    db.commit()
    db.close()
    flash('Pohľadávka bola zmazaná!', 'danger')
    return redirect(url_for('pohladavky'))


# ==================== ZÁVAZKY ====================

@app.route('/zavazky')
def zavazky():
    db = get_db()
    zavazky_data = db.execute('''
        SELECT * FROM zavazky ORDER BY datum_vystavenia DESC
    ''').fetchall()
    db.close()
    return render_template('zavazky.html', zavazky=zavazky_data)


@app.route('/pridat-zavazok', methods=['GET', 'POST'])
def pridat_zavazok():
    if request.method == 'POST':
        db = get_db()
        db.execute('''
            INSERT INTO zavazky (cislo_faktury, dodavatel, ico_dodavatela,
                               datum_vystavenia, datum_splatnosti, suma, dph, mena, poznamka)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.form['cislo_faktury'],
            request.form['dodavatel'],
            request.form.get('ico_dodavatela', ''),
            request.form['datum_vystavenia'],
            request.form['datum_splatnosti'],
            float(request.form['suma']),
            float(request.form.get('dph', 0)),
            request.form.get('mena', 'EUR'),
            request.form.get('poznamka', '')
        ))
        db.commit()
        db.close()
        flash('Záväzok bol pridaný!', 'success')
        return redirect(url_for('zavazky'))
    return render_template('pridat_zavazok.html')


@app.route('/uhradit-zavazok/<int:id>', methods=['POST'])
def uhradit_zavazok(id):
    db = get_db()
    db.execute('''
        UPDATE zavazky SET
            stav = 'uhradena',
            datum_uhrady = ?,
            uhradena_suma = ?,
            forma_uhrady = ?
        WHERE id = ?
    ''', (
        request.form['datum_uhrady'],
        float(request.form['uhradena_suma']),
        request.form.get('forma_uhrady', ''),
        id
    ))
    db.commit()
    db.close()
    flash('Záväzok bol uhradený!', 'success')
    return redirect(url_for('zavazky'))


@app.route('/zmazat-zavazok/<int:id>')
def zmazat_zavazok(id):
    db = get_db()
    db.execute('DELETE FROM zavazky WHERE id = ?', (id,))
    db.commit()
    db.close()
    flash('Záväzok bol zmazaný!', 'danger')
    return redirect(url_for('zavazky'))


# ==================== ZÁSOBY ====================

@app.route('/zasoby')
def zasoby():
    db = get_db()
    zasoby_data = db.execute('SELECT * FROM zasoby ORDER BY datum_obstarania DESC').fetchall()
    db.close()
    return render_template('zasoby.html', zasoby=zasoby_data)


@app.route('/pridat-zasobu', methods=['GET', 'POST'])
def pridat_zasobu():
    if request.method == 'POST':
        db = get_db()
        mnozstvo = float(request.form['mnozstvo'])
        jednotkova_cena = float(request.form['jednotkova_cena'])
        celkova_cena = mnozstvo * jednotkova_cena
        db.execute('''
            INSERT INTO zasoby (nazov, datum_obstarania, mnozstvo, jednotka,
                            jednotkova_cena, celkova_cena, zostatok_mnozstvo, zostatok_cena, poznamka)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.form['nazov'],
            request.form['datum_obstarania'],
            mnozstvo,
            request.form.get('jednotka', 'ks'),
            jednotkova_cena,
            celkova_cena,
            mnozstvo,
            celkova_cena,
            request.form.get('poznamka', '')
        ))
        db.commit()
        db.close()
        flash('Zásoba bola pridaná!', 'success')
        return redirect(url_for('zasoby'))
    return render_template('pridat_zasobu.html')


@app.route('/zmazat-zasobu/<int:id>')
def zmazat_zasobu(id):
    db = get_db()
    db.execute('DELETE FROM zasoby WHERE id = ?', (id,))
    db.commit()
    db.close()
    flash('Zásoba bola zmazaná!', 'danger')
    return redirect(url_for('zasoby'))


# ==================== ODVODY ====================

@app.route('/odvody')
def odvody():
    db = get_db()
    rok = request.args.get('rok', datetime.now().year, type=int)
    odvody_data = db.execute('''
        SELECT * FROM odvody
        WHERE strftime('%Y', datum_uhrady) = ?
        ORDER BY datum_uhrady DESC
    ''', (str(rok),)).fetchall()

    total = db.execute('''
        SELECT COALESCE(SUM(suma), 0) as total FROM odvody
        WHERE strftime('%Y', datum_uhrady) = ?
    ''', (str(rok),)).fetchone()

    db.close()
    return render_template('odvody.html', odvody=odvody_data, rok=rok, total=total['total'])


@app.route('/pridat-odvod', methods=['GET', 'POST'])
def pridat_odvod():
    if request.method == 'POST':
        db = get_db()
        db.execute('''
            INSERT INTO odvody (datum_uhrady, typ_odvodu, obdobie, suma, poznamka)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            request.form['datum_uhrady'],
            request.form['typ_odvodu'],
            request.form['obdobie'],
            float(request.form['suma']),
            request.form.get('poznamka', '')
        ))
        db.commit()
        db.close()
        flash('Odvod bol pridaný!', 'success')
        return redirect(url_for('odvody'))
    return render_template('pridat_odvod.html')


@app.route('/zmazat-odvod/<int:id>')
def zmazat_odvod(id):
    db = get_db()
    db.execute('DELETE FROM odvody WHERE id = ?', (id,))
    db.commit()
    db.close()
    flash('Odvod bol zmazaný!', 'danger')
    return redirect(url_for('odvody'))


# ==================== PREHĽAD ====================

@app.route('/prehlad')
def prehlad():
    db = get_db()
    rok = request.args.get('rok', datetime.now().year, type=int)
    nastavenia = db.execute('SELECT * FROM nastavenia LIMIT 1').fetchone()

    # Príjmy za rok
    prijmy_rok = db.execute('''
        SELECT COALESCE(SUM(suma), 0) as total FROM prijmy
        WHERE strftime('%Y', datum_prijetia) = ? AND danovy_prijem = 1
    ''', (str(rok),)).fetchone()

    # Výdavky za rok
    vydavky_rok = db.execute('''
        SELECT COALESCE(SUM(suma), 0) as total FROM vydavky
        WHERE strftime('%Y', datum_uhrady) = ? AND danovy_vydavok = 1
    ''', (str(rok),)).fetchone()

    # Paušálne výdavky
    pausalne = min(prijmy_rok['total'] * 0.60, 20000)

    # Odvody
    odvody_soc = db.execute('''
        SELECT COALESCE(SUM(suma), 0) as total FROM odvody
        WHERE strftime('%Y', datum_uhrady) = ? AND typ_odvodu = 'Sociálne poistenie'
    ''', (str(rok),)).fetchone()

    odvody_zdr = db.execute('''
        SELECT COALESCE(SUM(suma), 0) as total FROM odvody
        WHERE strftime('%Y', datum_uhrady) = ? AND typ_odvodu = 'Zdravotné poistenie'
    ''', (str(rok),)).fetchone()

    # Neuhradené pohľadávky k 31.12.
    pohladavky_k31 = db.execute('''
        SELECT COALESCE(SUM(suma), 0) as total FROM pohladavky
        WHERE stav = 'neuhradena' AND datum_vystavenia <= ?
    ''', (f'{rok}-12-31',)).fetchone()

    # Mesačné príjmy
    mesacne_prijmy = []
    for mesiac in range(1, 13):
        start = f'{rok}-{mesiac:02d}-01'
        end_day = calendar.monthrange(rok, mesiac)[1]
        end = f'{rok}-{mesiac:02d}-{end_day}'
        row = db.execute('''
            SELECT COALESCE(SUM(suma), 0) as total FROM prijmy
            WHERE datum_prijetia BETWEEN ? AND ? AND danovy_prijem = 1
        ''', (start, end)).fetchone()
        mesacne_prijmy.append(row['total'])

    # Mesačné výdavky
    mesacne_vydavky = []
    for mesiac in range(1, 13):
        start = f'{rok}-{mesiac:02d}-01'
        end_day = calendar.monthrange(rok, mesiac)[1]
        end = f'{rok}-{mesiac:02d}-{end_day}'
        row = db.execute('''
            SELECT COALESCE(SUM(suma), 0) as total FROM vydavky
            WHERE datum_uhrady BETWEEN ? AND ? AND danovy_vydavok = 1
        ''', (start, end)).fetchone()
        mesacne_vydavky.append(row['total'])

    db.close()

    return render_template('prehlad.html',
                           rok=rok,
                           nastavenia=nastavenia,
                           prijmy=prijmy_rok['total'],
                           vydavky=vydavky_rok['total'],
                           pausalne=pausalne,
                           odvody_soc=odvody_soc['total'],
                           odvody_zdr=odvody_zdr['total'],
                           pohladavky_k31=pohladavky_k31['total'],
                           mesacne_prijmy=mesacne_prijmy,
                           mesacne_vydavky=mesacne_vydavky)


# ==================== NASTAVENIA ====================

@app.route('/nastavenia', methods=['GET', 'POST'])
def nastavenia():
    db = get_db()
    if request.method == 'POST':
        db.execute('''
            UPDATE nastavenia SET
                nazov_firmy = ?, ico = ?, dic = ?, ic_dph = ?,
                adresa = ?, mesto = ?, psc = ?,
                bankovy_ucet = ?, iban = ?,
                pausalne_vydavky = ?, platitel_dph = ?
            WHERE id = 1
        ''', (
            request.form['nazov_firmy'],
            request.form.get('ico', ''),
            request.form.get('dic', ''),
            request.form.get('ic_dph', ''),
            request.form.get('adresa', ''),
            request.form.get('mesto', ''),
            request.form.get('psc', ''),
            request.form.get('bankovy_ucet', ''),
            request.form.get('iban', ''),
            1 if request.form.get('pausalne_vydavky') else 0,
            1 if request.form.get('platitel_dph') else 0
        ))
        db.commit()
        db.close()
        flash('Nastavenia boli uložené!', 'success')
        return redirect(url_for('nastavenia'))

    nastavenia_data = db.execute('SELECT * FROM nastavenia LIMIT 1').fetchone()
    db.close()
    return render_template('nastavenia.html', nastavenia=nastavenia_data)


# ==================== JEDNOTKY ====================

@app.route('/jednotky')
def jednotky_list():
    jednotky = get_jednotky()
    return render_template('jednotky.html', jednotky=jednotky)


@app.route('/jednotky/pridat', methods=['POST'])
def jednotky_pridat():
    nazov = request.form.get('nazov', '').strip()
    skratka = request.form.get('skratka', '').strip()
    if not nazov or not skratka:
        flash('Vyplňte názov aj skratku jednotky!', 'warning')
    else:
        ok, chyba = pridat_jednotku(nazov, skratka)
        if ok:
            flash('Jednotka bola pridaná!', 'success')
        else:
            flash(chyba or 'Chyba pri pridávaní jednotky.', 'danger')
    return redirect(url_for('jednotky_list'))


@app.route('/jednotky/upravit/<int:id>', methods=['POST'])
def jednotky_upravit(id):
    nazov = request.form.get('nazov', '').strip()
    skratka = request.form.get('skratka', '').strip()
    if not nazov or not skratka:
        flash('Vyplňte názov aj skratku jednotky!', 'warning')
    else:
        ok, chyba = upravit_jednotku(id, nazov, skratka)
        if ok:
            flash('Jednotka bola upravená!', 'success')
        else:
            flash(chyba or 'Chyba pri úprave jednotky.', 'danger')
    return redirect(url_for('jednotky_list'))


@app.route('/jednotky/zmazat/<int:id>')
def jednotky_zmazat(id):
    zmazat_jednotku(id)
    flash('Jednotka bola zmazaná!', 'success')
    return redirect(url_for('jednotky_list'))


# ==================== ŠABLÓNY POLOŽIEK ====================

@app.route('/sablony')
def sablony_list():
    sablony = get_sablony()
    return render_template('sablony.html', sablony=sablony)


@app.route('/sablony/pridat', methods=['POST'])
def sablony_pridat():
    nazov = request.form.get('nazov', '').strip()
    typ_dokladu = request.form.get('typ_dokladu', '').strip()
    popis = request.form.get('popis', '').strip()
    nazov_polozky = request.form.get('nazov_polozky', '').strip()
    poznamka = request.form.get('poznamka', '').strip()
    mnozstvo = float(request.form.get('mnozstvo', 1) or 1)
    jednotka = request.form.get('jednotka', 'ks').strip()
    jednotkova_cena_bez_dph = float(request.form.get('jednotkova_cena_bez_dph', 0) or 0)
    sadzba_dph = request.form.get('sadzba_dph', '23').strip()

    if not nazov or not typ_dokladu:
        flash('Vyplňte názov šablóny a typ dokladu!', 'warning')
    else:
        ok, chyba = pridat_sablonu(nazov, typ_dokladu, popis, nazov_polozky, poznamka, mnozstvo, jednotka, jednotkova_cena_bez_dph, sadzba_dph)
        if ok:
            flash('Šablóna bola pridaná!', 'success')
        else:
            flash(chyba or 'Chyba pri pridávaní šablóny.', 'danger')
    return redirect(url_for('sablony_list'))


@app.route('/sablony/upravit/<int:id>', methods=['POST'])
def sablony_upravit(id):
    nazov = request.form.get('nazov', '').strip()
    typ_dokladu = request.form.get('typ_dokladu', '').strip()
    popis = request.form.get('popis', '').strip()
    nazov_polozky = request.form.get('nazov_polozky', '').strip()
    poznamka = request.form.get('poznamka', '').strip()
    mnozstvo = float(request.form.get('mnozstvo', 1) or 1)
    jednotka = request.form.get('jednotka', 'ks').strip()
    jednotkova_cena_bez_dph = float(request.form.get('jednotkova_cena_bez_dph', 0) or 0)
    sadzba_dph = request.form.get('sadzba_dph', '23').strip()

    if not nazov or not typ_dokladu:
        flash('Vyplňte názov šablóny a typ dokladu!', 'warning')
    else:
        ok, chyba = upravit_sablonu(id, nazov, typ_dokladu, popis, nazov_polozky, poznamka, mnozstvo, jednotka, jednotkova_cena_bez_dph, sadzba_dph)
        if ok:
            flash('Šablóna bola upravená!', 'success')
        else:
            flash(chyba or 'Chyba pri úprave šablóny.', 'danger')
    return redirect(url_for('sablony_list'))


@app.route('/sablony/zmazat/<int:id>')
def sablony_zmazat(id):
    zmazat_sablonu(id)
    flash('Šablóna bola zmazaná!', 'success')
    return redirect(url_for('sablony_list'))


@app.route('/api/sablony/<typ_dokladu>')
def api_sablony(typ_dokladu):
    """API endpoint pre získanie šablón podľa typu dokladu."""
    sablony = get_sablony(typ_dokladu)
    return jsonify([dict(s) for s in sablony])


# ==================== SYSTEM CATALOG ====================

@app.route('/system-catalog')
def system_catalog():
    """Zoznam systémových katalógov."""
    kategoria = request.args.get('kategoria')
    items = get_system_catalog(kategoria)
    # Group by kategoria
    groups = {}
    for item in items:
        kat = item['kategoria']
        if kat not in groups:
            groups[kat] = []
        groups[kat].append(dict(item))
    return render_template('system_catalog.html', groups=groups, aktualna_kategoria=kategoria)

@app.route('/system-catalog/upravit/<int:id>', methods=['POST'])
def upravit_system_catalog(id):
    """Upraví položku systémového katalógu."""
    nazov = request.form.get('nazov')
    hodnota = request.form.get('hodnota')
    hodnota_cislo = request.form.get('hodnota_cislo')
    popis = request.form.get('popis')
    je_aktivny = request.form.get('je_aktivny')
    
    update_system_catalog(
        id, nazov, hodnota, 
        float(hodnota_cislo) if hodnota_cislo else None,
        popis,
        1 if je_aktivny else 0
    )
    flash('Položka bola upravená.', 'success')
    return redirect(url_for('system_catalog'))

@app.route('/api/dph-sadzby')
def api_dph_sadzby():
    """API endpoint pre DPH sadzby."""
    sadzby = get_dph_sadzby()
    return jsonify([dict(s) for s in sadzby])

@app.route('/api/typy-dokladov/<typ>')
def api_typy_dokladov(typ):
    """API endpoint pre typy dokladov."""
    if typ == 'prijem':
        items = get_typy_dokladov_prijem()
    else:
        items = get_typy_dokladov_vydavok()
    return jsonify([dict(i) for i in items])


# ==================== AGENDY (FIRMY) ====================

@app.route('/agendy')
def agendy():
    """Zoznam všetkých agend."""
    # Najprv načítať z hlavnej databázy
    set_db_path(DEFAULT_DB_PATH)
    agendy_list = get_agendy()
    aktivna = get_aktivna_agenda()
    return render_template('agendy.html', agendy=agendy_list, aktivna=aktivna)


@app.route('/vytvorit-agendu', methods=['POST'])
def vytvorit_agendu_route():
    nazov = request.form.get('nazov', '').strip()
    poznamka = request.form.get('poznamka', '').strip()
    if not nazov:
        flash('Zadajte názov agendy!', 'warning')
        return redirect(url_for('agendy'))

    cesta, chyba = vytvorit_agendu(nazov, poznamka)
    if chyba:
        flash(chyba, 'danger')
    else:
        flash(f'Agenda "{nazov}" bola vytvorená a aktivovaná!', 'success')
    return redirect(url_for('agendy'))


@app.route('/otvorit-agendu/<subor>')
def otvorit_agendu_route(subor):
    uspech, chyba = otvorit_agendu(subor)
    if uspech:
        flash('Agenda bola aktivovaná!', 'success')
    else:
        flash(chyba or 'Chyba pri otváraní agendy', 'danger')
    return redirect(url_for('index'))


@app.route('/exportovat-agendu/<subor>')
def exportovat_agendu_route(subor):
    cesta, chyba = exportovat_agendu(subor)
    if chyba:
        flash(chyba, 'danger')
    else:
        nazov = os.path.basename(cesta)
        flash(f'Agenda bola exportovaná do súboru: {nazov}', 'success')
    return redirect(url_for('agendy'))


@app.route('/importovat-agendu', methods=['POST'])
def importovat_agendu_route():
    if 'soubor' not in request.files:
        flash('Nebol vybraný žiadny súbor!', 'warning')
        return redirect(url_for('agendy'))
    file = request.files['soubor']
    if file.filename == '':
        flash('Nebol vybraný žiadny súbor!', 'warning')
        return redirect(url_for('agendy'))

    # Uložiť dočasne
    temp_path = os.path.join(get_agendy_dir(), 'temp_import.db')
    file.save(temp_path)

    novy_nazov = request.form.get('novy_nazov', '').strip() or None
    cesta, chyba = importovat_agendu(temp_path, novy_nazov)

    # Vyčistiť temp
    if os.path.exists(temp_path):
        os.remove(temp_path)

    if chyba:
        flash(chyba, 'danger')
    else:
        flash('Agenda bola úspešne importovaná!', 'success')
    return redirect(url_for('agendy'))


@app.route('/zmazat-agendu/<subor>')
def zmazat_agendu_route(subor):
    zmazat_agendu(subor)
    flash('Agenda bola zmazaná!', 'success')
    return redirect(url_for('agendy'))


@app.route('/resetnut-agendu/<subor>')
def resetnut_agendu_route(subor):
    uspech, chyba = resetnut_agendu(subor)
    if uspech:
        flash('Agenda bola resetnutá! Všetky doklady boli vymazané.', 'warning')
    else:
        flash(chyba or 'Chyba pri resetovaní agendy', 'danger')
    return redirect(url_for('agendy'))


@app.route('/nastavit-datum', methods=['POST'])
def nastavit_datum():
    """Nastaví aktuálny dátum do session."""
    novy_datum = request.form.get('datum', '')
    if novy_datum:
        session['aktualny_datum'] = novy_datum
        flash(f'Aktuálny dátum bol nastavený na {format_datum(novy_datum)}', 'info')
    return redirect(request.referrer or url_for('index'))


# ==================== ČÍSELNÍKY ====================

@app.route('/ciselniky')
def ciselniky():
    db = get_db()
    ciselniky_data = db.execute('''
        SELECT * FROM ciselniky_dokladov ORDER BY typ_dokladu, nazov
    ''').fetchall()
    db.close()
    return render_template('ciselniky.html', ciselniky=ciselniky_data)


@app.route('/pridat-ciselnik', methods=['GET', 'POST'])
def pridat_ciselnik():
    if request.method == 'POST':
        db = get_db()
        db.execute('''
            INSERT INTO ciselniky_dokladov
            (nazov, typ_dokladu, prefix, vzor, aktualne_cislo, pocet_cislic,
             oddelovac, rok_v_cisle, mesiac_v_cisle, den_v_cisle, je_aktivny, poznamka)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.form['nazov'],
            request.form['typ_dokladu'],
            request.form.get('prefix', ''),
            request.form['vzor'],
            int(request.form.get('aktualne_cislo', 0)),
            int(request.form.get('pocet_cislic', 6)),
            request.form.get('oddelovac', '-'),
            1 if request.form.get('rok_v_cisle') else 0,
            1 if request.form.get('mesiac_v_cisle') else 0,
            1 if request.form.get('den_v_cisle') else 0,
            1 if request.form.get('je_aktivny') else 0,
            request.form.get('poznamka', '')
        ))
        db.commit()
        db.close()
        flash('Číselník bol pridaný!', 'success')
        return redirect(url_for('ciselniky'))
    return render_template('pridat_ciselnik.html')


@app.route('/upravit-ciselnik/<int:id>', methods=['GET', 'POST'])
def upravit_ciselnik(id):
    db = get_db()
    if request.method == 'POST':
        db.execute('''
            UPDATE ciselniky_dokladov SET
                nazov = ?, typ_dokladu = ?, prefix = ?, vzor = ?,
                aktualne_cislo = ?, pocet_cislic = ?, oddelovac = ?,
                rok_v_cisle = ?, mesiac_v_cisle = ?, den_v_cisle = ?,
                je_aktivny = ?, poznamka = ?
            WHERE id = ?
        ''', (
            request.form['nazov'],
            request.form['typ_dokladu'],
            request.form.get('prefix', ''),
            request.form['vzor'],
            int(request.form.get('aktualne_cislo', 0)),
            int(request.form.get('pocet_cislic', 6)),
            request.form.get('oddelovac', '-'),
            1 if request.form.get('rok_v_cisle') else 0,
            1 if request.form.get('mesiac_v_cisle') else 0,
            1 if request.form.get('den_v_cisle') else 0,
            1 if request.form.get('je_aktivny') else 0,
            request.form.get('poznamka', ''),
            id
        ))
        db.commit()
        db.close()
        flash('Číselník bol upravený!', 'success')
        return redirect(url_for('ciselniky'))
    ciselnik = db.execute('SELECT * FROM ciselniky_dokladov WHERE id = ?', (id,)).fetchone()
    db.close()
    return render_template('upravit_ciselnik.html', ciselnik=ciselnik)


@app.route('/zmazat-ciselnik/<int:id>')
def zmazat_ciselnik(id):
    db = get_db()
    db.execute('DELETE FROM ciselniky_dokladov WHERE id = ?', (id,))
    db.commit()
    db.close()
    flash('Číselník bol zmazaný!', 'danger')
    return redirect(url_for('ciselniky'))


@app.route('/api/nasledujuce-cislo/<int:ciselnik_id>')
def api_nasledujuce_cislo(ciselnik_id):
    """API endpoint pre získanie náhľadu ďalšieho čísla dokladu."""
    datum_str = request.args.get('datum')
    datum = datetime.strptime(datum_str, '%Y-%m-%d') if datum_str else None
    cislo = dalsie_cislo_dokladu(ciselnik_id, datum)
    return jsonify({'cislo': cislo})


@app.route('/api/ciselniky-pre-typ/<typ>')
def api_ciselniky_pre_typ(typ):
    """API endpoint pre získanie číselníkov podľa typu."""
    db = get_db()
    ciselniky = db.execute('''
        SELECT id, nazov, prefix, vzor, aktualne_cislo, pocet_cislic, oddelovac
        FROM ciselniky_dokladov
        WHERE typ_dokladu = ? AND je_aktivny = 1
        ORDER BY nazov
    ''', (typ,)).fetchall()
    db.close()
    return jsonify([dict(row) for row in ciselniky])


# ==================== ADRESÁR ====================

@app.route('/adresar')
def adresar():
    db = get_db()
    typ_filter = request.args.get('typ', '')
    hladat = request.args.get('hladat', '')

    query = 'SELECT * FROM adresar WHERE 1=1'
    params = []

    if typ_filter:
        query += ' AND typ = ?'
        params.append(typ_filter)

    if hladat:
        query += ' AND (nazov LIKE ? OR ico LIKE ? OR dic LIKE ?)'
        like = f'%{hladat}%'
        params.extend([like, like, like])

    query += ' ORDER BY nazov'

    kontakty = db.execute(query, params).fetchall()
    db.close()
    return render_template('adresar.html', kontakty=kontakty, typ_filter=typ_filter, hladat=hladat)


@app.route('/pridat-kontakt', methods=['GET', 'POST'])
def pridat_kontakt():
    if request.method == 'POST':
        db = get_db()
        cursor = db.execute('''
            INSERT INTO adresar (typ, nazov, ico, dic, ic_dph,
                sidlo_ulica, sidlo_cislo, sidlo_psc, sidlo_mesto, sidlo_stat,
                platca_dph, je_aktivny)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.form['typ'],
            request.form['nazov'],
            request.form.get('ico', ''),
            request.form.get('dic', ''),
            request.form.get('ic_dph', ''),
            request.form.get('sidlo_ulica', ''),
            request.form.get('sidlo_cislo', ''),
            request.form.get('sidlo_psc', ''),
            request.form.get('sidlo_mesto', ''),
            request.form.get('sidlo_stat', 'Slovensko'),
            1 if request.form.get('platca_dph') else 0,
            1 if request.form.get('je_aktivny') else 0
        ))
        kontakt_id = cursor.lastrowid

        # Doručovacie adresy
        for i in range(int(request.form.get('adresa_count', '0'))):
            db.execute('''
                INSERT INTO adresar_dorucovacie_adresy
                (kontakt_id, nazov, ulica, cislo, psc, mesto, stat, je_aktivny)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                kontakt_id,
                request.form.get(f'adresa_nazov_{i}', ''),
                request.form.get(f'adresa_ulica_{i}', ''),
                request.form.get(f'adresa_cislo_{i}', ''),
                request.form.get(f'adresa_psc_{i}', ''),
                request.form.get(f'adresa_mesto_{i}', ''),
                request.form.get(f'adresa_stat_{i}', 'Slovensko'),
                1 if request.form.get(f'adresa_aktivny_{i}') else 0
            ))

        # Kontaktné osoby
        for i in range(int(request.form.get('kontakt_count', '0'))):
            db.execute('''
                INSERT INTO adresar_kontakty
                (kontakt_id, meno, telefon, email, poznamka, je_aktivny)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                kontakt_id,
                request.form.get(f'kontakt_meno_{i}', ''),
                request.form.get(f'kontakt_telefon_{i}', ''),
                request.form.get(f'kontakt_email_{i}', ''),
                request.form.get(f'kontakt_poznamka_{i}', ''),
                1 if request.form.get(f'kontakt_aktivny_{i}') else 0
            ))

        # Bankové účty
        for i in range(int(request.form.get('banka_count', '0'))):
            db.execute('''
                INSERT INTO adresar_bankove_ucty
                (kontakt_id, nazov, banka, bankovy_ucet, iban, swift, mena, je_aktivny)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                kontakt_id,
                request.form.get(f'banka_nazov_{i}', ''),
                request.form.get(f'banka_nazov_banky_{i}', ''),
                request.form.get(f'banka_ucet_{i}', ''),
                request.form.get(f'banka_iban_{i}', ''),
                request.form.get(f'banka_swift_{i}', ''),
                request.form.get(f'banka_mena_{i}', 'EUR'),
                1 if request.form.get(f'banka_aktivny_{i}') else 0
            ))

        # Poznámky
        for i in range(int(request.form.get('poznamka_count', '0'))):
            db.execute('''
                INSERT INTO adresar_poznamky
                (kontakt_id, text, je_aktivny)
                VALUES (?, ?, ?)
            ''', (
                kontakt_id,
                request.form.get(f'poznamka_text_{i}', ''),
                1 if request.form.get(f'poznamka_aktivny_{i}') else 0
            ))

        db.commit()
        db.close()
        flash('Kontakt bol pridaný!', 'success')
        return redirect(url_for('adresar'))
    return render_template('pridat_kontakt.html')


@app.route('/upravit-kontakt/<int:id>', methods=['GET', 'POST'])
def upravit_kontakt(id):
    db = get_db()
    if request.method == 'POST':
        db.execute('''
            UPDATE adresar SET
                typ = ?, nazov = ?, ico = ?, dic = ?, ic_dph = ?,
                sidlo_ulica = ?, sidlo_cislo = ?, sidlo_psc = ?, sidlo_mesto = ?, sidlo_stat = ?,
                platca_dph = ?, je_aktivny = ?
            WHERE id = ?
        ''', (
            request.form['typ'],
            request.form['nazov'],
            request.form.get('ico', ''),
            request.form.get('dic', ''),
            request.form.get('ic_dph', ''),
            request.form.get('sidlo_ulica', ''),
            request.form.get('sidlo_cislo', ''),
            request.form.get('sidlo_psc', ''),
            request.form.get('sidlo_mesto', ''),
            request.form.get('sidlo_stat', 'Slovensko'),
            1 if request.form.get('platca_dph') else 0,
            1 if request.form.get('je_aktivny') else 0,
            id
        ))

        # Doručovacie adresy - zmazať staré a pridať nové
        db.execute('DELETE FROM adresar_dorucovacie_adresy WHERE kontakt_id = ?', (id,))
        for i in range(int(request.form.get('adresa_count', '0'))):
            db.execute('''
                INSERT INTO adresar_dorucovacie_adresy
                (kontakt_id, nazov, ulica, cislo, psc, mesto, stat, je_aktivny)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                id,
                request.form.get(f'adresa_nazov_{i}', ''),
                request.form.get(f'adresa_ulica_{i}', ''),
                request.form.get(f'adresa_cislo_{i}', ''),
                request.form.get(f'adresa_psc_{i}', ''),
                request.form.get(f'adresa_mesto_{i}', ''),
                request.form.get(f'adresa_stat_{i}', 'Slovensko'),
                1 if request.form.get(f'adresa_aktivny_{i}') else 0
            ))

        # Kontaktné osoby
        db.execute('DELETE FROM adresar_kontakty WHERE kontakt_id = ?', (id,))
        for i in range(int(request.form.get('kontakt_count', '0'))):
            db.execute('''
                INSERT INTO adresar_kontakty
                (kontakt_id, meno, telefon, email, poznamka, je_aktivny)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                id,
                request.form.get(f'kontakt_meno_{i}', ''),
                request.form.get(f'kontakt_telefon_{i}', ''),
                request.form.get(f'kontakt_email_{i}', ''),
                request.form.get(f'kontakt_poznamka_{i}', ''),
                1 if request.form.get(f'kontakt_aktivny_{i}') else 0
            ))

        # Bankové účty
        db.execute('DELETE FROM adresar_bankove_ucty WHERE kontakt_id = ?', (id,))
        for i in range(int(request.form.get('banka_count', '0'))):
            db.execute('''
                INSERT INTO adresar_bankove_ucty
                (kontakt_id, nazov, banka, bankovy_ucet, iban, swift, mena, je_aktivny)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                id,
                request.form.get(f'banka_nazov_{i}', ''),
                request.form.get(f'banka_nazov_banky_{i}', ''),
                request.form.get(f'banka_ucet_{i}', ''),
                request.form.get(f'banka_iban_{i}', ''),
                request.form.get(f'banka_swift_{i}', ''),
                request.form.get(f'banka_mena_{i}', 'EUR'),
                1 if request.form.get(f'banka_aktivny_{i}') else 0
            ))

        # Poznámky
        db.execute('DELETE FROM adresar_poznamky WHERE kontakt_id = ?', (id,))
        for i in range(int(request.form.get('poznamka_count', '0'))):
            db.execute('''
                INSERT INTO adresar_poznamky
                (kontakt_id, text, je_aktivny)
                VALUES (?, ?, ?)
            ''', (
                id,
                request.form.get(f'poznamka_text_{i}', ''),
                1 if request.form.get(f'poznamka_aktivny_{i}') else 0
            ))

        db.commit()
        db.close()
        flash('Kontakt bol upravený!', 'success')
        return redirect(url_for('adresar'))

    kontakt = db.execute('SELECT * FROM adresar WHERE id = ?', (id,)).fetchone()
    adresy = db.execute('SELECT * FROM adresar_dorucovacie_adresy WHERE kontakt_id = ?', (id,)).fetchall()
    kontakty = db.execute('SELECT * FROM adresar_kontakty WHERE kontakt_id = ?', (id,)).fetchall()
    banky = db.execute('SELECT * FROM adresar_bankove_ucty WHERE kontakt_id = ?', (id,)).fetchall()
    poznamky = db.execute('SELECT * FROM adresar_poznamky WHERE kontakt_id = ?', (id,)).fetchall()
    db.close()
    return render_template('upravit_kontakt.html', kontakt=kontakt, adresy=adresy,
                           kontakty=kontakty, banky=banky, poznamky=poznamky)


@app.route('/zmazat-kontakt/<int:id>')
def zmazat_kontakt(id):
    db = get_db()
    db.execute('DELETE FROM adresar WHERE id = ?', (id,))
    db.commit()
    db.close()
    flash('Kontakt bol zmazaný!', 'danger')
    return redirect(url_for('adresar'))


@app.route('/detail-kontaktu/<int:id>')
def detail_kontaktu(id):
    db = get_db()
    kontakt = db.execute('SELECT * FROM adresar WHERE id = ?', (id,)).fetchone()
    adresy = db.execute('SELECT * FROM adresar_dorucovacie_adresy WHERE kontakt_id = ? ORDER BY je_aktivny DESC, nazov', (id,)).fetchall()
    kontakty = db.execute('SELECT * FROM adresar_kontakty WHERE kontakt_id = ? ORDER BY je_aktivny DESC, meno', (id,)).fetchall()
    banky = db.execute('SELECT * FROM adresar_bankove_ucty WHERE kontakt_id = ? ORDER BY je_aktivny DESC, nazov', (id,)).fetchall()
    poznamky = db.execute('SELECT * FROM adresar_poznamky WHERE kontakt_id = ? ORDER BY je_aktivny DESC, created_at DESC', (id,)).fetchall()
    db.close()
    return render_template('detail_kontaktu.html', kontakt=kontakt, adresy=adresy,
                           kontakty=kontakty, banky=banky, poznamky=poznamky)


# ==================== VYHĽADÁVANIE FIRMY V ORSR ====================

def vyhladaj_orsr(meno=None, ico=None):
    """Vyhľadá firmu v ORSR podľa obchodného mena alebo IČO."""
    vysledky = []
    try:
        if ico:
            url = 'https://www.orsr.sk/hladaj_ico.asp'
            params = {'ICO': ico, 'SID': '0'}
        elif meno:
            url = 'https://www.orsr.sk/hladaj_subjekt.asp'
            params = {'OBMENO': meno, 'PF': '0', 'SID': '0', 'S': 'on', 'R': 'on'}
        else:
            return []

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'sk,en;q=0.9',
        }

        resp = requests.get(url, params=params, headers=headers, timeout=20)
        resp.encoding = 'iso-8859-2'

        soup = BeautifulSoup(resp.text, 'html.parser')

        # ORŠR výsledky sú v tabuľke
        tables = soup.find_all('table', {'class': 'tab1'})
        if not tables:
            tables = soup.find_all('table')

        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 3:
                    texty = [c.get_text(strip=True) for c in cells]
                    # Heuristika na identifikáciu riadku s firmou
                    obchodne_meno = ''
                    sidlo = ''
                    najdene_ico = ''
                    pravna_forma = ''

                    for txt in texty:
                        if not txt:
                            continue
                        if 'IČO:' in txt or re.match(r'^\d{6,8}$', txt):
                            m = re.search(r'(\d{6,8})', txt)
                            if m:
                                najdene_ico = m.group(1)
                        elif any(x in txt.lower() for x in ['s.r.o.', 'a.s.', 'k.s.', 'v.o.s.', 'sr.', 'spol.', 'kom.', 'ver.', 'verejná']):
                            pravna_forma = txt
                        elif not obchodne_meno and len(txt) > 3 and not sidlo:
                            obchodne_meno = txt
                        elif not sidlo and (re.search(r'\d{3}\s?\d{2}', txt) or 'ulica' in txt.lower() or 'nám.' in txt.lower()):
                            sidlo = txt

                    if obchodne_meno or najdene_ico:
                        vysledky.append({
                            'obchodne_meno': obchodne_meno,
                            'nazov': obchodne_meno,
                            'ico': najdene_ico,
                            'sidlo': sidlo,
                            'pravna_forma': pravna_forma,
                            'dic': '',
                            'ic_dph': ''
                        })

        # Odstránenie duplikátov
        unikatne = []
        seen = set()
        for v in vysledky:
            k = v['obchodne_meno'] + '|' + v['ico']
            if k not in seen and (v['obchodne_meno'] or v['ico']):
                seen.add(k)
                unikatne.append(v)

        return unikatne[:10]
    except Exception as e:
        app.logger.error(f'ORSR chyba: {e}')
        return []


@app.route('/api/vyhladaj-firmu')
def api_vyhladaj_firmu():
    typ = request.args.get('typ', '')
    hodnota = request.args.get('hodnota', '').strip()
    if not hodnota:
        return jsonify({'error': 'Zadajte hodnotu na vyhľadanie'}), 400

    if typ == 'ico':
        vysledky = vyhladaj_orsr(ico=hodnota)
    else:
        vysledky = vyhladaj_orsr(meno=hodnota)

    if not vysledky:
        return jsonify({'error': 'Neboli nájdené žiadne výsledky. Skontrolujte zadané údaje alebo skúste vyhľadať priamo na www.orsr.sk'}), 200

    return jsonify({'vysledky': vysledky})


# ==================== NASTAVENIA ZOBRAZENIA ====================

@app.route('/nastavenia-zobrazenia', methods=['GET', 'POST'])
def nastavenia_zobrazenia():
    """Stránka nastavení zobrazenia (téma, hustota, formát dátumu, čísla, meny, jazyk, písmo)."""
    if request.method == 'POST':
        data = {
            'tema': request.form.get('tema', 'light'),
            'hustota': request.form.get('hustota', 'normal'),
            'format_datumu': request.form.get('format_datumu', 'sk'),
            'format_cisla': request.form.get('format_cisla', 'sk'),
            'format_meny': request.form.get('format_meny', 'sk'),
            'jazyk': request.form.get('jazyk', 'sk'),
            'font_family': request.form.get('font_family', ''),
            'font_size': request.form.get('font_size', '16'),
            'font_size_nadpisy': request.form.get('font_size_nadpisy', ''),
            'font_size_tabulky': request.form.get('font_size_tabulky', ''),
            'font_size_formulare': request.form.get('font_size_formulare', ''),
            'font_size_poznamky': request.form.get('font_size_poznamky', '0.85')
        }
        update_zobrazenie(data)
        flash('Nastavenia zobrazenia boli uložené.', 'success')
        return redirect(url_for('nastavenia_zobrazenia'))

    zobrazenie = get_zobrazenie()
    return render_template('nastavenia_zobrazenia.html', zobrazenie=zobrazenie)


@app.route('/api/zobrazenie')
def api_zobrazenie():
    """API endpoint pre získanie nastavení zobrazenia."""
    return jsonify(get_zobrazenie())


@app.route('/api/zobrazenie', methods=['POST'])
def api_zobrazenie_post():
    """API endpoint pre uloženie nastavení zobrazenia."""
    data = request.get_json() or {}
    update_zobrazenie(data)
    return jsonify({'status': 'ok'})


# ═══════════════════════════════════════════════════════════════
# IMPORT / EXPORT ROUTES
# ═══════════════════════════════════════════════════════════════

@app.route('/export-json')
def export_json():
    """Export všetkých dát do JSON formátu."""
    from database import DB_PATH
    db_verzia = get_current_version(DB_PATH) or 'unknown'
    
    export = export_data(DB_PATH, db_verzia)
    
    filename = f"danova-evidencia-export-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    
    response = app.response_class(
        response=json.dumps(export, indent=2, ensure_ascii=False, default=str),
        status=200,
        mimetype='application/json'
    )
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response


@app.route('/import-json', methods=['POST'])
def import_json():
    """Import dát z JSON formátu."""
    from database import DB_PATH
    
    if 'file' not in request.files:
        flash('Žiadny súbor nebol vybraný', 'danger')
        return redirect(url_for('nastavenia'))
    
    file = request.files['file']
    if file.filename == '':
        flash('Žiadny súbor nebol vybraný', 'danger')
        return redirect(url_for('nastavenia'))
    
    try:
        import_data_json = json.load(file)
        
        # Validácia
        is_valid, errors, warnings = validate_import(import_data_json, DB_PATH)
        
        if not is_valid:
            flash(f"Import zlyhal: {'; '.join(errors)}", 'danger')
            return redirect(url_for('nastavenia'))
        
        # Režim importu
        mode = request.form.get('import_mode', 'merge')
        
        success, message, stats = import_data(import_data_json, DB_PATH, mode=mode)
        
        if success:
            if warnings:
                flash(f"{message} (varovania: {len(warnings)})", 'warning')
            else:
                flash(message, 'success')
        else:
            flash(message, 'danger')
            
    except json.JSONDecodeError:
        flash('Neplatný JSON formát', 'danger')
    except Exception as e:
        flash(f'Chyba pri importe: {str(e)}', 'danger')
    
    return redirect(url_for('nastavenia'))


@app.route('/api/validate-import', methods=['POST'])
def api_validate_import():
    """API endpoint pre validáciu importu bez vykonania."""
    from database import DB_PATH
    
    data = request.get_json()
    if not data:
        return jsonify({'valid': False, 'errors': ['Žiadne dáta']})
    
    is_valid, errors, warnings = validate_import(data, DB_PATH)
    
    return jsonify({
        'valid': is_valid,
        'errors': errors,
        'warnings': warnings,
        'current_schema': _get_schema_version(DB_PATH),
        'import_schema': data.get('schema_version', 'unknown')
    })


def _get_schema_version(db_path):
    """Pomocná funkcia pre získanie verzie schémy."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else 'unknown'
    except:
        return 'unknown'
    finally:
        conn.close()


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8080)
