import sqlite3
import os
import shutil
from datetime import datetime

# Import migration system
from migrations import migrate, get_current_version

# Globálna premenná pre aktuálnu databázu - môže sa zmeniť podľa agendy
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), 'danova_evidencia.db')
DB_PATH = DEFAULT_DB_PATH


def set_db_path(path):
    """Nastaví cestu k databázovému súboru."""
    global DB_PATH
    DB_PATH = path


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    # Run migrations first
    migrate(DB_PATH)
    
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


def vytvorit_agendu(nazov, poznamka=''):
    """Vytvorí novú agendu (novú databázu)."""
    agendy_dir = get_agendy_dir()
    subor = nazov.replace(' ', '_').replace('/', '_').replace('\\', '_') + '.db'
    cesta = os.path.join(agendy_dir, subor)

    # Kontrola či už existuje
    if os.path.exists(cesta):
        return None, 'Agenda s týmto názvom už existuje'

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
