"""
Verzovaný import/export formát s kontrolou kompatibility schémy.

Formát exportu:
{
    "format_version": "1.0",
    "app_version": "2026-06-16-0001",
    "export_date": "2026-06-16T10:30:00",
    "schema_version": "2026-06-16-0004",
    "schema_hash": "sha256:abc123...",
    "data": {
        "prijmy": [...],
        "vydavky": [...],
        "ciselniky": [...],
        "sablony_poloziek": [...],
        "system_catalog": [...]
    }
}
"""

import json
import hashlib
import sqlite3
from datetime import datetime
from database import get_db, DB_PATH

FORMAT_VERSION = "1.0"


def _get_schema_hash(db_path):
    """Vypočíta hash schémy databázy pre kontrolu integrity."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Získaj DDL všetkých tabuliek
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL ORDER BY name")
    schemas = [row['sql'] for row in cursor.fetchall()]
    
    # Získaj DDL indexov
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL ORDER BY name")
    indexes = [row['sql'] for row in cursor.fetchall()]
    
    conn.close()
    
    full_schema = '\n'.join(schemas + indexes)
    return 'sha256:' + hashlib.sha256(full_schema.encode('utf-8')).hexdigest()


def _get_schema_version(db_path):
    """Získa aktuálnu verziu schémy z databázy."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1")
        row = cursor.fetchone()
        return row['version'] if row else 'unknown'
    except sqlite3.OperationalError:
        return 'unknown'
    finally:
        conn.close()


def export_data(db_path, app_version):
    """Exportuje všetky dáta do verzovaného JSON formátu."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Zoznam tabuliek na export
    tables = ['prijmy', 'vydavky', 'ciselniky', 'sablony_poloziek', 'system_catalog', 'historicka_hodnota']
    
    data = {}
    for table in tables:
        try:
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            # Konvertuj sqlite3.Row na dict
            data[table] = [dict(row) for row in rows]
        except sqlite3.OperationalError:
            # Tabuľka neexistuje - preskoč
            data[table] = []
    
    conn.close()
    
    export = {
        "format_version": FORMAT_VERSION,
        "app_version": app_version,
        "export_date": datetime.now().isoformat(),
        "schema_version": _get_schema_version(db_path),
        "schema_hash": _get_schema_hash(db_path),
        "data": data
    }
    
    return export


def validate_import(import_data, current_db_path):
    """
    Validuje importované dáta.
    
    Returns:
        (is_valid, errors, warnings)
    """
    errors = []
    warnings = []
    
    # Kontrola formátu
    if 'format_version' not in import_data:
        errors.append("Chýba format_version")
    elif import_data['format_version'] != FORMAT_VERSION:
        warnings.append(f"Format version {import_data['format_version']} != {FORMAT_VERSION}")
    
    if 'data' not in import_data:
        errors.append("Chýbajú dáta")
        return False, errors, warnings
    
    # Kontrola schémy
    current_schema = _get_schema_version(current_db_path)
    import_schema = import_data.get('schema_version', 'unknown')
    
    if import_schema != current_schema:
        warnings.append(f"Verzia schémy sa líši: import={import_schema}, aktuálna={current_schema}")
    
    # Kontrola hashu schémy
    current_hash = _get_schema_hash(current_db_path)
    import_hash = import_data.get('schema_hash')
    
    if import_hash and import_hash != current_hash:
        warnings.append("Hash schémy sa líši - môžu chýbať stĺpce alebo tabuľky")
    
    # Kontrola dát
    data = import_data.get('data', {})
    required_tables = ['prijmy', 'vydavky']
    
    for table in required_tables:
        if table not in data:
            warnings.append(f"Chýba tabuľka {table} v dátach")
    
    return len(errors) == 0, errors, warnings


def import_data(import_data, db_path, mode='merge'):
    """
    Importuje dáta do databázy.
    
    Args:
        import_data: dict s dátami
        db_path: cesta k databáze
        mode: 'merge' (pridá k existujúcim) alebo 'replace' (vymaže existujúce)
    
    Returns:
        (success, message, stats)
    """
    is_valid, errors, warnings = validate_import(import_data, db_path)
    
    if not is_valid:
        return False, f"Validácia zlyhala: {'; '.join(errors)}", {}
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    data = import_data.get('data', {})
    stats = {}
    
    # Tabuľky v poradí závislostí
    tables_order = ['system_catalog', 'ciselniky', 'sablony_poloziek', 'prijmy', 'vydavky', 'historicka_hodnota']
    
    if mode == 'replace':
        # Vymaž dáta v opačnom poradí (najprv závislé)
        for table in reversed(tables_order):
            if table in data:
                try:
                    cursor.execute(f"DELETE FROM {table}")
                    stats[f"{table}_deleted"] = cursor.rowcount
                except sqlite3.OperationalError:
                    pass
    
    # Importuj dáta
    for table in tables_order:
        if table not in data or not data[table]:
            continue
        
        try:
            # Získaj stĺpce
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [row['name'] for row in cursor.fetchall()]
            
            # Filtrované dáta - iba stĺpce ktoré existujú
            filtered_rows = []
            for row in data[table]:
                filtered = {k: v for k, v in row.items() if k in columns}
                if filtered:
                    filtered_rows.append(filtered)
            
            if not filtered_rows:
                continue
            
            # Vlož dáta
            placeholders = ', '.join(['?' for _ in filtered_rows[0]])
            columns_str = ', '.join(filtered_rows[0].keys())
            
            inserted = 0
            for row in filtered_rows:
                try:
                    cursor.execute(
                        f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})",
                        list(row.values())
                    )
                    inserted += 1
                except sqlite3.IntegrityError:
                    # Duplicita alebo constraint - preskoč
                    pass
            
            stats[f"{table}_inserted"] = inserted
            
        except sqlite3.OperationalError as e:
            stats[f"{table}_error"] = str(e)
    
    conn.commit()
    conn.close()
    
    total_inserted = sum(v for k, v in stats.items() if k.endswith('_inserted'))
    message = f"Importovaných {total_inserted} záznamov"
    if warnings:
        message += f" (varovania: {len(warnings)})"
    
    return True, message, stats
