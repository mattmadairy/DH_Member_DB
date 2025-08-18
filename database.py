import sqlite3
from datetime import datetime
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "members.db")

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    with get_connection() as conn:
        c = conn.cursor()
        # Main members table
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
        # Recycle log table
        c.execute("""
        CREATE TABLE IF NOT EXISTS deletion_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            action TEXT,                -- "delete", "restore", "permanent_delete"
            timestamp TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id)
        )
        """)
        conn.commit()

def get_all_members():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM members WHERE deleted_at IS NULL")
        return c.fetchall()

def get_deleted_members():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM members WHERE deleted_at IS NOT NULL")
        return c.fetchall()

def add_member(data):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO members (
                badge_number, membership_type, first_name, last_name, dob, email,
                phone, address, city, state, zip_code, join_date, email2,
                sponsor, card_internal, card_external, deleted_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
        """, data)
        conn.commit()

def update_member(member_id, data):
    """
    Update a member, but keep existing values for any blank fields.
    `data` is the 16-field tuple from MemberForm.
    """
    with get_connection() as conn:
        c = conn.cursor()

        # Get current record
        c.execute("SELECT * FROM members WHERE id=?", (member_id,))
        existing = c.fetchone()
        if not existing:
            return False  # no such member

        # existing schema order:
        # (id, badge_number, membership_type, first_name, last_name,
        #  dob, email, phone, address, city, state, zip_code,
        #  join_date, email2, sponsor, card_internal, card_external, deleted_at)

        # Merge: use new value if not empty, else keep existing
        merged = []
        for new_val, old_val in zip(data, existing[1:17]):  # skip id, take 16 fields
            merged.append(new_val if new_val.strip() != "" else old_val)

        c.execute("""
            UPDATE members SET
                badge_number=?, membership_type=?, first_name=?, last_name=?,
                dob=?, email=?, phone=?, address=?, city=?, state=?, zip_code=?,
                join_date=?, email2=?, sponsor=?, card_internal=?, card_external=?
            WHERE id=?
        """, (*merged, member_id))

        conn.commit()
        return True


def soft_delete_member_by_id(member_id):
    with get_connection() as conn:
        c = conn.cursor()
        deleted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE members SET deleted_at=? WHERE id=?", (deleted_time, member_id))
        c.execute(
            "INSERT INTO deletion_log (member_id, action, timestamp) VALUES (?, ?, ?)",
            (member_id, "delete", deleted_time),
        )
        conn.commit()

def restore_member(member_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE members SET deleted_at=NULL WHERE id=?", (member_id,))
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            "INSERT INTO deletion_log (member_id, action, timestamp) VALUES (?, ?, ?)",
            (member_id, "restore", ts),
        )
        conn.commit()

def permanent_delete_member(member_id):
    with get_connection() as conn:
        c = conn.cursor()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("DELETE FROM members WHERE id=?", (member_id,))
        c.execute(
            "INSERT INTO deletion_log (member_id, action, timestamp) VALUES (?, ?, ?)",
            (member_id, "permanent_delete", ts),
        )
        conn.commit()

def get_deletion_log():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM deletion_log ORDER BY timestamp DESC")
        return c.fetchall()

def insert_member_from_dict(data: dict):
    """
    Insert a new member from a dictionary of values.
    Skips if a member with the same Badge Number already exists.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Check for duplicates by badge number
    cur.execute("SELECT id FROM members WHERE badge_number = ?", (data["Badge Number"],))
    if cur.fetchone():
        conn.close()
        return False  # duplicate found, skip

    cur.execute("""
        INSERT INTO members (
            badge_number, membership_type, first_name, last_name, dob,
            email, phone, address, city, state, zip_code,
            join_date, email2, sponsor,
            card_internal, card_external, deleted_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
    """, (
        data.get("Badge Number", ""),
        data.get("Membership Type", ""),
        data.get("First Name", ""),
        data.get("Last Name", ""),
        data.get("Date of Birth", ""),
        data.get("Email Address", ""),
        data.get("Phone Number", ""),
        data.get("Address", ""),
        data.get("City", ""),
        data.get("State", ""),
        data.get("Zip Code", ""),
        data.get("Join Date", datetime.now().strftime("%Y-%m-%d")),  # default join date = today
        data.get("Email Address 2", ""),
        data.get("Sponsor", ""),
        data.get("Card/Fob Internal Number", ""),
        data.get("Card/Fob External Number", ""),
    ))

    conn.commit()
    conn.close()
    return True  # inserted successfully

def get_member_by_id(member_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM members WHERE id=?", (member_id,))
        return c.fetchone()
