import sqlite3
conn = sqlite3.connect('danova_evidencia.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='zobrazenie'")
if not c.fetchone():
    c.execute('''
        CREATE TABLE zobrazenie (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tema TEXT DEFAULT 'light',
            hustota TEXT DEFAULT 'normal',
            format_datumu TEXT DEFAULT 'sk',
            format_cisla TEXT DEFAULT 'sk',
            format_meny TEXT DEFAULT 'sk',
            jazyk TEXT DEFAULT 'sk',
            font_family TEXT DEFAULT '',
            font_size TEXT DEFAULT '16',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute("INSERT INTO zobrazenie (tema, hustota) VALUES ('light', 'normal')")
    conn.commit()
c.execute("UPDATE zobrazenie SET tema='dark', format_datumu='eu', format_meny='symbol', font_size='18', updated_at=CURRENT_TIMESTAMP")
conn.commit()
c.execute("SELECT * FROM zobrazenie")
print('Row:', c.fetchone())
conn.close()
