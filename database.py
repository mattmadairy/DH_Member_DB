import sqlite3
import os
import csv
from datetime import datetime

DB_FILE = "members.db"


def create_table():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS members (
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
            card_fob_internal TEXT,
            card_fob_external TEXT,
            deleted_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def add_member(badge_number, membership_type, first_name, last_name, date_of_birth,
               email_address, email_address_2, phone_number, address, city, state,
               zip_code, join_date, sponsor, card_fob_internal, card_fob_external):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO members (
            badge_number, membership_type, first_name, last_name, date_of_birth,
            email_address, email_address_2, phone_number, address, city, state,
            zip_code, join_date, sponsor, card_fob_internal, card_fob_external
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (badge_number, membership_type, first_name, last_name, date_of_birth,
          email_address, email_address_2, phone_number, address, city, state,
          zip_code, join_date, sponsor, card_fob_internal, card_fob_external))
    conn.commit()
    conn.close()


def get_all_members():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE deleted_at IS NULL")
    members = cursor.fetchall()
    conn.close()
    return members


def get_member_by_id(member_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE id=?", (member_id,))
    member = cursor.fetchone()
    conn.close()
    return member


def update_member(member_id, badge_number, membership_type, first_name, last_name, date_of_birth,
                  email_address, email_address_2, phone_number, address, city, state,
                  zip_code, join_date, sponsor, card_fob_internal, card_fob_external):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE members
        SET badge_number=?, membership_type=?, first_name=?, last_name=?, date_of_birth=?,
            email_address=?, email_address_2=?, phone_number=?, address=?, city=?, state=?,
            zip_code=?, join_date=?, sponsor=?, card_fob_internal=?, card_fob_external=?
        WHERE id=?
    """, (badge_number, membership_type, first_name, last_name, date_of_birth,
          email_address, email_address_2, phone_number, address, city, state,
          zip_code, join_date, sponsor, card_fob_internal, card_fob_external, member_id))
    conn.commit()
    conn.close()


def soft_delete_member_by_badge(badge_number):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE members
        SET deleted_at=datetime('now')
        WHERE badge_number=?
    """, (badge_number,))
    conn.commit()
    conn.close()


def get_deleted_members():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE deleted_at IS NOT NULL")
    members = cursor.fetchall()
    conn.close()
    return members


def restore_member_by_badge(badge_number):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE members
        SET deleted_at=NULL
        WHERE badge_number=?
    """, (badge_number,))
    conn.commit()
    conn.close()


def export_members_to_csv():
    # Get Downloads folder path
    downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")

    # Create filename with date and time
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"DHRGC_members_export_{timestamp}.csv"
    filepath = os.path.join(downloads_path, filename)

    # Connect to the database and fetch all members
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE deleted_at IS NULL")
    rows = cursor.fetchall()

    # Get column names
    col_names = [description[0] for description in cursor.description]

    # Write CSV
    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(col_names)
        writer.writerows(rows)

    conn.close()
    return filepath


# Ensure table exists on first run
create_table()
