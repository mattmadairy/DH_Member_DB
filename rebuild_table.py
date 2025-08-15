import sqlite3

DB_FILE = "members.db"

# Columns your current code expects
expected_columns = [
    ("badge_number", "TEXT"),
    ("first_name", "TEXT"),
    ("last_name", "TEXT"),
    ("address", "TEXT"),
    ("city", "TEXT"),
    ("state", "TEXT"),
    ("zip_code", "TEXT"),
    ("phone_number", "TEXT"),
    ("email_address", "TEXT"),
    ("dob", "TEXT"),
    ("membership_type", "TEXT"),
    ("start_date", "TEXT"),
    ("end_date", "TEXT"),
    ("notes", "TEXT"),
    ("sponsor", "TEXT"),
    ("card_fob_internal", "TEXT"),
    ("card_fob_external", "TEXT"),
    ("created_at", "TEXT"),
    ("updated_at", "TEXT"),
    ("deleted_at", "TEXT")
]

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# Get current columns in the table
cursor.execute("PRAGMA table_info(members)")
existing_columns = [row[1] for row in cursor.fetchall()]

# Add any missing columns
for col_name, col_type in expected_columns:
    if col_name not in existing_columns:
        cursor.execute(f"ALTER TABLE members ADD COLUMN {col_name} {col_type}")
        print(f"Added missing column: {col_name}")

conn.commit()
conn.close()

print("Database schema updated successfully!")
