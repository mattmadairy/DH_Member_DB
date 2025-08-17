import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "members.db")

def migrate():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # --- Ensure deleted_at column exists in members ---
    c.execute("PRAGMA table_info(members)")
    columns = [col[1] for col in c.fetchall()]

    if "deleted_at" not in columns:
        print("Adding deleted_at column to members table...")
        c.execute("ALTER TABLE members ADD COLUMN deleted_at DATETIME")
        print("Column added successfully.")
    else:
        print("deleted_at column already exists. Skipping.")

    # --- Ensure deletion_log table exists ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS deletion_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            deleted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members(id)
        )
    """)
    print("Ensured deletion_log table exists.")

    conn.commit()
    conn.close()
    print("Migration complete ✅")

if __name__ == "__main__":
    migrate()
