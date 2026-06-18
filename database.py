import sqlite3
import os
import shutil
from datetime import datetime

# Import migration system
from migrations import migrate, get_current_version

# Globálna premenná pre aktuálnu databázu - môže sa zmeniť podľa agendy
DEFAULT_DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.dirname(__file__), 'danova_evidencia.db'))
DB_PATH = DEFAULT_DB_PATH


def set_db_path(path):
    """Nastaví cestu k databázovému súboru."""
    global DB_PATH
    DB_PATH = path


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _add_column_if_not_exists(tabulka, stlpec, typ):
    """Bezpečne pridá stĺpec ak ešte neexistuje. Ak tabuľka neexistuje, ticho vráti."""
    db = get_db()
    cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabulka,))
    if not cursor.fetchone():
        db.close()
        return
    cursor = db.execute(f"PRAGMA table_info({tabulka})")
    columns = [row['name'] for row in cursor.fetchall()]
    if stlpec not in columns:
        db.execute(f'ALTER TABLE {tabulka} ADD COLUMN {stlpec} {typ}')
        db.commit()
    db.close()


def init_db():
    # Run migrations first
    migrate(DB_PATH)
    
    # Add columns safely (SQLite doesn't support IF NOT EXISTS in ALTER TABLE)
    _add_column_if_not_exists('prijmy', 'sadzba_dph_zakladna', 'REAL')
    _add_column_if_not_exists('prijmy', 'sadzba_dph_znizena', 'REAL')
    _add_column_if_not_exists('prijmy', 'sadzba_dph_super_znizena', 'REAL')
    _add_column_if_not_exists('vydavky', 'sadzba_dph_zakladna', 'REAL')
    _add_column_if_not_exists('vydavky', 'sadzba_dph_znizena', 'REAL')
    _add_column_if_not_exists('vydavky', 'sadzba_dph_super_znizena', 'REAL')
    _add_column_if_not_exists('nastavenia', 'mod', "TEXT DEFAULT 'zjednoduseny'")
    _add_column_if_not_exists('nastavenia', 'swift', 'TEXT')
    _add_column_if_not_exists('nastavenia', 'banka', 'TEXT')
    _add_column_if_not_exists('nastavenia', 'cislo_uctu', 'TEXT')
    _add_column_if_not_exists('nastavenia', 'predcislie', 'TEXT')
    _add_column_if_not_exists('adresar_bankove_ucty', 'cislo_uctu', 'TEXT')
    _add_column_if_not_exists('adresar_bankove_ucty', 'predcislie', 'TEXT')
    _add_column_if_not_exists('system_catalog', 'swift', 'TEXT')
    
    conn = get_db()
    cursor = conn.cursor()

    # Tabuľka agend (firiem)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agendy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nazov TEXT NOT NULL,
            subor TEXT NOT NULL UNIQUE,
            je_aktivna BOOLEAN DEFAULT 0,
            vytvorena TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            poznamka TEXT
        )
    ''')

    # Nastavenia podnikateľa
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nastavenia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nazov_firmy TEXT,
            ico TEXT,
            dic TEXT,
            ic_dph TEXT,
            adresa TEXT,
            mesto TEXT,
            psc TEXT,
            bankovy_ucet TEXT,
            iban TEXT,
            pausalne_vydavky BOOLEAN DEFAULT 0,
            platitel_dph BOOLEAN DEFAULT 0,
            mod TEXT DEFAULT 'zjednoduseny',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Evidencia príjmov
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prijmy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datum_prijetia DATE NOT NULL,
            cislo_dokladu TEXT NOT NULL,
            typ_dokladu TEXT NOT NULL,
            popis TEXT NOT NULL,
            odberatel TEXT,
            ico_odberatela TEXT,
            suma DECIMAL(10,2) NOT NULL,
            dph DECIMAL(10,2) DEFAULT 0,
            mena TEXT DEFAULT 'EUR',
            forma_uhrady TEXT,
            danovy_prijem BOOLEAN DEFAULT 1,
            poznamka TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Evidencia výdavkov
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vydavky (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datum_uhrady DATE NOT NULL,
            cislo_dokladu TEXT NOT NULL,
            typ_dokladu TEXT NOT NULL,
            popis TEXT NOT NULL,
            dodavatel TEXT,
            ico_dodavatela TEXT,
            suma DECIMAL(10,2) NOT NULL,
            dph DECIMAL(10,2) DEFAULT 0,
            mena TEXT DEFAULT 'EUR',
            forma_uhrady TEXT,
            danovy_vydavok BOOLEAN DEFAULT 1,
            kategoria TEXT,
            poznamka TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Evidencia majetku
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS majetok (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nazov TEXT NOT NULL,
            druh_majetku TEXT NOT NULL,
            datum_obstarania DATE NOT NULL,
            datum_zaradenia DATE,
            vstupna_cena DECIMAL(10,2) NOT NULL,
            odpisova_skupina INTEGER,
            rocny_odpis DECIMAL(10,2),
            zostatkova_cena DECIMAL(10,2),
            datum_vyradenia DATE,
            poznamka TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Evidencia zásob
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS zasoby (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nazov TEXT NOT NULL,
            datum_obstarania DATE NOT NULL,
            mnozstvo DECIMAL(10,2) NOT NULL,
            jednotka TEXT,
            jednotkova_cena DECIMAL(10,2) NOT NULL,
            celkova_cena DECIMAL(10,2) NOT NULL,
            datum_vyuzitia DATE,
            vyuzite_mnozstvo DECIMAL(10,2),
            zostatok_mnozstvo DECIMAL(10,2),
            zostatok_cena DECIMAL(10,2),
            poznamka TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Evidencia pohľadávok
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pohladavky (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cislo_faktury TEXT NOT NULL,
            odberatel TEXT NOT NULL,
            ico_odberatela TEXT,
            datum_vystavenia DATE NOT NULL,
            datum_splatnosti DATE NOT NULL,
            suma DECIMAL(10,2) NOT NULL,
            dph DECIMAL(10,2) DEFAULT 0,
            mena TEXT DEFAULT 'EUR',
            stav TEXT DEFAULT 'neuhradena',
            datum_uhrady DATE,
            uhradena_suma DECIMAL(10,2),
            forma_uhrady TEXT,
            poznamka TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Evidencia záväzkov
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS zavazky (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cislo_faktury TEXT NOT NULL,
            dodavatel TEXT NOT NULL,
            ico_dodavatela TEXT,
            datum_vystavenia DATE NOT NULL,
            datum_splatnosti DATE NOT NULL,
            suma DECIMAL(10,2) NOT NULL,
            dph DECIMAL(10,2) DEFAULT 0,
            mena TEXT DEFAULT 'EUR',
            stav TEXT DEFAULT 'neuhradena',
            datum_uhrady DATE,
            uhradena_suma DECIMAL(10,2),
            forma_uhrady TEXT,
            poznamka TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Odvody (sociálne a zdravotné poistenie)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS odvody (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datum_uhrady DATE NOT NULL,
            typ_odvodu TEXT NOT NULL,
            obdobie TEXT NOT NULL,
            suma DECIMAL(10,2) NOT NULL,
            poznamka TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Číselníky
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ciselniky_dokladov (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nazov TEXT NOT NULL,
            typ_dokladu TEXT NOT NULL,
            prefix TEXT DEFAULT '',
            vzor TEXT NOT NULL DEFAULT 'RRRR-NNNNNN',
            aktualne_cislo INTEGER DEFAULT 0,
            pocet_cislic INTEGER DEFAULT 6,
            oddelovac TEXT DEFAULT '-',
            rok_v_cisle BOOLEAN DEFAULT 1,
            mesiac_v_cisle BOOLEAN DEFAULT 0,
            den_v_cisle BOOLEAN DEFAULT 0,
            je_aktivny BOOLEAN DEFAULT 1,
            poznamka TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Vloženie predvolených číselníkov, ak ešte nie sú
    cursor.execute('SELECT COUNT(*) FROM ciselniky_dokladov')
    if cursor.fetchone()[0] == 0:
        defaults = [
            ('Faktúra vystavená', 'prijem', 'FV', 'RRRR-NNNNNN', 0, 6, '-', 1, 0, 0, 1, 'Faktúry vystavené odberateľom'),
            ('Pokladničný doklad', 'prijem', 'VPD', 'RRRR-NNNNNN', 0, 6, '-', 1, 0, 0, 1, 'Výdavkový pokladničný doklad'),
            ('Bankový výpis', 'prijem', 'VBÚ', 'RRRR-NNNNNN', 0, 6, '-', 1, 0, 0, 1, 'Bankový výpis - príjem'),
            ('Faktúra prijatá', 'vydavok', 'FP', 'RRRR-NNNNNN', 0, 6, '-', 1, 0, 0, 1, 'Faktúry prijaté od dodávateľov'),
            ('Interný doklad', 'vydavok', 'ID', 'RRRR-NNNNNN', 0, 6, '-', 1, 0, 0, 1, 'Interný doklad'),
            ('Pokladničný doklad výdavok', 'vydavok', 'VPD', 'RRRR-NNNNNN', 0, 6, '-', 1, 0, 0, 1, 'Výdavkový pokladničný doklad'),
            ('Bankový výpis výdavok', 'vydavok', 'VBÚ', 'RRRR-NNNNNN', 0, 6, '-', 1, 0, 0, 1, 'Bankový výpis - výdavok'),
        ]
        for d in defaults:
            cursor.execute('''
                INSERT INTO ciselniky_dokladov
                (nazov, typ_dokladu, prefix, vzor, aktualne_cislo, pocet_cislic,
                 oddelovac, rok_v_cisle, mesiac_v_cisle, den_v_cisle, je_aktivny, poznamka)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', d)

    # Šablóny položiek dokladov
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sablony_poloziek (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nazov TEXT NOT NULL,
            typ_dokladu TEXT NOT NULL,
            popis TEXT,
            nazov_polozky TEXT DEFAULT '',
            poznamka TEXT DEFAULT '',
            mnozstvo REAL DEFAULT 1,
            jednotka TEXT DEFAULT 'ks',
            jednotkova_cena_bez_dph REAL DEFAULT 0,
            sadzba_dph TEXT DEFAULT '23',
            je_aktivny BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Vloženie predvolených šablón, ak ešte nie sú
    cursor.execute('SELECT COUNT(*) FROM sablony_poloziek')
    if cursor.fetchone()[0] == 0:
        defaults = [
            ('Služba - konzultácia', 'prijem', 'Konzultačná služba', 'Konzultácia', '', 1, 'hod', 50, '23'),
            ('Služba - programovanie', 'prijem', 'Programátorská služba', 'Programovanie', '', 1, 'hod', 80, '23'),
            ('Tovar - štandardný', 'prijem', 'Predaj tovaru', 'Tovar', '', 1, 'ks', 25, '23'),
            ('Materiál', 'vydavok', 'Nákup materiálu', 'Materiál', '', 1, 'ks', 15, '23'),
            ('Služby - účtovníctvo', 'vydavok', 'Účtovnícke služby', 'Účtovníctvo', '', 1, 'mes', 150, '23'),
            ('Energia', 'vydavok', 'Nákup energií', 'Elektrická energia', '', 1, 'mes', 120, '23'),
        ]
        for d in defaults:
            cursor.execute('''
                INSERT INTO sablony_poloziek
                (nazov, typ_dokladu, popis, nazov_polozky, poznamka, mnozstvo, jednotka, jednotkova_cena_bez_dph, sadzba_dph)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', d)

    # Vloženie predvolených nastavení, ak ešte nie sú
    cursor.execute('SELECT COUNT(*) FROM nastavenia')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO nastavenia (nazov_firmy, pausalne_vydavky, platitel_dph)
            VALUES ('Moja firma', 0, 0)
        ''')

    # Jednotky merania
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jednotky (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nazov TEXT NOT NULL UNIQUE,
            skratka TEXT NOT NULL,
            je_aktivny BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Vloženie predvolených jednotiek, ak ešte nie sú
    cursor.execute('SELECT COUNT(*) FROM jednotky')
    if cursor.fetchone()[0] == 0:
        defaults = [
            ('Kus', 'ks'),
            ('Hodina', 'h'),
            ('Deň', 'd'),
            ('Mesiac', 'mes'),
            ('Kilogram', 'kg'),
            ('Gram', 'g'),
            ('Liter', 'l'),
            ('Meter', 'm'),
            ('Centimeter', 'cm'),
            ('Štvorcový meter', 'm²'),
            ('Kubický meter', 'm³'),
            ('Balenie', 'bal'),
            ('Paleta', 'pal'),
            ('Krabica', 'krab'),
            ('Lístok', 'ks'),
            ('Služba', 'služba'),
        ]
        for d in defaults:
            cursor.execute('INSERT INTO jednotky (nazov, skratka) VALUES (?, ?)', d)

    # Adresár kontaktov (odberatelia, dodávatelia)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS adresar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            typ TEXT NOT NULL DEFAULT 'odberatel',
            nazov TEXT NOT NULL,
            ico TEXT,
            dic TEXT,
            ic_dph TEXT,
            sidlo_ulica TEXT,
            sidlo_cislo TEXT,
            sidlo_psc TEXT,
            sidlo_mesto TEXT,
            sidlo_stat TEXT DEFAULT 'Slovensko',
            platca_dph BOOLEAN DEFAULT 0,
            je_aktivny BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Doručovacie adresy kontaktu (môže ich byť viac)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS adresar_dorucovacie_adresy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kontakt_id INTEGER NOT NULL,
            nazov TEXT DEFAULT 'Hlavná',
            ulica TEXT,
            cislo TEXT,
            psc TEXT,
            mesto TEXT,
            stat TEXT DEFAULT 'Slovensko',
            je_aktivny BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kontakt_id) REFERENCES adresar(id) ON DELETE CASCADE
        )
    ''')

    # Kontaktné osoby (môže ich byť viac)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS adresar_kontakty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kontakt_id INTEGER NOT NULL,
            meno TEXT NOT NULL,
            telefon TEXT,
            email TEXT,
            poznamka TEXT,
            je_aktivny BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kontakt_id) REFERENCES adresar(id) ON DELETE CASCADE
        )
    ''')

    # Bankové účty kontaktu (môže ich byť viac)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS adresar_bankove_ucty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kontakt_id INTEGER NOT NULL,
            nazov TEXT DEFAULT 'Hlavný',
            banka TEXT,
            bankovy_ucet TEXT,
            iban TEXT,
            swift TEXT,
            cislo_uctu TEXT,
            predcislie TEXT,
            mena TEXT DEFAULT 'EUR',
            je_aktivny BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kontakt_id) REFERENCES adresar(id) ON DELETE CASCADE
        )
    ''')

    # Poznámky kontaktu (môže ich byť viac)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS adresar_poznamky (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kontakt_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            je_aktivny BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kontakt_id) REFERENCES adresar(id) ON DELETE CASCADE
        )
    ''')

    # Pridať stĺpce pre adresár do prijmov a výdavkov (ak ešte nie sú)
    try:
        cursor.execute('ALTER TABLE prijmy ADD COLUMN odberatel_id INTEGER')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE prijmy ADD COLUMN dorucovacia_adresa_id INTEGER')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE prijmy ADD COLUMN kontaktna_osoba_id INTEGER')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE vydavky ADD COLUMN dodavatel_id INTEGER')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE vydavky ADD COLUMN dorucovacia_adresa_id INTEGER')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE vydavky ADD COLUMN kontaktna_osoba_id INTEGER')
    except:
        pass

    # === ROZŠÍRENIE PRIJMOV O POVINNÉ ÚDAJE FAKTÚRY ===
    nove_stlpce_prijmy = [
        ('datum_vystavenia', 'DATE'),
        ('datum_splatnosti', 'DATE'),
        ('datum_dodania', 'DATE'),
        ('odberatel_nazov', 'TEXT'),
        ('odberatel_ico', 'TEXT'),
        ('odberatel_dic', 'TEXT'),
        ('odberatel_ic_dph', 'TEXT'),
        ('odberatel_adresa', 'TEXT'),
        ('odberatel_mesto', 'TEXT'),
        ('odberatel_psc', 'TEXT'),
        ('odberatel_stat', 'TEXT DEFAULT "Slovensko"'),
        ('dodavatel_nazov', 'TEXT'),
        ('dodavatel_ico', 'TEXT'),
        ('dodavatel_dic', 'TEXT'),
        ('dodavatel_ic_dph', 'TEXT'),
        ('dodavatel_adresa', 'TEXT'),
        ('dodavatel_mesto', 'TEXT'),
        ('dodavatel_psc', 'TEXT'),
        ('dodavatel_stat', 'TEXT DEFAULT "Slovensko"'),
        ('sadzba_dph', 'TEXT DEFAULT "20"'),
        ('zaklad_dane', 'DECIMAL(10,2) DEFAULT 0'),
        ('celkova_suma', 'DECIMAL(10,2) DEFAULT 0'),
        ('cislo_objednavky', 'TEXT'),
        ('miesto_dodania', 'TEXT'),
        ('je_zahranicny', 'BOOLEAN DEFAULT 0'),
        ('je_reverzne_zdanenie', 'BOOLEAN DEFAULT 0'),
        ('je_oslobodene', 'BOOLEAN DEFAULT 0'),
    ]
    for nazov, typ in nove_stlpce_prijmy:
        try:
            cursor.execute(f'ALTER TABLE prijmy ADD COLUMN {nazov} {typ}')
        except:
            pass

    # === ROZŠÍRENIE VÝDAVKOV O POVINNÉ ÚDAJE FAKTÚRY ===
    nove_stlpce_vydavky = [
        ('datum_vystavenia', 'DATE'),
        ('datum_splatnosti', 'DATE'),
        ('datum_dodania', 'DATE'),
        ('dodavatel_nazov', 'TEXT'),
        ('dodavatel_ico', 'TEXT'),
        ('dodavatel_dic', 'TEXT'),
        ('dodavatel_ic_dph', 'TEXT'),
        ('dodavatel_adresa', 'TEXT'),
        ('dodavatel_mesto', 'TEXT'),
        ('dodavatel_psc', 'TEXT'),
        ('dodavatel_stat', 'TEXT DEFAULT "Slovensko"'),
        ('odberatel_nazov', 'TEXT'),
        ('odberatel_ico', 'TEXT'),
        ('odberatel_dic', 'TEXT'),
        ('odberatel_ic_dph', 'TEXT'),
        ('odberatel_adresa', 'TEXT'),
        ('odberatel_mesto', 'TEXT'),
        ('odberatel_psc', 'TEXT'),
        ('odberatel_stat', 'TEXT DEFAULT "Slovensko"'),
        ('sadzba_dph', 'TEXT DEFAULT "20"'),
        ('zaklad_dane', 'DECIMAL(10,2) DEFAULT 0'),
        ('celkova_suma', 'DECIMAL(10,2) DEFAULT 0'),
        ('cislo_objednavky', 'TEXT'),
        ('miesto_dodania', 'TEXT'),
        ('je_zahranicny', 'BOOLEAN DEFAULT 0'),
        ('je_reverzne_zdanenie', 'BOOLEAN DEFAULT 0'),
        ('je_oslobodene', 'BOOLEAN DEFAULT 0'),
    ]
    for nazov, typ in nove_stlpce_vydavky:
        try:
            cursor.execute(f'ALTER TABLE vydavky ADD COLUMN {nazov} {typ}')
        except:
            pass

    # === POLOŽKY PRÍJMOV (riadky faktúry) ===
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prijmy_polozky (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prijem_id INTEGER NOT NULL,
            nazov TEXT NOT NULL,
            poznamka TEXT,
            mnozstvo DECIMAL(10,2) DEFAULT 1,
            jednotka TEXT DEFAULT 'ks',
            jednotkova_cena_bez_dph DECIMAL(10,2) NOT NULL,
            sadzba_dph TEXT DEFAULT '20',
            zaklad_dane DECIMAL(10,2) NOT NULL,
            dph DECIMAL(10,2) DEFAULT 0,
            celkova_suma DECIMAL(10,2) NOT NULL,
            poradie INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (prijem_id) REFERENCES prijmy(id) ON DELETE CASCADE
        )
    ''')
    # Pridať poznamka ak ešte neexistuje (pre existujúce DB)
    try:
        cursor.execute('ALTER TABLE prijmy_polozky ADD COLUMN poznamka TEXT')
    except:
        pass

    # === POLOŽKY VÝDAVKOV (riadky faktúry) ===
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vydavky_polozky (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vydavok_id INTEGER NOT NULL,
            nazov TEXT NOT NULL,
            poznamka TEXT,
            mnozstvo DECIMAL(10,2) DEFAULT 1,
            jednotka TEXT DEFAULT 'ks',
            jednotkova_cena_bez_dph DECIMAL(10,2) NOT NULL,
            sadzba_dph TEXT DEFAULT '20',
            zaklad_dane DECIMAL(10,2) NOT NULL,
            dph DECIMAL(10,2) DEFAULT 0,
            celkova_suma DECIMAL(10,2) NOT NULL,
            poradie INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vydavok_id) REFERENCES vydavky(id) ON DELETE CASCADE
        )
    ''')
    # Pridať poznamka ak ešte neexistuje (pre existujúce DB)
    try:
        cursor.execute('ALTER TABLE vydavky_polozky ADD COLUMN poznamka TEXT')
    except:
        pass

    # Tabuľka zobrazenia (téma, hustota, formát dátumu, čísla, meny, jazyk, písmo)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS zobrazenie (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tema TEXT DEFAULT 'light',
            hustota TEXT DEFAULT 'normal',
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

    # Vložiť predvolené zobrazenie ak ešte nie je
    cursor.execute("SELECT COUNT(*) FROM zobrazenie")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO zobrazenie (tema, hustota) VALUES ('light', 'normal')")

    # Agenda-špecifické typy dokladov (prepisujú globálne)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agenda_typy_dokladov (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            typ TEXT NOT NULL,
            kod TEXT NOT NULL,
            nazov TEXT NOT NULL,
            popis TEXT,
            je_aktivny BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(typ, kod)
        )
    ''')

    conn.commit()
    conn.close()


# ==================== FUNKCIE PRE ZOBRAZENIE ====================

def get_zobrazenie():
    """Načíta nastavenia zobrazenia z hlavnej databázy (globálne pre všetky agendy)."""
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM zobrazenie ORDER BY id LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        'tema': 'light',
        'hustota': 'normal',
        'format_datumu': 'sk',
        'format_cisla': 'sk',
        'format_meny': 'sk',
        'jazyk': 'sk',
        'font_family': '',
        'font_size': '16',
        'font_size_nadpisy': '',
        'font_size_tabulky': '',
        'font_size_formulare': '',
        'font_size_poznamky': '0.85'
    }


def update_zobrazenie(data):
    """Aktualizuje nastavenia zobrazenia v hlavnej databáze (globálne pre všetky agendy)."""
    # Najprv načítať existujúce hodnoty
    existujuce = get_zobrazenie()

    # Zlúčiť - nové hodnoty prepíšu existujúce
    merged = {
        'tema': data.get('tema', existujuce.get('tema', 'light')),
        'hustota': data.get('hustota', existujuce.get('hustota', 'normal')),
        'format_datumu': data.get('format_datumu', existujuce.get('format_datumu', 'sk')),
        'format_cisla': data.get('format_cisla', existujuce.get('format_cisla', 'sk')),
        'format_meny': data.get('format_meny', existujuce.get('format_meny', 'sk')),
        'jazyk': data.get('jazyk', existujuce.get('jazyk', 'sk')),
        'font_family': data.get('font_family', existujuce.get('font_family', '')),
        'font_size': data.get('font_size', existujuce.get('font_size', '16')),
        'font_size_nadpisy': data.get('font_size_nadpisy', existujuce.get('font_size_nadpisy', '')),
        'font_size_tabulky': data.get('font_size_tabulky', existujuce.get('font_size_tabulky', '')),
        'font_size_formulare': data.get('font_size_formulare', existujuce.get('font_size_formulare', '')),
        'font_size_poznamky': data.get('font_size_poznamky', existujuce.get('font_size_poznamky', '0.85'))
    }

    conn = sqlite3.connect(DEFAULT_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM zobrazenie ORDER BY id LIMIT 1")
    row = cursor.fetchone()
    if row:
        cursor.execute('''
            UPDATE zobrazenie SET
                tema = ?,
                hustota = ?,
                format_datumu = ?,
                format_cisla = ?,
                format_meny = ?,
                jazyk = ?,
                font_family = ?,
                font_size = ?,
                font_size_nadpisy = ?,
                font_size_tabulky = ?,
                font_size_formulare = ?,
                font_size_poznamky = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            merged['tema'],
            merged['hustota'],
            merged['format_datumu'],
            merged['format_cisla'],
            merged['format_meny'],
            merged['jazyk'],
            merged['font_family'],
            merged['font_size'],
            merged['font_size_nadpisy'],
            merged['font_size_tabulky'],
            merged['font_size_formulare'],
            merged['font_size_poznamky'],
            row['id']
        ))
    else:
        cursor.execute('''
            INSERT INTO zobrazenie (tema, hustota, format_datumu, format_cisla, format_meny, jazyk, font_family, font_size,
                                    font_size_nadpisy, font_size_tabulky, font_size_formulare, font_size_poznamky)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            merged['tema'],
            merged['hustota'],
            merged['format_datumu'],
            merged['format_cisla'],
            merged['format_meny'],
            merged['jazyk'],
            merged['font_family'],
            merged['font_size'],
            merged['font_size_nadpisy'],
            merged['font_size_tabulky'],
            merged['font_size_formulare'],
            merged['font_size_poznamky']
        ))
    conn.commit()
    conn.close()


# ==================== FUNKCIE PRE JEDNOTKY ====================

def get_jednotky():
    """Vráti zoznam všetkých aktívnych jednotiek."""
    db = get_db()
    jednotky = db.execute('SELECT * FROM jednotky WHERE je_aktivny = 1 ORDER BY nazov').fetchall()
    db.close()
    return jednotky


def pridat_jednotku(nazov, skratka):
    """Pridá novú jednotku."""
    db = get_db()
    try:
        db.execute('INSERT INTO jednotky (nazov, skratka) VALUES (?, ?)', (nazov, skratka))
        db.commit()
        db.close()
        return True, None
    except sqlite3.IntegrityError:
        db.close()
        return False, 'Jednotka s týmto názvom už existuje'


def upravit_jednotku(id, nazov, skratka):
    """Upraví existujúcu jednotku."""
    db = get_db()
    try:
        db.execute('UPDATE jednotky SET nazov = ?, skratka = ? WHERE id = ?', (nazov, skratka, id))
        db.commit()
        db.close()
        return True, None
    except sqlite3.IntegrityError:
        db.close()
        return False, 'Jednotka s týmto názvom už existuje'


def zmazat_jednotku(id):
    """Označí jednotku ako neaktívnu (soft delete)."""
    db = get_db()
    db.execute('UPDATE jednotky SET je_aktivny = 0 WHERE id = ?', (id,))
    db.commit()
    db.close()


# ==================== FUNKCIE PRE ŠABLÓNY POLOŽIEK ====================

def get_sablony(typ_dokladu=None):
    """Vráti zoznam všetkých aktívnych šablón, voliteľne filtrovaných podľa typu dokladu."""
    db = get_db()
    if typ_dokladu:
        sablony = db.execute(
            'SELECT * FROM sablony_poloziek WHERE je_aktivny = 1 AND typ_dokladu = ? ORDER BY nazov',
            (typ_dokladu,)
        ).fetchall()
    else:
        sablony = db.execute('SELECT * FROM sablony_poloziek WHERE je_aktivny = 1 ORDER BY nazov').fetchall()
    db.close()
    return sablony


def get_sablona(id):
    """Vráti konkrétnu šablónu podľa ID."""
    db = get_db()
    sablona = db.execute('SELECT * FROM sablony_poloziek WHERE id = ?', (id,)).fetchone()
    db.close()
    return sablona


def pridat_sablonu(nazov, typ_dokladu, popis='', nazov_polozky='', poznamka='', mnozstvo=1, jednotka='ks', jednotkova_cena_bez_dph=0, sadzba_dph='23'):
    """Pridá novú šablónu položky."""
    db = get_db()
    try:
        db.execute('''
            INSERT INTO sablony_poloziek
            (nazov, typ_dokladu, popis, nazov_polozky, poznamka, mnozstvo, jednotka, jednotkova_cena_bez_dph, sadzba_dph)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nazov, typ_dokladu, popis, nazov_polozky, poznamka, mnozstvo, jednotka, jednotkova_cena_bez_dph, sadzba_dph))
        db.commit()
        db.close()
        return True, None
    except sqlite3.IntegrityError:
        db.close()
        return False, 'Šablóna s týmto názvom už existuje'


def upravit_sablonu(id, nazov, typ_dokladu, popis='', nazov_polozky='', poznamka='', mnozstvo=1, jednotka='ks', jednotkova_cena_bez_dph=0, sadzba_dph='23'):
    """Upraví existujúcu šablónu položky."""
    db = get_db()
    try:
        db.execute('''
            UPDATE sablony_poloziek SET
                nazov = ?, typ_dokladu = ?, popis = ?, nazov_polozky = ?, poznamka = ?,
                mnozstvo = ?, jednotka = ?, jednotkova_cena_bez_dph = ?, sadzba_dph = ?
            WHERE id = ?
        ''', (nazov, typ_dokladu, popis, nazov_polozky, poznamka, mnozstvo, jednotka, jednotkova_cena_bez_dph, sadzba_dph, id))
        db.commit()
        db.close()
        return True, None
    except sqlite3.IntegrityError:
        db.close()
        return False, 'Šablóna s týmto názvom už existuje'


def zmazat_sablonu(id):
    """Označí šablónu ako neaktívnu (soft delete)."""
    db = get_db()
    db.execute('UPDATE sablony_poloziek SET je_aktivny = 0 WHERE id = ?', (id,))
    db.commit()
    db.close()


# ==================== GLOBÁLNE ŠABLÓNY (v hlavnej DB) ====================

def get_global_sablony(typ_dokladu=None):
    """Vráti globálne šablóny z hlavnej DB."""
    db = get_db()
    if typ_dokladu:
        sablony = db.execute(
            'SELECT * FROM sablony_poloziek WHERE je_aktivny = 1 AND typ_dokladu = ? ORDER BY nazov',
            (typ_dokladu,)
        ).fetchall()
    else:
        sablony = db.execute('SELECT * FROM sablony_poloziek WHERE je_aktivny = 1 ORDER BY nazov').fetchall()
    db.close()
    return sablony


def get_global_sablona(id):
    """Vráti globálnu šablónu podľa ID."""
    db = get_db()
    sablona = db.execute('SELECT * FROM sablony_poloziek WHERE id = ?', (id,)).fetchone()
    db.close()
    return sablona


def pridat_global_sablonu(nazov, typ_dokladu, popis='', nazov_polozky='', poznamka='', mnozstvo=1, jednotka='ks', jednotkova_cena_bez_dph=0, sadzba_dph='23'):
    """Pridá novú globálnu šablónu do hlavnej DB."""
    db = get_db()
    try:
        db.execute('''
            INSERT INTO sablony_poloziek
            (nazov, typ_dokladu, popis, nazov_polozky, poznamka, mnozstvo, jednotka, jednotkova_cena_bez_dph, sadzba_dph)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nazov, typ_dokladu, popis, nazov_polozky, poznamka, mnozstvo, jednotka, jednotkova_cena_bez_dph, sadzba_dph))
        db.commit()
        db.close()
        return True, None
    except sqlite3.IntegrityError:
        db.close()
        return False, 'Šablóna s týmto názvom už existuje'


def upravit_global_sablonu(id, nazov, typ_dokladu, popis='', nazov_polozky='', poznamka='', mnozstvo=1, jednotka='ks', jednotkova_cena_bez_dph=0, sadzba_dph='23'):
    """Upraví existujúcu globálnu šablónu v hlavnej DB."""
    db = get_db()
    try:
        db.execute('''
            UPDATE sablony_poloziek SET
                nazov = ?, typ_dokladu = ?, popis = ?, nazov_polozky = ?, poznamka = ?,
                mnozstvo = ?, jednotka = ?, jednotkova_cena_bez_dph = ?, sadzba_dph = ?
            WHERE id = ?
        ''', (nazov, typ_dokladu, popis, nazov_polozky, poznamka, mnozstvo, jednotka, jednotkova_cena_bez_dph, sadzba_dph, id))
        db.commit()
        db.close()
        return True, None
    except sqlite3.IntegrityError:
        db.close()
        return False, 'Šablóna s týmto názvom už existuje'


def zmazat_global_sablonu(id):
    """Označí globálnu šablónu ako neaktívnu (soft delete)."""
    db = get_db()
    db.execute('UPDATE sablony_poloziek SET je_aktivny = 0 WHERE id = ?', (id,))
    db.commit()
    db.close()


# ==================== FUNKCIE PRE ADRESÁR (adresy, kontakty, banky, poznámky) ====================

def get_adresar_dorucovacie_adresy(kontakt_id):
    """Vráti doručovacie adresy kontaktu."""
    db = get_db()
    items = db.execute(
        'SELECT * FROM adresar_dorucovacie_adresy WHERE kontakt_id = ? ORDER BY je_aktivny DESC, nazov',
        (kontakt_id,)
    ).fetchall()
    db.close()
    return items

def pridat_adresar_adresu(kontakt_id, nazov, ulica, cislo, psc, mesto, stat='Slovensko'):
    """Pridá doručovaciu adresu kontaktu."""
    db = get_db()
    db.execute('''
        INSERT INTO adresar_dorucovacie_adresy (kontakt_id, nazov, ulica, cislo, psc, mesto, stat)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (kontakt_id, nazov, ulica, cislo, psc, mesto, stat))
    db.commit()
    db.close()

def upravit_adresar_adresu(id, nazov, ulica, cislo, psc, mesto, stat, je_aktivny):
    """Upraví doručovaciu adresu."""
    db = get_db()
    db.execute('''
        UPDATE adresar_dorucovacie_adresy SET
            nazov = ?, ulica = ?, cislo = ?, psc = ?, mesto = ?, stat = ?, je_aktivny = ?
        WHERE id = ?
    ''', (nazov, ulica, cislo, psc, mesto, stat, je_aktivny, id))
    db.commit()
    db.close()

def zmazat_adresar_adresu(id):
    """Označí adresu ako neaktívnu."""
    db = get_db()
    db.execute('UPDATE adresar_dorucovacie_adresy SET je_aktivny = 0 WHERE id = ?', (id,))
    db.commit()
    db.close()

def get_adresar_kontakty(kontakt_id):
    """Vráti kontaktné osoby kontaktu."""
    db = get_db()
    items = db.execute(
        'SELECT * FROM adresar_kontakty WHERE kontakt_id = ? ORDER BY je_aktivny DESC, meno',
        (kontakt_id,)
    ).fetchall()
    db.close()
    return items

def pridat_adresar_kontakt(kontakt_id, meno, telefon, email, poznamka=''):
    """Pridá kontaktnú osobu."""
    db = get_db()
    db.execute('''
        INSERT INTO adresar_kontakty (kontakt_id, meno, telefon, email, poznamka)
        VALUES (?, ?, ?, ?, ?)
    ''', (kontakt_id, meno, telefon, email, poznamka))
    db.commit()
    db.close()

def upravit_adresar_kontakt(id, meno, telefon, email, poznamka, je_aktivny):
    """Upraví kontaktnú osobu."""
    db = get_db()
    db.execute('''
        UPDATE adresar_kontakty SET
            meno = ?, telefon = ?, email = ?, poznamka = ?, je_aktivny = ?
        WHERE id = ?
    ''', (meno, telefon, email, poznamka, je_aktivny, id))
    db.commit()
    db.close()

def zmazat_adresar_kontakt(id):
    """Označí kontaktnú osobu ako neaktívnu."""
    db = get_db()
    db.execute('UPDATE adresar_kontakty SET je_aktivny = 0 WHERE id = ?', (id,))
    db.commit()
    db.close()

def get_adresar_bankove_ucty(kontakt_id):
    """Vráti bankové účty kontaktu."""
    db = get_db()
    items = db.execute(
        'SELECT * FROM adresar_bankove_ucty WHERE kontakt_id = ? ORDER BY je_aktivny DESC, nazov',
        (kontakt_id,)
    ).fetchall()
    db.close()
    return items

def pridat_adresar_bankovy_ucet(kontakt_id, nazov, banka, predcislie, cislo_uctu, bankovy_ucet, iban, swift, mena='EUR'):
    """Pridá bankový účet kontaktu."""
    db = get_db()
    db.execute('''
        INSERT INTO adresar_bankove_ucty
        (kontakt_id, nazov, banka, predcislie, cislo_uctu, bankovy_ucet, iban, swift, mena)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (kontakt_id, nazov, banka, predcislie, cislo_uctu, bankovy_ucet, iban, swift, mena))
    db.commit()
    db.close()

def upravit_adresar_bankovy_ucet(id, nazov, banka, predcislie, cislo_uctu, bankovy_ucet, iban, swift, mena, je_aktivny):
    """Upraví bankový účet."""
    db = get_db()
    db.execute('''
        UPDATE adresar_bankove_ucty SET
            nazov = ?, banka = ?, predcislie = ?, cislo_uctu = ?, bankovy_ucet = ?,
            iban = ?, swift = ?, mena = ?, je_aktivny = ?
        WHERE id = ?
    ''', (nazov, banka, predcislie, cislo_uctu, bankovy_ucet, iban, swift, mena, je_aktivny, id))
    db.commit()
    db.close()

def zmazat_adresar_bankovy_ucet(id):
    """Označí bankový účet ako neaktívny."""
    db = get_db()
    db.execute('UPDATE adresar_bankove_ucty SET je_aktivny = 0 WHERE id = ?', (id,))
    db.commit()
    db.close()

def get_adresar_poznamky(kontakt_id):
    """Vráti poznámky kontaktu."""
    db = get_db()
    items = db.execute(
        'SELECT * FROM adresar_poznamky WHERE kontakt_id = ? ORDER BY je_aktivny DESC, created_at DESC',
        (kontakt_id,)
    ).fetchall()
    db.close()
    return items

def pridat_adresar_poznamku(kontakt_id, text):
    """Pridá poznámku kontaktu."""
    db = get_db()
    db.execute('''
        INSERT INTO adresar_poznamky (kontakt_id, text)
        VALUES (?, ?)
    ''', (kontakt_id, text))
    db.commit()
    db.close()

def upravit_adresar_poznamku(id, text, je_aktivny):
    """Upraví poznámku."""
    db = get_db()
    db.execute('''
        UPDATE adresar_poznamky SET text = ?, je_aktivny = ? WHERE id = ?
    ''', (text, je_aktivny, id))
    db.commit()
    db.close()

def zmazat_adresar_poznamku(id):
    """Označí poznámku ako neaktívnu."""
    db = get_db()
    db.execute('UPDATE adresar_poznamky SET je_aktivny = 0 WHERE id = ?', (id,))
    db.commit()
    db.close()


# ==================== FUNKCIE PRE OBJEDNÁVKY ====================

def get_objednavky(stav=None, rok=None, typ=None):
    """Vráti zoznam objednávok, voliteľne filtrovaných podľa stavu, roka a typu."""
    db = get_db()
    query = 'SELECT * FROM objednavky WHERE 1=1'
    params = []
    if stav:
        query += ' AND stav = ?'
        params.append(stav)
    if rok:
        query += " AND strftime('%Y', datum_vystavenia) = ?"
        params.append(str(rok))
    if typ:
        query += ' AND typ = ?'
        params.append(typ)
    query += ' ORDER BY datum_vystavenia DESC'
    cursor = db.execute(query, params)
    items = cursor.fetchall()
    db.close()
    return items

def get_objednavka(id):
    """Vráti konkrétnu objednávku podľa ID."""
    db = get_db()
    cursor = db.execute('SELECT * FROM objednavky WHERE id = ?', (id,))
    item = cursor.fetchone()
    db.close()
    return item

def get_objednavka_polozky(objednavka_id):
    """Vráti položky objednávky."""
    db = get_db()
    cursor = db.execute('SELECT * FROM objednavky_polozky WHERE objednavka_id = ? ORDER BY poradie', (objednavka_id,))
    items = cursor.fetchall()
    db.close()
    return items

def pridat_objednavku(data, polozky):
    """
    Pridá novú objednávku s položkami.
    
    Args:
        data: dict s údajmi objednávky
        polozky: list of dicts s položkami
    
    Returns:
        (id, chyba)
    """
    db = get_db()
    try:
        cursor = db.execute('''
            INSERT INTO objednavky (
                cislo_objednavky, datum_vystavenia, datum_platnosti,
                odberatel_id, odberatel_nazov, odberatel_ico, odberatel_dic, odberatel_ic_dph,
                odberatel_adresa, odberatel_mesto, odberatel_psc, odberatel_stat,
                dodavatel_id, dodavatel_nazov, dodavatel_ico, dodavatel_dic, dodavatel_ic_dph,
                dodavatel_adresa, dodavatel_mesto, dodavatel_psc, dodavatel_stat,
                stav, typ, suma, dph, zaklad_dane, celkova_suma, mena, poznamka
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('cislo_objednavky', ''),
            data.get('datum_vystavenia'),
            data.get('datum_platnosti'),
            data.get('odberatel_id'),
            data.get('odberatel_nazov', ''),
            data.get('odberatel_ico', ''),
            data.get('odberatel_dic', ''),
            data.get('odberatel_ic_dph', ''),
            data.get('odberatel_adresa', ''),
            data.get('odberatel_mesto', ''),
            data.get('odberatel_psc', ''),
            data.get('odberatel_stat', 'Slovensko'),
            data.get('dodavatel_id'),
            data.get('dodavatel_nazov', ''),
            data.get('dodavatel_ico', ''),
            data.get('dodavatel_dic', ''),
            data.get('dodavatel_ic_dph', ''),
            data.get('dodavatel_adresa', ''),
            data.get('dodavatel_mesto', ''),
            data.get('dodavatel_psc', ''),
            data.get('dodavatel_stat', 'Slovensko'),
            data.get('stav', 'nova'),
            data.get('typ', 'prijata'),
            data.get('suma', 0),
            data.get('dph', 0),
            data.get('zaklad_dane', 0),
            data.get('celkova_suma', 0),
            data.get('mena', 'EUR'),
            data.get('poznamka', '')
        ))
        objednavka_id = cursor.lastrowid
        
        # Vložiť položky
        for i, polozka in enumerate(polozky):
            db.execute('''
                INSERT INTO objednavky_polozky
                (objednavka_id, nazov, poznamka, mnozstvo, jednotka, jednotkova_cena_bez_dph,
                 sadzba_dph, zaklad_dane, dph, celkova_suma, poradie)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                objednavka_id,
                polozka.get('nazov', ''),
                polozka.get('poznamka', ''),
                float(polozka.get('mnozstvo', 1)),
                polozka.get('jednotka', 'ks'),
                float(polozka.get('jednotkova_cena_bez_dph', 0)),
                polozka.get('sadzba_dph', '23'),
                float(polozka.get('zaklad_dane', 0)),
                float(polozka.get('dph', 0)),
                float(polozka.get('celkova_suma', 0)),
                i + 1
            ))
        
        db.commit()
        db.close()
        return objednavka_id, None
    except Exception as e:
        db.close()
        return None, str(e)

def upravit_objednavku(id, data, polozky):
    """Upraví objednávku - zmaže staré položky a pridá nové."""
    db = get_db()
    try:
        db.execute('''
            UPDATE objednavky SET
                cislo_objednavky = ?, datum_vystavenia = ?, datum_platnosti = ?,
                odberatel_id = ?, odberatel_nazov = ?, odberatel_ico = ?, odberatel_dic = ?, odberatel_ic_dph = ?,
                odberatel_adresa = ?, odberatel_mesto = ?, odberatel_psc = ?, odberatel_stat = ?,
                dodavatel_id = ?, dodavatel_nazov = ?, dodavatel_ico = ?, dodavatel_dic = ?, dodavatel_ic_dph = ?,
                dodavatel_adresa = ?, dodavatel_mesto = ?, dodavatel_psc = ?, dodavatel_stat = ?,
                stav = ?, typ = ?, suma = ?, dph = ?, zaklad_dane = ?, celkova_suma = ?, mena = ?, poznamka = ?
            WHERE id = ?
        ''', (
            data.get('cislo_objednavky', ''),
            data.get('datum_vystavenia'),
            data.get('datum_platnosti'),
            data.get('odberatel_id'),
            data.get('odberatel_nazov', ''),
            data.get('odberatel_ico', ''),
            data.get('odberatel_dic', ''),
            data.get('odberatel_ic_dph', ''),
            data.get('odberatel_adresa', ''),
            data.get('odberatel_mesto', ''),
            data.get('odberatel_psc', ''),
            data.get('odberatel_stat', 'Slovensko'),
            data.get('dodavatel_id'),
            data.get('dodavatel_nazov', ''),
            data.get('dodavatel_ico', ''),
            data.get('dodavatel_dic', ''),
            data.get('dodavatel_ic_dph', ''),
            data.get('dodavatel_adresa', ''),
            data.get('dodavatel_mesto', ''),
            data.get('dodavatel_psc', ''),
            data.get('dodavatel_stat', 'Slovensko'),
            data.get('stav', 'nova'),
            data.get('typ', 'prijata'),
            data.get('suma', 0),
            data.get('dph', 0),
            data.get('zaklad_dane', 0),
            data.get('celkova_suma', 0),
            data.get('mena', 'EUR'),
            data.get('poznamka', ''),
            id
        ))
        
        # Zmazať staré položky a pridať nové
        db.execute('DELETE FROM objednavky_polozky WHERE objednavka_id = ?', (id,))
        for i, polozka in enumerate(polozky):
            db.execute('''
                INSERT INTO objednavky_polozky
                (objednavka_id, nazov, poznamka, mnozstvo, jednotka, jednotkova_cena_bez_dph,
                 sadzba_dph, zaklad_dane, dph, celkova_suma, poradie)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                id,
                polozka.get('nazov', ''),
                polozka.get('poznamka', ''),
                float(polozka.get('mnozstvo', 1)),
                polozka.get('jednotka', 'ks'),
                float(polozka.get('jednotkova_cena_bez_dph', 0)),
                polozka.get('sadzba_dph', '23'),
                float(polozka.get('zaklad_dane', 0)),
                float(polozka.get('dph', 0)),
                float(polozka.get('celkova_suma', 0)),
                i + 1
            ))
        
        db.commit()
        db.close()
        return True, None
    except Exception as e:
        db.close()
        return False, str(e)

def zmenit_stav_objednavky(id, novy_stav):
    """Zmení stav objednávky."""
    db = get_db()
    db.execute('UPDATE objednavky SET stav = ? WHERE id = ?', (novy_stav, id))
    db.commit()
    db.close()

def zmazat_objednavku(id):
    """Zmaže objednávku a jej položky."""
    db = get_db()
    db.execute('DELETE FROM objednavky_polozky WHERE objednavka_id = ?', (id,))
    db.execute('DELETE FROM objednavky WHERE id = ?', (id,))
    db.commit()
    db.close()


# ==================== SYSTEM CATALOG ====================

def get_system_catalog(kategoria=None, je_aktivny=True):
    """Vráti položky systémového katalógu."""
    db = get_db()
    query = 'SELECT * FROM system_catalog WHERE 1=1'
    params = []
    if kategoria:
        query += ' AND kategoria = ?'
        params.append(kategoria)
    if je_aktivny is not None:
        query += ' AND je_aktivny = ?'
        params.append(1 if je_aktivny else 0)
    query += ' ORDER BY kategoria, nazov'
    cursor = db.execute(query, params)
    items = cursor.fetchall()
    db.close()
    return items


def get_banky(je_aktivny=None):
    """Vráti zoznam bánk zo systémového katalógu."""
    return get_system_catalog('banka', je_aktivny)


def get_bank_swift(kod_banky):
    """Vráti SWIFT kód banky podľa kódu."""
    item = get_system_catalog_item('banka', kod_banky)
    return item['hodnota'] if item else None


def get_system_catalog_item(kategoria, kod):
    """Vráti konkrétnu položku katalógu."""
    db = get_db()
    cursor = db.execute('SELECT * FROM system_catalog WHERE kategoria = ? AND kod = ?', (kategoria, kod))
    item = cursor.fetchone()
    db.close()
    return item

def get_dph_sadzby():
    """Vráti aktívne DPH sadzby."""
    return get_system_catalog('dph_sadzba')

def get_typy_dokladov_prijem():
    """Vráti typy dokladov pre príjem."""
    return get_system_catalog('typ_dokladu_prijem')

def get_typy_dokladov_vydavok():
    """Vráti typy dokladov pre výdavok."""
    return get_system_catalog('typ_dokladu_vydavok')


# ==================== AGENDA-ŠPECIFICKÉ TYPY DOKLADOV ====================

def get_agenda_typy_dokladov(typ):
    """Vráti agenda-špecifické typy dokladov pre daný typ (prijem/vydavok).
    Ak existujú, prepisujú globálne nastavenia."""
    db = get_db()
    cursor = db.execute(
        "SELECT * FROM agenda_typy_dokladov WHERE typ = ? AND je_aktivny = 1 ORDER BY nazov",
        (typ,)
    )
    items = cursor.fetchall()
    db.close()
    return items


def get_agenda_typ_dokladu(typ, kod):
    """Vráti konkrétny agenda-špecifický typ dokladu."""
    db = get_db()
    cursor = db.execute(
        "SELECT * FROM agenda_typy_dokladov WHERE typ = ? AND kod = ?",
        (typ, kod)
    )
    item = cursor.fetchone()
    db.close()
    return item


def pridat_agenda_typ_dokladu(typ, kod, nazov, popis=''):
    """Pridá alebo aktualizuje agenda-špecifický typ dokladu."""
    db = get_db()
    db.execute('''
        INSERT INTO agenda_typy_dokladov (typ, kod, nazov, popis, je_aktivny)
        VALUES (?, ?, ?, ?, 1)
        ON CONFLICT(typ, kod) DO UPDATE SET nazov = excluded.nazov, popis = excluded.popis, je_aktivny = 1
    ''', (typ, kod, nazov, popis))
    db.commit()
    db.close()


def upravit_agenda_typ_dokladu(id, nazov, popis, je_aktivny):
    """Upraví agenda-špecifický typ dokladu."""
    db = get_db()
    db.execute('''
        UPDATE agenda_typy_dokladov
        SET nazov = ?, popis = ?, je_aktivny = ?
        WHERE id = ?
    ''', (nazov, popis, 1 if je_aktivny else 0, id))
    db.commit()
    db.close()


def zmazat_agenda_typ_dokladu(id):
    """Zmaže agenda-špecifický typ dokladu."""
    db = get_db()
    db.execute("DELETE FROM agenda_typy_dokladov WHERE id = ?", (id,))
    db.commit()
    db.close()


def get_vsetky_typy_dokladov(typ):
    """Vráti zlúčený zoznam typov dokladov — agenda-špecifické majú prioritu nad globálnymi.
    Používa sa vo formulároch pre výber typu dokladu."""
    # Najprv načítaj globálne
    globalne = get_system_catalog(f'typ_dokladu_{typ}')
    # Potom agenda-špecifické
    agenda = get_agenda_typy_dokladov(typ)
    
    # Vytvor slovník podľa kódu — agenda prepíše globálne
    vysledok = {}
    for g in globalne:
        vysledok[g['kod']] = dict(g)
    for a in agenda:
        vysledok[a['kod']] = dict(a)
    
    # Vráť zoradené podľa názvu
    return sorted(vysledok.values(), key=lambda x: x['nazov'])


def get_legal_limit(kod):
    """Vráti hodnotu právneho limitu."""
    item = get_system_catalog_item('limit', kod)
    return item['hodnota_cislo'] if item else None

def update_system_catalog(id, nazov, hodnota=None, hodnota_cislo=None, popis=None, je_aktivny=None, platnost_od=None):
    """Upraví položku systémového katalógu s historickým sledovaním."""
    db = get_db()
    
    # Get old value for history
    cursor = db.execute('SELECT * FROM system_catalog WHERE id = ?', (id,))
    old = cursor.fetchone()
    
    fields = []
    params = []
    if nazov is not None:
        fields.append('nazov = ?')
        params.append(nazov)
    if hodnota is not None:
        fields.append('hodnota = ?')
        params.append(hodnota)
    if hodnota_cislo is not None:
        fields.append('hodnota_cislo = ?')
        params.append(hodnota_cislo)
    if popis is not None:
        fields.append('popis = ?')
        params.append(popis)
    if je_aktivny is not None:
        fields.append('je_aktivny = ?')
        params.append(je_aktivny)
    if platnost_od is not None:
        fields.append('platnost_od = ?')
        params.append(platnost_od)
    if fields:
        query = 'UPDATE system_catalog SET ' + ', '.join(fields) + ' WHERE id = ?'
        params.append(id)
        db.execute(query, params)
        db.commit()
        
        # Record history if numeric value changed
        if old and hodnota_cislo is not None and old['hodnota_cislo'] != hodnota_cislo:
            db.execute('''
                INSERT INTO historicka_hodnota (tabulka, stlpec, zaznam_id, hodnota_cislo, platnost_od, dovody_zmeny)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('system_catalog', 'hodnota_cislo', id, old['hodnota_cislo'], old['platnost_od'], 'Zmena legislatívy'))
            db.commit()
    db.close()


def get_effective_value(kategoria, kod, datum=None):
    """Vráti platnú hodnotu pre daný dátum (default: dnes)."""
    if datum is None:
        datum = datetime.now().strftime('%Y-%m-%d')
    
    db = get_db()
    cursor = db.execute('''
        SELECT * FROM system_catalog 
        WHERE kategoria = ? AND kod = ? AND je_aktivny = 1
        AND (platnost_od IS NULL OR platnost_od <= ?)
        AND (platnost_do IS NULL OR platnost_do >= ?)
        ORDER BY platnost_od DESC LIMIT 1
    ''', (kategoria, kod, datum, datum))
    item = cursor.fetchone()
    db.close()
    return item


def get_dph_sadzba_pre_datum(sadzba_kod, datum=None):
    """Vráti DPH sadzbu platnú pre daný dátum."""
    item = get_effective_value('dph_sadzba', sadzba_kod, datum)
    return item['hodnota_cislo'] if item else None


def get_historicke_hodnoty(tabulka, zaznam_id=None, limit=50):
    """Vráti históriu zmien hodnôt."""
    db = get_db()
    query = 'SELECT * FROM historicka_hodnota WHERE tabulka = ?'
    params = [tabulka]
    if zaznam_id:
        query += ' AND zaznam_id = ?'
        params.append(zaznam_id)
    query += ' ORDER BY created_at DESC LIMIT ?'
    params.append(limit)
    cursor = db.execute(query, params)
    items = cursor.fetchall()
    db.close()
    return items


def ulozit_dph_sadzby_do_dokladu(doklad_id, tabulka, datum=None):
    """
    Uloží aktuálne DPH sadzby priamo do dokladu pre právnu istotu.
    
    Args:
        doklad_id: ID dokladu
        tabulka: 'prijmy' alebo 'vydavky'
        datum: dátum pre ktorý získať sadzby (default: dnes)
    """
    if datum is None:
        datum = datetime.now().strftime('%Y-%m-%d')
    
    db = get_db()
    
    # Získaj aktuálne sadzby
    zakladna = get_dph_sadzba_pre_datum('zakladna', datum) or 23.0
    znizena = get_dph_sadzba_pre_datum('znizena', datum) or 19.0
    super_znizena = get_dph_sadzba_pre_datum('super_znizena', datum) or 5.0
    
    # Ulož do dokladu
    db.execute(f'''
        UPDATE {tabulka} SET
            sadzba_dph_zakladna = ?,
            sadzba_dph_znizena = ?,
            sadzba_dph_super_znizena = ?
        WHERE id = ?
    ''', (zakladna, znizena, super_znizena, doklad_id))
    db.commit()
    db.close()


def ulozit_kontakt_info_do_dokladu(doklad_id, tabulka, kontakt_id=None, adresa_id=None, kontaktna_osoba_id=None):
    """
    Uloží aktuálne kontaktné informácie priamo do dokladu.
    Toto zabezpečí, že doklad obsahuje presné údaje z času vystavenia.
    
    Args:
        doklad_id: ID dokladu
        tabulka: 'prijmy' alebo 'vydavky'
        kontakt_id: ID kontaktu z adresára
        adresa_id: ID doručovacej adresy
        kontaktna_osoba_id: ID kontaktnej osoby
    """
    if not kontakt_id:
        return
    
    db = get_db()
    
    # Načítaj kontakt
    kontakt = db.execute('SELECT * FROM adresar WHERE id = ?', (kontakt_id,)).fetchone()
    if not kontakt:
        db.close()
        return
    
    # Urči stĺpce podľa tabuľky
    if tabulka == 'prijmy':
        prefix = 'odberatel'
        db.execute('UPDATE prijmy SET odberatel_id = ? WHERE id = ?', (kontakt_id, doklad_id))
    else:
        prefix = 'dodavatel'
        db.execute('UPDATE vydavky SET dodavatel_id = ? WHERE id = ?', (kontakt_id, doklad_id))
    
    # Ulož základné údaje
    db.execute(f'''
        UPDATE {tabulka} SET
            {prefix}_nazov = ?,
            {prefix}_ico = ?,
            {prefix}_dic = ?,
            {prefix}_ic_dph = ?,
            {prefix}_adresa = ?,
            {prefix}_mesto = ?,
            {prefix}_psc = ?,
            {prefix}_stat = ?
        WHERE id = ?
    ''', (
        kontakt['nazov'],
        kontakt['ico'] or '',
        kontakt['dic'] or '',
        kontakt['ic_dph'] or '',
        f"{kontakt['sidlo_ulica'] or ''} {kontakt['sidlo_cislo'] or ''}".strip(),
        kontakt['sidlo_mesto'] or '',
        kontakt['sidlo_psc'] or '',
        kontakt['sidlo_stat'] or 'Slovensko',
        doklad_id
    ))
    
    # Ak je zvolená doručovacia adresa, ulož ju
    if adresa_id:
        adresa = db.execute('SELECT * FROM adresar_dorucovacie_adresy WHERE id = ?', (adresa_id,)).fetchone()
        if adresa:
            # Uložíme do poznámky alebo špeciálneho stĺpca
            db.execute(f'''
                UPDATE {tabulka} 
                SET poznamka = COALESCE(poznamka, '') || '\nDoručovacia adresa: ' || ? || ', ' || ? || ' ' || ? || ', ' || ?
                WHERE id = ?
            ''', (
                f"{adresa['ulica'] or ''} {adresa['cislo'] or ''}".strip(),
                adresa['psc'] or '',
                adresa['mesto'] or '',
                adresa['stat'] or 'Slovensko',
                doklad_id
            ))
    
    # Ak je zvolená kontaktná osoba, ulož ju
    if kontaktna_osoba_id:
        osoba = db.execute('SELECT * FROM adresar_kontakty WHERE id = ?', (kontaktna_osoba_id,)).fetchone()
        if osoba:
            db.execute(f'''
                UPDATE {tabulka} 
                SET poznamka = COALESCE(poznamka, '') || '\nKontaktná osoba: ' || ? || ' (' || ? || ')'
                WHERE id = ?
            ''', (
                osoba['meno'] or '',
                osoba['email'] or osoba['telefon'] or '',
                doklad_id
            ))
    
    db.commit()
    db.close()


# ==================== FUNKCIE PRE AGENDY ====================

def get_agendy_dir():
    """Vráti adresár pre agendy."""
    agendy_dir = os.path.join(os.path.dirname(__file__), 'agendy')
    if not os.path.exists(agendy_dir):
        os.makedirs(agendy_dir)
    return agendy_dir


def get_agendy():
    """Vráti zoznam všetkých agend z hlavnej databázy."""
    set_db_path(DEFAULT_DB_PATH)
    db = get_db()
    agendy = db.execute('SELECT * FROM agendy ORDER BY vytvorena DESC').fetchall()
    db.close()
    return agendy


def get_aktivna_agenda():
    """Vráti aktívnu agendu z hlavnej databázy."""
    set_db_path(DEFAULT_DB_PATH)
    db = get_db()
    agenda = db.execute('SELECT * FROM agendy WHERE je_aktivna = 1 LIMIT 1').fetchone()
    db.close()
    return agenda


def vytvorit_agendu(nazov, poznamka='', subor=None, cesta_k_db=None):
    """Vytvorí novú agendu (novú databázu)."""
    agendy_dir = get_agendy_dir()

    # Ak je zadaná cesta k DB, použijeme ju
    if cesta_k_db:
        cesta = cesta_k_db
        # Extrahuj názov súboru z cesty
        subor = os.path.basename(cesta)
    else:
        # Použi zadaný názov súboru alebo vygeneruj z názvu agendy
        if not subor:
            subor = nazov.replace(' ', '_').replace('/', '_').replace('\\', '_') + '.db'
        if not subor.endswith('.db'):
            subor += '.db'
        cesta = os.path.join(agendy_dir, subor)

    # Kontrola či už existuje
    if os.path.exists(cesta):
        return None, 'Agenda s týmto názvom/súborom už existuje'

    # Uisti sa že adresár existuje
    os.makedirs(os.path.dirname(cesta), exist_ok=True)

    # Vytvoriť prázdnu databázu
    conn = sqlite3.connect(cesta)
    conn.close()

    # Nastaviť ako aktuálnu a inicializovať
    set_db_path(cesta)
    init_db()

    # Zapísať do hlavnej databázy
    set_db_path(DEFAULT_DB_PATH)
    db = get_db()
    db.execute('INSERT INTO agendy (nazov, subor, je_aktivna, poznamka) VALUES (?, ?, 1, ?)',
               (nazov, subor, poznamka))
    # Deaktivovať ostatné
    db.execute('UPDATE agendy SET je_aktivna = 0 WHERE subor != ?', (subor,))
    db.commit()
    db.close()

    # Nastaviť späť na novú agendu ako aktívnu
    set_db_path(cesta)

    return cesta, None


def upravit_agendu(subor, nazov=None, poznamka=None, novy_subor=None):
    """Upraví existujúcu agendu (názov, poznámka, prípadne názov súboru)."""
    agendy_dir = get_agendy_dir()
    cesta = os.path.join(agendy_dir, subor)

    if not os.path.exists(cesta):
        return False, 'Súbor agendy neexistuje'

    set_db_path(DEFAULT_DB_PATH)
    db = get_db()

    # Získaj aktuálne hodnoty
    agenda = db.execute('SELECT * FROM agendy WHERE subor = ?', (subor,)).fetchone()
    if not agenda:
        db.close()
        return False, 'Agenda nebola nájdená v databáze'

    aktualny_nazov = agenda['nazov']
    aktualna_poznamka = agenda['poznamka']

    # Použi nové hodnoty alebo ponechaj staré
    novy_nazov = nazov if nazov is not None else aktualny_nazov
    nova_poznamka = poznamka if poznamka is not None else aktualna_poznamka

    # Ak sa mení názov súboru
    if novy_subor and novy_subor != subor:
        if not novy_subor.endswith('.db'):
            novy_subor += '.db'
        nova_cesta = os.path.join(agendy_dir, novy_subor)
        if os.path.exists(nova_cesta):
            db.close()
            return False, 'Agenda s týmto názvom súboru už existuje'
        # Premenovať súbor
        os.rename(cesta, nova_cesta)
        db.execute('UPDATE agendy SET subor = ? WHERE subor = ?', (novy_subor, subor))
        subor = novy_subor

    # Aktualizovať názov a poznámku
    db.execute('UPDATE agendy SET nazov = ?, poznamka = ? WHERE subor = ?',
               (novy_nazov, nova_poznamka, subor))
    db.commit()
    db.close()
    return True, None


def otvorit_agendu(subor):
    """Otvorí existujúcu agendu."""
    agendy_dir = get_agendy_dir()
    cesta = os.path.join(agendy_dir, subor)

    if not os.path.exists(cesta):
        return False, 'Súbor agendy neexistuje'

    set_db_path(cesta)

    # Aktualizovať stav v hlavnej databáze
    set_db_path(DEFAULT_DB_PATH)
    db = get_db()
    db.execute('UPDATE agendy SET je_aktivna = 0')
    db.execute('UPDATE agendy SET je_aktivna = 1 WHERE subor = ?', (subor,))
    db.commit()
    db.close()

    set_db_path(cesta)
    return True, None


def exportovat_agendu(subor):
    """Vráti cestu k exportovanému súboru."""
    agendy_dir = get_agendy_dir()
    zdroj = os.path.join(agendy_dir, subor)
    if not os.path.exists(zdroj):
        return None, 'Súbor agendy neexistuje'

    export_dir = os.path.join(os.path.dirname(__file__), 'exporty')
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    import time
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    ciel = os.path.join(export_dir, f'{subor}_{timestamp}.db')
    shutil.copy2(zdroj, ciel)
    return ciel, None


def importovat_agendu(cesta, novy_nazov=None):
    """Importuje agendu zo súboru."""
    if not os.path.exists(cesta):
        return None, 'Súbor neexistuje'

    agendy_dir = get_agendy_dir()
    nazov = novy_nazov or os.path.splitext(os.path.basename(cesta))[0]
    subor = nazov.replace(' ', '_').replace('/', '_').replace('\\', '_') + '.db'
    ciel = os.path.join(agendy_dir, subor)

    if os.path.exists(ciel):
        return None, 'Agenda s týmto názvom už existuje'

    shutil.copy2(cesta, ciel)

    # Aktivovať
    set_db_path(ciel)
    init_db()

    set_db_path(DEFAULT_DB_PATH)
    db = get_db()
    db.execute('UPDATE agendy SET je_aktivna = 0')
    db.execute('INSERT INTO agendy (nazov, subor, je_aktivna, poznamka) VALUES (?, ?, 1, ?)',
               (nazov, subor, 'Importovaná agenda'))
    db.commit()
    db.close()

    set_db_path(ciel)
    return ciel, None


# ==================== FUNKCIE PRE POLOŽKY PRÍJMOV ====================

def get_prijem_polozky(prijem_id):
    """Vráti položky príjmu (riadky faktúry)."""
    db = get_db()
    polozky = db.execute(
        'SELECT * FROM prijmy_polozky WHERE prijem_id = ? ORDER BY poradie',
        (prijem_id,)
    ).fetchall()
    db.close()
    return polozky


def pridat_prijem_polozku(prijem_id, data):
    """Pridá položku k príjmu."""
    db = get_db()
    db.execute('''
        INSERT INTO prijmy_polozky
        (prijem_id, nazov, mnozstvo, jednotka, jednotkova_cena_bez_dph,
         sadzba_dph, zaklad_dane, dph, celkova_suma, poradie)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        prijem_id, data['nazov'], data.get('mnozstvo', 1),
        data.get('jednotka', 'ks'), data['jednotkova_cena_bez_dph'],
        data.get('sadzba_dph', '20'), data['zaklad_dane'],
        data.get('dph', 0), data['celkova_suma'],
        data.get('poradie', 0)
    ))
    db.commit()
    db.close()


def upravit_prijem_polozku(polozka_id, data):
    """Upraví položku príjmu."""
    db = get_db()
    db.execute('''
        UPDATE prijmy_polozky SET
            nazov = ?, mnozstvo = ?, jednotka = ?,
            jednotkova_cena_bez_dph = ?, sadzba_dph = ?,
            zaklad_dane = ?, dph = ?, celkova_suma = ?
        WHERE id = ?
    ''', (
        data['nazov'], data.get('mnozstvo', 1), data.get('jednotka', 'ks'),
        data['jednotkova_cena_bez_dph'], data.get('sadzba_dph', '20'),
        data['zaklad_dane'], data.get('dph', 0), data['celkova_suma'],
        polozka_id
    ))
    db.commit()
    db.close()


def zmazat_prijem_polozku(polozka_id):
    """Zmaže položku príjmu."""
    db = get_db()
    db.execute('DELETE FROM prijmy_polozky WHERE id = ?', (polozka_id,))
    db.commit()
    db.close()


# ==================== FUNKCIE PRE POLOŽKY VÝDAVKOV ====================

def get_vydavok_polozky(vydavok_id):
    """Vráti položky výdavku (riadky faktúry)."""
    db = get_db()
    polozky = db.execute(
        'SELECT * FROM vydavky_polozky WHERE vydavok_id = ? ORDER BY poradie',
        (vydavok_id,)
    ).fetchall()
    db.close()
    return polozky


def pridat_vydavok_polozku(vydavok_id, data):
    """Pridá položku k výdavku."""
    db = get_db()
    db.execute('''
        INSERT INTO vydavky_polozky
        (vydavok_id, nazov, mnozstvo, jednotka, jednotkova_cena_bez_dph,
         sadzba_dph, zaklad_dane, dph, celkova_suma, poradie)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        vydavok_id, data['nazov'], data.get('mnozstvo', 1),
        data.get('jednotka', 'ks'), data['jednotkova_cena_bez_dph'],
        data.get('sadzba_dph', '20'), data['zaklad_dane'],
        data.get('dph', 0), data['celkova_suma'],
        data.get('poradie', 0)
    ))
    db.commit()
    db.close()


def upravit_vydavok_polozku(polozka_id, data):
    """Upraví položku výdavku."""
    db = get_db()
    db.execute('''
        UPDATE vydavky_polozky SET
            nazov = ?, mnozstvo = ?, jednotka = ?,
            jednotkova_cena_bez_dph = ?, sadzba_dph = ?,
            zaklad_dane = ?, dph = ?, celkova_suma = ?
        WHERE id = ?
    ''', (
        data['nazov'], data.get('mnozstvo', 1), data.get('jednotka', 'ks'),
        data['jednotkova_cena_bez_dph'], data.get('sadzba_dph', '20'),
        data['zaklad_dane'], data.get('dph', 0), data['celkova_suma'],
        polozka_id
    ))
    db.commit()
    db.close()


def zmazat_vydavok_polozku(polozka_id):
    """Zmaže položku výdavku."""
    db = get_db()
    db.execute('DELETE FROM vydavky_polozky WHERE id = ?', (polozka_id,))
    db.commit()
    db.close()


def zmazat_agendu(subor):
    """Zmaže agendu."""
    agendy_dir = get_agendy_dir()
    cesta = os.path.join(agendy_dir, subor)

    if os.path.exists(cesta):
        os.remove(cesta)

    set_db_path(DEFAULT_DB_PATH)
    db = get_db()
    db.execute('DELETE FROM agendy WHERE subor = ?', (subor,))
    db.commit()
    db.close()
    return True


def resetnut_agendu(subor):
    """Resetne agendu - vymaže všetky dáta okrem nastavení."""
    agendy_dir = get_agendy_dir()
    cesta = os.path.join(agendy_dir, subor)

    if not os.path.exists(cesta):
        return False, 'Súbor agendy neexistuje'

    set_db_path(cesta)
    db = get_db()
    cursor = db.cursor()

    # Získať nastavenia
    nastavenia = db.execute('SELECT * FROM nastavenia LIMIT 1').fetchone()

    # Zmazať všetky dáta okrem nastavení a agendy
    tables = ['prijmy', 'vydavky', 'majetok', 'zasoby', 'pohladavky', 'zavazky', 'odvody',
              'ciselniky_dokladov', 'adresar', 'adresar_dorucovacie_adresy', 'adresar_kontakty',
              'adresar_bankove_ucty', 'adresar_poznamky']

    for table in tables:
        try:
            cursor.execute(f'DELETE FROM {table}')
        except:
            pass

    # Obnoviť predvolené číselníky
    cursor.execute('SELECT COUNT(*) FROM ciselniky_dokladov')
    if cursor.fetchone()[0] == 0:
        defaults = [
            ('Faktúra vystavená', 'prijem', 'FV', 'RRRR-NNNNNN', 0, 6, '-', 1, 0, 0, 1, 'Faktúry vystavené odberateľom'),
            ('Pokladničný doklad', 'prijem', 'VPD', 'RRRR-NNNNNN', 0, 6, '-', 1, 0, 0, 1, 'Výdavkový pokladničný doklad'),
            ('Bankový výpis', 'prijem', 'VBÚ', 'RRRR-NNNNNN', 0, 6, '-', 1, 0, 0, 1, 'Bankový výpis - príjem'),
            ('Faktúra prijatá', 'vydavok', 'FP', 'RRRR-NNNNNN', 0, 6, '-', 1, 0, 0, 1, 'Faktúry prijaté od dodávateľov'),
            ('Interný doklad', 'vydavok', 'ID', 'RRRR-NNNNNN', 0, 6, '-', 1, 0, 0, 1, 'Interný doklad'),
            ('Pokladničný doklad výdavok', 'vydavok', 'VPD', 'RRRR-NNNNNN', 0, 6, '-', 1, 0, 0, 1, 'Výdavkový pokladničný doklad'),
            ('Bankový výpis výdavok', 'vydavok', 'VBÚ', 'RRRR-NNNNNN', 0, 6, '-', 1, 0, 0, 1, 'Bankový výpis - výdavok'),
        ]
        for d in defaults:
            cursor.execute('''
                INSERT INTO ciselniky_dokladov
                (nazov, typ_dokladu, prefix, vzor, aktualne_cislo, pocet_cislic,
                 oddelovac, rok_v_cisle, mesiac_v_cisle, den_v_cisle, je_aktivny, poznamka)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', d)

    db.commit()
    db.close()
    return True, None


if __name__ == '__main__':
    init_db()
    print("Databáza inicializovaná.")
