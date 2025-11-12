"""
Database migration script to add overextended columns
"""

import sqlite3
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from src.database import ScannerDatabase
from config.settings import DB_PATH

def migrate_database():
    """Add new overextended columns to existing database"""
    print("🔄 Migrating Database for Overextended Feature")
    print("=" * 50)
    
    if not os.path.exists(DB_PATH):
        print("❌ Database file not found")
        return
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(scan_results)")
        columns = [col[1] for col in cursor.fetchall()]
        
        new_columns = [
            ('is_overextended', 'BOOLEAN DEFAULT 0'),
            ('swing_low', 'REAL'),
            ('overextended_threshold', 'REAL'),
            ('current_price', 'REAL')
        ]
        
        added_columns = []
        
        for col_name, col_type in new_columns:
            if col_name not in columns:
                try:
                    cursor.execute(f"ALTER TABLE scan_results ADD COLUMN {col_name} {col_type}")
                    added_columns.append(col_name)
                    print(f"✅ Added column: {col_name}")
                except Exception as e:
                    print(f"❌ Error adding column {col_name}: {e}")
        
        if added_columns:
            conn.commit()
            print(f"✅ Migration complete! Added {len(added_columns)} columns")
        else:
            print("ℹ️  No migration needed, all columns exist")
        
        # Verify the updated schema
        cursor.execute("PRAGMA table_info(scan_results)")
        final_columns = [col[1] for col in cursor.fetchall()]
        print(f"\n📋 Current scan_results columns: {', '.join(final_columns)}")

if __name__ == "__main__":
    migrate_database()