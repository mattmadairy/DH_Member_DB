import sqlite3 
import os
import shutil
import datetime

DB_NAME = "members.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    return conn


# ------------------ Init DB ------------------ #
def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Members table
    c.execute("""
        CREATE TABLE IF NOT EXISTS members (
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
            card_external TEXT,
            deleted INTEGER DEFAULT 0
        )
    """)

    # Dues table (with year column)
    c.execute("""
        CREATE TABLE IF NOT EXISTS dues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            amount REAL,
            payment_date TEXT,
            year TEXT DEFAULT (strftime('%Y','now')),
            method TEXT,
            notes TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
        )
    """)

    # Settings table (dues amounts & default year)
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Ensure default settings exist
    defaults = {
        "dues_probationary": "150",
        "dues_associate": "300",
        "dues_active": "150",
        "default_year": str(datetime.datetime.now().year),
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    conn.commit()
    conn.close()


# ------------------ Migration ------------------ #
def rebuild_table(conn, table_name, schema_sql, required_columns):
    """Rebuild a table to include missing columns while preserving data."""
    c = conn.cursor()

    # Backup original
    backup_table = f"{table_name}_backup_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    c.execute(f"ALTER TABLE {table_name} RENAME TO {backup_table}")

    # Create new table with proper schema
    c.execute(schema_sql)

    # Copy common columns
    existing_cols = [col[1] for col in c.execute(f"PRAGMA table_info({backup_table})")]
    common_cols = [col for col in required_columns if col in existing_cols]

    if common_cols:
        cols_str = ", ".join(common_cols)
        c.execute(f"INSERT INTO {table_name} ({cols_str}) SELECT {cols_str} FROM {backup_table}")

    # Drop backup
    c.execute(f"DROP TABLE {backup_table}")


def migrate_all():
    conn = get_connection()
    c = conn.cursor()

    # Members migration
    c.execute("PRAGMA table_info(members)")
    existing_cols = [col[1] for col in c.fetchall()]
    required_members = [
        "id", "badge_number", "membership_type", "first_name", "last_name", "dob",
        "email", "phone", "address", "city", "state", "zip", "join_date",
        "email2", "sponsor", "card_internal", "card_external", "deleted"
    ]

    if set(required_members) != set(existing_cols):
        print("⚠️ Rebuilding members table with correct schema")
        rebuild_table(conn, "members", """
            CREATE TABLE members (
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
                card_external TEXT,
                deleted INTEGER DEFAULT 0
            )
        """, required_members)

    # Dues migration
    c.execute("PRAGMA table_info(dues)")
    existing_cols = [col[1] for col in c.fetchall()]
    required_dues = ["id", "member_id", "amount", "payment_date", "year", "method", "notes"]

    if set(required_dues) != set(existing_cols):
        print("⚠️ Rebuilding dues table with correct schema")
        rebuild_table(conn, "dues", """
            CREATE TABLE dues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER,
                amount REAL,
                payment_date TEXT,
                year TEXT DEFAULT (strftime('%Y','now')),
                method TEXT,
                notes TEXT,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
            )
        """, required_dues)

    # Settings table (ensure exists + defaults)
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    defaults = {
        "dues_probationary": "150",
        "dues_associate": "300",
        "dues_active": "150",
        "default_year": str(datetime.datetime.now().year),
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    conn.commit()
    conn.close()


# ------------------ Settings Helpers ------------------ #
def get_setting(key):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def set_setting(key, value):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()


def get_default_year():
    settings = get_all_settings()
    return int(settings.get("default_year", datetime.datetime.now().year))


def get_expected_dues(membership_type):
    """Return expected yearly dues for a given membership type from settings."""
    settings = get_all_settings()
    mapping = {
        "Probationary": int(settings.get("dues_probationary", 150)),
        "Associate": int(settings.get("dues_associate", 300)),
        "Active": int(settings.get("dues_active", 150)),
    }
    return mapping.get(membership_type, 0)


# ------------------ Member Functions ------------------ #
def add_member(data):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO members (
            badge_number, membership_type, first_name, last_name, dob,
            email, phone, address, city, state, zip,
            join_date, email2, sponsor, card_internal, card_external
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()
    member_id = c.lastrowid
    conn.close()
    return member_id


def update_member(member_id, data):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE members SET
            badge_number=?, membership_type=?, first_name=?, last_name=?, dob=?,
            email=?, phone=?, address=?, city=?, state=?, zip=?,
            join_date=?, email2=?, sponsor=?, card_internal=?, card_external=?
        WHERE id=?
    """, data + (member_id,))
    conn.commit()
    conn.close()


def delete_member(member_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM members WHERE id=?", (member_id,))
    conn.commit()
    conn.close()


def soft_delete_member_by_id(member_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE members SET deleted=1 WHERE id=?", (member_id,))
    conn.commit()
    conn.close()


def restore_member(member_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE members SET deleted=0 WHERE id=?", (member_id,))
    conn.commit()
    conn.close()


def get_member_by_id(member_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE id=?", (member_id,))
    row = c.fetchone()
    conn.close()
    return row


def get_all_members():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE deleted=0")
    rows = c.fetchall()
    conn.close()
    return rows


def get_deleted_members():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE deleted=1")
    rows = c.fetchall()
    conn.close()
    return rows


# ------------------ Dues Functions ------------------ #
def add_dues_payment(member_id, amount, payment_date, method, notes, year=None):
    # If caller doesn't provide year (or provides empty string), use default year setting.
    if not year:
        year = get_default_year()
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO dues (member_id, amount, payment_date, year, method, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (member_id, amount, payment_date, str(year), method, notes))
    conn.commit()
    conn.close()


def get_dues_by_member(member_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT id, member_id, amount, payment_date, year, method, notes
        FROM dues
        WHERE member_id=?
        ORDER BY payment_date DESC
    """, (member_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def get_dues_payment_by_id(dues_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT id, member_id, amount, payment_date, year, method, notes
        FROM dues
        WHERE id=?
    """, (dues_id,))
    row = c.fetchone()
    conn.close()
    return row


def update_dues_payment(dues_id, amount, payment_date, method, notes, year=None):
    # Respect explicit year if provided; otherwise use default year setting
    if not year:
        year = get_default_year()
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE dues
        SET amount=?, payment_date=?, year=?, method=?, notes=?
        WHERE id=?
    """, (amount, payment_date, str(year), method, notes, dues_id))
    conn.commit()
    conn.close()


def delete_dues_payment(dues_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM dues WHERE id=?", (dues_id,))
    conn.commit()
    conn.close()

def get_dues_report(membership_type="All"):
    conn = get_connection()
    cur = conn.cursor()

    query = """
    SELECT 
        m.first_name,
        m.last_name,
        m.membership_type,
        COALESCE(SUM(d.amount), 0) AS paid,
        expected.amount AS expected,
        expected.amount - COALESCE(SUM(d.amount), 0) AS outstanding,
        m.badge_number,
        MAX(d.payment_date) AS last_payment,
        COALESCE(d.year, strftime('%Y','now')) AS year
    FROM members m
    LEFT JOIN dues d ON d.member_id = m.id
    LEFT JOIN expected_dues expected 
        ON expected.membership_type = m.membership_type
    WHERE m.deleted = 0
    """
    params = []

    if membership_type != "All":
        query += " AND m.membership_type = ?"
        params.append(membership_type)

    query += """
    GROUP BY m.id, year
    ORDER BY year DESC, m.last_name, m.first_name
    """

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows


# ------------------ Reporting Functions ------------------ #
def _dues_settings_tuple():
    """Return dues amounts for CASE expressions (Probationary, Associate, Active)."""
    try:
        dues_prob = int(get_setting("dues_probationary") or 150)
        dues_assoc = int(get_setting("dues_associate") or 300)
        dues_active = int(get_setting("dues_active") or 150)
    except ValueError:
        dues_prob, dues_assoc, dues_active = 150, 300, 150
    return dues_prob, dues_assoc, dues_active


def get_payments_by_year(year, included_types):
    conn = get_connection()
    c = conn.cursor()

    placeholders = ",".join("?" * len(included_types))
    query = f"""
        SELECT m.first_name, m.last_name, m.membership_type,
               IFNULL(SUM(d.amount), 0) as total_paid,
               s.value as expected_dues,
               (CAST(s.value AS INT) - IFNULL(SUM(d.amount), 0)) as outstanding,
               m.badge_number,
               MAX(d.payment_date) as last_payment
        FROM members m
        LEFT JOIN dues d
            ON m.id = d.member_id AND d.year = ?
        LEFT JOIN settings s
            ON s.key = CASE m.membership_type
                WHEN 'Probationary' THEN 'dues_probationary'
                WHEN 'Associate' THEN 'dues_associate'
                WHEN 'Active' THEN 'dues_active'
                ELSE 'dues_active'
            END
        WHERE m.membership_type IN ({placeholders})
        GROUP BY m.id
        ORDER BY m.last_name, m.first_name
    """
    c.execute(query, (year, *included_types))
    rows = c.fetchall()
    conn.close()
    return rows


def get_outstanding_dues(year, included_types):
    conn = get_connection()
    c = conn.cursor()

    placeholders = ",".join("?" * len(included_types))
    query = f"""
        SELECT m.first_name, m.last_name, m.membership_type,
               IFNULL(SUM(d.amount), 0) as total_paid,
               s.value as expected_dues,
               (CAST(s.value AS INT) - IFNULL(SUM(d.amount), 0)) as outstanding,
               m.badge_number,
               MAX(d.payment_date) as last_payment
        FROM members m
        LEFT JOIN dues d
            ON m.id = d.member_id AND d.year = ?
        LEFT JOIN settings s
            ON s.key = CASE m.membership_type
                WHEN 'Probationary' THEN 'dues_probationary'
                WHEN 'Associate' THEN 'dues_associate'
                WHEN 'Active' THEN 'dues_active'
                ELSE 'dues_active'
            END
        WHERE m.membership_type IN ({placeholders})
        GROUP BY m.id
        HAVING outstanding > 0
        ORDER BY m.last_name, m.first_name
    """
    c.execute(query, (year, *included_types))
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_membership_types():
    """Return a list of distinct membership types currently in the database."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT membership_type FROM members WHERE membership_type IS NOT NULL ORDER BY membership_type")
    types = [row[0] for row in cur.fetchall()]
    conn.close()
    return types


# ------------------ Settings Table ------------------ #
def init_settings():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Insert defaults if not already present
    defaults = {
        "dues_probationary": "150",
        "dues_associate": "300",
        "dues_active": "150",
        "default_year": str(datetime.datetime.now().year)
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    conn.commit()
    conn.close()


def get_setting(key, default=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default


def set_setting(key, value):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()


def get_all_settings():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT key, value FROM settings")
    rows = c.fetchall()
    conn.close()
    return {k: v for k, v in rows}


# ------------------ Auto Init & Migrate ------------------ #
if not os.path.exists(DB_NAME):
    init_db()
    init_settings()
else:
    init_db()
    migrate_all()
    init_settings()

