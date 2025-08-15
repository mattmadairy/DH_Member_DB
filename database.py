import sqlite3
import csv
import os
from datetime import datetime

DB_FILE = "members.db"

def get_all_members():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE deleted_at IS NULL ORDER BY badge_number ASC")
    members = cursor.fetchall()
    conn.close()
    return members

def get_deleted_members():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE deleted_at IS NOT NULL ORDER BY badge_number ASC")
    members = cursor.fetchall()
    conn.close()
    return members

def get_member_by_id(member_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE id = ?", (member_id,))
    member = cursor.fetchone()
    conn.close()
    return member

def add_member(*args):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO members (
            badge_number, membership_type, first_name, last_name, dob, email, phone, address,
            city, state, zip_code, join_date, email2, sponsor, card_internal, card_external
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, args)
    conn.commit()
    conn.close()

def update_member(member_id, *args):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE members SET
            badge_number=?, membership_type=?, first_name=?, last_name=?, dob=?, email=?, phone=?, address=?,
            city=?, state=?, zip_code=?, join_date=?, email2=?, sponsor=?, card_internal=?, card_external=?
        WHERE id=?
    """, (*args, member_id))
    conn.commit()
    conn.close()

def soft_delete_member_by_badge(badge_number):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE members
        SET deleted_at = ?
        WHERE badge_number = ? AND deleted_at IS NULL
    """, (datetime.now().isoformat(), badge_number))
    conn.commit()
    conn.close()

def restore_member_by_badge(badge_number):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE members
        SET deleted_at = NULL
        WHERE badge_number = ?
    """, (badge_number,))
    conn.commit()
    conn.close()

def export_members_to_csv(member_types):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Filtering logic
    if "All" in member_types:
        cursor.execute("SELECT * FROM members WHERE deleted_at IS NULL ORDER BY badge_number ASC")
    else:
        placeholders = ",".join("?" for _ in member_types)
        cursor.execute(
            f"SELECT * FROM members WHERE deleted_at IS NULL AND LOWER(membership_type) IN ({placeholders}) ORDER BY badge_number ASC",
            [m.lower() for m in member_types]
        )

    members = cursor.fetchall()
    conn.close()

    # Prepare CSV path
    export_folder = "exports"
    os.makedirs(export_folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(export_folder, f"members_export_{timestamp}.csv")

    # Write to CSV
    with open(filepath, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        headers = [
            "ID", "Badge Number", "Membership Type", "First Name", "Last Name",
            "Date of Birth", "Email Address", "Phone Number", "Address", "City",
            "State", "Zip Code", "Join Date", "Email Address 2", "Sponsor",
            "Card/Fob Internal Number", "Card/Fob External Number", "Deleted At"
        ]
        writer.writerow(headers)
        writer.writerows(members)

    return os.path.abspath(filepath)
