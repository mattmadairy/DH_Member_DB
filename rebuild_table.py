import sqlite3

DB_FILE = "members.db"

# Connect to DB
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# 1. Rename old table
c.execute("ALTER TABLE members RENAME TO members_old;")

# 2. Create new members table with correct schema
c.execute("""
CREATE TABLE members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    badge_number TEXT,
    membership_type TEXT,
    first_name TEXT,
    last_name TEXT,
    date_of_birth TEXT,
    email_address TEXT,
    phone_number TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    join_date TEXT,
    email_address_2 TEXT,
    sponsor TEXT,
    card_fob_internal_number TEXT,
    card_fob_external_number TEXT,
    deleted_at TEXT
)
""")

# 3. Copy over data from old table to new one
# Adjust the column names here to match old table structure if different
c.execute("""
INSERT INTO members (
    id, badge_number, membership_type, first_name, last_name, date_of_birth,
    email_address, phone_number, address, city, state, zip_code, join_date,
    email_address_2, sponsor, card_fob_internal_number, card_fob_external_number, deleted_at
)
SELECT
    id, badge_number, membership_type, first_name, last_name, date_of_birth,
    email_address, phone_number, address, city, state, zip_code, join_date,
    email_address_2, sponsor, card_fob_internal_number, card_fob_external_number, deleted_at
FROM members_old;
""")

# 4. Drop the old table
c.execute("DROP TABLE members_old;")

conn.commit()
conn.close()

print("✅ Members table rebuilt successfully.")
