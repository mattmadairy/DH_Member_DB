import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "members.db")
CURRENT_YEAR = 2025  # change as needed

def migrate():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Step 1: check if "dues" table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dues'")
    if c.fetchone():
        # Step 2: rename dues -> YEAR_dues
        new_table = f"{CURRENT_YEAR}_dues"
        c.execute(f"ALTER TABLE dues RENAME TO \"{new_table}\"")

        # Step 3: rebuild table without year column
        c.execute(f"""
        CREATE TABLE IF NOT EXISTS "{new_table}_new" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_date TEXT NOT NULL,
            payment_method TEXT,
            notes TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
        )
        """)

        # Step 4: copy data over (ignoring the old 'year' column)
        c.execute(f"""
        INSERT INTO "{new_table}_new" (id, member_id, amount, payment_date, payment_method, notes)
        SELECT id, member_id, amount, payment_date, payment_method, notes
        FROM "{new_table}"
        """)

        # Step 5: drop old renamed table and replace
        c.execute(f"DROP TABLE \"{new_table}\"")
        c.execute(f"ALTER TABLE \"{new_table}_new\" RENAME TO \"{new_table}\"")

    conn.commit()
    conn.close()
    print(f"✅ Migration complete. '{CURRENT_YEAR}_dues' table ready (without year column).")

if __name__ == "__main__":
    migrate()
