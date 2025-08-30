import sqlite3

# Connect to your database (or create it if it doesn't exist)
conn = sqlite3.connect("members.db")
cursor = conn.cursor()

# ---------- Roles Table ----------
cursor.execute("""
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL,
    position TEXT NOT NULL,        -- president, vice-president, treasurer, secretary, trustee
    term_start DATE,               -- start date of term
    term_end DATE,                 -- end date of term
    FOREIGN KEY(member_id) REFERENCES members(id)
)
""")


# Commit and close
conn.commit()
conn.close()

print("Tables 'roles' created successfully.")
