import sqlite3 
from datetime import datetime
import os
import csv

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

# -------------------------
# MEMBERS HELPERS
# -------------------------

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

        c.execute("SELECT * FROM members WHERE id=?", (member_id,))
        existing = c.fetchone()
        if not existing:
            return False

        merged = []
        for new_val, old_val in zip(data, existing[1:17]):
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
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM members WHERE badge_number = ?", (data["Badge Number"],))
    if cur.fetchone():
        conn.close()
        return False

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
        data.get("Join Date", datetime.now().strftime("%Y-%m-%d")),
        data.get("Email Address 2", ""),
        data.get("Sponsor", ""),
        data.get("Card/Fob Internal Number", ""),
        data.get("Card/Fob External Number", ""),
    ))
    conn.commit()
    conn.close()
    return True

def get_member_by_id(member_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM members WHERE id=?", (member_id,))
        return c.fetchone()

# -------------------------
# DUES HELPERS (per-year tables)
# -------------------------

def ensure_dues_table(year):
    """
    Create the dues table for a given year if it doesn't exist.
    """
    table_name = f"{year}_dues"
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(f"""
        CREATE TABLE IF NOT EXISTS "{table_name}" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_date TEXT NOT NULL,
            payment_method TEXT,
            notes TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
        )
        """)
        conn.commit()
    return table_name

def add_dues_payment(member_id, amount, year, payment_method="", notes=""):
    table = ensure_dues_table(year)
    payment_date = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(f"""
            INSERT INTO "{table}" (member_id, amount, payment_date, payment_method, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (member_id, amount, payment_date, payment_method, notes))
        conn.commit()

def get_dues_for_member(member_id, year):
    table = ensure_dues_table(year)
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(f"""
            SELECT id, amount, payment_date, payment_method, notes
            FROM "{table}"
            WHERE member_id=?
            ORDER BY payment_date DESC
        """, (member_id,))
        return c.fetchall()

def has_paid_dues(member_id, year):
    table = ensure_dues_table(year)
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(f"SELECT 1 FROM \"{table}\" WHERE member_id=? LIMIT 1", (member_id,))
        return c.fetchone() is not None

def get_members_missing_dues(year):
    table = ensure_dues_table(year)
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(f"""
            SELECT m.id, m.first_name, m.last_name, m.badge_number, m.email
            FROM members m
            WHERE m.deleted_at IS NULL
              AND m.id NOT IN (
                  SELECT member_id FROM "{table}"
              )
            ORDER BY m.last_name, m.first_name
        """)
        return c.fetchall()

def get_dues_summary(year):
    table = ensure_dues_table(year)
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM members WHERE deleted_at IS NULL")
        total_members = c.fetchone()[0]

        c.execute(f"SELECT COUNT(DISTINCT member_id) FROM \"{table}\"")
        paid_members = c.fetchone()[0]

        unpaid_members = total_members - paid_members

        c.execute(f"SELECT SUM(amount) FROM \"{table}\"")
        total_amount_collected = c.fetchone()[0] or 0.0

        return {
            "year": year,
            "total_members": total_members,
            "paid_members": paid_members,
            "unpaid_members": unpaid_members,
            "total_amount_collected": total_amount_collected,
        }

def export_dues_to_csv(year, filename="dues_export.csv"):
    table = ensure_dues_table(year)
    with get_connection() as conn, open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Dues ID", "Member ID", "First Name", "Last Name", "Badge Number",
            "Amount", "Payment Date", "Payment Method", "Notes"
        ])
        c = conn.cursor()
        c.execute(f"""
            SELECT d.id, m.id, m.first_name, m.last_name, m.badge_number,
                   d.amount, d.payment_date, d.payment_method, d.notes
            FROM "{table}" d
            JOIN members m ON d.member_id = m.id
            ORDER BY d.payment_date DESC
        """)
        for row in c.fetchall():
            writer.writerow(row)
    return filename

def export_missing_dues_to_csv(year, filename="missing_dues_export.csv"):
    table = ensure_dues_table(year)
    with get_connection() as conn, open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Member ID", "First Name", "Last Name", "Badge Number", "Email", "Phone"
        ])
        c = conn.cursor()
        c.execute(f"""
            SELECT m.id, m.first_name, m.last_name, m.badge_number, m.email, m.phone
            FROM members m
            WHERE m.deleted_at IS NULL
              AND m.id NOT IN (
                  SELECT member_id FROM "{table}"
              )
            ORDER BY m.last_name, m.first_name
        """)
        for row in c.fetchall():
            writer.writerow(row)
    return filename

def get_dues_by_member(member_id):
    """
    Return all dues payments for a given member across all yearly dues tables.
    """
    with get_connection() as conn:
        c = conn.cursor()
        # Get all dues tables dynamically
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_dues'")
        dues_tables = [row[0] for row in c.fetchall()]

        results = []
        for table in dues_tables:
            c.execute(f"""
                SELECT id, payment_date, amount, notes, '{table}' as table_name
                FROM "{table}" 
                WHERE member_id = ?
            """, (member_id,))
            results.extend(c.fetchall())

        # Sort all payments by date descending
        results.sort(key=lambda r: r[1], reverse=True)
        return results


def add_due_payment(member_id, payment_date, amount, notes="", payment_method="", year=None):
    """
    Insert a new dues payment for a member.
    If no year is given, use the current year.
    """
    if year is None:
        year = datetime.now().year
    table = ensure_dues_table(year)

    with get_connection() as conn:
        c = conn.cursor()
        c.execute(f"""
            INSERT INTO "{table}" (member_id, amount, payment_date, payment_method, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (member_id, amount, payment_date, payment_method, notes))
        conn.commit()

