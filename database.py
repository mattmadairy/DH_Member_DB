# database.py
# Database management for members, dues, and work hours
# This module handles SQLite database operations for a membership management system.
# It includes functions for initializing the database, managing members and dues,

import sqlite3 
import os
import shutil
from datetime import datetime

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
        "dues_life": "0",
        "default_year": str(datetime.datetime.now().year),
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

     # At the end of init_db()
    init_work_hours_table()

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

    # ---------------- Members Migration ----------------
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

    # ---------------- Dues Migration ----------------
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

    # ---------------- Settings Table ----------------
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
        "dues_life": "0",
        "default_year": str(datetime.now().year),
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    # ---------------- Work Hours Migration ----------------
    c.execute("PRAGMA table_info(work_hours)")
    existing_cols = [col[1] for col in c.fetchall()]
    required_work_hours = ["id", "member_id", "date", "hours", "work_type", "notes"]

    if not existing_cols:
        print("⚠️ Creating work_hours table")
        c.execute("""
            CREATE TABLE work_hours (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                hours REAL NOT NULL,
                work_type TEXT,
                notes TEXT,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
            )
        """)

    conn.commit()
    conn.close()

    # ---------------- Meeting Attendance Migration ----------------
    c.execute("PRAGMA table_info(meeting_attendance)")
    existing_cols = [col[1] for col in c.fetchall()]
    required_meeting_attendance = ["id", "member_id", "meeting_date", "attended", "notes"]

    if not existing_cols:
        print("⚠️ Creating meeting_attendance table")
        c.execute("""
            CREATE TABLE meeting_attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER NOT NULL,
                meeting_date TEXT NOT NULL,
                attended INTEGER NOT NULL DEFAULT 1,
                notes TEXT,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
            )
        """)



# ------------------ Settings Helpers ------------------ #
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


def get_default_year():
    settings = get_all_settings()
    return int(settings.get("default_year", datetime.now().year))



def get_expected_dues(membership_type):
    """Return expected yearly dues for a given membership type from settings."""
    settings = get_all_settings()
    mapping = {
        "Probationary": int(settings.get("dues_probationary", 150)),
        "Associate": int(settings.get("dues_associate", 300)),
        "Active": int(settings.get("dues_active", 150)),
        "Life": int(settings.get("dues_life", 0)),
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


def permanent_delete_member(member_id):
    """
    Permanently delete a member from the database.
    Unlike soft_delete_member_by_id, this removes the row completely.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM members WHERE id = ?", (member_id,))
        conn.commit()
    finally:
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


def insert_member_from_dict(data: dict):
    """
    Insert a member using a dictionary (from CSV).
    Keys must match the members table schema.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO members (
                badge_number, membership_type, first_name, last_name, dob,
                email, phone, address, city, state, zip,
                join_date, email2, sponsor, card_internal, card_external
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("badge_number"),
            data.get("membership_type"),
            data.get("first_name"),
            data.get("last_name"),
            data.get("dob"),
            data.get("email"),
            data.get("phone"),
            data.get("address"),
            data.get("city"),
            data.get("state"),
            data.get("zip"),
            data.get("join_date"),
            data.get("email2"),
            data.get("sponsor"),
            data.get("card_internal"),
            data.get("card_external"),
        ))
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()


# ------------------ Deleted Members Functions ------------------ #
def ensure_deleted_members_table():
    conn = get_connection()
    c = conn.cursor()
    # Check if table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='deleted_members'")
    if not c.fetchone():
        # Create table
        c.execute("""
            CREATE TABLE deleted_members (
                id INTEGER PRIMARY KEY,
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
                deleted_at TEXT
            )
        """)
    else:
        # Ensure 'deleted_at' column exists
        c.execute("PRAGMA table_info(deleted_members)")
        columns = [row[1] for row in c.fetchall()]
        if 'deleted_at' not in columns:
            c.execute("ALTER TABLE deleted_members ADD COLUMN deleted_at TEXT")
    conn.commit()
    conn.close()


def insert_deleted_member(member_data, deleted_at):
    """
    Insert a member into the deleted_members table with the current columns dynamically.
    member_data: tuple from get_member_by_id (full member row)
    deleted_at: timestamp string
    """
    import sqlite3
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # 1️⃣ Get column names of deleted_members table
    c.execute("PRAGMA table_info(deleted_members)")
    columns = [col[1] for col in c.fetchall()]  # col[1] = name

    # 2️⃣ Exclude auto-increment ID if present and not in member_data
    if "ID" in columns:
        columns.remove("ID")

    # 3️⃣ Prepare values in the same order as columns
    values = []
    for col in columns:
        if col == "Deleted_At":
            values.append(deleted_at)
        else:
            # map by position from member_data assuming order matches members table
            idx = columns.index(col)
            # fallback if member_data has fewer items
            values.append(member_data[idx] if idx < len(member_data) else None)

    # 4️⃣ Build placeholders dynamically
    placeholders = ",".join("?" for _ in columns)
    col_names = ",".join(columns)
    c.execute(f"INSERT INTO deleted_members ({col_names}) VALUES ({placeholders})", values)

    conn.commit()
    conn.close()

def archive_member(member_data):
    """Insert a member into deleted_members safely, dynamically handling columns."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Get deleted_members column names
    c.execute("PRAGMA table_info(deleted_members)")
    cols = [col[1] for col in c.fetchall()]  # list of column names

    # We assume the last column is 'deleted_at'
    values = list(member_data[:len(cols)-1])  # trim/extract only matching columns
    values.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))  # deleted_at

    placeholders = ",".join("?" for _ in values)
    c.execute(f"INSERT INTO deleted_members ({','.join(cols)}) VALUES ({placeholders})", values)
    conn.commit()
    conn.close()



# ------------------ Dues Functions ------------------ #
def add_dues_payment(member_id, amount, payment_date, method, notes, year=None):
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

def get_dues_by_id(payment_id):
    """
    Retrieve a single dues payment by its ID.
    Returns a tuple: (id, member_id, amount, date, year, method, notes)
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT id, member_id, amount, date, year, method, notes
        FROM dues
        WHERE id=? 
        LIMIT 1
    """, (payment_id,))
    row = c.fetchone()
    conn.close()
    return row

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


def update_dues_payment(payment_id, amount, date, method, notes, year):
    """
    Update an existing dues payment with new data.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE dues
        SET amount=?, date=?, method=?, notes=?, year=?
        WHERE id=?
    """, (amount, date, method, notes, year, payment_id))
    conn.commit()
    conn.close()



def delete_dues_payment(payment_id):
    """
    Delete a dues payment by its ID.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM dues WHERE id=?", (payment_id,))
    conn.commit()
    conn.close()


# ------------------ Reporting Functions ------------------ #
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
                WHEN 'Life' THEN 'dues_life'
                ELSE 'dues_active'
            END
        WHERE m.membership_type IN ({placeholders})
        GROUP BY m.id
        HAVING outstanding <= 0
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
                WHEN 'Life' THEN 'dues_life'
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


def get_all_dues(year, included_types):
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
                WHEN 'Life' THEN 'dues_life'
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

# ------------------ Work Hours Functions ----------------- #
def init_work_hours_table():
    """Ensure the work_hours table exists with correct schema."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS work_hours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            hours REAL NOT NULL,
            work_type TEXT,
            notes TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

def add_work_hours(member_id, date, hours, work_type=None, notes=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO work_hours (member_id, date, hours, work_type, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (member_id, date, hours, work_type, notes))
    conn.commit()
    conn.close()

def get_work_hours(member_id=None):
    conn = get_connection()
    c = conn.cursor()
    if member_id:
        c.execute("SELECT id, member_id, date, hours, work_type, notes FROM work_hours WHERE member_id = ? ORDER BY date DESC", (member_id,))
    else:
        c.execute("SELECT id, member_id, date, hours, work_type, notes FROM work_hours ORDER BY date DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def get_work_hours_by_id(entry_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, member_id, date, hours, work_type, notes FROM work_hours WHERE id=?", (entry_id,))
    row = c.fetchone()
    conn.close()
    return row

def update_work_hours(entry_id, date, hours, work_type, notes):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE work_hours
        SET date=?, hours=?, work_type=?, notes=?
        WHERE id=?
    """, (date, hours, work_type, notes, entry_id))
    conn.commit()
    conn.close()

def delete_work_hours(entry_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM work_hours WHERE id=?", (entry_id,))
    conn.commit()
    conn.close()

# ------------------ Work Hours Functions ----------------- #
def init_work_hours_table():
    """Ensure the work_hours table exists with correct schema."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS work_hours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            hours REAL NOT NULL,
            work_type TEXT,
            notes TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

def add_work_hours(member_id, date, hours, work_type=None, notes=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO work_hours (member_id, date, hours, work_type, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (member_id, date, hours, work_type, notes))
    conn.commit()
    conn.close()

def get_work_hours(member_id=None):
    conn = get_connection()
    c = conn.cursor()
    if member_id:
        c.execute("SELECT id, member_id, date, hours, work_type, notes FROM work_hours WHERE member_id = ? ORDER BY date DESC", (member_id,))
    else:
        c.execute("SELECT id, member_id, date, hours, work_type, notes FROM work_hours ORDER BY date DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def get_work_hours_by_member(member_id):
    """Return all work hours for a specific member."""
    return get_work_hours(member_id=member_id)

def get_work_hours_by_id(entry_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, member_id, date, hours, work_type, notes FROM work_hours WHERE id=?", (entry_id,))
    row = c.fetchone()
    conn.close()
    return row

def update_work_hours(entry_id, date, hours, work_type, notes):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE work_hours
        SET date=?, hours=?, work_type=?, notes=?
        WHERE id=?
    """, (date, hours, work_type, notes, entry_id))
    conn.commit()
    conn.close()

def delete_work_hours(entry_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM work_hours WHERE id=?", (entry_id,))
    conn.commit()
    conn.close()

def update_member_basic(member_id, first_name, last_name, dob):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE members
        SET first_name=?, last_name=?, dob=?
        WHERE id=?
    """, (first_name, last_name, dob, member_id))
    conn.commit()
    conn.close()

def update_member_contact(member_id, email, email2, phone, address, city, state, zip_code):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE members
        SET email=?, email2=?, phone=?, address=?, city=?, state=?, zip=?
        WHERE id=?
    """, (email, email2, phone, address, city, state, zip_code, member_id))
    conn.commit()
    conn.close()

def update_member_membership(member_id, badge_number, membership_type, join_date, sponsor, card_internal, card_external):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE members
        SET badge_number=?, membership_type=?, join_date=?, sponsor=?, card_internal=?, card_external=?
        WHERE id=?
    """, (badge_number, membership_type, join_date, sponsor, card_internal, card_external, member_id))
    conn.commit()
    conn.close()

def get_work_hours_by_year(year):
    conn = get_connection()
    c = conn.cursor()

    # First try assuming ISO dates (YYYY-MM-DD or DATETIME)
    c.execute("""
        SELECT m.first_name, m.last_name, m.badge_number,
               SUM(w.hours) as total_hours
        FROM work_hours w
        JOIN members m ON m.id = w.member_id
        WHERE strftime('%Y', w.date) = ?
          AND m.deleted = 0
        GROUP BY m.id
        ORDER BY m.last_name, m.first_name
    """, (str(year),))
    rows = c.fetchall()

    # If nothing found, try fallback using last 4 chars of string (e.g. MM/DD/YYYY)
    if not rows:
        c.execute("""
            SELECT m.first_name, m.last_name, m.badge_number,
                   SUM(w.hours) as total_hours
            FROM work_hours w
            JOIN members m ON m.id = w.member_id
            WHERE substr(w.date, -4) = ?
              AND m.deleted = 0
            GROUP BY m.id
            ORDER BY m.last_name, m.first_name
        """, (str(year),))
        rows = c.fetchall()

    conn.close()
    return rows


def get_all_work_hours():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT wh.id, wh.member_id, wh.date, wh.hours, wh.work_type, wh.notes,
               m.first_name, m.last_name
        FROM work_hours wh
        JOIN members m ON wh.member_id = m.id
        ORDER BY wh.date DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "member_id": row[1],
            "date": row[2],
            "hours": row[3],
            "work_type": row[4],
            "notes": row[5],
            "first_name": row[6],
            "last_name": row[7],
        })
    return result

# ------------------ Meeting Attendance Functions ----------------- #
def init_meeting_attendance_table():
    """Ensure the meeting_attendance table exists with correct schema."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS meeting_attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            meeting_date TEXT NOT NULL,
            attended INTEGER NOT NULL DEFAULT 1,
            notes TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()


def add_meeting_attendance(member_id, meeting_date, attended=1, notes=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO meeting_attendance (member_id, meeting_date, attended, notes)
        VALUES (?, ?, ?, ?)
    """, (member_id, meeting_date, attended, notes))
    conn.commit()
    conn.close()

def update_meeting_attendance(entry_id, meeting_date=None, attended=None, notes=None):
    conn = get_connection()
    c = conn.cursor()
    updates = []
    params = []
    if meeting_date is not None:
        updates.append("meeting_date=?")
        params.append(meeting_date)
    if attended is not None:
        updates.append("attended=?")
        params.append(attended)
    if notes is not None:
        updates.append("notes=?")
        params.append(notes)
    params.append(entry_id)
    c.execute(f"""
        UPDATE meeting_attendance
        SET {', '.join(updates)}
        WHERE id=?
    """, params)
    conn.commit()
    conn.close()

def delete_meeting_attendance(entry_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM meeting_attendance WHERE id=?", (entry_id,))
    conn.commit()
    conn.close()

def get_meeting_attendance(member_id=None, year=None, month=None):
    """
    Returns attendance rows.
    Optionally filter by member_id, year (YYYY), month (1-12).
    """
    conn = get_connection()
    c = conn.cursor()
    query = "SELECT id, member_id, meeting_date, attended, notes FROM meeting_attendance WHERE 1=1"
    params = []
    if member_id is not None:
        query += " AND member_id=?"
        params.append(member_id)
    if year is not None:
        query += " AND strftime('%Y', meeting_date)=?"
        params.append(str(year))
    if month is not None:
        query += " AND strftime('%m', meeting_date)=?"
        params.append(f"{int(month):02d}")
    query += " ORDER BY meeting_date DESC"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows

def get_attendance_summary(year=None, month=None):
    """
    Returns summary counts for each member, using badge_number instead of member_id.
    Handles both ISO dates (YYYY-MM-DD) and US-style dates (MM/DD/YYYY).
    """
    conn = get_connection()
    c = conn.cursor()

    # Left join so attendance rows without a member still appear
    query = """
        SELECT 
            COALESCE(m.badge_number, 'Unknown') AS badge_number,
            COALESCE(m.first_name, 'Unknown') AS first_name,
            COALESCE(m.last_name, 'Unknown') AS last_name,
            COUNT(ma.id) AS total_meetings,
            SUM(ma.attended) AS attended_meetings
        FROM meeting_attendance ma
        LEFT JOIN members m ON ma.member_id = m.id
    """
    
    conditions = []
    params = []

    if year is not None:
        conditions.append(
            "(strftime('%Y', ma.meeting_date) = ? OR substr(ma.meeting_date, -4) = ?)"
        )
        params.extend([str(year), str(year)])

    if month is not None:
        month_num = f"{int(month):02d}"
        conditions.append(
            "(strftime('%m', ma.meeting_date) = ? OR substr(ma.meeting_date, 1, 2) = ?)"
        )
        params.extend([month_num, month_num])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " GROUP BY ma.member_id ORDER BY last_name, first_name"

    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows




# Ensure work_hours table exists on import
try:
    init_work_hours_table()
    init_meeting_attendance_table()
except Exception as e:
    print("⚠️ Failed to initialize work_hours table:", e)

