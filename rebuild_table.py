import sqlite3

db_path = "members.db"  # update path if needed

conn = sqlite3.connect(db_path)
c = conn.cursor()

try:
    # Add the column if it doesn’t already exist
    c.execute("ALTER TABLE members ADD COLUMN deleted INTEGER DEFAULT 0")
    print("✅ 'deleted' column added.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("ℹ️ 'deleted' column already exists, no changes made.")
    else:
        raise

conn.commit()
conn.close()
