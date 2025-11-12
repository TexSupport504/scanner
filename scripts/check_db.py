import sqlite3

conn = sqlite3.connect("scanner.db")
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("Tables in scanner.db:")
for table in tables:
    print(f"  - {table[0]}")
    
conn.close()
