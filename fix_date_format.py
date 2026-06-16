import sqlite3
conn = sqlite3.connect('danova_evidencia.db')
c = conn.cursor()
c.execute("UPDATE zobrazenie SET format_datumu='eu', updated_at=CURRENT_TIMESTAMP")
conn.commit()
c.execute("SELECT format_datumu FROM zobrazenie")
print('format_datumu:', c.fetchone()[0])
conn.close()
