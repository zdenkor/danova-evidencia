"""
Database Migration System
Version format: RRRR-MM-DD-xxxx (e.g. 2026-06-16-0001)
"""

import os
import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / 'migrations'

def get_db_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_schema_version_table(conn):
    conn.execute('''
        CREATE TABLE IF NOT EXISTS schema_version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL UNIQUE,
            applied_at TEXT NOT NULL DEFAULT (datetime('now')),
            description TEXT
        )
    ''')
    conn.commit()

def get_applied_versions(conn):
    cursor = conn.execute('SELECT version FROM schema_version ORDER BY version')
    return {row['version'] for row in cursor.fetchall()}

def get_migration_files():
    if not MIGRATIONS_DIR.exists():
        return []
    files = sorted(MIGRATIONS_DIR.glob('*.sql'))
    return files

def parse_version_from_filename(filename):
    # Format: YYYY-MM-DD-NNNN_description.sql
    stem = filename.stem
    parts = stem.split('_', 1)
    version = parts[0]
    description = parts[1] if len(parts) > 1 else ''
    return version, description

def apply_migration(conn, migration_file):
    version, description = parse_version_from_filename(migration_file)
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    # Execute migration
    conn.executescript(sql)
    
    # Record version
    conn.execute(
        'INSERT OR IGNORE INTO schema_version (version, description) VALUES (?, ?)',
        (version, description)
    )
    conn.commit()
    
    print(f"✓ Applied migration {version}: {description}")
    return version

def migrate(db_path):
    """Run all pending migrations"""
    conn = get_db_connection(db_path)
    try:
        ensure_schema_version_table(conn)
        applied = get_applied_versions(conn)
        files = get_migration_files()
        
        applied_count = 0
        for migration_file in files:
            version, _ = parse_version_from_filename(migration_file)
            if version not in applied:
                apply_migration(conn, migration_file)
                applied_count += 1
        
        if applied_count == 0:
            print("Database is up to date.")
        else:
            print(f"Applied {applied_count} migration(s).")
            
        return applied_count
    finally:
        conn.close()

def get_current_version(db_path):
    """Get current database version"""
    conn = get_db_connection(db_path)
    try:
        ensure_schema_version_table(conn)
        cursor = conn.execute(
            'SELECT version FROM schema_version ORDER BY version DESC LIMIT 1'
        )
        row = cursor.fetchone()
        return row['version'] if row else None
    finally:
        conn.close()

def create_migration(description):
    """Create a new migration file with next version number"""
    from datetime import datetime
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Find next sequence number for today
    existing = list(MIGRATIONS_DIR.glob(f'{today}-*.sql'))
    if existing:
        nums = []
        for f in existing:
            v, _ = parse_version_from_filename(f)
            parts = v.split('-')
            if len(parts) == 4:
                nums.append(int(parts[3]))
        next_num = max(nums) + 1 if nums else 1
    else:
        next_num = 1
    
    version = f"{today}-{next_num:04d}"
    safe_desc = description.replace(' ', '_').lower()
    filename = f"{version}_{safe_desc}.sql"
    filepath = MIGRATIONS_DIR / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"-- Migration: {version}\n")
        f.write(f"-- Date: {today}\n")
        f.write(f"-- Description: {description}\n\n")
        f.write("-- Add your SQL here\n")
    
    print(f"Created migration: {filepath}")
    return filepath

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'create':
        desc = sys.argv[2] if len(sys.argv) > 2 else 'new_migration'
        create_migration(desc)
    else:
        # Default: migrate main DB
        from database import DB_PATH
        migrate(DB_PATH)
