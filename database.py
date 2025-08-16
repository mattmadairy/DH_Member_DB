import sqlite3
import os
from datetime import datetime
import csv

DB_FILE = "members.db"

def _connect():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        badge_number TEXT UNIQUE,
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
    conn.commit()

    # Add starter data if table is empty
    cur.execute("SELECT COUNT(*) FROM members")
    if cur.fetchone()[0] == 0:
        sample_members = [
            ("1001", "Active", "John", "Doe", "01/15/1985",
             "john.doe@email.com", "john.alt@email.com", "555-123-4567",
             "123 Main St", "Springfield", "AL", "35801",
             "03/20/2020", "Jane Smith", "INT1001", "EXT2001", None),

            ("1002", "Probationary", "Alice", "Johnson", "07/22/1990",
             "alice.j@email.com", "", "555-987-6543",
             "456 Oak Ave", "Huntsville", "AL", "35802",
             "05/10/2023", "John Doe", "INT1002", "EXT2002", None),
        ]
        cur.executemany("""
            INSERT INTO members (
                badge_number, membership_type, first_name, last_name, dob,
                email, email2, phone, address, city, state, zip,
                join_date, sponsor, card_internal, card_external, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_members)
        conn.commit()

    conn.close()

def add_member(badge_number, membership_type, first_name, last_name, dob,
               email, email2, phone, address, city, state, zip_code,
               join_date, sponsor, card_internal, card_external):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO members (
            badge_number, membership_type, first_name, last_name, dob,
            email, email2, phone, address, city, state, zip,
            join_date, sponsor, card_internal, card_external, deleted_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
    """, (badge_number, membership_type, first_name, last_name, dob,
          email, email2, phone, address, city, state, zip_code,
          join_date, sponsor, card_internal, card_external))
    conn.commit()
    conn.close()

def update_member(member_id, badge_number, membership_type, first_name, last_name, dob,
                  email, email2, phone, address, city, state, zip_code,
                  join_date, sponsor, card_internal, card_external):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        UPDATE members SET
            badge_number=?, membership_type=?, first_name=?, last_name=?, dob=?,
            email=?, email2=?, phone=?, address=?, city=?, state=?, zip=?,
            join_date=?, sponsor=?, card_internal=?, card_external=?
        WHERE id=?
    """, (badge_number, membership_type, first_name, last_name, dob,
          email, email2, phone, address, city, state, zip_code,
          join_date, sponsor, card_internal, card_external, member_id))
    conn.commit()
    conn.close()

def get_all_members():
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM members WHERE deleted_at IS NULL")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_member_by_id(member_id):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM members WHERE id=?", (member_id,))
    row = cur.fetchone()
    conn.close()
    return row

def soft_delete_member_by_badge(badge_number):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("UPDATE members SET deleted_at=? WHERE badge_number=?", (datetime.now().isoformat(), badge_number))
    conn.commit()
    conn.close()

def get_deleted_members():
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM members WHERE deleted_at IS NOT NULL")
    rows = cur.fetchall()
    conn.close()
    return rows

def restore_member_by_badge(badge_number):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("UPDATE members SET deleted_at=NULL WHERE badge_number=?", (badge_number,))
    conn.commit()
    conn.close()

def export_members_to_csv(member_types, filepath=None):
    conn = _connect()
    cur = conn.cursor()
    if "All" in member_types:
        cur.execute("SELECT * FROM members WHERE deleted_at IS NULL")
    else:
        placeholders = ",".join("?" * len(member_types))
        cur.execute(f"SELECT * FROM members WHERE deleted_at IS NULL AND membership_type IN ({placeholders})", tuple(member_types))
    rows = cur.fetchall()
    conn.close()

    if not filepath:
        filepath = os.path.join(os.getcwd(), f"members_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

    headers = [
        "ID", "Badge Number", "Membership Type", "First Name", "Last Name",
        "Date of Birth", "Email Address", "Phone Number", "Address",
        "City", "State", "Zip Code", "Join Date", "Email Address 2",
        "Sponsor", "Card/Fob Internal Number", "Card/Fob External Number",
        "Deleted At"
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    return filepath

# Initialize DB + seed data
init_db()
