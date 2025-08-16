import sqlite3
from datetime import datetime

DB_NAME = "members.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Create table if not exists
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
            zip_code TEXT,
            join_date TEXT,
            email2 TEXT,
            sponsor TEXT,
            card_internal TEXT,
            card_external TEXT,
            deleted_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def add_member(
    badge_number, member_type, first_name, last_name, dob,
    email, phone, address, city, state, zip_code,
    join_date, sponsor, email2,
    card_internal, card_external
):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        INSERT INTO members (
            badge_number, membership_type, first_name, last_name, dob,
            email, phone, address, city, state, zip_code,
            join_date, sponsor, email2,
            card_internal, card_external, deleted_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
    """, (
        badge_number, member_type, first_name, last_name, dob,
        email, phone, address, city, state, zip_code,
        join_date, sponsor, email2,
        card_internal, card_external
    ))

    conn.commit()
    conn.close()


def get_all_members():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE deleted_at IS NULL")
    rows = c.fetchall()
    conn.close()
    return rows


def get_member_by_id(member_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE id=?", (member_id,))
    row = c.fetchone()
    conn.close()
    return row


def update_member(
    member_id, badge_number, member_type, first_name, last_name, dob,
    email, phone, address, city, state, zip_code,
    join_date, sponsor, email2,
    card_internal, card_external
):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        UPDATE members
        SET badge_number=?, membership_type=?, first_name=?, last_name=?, dob=?,
            email=?, phone=?, address=?, city=?, state=?, zip_code=?,
            join_date=?, sponsor=?, email2=?,
            card_internal=?, card_external=?
        WHERE id=?
    """, (
        badge_number, member_type, first_name, last_name, dob,
        email, phone, address, city, state, zip_code,
        join_date, sponsor, email2,
        card_internal, card_external,
        member_id
    ))

    conn.commit()
    conn.close()


def soft_delete_member_by_badge(member_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE members SET deleted_at=? WHERE id=?", (datetime.now().isoformat(), member_id))
    conn.commit()
    conn.close()


def get_deleted_members():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE deleted_at IS NOT NULL")
    rows = c.fetchall()
    conn.close()
    return rows


def restore_member(member_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE members SET deleted_at=NULL WHERE id=?", (member_id,))
    conn.commit()
    conn.close()


def permanent_delete_member(member_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM members WHERE id=?", (member_id,))
    conn.commit()
    conn.close()
