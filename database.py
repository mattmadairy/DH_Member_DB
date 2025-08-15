import sqlite3
import csv
from datetime import datetime
import os

DB_NAME = "members.db"

def connect():
    conn = sqlite3.connect(DB_NAME)
    return conn

def create_table():
    conn = connect()
    c = conn.cursor()
    c.execute("""
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
            zip_code TEXT,
            join_date TEXT,
            email2 TEXT,
            sponsor TEXT,
            card_fob_internal TEXT,
            card_fob_external TEXT,
            deleted_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_member(badge_number, membership_type, first_name, last_name, dob,
               email, email2, phone, address, city, state, zip_code, join_date,
               sponsor, card_fob_internal, card_fob_external):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO members (
            badge_number, membership_type, first_name, last_name, dob, email,
            phone, address, city, state, zip_code, join_date, email2, sponsor,
            card_fob_internal, card_fob_external, deleted_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
    """, (
        badge_number, membership_type, first_name, last_name, dob, email, phone,
        address, city, state, zip_code, join_date, email2, sponsor,
        card_fob_internal, card_fob_external
    ))
    conn.commit()
    conn.close()

def update_member(member_id, badge_number, membership_type, first_name, last_name, dob,
                  email, email2, phone, address, city, state, zip_code, join_date,
                  sponsor, card_fob_internal, card_fob_external):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        UPDATE members SET
            badge_number=?, membership_type=?, first_name=?, last_name=?, dob=?, email=?,
            phone=?, address=?, city=?, state=?, zip_code=?, join_date=?, email2=?, sponsor=?,
            card_fob_internal=?, card_fob_external=?
        WHERE id=?
    """, (
        badge_number, membership_type, first_name, last_name, dob, email, phone,
        address, city, state, zip_code, join_date, email2, sponsor,
        card_fob_internal, card_fob_external, member_id
    ))
    conn.commit()
    conn.close()

def get_all_members():
    conn = connect()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM members
        WHERE deleted_at IS NULL
        ORDER BY badge_number
    """)
    rows = c.fetchall()
    conn.close()
    return rows

def get_member_by_id(member_id):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE id=?", (member_id,))
    row = c.fetchone()
    conn.close()
    return row

def soft_delete_member_by_badge(badge_number):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        UPDATE members SET deleted_at=?
        WHERE badge_number=?
    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), badge_number))
    conn.commit()
    conn.close()

def get_deleted_members():
    conn = connect()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM members
        WHERE deleted_at IS NOT NULL
        ORDER BY deleted_at DESC
    """)
    rows = c.fetchall()
    conn.close()
    return rows

def restore_member_by_badge(badge_number):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        UPDATE members SET deleted_at=NULL
        WHERE badge_number=?
    """, (badge_number,))
    conn.commit()
    conn.close()

def export_members_to_csv(member_types):
    members = get_all_members()
    if "All" not in member_types:
        members = [m for m in members if m[2] in member_types]

    filename = f"members_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join(os.getcwd(), filename)

    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "ID", "Badge Number", "Membership Type", "First Name", "Last Name",
            "Date of Birth", "Email Address", "Phone Number", "Address", "City",
            "State", "Zip Code", "Join Date", "Email Address 2", "Sponsor",
            "Card/Fob Internal Number", "Card/Fob External Number", "Deleted At"
        ])
        for m in members:
            writer.writerow(m)

    return filepath

# Initialize DB if not exists
create_table()
