import sqlite3
import shutil
import os

DB_NAME = "members.db"

def migrate_table(table_name, schema_sql, required_cols):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # --- 1. Create new table ---
    c.execute(f"DROP TABLE IF EXISTS {table_name}_new")
    c.execute(schema_sql)

    # --- 2. Copy matching columns ---
    c.execute(f"PRAGMA table_info({table_name})")
    existing_cols = [row[1] for row in c.fetchall()]

    copy_cols = [col for col in required_cols if col in existing_cols]
    col_str = ", ".join(copy_cols)

    if copy_cols:
        c.execute(f"""
            INSERT INTO {table_name}_new ({col_str})
            SELECT {col_str} FROM {table_name}
        """)
        print(f"[{table_name}] Copied columns: {col_str}")
    else:
        print(f"[{table_name}] No columns matched, skipped data copy.")

    # --- 3. Replace old table ---
    c.execute(f"DROP TABLE {table_name}")
    c.execute(f"ALTER TABLE {table_name}_new RENAME TO {table_name}")

    conn.commit()
    conn.close()


def migrate_all():
    if not os.path.exists(DB_NAME):
        print("No database found, nothing to migrate.")
        return

    # Backup first
    backup_name = DB_NAME + ".backup"
    shutil.copy2(DB_NAME, backup_name)
    print(f"Backup created: {backup_name}")

    # --- Members table ---
    members_schema = """
        CREATE TABLE IF NOT EXISTS members_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            badge_number TEXT,
            membership_type TEXT,
            first_name TEXT,
            last_name TEXT,
            dob TEXT,
            email TEXT,
            phone TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            zip TEXT,
            join_date TEXT,
            email2 TEXT,
            sponsor TEXT,
            card_internal TEXT,
            card_external TEXT
        )
    """
    members_cols = [
        "id", "badge_number", "membership_type", "first_name", "last_name", "dob",
        "email", "phone", "address", "city", "state", "zip",
        "join_date", "email2", "sponsor", "card_internal", "card_external"
    ]
    migrate_table("members", members_schema, members_cols)

    # --- Dues table ---
    dues_schema = """
        CREATE TABLE IF NOT EXISTS dues_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            amount REAL,
            payment_date TEXT,
            method TEXT,
            notes TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
        )
    """
    dues_cols = ["id", "member_id", "amount", "payment_date", "method", "notes"]
    migrate_table("dues", dues_schema, dues_cols)

    print("✅ Migration completed successfully for both members and dues.")


if __name__ == "__main__":
    migrate_all()
